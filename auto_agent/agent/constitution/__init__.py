"""
OmniAgent X - Constitution Kernel
================================
Bu fayl butun Constitution Kernel'ni boshqaradi.

Constitution Kernel 12 ta fundamental qonundan iborat:

1. Original Core muqaddas - live self-edit yo'q, avval clone
2. Har o'zgarish iz qoldiradi - har change'da intent, why, files_touched, revert_recipe
3. Isbotsiz improvement yo'q - evaluation bundle, trust score, regression majburiy
4. Har promotion qaytariladizan - rollback anchor, parent version, artifact hash
5. Human sovereignty - yakuniy hukm insonda, agent faqat proposes
6. Permission scoped - task-bound, clone-bound, worker-bound, time-bound
7. Baholash 3 qatlamli - local validation, evaluation, behavior diff
8. Salbiy natija yashirilmaydi - gains, regressions, risks, unknowns
9. Evolution budget bilan - change budget, clone budget, eval budget
10. Har tajriba xotiraga - reject, fail, success - hamma saqlanadi
11. Identitet drift nazorat - divergence score, generality score
12. Constitution himoyalangan - protected zone, maxsus approval
"""
from typing import Optional, List
from .constitution_rules import (
    # Enums
    RuleClass,
    ConstitutionProfile,
    ViolationSeverity,
    # Dataclasses
    RuleMetadata,
    ChangeSet,
    EvaluationBundle,
    RollbackAnchor,
    DecisionRecord,
    PermissionScope,
    # Functions
    get_constitution_rules,
    get_rule_by_id,
    get_rules_by_class,
    get_rules_by_profile,
    get_absolute_rules,
    get_mode_dependent_rules,
    get_strategic_rules,
    verify_change_set,
    verify_evaluation_bundle,
    verify_rollback_anchor,
    verify_decision_record,
    verify_permission_scope,
    create_change_set,
    create_evaluation_bundle,
    create_rollback_anchor,
    create_permission_scope,
    compute_config_fingerprint,
    compute_artifact_hash,
)

from .rule_classes import (
    RuleEnforcementLevel,
    RuleClassConfig,
    ProfileRuleSettings,
    get_class_config,
    get_profile_settings,
    get_enforcement_level,
    is_rule_enabled,
    get_budget_limit,
    can_override,
    get_override_requirement,
    get_class_a_rules,
    get_class_b_rules,
    get_all_rules_by_class,
    verify_rule_class_integrity,
    get_rule_severity_for_profile,
    LAB_PROFILE_SETTINGS,
    OPERATOR_PROFILE_SETTINGS,
    PUBLIC_PROFILE_SETTINGS,
)

from .policy_guard import (
    PolicyDecision,
    PolicyViolation,
    PolicyCheckResult,
    PolicyGuard,
    create_policy_guard,
    ensure_clone_only_mutation,
    ensure_change_set_complete,
    ensure_evidence_present,
    ensure_rollback_ready,
    ensure_human_decision,
    ensure_scoped_permissions,
    ensure_constitution_protected,
)

from .protected_zone_registry import (
    ZoneType,
    ProtectedZone,
    ProtectedZoneRegistry,
    get_protected_zone_registry,
    create_protected_zone_registry,
    is_path_protected,
    validate_patch_access,
)

from .constitution_profiles import (
    ProfileCapability,
    ProfileConfig,
    get_profile_config,
    get_current_profile,
    set_current_profile,
    is_capability_allowed,
    get_allowed_capabilities,
    requires_approval,
    get_profile_settings as get_profile_settings_from_profiles,
    get_all_profiles,
    get_profile_info,
    validate_operation,
    ProfileManager,
    get_profile_manager,
)

from .constitution_change_protocol import (
    ChangeType,
    ChangeStatus,
    ImpactLevel,
    ImpactAnalysis,
    ConstitutionChangeProposal,
    ConstitutionalReview,
    ConstitutionChangeProtocol,
    get_constitution_change_protocol,
    create_constitution_change_proposal,
    propose_add_rule,
    propose_modify_rule,
)

from .constitutional_audit import (
    AuditEventType,
    AuditSeverity,
    AuditEvent,
    AuditSummary,
    ConstitutionalAudit,
    get_constitutional_audit,
    log_rule_violation,
    log_promotion_blocked,
    get_audit_summary,
)


# ============================================
# ASOSIY CONSTITUTION KERNEL CLASS
# ============================================

