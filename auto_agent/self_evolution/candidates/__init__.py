"""
Candidate Lifecycle Layer - Upgrade Candidate Management
=========================================================
Bu qatlam candidate larni hayot sikli bo'yicha boshqaradi.

Lifecycle holatlari:
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

import uuid
import logging
from datetime import datetime
from typing import Optional
from enum import Enum

from ..data_contracts import (
    UpgradeCandidate, CandidateState, RiskLevel, Observation
)

logger = logging.getLogger(__name__)


class CandidateRegistry:
    """
    Candidate Registry - Barcha candidate larni saqlash
    """
    
    def __init__(self):
        self.candidates: dict[str, UpgradeCandidate] = {}
        self.observations_to_candidates: dict[str, list[str]] = {}
        logger.info("📋 CandidateRegistry initialized")
    
    def create_candidate(
        self,
        title: str,
        why_now: str,
        linked_observations: list[str],
        capability_targets: Optional[list[str]] = None,
        estimated_risk: RiskLevel = RiskLevel.MEDIUM,
        estimated_roi: float = 0.5,
        implementation_type: str = "incremental"
    ) -> UpgradeCandidate:
        """
        Yangi candidate yaratish
        """
        candidate_id = f"candidate_{str(uuid.uuid4())[:12]}"
        
        candidate = UpgradeCandidate(
            id=candidate_id,
            title=title,
            why_now=why_now,
            linked_observations=linked_observations,
            capability_targets=capability_targets or [],
            estimated_risk=estimated_risk,
            estimated_roi=estimated_roi,
            implementation_type=implementation_type,
            state=CandidateState.CANDIDATE_CREATED
        )
        
        # Saqlash
        self.candidates[candidate_id] = candidate
        
        # Observation mapping
        for obs_id in linked_observations:
            if obs_id not in self.observations_to_candidates:
                self.observations_to_candidates[obs_id] = []
            self.observations_to_candidates[obs_id].append(candidate_id)
        
        logger.info(f"📋 Candidate created: {candidate_id}")
        
        return candidate
    
    def get_candidate(self, candidate_id: str) -> Optional[UpgradeCandidate]:
        """Candidate olish"""
        return self.candidates.get(candidate_id)
    
    def update_candidate_state(
        self,
        candidate_id: str,
        new_state: CandidateState,
        notes: str = ""
    ) -> bool:
        """
        Candidate holatini yangilash
        """
        candidate = self.candidates.get(candidate_id)
        if not candidate:
            logger.error(f"❌ Candidate not found: {candidate_id}")
            return False
        
        old_state = candidate.state
        candidate.state = new_state
        candidate.updated_at = datetime.now()
        
        if notes:
            candidate.implementation_notes += f"\n[{datetime.now().isoformat()}] {notes}"
        
        logger.info(f"📋 Candidate {candidate_id}: {old_state.value} -> {new_state.value}")
        
        return True
    
    def get_candidates_by_state(self, state: CandidateState) -> list[UpgradeCandidate]:
        """Holat bo'yicha candidate larni olish"""
        return [c for c in self.candidates.values() if c.state == state]
    
    def get_pending_candidates(self) -> list[UpgradeCandidate]:
        """Kutayotgan candidate lar"""
        pending_states = [
            CandidateState.CANDIDATE_CREATED,
            CandidateState.QUEUED,
            CandidateState.CLONE_ALLOCATED,
            CandidateState.IN_MODIFICATION
        ]
        return [c for c in self.candidates.values() if c.state in pending_states]
    
    def get_awaiting_decision(self) -> list[UpgradeCandidate]:
        """Qaror kutayotgan candidate lar"""
        return self.get_candidates_by_state(CandidateState.AWAITING_HUMAN_DECISION)
    
    def assign_priority(self, candidate_id: str, priority: int) -> bool:
        """Candidate ga priority belgilash"""
        candidate = self.candidates.get(candidate_id)
        if not candidate:
            return False
        
        candidate.priority = priority
        candidate.updated_at = datetime.now()
        logger.info(f"📋 Priority assigned to {candidate_id}: {priority}")
        return True
    
    def get_candidates_for_observation(self, obs_id: str) -> list[UpgradeCandidate]:
        """Observationga bog'langan candidate lar"""
        candidate_ids = self.observations_to_candidates.get(obs_id, [])
        return [self.candidates[cid] for cid in candidate_ids if cid in self.candidates]
    
    def get_all_candidates(self) -> list[UpgradeCandidate]:
        """Barcha candidate lar"""
        return list(self.candidates.values())
    
    def get_stats(self) -> dict:
        """Candidate statistikasi"""
        stats = {
            "total": len(self.candidates),
            "by_state": {}
        }
        
        for candidate in self.candidates.values():
            state = candidate.state.value
            stats["by_state"][state] = stats["by_state"].get(state, 0) + 1
        
        return stats


