"""
OmniAgent X - Protected Zone Registry
=================================
Bu fayl qaysi fayl va modullar oddiy clone patch uchun yopiq ekanligini belgilaydi.

Protected zones:
- constitution kernel
- promotion policy core
- secret broker core
- audit subsystem core
"""
import os
from typing import Dict, List, Set, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import fnmatch


class ZoneType(Enum):
    """Protected zone turlari"""
    CONSTITUTION = "constitution"      # Constitution Kernel
    PROMOTION = "promotion"           # Promotion policy
    SECURITY = "security"             # Security core
    AUDIT = "audit"                   # Audit subsystem
    SECRET_BROKER = "secret_broker"   # Secret management
    CORE_KERNEL = "core_kernel"       # Core kernel


@dataclass
class ProtectedZone:
    """Protected zone"""
    zone_id: str
    zone_type: ZoneType
    description: str
    paths: List[str]  # Path patterns
    allow_read: bool = True       # O'qish ruxsati
    allow_write: bool = False     # Yozish ruxsati
    allow_execute: bool = False   # Ishga tushirish
    require_special_approval: bool = False  # Maxsus approval
    bypass_roles: Set[str] = field(default_factory=set)  # Kimlar o'tishi mumkin


class ProtectedZoneRegistry:
    """
    Protected zone registry - qaysi fayllar patch uchun yopiq
    """
    
    def __init__(self):
        self.zones: Dict[str, ProtectedZone] = {}
        self._init_default_zones()
    
    def _init_default_zones(self):
        """Default protected zones"""
        
        # 1. Constitution Kernel zone
        self.register_zone(ProtectedZone(
            zone_id="constitution_kernel",
            zone_type=ZoneType.CONSTITUTION,
            description="Constitution Kernel - 12 ta asosiy qonun",
            paths=[
                "**/constitution/*.py",
                "**/constitution_rules.py",
                "**/rule_classes.py",
                "**/policy_guard.py",
            ],
            allow_read=True,
            allow_write=False,
            require_special_approval=True,
            bypass_roles={"constitutional_audit"}
        ))
        
        # 2. Promotion Policy zone
        self.register_zone(ProtectedZone(
            zone_id="promotion_policy",
            zone_type=ZoneType.PROMOTION,
            description="Promotion policy va governance",
            paths=[
                "**/promotion/*.py",
                "**/promotion_policy.py",
                "**/governance.py",
            ],
            allow_read=True,
            allow_write=False,
            require_special_approval=True,
            bypass_roles={"constitutional_audit"}
        ))
        
        # 3. Security Core zone
        self.register_zone(ProtectedZone(
            zone_id="security_core",
            zone_type=ZoneType.SECURITY,
            description="Xavfsizlik va secret management",
            paths=[
                "**/secret_guard.py",
                "**/security/*.py",
                "**/auth*.py",
            ],
            allow_read=True,
            allow_write=False,
            require_special_approval=True,
            bypass_roles=set()
        ))
        
        # 4. Audit Subsystem zone
        self.register_zone(ProtectedZone(
            zone_id="audit_subsystem",
            zone_type=ZoneType.AUDIT,
            description="Audit va logging subsystem",
            paths=[
                "**/audit*.py",
                "**/logging/*.py",
                "**/telemetry*.py",
            ],
            allow_read=True,
            allow_write=False,
            require_special_approval=False,  # Audit o'zini yozishi mumkin
            bypass_roles={"audit_system"}
        ))
        
        # 5. Secret Broker zone
        self.register_zone(ProtectedZone(
            zone_id="secret_broker",
            zone_type=ZoneType.SECRET_BROKER,
            description="Secret broker va credential management",
            paths=[
                "**/secret_broker.py",
                "**/credential*.py",
                "**/token*.py",
            ],
            allow_read=False,
            allow_write=False,
            require_special_approval=True,
            bypass_roles=set()
        ))
        
        # 6. Core Kernel zone (eng muhim)
        self.register_zone(ProtectedZone(
            zone_id="core_kernel",
            zone_type=ZoneType.CORE_KERNEL,
            description="Markaziy kernel - asosiy logika",
            paths=[
                "**/kernel.py",
                "**/brain.py",
                "**/core/*.py",
            ],
            allow_read=True,
            allow_write=False,
            require_special_approval=True,
            bypass_roles=set()
        ))
    
    def register_zone(self, zone: ProtectedZone):
        """Zone ro'yxatga olish"""
        self.zones[zone.zone_id] = zone
    
    def unregister_zone(self, zone_id: str):
        """Zone olib tashlash"""
        if zone_id in self.zones:
            del self.zones[zone_id]
    
    def is_path_protected(self, path: str) -> tuple[bool, Optional[ProtectedZone]]:
        """
        Path protected zone'mi?
        Returns: (is_protected, zone)
        """
        for zone in self.zones.values():
            for pattern in zone.paths:
                if fnmatch.fnmatch(path, pattern):
                    return True, zone
                # Subdirectory check
                if "**/" in pattern:
                    base_pattern = pattern.replace("**/", "")
                    if path.endswith(base_pattern):
                        return True, zone
        
        return False, None
    
    def can_read(self, path: str, role: str = "") -> bool:
        """Path'ga o'qish mumkinmi?"""
        is_protected, zone = self.is_path_protected(path)
        
        if not is_protected:
            return True  # Protected bo'lmagan - ruxsat
        
        if role in zone.bypass_roles:
            return True
        
        return zone.allow_read
    
    def can_write(self, path: str, role: str = "", approval: str = "") -> bool:
        """Path'ga yozish mumkinmi?"""
        is_protected, zone = self.is_path_protected(path)
        
        if not is_protected:
            return True  # Protected bo'lmagan - ruxsat
        
        if role in zone.bypass_roles:
            return True
        
        if not zone.allow_write:
            return False
        
        if zone.require_special_approval:
            return approval == "approved"
        
        return True
    
    def can_execute(self, path: str, role: str = "") -> bool:
        """Path'ni ishga tushirish mumkinmi?"""
        is_protected, zone = self.is_path_protected(path)
        
        if not is_protected:
            return True
        
        if role in zone.bypass_roles:
            return True
        
        return zone.allow_execute
    
    def get_zone_for_path(self, path: str) -> Optional[ProtectedZone]:
        """Path uchun zone olish"""
        _, zone = self.is_path_protected(path)
        return zone
    
    def get_all_zones(self) -> Dict[str, ProtectedZone]:
        """Barcha zonalarni olish"""
        return self.zones.copy()
    
    def get_zones_by_type(self, zone_type: ZoneType) -> List[ProtectedZone]:
        """Tur bo'yicha zonalar"""
        return [z for z in self.zones.values() if z.zone_type == zone_type]
    
    def check_access(
        self,
        path: str,
        operation: str,  # "read", "write", "execute"
        role: str = "",
        approval: str = ""
    ) -> tuple[bool, str]:
        """
        Access tekshirish
        Returns: (is_allowed, reason)
        """
        is_protected, zone = self.is_path_protected(path)
        
        if not is_protected:
            return True, "Not protected"
        
        # Role bypass
        if role and role in zone.bypass_roles:
            return True, f"Bypass by role: {role}"
        
        # Operation check
        if operation == "read":
            if zone.allow_read:
                return True, "Read allowed"
            return False, f"Read denied: {zone.description}"
        
        elif operation == "write":
            if not zone.allow_write:
                return False, f"Write denied: {zone.description}"
            
            if zone.require_special_approval:
                if approval == "approved":
                    return True, "Write with approval"
                return False, f"Special approval required for: {zone.description}"
            
            return True, "Write allowed"
        
        elif operation == "execute":
            if zone.allow_execute:
                return True, "Execute allowed"
            return False, f"Execute denied: {zone.description}"
        
        return False, "Unknown operation"
    
    def get_protected_paths(self) -> List[str]:
        """Barcha protected path patterns"""
        paths = []
        for zone in self.zones.values():
            paths.extend(zone.paths)
        return paths
    
    def validate_patch_target(
        self,
        target_path: str,
        patch_type: str = "code",  # "code", "config", "constitution"
        role: str = "",
        approval: str = ""
    ) -> tuple[bool, List[str]]:
        """
        Patch target tekshirish
        Returns: (is_valid, list_of_violations)
        """
        violations = []
        
        # 1. Protected zone check
        is_protected, zone = self.is_path_protected(target_path)
        
        if is_protected:
            if patch_type == "constitution":
                # Constitution patch - faqat maxsus workflow bilan
                can_access, reason = self.check_access(target_path, "write", role, approval)
                if not can_access:
                    violations.append(f"Constitution patch denied: {reason}")
            else:
                # Oddiy patch protected zone'ga kirish mumkin emas
                can_access, reason = self.check_access(target_path, "write", role, approval)
                if not can_access:
                    violations.append(f"Protected zone violation: {reason}")
        
        # 2. Constitution o'zgartirish - faqat Qonun 12 workflow bilan
        if "constitution" in target_path.lower() and patch_type != "constitution":
            violations.append("Constitution files can only be modified via constitutional change protocol")
        
        return len(violations) == 0, violations


# Global registry
_registry: Optional[ProtectedZoneRegistry] = None


def get_protected_zone_registry() -> ProtectedZoneRegistry:
    """Global registry olish"""
    global _registry
    if _registry is None:
        _registry = ProtectedZoneRegistry()
    return _registry


def create_protected_zone_registry() -> ProtectedZoneRegistry:
    """Registry yaratish"""
    return ProtectedZoneRegistry()


def is_path_protected(path: str) -> bool:
    """Path protectedmi (tez funksiya)"""
    registry = get_protected_zone_registry()
    is_protected, _ = registry.is_path_protected(path)
    return is_protected


def validate_patch_access(
    target_path: str,
    patch_type: str = "code",
    role: str = "",
    approval: str = ""
) -> tuple[bool, List[str]]:
    """Patch access tekshirish (tez funksiya)"""
    registry = get_protected_zone_registry()
    return registry.validate_patch_target(target_path, patch_type, role, approval)
