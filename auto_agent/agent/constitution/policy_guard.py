"""
OmniAgent X - Policy Guard
=========================
Bu fayl Constitution Kernel qonunlarini runtime'da tekshiradi.

Bu qatlam qonunlarni real vaqtda majbur qiladi:
- ensure_clone_only_mutation()
- ensure_human_decision_for_main()
- ensure_negative_sections_present()
- ensure_scoped_permissions()
- va boshqalar
"""
import os
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from .constitution_rules import (
    CONSTITUTION_RULES,
    ChangeSet,
    EvaluationBundle,
    RollbackAnchor,
    DecisionRecord,
    PermissionScope,
    ConstitutionProfile,
    ViolationSeverity,
    RuleClass,
    verify_change_set,
    verify_evaluation_bundle,
    verify_rollback_anchor,
    verify_decision_record,
    verify_permission_scope,
    RuleMetadata
)
from .rule_classes import (
    get_profile_settings,
    is_rule_enabled,
    get_enforcement_level,
    RuleEnforcementLevel,
    PROFILE_SETTINGS_MAP
)


logger = logging.getLogger(__name__)


class PolicyDecision(Enum):
    """PolicyGuard qarori"""
    ALLOW = "allow"
    DENY = "deny"
    WARN = "warn"        # Ruxsat beradi, lekin ogohlantiradi
    AUDIT = "audit"      # Log qiladi, ruxsat beradi


@dataclass
class PolicyViolation:
    """Qoidabuzarlash"""
    rule_id: str
    rule_name: str
    severity: ViolationSeverity
    message: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    context: Dict[str, Any] = field(default_factory=dict)
    action_taken: str = "blocked"  # blocked, warned, logged


@dataclass
class PolicyCheckResult:
    """Policy tekshiruv natijasi"""
    decision: PolicyDecision
    violations: List[PolicyViolation] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_allowed(self) -> bool:
        return self.decision in [PolicyDecision.ALLOW, PolicyDecision.WARN, PolicyDecision.AUDIT]
    
    @property
    def has_blocking_violations(self) -> bool:
        return any(v.severity == ViolationSeverity.BLOCKING for v in self.violations)


