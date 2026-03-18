"""
Unified Master Architecture - Data Contracts
==============================================
Bu fayl barcha data contracts larni o'z ichiga oladi.
Modullar orasidagi aloqa shu contractlar bo'yicha amalga oshadi.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class SignalType(Enum):
    """Signal turlari"""
    EXTERNAL_OBSERVATION = "external_observation"
    BENCHMARK_FAILURE = "benchmark_failure"
    USER_FEEDBACK = "user_feedback"
    REGRESSION_ALERT = "regression_alert"
    NEW_TOOL_OPPORTUNITY = "new_tool_opportunity"
    COMPETITOR_CAPABILITY = "competitor_capability"
    SOCIAL_PAIN = "social_pain"
    RESEARCH_CONCLUSION = "research_conclusion"


class SignalSource(Enum):
    """Signal manbalari"""
    BENCHMARK = "benchmark"
    USER = "user"
    OBSERVATION = "observation"
    REGRESSION = "regression"
    COMPETITOR = "competitor"
    SOCIAL = "social"
    RESEARCH = "research"
    INTERNAL = "internal"


class CandidateState(Enum):
    """Candidate holatlari"""
    OBSERVED = "observed"
    TRIAGED = "triaged"
    CANDIDATE_CREATED = "candidate_created"
    QUEUED = "queued"
    CLONE_ALLOCATED = "clone_allocated"
    IN_MODIFICATION = "in_modification"
    LOCAL_VALIDATION = "local_validation"
    FULL_EVALUATION = "full_evaluation"
    REPORT_READY = "report_ready"
    AWAITING_HUMAN_DECISION = "awaiting_human_decision"
    APPROVED_FOR_DESTINATION = "approved_for_destination"
    PROMOTED = "promoted"
    FORKED = "forked"
    ARCHIVED = "archived"
    REJECTED = "rejected"
    ROLLED_BACK = "rolled_back"


class CloneState(Enum):
    """Clone holatlari"""
    CREATING = "creating"
    INITIALIZING = "initializing"
    RUNNING = "running"
    MODIFYING = "modifying"
    VALIDATING = "validating"
    EVALUATING = "evaluating"
    COMPLETED = "completed"
    FAILED = "failed"
    TERMINATED = "terminated"


class DestinationType(Enum):
    """Promotion yo'nalishlari"""
    MAIN = "main"
    CANARY = "canary"
    FORK = "fork"
    ARCHIVE = "archive"
    EXPERIMENT = "experiment"


class ApprovalDecision(Enum):
    """Qaror turlari"""
    APPROVED = "approved"
    REJECTED = "rejected"
    REVISE = "revise"
    KEEP_AS_EXPERIMENT = "keep_as_experiment"
    CANARY = "canary"


class RiskLevel(Enum):
    """Xavf darajalari"""
    MINIMAL = "minimal"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Observation:
    """
    Tashqi dunyodan kelgan signal/kuzatuv
    """
    id: str
    source: SignalSource
    timestamp: datetime
    summary: str
    evidence: dict = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    confidence: float = 0.5
    novelty: float = 0.5
    signal_type: SignalType = SignalType.EXTERNAL_OBSERVATION
    
    # Triage natijalari
    triage_result: Optional[str] = None
    credibility_score: Optional[float] = None
    roi_score: Optional[float] = None
    
    # Vaqt o'tishi bilan ma'lumotlar
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    
    def to_dict(self) -> dict:
        """Dictionary ga aylantirish"""
        return {
            "id": self.id,
            "source": self.source.value,
            "timestamp": self.timestamp.isoformat(),
            "summary": self.summary,
            "evidence": self.evidence,
            "tags": self.tags,
            "confidence": self.confidence,
            "novelty": self.novelty,
            "signal_type": self.signal_type.value,
            "triage_result": self.triage_result,
            "credibility_score": self.credibility_score,
            "roi_score": self.roi_score,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None
        }


