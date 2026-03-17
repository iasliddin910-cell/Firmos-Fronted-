"""
================================================================================
UNIFIED MASTER ARCHITECTURE / ORCHESTRATION LAYER
================================================================================
Bu barcha 4 ta bo'limni bitta platformaga birlashtiradi.

Bu "operating system" - butun self-evolution tizimining bosh miyasi.

7 ta asosiy qatlam:
1. Intake Layer - Signal kirish
2. Reasoning + Prioritization Layer - Tahlil va prioritet
3. Candidate Lifecycle Layer - Candidate hayot sikli
4. Execution Layer - Amaliy ish
5. Governance Layer - Boshqaruv
6. Promotion Layer - Promotion
7. Memory + Evolution Layer - Xotira va evolyutsiya

Bosh miya: Central Orchestrator

Asosiy prinsip:
"Every upgrade must have a destination policy"
"Original is immutable without approval"
"No upgrade without evidence"
================================================================================
"""
import os
import json
import logging
import time
import uuid
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict
from enum import Enum

logger = logging.getLogger(__name__)


# ================================================================================
# ENUMS
# ================================================================================

class SignalSource(Enum):
    """Signal source types"""
    BENCHMARK = "benchmark"
    USER_FEEDBACK = "user_feedback"
    REGRESSION = "regression"
    RESEARCH = "research"
    COMPETITOR = "competitor"
    SOCIAL = "social"
    OBSERVATION = "observation"
    MANUAL = "manual"


class SignalType(Enum):
    """Signal types"""
    OBSERVATION = "observation"
    ISSUE = "issue"
    OPPORTUNITY = "opportunity"
    ALERT = "alert"


class SignalStatus(Enum):
    """Signal status"""
    NEW = "new"
    TRIAGED = "triaged"
    WATCHLIST = "watchlist"
    REJECTED = "rejected"
    CANDIDATE_CREATED = "candidate_created"


class CandidateStatus(Enum):
    """Candidate status"""
    OBSERVED = "observed"
    TRIAGED = "triaged"
    CREATED = "candidate_created"
    QUEUED = "queued"
    CLONE_ALLOCATED = "clone_allocated"
    IN_MODIFICATION = "in_modification"
    LOCAL_VALIDATION = "local_validation"
    FULL_EVALUATION = "full_evaluation"
    REPORT_READY = "report_ready"
    AWAITING_DECISION = "awaiting_decision"
    APPROVED = "approved"
    PROMOTED = "promoted"
    FORKED = "forked"
    ARCHIVED = "archived"
    REJECTED = "rejected"
    ROLLED_BACK = "rolled_back"


# ================================================================================
# DATA CLASSES
# ================================================================================

@dataclass
class Observation:
    """Observation - tashqi dunyodan kelgan signal"""
    obs_id: str
    source: SignalSource
    timestamp: float = field(default_factory=time.time)
    summary: str = ""
    evidence: Dict = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    confidence: float = 0.5
    novelty: float = 0.5
    signal_type: SignalType = SignalType.OBSERVATION
    status: SignalStatus = SignalStatus.NEW
    
    def to_dict(self) -> Dict:
        return {
            "obs_id": self.obs_id,
            "source": self.source.value,
            "timestamp": self.timestamp,
            "summary": self.summary,
            "evidence": self.evidence,
            "tags": self.tags,
            "confidence": self.confidence,
            "novelty": self.novelty,
            "signal_type": self.signal_type.value,
            "status": self.status.value
        }


@dataclass
class UpgradeCandidate:
    """Upgrade Candidate - tasdiqlangan upgrade g'oyasi"""
    candidate_id: str
    title: str
    why_now: str
    linked_observations: List[str] = field(default_factory=list)
    capability_targets: List[str] = field(default_factory=list)
    estimated_risk: str = "medium"
    estimated_roi: float = 0.5
    implementation_type: str = "improvement"
    eval_plan: str = ""
    rollback_complexity: str = "medium"
    status: CandidateStatus = CandidateStatus.CREATED
    created_at: float = field(default_factory=time.time)
    priority: int = 0
    
    def to_dict(self) -> Dict:
        return {
            "candidate_id": self.candidate_id,
            "title": self.title,
            "why_now": self.why_now,
            "linked_observations": self.linked_observations,
            "capability_targets": self.capability_targets,
            "estimated_risk": self.estimated_risk,
            "estimated_roi": self.estimated_roi,
            "implementation_type": self.implementation_type,
            "status": self.status.value,
            "created_at": self.created_at,
            "priority": self.priority
        }


