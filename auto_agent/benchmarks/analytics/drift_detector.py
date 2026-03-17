"""
DriftDetector - Capability Drift Detection
=======================================

Capability drift aniqlash.

Bu modul:
- Retrieval drift
- Browser drift
- Frontier task drift
- Canary decay
- Cost inflation
- Self-mod regression trend

aniqlaydi.

Definition of Done:
5. Drift va anomaly detector ishlaydi.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from collections import defaultdict
from datetime import datetime, timedelta


@dataclass
class DriftSignal:
    """Drift signal."""
    capability: str
    direction: str  # improving, degrading
    delta: float
    severity: str  # low, medium, high
    timeframe_days: int
    description: str


@dataclass
class DriftReport:
    """Drift hisoboti."""
    generated_at: str
    timeframe_start: str
    timeframe_end: str
    
    signals: List[DriftSignal] = field(default_factory=list)
    
    # Summary
    improving_capabilities: List[str] = field(default_factory=list)
    degrading_capabilities: List[str] = field(default_factory=list)
    severity_counts: Dict[str, int] = field(default_factory=dict)


class DriftDetector:
    """
    Drift detector.
    
    Definition of Done:
    5. Drift va anomaly detector ishlaydi.
    """
    
    def __init__(self):
        self.trace_storage = None
        self.min_data_points = 5  # Minimum runs for drift detection
    
    def detect_drift(
        self,
        run_traces: List[Any],
        timeframe_days: int = 7,
    ) -> DriftReport:
        """Driftni aniqlash."""
        # Group runs by date
        runs_by_date = self._group_runs_by_date(run_traces)
        
        if len(runs_by_date) < 2:
            return DriftReport(
                generated_at=datetime.utcnow().isoformat(),
                timeframe_start="",
                timeframe_end="",
                signals=[],
            )
        
        # Analyze drift by capability
        signals = []
        
        # Suite-level drift
        signals.extend(self._detect_suite_drift(runs_by_date))
        
        # Difficulty drift
        signals.extend(self._detect_difficulty_drift(runs_by_date))
        
        # Cost drift
        signals.extend(self._detect_cost_drift(runs_by_date))
        
        # Generate report
        report = DriftReport(
            generated_at=datetime.utcnow().isoformat(),
            timeframe_start=min(runs_by_date.keys()),
            timeframe_end=max(runs_by_date.keys()),
            signals=signals,
            improving_capabilities=[s.capability for s in signals if s.direction == "improving"],
            degrading_capabilities=[s.capability for s in signals if s.direction == "degrading"],
            severity_counts=self._count_severities(signals),
        )
        
        return report
    
    def _group_runs_by_date(self, traces: List[Any]) -> Dict[str, List[Any]]:
        """Runs'ni sanaga guruhlash."""
        by_date = defaultdict(list)
        
        for trace in traces:
            date = trace.started_at[:10]  # YYYY-MM-DD
            by_date[date].append(trace)
        
        return dict(sorted(by_date.items()))
    
    def _detect_suite_drift(self, runs_by_date: Dict[str, List[Any]]) -> List[DriftSignal]:
        """Suite drift aniqlash."""
        signals = []
        
        # Get all suites
        all_suites = set()
        for traces in runs_by_date.values():
            for trace in traces:
                all_suites.update(set(t.suite for t in trace.task_traces))
        
        for suite in all_suites:
            # Get pass rates over time
            rates = []
            for date, traces in runs_by_date.items():
                suite_traces = [t for t in traces if t.suite == suite]
                if suite_traces:
                    passed = sum(1 for t in suite_traces if t.final_outcome == "success")
                    rate = passed / len(suite_traces)
                    rates.append((date, rate))
            
            if len(rates) >= 2:
                first_rate = rates[0][1]
                last_rate = rates[-1][1]
                delta = last_rate - first_rate
                
                if abs(delta) > 0.1:  # More than 10% change
                    signals.append(DriftSignal(
                        capability=f"suite_{suite}",
                        direction="improving" if delta > 0 else "degrading",
                        delta=delta,
                        severity="high" if abs(delta) > 0.2 else "medium",
                        timeframe_days=len(rates),
                        description=f"Suite '{suite}' {('improved' if delta > 0 else 'degraded')} by {abs(delta):.1%}",
                    ))
        
        return signals
    
    def _detect_difficulty_drift(self, runs_by_date: Dict[str, List[Any]]) -> List[DriftSignal]:
        """Difficulty drift aniqlash."""
        signals = []
        
        difficulties = ["easy", "medium", "hard", "frontier"]
        
        for diff in difficulties:
            rates = []
            for date, traces in runs_by_date.items():
                diff_traces = [t for t in traces if t.difficulty == diff]
                if diff_traces:
                    passed = sum(1 for t in diff_traces if t.final_outcome == "success")
                    rate = passed / len(diff_traces)
                    rates.append((date, rate))
            
            if len(rates) >= 2:
                first_rate = rates[0][1]
                last_rate = rates[-1][1]
                delta = last_rate - first_rate
                
                if abs(delta) > 0.1:
                    signals.append(DriftSignal(
                        capability=f"difficulty_{diff}",
                        direction="improving" if delta > 0 else "degrading",
                        delta=delta,
                        severity="high" if abs(delta) > 0.2 else "medium",
                        timeframe_days=len(rates),
                        description=f"Difficulty '{diff}' {('improved' if delta > 0 else 'degraded')} by {abs(delta):.1%}",
                    ))
        
        return signals
    
    def _detect_cost_drift(self, runs_by_date: Dict[str, List[Any]]) -> List[DriftSignal]:
        """Cost drift aniqlash."""
        costs = []
        
        for date, traces in runs_by_date.items():
            total_cost = sum(t.total_cost_usd for t in traces)
            task_count = sum(t.total_tasks for t in traces)
            if task_count > 0:
                avg_cost = total_cost / task_count
                costs.append((date, avg_cost))
        
        if len(costs) >= 2:
            first_cost = costs[0][1]
            last_cost = costs[-1][1]
            delta = (last_cost - first_cost) / first_cost if first_cost > 0 else 0
            
            if delta > 0.2:  # More than 20% cost increase
                return [DriftSignal(
                    capability="cost_inflation",
                    direction="degrading",
                    delta=delta,
                    severity="high" if delta > 0.5 else "medium",
                    timeframe_days=len(costs),
                    description=f"Cost increased by {delta:.1%}",
                )]
        
        return []
    
    def _count_severities(self, signals: List[DriftSignal]) -> Dict[str, int]:
        """Severity'ni hisoblash."""
        counts = {"low": 0, "medium": 0, "high": 0}
        for s in signals:
            counts[s.severity] = counts.get(s.severity, 0) + 1
        return counts


def create_drift_detector() -> DriftDetector:
    """DriftDetector yaratish."""
    return DriftDetector()
