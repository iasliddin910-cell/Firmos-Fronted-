"""
Capability Heatmap - Evaluation-Driven Control System
==================================================

This module tracks capability scores across the agent and provides
a real-time heatmap of strengths and weaknesses.

The heatmap is crucial for:
- Identifying which subsystems need attention
- Prioritizing interventions
- Tracking improvement over time
- Making data-driven decisions about what to fix next
"""
import time
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from collections import defaultdict
from datetime import datetime, timedelta

from .signals.failure_taxonomy import CAPABILITY_TAXONOMY

logger = logging.getLogger(__name__)


@dataclass
class CapabilityScore:
    """Score for a single capability"""
    capability_id: str
    score: float  # 0-1
    sample_count: int
    last_updated: float
    trend: str  # "improving", "stable", "declining"
    trend_delta: float = 0.0


@dataclass
class HeatmapEntry:
    """Entry in the capability heatmap"""
    capability_id: str
    display_name: str
    description: str
    
    # Current state
    score: float
    sample_count: int
    
    # Trend
    trend: str
    trend_delta: float
    
    # Priority
    priority: int  # 1 = highest priority to fix
    priority_reason: str
    
    # History
    history: List[Dict] = field(default_factory=list)


class CapabilityHeatmap:
    """
    ADVANCED Capability Heatmap that tracks all subsystem capabilities.
    
    This provides the "global view" needed for informed decision-making:
    - Which capabilities are strong
    - Which are weak and need attention
    - Which are improving/declining
    - Where to focus next
    """
    
    def __init__(self):
        # Capability scores storage
        self.capabilities: Dict[str, CapabilityScore] = {}
        
        # Initialize capabilities from taxonomy
        for cap_id, cap_info in CAPABILITY_TAXONOMY.items():
            self.capabilities[cap_id] = CapabilityScore(
                capability_id=cap_id,
                score=0.5,  # Default neutral score
                sample_count=0,
                last_updated=time.time(),
                trend="stable",
                trend_delta=0.0
            )
        
        # History for trend calculation
        self.score_history: Dict[str, List[Dict]] = defaultdict(list)
        
        # Configuration
        self.trend_window = 10  # Number of samples for trend
        self.min_samples_for_trend = 3
        
        logger.info("📊 CapabilityHeatmap initialized - tracking %d capabilities" % 
                   len(self.capabilities))
    
    def update_capability(
        self,
        capability_id: str,
        score: float,
        task_id: Optional[str] = None,
        benchmark_name: Optional[str] = None
    ):
        """Update a capability score based on benchmark result"""
        if capability_id not in self.capabilities:
            logger.warning(f"⚠️ Unknown capability: {capability_id}")
            return
        
        cap = self.capabilities[cap_id]
        
        # Update score with exponential moving average
        if cap.sample_count == 0:
            cap.score = score
        else:
            # Weight new sample at 20%
            cap.score = cap.score * 0.8 + score * 0.2
        
        cap.sample_count += 1
        cap.last_updated = time.time()
        
        # Record history
        self.score_history[capability_id].append({
            "timestamp": time.time(),
            "score": score,
            "task_id": task_id,
            "benchmark": benchmark_name
        })
        
        # Keep history bounded
        if len(self.score_history[capability_id]) > 100:
            self.score_history[capability_id] = self.score_history[capability_id][-100:]
        
        # Update trend
        self._update_trend(capability_id)
        
        logger.debug(f"📊 Updated {capability_id}: {cap.score:.2f} (trend: {cap.trend})")
    
    def update_from_benchmark_result(self, result: Dict):
        """Update heatmap from a benchmark result"""
        # Extract capability from result
        capability_id = result.get("capability")
        if not capability_id:
            # Try to infer from benchmark type
            benchmark_type = result.get("benchmark_type", "")
            capability_id = self._infer_capability(benchmark_type)
        
        if capability_id:
            score = result.get("score", result.get("success_rate", 0.5))
            self.update_capability(
                capability_id=capability_id,
                score=score,
                task_id=result.get("task_id"),
                benchmark_name=result.get("benchmark_name")
            )
    
    def update_from_failure_label(self, failure_label: Dict):
        """Update heatmap based on a failure diagnosis"""
        failed_capability = failure_label.get("failed_capability")
        if failed_capability:
            # Reduce score for failed capability
            current = self.capabilities.get(failed_capability)
            if current:
                new_score = max(0.0, current.score - 0.1)
                self.update_capability(
                    capability_id=failed_capability,
                    score=new_score,
                    task_id=failure_label.get("task_id")
                )
    
    def _infer_capability(self, benchmark_type: str) -> Optional[str]:
        """Infer capability from benchmark type"""
        mapping = {
            "planner": "planning",
            "planning": "planning",
            "memory": "retrieval",
            "retrieval": "retrieval",
            "self_mod": "patching",
            "patch": "patching",
            "browser": "browser_recovery",
            "tool": "tool_routing",
            "routing": "tool_routing",
            "safety": "self_mod_safety",
            "verification": "verification",
            "coding": "code_generation",
            "debug": "debugging",
            "tool_creation": "tool_creation",
            "learning": "learning"
        }
        
        for key, cap in mapping.items():
            if key in benchmark_type.lower():
                return cap
        
        return None
    
    def _update_trend(self, capability_id: str):
        """Calculate trend for a capability"""
        history = self.score_history[capability_id]
        
        if len(history) < self.min_samples_for_trend:
            self.capabilities[capability_id].trend = "stable"
            self.capabilities[capability_id].trend_delta = 0.0
            return
        
        # Calculate trend using recent samples
        recent = history[-self.trend_window:]
        
        if len(recent) < 2:
            return
        
        # Simple linear trend
        first_half = recent[:len(recent)//2]
        second_half = recent[len(recent)//2:]
        
        avg_first = sum(s["score"] for s in first_half) / len(first_half)
        avg_second = sum(s["score"] for s in second_half) / len(second_half)
        
        delta = avg_second - avg_first
        
        if delta > 0.05:
            trend = "improving"
        elif delta < -0.05:
            trend = "declining"
        else:
            trend = "stable"
        
        self.capabilities[capability_id].trend = trend
        self.capabilities[capability_id].trend_delta = delta
    
    def get_heatmap(self) -> List[HeatmapEntry]:
        """Get full heatmap with priorities"""
        entries = []
        
        for cap_id, cap in self.capabilities.items():
            # Get taxonomy info
            tax_info = CAPABILITY_TAXONOMY.get(cap_id, {})
            
            # Calculate priority
            priority, reason = self._calculate_priority(cap_id, cap)
            
            entry = HeatmapEntry(
                capability_id=cap_id,
                display_name=tax_info.get("display_name", cap_id),
                description=tax_info.get("description", ""),
                score=cap.score,
                sample_count=cap.sample_count,
                trend=cap.trend,
                trend_delta=cap.trend_delta,
                priority=priority,
                priority_reason=reason,
                history=self.score_history[cap_id][-10:]  # Last 10
            )
            
            entries.append(entry)
        
        # Sort by priority (highest first)
        entries.sort(key=lambda e: e.priority)
        
        return entries
    
    def _calculate_priority(self, capability_id: str, cap: CapabilityScore) -> tuple:
        """
        Calculate priority for fixing this capability.
        
        Priority factors:
        1. Low score (needs fixing)
        2. Declining trend (getting worse)
        3. High impact (affects many tasks)
        """
        priority = 0
        reasons = []
        
        # Factor 1: Score (lower = higher priority)
        if cap.score < 0.3:
            priority += 100
            reasons.append("critical_low_score")
        elif cap.score < 0.5:
            priority += 50
            reasons.append("low_score")
        elif cap.score < 0.7:
            priority += 20
            reasons.append("moderate_score")
        
        # Factor 2: Trend (declining = higher priority)
        if cap.trend == "declining":
            priority += 40
            reasons.append("declining_trend")
        
        # Factor 3: Sample count (more samples = more reliable)
        if cap.sample_count < 5:
            priority -= 10
            reasons.append("low_confidence")
        
        reason_str = ", ".join(reasons) if reasons else "normal"
        
        return priority, reason_str
    
    def get_top_priority_capabilities(self, n: int = 3) -> List[Dict]:
        """Get top N capabilities that need attention"""
        heatmap = self.get_heatmap()
        
        # Filter to capabilities with issues
        issues = [e for e in heatmap if e.priority > 20]
        
        return [
            {
                "capability_id": e.capability_id,
                "display_name": e.display_name,
                "score": e.score,
                "trend": e.trend,
                "priority": e.priority,
                "reason": e.priority_reason
            }
            for e in issues[:n]
        ]
    
    def get_capability_report(self) -> Dict:
        """Generate comprehensive capability report"""
        heatmap = self.get_heatmap()
        
        # Calculate overall health
        total_score = sum(e.score for e in heatmap)
        avg_score = total_score / len(heatmap) if heatmap else 0
        
        # Count by status
        status_counts = {
            "critical": len([e for e in heatmap if e.score < 0.3]),
            "warning": len([e for e in heatmap if 0.3 <= e.score < 0.5]),
            "ok": len([e for e in heatmap if 0.5 <= e.score < 0.7]),
            "good": len([e for e in heatmap if e.score >= 0.7])
        }
        
        # Trends
        trends = {
            "improving": len([e for e in heatmap if e.trend == "improving"]),
            "stable": len([e for e in heatmap if e.trend == "stable"]),
            "declining": len([e for e in heatmap if e.trend == "declining"])
        }
        
        return {
            "overall_health": avg_score,
            "status_counts": status_counts,
            "trends": trends,
            "top_priorities": self.get_top_priority_capabilities(5),
            "heatmap": [
                {
                    "capability_id": e.capability_id,
                    "display_name": e.display_name,
                    "score": e.score,
                    "trend": e.trend,
                    "priority": e.priority
                }
                for e in heatmap
            ]
        }
    
    def export_for_debugging(self) -> Dict:
        """Export heatmap data for debugging"""
        return {
            "capabilities": {
                cap_id: {
                    "score": cap.score,
                    "sample_count": cap.sample_count,
                    "last_updated": cap.last_updated,
                    "trend": cap.trend,
                    "trend_delta": cap.trend_delta
                }
                for cap_id, cap in self.capabilities.items()
            },
            "history": dict(self.score_history),
            "generated_at": time.time()
        }


def create_capability_heatmap() -> CapabilityHeatmap:
    """Factory function to create CapabilityHeatmap"""
    return CapabilityHeatmap()
