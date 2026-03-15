"""
Failure Taxonomy - Evaluation-Driven Control System
==================================================

This module defines the classification system for all failure types.
Each failure is labeled with a specific type for targeted intervention.

Failure Categories:
- planning_failure: Issues in task planning and decomposition
- tool_selection_failure: Wrong tool chosen for task
- retrieval_failure: Memory/retrieval returns wrong results
- patch_failure: Self-modification produces poor patches
- verification_failure: Verifier gives wrong verdict
- recovery_failure: Agent cannot recover from errors
- thrash_failure: Agent stuck in retry loops
- latency_budget_failure: Task takes too long
- forbidden_edit_failure: Agent modified restricted files
"""
from enum import Enum
from typing import Dict, List, Optional
from dataclasses import dataclass, field


class FailureType(Enum):
    """Complete failure taxonomy for agent evaluation"""
    
    # Planning failures
    PLANNING_FAILURE = "planning_failure"
    PLANNING_TOO_COMPLEX = "planning_too_complex"
    PLANNING_ZERO_PROGRESS = "planning_zero_progress"
    PLANNING_REPLAN_TOO_MANY = "planning_replan_too_many"
    
    # Tool selection failures
    TOOL_SELECTION_FAILURE = "tool_selection_failure"
    TOOL_WRONG_CHOICE = "tool_wrong_choice"
    TOOL_MISSING = "tool_missing"
    TOOL_THRAASH = "tool_thraash"
    
    # Retrieval failures
    RETRIEVAL_FAILURE = "retrieval_failure"
    RETRIEVAL_IRRELEVANT = "retrieval_irrelevant"
    RETRIEVAL_LATE_DISCOVERY = "retrieval_late_discovery"
    RETRIEVAL_REDISCOVERY = "retrieval_rediscovery"
    
    # Patch failures
    PATCH_FAILURE = "patch_failure"
    PATCH_INCORRECT = "patch_incorrect"
    PATCH_INCOMPLETE = "patch_incomplete"
    PATCH_REGRESSION = "patch_regression"
    PATCH_SELF_DAMAGE = "patch_self_damage"
    
    # Verification failures
    VERIFICATION_FAILURE = "verification_failure"
    VERIFICATION_FALSE_POSITIVE = "verification_false_positive"
    VERIFICATION_FALSE_NEGATIVE = "verification_false_negative"
    VERIFICATION_TIMEOUT = "verification_timeout"
    
    # Recovery failures
    RECOVERY_FAILURE = "recovery_failure"
    RECOVERY_NO_STRATEGY = "recovery_no_strategy"
    RECOVERY_WRONG_STRATEGY = "recovery_wrong_strategy"
    
    # Thrash failures
    THRASH_FAILURE = "thrash_failure"
    THRASH_RETRY_SAME = "thrash_retry_same"
    THRASH_INFINITE_LOOP = "thrash_infinite_loop"
    THRASH_NO_PROGRESS = "thrash_no_progress"
    
    # Latency failures
    LATENCY_FAILURE = "latency_failure"
    LATENCY_TIMEOUT = "latency_timeout"
    LATENCY_OVER_BUDGET = "latency_over_budget"
    
    # Security failures
    FORBIDDEN_EDIT_FAILURE = "forbidden_edit_failure"
    FORBIDDEN_PATH_ACCESS = "forbidden_path_access"
    FORBIDDEN_OPERATION = "forbidden_operation"


class FailureSeverity(Enum):
    """Severity levels for failure prioritization"""
    CRITICAL = "critical"   # System cannot continue
    HIGH = "high"           # Major capability broken
    MEDIUM = "medium"       # Significant degradation
    LOW = "low"             # Minor issue
    INFO = "info"           # Near-optimal


class Subsystem(Enum):
    """Agent subsystems that can have failures"""
    PLANNER = "planner"
    TOOL_ROUTER = "tool_router"
    MEMORY = "memory"
    RETRIEVAL = "retrieval"
    BENCHMARK = "benchmark"
    VERIFIER = "verifier"
    SELF_IMPROVEMENT = "self_improvement"
    TOOL_FACTORY = "tool_factory"
    LEARNING = "learning"
    EXECUTOR = "executor"
    BROWSER = "browser"
    SANDBOX = "sandbox"


