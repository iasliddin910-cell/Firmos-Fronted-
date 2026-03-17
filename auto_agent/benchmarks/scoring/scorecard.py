"""
ScoreCard - Structured Result Schema
=====================================

Frontier-grade scoring system that captures multi-dimensional results.

This module provides:
- ScoreCard: Structured result for each run
- TaskResult: Individual task result with all dimensions
- Dimension scores: capability, reliability, efficiency, integrity, safety, generalization

Definition of Done uchun:
1. Har run structured scorecard bilan saqlanadi.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Set
from enum import Enum
from datetime import datetime
import json


# ==================== QUALITY DIMENSIONS ====================

class QualityDimension(str, Enum):
    """
    Quality dimensions for multi-axis scoring.
    """
    CAPABILITY = "capability"
    RELIABILITY = "reliability"
    EFFICIENCY = "efficiency"
    INTEGRITY = "integrity"
    SAFETY = "safety"
    GENERALIZATION = "generalization"


class DifficultyLevel(str, Enum):
    """
    Task difficulty levels with weights.
    """
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    FRONTIER = "frontier"
    
    @property
    def weight(self) -> float:
        weights = {
            DifficultyLevel.EASY: 1.0,
            DifficultyLevel.MEDIUM: 2.0,
            DifficultyLevel.HARD: 4.0,
            DifficultyLevel.FRONTIER: 6.0
        }
        return weights[self]


class RunStatus(str, Enum):
    """
    Status of a benchmark run.
    """
    PASSED = "passed"
    FAILED = "failed"
    PARTIAL = "partial"
    ERROR = "error"
    TIMEOUT = "timeout"
    FLAKY = "flaky"


# ==================== TASK RESULT ====================

@dataclass
class TaskResult:
    """
    Individual task result with all quality dimensions.
    
    This is the atomic unit of scoring - every task run produces
    a TaskResult with all dimensions captured.
    """
    task_id: str
    suite: str
    status: RunStatus
    
    # Raw scores (0.0 - 1.0)
    raw_capability_score: float = 0.0
    
    # Quality dimensions
    reliability_score: float = 1.0  # How consistent (retries, seeds)
    efficiency_score: float = 1.0   # Cost/time/steps efficiency
    integrity_score: float = 1.0   # No suspicious/patched results
    safety_score: float = 1.0       # No dangerous operations
    generalization_score: float = 1.0  # Works on novel/shifted tasks
    
    # Metadata
    difficulty: str = DifficultyLevel.EASY.value
    capabilities: List[str] = field(default_factory=list)
    environments: List[str] = field(default_factory=list)
    
    # Execution metrics
    cost_usd: float = 0.0
    time_seconds: float = 0.0
    steps: int = 0
    retries: int = 0
    seeds: List[str] = field(default_factory=list)
    
    # Anti-gaming
    hidden_test_passed: bool = True
    suspicious_patterns: List[str] = field(default_factory=list)
    
    # Timestamps
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    
    # Additional metadata
    tags: List[str] = field(default_factory=list)
    error_message: Optional[str] = None
    
    def get_weight(self) -> float:
        """Get task weight based on difficulty."""
        return DifficultyLevel(self.difficulty).weight
    
    def get_adjusted_capability_score(self) -> float:
        """
        Calculate adjusted capability score with all multipliers.
        
        Formula:
        adjusted = raw_score * integrity * reliability * difficulty_weight
        """
        return (
            self.raw_capability_score 
            * self.integrity_score 
            * self.reliability_score 
            * self.get_weight()
        )
    
    def get_efficiency_penalty(self) -> float:
        """
        Calculate efficiency penalty.
        
        Returns penalty (0.0 - 1.0) based on:
        - Cost vs baseline
        - Time vs baseline
        - Steps vs baseline
        """
        # Baseline expectations (can be configured)
        baseline_cost = 0.10  # $0.10 per task
        baseline_time = 60.0  # 60 seconds
        baseline_steps = 50  # 50 steps
        
        # Calculate penalties
        cost_penalty = min(1.0, self.cost_usd / baseline_cost) - 1.0
        time_penalty = min(1.0, self.time_seconds / baseline_time) - 1.0
        steps_penalty = min(1.0, self.steps / baseline_steps) - 1.0
        
        # Average penalty
        avg_penalty = (cost_penalty + time_penalty + steps_penalty) / 3.0
        return max(0.0, avg_penalty)
    
    def is_healthy(self) -> bool:
        """Check if result is healthy (not suspicious)."""
        return (
            self.hidden_test_passed 
            and len(self.suspicious_patterns) == 0
            and self.status != RunStatus.ERROR
            and self.status != RunStatus.FLAKY
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "task_id": self.task_id,
            "suite": self.suite,
            "status": self.status.value,
            "raw_capability_score": self.raw_capability_score,
            "reliability_score": self.reliability_score,
            "efficiency_score": self.efficiency_score,
            "integrity_score": self.integrity_score,
            "safety_score": self.safety_score,
            "generalization_score": self.generalization_score,
            "difficulty": self.difficulty,
            "capabilities": self.capabilities,
            "environments": self.environments,
            "cost_usd": self.cost_usd,
            "time_seconds": self.time_seconds,
            "steps": self.steps,
            "retries": self.retries,
            "seeds": self.seeds,
            "hidden_test_passed": self.hidden_test_passed,
            "suspicious_patterns": self.suspicious_patterns,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "tags": self.tags,
            "error_message": self.error_message,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TaskResult':
        """Create from dictionary."""
        return cls(
            task_id=data["task_id"],
            suite=data["suite"],
            status=RunStatus(data["status"]),
            raw_capability_score=data.get("raw_capability_score", 0.0),
            reliability_score=data.get("reliability_score", 1.0),
            efficiency_score=data.get("efficiency_score", 1.0),
            integrity_score=data.get("integrity_score", 1.0),
            safety_score=data.get("safety_score", 1.0),
            generalization_score=data.get("generalization_score", 1.0),
            difficulty=data.get("difficulty", DifficultyLevel.EASY.value),
            capabilities=data.get("capabilities", []),
            environments=data.get("environments", []),
            cost_usd=data.get("cost_usd", 0.0),
            time_seconds=data.get("time_seconds", 0.0),
            steps=data.get("steps", 0),
            retries=data.get("retries", 0),
            seeds=data.get("seeds", []),
            hidden_test_passed=data.get("hidden_test_passed", True),
            suspicious_patterns=data.get("suspicious_patterns", []),
            started_at=data.get("started_at"),
            completed_at=data.get("completed_at"),
            tags=data.get("tags", []),
            error_message=data.get("error_message"),
        )


# ==================== SCORE CARD ====================

@dataclass
class ScoreCard:
    """
    Structured result for a complete benchmark run.
    
    This is the main container that holds all task results
    and computed dimension scores.
    
    Definition of Done:
    1. Har run structured scorecard bilan saqlanadi.
    """
    run_id: str
    agent_version: str
    config: Dict[str, Any] = field(default_factory=dict)
    
    # Task results
    task_results: List[TaskResult] = field(default_factory=list)
    
    # Timestamp
    run_started: Optional[str] = None
    run_completed: Optional[str] = None
    
    # Metadata
    run_config: Dict[str, Any] = field(default_factory=dict)
    environment_info: Dict[str, Any] = field(default_factory=dict)
    
    # Tags
    tags: List[str] = field(default_factory=list)
    
    # Computed scores (lazy computed)
    _suite_scores: Dict[str, float] = field(default_factory=dict, repr=False)
    _capability_scores: Dict[str, float] = field(default_factory=dict, repr=False)
    _difficulty_scores: Dict[str, float] = field(default_factory=dict, repr=False)
    _dimension_scores: Dict[str, float] = field(default_factory=dict, repr=False)
    _global_score: Optional[float] = None
    
    def add_task_result(self, result: TaskResult) -> None:
        """Add a task result to the scorecard."""
        self.task_results.append(result)
        # Invalidate cached scores
        self._invalidate_cache()
    
    def _invalidate_cache(self) -> None:
        """Invalidate cached computed scores."""
        self._suite_scores = {}
        self._capability_scores = {}
        self._difficulty_scores = {}
        self._dimension_scores = {}
        self._global_score = None
    
    # ==================== AGGREGATION METHODS ====================
    
    def get_suite_scores(self) -> Dict[str, float]:
        """
        Get per-suite aggregated scores.
        
        Returns dict of suite -> weighted average score.
        """
        if self._suite_scores:
            return self._suite_scores
        
        suite_results = {}
        for result in self.task_results:
            if result.suite not in suite_results:
                suite_results[result.suite] = []
            suite_results[result.suite].append(result)
        
        # Calculate weighted scores
        for suite, results in suite_results.items():
            weighted_sum = sum(r.get_adjusted_capability_score() for r in results)
            weight_sum = sum(r.get_weight() for r in results)
            self._suite_scores[suite] = weighted_sum / weight_sum if weight_sum > 0 else 0.0
        
        return self._suite_scores
    
    def get_capability_scores(self) -> Dict[str, float]:
        """
        Get per-capability aggregated scores.
        
        Returns dict of capability -> weighted average score.
        """
        if self._capability_scores:
            return self._capability_scores
        
        capability_results = {}
        for result in self.task_results:
            for cap in result.capabilities:
                if cap not in capability_results:
                    capability_results[cap] = []
                capability_results[cap].append(result)
        
        # Calculate weighted scores
        for cap, results in capability_results.items():
            weighted_sum = sum(r.get_adjusted_capability_score() for r in results)
            weight_sum = sum(r.get_weight() for r in results)
            self._capability_scores[cap] = weighted_sum / weight_sum if weight_sum > 0 else 0.0
        
        return self._capability_scores
    
    def get_difficulty_scores(self) -> Dict[str, float]:
        """
        Get per-difficulty aggregated scores.
        
        Returns dict of difficulty -> average score.
        This is CRITICAL for detecting:
        - Easy-task farming
        - Frontier weakness
        """
        if self._difficulty_scores:
            return self._difficulty_scores
        
        difficulty_results = {}
        for result in self.task_results:
            diff = result.difficulty
            if diff not in difficulty_results:
                difficulty_results[diff] = []
            difficulty_results[diff].append(result)
        
        # Calculate scores per difficulty
        for diff, results in difficulty_results.items():
            scores = [r.raw_capability_score for r in results]
            self._difficulty_scores[diff] = sum(scores) / len(scores) if scores else 0.0
        
        return self._difficulty_scores
    
    def get_dimension_scores(self) -> Dict[str, float]:
        """
        Get quality dimension scores.
        
        Returns:
        - capability: Raw capability score
        - reliability: Consistency across runs
        - efficiency: Cost/time/steps efficiency
        - integrity: No suspicious patterns
        - safety: No dangerous operations
        - generalization: Works on novel tasks
        """
        if self._dimension_scores:
            return self._dimension_scores
        
        # Capability (weighted average of raw scores)
        raw_scores = [r.raw_capability_score for r in self.task_results]
        self._dimension_scores[QualityDimension.CAPABILITY.value] = (
            sum(raw_scores) / len(raw_scores) if raw_scores else 0.0
        )
        
        # Reliability
        rel_scores = [r.reliability_score for r in self.task_results]
        self._dimension_scores[QualityDimension.RELIABILITY.value] = (
            sum(rel_scores) / len(rel_scores) if rel_scores else 0.0
        )
        
        # Efficiency
        eff_scores = [r.efficiency_score for r in self.task_results]
        self._dimension_scores[QualityDimension.EFFICIENCY.value] = (
            sum(eff_scores) / len(eff_scores) if eff_scores else 0.0
        )
        
        # Integrity
        int_scores = [r.integrity_score for r in self.task_results]
        self._dimension_scores[QualityDimension.INTEGRITY.value] = (
            sum(int_scores) / len(int_scores) if int_scores else 0.0
        )
        
        # Safety
        safe_scores = [r.safety_score for r in self.task_results]
        self._dimension_scores[QualityDimension.SAFETY.value] = (
            sum(safe_scores) / len(safe_scores) if safe_scores else 0.0
        )
        
        # Generalization
        gen_scores = [r.generalization_score for r in self.task_results]
        self._dimension_scores[QualityDimension.GENERALIZATION.value] = (
            sum(gen_scores) / len(gen_scores) if gen_scores else 0.0
        )
        
        return self._dimension_scores
    
    def get_global_score(self) -> float:
        """
        Get global composite score.
        
        Formula:
        global_score = 
            0.35 * capability +
            0.20 * reliability +
            0.15 * efficiency +
            0.15 * integrity +
            0.10 * generalization +
            0.05 * safety
        """
        if self._global_score is not None:
            return self._global_score
        
        dims = self.get_dimension_scores()
        
        weights = {
            QualityDimension.CAPABILITY.value: 0.35,
            QualityDimension.RELIABILITY.value: 0.20,
            QualityDimension.EFFICIENCY.value: 0.15,
            QualityDimension.INTEGRITY.value: 0.15,
            QualityDimension.GENERALIZATION.value: 0.10,
            QualityDimension.SAFETY.value: 0.05,
        }
        
        self._global_score = sum(
            dims.get(dim, 0.0) * weight 
            for dim, weight in weights.items()
        )
        
        return self._global_score
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the scorecard."""
        return {
            "run_id": self.run_id,
            "agent_version": self.agent_version,
            "total_tasks": len(self.task_results),
            "passed_tasks": len([r for r in self.task_results if r.status == RunStatus.PASSED]),
            "failed_tasks": len([r for r in self.task_results if r.status == RunStatus.FAILED]),
            "global_score": self.get_global_score(),
            "suite_scores": self.get_suite_scores(),
            "capability_scores": self.get_capability_scores(),
            "difficulty_scores": self.get_difficulty_scores(),
            "dimension_scores": self.get_dimension_scores(),
        }
    
    # ==================== SERIALIZATION ====================
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "run_id": self.run_id,
            "agent_version": self.agent_version,
            "config": self.config,
            "task_results": [r.to_dict() for r in self.task_results],
            "run_started": self.run_started,
            "run_completed": self.run_completed,
            "run_config": self.run_config,
            "environment_info": self.environment_info,
            "tags": self.tags,
            "summary": self.get_summary(),
        }
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=2)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ScoreCard':
        """Create from dictionary."""
        card = cls(
            run_id=data["run_id"],
            agent_version=data["agent_version"],
            config=data.get("config", {}),
            run_started=data.get("run_started"),
            run_completed=data.get("run_completed"),
            run_config=data.get("run_config", {}),
            environment_info=data.get("environment_info", {}),
            tags=data.get("tags", []),
        )
        
        # Restore task results
        for tr_data in data.get("task_results", []):
            card.task_results.append(TaskResult.from_dict(tr_data))
        
        return card
    
    @classmethod
    def from_json(cls, json_str: str) -> 'ScoreCard':
        """Create from JSON string."""
        return cls.from_dict(json.loads(json_str))
    
    # ==================== ANALYSIS METHODS ====================
    
    def get_hard_frontier_average(self) -> float:
        """Get average score for hard + frontier tasks only."""
        hard_frontier = [
            r for r in self.task_results 
            if r.difficulty in [DifficultyLevel.HARD.value, DifficultyLevel.FRONTIER.value]
        ]
        if not hard_frontier:
            return 0.0
        return sum(r.raw_capability_score for r in hard_frontier) / len(hard_frontier)
    
    def get_reliability_rate(self) -> float:
        """Get reliability rate (tasks that passed without retries)."""
        reliable = [r for r in self.task_results if r.retries == 0 and r.status == RunStatus.PASSED]
        return len(reliable) / len(self.task_results) if self.task_results else 0.0
    
    def get_integrity_rate(self) -> float:
        """Get integrity rate (tasks without suspicious patterns)."""
        clean = [r for r in self.task_results if r.is_healthy()]
        return len(clean) / len(self.task_results) if self.task_results else 0.0
    
    def get_total_cost(self) -> float:
        """Get total cost of all tasks."""
        return sum(r.cost_usd for r in self.task_results)
    
    def get_average_efficiency(self) -> float:
        """Get average efficiency across all tasks."""
        scores = [r.efficiency_score for r in self.task_results]
        return sum(scores) / len(scores) if scores else 0.0


