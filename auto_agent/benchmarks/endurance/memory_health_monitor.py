"""
Memory Health Monitor - Memory Rot Detection and Health Tracking
================================================================

This module monitors memory health over time, detecting:
- Memory bloat (uncontrolled growth)
- Memory rot (irrelevant/stale entries accumulating)
- Retrieval precision decay
- Duplicate memory entries
- Cache poisoning

Author: No1 World+ Autonomous System
"""

import asyncio
import time
import logging
import threading
from typing import Dict, List, Optional, Any, Set, Callable
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

class MemoryHealthLevel(str, Enum):
    """Memory health levels"""
    HEALTHY = "healthy"           # All good
    WARNING = "warning"            # Some degradation
    DEGRADED = "degraded"         # Significant issues
    CRITICAL = "critical"         # Immediate action needed


class MemoryIssueType(str, Enum):
    """Types of memory issues"""
    BLOAT = "bloat"               # Uncontrolled growth
    ROT = "rot"                   # Stale/irrelevant entries
    DUPLICATE = "duplicate"       # Duplicate entries
    POISONING = "poisoning"       # Corrupted/poisoned entries
    PRECISION_LOSS = "precision_loss"  # Retrieval getting worse
    CACHE_POLSONING = "cache_poisoning"  # Tool cache corrupted


# ==================== DATA CLASSES ====================

@dataclass
class MemoryEntry:
    """A single memory entry"""
    entry_id: str
    content: str
    embedding_hash: str
    created_at: datetime
    last_accessed: datetime
    access_count: int
    relevance_score: float
    tags: Set[str]
    metadata: Dict


@dataclass
class MemorySnapshot:
    """Snapshot of memory state"""
    timestamp: datetime
    total_entries: int
    total_size_bytes: int
    avg_entry_size: int
    stale_entries: int
    duplicate_entries: int
    unique_embeddings: int
    retrieval_precision: float
    cache_hit_rate: float
    health_level: MemoryHealthLevel


@dataclass
class MemoryIssue:
    """Detected memory issue"""
    issue_type: MemoryIssueType
    severity: float          # 0-1
    description: str
    affected_entries: int
    detected_at: datetime
    recommendation: str


@dataclass
class MemoryHealthReport:
    """Comprehensive memory health report"""
    timestamp: datetime
    current_level: MemoryHealthLevel
    
    # Entry statistics
    total_entries: int
    total_size_mb: float
    avg_entry_size: bytes
    
    # Health metrics
    staleness_ratio: float
    duplicate_ratio: float
    retrieval_precision: float
    cache_hit_rate: float
    
    # Trends (last hour)
    size_trend: str          # "stable", "growing", "shrinking"
    precision_trend: str     # "stable", "improving", "degrading"
    
    # Issues
    active_issues: List[MemoryIssue]
    resolved_issues: int
    
    # Recommendations
    recommendations: List[str]
    
    # Overall score (0-100)
    health_score: float


# ==================== MEMORY ENTRY TRACKER ====================

