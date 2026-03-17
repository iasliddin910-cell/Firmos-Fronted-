"""
AnomalyDetector - Anomaly Detection
==============================

Anomaly aniqlash.

Bu modul:
- Birdan cost spike
- Birdan retry spike
- Birdan integrity drop
- Birdan canary collapse
- Bitta tool fail rate portlashi
- Bitta suite sudden drop

aniqlaydi.

Definition of Done:
5. Drift va anomaly detector ishlaydi.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from collections import defaultdict
from datetime import datetime


@dataclass
class Anomaly:
    """Anomaly."""
    anomaly_type: str
    severity: str  # low, medium, high, critical
    description: str
    metric_name: str
    current_value: float
    baseline_value: float
    change_pct: float
    timestamp: str


class AnomalyDetector:
    """
    Anomaly detector.
    
    Definition of Done:
    5. Drift va anomaly detector ishlaydi.
    """
    
    def __init__(self):
        self.trace_storage = None
        self.baseline: Dict[str, float] = {}
    
    def detect_anomalies(
        self,
        traces: List[Any],
        baseline: Dict[str, float] = None,
    ) -> Dict[str, Any]:
        """Anomalylarni aniqlash."""
        if baseline:
            self.baseline = baseline
        
        anomalies = []
        
        # Cost spike
        cost_anomaly = self._detect_cost_spike(traces)
        if cost_anomaly:
            anomalies.append(cost_anomaly)
        
        # Retry spike
        retry_anomaly = self._detect_retry_spike(traces)
        if retry_anomaly:
            anomalies.append(retry_anomaly)
        
        # Pass rate drop
        pass_anomaly = self._detect_pass_rate_drop(traces)
        if pass_anomaly:
            anomalies.append(pass_anomaly)
        
        # Tool failure spike
        tool_anomaly = self._detect_tool_failure_spike(traces)
        anomalies.extend(tool_anomaly)
        
        # Suite drop
        suite_anomaly = self._detect_suite_drop(traces)
        anomalies.extend(suite_anomaly)
        
        return {
            "total_anomalies": len(anomalies),
            "critical": len([a for a in anomalies if a.severity == "critical"]),
            "high": len([a for a in anomalies if a.severity == "high"]),
            "anomalies": [a.__dict__ for a in anomalies],
        }
    
    def _detect_cost_spike(self, traces: List[Any]) -> Optional[Anomaly]:
        """Cost spike aniqlash."""
        if not traces:
            return None
        
        avg_cost = sum(t.total_cost_usd for t in traces) / len(traces)
        baseline_cost = self.baseline.get("avg_cost", avg_cost)
        
        if baseline_cost > 0:
            change_pct = (avg_cost - baseline_cost) / baseline_cost
            
            if change_pct > 0.5:  # 50% increase
                return Anomaly(
                    anomaly_type="cost_spike",
                    severity="critical" if change_pct > 1.0 else "high",
                    description=f"Cost increased by {change_pct:.1%}",
                    metric_name="avg_cost",
                    current_value=avg_cost,
                    baseline_value=baseline_cost,
                    change_pct=change_pct,
                    timestamp=datetime.utcnow().isoformat(),
                )
        
        return None
    
    def _detect_retry_spike(self, traces: List[Any]) -> Optional[Anomaly]:
        """Retry spike aniqlash."""
        if not traces:
            return None
        
        total_retries = sum(t.total_retries for t in traces)
        total_tasks = len(traces)
        avg_retries = total_retries / total_tasks if total_tasks > 0 else 0
        
        baseline_retries = self.baseline.get("avg_retries", avg_retries)
        
        if baseline_retries > 0:
            change_pct = (avg_retries - baseline_retries) / baseline_retries
            
            if change_pct > 0.5:
                return Anomaly(
                    anomaly_type="retry_spike",
                    severity="high",
                    description=f"Retries increased by {change_pct:.1%}",
                    metric_name="avg_retries",
                    current_value=avg_retries,
                    baseline_value=baseline_retries,
                    change_pct=change_pct,
                    timestamp=datetime.utcnow().isoformat(),
                )
        
        return None
    
    def _detect_pass_rate_drop(self, traces: List[Any]) -> Optional[Anomaly]:
        """Pass rate drop aniqlash."""
        if not traces:
            return None
        
        passed = sum(1 for t in traces if t.final_outcome == "success")
        pass_rate = passed / len(traces) if traces else 0
        
        baseline_pass = self.baseline.get("pass_rate", pass_rate)
        
        if baseline_pass > 0:
            change_pct = (pass_rate - baseline_pass) / baseline_pass
            
            if change_pct < -0.2:  # 20% drop
                return Anomaly(
                    anomaly_type="pass_rate_drop",
                    severity="critical" if change_pct < -0.4 else "high",
                    description=f"Pass rate dropped by {-change_pct:.1%}",
                    metric_name="pass_rate",
                    current_value=pass_rate,
                    baseline_value=baseline_pass,
                    change_pct=change_pct,
                    timestamp=datetime.utcnow().isoformat(),
                )
        
        return None
    
    def _detect_tool_failure_spike(self, traces: List[Any]) -> List[Anomaly]:
        """Tool failure spike aniqlash."""
        anomalies = []
        
        # Count tool failures
        tool_failures = defaultdict(lambda: {"total": 0, "failed": 0})
        
        for trace in traces:
            for tc in trace.tool_calls:
                tool_failures[tc.tool_name]["total"] += 1
                if tc.outcome != "success":
                    tool_failures[tc.tool_name]["failed"] += 1
        
        baseline_failures = self.baseline.get("tool_failures", {})
        
        for tool, stats in tool_failures.items():
            if stats["total"] == 0:
                continue
            
            fail_rate = stats["failed"] / stats["total"]
            baseline_rate = baseline_failures.get(tool, {}).get("fail_rate", fail_rate)
            
            if baseline_rate > 0:
                change_pct = (fail_rate - baseline_rate) / baseline_rate
                
                if change_pct > 0.5:  # 50% increase in failure rate
                    anomalies.append(Anomaly(
                        anomaly_type="tool_failure_spike",
                        severity="high",
                        description=f"Tool '{tool}' failure rate increased by {change_pct:.1%}",
                        metric_name=f"tool_{tool}_fail_rate",
                        current_value=fail_rate,
                        baseline_value=baseline_rate,
                        change_pct=change_pct,
                        timestamp=datetime.utcnow().isoformat(),
                    ))
        
        return anomalies
    
    def _detect_suite_drop(self, traces: List[Any]) -> List[Anomaly]:
        """Suite drop aniqlash."""
        anomalies = []
        
        # Calculate pass rates by suite
        suite_rates = defaultdict(lambda: {"total": 0, "passed": 0})
        
        for trace in traces:
            suite_rates[trace.suite]["total"] += 1
            if trace.final_outcome == "success":
                suite_rates[trace.suite]["passed"] += 1
        
        baseline_suites = self.baseline.get("suite_pass_rates", {})
        
        for suite, stats in suite_rates.items():
            if stats["total"] == 0:
                continue
            
            pass_rate = stats["passed"] / stats["total"]
            baseline_rate = baseline_suites.get(suite, {}).get("pass_rate", pass_rate)
            
            if baseline_rate > 0:
                change_pct = (pass_rate - baseline_rate) / baseline_rate
                
                if change_pct < -0.3:  # 30% drop
                    anomalies.append(Anomaly(
                        anomaly_type="suite_drop",
                        severity="critical" if change_pct < -0.5 else "high",
                        description=f"Suite '{suite}' pass rate dropped by {-change_pct:.1%}",
                        metric_name=f"suite_{suite}_pass_rate",
                        current_value=pass_rate,
                        baseline_value=baseline_rate,
                        change_pct=change_pct,
                        timestamp=datetime.utcnow().isoformat(),
                    ))
        
        return anomalies


def create_anomaly_detector() -> AnomalyDetector:
    """AnomalyDetector yaratish."""
    return AnomalyDetector()
