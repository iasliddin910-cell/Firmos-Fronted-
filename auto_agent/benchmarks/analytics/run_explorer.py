"""
RunExplorer - Run Analysis View
==============================

Bu analytics uchun asosiy view.
Task trace'ni timeline, tool sequence, failures, retries va boshqa
detallarni ko'rsatadi.

Definition of Done:
2. Run explorer orqali bitta run'ni timeline ko'rishda tahlil qila olasan.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict
from datetime import datetime


@dataclass
class RunSummary:
    """Run uchun summary."""
    run_id: str
    agent_version: str
    total_tasks: int
    passed: int
    failed: int
    total_duration_ms: int
    total_cost: float
    total_retries: int
    total_replans: int


@dataclass
class TaskSummary:
    """Task uchun summary."""
    task_id: str
    suite: str
    difficulty: str
    outcome: str
    duration_ms: int
    retries: int
    replans: int
    tool_count: int
    failed_step: Optional[int] = None
    error_type: Optional[str] = None


@dataclass
class ToolSequence:
    """Tool call sequence."""
    tool_name: str
    count: int
    success_count: int
    fail_count: int
    avg_duration_ms: float


class RunExplorer:
    """
    Run trace'ni tahlil qilish.
    
    Definition of Done:
    2. Run explorer orqali bitta run'ni timeline ko'rishda tahlil qila olasan.
    """
    
    def __init__(self, trace_storage=None):
        self.trace_storage = trace_storage
    
    def explore_run(self, run_id: str) -> Dict[str, Any]:
        """Run'ni to'liq tahlil qilish."""
        if not self.trace_storage:
            return {"error": "No trace storage"}
        
        trace = self.trace_storage.load_run_trace(run_id)
        if not trace:
            return {"error": f"Run {run_id} not found"}
        
        return self._build_run_view(trace)
    
    def _build_run_view(self, trace) -> Dict[str, Any]:
        """Run view qurish."""
        # Run summary
        summary = RunSummary(
            run_id=trace.run_id,
            agent_version=trace.agent_version,
            total_tasks=trace.total_tasks,
            passed=trace.passed_tasks,
            failed=trace.failed_tasks,
            total_duration_ms=trace.total_duration_ms,
            total_cost=trace.total_cost_usd,
            total_retries=sum(t.total_retries for t in trace.task_traces),
            total_replans=sum(t.total_replans for t in trace.task_traces),
        )
        
        # Task summaries
        task_summaries = []
        for task_trace in trace.task_traces:
            failed_step = None
            error_type = None
            
            for i, tc in enumerate(task_trace.tool_calls):
                if tc.outcome == "fail":
                    failed_step = i
                    error_type = tc.error_type
                    break
            
            task_summaries.append(TaskSummary(
                task_id=task_trace.task_id,
                suite=task_trace.suite,
                difficulty=task_trace.difficulty,
                outcome=task_trace.final_outcome,
                duration_ms=task_trace.total_duration_ms,
                retries=task_trace.total_retries,
                replans=task_trace.total_replans,
                tool_count=len(task_trace.tool_calls),
                failed_step=failed_step,
                error_type=error_type,
            ))
        
        # Tool sequences
        tool_sequences = self._analyze_tool_sequences(trace)
        
        # Timeline (first 10 steps of each task)
        timeline = []
        for task_trace in trace.task_traces[:5]:  # First 5 tasks
            task_timeline = []
            for tc in task_trace.tool_calls[:10]:  # First 10 steps
                task_timeline.append({
                    "step": tc.step_index,
                    "tool": tc.tool_name,
                    "phase": tc.phase,
                    "outcome": tc.outcome,
                    "duration_ms": tc.duration_ms,
                    "files_read": len(tc.files_read),
                    "files_written": len(tc.files_written),
                })
            timeline.append({
                "task_id": task_trace.task_id,
                "steps": task_timeline,
            })
        
        # Failures
        failures = self._analyze_failures(trace)
        
        # Success patterns
        successes = self._analyze_successes(trace)
        
        return {
            "summary": summary.__dict__,
            "task_summaries": [ts.__dict__ for ts in task_summaries],
            "tool_sequences": tool_sequences,
            "timeline": timeline,
            "failures": failures,
            "successes": successes,
        }
    
    def _analyze_tool_sequences(self, trace) -> List[Dict]:
        """Tool sequence tahlil."""
        tool_stats = defaultdict(lambda: {"count": 0, "success": 0, "fail": 0, "duration": 0})
        
        for task_trace in trace.task_traces:
            for tc in task_trace.tool_calls:
                stats = tool_stats[tc.tool_name]
                stats["count"] += 1
                stats["duration"] += tc.duration_ms
                if tc.outcome == "success":
                    stats["success"] += 1
                else:
                    stats["fail"] += 1
        
        sequences = []
        for tool, stats in tool_stats.items():
            sequences.append({
                "tool": tool,
                "count": stats["count"],
                "success_count": stats["success"],
                "fail_count": stats["fail"],
                "avg_duration_ms": stats["duration"] / stats["count"] if stats["count"] > 0 else 0,
            })
        
        return sorted(sequences, key=lambda x: x["count"], reverse=True)
    
    def _analyze_failures(self, trace) -> Dict[str, Any]:
        """Failure tahlil."""
        failures = []
        
        for task_trace in trace.task_traces:
            if task_trace.final_outcome != "success":
                # Find failure point
                failed_at = None
                error_type = None
                
                for tc in task_trace.tool_calls:
                    if tc.outcome == "fail":
                        failed_at = tc.step_index
                        error_type = tc.error_type
                        break
                
                failures.append({
                    "task_id": task_trace.task_id,
                    "suite": task_trace.suite,
                    "difficulty": task_trace.difficulty,
                    "failed_at_step": failed_at,
                    "error_type": error_type,
                    "retries": task_trace.total_retries,
                    "replans": task_trace.total_replans,
                })
        
        # Group by error type
        error_groups = defaultdict(list)
        for f in failures:
            error_groups[f["error_type"]].append(f)
        
        return {
            "total_failures": len(failures),
            "by_error_type": {k: len(v) for k, v in error_groups.items()},
            "samples": failures[:10],
        }
    
    def _analyze_successes(self, trace) -> Dict[str, Any]:
        """Success tahlil."""
        successes = []
        
        for task_trace in trace.task_traces:
            if task_trace.final_outcome == "success":
                # Find key success markers
                first_tool = task_trace.tool_calls[0].tool_name if task_trace.tool_calls else ""
                total_tools = len(task_trace.tool_calls)
                total_retries = task_trace.total_retries
                
                successes.append({
                    "task_id": task_trace.task_id,
                    "suite": task_trace.suite,
                    "difficulty": task_trace.difficulty,
                    "first_tool": first_tool,
                    "total_tools": total_tools,
                    "retries": total_retries,
                    "duration_ms": task_trace.total_duration_ms,
                })
        
        return {
            "total_successes": len(successes),
            "avg_tools": sum(s["total_tools"] for s in successes) / len(successes) if successes else 0,
            "avg_retries": sum(s["retries"] for s in successes) / len(successes) if successes else 0,
            "first_tool_dist": self._count_field(successes, "first_tool"),
            "samples": successes[:10],
        }
    
    def _count_field(self, items: List[Dict], field: str) -> Dict[str, int]:
        """Field'ni hisoblash."""
        counts = defaultdict(int)
        for item in items:
            counts[item.get(field, "")] += 1
        return dict(counts)
    
    def compare_runs(self, run_id_1: str, run_id_2: str) -> Dict[str, Any]:
        """Ikki run'ni solishtirish."""
        run1 = self.trace_storage.load_run_trace(run_id_1) if self.trace_storage else None
        run2 = self.trace_storage.load_run_trace(run_id_2) if self.trace_storage else None
        
        if not run1 or not run2:
            return {"error": "One or both runs not found"}
        
        # Compare basic stats
        return {
            "run_1": {
                "id": run1.run_id,
                "passed": run1.passed_tasks,
                "failed": run1.failed_tasks,
                "total_cost": run1.total_cost_usd,
            },
            "run_2": {
                "id": run2.run_id,
                "passed": run2.passed_tasks,
                "failed": run2.failed_tasks,
                "total_cost": run2.total_cost_usd,
            },
            "delta": {
                "passed": run2.passed_tasks - run1.passed_tasks,
                "failed": run2.failed_tasks - run1.failed_tasks,
                "total_cost": run2.total_cost_usd - run1.total_cost_usd,
            },
        }


def create_run_explorer(trace_storage=None) -> RunExplorer:
    """RunExplorer yaratish."""
    return RunExplorer(trace_storage)
