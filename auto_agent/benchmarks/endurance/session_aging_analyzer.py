"""
Session Aging Analyzer - Time-based Quality Decay Analysis
===========================================================

This module analyzes how session quality degrades over time.
It compares early tasks vs late tasks across multiple dimensions:
- Quality decay
- Cost inflation
- Retry increase
- Replan increase
- Retrieval degradation

Author: No1 World+ Autonomous System
"""

import asyncio
import time
import logging
import threading
from typing import Dict, List, Optional, Any, Tuple, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from collections import defaultdict, deque
import statistics
import json

logger = logging.getLogger(__name__)


# ==================== AGING ENUMS ====================

class AgingPhase(str, Enum):
    """Session aging phases"""
    FRESH = "fresh"                 # 0-25% of session
    MATURE = "mature"               # 25-50% of session
    AGING = "aging"                 # 50-75% of session
    OLD = "old"                     # 75-100% of session


class DecayCategory(str, Enum):
    """Categories of decay"""
    QUALITY = "quality"
    SPEED = "speed"
    COST = "cost"
    RETRY = "retry"
    REPLAN = "replan"
    MEMORY = "memory"
    ROUTING = "routing"
    POLICY = "policy"


# ==================== DATA CLASSES ====================

@dataclass
class AgingMetrics:
    """Metrics for a specific aging phase"""
    phase: AgingPhase
    task_count: int
    success_rate: float
    avg_quality: float
    avg_duration: float
    avg_cost: float
    avg_retries: float
    avg_replans: float
    memory_usage: float
    context_tokens: int
    cache_hit_rate: float


@dataclass
class DecayScore:
    """Score for a specific decay category"""
    category: DecayCategory
    early_score: float
    late_score: float
    decay_rate: float          # Percentage change (negative = decay)
    severity: float            # 0-1, how significant
    trend: str                 # "stable", "degrading", "improving"
    confidence: float          # How confident we are in this measurement


@dataclass
class SessionAgingReport:
    """Comprehensive session aging analysis"""
    session_id: str
    start_time: datetime
    end_time: Optional[datetime]
    total_tasks: int
    completed_tasks: int
    failed_tasks: int
    
    # Phase metrics
    fresh_metrics: Optional[AgingMetrics]
    mature_metrics: Optional[AgingMetrics]
    aging_metrics: Optional[AgingMetrics]
    old_metrics: Optional[AgingMetrics]
    
    # Decay scores
    quality_decay: Optional[DecayScore]
    speed_decay: Optional[DecayScore]
    cost_inflation: Optional[DecayScore]
    retry_increase: Optional[DecayScore]
    replan_increase: Optional[DecayScore]
    memory_decay: Optional[DecayScore]
    routing_decay: Optional[DecayScore]
    policy_decay: Optional[DecayScore]
    
    # Overall assessment
    overall_health_score: float    # 0-100
    aging_detected: bool
    critical_issues: List[str]
    recommendations: List[str]


# ==================== METRICS STORAGE ====================

class SessionMetricsStore:
    """Stores session metrics with temporal tracking"""
    
    def __init__(self):
        self._lock = threading.Lock()
        self._tasks: List[Dict] = []
        self._task_counter = 0
    
    def record_task(self, task_id: str, success: bool, quality: float,
                   duration: float, cost: float, retries: int, replans: int,
                   memory_mb: float, context_tokens: int, cache_hit_rate: float,
                   timestamp: Optional[datetime] = None):
        """Record task execution metrics"""
        with self._lock:
            self._task_counter += 1
            self._tasks.append({
                "task_id": task_id,
                "task_number": self._task_counter,
                "success": success,
                "quality": quality,
                "duration": duration,
                "cost": cost,
                "retries": retries,
                "replans": replans,
                "memory_mb": memory_mb,
                "context_tokens": context_tokens,
                "cache_hit_rate": cache_hit_rate,
                "timestamp": timestamp or datetime.now()
            })
    
    def get_tasks(self, phase: Optional[AgingPhase] = None,
                 since: Optional[datetime] = None) -> List[Dict]:
        """Get tasks filtered by phase or time"""
        with self._lock:
            filtered = list(self._tasks)
        
        if since:
            filtered = [t for t in filtered if t["timestamp"] >= since]
        
        if phase:
            filtered = [t for t in filtered if self._get_phase(t["task_number"]) == phase]
        
        return filtered
    
    def get_task_count(self) -> int:
        return len(self._tasks)
    
    def _get_phase(self, task_number: int) -> AgingPhase:
        """Determine phase based on task number"""
        if self._task_counter == 0:
            return AgingPhase.FRESH
        
        progress = task_number / self._task_counter
        
        if progress <= 0.25:
            return AgingPhase.FRESH
        elif progress <= 0.50:
            return AgingPhase.MATURE
        elif progress <= 0.75:
            return AgingPhase.AGING
        else:
            return AgingPhase.OLD
    
    def get_phase_tasks(self) -> Dict[AgingPhase, List[Dict]]:
        """Get all tasks grouped by phase"""
        result = {
            AgingPhase.FRESH: [],
            AgingPhase.MATURE: [],
            AgingPhase.AGING: [],
            AgingPhase.OLD: []
        }
        
        for task in self._tasks:
            phase = self._get_phase(task["task_number"])
            result[phase].append(task)
        
        return result
    
    def clear(self):
        """Clear all stored metrics"""
        with self._lock:
            self._tasks.clear()
            self._task_counter = 0