class CandidateQueue:
    """
    Candidate Queue - Priority bo'yicha tartiblash
    """
    
    def __init__(self, registry: CandidateRegistry):
        self.registry = registry
        self.queue: list[str] = []
        logger.info("📬 CandidateQueue initialized")
    
    def add_to_queue(self, candidate_id: str) -> bool:
        """
        Candidate ni queue ga qo'shish
        """
        candidate = self.registry.get_candidate(candidate_id)
        if not candidate:
            logger.error(f"❌ Cannot add - candidate not found: {candidate_id}")
            return False
        
        # Holatni QUEUED ga o'zgartirish
        self.registry.update_candidate_state(
            candidate_id,
            CandidateState.QUEUED,
            "Added to queue"
        )
        
        # Queue ga qo'shish
        if candidate_id not in self.queue:
            self.queue.append(candidate_id)
            self._reorder_queue()
            
        logger.info(f"📬 Candidate added to queue: {candidate_id}")
        return True
    
    def _reorder_queue(self):
        """
        Queue ni priority bo'yicha qayta tartiblash
        """
        # Priority bo'yicha tartiblash (yuqori priority oldin)
        self.queue.sort(
            key=lambda cid: self.registry.get_candidate(cid).priority,
            reverse=True
        )
    
    def get_next(self) -> Optional[str]:
        """
        Keyingi candidate ni olish
        """
        if not self.queue:
            return None
        
        return self.queue[0]
    
    def pop_next(self) -> Optional[str]:
        """
        Keyingi candidate ni olish va queue dan o'chirish
        """
        next_id = self.get_next()
        if next_id:
            self.queue.remove(next_id)
            self.registry.update_candidate_state(
                next_id,
                CandidateState.CLONE_ALLOCATED,
                "Popped from queue for execution"
            )
            logger.info(f"📬 Next candidate from queue: {next_id}")
        return next_id
    
    def remove_from_queue(self, candidate_id: str) -> bool:
        """
        Candidate ni queue dan o'chirish
        """
        if candidate_id in self.queue:
            self.queue.remove(candidate_id)
            logger.info(f"📬 Candidate removed from queue: {candidate_id}")
            return True
        return False
    
    def get_queue_order(self) -> list[dict]:
        """
        Queue tartibini olish
        """
        result = []
        for cid in self.queue:
            candidate = self.registry.get_candidate(cid)
            if candidate:
                result.append({
                    "candidate_id": cid,
                    "title": candidate.title,
                    "priority": candidate.priority,
                    "risk": candidate.estimated_risk.value,
                    "state": candidate.state.value
                })
        return result
    
    def get_queue_size(self) -> int:
        """Queue hajmi"""
        return len(self.queue)


