"""
SuccessPatternMiner - Success Pattern Mining
=========================================

Successful runlardan patternlarni qidirish.

Bu modul:
- Early success markers
- High-value action sequences
- Low-cost successful paths
- Effective recovery strategies
- File discovery heuristics

aniqlaydi.

Definition of Done:
3. Failure va success pattern reportlari mavjud.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Set
from collections import defaultdict


@dataclass
class SuccessPattern:
    """Success pattern."""
    pattern_id: str
    pattern_type: str
    frequency: int
    success_rate: float  # How often this pattern leads to success
    avg_cost: float
    avg_duration_ms: int
    description: str


@dataclass
class SuccessInsight:
    """Success insight."""
    insight_type: str
    description: str
    evidence_count: int
    impact_score: float


class SuccessPatternMiner:
    """
    Success pattern mining.
    
    Definition of Done:
    3. Failure va success pattern reportlari mavjud.
    """
    
    def __init__(self):
        self.trace_storage = None
    
    def mine_patterns(self, traces: List[Any]) -> Dict[str, Any]:
        """Success patternlarni qidirish."""
        successful_traces = [t for t in traces if t.final_outcome == "success"]
        
        if not successful_traces:
            return {"total_successes": 0, "patterns": [], "insights": []}
        
        patterns = []
        patterns.extend(self._find_early_success_markers(successful_traces))
        patterns.extend(self._find_action_sequences(successful_traces))
        patterns.extend(self._find_low_cost_paths(successful_traces))
        patterns.extend(self._find_file_discovery_heuristics(successful_traces))
        
        insights = self._generate_insights(successful_traces, patterns)
        
        return {
            "total_successes": len(successful_traces),
            "patterns": [p.__dict__ for p in patterns],
            "insights": [i.__dict__ for i in insights],
        }
    
    def _find_early_success_markers(self, traces: List[Any]) -> List[SuccessPattern]:
        """Early success markers."""
        # Quick success: less than 10 tool calls
        quick_success = [t for t in traces if len(t.tool_calls) <= 10]
        
        if not quick_success:
            return []
        
        # Common first tools
        first_tools = defaultdict(int)
        for t in quick_success:
            if t.tool_calls:
                first_tools[t.tool_calls[0].tool_name] += 1
        
        patterns = []
        for tool, count in first_tools.items():
            if count >= 2:
                patterns.append(SuccessPattern(
                    pattern_id=f"early_marker_{tool}",
                    pattern_type="early_success",
                    frequency=count,
                    success_rate=count / len(traces),
                    avg_cost=sum(t.total_cost_usd for t in quick_success) / len(quick_success),
                    avg_duration_ms=sum(t.total_duration_ms for t in quick_success) / len(quick_success),
                    description=f"Starting with '{tool}' leads to quick success",
                ))
        
        return patterns
    
    def _find_action_sequences(self, traces: List[Any]) -> List[SuccessPattern]:
        """Action sequences that lead to success."""
        # Common successful sequences
        sequences = defaultdict(lambda: {"count": 0, "total_cost": 0, "total_duration": 0})
        
        for trace in traces:
            if len(trace.tool_calls) < 2:
                continue
            
            # Get first 3 tool calls
            seq = " -> ".join([tc.tool_name for tc in trace.tool_calls[:3]])
            sequences[seq]["count"] += 1
            sequences[seq]["total_cost"] += trace.total_cost_usd
            sequences[seq]["total_duration"] += trace.total_duration_ms
        
        patterns = []
        for seq, stats in sequences.items():
            if stats["count"] >= 2:
                patterns.append(SuccessPattern(
                    pattern_id=f"action_seq_{len(patterns)}",
                    pattern_type="action_sequence",
                    frequency=stats["count"],
                    success_rate=stats["count"] / len(traces),
                    avg_cost=stats["total_cost"] / stats["count"],
                    avg_duration_ms=stats["total_duration"] // stats["count"],
                    description=f"Action sequence: {seq}",
                ))
        
        return sorted(patterns, key=lambda p: p.frequency, reverse=True)[:10]
    
    def _find_low_cost_paths(self, traces: List[Any]) -> List[SuccessPattern]:
        """Low-cost successful paths."""
        if not traces:
            return []
        
        avg_cost = sum(t.total_cost_usd for t in traces) / len(traces)
        low_cost = [t for t in traces if t.total_cost_usd < avg_cost * 0.7]
        
        if not low_cost:
            return []
        
        patterns = [SuccessPattern(
            pattern_id="low_cost_path",
            pattern_type="efficiency",
            frequency=len(low_cost),
            success_rate=len(low_cost) / len(traces),
            avg_cost=sum(t.total_cost_usd for t in low_cost) / len(low_cost),
            avg_duration_ms=int(sum(t.total_duration_ms for t in low_cost) / len(low_cost)),
            description=f"Low-cost paths (<70% of average)",
        )]
        
        return patterns
    
    def _find_file_discovery_heuristics(self, traces: List[Any]) -> List[SuccessPattern]:
        """File discovery patterns."""
        first_file_reads = defaultdict(int)
        
        for trace in traces:
            for tc in trace.tool_calls:
                if tc.files_read:
                    first_file_reads[tc.files_read[0]] += 1
                    break  # Only first file read
        
        patterns = []
        for file_path, count in first_file_reads.items():
            if count >= 2:
                patterns.append(SuccessPattern(
                    pattern_id=f"file_discovery_{len(patterns)}",
                    pattern_type="file_discovery",
                    frequency=count,
                    success_rate=count / len(traces),
                    avg_cost=0,  # Would need calculation
                    avg_duration_ms=0,
                    description=f"First read: {file_path}",
                ))
        
        return sorted(patterns, key=lambda p: p.frequency, reverse=True)[:5]
    
    def _generate_insights(self, traces: List[Any], patterns: List[SuccessPattern]) -> List[SuccessInsight]:
        """Insights generatsiya."""
        insights = []
        
        # Quick success insight
        quick = len([t for t in traces if len(t.tool_calls) <= 10])
        if quick > len(traces) * 0.3:
            insights.append(SuccessInsight(
                insight_type="quick_success",
                description=f"{quick}/{len(traces)} succeed in ≤10 steps",
                evidence_count=quick,
                impact_score=0.8,
            ))
        
        # Low retry success
        low_retry = len([t for t in traces if t.total_retries == 0])
        if low_retry > len(traces) * 0.5:
            insights.append(SuccessInsight(
                insight_type="no_retry_success",
                description=f"{low_retry}/{len(traces)} succeed without retries",
                evidence_count=low_retry,
                impact_score=0.7,
            ))
        
        return insights


def create_success_miner() -> SuccessPatternMiner:
    """SuccessPatternMiner yaratish."""
    return SuccessPatternMiner()
