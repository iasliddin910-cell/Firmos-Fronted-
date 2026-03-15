"""
Intervention Queue - Evaluation-Driven Control System
==================================================

This module manages the queue of candidate interventions based on failures.
Each intervention is scored by expected gain, cost, and risk.

The InterventionQueue:
1. Receives failure diagnoses from FailureAnalyzer
2. Generates candidate interventions
3. Scores them by multiple factors
4. Returns prioritized list for execution
"""
import time
import logging
import uuid
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict

logger = logging.getLogger(__name__)


class InterventionType(Enum):
    """Types of interventions available"""
    # Planner interventions
    PLANNER_POLICY_PATCH = "planner_policy_patch"
    PLAN_DEPTH_REDUCTION = "plan_depth_reduction"
    EARLY_CHECKPOINT = "early_checkpoint"
    REPLAN_TRIGGER_TUNING = "replan_trigger_tuning"
    
    # Tool routing interventions
    ROUTING_WEIGHT_UPDATE = "routing_weight_update"
    NEGATIVE_PRIOR_ADD = "negative_prior_add"
    TOOL_PREFERENCE_UPDATE = "tool_preference_update"
    
    # Memory/retrieval interventions
    RETRIEVAL_RANK_TUNING = "retrieval_rank_tuning"
    MEMORY_WEIGHT_ADJUST = "memory_weight_adjust"
    BAD_RETRIEVAL_SUPPRESS = "bad_retrieval_suppress"
    
    # Self-improvement interventions
    SELF_PATCH_PROPOSAL = "self_patch_proposal"
    PATCH_PRIORITY_UPDATE = "patch_priority_update"
    
    # Tool creation interventions
    NEW_TOOL_PROPOSAL = "new_tool_proposal"
    TOOL_TRIGGER_DETECTED = "tool_trigger_detected"
    
    # Safety interventions
    SAFETY_POLICY_HARDEN = "safety_policy_harden"
    FORBIDDEN_PATH_UPDATE = "forbidden_path_update"
    
    # Learning interventions
    LEARNING_PRIORITY_UPDATE = "learning_priority_update"
    KNOWLEDGE_REFRESH = "knowledge_refresh"


class InterventionStatus(Enum):
    """Status of an intervention"""
    PENDING = "pending"
    EVALUATING = "evaluating"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTED = "executed"
    FAILED = "failed"


@dataclass
class Intervention:
    """
    A single candidate intervention.
    
    Each intervention has:
    - Expected benefit (how much it will improve)
    - Cost (how hard to implement)
    - Risk (what could go wrong)
    - Blast radius (how many capabilities affected)
    """
    intervention_id: str
    intervention_type: InterventionType
    
    # What triggered this
    failure_type: str
    failure_id: str
    
    # Description
    description: str
    target_subsystem: str
    
    # Scoring
    expected_gain: float  # 0-1, expected improvement
    confidence: float     # 0-1, how sure we are
    implementation_cost: float  # 0-1, effort required
    regression_risk: float  # 0-1, chance of causing issues
    blast_radius: float   # 0-1, how many subsystems affected
    
    # Priority (calculated)
    priority_score: float = 0.0
    
    # Status
    status: InterventionStatus = InterventionStatus.PENDING
    
    # Metadata
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    parent_intervention_id: Optional[str] = None
    
    # Results
    actual_gain: Optional[float] = None
    execution_time: Optional[float] = None
    
    def calculate_priority(self):
        """
        Calculate priority score based on all factors.
        
        Priority = expected_gain * confidence * (1 - regression_risk) / (cost * blast_radius + 0.1)
        """
        if self.implementation_cost == 0:
            self.implementation_cost = 0.1
        
        if self.blast_radius == 0:
            self.blast_radius = 0.1
        
        self.priority_score = (
            self.expected_gain * 
            self.confidence * 
            (1 - self.regression_risk)
        ) / (
            self.implementation_cost * 
            0.3 + 
            self.blast_radius * 0.2 +
            0.1  # Base to prevent division issues
        )
        
        return self.priority_score
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "intervention_id": self.intervention_id,
            "intervention_type": self.intervention_type.value,
            "description": self.description,
            "target_subsystem": self.target_subsystem,
            "expected_gain": self.expected_gain,
            "confidence": self.confidence,
            "implementation_cost": self.implementation_cost,
            "regression_risk": self.regression_risk,
            "blast_radius": self.blast_radius,
            "priority_score": self.priority_score,
            "status": self.status.value,
            "created_at": self.created_at,
            "failure_type": self.failure_type
        }


