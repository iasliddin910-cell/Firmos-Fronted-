"""
OmniAgent X - Provider Lifecycle Manager
=========================================
Manages subkernel lifecycle: discover, init, register, activate, degrade, unload

Bu manager har bir subkernel lifecycle'ini boshqaradi.
"""

import logging
import asyncio
import time
from typing import Dict, List, Optional, Any, Callable, Type
from threading import RLock
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod

from agent.subkernel import (
    SubkernelCategory, 
    SubkernelStatus, 
    TrustLevel,
    SubkernelInterface,
    PluggableCapability,
)
from agent.subkernel.spec import SubkernelSpec, PluginManifest
from agent.subkernel.registry import CapabilityRegistry, get_capability_registry


logger = logging.getLogger(__name__)


class LifecycleEvent(str, Enum):
    """Lifecycle events"""
    DISCOVERED = "discovered"
    VALIDATING = "validating"
    INITIALIZING = "initializing"
    INITIALIZED = "initialized"
    REGISTERED = "registered"
    PROBING = "probing"
    READY = "ready"
    ACTIVATED = "activated"
    DEGRADED = "degraded"
    QUARANTINED = "quarantined"
    DISABLED = "disabled"
    UNLOADING = "unloading"
    UNLOADED = "unloaded"
    FAILED = "failed"


@dataclass
class LifecycleTransition:
    """Lifecycle o'tish yozuvi"""
    from_state: SubkernelStatus
    to_state: SubkernelStatus
    timestamp: float
    reason: str
    error: Optional[str] = None


class SubkernelProvider(ABC):
    """
    Subkernel Provider - asosiy abstract class
    
    Har bir subkernel bu class'dan inheritance oladi.
    Bu class lifecycle method'larini taqdim etadi.
    """
    
    @abstractmethod
    def get_spec(self) -> SubkernelSpec:
        """Subkernel spec olish"""
        pass
    
    @abstractmethod
    async def initialize(self, config: Dict[str, Any]) -> bool:
        """Subkernel'ni ishga tushirish"""
        pass
    
    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Health check"""
        pass
    
    @abstractmethod
    async def shutdown(self) -> bool:
        """Subkernel'ni to'xtatish"""
        pass
    
    async def validate(self) -> bool:
        """Subkernel'ni validatsiya qilish"""
        # Default implementation - always valid
        return True
    
    async def probe(self, probe_name: str) -> Dict[str, Any]:
        """Maxsus probe"""
        return {"status": "ok", "probe": probe_name}
    
    async def on_activate(self):
        """Activate bo'lganda chaqiriladi"""
        pass
    
    async def on_deactivate(self):
        """Deactivate bo'lganda chaqiriladi"""
        pass
    
    async def on_degrade(self, reason: str):
        """Degrade bo'lganda chaqiriladi"""
        pass
    
    async def on_quarantine(self, reason: str):
        """Quarantine bo'lganda chaqiriladi"""
        pass
    
    async def on_recover(self):
        """Quarantine yoki degraded'dan qaytganda"""
        pass


