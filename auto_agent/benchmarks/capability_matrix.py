"""
OmniAgent X - Capability Matrix & Suite Architecture
===================================================
World-class benchmark coverage for No1 autonomous coder.

This module provides:
- Capability taxonomy (12+ capabilities)
- Suite architecture (8 suites)
- Task metadata (tags, weight, difficulty)
- Score weighting system
- Coverage analyzer

The key question this answers:
    "Agent real software engineering va autonomy spektrining 
    qaysi qatlamlarida, qanday barqarorlik bilan, 
    qanday xarajat bilan, qaysi failure mode'lar ostida ishlayapti?"
"""
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Set
from collections import defaultdict


# ==================== CAPABILITY TAXONOMY ====================

class Capability(str, Enum):
    """
    Core capabilities that world-class autonomous coder must have.
    """
    # Understanding
    REPO_COMPREHENSION = "repo_comprehension"
    BUG_LOCALIZATION = "bug_localization"
    CODE_UNDERSTANDING = "code_understanding"
    
    # Action
    MULTI_FILE_PATCHING = "multi_file_patching"
    TEST_WRITING = "test_writing"
    TEST_REPAIR = "test_repair"
    REFACTORING = "refactoring"
    
    # Tools
    TERMINAL_OPS = "terminal_ops"
    BROWSER_AUTOMATION = "browser_automation"
    TOOL_CREATION = "tool_creation"
    TOOL_USE = "tool_use"
    
    # Advanced
    LONG_HORIZON_ORCHESTRATION = "long_horizon_orchestration"
    RECOVERY = "recovery"
    SELF_MODIFICATION = "self_modification"
    SELF_IMPROVEMENT = "self_improvement"
    
    # Knowledge
    KNOWLEDGE_REFRESH = "knowledge_refresh"
    SOURCE_VALIDATION = "source_validation"
    
    # Efficiency
    EFFICIENCY = "efficiency"
    PLANNING = "planning"
    MEMORY_USE = "memory_use"


class Environment(str, Enum):
    """
    Execution environments.
    """
    CODE_REPO = "code_repo"
    TERMINAL = "terminal"
    BROWSER = "browser"
    DESKTOP = "desktop"
    LOCAL_SERVICE = "local_service"
    LONG_HORIZON_WORKSPACE = "long_horizon_workspace"
    SELF_MODIFICATION_SANDBOX = "self_modification_sandbox"
    API = "api"


class Difficulty(str, Enum):
    """
    Task difficulty levels.
    """
    EASY = "easy"      # x1 weight
    MEDIUM = "medium"   # x2 weight
    HARD = "hard"      # x4 weight
    FRONTIER = "frontier"  # x6 weight


# ==================== TASK METADATA ====================

@dataclass
class TaskMetadata:
    """
    Rich metadata for every benchmark task.
    
    This enables:
    - Capability mapping
    - Difficulty-based scoring
    - Coverage analysis
    - Weighted leaderboards
    """
    task_id: str
    suite: str
    
    # Capabilities (multiple allowed)
    capabilities: List[str]
    
    # Environment
    environments: List[str]
    
    # Difficulty
    difficulty: str = Difficulty.EASY.value
    
    # Scoring
    weight: float = 1.0
    
    # Metrics
    primary_metric: str = "capability_score"
    secondary_metrics: List[str] = field(default_factory=list)
    
    # Additional
    tags: List[str] = field(default_factory=list)
    description: str = ""
    
    # Failure injection
    failure_modes: List[str] = field(default_factory=list)
    recovery_required: bool = False
    
    # Anti-reward-hacking
    hidden_verifier: bool = False
    adversarial: bool = False
    
    def get_weight(self) -> float:
        """Get weighted score multiplier"""
        difficulty_weights = {
            Difficulty.EASY.value: 1.0,
            Difficulty.MEDIUM.value: 2.0,
            Difficulty.HARD.value: 4.0,
            Difficulty.FRONTIER.value: 6.0
        }
        return difficulty_weights.get(self.difficulty, 1.0) * self.weight


# ==================== SUITE DEFINITIONS ====================