class InterventionQueue:
    """
    ADVANCED Intervention Queue that manages all candidate interventions.
    
    This is the bridge between failure diagnosis and improvement:
    - Receives failures
    - Generates interventions
    - Scores and prioritizes
    - Returns best interventions for execution
    """
    
    def __init__(self):
        # All interventions
        self.interventions: Dict[str, Intervention] = {}
        
        # Pending interventions (by priority)
        self.pending_queue: List[str] = []
        
        # Intervention templates
        self._init_templates()
        
        # Statistics
        self.stats = {
            "total_created": 0,
            "total_executed": 0,
            "total_rejected": 0,
            "avg_actual_gain": 0.0
        }
        
        # Intervention history for learning
        self.intervention_history: List[Dict] = []
        
        logger.info("📋 InterventionQueue initialized - ADVANCED intervention management ENABLED")
    
    def _init_templates(self):
        """Initialize intervention templates"""
        self.templates = {
            # Planner templates
            InterventionType.PLANNER_POLICY_PATCH: {
                "expected_gain": 0.3,
                "confidence": 0.6,
                "implementation_cost": 0.5,
                "regression_risk": 0.3,
                "blast_radius": 0.5
            },
            InterventionType.PLAN_DEPTH_REDUCTION: {
                "expected_gain": 0.2,
                "confidence": 0.7,
                "implementation_cost": 0.2,
                "regression_risk": 0.1,
                "blast_radius": 0.3
            },
            InterventionType.EARLY_CHECKPOINT: {
                "expected_gain": 0.25,
                "confidence": 0.65,
                "implementation_cost": 0.3,
                "regression_risk": 0.15,
                "blast_radius": 0.3
            },
            
            # Tool routing templates
            InterventionType.ROUTING_WEIGHT_UPDATE: {
                "expected_gain": 0.35,
                "confidence": 0.7,
                "implementation_cost": 0.2,
                "regression_risk": 0.2,
                "blast_radius": 0.2
            },
            InterventionType.NEGATIVE_PRIOR_ADD: {
                "expected_gain": 0.3,
                "confidence": 0.75,
                "implementation_cost": 0.1,
                "regression_risk": 0.1,
                "blast_radius": 0.1
            },
            
            # Memory templates
            InterventionType.RETRIEVAL_RANK_TUNING: {
                "expected_gain": 0.4,
                "confidence": 0.7,
                "implementation_cost": 0.3,
                "regression_risk": 0.2,
                "blast_radius": 0.3
            },
            InterventionType.BAD_RETRIEVAL_SUPPRESS: {
                "expected_gain": 0.35,
                "confidence": 0.8,
                "implementation_cost": 0.2,
                "regression_risk": 0.1,
                "blast_radius": 0.2
            },
            
            # Self-improvement templates
            InterventionType.SELF_PATCH_PROPOSAL: {
                "expected_gain": 0.5,
                "confidence": 0.5,
                "implementation_cost": 0.7,
                "regression_risk": 0.4,
                "blast_radius": 0.6
            },
            
            # Tool creation templates
            InterventionType.NEW_TOOL_PROPOSAL: {
                "expected_gain": 0.6,
                "confidence": 0.6,
                "implementation_cost": 0.8,
                "regression_risk": 0.3,
                "blast_radius": 0.4
            },
            
            # Safety templates
            InterventionType.SAFETY_POLICY_HARDEN: {
                "expected_gain": 0.2,
                "confidence": 0.9,
                "implementation_cost": 0.3,
                "regression_risk": 0.05,
                "blast_radius": 0.2
            }
        }
    
    def add_intervention(
        self,
        intervention_type: InterventionType,
        failure_type: str,
        failure_id: str,
        description: str,
        target_subsystem: str,
        custom_params: Optional[Dict] = None
    ) -> Intervention:
        """Add a new intervention to the queue"""
        
        # Get template parameters
        template = self.templates.get(intervention_type, {})
        
        # Create intervention
        intervention = Intervention(
            intervention_id=str(uuid.uuid4())[:8],
            intervention_type=intervention_type,
            failure_type=failure_type,
            failure_id=failure_id,
            description=description,
            target_subsystem=target_subsystem,
            expected_gain=custom_params.get("expected_gain", template.get("expected_gain", 0.3)),
            confidence=custom_params.get("confidence", template.get("confidence", 0.5)),
            implementation_cost=custom_params.get("implementation_cost", template.get("implementation_cost", 0.5)),
            regression_risk=custom_params.get("regression_risk", template.get("regression_risk", 0.3)),
            blast_radius=custom_params.get("blast_radius", template.get("blast_radius", 0.3))
        )
        
        # Calculate priority
        intervention.calculate_priority()
        
        # Store
        self.interventions[intervention.intervention_id] = intervention
        self.pending_queue.append(intervention.intervention_id)
        
        # Update stats
        self.stats["total_created"] += 1
        
        # Re-sort queue by priority
        self._sort_queue()
        
        logger.info(f"📋 Added intervention: {intervention_type.value} "
                   f"(priority: {intervention.priority_score:.2f})")
        
        return intervention
    
    def add_intervention_from_failure(
        self,
        failure_label: Dict,
        suggested_interventions: List[str]
    ) -> List[Intervention]:
        """
        Add interventions based on failure diagnosis.
        
        This is the main entry point from FailureAnalyzer.
        """
        interventions = []
        
        failure_type = failure_label.get("failure_type", "unknown")
        failure_id = failure_label.get("task_id", "unknown")
        
        for suggested in suggested_interventions:
            # Parse suggestion (e.g., "routing_tuner:update_weights")
            if ":" in suggested:
                subsystem, action = suggested.split(":", 1)
                intervention_type = self._get_intervention_type(subsystem, action)
            else:
                intervention_type = self._get_intervention_type_from_string(suggested)
            
            if intervention_type:
                intervention = self.add_intervention(
                    intervention_type=intervention_type,
                    failure_type=failure_type,
                    failure_id=failure_id,
                    description=f"Fix {failure_type}: {suggested}",
                    target_subsystem=subsystem if 'subsystem' in locals() else "unknown"
                )
                interventions.append(intervention)
        
        return interventions
    
    def _get_intervention_type(self, subsystem: str, action: str) -> Optional[InterventionType]:
        """Map subsystem+action to intervention type"""
        mapping = {
            ("planner", "simplify_plans"): InterventionType.PLAN_DEPTH_REDUCTION,
            ("planner", "add_early_checkpoint"): InterventionType.EARLY_CHECKPOINT,
            ("planner", "tighten_budget"): InterventionType.PLAN_DEPTH_REDUCTION,
            ("routing_tuner", "update_weights"): InterventionType.ROUTING_WEIGHT_UPDATE,
            ("retrieval_tuner", "rerank_adjustment"): InterventionType.RETRIEVAL_RANK_TUNING,
            ("retry_budget_tuner", "add_diversification"): InterventionType.REPLAN_TRIGGER_TUNING,
            ("safety_policy", "harden_restrictions"): InterventionType.SAFETY_POLICY_HARDEN,
            ("tool_factory", "new_tool"): InterventionType.NEW_TOOL_PROPOSAL
        }
        
        return mapping.get((subsystem, action))
    
    def _get_intervention_type_from_string(self, s: str) -> Optional[InterventionType]:
        """Map string to intervention type"""
        mapping = {
            "planner_policy_adapter": InterventionType.PLANNER_POLICY_PATCH,
            "routing_tuner": InterventionType.ROUTING_WEIGHT_UPDATE,
            "retrieval_tuner": InterventionType.RETRIEVAL_RANK_TUNING,
            "patch_impact_analyzer": InterventionType.SELF_PATCH_PROPOSAL,
            "retry_budget_tuner": InterventionType.REPLAN_TRIGGER_TUNING,
            "safety_policy": InterventionType.SAFETY_POLICY_HARDEN,
            "tool_factory": InterventionType.NEW_TOOL_PROPOSAL
        }
        
        for key, val in mapping.items():
            if key in s:
                return val
        
        return InterventionType.SELF_PATCH_PROPOSAL  # Default
    
    def _sort_queue(self):
        """Sort pending queue by priority"""
        self.pending_queue.sort(
            key=lambda iid: self.interventions[iid].priority_score,
            reverse=True
        )
    
    def get_top_intervention(self, max_risk: float = 0.5) -> Optional[Intervention]:
        """
        Get the highest priority intervention that meets risk criteria.
        
        This is what the meta-controller calls to get next action.
        """
        for iid in self.pending_queue:
            intervention = self.interventions[iid]
            
            if intervention.status != InterventionStatus.PENDING:
                continue
            
            if intervention.regression_risk > max_risk:
                # Skip high-risk interventions
                continue
            
            return intervention
        
        return None
    
    def get_interventions_for_subsystem(
        self,
        subsystem: str,
        limit: int = 5
    ) -> List[Intervention]:
        """Get top interventions for a specific subsystem"""
        subsystem_interventions = [
            i for i in self.interventions.values()
            if i.target_subsystem == subsystem and i.status == InterventionStatus.PENDING
        ]
        
        subsystem_interventions.sort(key=lambda i: i.priority_score, reverse=True)
        
        return subsystem_interventions[:limit]
    
    def approve_intervention(self, intervention_id: str) -> bool:
        """Approve an intervention for execution"""
        intervention = self.interventions.get(intervention_id)
        if not intervention:
            return False
        
        intervention.status = InterventionStatus.APPROVED
        intervention.updated_at = time.time()
        
        logger.info(f"✅ Approved intervention: {intervention_id}")
        
        return True
    
    def reject_intervention(self, intervention_id: str, reason: str) -> bool:
        """Reject an intervention"""
        intervention = self.interventions.get(intervention_id)
        if not intervention:
            return False
        
        intervention.status = InterventionStatus.REJECTED
        intervention.updated_at = time.time()
        
        self.stats["total_rejected"] += 1
        
        # Remove from pending
        if intervention_id in self.pending_queue:
            self.pending_queue.remove(intervention_id)
        
        # Record in history
        self.intervention_history.append({
            "intervention": intervention.to_dict(),
            "result": "rejected",
            "reason": reason
        })
        
        logger.info(f"❌ Rejected intervention: {intervention_id} - {reason}")
        
        return True
    
    def mark_executed(
        self,
        intervention_id: str,
        actual_gain: Optional[float] = None,
        failed: bool = False
    ):
        """Mark an intervention as executed"""
        intervention = self.interventions.get(intervention_id)
        if not intervention:
            return
        
        if failed:
            intervention.status = InterventionStatus.FAILED
        else:
            intervention.status = InterventionStatus.EXECUTED
            intervention.actual_gain = actual_gain
        
        intervention.execution_time = time.time() - intervention.created_at
        intervention.updated_at = time.time()
        
        # Update stats
        self.stats["total_executed"] += 1
        if actual_gain is not None:
            # Update average
            current_avg = self.stats["avg_actual_gain"]
            total = self.stats["total_executed"]
            self.stats["avg_actual_gain"] = (current_avg * (total - 1) + actual_gain) / total
        
        # Remove from pending
        if intervention_id in self.pending_queue:
            self.pending_queue.remove(intervention_id)
        
        # Record in history
        self.intervention_history.append({
            "intervention": intervention.to_dict(),
            "result": "executed",
            "actual_gain": actual_gain,
            "execution_time": intervention.execution_time
        })
        
        logger.info(f"📋 Executed intervention: {intervention_id}, "
                   f"actual_gain: {actual_gain}")
    
    def get_queue_status(self) -> Dict:
        """Get status of the intervention queue"""
        pending = [i for i in self.interventions.values() 
                  if i.status == InterventionStatus.PENDING]
        approved = [i for i in self.interventions.values() 
                   if i.status == InterventionStatus.APPROVED]
        executed = [i for i in self.interventions.values() 
                    if i.status == InterventionStatus.EXECUTED]
        
        return {
            "pending_count": len(pending),
            "approved_count": len(approved),
            "executed_count": len(executed),
            "total_created": self.stats["total_created"],
            "avg_actual_gain": self.stats["avg_actual_gain"],
            "top_pending": [
                i.to_dict() for i in sorted(
                    pending, key=lambda x: x.priority_score, reverse=True
                )[:5]
            ]
        }


def create_intervention_queue() -> InterventionQueue:
    """Factory function to create InterventionQueue"""
    return InterventionQueue()
