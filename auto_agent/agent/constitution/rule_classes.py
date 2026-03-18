"""
OmniAgent X - Constitution Rule Classes
=====================================
Qonunlar 3 sinfga ajratilgan:
- Class A: Absolute laws (hech qachon buzilmaydi)
- Class B: Mode-dependent laws (profilga qarab o'zgaradi)
- Class C: Strategic laws (roadmap va identity ga tegishli)
"""
from enum import Enum
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass, field
from .constitution_rules import (
    CONSTITUTION_RULES, 
    RuleClass, 
    ConstitutionProfile,
    RuleMetadata,
    get_absolute_rules,
    get_mode_dependent_rules,
    get_strategic_rules,
    get_rules_by_profile,
    ViolationSeverity
)


class RuleEnforcementLevel(Enum):
    """Qonunni qanchalik qattiq bajarish"""
    STRICT = "strict"      # Buzilishi mumkin emas
    FLEXIBLE = "flexible"  # Ayrim holatlarda moslashish mumkin
    ADVISORY = "advisory" # Faqat maslahat


@dataclass
class RuleClassConfig:
    """Har bir qonun sinfining konfiguratsiyasi"""
    rule_class: RuleClass
    enforcement_level: RuleEnforcementLevel
    bypass_allowed: bool = False
    override_requires: str = ""  # Kim override qilishi mumkin


@dataclass
class ProfileRuleSettings:
    """Profil bo'yicha qonun sozlamalari"""
    profile: ConstitutionProfile
    enabled_rules: Set[str] = field(default_factory=set)
    enforcement_levels: Dict[str, RuleEnforcementLevel] = field(default_factory=dict)
    custom_severity: Dict[str, ViolationSeverity] = field(default_factory=dict)
    budget_limits: Dict[str, int] = field(default_factory=dict)  # Qonun 9 uchun


# ============================================
# RULE CLASS A - ABSOLUTE LAWS
# ============================================
# Hech qachon buzilmaydi

CLASS_A_CONFIG = RuleClassConfig(
    rule_class=RuleClass.A_ABSOLUTE,
    enforcement_level=RuleEnforcementLevel.STRICT,
    bypass_allowed=False,
    override_requires="N/A - Cannot be overridden"
)

ABSOLUTE_RULES = get_absolute_rules()

ABSOLUTE_RULE_IDS = {rule.rule_id for rule in ABSOLUTE_RULES}

# Class A qonunlari ro'yxati
CLASS_A_RULES = {
    "CK_001": "Original Core muqaddas",
    "CK_002": "Har o'zgarish iz qoldiradi",
    "CK_003": "Isbotsiz improvement yo'q",
    "CK_004": "Har promotion qaytariladigan",
    "CK_005": "Human sovereignty",
    "CK_006": "Permission scoped",
    "CK_007": "Baholash 3 qatlamli",
    "CK_008": "Salbiy natija yashirilmaydi",
    "CK_010": "Har tajriba xotiraga",
    "CK_012": "Constitution himoyalangan",
}


# ============================================
# RULE CLASS B - MODE-DEPENDENT LAWS
# ============================================
# Lab/Operator/Public ga qarab o'zgaradi

CLASS_B_CONFIG = RuleClassConfig(
    rule_class=RuleClass.B_MODE_DEPENDENT,
    enforcement_level=RuleEnforcementLevel.FLEXIBLE,
    bypass_allowed=True,
    override_requires="constitutional_audit + human_approval"
)

MODE_DEPENDENT_RULES = get_mode_dependent_rules()

MODE_DEPENDENT_RULE_IDS = {rule.rule_id for rule in MODE_DEPENDENT_RULES}

# Class B qonunlari
CLASS_B_RULES = {
    "CK_009": "Evolution budget bilan",
    "CK_011": "Identitet drift nazorat",
}


# ============================================
# RULE CLASS C - STRATEGIC LAWS
# ============================================
# Roadmap va identity ga tegishli

CLASS_C_CONFIG = RuleClassConfig(
    rule_class=RuleClass.C_STRATEGIC,
    enforcement_level=RuleEnforcementLevel.ADVISORY,
    bypass_allowed=True,
    override_requires="human_strategic_decision"
)

STRATEGIC_RULES = get_strategic_rules()

STRATEGIC_RULE_IDS = {rule.rule_id for rule in STRATEGIC_RULES}


# ============================================
# PROFILE-BASED SETTINGS
# ============================================

# Lab Constitution - Ichki kuchli rejim
LAB_PROFILE_SETTINGS = ProfileRuleSettings(
    profile=ConstitutionProfile.LAB,
    enabled_rules={
        "CK_001", "CK_002", "CK_003", "CK_004", "CK_005", "CK_006",
        "CK_007", "CK_008", "CK_009", "CK_010", "CK_011", "CK_012"
    },
    enforcement_levels={
        "CK_009": RuleEnforcementLevel.FLEXIBLE,  # Budget kengroq
        "CK_011": RuleEnforcementLevel.FLEXIBLE,  # Drift kengroq
    },
    budget_limits={
        "clone_budget": 10,       # Ko'proq clone ruxsati
        "change_budget": 50,      # Ko'proq o'zgarish
        "eval_budget": 20,        # Ko'proq eval
        "risk_budget": 5,         # Ko'proq risk
    }
)

