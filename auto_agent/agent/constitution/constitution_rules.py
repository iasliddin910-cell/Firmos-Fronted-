"""
OmniAgent X - Constitution Kernel
=================================
Bu fayl 12 ta fundamental qonundan iborat.
Bular World No.1+ self-evolving system uchun yetarlicha qattiq va to'g'ri to'plam.

Qonunlar:
1. Original Core muqaddas
2. Har o'zgarish iz qoldiradi
3. Isbotsiz improvement yo'q
4. Har promotion qaytariladigan
5. Human sovereignty
6. Permission scoped
7. Baholash 3 qatlamli
8. Salbiy natija yashirilmaydi
9. Evolution budget bilan
10. Har tajriba xotiraga
11. Identitet drift nazorat
12. Constitution himoyalangan
"""
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
import hashlib
import json


class RuleClass(Enum):
    """
    Constitutional Classes - Barcha qonunlar bir xil darajada emas.
    """
    A_ABSOLUTE = "A"  # Hech qachon buzilmaydi
    B_MODE_DEPENDENT = "B"  # Lab/Operator/Public ga qarab o'zgaradi
    C_STRATEGIC = "C"  # Roadmap va identity ga tegishli


class ConstitutionProfile(Enum):
    """Constitution profillari"""
    LAB = "lab"           # Ichki kuchli rejim
    OPERATOR = "operator" # Real boshqarish
    PUBLIC = "public"    # Ommaga chiqish


class ViolationSeverity(Enum):
    """Qoidabuzarlash og'irligi"""
    BLOCKING = "blocking"       # Promotionni to'xtatadi
    WARNING = "warning"        # Ogohlantirish
    AUDIT = "audit"            # Faqat log


@dataclass
class RuleMetadata:
    """Qonun haqida metadata"""
    rule_id: str
    name: str
    description: str
    rule_class: RuleClass
    profiles: List[ConstitutionProfile]
    severity_on_violation: ViolationSeverity
    enforce_function: Optional[Callable] = None


@dataclass
class ChangeSet:
    """
    Har o'zgarish uchun majburiy maydonlar (Qonun 2)
    """
    intent: str                          # Nima maqsad qilindi
    why: str                              # Nega
    files_touched: List[str]             # Qaysi fayllar tegildi
    patch_summary: str                    # Patch xulosa
    revert_recipe: str                    # Qaytarish retsepti
    evidence_refs: List[str]             # Dalil havolalari
    author: str = "agent"                 # Kim sabab bo'ldi
    signal_basis: str = ""                # Qaysi signal asos
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    artifact_hash: str = ""               # Chiqgan artifact
    

@dataclass
class EvaluationBundle:
    """
    Improvement uchun majburiy evidence (Qonun 3)
    """
    baseline_comparison: Dict[str, Any]   # Baseline taqqoslash
    validation_artifacts: Dict[str, Any]  # Validation artifactlari
    task_metrics: Dict[str, float]         # Task metrikalari
    behavior_delta: Dict[str, Any]        # Behavior o'zgarishi
    trust_score: float                     # Ishonch balli (0-1)
    regressions: List[str] = field(default_factory=list)


@dataclass
class RollbackAnchor:
    """
    Promotion uchun qaytarish nuqtasi (Qonun 4)
    """
    parent_version: str                    # Oldingi versiya
    config_fingerprint: str                # Config barmoq izi
    artifact_hash: str                     # Artifact hash
    revert_recipe: str                    # Qaytarish retsepti
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class DecisionRecord:
    """
    Human decision record (Qonun 5)
    """
    decision: str                          # approve/deny
    approver: str                         # Kim tasdiqladi
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    signature: str = ""                    # Imzo


@dataclass
class PermissionScope:
    """
    Scoped permission (Qonun 6)
    """
    task_bound: str                        # Qaysi task
    clone_bound: str                       # Qaysi clone
    worker_bound: str                      # Qaysi worker
    time_bound: Optional[str]              # Qachongacha
    least_privilege: bool = True           # Minimal imtiyoz


# ============================================
# 12 TA KONSTITUTSIYA QONUNI
# ============================================

CONSTITUTION_RULES: Dict[str, RuleMetadata] = {}


