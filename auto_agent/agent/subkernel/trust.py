"""
OmniAgent X - TrustClass & ContainmentPolicy
============================================
Trust levels and containment policies for subkernels

Bu modul subkernellar uchun trust class va containment policy ni belgilaydi.
"""

import logging
from typing import Dict, List, Optional, Any, Set, FrozenSet
from dataclasses import dataclass, field
from enum import Enum
from threading import RLock

from agent.subkernel import (
    SubkernelCategory, 
    SubkernelStatus, 
    TrustLevel,
    SubkernelInterface,
    PluggableCapability,
)
from agent.subkernel.spec import SubkernelSpec, PluginManifest
from agent.subkernel.registry import CapabilityRegistry


logger = logging.getLogger(__name__)


class PolicyPosture(str, Enum):
    """
    Policy Posture - system qaysi rejimda ishlaydi
    
    Research mode - eksperimental ruxsatlar
    Production mode - qat'iy cheklovlar
    """
    RESEARCH = "research"           # Research/revelopment
    DEVELOPMENT = "development"    # Development testing
    STAGING = "staging"            # Pre-production
    PRODUCTION = "production"      # Production


class AccessLevel(str, Enum):
    """Subkernel access level"""
    FULL = "full"                 # To'liq ruxsat
    READ_ONLY = "read_only"       # Faqat o'qish
    RESTRICTED = "restricted"     # Cheklangan
    NONE = "none"                # Ruxsat yo'q


@dataclass
class TrustPolicy:
    """Trust policy for a trust class"""
    trust_level: TrustLevel
    name: str
    description: str
    
    # Access policies
    filesystem_access: AccessLevel = AccessLevel.FULL
    network_access: AccessLevel = AccessLevel.FULL
    execution_access: AccessLevel = AccessLevel.FULL
    memory_access: AccessLevel = AccessLevel.FULL
    
    # Safety policies
    can_execute_external: bool = True
    can_modify_files: bool = True
    can_access_secrets: bool = True
    can_spawn_subprocess: bool = True
    can_load_external_code: bool = True
    
    # Replay policies
    replay_safe: bool = False
    simulation_safe: bool = False
    
    # Quarantine policies
    auto_quarantine_failures: int = 5
    quarantine_on_error: bool = False
    
    # Resource limits
    max_memory_mb: Optional[int] = None
    max_cpu_percent: Optional[int] = None
    max_execution_time_seconds: Optional[int] = None


# Trust policies for each trust level
TRUST_POLICIES: Dict[TrustLevel, TrustPolicy] = {
    TrustLevel.CORE_TRUSTED: TrustPolicy(
        trust_level=TrustLevel.CORE_TRUSTED,
        name="Core Trusted",
        description="Kernel bilan birga keladi, to'liq ishonch",
        filesystem_access=AccessLevel.FULL,
        network_access=AccessLevel.FULL,
        execution_access=AccessLevel.FULL,
        memory_access=AccessLevel.FULL,
        can_execute_external=True,
        can_modify_files=True,
        can_access_secrets=True,
        can_spawn_subprocess=True,
        can_load_external_code=True,
        replay_safe=True,
        simulation_safe=True,
        auto_quarantine_failures=999,  # Never auto-quarantine
        max_memory_mb=None,
        max_cpu_percent=None,
    ),
    
    TrustLevel.INTERNAL_TRUSTED: TrustPolicy(
        trust_level=TrustLevel.INTERNAL_TRUSTED,
        name="Internal Trusted",
        description="Ichki, sinovdan o'tgan",
        filesystem_access=AccessLevel.FULL,
        network_access=AccessLevel.FULL,
        execution_access=AccessLevel.FULL,
        memory_access=AccessLevel.FULL,
        can_execute_external=True,
        can_modify_files=True,
        can_access_secrets=False,
        can_spawn_subprocess=True,
        can_load_external_code=False,
        replay_safe=True,
        simulation_safe=True,
        auto_quarantine_failures=10,
        max_memory_mb=1024,
        max_cpu_percent=50,
    ),
    
    TrustLevel.EXPERIMENTAL: TrustPolicy(
        trust_level=TrustLevel.EXPERIMENTAL,
        name="Experimental",
        description="Tajriba uchun, ko'p cheklovlar",
        filesystem_access=AccessLevel.RESTRICTED,
        network_access=AccessLevel.READ_ONLY,
        execution_access=AccessLevel.RESTRICTED,
        memory_access=AccessLevel.RESTRICTED,
        can_execute_external=False,
        can_modify_files=False,
        can_access_secrets=False,
        can_spawn_subprocess=False,
        can_load_external_code=False,
        replay_safe=False,
        simulation_safe=True,
        auto_quarantine_failures=2,
        quarantine_on_error=True,
        max_memory_mb=256,
        max_cpu_percent=20,
        max_execution_time_seconds=30,
    ),
    
    TrustLevel.READ_ONLY: TrustPolicy(
        trust_level=TrustLevel.READ_ONLY,
        name="Read Only",
        description="Faqat o'qish operatsiyalari",
        filesystem_access=AccessLevel.READ_ONLY,
        network_access=AccessLevel.READ_ONLY,
        execution_access=AccessLevel.NONE,
        memory_access=AccessLevel.READ_ONLY,
        can_execute_external=False,
        can_modify_files=False,
        can_access_secrets=False,
        can_spawn_subprocess=False,
        can_load_external_code=False,
        replay_safe=True,
        simulation_safe=True,
        auto_quarantine_failures=999,
    ),
    
    TrustLevel.DESTRUCTIVE_HIGH_RISK: TrustPolicy(
        trust_level=TrustLevel.DESTRUCTIVE_HIGH_RISK,
        name="Destructive/High Risk",
        description="Xavfli operatsiyalar uchun",
        filesystem_access=AccessLevel.FULL,
        network_access=AccessLevel.FULL,
        execution_access=AccessLevel.FULL,
        memory_access=AccessLevel.FULL,
        can_execute_external=True,
        can_modify_files=True,
        can_access_secrets=True,
        can_spawn_subprocess=True,
        can_load_external_code=True,
        replay_safe=False,
        simulation_safe=False,
        auto_quarantine_failures=1,
        quarantine_on_error=True,
        max_memory_mb=512,
        max_cpu_percent=30,
        max_execution_time_seconds=60,
    ),
}