class SuiteDefinition:
    """
    Definition of a benchmark suite.
    """
    
    REPO_ENGINEERING = "repo_engineering"
    BUG_LOCALIZATION_REPAIR = "bug_localization_repair"
    TERMINAL_OPERATIONS = "terminal_operations"
    BROWSER_WORKFLOW = "browser_workflow"
    LONG_HORIZON_ORCHESTRATION = "long_horizon_orchestration"
    TOOL_CREATION_USE = "tool_creation_use"
    SELF_MODIFICATION = "self_modification"
    KNOWLEDGE_REFRESH = "knowledge_refresh"
    
    @classmethod
    def get_all_suites(cls) -> List[str]:
        return [
            cls.REPO_ENGINEERING,
            cls.BUG_LOCALIZATION_REPAIR,
            cls.TERMINAL_OPERATIONS,
            cls.BROWSER_WORKFLOW,
            cls.LONG_HORIZON_ORCHESTRATION,
            cls.TOOL_CREATION_USE,
            cls.SELF_MODIFICATION,
            cls.KNOWLEDGE_REFRESH
        ]
    
    @classmethod
    def get_suite_capabilities(cls, suite: str) -> List[str]:
        """Get capabilities for a suite"""
        suite_capabilities = {
            cls.REPO_ENGINEERING: [
                Capability.REPO_COMPREHENSION,
                Capability.MULTI_FILE_PATCHING,
                Capability.REFACTORING,
                Capability.TEST_REPAIR,
            ],
            cls.BUG_LOCALIZATION_REPAIR: [
                Capability.BUG_LOCALIZATION,
                Capability.CODE_UNDERSTANDING,
                Capability.MULTI_FILE_PATCHING,
                Capability.RECOVERY,
            ],
            cls.TERMINAL_OPERATIONS: [
                Capability.TERMINAL_OPS,
                Capability.PLANNING,
                Capability.EFFICIENCY,
            ],
            cls.BROWSER_WORKFLOW: [
                Capability.BROWSER_AUTOMATION,
                Capability.RECOVERY,
            ],
            cls.LONG_HORIZON_ORCHESTRATION: [
                Capability.LONG_HORIZON_ORCHESTRATION,
                Capability.PLANNING,
                Capability.RECOVERY,
                Capability.MEMORY_USE,
            ],
            cls.TOOL_CREATION_USE: [
                Capability.TOOL_CREATION,
                Capability.TOOL_USE,
                Capability.PLANNING,
            ],
            cls.SELF_MODIFICATION: [
                Capability.SELF_MODIFICATION,
                Capability.SELF_IMPROVEMENT,
                Capability.RECOVERY,
            ],
            cls.KNOWLEDGE_REFRESH: [
                Capability.KNOWLEDGE_REFRESH,
                Capability.SOURCE_VALIDATION,
            ],
        }
        return suite_capabilities.get(suite, [])


# ==================== SUITE TASK DEFINITIONS ====================

# Minimal task definitions for each suite
# These serve as templates - actual fixtures needed