def _register_rule(rule: RuleMetadata):
    """Qonunni ro'yxatga olish"""
    CONSTITUTION_RULES[rule.rule_id] = rule
    return rule


# ============================================
# QONUN 1: Original Core muqaddas
# ============================================
QONUN_1 = _register_rule(RuleMetadata(
    rule_id="CK_001",
    name="Original Core muqaddas",
    description=(
        "Asosiy jonli tizim default holatda immutable. "
        "Hech qanday self-upgrade to'g'ridan-to'g'ri main kodga, "
        "live config'ga yoki active runtime behavior'ga tegamaydi. "
        "Barcha self-modification clone'da, isolated workspace'da, "
        "review'dan keyin bo'ladi."
    ),
    rule_class=RuleClass.A_ABSOLUTE,
    profiles=[ConstitutionProfile.LAB, ConstitutionProfile.OPERATOR, ConstitutionProfile.PUBLIC],
    severity_on_violation=ViolationSeverity.BLOCKING,
    enforce_function=None
))


# ============================================
# QONUN 2: Har o'zgarish iz qoldiradi
# ============================================
QONUN_2 = _register_rule(RuleMetadata(
    rule_id="CK_002",
    name="Har o'zgarish iz qoldiradi",
    description=(
        "Tizim ichida 'nima o'zgargani noma'lum' degan holat bo'lmasligi kerak. "
        "Har change'da bo'lishi shart: kim sabab bo'ldi, qaysi signal asos bo'ldi, "
        "qaysi fayllar tegildi, nima maqsad qilindi, nima artifact chiqdi."
    ),
    rule_class=RuleClass.A_ABSOLUTE,
    profiles=[ConstitutionProfile.LAB, ConstitutionProfile.OPERATOR, ConstitutionProfile.PUBLIC],
    severity_on_violation=ViolationSeverity.BLOCKING,
    enforce_function=None
))


# ============================================
# QONUN 3: Isbotsiz improvement yo'q
# ============================================
QONUN_3 = _register_rule(RuleMetadata(
    rule_id="CK_003",
    name="Isbotsiz improvement yo'q",
    description=(
        "Agent hech qachon 'men yaxshilandim', 'bu yaxshi upgrade', "
        "'bu merge'ga tayyor' deya olmaydi, agar o'lchov va evidence bo'lmasa. "
        "Kamida: baseline comparison, validation artifacts, evaluation bundle, "
        "capability delta yoki behavior delta bo'lishi kerak."
    ),
    rule_class=RuleClass.A_ABSOLUTE,
    profiles=[ConstitutionProfile.LAB, ConstitutionProfile.OPERATOR, ConstitutionProfile.PUBLIC],
    severity_on_violation=ViolationSeverity.BLOCKING,
    enforce_function=None
))


# ============================================
# QONUN 4: Har promotion qaytariladigan
# ============================================
QONUN_4 = _register_rule(RuleMetadata(
    rule_id="CK_004",
    name="Har promotion qaytariladigan bo'lishi shart",
    description=(
        "Qaytib bo'lmaydigan upgrade promotion'ga chiqmaydi. "
        "Har approved destination uchun: rollback anchor, parent version, "
        "config fingerprint, artifact hash, revert recipe bo'lishi kerak."
    ),
    rule_class=RuleClass.A_ABSOLUTE,
    profiles=[ConstitutionProfile.LAB, ConstitutionProfile.OPERATOR, ConstitutionProfile.PUBLIC],
    severity_on_violation=ViolationSeverity.BLOCKING,
    enforce_function=None
))


# ============================================
# QONUN 5: Human sovereignty
# ============================================
QONUN_5 = _register_rule(RuleMetadata(
    rule_id="CK_005",
    name="Human sovereignty saqlanadi",
    description=(
        "Yakuniy hukm sizda. Agent tavsiya beradi, report qiladi, "
        "canary tavsiya qiladi, fork tavsiya qiladi. "
        "Lekin main, branch, fork taqdirini o'zi yakuniy hal qilmaydi. "
        "Agent proposes. Human disposes."
    ),
    rule_class=RuleClass.A_ABSOLUTE,
    profiles=[ConstitutionProfile.LAB, ConstitutionProfile.OPERATOR, ConstitutionProfile.PUBLIC],
    severity_on_violation=ViolationSeverity.BLOCKING,
    enforce_function=None
))


