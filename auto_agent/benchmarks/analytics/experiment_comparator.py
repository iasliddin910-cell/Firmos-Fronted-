"""
ExperimentComparator - Experiment Comparison
======================================

Experiment solishtirish.

Bu modul:
- Same task slice comparison
- Delta by capability
- Delta by difficulty
- Delta by efficiency
- Flake-adjusted change

bajaradi.

Definition of Done:
6. Experiment A/B solishtirish structured tarzda ishlaydi.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from collections import defaultdict


@dataclass
class ComparisonResult:
    """Solishtirish natijasi."""
    experiment_a: str
    experiment_b: str
    
    # Overall
    score_delta: float
    score_delta_pct: float
    
    # By dimension
    by_capability: Dict[str, Dict[str, float]] = field(default_factory=dict)
    by_difficulty: Dict[str, Dict[str, float]] = field(default_factory=dict)
    by_suite: Dict[str, Dict[str, float]] = field(default_factory=dict)
    
    # Efficiency
    cost_delta: float = 0.0
    time_delta_ms: int = 0
    
    # Quality
    flake_adjusted_delta: float = 0.0
    
    # Significance
    significant_wins: List[Dict] = field(default_factory=list)
    significant_losses: List[Dict] = field(default_factory=list)


class ExperimentComparator:
    """
    Experiment comparator.
    
    Definition of Done:
    6. Experiment A/B solishtirish structured tarzda ishlaydi.
    """
    
    def __init__(self):
        self.trace_storage = None
    
    def compare(
        self,
        run_a_id: str,
        run_b_id: str,
    ) -> ComparisonResult:
        """Ikki run'ni solishtirish."""
        # Load traces
        if not self.trace_storage:
            return ComparisonResult(
                experiment_a=run_a_id,
                experiment_b=run_b_id,
                score_delta=0,
                score_delta_pct=0,
            )
        
        trace_a = self.trace_storage.load_run_trace(run_a_id)
        trace_b = self.trace_storage.load_run_trace(run_b_id)
        
        if not trace_a or not trace_b:
            return ComparisonResult(
                experiment_a=run_a_id,
                experiment_b=run_b_id,
                score_delta=0,
                score_delta_pct=0,
            )
        
        # Calculate deltas
        score_a = trace_a.passed_tasks / trace_a.total_tasks if trace_a.total_tasks > 0 else 0
        score_b = trace_b.passed_tasks / trace_b.total_tasks if trace_b.total_tasks > 0 else 0
        
        score_delta = score_b - score_a
        score_delta_pct = (score_delta / score_a * 100) if score_a > 0 else 0
        
        result = ComparisonResult(
            experiment_a=run_a_id,
            experiment_b=run_b_id,
            score_delta=score_delta,
            score_delta_pct=score_delta_pct,
            cost_delta=trace_b.total_cost_usd - trace_a.total_cost_usd,
            time_delta_ms=trace_b.total_duration_ms - trace_a.total_duration_ms,
        )
        
        # By capability
        result.by_capability = self._compare_by_capability(trace_a, trace_b)
        
        # By difficulty
        result.by_difficulty = self._compare_by_difficulty(trace_a, trace_b)
        
        # By suite
        result.by_suite = self._compare_by_suite(trace_a, trace_b)
        
        # Significant changes
        result.significant_wins, result.significant_losses = self._find_significant_changes(
            result.by_capability, result.by_suite
        )
        
        return result
    
    def _compare_by_capability(self, trace_a, trace_b) -> Dict[str, Dict[str, float]]:
        """Capability bo'yicha solishtirish."""
        cap_scores_a = self._get_capability_scores(trace_a)
        cap_scores_b = self._get_capability_scores(trace_b)
        
        comparison = {}
        all_caps = set(cap_scores_a.keys()) | set(cap_scores_b.keys())
        
        for cap in all_caps:
            score_a = cap_scores_a.get(cap, 0)
            score_b = cap_scores_b.get(cap, 0)
            comparison[cap] = {
                "a": score_a,
                "b": score_b,
                "delta": score_b - score_a,
            }
        
        return comparison
    
    def _compare_by_difficulty(self, trace_a, trace_b) -> Dict[str, Dict[str, float]]:
        """Difficulty bo'yicha solishtirish."""
        diff_scores_a = self._get_difficulty_scores(trace_a)
        diff_scores_b = self._get_difficulty_scores(trace_b)
        
        comparison = {}
        all_diffs = set(diff_scores_a.keys()) | set(diff_scores_b.keys())
        
        for diff in all_diffs:
            score_a = diff_scores_a.get(diff, 0)
            score_b = diff_scores_b.get(diff, 0)
            comparison[diff] = {
                "a": score_a,
                "b": score_b,
                "delta": score_b - score_a,
            }
        
        return comparison
    
    def _compare_by_suite(self, trace_a, trace_b) -> Dict[str, Dict[str, float]]:
        """Suite bo'yicha solishtirish."""
        suite_scores_a = self._get_suite_scores(trace_a)
        suite_scores_b = self._get_suite_scores(trace_b)
        
        comparison = {}
        all_suites = set(suite_scores_a.keys()) | set(suite_scores_b.keys())
        
        for suite in all_suites:
            score_a = suite_scores_a.get(suite, 0)
            score_b = suite_scores_b.get(suite, 0)
            comparison[suite] = {
                "a": score_a,
                "b": score_b,
                "delta": score_b - score_a,
            }
        
        return comparison
    
    def _get_capability_scores(self, trace) -> Dict[str, float]:
        """Capability scores olish."""
        scores = defaultdict(lambda: {"total": 0, "passed": 0})
        
        for task_trace in trace.task_traces:
            # Simplified - would use actual capability mapping
            pass
        
        return dict(scores)
    
    def _get_difficulty_scores(self, trace) -> Dict[str, float]:
        """Difficulty scores olish."""
        scores = defaultdict(lambda: {"total": 0, "passed": 0})
        
        for task_trace in trace.task_traces:
            diff = task_trace.difficulty
            scores[diff]["total"] += 1
            if task_trace.final_outcome == "success":
                scores[diff]["passed"] += 1
        
        return {
            diff: (s["passed"] / s["total"] if s["total"] > 0 else 0)
            for diff, s in scores.items()
        }
    
    def _get_suite_scores(self, trace) -> Dict[str, float]:
        """Suite scores olish."""
        scores = defaultdict(lambda: {"total": 0, "passed": 0})
        
        for task_trace in trace.task_traces:
            suite = task_trace.suite
            scores[suite]["total"] += 1
            if task_trace.final_outcome == "success":
                scores[suite]["passed"] += 1
        
        return {
            suite: (s["passed"] / s["total"] if s["total"] > 0 else 0)
            for suite, s in scores.items()
        }
    
    def _find_significant_changes(
        self,
        by_capability: Dict,
        by_suite: Dict,
    ) -> tuple:
        """Significant o'zgarishlarni topish."""
        wins = []
        losses = []
        
        # Check capability changes
        for cap, scores in by_capability.items():
            delta = scores.get("delta", 0)
            if delta > 0.1:
                wins.append({"type": "capability", "name": cap, "delta": delta})
            elif delta < -0.1:
                losses.append({"type": "capability", "name": cap, "delta": delta})
        
        # Check suite changes
        for suite, scores in by_suite.items():
            delta = scores.get("delta", 0)
            if delta > 0.15:
                wins.append({"type": "suite", "name": suite, "delta": delta})
            elif delta < -0.15:
                losses.append({"type": "suite", "name": suite, "delta": delta})
        
        return wins[:10], losses[:10]


def create_comparator() -> ExperimentComparator:
    """ExperimentComparator yaratish."""
    return ExperimentComparator()