SUITE_TASK_TEMPLATES = {
    SuiteDefinition.REPO_ENGINEERING: [
        # Easy (1-2 files)
        {
            "id": "repo_onboarding_v1",
            "name": "Codebase Onboarding",
            "capabilities": [Capability.REPO_COMPREHENSION],
            "difficulty": Difficulty.EASY,
            "weight": 1.0,
            "description": "Understand codebase structure and find relevant files"
        },
        {
            "id": "single_file_patch_v1",
            "name": "Single File Patch",
            "capabilities": [Capability.MULTI_FILE_PATCHING],
            "difficulty": Difficulty.EASY,
            "weight": 1.0,
            "description": "Patch a single file correctly"
        },
        # Medium (3-5 files + tests)
        {
            "id": "multi_file_refactor_v1",
            "name": "Multi-File Refactor",
            "capabilities": [Capability.MULTI_FILE_PATCHING, Capability.REFACTORING],
            "difficulty": Difficulty.MEDIUM,
            "weight": 2.0,
            "description": "Refactor across multiple files with tests"
        },
        {
            "id": "test_update_v1",
            "name": "Test Update",
            "capabilities": [Capability.TEST_REPAIR, Capability.CODE_UNDERSTANDING],
            "difficulty": Difficulty.MEDIUM,
            "weight": 2.0,
            "description": "Update tests while preserving intent"
        },
        # Hard (repo-level + env issues)
        {
            "id": "env_dependency_fix_v1",
            "name": "Environment Dependency Fix",
            "capabilities": [Capability.TERMINAL_OPS, Capability.REPO_COMPREHENSION],
            "difficulty": Difficulty.HARD,
            "weight": 4.0,
            "description": "Fix dependency hell in codebase"
        },
        # Frontier (ambiguity + recovery)
    ],
    
    SuiteDefinition.BUG_LOCALIZATION_REPAIR: [
        # Easy
        {
            "id": "clear_bug_fix_v1",
            "name": "Clear Bug Fix",
            "capabilities": [Capability.CODE_UNDERSTANDING, Capability.MULTI_FILE_PATCHING],
            "difficulty": Difficulty.EASY,
            "weight": 1.0,
            "description": "Fix clearly described bug"
        },
        # Medium
        {
            "id": "unclear_symptom_v1",
            "name": "Unclear Symptom Localization",
            "capabilities": [Capability.BUG_LOCALIZATION, Capability.CODE_UNDERSTANDING],
            "difficulty": Difficulty.MEDIUM,
            "weight": 2.0,
            "description": "Find root cause from vague symptom"
        },
        {
            "id": "log_analysis_v1",
            "name": "Log Analysis & Bug Finding",
            "capabilities": [Capability.BUG_LOCALIZATION, Capability.RECOVERY],
            "difficulty": Difficulty.MEDIUM,
            "weight": 2.0,
            "description": "Analyze logs to find bug"
        },
        # Hard
        {
            "id": "hidden_root_cause_v1",
            "name": "Hidden Root Cause",
            "capabilities": [Capability.BUG_LOCALIZATION, Capability.MULTI_FILE_PATCHING, Capability.RECOVERY],
            "difficulty": Difficulty.HARD,
            "weight": 4.0,
            "description": "Find and fix hidden root cause across files"
        },
        {
            "id": "flaky_test_repair_v1",
            "name": "Flaky Test Repair",
            "capabilities": [Capability.BUG_LOCALIZATION, Capability.TEST_REPAIR],
            "difficulty": Difficulty.HARD,
            "weight": 4.0,
            "description": "Fix flaky test while preserving test intent"
        },
    ],
    
    SuiteDefinition.TERMINAL_OPERATIONS: [
        {
            "id": "cli_fluency_v1",
            "name": "CLI Fluency",
            "capabilities": [Capability.TERMINAL_OPS],
            "difficulty": Difficulty.EASY,
            "weight": 1.0,
            "description": "Execute complex CLI operations"
        },
        {
            "id": "build_fix_v1",
            "name": "Build Fix",
            "capabilities": [Capability.TERMINAL_OPS, Capability.CODE_UNDERSTANDING],
            "difficulty": Difficulty.MEDIUM,
            "weight": 2.0,
            "description": "Fix build errors"
        },
        {
            "id": "test_selection_v1",
            "name": "Test Selection",
            "capabilities": [Capability.TERMINAL_OPS, Capability.PLANNING],
            "difficulty": Difficulty.MEDIUM,
            "weight": 2.0,
            "description": "Select and run relevant tests"
        },
        {
            "id": "script_orchestration_v1",
            "name": "Script Orchestration",
            "capabilities": [Capability.TERMINAL_OPS, Capability.PLANNING],
            "difficulty": Difficulty.HARD,
            "weight": 4.0,
            "description": "Orchestrate multiple scripts"
        },
    ],
    
    SuiteDefinition.BROWSER_WORKFLOW: [
        {
            "id": "auth_flow_v1",
            "name": "Authentication Flow",
            "capabilities": [Capability.BROWSER_AUTOMATION],
            "difficulty": Difficulty.MEDIUM,
            "weight": 2.0,
            "description": "Complete auth flow"
        },
        {
            "id": "multi_step_form_v1",
            "name": "Multi-Step Form",
            "capabilities": [Capability.BROWSER_AUTOMATION, Capability.RECOVERY],
            "difficulty": Difficulty.MEDIUM,
            "weight": 2.0,
            "description": "Fill multi-page form with validation"
        },
        {
            "id": "brittle_selector_recovery_v1",
            "name": "Brittle Selector Recovery",
            "capabilities": [Capability.BROWSER_AUTOMATION, Capability.RECOVERY],
            "difficulty": Difficulty.HARD,
            "weight": 4.0,
            "description": "Handle selector failures gracefully"
        },
        {
            "id": "stateful_workflow_v1",
            "name": "Stateful Workflow",
            "capabilities": [Capability.BROWSER_AUTOMATION, Capability.PLANNING],
            "difficulty": Difficulty.HARD,
            "weight": 4.0,
            "description": "Complete complex stateful workflow"
        },
    ],
    
    SuiteDefinition.LONG_HORIZON_ORCHESTRATION: [
        {
            "id": "checkpoint_recovery_v1",
            "name": "Checkpoint & Recovery",
            "capabilities": [Capability.LONG_HORIZON_ORCHESTRATION, Capability.RECOVERY],
            "difficulty": Difficulty.MEDIUM,
            "weight": 2.0,
            "description": "Task with checkpoint and recovery"
        },
        {
            "id": "multi_step_ordered_v1",
            "name": "Ordered Multi-Step",
            "capabilities": [Capability.LONG_HORIZON_ORCHESTRATION, Capability.PLANNING],
            "difficulty": Difficulty.MEDIUM,
            "weight": 2.0,
            "description": "Complete ordered multi-step task"
        },
        {
            "id": "interruption_handling_v1",
            "name": "Interruption Handling",
            "capabilities": [Capability.LONG_HORIZON_ORCHESTRATION, Capability.RECOVERY, Capability.MEMORY_USE],
            "difficulty": Difficulty.HARD,
            "weight": 4.0,
            "description": "Handle mid-task interruption"
        },
        {
            "id": "final_deliverable_v1",
            "name": "Final Deliverable",
            "capabilities": [Capability.LONG_HORIZON_ORCHESTRATION, Capability.PLANNING],
            "difficulty": Difficulty.FRONTIER,
            "weight": 6.0,
            "description": "Produce final deliverable with multiple subtasks"
        },
    ],
    
    SuiteDefinition.TOOL_CREATION_USE: [
        {
            "id": "tool_use_v1",
            "name": "Tool Use",
            "capabilities": [Capability.TOOL_USE],
            "difficulty": Difficulty.EASY,
            "weight": 1.0,
            "description": "Use existing tools effectively"
        },
        {
            "id": "tool_creation_v1",
            "name": "Tool Creation",
            "capabilities": [Capability.TOOL_CREATION, Capability.PLANNING],
            "difficulty": Difficulty.HARD,
            "weight": 4.0,
            "description": "Create new tool to solve task"
        },
        {
            "id": "tool_chain_v1",
            "name": "Tool Chain",
            "capabilities": [Capability.TOOL_CREATION, Capability.TOOL_USE, Capability.PLANNING],
            "difficulty": Difficulty.FRONTIER,
            "weight": 6.0,
            "description": "Create tool chain for complex task"
        },
    ],
    
    SuiteDefinition.SELF_MODIFICATION: [
        {
            "id": "self_patch_v1",
            "name": "Self Patch",
            "capabilities": [Capability.SELF_MODIFICATION],
            "difficulty": Difficulty.HARD,
            "weight": 4.0,
            "description": "Modify own code safely"
        },
        {
            "id": "benchmark_improve_v1",
            "name": "Benchmark Improvement",
            "capabilities": [Capability.SELF_MODIFICATION, Capability.SELF_IMPROVEMENT],
            "difficulty": Difficulty.FRONTIER,
            "weight": 6.0,
            "description": "Improve benchmark and verify"
        },
    ],
    
    SuiteDefinition.KNOWLEDGE_REFRESH: [
        {
            "id": "source_lookup_v1",
            "name": "Source Lookup",
            "capabilities": [Capability.SOURCE_VALIDATION],
            "difficulty": Difficulty.MEDIUM,
            "weight": 2.0,
            "description": "Find and validate source information"
        },
        {
            "id": "knowledge_update_v1",
            "name": "Knowledge Update",
            "capabilities": [Capability.KNOWLEDGE_REFRESH, Capability.SOURCE_VALIDATION],
            "difficulty": Difficulty.HARD,
            "weight": 4.0,
            "description": "Update knowledge with citations"
        },
    ],
}