class PolicyGuard:
    """
    Runtime enforcement for Constitution Kernel
    Bu qatlam barcha qonunlarni runtime'da tekshiradi.
    """
    
    def __init__(self, profile: ConstitutionProfile = ConstitutionProfile.LAB):
        self.profile = profile
        self.settings = get_profile_settings(profile)
        self.violation_history: List[PolicyViolation] = []
        self.audit_log: List[Dict[str, Any]] = []
        
        logger.info(f"PolicyGuard initialized with profile: {profile.value}")
    
    # =============================================
    # QONUN 1: Original Core muqaddas
    # =============================================
    
    def ensure_clone_only_mutation(
        self,
        destination: str,
        current_workspace: str,
        is_promotion: bool = False
    ) -> PolicyCheckResult:
        """
        Qonun 1 ni tekshirish: Faqat clone'da mutation ruxsat etiladi.
        Originalga to'g'ridan-to'g'ri yozish mumkin emas.
        """
        violations = []
        
        # Original workspace aniqlash
        original_paths = ["/workspace/original", "/workspace/main", "/workspace/project/Firmos-Fronted-/auto_agent"]
        is_original = any(destination.startswith(op) for op in original_paths)
        
        if is_original and not is_promotion:
            # Bu promotion emas, to'g'ridan-to'g'ri yozish
            violations.append(PolicyViolation(
                rule_id="CK_001",
                rule_name="Original Core muqaddas",
                severity=ViolationSeverity.BLOCKING,
                message=f"Original workspace'ga to'g'ridan-to'g'ri yozish taqiqlanadi: {destination}",
                context={"destination": destination, "current_workspace": current_workspace}
            ))
        
        # Qaror
        decision = PolicyDecision.DENY if violations else PolicyDecision.ALLOW
        
        result = PolicyCheckResult(decision=decision, violations=violations)
        self._log_check("CK_001", result)
        
        return result
    
    # =============================================
    # QONUN 2: Har o'zgarish iz qoldiradi
    # =============================================
    
    def ensure_change_set_complete(self, change_set: Optional[ChangeSet]) -> PolicyCheckResult:
        """
        Qonun 2 ni tekshirish: Har o'zgarish to'liq iz qoldiradi.
        """
        violations = []
        warnings = []
        
        if change_set is None:
            violations.append(PolicyViolation(
                rule_id="CK_002",
                rule_name="Har o'zgarish iz qoldiradi",
                severity=ViolationSeverity.BLOCKING,
                message="ChangeSet taqdim etilmagan"
            ))
        else:
            is_valid, missing = verify_change_set(change_set)
            if not is_valid:
                violations.append(PolicyViolation(
                    rule_id="CK_002",
                    rule_name="Har o'zgarish iz qoldiradi",
                    severity=ViolationSeverity.BLOCKING,
                    message=f"ChangeSet to'liq emas. Yo'q maydonlar: {', '.join(missing)}",
                    context={"missing_fields": missing}
                ))
        
        decision = PolicyDecision.DENY if violations else PolicyDecision.ALLOW
        result = PolicyCheckResult(decision=decision, violations=violations, warnings=warnings)
        self._log_check("CK_002", result)
        
        return result
    
    # =============================================
    # QONUN 3: Isbotsiz improvement yo'q
    # =============================================
    
    def ensure_evidence_present(self, bundle: Optional[EvaluationBundle]) -> PolicyCheckResult:
        """
        Qonun 3 ni tekshirish: Isbotsiz improvement claim qilinmaydi.
        """
        violations = []
        warnings = []
        
        if bundle is None:
            violations.append(PolicyViolation(
                rule_id="CK_003",
                rule_name="Isbotsiz improvement yo'q",
                severity=ViolationSeverity.BLOCKING,
                message="EvaluationBundle taqdim etilmagan"
            ))
        else:
            is_valid, missing = verify_evaluation_bundle(bundle)
            if not is_valid:
                violations.append(PolicyViolation(
                    rule_id="CK_003",
                    rule_name="Isbotsiz improvement yo'q",
                    severity=ViolationSeverity.BLOCKING,
                    message=f"EvaluationBundle to'liq emas. Yo'q maydonlar: {', '.join(missing)}",
                    context={"missing_fields": missing}
                ))
            
            # Trust score tekshirish
            if bundle.trust_score < 0.5:
                warnings.append(f"Trust score past: {bundle.trust_score}")
        
        decision = PolicyDecision.DENY if violations else (PolicyDecision.WARN if warnings else PolicyDecision.ALLOW)
        result = PolicyCheckResult(decision=decision, violations=violations, warnings=warnings)
        self._log_check("CK_003", result)
        
        return result
    
    # =============================================
    # QONUN 4: Har promotion qaytariladigan
    # =============================================
    
    def ensure_rollback_ready(
        self,
        anchor: Optional[RollbackAnchor],
        is_main_promotion: bool = False
    ) -> PolicyCheckResult:
        """
        Qonun 4 ni tekshirish: Har promotion qaytariladigan bo'lishi shart.
        """
        violations = []
        warnings = []
        
        if anchor is None:
            violations.append(PolicyViolation(
                rule_id="CK_004",
                rule_name="Har promotion qaytariladigan bo'lishi shart",
                severity=ViolationSeverity.BLOCKING,
                message="RollbackAnchor taqdim etilmagan"
            ))
        else:
            is_valid, missing = verify_rollback_anchor(anchor)
            if not is_valid:
                violations.append(PolicyViolation(
                    rule_id="CK_004",
                    rule_name="Har promotion qaytariladigan bo'lishi shart",
                    severity=ViolationSeverity.BLOCKING,
                    message=f"RollbackAnchor to'liq emas. Yo'q maydonlar: {', '.join(missing)}",
                    context={"missing_fields": missing}
                ))
        
        decision = PolicyDecision.DENY if violations else PolicyDecision.ALLOW
        result = PolicyCheckResult(decision=decision, violations=violations, warnings=warnings)
        self._log_check("CK_004", result)
        
        return result
    
    # =============================================
    # QONUN 5: Human sovereignty
    # =============================================
    
    def ensure_human_decision(self, decision: Optional[DecisionRecord], destination: str) -> PolicyCheckResult:
        """
        Qonun 5 ni tekshirish: Main promotion uchun human decision majburiy.
        """
        violations = []
        warnings = []
        
        is_main = destination in ["main", "MAIN", "primary"]
        
        if is_main:
            if decision is None:
                violations.append(PolicyViolation(
                    rule_id="CK_005",
                    rule_name="Human sovereignty saqlanadi",
                    severity=ViolationSeverity.BLOCKING,
                    message="Main promotion uchun DecisionRecord talab qilinadi"
                ))
            else:
                is_valid = verify_decision_record(decision)
                if not is_valid:
                    violations.append(PolicyViolation(
                        rule_id="CK_005",
                        rule_name="Human sovereignty saqlanadi",
                        severity=ViolationSeverity.BLOCKING,
                        message="DecisionRecord noto'g'ri"
                    ))
        
        decision = PolicyDecision.DENY if violations else PolicyDecision.ALLOW
        result = PolicyCheckResult(decision=decision, violations=violations, warnings=warnings)
        self._log_check("CK_005", result)
        
        return result
    
    # =============================================
    # QONUN 6: Permission scoped
    # =============================================
    
    def ensure_scoped_permissions(self, scope: Optional[PermissionScope]) -> PolicyCheckResult:
        """
        Qonun 6 ni tekshirish: Permission har doim scope bilan beriladi.
        """
        violations = []
        warnings = []
        
        if scope is None:
            violations.append(PolicyViolation(
                rule_id="CK_006",
                rule_name="Permission scoped",
                severity=ViolationSeverity.BLOCKING,
                message="PermissionScope taqdim etilmagan"
            ))
        else:
            is_valid, issues = verify_permission_scope(scope)
            if not is_valid:
                violations.append(PolicyViolation(
                    rule_id="CK_006",
                    rule_name="Permission scoped",
                    severity=ViolationSeverity.BLOCKING,
                    message=f"PermissionScope muammolari: {', '.join(issues)}",
                    context={"issues": issues}
                ))
        
        decision = PolicyDecision.DENY if violations else PolicyDecision.ALLOW
        result = PolicyCheckResult(decision=decision, violations=violations, warnings=warnings)
        self._log_check("CK_006", result)
        
        return result
    
    # =============================================
    # QONUN 7: Baholash 3 qatlamli
    # =============================================
    
    def ensure_triple_validation(
        self,
        local_validation: bool,
        evaluation_bundle: Optional[EvaluationBundle],
        behavior_diff: Optional[Dict[str, Any]]
    ) -> PolicyCheckResult:
        """
        Qonun 7 ni tekshirish: Har upgrade 3 qavatdan o'tadi.
        """
        violations = []
        warnings = []
        
        # 1. Local validation
        if not local_validation:
            violations.append(PolicyViolation(
                rule_id="CK_007",
                rule_name="Baholash 3 qatlamli",
                severity=ViolationSeverity.BLOCKING,
                message="Local validation muvaffaqiyatsiz"
            ))
        
        # 2. Evaluation bundle
        if evaluation_bundle is None:
            violations.append(PolicyViolation(
                rule_id="CK_007",
                rule_name="Baholash 3 qatlamli",
                severity=ViolationSeverity.BLOCKING,
                message="Evaluation bundle yo'q"
            ))
        
        # 3. Behavior diff
        if behavior_diff is None or not behavior_diff:
            warnings.append("Behavior diff taqdim etilmagan")
        
        # Decision
        if violations:
            decision = PolicyDecision.DENY
        elif warnings:
            decision = PolicyDecision.WARN
        else:
            decision = PolicyDecision.ALLOW
            
        result = PolicyCheckResult(decision=decision, violations=violations, warnings=warnings)
        self._log_check("CK_007", result)
        
        return result
    
    # =============================================
    # QONUN 8: Salbiy natija yashirilmaydi
    # =============================================
    
    def ensure_negative_sections(
        self,
        gains: Optional[List[str]],
        regressions: Optional[List[str]],
        risks: Optional[List[str]],
        unknowns: Optional[List[str]]
    ) -> PolicyCheckResult:
        """
        Qonun 8 ni tekshirish: Har dossier'da salbiy natijalar ham bo'lishi kerak.
        """
        violations = []
        warnings = []
        
        # Majburiy maydonlar
        if gains is None:
            violations.append(PolicyViolation(
                rule_id="CK_008",
                rule_name="Salbiy natija yashirilmaydi",
                severity=ViolationSeverity.BLOCKING,
                message="Gains section yo'q"
            ))
        
        # Regressions - bu eng muhim
        if regressions is None:
            violations.append(PolicyViolation(
                rule_id="CK_008",
                rule_name="Salbiy natija yashirilmaydi",
                severity=ViolationSeverity.BLOCKING,
                message="Regressions section majburiy"
            ))
        
        # Risks va unknowns - ogohlantirish
        if risks is None or len(risks) == 0:
            warnings.append("Risks section yo'q yoki bo'sh")
        
        if unknowns is None or len(unknowns) == 0:
            warnings.append("Unknowns section yo'q yoki bo'sh")
        
        decision = PolicyDecision.DENY if violations else (PolicyDecision.WARN if warnings else PolicyDecision.ALLOW)
        result = PolicyCheckResult(decision=decision, violations=violations, warnings=warnings)
        self._log_check("CK_008", result)
        
        return result
    
    # =============================================
    # QONUN 9: Evolution budget
    # =============================================
    
    def ensure_within_budget(
        self,
        budget_type: str,
        current_usage: int
    ) -> PolicyCheckResult:
        """
        Qonun 9 ni tekshirish: Evolution budget bilan yuradi.
        """
        violations = []
        warnings = []
        
        limit = self.settings.budget_limits.get(budget_type, 0)
        
        if current_usage >= limit:
            violations.append(PolicyViolation(
                rule_id="CK_009",
                rule_name="Evolution budget bilan",
                severity=ViolationSeverity.WARNING,  # Qattiqroq qilish mumkin
                message=f"{budget_type} budget tugadi: {current_usage}/{limit}",
                context={"budget_type": budget_type, "current": current_usage, "limit": limit}
            ))
        
        decision = PolicyDecision.DENY if violations else PolicyDecision.ALLOW
        result = PolicyCheckResult(decision=decision, violations=violations, warnings=warnings)
        self._log_check("CK_009", result)
        
        return result
    
    # =============================================
    # QONUN 10: Har tajriba xotiraga
    # =============================================
    
    def ensure_experiment_logged(self, experiment_id: str) -> PolicyCheckResult:
        """
        Qonun 10 ni tekshirish: Har tajriba xotiraga tushadi.
        """
        # Bu asosan audit uchun - har doim ruxsat beriladi
        result = PolicyCheckResult(
            decision=PolicyDecision.AUDIT,
            metadata={"experiment_id": experiment_id, "logged": True}
        )
        self._log_check("CK_010", result)
        
        return result
    
    # =============================================
    # QONUN 11: Identitet drift
    # =============================================
    
    def ensure_identity_preserved(
        self,
        divergence_score: float,
        generality_score: float,
        is_main_promotion: bool = False
    ) -> PolicyCheckResult:
        """
        Qonun 11 ni tekshirish: Identitet drift nazorat qilinadi.
        """
        violations = []
        warnings = []
        
        # Divergence score - yangi kod asosiy koddan qancha farq qilmoqda
        if divergence_score > 0.7 and is_main_promotion:
            violations.append(PolicyViolation(
                rule_id="CK_011",
                rule_name="Identitet drift nazorat",
                severity=ViolationSeverity.WARNING,
                message=f"Divergence score yuqori: {divergence_score}. Branch/fork kerak bo'lishi mumkin.",
                context={"divergence_score": divergence_score}
            ))
        
        # Generality score - kod qancha umumiy
        if generality_score < 0.3 and is_main_promotion:
            warnings.append(f"Generality score past: {generality_score}")
        
        decision = PolicyDecision.DENY if violations else (PolicyDecision.WARN if warnings else PolicyDecision.ALLOW)
        result = PolicyCheckResult(decision=decision, violations=violations, warnings=warnings)
        self._log_check("CK_011", result)
        
        return result
    
    # =============================================
    # QONUN 12: Constitution himoyalangan
    # =============================================
    
    def ensure_constitution_protected(self, target_path: str) -> PolicyCheckResult:
        """
        Qonun 12 ni tekshirish: Constitution fayllarini himoyalash.
        """
        violations = []
        
        # Protected zones
        protected_patterns = [
            "constitution/constitution_rules.py",
            "constitution/rule_classes.py",
            "constitution/policy_guard.py",
            "constitution/protected_zone_registry.py",
            "constitution/constitution_profiles.py",
            "constitution/constitution_change_protocol.py",
            "constitution/constitutional_audit.py",
        ]
        
        is_protected = any(pattern in target_path for pattern in protected_patterns)
        
        if is_protected:
            violations.append(PolicyViolation(
                rule_id="CK_012",
                rule_name="Constitution himoyalangan",
                severity=ViolationSeverity.BLOCKING,
                message=f"Protected zone'ga kirishga urunish: {target_path}",
                context={"target_path": target_path}
            ))
        
        decision = PolicyDecision.DENY if violations else PolicyDecision.ALLOW
        result = PolicyCheckResult(decision=decision, violations=violations)
        self._log_check("CK_012", result)
        
        return result
    
    # =============================================
    # YORDAMCHI METODLAR
    # =============================================
    
    def _log_check(self, rule_id: str, result: PolicyCheckResult):
        """Tekshiruvni log qilish"""
        self.audit_log.append({
            "timestamp": datetime.now().isoformat(),
            "rule_id": rule_id,
            "decision": result.decision.value,
            "violations": len(result.violations),
            "warnings": len(result.warnings),
            "metadata": result.metadata
        })
        
        if result.violations:
            self.violation_history.extend(result.violations)
    
    def get_violation_history(self) -> List[PolicyViolation]:
        """Buzulishlar tarixini olish"""
        return self.violation_history.copy()
    
    def get_audit_log(self) -> List[Dict[str, Any]]:
        """Audit log ni olish"""
        return self.audit_log.copy()
    
    def check_all_rules(
        self,
        change_set: Optional[ChangeSet] = None,
        evaluation_bundle: Optional[EvaluationBundle] = None,
        rollback_anchor: Optional[RollbackAnchor] = None,
        decision_record: Optional[DecisionRecord] = None,
        permission_scope: Optional[PermissionScope] = None,
        destination: str = "",
        is_main_promotion: bool = False,
    ) -> PolicyCheckResult:
        """
        Barcha qonunlarni birga tekshirish.
        Bu metod promotion yoki clone request uchun to'liq tekshiruv o'tkazadi.
        """
        all_violations = []
        all_warnings = []
        
        # Qonun 1: Clone only
        # (alohida tekshiriladi)
        
        # Qonun 2: ChangeSet
        if change_set:
            result = self.ensure_change_set_complete(change_set)
            all_violations.extend(result.violations)
            all_warnings.extend(result.warnings)
        
        # Qonun 3: Evidence
        if evaluation_bundle:
            result = self.ensure_evidence_present(evaluation_bundle)
            all_violations.extend(result.violations)
            all_warnings.extend(result.warnings)
        
        # Qonun 4: Rollback
        if rollback_anchor:
            result = self.ensure_rollback_ready(rollback_anchor, is_main_promotion)
            all_violations.extend(result.violations)
            all_warnings.extend(result.warnings)
        
        # Qonun 5: Human decision
        if destination:
            result = self.ensure_human_decision(decision_record, destination)
            all_violations.extend(result.violations)
            all_warnings.extend(result.warnings)
        
        # Qonun 6: Permission scope
        if permission_scope:
            result = self.ensure_scoped_permissions(permission_scope)
            all_violations.extend(result.violations)
            all_warnings.extend(result.warnings)
        
        # Qonun 8: Negative sections
        if evaluation_bundle:
            result = self.ensure_negative_sections(
                gains=evaluation_bundle.baseline_comparison.get("gains"),
                regressions=evaluation_bundle.regressions,
                risks=evaluation_bundle.validation_artifacts.get("risks"),
                unknowns=evaluation_bundle.validation_artifacts.get("unknowns")
            )
            all_violations.extend(result.violations)
            all_warnings.extend(result.warnings)
        
        # Final decision
        has_blocking = any(v.severity == ViolationSeverity.BLOCKING for v in all_violations)
        
        if has_blocking:
            decision = PolicyDecision.DENY
        elif all_warnings:
            decision = PolicyDecision.WARN
        else:
            decision = PolicyDecision.ALLOW
        
        return PolicyCheckResult(
            decision=decision,
            violations=all_violations,
            warnings=all_warnings
        )


