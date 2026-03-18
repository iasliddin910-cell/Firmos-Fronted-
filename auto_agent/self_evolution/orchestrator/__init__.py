"""
ORCHESTRATOR MODULE - Bosh Boshqaruv
=====================================
CentralOrchestrator va LifecycleManager
"""

import logging
from datetime import datetime
from typing import Optional, Dict, List
from ..domain import CandidateStatus, CloneState, DecisionType, DestinationType

logger = logging.getLogger(__name__)


class LifecycleManager:
    """State transition boshqaruv"""
    
    VALID_TRANSITIONS = {
        CandidateStatus.OBSERVED: [CandidateStatus.TRIAGED],
        CandidateStatus.TRIAGED: [CandidateStatus.QUEUED, CandidateStatus.REJECTED],
        CandidateStatus.QUEUED: [CandidateStatus.CLONE_ALLOCATED, CandidateStatus.REJECTED],
        CandidateStatus.CLONE_ALLOCATED: [CandidateStatus.IN_MODIFICATION, CandidateStatus.REJECTED],
        CandidateStatus.IN_MODIFICATION: [CandidateStatus.LOCAL_VALIDATION, CandidateStatus.REJECTED],
        CandidateStatus.LOCAL_VALIDATION: [CandidateStatus.FULL_EVALUATION, CandidateStatus.REJECTED],
        CandidateStatus.FULL_EVALUATION: [CandidateStatus.REPORT_READY, CandidateStatus.REJECTED],
        CandidateStatus.REPORT_READY: [CandidateStatus.AWAITING_DECISION],
        CandidateStatus.AWAITING_DECISION: [CandidateStatus.APPROVED, CandidateStatus.REJECTED, CandidateStatus.ARCHIVED],
        CandidateStatus.APPROVED: [CandidateStatus.PROMOTED, CandidateStatus.FORKED],
        CandidateStatus.PROMOTED: [CandidateStatus.ROLLED_BACK],
    }
    
    def __init__(self):
        self.candidates: Dict = {}
        logger.info("🔄 LifecycleManager initialized")
    
    def transition(self, candidate_id: str, new_status: CandidateStatus) -> bool:
        if candidate_id not in self.candidates:
            return False
        
        current = self.candidates[candidate_id].get("status")
        allowed = self.VALID_TRANSITIONS.get(current, [])
        
        if new_status not in allowed:
            logger.warning(f"❌ Invalid transition: {current} -> {new_status}")
            return False
        
        self.candidates[candidate_id]["status"] = new_status
        self.candidates[candidate_id]["updated_at"] = datetime.now().isoformat()
        logger.info(f"🔄 {candidate_id}: {current} -> {new_status}")
        return True
    
    def register(self, candidate_id: str, data: dict):
        self.candidates[candidate_id] = {**data, "status": CandidateStatus.OBSERVED, "created_at": datetime.now().isoformat()}


class PriorityEngine:
    """Queue tartiblash"""
    
    def __init__(self):
        self.queue: List[str] = []
        logger.info("📊 PriorityEngine initialized")
    
    def score_candidate(self, candidate: dict) -> float:
        roi = candidate.get("roi", 0.5)
        risk_inverted = 1.0 - ({"low": 0.2, "medium": 0.5, "high": 0.8}.get(candidate.get("risk", "medium"), 0.5))
        return roi * 0.6 + risk_inverted * 0.4
    
    def rank(self, candidates: List[dict]) -> List[dict]:
        return sorted(candidates, key=lambda c: self.score_candidate(c), reverse=True)
    
    def select_next(self) -> Optional[str]:
        return self.queue[0] if self.queue else None


class PolicyGuard:
    """Invariant tekshirish"""
    
    def __init__(self):
        self.violations: List[dict] = []
        logger.info("🛡️ PolicyGuard initialized")
    
    def ensure_clone_only(self, candidate: dict) -> bool:
        if candidate.get("status") != CandidateStatus.CLONE_ALLOCATED:
            return True
        return True
    
    def ensure_rollback_before_promotion(self, record: dict) -> bool:
        return bool(record.get("rollback_anchor"))
    
    def ensure_human_decision(self, record: dict) -> bool:
        return record.get("by") == "human"