# ==================== WEIGHTED SCORING ====================

class WeightedScorer:
    """
    Computes weighted scores based on task metadata.
    """
    
    def __init__(self):
        self.difficulty_multipliers = {
            Difficulty.EASY.value: 1.0,
            Difficulty.MEDIUM.value: 2.0,
            Difficulty.HARD.value: 4.0,
            Difficulty.FRONTIER.value: 6.0,
        }
    
    def compute_score(self, raw_score: float, metadata: TaskMetadata) -> Dict[str, float]:
        """
        Compute weighted score.
        
        Returns:
            {
                "raw": float,
                "weighted": float,
                "difficulty_bonus": float
            }
        """
        difficulty_mult = self.difficulty_multipliers.get(metadata.difficulty, 1.0)
        
        return {
            "raw": raw_score,
            "weighted": raw_score * difficulty_mult * metadata.weight,
            "difficulty_bonus": difficulty_mult,
            "weight": metadata.weight
        }
    
    def aggregate_scores(self, scored_tasks: List[Dict]) -> Dict[str, float]:
        """
        Aggregate weighted scores across tasks.
        
        Returns:
            {
                "total_weighted": float,
                "total_raw": float,
                "pass_rate": float,
                "per_capability": {...},
                "per_suite": {...},
                "per_difficulty": {...}
            }
        """
        total_weighted = 0.0
        total_raw = 0.0
        
        per_capability = defaultdict(lambda: {"weighted": 0.0, "raw": 0.0, "count": 0})
        per_suite = defaultdict(lambda: {"weighted": 0.0, "raw": 0.0, "count": 0})
        per_difficulty = defaultdict(lambda: {"weighted": 0.0, "raw": 0.0, "count": 0})
        
        passed = 0
        
        for task in scored_tasks:
            weighted = task.get("weighted_score", 0)
            raw = task.get("raw_score", 0)
            capabilities = task.get("capabilities", [])
            suite = task.get("suite", "")
            difficulty = task.get("difficulty", "")
            
            total_weighted += weighted
            total_raw += raw
            
            if raw > 0:
                passed += 1
            
            for cap in capabilities:
                per_capability[cap]["weighted"] += weighted
                per_capability[cap]["raw"] += raw
                per_capability[cap]["count"] += 1
            
            per_suite[suite]["weighted"] += weighted
            per_suite[suite]["raw"] += raw
            per_suite[suite]["count"] += 1
            
            per_difficulty[difficulty]["weighted"] += weighted
            per_difficulty[difficulty]["raw"] += raw
            per_difficulty[difficulty]["count"] += 1
        
        pass_rate = passed / len(scored_tasks) if scored_tasks else 0
        
        return {
            "total_weighted": total_weighted,
            "total_raw": total_raw,
            "pass_rate": pass_rate,
            "total_tasks": len(scored_tasks),
            "per_capability": dict(per_capability),
            "per_suite": dict(per_suite),
            "per_difficulty": dict(per_difficulty),
        }


