"""
OmniAgent X - Kernel Subkernel Integration
==========================================
Kernel integration with Subkernel Architecture

Bu modul kernelni subkernel arxitekturaga ulaydi.
Kernel endi capability'larni subkernel registry orqali chaqiradi.
"""

import logging
from typing import Dict, List, Optional, Any, Set, Callable
from dataclasses import dataclass, field
from threading import RLock

from agent.subkernel import (
    # Core
    CoreComponent,
    PluggableCapability,
    SubkernelCategory,
    SubkernelStatus,
    TrustLevel,
    SubkernelInterface,
    
    # Spec & Registry
    SubkernelSpec,
    PluginManifest,
    CapabilityRegistry,
    get_capability_registry,
    
    # Lifecycle
    LifecycleManager,
    get_lifecycle_manager,
    SubkernelProvider,
    
    # Trust & Policy
    TrustManager,
    get_trust_manager,
    PolicyPosture,
    
    # Sandbox
    SandboxManager,
    get_sandbox_manager,
)


logger = logging.getLogger(__name__)


@dataclass
class SubkernelGateway:
    """
    Subkernel Gateway - Kernel va Subkernel o'rtasidagi bridge
    
    Bu gateway:
    - Kernel request'larini subkernel call'lariga o'giradi
    - Subkernel response'larini kernel formatiga qaytaradi
    - Health va status monitoring qiladi
    - Capability gating qo'llaydi
    """
    
    # Core components
    registry: CapabilityRegistry
    lifecycle: LifecycleManager
    trust_manager: TrustManager
    sandbox_manager: SandboxManager
    
    # Kernel reference
    kernel: Optional[Any] = None
    
    # Lock for thread safety
    _lock: Any = field(default_factory=RLock, repr=False)
    
    def __post_init__(self):
        """Initialize gateway"""
        # Set up event handlers
        self._setup_event_handlers()
        
        logger.info("🌐 Subkernel Gateway initialized")
    
    def _setup_event_handlers(self):
        """Set up event handlers for lifecycle changes"""
        # React to subkernel status changes
        self.registry.subscribe(
            "status_changed",
            self._on_status_changed
        )
        
        self.registry.subscribe(
            "health_changed",
            self._on_health_changed
        )
    
    def _on_status_changed(self, data: Dict):
        """Handle status change event"""
        name = data.get("name")
        status = data.get("status")
        logger.info(f"🔄 Subkernel {name} status changed to {status}")
        
        # Notify kernel if needed
        if self.kernel:
            self.kernel.notify_subkernel_status(name, status)
    
    def _on_health_changed(self, data: Dict):
        """Handle health change event"""
        name = data.get("name")
        old_health = data.get("old_health")
        new_health = data.get("new_health")
        
        logger.info(f"💚 Subkernel {name} health: {old_health} -> {new_health}")
        
        # Check if health dropped below threshold
        if new_health < 0.3:
            logger.warning(f"⚠️ Subkernel {name} health critical!")
            
            # Trigger degradation if needed
            if self.trust_manager.should_quarantine(name):
                reason = self.trust_manager.get_quarantine_reason(name)
                self.lifecycle.quarantine_provider(name, reason)
    
    # ==================== CAPABILITY GATING ====================
    
    def can_execute_capability(
        self, 
        capability: PluggableCapability,
        operation: str = "execute"
    ) -> tuple[bool, Optional[str]]:
        """
        Check if capability can be executed
        
        Returns:
            (allowed, reason_if_not)
        """
        # Get manifest
        manifest = self.registry.get_by_capability(capability)
        
        if not manifest:
            return False, f"Capability {capability.value} not registered"
        
        # Check if active
        if not manifest.is_active:
            return False, f"Capability {capability.value} not active"
        
        # Check health
        if not manifest.is_healthy():
            return False, f"Capability {capability.value} not healthy (health: {manifest.health_score})"
        
        # Check trust policy
        trust = self.trust_manager.get_trust_level(manifest.spec.name)
        
        if trust == TrustLevel.EXPERIMENTAL:
            # Check if operation is allowed in experimental mode
            posture = self.trust_manager.get_posture()
            if posture == PolicyPosture.PRODUCTION:
                return False, f"Experimental capability {capability.value} not allowed in production"
        
        return True, None
    
    # ==================== EXECUTION ====================
    
    async def execute_capability(
        self,
        capability: PluggableCapability,
        method: str,
        *args,
        **kwargs
    ) -> Any:
        """
        Execute a capability method through subkernel
        
        This is the main entry point for executing subkernel capabilities.
        """
        # Check if can execute
        allowed, reason = self.can_execute_capability(capability)
        if not allowed:
            raise PermissionError(f"Cannot execute {capability.value}.{method}: {reason}")
        
        # Get manifest
        manifest = self.registry.get_by_capability(capability)
        if not manifest:
            raise ValueError(f"Capability {capability.value} not found")
        
        # Get sandbox if needed
        trust = self.trust_manager.get_trust_level(manifest.spec.name)
        
        if trust == TrustLevel.EXPERIMENTAL:
            # Execute in sandbox
            sandbox = self.sandbox_manager.get_or_create_sandbox(
                manifest.spec.name,
                self.trust_manager.get_trust_policy(manifest.spec.name),
                None
            )
            
        # Record call in registry
        import time
        start = time.time()
        
        try:
            # Execute (simplified - actual execution would call the provider)
            result = {
                "status": "success",
                "capability": capability.value,
                "method": method,
            }
            
            # Record success
            latency_ms = (time.time() - start) * 1000
            self.registry.record_call(manifest.spec.name, True, latency_ms)
            
            return result
            
        except Exception as e:
            # Record failure
            latency_ms = (time.time() - start) * 1000
            self.registry.record_call(manifest.spec.name, False, latency_ms)
            
            raise
    
    # ==================== QUERY ====================
    
    def get_capability_status(self, capability: PluggableCapability) -> Dict[str, Any]:
        """Get capability status"""
        manifest = self.registry.get_by_capability(capability)
        
        if not manifest:
            return {"available": False, "reason": "not_registered"}
        
        return {
            "available": manifest.is_active and manifest.is_healthy(),
            "status": manifest.status.value,
            "health_score": manifest.health_score,
            "trust_level": manifest.spec.trust_class.value,
            "category": manifest.spec.category.value,
        }
    
    def get_all_capabilities(self) -> List[Dict[str, Any]]:
        """Get all registered capabilities"""
        return [
            {
                "name": m.spec.name,
                "capability": m.spec.capability_type.value,
                "status": m.status.value,
                "is_active": m.is_active,
                "is_healthy": m.is_healthy(),
                "health_score": m.health_score,
                "trust_level": m.spec.trust_class.value,
                "category": m.spec.category.value,
            }
            for m in self.registry.get_all()
        ]
    
    def get_healthy_capabilities(self) -> List[PluggableCapability]:
        """Get list of healthy capabilities"""
        healthy = []
        for m in self.registry.get_healthy():
            if m.is_active:
                healthy.append(m.spec.capability_type)
        return healthy
    
    def get_degraded_capabilities(self) -> List[PluggableCapability]:
        """Get list of degraded capabilities"""
        degraded = []
        for m in self.registry.get_by_status(SubkernelStatus.DEGRADED):
            degraded.append(m.spec.capability_type)
        return degraded
    
    # ==================== LIFECYCLE ====================
    
    async def initialize_all_subkernels(self):
        """Initialize all registered subkernels"""
        results = await self.lifecycle.initialize_all()
        
        for name, success in results.items():
            if success:
                await self.lifecycle.activate_provider(name)
        
        return results
    
    async def shutdown_all_subkernels(self):
        """Shutdown all subkernels"""
        return await self.lifecycle.shutdown_all()
    
    def get_lifecycle_status(self) -> Dict[str, Any]:
        """Get lifecycle status"""
        return self.lifecycle.get_status()
    
    # ==================== TRUST ====================
    
    def set_posture(self, posture: PolicyPosture):
        """Set system posture"""
        self.trust_manager.set_posture(posture)
    
    def get_posture(self) -> PolicyPosture:
        """Get current posture"""
        return self.trust_manager.get_posture()
    
    def get_trust_summary(self) -> Dict[str, Any]:
        """Get trust summary"""
        return self.trust_manager.get_trust_summary()