def create_policy_guard(profile: ConstitutionProfile = ConstitutionProfile.LAB) -> PolicyGuard:
    """PolicyGuard yaratish (factory function)"""
    return PolicyGuard(profile=profile)


# =============================================
# TEKSHIRUV FUNKTSIYALARI
# =============================================#

def ensure_clone_only_mutation(
    destination: str,
    current_workspace: str,
    profile: ConstitutionProfile = ConstitutionProfile.LAB
) -> PolicyCheckResult:
    """Qonun 1 tekshiruvi"""
    guard = create_policy_guard(profile)
    return guard.ensure_clone_only_mutation(destination, current_workspace)


def ensure_change_set_complete(
    change_set: ChangeSet,
    profile: ConstitutionProfile = ConstitutionProfile.LAB
) -> PolicyCheckResult:
    """Qonun 2 tekshiruvi"""
    guard = create_policy_guard(profile)
    return guard.ensure_change_set_complete(change_set)


def ensure_evidence_present(
    bundle: EvaluationBundle,
    profile: ConstitutionProfile = ConstitutionProfile.LAB
) -> PolicyCheckResult:
    """Qonun 3 tekshiruvi"""
    guard = create_policy_guard(profile)
    return guard.ensure_evidence_present(bundle)


def ensure_rollback_ready(
    anchor: RollbackAnchor,
    is_main_promotion: bool = False,
    profile: ConstitutionProfile = ConstitutionProfile.LAB
) -> PolicyCheckResult:
    """Qonun 4 tekshiruvi"""
    guard = create_policy_guard(profile)
    return guard.ensure_rollback_ready(anchor, is_main_promotion)


def ensure_human_decision(
    decision: DecisionRecord,
    destination: str,
    profile: ConstitutionProfile = ConstitutionProfile.LAB
) -> PolicyCheckResult:
    """Qonun 5 tekshiruvi"""
    guard = create_policy_guard(profile)
    return guard.ensure_human_decision(decision, destination)


def ensure_scoped_permissions(
    scope: PermissionScope,
    profile: ConstitutionProfile = ConstitutionProfile.LAB
) -> PolicyCheckResult:
    """Qonun 6 tekshiruvi"""
    guard = create_policy_guard(profile)
    return guard.ensure_scoped_permissions(scope)


def ensure_constitution_protected(
    target_path: str,
    profile: ConstitutionProfile = ConstitutionProfile.LAB
) -> PolicyCheckResult:
    """Qonun 12 tekshiruvi"""
    guard = create_policy_guard(profile)
    return guard.ensure_constitution_protected(target_path)