# ==================== COVERAGE ANALYZER ====================

class CoverageAnalyzer:
    """
    Analyzes benchmark coverage to identify gaps.
    """
    
    def __init__(self):
        self.all_capabilities = [c.value for c in Capability]
        self.all_environments = [e.value for e in Environment]
        self.all_suites = SuiteDefinition.get_all_suites()
    
    def analyze_coverage(self, registered_tasks: List[TaskMetadata]) -> Dict[str, Any]:
        """
        Analyze coverage across all dimensions.
        
        Returns:
            {
                "capabilities": {
                    "covered": [...],
                    "missing": [...]
                },
                "environments": {...},
                "suites": {...},
                "gaps": [...]
            }
        )
        """
        # Count per capability
        capability_counts = defaultdict(int)
        environment_counts = defaultdict(int)
        suite_counts = defaultdict(int)
        difficulty_counts = defaultdict(int)
        
        for task in registered_tasks:
            for cap in task.capabilities:
                capability_counts[cap] += 1
            for env in task.environments:
                environment_counts[env] += 1
            suite_counts[task.suite] += 1
            difficulty_counts[task.difficulty] += 1
        
        # Find covered vs missing
        covered_caps = set(capability_counts.keys())
        missing_caps = set(self.all_capabilities) - covered_caps
        
        covered_envs = set(environment_counts.keys())
        missing_envs = set(self.all_environments) - covered_envs
        
        # Generate gap analysis
        gaps = []
        
        if missing_caps:
            gaps.append({
                "type": "capability",
                "items": list(missing_caps),
                "severity": "high",
                "recommendation": "Add tasks for missing capabilities"
            })
        
        for suite in self.all_suites:
            if suite_counts[suite] < 3:
                gaps.append({
                    "type": "suite_coverage",
                    "suite": suite,
                    "current_count": suite_counts[suite],
                    "severity": "medium" if suite_counts[suite] > 0 else "high",
                    "recommendation": f"Need at least 3 tasks per suite (currently {suite_counts[suite]})"
                })
        
        # Difficulty distribution
        if difficulty_counts.get(Difficulty.FRONTIER.value, 0) < 2:
            gaps.append({
                "type": "difficulty",
                "severity": "medium",
                "recommendation": "Need more frontier-level tasks"
            })
        
        return {
            "capabilities": {
                "covered": list(covered_caps),
                "missing": list(missing_caps),
                "counts": dict(capability_counts)
            },
            "environments": {
                "covered": list(covered_envs),
                "missing": list(missing_envs),
                "counts": dict(environment_counts)
            },
            "suites": {
                "counts": dict(suite_counts)
            },
            "difficulty": {
                "counts": dict(difficulty_counts)
            },
            "gaps": gaps,
            "coverage_score": len(covered_caps) / len(self.all_capabilities) if self.all_capabilities else 0
        }
    
    def get_recommendations(self, coverage_analysis: Dict) -> List[str]:
        """Generate recommendations based on coverage analysis"""
        recommendations = []
        
        gaps = coverage_analysis.get("gaps", [])
        
        for gap in gaps:
            if gap["severity"] == "high":
                recommendations.append(f"URGENT: {gap['recommendation']}")
            elif gap["severity"] == "medium":
                recommendations.append(f"IMPORTANT: {gap['recommendation']}")
        
        return recommendations


