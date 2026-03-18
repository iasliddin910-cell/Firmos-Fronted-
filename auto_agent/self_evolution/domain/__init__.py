"""
DOMAIN MODULE - Asosiy ma'lumotlar va enumlar
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict

# ENUMS
class CandidateStatus(Enum):
    OBSERVED = "observed"
    TRIAGED = "triaged"
    QUEUED = "queued"
    CLONE_ALLOCATED = "clone_allocated"
    IN_MODIFICATION = "in_modification"
    LOCAL_VALIDATION = "local_validation"
    FULL_EVALUATION = "full_evaluation"
    REPORT_READY = "report_ready"
    AWAITING_DECISION = "awaiting_decision"
    APPROVED = "approved"
    REJECTED = "rejected"
    ARCHIVED = "archived"
    PROMOTED = "promoted"
    FORKED = "forked"
    ROLLED_BACK = "rolled_back"

class CloneType(Enum):
    MICRO_PATCH = "micro_patch"
    CAPABILITY = "capability"
    WORKFLOW = "workflow"
    RESEARCH = "research"
    FORK_SEED = "fork_seed"

class CloneState(Enum):
    CREATING = "creating"
    RUNNING = "running"
    MODIFYING = "modifying"
    VALIDATING = "validating"
    EVALUATING = "evaluating"
    COMPLETED = "completed"
    FAILED = "failed"
    TERMINATED = "terminated"

class DecisionType(Enum):
    REJECT = "reject"
    REQUEST_REVISION = "request_revision"
    KEEP_EXPERIMENT = "keep_experiment"
    APPROVE_CANARY = "approve_canary"
    APPROVE_MAIN = "approve_main"
    CREATE_FORK = "create_fork"

class DestinationType(Enum):
    EXPERIMENT = "experiment"
    CANARY = "canary"
    MAIN = "main"
    SPECIALIZED_BRANCH = "specialized_branch"
    NEW_MODEL = "new_model"
    ARCHIVE = "archive"

class SignalType(Enum):
    EXTERNAL = "external"
    BENCHMARK_FAILURE = "benchmark_failure"
    USER_FEEDBACK = "user_feedback"
    REGRESSION = "regression"
    COMPETITOR = "competitor"
    SOCIAL = "social"
    RESEARCH = "research"

class RiskLevel(Enum):
    MINIMAL = "minimal"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

# MODELS
@dataclass
class Observation:
    id: str
    source_type: str
    source_name: str
    created_at: datetime
    summary: str
    raw_refs: Dict = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    credibility: float = 0.5
    novelty: float = 0.5
    relevance: float = 0.5

@dataclass
class UpgradeCandidate:
    id: str
    title: str
    why_now: str
    source_obs: List[str] = field(default_factory=list)
    capabilities: List[str] = field(default_factory=list)
    impl_type: str = "incremental"
    risk: RiskLevel = RiskLevel.MEDIUM
    roi: float = 0.5
    blast_radius: str = "medium"
    status: CandidateStatus = CandidateStatus.OBSERVED
    created_at: datetime = field(default_factory=datetime.now)

@dataclass
class CloneSpec:
    clone_type: CloneType
    parent_version: str
    candidate_id: str
    workspace_mode: str = "isolated"

@dataclass
class CloneRun:
    clone_id: str
    spec: CloneSpec
    state: CloneState
    workspace_path: str
    touched_files: List[str] = field(default_factory=list)
    started_at: datetime = field(default_factory=datetime.now)

@dataclass
class ChangeSet:
    change_id: str
    clone_id: str
    intent: str
    why: str
    files: List[str] = field(default_factory=list)
    revert: str = ""

@dataclass
class ValidationResult:
    clone_id: str
    passed: bool = False
    syntax_ok: bool = False
    imports_ok: bool = False
    failures: List[str] = field(default_factory=list)

@dataclass
class EvaluationBundle:
    clone_id: str
    benchmarks: Dict = field(default_factory=dict)
    replays: Dict = field(default_factory=dict)
    trust_score: float = 0.0

@dataclass
class UpgradeDossier:
    candidate_id: str
    clone_id: str
    summary: str = ""
    capability_delta: Dict = field(default_factory=dict)
    risk_summary: str = ""
    recommendation: str = ""

@dataclass
class DecisionRecord:
    candidate_id: str
    clone_id: str
    decision: DecisionType
    reason: str = ""
    by: str = "human"
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class PromotionRecord:
    promo_id: str
    clone_id: str
    destination: DestinationType
    from_ver: str
    to_ver: str

__all__ = ["CandidateStatus", "CloneType", "CloneState", "DecisionType", "DestinationType", "SignalType", "RiskLevel", "Observation", "UpgradeCandidate", "CloneSpec", "CloneRun", "ChangeSet", "ValidationResult", "EvaluationBundle", "UpgradeDossier", "DecisionRecord", "PromotionRecord"]
