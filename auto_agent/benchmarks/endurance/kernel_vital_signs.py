"""
Kernel Vital Signs - Continuous System Health Monitoring
==================================================

This module provides continuous monitoring of kernel health metrics:
- Active tasks
- Retry pressure
- Memory load
- Irrelevant retrieval rate
- Tool failure pressure
- Replan pressure
- Checkpoint age
- Policy violations trend
- Cost burn rate
- Context compression ratio

Author: No1 World+ Autonomous System
"""

import asyncio
import time
import logging
import threading
import psutil
from typing import Dict, List, Optional, Any, Callable, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from collections import defaultdict, deque
import statistics
import json

logger = logging.getLogger(__name__)


# ==================== ENUMS ====================

class VitalStatus(str, Enum):
    """Vital sign status"""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"


class MetricType(str, Enum):
    """Types of vital metrics"""
    ACTIVE_TASKS = "active_tasks"
    RETRY_PRESSURE = "retry_pressure"
    MEMORY_LOAD = "memory_load"
    IRRELEVANT_RETRIEVAL = "irrelevant_retrieval"
    TOOL_FAILURE_PRESSURE = "tool_failure_pressure"
    REPLAN_PRESSURE = "replan_pressure"
    CHECKPOINT_AGE = "checkpoint_age"
    POLICY_VIOLATIONS = "policy_violations"
    COST_BURN_RATE = "cost_burn_rate"
    CONTEXT_COMPRESSION = "context_compression"


# ==================== DATA CLASSES ====================

@dataclass
class VitalMetric:
    """A single vital metric measurement"""
    metric_type: MetricType
    timestamp: datetime
    value: float
    unit: str
    status: VitalStatus


@dataclass
class VitalSnapshot:
    """Snapshot of all vital signs"""
    timestamp: datetime
    
    # Task metrics
    active_tasks: int
    queued_tasks: int
    completed_tasks: int
    failed_tasks: int
    
    # Performance metrics
    avg_task_duration: float
    success_rate: float
    retry_rate: float
    replan_rate: float
    
    # Resource metrics
    cpu_usage: float
    memory_usage_mb: float
    memory_percent: float
    
    # Quality metrics
    tool_failure_rate: float
    irrelevant_retrieval_rate: float
    policy_violation_rate: float
    
    # Cost metrics
    cost_accumulated: float
    cost_burn_rate: float
    
    # Context metrics
    context_tokens: int
    context_compression_ratio: float
    
    # Checkpoint metrics
    checkpoint_age_minutes: int
    checkpoint_count: int
    
    # Overall
    overall_status: VitalStatus
    health_score: float  # 0-100


@dataclass
class ThresholdConfig:
    """Configuration for metric thresholds"""
    metric: MetricType
    warning_low: Optional[float] = None
    warning_high: Optional[float] = None
    critical_low: Optional[float] = None
    critical_high: Optional[float] = None


# ==================== VITAL SIGN MONITOR ====================