# ==================== EFFICIENCY METRICS ====================

@dataclass
class EfficiencyMetrics:
    """
    Efficiency metrics for task execution.
    """
    wall_time_seconds: float = 0.0
    step_count: int = 0
    retry_count: int = 0
    failed_tool_calls: int = 0
    token_count: int = 0
    unnecessary_file_touches: int = 0
    
    def compute_efficiency_score(self) -> float:
        """
        Compute composite efficiency score (0-1, higher is better).
        """
        # Normalize metrics (inverse - lower is better)
        time_score = max(0, 1 - (self.wall_time_seconds / 300))  # 5 min = 0
        step_score = max(0, 1 - (self.step_count / 50))  # 50 steps = 0
        retry_score = max(0, 1 - (self.retry_count / 5))  # 5 retries = 0
        fail_score = max(0, 1 - (self.failed_tool_calls / 10))  # 10 fails = 0
        
        return (time_score + step_score + retry_score + fail_score) / 4


# ==================== FAILURE INJECTION ====================

class FailureMode(str, Enum):
    """Types of failures that can be injected"""
    TOOL_FAIL = "tool_fail"
    NETWORK_TIMEOUT = "network_timeout"
    FILE_LOCK = "file_lock"
    AMBIGUOUS_LOG = "ambiguous_log"
    SELECTOR_FAIL = "selector_fail"
    RUNTIME_CRASH = "runtime_crash"
    PERMISSION_DENIED = "permission_denied"


@dataclass
class FailureInjection:
    """Configuration for task failure injection"""
    failure_type: str
    trigger_point: str  # "start", "middle", "end"
    probability: float = 1.0
    recovery_required: bool = True


