"""
Central Orchestrator - Bosh Boshqaruv Markazi
====================================================
Bu tizimning yuragi!

Vazifalari:
- Qaysi signalga javob berishni tanlash
- Qaysi candidate ni birinchi ishlashni tanlash
- Qachon clone yaratishni hal qilish
- Parallel ishlarni boshqarish
- Risk budgetni kuzatish
- Human approvalsiz hech narsani main'ga o'tkazmaslik
"""

import uuid
import logging
from datetime import datetime
from typing import Optional
from enum import Enum

from ..data_contracts import (
    SystemState, Observation, UpgradeCandidate, CloneRun,
    CandidateState, DestinationType, ApprovalDecision
)

logger = logging.getLogger(__name__)


class OrchestratorState(Enum):
    """Orchestrator holatlari"""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"


class CentralOrchestrator:
    """
    Central Orchestrator - Bosh Boshqaruv Markazi
    """
    
    def __init__(self, workspace_path: str):
        self.workspace_path = workspace_path
        self.system_state = SystemState()
        self.state = OrchestratorState.IDLE
        
        self.intake_system = None
        self.candidate_system = None
        self.execution_layer = None
        self.evaluation_layer = None
        self.reporting_layer = None
        self.governance_layer = None
        self.promotion_layer = None
        self.memory_layer = None
        
        self.backlog: list[str] = []
        self.roadmap_priorities: list[str] = []
        
        logger.info("🎯 CentralOrchestrator initialized")
    
    def connect_layers(self, layers: dict):
        """Barcha qatlamlarni ulash"""
        self.intake_system = layers.get("intake")
        self.candidate_system = layers.get("candidates")
        self.execution_layer = layers.get("execution")
        self.evaluation_layer = layers.get("evaluation")
        self.reporting_layer = layers.get("reporting")
        self.governance_layer = layers.get("governance")
        self.promotion_layer = layers.get("promotion")
        self.memory_layer = layers.get("memory")
        logger.info("🔗 All layers connected")
    
    def process_observation(self, observation: Observation) -> dict:
        """Observation ni qayta ishlash"""
        logger.info(f"🎯 Processing observation: {observation.id}")
        
        result = {"observation_id": observation.id, "action": None, "candidate_id": None, "status": "pending"}
        
        if self.intake_system:
            triage_result = self.intake_system["triage"].triage_observation(observation)
            result["triage_result"] = triage_result
        
        if triage_result == "candidate_create":
            candidate = self._create_candidate_from_observation(observation)
            result["action"] = "candidate_created"
            result["candidate_id"] = candidate.id
        
        if result["candidate_id"]:
            self._add_to_backlog(result["candidate_id"])
        
        result["status"] = "completed"
        return result
    
    def _create_candidate_from_observation(self, observation: Observation) -> UpgradeCandidate:
        if not self.candidate_system:
            raise RuntimeError("Candidate system not connected")
        
        factory = self.candidate_system["factory"]
        candidate = factory.create_from_observation(observation)
        logger.info(f"📋 Candidate created: {candidate.id}")
        return candidate
    
    def _add_to_backlog(self, candidate_id: str):
        if candidate_id not in self.backlog:
            self.backlog.append(candidate_id)
            self._reorder_backlog()
    
    def _reorder_backlog(self):
        if not self.candidate_system:
            return
        
        registry = self.candidate_system["registry"]
        
        self.backlog.sort(
            key=lambda cid: registry.get_candidate(cid).priority if registry.get_candidate(cid) else 0,
            reverse=True
        )
    
    def select_next_candidate(self) -> Optional[str]:
        if self.system_state.active_clones_count >= self.system_state.clone_limit:
            logger.warning("⚠️ Clone limit reached")
            return None
        
        if self.system_state.used_risk_budget >= self.system_state.current_risk_budget:
            logger.warning("⚠️ Risk budget exhausted")
            return None
        
        if not self.backlog:
            return None
        
        candidate_id = self.backlog[0]
        
        if self.candidate_system:
            candidate = self.candidate_system["registry"].get_candidate(candidate_id)
            if not candidate or candidate.state != CandidateState.QUEUED:
                self.backlog.remove(candidate_id)
                return self.select_next_candidate()
        
        return candidate_id
    
    def execute_candidate(self, candidate_id: str, modifications: list[dict]) -> Optional[CloneRun]:
        logger.info(f"⚡ Executing candidate: {candidate_id}")
        
        if not self.execution_layer:
            raise RuntimeError("Execution layer not connected")
        
        clone = self.execution_layer.execute_candidate(candidate_id, modifications)
        
        if clone:
            self.system_state.active_clones_count += 1
            self.system_state.last_updated = datetime.now()
        
        return clone
    
    def evaluate_clone(self, clone: CloneRun, candidate: UpgradeCandidate) -> dict:
        logger.info(f"📈 Evaluating clone: {clone.clone_id}")
        
        if not self.evaluation_layer:
            raise RuntimeError("Evaluation layer not connected")
        
        evaluation = self.evaluation_layer.evaluate_clone(clone)
        
        if self.reporting_layer:
            report = self.reporting_layer.create_full_report(candidate, clone, evaluation)
            return report
        
        return {"evaluation": evaluation}
    
    def get_system_status(self) -> dict:
        return {
            "orchestrator_state": self.state.value,
            "system_state": self.system_state.to_dict(),
            "backlog_size": len(self.backlog),
            "active_clones": self.system_state.active_clones_count,
            "pending_decisions": self.system_state.awaiting_decision_count
        }
    
    def can_clone(self) -> bool:
        return (
            self.system_state.active_clones_count < self.system_state.clone_limit and
            self.system_state.used_risk_budget < self.system_state.current_risk_budget
        )
    
    def start(self):
        self.state = OrchestratorState.RUNNING
        logger.info("🎯 CentralOrchestrator started")
    
    def stop(self):
        self.state = OrchestratorState.IDLE
        logger.info("⏹️ CentralOrchestrator stopped")


def create_central_orchestrator(workspace_path: str) -> CentralOrchestrator:
    return CentralOrchestrator(workspace_path)