@dataclass
class SystemState:
    """Global tizim holati"""
    active_clones: int = 0
    pending_candidates: int = 0
    awaiting_decisions: int = 0
    active_canaries: int = 0
    active_forks: int = 0
    current_risk_budget: float = 1.0
    compute_budget_used: float = 0.0
    
    def to_dict(self) -> Dict:
        return {
            "active_clones": self.active_clones,
            "pending_candidates": self.pending_candidates,
            "awaiting_decisions": self.awaiting_decisions,
            "active_canaries": self.active_canaries,
            "active_forks": self.active_forks,
            "current_risk_budget": self.current_risk_budget,
            "compute_budget_used": self.compute_budget_used
        }


# ================================================================================
# INTAKE LAYER
# ================================================================================

class IntakeLayer:
    """
    Intake Layer - Signal kirish nuqtasi
    
    Bu yerga quyidagilar keladi:
    - external observations
    - benchmark failures
    - user feedback
    - regression alerts
    - new tool opportunities
    """
    
    def __init__(self):
        self.observations: Dict[str, Observation] = {}
        self.observation_queue: List[str] = []
        
        logger.info("📥 Intake Layer initialized")
    
    def ingest_signal(self,
                     source: SignalSource,
                     summary: str,
                     evidence: Dict = None,
                     tags: List[str] = None) -> Observation:
        """Signal ni qabul qilish"""
        obs_id = f"obs_{uuid.uuid4().hex[:12]}"
        
        obs = Observation(
            obs_id=obs_id,
            source=source,
            summary=summary,
            evidence=evidence or {},
            tags=tags or []
        )
        
        self.observations[obs_id] = obs
        self.observation_queue.append(obs_id)
        
        logger.info(f"📥 Signal ingested: {obs_id} from {source.value}")
        
        return obs
    
    def get_observation(self, obs_id: str) -> Optional[Observation]:
        return self.observations.get(obs_id)
    
    def get_pending_observations(self) -> List[Observation]:
        return [self.observations[oid] for oid in self.observation_queue]


# ================================================================================
# REASONING + PRIORITIZATION LAYER
# ================================================================================

class ReasoningLayer:
    """
    Reasoning + Prioritization Layer
    
    Signal scoring va triage
    """
    
    def __init__(self, intake: IntakeLayer):
        self.intake = intake
        self.watchlist: List[str] = []
        self.rejected: List[str] = []
        
        logger.info("🧠 Reasoning Layer initialized")
    
    def triage_signal(self, obs_id: str) -> SignalStatus:
        """Signal ni triage qilish"""
        obs = self.intake.get_observation(obs_id)
        if not obs:
            return SignalStatus.REJECTED
        
        # Simple scoring
        score = obs.confidence * 0.4 + obs.novelty * 0.3
        
        # Determine status
        if score < 0.3:
            status = SignalStatus.REJECTED
            self.rejected.append(obs_id)
        elif score < 0.6:
            status = SignalStatus.WATCHLIST
            self.watchlist.append(obs_id)
        else:
            status = SignalStatus.TRIAGED
        
        obs.status = status
        logger.info(f"🧠 Signal {obs_id} triaged: {status.value} (score: {score:.2f})")
        
        return status
    
    def should_create_candidate(self, obs_id: str) -> bool:
        """Candidate yaratish kerakmi?"""
        obs = self.intake.get_observation(obs_id)
        
        if not obs:
            return False
        
        # High confidence + novelty = candidate
        return obs.confidence > 0.7 and obs.novelty > 0.5


# ================================================================================
# CANDIDATE LIFECYCLE MANAGER
# ================================================================================