# ==================== PHASE ANALYZER ====================

class PhaseAnalyzer:
    """Analyzes metrics for specific session phases"""
    
    @staticmethod
    def analyze_phase(tasks: List[Dict]) -> Optional[AgingMetrics]:
        """Analyze metrics for a specific phase"""
        if not tasks:
            return None
        
        successful = [t for t in tasks if t["success"]]
        
        return AgingMetrics(
            phase=AgingPhase.FRESH,  # Will be set by caller
            task_count=len(tasks),
            success_rate=len(successful) / len(tasks) if tasks else 0,
            avg_quality=statistics.mean([t["quality"] for t in successful]) if successful else 0,
            avg_duration=statistics.mean([t["duration"] for t in tasks]),
            avg_cost=statistics.mean([t["cost"] for t in tasks]),
            avg_retries=statistics.mean([t["retries"] for t in tasks]),
            avg_replans=statistics.mean([t["replans"] for t in tasks]),
            memory_usage=statistics.mean([t["memory_mb"] for t in tasks]),
            context_tokens=int(statistics.mean([t["context_tokens"] for t in tasks])),
            cache_hit_rate=statistics.mean([t["cache_hit_rate"] for t in tasks])
        )


# ==================== DECAY CALCULATOR ====================

class DecayCalculator:
    """Calculates decay rates between early and late session"""
    
    def __init__(self, min_tasks_per_phase: int = 5):
        self._min_tasks = min_tasks_per_phase
    
    def calculate_decay(self, early_tasks: List[Dict], late_tasks: List[Dict],
                       category: DecayCategory) -> Optional[DecayScore]:
        """Calculate decay for a category between early and late phases"""
        if len(early_tasks) < self._min_tasks or len(late_tasks) < self._min_tasks:
            return None
        
        # Get the metric key for this category
        metric_key = self._get_metric_key(category)
        if not metric_key:
            return None
        
        early_values = [t[metric_key] for t in early_tasks if metric_key in t]
        late_values = [t[metric_key] for t in late_tasks if metric_key in t]
        
        if not early_values or not late_values:
            return None
        
        early_avg = statistics.mean(early_values)
        late_avg = statistics.mean(late_values)
        
        # Calculate decay rate (percentage change)
        if early_avg == 0:
            return None
        
        decay_rate = (late_avg - early_avg) / early_avg
        
        # Determine severity based on absolute change
        if category in [DecayCategory.QUALITY, DecayCategory.SPEED]:
            # For quality/speed, negative is bad
            severity = abs(decay_rate) if decay_rate < 0 else 0
            trend = "degrading" if decay_rate < -0.1 else "stable"
            if decay_rate > 0.1:
                trend = "improving"
        elif category == DecayCategory.COST:
            # For cost, positive is bad (inflation)
            severity = decay_rate if decay_rate > 0 else 0
            trend = "inflating" if decay_rate > 0.1 else "stable"
        elif category in [DecayCategory.RETRY, DecayCategory.REPLAN]:
            # For retries/replans, positive is bad (more failures)
            severity = decay_rate if decay_rate > 0 else 0
            trend = "increasing" if decay_rate > 0.2 else "stable"
        else:
            severity = abs(decay_rate)
            trend = "degrading" if decay_rate < -0.1 else "stable"
        
        # Calculate confidence based on sample size and variance
        all_values = early_values + late_values
        if len(all_values) >= 10:
            try:
                cv = statistics.stdev(all_values) / statistics.mean(all_values) if statistics.mean(all_values) > 0 else 0
                confidence = min(1.0, len(all_values) / 20) * (1 - min(1.0, cv))
            except statistics.StatisticsError:
                confidence = 0.5
        else:
            confidence = 0.3
        
        return DecayScore(
            category=category,
            early_score=early_avg,
            late_score=late_avg,
            decay_rate=decay_rate,
            severity=min(1.0, severity),
            trend=trend,
            confidence=confidence
        )
    
    def _get_metric_key(self, category: DecayCategory) -> Optional[str]:
        """Get the metric key for a decay category"""
        mapping = {
            DecayCategory.QUALITY: "quality",
            DecayCategory.SPEED: "duration",
            DecayCategory.COST: "cost",
            DecayCategory.RETRY: "retries",
            DecayCategory.REPLAN: "replans",
            DecayCategory.MEMORY: "memory_mb",
            DecayCategory.ROUTING: "replans",
            DecayCategory.POLICY: "quality"  # Policy tracked via quality
        }
        return mapping.get(category)


