"""
Change Planner Contracts
=======================
Core data structures for the planning system.

Defines:
- GoalSpec: User request → Technical goal
- EditContract: The formal patch specification
- EditPlan: Candidate execution plan
- ProofObligation: Pre-commit verification requirements
- RiskAssessment: Blast radius and risk analysis
- ChangeType: 6 types of changes
- PatchFamily: 5 transform engine families
- ChangePhase: 5-phase staged execution
"""

from enum import Enum
from typing import List, Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime


class ChangeType(str, Enum):
    """
    6 types of changes - each requires different strategy.
    
    FIXED: Complete type system for change classification.
    """
    MICRO_PATCH = "micro_patch"              # Small bugfix, logica correction
    LOCAL_STRUCTURAL = "local_structural"   # Multi-file pattern change
    SEMANTIC_REFACTOR = "semantic_refactor" # Typed rename, signature migration
    DEPENDENCY_MIGRATION = "dependency_migration"  # Library/API upgrade
    BEHAVIORAL_REWRITE = "behavioral_rewrite"  # Algorithm or flow change
    SPECIES_LEVEL = "species_level"          # Core behavior, self-edit


class PatchFamily(str, Enum):
    """
    5 patch families - each uses different transform engine.
    
    FIXED: Clear mapping to transform tools.
    """
    TEXT_DIFF = "text_diff"           # Simple text replacement
    STRUCTURAL_CODEMOD = "structural_codemod"  # Comby-style
    SEMANTIC_TYPED = "semantic_typed"  # OpenRewrite-style
    SEMANTIC_PATCH = "semantic_patch"  # Coccinelle-style
    SECURITY_GUARDED = "security_guarded"  # CodeQL-guarded


class ChangePhase(str, Enum):
    """
    5 phases of staged patching.
    
    FIXED: Ordered execution for safety.
    """
    PREPARATION = "preparation"    # Adapter, flag, compat layer
    CORE = "core"                  # Main behavior change
    PROPAGATION = "propagation"   # Call sites, imports, tests
    CLEANUP = "cleanup"           # Dead code, old adapters
    HARDENING = "hardening"        # Monitoring, asserts, fallback


class RiskLevel(str, Enum):
    """
    Risk levels for blast radius assessment.
    """
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NEGLIGIBLE = "negligible"


@dataclass
class GoalSpec:
    """
    User request → Technical goal conversion.
    
    This is the output of GoalCompiler.
    
    FIXED: Complete specification with all required fields.
    """
    # Core goal
    objective: str                    # What to achieve
    target_metric: Optional[str] = None  # e.g., "latency_p95 < 200ms"
    
    # Scope
    allowed_scope: Set[str] = field(default_factory=set)  # Files/modules allowed
    forbidden_scope: Set[str] = field(default_factory=set)  # Never touch these
    
    # Constraints
    max_patch_size: int = 1000        # Max lines changed
    rollback_class: str = "snapshot"  # How to rollback
    
    # Acceptance criteria
    acceptance_criteria: List[str] = field(default_factory=list)
    
    # Metadata
    goal_id: str = field(default_factory=lambda: f"goal_{datetime.now().timestamp()}")
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())
    
    def to_dict(self) -> Dict:
        """Serialize to dictionary."""
        return {
            'goal_id': self.goal_id,
            'objective': self.objective,
            'target_metric': self.target_metric,
            'allowed_scope': list(self.allowed_scope),
            'forbidden_scope': list(self.forbidden_scope),
            'max_patch_size': self.max_patch_size,
            'rollback_class': self.rollback_class,
            'acceptance_criteria': self.acceptance_criteria,
            'created_at': self.created_at
        }


@dataclass
class ConstraintSpec:
    """
    Extracted constraints from code understanding.
    
    This is the output of ConstraintMiner.
    """
    # Invariants that must be preserved
    invariants: List[str] = field(default_factory=list)
    
    # Red-zone modules (never touch without extra approval)
    red_zone_modules: Set[str] = field(default_factory=set)
    
    # Required tests
    required_tests: List[str] = field(default_factory=list)
    
    # Data flow risks
    data_flow_risks: List[str] = field(default_factory=list)
    
    # Dependency constraints
    dependency_constraints: Dict[str, Any] = field(default_factory=dict)
    
    # Migration constraints
    migration_constraints: List[str] = field(default_factory=list)
    
    # Security-sensitive symbols
    security_symbols: Set[str] = field(default_factory=set)
    
    # Hot paths (performance-critical)
    hot_paths: Set[str] = field(default_factory=set)
    
    def to_dict(self) -> Dict:
        """Serialize to dictionary."""
        return {
            'invariants': self.invariants,
            'red_zone_modules': list(self.red_zone_modules),
            'required_tests': self.required_tests,
            'data_flow_risks': self.data_flow_risks,
            'dependency_constraints': self.dependency_constraints,
            'migration_constraints': self.migration_constraints,
            'security_symbols': list(self.security_symbols),
            'hot_paths': list(self.hot_paths)
        }


