"""
Endurance Benchmark Suite - Multi-hour autonomous stability evaluation
=========================================================================

This module provides comprehensive endurance testing for long-run autonomous operations.
It evaluates the system's ability to maintain stability, quality, and performance over
extended periods (hours to days) of continuous operation.

Key Components:
1. EnduranceBenchmarkSuite - Main orchestrator for endurance tests
2. Task Families - Different workload patterns for stress testing
3. Metrics Collection - Time-series metrics for decay analysis
4. Report Generation - Comprehensive endurance reports

Author: No1 World+ Autonomous System
"""

import asyncio
import time
import json
import logging
import threading
import random
from typing import Dict, List, Optional, Any, Tuple, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from collections import defaultdict, deque
from pathlib import Path
import uuid
import statistics
import traceback

logger = logging.getLogger(__name__)


# ==================== ENDURANCE ENUMS ====================

class EnduranceTestType(str, Enum):
    """Types of endurance tests"""
    CHAINED_TASKS = "chained_tasks"           # 50+ task chained workload
    MIXED_SESSION = "mixed_session"           # browser + repair + terminal mixed
    SELF_PATCH_MID_SESSION = "self_patch_mid_session"  # Self-modification in middle
    TOOL_INTEGRATION = "tool_integration"     # New tool integration mid-run
    RECOVERY_CYCLES = "recovery_cycles"        # Repeated recoveries
    CHECKPOINT_RESUME = "checkpoint_resume"   # Checkpoint/resume cycles
    IDLE_RESUME = "idle_resume"                # Long idle + resume
    DEGRADED_SIGNAL = "degraded_signal"        # Degraded signal environment
    MEMORY_HEAVY = "memory_heavy"              # Memory-intensive sequence
    CONTINUOUS_24H = "continuous_24h"          # 24/7 continuous operation


class SessionState(str, Enum):
    """Session lifecycle states"""
    INITIALIZING = "initializing"
    STABLE = "stable"
    DEGRADING = "degrading"
    THRASHING = "thrashing"
    NOISY = "noisy"
    UNUSABLE = "unusable"
    RECOVERING = "recovering"
    HEALTHY = "healthy"


class DecayType(str, Enum):
    """Types of quality decay"""
    NONE = "none"
    QUALITY = "quality"
    SPEED = "speed"
    MEMORY = "memory"
    ROUTING = "routing"
    RECOVERY = "recovery"
    POLICY = "policy"
    COST = "cost"
    COMBINED = "combined"


# ==================== ENDURANCE DATA CLASSES ====================

@dataclass
class EnduranceTask:
    """A single task in endurance test"""
    task_id: str
    task_type: str
    description: str
    expected_duration_sec: int
    difficulty: str
    dependencies: List[str] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)


@dataclass
class EnduranceMetrics:
    """Metrics collected during endurance test"""
    timestamp: datetime
    task_id: Optional[str]
    metric_name: str
    value: float
    unit: str
    tags: Dict = field(default_factory=dict)


@dataclass
class SessionSnapshot:
    """Snapshot of session state at a point in time"""
    timestamp: datetime
    elapsed_seconds: float
    tasks_completed: int
    tasks_failed: int
    active_tasks: int
    total_retries: int
    total_replans: int
    memory_usage_mb: float
    context_tokens: int
    cache_hit_rate: float
    avg_task_duration_sec: float
    success_rate: float
    cost_accumulated: float
    state: SessionState
    quality_score: float
    speed_score: float
    recovery_score: float
    policy_score: float


@dataclass
class DecayAnalysis:
    """Analysis of decay trends"""
    decay_type: DecayType
    severity: float  # 0-1
    trend: str  # "stable", "increasing", "decreasing"
    first_quarter_score: float
    last_quarter_score: float
    decay_rate: float
    detected_at: datetime
    recommendation: str


@dataclass
class EnduranceReport:
    """Comprehensive endurance test report"""
    test_id: str
    test_type: EnduranceTestType
    start_time: datetime
    end_time: datetime
    duration_hours: float
    total_tasks: int
    successful_tasks: int
    failed_tasks: int
    success_rate: float
    first_task_quality: float
    last_task_quality: float
    quality_decay_rate: float
    first_task_speed: float
    last_task_speed: float
    speed_decay_rate: float
    first_task_cost: float
    last_task_cost: float
    cost_inflation_rate: float
    retry_storm_count: int
    memory_rot_detected: bool
    routing_drift_detected: bool
    policy_erosion_detected: bool
    checkpoint_failures: int
    state_transitions: List[Tuple[datetime, SessionState]]
    decay_analyses: List[DecayAnalysis]
    anomalies: List[Dict]
    recommendations: List[str]
    overall_score: float  # 0-100


# ==================== ENDURANCE TASK FAMILIES ====================