# Operator Constitution - Real boshqarish
OPERATOR_PROFILE_SETTINGS = ProfileRuleSettings(
    profile=ConstitutionProfile.OPERATOR,
    enabled_rules={
        "CK_001", "CK_002", "CK_003", "CK_004", "CK_005", "CK_006",
        "CK_007", "CK_008", "CK_009", "CK_010", "CK_011", "CK_012"
    },
    enforcement_levels={
        "CK_009": RuleEnforcementLevel.STRICT,  # Budget qattiq
        "CK_011": RuleEnforcementLevel.STRICT,   # Drift qattiq
    },
    budget_limits={
        "clone_budget": 5,
        "change_budget": 20,
        "eval_budget": 10,
        "risk_budget": 2,
    }
)

# Public Constitution - Ommaga chiqish
PUBLIC_PROFILE_SETTINGS = ProfileRuleSettings(
    profile=ConstitutionProfile.PUBLIC,
    enabled_rules={
        "CK_001", "CK_002", "CK_003", "CK_004", "CK_005", "CK_006",
        "CK_007", "CK_008", "CK_009", "CK_010", "CK_011", "CK_012"
    },
    enforcement_levels={
        "CK_009": RuleEnforcementLevel.STRICT,  # Budget juda qattiq
        "CK_011": RuleEnforcementLevel.STRICT,  # Drift juda qattiq
    },
    budget_limits={
        "clone_budget": 2,
        "change_budget": 10,
        "eval_budget": 5,
        "risk_budget": 1,
    }
)


# ============================================
# PROFILE SETTINGS MAP
# ============================================

PROFILE_SETTINGS_MAP: Dict[ConstitutionProfile, ProfileRuleSettings] = {
    ConstitutionProfile.LAB: LAB_PROFILE_SETTINGS,
    ConstitutionProfile.OPERATOR: OPERATOR_PROFILE_SETTINGS,
    ConstitutionProfile.PUBLIC: PUBLIC_PROFILE_SETTINGS,
}


# ============================================
# FUNKTSIYALAR
# ============================================

def get_class_config(rule_class: RuleClass) -> RuleClassConfig:
    """Qonun sinfining konfiguratsiyasini olish"""
    if rule_class == RuleClass.A_ABSOLUTE:
        return CLASS_A_CONFIG
    elif rule_class == RuleClass.B_MODE_DEPENDENT:
        return CLASS_B_CONFIG
    elif rule_class == RuleClass.C_STRATEGIC:
        return CLASS_C_CONFIG
    raise ValueError(f"Unknown rule class: {rule_class}")


def get_profile_settings(profile: ConstitutionProfile) -> ProfileRuleSettings:
    """Profil bo'yicha sozlamalarni olish"""
    return PROFILE_SETTINGS_MAP.get(profile)


def get_enforcement_level(
    rule_id: str, 
    profile: ConstitutionProfile
) -> RuleEnforcementLevel:
    """Qonun uchun enforcement level olish"""
    settings = get_profile_settings(profile)
    return settings.enforcement_levels.get(rule_id, RuleEnforcementLevel.STRICT)


def is_rule_enabled(rule_id: str, profile: ConstitutionProfile) -> bool:
    """Qonun profil uchun faolmi"""
    settings = get_profile_settings(profile)
    return rule_id in settings.enabled_rules


def get_budget_limit(profile: ConstitutionProfile, budget_type: str) -> int:
    """Budget limit olish"""
    settings = get_profile_settings(profile)
    return settings.budget_limits.get(budget_type, 0)


def can_override(rule_class: RuleClass) -> bool:
    """Qonunni override qilish mumkinmi"""
    config = get_class_config(rule_class)
    return config.bypass_allowed


def get_override_requirement(rule_class: RuleClass) -> str:
    """Override uchun talab"""
    config = get_class_config(rule_class)
    return config.override_requires


def get_class_a_rules() -> Dict[str, str]:
    """Class A qonunlarini olish"""
    return CLASS_A_RULES.copy()


def get_class_b_rules() -> Dict[str, str]:
    """Class B qonunlarini olish"""
    return CLASS_B_RULES.copy()


def get_all_rules_by_class() -> Dict[RuleClass, Dict[str, str]]:
    """Barcha qonunlarni sinflar bo'yicha olish"""
    return {
        RuleClass.A_ABSOLUTE: CLASS_A_RULES,
        RuleClass.B_MODE_DEPENDENT: CLASS_B_RULES,
        RuleClass.C_STRATEGIC: CLASS_C_RULES,
    }


# Class C rules (hozircha bo'sh - keyinchalik qo'shish mumkin)
CLASS_C_RULES: Dict[str, str] = {}


def verify_rule_class_integrity() -> tuple[bool, List[str]]:
    """
    Barcha qonunlar to'g'ri sinflarga ajratilganligini tekshirish
    """
    all_rule_ids = set(CONSTITUTION_RULES.keys())
    classified_ids = ABSOLUTE_RULE_IDS | MODE_DEPENDENT_RULE_IDS | STRATEGIC_RULE_IDS
    
    missing = all_rule_ids - classified_ids
    extra = classified_ids - all_rule_ids
    
    errors = []
    if missing:
        errors.append(f"Qonunlar sinflarga ajratilmagan: {missing}")
    if extra:
        errors.append(f"Noma'lum qonun IDlari: {extra}")
        
    return len(errors) == 0, errors


def get_rule_severity_for_profile(
    rule_id: str, 
    profile: ConstitutionProfile
) -> ViolationSeverity:
    """Profil uchun qonunning violation severity"""
    settings = get_profile_settings(profile)
    if rule_id in settings.custom_severity:
        return settings.custom_severity[rule_id]
    
    # Default - rule metadata dan olish
    rule = CONSTITUTION_RULES.get(rule_id)
    if rule:
        return rule.severity_on_violation
        
    return ViolationSeverity.BLOCKING