# ============================================
# QONUN 6: Permission scoped
# ============================================
QONUN_6 = _register_rule(RuleMetadata(
    rule_id="CK_006",
    name="Permission har doim scope bilan beriladi",
    description=(
        "Hech bir clone, worker yoki tool cheksiz access, doimiy secret, "
        "global session yoki universal write capability olmasligi kerak. "
        "Har permission: task-bound, clone-bound, worker-bound, time-bound, "
        "least-privilege bo'lishi kerak."
    ),
    rule_class=RuleClass.A_ABSOLUTE,
    profiles=[ConstitutionProfile.LAB, ConstitutionProfile.OPERATOR, ConstitutionProfile.PUBLIC],
    severity_on_violation=ViolationSeverity.BLOCKING,
    enforce_function=None
))


# ============================================
# QONUN 7: Baholash 3 qatlamli
# ============================================
QONUN_7 = _register_rule(RuleMetadata(
    rule_id="CK_007",
    name="Baholash har doim uch qatlamli",
    description=(
        "Bitta test yoki bitta benchmark yetmaydi. "
        "Har upgrade kamida 3 qavatdan o'tadi: "
        "local validation, evaluation/replay/benchmark, behavior diff."
    ),
    rule_class=RuleClass.A_ABSOLUTE,
    profiles=[ConstitutionProfile.LAB, ConstitutionProfile.OPERATOR, ConstitutionProfile.PUBLIC],
    severity_on_violation=ViolationSeverity.BLOCKING,
    enforce_function=None
))


# ============================================
# QONUN 8: Salbiy natija yashirilmaydi
# ============================================
QONUN_8 = _register_rule(RuleMetadata(
    rule_id="CK_008",
    name="Salbiy natija yashirilmaydi",
    description=(
        "Report faqat yaxshi tomonni ko'rsatmaydi. "
        "Har dossier'da majburiy: gains, regressions, risks, unknowns."
    ),
    rule_class=RuleClass.A_ABSOLUTE,
    profiles=[ConstitutionProfile.LAB, ConstitutionProfile.OPERATOR, ConstitutionProfile.PUBLIC],
    severity_on_violation=ViolationSeverity.BLOCKING,
    enforce_function=None
))


# ============================================
# QONUN 9: Evolution budget
# ============================================
QONUN_9 = _register_rule(RuleMetadata(
    rule_id="CK_009",
    name="Evolution budget bilan yuradi",
    description=(
        "Self-improvement cheksiz parallel, cheksiz diff, cheksiz experiment bo'lmaydi. "
        "Tizimda budget bo'ladi: change budget, clone budget, eval budget, "
        "risk budget, resource budget."
    ),
    rule_class=RuleClass.B_MODE_DEPENDENT,
    profiles=[ConstitutionProfile.LAB, ConstitutionProfile.OPERATOR, ConstitutionProfile.PUBLIC],
    severity_on_violation=ViolationSeverity.WARNING,
    enforce_function=None
))


# ============================================
# QONUN 10: Har tajriba xotiraga
# ============================================
QONUN_10 = _register_rule(RuleMetadata(
    rule_id="CK_010",
    name="Har tajriba xotiraga tushadi",
    description=(
        "Reject bo'lsin, fail bo'lsin, success bo'lsin - "
        "har urinish tizim xotirasiga kiradi. "
        "Saqlanadi: nima sinandi, nima ishladi, nima ishlamadi, "
        "nega rad qilindi, qaysi signal hype chiqdi."
    ),
    rule_class=RuleClass.A_ABSOLUTE,
    profiles=[ConstitutionProfile.LAB, ConstitutionProfile.OPERATOR, ConstitutionProfile.PUBLIC],
    severity_on_violation=ViolationSeverity.AUDIT,
    enforce_function=None
))