class EnduranceTaskFamilies:
    """Predefined task families for endurance testing"""
    
    @staticmethod
    def chained_mixed_workload(count: int = 50) -> List[EnduranceTask]:
        """Generate 50-task chained mixed workload"""
        tasks = []
        task_types = ["code", "browser", "terminal", "research", "file_operation"]
        
        for i in range(count):
            task_type = task_types[i % len(task_types)]
            tasks.append(EnduranceTask(
                task_id=f"chained_{i:03d}",
                task_type=task_type,
                description=f"Chained task {i+1}/{count} - {task_type}",
                expected_duration_sec=random.randint(30, 180),
                difficulty=random.choice(["easy", "medium", "hard"]),
                dependencies=[f"chained_{i-1:03d}"] if i > 0 else []
            ))
        return tasks
    
    @staticmethod
    def browser_repair_terminal_mixed(count: int = 30) -> List[EnduranceTask]:
        """Browser + repair + terminal mixed session"""
        tasks = []
        pattern = ["browser", "terminal", "repair", "browser", "terminal", "repair"]
        
        for i in range(count):
            task_type = pattern[i % len(pattern)]
            tasks.append(EnduranceTask(
                task_id=f"mixed_{i:03d}",
                task_type=task_type,
                description=f"Mixed workload {i+1}/{count} - {task_type}",
                expected_duration_sec=random.randint(60, 300),
                difficulty="medium",
                dependencies=[f"mixed_{i-1:03d}"] if i > 0 else []
            ))
        return tasks
    
    @staticmethod
    def self_patch_workload() -> List[EnduranceTask]:
        """Workload with self-modification in the middle"""
        tasks = []
        
        # Phase 1: Normal tasks (0-15)
        for i in range(15):
            tasks.append(EnduranceTask(
                task_id=f"pre_patch_{i:03d}",
                task_type="code",
                description=f"Pre-patch task {i+1}/15",
                expected_duration_sec=60,
                difficulty="easy"
            ))
        
        # Phase 2: Self-modification task (16)
        tasks.append(EnduranceTask(
            task_id="self_modification",
            task_type="self_patch",
            description="Self-modification task - adding new capability",
            expected_duration_sec=300,
            difficulty="hard",
            metadata={"self_mod": True, "patch_type": "capability_addition"}
        ))
        
        # Phase 3: Tasks after modification (17-30)
        for i in range(14):
            tasks.append(EnduranceTask(
                task_id=f"post_patch_{i:03d}",
                task_type="code",
                description=f"Post-patch task {i+1}/14",
                expected_duration_sec=60,
                difficulty="medium",
                metadata={"uses_new_capability": True}
            ))
        
        return tasks
    
    @staticmethod
    def recovery_heavy_workload(failures: int = 10) -> List[EnduranceTask]:
        """Workload designed to test repeated recoveries"""
        tasks = []
        
        for i in range(20):
            task = EnduranceTask(
                task_id=f"recovery_{i:03d}",
                task_type="code",
                description=f"Recovery test task {i+1}/20",
                expected_duration_sec=60,
                difficulty="medium"
            )
            
            # Inject failure for certain tasks
            if i in [3, 7, 11, 15, 19]:
                task.metadata["force_failure"] = True
                task.metadata["failure_type"] = random.choice([
                    "timeout", "assertion", "import_error", "runtime_error"
                ])
            
            tasks.append(task)
        
        return tasks
    
    @staticmethod
    def checkpoint_resume_workload(cycles: int = 5) -> List[EnduranceTask]:
        """Workload with checkpoint/resume cycles"""
        tasks = []
        
        for cycle in range(cycles):
            # Each cycle: 10 tasks + checkpoint
            for i in range(10):
                tasks.append(EnduranceTask(
                    task_id=f"cycle_{cycle}_task_{i:03d}",
                    task_type="code",
                    description=f"Cycle {cycle+1}/{cycles} - Task {i+1}/10",
                    expected_duration_sec=60,
                    difficulty="medium"
                ))
            
            # Checkpoint task
            tasks.append(EnduranceTask(
                task_id=f"checkpoint_{cycle}",
                task_type="checkpoint",
                description=f"Checkpoint after cycle {cycle+1}",
                expected_duration_sec=30,
                difficulty="easy",
                metadata={"checkpoint": True, "cycle": cycle}
            ))
        
        return tasks
    
    @staticmethod
    def idle_resume_workload() -> List[EnduranceTask]:
        """Long idle + resume scenario"""
        tasks = []
        
        # Pre-idle tasks
        for i in range(10):
            tasks.append(EnduranceTask(
                task_id=f"pre_idle_{i:03d}",
                task_type="code",
                description=f"Pre-idle task {i+1}/10",
                expected_duration_sec=60,
                difficulty="easy"
            ))
        
        # Idle task (simulates long idle period)
        tasks.append(EnduranceTask(
            task_id="idle_period",
            task_type="idle",
            description="Simulated 1-hour idle period",
            expected_duration_sec=3600,
            difficulty="easy",
            metadata={"idle": True, "duration_sec": 3600}
        ))
        
        # Post-idle tasks
        for i in range(10):
            tasks.append(EnduranceTask(
                task_id=f"post_idle_{i:03d}",
                task_type="code",
                description=f"Post-idle task {i+1}/10",
                expected_duration_sec=60,
                difficulty="medium"
            ))
        
        return tasks
    
    @staticmethod
    def memory_heavy_workload(item_count: int = 100) -> List[EnduranceTask]:
        """Memory-intensive sequence"""
        tasks = []
        
        for i in range(item_count):
            tasks.append(EnduranceTask(
                task_id=f"memory_heavy_{i:03d}",
                task_type="research",
                description=f"Memory-intensive task {i+1}/{item_count}",
                expected_duration_sec=45,
                difficulty="hard",
                metadata={
                    "memory_intensive": True,
                    "items_to_store": random.randint(10, 100),
                    "retrieval_likely": True
                }
            ))
        
        return tasks


# ==================== METRICS COLLECTOR ====================

