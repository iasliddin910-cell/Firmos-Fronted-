"""
Drift Sentinel - Trend Detection and Quality Decay Monitoring
==========================================================

This module monitors quality decay trends over time:
- Quality decay detection
- Rising thrash monitoring
- Memory rot detection
- Routing drift detection
- Policy erosion monitoring
- Recovery fatigue detection

When thresholds are exceeded, it triggers automatic mitigation.

Author: No1 World+ Autonomous System
"""

import asyncio
import time
import logging
import threading
from typing import Dict, List, Optional, Any, Callable, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from collections import defaultdict, deque
from pathlib import Path
import statistics
import json

logger = logging.getLogger(__name__)


# ==================== ENUMS ====================

class DriftType(str, Enum):
    """Types of drift to monitor"""
    QUALITY = "quality"
    SPEED = "speed"
    MEMORY = "memory"
    ROUTING = "routing"
    POLICY = "policy"
    RECOVERY = "recovery"
    COST = "cost"
    THRASH = "thrash"


class DriftSeverity(str, Enum):
    """Severity of drift"""
    NONE = "none"
    MINOR = "minor"
    MODERATE = "moderate"
    SIGNIFICANT = "significant"
    CRITICAL = "critical"


class MitigationAction(str, Enum):
    """Available mitigation actions"""
    AUTO_COOLDOWN = "auto_cooldown"
    CACHE_PURGE = "cache_purge"
    MEMORY_CLEANUP = "memory_cleanup"
    ROUTE_RESET = "route_reset"
    PLANNER_RESET = "planner_reset"
    SAFE_MODE = "safe_mode"
    DIAGNOSTIC_RUN = "diagnostic_run"
    PARALLELISM_REDUCE = "parallelism_reduce"
    RETRY_BUDGET_REDUCE = "retry_budget_reduce"


# ==================== DATA CLASSES ====================

@dataclass
class DriftMetric:
    """A single drift metric measurement"""
    timestamp: datetime
    metric_type: DriftType
    value: float
    baseline: float
    change_percent: float


@dataclass
class DriftSignal:
    """Detected drift signal"""
    drift_type: DriftType
    severity: DriftSeverity
    current_value: float
    baseline_value: float
    change_rate: float          # % change per hour
    detected_at: datetime
    confidence: float           # How confident we are
    trend: str                 # "stable", "degrading", "improving"
    description: str


@dataclass
class MitigationPlan:
    """Planned mitigation actions"""
    actions: List[MitigationAction]
    priority: DriftSeverity
    reason: str
    triggered_by: List[DriftType]
    created_at: datetime
    executed: bool


@dataclass
class SentinelReport:
    """Comprehensive sentinel report"""
    timestamp: datetime
    
    # Overall status
    is_drift_detected: bool
    overall_severity: DriftSeverity
    
    # Individual drift signals
    quality_drift: Optional[DriftSignal]
    speed_drift: Optional[DriftSignal]
    memory_drift: Optional[DriftSignal]
    routing_drift: Optional[DriftSignal]
    policy_drift: Optional[DriftSignal]
    recovery_drift: Optional[DriftSignal]
    cost_drift: Optional[DriftSignal]
    thrash_drift: Optional[DriftSignal]
    
    # Mitigation
    active_mitigations: List[MitigationPlan]
    pending_actions: List[MitigationAction]
    
    # Recommendations
    recommendations: List[str]
    
    # Health score
    health_score: float  # 0-100


# ==================== DRIFT TRACKER ====================

