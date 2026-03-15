"""
Planner Policy Adapter - Tuner for Planner Subsystem
================================================

This tuner adjusts planner parameters based on benchmark feedback.

When benchmark shows:
- Too many replans -> reduce initial plan depth
- Zero-progress loops -> add early checkpoint mandate
- Excessive steps -> tighten milestone requirements
- Timeout issues -> add budget enforcement
"""
import logging
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class PlannerPolicy:
    """Current planner policy configuration"""
    max_initial_plan_depth: int = 10
    early_checkpoint_mandate: bool = False
    checkpoint_frequency: int = 5
    replan_threshold: int = 3
    zero_progress_threshold: int = 3
    max_total_steps: int = 50
    timeout_per_step_seconds: int = 30
    min_diversity_per_retry: int = 2
    allow_partial_plan: bool = True
    validate_before_execute: bool = True


@dataclass
class PlannerAdjustment:
    """Record of a planner adjustment"""
    adjustment_id: str
    parameter: str
    old_value: Any
    new_value: Any
    reason: str
    benchmark_evidence: Dict
    timestamp: float = field(default_factory=time.time)


class PlannerPolicyAdapter:
    """
    Tuner that adjusts planner policy based on benchmark feedback.
    
    This closes the loop between benchmark results and planner behavior.
    """
    
    def __init__(self):
        self.current_policy = PlannerPolicy()
        self.adjustment_history: List[PlannerAdjustment] = []
        
        # Thresholds for adjustment
        self.replan_high_threshold = 5
        self.replan_medium_threshold = 3
        self.steps_high_threshold = 30
        self.steps_medium_threshold = 20
        self.zero_progress_threshold = 3
        
        logger.info("🎯 PlannerPolicyAdapter initialized - ADVANCED planner tuning ENABLED")
    
    def analyze_benchmark_feedback(self, benchmark_result: Dict) -> Dict:
        """
        Analyze benchmark result and determine needed adjustments.
        
        Returns dictionary of suggested adjustments.
        """
        suggestions = {}
        
        # Extract metrics
        replan_count = benchmark_result.get("replan_count", 0)
        step_count = benchmark_result.get("step_count", 0)
        zero_progress_count = benchmark_result.get("zero_progress_count", 0)
        timeout_count = benchmark_result.get("timeout_count", 0)
        
        # Check for replanning issues
        if replan_count >= self.replan_high_threshold:
            suggestions["max_initial_plan_depth"] = {
                "current": self.current_policy.max_initial_plan_depth,
                "suggested": max(3, self.current_policy.max_initial_plan_depth - 2),
                "reason": f"High replan count ({replan_count}) detected"
            }
            suggestions["min_diversity_per_retry"] = {
                "current": self.current_policy.min_diversity_per_retry,
                "suggested": min(5, self.current_policy.min_diversity_per_retry + 1),
                "reason": "Need more diversity in retries"
            }
        
        # Check for zero-progress loops
        if zero_progress_count >= self.zero_progress_threshold:
            suggestions["early_checkpoint_mandate"] = {
                "current": self.current_policy.early_checkpoint_mandate,
                "suggested": True,
                "reason": f"Zero-progress loops ({zero_progress_count}) detected"
            }
            suggestions["checkpoint_frequency"] = {
                "current": self.current_policy.checkpoint_frequency,
                "suggested": max(2, self.current_policy.checkpoint_frequency - 1),
                "reason": "More frequent checkpoints needed"
            }
        
        # Check for excessive steps
        if step_count >= self.steps_high_threshold:
            suggestions["max_initial_plan_depth"] = {
                "current": self.current_policy.max_initial_plan_depth,
                "suggested": max(3, self.current_policy.max_initial_plan_depth - 3),
                "reason": f"Excessive steps ({step_count}) detected"
            }
            suggestions["validate_before_execute"] = {
                "current": self.current_policy.validate_before_execute,
                "suggested": True,
                "reason": "Need validation to prevent wasted steps"
            }
        
        # Check for timeout issues
        if timeout_count > 0:
            suggestions["timeout_per_step_seconds"] = {
                "current": self.current_policy.timeout_per_step_seconds,
                "suggested": max(10, self.current_policy.timeout_per_step_seconds - 5),
                "reason": f"Timeouts ({timeout_count}) detected"
            }
        
        return suggestions
    
    def apply_adjustment(
        self,
        parameter: str,
        new_value: Any,
        reason: str,
        benchmark_evidence: Optional[Dict] = None
    ) -> bool:
        """Apply a policy adjustment"""
        old_value = getattr(self.current_policy, parameter, None)
        
        if old_value is None:
            logger.warning(f"⚠️ Unknown parameter: {parameter}")
            return False
        
        # Record adjustment
        adjustment = PlannerAdjustment(
            adjustment_id=f"adj_{len(self.adjustment_history)}",
            parameter=parameter,
            old_value=old_value,
            new_value=new_value,
            reason=reason,
            benchmark_evidence=benchmark_evidence or {}
        )
        self.adjustment_history.append(adjustment)
        
        # Apply
        setattr(self.current_policy, parameter, new_value)
        
        logger.info(f"🎯 Applied planner adjustment: {parameter} = {new_value} "
                   f"(was {old_value})")
        
        return True
    
    def apply_suggestions(self, suggestions: Dict) -> List[str]:
        """Apply all suggested adjustments"""
        applied = []
        
        for param, suggestion in suggestions.items():
            new_value = suggestion.get("suggested")
            reason = suggestion.get("reason")
            
            if self.apply_adjustment(param, new_value, reason, suggestion):
                applied.append(param)
        
        return applied
    
    def get_current_policy(self) -> Dict:
        """Get current policy as dictionary"""
        return {
            "max_initial_plan_depth": self.current_policy.max_initial_plan_depth,
            "early_checkpoint_mandate": self.current_policy.early_checkpoint_mandate,
            "checkpoint_frequency": self.current_policy.checkpoint_frequency,
            "replan_threshold": self.current_policy.replan_threshold,
            "zero_progress_threshold": self.current_policy.zero_progress_threshold,
            "max_total_steps": self.current_policy.max_total_steps,
            "timeout_per_step_seconds": self.current_policy.timeout_per_step_seconds,
            "min_diversity_per_retry": self.current_policy.min_diversity_per_retry,
            "allow_partial_plan": self.current_policy.allow_partial_plan,
            "validate_before_execute": self.current_policy.validate_before_execute
        }
    
    def reset_policy(self):
        """Reset to default policy"""
        self.current_policy = PlannerPolicy()
        logger.info("🎯 Planner policy reset to defaults")


def create_planner_policy_adapter() -> PlannerPolicyAdapter:
    """Factory function"""
    return PlannerPolicyAdapter()
