"""
FailureClusterer - Failure Pattern Clustering Module

Bu modul benchmarklardan kelgan failure signallarini klasterlab, 
har bir klasterdan yangi benchmark task generatsiya qilish uchun asos yaratadi.

Failure klasterlari:
- wrong-file-first: Noto'g'ri faylni birinchi bo'lib tanlash
- tool-thrash: Ko'p tool chaqiruvlari, lekin muvaffaqiyatsiz
- hidden-regression: Yashirin regression - dastur ishlaydi, lekin muayyan holatda ishlamaydi
- late-lock-on: Kech qolib to'g'ri yechimga yetib borish
- selector-fragility: Browser selector ishlamay qolishi
- overbroad-patch: juda keng patch - ko'p narsalarni o'zgartiradi
- rollback-failure: O'zgartirishlarni bekor qilish muvaffaqiyatsiz
- retrieval-miss: Kerakli ma'lumotni topa olmaslik
- same-wrong-tool: Xuddi shu noto'g'ri tool qayta-qayta ishlatilishi

Policy 2: Har katta improvementdan keyin frontier task generation ishlasin.
"""

from typing import Dict, List, Tuple, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, Counter
import statistics
import re


class FailureCluster(Enum):
    """Known failure cluster types"""
    WRONG_FILE_FIRST = "wrong_file_first"
    TOOL_THRASH = "tool_thrash"
    HIDDEN_REGRESSION = "hidden_regression"
    LATE_LOCK_ON = "late_lock_on"
    SELECTOR_FRAGILITY = "selector_fragility"
    OVERBROAD_PATCH = "overbroad_patch"
    ROLLBACK_FAILURE = "rollback_failure"
    RETRIEVAL_MISS = "retrieval_miss"
    SAME_WRONG_TOOL = "same_wrong_tool"
    AMBIGUITY_HANDLING = "ambiguity_handling"
    SELF_MOD_DELTA = "self_mod_delta"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"


