"""
Retry Storm Detector - Detection of Repeated Failure Patterns
============================================================

This module detects retry storms and repeated failure patterns:
- Same command repeated failures
- Same browser action failures
- Same search pattern failures  
- Bad recovery loop detection
- Escalating retry density
- No-progress loops

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
import hashlib
import json

logger = logging.getLogger(__name__)


# ==================== ENUMS ====================

class RetryPatternType(str, Enum):
    """Types of retry patterns"""
    SAME_COMMAND = "same_command"
    SAME_BROWSER_ACTION = "same_browser_action"
    SAME_SEARCH = "same_search"
    BAD_RECOVERY_LOOP = "bad_recovery_loop"
    ESCALATING_DENSITY = "escalating_density"
    NO_PROGRESS = "no_progress"


class StormSeverity(str, Enum):
    """Severity of retry storm"""
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# ==================== DATA CLASSES ====================

@dataclass
class RetryEvent:
    """A single retry event"""
    event_id: str
    timestamp: datetime
    task_id: str
    attempt_number: int
    action_type: str
    action_signature: str  # Hash of the action
    error_type: str
    error_message: str
    recovery_strategy: Optional[str]
    success: bool


@dataclass
class RetryPattern:
    """Detected retry pattern"""
    pattern_type: RetryPatternType
    severity: StormSeverity
    first_seen: datetime
    last_seen: datetime
    occurrence_count: int
    affected_tasks: Set[str]
    unique_actions: Set[str]
    description: str
    recommendation: str


@dataclass
class StormReport:
    """Comprehensive retry storm report"""
    timestamp: datetime
    is_storm_active: bool
    current_severity: StormSeverity
    
    # Statistics
    total_retries: int
    total_failures: int
    retry_rate: float              # Retries per minute
    failure_rate: float            # Failures per minute
    
    # Patterns detected
    active_patterns: List[RetryPattern]
    
    # Recommendations
    recommendations: List[str]
    
    # Overall risk score (0-100)
    risk_score: float


# ==================== PATTERN DETECTOR ====================

class RetryPatternDetector:
    """Detects specific retry patterns"""
    
    def __init__(self, window_minutes: int = 10, min_occurrences: int = 3):
        self._window_minutes = window_minutes
        self._min_occurrences = min_occurrences
        self._lock = threading.Lock()
        
        # Pattern tracking
        self._action_counts: Dict[str, int] = defaultdict(int)
        self._action_timestamps: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        self._task_actions: Dict[str, List[str]] = defaultdict(list)
    
    def record_retry(self, event: RetryEvent):
        """Record a retry event"""
        with self._lock:
            # Track action frequency
            self._action_counts[event.action_signature] += 1
            
            # Track timestamps for rate calculation
            self._action_timestamps[event.action_signature].append(event.timestamp)
            
            # Track task actions for sequence analysis
            self._task_actions[event.task_id].append(event.action_signature)
    
    def detect_same_action_pattern(self, recent_events: List[RetryEvent]) -> Optional[RetryPattern]:
        """Detect repeated same action failures"""
        with self._lock:
            # Group by action signature
            action_tasks: Dict[str, Set[str]] = defaultdict(set)
            
            for event in recent_events:
                action_tasks[event.action_signature].add(event.task_id)
            
            # Find actions repeated across multiple tasks
            for action_sig, tasks in action_tasks.items():
                if len(tasks) >= self._min_occurrences:
                    # Get timestamps
                    timestamps = list(self._action_timestamps[action_sig])
                    
                    return RetryPattern(
                        pattern_type=RetryPatternType.SAME_COMMAND,
                        severity=self._calculate_severity(len(tasks), len(tasks)),
                        first_seen=min(timestamps),
                        last_seen=max(timestamps),
                        occurrence_count=len(timestamps),
                        affected_tasks=tasks,
                        unique_actions={action_sig},
                        description=f"Same action repeated {len(tasks)} times across {len(tasks)} tasks",
                        recommendation="Investigate root cause - same action failing repeatedly"
                    )
        
        return None
    
    def detect_bad_recovery_loop(self, task_actions: List[str]) -> Optional[RetryPattern]:
        """Detect recovery strategies that aren't working"""
        if len(task_actions) < self._min_occurrences * 2:
            return None
        
        # Check for repeating patterns of actions
        for pattern_length in range(2, 5):
            # Check if pattern repeats
            for i in range(len(task_actions) - pattern_length * 2):
                pattern = task_actions[i:i+pattern_length]
                next_segment = task_actions[i+pattern_length:i+pattern_length*2]
                
                if pattern == next_segment and len(set(pattern)) > 1:
                    # Found a repeating recovery pattern
                    return RetryPattern(
                        pattern_type=RetryPatternType.BAD_RECOVERY_LOOP,
                        severity=StormSeverity.HIGH,
                        first_seen=datetime.now() - timedelta(minutes=self._window_minutes),
                        last_seen=datetime.now(),
                        occurrence_count=len(task_actions) // pattern_length,
                        affected_tasks=set(),
                        unique_actions=set(pattern),
                        description=f"Recovery loop detected: {pattern} repeated",
                        recommendation="Review recovery strategy - not making progress"
                    )
        
        return None
    
    def _calculate_severity(self, occurrence_count: int, task_count: int) -> StormSeverity:
        """Calculate severity based on occurrence"""
        if occurrence_count >= 10 or task_count >= 5:
            return StormSeverity.CRITICAL
        elif occurrence_count >= 7 or task_count >= 4:
            return StormSeverity.HIGH
        elif occurrence_count >= 5 or task_count >= 3:
            return StormSeverity.MEDIUM
        elif occurrence_count >= 3:
            return StormSeverity.LOW
        return StormSeverity.NONE