# ============================================
# QONUN 11: Identitet drift
# ============================================
QONUN_11 = _register_rule(RuleMetadata(
    rule_id="CK_011",
    name="Identitet drift nazorat qilinadi",
    description=(
        "Har improvement main'ga qo'shilmaydi. "
        "Tizim o'z identitetini yo'qotmasligi kerak. "
        "Agar upgrade juda ixtisoslashgan bo'lsa, main utility'ni buzsa, "
        "behavior'ni keskin o'zgartirsa - u branch, fork yoki experiment yo'liga tushadi."
    ),
    rule_class=RuleClass.B_MODE_DEPENDENT,
    profiles=[ConstitutionProfile.LAB, ConstitutionProfile.OPERATOR, ConstitutionProfile.PUBLIC],
    severity_on_violation=ViolationSeverity.WARNING,
    enforce_function=None
))


# ============================================
# QONUN 12: Constitution himoyalangan
# ============================================
QONUN_12 = _register_rule(RuleMetadata(
    rule_id="CK_012",
    name="Konstitutsiya o'zi ham himoyalangan bo'ladi",
    description=(
        "Agent o'zi self-modification qila oladi, lekin Constitution Kernel'ni "
        "oddiy patch sifatida o'zgartira olmaydi. "
        "Konstitutsiya qoidalarini o'zgartirish: alohida class'dagi high-trust proposal, "
        "alohida audit, maxsus approval path bilan bo'ladi."
    ),
    rule_class=RuleClass.A_ABSOLUTE,
    profiles=[ConstitutionProfile.LAB, ConstitutionProfile.OPERATOR, ConstitutionProfile.PUBLIC],
    severity_on_violation=ViolationSeverity.BLOCKING,
    enforce_function=None
))


# ============================================
# YORDAMCHI FUNKTSIYALAR
# ============================================

def get_constitution_rules() -> Dict[str, RuleMetadata]:
    """Barcha konstitutsiya qonunlarini olish"""
    return CONSTITUTION_RULES


def get_rule_by_id(rule_id: str) -> Optional[RuleMetadata]:
    """Qonunni ID bo'yicha olish"""
    return CONSTITUTION_RULES.get(rule_id)


def get_rules_by_class(rule_class: RuleClass) -> List[RuleMetadata]:
    """Qonunlarni sinf bo'yicha filtrlash"""
    return [r for r in CONSTITUTION_RULES.values() if r.rule_class == rule_class]


def get_rules_by_profile(profile: ConstitutionProfile) -> List[RuleMetadata]:
    """Qonunlarni profil bo'yicha filtrlash"""
    return [r for r in CONSTITUTION_RULES.values() if profile in r.profiles]


def get_absolute_rules() -> List[RuleMetadata]:
    """Class A - Absolute laws (hech qachon buzilmaydi)"""
    return get_rules_by_class(RuleClass.A_ABSOLUTE)


def get_mode_dependent_rules() -> List[RuleMetadata]:
    """Class B - Mode-dependent laws"""
    return get_rules_by_class(RuleClass.B_MODE_DEPENDENT)


def get_strategic_rules() -> List[RuleMetadata]:
    """Class C - Strategic laws"""
    return get_rules_by_class(RuleClass.C_STRATEGIC)


def verify_change_set(change_set: ChangeSet) -> tuple[bool, List[str]]:
    """
    ChangeSet ni tekshirish (Qonun 2 ni bajarish)
    Returns: (is_valid, list_of_missing_fields)
    """
    missing = []
    
    if not change_set.intent:
        missing.append("intent")
    if not change_set.why:
        missing.append("why")
    if not change_set.files_touched:
        missing.append("files_touched")
    if not change_set.patch_summary:
        missing.append("patch_summary")
    if not change_set.revert_recipe:
        missing.append("revert_recipe")
    if not change_set.evidence_refs:
        missing.append("evidence_refs")
        
    return len(missing) == 0, missing


def verify_evaluation_bundle(bundle: EvaluationBundle) -> tuple[bool, List[str]]:
    """
    EvaluationBundle ni tekshirish (Qonun 3 ni bajarish)
    Returns: (is_valid, list_of_missing_fields)
    """
    missing = []
    
    if not bundle.baseline_comparison:
        missing.append("baseline_comparison")
    if not bundle.validation_artifacts:
        missing.append("validation_artifacts")
    if not bundle.task_metrics:
        missing.append("task_metrics")
    if not bundle.behavior_delta:
        missing.append("behavior_delta")
    if bundle.trust_score is None or bundle.trust_score < 0:
        missing.append("trust_score")
        
    return len(missing) == 0, missing