@dataclass
class FailureEvidence:
    """Evidence supporting a failure classification"""
    evidence_type: str  # "log", "trace", "telemetry", "diff"
    description: str
    location: Optional[str] = None
    timestamp: Optional[float] = None
    raw_data: Optional[Dict] = None


@dataclass
class FailureLabel:
    """
    Complete failure label with full diagnosis
    
    This is the CORE output of FailureAnalyzer.
    """
    failure_type: FailureType
    severity: FailureSeverity
    
    # Classification confidence
    confidence: float  # 0-1
    
    # Root cause vs symptom
    is_root_cause: bool
    
    # Evidence
    evidence: List[FailureEvidence] = field(default_factory=list)
    
    # Affected subsystems
    affected_subsystems: List[Subsystem] = field(default_factory=list)
    
    # Failed capability
    failed_capability: Optional[str] = None
    
    # Error details
    error_message: Optional[str] = None
    error_location: Optional[str] = None
    
    # Context
    task_id: Optional[str] = None
    session_id: Optional[str] = None
    timestamp: float = field(default_factory=lambda: __import__("time").time())
    
    # Recommendations
    suggested_interventions: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "failure_type": self.failure_type.value,
            "severity": self.severity.value,
            "confidence": self.confidence,
            "is_root_cause": self.is_root_cause,
            "evidence": [
                {
                    "type": e.evidence_type,
                    "description": e.description,
                    "location": e.location
                } for e in self.evidence
            ],
            "affected_subsystems": [s.value for s in self.affected_subsystems],
            "failed_capability": self.failed_capability,
            "error_message": self.error_message,
            "task_id": self.task_id,
            "timestamp": self.timestamp,
            "suggested_interventions": self.suggested_interventions
        }


# Capability definitions for heatmap
CAPABILITY_TAXONOMY = {
    "planning": {
        "display_name": "Task Planning",
        "description": "Ability to decompose complex tasks",
        "benchmarks": ["planner_efficiency", "task_decomposition", "milestone_achievement"]
    },
    "retrieval": {
        "display_name": "Information Retrieval",
        "description": "Finding relevant information",
        "benchmarks": ["memory_accuracy", "file_discovery", "context_retrieval"]
    },
    "patching": {
        "display_name": "Self-Patching",
        "description": "Improving own code",
        "benchmarks": ["self_mod", "patch_quality", "regression_avoidance"]
    },
    "browser_recovery": {
        "display_name": "Browser Recovery",
        "description": "Recovering from browser issues",
        "benchmarks": ["browser_stability", "selector_repair", "page_load_retry"]
    },
    "tool_routing": {
        "display_name": "Tool Routing",
        "description": "Selecting appropriate tools",
        "benchmarks": ["tool_selection_accuracy", "tool_effectiveness", "routing_efficiency"]
    },
    "self_mod_safety": {
        "display_name": "Self-Mod Safety",
        "description": "Safe self-modification",
        "benchmarks": ["safety_compliance", "forbidden_path_avoidance", "rollback_safety"]
    },
    "code_generation": {
        "display_name": "Code Generation",
        "description": "Writing correct code",
        "benchmarks": ["coding_correctness", "code_quality", "test_coverage"]
    },
    "debugging": {
        "display_name": "Debugging",
        "description": "Finding and fixing bugs",
        "benchmarks": ["bug_localization", "root_cause_analysis", "fix_effectiveness"]
    },
    "verification": {
        "display_name": "Verification",
        "description": "Verifying correctness",
        "benchmarks": ["verifier_accuracy", "false_positive_rate", "false_negative_rate"]
    },
    "tool_creation": {
        "display_name": "Tool Creation",
        "description": "Creating new tools",
        "benchmarks": ["tool_design", "tool_quality", "downstream_improvement"]
    },
    "learning": {
        "display_name": "Learning",
        "description": "Learning from feedback",
        "benchmarks": ["lesson_extraction", "knowledge_refresh", "adaptation_speed"]
    },
    "coordination": {
        "display_name": "Multi-Task Coordination",
        "description": "Managing multiple tasks",
        "benchmarks": ["parallel_efficiency", "resource_allocation", "priority_handling"]
    }
}