@dataclass
class ContainmentPolicy:
    """Containment zone policy for subkernels"""
    
    # Isolation level
    isolation_level: str = "none"  # none, lane, process, vm
    
    # Resource limits
    memory_limit_mb: int = 1024
    cpu_percent_limit: int = 50
    max_file_size_mb: int = 100
    max_network_bandwidth_mbps: int = 100
    
    # Execution limits
    max_execution_time_seconds: int = 300
    max_concurrent_operations: int = 10
    
    # Network policies
    allowed_networks: FrozenSet[str] = frozenset({"*"})  # * = all
    blocked_networks: FrozenSet[str] = frozenset()
    dns_allowed: bool = True
    raw_sockets_allowed: bool = False
    
    # Filesystem policies
    allowed_paths: FrozenSet[str] = frozenset({"*"})
    blocked_paths: FrozenSet[str] = frozenset()
    temp_dir_isolated: bool = True
    
    # Monitoring
    enable_logging: bool = True
    enable_audit: bool = False
    enable_telemetry: bool = True
    
    # Failure handling
    failure_isolation: bool = True  # Failure doesn't propagate
    auto_kill_on_failure: bool = False
    preserve_state_on_failure: bool = True


# Default containment policies by trust level
CONTAINMENT_BY_TRUST: Dict[TrustLevel, ContainmentPolicy] = {
    TrustLevel.CORE_TRUSTED: ContainmentPolicy(
        isolation_level="none",
        memory_limit_mb=4096,
        cpu_percent_limit=100,
        max_execution_time_seconds=3600,
    ),
    
    TrustLevel.INTERNAL_TRUSTED: ContainmentPolicy(
        isolation_level="lane",
        memory_limit_mb=2048,
        cpu_percent_limit=80,
        max_execution_time_seconds=600,
    ),
    
    TrustLevel.EXPERIMENTAL: ContainmentPolicy(
        isolation_level="process",
        memory_limit_mb=512,
        cpu_percent_limit=30,
        max_execution_time_seconds=60,
        blocked_paths=frozenset({"/etc", "/root", "/home", "/var"}),
        enable_audit=True,
        auto_kill_on_failure=True,
    ),
    
    TrustLevel.READ_ONLY: ContainmentPolicy(
        isolation_level="lane",
        memory_limit_mb=256,
        cpu_percent_limit=10,
        max_execution_time_seconds=30,
        allowed_networks=frozenset(),  # No network
    ),
    
    TrustLevel.DESTRUCTIVE_HIGH_RISK: ContainmentPolicy(
        isolation_level="vm",  # Full VM isolation
        memory_limit_mb=1024,
        cpu_percent_limit=50,
        max_execution_time_seconds=120,
        enable_audit=True,
        auto_kill_on_failure=True,
        preserve_state_on_failure=False,
    ),
}