def verify_rollback_anchor(anchor: RollbackAnchor) -> tuple[bool, List[str]]:
    """
    RollbackAnchor ni tekshirish (Qonun 4 ni bajarish)
    Returns: (is_valid, list_of_missing_fields)
    """
    missing = []
    
    if not anchor.parent_version:
        missing.append("parent_version")
    if not anchor.config_fingerprint:
        missing.append("config_fingerprint")
    if not anchor.artifact_hash:
        missing.append("artifact_hash")
    if not anchor.revert_recipe:
        missing.append("revert_recipe")
        
    return len(missing) == 0, missing


def verify_decision_record(record: DecisionRecord) -> bool:
    """
    DecisionRecord ni tekshirish (Qonun 5 ni bajarish)
    Returns: is_valid
    """
    if not record.decision:
        return False
    if not record.approver:
        return False
    if record.decision not in ["approve", "deny"]:
        return False
    return True


def verify_permission_scope(scope: PermissionScope) -> tuple[bool, List[str]]:
    """
    PermissionScope ni tekshirish (Qonun 6 ni bajarish)
    Returns: (is_valid, list_of_issues)
    """
    issues = []
    
    if not scope.task_bound:
        issues.append("task_bound")
    if not scope.clone_bound:
        issues.append("clone_bound")
    if not scope.worker_bound:
        issues.append("worker_bound")
        
    # Cheksiz permission xavfi
    if scope.task_bound == "*" and scope.clone_bound == "*":
        issues.append("unrestricted_scope")
        
    return len(issues) == 0, issues


def create_change_set(
    intent: str,
    why: str,
    files_touched: List[str],
    patch_summary: str,
    revert_recipe: str,
    evidence_refs: List[str],
    author: str = "agent",
    signal_basis: str = ""
) -> ChangeSet:
    """ChangeSet yaratish"""
    return ChangeSet(
        intent=intent,
        why=why,
        files_touched=files_touched,
        patch_summary=patch_summary,
        revert_recipe=revert_recipe,
        evidence_refs=evidence_refs,
        author=author,
        signal_basis=signal_basis
    )


def create_evaluation_bundle(
    baseline_comparison: Dict[str, Any],
    validation_artifacts: Dict[str, Any],
    task_metrics: Dict[str, float],
    behavior_delta: Dict[str, Any],
    trust_score: float,
    regressions: List[str] = None
) -> EvaluationBundle:
    """EvaluationBundle yaratish"""
    return EvaluationBundle(
        baseline_comparison=baseline_comparison,
        validation_artifacts=validation_artifacts,
        task_metrics=task_metrics,
        behavior_delta=behavior_delta,
        trust_score=trust_score,
        regressions=regressions or []
    )


def create_rollback_anchor(
    parent_version: str,
    config_fingerprint: str,
    artifact_hash: str,
    revert_recipe: str
) -> RollbackAnchor:
    """RollbackAnchor yaratish"""
    return RollbackAnchor(
        parent_version=parent_version,
        config_fingerprint=config_fingerprint,
        artifact_hash=artifact_hash,
        revert_recipe=revert_recipe
    )


def create_permission_scope(
    task_bound: str,
    clone_bound: str,
    worker_bound: str,
    time_bound: Optional[str] = None
) -> PermissionScope:
    """PermissionScope yaratish"""
    return PermissionScope(
        task_bound=task_bound,
        clone_bound=clone_bound,
        worker_bound=worker_bound,
        time_bound=time_bound
    )


def compute_config_fingerprint(config: Dict[str, Any]) -> str:
    """Config dan barmoq izi hisoblash"""
    config_str = json.dumps(config, sort_keys=True)
    return hashlib.sha256(config_str.encode()).hexdigest()[:16]


def compute_artifact_hash(artifact: Any) -> str:
    """Artifact dan hash hisoblash"""
    artifact_str = str(artifact)
    return hashlib.sha256(artifact_str.encode()).hexdigest()[:16]
