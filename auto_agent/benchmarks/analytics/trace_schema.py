"""
TraceSchema - Standard Trace Format
==================================

Benchmark trace uchun standart schema.

Har run, har task, har tool call bir xil schema bilan saqlanadi.

Definition of Done:
1. Har benchmark run standart trace bilan saqlanadi.
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Any, Optional, Set
from enum import Enum
from datetime import datetime
import json
import os


# ==================== PHASE TYPES ====================

class Phase(str, Enum):
    """Task execution phases."""
    PLAN = "plan"
    EXPLORE = "explore"
    TOOL_SELECT = "tool_select"
    TOOL_EXECUTE = "tool_execute"
    VERIFY = "verify"
    PATCH = "patch"
    RECOVERY = "recovery"
    REPLAN = "replan"
    COMPLETE = "complete"
    FAIL = "fail"


class Outcome(str, Enum):
    """Step outcomes."""
    SUCCESS = "success"
    FAIL = "fail"
    RETRY = "retry"
    REPLAN = "replan"
    TIMEOUT = "timeout"
    ERROR = "error"


class ErrorType(str, Enum):
    """Error types."""
    NONE = "none"
    TOOL_ERROR = "tool_error"
    VERIFIER_MISMATCH = "verifier_mismatch"
    FILE_NOT_FOUND = "file_not_found"
    SYNTAX_ERROR = "syntax_error"
    RUNTIME_ERROR = "runtime_error"
    TIMEOUT_ERROR = "timeout_error"
    PERMISSION_ERROR = "permission_error"
    RECOVERY_DEAD_END = "recovery_dead_end"
    WRONG_FILE = "wrong_file"
    MISSING_CONTEXT = "missing_context"


# ==================== TRACE ENTITIES ====================

@dataclass
class ToolCall:
    """Single tool call."""
    step_index: int
    timestamp: str
    phase: str
    
    # Tool info
    tool_name: str
    tool_args: Dict[str, Any] = field(default_factory=dict)
    tool_args_hash: str = ""
    
    # Execution
    outcome: str = Outcome.SUCCESS.value
    duration_ms: int = 0
    
    # Tokens
    tokens_in: int = 0
    tokens_out: int = 0
    
    # File touches
    files_read: List[str] = field(default_factory=list)
    files_written: List[str] = field(default_factory=list)
    
    # Retry info
    is_retry: bool = False
    retry_count: int = 0
    
    # Error
    error_type: str = ErrorType.NONE.value
    error_message: str = ""
    
    # Evidence
    evidence_refs: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TaskTrace:
    """Single task trace."""
    run_id: str
    task_id: str
    suite: str
    difficulty: str
    
    # Timing
    started_at: str
    completed_at: Optional[str] = None
    total_duration_ms: int = 0
    
    # Steps
    tool_calls: List[ToolCall] = field(default_factory=list)
    
    # Outcomes
    final_outcome: str = ""
    final_score: float = 0.0
    
    # Retry info
    total_retries: int = 0
    total_replans: int = 0
    
    # Patch
    patch_diff: str = ""
    patch_files: List[str] = field(default_factory=list)
    
    # Verifier
    verifier_calls: int = 0
    verifier_outcomes: List[str] = field(default_factory=list)
    
    # Checkpoints
    checkpoint_ids: List[str] = field(default_factory=list)
    
    # Metadata
    seeds: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "task_id": self.task_id,
            "suite": self.suite,
            "difficulty": self.difficulty,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "total_duration_ms": self.total_duration_ms,
            "tool_calls": [tc.to_dict() for tc in self.tool_calls],
            "final_outcome": self.final_outcome,
            "final_score": self.final_score,
            "total_retries": self.total_retries,
            "total_replans": self.total_replans,
            "patch_diff": self.patch_diff,
            "patch_files": self.patch_files,
            "verifier_calls": self.verifier_calls,
            "verifier_outcomes": self.verifier_outcomes,
            "checkpoint_ids": self.checkpoint_ids,
            "seeds": self.seeds,
            "tags": self.tags,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TaskTrace':
        trace = cls(
            run_id=data["run_id"],
            task_id=data["task_id"],
            suite=data["suite"],
            difficulty=data["difficulty"],
            started_at=data["started_at"],
            completed_at=data.get("completed_at"),
            total_duration_ms=data.get("total_duration_ms", 0),
            final_outcome=data.get("final_outcome", ""),
            final_score=data.get("final_score", 0.0),
            total_retries=data.get("total_retries", 0),
            total_replans=data.get("total_replans", 0),
            patch_diff=data.get("patch_diff", ""),
            patch_files=data.get("patch_files", []),
            verifier_calls=data.get("verifier_calls", 0),
            verifier_outcomes=data.get("verifier_outcomes", []),
            checkpoint_ids=data.get("checkpoint_ids", []),
            seeds=data.get("seeds", []),
            tags=data.get("tags", []),
        )
        for tc_data in data.get("tool_calls", []):
            trace.tool_calls.append(ToolCall(**tc_data))
        return trace


@dataclass
class RunTrace:
    """Complete run trace."""
    run_id: str
    agent_version: str
    config: Dict[str, Any] = field(default_factory=dict)
    
    # Timing
    started_at: str
    completed_at: Optional[str] = None
    
    # Task traces
    task_traces: List[TaskTrace] = field(default_factory=list)
    
    # Summary
    total_tasks: int = 0
    passed_tasks: int = 0
    failed_tasks: int = 0
    
    # Metrics
    total_cost_usd: float = 0.0
    total_tokens: int = 0
    total_duration_ms: int = 0
    
    # Metadata
    environment: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "agent_version": self.agent_version,
            "config": self.config,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "task_traces": [tt.to_dict() for tt in self.task_traces],
            "total_tasks": self.total_tasks,
            "passed_tasks": self.passed_tasks,
            "failed_tasks": self.failed_tasks,
            "total_cost_usd": self.total_cost_usd,
            "total_tokens": self.total_tokens,
            "total_duration_ms": self.total_duration_ms,
            "environment": self.environment,
            "tags": self.tags,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RunTrace':
        run = cls(
            run_id=data["run_id"],
            agent_version=data["agent_version"],
            config=data.get("config", {}),
            started_at=data["started_at"],
            completed_at=data.get("completed_at"),
            total_tasks=data.get("total_tasks", 0),
            passed_tasks=data.get("passed_tasks", 0),
            failed_tasks=data.get("failed_tasks", 0),
            total_cost_usd=data.get("total_cost_usd", 0.0),
            total_tokens=data.get("total_tokens", 0),
            total_duration_ms=data.get("total_duration_ms", 0),
            environment=data.get("environment", {}),
            tags=data.get("tags", []),
        )
        for tt_data in data.get("task_traces", []):
            run.task_traces.append(TaskTrace.from_dict(tt_data))
        return run
    
    def add_task_trace(self, trace: TaskTrace) -> None:
        self.task_traces.append(trace)
        self.total_tasks += 1
        if trace.final_outcome == "success":
            self.passed_tasks += 1
        else:
            self.failed_tasks += 1


# ==================== TRACE STORAGE ====================

class TraceStorage:
    """Trace'arni saqlash va yuklash."""
    
    def __init__(self, storage_path: str = None):
        self.storage_path = storage_path or "benchmarks/traces"
        os.makedirs(self.storage_path, exist_ok=True)
    
    def save_run_trace(self, trace: RunTrace) -> str:
        """Run trace'ni saqlash."""
        filename = f"{trace.run_id}.json"
        path = os.path.join(self.storage_path, filename)
        
        with open(path, 'w') as f:
            json.dump(trace.to_dict(), f, indent=2)
        
        return path
    
    def load_run_trace(self, run_id: str) -> Optional[RunTrace]:
        """Run trace'ni yuklash."""
        path = os.path.join(self.storage_path, f"{run_id}.json")
        
        if not os.path.exists(path):
            return None
        
        with open(path, 'r') as f:
            data = json.load(f)
        
        return RunTrace.from_dict(data)
    
    def list_run_ids(self) -> List[str]:
        """Barcha run ID'lar."""
        files = [f.replace(".json", "") for f in os.listdir(self.storage_path) if f.endswith(".json")]
        return sorted(files)


# ==================== FACTORY ====================

def create_task_trace(
    run_id: str,
    task_id: str,
    suite: str,
    difficulty: str,
) -> TaskTrace:
    """TaskTrace yaratish."""
    return TaskTrace(
        run_id=run_id,
        task_id=task_id,
        suite=suite,
        difficulty=difficulty,
        started_at=datetime.utcnow().isoformat(),
    )


def create_run_trace(
    run_id: str,
    agent_version: str,
    config: Dict[str, Any] = None,
) -> RunTrace:
    """RunTrace yaratish."""
    return RunTrace(
        run_id=run_id,
        agent_version=agent_version,
        config=config or {},
        started_at=datetime.utcnow().isoformat(),
    )


def create_trace_storage(storage_path: str = None) -> TraceStorage:
    """TraceStorage yaratish."""
    return TraceStorage(storage_path)
