"""
Marginal Gain Tracker - Value vs Cost Tracking
===========================================

This module tracks marginal gains and costs:
- Capability delta
- Cost delta
- Throughput delta
- Stability delta

Author: No1 World+ Autonomous System
"""

import logging
import threading
import time
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class ImprovementType(str, Enum):
    """Types of improvements"""
    PATCH = "patch"
    NEW_TOOL = "new_tool"
    POLICY_CHANGE = "policy_change"
    MODEL_UPGRADE = "model_upgrade"


@dataclass
class ImprovementMetrics:
    """Metrics for an improvement"""
    improvement_id: str
    improvement_type: ImprovementType
    timestamp: datetime
    
    # Capability
    capability_delta: float  # +% in capability
    
    # Cost
    cost_delta: float  # +% in cost
    
    # Throughput
    throughput_delta: float  # +% in throughput
    
    # Stability
    stability_delta: float  # +% in stability
    
    # Net value
    net_value: float


class MarginalGainTracker:
    """Track marginal gains of improvements"""
    
    def __init__(self):
        self._lock = threading.Lock()
        self._improvements: Dict[str, ImprovementMetrics] = {}
    
    def record_improvement(self, improvement_id: str, improvement_type: ImprovementType,
                         capability_delta: float, cost_delta: float,
                         throughput_delta: float, stability_delta: float):
        """Record improvement metrics"""
        
        # Calculate net value (positive = good)
        net_value = capability_delta + throughput_delta + stability_delta - cost_delta
        
        metrics = ImprovementMetrics(
            improvement_id=improvement_id,
            improvement_type=improvement_type,
            timestamp=datetime.now(),
            capability_delta=capability_delta,
            cost_delta=cost_delta,
            throughput_delta=throughput_delta,
            stability_delta=stability_delta,
            net_value=net_value
        )
        
        with self._lock:
            self._improvements[improvement_id] = metrics
    
    def get_best_improvements(self, limit: int = 10) -> List[ImprovementMetrics]:
        """Get improvements sorted by net value"""
        with self._lock:
            sorted_improvements = sorted(
                self._improvements.values(),
                key=lambda x: x.net_value,
                reverse=True
            )
            return sorted_improvements[:limit]
    
    def get_roi_ranking(self) -> List[Dict]:
        """Get improvements ranked by ROI"""
        with self._lock:
            roi_list = []
            
            for imp in self._improvements.values():
                # ROI = net value / cost
                if imp.cost_delta > 0:
                    roi = imp.net_value / imp.cost_delta
                else:
                    roi = float('inf')
                
                roi_list.append({
                    "improvement_id": imp.improvement_id,
                    "type": imp.improvement_type.value,
                    "net_value": imp.net_value,
                    "cost_delta": imp.cost_delta,
                    "roi": roi
                })
            
            return sorted(roi_list, key=lambda x: x["roi"], reverse=True)


def create_marginal_gain_tracker() -> MarginalGainTracker:
    return MarginalGainTracker()