@dataclass
class UpgradeCandidate:
    """
    Upgrade candidate - upgrade qilish uchun nomzod
    """
    id: str
    title: str
    why_now: str
    linked_observations: list[str] = field(default_factory=list)
    capability_targets: list[str] = field(default_factory=list)
    estimated_risk: RiskLevel = RiskLevel.MEDIUM
    estimated_roi: float = 0.5
    implementation_type: str = "incremental"
    eval_plan: dict = field(default_factory=dict)
    rollback_complexity: str = "medium"
    
    # Holat
    state: CandidateState = CandidateState.CANDIDATE_CREATED
    priority: int = 0
    
    # Vaqt
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    # Baholash natijalari
    credibility: Optional[float] = None
    usefulness: Optional[float] = None
    urgency: Optional[float] = None
    
    # Implementatsiya
    implementation_notes: str = ""
    target_modules: list[str] = field(default_factory=list)
    expected_outcomes: list[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        """Dictionary ga aylantirish"""
        return {
            "id": self.id,
            "title": self.title,
            "why_now": self.why_now,
            "linked_observations": self.linked_observations,
            "capability_targets": self.capability_targets,
            "estimated_risk": self.estimated_risk.value,
            "estimated_roi": self.estimated_roi,
            "implementation_type": self.implementation_type,
            "eval_plan": self.eval_plan,
            "rollback_complexity": self.rollback_complexity,
            "state": self.state.value,
            "priority": self.priority,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "credibility": self.credibility,
            "usefulness": self.usefulness,
            "urgency": self.urgency,
            "implementation_notes": self.implementation_notes,
            "target_modules": self.target_modules,
            "expected_outcomes": self.expected_outcomes
        }


@dataclass
class CloneRun:
    """
    Clone running - clone ustida ishlash
    """
    clone_id: str
    parent_version: str
    candidate_id: str
    
    # Runtime
    runtime_profile: dict = field(default_factory=dict)
    resource_budget: dict = field(default_factory=dict)
    state: CloneState = CloneState.CREATING
    
    # Natijalar
    artifacts: dict = field(default_factory=dict)
    touched_modules: list[str] = field(default_factory=list)
    added_tools: list[str] = field(default_factory=list)
    validation_status: dict = field(default_factory=dict)
    
    # Vaqt
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Xatolar
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    
    # Self-model
    self_model_graph: dict = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        """Dictionary ga aylantirish"""
        return {
            "clone_id": self.clone_id,
            "parent_version": self.parent_version,
            "candidate_id": self.candidate_id,
            "runtime_profile": self.runtime_profile,
            "resource_budget": self.resource_budget,
            "state": self.state.value,
            "artifacts": self.artifacts,
            "touched_modules": self.touched_modules,
            "added_tools": self.added_tools,
            "validation_status": self.validation_status,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "errors": self.errors,
            "warnings": self.warnings,
            "self_model_graph": self.self_model_graph
        }


@dataclass
class EvaluationBundle:
    """
    Evaluation natijalar to'plami
    """
    id: str
    candidate_id: str
    clone_id: str
    
    # Natijalar
    benchmark_results: dict = field(default_factory=dict)
    replay_results: dict = field(default_factory=dict)
    behavior_deltas: dict = field(default_factory=dict)
    regressions: list[str] = field(default_factory=list)
    
    # Baho
    trust_score: float = 0.0
    overall_score: float = 0.0
    
    # Isbotlar
    evidence_index: dict = field(default_factory=dict)
    
    # Vaqt
    created_at: datetime = field(default_factory=datetime.now)
    duration_seconds: float = 0.0
    
    def to_dict(self) -> dict:
        """Dictionary ga aylantirish"""
        return {
            "id": self.id,
            "candidate_id": self.candidate_id,
            "clone_id": self.clone_id,
            "benchmark_results": self.benchmark_results,
            "replay_results": self.replay_results,
            "behavior_deltas": self.behavior_deltas,
            "regressions": self.regressions,
            "trust_score": self.trust_score,
            "overall_score": self.overall_score,
            "evidence_index": self.evidence_index,
            "created_at": self.created_at.isoformat(),
            "duration_seconds": self.duration_seconds
        }


@dataclass
class UpgradeDossier:
    """
    Upgrade hisoboti - human decision uchun
    """
    id: str
    candidate_id: str
    clone_id: str
    
    # Xulosa
    executive_summary: str
    capability_delta: dict = field(default_factory=dict)
    technical_delta: dict = field(default_factory=dict)
    
    # Risk
    risks: list[dict] = field(default_factory=list)
    risk_summary: str = ""
    
    # Regressiyalar
    regressions: list[dict] = field(default_factory=list)
    unknown_items: list[dict] = field(default_factory=list)
    
    # Tavsiya
    recommendation: str = ""
    decision_options: list[str] = field(default_factory=list)
    
    # Rollback
    rollback_plan: str = ""
    rollback_readiness: str = "ready"
    
    # Baho
    trust_score: float = 0.0
    
    # Evaluation
    evaluation_bundle_id: Optional[str] = None
    
    # Vaqt
    created_at: datetime = field(default_factory=datetime.now)
    created_by: str = "system"
    
    def to_dict(self) -> dict:
        """Dictionary ga aylantirish"""
        return {
            "id": self.id,
            "candidate_id": self.candidate_id,
            "clone_id": self.clone_id,
            "executive_summary": self.executive_summary,
            "capability_delta": self.capability_delta,
            "technical_delta": self.technical_delta,
            "risks": self.risks,
            "risk_summary": self.risk_summary,
            "regressions": self.regressions,
            "unknown_items": self.unknown_items,
            "recommendation": self.recommendation,
            "decision_options": self.decision_options,
            "rollback_plan": self.rollback_plan,
            "rollback_readiness": self.rollback_readiness,
            "trust_score": self.trust_score,
            "evaluation_bundle_id": self.evaluation_bundle_id,
            "created_at": self.created_at.isoformat(),
            "created_by": self.created_by
        }


@dataclass
class PromotionRecord:
    """
    Promotion yozuvi
    """
    id: str
    destination: DestinationType
    approved_by: str
    promoted_from: str
    promoted_to: str
    
    # Artifact
    artifacts_hash: str = ""
    
    # Rollback
    rollback_anchor: Optional[str] = None
    
    # Lineage
    lineage_update: dict = field(default_factory=dict)
    
    # Vaqt
    promoted_at: datetime = field(default_factory=datetime.now)
    
    # Qo'shimcha
    notes: str = ""
    promotion_type: str = "standard"
    
    def to_dict(self) -> dict:
        """Dictionary ga aylantirish"""
        return {
            "id": self.id,
            "destination": self.destination.value,
            "approved_by": self.approved_by,
            "promoted_from": self.promoted_from,
            "promoted_to": self.promoted_to,
            "artifacts_hash": self.artifacts_hash,
            "rollback_anchor": self.rollback_anchor,
            "lineage_update": self.lineage_update,
            "promoted_at": self.promoted_at.isoformat(),
            "notes": self.notes,
            "promotion_type": self.promotion_type
        }


@dataclass
class SystemState:
    """
    Tizim holati - Global haqiqatlar
    """
    # Clone holatlari
    active_clones_count: int = 0
    clone_limit: int = 10
    
    # Candidate holatlari
    pending_candidates_count: int = 0
    awaiting_decision_count: int = 0
    
    # Canary/Fork
    active_canaries: int = 0
    active_forks: int = 0
    
    # Risk
    current_risk_budget: float = 1.0
    used_risk_budget: float = 0.0
    
    # Resources
    compute_budget: float = 1.0
    eval_budget: float = 1.0
    storage_used_gb: float = 0.0
    
    # Policy
    allowed_directions: list[str] = field(default_factory=lambda: ["main", "canary", "fork"])
    frozen_directions: list[str] = field(default_factory=list)
    main_gate_open: bool = True
    
    # Vaqt
    last_updated: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> dict:
        """Dictionary ga aylantirish"""
        return {
            "active_clones_count": self.active_clones_count,
            "clone_limit": self.clone_limit,
            "pending_candidates_count": self.pending_candidates_count,
            "awaiting_decision_count": self.awaiting_decision_count,
            "active_canaries": self.active_canaries,
            "active_forks": self.active_forks,
            "current_risk_budget": self.current_risk_budget,
            "used_risk_budget": self.used_risk_budget,
            "compute_budget": self.compute_budget,
            "eval_budget": self.eval_budget,
            "storage_used_gb": self.storage_used_gb,
            "allowed_directions": self.allowed_directions,
            "frozen_directions": self.frozen_directions,
            "main_gate_open": self.main_gate_open,
            "last_updated": self.last_updated.isoformat()
        }


@dataclass
class ApprovalRequest:
    """
    Approval so'rovnoma
    """
    id: str
    dossier_id: str
    candidate_id: str
    
    # Decision
    decision: Optional[ApprovalDecision] = None
    decision_reason: str = ""
    decided_by: str = ""
    decided_at: Optional[datetime] = None
    
    # Destination (if approved)
    destination: Optional[DestinationType] = None
    
    # Vaqt
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    
    def to_dict(self) -> dict:
        """Dictionary ga aylantirish"""
        return {
            "id": self.id,
            "dossier_id": self.dossier_id,
            "candidate_id": self.candidate_id,
            "decision": self.decision.value if self.decision else None,
            "decision_reason": self.decision_reason,
            "decided_by": self.decided_by,
            "decided_at": self.decided_at.isoformat() if self.decided_at else None,
            "destination": self.destination.value if self.destination else None,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None
        }