class CandidateLifecycleManager:
    """
    Candidate Lifecycle Manager
    
    Candidate hayot siklini boshqaradi:
    - observed
    - triaged
    - candidate_created
    - queued
    - clone_allocated
    - in_modification
    - local_validation
    - full_evaluation
    - report_ready
    - awaiting_human_decision
    - approved_for_destination
    - promoted
    - forked
    - archived
    - rejected
    - rolled_back
    """
    
    def __init__(self):
        self.candidates: Dict[str, UpgradeCandidate] = {}
        self.queue: List[str] = []
        
        logger.info("🔄 Candidate Lifecycle Manager initialized")
    
    def create_candidate(self,
                       title: str,
                       why_now: str,
                       linked_obs: List[str] = None) -> UpgradeCandidate:
        """Candidate yaratish"""
        candidate_id = f"candidate_{uuid.uuid4().hex[:12]}"
        
        candidate = UpgradeCandidate(
            candidate_id=candidate_id,
            title=title,
            why_now=why_now,
            linked_observations=linked_obs or []
        )
        
        self.candidates[candidate_id] = candidate
        self.queue.append(candidate_id)
        
        logger.info(f"🔄 Candidate created: {candidate_id}")
        
        return candidate
    
    def get_next_candidate(self) -> Optional[UpgradeCandidate]:
        """Keyingi candidate olish"""
        if not self.queue:
            return None
        
        candidate_id = self.queue[0]
        return self.candidates.get(candidate_id)
    
    def update_status(self, candidate_id: str, status: CandidateStatus):
        """Status yangilash"""
        if candidate_id in self.candidates:
            self.candidates[candidate_id].status = status
            logger.info(f"🔄 Candidate {candidate_id} status: {status.value}")
    
    def get_candidates_by_status(self, status: CandidateStatus) -> List[UpgradeCandidate]:
        return [c for c in self.candidates.values() if c.status == status]


# ================================================================================
# CENTRAL ORCHESTRATOR
# ================================================================================

