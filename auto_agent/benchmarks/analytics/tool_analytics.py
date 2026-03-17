"""
ToolAnalytics - Tool Usage Analysis
==============================

Tool usage tahlili.

Bu modul:
- Tool usage frequency
- Success contribution
- Failure contribution
- Average latency
- Average retries
- Task-type fit

hisoblaydi.

Definition of Done:
4. Patch impact va tool effectiveness reportlari mavjud.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any
from collections import defaultdict


@dataclass
class ToolMetrics:
    """Tool metrikalari."""
    tool_name: str
    usage_count: int
    success_count: int
    failure_count: int
    success_rate: float
    avg_latency_ms: float
    avg_retries: float
    total_cost: float


class ToolAnalytics:
    """
    Tool analytics.
    
    Definition of Done:
    4. Patch impact va tool effectiveness reportlari mavjud.
    """
    
    def __init__(self):
        self.trace_storage = None
    
    def analyze_tools(self, traces: List[Any]) -> Dict[str, Any]:
        """Toollarni tahlil qilish."""
        tool_stats = defaultdict(lambda: {
            "count": 0, "success": 0, "fail": 0, 
            "latency": 0, "retries": 0, "cost": 0
        })
        
        suite_tool_stats = defaultdict(lambda: defaultdict(lambda: {
            "count": 0, "success": 0, "fail": 0
        }))
        
        for trace in traces:
            for tc in trace.tool_calls:
                stats = tool_stats[tc.tool_name]
                stats["count"] += 1
                stats["latency"] += tc.duration_ms
                stats["retries"] += tc.retry_count
                
                if tc.outcome == "success":
                    stats["success"] += 1
                else:
                    stats["fail"] += 1
                
                # Suite-specific
                suite_stats = suite_tool_stats[trace.suite][tc.tool_name]
                suite_stats["count"] += 1
                if tc.outcome == "success":
                    suite_stats["success"] += 1
                else:
                    suite_stats["fail"] += 1
        
        # Build tool metrics
        tools = []
        for tool_name, stats in tool_stats.items():
            count = stats["count"]
            tools.append(ToolMetrics(
                tool_name=tool_name,
                usage_count=count,
                success_count=stats["success"],
                failure_count=stats["fail"],
                success_rate=stats["success"] / count if count > 0 else 0,
                avg_latency_ms=stats["latency"] / count if count > 0 else 0,
                avg_retries=stats["retries"] / count if count > 0 else 0,
                total_cost=stats["cost"],
            ))
        
        # Sort by usage
        tools.sort(key=lambda t: t.usage_count, reverse=True)
        
        # Find best and worst
        best_tools = [t for t in tools if t.success_rate > 0.8][:5]
        worst_tools = [t for t in tools if t.success_rate < 0.5][:5]
        
        return {
            "total_tools": len(tools),
            "tools": [t.__dict__ for t in tools[:20]],
            "best_tools": [t.__dict__ for t in best_tools],
            "worst_tools": [t.__dict__ for t in worst_tools],
            "by_suite": {
                suite: {
                    tool: {
                        "count": stats["count"],
                        "success_rate": stats["success"] / stats["count"] if stats["count"] > 0 else 0
                    }
                    for tool, stats in tool_stats.items()
                }
                for suite, tool_stats in suite_tool_stats.items()
            },
        }


def create_tool_analytics() -> ToolAnalytics:
    """ToolAnalytics yaratish."""
    return ToolAnalytics()