class VitalSignMonitor:
    """Monitors individual vital signs"""
    
    def __init__(self, metric_type: MetricType, window_size: int = 60):
        self._type = metric_type
        self._window_size = window_size
        self._lock = threading.Lock()
        self._measurements: deque = deque(maxlen=window_size)
        self._thresholds: Dict[str, tuple] = {}
    
    def record(self, value: float, unit: str = ""):
        """Record a measurement"""
        with self._lock:
            status = self._evaluate_status(value)
            
            metric = VitalMetric(
                metric_type=self._type,
                timestamp=datetime.now(),
                value=value,
                unit=unit,
                status=status
            )
            
            self._measurements.append(metric)
            
            return status
    
    def _evaluate_status(self, value: float) -> VitalStatus:
        """Evaluate status based on thresholds"""
        if not self._thresholds:
            return VitalStatus.HEALTHY
        
        warning_low = self._thresholds.get("warning_low")
        warning_high = self._thresholds.get("warning_high")
        critical_low = self._thresholds.get("critical_low")
        critical_high = self._thresholds.get("critical_high")
        
        # Check critical first
        if critical_low is not None and value < critical_low:
            return VitalStatus.CRITICAL
        if critical_high is not None and value > critical_high:
            return VitalStatus.CRITICAL
        
        # Check warning
        if warning_low is not None and value < warning_low:
            return VitalStatus.WARNING
        if warning_high is not None and value > warning_high:
            return VitalStatus.WARNING
        
        return VitalStatus.HEALTHY
    
    def set_thresholds(self, warning_low: Optional[float] = None,
                     warning_high: Optional[float] = None,
                     critical_low: Optional[float] = None,
                     critical_high: Optional[float] = None):
        """Set threshold values"""
        self._thresholds = {
            "warning_low": warning_low,
            "warning_high": warning_high,
            "critical_low": critical_low,
            "critical_high": critical_high
        }
    
    def get_current(self) -> Optional[VitalMetric]:
        """Get most recent measurement"""
        with self._lock:
            if self._measurements:
                return self._measurements[-1]
            return None
    
    def get_average(self, window_minutes: Optional[int] = None) -> Optional[float]:
        """Get average value over window"""
        with self._lock:
            if not self._measurements:
                return None
            
            if window_minutes:
                cutoff = datetime.now() - timedelta(minutes=window_minutes)
                recent = [m.value for m in self._measurements if m.timestamp > cutoff]
            else:
                recent = [m.value for m in self._measurements]
            
            return statistics.mean(recent) if recent else None
    
    def get_trend(self) -> str:
        """Get trend direction"""
        with self._lock:
            if len(self._measurements) < 10:
                return "unknown"
            
            values = [m.value for m in list(self._measurements)[-10:]]
            
            first_half = values[:len(values)//2]
            second_half = values[len(values)//2:]
            
            first_avg = statistics.mean(first_half)
            second_avg = statistics.mean(second_half)
            
            if abs(second_avg - first_avg) / first_avg < 0.1:
                return "stable"
            elif second_avg > first_avg:
                return "increasing"
            else:
                return "decreasing"
    
    def get_status(self) -> VitalStatus:
        """Get current status"""
        current = self.get_current()
        if current:
            return current.status
        return VitalStatus.HEALTHY


# ==================== KERNEL VITAL SIGNS ====================

class KernelVitalSigns:
    """
    Continuous kernel health monitoring system.
    
    Features:
    - Multi-metric monitoring
    - Real-time status evaluation
    - Trend analysis
    - Alert generation
    - Historical tracking
    - Health scoring
    
    This is the kernel's "heart rate monitor" that tracks
    all critical health indicators in real-time.
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self._config = config or {}
        
        # Create monitors for each metric type
        self._monitors: Dict[MetricType, VitalSignMonitor] = {
            MetricType.ACTIVE_TASKS: VitalSignMonitor(MetricType.ACTIVE_TASKS),
            MetricType.RETRY_PRESSURE: VitalSignMonitor(MetricType.RETRY_PRESSURE),
            MetricType.MEMORY_LOAD: VitalSignMonitor(MetricType.MEMORY_LOAD),
            MetricType.IRRELEVANT_RETRIEVAL: VitalSignMonitor(MetricType.IRRELEVANT_RETRIEVAL),
            MetricType.TOOL_FAILURE_PRESSURE: VitalSignMonitor(MetricType.TOOL_FAILURE_PRESSURE),
            MetricType.REPLAN_PRESSURE: VitalSignMonitor(MetricType.REPLAN_PRESSURE),
            MetricType.CHECKPOINT_AGE: VitalSignMonitor(MetricType.CHECKPOINT_AGE),
            MetricType.POLICY_VIOLATIONS: VitalSignMonitor(MetricType.POLICY_VIOLATIONS),
            MetricType.COST_BURN_RATE: VitalSignMonitor(MetricType.COST_BURN_RATE),
            MetricType.CONTEXT_COMPRESSION: VitalSignMonitor(MetricType.CONTEXT_COMPRESSION)
        }
        
        # Configure thresholds
        self._configure_thresholds()
        
        # State
        self._is_monitoring = False
        self._snapshot_history: deque = deque(maxlen=100)
        
        # Callbacks
        self._on_warning: Optional[Callable] = None
        self._on_critical: Optional[Callable] = None
        self._on_status_change: Optional[Callable] = None
    
    def _configure_thresholds(self):
        """Configure thresholds for all metrics"""
        
        # Active tasks
        self._monitors[MetricType.ACTIVE_TASKS].set_thresholds(
            warning_high=15,
            critical_high=20
        )
        
        # Retry pressure
        self._monitors[MetricType.RETRY_PRESSURE].set_thresholds(
            warning_high=5,
            critical_high=10
        )
        
        # Memory load
        self._monitors[MetricType.MEMORY_LOAD].set_thresholds(
            warning_high=80,
            critical_high=95
        )
        
        # Irrelevant retrieval
        self._monitors[MetricType.IRRELEVANT_RETRIEVAL].set_thresholds(
            warning_high=0.3,
            critical_high=0.5
        )
        
        # Tool failure
        self._monitors[MetricType.TOOL_FAILURE_PRESSURE].set_thresholds(
            warning_high=0.2,
            critical_high=0.4
        )
        
        # Replan pressure
        self._monitors[MetricType.REPLAN_PRESSURE].set_thresholds(
            warning_high=0.3,
            critical_high=0.5
        )
        
        # Checkpoint age (in minutes)
        self._monitors[MetricType.CHECKPOINT_AGE].set_thresholds(
            warning_high=30,
            critical_high=60
        )
        
        # Policy violations
        self._monitors[MetricType.POLICY_VIOLATIONS].set_thresholds(
            warning_high=0.1,
            critical_high=0.2
        )
        
        # Cost burn rate
        self._monitors[MetricType.COST_BURN_RATE].set_thresholds(
            warning_high=100,
            critical_high=200
        )
        
        # Context compression (lower is better)
        self._monitors[MetricType.CONTEXT_COMPRESSION].set_thresholds(
            warning_low=0.5,
            critical_low=0.3
        )
    
    def set_callbacks(self,
                     on_warning: Optional[Callable] = None,
                     on_critical: Optional[Callable] = None,
                     on_status_change: Optional[Callable] = None):
        """Set callback functions"""
        self._on_warning = on_warning
        self._on_critical = on_critical
        self._on_status_change = on_status_change
    
    # ==================== METRIC RECORDING ====================
    
    def record_active_tasks(self, count: int):
        """Record active task count"""
        return self._monitors[MetricType.ACTIVE_TASKS].record(float(count), "tasks")
    
    def record_retry_pressure(self, retries_per_minute: float):
        """Record retry pressure"""
        return self._monitors[MetricType.RETRY_PRESSURE].record(retries_per_minute, "retries/min")
    
    def record_memory_load(self, usage_mb: float, usage_percent: float = 0):
        """Record memory load"""
        self._monitors[MetricType.MEMORY_LOAD].record(usage_mb, "MB")
        if usage_percent > 0:
            self._monitors[MetricType.MEMORY_LOAD].record(usage_percent, "%")
    
    def record_irrelevant_retrieval(self, rate: float):
        """Record irrelevant retrieval rate"""
        return self._monitors[MetricType.IRRELEVANT_RETRIEVAL].record(rate, "rate")
    
    def record_tool_failure(self, rate: float):
        """Record tool failure rate"""
        return self._monitors[MetricType.TOOL_FAILURE_PRESSURE].record(rate, "rate")
    
    def record_replan_pressure(self, rate: float):
        """Record replan rate"""
        return self._monitors[MetricType.REPLAN_PRESSURE].record(rate, "rate")
    
    def record_checkpoint_age(self, age_minutes: int):
        """Record checkpoint age"""
        return self._monitors[MetricType.CHECKPOINT_AGE].record(float(age_minutes), "minutes")
    
    def record_policy_violations(self, rate: float):
        """Record policy violation rate"""
        return self._monitors[MetricType.POLICY_VIOLATIONS].record(rate, "rate")
    
    def record_cost_burn(self, cost: float):
        """Record cost burn rate"""
        return self._monitors[MetricType.COST_BURN_RATE].record(cost, "$/hour")
    
    def record_context_compression(self, ratio: float):
        """Record context compression ratio"""
        return self._monitors[MetricType.CONTEXT_COMPRESSION].record(ratio, "ratio")
    
    # ==================== SNAPSHOT ====================
    
    def take_snapshot(self, task_stats: Optional[Dict] = None) -> VitalSnapshot:
        """Take a snapshot of all vital signs"""
        
        # Get current values
        active_tasks = int(self._monitors[MetricType.ACTIVE_TASKS].get_current().value 
                          if self._monitors[MetricType.ACTIVE_TASKS].get_current() else 0)
        
        retry_pressure = self._monitors[MetricType.RETRY_PRESSURE].get_average(5) or 0
        memory_mb = self._monitors[MetricType.MEMORY_LOAD].get_current().value \
                   if self._monitors[MetricType.MEMORY_LOAD].get_current() else 0
        
        irrelevant_rate = self._monitors[MetricType.IRRELEVANT_RETRIEVAL].get_average(10) or 0
        tool_failure_rate = self._monitors[MetricType.TOOL_FAILURE_PRESSURE].get_average(10) or 0
        replan_rate = self._monitors[MetricType.REPLAN_PRESSURE].get_average(10) or 0
        checkpoint_age = int(self._monitors[MetricType.CHECKPOINT_AGE].get_current().value \
                           if self._monitors[MetricType.CHECKPOINT_AGE].get_current() else 0)
        policy_violations = self._monitors[MetricType.POLICY_VIOLATIONS].get_average(10) or 0
        cost_burn = self._monitors[MetricType.COST_BURN_RATE].get_average(60) or 0
        context_compression = self._monitors[MetricType.CONTEXT_COMPRESSION].get_current().value \
                            if self._monitors[MetricType.CONTEXT_COMPRESSION].get_current() else 1.0
        
        # Get system resources
        try:
            process = psutil.Process()
            cpu_usage = process.cpu_percent(interval=0.1)
            memory_info = process.memory_info()
            memory_mb_actual = memory_info.rss / (1024 * 1024)
            memory_percent = process.memory_percent()
        except:
            cpu_usage = 0
            memory_mb_actual = memory_mb
            memory_percent = 0
        
        # Get task stats if provided
        if task_stats:
            queued = task_stats.get("queued", 0)
            completed = task_stats.get("completed", 0)
            failed = task_stats.get("failed", 0)
            success_rate = task_stats.get("success_rate", 1.0)
            avg_duration = task_stats.get("avg_duration", 0)
        else:
            queued = 0
            completed = 0
            failed = 0
            success_rate = 1.0
            avg_duration = 0
        
        # Determine overall status
        statuses = [m.get_status() for m in self._monitors.values()]
        
        if VitalStatus.CRITICAL in statuses:
            overall = VitalStatus.CRITICAL
        elif VitalStatus.WARNING in statuses:
            overall = VitalStatus.WARNING
        else:
            overall = VitalStatus.HEALTHY
        
        # Calculate health score
        health_score = self._calculate_health_score(statuses)
        
        snapshot = VitalSnapshot(
            timestamp=datetime.now(),
            active_tasks=active_tasks,
            queued_tasks=queued,
            completed_tasks=completed,
            failed_tasks=failed,
            avg_task_duration=avg_duration,
            success_rate=success_rate,
            retry_rate=retry_pressure,
            replan_rate=replan_rate,
            cpu_usage=cpu_usage,
            memory_usage_mb=memory_mb_actual,
            memory_percent=memory_percent,
            tool_failure_rate=tool_failure_rate,
            irrelevant_retrieval_rate=irrelevant_rate,
            policy_violation_rate=policy_violations,
            cost_accumulated=cost_burn,
            cost_burn_rate=cost_burn,
            context_tokens=0,  # Would be tracked separately
            context_compression_ratio=context_compression,
            checkpoint_age_minutes=checkpoint_age,
            checkpoint_count=0,
            overall_status=overall,
            health_score=health_score
        )
        
        self._snapshot_history.append(snapshot)
        
        # Check for status changes and trigger callbacks
        if len(self._snapshot_history) >= 2:
            prev = self._snapshot_history[-2]
            
            if prev.overall_status != snapshot.overall_status:
                if self._on_status_change:
                    self._on_status_change(prev.overall_status, snapshot.overall_status)
        
        # Check for warnings/critical
        if overall == VitalStatus.CRITICAL and self._on_critical:
            self._on_critical(snapshot)
        elif overall == VitalStatus.WARNING and self._on_warning:
            self._on_warning(snapshot)
        
        return snapshot
    
    def _calculate_health_score(self, statuses: List[VitalStatus]) -> float:
        """Calculate overall health score"""
        score = 100.0
        
        # Deduct for warnings and criticals
        critical_count = statuses.count(VitalStatus.CRITICAL)
        warning_count = statuses.count(VitalStatus.WARNING)
        
        score -= critical_count * 20
        score -= warning_count * 5
        
        return max(0, min(100, score))
    
    # ==================== QUERIES ====================
    
    def get_metric_status(self, metric: MetricType) -> VitalStatus:
        """Get status of specific metric"""
        if metric in self._monitors:
            return self._monitors[metric].get_status()
        return VitalStatus.HEALTHY
    
    def get_metric_trend(self, metric: MetricType) -> str:
        """Get trend of specific metric"""
        if metric in self._monitors:
            return self._monitors[metric].get_trend()
        return "unknown"
    
    def get_all_warnings(self) -> List[Dict]:
        """Get all metrics in warning or critical status"""
        warnings = []
        
        for metric, monitor in self._monitors.items():
            status = monitor.get_status()
            
            if status != VitalStatus.HEALTHY:
                current = monitor.get_current()
                
                warnings.append({
                    "metric": metric.value,
                    "status": status.value,
                    "value": current.value if current else None,
                    "unit": current.unit if current else None,
                    "trend": monitor.get_trend()
                })
        
        return warnings
    
    def get_health_score(self) -> float:
        """Get current health score"""
        if self._snapshot_history:
            return self._snapshot_history[-1].health_score
        return 100.0
    
    # ==================== MONITORING ====================
    
    async def start_monitoring(self, interval: int = 30):
        """Start continuous monitoring"""
        self._is_monitoring = True
        logger.info("Kernel vital signs monitoring started")
        
        while self._is_monitoring:
            await asyncio.sleep(interval)
            
            # Take snapshot with current stats
            self.take_snapshot()
            
            # Log health score periodically
            score = self.get_health_score()
            if score < 50:
                logger.warning(f"Health score critical: {score:.1f}")
            elif score < 80:
                logger.info(f"Health score warning: {score:.1f}")
    
    def stop_monitoring(self):
        """Stop monitoring"""
        self._is_monitoring = False
        logger.info("Kernel vital signs monitoring stopped")
    
    def get_recent_snapshots(self, count: int = 10) -> List[VitalSnapshot]:
        """Get recent snapshots"""
        return list(self._snapshot_history)[-count:]
    
    @property
    def is_monitoring(self) -> bool:
        return self._is_monitoring
    
    @property
    def health_score(self) -> float:
        return self.get_health_score()


# ==================== FACTORY ====================

def create_kernel_vital_signs(config: Optional[Dict] = None) -> KernelVitalSigns:
    """Factory function to create kernel vital signs monitor"""
    return KernelVitalSigns(config=config)