class TrustManager:
    """
    Trust Manager - Subkernellar uchun trust va policy boshqaruvi
    
    Bu manager:
    - Trust level'ni aniqlaydi
    - Policy'ni qo'llaydi
    - Containment zone'ni boshqaradi
    """
    
    def __init__(self, registry: CapabilityRegistry):
        self._registry = registry
        self._lock = RLock()
        
        # Current posture
        self._posture: PolicyPosture = PolicyPosture.RESEARCH
        
        # Per-subkernel trust overrides
        self._trust_overrides: Dict[str, TrustLevel] = {}
        
        # Per-subkernel containment policies
        self._containment_policies: Dict[str, ContainmentPolicy] = {}
        
        # Audit log
        self._audit_log: List[Dict] = []
    
    # ==================== TRUST LEVEL ====================
    
    def get_trust_level(self, name: str) -> TrustLevel:
        """Subkernel uchun trust level olish"""
        with self._lock:
            # Check override first
            if name in self._trust_overrides:
                return self._trust_overrides[name]
            
            # Get from manifest
            manifest = self._registry.get(name)
            if manifest:
                return manifest.spec.trust_class
            
            # Default
            return TrustLevel.INTERNAL_TRUSTED
    
    def set_trust_override(self, name: str, level: TrustLevel):
        """Trust level override qilish"""
        with self._lock:
            self._trust_overrides[name] = level
            logger.info(f"🔐 Trust override for {name}: {level.value}")
            
            # Update containment based on new trust
            self._containment_policies[name] = CONTAINMENT_BY_TRUST[level]
    
    def get_trust_policy(self, name: str) -> TrustPolicy:
        """Trust policy olish"""
        trust_level = self.get_trust_level(name)
        return TRUST_POLICIES[trust_level]
    
    # ==================== CONTAINMENT ====================
    
    def get_containment_policy(self, name: str) -> ContainmentPolicy:
        """Containment policy olish"""
        with self._lock:
            # Check custom policy first
            if name in self._containment_policies:
                return self._containment_policies[name]
            
            # Get from trust level
            trust_level = self.get_trust_level(name)
            return CONTAINMENT_BY_TRUST[trust_level]
    
    def set_containment_policy(self, name: str, policy: ContainmentPolicy):
        """Custom containment policy o'rnatish"""
        with self._lock:
            self._containment_policies[name] = policy
            logger.info(f"🛡️ Custom containment policy for {name}")
    
    # ==================== PERMISSION CHECKS ====================
    
    def can_execute(self, name: str) -> bool:
        """Subkernel execute qila oladimi?"""
        policy = self.get_trust_policy(name)
        return policy.execution_access in (AccessLevel.FULL, AccessLevel.RESTRICTED)
    
    def can_access_filesystem(self, name: str, path: str) -> bool:
        """Subkernel filesystemga kirisha oladimi?"""
        policy = self.get_trust_policy(name)
        
        if policy.filesystem_access == AccessLevel.NONE:
            return False
        
        if policy.filesystem_access == AccessLevel.READ_ONLY:
            # Only read operations allowed (check done at tool level)
            return True
        
        # Check path against blocked paths
        containment = self.get_containment_policy(name)
        
        # Check allowed paths
        allowed = False
        for allowed_path in containment.allowed_paths:
            if allowed_path == "*":
                allowed = True
            elif path.startswith(allowed_path):
                allowed = True
        
        if not allowed:
            return False
        
        # Check blocked paths
        for blocked_path in containment.blocked_paths:
            if path.startswith(blocked_path):
                return False
        
        return True
    
    def can_access_network(self, name: str, network: str = "*") -> bool:
        """Subkernel networkga kirisha oladimi?"""
        policy = self.get_trust_policy(name)
        
        if policy.network_access == AccessLevel.NONE:
            return False
        
        if policy.network_access == AccessLevel.READ_ONLY:
            return False  # No network writes
        
        # Check containment policy
        containment = self.get_containment_policy(name)
        
        # Check allowed networks
        allowed = False
        for allowed_net in containment.allowed_networks:
            if allowed_net == "*":
                allowed = True
            elif network == allowed_net:
                allowed = True
        
        if not allowed:
            return False
        
        # Check blocked networks
        for blocked_net in containment.blocked_networks:
            if network == blocked_net:
                return False
        
        return True
    
    def can_access_secrets(self, name: str) -> bool:
        """Subkernel secretsga kirisha oladimi?"""
        policy = self.get_trust_policy(name)
        return policy.can_access_secrets
    
    def can_modify_files(self, name: str) -> bool:
        """Subkernel filelarni o'zgartira oladimi?"""
        policy = self.get_trust_policy(name)
        return policy.can_modify_files
    
    # ==================== POSTURE ====================
    
    def get_posture(self) -> PolicyPosture:
        """Hozirgi posture olish"""
        return self._posture
    
    def set_posture(self, posture: PolicyPosture):
        """Posture o'zgartirish"""
        with self._lock:
            old_posture = self._posture
            self._posture = posture
            logger.info(f"🔄 Posture changed: {old_posture.value} -> {posture.value}")
            
            # Apply posture-specific restrictions
            self._apply_posture_restrictions(posture)
    
    def _apply_posture_restrictions(self, posture: PolicyPosture):
        """Posturega qarab cheklovlar qo'llash"""
        if posture == PolicyPosture.PRODUCTION:
            # Stricter policies for production
            for name in self._registry.get_all():
                trust = self.get_trust_level(name)
                if trust == TrustLevel.EXPERIMENTAL:
                    self.set_trust_override(name, TrustLevel.READ_ONLY)
    
    # ==================== AUDIT ====================
    
    def audit(
        self, 
        action: str, 
        subkernel: str, 
        resource: str, 
        allowed: bool,
        details: Optional[Dict] = None
    ):
        """Audit log yozish"""
        import time
        entry = {
            "timestamp": time.time(),
            "action": action,
            "subkernel": subkernel,
            "resource": resource,
            "allowed": allowed,
            "details": details or {},
        }
        
        with self._lock:
            self._audit_log.append(entry)
            
            # Keep only last 1000 entries
            if len(self._audit_log) > 1000:
                self._audit_log = self._audit_log[-1000:]
    
    def get_audit_log(self, subkernel: Optional[str] = None) -> List[Dict]:
        """Audit log olish"""
        with self._lock:
            if subkernel:
                return [e for e in self._audit_log if e["subkernel"] == subkernel]
            return list(self._audit_log)
    
    # ==================== QUARANTINE ====================
    
    def should_quarantine(self, name: str) -> bool:
        """Subkernel quarantine qilinishi kerakmi?"""
        manifest = self._registry.get(name)
        if not manifest:
            return False
        
        policy = self.get_trust_policy(name)
        return (
            policy.quarantine_on_error and 
            manifest.consecutive_failures >= policy.auto_quarantine_failures
        )
    
    def get_quarantine_reason(self, name: str) -> str:
        """Quarantine sababini olish"""
        policy = self.get_trust_policy(name)
        manifest = self._registry.get(name)
        
        if manifest and manifest.last_error:
            return f"Error: {manifest.last_error}"
        
        return f"Trust policy: {policy.name}"
    
    # ==================== REPLAY/SIMULATION ====================
    
    def is_replay_safe(self, name: str) -> bool:
        """Subkernel replay'da ishlash uchun xavfsizmi?"""
        policy = self.get_trust_policy(name)
        return policy.replay_safe
    
    def is_simulation_safe(self, name: str) -> bool:
        """Subkernel simulation'da ishlash uchun xavfsizmi?"""
        policy = self.get_trust_policy(name)
        return policy.simulation_safe
    
    # ==================== SUMMARY ====================
    
    def get_trust_summary(self) -> Dict[str, Any]:
        """Trust holati xulosasi"""
        with self._lock:
            result = {
                "posture": self._posture.value,
                "trust_levels": {},
                "containment_zones": {},
            }
            
            for manifest in self._registry.get_all():
                name = manifest.spec.name
                trust = self.get_trust_level(name)
                containment = self.get_containment_policy(name)
                
                result["trust_levels"][name] = {
                    "level": trust.value,
                    "policy": TRUST_POLICIES[trust].name,
                }
                
                result["containment_zones"][name] = {
                    "isolation": containment.isolation_level,
                    "memory_limit_mb": containment.memory_limit_mb,
                    "cpu_limit": containment.cpu_percent_limit,
                }
            
            return result


# Global trust manager
_trust_manager: Optional[TrustManager] = None


def get_trust_manager(registry: Optional[CapabilityRegistry] = None) -> TrustManager:
    """Get or create global trust manager"""
    global _trust_manager
    if _trust_manager is None:
        from agent.subkernel.registry import get_capability_registry
        reg = registry or get_capability_registry()
        _trust_manager = TrustManager(reg)
    return _trust_manager


def reset_trust_manager():
    """Reset global trust manager"""
    global _trust_manager
    _trust_manager = None
