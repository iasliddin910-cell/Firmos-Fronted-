"""
FailurePathAnalyzer - Failure Pattern Analysis
==========================================

Failure patternlarini aniqlash.

Bu modul:
- Faildan oldingi tipik tool patterns
- Fail oldidan step explosion
- Repeated replans
- Wrong-file-first patterns
- Verifier mismatch classes
- Recovery dead-ends

aniqlaydi.

Definition of Done:
3. Failure va success pattern reportlari mavjud.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Set, Tuple
from collections import defaultdict
import re


@dataclass
class FailurePattern:
    """Failure pattern."""
    pattern_id: str
    pattern_type: str  # tool_sequence, file_access, retry, replan, etc.
    frequency: int
    affected_tasks: List[str]
    description: str


@dataclass
class FailureInsight:
    """Failure haqida insight."""
    insight_type: str
    description: str
    affected_count: int
    severity: str  # low, medium, high, critical
    recommendations: List[str]


class FailurePathAnalyzer:
    """
    Failure path tahlil.
    
    Definition of Done:
    3. Failure va success pattern reportlari mavjud.
    """
    
    def __init__(self):
        self.trace_storage = None
    
    def analyze_failures(self, traces: List[Any]) -> Dict[str, Any]:
        """Barcha failure'arni tahlil qilish."""
        failed_traces = [t for t in traces if t.final_outcome != "success"]
        
        if not failed_traces:
            return {"total_failures": 0, "patterns": [], "insights": []}
        
        # Find patterns
        patterns = []
        patterns.extend(self._find_tool_sequence_patterns(failed_traces))
        patterns.extend(self._find_retry_patterns(failed_traces))
        patterns.extend(self._find_replan_patterns(failed_traces))
        patterns.extend(self._find_file_access_patterns(failed_traces))
        patterns.extend(self._find_verifier_patterns(failed_traces))
        
        # Generate insights
        insights = self._generate_insights(failed_traces, patterns)
        
        return {
            "total_failures": len(failed_traces),
            "patterns": [p.__dict__ for p in patterns],
            "insights": [i.__dict__ for i in insights],
        }
    
    def _find_tool_sequence_patterns(self, traces: List[Any]) -> List[FailurePattern]:
        """Tool sequence patternlarini topish."""
        # Extract tool sequences leading to failure
        sequences = defaultdict(list)
        
        for trace in traces:
            if len(trace.tool_calls) < 2:
                continue
            
            # Get last 3 tool calls before failure
            last_tools = [tc.tool_name for tc in trace.tool_calls[-3:]]
            seq_key = " -> ".join(last_tools)
            sequences[seq_key].append(trace.task_id)
        
        # Find common patterns
        patterns = []
        for seq, task_ids in sequences.items():
            if len(task_ids) >= 2:  # At least 2 occurrences
                patterns.append(FailurePattern(
                    pattern_id=f"tool_seq_{len(patterns)}",
                    pattern_type="tool_sequence",
                    frequency=len(task_ids),
                    affected_tasks=task_ids,
                    description=f"Tool sequence '{seq}' leads to failure",
                ))
        
        return patterns[:10]  # Top 10
    
    def _find_retry_patterns(self, traces: List[Any]) -> List[FailurePattern]:
        """Retry patternlarini topish."""
        high_retry_traces = [t for t in traces if t.total_retries >= 3]
        
        if not high_retry_traces:
            return []
        
        return [FailurePattern(
            pattern_id="high_retry",
            pattern_type="retry",
            frequency=len(high_retry_traces),
            affected_tasks=[t.task_id for t in high_retry_traces],
            description=f"Tasks with 3+ retries: {len(high_retry_traces)}",
        )]
    
    def _find_replan_patterns(self, traces: List[Any]) -> List[FailurePattern]:
        """Replan patternlarini topish."""
        high_replan_traces = [t for t in traces if t.total_replans >= 2]
        
        if not high_replan_traces:
            return []
        
        # Find common replan sequences
        replan_sequences = defaultdict(list)
        
        for trace in high_replan_traces:
            # Get tool around replans
            for i, tc in enumerate(trace.tool_calls):
                if tc.outcome == "replan" or tc.phase == "replan":
                    # Get surrounding tools
                    start = max(0, i - 2)
                    end = min(len(trace.tool_calls), i + 3)
                    seq = " -> ".join([t.tool_name for t in trace.tool_calls[start:end]])
                    replan_sequences[seq].append(trace.task_id)
        
        patterns = []
        for seq, task_ids in replan_sequences.items():
            if len(task_ids) >= 1:
                patterns.append(FailurePattern(
                    pattern_id=f"replan_{len(patterns)}",
                    pattern_type="replan",
                    frequency=len(task_ids),
                    affected_tasks=task_ids,
                    description=f"Replan context: {seq}",
                ))
        
        return patterns[:5]
    
    def _find_file_access_patterns(self, traces: List[Any]) -> List[FailurePattern]:
        """File access patternlarini topish."""
        # Track which files are read before failure
        wrong_file_patterns = defaultdict(list)
        
        for trace in traces:
            # Check if wrong file was accessed first
            first_file_reads = []
            for tc in trace.tool_calls[:3]:  # First 3 calls
                first_file_reads.extend(tc.files_read)
            
            if first_file_reads:
                # This is simplified - in reality would compare to actual target
                key = first_file_reads[0] if first_file_reads else "none"
                wrong_file_patterns[key].append(trace.task_id)
        
        patterns = []
        for file_path, task_ids in wrong_file_patterns.items():
            if len(task_ids) >= 2 and file_path != "none":
                patterns.append(FailurePattern(
                    pattern_id=f"file_access_{len(patterns)}",
                    pattern_type="file_access",
                    frequency=len(task_ids),
                    affected_tasks=task_ids,
                    description=f"Started with file: {file_path}",
                ))
        
        return patterns[:5]
    
    def _find_verifier_patterns(self, traces: List[Any]) -> List[FailurePattern]:
        """Verifier mismatch patternlarini topish."""
        verifier_failures = []
        
        for trace in traces:
            # Check verifier outcomes
            for i, outcome in enumerate(trace.verifier_outcomes):
                if outcome == "fail":
                    verifier_failures.append({
                        "task_id": trace.task_id,
                        "attempt": i,
                        "verifier_calls": trace.verifier_calls,
                    })
        
        # Group by number of verifier calls
        call_groups = defaultdict(list)
        for v in verifier_failures:
            call_groups[v["verifier_calls"]].append(v["task_id"])
        
        patterns = []
        for calls, task_ids in call_groups.items():
            patterns.append(FailurePattern(
                pattern_id=f"verifier_{calls}_calls",
                pattern_type="verifier_mismatch",
                frequency=len(task_ids),
                affected_tasks=task_ids,
                description=f"Failed after {calls} verifier calls",
            ))
        
        return patterns
    
    def _generate_insights(self, traces: List[Any], patterns: List[FailurePattern]) -> List[FailureInsight]:
        """Insights generatsiya."""
        insights = []
        
        # High retry insight
        high_retry = len([t for t in traces if t.total_retries >= 3])
        if high_retry > len(traces) * 0.2:
            insights.append(FailureInsight(
                insight_type="high_retry_rate",
                description=f"{high_retry}/{len(traces)} tasks have 3+ retries",
                affected_count=high_retry,
                severity="high",
                recommendations=[
                    "Check for flaky tests or unstable environment",
                    "Review retry logic for stuck patterns",
                    "Consider adding timeout handling",
                ],
            ))
        
        # High replan insight
        high_replan = len([t for t in traces if t.total_replans >= 2])
        if high_replan > len(traces) * 0.15:
            insights.append(FailureInsight(
                insight_type="high_replan_rate",
                description=f"{high_replan}/{len(traces)} tasks replanned 2+ times",
                affected_count=high_replan,
                severity="medium",
                recommendations=[
                    "Review planning logic for thrashing",
                    "Check if task descriptions are ambiguous",
                    "Consider adding checkpointing",
                ],
            ))
        
        # Early failure insight
        early_failures = len([t for t in traces if len(t.tool_calls) <= 3])
        if early_failures > len(traces) * 0.3:
            insights.append(FailureInsight(
                insight_type="early_failures",
                description=f"{early_failures}/{len(traces)} tasks fail within 3 steps",
                affected_count=early_failures,
                severity="high",
                recommendations=[
                    "Check if tools are being selected correctly",
                    "Review task setup and initialization",
                    "Verify tool availability and permissions",
                ],
            ))
        
        return insights


def create_failure_analyzer() -> FailurePathAnalyzer:
    """FailurePathAnalyzer yaratish."""
    return FailurePathAnalyzer()