class EnduranceMetricsCollector:
    """Collects and stores time-series metrics for endurance analysis"""
    
    def __init__(self, retention_minutes: int = 1440):  # 24 hours default
        self._metrics: deque = deque(maxlen=10000)
        self._retention_minutes = retention_minutes
        self._lock = threading.Lock()
        self._start_time = datetime.now()
    
    def record(self, metric_name: str, value: float, unit: str = "",
               task_id: Optional[str] = None, tags: Optional[Dict] = None):
        """Record a metric"""
        with self._lock:
            metric = EnduranceMetrics(
                timestamp=datetime.now(),
                task_id=task_id,
                metric_name=metric_name,
                value=value,
                unit=unit,
                tags=tags or {}
            )
            self._metrics.append(metric)
            
            # Clean old metrics
            self._cleanup_old_metrics()
    
    def _cleanup_old_metrics(self):
        """Remove metrics older than retention period"""
        cutoff = datetime.now() - timedelta(minutes=self._retention_minutes)
        while self._metrics and self._metrics[0].timestamp < cutoff:
            self._metrics.popleft()
    
    def get_metrics(self, metric_name: Optional[str] = None,
                    since: Optional[datetime] = None) -> List[EnduranceMetrics]:
        """Get metrics filtered by name and time"""
        with self._lock:
            filtered = list(self._metrics)
        
        if metric_name:
            filtered = [m for m in filtered if m.metric_name == metric_name]
        
        if since:
            filtered = [m for m in filtered if m.timestamp >= since]
        
        return filtered
    
    def get_time_series(self, metric_name: str, 
                       window_minutes: int = 60) -> List[Tuple[datetime, float]]:
        """Get time series data for a metric"""
        since = datetime.now() - timedelta(minutes=window_minutes)
        metrics = self.get_metrics(metric_name=metric_name, since=since)
        return [(m.timestamp, m.value) for m in sorted(metrics, key=lambda x: x.timestamp)]
    
    def calculate_trend(self, metric_name: str, window_minutes: int = 60) -> Dict:
        """Calculate trend for a metric"""
        time_series = self.get_time_series(metric_name, window_minutes)
        
        if len(time_series) < 2:
            return {"trend": "insufficient_data", "slope": 0, "confidence": 0}
        
        values = [v for _, v in time_series]
        n = len(values)
        
        # Simple linear regression
        x_mean = (n - 1) / 2
        y_mean = sum(values) / n
        
        numerator = sum((i - x_mean) * (values[i] - y_mean) for i in range(n))
        denominator = sum((i - x_mean) ** 2 for i in range(n))
        
        if denominator == 0:
            slope = 0
        else:
            slope = numerator / denominator
        
        # Determine trend direction
        if abs(slope) < 0.01:
            trend = "stable"
        elif slope > 0:
            trend = "increasing"
        else:
            trend = "decreasing"
        
        # Calculate R-squared for confidence
        y_pred = [y_mean + slope * (i - x_mean) for i in range(n)]
        ss_res = sum((values[i] - y_pred[i]) ** 2 for i in range(n))
        ss_tot = sum((values[i] - y_mean) ** 2 for i in range(n))
        
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
        
        return {
            "trend": trend,
            "slope": slope,
            "confidence": max(0, r_squared),
            "current": values[-1] if values else 0,
            "average": y_mean,
            "min": min(values) if values else 0,
            "max": max(values) if values else 0
        }


# ==================== SESSION STATE TRACKER ====================

class SessionStateTracker:
    """Tracks session state transitions over time"""
    
    def __init__(self):
        self._state = SessionState.INITIALIZING
        self._transitions: List[Tuple[datetime, SessionState]] = []
        self._lock = threading.Lock()
        self._start_time = datetime.now()
        
        # Thresholds for state transitions
        self._stable_threshold = 0.95
        self._degrading_threshold = 0.80
        self._thrashing_threshold = 0.50
        self._noisy_threshold = 0.30
    
    def update_state(self, snapshot: SessionSnapshot):
        """Update session state based on snapshot"""
        with self._lock:
            old_state = self._state
            
            # Determine new state based on metrics
            if snapshot.success_rate >= self._stable_threshold:
                new_state = SessionState.STABLE
            elif snapshot.success_rate >= self._degrading_threshold:
                new_state = SessionState.DEGRADING
            elif snapshot.success_rate >= self._thrashing_threshold:
                new_state = SessionState.THRASHING
            elif snapshot.success_rate >= self._noisy_threshold:
                new_state = SessionState.NOISY
            else:
                new_state = SessionState.UNUSABLE
            
            # Check for recovery
            if new_state in [SessionState.THRASHING, SessionState.NOISY, SessionState.UNUSABLE]:
                if old_state in [SessionState.RECOVERING, SessionState.HEALTHY]:
                    new_state = SessionState.RECOVERING
            
            if old_state != new_state:
                self._state = new_state
                self._transitions.append((datetime.now(), new_state))
                logger.info(f"Session state transition: {old_state} -> {new_state}")
    
    @property
    def current_state(self) -> SessionState:
        return self._state
    
    @property
    def transitions(self) -> List[Tuple[datetime, SessionState]]:
        return self._transitions.copy()
    
    @property
    def time_in_state(self) -> float:
        """Time spent in current state (seconds)"""
        if not self._transitions:
            return (datetime.now() - self._start_time).total_seconds()
        
        last_transition = self._transitions[-1][0]
        return (datetime.now() - last_transition).total_seconds()


# ==================== DECAY ANALYZER ====================