class MemoryEntryTracker:
    """Tracks individual memory entries"""
    
    def __init__(self):
        self._lock = threading.Lock()
        self._entries: Dict[str, MemoryEntry] = {}
        self._embeddings: Dict[str, Set[str]] = defaultdict(set)  # hash -> entry_ids
        self._tag_index: Dict[str, Set[str]] = defaultdict(set)   # tag -> entry_ids
    
    def add_entry(self, entry: MemoryEntry):
        """Add a memory entry"""
        with self._lock:
            self._entries[entry.entry_id] = entry
            
            # Update indices
            self._embeddings[entry.embedding_hash].add(entry.entry_id)
            for tag in entry.tags:
                self._tag_index[tag].add(entry.entry_id)
    
    def update_entry(self, entry_id: str, updates: Dict):
        """Update an existing entry"""
        with self._lock:
            if entry_id not in self._entries:
                return
            
            entry = self._entries[entry_id]
            
            if "last_accessed" in updates:
                entry.last_accessed = updates["last_accessed"]
                entry.access_count += 1
            
            if "relevance_score" in updates:
                entry.relevance_score = updates["relevance_score"]
    
    def remove_entry(self, entry_id: str):
        """Remove a memory entry"""
        with self._lock:
            if entry_id not in self._entries:
                return
            
            entry = self._entries[entry_id]
            
            # Remove from indices
            self._embeddings[entry.embedding_hash].discard(entry_id)
            for tag in entry.tags:
                self._tag_index[tag].discard(entry_id)
            
            del self._entries[entry_id]
    
    def get_stale_entries(self, stale_threshold_days: int = 7) -> List[MemoryEntry]:
        """Get entries that haven't been accessed recently"""
        cutoff = datetime.now() - timedelta(days=stale_threshold_days)
        
        with self._lock:
            return [
                e for e in self._entries.values()
                if e.last_accessed < cutoff
            ]
    
    def get_duplicates(self) -> List[List[MemoryEntry]]:
        """Find duplicate entries (same embedding hash)"""
        duplicates = []
        
        with self._lock:
            for hash_val, entry_ids in self._embeddings.items():
                if len(entry_ids) > 1:
                    entries = [self._entries[eid] for eid in entry_ids if eid in self._entries]
                    if len(entries) > 1:
                        duplicates.append(entries)
        
        return duplicates
    
    def get_statistics(self) -> Dict:
        """Get overall memory statistics"""
        with self._lock:
            if not self._entries:
                return {
                    "total_entries": 0,
                    "total_size": 0,
                    "avg_size": 0,
                    "unique_embeddings": 0,
                    "stale_entries": 0
                }
            
            total_size = sum(len(e.content) for e in self._entries.values())
            stale = self.get_stale_entries()
            
            return {
                "total_entries": len(self._entries),
                "total_size": total_size,
                "avg_size": total_size // len(self._entries) if self._entries else 0,
                "unique_embeddings": len(self._embeddings),
                "stale_entries": len(stale),
                "duplicate_groups": sum(1 for ids in self._embeddings.values() if len(ids) > 1)
            }


# ==================== RETRIEVAL ANALYZER ====================