# ==================== ADVERSARIAL TASKS ====================

@dataclass
class AdversarialConfig:
    """Configuration for anti-reward-hacking tasks"""
    hidden_verifier: bool = False
    fake_shortcuts: List[str] = field(default_factory=list)
    decoy_files: List[str] = field(default_factory=list)
    misleading_logs: bool = False
    forbidden_paths: List[str] = field(default_factory=list)


# ==================== LEADERBOARD ====================

@dataclass
class LeaderboardEntry:
    """Single leaderboard entry"""
    task_id: str
    suite: str
    capabilities: List[str]
    difficulty: str
    
    # Scores
    raw_score: float = 0.0
    weighted_score: float = 0.0
    efficiency_score: float = 0.0
    
    # Metadata
    run_count: int = 0
    pass_count: int = 0
    pass_rate: float = 0.0
    
    def to_dict(self) -> Dict:
        return {
            "task_id": self.task_id,
            "suite": self.suite,
            "capabilities": self.capabilities,
            "difficulty": self.difficulty,
            "raw_score": self.raw_score,
            "weighted_score": self.weighted_score,
            "efficiency_score": self.efficiency_score,
            "run_count": self.run_count,
            "pass_count": self.pass_count,
            "pass_rate": self.pass_rate,
        }


class Leaderboard:
    """
    Maintains leaderboard with multiple views.
    """
    
    def __init__(self):
        self.entries: Dict[str, LeaderboardEntry] = {}
        self.scorer = WeightedScorer()
    
    def add_result(self, task_metadata: TaskMetadata, result: Dict):
        """Add a task result"""
        task_id = task_metadata.task_id
        
        if task_id not in self.entries:
            self.entries[task_id] = LeaderboardEntry(
                task_id=task_id,
                suite=task_metadata.suite,
                capabilities=task_metadata.capabilities,
                difficulty=task_metadata.difficulty
            )
        
        entry = self.entries[task_id]
        
        # Update scores
        scores = self.scorer.compute_score(
            result.get("passed", 0) and 1.0 or 0,
            task_metadata
        )
        
        entry.raw_score = scores["raw"]
        entry.weighted_score = scores["weighted"]
        
        if "efficiency" in result:
            entry.efficiency_score = result["efficiency"]
        
        # Update pass tracking
        entry.run_count += 1
        if result.get("passed", False):
            entry.pass_count += 1
        entry.pass_rate = entry.pass_count / entry.run_count
    
    def get_overall_scores(self) -> Dict:
        """Get aggregated scores"""
        total_weighted = sum(e.weighted_score for e in self.entries.values())
        total_raw = sum(e.raw_score for e in self.entries.values())
        total_runs = sum(e.run_count for e in self.entries.values())
        
        # Per-suite scores
        suite_scores = defaultdict(lambda: {"weighted": 0.0, "count": 0})
        for entry in self.entries.values():
            suite_scores[entry.suite]["weighted"] += entry.weighted_score
            suite_scores[entry.suite]["count"] += 1
        
        # Per-capability scores
        cap_scores = defaultdict(lambda: {"weighted": 0.0, "count": 0})
        for entry in self.entries.values():
            for cap in entry.capabilities:
                cap_scores[cap]["weighted"] += entry.weighted_score
                cap_scores[cap]["count"] += 1
        
        return {
            "total_weighted": total_weighted,
            "total_raw": total_raw,
            "total_runs": total_runs,
            "per_suite": dict(suite_scores),
            "per_capability": dict(cap_scores),
            "task_count": len(self.entries)
        }


# ==================== FACTORY ====================

def create_task_metadata(task_data: Dict) -> TaskMetadata:
    """Factory to create TaskMetadata from dict"""
    return TaskMetadata(
        task_id=task_data["id"],
        suite=task_data["suite"],
        capabilities=task_data.get("capabilities", []),
        environments=task_data.get("environments", []),
        difficulty=task_data.get("difficulty", Difficulty.EASY.value),
        weight=task_data.get("weight", 1.0),
        tags=task_data.get("tags", []),
        description=task_data.get("description", "")
    )
