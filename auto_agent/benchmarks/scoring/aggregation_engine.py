"""
Aggregation Engine - Weighted Score Aggregation
==============================================

Frontier-grade weighted aggregation system for multi-dimensional scoring.

This module provides:
- Weighted aggregation across suites, capabilities, difficulties
- Configurable weighting policies
- Efficiency penalty calculation
- Multi-axis score computation
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Callable
from enum import Enum
import numpy as np


# ==================== WEIGHTING CONFIG ====================

@dataclass
class WeightingConfig:
    """
    Configuration for score aggregation weights.
    
    This allows fine-tuning of how different factors
    affect the final scores.
    """
    # Difficulty weights
    easy_weight: float = 1.0
    medium_weight: float = 2.0
    hard_weight: float = 4.0
    frontier_weight: float = 6.0
    
    # Suite weights (can be customized per suite)
    suite_weights: Dict[str, float] = field(default_factory=dict)
    
    # Capability weights
    capability_weights: Dict[str, float] = field(default_factory=dict)
    
    # Dimension weights for global score
    capability_dimension_weight: float = 0.35
    reliability_dimension_weight: float = 0.20
    efficiency_dimension_weight: float = 0.15
    integrity_dimension_weight: float = 0.15
    generalization_dimension_weight: float = 0.10
    safety_dimension_weight: float = 0.05
    
    # Efficiency penalty settings
    cost_baseline: float = 0.10  # USD per task
    time_baseline: float = 60.0  # seconds per task
    steps_baseline: int = 50  # steps per task
    
    # Floor policies (minimums)
    hard_frontier_minimum: float = 0.60
    reliability_minimum: float = 0.80
    integrity_minimum: float = 0.95
    self_mod_minimum: float = 0.40
    
    @classmethod
    def default(cls) -> 'WeightingConfig':
        """Get default weighting configuration."""
        return cls()
    
    @classmethod
    def frontier_grade(cls) -> 'WeightingConfig':
        """Get frontier-grade weighting configuration."""
        config = cls()
        # Increase frontier weight even more
        config.frontier_weight = 8.0
        config.hard_weight = 6.0
        # Suite-specific weights
        config.suite_weights = {
            "self_modification": 2.0,
            "tool_creation_use": 1.8,
            "long_horizon_orchestration": 1.5,
            "browser_workflow": 1.2,
        }
        return config
    
    def get_difficulty_weight(self, difficulty: str) -> float:
        """Get weight for a difficulty level."""
        weights = {
            "easy": self.easy_weight,
            "medium": self.medium_weight,
            "hard": self.hard_weight,
            "frontier": self.frontier_weight,
        }
        return weights.get(difficulty, 1.0)
    
    def get_suite_weight(self, suite: str) -> float:
        """Get weight for a suite."""
        return self.suite_weights.get(suite, 1.0)
    
    def get_capability_weight(self, capability: str) -> float:
        """Get weight for a capability."""
        return self.capability_weights.get(capability, 1.0)


# ==================== AGGREGATION ENGINE ====================

class AggregationEngine:
    """
    Advanced aggregation engine for multi-dimensional scoring.
    
    This engine handles:
    - Per-suite aggregation
    - Per-capability aggregation
    - Per-difficulty aggregation
    - Efficiency penalties
    - Reliability weighting
    - Composite score calculation
    """
    
    def __init__(self, config: WeightingConfig = None):
        self.config = config or WeightingConfig.default()
    
    def aggregate_task_results(
        self, 
        results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Aggregate multiple task results into a summary.
        
        Args:
            results: List of task result dictionaries
        
        Returns:
            Aggregated scores dictionary
        """
        if not results:
            return {}
        
        # Group by dimensions
        suite_groups = self._group_by(results, "suite")
        capability_groups = self._group_by_multiple(results, "capabilities")
        difficulty_groups = self._group_by(results, "difficulty")
        
        # Calculate aggregated scores
        aggregated = {
            "suite_scores": self._aggregate_groups(suite_groups, results),
            "capability_scores": self._aggregate_capabilities(capability_groups, results),
            "difficulty_scores": self._aggregate_groups(difficulty_groups, results),
            "dimension_scores": self._calculate_dimension_scores(results),
            "global_score": self._calculate_global_score(results),
        }
        
        # Add floor check results
        aggregated["floor_checks"] = self._check_floors(aggregated)
        
        return aggregated
    
    def _group_by(
        self, 
        results: List[Dict[str, Any]], 
        key: str
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Group results by a key."""
        groups = {}
        for result in results:
            value = result.get(key, "unknown")
            if value not in groups:
                groups[value] = []
            groups[value].append(result)
        return groups
    
    def _group_by_multiple(
        self, 
        results: List[Dict[str, Any]], 
        key: str
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Group results by a key that has multiple values per result."""
        groups = {}
        for result in results:
            values = result.get(key, [])
            if not isinstance(values, list):
                values = [values]
            for value in values:
                if value not in groups:
                    groups[value] = []
                groups[value].append(result)
        return groups
    
    def _aggregate_groups(
        self,
        groups: Dict[str, List[Dict[str, Any]]],
        all_results: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        """Aggregate scores by groups."""
        aggregated = {}
        
        for group_name, group_results in groups.items():
            # Get weights
            weights = [
                self.config.get_difficulty_weight(r.get("difficulty", "easy"))
                for r in group_results
            ]
            
            # Calculate weighted average
            scores = [r.get("raw_capability_score", 0.0) for r in group_results]
            if weights and scores:
                weighted_sum = sum(s * w for s, w in zip(scores, weights))
                weight_sum = sum(weights)
                aggregated[group_name] = weighted_sum / weight_sum if weight_sum > 0 else 0.0
            else:
                aggregated[group_name] = 0.0
        
        return aggregated
    
    def _aggregate_capabilities(
        self,
        capability_groups: Dict[str, List[Dict[str, Any]]],
        all_results: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        """Aggregate scores by capabilities."""
        aggregated = {}
        
        for cap, group_results in capability_groups.items():
            # Calculate weighted average
            scores = [r.get("raw_capability_score", 0.0) for r in group_results]
            if scores:
                aggregated[cap] = sum(scores) / len(scores)
            else:
                aggregated[cap] = 0.0
        
        return aggregated
    
    def _calculate_dimension_scores(
        self, 
        results: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        """Calculate quality dimension scores."""
        if not results:
            return {}
        
        dimensions = {
            "capability": [],
            "reliability": [],
            "efficiency": [],
            "integrity": [],
            "safety": [],
            "generalization": [],
        }
        
        for result in results:
            for dim in dimensions.keys():
                score = result.get(f"{dim}_score", 1.0 if dim != "capability" else 0.0)
                dimensions[dim].append(score)
        
        # Calculate averages
        return {
            dim: sum(scores) / len(scores) if scores else 0.0
            for dim, scores in dimensions.items()
        }
    
    def _calculate_global_score(
        self, 
        results: List[Dict[str, Any]]
    ) -> float:
        """Calculate global composite score."""
        dims = self._calculate_dimension_scores(results)
        
        weights = {
            "capability": self.config.capability_dimension_weight,
            "reliability": self.config.reliability_dimension_weight,
            "efficiency": self.config.efficiency_dimension_weight,
            "integrity": self.config.integrity_dimension_weight,
            "generalization": self.config.generalization_dimension_weight,
            "safety": self.config.safety_dimension_weight,
        }
        
        return sum(
            dims.get(dim, 0.0) * weight 
            for dim, weight in weights.items()
        )
    
    def _check_floors(
        self, 
        aggregated: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Check floor policies."""
        checks = {}
        
        # Hard/frontier minimum
        diff_scores = aggregated.get("difficulty_scores", {})
        hard_frontier = []
        if "hard" in diff_scores:
            hard_frontier.append(diff_scores["hard"])
        if "frontier" in diff_scores:
            hard_frontier.append(diff_scores["frontier"])
        
        if hard_frontier:
            avg = sum(hard_frontier) / len(hard_frontier)
            checks["hard_frontier_passed"] = avg >= self.config.hard_frontier_minimum
            checks["hard_frontier_score"] = avg
        else:
            checks["hard_frontier_passed"] = True
            checks["hard_frontier_score"] = None
        
        # Reliability minimum
        dim_scores = aggregated.get("dimension_scores", {})
        rel_score = dim_scores.get("reliability", 1.0)
        checks["reliability_passed"] = rel_score >= self.config.reliability_minimum
        checks["reliability_score"] = rel_score
        
        # Integrity minimum
        int_score = dim_scores.get("integrity", 1.0)
        checks["integrity_passed"] = int_score >= self.config.integrity_minimum
        checks["integrity_score"] = int_score
        
        # Self-mod minimum
        suite_scores = aggregated.get("suite_scores", {})
        self_mod_score = suite_scores.get("self_modification", 0.0)
        checks["self_mod_passed"] = self_mod_score >= self.config.self_mod_minimum
        checks["self_mod_score"] = self_mod_score
        
        # Overall floor check
        checks["all_floors_passed"] = all([
            checks["hard_frontier_passed"],
            checks["reliability_passed"],
            checks["integrity_passed"],
        ])
        
        return checks
    
    def calculate_efficiency_penalty(
        self,
        cost_usd: float,
        time_seconds: float,
        steps: int,
    ) -> float:
        """
        Calculate efficiency penalty for a task.
        
        Returns penalty (0.0 - 1.0) that should be subtracted from score.
        """
        cost_ratio = cost_usd / self.config.cost_baseline if self.config.cost_baseline > 0 else 1.0
        time_ratio = time_seconds / self.config.time_baseline if self.config.time_baseline > 0 else 1.0
        steps_ratio = steps / self.config.steps_baseline if self.config.steps_baseline > 0 else 1.0
        
        # Average ratio
        avg_ratio = (cost_ratio + time_ratio + steps_ratio) / 3.0
        
        # Penalty is proportional to how much over baseline
        # If under baseline, penalty is 0
        return max(0.0, (avg_ratio - 1.0) * 0.5)  # 50% penalty for 2x baseline
    
    def get_pareto_frontier(
        self,
        candidates: List[Dict[str, Any]],
        x_metric: str,
        y_metric: str,
    ) -> List[Dict[str, Any]]:
        """
        Get Pareto frontier from candidates.
        
        Args:
            candidates: List of candidate dictionaries
            x_metric: Metric for x-axis
            y_metric: Metric for y-axis
        
        Returns:
            List of candidates on Pareto frontier
        """
        frontier = []
        
        for candidate in candidates:
            x = candidate.get(x_metric, 0.0)
            y = candidate.get(y_metric, 0.0)
            
            is_dominated = False
            for other in candidates:
                if other == candidate:
                    continue
                
                ox = other.get(x_metric, 0.0)
                oy = other.get(y_metric, 0.0)
                
                # Other dominates if it's better in both dimensions
                if ox >= x and oy >= y and (ox > x or oy > y):
                    is_dominated = True
                    break
            
            if not is_dominated:
                frontier.append(candidate)
        
        return frontier


# ==================== ADVANCED AGGREGATION ====================

class AdvancedAggregator:
    """
    Advanced aggregation with custom aggregation functions.
    """
    
    def __init__(self):
        self.aggregation_functions: Dict[str, Callable] = {
            "mean": self._mean,
            "weighted_mean": self._weighted_mean,
            "geometric_mean": self._geometric_mean,
            "harmonic_mean": self._harmonic_mean,
            "max": self._max,
            "min": self._min,
            "median": self._median,
        }
    
    def _mean(self, values: List[float]) -> float:
        """Arithmetic mean."""
        return sum(values) / len(values) if values else 0.0
    
    def _weighted_mean(self, values: List[float], weights: List[float]) -> float:
        """Weighted mean."""
        if not values or not weights:
            return 0.0
        return sum(v * w for v, w in zip(values, weights)) / sum(weights)
    
    def _geometric_mean(self, values: List[float]) -> float:
        """Geometric mean."""
        if not values:
            return 0.0
        # Filter out zeros
        values = [v for v in values if v > 0]
        if not values:
            return 0.0
        product = np.prod(values)
        return product ** (1 / len(values))
    
    def _harmonic_mean(self, values: List[float]) -> float:
        """Harmonic mean."""
        if not values:
            return 0.0
        values = [v for v in values if v > 0]
        if not values:
            return 0.0
        return len(values) / sum(1 / v for v in values)
    
    def _max(self, values: List[float]) -> float:
        """Maximum."""
        return max(values) if values else 0.0
    
    def _min(self, values: List[float]) -> float:
        """Minimum."""
        return min(values) if values else 0.0
    
    def _median(self, values: List[float]) -> float:
        """Median."""
        if not values:
            return 0.0
        sorted_vals = sorted(values)
        n = len(sorted_vals)
        if n % 2 == 0:
            return (sorted_vals[n // 2 - 1] + sorted_vals[n // 2]) / 2
        return sorted_vals[n // 2]
    
    def aggregate_with_method(
        self,
        values: List[float],
        method: str = "mean",
        weights: List[float] = None,
    ) -> float:
        """Aggregate values with specified method."""
        func = self.aggregation_functions.get(method, self._mean)
        
        if method == "weighted_mean":
            return func(values, weights or [1.0] * len(values))
        
        return func(values)


# ==================== REGRESSION DETECTOR ====================

class RegressionDetector:
    """
    Detect performance regressions across runs.
    """
    
    def __init__(self, history_weight: float = 0.3):
        self.history_weight = history_weight
    
    def detect_regression(
        self,
        current_score: float,
        previous_scores: List[float],
    ) -> Dict[str, Any]:
        """
        Detect if current score represents a regression.
        
        Returns:
            Dictionary with regression analysis
        """
        if not previous_scores:
            return {
                "has_regression": False,
                "reason": "no_history",
                "current": current_score,
                "previous_avg": None,
                "delta": None,
            }
        
        previous_avg = sum(previous_scores) / len(previous_scores)
        delta = current_score - previous_avg
        
        # Calculate rolling average (recent runs weighted more)
        weights = [i + 1 for i in range(len(previous_scores))]
        weighted_avg = sum(
            s * w for s, w in zip(previous_scores, weights)
        ) / sum(weights)
        
        # Determine regression
        threshold = 0.05  # 5% regression threshold
        has_regression = delta < -threshold
        
        # Calculate stability (variance)
        variance = sum((s - previous_avg) ** 2 for s in previous_scores) / len(previous_scores)
        stability = 1.0 - min(1.0, variance * 10)  # Normalize
        
        return {
            "has_regression": has_regression,
            "reason": "below_threshold" if has_regression else "acceptable",
            "current": current_score,
            "previous_avg": previous_avg,
            "weighted_avg": weighted_avg,
            "delta": delta,
            "delta_percent": (delta / previous_avg * 100) if previous_avg > 0 else 0,
            "stability": stability,
            "is_stable": stability > 0.8,
        }
    
    def detect_dimension_regression(
        self,
        current_dims: Dict[str, float],
        previous_dims: Dict[str, float],
    ) -> Dict[str, Any]:
        """Detect regression in specific dimensions."""
        regressions = {}
        
        for dim in current_dims.keys():
            current = current_dims.get(dim, 0.0)
            previous = previous_dims.get(dim, 0.0)
            
            if dim in previous_dims:
                delta = current - previous
                regressions[dim] = {
                    "current": current,
                    "previous": previous,
                    "delta": delta,
                    "has_regression": delta < -0.05,
                }
        
        return regressions


# ==================== FACTORY ====================

def create_aggregation_engine(
    config: WeightingConfig = None,
) -> AggregationEngine:
    """Create an aggregation engine."""
    return AggregationEngine(config)