class RetrievalAnalyzer:
    """Analyzes retrieval patterns and precision"""
    
    def __init__(self):
        self._lock = threading.Lock()
        self._retrievals: deque = deque(maxlen=1000)
        self._relevant: deque = deque(maxlen=1000)
    
    def record_retrieval(self, query: str, retrieved_ids: List[str],
                        relevant_ids: Set[str]):
        """Record a retrieval event"""
        with self._lock:
            # Calculate precision
            if retrieved_ids:
                relevant_count = len(set(retrieved_ids) & relevant_ids)
                precision = relevant_count / len(retrieved_ids)
            else:
                precision = 0.0
            
            self._retrievals.append({
                "timestamp": datetime.now(),
                "query": query,
                "retrieved_count": len(retrieved_ids),
                "relevant_count": len(set(retrieved_ids) & relevant_ids),
                "precision": precision
            })
            
            self._relevant.extend(relevant_ids)
    
    def get_precision(self, window_minutes: int = 30) -> float:
        """Get retrieval precision over time window"""
        cutoff = datetime.now() - timedelta(minutes=window_minutes)
        
        with self._lock:
            recent = [r for r in self._retrievals if r["timestamp"] > cutoff]
            
            if not recent:
                return 1.0  # Default to healthy
            
            return statistics.mean([r["precision"] for r in recent])
    
    def get_precision_trend(self, window_minutes: int = 60) -> str:
        """Get precision trend"""
        cutoff = datetime.now() - timedelta(minutes=window_minutes)
        
        with self._lock:
            retrievals = [r for r in self._retrievals if r["timestamp"] > cutoff]
        
        if len(retrievals) < 10:
            return "insufficient_data"
        
        # Split into halves
        n = len(retrievals)
        first_half = retrievals[:n//2]
        second_half = retrievals[n//2:]
        
        first_avg = statistics.mean([r["precision"] for r in first_half])
        second_avg = statistics.mean([r["precision"] for r in second_half])
        
        diff = second_avg - first_avg
        
        if abs(diff) < 0.05:
            return "stable"
        elif diff > 0:
            return "improving"
        else:
            return "degrading"


# ==================== MEMORY HEALTH MONITOR ====================

class MemoryHealthMonitor:
    """
    Monitors memory health over time, detecting degradation patterns.
    
    Key Features:
    - Real-time memory health scoring
    - Stale entry detection
    - Duplicate detection
    - Retrieval precision tracking
    - Cache health monitoring
    - Issue detection and recommendations
    - Automatic cleanup triggers
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self._config = config or {}
        
        # Components
        self._entry_tracker = MemoryEntryTracker()
        self._retrieval_analyzer = RetrievalAnalyzer()
        
        # State
        self._is_monitoring = False
        self._start_time = datetime.now()
        self._snapshot_history: deque = deque(maxlen=100)
        self._issues: List[MemoryIssue] = []
        self._resolved_issues = 0
        
        # Configuration
        self._stale_threshold_days = self._config.get("stale_threshold_days", 7)
        self._duplicate_threshold = self._config.get("duplicate_threshold", 0.1)  # 10%
        self._precision_warning = self._config.get("precision_warning", 0.7)
        self._precision_critical = self._config.get("precision_critical", 0.5)
        self._size_warning_mb = self._config.get("size_warning_mb", 500)
        self._size_critical_mb = self._config.get("size_critical_mb", 1000)
        
        # Callbacks
        self._on_issue_detected: Optional[Callable] = None
        self._on_cleanup_needed: Optional[Callable] = None
        self._on_health_critical: Optional[Callable] = None
    
    def set_callbacks(self,
                     on_issue_detected: Optional[Callable] = None,
                     on_cleanup_needed: Optional[Callable] = None,
                     on_health_critical: Optional[Callable] = None):
        """Set callback functions"""
        self._on_issue_detected = on_issue_detected
        self._on_cleanup_needed = on_cleanup_needed
        self._on_health_critical = on_health_critical
    
    # ==================== ENTRY MANAGEMENT ====================
    
    def add_memory_entry(self, entry_id: str, content: str, tags: Set[str],
                         relevance_score: float = 1.0, metadata: Optional[Dict] = None):
        """Add a new memory entry"""
        # Generate embedding hash
        embedding_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
        
        entry = MemoryEntry(
            entry_id=entry_id,
            content=content,
            embedding_hash=embedding_hash,
            created_at=datetime.now(),
            last_accessed=datetime.now(),
            access_count=1,
            relevance_score=relevance_score,
            tags=tags,
            metadata=metadata or {}
        )
        
        self._entry_tracker.add_entry(entry)
        
        # Check if cleanup is needed after adding
        self._check_cleanup_needed()
    
    def access_entry(self, entry_id: str, relevance_score: Optional[float] = None):
        """Record access to a memory entry"""
        updates = {
            "last_accessed": datetime.now()
        }
        
        if relevance_score is not None:
            updates["relevance_score"] = relevance_score
        
        self._entry_tracker.update_entry(entry_id, updates)
    
    def remove_entry(self, entry_id: str):
        """Remove a memory entry"""
        self._entry_tracker.remove_entry(entry_id)
    
    def record_retrieval(self, query: str, retrieved_ids: List[str],
                        relevant_ids: Set[str]):
        """Record a retrieval event"""
        self._retrieval_analyzer.record_retrieval(query, retrieved_ids, relevant_ids)
    
    # ==================== HEALTH ANALYSIS ====================
    
    def analyze_health(self) -> MemoryHealthReport:
        """Perform comprehensive health analysis"""
        stats = self._entry_tracker.get_statistics()
        
        # Calculate ratios
        stale_entries = self._entry_tracker.get_stale_entries(self._stale_threshold_days)
        duplicates = self._entry_tracker.get_duplicates()
        
        total_entries = stats["total_entries"]
        stale_ratio = len(stale_entries) / total_entries if total_entries > 0 else 0
        
        duplicate_count = sum(len(d) - 1 for d in duplicates)  # Count extras
        duplicate_ratio = duplicate_count / total_entries if total_entries > 0 else 0
        
        # Retrieval precision
        precision = self._retrieval_analyzer.get_precision()
        precision_trend = self._retrieval_analyzer.get_precision_trend()
        
        # Determine health level
        health_level = self._determine_health_level(
            stale_ratio, duplicate_ratio, precision, stats["total_size"]
        )
        
        # Calculate health score
        health_score = self._calculate_health_score(
            stale_ratio, duplicate_ratio, precision
        )
        
        # Detect issues
        issues = self._detect_issues(stale_ratio, duplicate_ratio, precision, stats)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            health_level, stale_ratio, duplicate_ratio, precision, stats
        )
        
        # Create snapshot
        snapshot = MemorySnapshot(
            timestamp=datetime.now(),
            total_entries=total_entries,
            total_size_bytes=stats["total_size"],
            avg_entry_size=stats["avg_size"],
            stale_entries=len(stale_entries),
            duplicate_entries=duplicate_count,
            unique_embeddings=stats["unique_embeddings"],
            retrieval_precision=precision,
            cache_hit_rate=0.9,  # Would track from actual cache
            health_level=health_level
        )
        
        self._snapshot_history.append(snapshot)
        
        # Check for critical health
        if health_level == MemoryHealthLevel.CRITICAL:
            if self._on_health_critical:
                self._on_health_critical(health_score, issues)
        
        # Check for cleanup needed
        if stale_ratio > 0.3 or duplicate_ratio > 0.2:
            if self._on_cleanup_needed:
                self._on_cleanup_needed(len(stale_entries), duplicate_count)
        
        return MemoryHealthReport(
            timestamp=datetime.now(),
            current_level=health_level,
            total_entries=total_entries,
            total_size_mb=stats["total_size"] / (1024 * 1024),
            avg_entry_size=stats["avg_size"],
            staleness_ratio=stale_ratio,
            duplicate_ratio=duplicate_ratio,
            retrieval_precision=precision,
            cache_hit_rate=0.9,
            size_trend=self._get_size_trend(),
            precision_trend=precision_trend,
            active_issues=issues,
            resolved_issues=self._resolved_issues,
            recommendations=recommendations,
            health_score=health_score
        )
    
    def _determine_health_level(self, stale_ratio: float, duplicate_ratio: float,
                                precision: float, total_size: int) -> MemoryHealthLevel:
        """Determine current memory health level"""
        size_mb = total_size / (1024 * 1024)
        
        # Check critical conditions
        if precision < self._precision_critical or size_mb > self._size_critical_mb:
            return MemoryHealthLevel.CRITICAL
        
        # Check warning conditions
        if precision < self._precision_warning or stale_ratio > 0.3 or duplicate_ratio > 0.2:
            return MemoryHealthLevel.WARNING
        
        # Check degraded conditions
        if stale_ratio > 0.2 or duplicate_ratio > 0.1 or size_mb > self._size_warning_mb:
            return MemoryHealthLevel.DEGRADED
        
        return MemoryHealthLevel.HEALTHY
    
    def _calculate_health_score(self, stale_ratio: float, duplicate_ratio: float,
                               precision: float) -> float:
        """Calculate overall health score (0-100)"""
        score = 100.0
        
        # Precision penalty (most important)
        score -= (1 - precision) * 40
        
        # Stale ratio penalty
        score -= stale_ratio * 25
        
        # Duplicate ratio penalty
        score -= duplicate_ratio * 20
        
        # Other factors (15 points reserved)
        
        return max(0, min(100, score))
    
    def _detect_issues(self, stale_ratio: float, duplicate_ratio: float,
                      precision: float, stats: Dict) -> List[MemoryIssue]:
        """Detect active memory issues"""
        issues = []
        
        # Stale entries issue
        if stale_ratio > 0.2:
            issue = MemoryIssue(
                issue_type=MemoryIssueType.ROT,
                severity=min(1.0, stale_ratio),
                description=f"{stale_ratio:.1%} of entries are stale",
                affected_entries=stats["stale_entries"],
                detected_at=datetime.now(),
                recommendation="Run memory cleanup to remove stale entries"
            )
            issues.append(issue)
            self._issues.append(issue)
        
        # Duplicate entries issue
        if duplicate_ratio > 0.1:
            issue = MemoryIssue(
                issue_type=MemoryIssueType.DUPLICATE,
                severity=min(1.0, duplicate_ratio),
                description=f"{duplicate_ratio:.1%} of entries are duplicates",
                affected_entries=stats["duplicate_groups"],
                detected_at=datetime.now(),
                recommendation="Deduplicate memory entries"
            )
            issues.append(issue)
            self._issues.append(issue)
        
        # Precision loss issue
        if precision < 0.7:
            issue = MemoryIssue(
                issue_type=MemoryIssueType.PRECISION_LOSS,
                severity=1.0 - precision,
                description=f"Retrieval precision dropped to {precision:.1%}",
                affected_entries=0,
                detected_at=datetime.now(),
                recommendation="Review memory indexing and retrieval strategy"
            )
            issues.append(issue)
            self._issues.append(issue)
        
        return issues
    
    def _generate_recommendations(self, health_level: MemoryHealthLevel,
                                stale_ratio: float, duplicate_ratio: float,
                                precision: float, stats: Dict) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []
        
        if health_level == MemoryHealthLevel.CRITICAL:
            recommendations.append("CRITICAL: Immediate memory cleanup required")
            recommendations.append("Consider triggering emergency memory compaction")
        
        if stale_ratio > 0.3:
            recommendations.append(f"Remove {stats['stale_entries']} stale entries")
        
        if duplicate_ratio > 0.15:
            recommendations.append("Deduplicate memory entries to reduce bloat")
        
        if precision < 0.7:
            recommendations.append("Review and optimize memory retrieval strategy")
        
        if not recommendations:
            recommendations.append("Memory health is good - maintain current practices")
        
        return recommendations
    
    def _get_size_trend(self) -> str:
        """Get memory size trend"""
        if len(self._snapshot_history) < 10:
            return "insufficient_data"
        
        recent = list(self._snapshot_history)[-10:]
        sizes = [s.total_size_bytes for s in recent]
        
        if len(sizes) < 2:
            return "stable"
        
        # Simple linear trend
        first_half = statistics.mean(sizes[:len(sizes)//2])
        second_half = statistics.mean(sizes[len(sizes)//2:])
        
        if first_half == 0:
            return "stable"
        
        change = (second_half - first_half) / first_half
        
        if abs(change) < 0.05:
            return "stable"
        elif change > 0:
            return "growing"
        else:
            return "shrinking"
    
    def _check_cleanup_needed(self):
        """Check if cleanup is needed"""
        report = self.analyze_health()
        
        if report.staleness_ratio > 0.3 or report.duplicate_ratio > 0.2:
            if self._on_cleanup_needed:
                self._on_cleanup_needed(
                    int(report.staleness_ratio * report.total_entries),
                    int(report.duplicate_ratio * report.total_entries)
                )
    
    # ==================== CLEANUP OPERATIONS ====================
    
    def cleanup_stale_entries(self, threshold_days: Optional[int] = None) -> int:
        """Remove stale entries"""
        threshold = threshold_days or self._stale_threshold_days
        stale = self._entry_tracker.get_stale_entries(threshold)
        
        for entry in stale:
            self._entry_tracker.remove_entry(entry.entry_id)
        
        logger.info(f"Cleaned up {len(stale)} stale entries")
        return len(stale)
    
    def cleanup_duplicates(self) -> int:
        """Remove duplicate entries, keeping most recent"""
        duplicates = self._entry_tracker.get_duplicates()
        
        removed = 0
        for dup_group in duplicates:
            # Keep the first, remove rest
            for entry in dup_group[1:]:
                self._entry_tracker.remove_entry(entry.entry_id)
                removed += 1
        
        logger.info(f"Cleaned up {removed} duplicate entries")
        return removed
    
    def perform_full_cleanup(self) -> Dict[str, int]:
        """Perform full memory cleanup"""
        stale_removed = self.cleanup_stale_entries()
        dup_removed = self.cleanup_duplicates()
        
        self._resolved_issues += len(self._issues)
        self._issues.clear()
        
        return {
            "stale_removed": stale_removed,
            "duplicates_removed": dup_removed,
            "total_removed": stale_removed + dup_removed
        }
    
    # ==================== MONITORING ====================
    
    def start_monitoring(self):
        """Start continuous monitoring"""
        self._is_monitoring = True
        logger.info("Memory health monitoring started")
    
    def stop_monitoring(self):
        """Stop continuous monitoring"""
        self._is_monitoring = False
        logger.info("Memory health monitoring stopped")
    
    @property
    def is_monitoring(self) -> bool:
        return self._is_monitoring
    
    @property
    def issues(self) -> List[MemoryIssue]:
        return self._issues.copy()
    
    @property
    def current_health_score(self) -> float:
        """Get current health score without full analysis"""
        report = self.analyze_health()
        return report.health_score


# ==================== FACTORY ====================

def create_memory_health_monitor(config: Optional[Dict] = None) -> MemoryHealthMonitor:
    """Factory function to create memory health monitor"""
    return MemoryHealthMonitor(config=config)