class CandidateFactory:
    """
    Candidate Factory - Candidate yaratish factory si
    """
    
    def __init__(self, registry: CandidateRegistry):
        self.registry = registry
        logger.info("🏭 CandidateFactory initialized")
    
    def create_from_observation(
        self,
        observation,
        additional_context: Optional[dict] = None
    ) -> UpgradeCandidate:
        """
        Observation dan candidate yaratish
        """
        # Title yaratish
        title = f"Upgrade: {observation.summary[:50]}"
        
        # Why now yaratish
        why_now = f"""
Based on {observation.source.value} signal:
- Summary: {observation.summary}
- Confidence: {observation.confidence}
- ROI: {observation.roi_score or 'N/A'}
- Triage result: {observation.triage_result}
        """.strip()
        
        # Capability targets
        capability_targets = observation.tags.copy()
        
        # Risk level
        estimated_risk = self._estimate_risk(observation)
        
        # ROI
        estimated_roi = observation.roi_score or 0.5
        
        # Create candidate
        candidate = self.registry.create_candidate(
            title=title,
            why_now=why_now,
            linked_observations=[observation.id],
            capability_targets=capability_targets,
            estimated_risk=estimated_risk,
            estimated_roi=estimated_roi,
            implementation_type="incremental"
        )
        
        # Implementation notes
        candidate.implementation_notes = f"""
Source observation: {observation.id}
Signal type: {observation.signal_type.value}
Evidence: {observation.evidence}
        """.strip()
        
        # Target modules (placeholder - execution da to'ldiriladi)
        candidate.target_modules = []
        
        # Expected outcomes
        candidate.expected_outcomes = [
            f"Address {observation.signal_type.value}",
            f"Improve from {observation.source.value}"
        ]
        
        logger.info(f"🏭 Candidate created from observation: {candidate.id}")
        
        return candidate
    
    def _estimate_risk(self, observation) -> RiskLevel:
        """
        Risk ni baholash
        """
        # Signal type bo'yicha risk
        type_risk = {
            "benchmark_failure": RiskLevel.MEDIUM,
            "user_feedback": RiskLevel.LOW,
            "regression_alert": RiskLevel.HIGH,
            "competitor_capability": RiskLevel.MEDIUM,
            "social_pain": RiskLevel.LOW,
            "research_conclusion": RiskLevel.LOW,
            "new_tool_opportunity": RiskLevel.MEDIUM,
            "external_observation": RiskLevel.MEDIUM
        }
        
        base_risk = type_risk.get(
            observation.signal_type.value,
            RiskLevel.MEDIUM
        )
        
        # Confidence ga qarab o'zgartirish
        if observation.confidence < 0.5:
            # Past confidence - yuqori risk
            risk_values = list(RiskLevel)
            idx = risk_values.index(base_risk)
            if idx < len(risk_values) - 1:
                return risk_values[idx + 1]
        
        return base_risk
    
    def create_manual_candidate(
        self,
        title: str,
        description: str,
        target_modules: list[str],
        risk: RiskLevel = RiskLevel.MEDIUM
    ) -> UpgradeCandidate:
        """
        Qo'lda candidate yaratish (manual)
        """
        candidate = self.registry.create_candidate(
            title=title,
            why_now=description,
            linked_observations=[],
            estimated_risk=risk,
            estimated_roi=0.7,
            implementation_type="manual"
        )
        
        candidate.target_modules = target_modules
        candidate.implementation_notes = description
        
        logger.info(f"🏭 Manual candidate created: {candidate.id}")
        
        return candidate


