"""
Meta Controller - Evaluation-Driven Control System
================================================

The MetaController is the highest-level component that orchestrates the entire
feedback loop between benchmark evaluation and agent improvement.

It:
1. Receives benchmark results
2. Runs failure analysis
3. Updates capability heatmap
4. Manages intervention queue
5. Coordinates tuners
6. Makes high-level decisions about what to fix next
"""
import logging
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

from .failure_analyzer import FailureAnalyzer, create_failure_analyzer
from .capability_heatmap import CapabilityHeatmap, create_capability_heatmap
from .intervention_queue import InterventionQueue, InterventionType, create_intervention_queue

logger = logging.getLogger(__name__)


@dataclass
class ControlDecision:
    """High-level decision from meta-controller"""
    decision_id: str
    decision_type: str  # "execute_intervention", "wait", "escalate"
    target: Optional[str]  # intervention_id or subsystem
    reason: str
    expected_impact: float
    risk_level: str  # "low", "medium", "high"
    timestamp: float = field(default_factory=time.time)


@dataclass
class FeedbackLoopState:
    """Current state of the feedback loop"""
    last_benchmark_time: float = 0.0
    last_analysis_time: float = 0.0
    total_failures_analyzed: int = 0
    total_interventions_executed: int = 0
    loop_iterations: int = 0