class ConstitutionKernel:
    """
    Constitution Kernel - butun tizimning eng chuqur qatlami.
    
    Bu klass 12 ta fundamental qonunni machine-readable tarzda 
    taqdim etadi va ularni runtime'da majbur qiladi.
    """
    
    def __init__(self, profile: ConstitutionProfile = ConstitutionProfile.LAB):
        self.profile = profile
        self.rules = get_constitution_rules()
        self.policy_guard = create_policy_guard(profile)
        self.protected_zones = get_protected_zone_registry()
        self.audit = get_constitutional_audit()
        self.profile_manager = get_profile_manager()
        
    def get_rules(self):
        """Barcha qonunlarni olish"""
        return self.rules
    
    def get_rule(self, rule_id: str):
        """Bitta qonunni olish"""
        return get_rule_by_id(rule_id)
    
    def check_promotion(
        self,
        change_set: ChangeSet,
        evaluation_bundle: EvaluationBundle,
        rollback_anchor: RollbackAnchor,
        decision_record: DecisionRecord,
        permission_scope: PermissionScope,
        destination: str,
    ) -> PolicyCheckResult:
        """Promotion tekshiruvi"""
        
        # Barcha qonunlarni tekshirish
        result = self.policy_guard.check_all_rules(
            change_set=change_set,
            evaluation_bundle=evaluation_bundle,
            rollback_anchor=rollback_anchor,
            decision_record=decision_record,
            permission_scope=permission_scope,
            destination=destination,
            is_main_promotion=(destination == "main"),
        )
        
        # Audit log
        if result.has_blocking_violations:
            self.audit.log_promotion_blocked(
                reason=f"Constitution violations: {len(result.violations)}",
                rule_id=", ".join([v.rule_id for v in result.violations])
            )
        
        return result
    
    def validate_patch(self, target_path: str, patch_type: str = "code") -> tuple[bool, List[str]]:
        """Patch target tekshiruvi"""
        return self.protected_zones.validate_patch_target(target_path, patch_type)
    
    def can_modify_constitution(self, proposal_id: str) -> bool:
        """Constitution o'zgartirish mumkinmi"""
        # Faqat maxsus workflow bilan
        protocol = get_constitution_change_protocol()
        proposal = protocol.get_proposal(proposal_id)
        
        if not proposal:
            return False
        
        return proposal.status == ChangeStatus.APPROVED
    
    def get_status(self) -> dict:
        """Constitution Kernel holati"""
        return {
            "profile": self.profile.value,
            "total_rules": len(self.rules),
            "absolute_rules": len(get_absolute_rules()),
            "mode_dependent_rules": len(get_mode_dependent_rules()),
            "protected_zones": len(self.protected_zones.get_all_zones()),
            "audit_events": len(self.audit.events),
            "current_version": get_constitution_change_protocol().get_current_version(),
        }


# Global kernel
_kernel: Optional[ConstitutionKernel] = None


def get_constitution_kernel(profile: ConstitutionProfile = ConstitutionProfile.LAB) -> ConstitutionKernel:
    """Global Constitution Kernel olish"""
    global _kernel
    if _kernel is None:
        _kernel = ConstitutionKernel(profile)
    return _kernel


def create_constitution_kernel(profile: ConstitutionProfile = ConstitutionProfile.LAB) -> ConstitutionKernel:
    """Constitution Kernel yaratish"""
    return ConstitutionKernel(profile)


# ============================================
# TEZ FUNKTSIYALAR
# ============================================

def get_rules() -> dict:
    """Barcha qonunlarni olish"""
    return get_constitution_rules()


def get_absolute_rules_list() -> list:
    """Class A qonunlarni olish"""
    return get_absolute_rules()


def check_constitution_violation(
    rule_id: str,
    message: str,
    details: dict = None
) -> AuditEvent:
    """Qoidabuzarlashni log qilish"""
    rule = get_rule_by_id(rule_id)
    rule_name = rule.name if rule else "Unknown"
    return log_rule_violation(rule_id, rule_name, message, details)


def verify_promotion_ready(
    change_set: ChangeSet,
    evaluation_bundle: EvaluationBundle,
    rollback_anchor: RollbackAnchor,
    decision_record: DecisionRecord,
    permission_scope: PermissionScope,
    destination: str,
    profile: ConstitutionProfile = ConstitutionProfile.LAB
) -> PolicyCheckResult:
    """Promotion tayyormi tekshirish"""
    kernel = get_constitution_kernel(profile)
    return kernel.check_promotion(
        change_set=change_set,
        evaluation_bundle=evaluation_bundle,
        rollback_anchor=rollback_anchor,
        decision_record=decision_record,
        permission_scope=permission_scope,
        destination=destination,
    )


def get_constitution_status() -> dict:
    """Constitution holatini olish"""
    kernel = get_constitution_kernel()
    return kernel.get_status()
