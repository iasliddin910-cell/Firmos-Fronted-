"""
OmniAgent X - Constitution Profiles
================================
Bu fayl Lab/Operator/Public profilelarini belgilaydi.

Lab Constitution:
- Ichki kuchli rejim
- Kengroq experimentation
- Ko'proq clone freedom
- Originalga tegish yo'q
- Evidence majburiy
- Rollback majburiy

Operator Constitution:
- Real boshqarish
- Approval gate qattiqroq
- Canary/main policy qattiqroq

Public Constitution:
- Ommaga chiqish
- Strictest external actions
- Tenant isolation
"""
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum
from .constitution_rules import ConstitutionProfile as Profile
from .rule_classes import (
    RuleEnforcementLevel,
    ProfileRuleSettings,
    LAB_PROFILE_SETTINGS,
    OPERATOR_PROFILE_SETTINGS,
    PUBLIC_PROFILE_SETTINGS,
    PROFILE_SETTINGS_MAP
)


class ProfileCapability(Enum):
    """Profil imkoniyatlari"""
    # Code execution
    EXECUTE_PYTHON = "execute_python"
    EXECUTE_SHELL = "execute_shell"
    EXECUTE_DOCKER = "execute_docker"
    
    # Network
    NETWORK_HTTP = "network_http"
    NETWORK_WEBSOCKET = "network_websocket"
    NETWORK_EXTERNAL = "network_external"
    
    # File system
    FS_READ = "fs_read"
    FS_WRITE = "fs_write"
    FS_DELETE = "fs_delete"
    
    # Browser
    BROWSER_AUTOMATION = "browser_automation"
    BROWSER_DOWNLOAD = "browser_download"
    
    # External services
    TELEGRAM_ACCESS = "telegram_access"
    EMAIL_ACCESS = "email_access"
    API_ACCESS = "api_access"
    
    # Self-modification
    SELF_CLONE = "self_clone"
    SELF_PROMOTE = "self_promote"
    SELF_CREATE_TOOL = "self_create_tool"


@dataclass
class ProfileConfig:
    """Profil konfiguratsiyasi"""
    profile: Profile
    name: str
    description: str
    
    # Allowed capabilities
    allowed_capabilities: Set[ProfileCapability] = field(default_factory=set)
    
    # Constraints
    max_concurrent_tasks: int = 5
    max_clone_depth: int = 3
    max_file_size_mb: int = 100
    timeout_seconds: int = 300
    
    # External access
    allow_external_api: bool = False
    allow_telegram: bool = False
    allow_email: bool = False
    
    # Self-modification
    allow_self_clone: bool = True
    allow_self_promote: bool = False  # Human approval required
    allow_tool_creation: bool = True
    
    # Approval requirements
    require_approval_for_main: bool = True
    require_approval_for_branch: bool = False
    require_approval_for_external: bool = True
    
    # Logging
    log_level: str = "INFO"
    audit_all_actions: bool = True


# ============================================
# PROFILE CONFIGS
# ============================================

LAB_PROFILE_CONFIG = ProfileConfig(
    profile=Profile.LAB,
    name="Lab Constitution",
    description="Ichki kuchli rejim - to'liq tadqiqot va tajriba uchun",
    
    allowed_capabilities={
        ProfileCapability.EXECUTE_PYTHON,
        ProfileCapability.EXECUTE_SHELL,
        ProfileCapability.EXECUTE_DOCKER,
        ProfileCapability.NETWORK_HTTP,
        ProfileCapability.NETWORK_WEBSOCKET,
        ProfileCapability.NETWORK_EXTERNAL,
        ProfileCapability.FS_READ,
        ProfileCapability.FS_WRITE,
        ProfileCapability.FS_DELETE,
        ProfileCapability.BROWSER_AUTOMATION,
        ProfileCapability.BROWSER_DOWNLOAD,
        ProfileCapability.TELEGRAM_ACCESS,
        ProfileCapability.API_ACCESS,
        ProfileCapability.SELF_CLONE,
        ProfileCapability.SELF_CREATE_TOOL,
    },
    
    max_concurrent_tasks=10,
    max_clone_depth=5,
    max_file_size_mb=500,
    timeout_seconds=600,
    
    allow_external_api=True,
    allow_telegram=True,
    allow_email=False,
    
    allow_self_clone=True,
    allow_self_promote=False,  # Human approval
    allow_tool_creation=True,
    
    require_approval_for_main=True,
    require_approval_for_branch=False,
    require_approval_for_external=True,
    
    log_level="DEBUG",
    audit_all_actions=True
)