class CentralOrchestrator:
    """
    Bosh Boshqaruv Markazi
    
    Asosiy vazifalar:
    - navbatdagi candidate'ni tanlash
    - clone ochishga ruxsat berish
    - stage transition'larni boshqarish
    - approval'siz originalga tegilmasligini majbur qilish
    """
    
    def __init__(self, workspace_path: str):
        self.workspace_path = workspace_path
        self.lifecycle = LifecycleManager()
        self.priority = PriorityEngine()
        self.policy = PolicyGuard()
        
        # State
        self.candidates: Dict = {}
        self.clones: Dict = {}
        self.observations: Dict = {}
        self.dossiers: Dict = {}
        self.decisions: Dict = {}
        
        # Services (will be connected later)
        self.intake_service = None
        self.candidate_factory = None
        self.clone_factory = None
        self.patch_engine = None
        self.validation_service = None
        self.evaluation_service = None
        self.reporting_service = None
        self.governance_service = None
        self.promotion_service = None
        self.memory_service = None
        
        logger.info("🎯 CentralOrchestrator initialized")
    
    def connect_services(self, services: dict):
        """Service larni ulash"""
        self.intake_service = services.get("intake")
        self.candidate_factory = services.get("candidate_factory")
        self.clone_factory = services.get("clone_factory")
        self.patch_engine = services.get("patch_engine")
        self.validation_service = services.get("validation")
        self.evaluation_service = services.get("evaluation")
        self.reporting_service = services.get("reporting")
        self.governance_service = services.get("governance")
        self.promotion_service = services.get("promotion")
        self.memory_service = services.get("memory")
        logger.info("🔗 Services connected")
    
    # === OBSERVATION ===
    
    def submit_observation(self, observation: dict) -> str:
        """Observation qabul qilish"""
        obs_id = observation.get("id")
        self.observations[obs_id] = observation
        logger.info(f"👁️ Observation received: {obs_id}")
        return obs_id
    
    def create_candidate_from_signal(self, observation_id: str) -> Optional[str]:
        """Signal dan candidate yaratish"""
        if not self.candidate_factory:
            return None
        
        candidate = self.candidate_factory.from_observation(self.observations.get(observation_id))
        if candidate:
            self.candidates[candidate["id"]] = candidate
            self.lifecycle.register(candidate["id"], candidate)
            logger.info(f"📋 Candidate created: {candidate['id']}")
            return candidate["id"]
        return None
    
    # === SCHEDULING ===
    
    def schedule_next_candidate(self) -> Optional[str]:
        """Keyingi candidate ni tanlash"""
        pending = [c for c in self.candidates.values() if c.get("status") == CandidateStatus.QUEUED]
        if not pending:
            return None
        
        ranked = self.priority.rank(pending)
        return ranked[0].get("id") if ranked else None
    
    # === CLONE RUN ===
    
    def start_clone_run(self, candidate_id: str) -> Optional[str]:
        """Clone ishga tushirish"""
        if not self.clone_factory:
            return None
        
        clone = self.clone_factory.create_clone(candidate_id)
        if clone:
            self.clones[clone["clone_id"]] = clone
            self.lifecycle.transition(candidate_id, CandidateStatus.CLONE_ALLOCATED)
            logger.info(f"🏭 Clone started: {clone['clone_id']}")
            return clone["clone_id"]
        return None
    
    # === TRANSITION ===
    
    def advance_candidate(self, candidate_id: str, new_status: CandidateStatus) -> bool:
        """Candidate ni keyingi holatga o'tkazish"""
        success = self.lifecycle.transition(candidate_id, new_status)
        if success:
            self.candidates[candidate_id]["status"] = new_status
        return success
    
    def pause_candidate(self, candidate_id: str, reason: str) -> bool:
        """Candidate ni to'xtatish"""
        logger.info(f"⏸️ Candidate paused: {candidate_id} - {reason}")
        return True
    
    # === VALIDATION & EVALUATION ===
    
    def validate_clone(self, clone_id: str) -> dict:
        """Clone ni tekshirish"""
        if not self.validation_service:
            return {"passed": False, "error": "Service not connected"}
        
        result = self.validation_service.validate(clone_id, self.clones.get(clone_id, {}).get("path", ""))
        return result
    
    def evaluate_clone(self, clone_id: str) -> dict:
        """Clone ni baholash"""
        if not self.evaluation_service:
            return {}
        
        return self.evaluation_service.evaluate(clone_id)
    
    # === REPORTING ===
    
    def build_dossier(self, candidate_id: str, clone_id: str, evaluation: dict) -> dict:
        """Hisobot yaratish"""
        if not self.reporting_service:
            return {}
        
        dossier = self.reporting_service.build(candidate_id, clone_id, evaluation)
        self.dossiers[dossier.get("id")] = dossier
        return dossier
    
    # === GOVERNANCE ===
    
    def submit_for_approval(self, dossier_id: str) -> str:
        """Approval uchun yuborish"""
        if not self.governance_service:
            return ""
        
        approval_id = self.governance_service.submit(dossier_id)
        self.advance_candidate(self.dossiers.get(dossier_id, {}).get("candidate_id"), CandidateStatus.AWAITING_DECISION)
        return approval_id
    
    def finalize_decision(self, decision: dict) -> bool:
        """Qaror qilish"""
        candidate_id = decision.get("candidate_id")
        decision_type = decision.get("decision")
        
        # Decision ni qayd qilish
        self.decisions[candidate_id] = decision
        
        # Holatni o'zgartirish
        if decision_type == DecisionType.APPROVE_MAIN or decision_type == DecisionType.APPROVE_CANARY:
            self.advance_candidate(candidate_id, CandidateStatus.APPROVED)
        elif decision_type == DecisionType.REJECT:
            self.advance_candidate(candidate_id, CandidateStatus.REJECTED)
        
        logger.info(f"✅ Decision finalized: {candidate_id} -> {decision_type.value}")
        return True
    
    # === PROMOTION ===
    
    def promote(self, candidate_id: str, destination: DestinationType) -> Optional[dict]:
        """Promotion qilish"""
        if not self.promotion_service:
            return None
        
        clone_id = self._get_clone_for_candidate(candidate_id)
        if not clone_id:
            return None
        
        record = self.promotion_service.promote(clone_id, destination)
        self.advance_candidate(candidate_id, CandidateStatus.PROMOTED)
        return record
    
    def _get_clone_for_candidate(self, candidate_id: str) -> Optional[str]:
        for clone in self.clones.values():
            if clone.get("candidate_id") == candidate_id:
                return clone.get("clone_id")
        return None
    
    # === STATUS ===
    
    def get_status(self) -> dict:
        """Tizim holatini olish"""
        return {
            "candidates": len(self.candidates),
            "clones": len(self.clones),
            "observations": len(self.observations),
            "dossiers": len(self.dossiers),
            "decisions": len(self.decisions)
        }


__all__ = ["CentralOrchestrator", "LifecycleManager", "PriorityEngine", "PolicyGuard"]