class LifecycleManager:
    """
    Provider Lifecycle Manager
    
    Har subkernel lifecycle'ini boshqaradi:
    - discover: Topish
    - validate: Tekshirish
    - initialize: Ishga tushirish
    - register: Ro'yxatga olish
    - probe: Health probe
    - activate: Faollashtirish
    
    Va kerak bo'lsa:
    - degrade: Cheklangan holatga o'tkazish
    - quarantine: Izolyatsiya qilish
    - unload: Yuklash
    """
    
    def __init__(self, registry: Optional[CapabilityRegistry] = None):
        self._registry = registry or get_capability_registry()
        self._lock = RLock()
        
        # Registered providers
        self._providers: Dict[str, SubkernelProvider] = {}
        
        # Lifecycle history
        self._lifecycle_history: Dict[str, List[LifecycleTransition]] = {}
        
        # Event callbacks
        self._event_callbacks: Dict[LifecycleEvent, List[Callable]] = {
            event: [] for event in LifecycleEvent
        }
        
        # Config
        self._configs: Dict[str, Dict[str, Any]] = {}
        
        # Startup order
        self._startup_order: List[str] = []
    
    # ==================== REGISTRATION ====================
    
    def register_provider(self, provider: SubkernelProvider) -> bool:
        """
        Provider'ni ro'yxatga olish
        
        Bu method provider'ni lifecycle manager'ga qo'shadi.
        """
        with self._lock:
            spec = provider.get_spec()
            name = spec.name
            
            if name in self._providers:
                logger.warning(f"⚠️ Provider {name} already registered")
                return False
            
            # Validate spec
            if not spec.validate_version("2.0"):
                logger.error(f"❌ Provider {name} kernel version not compatible")
                return False
            
            # Store provider
            self._providers[name] = provider
            
            # Create manifest
            manifest = PluginManifest(spec=spec)
            manifest.is_loaded = True
            
            # Register with registry
            if not self._registry.register(manifest):
                logger.error(f"❌ Failed to register {name} in registry")
                del self._providers[name]
                return False
            
            logger.info(f"✅ Registered provider: {name}")
            return True
    
    def unregister_provider(self, name: str) -> bool:
        """Provider'ni ro'yxatdan o'chirish"""
        with self._lock:
            if name not in self._providers:
                return False
            
            # Shutdown first
            provider = self._providers[name]
            try:
                asyncio.run(provider.shutdown())
            except Exception as e:
                logger.error(f"Error shutting down {name}: {e}")
            
            # Unregister from registry
            self._registry.unregister(name, "provider_unregistered")
            
            # Remove
            del self._providers[name]
            
            logger.info(f"🗑️ Unregistered provider: {name}")
            return True
    
    # ==================== LIFECYCLE ====================
    
    async def discover_providers(self) -> List[str]:
        """
        Auto-discover providers
        
        Bu method barcha mavjud provider'larni topadi.
        Hozircha qo'lda ro'yxat, keyinchalik auto-discovery qilinadi.
        """
        discovered = []
        
        # Built-in providers ro'yxati
        builtin_providers = [
            "sandbox",
            "health_check",
            "tool_engine",
            "native_brain",
            "semantic_memory",
            "browser_execution",
            "code_execution",
            "replay_engine",
        ]
        
        for name in builtin_providers:
            if name in self._providers:
                discovered.append(name)
        
        return discovered
    
    async def validate_provider(self, name: str) -> bool:
        """Provider'ni validatsiya qilish"""
        with self._lock:
            provider = self._providers.get(name)
            if not provider:
                return False
            
            self._record_transition(name, SubkernelStatus.DISCOVERED, SubkernelStatus.VALIDATING, "validation")
            
            try:
                is_valid = await provider.validate()
                if is_valid:
                    self._record_transition(name, SubkernelStatus.VALIDATING, SubkernelStatus.DISCOVERED, "validation_passed")
                    return True
                else:
                    self._record_transition(name, SubkernelStatus.VALIDATING, SubkernelStatus.FAILED, "validation_failed")
                    return False
            except Exception as e:
                logger.error(f"Validation error for {name}: {e}")
                self._record_transition(name, SubkernelStatus.VALIDATING, SubkernelStatus.FAILED, str(e), str(e))
                return False
    
    async def initialize_provider(self, name: str, config: Optional[Dict[str, Any]] = None) -> bool:
        """Provider'ni ishga tushirish"""
        with self._lock:
            provider = self._providers.get(name)
            if not provider:
                logger.error(f"❌ Provider {name} not found")
                return False
            
            manifest = self._registry.get(name)
            if not manifest:
                logger.error(f"❌ Manifest for {name} not found")
                return False
            
            self._record_transition(name, SubkernelStatus.DISCOVERED, SubkernelStatus.INITIALIZING, "initialization")
            
            # Use provided config or get from stored
            init_config = config or self._configs.get(name, {})
            
            try:
                manifest.status = SubkernelStatus.INITIALIZING
                success = await provider.initialize(init_config)
                
                if success:
                    manifest.status = SubkernelStatus.READY
                    manifest.is_loaded = True
                    self._record_transition(name, SubkernelStatus.INITIALIZING, SubkernelStatus.READY, "initialization_complete")
                    logger.info(f"✅ Initialized provider: {name}")
                    return True
                else:
                    manifest.status = SubkernelStatus.FAILED
                    manifest.load_error = "Initialization failed"
                    self._record_transition(name, SubkernelStatus.INITIALIZING, SubkernelStatus.FAILED, "initialization_failed")
                    return False
                    
            except Exception as e:
                logger.error(f"❌ Initialization error for {name}: {e}")
                manifest.status = SubkernelStatus.FAILED
                manifest.load_error = str(e)
                self._record_transition(name, SubkernelStatus.INITIALIZING, SubkernelStatus.FAILED, str(e), str(e))
                return False
    
    async def activate_provider(self, name: str) -> bool:
        """Provider'ni faollashtirish"""
        with self._lock:
            provider = self._providers.get(name)
            if not provider:
                logger.error(f"❌ Provider {name} not found")
                return False
            
            manifest = self._registry.get(name)
            if not manifest:
                return False
            
            # Check if already active
            if manifest.is_active:
                return True
            
            # Check dependencies
            for dep in manifest.spec.dependencies:
                dep_manifest = self._registry.get(dep)
                if not dep_manifest or not dep_manifest.is_active:
                    logger.warning(f"⚠️ Activating {name} but dependency {dep} not active")
            
            try:
                # Run health probes
                manifest.status = SubkernelStatus.READY
                await self._run_health_probes(name)
                
                # Activate
                await provider.on_activate()
                manifest.is_active = True
                
                self._registry.activate(name)
                self._record_transition(name, SubkernelStatus.READY, SubkernelStatus.ACTIVE, "activation")
                
                logger.info(f"🚀 Activated provider: {name}")
                return True
                
            except Exception as e:
                logger.error(f"❌ Activation error for {name}: {e}")
                self._record_transition(name, SubkernelStatus.READY, SubkernelStatus.FAILED, str(e), str(e))
                return False
    
    async def deactivate_provider(self, name: str, reason: str = "") -> bool:
        """Provider'ni o'chirish"""
        with self._lock:
            provider = self._providers.get(name)
            if not provider:
                return False
            
            try:
                await provider.on_deactivate()
            except Exception as e:
                logger.error(f"Error in on_deactivate for {name}: {e}")
            
            self._registry.deactivate(name, reason)
            self._record_transition(name, SubkernelStatus.ACTIVE, SubkernelStatus.DISABLED, reason or "deactivation")
            
            logger.info(f"🔴 Deactivated provider: {name}")
            return True
    
    async def degrade_provider(self, name: str, reason: str) -> bool:
        """Provider'ni degraded holatga o'tkazish"""
        with self._lock:
            provider = self._providers.get(name)
            if not provider:
                return False
            
            manifest = self._registry.get(name)
            if not manifest or not manifest.spec.can_degrade:
                return False
            
            try:
                await provider.on_degrade(reason)
            except Exception as e:
                logger.error(f"Error in on_degrade for {name}: {e}")
            
            self._registry.degrade(name, reason)
            
            from_state = manifest.status
            self._record_transition(name, from_state, SubkernelStatus.DEGRADED, reason)
            
            logger.warning(f"📉 Degraded provider: {name} - {reason}")
            return True
    
    async def recover_provider(self, name: str) -> bool:
        """Provider'ni degraded/quarantine'dan qaytarish"""
        with self._lock:
            provider = self._providers.get(name)
            if not provider:
                return False
            
            manifest = self._registry.get(name)
            if not manifest:
                return False
            
            # Run health check
            health = await provider.health_check()
            health_score = health.get("score", 0.5)
            
            if health_score >= 0.7:
                # Recover
                manifest.status = SubkernelStatus.ACTIVE
                manifest.health_score = health_score
                manifest.degradation_reason = None
                manifest.quarantine_reason = None
                
                try:
                    await provider.on_recover()
                except Exception as e:
                    logger.error(f"Error in on_recover for {name}: {e}")
                
                logger.info(f"✅ Recovered provider: {name}")
                return True
            else:
                logger.warning(f"⚠️ Cannot recover {name}: health score {health_score}")
                return False
    
    async def quarantine_provider(self, name: str, reason: str) -> bool:
        """Provider'ni karantinga o'tkazish"""
        with self._lock:
            provider = self._providers.get(name)
            if not provider:
                return False
            
            manifest = self._registry.get(name)
            if not manifest or not manifest.spec.can_quarantine:
                return False
            
            try:
                await provider.on_quarantine(reason)
            except Exception as e:
                logger.error(f"Error in on_quarantine for {name}: {e}")
            
            self._registry.quarantine(name, reason)
            from_state = manifest.status
            self._record_transition(name, from_state, SubkernelStatus.QUARANTINED, reason)
            
            logger.warning(f"🚫 Quarantined provider: {name}")
            return True
    
    async def unload_provider(self, name: str) -> bool:
        """Provider'ni yuklash (memory'dan chiqarish)"""
        with self._lock:
            provider = self._providers.get(name)
            if not provider:
                return False
            
            manifest = self._registry.get(name)
            if not manifest:
                return False
            
            # Deactivate first
            if manifest.is_active:
                await self.deactivate_provider(name, "unload")
            
            # Shutdown
            try:
                await provider.shutdown()
            except Exception as e:
                logger.error(f"Error shutting down {name}: {e}")
            
            manifest.is_loaded = False
            manifest.status = SubkernelStatus.UNLOADED
            
            self._record_transition(name, SubkernelStatus.READY, SubkernelStatus.UNLOADED, "unload")
            
            logger.info(f"📦 Unloaded provider: {name}")
            return True
    
    # ==================== BATCH OPERATIONS ====================
    
    async def initialize_all(self, order: Optional[List[str]] = None) -> Dict[str, bool]:
        """Barcha provider'larni initialize qilish"""
        if order is None:
            # Sort by startup priority
            order = sorted(
                self._providers.keys(),
                key=lambda n: self._registry.get(n).spec.startup_priority if self._registry.get(n) else 100
            )
        
        results = {}
        for name in order:
            results[name] = await self.initialize_provider(name)
        
        return results
    
    async def activate_all(self) -> Dict[str, bool]:
        """Barcha provider'larni faollashtirish"""
        # Sort by startup priority
        providers = sorted(
            self._providers.keys(),
            key=lambda n: self._registry.get(n).spec.startup_priority if self._registry.get(n) else 100
        )
        
        results = {}
        for name in providers:
            manifest = self._registry.get(name)
            if manifest and manifest.is_loaded and manifest.status != SubkernelStatus.FAILED:
                results[name] = await self.activate_provider(name)
        
        return results
    
    async def shutdown_all(self) -> Dict[str, bool]:
        """Barcha provider'larni to'xtatish (reverse order)"""
        # Sort by shutdown priority (reverse)
        providers = sorted(
            self._providers.keys(),
            key=lambda n: self._registry.get(n).spec.shutdown_priority if self._registry.get(n) else 100,
            reverse=True
        )
        
        results = {}
        for name in providers:
            results[name] = await self.deactivate_provider(name, "shutdown")
        
        return results
    
    # ==================== HEALTH ====================
    
    async def _run_health_probes(self, name: str) -> bool:
        """Health probe'larni ishga tushirish"""
        provider = self._providers.get(name)
        if not provider:
            return False
        
        manifest = self._registry.get(name)
        if not manifest:
            return False
        
        try:
            health = await provider.health_check()
            health_score = health.get("score", 1.0)
            
            self._registry.update_health(name, health_score)
            return health_score >= 0.5
            
        except Exception as e:
            logger.error(f"Health probe error for {name}: {e}")
            self._registry.update_health(name, 0.0, str(e))
            return False
    
    async def health_check_all(self) -> Dict[str, Dict]:
        """Barcha provider'larni health check"""
        results = {}
        for name in self._providers:
            provider = self._providers[name]
            try:
                health = await provider.health_check()
                health_score = health.get("score", 1.0)
                self._registry.update_health(name, health_score)
                results[name] = {"status": "ok", "score": health_score, **health}
            except Exception as e:
                results[name] = {"status": "error", "error": str(e)}
                self._registry.update_health(name, 0.0, str(e))
        
        return results
    
    # ==================== EVENTS ====================
    
    def on_lifecycle_event(self, event: LifecycleEvent, callback: Callable):
        """Lifecycle event'ga obuna bo'lish"""
        if event not in self._event_callbacks:
            self._event_callbacks[event] = []
        self._event_callbacks[event].append(callback)
    
    def _emit_lifecycle_event(self, event: LifecycleEvent, data: Dict):
        """Lifecycle event chiqarish"""
        for callback in self._event_callbacks.get(event, []):
            try:
                callback(data)
            except Exception as e:
                logger.error(f"Lifecycle event callback error: {e}")
    
    # ==================== HELPERS ====================
    
    def _record_transition(
        self, 
        name: str, 
        from_state: SubkernelStatus, 
        to_state: SubkernelStatus, 
        reason: str,
        error: Optional[str] = None
    ):
        """Lifecycle transition yozuvi"""
        if name not in self._lifecycle_history:
            self._lifecycle_history[name] = []
        
        self._lifecycle_history[name].append(LifecycleTransition(
            from_state=from_state,
            to_state=to_state,
            timestamp=time.time(),
            reason=reason,
            error=error,
        ))
        
        # Emit event
        event_map = {
            (SubkernelStatus.DISCOVERED, SubkernelStatus.VALIDATING): LifecycleEvent.VALIDATING,
            (SubkernelStatus.VALIDATING, SubkernelStatus.DISCOVERED): LifecycleEvent.READY,
            (SubkernelStatus.DISCOVERED, SubkernelStatus.INITIALIZING): LifecycleEvent.INITIALIZING,
            (SubkernelStatus.INITIALIZING, SubkernelStatus.READY): LifecycleEvent.INITIALIZED,
            (SubkernelStatus.READY, SubkernelStatus.ACTIVE): LifecycleEvent.ACTIVATED,
            (SubkernelStatus.READY, SubkernelStatus.DEGRADED): LifecycleEvent.DEGRADED,
            (SubkernelStatus.ACTIVE, SubkernelStatus.QUARANTINED): LifecycleEvent.QUARANTINED,
            (SubkernelStatus.ACTIVE, SubkernelStatus.DISABLED): LifecycleEvent.DISABLED,
            (SubkernelStatus.READY, SubkernelStatus.UNLOADED): LifecycleEvent.UNLOADED,
        }
        
        event = event_map.get((from_state, to_state))
        if event:
            self._emit_lifecycle_event(event, {
                "name": name,
                "from": from_state.value,
                "to": to_state.value,
                "reason": reason,
            })
    
    def get_lifecycle_history(self, name: str) -> List[LifecycleTransition]:
        """Lifecycle history olish"""
        return self._lifecycle_history.get(name, [])
    
    def get_status(self) -> Dict[str, Any]:
        """Umumiy status"""
        total = len(self._providers)
        active = len([n for n in self._providers if self._registry.get(n) and self._registry.get(n).is_active])
        ready = len([n for n in self._providers if self._registry.get(n) and self._registry.get(n).status == SubkernelStatus.READY])
        failed = len([n for n in self._providers if self._registry.get(n) and self._registry.get(n).status == SubkernelStatus.FAILED])
        
        return {
            "total": total,
            "active": active,
            "ready": ready,
            "failed": failed,
            "providers": list(self._providers.keys()),
        }


# Global lifecycle manager
_lifecycle_manager: Optional[LifecycleManager] = None


def get_lifecycle_manager() -> LifecycleManager:
    """Get or create global lifecycle manager"""
    global _lifecycle_manager
    if _lifecycle_manager is None:
        _lifecycle_manager = LifecycleManager()
    return _lifecycle_manager


def reset_lifecycle_manager():
    """Reset global lifecycle manager (for testing)"""
    global _lifecycle_manager
    _lifecycle_manager = None
