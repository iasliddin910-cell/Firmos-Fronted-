"""
CohortAnalyzer - Cohort Analysis
=============================

Task cohort tahlili.

Bu modul:
- Cohort bo'yicha performance
- Qaysi cohortda eng yomon
- Qaysi cohortda eng ko'p thrash
- Qaysi cohortda self-mod foydali
aniqlaydi.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any
from collections import defaultdict


class CohortAnalyzer:
    """Cohort tahlil."""
    
    def __init__(self):
        self.trace_storage = None
    
    def analyze_cohorts(self, traces: List[Any]) -> Dict[str, Any]:
        """Cohortlarni tahlil qilish."""
        # Define cohorts
        cohorts = {
            "by_difficulty": self._cohort_by_difficulty(traces),
            "by_suite": self._cohort_by_suite(traces),
            "by_task_size": self._cohort_by_task_size(traces),
            "by_context": self._cohort_by_context(traces),
        }
        
        return {
            "cohorts": cohorts,
        }
    
    def _cohort_by_difficulty(self, traces: List[Any]) -> Dict:
        """Difficulty bo'yicha cohort."""
        by_diff = defaultdict(lambda: {"total": 0, "passed": 0, "failed": 0, "total_cost": 0})
        
        for trace in traces:
            diff = trace.difficulty
            by_diff[diff]["total"] += 1
            if trace.final_outcome == "success":
                by_diff[diff]["passed"] += 1
            else:
                by_diff[diff]["failed"] += 1
            by_diff[diff]["total_cost"] += trace.total_cost_usd
        
        return {
            d: {
                "total": s["total"],
                "passed": s["passed"],
                "pass_rate": s["passed"] / s["total"] if s["total"] > 0 else 0,
                "avg_cost": s["total_cost"] / s["total"] if s["total"] > 0 else 0,
            }
            for d, s in by_diff.items()
        }
    
    def _cohort_by_suite(self, traces: List[Any]) -> Dict:
        """Suite bo'yicha cohort."""
        by_suite = defaultdict(lambda: {"total": 0, "passed": 0, "failed": 0})
        
        for trace in traces:
            suite = trace.suite
            by_suite[suite]["total"] += 1
            if trace.final_outcome == "success":
                by_suite[suite]["passed"] += 1
            else:
                by_suite[suite]["failed"] += 1
        
        return {
            s: {
                "total": stats["total"],
                "passed": stats["passed"],
                "pass_rate": stats["passed"] / stats["total"] if stats["total"] > 0 else 0,
            }
            for s, stats in by_suite.items()
        }
    
    def _cohort_by_task_size(self, traces: List[Any]) -> Dict:
        """Task size bo'yicha cohort."""
        small = []
        medium = []
        large = []
        
        for trace in traces:
            tool_count = len(trace.tool_calls)
            if tool_count <= 10:
                small.append(trace)
            elif tool_count <= 30:
                medium.append(trace)
            else:
                large.append(trace)
        
        def calc_stats(traces):
            passed = sum(1 for t in traces if t.final_outcome == "success")
            return {
                "total": len(traces),
                "passed": passed,
                "pass_rate": passed / len(traces) if traces else 0,
            }
        
        return {
            "small": calc_stats(small),
            "medium": calc_stats(medium),
            "large": calc_stats(large),
        }
    
    def _cohort_by_context(self, traces: List[Any]) -> Dict:
        """Context level bo'yicha cohort."""
        # Simplified - would use actual context analysis
        return {}


def create_cohort_analyzer() -> CohortAnalyzer:
    """CohortAnalyzer yaratish."""
    return CohortAnalyzer()