@dataclass
class EditContract:
    """
    The formal patch specification.
    
    This is the PRIMARY output of the ChangePlanner.
    NO patch should be applied without an EditContract!
    
    FIXED: Complete contract with all required fields.
    """
    # Identity
    contract_id: str
    goal_id: str
    
    # Classification
    change_type: ChangeType
    patch_family: PatchFamily
    
    # Target
    target_symbols: Set[str] = field(default_factory=set)
    target_files: Set[str] = field(default_factory=set)
    forbidden_files: Set[str] = field(default_factory=set)
    
    # Constraints
    invariants_to_preserve: List[str] = field(default_factory=list)
    
    # Proof obligations
    proof_obligations: List['ProofObligation'] = field(default_factory=list)
    
    # Required verifications
    required_tests: List[str] = field(default_factory=list)
    required_static_checks: List[str] = field(default_factory=list)
    
    # Expected outcomes
    expected_metrics_delta: Dict[str, float] = field(default_factory=dict)
    
    # Rollback
    rollback_point: Optional[str] = None
    
    # Promotion policy
    promote_policy: str = "minimal_sufficient"  # minimal_sufficient, balanced, aggressive
    
    # Status
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())
    status: str = "draft"  # draft, planned, approved, executing, completed, failed
    
    def to_dict(self) -> Dict:
        """Serialize to dictionary."""
        return {
            'contract_id': self.contract_id,
            'goal_id': self.goal_id,
            'change_type': self.change_type.value,
            'patch_family': self.patch_family.value,
            'target_symbols': list(self.target_symbols),
            'target_files': list(self.target_files),
            'forbidden_files': list(self.forbidden_files),
            'invariants_to_preserve': self.invariants_to_preserve,
            'proof_obligations': [p.to_dict() for p in self.proof_obligations],
            'required_tests': self.required_tests,
            'required_static_checks': self.required_static_checks,
            'expected_metrics_delta': self.expected_metrics_delta,
            'rollback_point': self.rollback_point,
            'promote_policy': self.promote_policy,
            'created_at': self.created_at,
            'status': self.status
        }


@dataclass
class ProofObligation:
    """
    Pre-commit verification requirement.
    
    FIXED: Explicit proof before promotion.
    """
    # What to verify
    obligation_id: str
    description: str
    category: str  # test, static_check, symbol_resolution, runtime_replay, metric
    
    # Verification criteria
    verification_method: str  # test_suite, codeql_query, symbol_check, benchmark
    expected_result: Any
    
    # Criticality
    blocking: bool = True  # If false, can be deferred
    severity: str = "required"  # required, recommended, optional
    
    # Status
    passed: Optional[bool] = None
    evidence: Optional[Dict] = None
    
    def to_dict(self) -> Dict:
        """Serialize to dictionary."""
        return {
            'obligation_id': self.obligation_id,
            'description': self.description,
            'category': self.category,
            'verification_method': self.verification_method,
            'expected_result': str(self.expected_result),
            'blocking': self.blocking,
            'severity': self.severity,
            'passed': self.passed,
            'evidence': self.evidence
        }


@dataclass
class RiskAssessment:
    """
    Blast radius and risk analysis.
    
    FIXED: Comprehensive risk calculation.
    """
    # Risk level
    risk_level: RiskLevel
    
    # Blast radius metrics
    touched_symbols: Set[str] = field(default_factory=set)
    transitive_callers: Set[str] = field(default_factory=set)
    runtime_hot_paths: Set[str] = field(default_factory=set)
    red_zone_overlap: bool = False
    config_coupling: bool = False
    migration_impact: bool = False
    external_api_risk: bool = False
    browser_auth_risk: bool = False
    
    # Specific risks
    security_risks: List[str] = field(default_factory=list)
    stability_risks: List[str] = field(default_factory=list)
    performance_risks: List[str] = field(default_factory=list)
    
    # Reversibility
    reversible: bool = True
    rollback_difficulty: str = "easy"  # easy, medium, hard, impossible
    
    # Score (0-100)
    risk_score: float = 0.0
    
    def to_dict(self) -> Dict:
        """Serialize to dictionary."""
        return {
            'risk_level': self.risk_level.value,
            'touched_symbols': list(self.touched_symbols),
            'transitive_callers': list(self.transitive_callers),
            'runtime_hot_paths': list(self.runtime_hot_paths),
            'red_zone_overlap': self.red_zone_overlap,
            'config_coupling': self.config_coupling,
            'migration_impact': self.migration_impact,
            'external_api_risk': self.external_api_risk,
            'browser_auth_risk': self.browser_auth_risk,
            'security_risks': self.security_risks,
            'stability_risks': self.stability_risks,
            'performance_risks': self.performance_risks,
            'reversible': self.reversible,
            'rollback_difficulty': self.rollback_difficulty,
            'risk_score': self.risk_score
        }