# ==================== STORM ANALYZER ====================

class RetryStormAnalyzer:
    """Analyzes retry patterns to detect storms"""
    
    def __init__(self):
        self._lock = threading.Lock()
        self._events: deque = deque(maxlen=5000)
        self._window_minutes = 10
        self._min_events_for_analysis = 10
    
    def record_event(self, task_id: str, attempt_number: int, action_type: str,
                    action_content: str, error_type: str, error_message: str,
                    recovery_strategy: Optional[str] = None, success: bool = False):
        """Record a retry event"""
        # Create action signature
        action_sig = hashlib.sha256(
            f"{action_type}:{action_content}".encode()
        ).hexdigest()[:16]
        
        event = RetryEvent(
            event_id=str(uuid.uuid4()),
            timestamp=datetime.now(),
            task_id=task_id,
            attempt_number=attempt_number,
            action_type=action_type,
            action_signature=action_sig,
            error_type=error_type,
            error_message=error_message,
            recovery_strategy=recovery_strategy,
            success=success
        )
        
        with self._lock:
            self._events.append(event)
    
    def analyze(self) -> StormReport:
        """Analyze current retry patterns"""
        with self._lock:
            # Get recent events
            cutoff = datetime.now() - timedelta(minutes=self._window_minutes)
            recent = [e for e in self._events if e.timestamp > cutoff]
        
        if len(recent) < self._min_events_for_analysis:
            return StormReport(
                timestamp=datetime.now(),
                is_storm_active=False,
                current_severity=StormSeverity.NONE,
                total_retries=len(recent),
                total_failures=0,
                retry_rate=0,
                failure_rate=0,
                active_patterns=[],
                recommendations=["Insufficient data for analysis"],
                risk_score=0
            )
        
        # Calculate rates
        duration = self._window_minutes * 60  # seconds
        elapsed = (datetime.now() - recent[0].timestamp).total_seconds()
        
        if elapsed > 0:
            retry_rate = len(recent) / (elapsed / 60)  # per minute
        else:
            retry_rate = 0
        
        failures = [e for e in recent if not e.success]
        failure_rate = len(failures) / (elapsed / 60) if elapsed > 0 else 0
        
        # Detect patterns
        patterns = self._detect_patterns(recent)
        
        # Calculate severity
        severity = self._calculate_severity(len(recent), len(failures), patterns)
        
        # Calculate risk score
        risk_score = self._calculate_risk_score(
            len(recent), len(failures), retry_rate, severity
        )
        
        # Generate recommendations
        recommendations = self._generate_recommendations(patterns, severity)
        
        return StormReport(
            timestamp=datetime.now(),
            is_storm_active=severity != StormSeverity.NONE,
            current_severity=severity,
            total_retries=len(recent),
            total_failures=len(failures),
            retry_rate=retry_rate,
            failure_rate=failure_rate,
            active_patterns=patterns,
            recommendations=recommendations,
            risk_score=risk_score
        )
    
    def _detect_patterns(self, events: List[RetryEvent]) -> List[RetryPattern]:
        """Detect all retry patterns"""
        patterns = []
        
        # Same action pattern
        action_counts: Dict[str, int] = defaultdict(int)
        action_tasks: Dict[str, Set[str]] = defaultdict(set)
        
        for event in events:
            action_counts[event.action_signature] += 1
            action_tasks[event.action_signature].add(event.task_id)
        
        for action_sig, count in action_counts.items():
            if count >= 3:
                patterns.append(RetryPattern(
                    pattern_type=RetryPatternType.SAME_COMMAND,
                    severity=self._map_count_to_severity(count),
                    first_seen=events[0].timestamp,
                    last_seen=events[-1].timestamp,
                    occurrence_count=count,
                    affected_tasks=action_tasks[action_sig],
                    unique_actions={action_sig},
                    description=f"Action {action_sig} repeated {count} times",
                    recommendation="Investigate this specific action failure"
                ))
        
        # Escalating density pattern
        if len(events) >= 10:
            first_half = events[:len(events)//2]
            second_half = events[len(events)//2:]
            
            if len(second_half) > len(first_half) * 1.5:
                patterns.append(RetryPattern(
                    pattern_type=RetryPatternType.ESCALATING_DENSITY,
                    severity=StormSeverity.HIGH,
                    first_seen=events[0].timestamp,
                    last_seen=events[-1].timestamp,
                    occurrence_count=len(events),
                    affected_tasks=set(e.task_id for e in events),
                    unique_actions=set(),
                    description="Retry density is increasing over time",
                    recommendation="System may be entering cascading failure"
                ))
        
        # No progress pattern
        task_progress: Dict[str, List[RetryEvent]] = defaultdict(list)
        for event in events:
            task_progress[event.task_id].append(event)
        
        for task_id, task_events in task_progress.items():
            if len(task_events) >= 5:
                successes = sum(1 for e in task_events if e.success)
                if successes == 0:
                    patterns.append(RetryPattern(
                        pattern_type=RetryPatternType.NO_PROGRESS,
                        severity=StormSeverity.CRITICAL,
                        first_seen=task_events[0].timestamp,
                        last_seen=task_events[-1].timestamp,
                        occurrence_count=len(task_events),
                        affected_tasks={task_id},
                        unique_actions=set(e.action_signature for e in task_events),
                        description=f"Task {task_id} has no successful retries",
                        recommendation="Abort task or try completely different approach"
                    ))
        
        return patterns
    
    def _map_count_to_severity(self, count: int) -> StormSeverity:
        """Map occurrence count to severity"""
        if count >= 10:
            return StormSeverity.CRITICAL
        elif count >= 7:
            return StormSeverity.HIGH
        elif count >= 5:
            return StormSeverity.MEDIUM
        elif count >= 3:
            return StormSeverity.LOW
        return StormSeverity.NONE
    
    def _calculate_severity(self, total: int, failures: int, 
                          patterns: List[RetryPattern]) -> StormSeverity:
        """Calculate overall severity"""
        # Check for critical patterns
        if any(p.severity == StormSeverity.CRITICAL for p in patterns):
            return StormSeverity.CRITICAL
        
        if any(p.severity == StormSeverity.HIGH for p in patterns):
            return StormSeverity.HIGH
        
        # Check failure rate
        failure_ratio = failures / total if total > 0 else 0
        
        if failure_ratio > 0.8 and total >= 10:
            return StormSeverity.HIGH
        elif failure_ratio > 0.5 and total >= 7:
            return StormSeverity.MEDIUM
        elif total >= 5:
            return StormSeverity.LOW
        
        return StormSeverity.NONE
    
    def _calculate_risk_score(self, total: int, failures: int,
                            rate: float, severity: StormSeverity) -> float:
        """Calculate risk score (0-100)"""
        score = 0.0
        
        # Base on count
        score += min(30, total * 2)
        
        # Failure ratio
        if total > 0:
            score += (failures / total) * 30
        
        # Rate contribution
        score += min(20, rate * 5)
        
        # Severity contribution
        severity_scores = {
            StormSeverity.CRITICAL: 20,
            StormSeverity.HIGH: 15,
            StormSeverity.MEDIUM: 10,
            StormSeverity.LOW: 5,
            StormSeverity.NONE: 0
        }
        score += severity_scores.get(severity, 0)
        
        return min(100, score)
    
    def _generate_recommendations(self, patterns: List[RetryPattern],
                                 severity: StormSeverity) -> List[str]:
        """Generate recommendations based on patterns"""
        recommendations = []
        
        if severity == StormSeverity.CRITICAL:
            recommendations.append("CRITICAL: Stop current operations and investigate")
            recommendations.append("Consider activating circuit breaker")
        
        for pattern in patterns:
            if pattern.pattern_type == RetryPatternType.SAME_COMMAND:
                recommendations.append(f"Action {pattern.unique_actions} failing repeatedly - check for systemic issue")
            elif pattern.pattern_type == RetryPatternType.BAD_RECOVERY_LOOP:
                recommendations.append("Recovery loop detected - change strategy entirely")
            elif pattern.pattern_type == RetryPatternType.ESCALATING_DENSITY:
                recommendations.append("Retry rate increasing - possible cascading failure")
            elif pattern.pattern_type == RetryPatternType.NO_PROGRESS:
                recommendations.append("Tasks not making progress - consider aborting")
        
        if not recommendations:
            recommendations.append("Retry patterns appear normal")
        
        return recommendations


# ==================== RETRY STORM DETECTOR ====================

class RetryStormDetector:
    """
    Main retry storm detection system.
    
    Features:
    - Real-time retry event tracking
    - Pattern detection across multiple dimensions
    - Severity assessment
    - Risk scoring
    - Automatic mitigation triggers
    - Historical analysis
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self._config = config or {}
        
        # Components
        self._analyzer = RetryStormAnalyzer()
        self._pattern_detector = RetryPatternDetector()
        
        # State
        self._is_monitoring = False
        self._storm_history: deque = deque(maxlen=100)
        self._mitigation_triggered = False
        
        # Configuration
        self._check_interval = self._config.get("check_interval", 30)  # seconds
        self._critical_threshold = self._config.get("critical_threshold", 70)
        
        # Callbacks
        self._on_storm_detected: Optional[Callable] = None
        self._on_mitigation_needed: Optional[Callable] = None
        self._on_pattern_detected: Optional[Callable] = None
    
    def set_callbacks(self,
                     on_storm_detected: Optional[Callable] = None,
                     on_mitigation_needed: Optional[Callable] = None,
                     on_pattern_detected: Optional[Callable] = None):
        """Set callback functions"""
        self._on_storm_detected = on_storm_detected
        self._on_mitigation_needed = on_mitigation_needed
        self._on_pattern_detected = on_pattern_detected
    
    def record_retry(self, task_id: str, attempt_number: int, action_type: str,
                    action_content: str, error_type: str, error_message: str,
                    recovery_strategy: Optional[str] = None, success: bool = False):
        """Record a retry event"""
        self._analyzer.record_event(
            task_id=task_id,
            attempt_number=attempt_number,
            action_type=action_type,
            action_content=action_content,
            error_type=error_type,
            error_message=error_message,
            recovery_strategy=recovery_strategy,
            success=success
        )
        
        # Create event for pattern detector
        event = RetryEvent(
            event_id=str(uuid.uuid4()),
            timestamp=datetime.now(),
            task_id=task_id,
            attempt_number=attempt_number,
            action_type=action_type,
            action_signature=hashlib.sha256(
                f"{action_type}:{action_content}".encode()
            ).hexdigest()[:16],
            error_type=error_type,
            error_message=error_message,
            recovery_strategy=recovery_strategy,
            success=success
        )
        self._pattern_detector.record_retry(event)
    
    def check_for_storm(self) -> StormReport:
        """Check for active retry storm"""
        report = self._analyzer.analyze()
        
        # Store in history
        self._storm_history.append(report)
        
        # Check for mitigation trigger
        if report.risk_score >= self._critical_threshold and not self._mitigation_triggered:
            self._mitigation_triggered = True
            if self._on_mitigation_needed:
                self._on_mitigation_needed(report)
        
        # Reset mitigation if recovered
        if report.risk_score < self._critical_threshold / 2:
            self._mitigation_triggered = False
        
        return report
    
    async def start_monitoring(self):
        """Start continuous storm monitoring"""
        self._is_monitoring = True
        logger.info("Retry storm monitoring started")
        
        while self._is_monitoring:
            await asyncio.sleep(self._check_interval)
            report = self.check_for_storm()
            
            if report.is_storm_active:
                logger.warning(f"Retry storm detected: {report.current_severity.value} - {report.risk_score:.1f}")
                
                if self._on_storm_detected:
                    self._on_storm_detected(report)
    
    def stop_monitoring(self):
        """Stop continuous monitoring"""
        self._is_monitoring = False
        logger.info("Retry storm monitoring stopped")
    
    def get_storm_history(self, last_n: int = 10) -> List[StormReport]:
        """Get recent storm reports"""
        return list(self._storm_history)[-last_n:]
    
    def is_storm_active(self) -> bool:
        """Check if storm is currently active"""
        if not self._storm_history:
            return False
        
        return self._storm_history[-1].is_storm_active
    
    def get_current_severity(self) -> StormSeverity:
        """Get current storm severity"""
        if not self._storm_history:
            return StormSeverity.NONE
        
        return self._storm_history[-1].current_severity
    
    @property
    def is_monitoring(self) -> bool:
        return self._is_monitoring
    
    @property
    def mitigation_triggered(self) -> bool:
        return self._mitigation_triggered
    
    def reset_mitigation(self):
        """Reset mitigation flag"""
        self._mitigation_triggered = False


# ==================== FACTORY ====================

def create_retry_storm_detector(config: Optional[Dict] = None) -> RetryStormDetector:
    """Factory function to create retry storm detector"""
    return RetryStormDetector(config=config)


# Helper to generate unique IDs
import uuid