class CentralOrchestrator:
    """
    Central Orchestrator - Bosh miya
    
    Bu bitta bosh tizim va u:
    - qaysi signalga javob berishni tanlaydi
    - qaysi candidate'ni birinchi ishlashni tanlaydi
    - qachon clone yaratishni hal qiladi
    - parallel ishlarni boshqaradi
    - conflictlarni to'xtatadi
    - risk budgetni kuzatadi
    - human approvalsiz hech narsani main'ga o'tkazmaydi
    """
    
    def __init__(self, workspace_root: str):
        self.workspace_root = workspace_root
        
        # Layers
        self.intake = IntakeLayer()
        self.reasoning = ReasoningLayer(self.intake)
        self.lifecycle = CandidateLifecycleManager()
        
        # System state
        self.system_state = SystemState()
        
        # Connected systems (will be set later)
        self.clone_system = None
        self.reporting_system = None
        self.promotion_system = None
        
        # Memory
        self.research_memory: List[Dict] = []
        self.lineage_history: List[Dict] = []
        
        logger.info("🎯 Central Orchestrator initialized")
    
    def connect_systems(self, clone_system, reporting_system, promotion_system):
        """Boshqa sistemalarni ulash"""
        self.clone_system = clone_system
        self.reporting_system = reporting_system
        self.promotion_system = promotion_system
        logger.info("🔗 Systems connected to orchestrator")
    
    # ============ STEP 1: Observation ============
    
    def ingest_observation(self,
                         source: SignalSource,
                         summary: str,
                         evidence: Dict = None,
                         tags: List[str] = None) -> str:
        """Observation ni kiritish"""
        obs = self.intake.ingest_signal(source, summary, evidence, tags)
        return obs.obs_id
    
    # ============ STEP 2: Triage ============
    
    def process_observations(self):
        """Observationslarni process qilish"""
        pending = self.intake.get_pending_observations()
        
        for obs in pending:
            # Triage
            self.reasoning.triage_signal(obs.obs_id)
            
            # Check if should create candidate
            if self.reasoning.should_create_candidate(obs.obs_id):
                self.create_candidate_from_observation(obs)
    
    def create_candidate_from_observation(self, obs: Observation) -> Optional[UpgradeCandidate]:
        """Observation dan candidate yaratish"""
        candidate = self.lifecycle.create_candidate(
            title=obs.summary,
            why_now=f"Signal from {obs.source.value}",
            linked_obs=[obs.obs_id]
        )
        
        # Update observation status
        obs.status = SignalStatus.CANDIDATE_CREATED
        
        return candidate
    
    # ============ STEP 3: Execution ============
    
    def execute_next_candidate(self) -> Dict:
        """Keyingi candidate ni execution qilish"""
        candidate = self.lifecycle.get_next_candidate()
        
        if not candidate:
            return {"status": "no_candidates"}
        
        if not self.clone_system:
            return {"status": "clone_system_not_connected"}
        
        try:
            # Move to executing
            self.lifecycle.update_status(
                candidate.candidate_id,
                CandidateStatus.CLONE_ALLOCATED
            )
            
            # Create clone
            from .clone_system import CloneType
            clone_meta = self.clone_system.create_clone(
                clone_type=CloneType.CAPABILITY,
                reason=candidate.title,
                candidate_id=candidate.candidate_id
            )
            
            # Update state
            self.system_state.active_clones += 1
            
            self.lifecycle.update_status(
                candidate.candidate_id,
                CandidateStatus.IN_MODIFICATION
            )
            
            return {
                "status": "executing",
                "candidate_id": candidate.candidate_id,
                "clone_id": clone_meta.clone_id
            }
            
        except Exception as e:
            logger.error(f"Execution failed: {e}")
            return {"status": "error", "error": str(e)}
    
    # ============ STEP 4: Governance ============
    
    def generate_dossier(self, clone_id: str) -> Dict:
        """Dossier yaratish"""
        if not self.reporting_system:
            return {"status": "reporting_system_not_connected"}
        
        try:
            dossier = self.reporting_system.generate_dossier(
                clone_id=clone_id,
                upgrade_title="Upgrade",
                why_attempted="Candidate improvement",
                clone_files={},
                original_files={}
            )
            
            self.lifecycle.update_status(
                self._find_candidate_by_clone(clone_id),
                CandidateStatus.REPORT_READY
            )
            
            return dossier.to_dict()
            
        except Exception as e:
            logger.error(f"Dossier generation failed: {e}")
            return {"status": "error", "error": str(e)}
    
    # ============ STEP 5: Promotion ============
    
    def promote_candidate(self, 
                       candidate_id: str,
                       destination: str) -> Dict:
        """Candidate promotion"""
        if not self.promotion_system:
            return {"status": "promotion_system_not_connected"}
        
        try:
            from .decision_engine import DestinationType
            
            dest_map = {
                "main": DestinationType.MAIN,
                "canary": DestinationType.CANARY,
                "experiment": DestinationType.ARCHIVE_EXPERIMENT,
                "fork": DestinationType.NEW_FORK,
                "reject": DestinationType.REJECT
            }
            
            destination_type = dest_map.get(destination, DestinationType.REJECT)
            
            result = self.promotion_system.execute_promotion(
                clone_id=candidate_id,
                destination=destination_type,
                dossier={},
                approver="system"
            )
            
            # Update candidate status
            status_map = {
                DestinationType.MAIN: CandidateStatus.PROMOTED,
                DestinationType.CANARY: CandidateStatus.PROMOTED,
                DestinationType.ARCHIVE_EXPERIMENT: CandidateStatus.ARCHIVED,
                DestinationType.NEW_FORK: CandidateStatus.FORKED,
                DestinationType.REJECT: CandidateStatus.REJECTED
            }
            
            self.lifecycle.update_status(
                candidate_id,
                status_map.get(destination_type, CandidateStatus.REJECTED)
            )
            
            # Update system state
            self.system_state.active_clones = max(0, self.system_state.active_clones - 1)
            
            return result
            
        except Exception as e:
            logger.error(f"Promotion failed: {e}")
            return {"status": "error", "error": str(e)}
    
    # ============ SYSTEM STATE ============
    
    def get_system_status(self) -> Dict:
        """Tizim holatini olish"""
        return {
            "system_state": self.system_state.to_dict(),
            "observations": len(self.intake.observations),
            "candidates": len(self.lifecycle.candidates),
            "queue": len(self.lifecycle.queue),
            "watchlist": len(self.reasoning.watchlist)
        }
    
    def _find_candidate_by_clone(self, clone_id: str) -> str:
        """Clone_id dan candidate topish"""
        # Simple lookup - would need proper mapping in real system
        return self.lifecycle.queue[0] if self.lifecycle.queue else ""


def create_orchestrator(workspace_root: str) -> CentralOrchestrator:
    """Orchestrator yaratish"""
    return CentralOrchestrator(workspace_root)
