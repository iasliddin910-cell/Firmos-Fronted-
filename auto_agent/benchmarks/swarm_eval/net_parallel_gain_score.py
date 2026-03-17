"""
NetParallelGainScore - Single vs Multi-Agent Comparison

Bu modul single-agent vs multi-agent taqqoslashni olchaydi:
- quality delta
- speed delta
- cost delta
- retry delta
- merge risk delta

Policy 6: Net-parallel-gain bo'lmasa stable promote yo'q.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import time


class GainType(Enum):
    """Types of parallel gain"""
    QUALITY = "quality"
    SPEED = "speed"
    COST = "cost"
    RELIABILITY = "reliability"


@dataclass
class BaselineMetrics:
    """Metrics from single-agent baseline"""
    duration: float
    cost: float
    success: bool
    retry_count: int
    quality_score: float


@dataclass
class MultiAgentMetrics:
    """Metrics from multi-agent execution"""
    duration: float
    cost: float
    success: bool
    retry_count: int
    quality_score: float
    workers_used: int
    parallel_branches: int


@dataclass
class GainScore:
    """Net parallel gain score"""
    gain_type: GainType
    baseline_value: float
    multi_agent_value: float
    delta: float
    percentage_change: float
    is_positive: bool


class NetParallelGainScore:
    """
    Calculates net parallel gain comparing single-agent vs multi-agent.
    
    Policy 6: Net-parallel-gain bo'lmasa stable promote yo'q.
    """
    
    # Thresholds
    MIN_GAIN_THRESHOLD = 0.1  # 10% minimum gain required
    QUALITY_WEIGHT = 0.4
    SPEED_WEIGHT = 0.3
    COST_WEIGHT = 0.2
    RELIABILITY_WEIGHT = 0.1
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.history: List[Dict[str, Any]] = []
        
    def calculate_gain(
        self,
        baseline: BaselineMetrics,
        multi_agent: MultiAgentMetrics
    ) -> Dict[str, Any]:
        """
        Calculate net parallel gain.
        
        Args:
            baseline: Single-agent baseline metrics
            multi_agent: Multi-agent execution metrics
            
        Returns:
            Dictionary with gain analysis
        """
        # Calculate individual gains
        quality_gain = self._calculate_quality_gain(baseline, multi_agent)
        speed_gain = self._calculate_speed_gain(baseline, multi_agent)
        cost_gain = self._calculate_cost_gain(baseline, multi_agent)
        reliability_gain = self._calculate_reliability_gain(baseline, multi_agent)
        
        gains = [quality_gain, speed_gain, cost_gain, reliability_gain]
        
        # Calculate weighted net gain
        net_gain = (
            quality_gain.delta * self.QUALITY_WEIGHT +
            speed_gain.delta * self.SPEED_WEIGHT +
            cost_gain.delta * self.COST_WEIGHT +
            reliability_gain.delta * self.RELIABILITY_WEIGHT
        )
        
        # Overall assessment
        is_positive = net_gain > self.MIN_GAIN_THRESHOLD
        
        result = {
            "net_gain": net_gain,
            "is_positive": is_positive,
            "quality_gain": self._gain_to_dict(quality_gain),
            "speed_gain": self._gain_to_dict(speed_gain),
            "cost_gain": self._gain_to_dict(cost_gain),
            "reliability_gain": self._gain_to_dict(reliability_gain),
            "can_promote": is_positive
        }
        
        self.history.append(result)
        
        return result
    
    def _calculate_quality_gain(
        self,
        baseline: BaselineMetrics,
        multi_agent: MultiAgentMetrics
    ) -> GainScore:
        """Calculate quality gain"""
        base_val = baseline.quality_score
        multi_val = multi_agent.quality_score
        
        delta = multi_val - base_val
        pct = (delta / base_val) if base_val > 0 else 0
        
        return GainScore(
            gain_type=GainType.QUALITY,
            baseline_value=base_val,
            multi_agent_value=multi_val,
            delta=delta,
            percentage_change=pct,
            is_positive=delta >= 0
        )
    
    def _calculate_speed_gain(
        self,
        baseline: BaselineMetrics,
        multi_agent: MultiAgentMetrics
    ) -> GainScore:
        """Calculate speed gain"""
        base_val = baseline.duration
        multi_val = multi_agent.duration
        
        if base_val <= 0:
            return GainScore(
                gain_type=GainType.SPEED,
                baseline_value=base_val,
                multi_agent_value=multi_val,
                delta=0,
                percentage_change=0,
                is_positive=True
            )
        
        # Speedup ratio (higher is better)
        speedup = base_val / multi_val if multi_val > 0 else 0
        delta = speedup - 1.0  # 0 = no change, positive = faster
        pct = (delta / 1.0)  # Normalize
        
        return GainScore(
            gain_type=GainType.SPEED,
            baseline_value=base_val,
            multi_agent_value=multi_val,
            delta=delta,
            percentage_change=pct,
            is_positive=delta >= 0
        )
    
    def _calculate_cost_gain(
        self,
        baseline: BaselineMetrics,
        multi_agent: MultiAgentMetrics
    ) -> GainScore:
        """Calculate cost gain"""
        base_val = baseline.cost
        multi_val = multi_agent.cost
        
        if base_val <= 0:
            return GainScore(
                gain_type=GainType.COST,
                baseline_value=base_val,
                multi_agent_value=multi_val,
                delta=0,
                percentage_change=0,
                is_positive=True
            )
        
        # Cost ratio (lower is better)
        cost_ratio = multi_val / base_val
        delta = 1.0 - cost_ratio  # Positive = cheaper
        pct = delta
        
        return GainScore(
            gain_type=GainType.COST,
            baseline_value=base_val,
            multi_agent_value=multi_val,
            delta=delta,
            percentage_change=pct,
            is_positive=delta >= 0
        )
    
    def _calculate_reliability_gain(
        self,
        baseline: BaselineMetrics,
        multi_agent: MultiAgentMetrics
    ) -> GainScore:
        """Calculate reliability gain"""
        base_val = baseline.success
        multi_val = multi_agent.success
        
        delta = multi_val - base_val
        pct = delta  # Already -1 to 1
        
        return GainScore(
            gain_type=GainType.RELIABILITY,
            baseline_value=base_val,
            multi_agent_value=multi_val,
            delta=delta,
            percentage_change=pct,
            is_positive=delta >= 0
        )
    
    def _gain_to_dict(self, gain: GainScore) -> Dict[str, Any]:
        """Convert GainScore to dictionary"""
        return {
            "baseline_value": gain.baseline_value,
            "multi_agent_value": gain.multi_agent_value,
            "delta": gain.delta,
            "percentage_change": gain.percentage_change,
            "is_positive": gain.is_positive
        }
    
    def can_promote_to_stable(
        self,
        baseline: BaselineMetrics,
        multi_agent: MultiAgentMetrics
    ) -> Dict[str, Any]:
        """
        Determine if multi-agent can be promoted to stable.
        
        Policy 6: Net-parallel-gain bo'lmasa stable promote yo'q.
        """
        result = self.calculate_gain(baseline, multi_agent)
        
        promotion_decision = {
            "can_promote": result["can_promote"],
            "net_gain": result["net_gain"],
            "reason": ""
        }
        
        if not result["can_promote"]:
            promotion_decision["reason"] = (
                f"Net gain {result['net_gain']:.2f} is below "
                f"threshold {self.MIN_GAIN_THRESHOLD}"
            )
        elif result["quality_gain"]["is_positive"] and result["speed_gain"]["is_positive"]:
            promotion_decision["reason"] = "Quality and speed gains are positive"
        else:
            # Check individual failures
            issues = []
            if not result["quality_gain"]["is_positive"]:
                issues.append("quality decreased")
            if not result["speed_gain"]["is_positive"]:
                issues.append("speed decreased")
            
            if issues:
                promotion_decision["can_promote"] = False
                promotion_decision["reason"] = f"Issues: {', '.join(issues)}"
        
        return promotion_decision
    
    def get_gain_history(self) -> List[Dict[str, Any]]:
        """Get history of gain calculations"""
        return self.history
    
    def get_average_gain(self) -> Dict[str, float]:
        """Get average gain across all calculations"""
        if not self.history:
            return {"net_gain": 0.0}
        
        return {
            "net_gain": sum(h["net_gain"] for h in self.history) / len(self.history),
            "quality_gain": sum(h["quality_gain"]["delta"] for h in self.history) / len(self.history),
            "speed_gain": sum(h["speed_gain"]["delta"] for h in self.history) / len(self.history),
            "cost_gain": sum(h["cost_gain"]["delta"] for h in self.history) / len(self.history),
            "reliability_gain": sum(h["reliability_gain"]["delta"] for h in self.history) / len(self.history)
        }


__all__ = [
    'NetParallelGainScore',
    'GainType',
    'BaselineMetrics',
    'MultiAgentMetrics',
    'GainScore'
]
