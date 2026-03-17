"""
================================================================================
3. BENCHMARK COMPARISON ENGINE
================================================================================
Bu modul siz so'ragan "necha foiz yaxshilandi?" savoliga javob beradi.

Foiz faqat aniq o'lchangan joyda bo'lishi kerak.

Qattiq qoida:
Agent hech qachon:
- "umuman 30% aqlliroq bo'ldim"
- "overall much better"
- "significant improvement"

kabi bo'sh gap bilan qutulmasligi kerak.
================================================================================
"""
import os
import json
import logging
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from collections import defaultdict

from .reporting_types import MetricsImpact, TrustLevel

logger = logging.getLogger(__name__)


class BenchmarkComparisonEngine:
    """
    Benchmark Comparison Engine
    
    Aniq metrikalar bo'yicha before/after taqqoslash
    """
    
    def __init__(self):
        # Known benchmark types
        self.benchmark_types = [
            "task_success",
            "tool_success",
            "latency",
            "cost",
            "retry_rate",
            "failure_recovery",
            "capability_score"
        ]
        
        logger.info("📊 Benchmark Comparison Engine initialized")
    
    def compare(self,
              baseline_metrics: Dict[str, float],
              current_metrics: Dict[str, float],
              benchmark_coverage: float = 1.0) -> List[MetricsImpact]:
        """
        Benchmark taqqoslash
        
        Args:
            baseline_metrics: Asl metrikalar
            current_metrics: Joriy metrikalar
            benchmark_coverage: Benchmark qamrov (0-1)
        
        Returns:
            List[MetricsImpact]: Metrik ta'siri
        """
        impacts = []
        
        for metric_name, current_value in current_metrics.items():
            baseline_value = baseline_metrics.get(metric_name, current_value)
            
            # Calculate improvement
            if baseline_value == 0:
                if current_value == 0:
                    improvement = 0
                else:
                    improvement = 100  # New capability
            else:
                improvement = ((current_value - baseline_value) / baseline_value) * 100
            
            # Determine confidence based on coverage
            confidence = TrustLevel.HIGH
            if benchmark_coverage < 0.5:
                confidence = TrustLevel.LOW
            elif benchmark_coverage < 0.8:
                confidence = TrustLevel.MEDIUM
            
            impact = MetricsImpact(
                metric_name=metric_name,
                before_value=baseline_value,
                after_value=current_value,
                improvement_percent=round(improvement, 1),
                confidence=confidence
            )
            
            impacts.append(impact)
        
        return impacts
    
    def calculate_capability_metrics(self,
                                   code_delta: Dict,
                                   capability_delta: Dict) -> List[MetricsImpact]:
        """
        Capability metrikalarini hisoblash
        
        Args:
            code_delta: Code delta
            capability_delta: Capability delta
        
        Returns:
            List[MetricsImpact]: Metrik ta'siri
        """
        impacts = []
        
        # Analyze capability gains
        new_abilities = capability_delta.get("new_abilities", [])
        if new_abilities:
            impacts.append(MetricsImpact(
                metric_name="new_capabilities",
                before_value=0,
                after_value=len(new_abilities),
                improvement_percent=100 if new_abilities else 0,
                confidence=TrustLevel.HIGH
            ))
        
        # Analyze tool additions
        tool_delta = capability_delta.get("tool_delta", {})
        tools_added = len(tool_delta.get("tools_added", []))
        
        if tools_added:
            impacts.append(MetricsImpact(
                metric_name="tools_added",
                before_value=0,
                after_value=tools_added,
                improvement_percent=100,
                confidence=TrustLevel.HIGH
            ))
        
        return impacts
    
    def generate_metrics_summary(self, impacts: List[MetricsImpact]) -> Dict:
        """
        Metrikalar xulosasi
        
        Args:
            impacts: Metrik ta'sirlari
        
        Returns:
            Dict: Xulosa
        """
        if not impacts:
            return {
                "total": 0,
                "improved": 0,
                "worsened": 0,
                "unchanged": 0,
                "summary": "No metrics available"
            }
        
        improved = [i for i in impacts if i.improvement_percent > 0]
        worsened = [i for i in impacts if i.improvement_percent < 0]
        unchanged = [i for i in impacts if i.improvement_percent == 0]
        
        return {
            "total": len(impacts),
            "improved": len(improved),
            "worsened": len(worsened),
            "unchanged": len(unchanged),
            "improvement_rate": len(improved) / len(impacts) * 100 if impacts else 0,
            "top_improvements": [
                {"metric": i.metric_name, "change": f"+{i.improvement_percent:.1f}%"}
                for i in sorted(improved, key=lambda x: x.improvement_percent, reverse=True)[:5]
            ],
            "top_regressions": [
                {"metric": i.metric_name, "change": f"{i.improvement_percent:.1f}%"}
                for i in sorted(worsened, key=lambda x: x.improvement_percent)[:3]
            ]
        }
    
    def format_metric_claim(self, impact: MetricsImpact) -> str:
        """
        Metrik da'vosini formatlash
        
        Args:
            impact: Metrik ta'siri
        
        Returns:
            str: Formatlangan da'vo
        """
        # Format the metric claim properly
        sign = "+" if impact.improvement_percent > 0 else ""
        
        # For success metrics, improvement is good
        # For latency/cost metrics, lower is better
        is_lower_better = impact.metric_name in ["latency", "cost", "retry_rate", "failures"]
        
        if is_lower_better:
            # Negative improvement is actually good
            actual_change = -impact.improvement_percent
            direction = "↓" if actual_change > 0 else "↑"
        else:
            actual_change = impact.improvement_percent
            direction = "↑" if actual_change > 0 else "↓"
        
        return f"{impact.metric_name}: {impact.before_value:.1f} → {impact.after_value:.1f} ({sign}{actual_change:.1f}%) {direction}"


def create_benchmark_comparison_engine() -> BenchmarkComparisonEngine:
    """Benchmark Comparison Engine yaratish"""
    return BenchmarkComparisonEngine()