OPERATOR_PROFILE_CONFIG = ProfileConfig(
    profile=Profile.OPERATOR,
    name="Operator Constitution",
    description="Real boshqarish - productionga yaqin",
    
    allowed_capabilities={
        ProfileCapability.EXECUTE_PYTHON,
        ProfileCapability.EXECUTE_SHELL,
        ProfileCapability.NETWORK_HTTP,
        ProfileCapability.FS_READ,
        ProfileCapability.FS_WRITE,
        ProfileCapability.BROWSER_AUTOMATION,
    },
    
    max_concurrent_tasks=5,
    max_clone_depth=3,
    max_file_size_mb=100,
    timeout_seconds=300,
    
    allow_external_api=True,
    allow_telegram=True,
    allow_email=False,
    
    allow_self_clone=True,
    allow_self_promote=False,
    allow_tool_creation=False,  # Faqat approve bilan
    
    require_approval_for_main=True,
    require_approval_for_branch=True,
    require_approval_for_external=True,
    
    log_level="INFO",
    audit_all_actions=True
)


PUBLIC_PROFILE_CONFIG = ProfileConfig(
    profile=Profile.PUBLIC,
    name="Public Constitution",
    description="Ommaga chiqish - xavfsiz va cheklangan",
    
    allowed_capabilities={
        ProfileCapability.EXECUTE_PYTHON,  # Sandbox
        ProfileCapability.NETWORK_HTTP,
        ProfileCapability.FS_READ,
    },
    
    max_concurrent_tasks=2,
    max_clone_depth=1,
    max_file_size_mb=10,
    timeout_seconds=60,
    
    allow_external_api=False,
    allow_telegram=False,
    allow_email=False,
    
    allow_self_clone=False,
    allow_self_promote=False,
    allow_tool_creation=False,
    
    require_approval_for_main=True,
    require_approval_for_branch=True,
    require_approval_for_external=True,
    
    log_level="WARNING",
    audit_all_actions=True
)


# Profile config map
PROFILE_CONFIGS: Dict[Profile, ProfileConfig] = {
    Profile.LAB: LAB_PROFILE_CONFIG,
    Profile.OPERATOR: OPERATOR_PROFILE_CONFIG,
    Profile.PUBLIC: PUBLIC_PROFILE_CONFIG,
}


# ============================================
# FUNKTSIYALAR
# ============================================

def get_profile_config(profile: Profile) -> ProfileConfig:
    """Profil konfiguratsiyasini olish"""
    return PROFILE_CONFIGS.get(profile, LAB_PROFILE_CONFIG)


def get_current_profile() -> Profile:
    """Joriy profili olish (environment variable dan)"""
    import os
    profile_name = os.getenv("CONSTITUTION_PROFILE", "lab").upper()
    
    try:
        return Profile[profile_name]
    except KeyError:
        return Profile.LAB


def set_current_profile(profile: Profile):
    """Joriy profilni o'rnatish"""
    import os
    os.environ["CONSTITUTION_PROFILE"] = profile.value


def is_capability_allowed(
    capability: ProfileCapability,
    profile: Optional[Profile] = None
) -> bool:
    """Profil uchun capability ruxsatmi?"""
    if profile is None:
        profile = get_current_profile()
    
    config = get_profile_config(profile)
    return capability in config.allowed_capabilities


def get_allowed_capabilities(profile: Optional[Profile] = None) -> Set[ProfileCapability]:
    """Profil uchun ruxsatli capabilitylar"""
    if profile is None:
        profile = get_current_profile()
    
    config = get_profile_config(profile)
    return config.allowed_capabilities.copy()


def requires_approval(
    target: str,  # "main", "branch", "external"
    profile: Optional[Profile] = None
) -> bool:
    """Target uchun approval talabmi?"""
    if profile is None:
        profile = get_current_profile()
    
    config = get_profile_config(profile)
    
    if target == "main":
        return config.require_approval_for_main
    elif target == "branch":
        return config.require_approval_for_branch
    elif target == "external":
        return config.require_approval_for_external
    
    return True