# ==================== FACTORY METHODS ====================

def create_task_result(
    task_id: str,
    suite: str,
    status: RunStatus,
    raw_capability_score: float = 0.0,
    difficulty: str = DifficultyLevel.EASY.value,
    capabilities: List[str] = None,
    **kwargs
) -> TaskResult:
    """
    Factory method to create a TaskResult.
    
    Args:
        task_id: Unique task identifier
        suite: Benchmark suite
        status: Pass/fail status
        raw_capability_score: Raw score (0.0-1.0)
        difficulty: Task difficulty
        capabilities: List of capabilities required
        **kwargs: Additional fields
    
    Returns:
        TaskResult instance
    """
    return TaskResult(
        task_id=task_id,
        suite=suite,
        status=status,
        raw_capability_score=raw_capability_score,
        difficulty=difficulty,
        capabilities=capabilities or [],
        **kwargs
    )


def create_scorecard(
    run_id: str,
    agent_version: str,
    config: Dict[str, Any] = None,
) -> ScoreCard:
    """
    Factory method to create a ScoreCard.
    
    Args:
        run_id: Unique run identifier
        agent_version: Agent version string
        config: Run configuration
    
    Returns:
        ScoreCard instance
    """
    return ScoreCard(
        run_id=run_id,
        agent_version=agent_version,
        config=config or {},
        run_started=datetime.utcnow().isoformat(),
    )
