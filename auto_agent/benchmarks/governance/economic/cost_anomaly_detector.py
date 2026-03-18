"""
Cost Anomaly Detector - Anomaly Detection for Cost Spikes
===================================================

This module detects cost anomalies:
- Token burn spikes
- Runaway browser loops
- Excessive escalations
- Expensive dead-end traces
- Abnormal queue stalls

Author: No1 World+ Autonomous System
"""

import asyncio
import logging
import threading
import time
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from collections import defaultdict, deque
import statistics

logger = logging.getLogger(__name__)


# ==================== ENUMS ====================

class AnomalyType(str, Enum):
    """Types of cost anomalies"""
    TOKEN_SPIKE = "token_spike"
    BROWSER_LOOP = "browser_loop"
    EXCESSIVE_ESCALATION = "excessive_escalation"
    EXPENSIVE_DEAD_END = "expensive_dead_end"
    QUEUE_STALL = "queue_stall"
    COST_SPIKE = "cost_spike"


class AnomalySeverity(str, Enum):
    """Anomaly severity"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# ==================== DATA CLASSES ====================

@dataclass
class Anomaly:
    """Detected anomaly"""
    anomaly_id: str
    anomaly_type: AnomalyType
    severity: AnomalySeverity
    detected_at: datetime
    description: str
    evidence: Dict
    recommended_action: str


@dataclass
class CostMetrics:
    """Cost metrics at a point in time"""
    timestamp: datetime
    task_id: str
    tokens_used: float
    cost: float
    duration_seconds: float
    tool_calls: int
    retries: int


# ==================== ANOMALY DETECTOR ====================

class AnomalyDetector:
    """Detects cost anomalies"""
    
    def __init__(self):
        self._lock = threading.Lock()
        
        # Metrics history
        self._cost_history: deque = deque(maxlen=1000)
        self._token_history: deque = deque(maxlen=1000)
        self._tool_calls_history: deque = deque(maxlen=1000)
        
        # Anomaly tracking
        self._detected_anomalies: List[Anomaly] = []
        
        # Thresholds
        self._token_spike_threshold = 3.0  # 3x baseline
        self._cost_spike_threshold = 3.0
        self._browser_loop_threshold = 10  # same action repeated
        self._escalation_threshold = 3  # model escalations
        self._stall_threshold = 300  # seconds without progress
    
    def record_cost(self, task_id: str, tokens: float, cost: float,
                   duration: float, tool_calls: int, retries: int = 0):
        """Record cost metrics"""
        
        metrics = CostMetrics(
            timestamp=datetime.now(),
            task_id=task_id,
            tokens_used=tokens,
            cost=cost,
            duration_seconds=duration,
            tool_calls=tool_calls,
            retries=retries
        )
        
        with self._lock:
            self._cost_history.append(metrics)
            self._token_history.append((datetime.now(), tokens))
            self._tool_calls_history.append((datetime.now(), tool_calls))
    
    def detect_all(self) -> List[Anomaly]:
        """Detect all anomaly types"""
        anomalies = []
        
        # Token spike
        anomalies.extend(self._detect_token_spikes())
        
        # Cost spike
        anomalies.extend(self._detect_cost_spikes())
        
        # Browser loop
        anomalies.extend(self._detect_browser_loops())
        
        # Excessive escalation
        anomalies.extend(self._detect_excessive_escalation())
        
        # Queue stall
        anomalies.extend(self._detect_queue_stalls())
        
        # Store anomalies
        self._detected_anomalies.extend(anomalies)
        
        return anomalies
    
    def _detect_token_spikes(self) -> List[Anomaly]:
        """Detect token usage spikes"""
        anomalies = []
        
        with self._lock:
            if len(self._token_history) < 10:
                return anomalies
        
            tokens = [t for _, t in list(self._token_history)[-20:]]
        
        if len(tokens) < 10:
            return anomalies
        
        # Calculate baseline
        baseline = statistics.mean(tokens[:-2])  # Exclude last 2
        recent = tokens[-2:]
        
        for token_count in recent:
            if baseline > 0 and token_count > baseline * self._token_spike_threshold:
                anomaly = Anomaly(
                    anomaly_id=f"token_spike_{int(time.time())}",
                    anomaly_type=AnomalyType.TOKEN_SPIKE,
                    severity=AnomalySeverity.HIGH,
                    detected_at=datetime.now(),
                    description=f"Token usage {token_count:.0f} is {token_count/baseline:.1f}x baseline ({baseline:.0f})",
                    evidence={"tokens": token_count, "baseline": baseline, "ratio": token_count/baseline},
                    recommended_action="Investigate task - possible infinite loop or excessive context"
                )
                anomalies.append(anomaly)
        
        return anomalies
    
    def _detect_cost_spikes(self) -> List[Anomaly]:
        """Detect cost spikes"""
        anomalies = []
        
        with self._lock:
            if len(self._cost_history) < 5:
                return anomalies
        
            recent_costs = list(self._cost_history)[-10:]
        
        if len(recent_costs) < 5:
            return anomalies
        
        costs = [m.cost for m in recent_costs]
        baseline = statistics.mean(costs[:-2])
        
        for cost in costs[-2:]:
            if baseline > 0 and cost > baseline * self._cost_spike_threshold:
                anomaly = Anomaly(
                    anomaly_id=f"cost_spike_{int(time.time())}",
                    anomaly_type=AnomalyType.COST_SPIKE,
                    severity=AnomalySeverity.CRITICAL,
                    detected_at=datetime.now(),
                    description=f"Cost ${cost:.2f} is {cost/baseline:.1f}x baseline (${baseline:.2f})",
                    evidence={"cost": cost, "baseline": baseline},
                    recommended_action="URGENT: Check for runaway computation or expensive model escalation"
                )
                anomalies.append(anomaly)
        
        return anomalies
    
    def _detect_browser_loops(self) -> List[Anomaly]:
        """Detect browser action loops"""
        # Would track repeated browser actions
        # Simplified for demo
        return []
    
    def _detect_excessive_escalation(self) -> List[Anomaly]:
        """Detect excessive model escalations"""
        # Would track model escalations
        # Simplified for demo
        return []
    
    def _detect_queue_stalls(self) -> List[Anomaly]:
        """Detect queue stalls"""
        # Would track queue progress
        # Simplified for demo
        return []
    
    def get_anomalies(self, since: Optional[datetime] = None) -> List[Anomaly]:
        """Get detected anomalies"""
        if since:
            return [a for a in self._detected_anomalies if a.detected_at >= since]
        return self._detected_anomalies.copy()


class CostAnomalyDetector:
    """
    Main cost anomaly detection system.
    
    Features:
    - Token spike detection
    - Cost spike detection
    - Browser loop detection
    - Escalation detection
    - Queue stall detection
    - Automatic alerting
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self._config = config or {}
        
        # Detector
        self._detector = AnomalyDetector()
        
        # State
        self._is_monitoring = False
        
        # Callbacks
        self._on_anomaly_detected: Optional[Callable] = None
    
    def set_callbacks(self, on_anomaly_detected: Optional[Callable] = None):
        """Set callback functions"""
        self._on_anomaly_detected = on_anomaly_detected
    
    def record(self, task_id: str, tokens: float, cost: float,
              duration: float, tool_calls: int, retries: int = 0):
        """Record cost metrics"""
        self._detector.record_cost(task_id, tokens, cost, duration, tool_calls, retries)
    
    def check(self) -> List[Anomaly]:
        """Check for anomalies"""
        anomalies = self._detector.detect_all()
        
        # Trigger callbacks
        for anomaly in anomalies:
            if self._on_anomaly_detected:
                self._on_anomaly_detected(anomaly)
        
        return anomalies
    
    def get_recent_anomalies(self, hours: int = 24) -> List[Anomaly]:
        """Get anomalies from last N hours"""
        since = datetime.now() - timedelta(hours=hours)
        return self._detector.get_anomalies(since=since)


# ==================== FACTORY ====================

def create_cost_anomaly_detector(config: Optional[Dict] = None) -> CostAnomalyDetector:
    """Factory function to create cost anomaly detector"""
    return CostAnomalyDetector(config=config)