def get_profile_settings(profile: Profile) -> ProfileRuleSettings:
    """Profil uchun rule settings"""
    return PROFILE_SETTINGS_MAP.get(profile)


def get_all_profiles() -> List[Profile]:
    """Barcha profilelar"""
    return list(Profile)


def get_profile_info(profile: Profile) -> Dict[str, Any]:
    """Profil haqida to'liq ma'lumot"""
    config = get_profile_config(profile)
    settings = get_profile_settings(profile)
    
    return {
        "profile": profile.value,
        "name": config.name,
        "description": config.description,
        "capabilities": [c.value for c in config.allowed_capabilities],
        "constraints": {
            "max_concurrent_tasks": config.max_concurrent_tasks,
            "max_clone_depth": config.max_clone_depth,
            "max_file_size_mb": config.max_file_size_mb,
            "timeout_seconds": config.timeout_seconds,
        },
        "approval_requirements": {
            "main": config.require_approval_for_main,
            "branch": config.require_approval_for_branch,
            "external": config.require_approval_for_external,
        },
        "budget_limits": settings.budget_limits if settings else {},
    }


def validate_operation(
    operation: str,
    target: str,
    profile: Optional[Profile] = None
) -> tuple[bool, str]:
    """
    Operatsiyani tekshirish
    Returns: (is_valid, reason)
    """
    if profile is None:
        profile = get_current_profile()
    
    config = get_profile_config(profile)
    
    # Check capability
    capability_map = {
        "execute_python": ProfileCapability.EXECUTE_PYTHON,
        "execute_shell": ProfileCapability.EXECUTE_SHELL,
        "execute_docker": ProfileCapability.EXECUTE_DOCKER,
        "network_http": ProfileCapability.NETWORK_HTTP,
        "network_external": ProfileCapability.NETWORK_EXTERNAL,
        "fs_write": ProfileCapability.FS_WRITE,
        "fs_delete": ProfileCapability.FS_DELETE,
        "browser": ProfileCapability.BROWSER_AUTOMATION,
        "telegram": ProfileCapability.TELEGRAM_ACCESS,
        "clone": ProfileCapability.SELF_CLONE,
        "promote": ProfileCapability.SELF_PROMOTE,
        "create_tool": ProfileCapability.SELF_CREATE_TOOL,
    }
    
    capability = capability_map.get(operation)
    if capability and capability not in config.allowed_capabilities:
        return False, f"Capability not allowed in {profile.value} profile"
    
    # Check approval requirement
    target_map = {
        "main": "main",
        "branch": "branch",
        "external": "external",
    }
    
    approval_target = target_map.get(target, target)
    if requires_approval(approval_target, profile):
        return True, f"Approval required for {approval_target}"
    
    return True, "Operation allowed"


# ============================================
# PROFILE SWITCHING
# ============================================

class ProfileManager:
    """Profil boshqaruvchisi"""
    
    def __init__(self):
        self.current_profile = get_current_profile()
        self.profile_history: List[Profile] = []
    
    def switch_profile(self, new_profile: Profile) -> bool:
        """Profilni almashtirish"""
        # Validate switch
        if new_profile == self.current_profile:
            return True
        
        # Log switch
        self.profile_history.append(self.current_profile)
        
        # Switch
        set_current_profile(new_profile)
        self.current_profile = new_profile
        
        return True
    
    def switch_to_lab(self):
        """Lab profilga o'tish"""
        return self.switch_profile(Profile.LAB)
    
    def switch_to_operator(self):
        """Operator profilga o'tish"""
        return self.switch_profile(Profile.OPERATOR)
    
    def switch_to_public(self):
        """Public profilga o'tish"""
        return self.switch_profile(Profile.PUBLIC)
    
    def revert_profile(self) -> bool:
        """Oldingi profilga qaytish"""
        if self.profile_history:
            old_profile = self.profile_history.pop()
            return self.switch_profile(old_profile)
        return False
    
    def get_history(self) -> List[Profile]:
        """Profil o'zgarishlar tarixi"""
        return self.profile_history.copy()


# Global profile manager
_profile_manager: Optional[ProfileManager] = None


def get_profile_manager() -> ProfileManager:
    """Global profile manager olish"""
    global _profile_manager
    if _profile_manager is None:
        _profile_manager = ProfileManager()
    return _profile_manager