class MetaController:
    """
    ADVANCED Meta-Controller that orchestrates the complete feedback loop.
    
    This is the "brain" of the evaluation-driven control system:
    - Input: benchmark results, telemetry
    - Output: actionable decisions for improvement
    
    The feedback loop:
    1. Benchmark/task runs
    2. Telemetry + results collected
    3. FailureAnalyzer diagnoses issues
    4. CapabilityHeatmap updates
    5. InterventionQueue generates candidates
    6. Tuners apply fixes
    7. Re-evaluate
    8. Promote or rollback
    """
    
    def __init__(self):
        # Core components
        self.failure_analyzer = create_failure_analyzer()
        self.capability_heatmap = create_capability_heatmap()
        self.intervention_queue = create_intervention_queue()
        
        # State
        self.state = FeedbackLoopState()
        
        # Decision history
        self.decision_history: List[ControlDecision] = []
        
        # Configuration
        self.min_interval_seconds = 10  # Min time between feedback cycles
        self.max_interventions_per_cycle = 3
        self.high_priority_threshold = 0.7
        
        # External connections (will be set by main.py)
        self.planner_adapter = None
        self.routing_tuner = None
        self.retrieval_tuner = None
        self.self_improvement = None
        self.tool_factory = None
        
        logger.info("🧠 MetaController initialized - ADVANCED feedback loop ENABLED")
    
    def connect_tuners(
        self,
        planner_adapter=None,
        routing_tuner=None,
        retrieval_tuner=None,
        self_improvement=None,
        tool_factory=None
    ):
        """Connect to external tuner components"""
        self.planner_adapter = planner_adapter
        self.routing_tuner = routing_tuner
        self.retrieval_tuner = retrieval_tuner
        self.self_improvement = self_improvement
        self.tool_factory = tool_factory
        
        logger.info("🧠 MetaController connected to tuners")
    
    def process_benchmark_result(
        self,
        benchmark_result: Dict,
        trace: Optional[List] = None,
        telemetry: Optional[Dict] = None
    ) -> ControlDecision:
        """
        Process a benchmark result through the feedback loop.
        
        This is the main entry point for benchmark integration.
        """
        start_time = time.time()
        
        logger.info("🔄 Processing benchmark result through feedback loop...")
        
        # Step 1: Update state
        self.state.last_benchmark_time = time.time()
        self.state.loop_iterations += 1
        
        # Step 2: Analyze failure
        failure_label = self.failure_analyzer.analyze(
            benchmark_result=benchmark_result,
            trace=trace,
            telemetry=telemetry
        )
        
        self.state.last_analysis_time = time.time()
        self.state.total_failures_analyzed += 1
        
        # Step 3: Update capability heatmap
        self.capability_heatmap.update_from_benchmark_result(benchmark_result)
        self.capability_heatmap.update_from_failure_label(failure_label.to_dict())
        
        # Step 4: Generate interventions
        interventions = self.intervention_queue.add_intervention_from_failure(
            failure_label=failure_label.to_dict(),
            suggested_interventions=failure_label.suggested_interventions
        )
        
        # Step 5: Make decision
        decision = self._make_decision(interventions)
        
        # Step 6: Execute if approved
        if decision.decision_type == "execute_intervention":
            self._execute_intervention(decision.target)
        
        # Log timing
        elapsed = time.time() - start_time
        logger.info(f"✅ Feedback loop completed in {elapsed:.2f}s")
        
        return decision
    
    def _make_decision(self, interventions: List) -> ControlDecision:
        """Make a decision about what to do next"""
        
        # Get top intervention
        top = self.intervention_queue.get_top_intervention()
        
        if not top:
            # No pending interventions
            return ControlDecision(
                decision_id=f"dec_{len(self.decision_history)}",
                decision_type="wait",
                target=None,
                reason="No pending interventions",
                expected_impact=0.0,
                risk_level="low"
            )
        
        # Check priority
        if top.priority_score < self.high_priority_threshold:
            return ControlDecision(
                decision_id=f"dec_{len(self.decision_history)}",
                decision_type="wait",
                target=None,
                reason=f"Top intervention priority too low ({top.priority_score:.2f})",
                expected_impact=top.expected_gain,
                risk_level="low"
            )
        
        # Check risk
        risk_level = "low"
        if top.regression_risk > 0.4:
            risk_level = "high"
        elif top.regression_risk > 0.2:
            risk_level = "medium"
        
        # Approve intervention
        self.intervention_queue.approve_intervention(top.intervention_id)
        
        decision = ControlDecision(
            decision_id=f"dec_{len(self.decision_history)}",
            decision_type="execute_intervention",
            target=top.intervention_id,
            reason=f"High priority intervention: {top.intervention_type.value}",
            expected_impact=top.expected_gain,
            risk_level=risk_level
        )
        
        self.decision_history.append(decision)
        
        logger.info(f"🧠 Decision: {decision.decision_type} - {decision.reason}")
        
        return decision
    
    def _execute_intervention(self, intervention_id: str) -> bool:
        """Execute an approved intervention"""
        
        intervention = self.intervention_queue.interventions.get(intervention_id)
        if not intervention:
            return False
        
        logger.info(f"⚡ Executing intervention: {intervention_id}")
        
        # Route to appropriate tuner
        success = False
        actual_gain = None
        
        if intervention.target_subsystem == "planner" and self.planner_adapter:
            # Apply planner adjustment
            success = True
            # Actual implementation would call planner_adapter
            
        elif intervention.target_subsystem == "tool_router" and self.routing_tuner:
            # Apply routing adjustment
            success = True
            # Actual implementation would call routing_tuner
            
        elif intervention.target_subsystem == "memory" and self.retrieval_tuner:
            # Apply retrieval adjustment
            success = True
            # Actual implementation would call retrieval_tuner
            
        elif intervention.intervention_type == InterventionType.SELF_PATCH_PROPOSAL:
            # Generate self-patch proposal
            success = True
            # Would trigger self-improvement pipeline
            
        elif intervention.intervention_type == InterventionType.NEW_TOOL_PROPOSAL:
            # Trigger tool creation
            success = True
            # Would trigger tool_factory
        
        # Mark as executed
        self.intervention_queue.mark_executed(
            intervention_id=intervention_id,
            actual_gain=actual_gain,
            failed=not success
        )
        
        if success:
            self.state.total_interventions_executed += 1
        
        return success
    
    def run_feedback_cycle(self) -> ControlDecision:
        """
        Run a complete feedback cycle.
        
        Called periodically to process any pending work.
        """
        # Check if enough time has passed
        if time.time() - self.state.last_benchmark_time < self.min_interval_seconds:
            return ControlDecision(
                decision_id=f"dec_{len(self.decision_history)}",
                decision_type="wait",
                target=None,
                reason="Too soon since last benchmark",
                expected_impact=0.0,
                risk_level="low"
            )
        
        # Get top intervention
        top = self.intervention_queue.get_top_intervention()
        
        if not top:
            return ControlDecision(
                decision_id=f"dec_{len(self.decision_history)}",
                decision_type="wait",
                target=None,
                reason="No interventions pending",
                expected_impact=0.0,
                risk_level="low"
            )
        
        # Make and execute decision
        decision = self._make_decision([top])
        
        if decision.decision_type == "execute_intervention":
            self._execute_intervention(decision.target)
        
        return decision
    
    def get_system_status(self) -> Dict:
        """Get comprehensive system status"""
        return {
            "state": {
                "last_benchmark_time": self.state.last_benchmark_time,
                "last_analysis_time": self.state.last_analysis_time,
                "total_failures_analyzed": self.state.total_failures_analyzed,
                "total_interventions_executed": self.state.total_interventions_executed,
                "loop_iterations": self.state.loop_iterations
            },
            "failure_summary": self.failure_analyzer.get_failure_summary(),
            "capability_report": self.capability_heatmap.get_capability_report(),
            "intervention_queue": self.intervention_queue.get_queue_status(),
            "subsystem_health": self.failure_analyzer.get_subsystem_health()
        }
    
    def get_top_priority_capabilities(self, n: int = 3) -> List[Dict]:
        """Get top capabilities that need attention"""
        return self.capability_heatmap.get_top_priority_capabilities(n)
    
    def get_recommended_actions(self) -> List[Dict]:
        """Get recommended next actions"""
        actions = []
        
        # Get top priorities
        priorities = self.capability_heatmap.get_top_priority_capabilities(5)
        for p in priorities:
            actions.append({
                "type": "capability_improvement",
                "target": p["capability_id"],
                "reason": p["reason"],
                "priority": p["priority"]
            })
        
        # Get top interventions
        queue_status = self.intervention_queue.get_queue_status()
        for干预 in queue_status.get("top_pending", [])[:3]:
            actions.append({
                "type": "intervention",
                "target":干预["intervention_id"],
                "reason":干预["description"],
                "priority":干预["priority_score"]
            })
        
        # Sort by priority
        actions.sort(key=lambda a: a.get("priority", 0), reverse=True)
        
        return actions


def create_meta_controller() -> MetaController:
    """Factory function to create MetaController"""
    return MetaController()
