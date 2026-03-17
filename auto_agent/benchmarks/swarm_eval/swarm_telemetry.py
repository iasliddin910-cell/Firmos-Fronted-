"""
SwarmTelemetry - Multi-Agent Monitoring

Bu modul multi-agent tizimni kuzatib boradi:
- worker utilization
- parallel branch count
- idle time
- duplicated effort
- coordination latency
- merge delay
- arbitration frequency
- reroute count
- failover success rate
"""

from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum
import time
from collections import defaultdict


class MetricType(Enum):
    """Telemetry metric types"""
    WORKER_UTILIZATION = "worker_utilization"
    PARALLEL_BRANCH_COUNT = "parallel_branch_count"
    IDLE_TIME = "idle_time"
    DUPLICATED_EFFORT = "duplicated_effort"
    COORDINATION_LATENCY = "coordination_latency"
    MERGE_DELAY = "merge_delay"
    ARBITRATION_FREQUENCY = "arbitration_frequency"
    REROUTE_COUNT = "reroute_count"
    FAILOVER_SUCCESS_RATE = "failover_success_rate"
    MESSAGE_COUNT = "message_count"
    MESSAGE_LATENCY = "message_latency"


@dataclass
class WorkerMetric:
    """Metrics for a single worker"""
    worker_id: str
    role: str
    utilization: float = 0.0
    active_time: float = 0.0
    idle_time: float = 0.0
    tasks_completed: int = 0
    tasks_failed: int = 0
    messages_sent: int = 0
    messages_received: int = 0


@dataclass
class SwarmTelemetryEvent:
    """A telemetry event"""
    event_type: MetricType
    timestamp: float
    worker_id: Optional[str]
    value: float
    metadata: Dict[str, Any] = field(default_factory=dict)


class SwarmTelemetry:
    """
    Monitors and collects multi-agent execution metrics.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.worker_metrics: Dict[str, WorkerMetric] = {}
        self.events: List[SwarmTelemetryEvent] = []
        self._start_time = time.time()
        
    def register_worker(self, worker_id: str, role: str) -> None:
        """Register a new worker"""
        self.worker_metrics[worker_id] = WorkerMetric(
            worker_id=worker_id,
            role=role
        )
    
    def record_worker_active(self, worker_id: str, duration: float) -> None:
        """Record worker active time"""
        if worker_id in self.worker_metrics:
            self.worker_metrics[worker_id].active_time += duration
            self.worker_metrics[worker_id].utilization = (
                self.worker_metrics[worker_id].active_time /
                (time.time() - self._start_time)
            )
    
    def record_worker_idle(self, worker_id: str, duration: float) -> None:
        """Record worker idle time"""
        if worker_id in self.worker_metrics:
            self.worker_metrics[worker_id].idle_time += duration
    
    def record_task_completed(self, worker_id: str) -> None:
        """Record task completion"""
        if worker_id in self.worker_metrics:
            self.worker_metrics[worker_id].tasks_completed += 1
    
    def record_task_failed(self, worker_id: str) -> None:
        """Record task failure"""
        if worker_id in self.worker_metrics:
            self.worker_metrics[worker_id].tasks_failed += 1
    
    def record_message(self, sender: str, receiver: str) -> None:
        """Record message sent between workers"""
        if sender in self.worker_metrics:
            self.worker_metrics[sender].messages_sent += 1
        if receiver in self.worker_metrics:
            self.worker_metrics[receiver].messages_received += 1
    
    def record_event(
        self,
        event_type: MetricType,
        value: float,
        worker_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Record a telemetry event"""
        event = SwarmTelemetryEvent(
            event_type=event_type,
            timestamp=time.time(),
            worker_id=worker_id,
            value=value,
            metadata=metadata or {}
        )
        self.events.append(event)
    
    def get_worker_utilization(self) -> Dict[str, float]:
        """Get utilization for all workers"""
        return {
            w_id: w.utilization
            for w_id, w in self.worker_metrics.items()
        }
    
    def get_total_idle_time(self) -> float:
        """Get total idle time across all workers"""
        return sum(w.idle_time for w in self.worker_metrics.values())
    
    def get_total_active_time(self) -> float:
        """Get total active time across all workers"""
        return sum(w.active_time for w in self.worker_metrics.values())
    
    def get_message_stats(self) -> Dict[str, Any]:
        """Get message statistics"""
        total_sent = sum(w.messages_sent for w in self.worker_metrics.values())
        total_received = sum(w.messages_received for w in self.worker_metrics.values())
        
        return {
            "total_sent": total_sent,
            "total_received": total_received,
            "balance": abs(total_sent - total_received),
            "per_worker": {
                w_id: {"sent": w.messages_sent, "received": w.messages_received}
                for w_id, w in self.worker_metrics.items()
            }
        }
    
    def get_task_stats(self) -> Dict[str, Any]:
        """Get task completion statistics"""
        total_completed = sum(w.tasks_completed for w in self.worker_metrics.values())
        total_failed = sum(w.tasks_failed for w in self.worker_metrics.values())
        total_tasks = total_completed + total_failed
        
        success_rate = total_completed / total_tasks if total_tasks > 0 else 0.0
        
        return {
            "total_completed": total_completed,
            "total_failed": total_failed,
            "success_rate": success_rate,
            "per_worker": {
                w_id: {
                    "completed": w.tasks_completed,
                    "failed": w.tasks_failed
                }
                for w_id, w in self.worker_metrics.items()
            }
        }
    
    def get_event_summary(self) -> Dict[str, int]:
        """Get summary of events by type"""
        summary = defaultdict(int)
        for event in self.events:
            summary[event.event_type.value] += 1
        return dict(summary)
    
    def get_full_report(self) -> Dict[str, Any]:
        """Get comprehensive telemetry report"""
        elapsed = time.time() - self._start_time
        
        return {
            "elapsed_time": elapsed,
            "worker_count": len(self.worker_metrics),
            "worker_utilization": self.get_worker_utilization(),
            "total_idle_time": self.get_total_idle_time(),
            "total_active_time": self.get_total_active_time(),
            "message_stats": self.get_message_stats(),
            "task_stats": self.get_task_stats(),
            "event_summary": self.get_event_summary()
        }


__all__ = [
    'SwarmTelemetry',
    'MetricType',
    'WorkerMetric',
    'SwarmTelemetryEvent'
]