class DriftTracker:
    """Tracks specific drift metrics over time"""
    
    def __init__(self, drift_type: DriftType, window_hours: int = 1,
                 min_samples: int = 10):
        self._type = drift_type
        self._window_hours = window_hours
        self._min_samples = min_samples
        self._lock = threading.Lock()
        self._measurements: deque = deque(maxlen=500)
        self._baseline: Optional[float] = None
    
    def record(self, value: float, baseline: Optional[float] = None):
        """Record a measurement"""
        with self._lock:
            # Set baseline if not set
            if self._baseline is None and baseline is not None:
                self._baseline = baseline
            elif self._baseline is None:
                self._baseline = value
            
            use_baseline = baseline if baseline is not None else self._baseline
            
            measurement = DriftMetric(
                timestamp=datetime.now(),
                metric_type=self._type,
                value=value,
                baseline=use_baseline,
                change_percent=((value - use_baseline) / use_baseline * 100) if use_baseline else 0
            )
            
            self._measurements.append(measurement)
            
            # Clean old measurements
            self._cleanup_old()
    
    def _cleanup_old(self):
        """Remove measurements outside window"""
        cutoff = datetime.now() - timedelta(hours=self._window_hours)
        while self._measurements and self._measurements[0].timestamp < cutoff:
            self._measurements.popleft()
    
    def analyze(self) -> Optional[DriftSignal]:
        """Analyze current drift"""
        with self._lock:
            if len(self._measurements) < self._min_samples:
                return None
            
            measurements = list(self._measurements)
        
        # Calculate statistics
        recent = measurements[-self._min_samples:]
        values = [m.value for m in recent]
        
        current = values[-1]
        baseline = self._baseline or statistics.mean(values[:5])
        
        if baseline == 0:
            return None
        
        # Calculate change rate (per hour)
        time_span = (recent[-1].timestamp - recent[0].timestamp).total_seconds() / 3600
        if time_span > 0:
            change_rate = ((current - baseline) / baseline) / time_span * 100
        else:
            change_rate = 0
        
        # Determine trend
        if len(values) >= 5:
            first_half = values[:len(values)//2]
            second_half = values[len(values)//2:]
            
            first_avg = statistics.mean(first_half)
            second_avg = statistics.mean(second_half)
            
            if abs(second_avg - first_avg) / first_avg < 0.05:
                trend = "stable"
            elif second_avg < first_avg:
                trend = "degrading"
            else:
                trend = "improving"
        else:
            trend = "stable"
        
        # Calculate confidence based on consistency
        try:
            cv = statistics.stdev(values) / statistics.mean(values) if statistics.mean(values) > 0 else 0
            confidence = max(0, 1 - cv)
        except:
            confidence = 0.5
        
        # Determine severity
        change_percent = abs((current - baseline) / baseline * 100)
        severity = self._calculate_severity(change_percent, change_rate)
        
        return DriftSignal(
            drift_type=self._type,
            severity=severity,
            current_value=current,
            baseline_value=baseline,
            change_rate=change_rate,
            detected_at=datetime.now(),
            confidence=confidence,
            trend=trend,
            description=self._generate_description(change_percent, trend)
        )
    
    def _calculate_severity(self, change_percent: float, change_rate: float) -> DriftSeverity:
        """Calculate severity based on change"""
        # For negative changes (degradation)
        if change_percent > 50 or abs(change_rate) > 50:
            return DriftSeverity.CRITICAL
        elif change_percent > 30 or abs(change_rate) > 30:
            return DriftSeverity.SIGNIFICANT
        elif change_percent > 15 or abs(change_rate) > 15:
            return DriftSeverity.MODERATE
        elif change_percent > 5:
            return DriftSeverity.MINOR
        return DriftSeverity.NONE
    
    def _generate_description(self, change_percent: float, trend: str) -> str:
        """Generate human-readable description"""
        direction = "increased" if change_percent > 0 else "decreased"
        
        if self._type == DriftType.QUALITY:
            return f"Quality has {direction} by {abs(change_percent):.1f}% - trend: {trend}"
        elif self._type == DriftType.SPEED:
            return f"Speed has {direction} by {abs(change_percent):.1f}% - trend: {trend}"
        elif self._type == DriftType.MEMORY:
            return f"Memory usage has {direction} by {abs(change_percent):.1f}% - trend: {trend}"
        elif self._type == DriftType.ROUTING:
            return f"Routing efficiency has {direction} by {abs(change_percent):.1f}% - trend: {trend}"
        else:
            return f"{self._type.value} has {direction} by {abs(change_percent):.1f}%"
    
    def reset_baseline(self):
        """Reset the baseline to current values"""
        with self._lock:
            if self._measurements:
                self._baseline = statistics.mean([m.value for m in list(self._measurements)[-10:]])


# ==================== MITIGATION PLANNER ====================

class MitigationPlanner:
    """Plans mitigation actions based on drift signals"""
    
    def __init__(self):
        self._lock = threading.Lock()
        self._active_mitigations: List[MitigationPlan] = []
    
    def plan_mitigation(self, signals: List[DriftSignal]) -> MitigationPlan:
        """Create mitigation plan based on drift signals"""
        with self._lock:
            # Determine overall severity
            severities = [s.severity for s in signals if s.severity != DriftSeverity.NONE]
            
            if not severities:
                return MitigationPlan(
                    actions=[],
                    priority=DriftSeverity.NONE,
                    reason="No drift detected",
                    triggered_by=[],
                    created_at=datetime.now(),
                    executed=False
                )
            
            max_severity = max(severities)
            
            # Determine actions based on severity and drift types
            actions = self._determine_actions(signals, max_severity)
            
            # Create plan
            plan = MitigationPlan(
                actions=actions,
                priority=max_severity,
                reason=self._generate_reason(signals),
                triggered_by=[s.drift_type for s in signals],
                created_at=datetime.now(),
                executed=False
            )
            
            self._active_mitigations.append(plan)
            
            return plan
    
    def _determine_actions(self, signals: List[DriftSignal], 
                         severity: DriftSeverity) -> List[MitigationAction]:
        """Determine which actions to take"""
        actions = []
        
        # Get drift types present
        drift_types = {s.drift_type for s in signals if s.severity != DriftSeverity.NONE}
        
        if severity == DriftSeverity.CRITICAL:
            # Critical - take strongest actions
            actions.extend([
                MitigationAction.SAFE_MODE,
                MitigationAction.DIAGNOSTIC_RUN,
                MitigationAction.AUTO_COOLDOWN
            ])
        elif severity == DriftSeverity.SIGNIFICANT:
            # Significant - substantial mitigation
            if DriftType.QUALITY in drift_types:
                actions.append(MitigationAction.MEMORY_CLEANUP)
            if DriftType.MEMORY in drift_types:
                actions.append(MitigationAction.CACHE_PURGE)
            if DriftType.ROUTING in drift_types:
                actions.append(MitigationAction.ROUTE_RESET)
            if DriftType.RECOVERY in drift_types:
                actions.append(MitigationAction.RETRY_BUDGET_REDUCE)
            actions.append(MitigationAction.AUTO_COOLDOWN)
        elif severity == DriftSeverity.MODERATE:
            # Moderate - targeted actions
            if DriftType.MEMORY in drift_types:
                actions.append(MitigationAction.CACHE_PURGE)
            if DriftType.QUALITY in drift_types:
                actions.append(MitigationAction.MEMORY_CLEANUP)
        else:
            # Minor - just monitor
            actions.append(MitigationAction.AUTO_COOLDOWN)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_actions = []
        for a in actions:
            if a not in seen:
                seen.add(a)
                unique_actions.append(a)
        
        return unique_actions
    
    def _generate_reason(self, signals: List[DriftSignal]) -> str:
        """Generate human-readable reason"""
        if not signals:
            return "No drift detected"
        
        types = [s.drift_type.value for s in signals if s.severity != DriftSeverity.NONE]
        
        if len(types) == 1:
            return f"Detected {types[0]} drift"
        elif len(types) == 2:
            return f"Detected {types[0]} and {types[1]} drift"
        else:
            return f"Detected multiple drift types: {', '.join(types)}"
    
    def mark_executed(self, plan: MitigationPlan):
        """Mark a mitigation plan as executed"""
        with self._lock:
            for m in self._active_mitigations:
                if m.created_at == plan.created_at:
                    m.executed = True
    
    def get_active_mitigations(self) -> List[MitigationPlan]:
        """Get active (non-executed) mitigations"""
        with self._lock:
            return [m for m in self._active_mitigations if not m.executed]


# ==================== DRIFT SENTINEL ====================

class DriftSentinel:
    """
    Main drift monitoring and mitigation system.
    
    Features:
    - Multi-metric drift tracking
    - Real-time trend analysis
    - Severity assessment
    - Automatic mitigation planning
    - Health scoring
    - Callback notifications
    
    This is the "watchdog" that keeps the system healthy
    by detecting degradation early and triggering responses.
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self._config = config or {}
        
        # Trackers for each drift type
        self._trackers: Dict[DriftType, DriftTracker] = {
            DriftType.QUALITY: DriftTracker(DriftType.QUALITY),
            DriftType.SPEED: DriftTracker(DriftType.SPEED),
            DriftType.MEMORY: DriftTracker(DriftType.MEMORY),
            DriftType.ROUTING: DriftTracker(DriftType.ROUTING),
            DriftType.RECOVERY: DriftTracker(DriftType.RECOVERY),
            DriftType.COST: DriftTracker(DriftType.COST),
            DriftType.THRASH: DriftTracker(DriftType.THRASH)
        }
        
        # Mitigation planner
        self._planner = MitigationPlanner()
        
        # State
        self._is_monitoring = False
        self._last_report: Optional[SentinelReport] = None
        self._check_interval = self._config.get("check_interval", 60)  # seconds
        
        # Severity thresholds
        self._critical_threshold = self._config.get("critical_threshold", 50)
        self._warning_threshold = self._config.get("warning_threshold", 30)
        
        # Callbacks
        self._on_drift_detected: Optional[Callable] = None
        self._on_mitigation_needed: Optional[Callable] = None
        self._on_critical: Optional[Callable] = None
    
    def set_callbacks(self,
                     on_drift_detected: Optional[Callable] = None,
                     on_mitigation_needed: Optional[Callable] = None,
                     on_critical: Optional[Callable] = None):
        """Set callback functions"""
        self._on_drift_detected = on_drift_detected
        self._on_mitigation_needed = on_mitigation_needed
        self._on_critical = on_critical
    
    # ==================== METRIC RECORDING ====================
    
    def record_quality(self, quality_score: float, baseline: Optional[float] = None):
        """Record quality metric"""
        self._trackers[DriftType.QUALITY].record(quality_score, baseline)
    
    def record_speed(self, speed_score: float, baseline: Optional[float] = None):
        """Record speed metric"""
        self._trackers[DriftType.SPEED].record(speed_score, baseline)
    
    def record_memory(self, memory_mb: float, baseline: Optional[float] = None):
        """Record memory metric"""
        self._trackers[DriftType.MEMORY].record(memory_mb, baseline)
    
    def record_routing(self, efficiency: float, baseline: Optional[float] = None):
        """Record routing efficiency"""
        self._trackers[DriftType.ROUTING].record(efficiency, baseline)
    
    def record_recovery(self, success_rate: float, baseline: Optional[float] = None):
        """Record recovery success rate"""
        self._trackers[DriftType.RECOVERY].record(success_rate, baseline)
    
    def record_cost(self, cost: float, baseline: Optional[float] = None):
        """Record cost metric"""
        self._trackers[DriftType.COST].record(cost, baseline)
    
    def record_thrash(self, thrash_count: int, baseline: Optional[float] = None):
        """Record thrashing metric"""
        self._trackers[DriftType.THRASH].record(float(thrash_count), baseline)
    
    def record_metric(self, drift_type: DriftType, value: float, 
                     baseline: Optional[float] = None):
        """Generic metric recording"""
        if drift_type in self._trackers:
            self._trackers[drift_type].record(value, baseline)
    
    # ==================== ANALYSIS ====================
    
    def analyze(self) -> SentinelReport:
        """Perform comprehensive drift analysis"""
        signals = []
        
        # Analyze each tracker
        for drift_type, tracker in self._trackers.items():
            signal = tracker.analyze()
            if signal:
                signals.append(signal)
        
        # Determine overall severity
        severities = [s.severity for s in signals]
        overall = DriftSeverity.NONE
        
        if DriftSeverity.CRITICAL in severities:
            overall = DriftSeverity.CRITICAL
        elif DriftSeverity.SIGNIFICANT in severities:
            overall = DriftSeverity.SIGNIFICANT
        elif DriftSeverity.MODERATE in severities:
            overall = DriftSeverity.MODERATE
        elif DriftSeverity.MINOR in severities:
            overall = DriftSeverity.MINOR
        
        # Plan mitigation
        active_mitigations = self._planner.get_active_mitigations()
        
        if signals and overall != DriftSeverity.NONE:
            # Check if we need new mitigation
            if not active_mitigations:
                plan = self._planner.plan_mitigation(signals)
                active_mitigations.append(plan)
                
                # Trigger callbacks
                if self._on_drift_detected:
                    self._on_drift_detected(signals)
                
                if overall == DriftSeverity.CRITICAL and self._on_critical:
                    self._on_critical(signals, plan)
                
                if self._on_mitigation_needed:
                    self._on_mitigation_needed(plan)
        
        # Get pending actions
        pending = []
        for m in active_mitigations:
            pending.extend(m.actions)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(signals, overall)
        
        # Calculate health score
        health_score = self._calculate_health_score(signals, overall)
        
        # Build report
        report = SentinelReport(
            timestamp=datetime.now(),
            is_drift_detected=overall != DriftSeverity.NONE,
            overall_severity=overall,
            quality_drift=self._get_signal(signals, DriftType.QUALITY),
            speed_drift=self._get_signal(signals, DriftType.SPEED),
            memory_drift=self._get_signal(signals, DriftType.MEMORY),
            routing_drift=self._get_signal(signals, DriftType.ROUTING),
            policy_drift=self._get_signal(signals, DriftType.POLICY),
            recovery_drift=self._get_signal(signals, DriftType.RECOVERY),
            cost_drift=self._get_signal(signals, DriftType.COST),
            thrash_drift=self._get_signal(signals, DriftType.THRASH),
            active_mitigations=active_mitigations,
            pending_actions=list(set(pending)),
            recommendations=recommendations,
            health_score=health_score
        )
        
        self._last_report = report
        return report
    
    def _get_signal(self, signals: List[DriftSignal], 
                   drift_type: DriftType) -> Optional[DriftSignal]:
        """Get signal for specific drift type"""
        for s in signals:
            if s.drift_type == drift_type:
                return s
        return None
    
    def _calculate_health_score(self, signals: List[DriftSignal],
                               severity: DriftSeverity) -> float:
        """Calculate overall health score"""
        score = 100.0
        
        # Penalty based on severity
        severity_penalties = {
            DriftSeverity.CRITICAL: 40,
            DriftSeverity.SIGNIFICANT: 25,
            DriftSeverity.MODERATE: 15,
            DriftSeverity.MINOR: 5,
            DriftSeverity.NONE: 0
        }
        
        score -= severity_penalties.get(severity, 0)
        
        # Additional penalties based on signal confidence
        for signal in signals:
            if signal.severity != DriftSeverity.NONE:
                score -= signal.severity.value * signal.confidence * 5
        
        return max(0, min(100, score))
    
    def _generate_recommendations(self, signals: List[DriftSignal],
                                 severity: DriftSeverity) -> List[str]:
        """Generate recommendations"""
        recommendations = []
        
        if severity == DriftSeverity.CRITICAL:
            recommendations.append("CRITICAL: Activate safe mode immediately")
            recommendations.append("Run diagnostic to identify root cause")
            recommendations.append("Reduce parallelism")
        
        for signal in signals:
            if signal.severity == DriftSeverity.CRITICAL:
                recommendations.append(f"URGENT: Address {signal.drift_type.value} drift - {signal.description}")
            elif signal.severity == DriftSeverity.SIGNIFICANT:
                recommendations.append(f"Address {signal.drift_type.value} drift - {signal.description}")
        
        if not recommendations:
            recommendations.append("System health is good")
        
        return recommendations
    
    # ==================== MITIGATION ====================
    
    async def execute_mitigation(self, action: MitigationAction) -> bool:
        """Execute a mitigation action"""
        logger.info(f"Executing mitigation action: {action.value}")
        
        try:
            if action == MitigationAction.AUTO_COOLDOWN:
                await self._auto_cooldown()
            elif action == MitigationAction.CACHE_PURGE:
                await self._cache_purge()
            elif action == MitigationAction.MEMORY_CLEANUP:
                await self._memory_cleanup()
            elif action == MitigationAction.ROUTE_RESET:
                await self._route_reset()
            elif action == MitigationAction.PLANNER_RESET:
                await self._planner_reset()
            elif action == MitigationAction.SAFE_MODE:
                await self._activate_safe_mode()
            elif action == MitigationAction.DIAGNOSTIC_RUN:
                await self._diagnostic_run()
            elif action == MitigationAction.PARALLELISM_REDUCE:
                await self._reduce_parallelism()
            elif action == MitigationAction.RETRY_BUDGET_REDUCE:
                await self._reduce_retry_budget()
            
            return True
        
        except Exception as e:
            logger.error(f"Mitigation action {action.value} failed: {e}")
            return False
    
    async def _auto_cooldown(self):
        """Reduce system load temporarily"""
        logger.info("Performing auto-cooldown...")
        await asyncio.sleep(1)  # Simulate cooldown
    
    async def _cache_purge(self):
        """Purge caches"""
        logger.info("Purging caches...")
        await asyncio.sleep(0.5)
    
    async def _memory_cleanup(self):
        """Clean up memory"""
        logger.info("Performing memory cleanup...")
        await asyncio.sleep(0.5)
    
    async def _route_reset(self):
        """Reset routing"""
        logger.info("Resetting routes...")
        await asyncio.sleep(0.5)
    
    async def _planner_reset(self):
        """Reset planner"""
        logger.info("Resetting planner...")
        await asyncio.sleep(0.5)
    
    async def _activate_safe_mode(self):
        """Activate safe mode"""
        logger.info("Activating safe mode...")
        await asyncio.sleep(0.5)
    
    async def _diagnostic_run(self):
        """Run diagnostics"""
        logger.info("Running diagnostics...")
        await asyncio.sleep(1)
    
    async def _reduce_parallelism(self):
        """Reduce parallelism"""
        logger.info("Reducing parallelism...")
        await asyncio.sleep(0.5)
    
    async def _reduce_retry_budget(self):
        """Reduce retry budget"""
        logger.info("Reducing retry budget...")
        await asyncio.sleep(0.5)
    
    # ==================== MONITORING ====================
    
    async def start_monitoring(self):
        """Start continuous monitoring"""
        self._is_monitoring = True
        logger.info("Drift sentinel monitoring started")
        
        while self._is_monitoring:
            await asyncio.sleep(self._check_interval)
            report = self.analyze()
            
            if report.is_drift_detected:
                logger.warning(f"Drift detected: {report.overall_severity.value} - health: {report.health_score:.1f}")
    
    def stop_monitoring(self):
        """Stop monitoring"""
        self._is_monitoring = False
        logger.info("Drift sentinel monitoring stopped")
    
    def reset(self):
        """Reset all trackers and baselines"""
        for tracker in self._trackers.values():
            tracker.reset_baseline()
        
        logger.info("Drift sentinel reset")
    
    @property
    def is_monitoring(self) -> bool:
        return self._is_monitoring
    
    @property
    def last_report(self) -> Optional[SentinelReport]:
        return self._last_report
    
    @property
    def health_score(self) -> float:
        """Get current health score"""
        if self._last_report:
            return self._last_report.health_score
        return 100.0


# ==================== FACTORY ====================

def create_drift_sentinel(config: Optional[Dict] = None) -> DriftSentinel:
    """Factory function to create drift sentinel"""
    return DriftSentinel(config=config)