# ==================== SESSION AGING ANALYZER ====================

class SessionAgingAnalyzer:
    """
    Analyzes session aging effects over time.
    
    This analyzer tracks how the session's performance degrades as more tasks
    are executed, identifying specific decay patterns and providing actionable
    insights for maintaining long-run stability.
    
    Key Features:
    - Phase-based analysis (fresh, mature, aging, old)
    - Cross-phase decay calculation
    - Trend detection with confidence scores
    - Critical issue identification
    - Recommendations for mitigation
    """
    
    def __init__(self, session_id: Optional[str] = None):
        self._session_id = session_id or str(id(self))
        self._store = SessionMetricsStore()
        self._calculator = DecayCalculator()
        self._start_time = datetime.now()
        self._end_time: Optional[datetime] = None
        
        # Configuration
        self._min_tasks_for_analysis = 20
        self._critical_severity_threshold = 0.3
        self._warning_severity_threshold = 0.15
    
    def record_task(self, task_id: str, success: bool, quality: float = 1.0,
                   duration: float = 0, cost: float = 0, retries: int = 0,
                   replans: int = 0, memory_mb: float = 0, context_tokens: int = 0,
                   cache_hit_rate: float = 1.0):
        """Record task execution metrics for aging analysis"""
        self._store.record_task(
            task_id=task_id,
            success=success,
            quality=quality,
            duration=duration,
            cost=cost,
            retries=retries,
            replans=replans,
            memory_mb=memory_mb,
            context_tokens=context_tokens,
            cache_hit_rate=cache_hit_rate
        )
    
    def end_session(self):
        """Mark session as ended"""
        self._end_time = datetime.now()
    
    def analyze(self) -> SessionAgingReport:
        """Perform comprehensive aging analysis"""
        total_tasks = self._store.get_task_count()
        
        # Get phase tasks
        phase_tasks = self._store.get_phase_tasks()
        
        # Analyze each phase
        fresh = PhaseAnalyzer.analyze_phase(phase_tasks[AgingPhase.FRESH])
        mature = PhaseAnalyzer.analyze_phase(phase_tasks[AgingPhase.MATURE])
        aging = PhaseAnalyzer.analyze_phase(phase_tasks[AgingPhase.AGING])
        old = PhaseAnalyzer.analyze_phase(phase_tasks[AgingPhase.OLD])
        
        if fresh:
            fresh.phase = AgingPhase.FRESH
        if mature:
            mature.phase = AgingPhase.MATURE
        if aging:
            aging.phase = AgingPhase.AGING
        if old:
            old.phase = AgingPhase.OLD
        
        # Get early and late tasks for decay calculation
        early_tasks = phase_tasks[AgingPhase.FRESH] + phase_tasks[AgingPhase.MATURE]
        late_tasks = phase_tasks[AgingPhase.AGING] + phase_tasks[AgingPhase.OLD]
        
        # Calculate decay for each category
        quality_decay = self._calculator.calculate_decay(
            early_tasks, late_tasks, DecayCategory.QUALITY)
        speed_decay = self._calculator.calculate_decay(
            early_tasks, late_tasks, DecayCategory.SPEED)
        cost_inflation = self._calculator.calculate_decay(
            early_tasks, late_tasks, DecayCategory.COST)
        retry_increase = self._calculator.calculate_decay(
            early_tasks, late_tasks, DecayCategory.RETRY)
        replan_increase = self._calculator.calculate_decay(
            early_tasks, late_tasks, DecayCategory.REPLAN)
        memory_decay = self._calculator.calculate_decay(
            early_tasks, late_tasks, DecayCategory.MEMORY)
        
        # Calculate overall health score
        health_score = self._calculate_health_score(
            quality_decay, speed_decay, cost_inflation, retry_increase
        )
        
        # Identify critical issues
        critical_issues = self._identify_critical_issues(
            quality_decay, speed_decay, cost_inflation, retry_increase, memory_decay
        )
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            quality_decay, speed_decay, cost_inflation, retry_increase, memory_decay
        )
        
        # Determine if aging is detected
        aging_detected = (
            (quality_decay and quality_decay.severity > self._warning_severity_threshold) or
            (speed_decay and speed_decay.severity > self._warning_severity_threshold) or
            (retry_increase and retry_increase.severity > self._warning_severity_threshold)
        )
        
        # Calculate completion stats
        all_tasks = self._store.get_tasks()
        completed = sum(1 for t in all_tasks if t["success"])
        failed = sum(1 for t in all_tasks if not t["success"])
        
        return SessionAgingReport(
            session_id=self._session_id,
            start_time=self._start_time,
            end_time=self._end_time,
            total_tasks=total_tasks,
            completed_tasks=completed,
            failed_tasks=failed,
            fresh_metrics=fresh,
            mature_metrics=mature,
            aging_metrics=aging,
            old_metrics=old,
            quality_decay=quality_decay,
            speed_decay=speed_decay,
            cost_inflation=cost_inflation,
            retry_increase=retry_increase,
            replan_increase=replan_increase,
            memory_decay=memory_decay,
            routing_decay=replan_increase,  # Alias
            policy_decay=None,  # Would require policy tracking
            overall_health_score=health_score,
            aging_detected=aging_detected,
            critical_issues=critical_issues,
            recommendations=recommendations
        )
    
    def _calculate_health_score(self, quality_decay: Optional[DecayScore],
                                speed_decay: Optional[DecayScore],
                                cost_inflation: Optional[DecayScore],
                                retry_increase: Optional[DecayScore]) -> float:
        """Calculate overall session health score (0-100)"""
        score = 100.0
        
        # Quality decay penalty
        if quality_decay and quality_decay.trend == "degrading":
            score -= quality_decay.severity * 30
        
        # Speed decay penalty
        if speed_decay and speed_decay.trend == "degrading":
            score -= speed_decay.severity * 20
        
        # Cost inflation penalty
        if cost_inflation and cost_inflation.trend == "inflating":
            score -= cost_inflation.severity * 15
        
        # Retry increase penalty
        if retry_increase and retry_increase.trend == "increasing":
            score -= retry_increase.severity * 25
        
        return max(0, min(100, score))
    
    def _identify_critical_issues(self, quality_decay: Optional[DecayScore],
                                  speed_decay: Optional[DecayScore],
                                  cost_inflation: Optional[DecayScore],
                                  retry_increase: Optional[DecayScore],
                                  memory_decay: Optional[DecayScore]) -> List[str]:
        """Identify critical issues requiring immediate attention"""
        issues = []
        
        if quality_decay and quality_decay.severity > self._critical_severity_threshold:
            issues.append(f"CRITICAL: Quality decay of {quality_decay.severity:.1%} detected")
        
        if speed_decay and speed_decay.severity > self._critical_severity_threshold:
            issues.append(f"CRITICAL: Speed degradation of {speed_decay.severity:.1%} detected")
        
        if cost_inflation and cost_inflation.severity > self._critical_severity_threshold:
            issues.append(f"CRITICAL: Cost inflation of {cost_inflation.severity:.1%} detected")
        
        if retry_increase and retry_increase.severity > self._critical_severity_threshold:
            issues.append(f"CRITICAL: Retry increase of {retry_increase.severity:.1%} detected")
        
        if memory_decay and memory_decay.severity > self._critical_severity_threshold:
            issues.append(f"CRITICAL: Memory growth of {memory_decay.severity:.1%} detected")
        
        return issues
    
    def _generate_recommendations(self, quality_decay: Optional[DecayScore],
                                  speed_decay: Optional[DecayScore],
                                  cost_inflation: Optional[DecayScore],
                                  retry_increase: Optional[DecayScore],
                                  memory_decay: Optional[DecayScore]) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []
        
        # Quality recommendations
        if quality_decay and quality_decay.trend == "degrading":
            if quality_decay.severity > 0.3:
                recommendations.append("URGENT: Initiate memory cleanup and context compression")
                recommendations.append("Consider triggering safe mode with reduced parallelism")
            else:
                recommendations.append("Monitor quality trends - consider proactive memory cleanup")
        
        # Speed recommendations
        if speed_decay and speed_decay.trend == "degrading":
            recommendations.append("Review caching strategy - cache hit rate may be declining")
            recommendations.append("Check for resource contention or memory pressure")
        
        # Cost recommendations
        if cost_inflation and cost_inflation.trend == "inflating":
            recommendations.append("Optimize resource allocation - cost efficiency declining")
            recommendations.append("Review task routing for unnecessary retries")
        
        # Retry recommendations
        if retry_increase and retry_increase.trend == "increasing":
            recommendations.append("Investigate root cause of increasing retries")
            recommendations.append("Consider adjusting retry budget or adding circuit breaker")
        
        # Memory recommendations
        if memory_decay and memory_decay.severity > 0.2:
            recommendations.append("Memory cleanup recommended - stale entries accumulating")
            recommendations.append("Consider periodic memory compaction")
        
        if not recommendations:
            recommendations.append("Session health is good - continue monitoring")
        
        return recommendations
    
    def get_current_phase(self) -> AgingPhase:
        """Get the current session phase based on task count"""
        task_count = self._store.get_task_count()
        if task_count == 0:
            return AgingPhase.FRESH
        
        # This is a simplified version - in reality would track actual session length
        if task_count <= 10:
            return AgingPhase.FRESH
        elif task_count <= 25:
            return AgingPhase.MATURE
        elif task_count <= 50:
            return AgingPhase.AGING
        else:
            return AgingPhase.OLD
    
    def get_phase_summary(self) -> Dict[str, Any]:
        """Get a quick summary of current phase metrics"""
        phase = self.get_current_phase()
        phase_tasks = self._store.get_phase_tasks()
        tasks = phase_tasks[phase]
        
        if not tasks:
            return {"phase": phase.value, "task_count": 0}
        
        successful = [t for t in tasks if t["success"]]
        
        return {
            "phase": phase.value,
            "task_count": len(tasks),
            "success_rate": len(successful) / len(tasks) if tasks else 0,
            "avg_quality": statistics.mean([t["quality"] for t in successful]) if successful else 0,
            "avg_retries": statistics.mean([t["retries"] for t in tasks])
        }
    
    def reset(self):
        """Reset the analyzer for a new session"""
        self._store.clear()
        self._start_time = datetime.now()
        self._end_time = None
        self._session_id = str(id(self))
    
    @property
    def session_id(self) -> str:
        return self._session_id
    
    @property
    def task_count(self) -> int:
        return self._store.get_task_count()