class LifecycleManager:
    """
    Lifecycle Manager - Hayot sikli boshqaruvi
    Bu candidate larni hayot sikli bo'yicha boshqaradi
    """
    
    def __init__(self, registry: CandidateRegistry, queue: CandidateQueue):
        self.registry = registry
        self.queue = queue
        self.lifecycle_hooks: dict[str, list[callable]] = {
            "on_state_change": [],
            "on_queued": [],
            "on_clone_allocated": [],
            "on_completed": [],
            "on_rejected": []
        }
        logger.info("🔄 LifecycleManager initialized")
    
    def register_hook(self, event: str, callback: callable):
        """Hook ro'yxatga olish"""
        if event in self.lifecycle_hooks:
            self.lifecycle_hooks[event].append(callback)
            logger.info(f"🔗 Hook registered: {event}")
    
    def _execute_hooks(self, event: str, candidate_id: str, data: dict = None):
        """Hook larni ishga tushirish"""
        if event in self.lifecycle_hooks:
            for callback in self.lifecycle_hooks[event]:
                try:
                    callback(candidate_id, data or {})
                except Exception as e:
                    logger.error(f"❌ Hook error: {e}")
    
    def transition_to(
        self,
        candidate_id: str,
        new_state: CandidateState,
        metadata: dict = None
    ) -> bool:
        """
        Candidate ni yangi holatga o'tkazish
        """
        candidate = self.registry.get_candidate(candidate_id)
        if not candidate:
            logger.error(f"❌ Candidate not found: {candidate_id}")
            return False
        
        old_state = candidate.state
        
        # Validate transition
        if not self._validate_transition(old_state, new_state):
            logger.error(f"❌ Invalid transition: {old_state.value} -> {new_state.value}")
            return False
        
        # Update state
        success = self.registry.update_candidate_state(
            candidate_id,
            new_state,
            f"Transition: {old_state.value} -> {new_state.value}"
        )
        
        if success:
            # Execute hooks
            self._execute_hooks("on_state_change", candidate_id, {
                "old_state": old_state.value,
                "new_state": new_state.value,
                "metadata": metadata
            })
            
            # State-specific hooks
            if new_state == CandidateState.QUEUED:
                self._execute_hooks("on_queued", candidate_id)
            elif new_state == CandidateState.CLONE_ALLOCATED:
                self._execute_hooks("on_clone_allocated", candidate_id)
            elif new_state in [CandidateState.PROMOTED, CandidateState.ARCHIVED]:
                self._execute_hooks("on_completed", candidate_id)
            elif new_state == CandidateState.REJECTED:
                self._execute_hooks("on_rejected", candidate_id)
        
        return success
    
    def _validate_transition(
        self,
        from_state: CandidateState,
        to_state: CandidateState
    ) -> bool:
        """
        O'tishni validatsiya qilish
        """
        # Valid transitions
        valid_transitions = {
            CandidateState.OBSERVED: [CandidateState.TRIAGED],
            CandidateState.TRIAGED: [CandidateState.CANDIDATE_CREATED, CandidateState.REJECTED],
            CandidateState.CANDIDATE_CREATED: [CandidateState.QUEUED, CandidateState.REJECTED],
            CandidateState.QUEUED: [CandidateState.CLONE_ALLOCATED, CandidateState.REJECTED],
            CandidateState.CLONE_ALLOCATED: [CandidateState.IN_MODIFICATION, CandidateState.REJECTED],
            CandidateState.IN_MODIFICATION: [CandidateState.LOCAL_VALIDATION, CandidateState.REJECTED],
            CandidateState.LOCAL_VALIDATION: [CandidateState.FULL_EVALUATION, CandidateState.REJECTED],
            CandidateState.FULL_EVALUATION: [CandidateState.REPORT_READY, CandidateState.REJECTED],
            CandidateState.REPORT_READY: [CandidateState.AWAITING_HUMAN_DECISION],
            CandidateState.AWAITING_HUMAN_DECISION: [
                CandidateState.APPROVED_FOR_DESTINATION,
                CandidateState.REJECTED,
                CandidateState.CANDIDATE_CREATED  # revise
            ],
            CandidateState.APPROVED_FOR_DESTINATION: [
                CandidateState.PROMOTED,
                CandidateState.FORKED,
                CandidateState.ARCHIVED
            ],
            CandidateState.PROMOTED: [CandidateState.ROLLED_BACK],
            CandidateState.FORKED: [],
            CandidateState.ARCHIVED: [],
            CandidateState.REJECTED: [],
            CandidateState.ROLLED_BACK: [CandidateState.CANDIDATE_CREATED]
        }
        
        return to_state in valid_transitions.get(from_state, [])
    
    def can_transition(self, candidate_id: str, target_state: CandidateState) -> bool:
        """O'tish mumkinmi?"""
        candidate = self.registry.get_candidate(candidate_id)
        if not candidate:
            return False
        
        return self._validate_transition(candidate.state, target_state)
    
    def get_lifecycle_path(self, candidate_id: str) -> list[str]:
        """Candidate uchun lifecycle yo'lini olish"""
        candidate = self.registry.get_candidate(candidate_id)
        if not candidate:
            return []
        
        # Simplified - real tizimda to'liq path hisoblanadi
        return [s.value for s in CandidateState]
    
    def get_stats(self) -> dict:
        """Lifecycle statistikasi"""
        return self.registry.get_stats()


def create_candidate_system(registry: Optional[CandidateRegistry] = None):
    """
    Candidate system yaratish
    """
    if registry is None:
        registry = CandidateRegistry()
    
    queue = CandidateQueue(registry)
    factory = CandidateFactory(registry)
    lifecycle = LifecycleManager(registry, queue)
    
    return {
        "registry": registry,
        "queue": queue,
        "factory": factory,
        "lifecycle": lifecycle
    }


# Candidates module exports
__all__ = [
    "CandidateRegistry",
    "CandidateQueue", 
    "CandidateFactory",
    "LifecycleManager",
    "create_candidate_system"
]