@dataclass
class EditPlan:
    """
    Candidate execution plan.
    
    FIXED: Multi-plan generation with scoring.
    """
    # Identity
    plan_id: str
    contract_id: str
    
    # Plan type
    plan_type: str  # minimal, balanced, aggressive
    
    # Phased execution
    phases: List[ChangePhase] = field(default_factory=list)
    
    # Patch details per phase
    phase_patches: Dict[ChangePhase, Dict[str, Any]] = field(default_factory=dict)
    
    # Scoring
    semantic_certainty: float = 0.0  # How confident we are
    blast_radius: int = 0            # Files/symbols affected
    reversibility: float = 1.0       # 0-1, how easy to rollback
    expected_gain: float = 0.0       # Expected improvement
    validation_cost: float = 0.0     # Time/effort to validate
    
    # Total score (0-100)
    total_score: float = 0.0
    
    # Status
    status: str = "draft"  # draft, approved, executing, completed, failed
    
    # Metadata
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())
    
    def calculate_score(self) -> float:
        """Calculate total plan score."""
        # Higher certainty, lower radius, more reversible, more gain = better
        score = (
            self.semantic_certainty * 30 +
            (1 - self.blast_radius / 100) * 20 +
            self.reversibility * 20 +
            self.expected_gain * 20 -
            self.validation_cost * 10
        )
        self.total_score = max(0, min(100, score))
        return self.total_score
    
    def to_dict(self) -> Dict:
        """Serialize to dictionary."""
        return {
            'plan_id': self.plan_id,
            'contract_id': self.contract_id,
            'plan_type': self.plan_type,
            'phases': [p.value for p in self.phases],
            'phase_patches': {k.value: v for k, v in self.phase_patches.items()},
            'semantic_certainty': self.semantic_certainty,
            'blast_radius': self.blast_radius,
            'reversibility': self.reversibility,
            'expected_gain': self.expected_gain,
            'validation_cost': self.validation_cost,
            'total_score': self.total_score,
            'status': self.status,
            'created_at': self.created_at
        }


@dataclass
class PlannerMetrics:
    """
    Planner quality metrics.
    
    FIXED: Comprehensive KPI tracking.
    """
    # Success metrics
    plan_acceptance_rate: float = 0.0      # Plans approved
    patch_success_rate: float = 0.0        # Patches that worked
    reverted_patch_rate: float = 0.0       # Patches reverted
    proof_failure_rate: float = 0.0         # Proof obligations failed
    
    # Scope metrics
    over_scoped_rate: float = 0.0          # Changed too much
    under_scoped_rate: float = 0.0         # Changed too little
    
    # Efficiency metrics
    time_to_safe_patch: float = 0.0        # Seconds to safe patch
    gain_per_line_changed: float = 0.0      # Metric improvement per line
    
    # Certainty metrics
    semantic_certainty_avg: float = 0.0
    actual_outcome_match: float = 0.0      # How often predictions were correct
    
    def to_dict(self) -> Dict:
        """Serialize to dictionary."""
        return {
            'plan_acceptance_rate': self.plan_acceptance_rate,
            'patch_success_rate': self.patch_success_rate,
            'reverted_patch_rate': self.reverted_patch_rate,
            'proof_failure_rate': self.proof_failure_rate,
            'over_scoped_rate': self.over_scoped_rate,
            'under_scoped_rate': self.under_scoped_rate,
            'time_to_safe_patch': self.time_to_safe_patch,
            'gain_per_line_changed': self.gain_per_line_changed,
            'semantic_certainty_avg': self.semantic_certainty_avg,
            'actual_outcome_match': self.actual_outcome_match
        }