def get_failure_patterns() -> Dict[FailureType, Dict]:
    """
    Get known failure patterns for quick classification
    
    Returns patterns that help identify failure types from traces
    """
    return {
        FailureType.PLANNING_ZERO_PROGRESS: {
            "indicators": ["no_progress_after_10_steps", "same_state_repeated"],
            "evidence_types": ["trace", "telemetry"],
            "suggested_fix": "early_checkpoint_mandate"
        },
        FailureType.TOOL_WRONG_CHOICE: {
            "indicators": ["wrong_tool_selected", "tool_effective_but_unused"],
            "evidence_types": ["tool_call_log", "telemetry"],
            "suggested_fix": "routing_weight_update"
        },
        FailureType.RETRIEVAL_IRRELEVANT: {
            "indicators": ["irrelevant_files_top", "low_relevance_scores"],
            "evidence_types": ["retrieval_log", "benchmark_result"],
            "suggested_fix": "retrieval_rerank_tuning"
        },
        FailureType.THRASH_RETRY_SAME: {
            "indicators": ["same_error_repeated", "approach_not_diversified"],
            "evidence_types": ["trace", "telemetry"],
            "suggested_fix": "retry_diversification_rule"
        },
        FailureType.PATCH_REGRESSION: {
            "indicators": ["tests_failed_after_patch", "new_errors_appeared"],
            "evidence_types": ["test_result", "diff_analysis"],
            "suggested_fix": "regression_test_mandate"
        },
        FailureType.LATENCY_TIMEOUT: {
            "indicators": ["task_timeout", "budget_exceeded"],
            "evidence_types": ["telemetry", "benchmark_result"],
            "suggested_fix": "timeout_budget_tightening"
        },
        FailureType.FORBIDDEN_EDIT_FAILURE: {
            "indicators": ["modified_restricted_file", "bypassed_security"],
            "evidence_types": ["diff", "audit_log"],
            "suggested_fix": "safety_policy_hardening"
        }
    }


def get_subsystem_for_failure(failure_type: FailureType) -> List[Subsystem]:
    """Map failure types to affected subsystems"""
    mapping = {
        FailureType.PLANNING_FAILURE: [Subsystem.PLANNER],
        FailureType.PLANNING_ZERO_PROGRESS: [Subsystem.PLANNER],
        FailureType.TOOL_SELECTION_FAILURE: [Subsystem.TOOL_ROUTER, Subsystem.EXECUTOR],
        FailureType.RETRIEVAL_FAILURE: [Subsystem.MEMORY, Subsystem.RETRIEVAL],
        FailureType.PATCH_FAILURE: [Subsystem.SELF_IMPROVEMENT],
        FailureType.VERIFICATION_FAILURE: [Subsystem.BENCHMARK, Subsystem.VERIFIER],
        FailureType.RECOVERY_FAILURE: [Subsystem.EXECUTOR, Subsystem.PLANNER],
        FailureType.THRASH_FAILURE: [Subsystem.PLANNER, Subsystem.TOOL_ROUTER],
        FailureType.LATENCY_FAILURE: [Subsystem.PLANNER, Subsystem.EXECUTOR],
        FailureType.FORBIDDEN_EDIT_FAILURE: [Subsystem.SANDBOX, Subsystem.SELF_IMPROVEMENT]
    }
    return mapping.get(failure_type, [Subsystem.PLANNER])


def get_intervention_for_failure(failure_type: FailureType) -> str:
    """Get suggested intervention for failure type"""
    interventions = {
        FailureType.PLANNING_FAILURE: "planner_policy_adapter:simplify_plans",
        FailureType.TOOL_SELECTION_FAILURE: "routing_tuner:update_weights",
        FailureType.RETRIEVAL_FAILURE: "retrieval_tuner:rerank_adjustment",
        FailureType.PATCH_FAILURE: "patch_impact_analyzer:review_before_promote",
        FailureType.VERIFICATION_FAILURE: "verifier_calibration:adjust_thresholds",
        FailureType.RECOVERY_FAILURE: "recovery_strategy:inventory_update",
        FailureType.THRASH_FAILURE: "retry_budget_tuner:reduce_diversify",
        FailureType.LATENCY_FAILURE: "planner_policy_adapter:tighten_budget",
        FailureType.FORBIDDEN_EDIT_FAILURE: "safety_policy:harden_restrictions"
    }
    return interventions.get(failure_type, "generic_review")