# ==================== AGING WATCHER ====================

class AgingWatcher:
    """
    Continuous watcher that monitors session aging in real-time.
    
    This runs alongside the session and provides early warnings
    when aging effects start to appear.
    """
    
    def __init__(self, analyzer: SessionAgingAnalyzer,
                 check_interval: int = 10,
                 warning_threshold: float = 0.15):
        self._analyzer = analyzer
        self._check_interval = check_interval
        self._warning_threshold = warning_threshold
        self._is_running = False
        self._last_warning_time: Optional[datetime] = None
        self._warnings: List[Dict] = []
        
        # Callbacks
        self._on_warning: Optional[Callable] = None
        self._on_critical: Optional[Callable] = None
    
    def set_callbacks(self, on_warning: Optional[Callable] = None,
                      on_critical: Optional[Callable] = None):
        """Set callback functions for warnings"""
        self._on_warning = on_warning
        self._on_critical = on_critical
    
    async def start(self):
        """Start the aging watcher"""
        self._is_running = True
        logger.info("Session aging watcher started")
        
        while self._is_running:
            await asyncio.sleep(self._check_interval)
            
            # Only analyze if we have enough tasks
            if self._analyzer.task_count < 10:
                continue
            
            # Quick analysis
            report = self._analyzer.analyze()
            
            # Check for warnings
            if report.aging_detected:
                warning = {
                    "timestamp": datetime.now(),
                    "health_score": report.overall_health_score,
                    "issues": report.critical_issues
                }
                
                self._warnings.append(warning)
                self._last_warning_time = datetime.now()
                
                # Trigger callbacks
                if report.overall_health_score < 50 and self._on_critical:
                    self._on_critical(report)
                elif self._on_warning:
                    self._on_warning(report)
    
    def stop(self):
        """Stop the aging watcher"""
        self._is_running = False
        logger.info("Session aging watcher stopped")
    
    def get_warnings(self) -> List[Dict]:
        """Get all warnings recorded"""
        return self._warnings.copy()
    
    @property
    def is_running(self) -> bool:
        return self._is_running


# ==================== FACTORY ====================

def create_session_analyzer(session_id: Optional[str] = None) -> SessionAgingAnalyzer:
    """Factory function to create session aging analyzer"""
    return SessionAgingAnalyzer(session_id=session_id)


def create_aging_watcher(analyzer: SessionAgingAnalyzer,
                        check_interval: int = 10) -> AgingWatcher:
    """Factory function to create aging watcher"""
    return AgingWatcher(analyzer=analyzer, check_interval=check_interval)