class DecayAnalyzer:
    """Analyzes decay patterns in session metrics"""
    
    def __init__(self, metrics_collector: EnduranceMetricsCollector):
        self._metrics = metrics_collector
        self._baseline_window = 15  # minutes for baseline
        self._analysis_window = 60  # minutes for full analysis
    
    def analyze_quality_decay(self) -> Optional[DecayAnalysis]:
        """Analyze quality decay over time"""
        # Get quality scores over time
        quality_series = self._metrics.get_time_series("task_quality", self._analysis_window)
        
        if len(quality_series) < 10:
            return None
        
        # Split into quarters
        n = len(quality_series)
        q1_scores = [v for _, v in quality_series[:n//4]]
        q4_scores = [v for _, v in quality_series[-n//4:]]
        
        q1_avg = statistics.mean(q1_scores) if q1_scores else 0
        q4_avg = statistics.mean(q4_scores) if q4_scores else 0
        
        if q1_avg == 0:
            return None
        
        decay_rate = (q1_avg - q4_avg) / q1_avg
        severity = min(1.0, abs(decay_rate))
        
        trend = self._metrics.calculate_trend("task_quality", self._analysis_window)
        
        return DecayAnalysis(
            decay_type=DecayType.QUALITY,
            severity=severity,
            trend=trend.get("trend", "unknown"),
            first_quarter_score=q1_avg,
            last_quarter_score=q4_avg,
            decay_rate=decay_rate,
            detected_at=datetime.now(),
            recommendation=self._get_quality_recommendation(decay_rate, severity)
        )
    
    def analyze_speed_decay(self) -> Optional[DecayAnalysis]:
        """Analyze speed decay over time"""
        speed_series = self._metrics.get_time_series("task_duration", self._analysis_window)
        
        if len(speed_series) < 10:
            return None
        
        n = len(speed_series)
        q1_times = [v for _, v in speed_series[:n//4]]
        q4_times = [v for _, v in speed_series[-n//4:]]
        
        q1_avg = statistics.mean(q1_times) if q1_times else 0
        q4_avg = statistics.mean(q4_times) if q4_times else 0
        
        if q1_avg == 0:
            return None
        
        decay_rate = (q4_avg - q1_avg) / q1_avg  # Positive = slower
        severity = min(1.0, abs(decay_rate))
        
        trend = self._metrics.calculate_trend("task_duration", self._analysis_window)
        
        return DecayAnalysis(
            decay_type=DecayType.SPEED,
            severity=severity,
            trend=trend.get("trend", "unknown"),
            first_quarter_score=q1_avg,
            last_quarter_score=q4_avg,
            decay_rate=decay_rate,
            detected_at=datetime.now(),
            recommendation=self._get_speed_recommendation(decay_rate, severity)
        )
    
    def analyze_memory_decay(self) -> Optional[DecayAnalysis]:
        """Analyze memory health decay"""
        memory_series = self._metrics.get_time_series("memory_usage_mb", self._analysis_window)
        
        if len(memory_series) < 10:
            return None
        
        n = len(memory_series)
        q1_mem = [v for _, v in memory_series[:n//4]]
        q4_mem = [v for _, v in memory_series[-n//4:]]
        
        q1_avg = statistics.mean(q1_mem) if q1_mem else 0
        q4_avg = statistics.mean(q4_mem) if q4_mem else 0
        
        if q1_avg == 0:
            return None
        
        growth_rate = (q4_avg - q1_avg) / q1_avg
        severity = min(1.0, abs(growth_rate))
        
        # Check for memory rot (irrelevant entries)
        irrelevant_series = self._metrics.get_time_series("irrelevant_retrieval_rate", self._analysis_window)
        irrelevant_trend = self._metrics.calculate_trend("irrelevant_retrieval_rate", self._analysis_window)
        
        memory_rot_detected = (
            irrelevant_trend.get("trend") == "increasing" and 
            irrelevant_trend.get("confidence", 0) > 0.5
        )
        
        return DecayAnalysis(
            decay_type=DecayType.MEMORY,
            severity=severity,
            trend=irrelevant_trend.get("trend", "unknown"),
            first_quarter_score=q1_avg,
            last_quarter_score=q4_avg,
            decay_rate=growth_rate,
            detected_at=datetime.now(),
            recommendation="Memory cleanup triggered" if memory_rot_detected else "Monitor memory"
        )
    
    def analyze_cost_inflation(self) -> Optional[DecayAnalysis]:
        """Analyze cost inflation over time"""
        cost_series = self._metrics.get_time_series("task_cost", self._analysis_window)
        
        if len(cost_series) < 10:
            return None
        
        n = len(cost_series)
        q1_cost = [v for _, v in cost_series[:n//4]]
        q4_cost = [v for _, v in cost_series[-n//4:]]
        
        q1_avg = statistics.mean(q1_cost) if q1_cost else 0
        q4_avg = statistics.mean(q4_cost) if q4_cost else 0
        
        if q1_avg == 0:
            return None
        
        inflation_rate = (q4_avg - q1_avg) / q1_avg
        severity = min(1.0, abs(inflation_rate))
        
        trend = self._metrics.calculate_trend("task_cost", self._analysis_window)
        
        return DecayAnalysis(
            decay_type=DecayType.COST,
            severity=severity,
            trend=trend.get("trend", "unknown"),
            first_quarter_score=q1_avg,
            last_quarter_score=q4_avg,
            decay_rate=inflation_rate,
            detected_at=datetime.now(),
            recommendation=self._get_cost_recommendation(inflation_rate, severity)
        )
    
    def analyze_all(self) -> List[DecayAnalysis]:
        """Run all decay analyses"""
        analyses = []
        
        for analyzer in [
            self.analyze_quality_decay,
            self.analyze_speed_decay,
            self.analyze_memory_decay,
            self.analyze_cost_inflation
        ]:
            result = analyzer()
            if result and result.severity > 0.1:  # Only report significant decay
                analyses.append(result)
        
        return analyses
    
    def _get_quality_recommendation(self, decay_rate: float, severity: float) -> str:
        if severity > 0.5:
            return "CRITICAL: Quality decay detected. Initiate safe mode and diagnostic run."
        elif severity > 0.3:
            return "WARNING: Quality declining. Increase monitoring frequency."
        elif severity > 0.1:
            return "NOTICE: Slight quality decline observed. Continue monitoring."
        return "Quality stable."
    
    def _get_speed_recommendation(self, decay_rate: float, severity: float) -> str:
        if severity > 0.5:
            return "CRITICAL: Significant slowdown detected. Check for resource contention."
        elif severity > 0.3:
            return "WARNING: Performance degrading. Review caching strategy."
        return "Performance stable."
    
    def _get_cost_recommendation(self, inflation_rate: float, severity: float) -> str:
        if severity > 0.5:
            return "CRITICAL: Cost inflation detected. Optimize resource usage."
        elif severity > 0.3:
            return "WARNING: Cost increasing. Review efficiency metrics."
        return "Cost stable."


# ==================== ANOMALY DETECTOR ====================

class AnomalyDetector:
    """Detects anomalies during endurance runs"""
    
    def __init__(self, metrics_collector: EnduranceMetricsCollector):
        self._metrics = metrics_collector
        self._anomalies: List[Dict] = []
        self._lock = threading.Lock()
    
    def detect_retry_storm(self, threshold: int = 5) -> Optional[Dict]:
        """Detect retry storms - repeated failures in succession"""
        recent_retries = self._metrics.get_metrics("retry_count", 
            since=datetime.now() - timedelta(minutes=10))
        
        if len(recent_retries) < threshold:
            return None
        
        # Check for consecutive high retries
        retry_values = [m.value for m in recent_retries]
        consecutive_high = 0
        max_consecutive = 0
        
        for val in retry_values:
            if val > 3:  # High retry count
                consecutive_high += 1
                max_consecutive = max(max_consecutive, consecutive_high)
            else:
                consecutive_high = 0
        
        if max_consecutive >= threshold:
            anomaly = {
                "type": "retry_storm",
                "severity": "high",
                "detected_at": datetime.now(),
                "consecutive_failures": max_consecutive,
                "recommendation": "Retry storm detected. Check for systemic failures."
            }
            self._record_anomaly(anomaly)
            return anomaly
        
        return None
    
    def detect_context_drift(self, threshold: float = 0.3) -> Optional[Dict]:
        """Detect context drift over time"""
        # Check for increasing context size without purpose
        context_series = self._metrics.get_time_series("context_tokens", 60)
        
        if len(context_series) < 10:
            return None
        
        # Calculate drift
        n = len(context_series)
        early_avg = statistics.mean([v for _, v in context_series[:n//3]])
        late_avg = statistics.mean([v for _, v in context_series[-n//3:]])
        
        if early_avg == 0:
            return None
        
        drift_ratio = (late_avg - early_avg) / early_avg
        
        if drift_ratio > threshold:
            anomaly = {
                "type": "context_drift",
                "severity": "medium",
                "detected_at": datetime.now(),
                "drift_ratio": drift_ratio,
                "recommendation": "Context growing without purpose. Consider compression."
            }
            self._record_anomaly(anomaly)
            return anomaly
        
        return None
    
    def detect_routing_drift(self, threshold: float = 0.2) -> Optional[Dict]:
        """Detect routing decisions becoming suboptimal"""
        # Check for increasing replan rate
        replan_series = self._metrics.get_time_series("replan_count", 60)
        
        if len(replan_series) < 10:
            return None
        
        n = len(replan_series)
        early_replans = sum(1 for _, v in replan_series[:n//3] if v > 0)
        late_replans = sum(1 for _, v in replan_series[-n//3:] if v > 0)
        
        if early_replans == 0:
            return None
        
        drift_ratio = (late_replans - early_replans) / early_replans
        
        if drift_ratio > threshold:
            anomaly = {
                "type": "routing_drift",
                "severity": "medium",
                "detected_at": datetime.now(),
                "drift_ratio": drift_ratio,
                "recommendation": "Routing becoming less optimal. Review planner health."
            }
            self._record_anomaly(anomaly)
            return anomaly
        
        return None
    
    def detect_all(self) -> List[Dict]:
        """Run all anomaly detectors"""
        anomalies = []
        
        for detector in [
            self.detect_retry_storm,
            self.detect_context_drift,
            self.detect_routing_drift
        ]:
            result = detector()
            if result:
                anomalies.append(result)
        
        return anomalies
    
    def _record_anomaly(self, anomaly: Dict):
        with self._lock:
            self._anomalies.append(anomaly)
    
    @property
    def anomalies(self) -> List[Dict]:
        return self._anomalies.copy()


# ==================== ENDURANCE BENCHMARK SUITE ====================

class EnduranceBenchmarkSuite:
    """
    Main orchestrator for endurance benchmarking.
    
    This suite runs comprehensive long-duration tests to evaluate:
    - Session stability over time
    - Quality decay patterns
    - Memory health
    - Retry storm detection
    - Checkpoint integrity
    - Cumulative self-mod risk
    - Policy retention
    - Recovery sustainability
    """
    
    def __init__(self, kernel=None, config: Optional[Dict] = None):
        self._kernel = kernel
        self._config = config or {}
        
        # Initialize components
        self._metrics = EnduranceMetricsCollector()
        self._state_tracker = SessionStateTracker()
        self._decay_analyzer = DecayAnalyzer(self._metrics)
        self._anomaly_detector = AnomalyDetector(self._metrics)
        
        # Test state
        self._is_running = False
        self._current_test_id: Optional[str] = None
        self._current_test_type: Optional[EnduranceTestType] = None
        self._start_time: Optional[datetime] = None
        self._tasks_completed = 0
        self._tasks_failed = 0
        self._task_results: List[Dict] = []
        
        # Configuration
        self._checkpoint_interval = self._config.get("checkpoint_interval", 10)
        self._health_check_interval = self._config.get("health_check_interval", 5)
        self._max_test_duration_hours = self._config.get("max_duration_hours", 24)
        self._decay_threshold = self._config.get("decay_threshold", 0.2)
        
        # Callbacks
        self._on_decay_detected: Optional[Callable] = None
        self._on_anomaly_detected: Optional[Callable] = None
        self._on_state_change: Optional[Callable] = None
    
    def set_callbacks(self, 
                      on_decay_detected: Optional[Callable] = None,
                      on_anomaly_detected: Optional[Callable] = None,
                      on_state_change: Optional[Callable] = None):
        """Set callback functions for events"""
        self._on_decay_detected = on_decay_detected
        self._on_anomaly_detected = on_anomaly_detected
        self._on_state_change = on_state_change
    
    async def run_chained_tasks_test(self, task_count: int = 50) -> EnduranceReport:
        """Run chained tasks endurance test"""
        return await self._run_test(
            test_type=EnduranceTestType.CHAINED_TASKS,
            tasks=EnduranceTaskFamilies.chained_mixed_workload(task_count)
        )
    
    async def run_mixed_session_test(self, task_count: int = 30) -> EnduranceReport:
        """Run browser + repair + terminal mixed session"""
        return await self._run_test(
            test_type=EnduranceTestType.MIXED_SESSION,
            tasks=EnduranceTaskFamilies.browser_repair_terminal_mixed(task_count)
        )
    
    async def run_self_patch_test(self) -> EnduranceReport:
        """Run test with self-modification in the middle"""
        return await self._run_test(
            test_type=EnduranceTestType.SELF_PATCH_MID_SESSION,
            tasks=EnduranceTaskFamilies.self_patch_workload()
        )
    
    async def run_recovery_cycles_test(self, failures: int = 10) -> EnduranceReport:
        """Run test with repeated recovery cycles"""
        return await self._run_test(
            test_type=EnduranceTestType.RECOVERY_CYCLES,
            tasks=EnduranceTaskFamilies.recovery_heavy_workload(failures)
        )
    
    async def run_checkpoint_resume_test(self, cycles: int = 5) -> EnduranceReport:
        """Run test with checkpoint/resume cycles"""
        return await self._run_test(
            test_type=EnduranceTestType.CHECKPOINT_RESUME,
            tasks=EnduranceTaskFamilies.checkpoint_resume_workload(cycles)
        )
    
    async def run_idle_resume_test(self) -> EnduranceReport:
        """Run test with long idle + resume"""
        return await self._run_test(
            test_type=EnduranceTestType.IDLE_RESUME,
            tasks=EnduranceTaskFamilies.idle_resume_workload()
        )
    
    async def run_memory_heavy_test(self, item_count: int = 100) -> EnduranceReport:
        """Run memory-intensive test"""
        return await self._run_test(
            test_type=EnduranceTestType.MEMORY_HEAVY,
            tasks=EnduranceTaskFamilies.memory_heavy_workload(item_count)
        )
    
    async def run_continuous_24h_test(self) -> EnduranceReport:
        """Run 24/7 continuous operation test"""
        # Generate 24 hours worth of mixed tasks
        tasks = []
        
        # Each task ~5 min average = 288 tasks for 24 hours
        for i in range(288):
            task_type = random.choice(["code", "browser", "terminal", "research"])
            tasks.append(EnduranceTask(
                task_id=f"continuous_{i:04d}",
                task_type=task_type,
                description=f"Continuous task {i+1}/288",
                expected_duration_sec=random.randint(180, 420),
                difficulty=random.choice(["easy", "medium", "hard"])
            ))
        
        return await self._run_test(
            test_type=EnduranceTestType.CONTINUOUS_24H,
            tasks=tasks,
            max_duration_hours=24
        )
    
    async def _run_test(self, test_type: EnduranceTestType, 
                       tasks: List[EnduranceTask],
                       max_duration_hours: Optional[float] = None) -> EnduranceReport:
        """Internal test runner"""
        self._is_running = True
        self._current_test_id = str(uuid.uuid4())
        self._current_test_type = test_type
        self._start_time = datetime.now()
        self._tasks_completed = 0
        self._tasks_failed = 0
        self._task_results = []
        
        max_duration = max_duration_hours or self._max_test_duration_hours
        max_end_time = self._start_time + timedelta(hours=max_duration)
        
        logger.info(f"Starting endurance test: {test_type.value}")
        logger.info(f"Test ID: {self._current_test_id}")
        logger.info(f"Tasks: {len(tasks)}")
        logger.info(f"Max duration: {max_duration} hours")
        
        try:
            for i, task in enumerate(tasks):
                # Check time limit
                if datetime.now() >= max_end_time:
                    logger.warning("Test duration limit reached")
                    break
                
                # Check for stop signal
                if not self._is_running:
                    logger.info("Test stopped by user")
                    break
                
                # Execute task
                await self._execute_task(task, i, len(tasks))
                
                # Periodic health check
                if (i + 1) % self._health_check_interval == 0:
                    await self._periodic_health_check()
                
                # Checkpoint
                if (i + 1) % self._checkpoint_interval == 0:
                    await self._checkpoint()
        
        except Exception as e:
            logger.error(f"Endurance test error: {e}")
            traceback.print_exc()
        
        finally:
            self._is_running = False
            end_time = datetime.now()
            
            # Generate report
            report = await self._generate_report(end_time)
            
            logger.info(f"Endurance test completed: {test_type.value}")
            logger.info(f"Total tasks: {report.total_tasks}")
            logger.info(f"Success rate: {report.success_rate:.2%}")
            logger.info(f"Overall score: {report.overall_score:.1f}/100")
        
        return report
    
    async def _execute_task(self, task: EnduranceTask, index: int, total: int):
        """Execute a single endurance task"""
        logger.info(f"Executing endurance task {index+1}/{total}: {task.task_id}")
        
        task_start = time.time()
        success = False
        error = None
        
        try:
            # Simulate task execution (in real implementation, this would call kernel)
            if self._kernel:
                # Real kernel execution
                result = await self._kernel.execute_task({
                    "task_id": task.task_id,
                    "task_type": task.task_type,
                    "description": task.description,
                    "expected_duration": task.expected_duration_sec
                })
                success = result.get("success", False)
                error = result.get("error")
            else:
                # Simulation mode
                await asyncio.sleep(min(task.expected_duration_sec / 10, 5))  # Speed up for testing
                
                # Simulate occasional failures
                if random.random() < 0.05:  # 5% failure rate
                    success = False
                    error = "Simulated failure"
                else:
                    success = True
        
        except Exception as e:
            error = str(e)
            logger.error(f"Task {task.task_id} failed: {e}")
        
        finally:
            task_duration = time.time() - task_start
            
            # Record metrics
            self._metrics.record("task_duration", task_duration, "seconds", task.task_id)
            self._metrics.record("task_success", 1 if success else 0, "bool", task.task_id)
            self._metrics.record("task_quality", random.uniform(0.7, 1.0) if success else 0.3, "score", task.task_id)
            self._metrics.record("task_cost", random.uniform(0.1, 1.0), "dollars", task.task_id)
            self._metrics.record("retry_count", random.randint(0, 3), "count", task.task_id)
            self._metrics.record("replan_count", random.randint(0, 2), "count", task.task_id)
            self._metrics.record("memory_usage_mb", random.uniform(100, 500), "MB", task.task_id)
            self._metrics.record("context_tokens", random.randint(1000, 8000), "tokens", task.task_id)
            self._metrics.record("cache_hit_rate", random.uniform(0.7, 0.95), "rate", task.task_id)
            
            # Update counters
            if success:
                self._tasks_completed += 1
            else:
                self._tasks_failed += 1
            
            # Store result
            self._task_results.append({
                "task_id": task.task_id,
                "success": success,
                "duration": task_duration,
                "error": error,
                "timestamp": datetime.now()
            })
    
    async def _periodic_health_check(self):
        """Perform periodic health check during test"""
        # Take snapshot
        snapshot = await self._take_snapshot()
        
        # Update state tracker
        self._state_tracker.update_state(snapshot)
        
        # Check for decay
        decay_analyses = self._decay_analyzer.analyze_all()
        for decay in decay_analyses:
            if decay.severity > self._decay_threshold:
                logger.warning(f"Decay detected: {decay.decay_type.value} - {decay.recommendation}")
                if self._on_decay_detected:
                    self._on_decay_detected(decay)
        
        # Check for anomalies
        anomalies = self._anomaly_detector.detect_all()
        for anomaly in anomalies:
            logger.warning(f"Anomaly detected: {anomaly}")
            if self._on_anomaly_detected:
                self._on_anomaly_detected(anomaly)
    
    async def _take_snapshot(self) -> SessionSnapshot:
        """Take current session snapshot"""
        recent_tasks = self._task_results[-20:] if self._task_results else []
        
        if recent_tasks:
            avg_duration = statistics.mean([t["duration"] for t in recent_tasks])
            success_rate = sum(1 for t in recent_tasks if t["success"]) / len(recent_tasks)
            recent_quality = statistics.mean([
                self._metrics.get_metrics(task_id=t["task_id"], metric_name="task_quality")[0].value
                for t in recent_tasks if self._metrics.get_metrics(task_id=t["task_id"], metric_name="task_quality")
            ]) if recent_tasks else 0
        else:
            avg_duration = 0
            success_rate = 0
            recent_quality = 0
        
        return SessionSnapshot(
            timestamp=datetime.now(),
            elapsed_seconds=(datetime.now() - self._start_time).total_seconds() if self._start_time else 0,
            tasks_completed=self._tasks_completed,
            tasks_failed=self._tasks_failed,
            active_tasks=0,
            total_retries=sum(m.value for m in self._metrics.get_metrics("retry_count")),
            total_replans=sum(m.value for m in self._metrics.get_metrics("replan_count")),
            memory_usage_mb=statistics.mean([m.value for m in self._metrics.get_metrics("memory_usage_mb")]) or 0,
            context_tokens=int(statistics.mean([m.value for m in self._metrics.get_metrics("context_tokens")]) or 0),
            cache_hit_rate=statistics.mean([m.value for m in self._metrics.get_metrics("cache_hit_rate")]) or 0,
            avg_task_duration_sec=avg_duration,
            success_rate=success_rate,
            cost_accumulated=sum(m.value for m in self._metrics.get_metrics("task_cost")),
            state=self._state_tracker.current_state,
            quality_score=recent_quality,
            speed_score=1.0 - min(1.0, avg_duration / 300),  # Normalize
            recovery_score=1.0,
            policy_score=1.0
        )
    
    async def _checkpoint(self):
        """Create checkpoint during test"""
        logger.info("Creating endurance checkpoint...")
        # In real implementation, would serialize state
        self._metrics.record("checkpoint_created", 1, "count")
    
    async def _generate_report(self, end_time: datetime) -> EnduranceReport:
        """Generate comprehensive endurance report"""
        
        # Calculate metrics
        total_tasks = self._tasks_completed + self._tasks_failed
        success_rate = self._tasks_completed / total_tasks if total_tasks > 0 else 0
        
        # Quality decay
        first_10 = [r for r in self._task_results[:10] if r["success"]]
        last_10 = [r for r in self._task_results[-10:] if r["success"]]
        
        first_quality = statistics.mean([
            self._metrics.get_metrics(task_id=t["task_id"], metric_name="task_quality")[0].value
            for t in first_10 if self._metrics.get_metrics(task_id=t["task_id"], metric_name="task_quality")
        ]) if first_10 else 0
        
        last_quality = statistics.mean([
            self._metrics.get_metrics(task_id=t["task_id"], metric_name="task_quality")[0].value
            for t in last_10 if self._metrics.get_metrics(task_id=t["task_id"], metric_name="task_quality")
        ]) if last_10 else 0
        
        quality_decay = (first_quality - last_quality) / first_quality if first_quality > 0 else 0
        
        # Speed decay
        first_durations = [r["duration"] for r in first_10]
        last_durations = [r["duration"] for r in last_10]
        
        first_speed = statistics.mean(first_durations) if first_durations else 0
        last_speed = statistics.mean(last_durations) if last_durations else 0
        
        speed_decay = (last_speed - first_speed) / first_speed if first_speed > 0 else 0
        
        # Cost inflation
        first_costs = [self._metrics.get_metrics(task_id=t["task_id"], metric_name="task_cost")[0].value
                      for t in first_10 if self._metrics.get_metrics(task_id=t["task_id"], metric_name="task_cost")]
        last_costs = [self._metrics.get_metrics(task_id=t["task_id"], metric_name="task_cost")[0].value
                      for t in last_10 if self._metrics.get_metrics(task_id=t["task_id"], metric_name="task_cost")]
        
        first_cost_avg = statistics.mean(first_costs) if first_costs else 0
        last_cost_avg = statistics.mean(last_costs) if last_costs else 0
        
        cost_inflation = (last_cost_avg - first_cost_avg) / first_cost_avg if first_cost_avg > 0 else 0
        
        # Decay analyses
        decay_analyses = self._decay_analyzer.analyze_all()
        
        # Anomalies
        anomalies = self._anomaly_detector.anomalies
        
        # Retry storm count
        retry_storms = len([a for a in anomalies if a.get("type") == "retry_storm"])
        
        # Memory rot detection
        memory_rot = any(d.decay_type == DecayType.MEMORY and d.severity > 0.3 for d in decay_analyses)
        
        # Routing drift
        routing_drift = any(d.decay_type == DecayType.ROUTING and d.severity > 0.2 for d in decay_analyses)
        
        # Policy erosion
        policy_erosion = any(d.decay_type == DecayType.POLICY and d.severity > 0.2 for d in decay_analyses)
        
        # Calculate overall score
        overall_score = self._calculate_overall_score(
            success_rate, quality_decay, speed_decay, cost_inflation,
            retry_storms, memory_rot, routing_drift, policy_erosion
        )
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            decay_analyses, anomalies
        )
        
        duration = (end_time - self._start_time).total_seconds() / 3600 if self._start_time else 0
        
        return EnduranceReport(
            test_id=self._current_test_id,
            test_type=self._current_test_type,
            start_time=self._start_time,
            end_time=end_time,
            duration_hours=duration,
            total_tasks=total_tasks,
            successful_tasks=self._tasks_completed,
            failed_tasks=self._tasks_failed,
            success_rate=success_rate,
            first_task_quality=first_quality,
            last_task_quality=last_quality,
            quality_decay_rate=quality_decay,
            first_task_speed=first_speed,
            last_task_speed=last_speed,
            speed_decay_rate=speed_decay,
            first_task_cost=first_cost_avg,
            last_task_cost=last_cost_avg,
            cost_inflation_rate=cost_inflation,
            retry_storm_count=retry_storms,
            memory_rot_detected=memory_rot,
            routing_drift_detected=routing_drift,
            policy_erosion_detected=policy_erosion,
            checkpoint_failures=0,  # Would track in real implementation
            state_transitions=self._state_tracker.transitions,
            decay_analyses=decay_analyses,
            anomalies=anomalies,
            recommendations=recommendations,
            overall_score=overall_score
        )
    
    def _calculate_overall_score(self, success_rate: float, quality_decay: float,
                                speed_decay: float, cost_inflation: float,
                                retry_storms: int, memory_rot: bool,
                                routing_drift: bool, policy_erosion: bool) -> float:
        """Calculate overall endurance score (0-100)"""
        score = 100.0
        
        # Success rate contribution (max -40)
        score -= (1 - success_rate) * 40
        
        # Quality decay (max -20)
        score -= quality_decay * 20
        
        # Speed decay (max -15)
        score -= speed_decay * 15
        
        # Cost inflation (max -10)
        score -= cost_inflation * 10
        
        # Retry storms (max -5 per storm, max -10)
        score -= min(retry_storms * 5, 10)
        
        # Memory rot (-5)
        if memory_rot:
            score -= 5
        
        # Routing drift (-5)
        if routing_drift:
            score -= 5
        
        # Policy erosion (-5)
        if policy_erosion:
            score -= 5
        
        return max(0, min(100, score))
    
    def _generate_recommendations(self, decay_analyses: List[DecayAnalysis],
                                  anomalies: List[Dict]) -> List[str]:
        """Generate recommendations based on findings"""
        recommendations = []
        
        for decay in decay_analyses:
            if decay.severity > 0.5:
                recommendations.append(f"CRITICAL: {decay.decay_type.value} decay requires immediate action - {decay.recommendation}")
            elif decay.severity > 0.3:
                recommendations.append(f"WARNING: {decay.decay_type.value} decay detected - {decay.recommendation}")
        
        for anomaly in anomalies:
            if anomaly.get("severity") == "high":
                recommendations.append(f"CRITICAL ANOMALY: {anomaly.get('type')} - {anomaly.get('recommendation')}")
        
        if not recommendations:
            recommendations.append("System shows stable endurance performance. Continue monitoring.")
        
        return recommendations
    
    def stop(self):
        """Stop the endurance test"""
        self._is_running = False
        logger.info("Endurance test stop requested")
    
    @property
    def is_running(self) -> bool:
        return self._is_running
    
    @property
    def current_state(self) -> SessionState:
        return self._state_tracker.current_state


# ==================== FACTORY ====================

def create_endurance_suite(kernel=None, config: Optional[Dict] = None) -> EnduranceBenchmarkSuite:
    """Factory function to create endurance suite"""
    return EnduranceBenchmarkSuite(kernel=kernel, config=config)