def create_subkernel_gateway(
    kernel: Optional[Any] = None,
    registry: Optional[CapabilityRegistry] = None,
) -> SubkernelGateway:
    """
    Create and configure Subkernel Gateway
    
    This is the main entry point for setting up the subkernel integration.
    """
    # Get or create registry
    if registry is None:
        registry = get_capability_registry()
    
    # Get or create lifecycle manager
    lifecycle = get_lifecycle_manager()
    
    # Get or create trust manager
    trust_manager = get_trust_manager(registry)
    
    # Get or create sandbox manager
    sandbox_manager = get_sandbox_manager(trust_manager)
    
    # Create gateway
    gateway = SubkernelGateway(
        registry=registry,
        lifecycle=lifecycle,
        trust_manager=trust_manager,
        sandbox_manager=sandbox_manager,
        kernel=kernel,
    )
    
    return gateway


# ==================== KERNEL INTEGRATION ====================

class KernelSubkernelMixin:
    """
    Mixin for Kernel to integrate with Subkernel Architecture
    
    Add this mixin to Kernel to enable subkernel integration.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._subkernel_gateway: Optional[SubkernelGateway] = None
    
    def init_subkernel_gateway(self) -> SubkernelGateway:
        """Initialize subkernel gateway"""
        self._subkernel_gateway = create_subkernel_gateway(kernel=self)
        return self._subkernel_gateway
    
    @property
    def subkernel(self) -> SubkernelGateway:
        """Get subkernel gateway"""
        if self._subkernel_gateway is None:
            self._subkernel_gateway = self.init_subkernel_gateway()
        return self._subkernel_gateway
    
    def notify_subkernel_status(self, name: str, status: SubkernelStatus):
        """Handle subkernel status notification"""
        logger.info(f"📢 Kernel received: {name} -> {status.value}")
        
        # Could trigger kernel-level responses here
    
    def can_use_capability(self, capability: PluggableCapability) -> bool:
        """Check if capability can be used"""
        if self._subkernel_gateway is None:
            return False
        allowed, _ = self._subkernel_gateway.can_execute_capability(capability)
        return allowed
    
    def get_capability_info(self, capability: PluggableCapability) -> Dict[str, Any]:
        """Get capability information"""
        if self._subkernel_gateway is None:
            return {"available": False, "reason": "gateway_not_initialized"}
        return self._subkernel_gateway.get_capability_status(capability)