class Severity(Enum):
    """Failure severity levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class FailureTrace:
    """A single failure trace from evaluation"""
    task_id: str
    run_id: str
    timestamp: float
    error_type: str
    error_message: str
    tools_used: List[str]
    files_accessed: List[str]
    execution_time: float
    partial_output: Optional[str] = None
    stack_trace: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FailurePattern:
    """A pattern of repeated failures"""
    cluster_type: FailureCluster
    occurrence_count: int
    affected_tasks: List[str]
    severity: Severity
    description: str
    common_symptoms: List[str]
    recommended_fix: str
    task_generation_hints: List[str]
    diagnostic_value: float


@dataclass
class FailureClusterResult:
    """Result of clustering failures"""
    clusters: List[FailurePattern]
    total_failures: int
    cluster_map: Dict[str, FailureCluster]  # task_id -> cluster
    unclustered_failures: List[str]


class FailureClusterer:
    """
    Clusters failures from benchmark runs to identify common patterns.
    
    Bu klasterlar benchmarkdan yangi task yaratish uchun asos bo'ladi.
    Har bir failure cluster yangi task oilasini generatsiya qilish uchun ishlatiladi.
    """
    
    # Pattern detection thresholds
    MIN_CLUSTER_SIZE = 2
    MAX_CLUSTERS = 12
    SIMILARITY_THRESHOLD = 0.6
    
    # Severity weights
    SEVERITY_WEIGHTS = {
        Severity.CRITICAL: 1.0,
        Severity.HIGH: 0.75,
        Severity.MEDIUM: 0.5,
        Severity.LOW: 0.25
    }
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self._pattern_detectors = self._init_pattern_detectors()
        
    def _init_pattern_detectors(self) -> Dict[FailureCluster, 'PatternDetector']:
        """Initialize pattern detectors for each cluster type"""
        return {
            FailureCluster.WRONG_FILE_FIRST: PatternDetector(
                patterns=[
                    r"wrong file",
                    r"incorrect file",
                    r"wrong.*edit",
                    r"edit.*wrong"
                ],
                keywords=["file", "edit", "modify", "wrong"]
            ),
            FailureCluster.TOOL_THRASH: PatternDetector(
                patterns=[
                    r"tool.*fail",
                    r"multiple.*attempt",
                    r"retry.*fail"
                ],
                keywords=["tool", "retry", "attempt", "multiple"]
            ),
            FailureCluster.HIDDEN_REGRESSION: PatternDetector(
                patterns=[
                    r"regression",
                    r"was working.*now.*fail",
                    r"previously.*now"
                ],
                keywords=["regression", "previously", "broken"]
            ),
            FailureCluster.LATE_LOCK_ON: PatternDetector(
                patterns=[
                    r"late.*find",
                    r"eventually.*correct",
                    r"final.*attempt.*success"
                ],
                keywords=["late", "eventually", "final"]
            ),
            FailureCluster.SELECTOR_FRAGILITY: PatternDetector(
                patterns=[
                    r"selector.*fail",
                    r"xpath.*error",
                    r"css.*not.*found",
                    r"element.*not.*found"
                ],
                keywords=["selector", "xpath", "css", "element"]
            ),
            FailureCluster.OVERBROAD_PATCH: PatternDetector(
                patterns=[
                    r"too.*many.*change",
                    r"broad.*patch",
                    r"excessive.*modification"
                ],
                keywords=["change", "modify", "patch", "many"]
            ),
            FailureCluster.ROLLBACK_FAILURE: PatternDetector(
                patterns=[
                    r"rollback.*fail",
                    r"cannot.*revert",
                    r"revert.*error"
                ],
                keywords=["rollback", "revert", "undo"]
            ),
            FailureCluster.RETRIEVAL_MISS: PatternDetector(
                patterns=[
                    r"not found",
                    r"cannot.*find",
                    r"missing",
                    r"no.*result"
                ],
                keywords=["find", "search", "retrieve", "missing"]
            ),
            FailureCluster.SAME_WRONG_TOOL: PatternDetector(
                patterns=[
                    r"same.*tool.*again",
                    r"repeated.*wrong",
                    r"tool.*repeat"
                ],
                keywords=["tool", "repeat", "wrong", "again"]
            ),
            FailureCluster.AMBIGUITY_HANDLING: PatternDetector(
                patterns=[
                    r"ambiguous",
                    r"unclear.*spec",
                    r"multiple.*possible"
                ],
                keywords=["ambiguous", "unclear", "multiple"]
            ),
            FailureCluster.SELF_MOD_DELTA: PatternDetector(
                patterns=[
                    r"self.*modif",
                    r"self.*patch",
                    r"agent.*change.*self"
                ],
                keywords=["self", "modify", "patch", "change"]
            ),
            FailureCluster.TIMEOUT: PatternDetector(
                patterns=[
                    r"timeout",
                    r"took.*too.*long",
                    r"exceed.*time"
                ],
                keywords=["timeout", "time", "long", "exceed"]
            )
        }
    
    def cluster_failures(self, traces: List[FailureTrace]) -> FailureClusterResult:
        """
        Cluster failures into common patterns.
        
        Args:
            traces: List of FailureTrace from benchmark runs
            
        Returns:
            FailureClusterResult with clustered patterns
        """
        # Classify each failure
        task_clusters: Dict[str, FailureCluster] = {}
        cluster_tasks: Dict[FailureCluster, List[str]] = defaultdict(list)
        cluster_traces: Dict[FailureCluster, List[FailureTrace]] = defaultdict(list)
        
        for trace in traces:
            cluster = self._classify_failure(trace)
            task_clusters[trace.task_id] = cluster
            cluster_tasks[cluster].append(trace.task_id)
            cluster_traces[cluster].append(trace)
        
        # Build patterns from clusters
        patterns = []
        for cluster_type, task_ids in cluster_tasks.items():
            if len(task_ids) >= self.MIN_CLUSTER_SIZE:
                pattern = self._build_pattern(cluster_type, task_ids, cluster_traces[cluster_type])
                patterns.append(pattern)
        
        # Sort by diagnostic value
        patterns.sort(key=lambda p: p.diagnostic_value, reverse=True)
        
        # Limit to top clusters
        patterns = patterns[:self.MAX_CLUSTERS]
        
        # Identify unclustered failures
        all_clustered = set()
        for p in patterns:
            all_clustered.update(p.affected_tasks)
        
        unclustered = [t.task_id for t in traces if t.task_id not in all_clustered]
        
        return FailureClusterResult(
            clusters=patterns,
            total_failures=len(traces),
            cluster_map=task_clusters,
            unclustered_failures=unclustered
        )
    
    def _classify_failure(self, trace: FailureTrace) -> FailureCluster:
        """Classify a single failure trace"""
        combined_text = f"{trace.error_type} {trace.error_message} {' '.join(trace.tools_used)}"
        
        scores = {}
        
        for cluster_type, detector in self._pattern_detectors.items():
            score = detector.calculate_score(combined_text)
            if score > 0:
                scores[cluster_type] = score
        
        if not scores:
            return FailureCluster.UNKNOWN
        
        # Return highest scoring cluster
        return max(scores, key=scores.get)
    
    def _build_pattern(
        self,
        cluster_type: FailureCluster,
        task_ids: List[str],
        traces: List[FailureTrace]
    ) -> FailurePattern:
        """Build a FailurePattern from clustered traces"""
        # Determine severity
        severity = self._determine_severity(cluster_type, traces)
        
        # Extract common symptoms
        symptoms = self._extract_symptoms(traces)
        
        # Generate description and recommendations
        description = self._generate_description(cluster_type, len(task_ids))
        recommended_fix = self._generate_fix_hint(cluster_type)
        task_hints = self._generate_task_hints(cluster_type)
        
        # Calculate diagnostic value
        diagnostic_value = self._calculate_diagnostic_value(
            cluster_type, len(task_ids), severity, symptoms
        )
        
        return FailurePattern(
            cluster_type=cluster_type,
            occurrence_count=len(task_ids),
            affected_tasks=task_ids,
            severity=severity,
            description=description,
            common_symptoms=symptoms,
            recommended_fix=recommended_fix,
            task_generation_hints=task_hints,
            diagnostic_value=diagnostic_value
        )
    
    def _determine_severity(
        self,
        cluster_type: FailureCluster,
        traces: List[FailureTrace]
    ) -> Severity:
        """Determine severity of a cluster"""
        # Base severity from cluster type
        base_severity = {
            FailureCluster.WRONG_FILE_FIRST: Severity.HIGH,
            FailureCluster.TOOL_THRASH: Severity.MEDIUM,
            FailureCluster.HIDDEN_REGRESSION: Severity.CRITICAL,
            FailureCluster.LATE_LOCK_ON: Severity.MEDIUM,
            FailureCluster.SELECTOR_FRAGILITY: Severity.HIGH,
            FailureCluster.OVERBROAD_PATCH: Severity.MEDIUM,
            FailureCluster.ROLLBACK_FAILURE: Severity.HIGH,
            FailureCluster.RETRIEVAL_MISS: Severity.MEDIUM,
            FailureCluster.SAME_WRONG_TOOL: Severity.HIGH,
            FailureCluster.AMBIGUITY_HANDLING: Severity.MEDIUM,
            FailureCluster.SELF_MOD_DELTA: Severity.CRITICAL,
            FailureCluster.TIMEOUT: Severity.MEDIUM,
            FailureCluster.UNKNOWN: Severity.LOW
        }.get(cluster_type, Severity.MEDIUM)
        
        # Adjust based on execution time variance
        if traces:
            times = [t.execution_time for t in traces]
            if len(times) > 1:
                cv = statistics.stdev(times) / statistics.mean(times) if statistics.mean(times) > 0 else 0
                if cv > 0.5:
                    # High variance - might indicate instability
                    return Severity(base_severity.value + 1) if base_severity != Severity.CRITICAL else Severity.CRITICAL
        
        return base_severity
    
    def _extract_symptoms(self, traces: List[FailureTrace]) -> List[str]:
        """Extract common symptoms from traces"""
        all_symptoms = []
        
        for trace in traces:
            # Extract keywords from error message
            words = re.findall(r'\b\w+\b', trace.error_message.lower())
            all_symptoms.extend(words[:5])  # Top 5 words per trace
        
        # Get most common symptoms
        counter = Counter(all_symptoms)
        return [s for s, _ in counter.most_common(10)]
    
    def _generate_description(self, cluster_type: FailureCluster, count: int) -> str:
        """Generate human-readable description"""
        descriptions = {
            FailureCluster.WRONG_FILE_FIRST: f"{count} tasks where agent edits wrong file first",
            FailureCluster.TOOL_THRASH: f"{count} tasks with excessive tool thrashing",
            FailureCluster.HIDDEN_REGRESSION: f"{count} tasks with hidden regression issues",
            FailureCluster.LATE_LOCK_ON: f"{count} tasks where agent finds solution late",
            FailureCluster.SELECTOR_FRAGILITY: f"{count} tasks with brittle selector failures",
            FailureCluster.OVERBROAD_PATCH: f"{count} tasks with overly broad patches",
            FailureCluster.ROLLBACK_FAILURE: f"{count} tasks with rollback failures",
            FailureCluster.RETRIEVAL_MISS: f"{count} tasks with retrieval misses",
            FailureCluster.SAME_WRONG_TOOL: f"{count} tasks repeatedly using wrong tool",
            FailureCluster.AMBIGUITY_HANDLING: f"{count} tasks with ambiguity handling issues",
            FailureCluster.SELF_MOD_DELTA: f"{count} tasks with self-modification failures",
            FailureCluster.TIMEOUT: f"{count} tasks with timeout issues",
            FailureCluster.UNKNOWN: f"{count} unclassified failures"
        }
        return descriptions.get(cluster_type, f"{count} failures")
    
    def _generate_fix_hint(self, cluster_type: FailureCluster) -> str:
        """Generate fix hint for a cluster type"""
        hints = {
            FailureCluster.WRONG_FILE_FIRST: "Improve file search and verification before editing",
            FailureCluster.TOOL_THRASH: "Add tool selection validation and early termination",
            FailureCluster.HIDDEN_REGRESSION: "Add regression test coverage for edge cases",
            FailureCluster.LATE_LOCK_ON: "Improve early solution recognition",
            FailureCluster.SELECTOR_FRAGILITY: "Use more robust selector strategies",
            FailureCluster.OVERBROAD_PATCH: "Implement patch scope validation",
            FailureCluster.ROLLBACK_FAILURE: "Add safe rollback mechanisms",
            FailureCluster.RETRIEVAL_MISS: "Improve retrieval and search strategies",
            FailureCluster.SAME_WRONG_TOOL: "Add tool usage history tracking",
            FailureCluster.AMBIGUITY_HANDLING: "Improve specification clarification",
            FailureCluster.SELF_MOD_DELTA: "Add safer self-modification guards",
            FailureCluster.TIMEOUT: "Optimize execution paths and add timeouts"
        }
        return hints.get(cluster_type, "Analyze and improve")
    
    def _generate_task_hints(self, cluster_type: FailureCluster) -> List[str]:
        """Generate task generation hints from cluster"""
        hints = {
            FailureCluster.WRONG_FILE_FIRST: [
                "Create tasks with multiple similar files",
                "Add file verification steps",
                "Test with ambiguous file names"
            ],
            FailureCluster.TOOL_THRASH: [
                "Create tasks requiring optimal tool selection",
                "Add tasks with limited tool budget",
                "Test multi-step tool chains"
            ],
            FailureCluster.HIDDEN_REGRESSION: [
                "Create tasks with edge case regressions",
                "Add tasks with subtle behavioral changes",
                "Test previously working scenarios"
            ],
            FailureCluster.LATE_LOCK_ON: [
                "Create tasks with time pressure",
                "Add tasks requiring quick recognition",
                "Test early vs late solution finding"
            ],
            FailureCluster.SELECTOR_FRAGILITY: [
                "Create tasks with fragile selectors",
                "Add tasks with dynamic elements",
                "Test selector resilience"
            ],
            FailureCluster.OVERBROAD_PATCH: [
                "Create tasks requiring minimal changes",
                "Add tasks with scope constraints",
                "Test targeted vs broad fixes"
            ],
            FailureCluster.RETRIEVAL_MISS: [
                "Create tasks with hard-to-find information",
                "Add tasks with misleading context",
                "Test retrieval under ambiguity"
            ],
            FailureCluster.SELF_MOD_DELTA: [
                "Create tasks requiring self-patching",
                "Add tasks with self-modification safety",
                "Test delta-based improvements"
            ]
        }
        return hints.get(cluster_type, ["Analyze failure pattern for task generation"])
    
    def _calculate_diagnostic_value(
        self,
        cluster_type: FailureCluster,
        count: int,
        severity: Severity,
        symptoms: List[str]
    ) -> float:
        """Calculate diagnostic value of a cluster"""
        value = 0.0
        
        # More occurrences = more diagnostic
        value += min(count * 0.1, 0.3)
        
        # Higher severity = more diagnostic
        value += self.SEVERITY_WEIGHTS.get(severity, 0.25) * 0.4
        
        # More unique symptoms = more diagnostic
        value += min(len(symptoms) * 0.05, 0.2)
        
        # Critical clusters get bonus
        if severity == Severity.CRITICAL:
            value += 0.1
        
        return value
    
    def get_cluster_report(self, traces: List[FailureTrace]) -> Dict[str, Any]:
        """Generate a comprehensive cluster report"""
        result = self.cluster_failures(traces)
        
        return {
            "total_failures": result.total_failures,
            "cluster_count": len(result.clusters),
            "clusters": [
                {
                    "type": p.cluster_type.value,
                    "count": p.occurrence_count,
                    "severity": p.severity.value,
                    "description": p.description,
                    "fix_hint": p.recommended_fix,
                    "task_hints": p.task_generation_hints,
                    "diagnostic_value": p.diagnostic_value,
                    "affected_tasks": p.affected_tasks[:5]
                }
                for p in result.clusters
            ],
            "unclustered_count": len(result.unclustered_failures),
            "summary": self._generate_summary(result.clusters)
        }
    
    def _generate_summary(self, clusters: List[FailurePattern]) -> str:
        """Generate text summary of clusters"""
        if not clusters:
            return "No significant failure clusters detected."
        
        lines = [f"Found {len(clusters)} failure clusters:"]
        
        for i, cluster in enumerate(clusters[:5], 1):
            lines.append(
                f"{i}. {cluster.cluster_type.value}: {cluster.occurrence_count} tasks "
                f"({cluster.severity.value})"
            )
        
        return "\n".join(lines)


class PatternDetector:
    """Helper class for detecting failure patterns"""
    
    def __init__(self, patterns: List[str], keywords: List[str]):
        self.patterns = [re.compile(p, re.IGNORECASE) for p in patterns]
        self.keywords = set(keywords)
    
    def calculate_score(self, text: str) -> float:
        """Calculate pattern match score"""
        text = text.lower()
        score = 0.0
        
        # Pattern matches
        for pattern in self.patterns:
            if pattern.search(text):
                score += 0.5
        
        # Keyword matches
        text_words = set(text.split())
        keyword_matches = len(self.keywords & text_words)
        score += keyword_matches * 0.1
        
        return score


__all__ = [
    'FailureClusterer',
    'FailureTrace',
    'FailurePattern',
    'FailureClusterResult',
    'FailureCluster',
    'Severity',
    'PatternDetector'
]
