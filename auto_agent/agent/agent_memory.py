"""
OmniAgent X - Agent State Memory System
=======================================
Extended memory for autonomous agents

This provides:
- Task-state memory: Current task, progress, checkpoints
- Run history: Past executions with outcomes
- Tool reliability: Success/failure rates per tool
- Failed patch memory: What patches didn't work
- File change memory: Track modifications
- Active objective memory: Current goals
- Procedural memory: Learned procedures
"""
import json
import logging
import time
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from collections import defaultdict
from pathlib import Path
import hashlib

logger = logging.getLogger(__name__)


# ==================== DATA CLASSES ====================

@dataclass
class TaskState:
    """State of current task"""
    task_id: str
    description: str
    status: str  # pending, running, paused, completed, failed
    progress: float  # 0.0 to 1.0
    checkpoint: str  # Last checkpoint
    created_at: float
    updated_at: float
    metadata: Dict = field(default_factory=dict)


@dataclass
class RunRecord:
    """Record of a single run"""
    run_id: str
    start_time: float
    end_time: Optional[float]
    task: str
    outcome: str  # success, failed, partial
    duration: float
    steps: int
    tools_used: List[str]
    errors: List[str]
    artifacts: List[str]


@dataclass
class ToolReliability:
    """Tool reliability metrics"""
    tool_name: str
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    avg_duration: float = 0.0
    last_used: float = 0.0
    failure_patterns: List[str] = field(default_factory=list)
    
    @property
    def success_rate(self) -> float:
        if self.total_calls == 0:
            return 0.0
        return self.successful_calls / self.total_calls


@dataclass
class FailedPatch:
    """Record of failed patch attempts"""
    patch_id: str
    original_error: str
    attempted_fix: str
    why_failed: str
    timestamp: float
    file_path: str


@dataclass
class FileChange:
    """Record of file modification"""
    file_path: str
    change_type: str  # created, modified, deleted
    timestamp: float
    hash_before: str
    hash_after: str
    backup_available: bool


@dataclass
class Objective:
    """Active objective"""
    objective_id: str
    description: str
    priority: int  # 1-5
    deadline: Optional[float]
    status: str  # active, paused, completed, abandoned
    subobjectives: List[str] = field(default_factory=list)
    created_at: float
    updated_at: float


@dataclass
class ProceduralMemory:
    """Learned procedures"""
    procedure_id: str
    name: str
    steps: List[Dict]
    success_count: int = 0
    failure_count: int = 0
    avg_duration: float = 0.0
    last_used: float = 0.0
    tags: List[str] = field(default_factory=list)


# ==================== AGENT STATE MEMORY ====================

class AgentStateMemory:
    """
    Comprehensive memory for autonomous agents
    
    Extends knowledge memory with:
    - Task state tracking
    - Execution history
    - Tool reliability
    - Failed patch memory
    - File change tracking
    - Active objectives
    - Learned procedures
    """
    
    def __init__(self, storage_dir: str = "data/agent_memory"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # Task state memory
        self.current_tasks: Dict[str, TaskState] = {}
        
        # Run history
        self.run_history: List[RunRecord] = []
        self.max_runs = 1000
        
        # Tool reliability
        self.tool_reliability: Dict[str, ToolReliability] = {}
        
        # Failed patches
        self.failed_patches: List[FailedPatch] = []
        self.max_failed_patches = 500
        
        # File changes
        self.file_changes: List[FileChange] = []
        
        # Active objectives
        self.objectives: Dict[str, Objective] = {}
        
        # Procedural memory
        self.procedures: Dict[str, ProceduralMemory] = {}
        
        # Load from disk if exists
        self._load()
        
        logger.info("🧠 Agent State Memory initialized")
    
    # ==================== TASK STATE ====================
    
    def start_task(self, task_id: str, description: str, metadata: Dict = None) -> TaskState:
        """Start a new task"""
        task = TaskState(
            task_id=task_id,
            description=description,
            status="running",
            progress=0.0,
            checkpoint="",
            created_at=time.time(),
            updated_at=time.time(),
            metadata=metadata or {}
        )
        
        self.current_tasks[task_id] = task
        self._save()
        
        logger.info(f"📋 Task started: {task_id}")
        return task
    
    def update_task_progress(self, task_id: str, progress: float, checkpoint: str = ""):
        """Update task progress"""
        if task_id in self.current_tasks:
            self.current_tasks[task_id].progress = progress
            if checkpoint:
                self.current_tasks[task_id].checkpoint = checkpoint
            self.current_tasks[task_id].updated_at = time.time()
            self._save()
    
    def complete_task(self, task_id: str, status: str = "completed"):
        """Mark task as complete"""
        if task_id in self.current_tasks:
            self.current_tasks[task_id].status = status
            self.current_tasks[task_id].progress = 1.0
            self.current_tasks[task_id].updated_at = time.time()
            self._save()
    
    def get_current_task(self, task_id: str = None) -> Optional[TaskState]:
        """Get current task state"""
        if task_id:
            return self.current_tasks.get(task_id)
        
        # Return first running task
        for task in self.current_tasks.values():
            if task.status == "running":
                return task
        
        return None
    
    # ==================== RUN HISTORY ====================
    
    def start_run(self, task: str) -> str:
        """Start a new run"""
        run_id = f"run_{int(time.time())}_{hashlib.md5(task.encode()).hexdigest()[:6]}"
        
        run = RunRecord(
            run_id=run_id,
            start_time=time.time(),
            end_time=None,
            task=task,
            outcome="",
            duration=0.0,
            steps=0,
            tools_used=[],
            errors=[],
            artifacts=[]
        )
        
        self.run_history.append(run)
        
        # Trim if needed
        if len(self.run_history) > self.max_runs:
            self.run_history = self.run_history[-self.max_runs:]
        
        return run_id
    
    def end_run(self, run_id: str, outcome: str, steps: int = 0):
        """End a run"""
        for run in reversed(self.run_history):
            if run.run_id == run_id:
                run.end_time = time.time()
                run.duration = run.end_time - run.start_time
                run.outcome = outcome
                run.steps = steps
                break
        
        self._save()
    
    def record_tool_use(self, run_id: str, tool_name: str):
        """Record tool usage in current run"""
        for run in reversed(self.run_history):
            if run.run_id == run_id:
                if tool_name not in run.tools_used:
                    run.tools_used.append(tool_name)
                break
    
    def record_error(self, run_id: str, error: str):
        """Record error in current run"""
        for run in reversed(self.run_history):
            if run.run_id == run_id:
                run.errors.append(error)
                break
    
    def get_run_history(self, limit: int = 100) -> List[Dict]:
        """Get recent run history"""
        runs = self.run_history[-limit:]
        return [asdict(r) for r in runs]
    
    def get_run_stats(self) -> Dict:
        """Get run statistics"""
        total = len(self.run_history)
        if total == 0:
            return {"total": 0, "success": 0, "failed": 0, "success_rate": 0.0}
        
        success = sum(1 for r in self.run_history if r.outcome == "success")
        failed = sum(1 for r in self.run_history if r.outcome == "failed")
        
        return {
            "total": total,
            "success": success,
            "failed": failed,
            "success_rate": success / total if total > 0 else 0.0,
            "avg_duration": sum(r.duration for r in self.run_history) / total
        }
    
    # ==================== TOOL RELIABILITY ====================
    
    def record_tool_call(self, tool_name: str, success: bool, duration: float):
        """Record tool call result"""
        if tool_name not in self.tool_reliability:
            self.tool_reliability[tool_name] = ToolReliability(tool_name=tool_name)
        
        reliability = self.tool_reliability[tool_name]
        reliability.total_calls += 1
        
        if success:
            reliability.successful_calls += 1
        else:
            reliability.failed_calls += 1
        
        # Update average duration
        reliability.avg_duration = (
            (reliability.avg_duration * (reliability.total_calls - 1) + duration)
            / reliability.total_calls
        )
        
        reliability.last_used = time.time()
        
        self._save()
    
    def get_tool_reliability(self, tool_name: str = None) -> Dict:
        """Get tool reliability metrics"""
        if tool_name:
            if tool_name in self.tool_reliability:
                return asdict(self.tool_reliability[tool_name])
            return {}
        
        return {
            name: asdict(rel) 
            for name, rel in self.tool_reliability.items()
        }
    
    def get_reliable_tools(self, min_success_rate: float = 0.8) -> List[str]:
        """Get tools with high reliability"""
        reliable = []
        for name, rel in self.tool_reliability.items():
            if rel.success_rate >= min_success_rate:
                reliable.append(name)
        return reliable
    
    def get_unreliable_tools(self, max_success_rate: float = 0.5) -> List[str]:
        """Get tools with low reliability"""
        unreliable = []
        for name, rel in self.tool_reliability.items():
            if rel.total_calls >= 5 and rel.success_rate <= max_success_rate:
                unreliable.append(name)
        return unreliable
    
    # ==================== FAILED PATCHES ====================
    
    def record_failed_patch(self, original_error: str, attempted_fix: str, 
                          why_failed: str, file_path: str):
        """Record a failed patch attempt"""
        patch = FailedPatch(
            patch_id=f"patch_{int(time.time())}",
            original_error=original_error,
            attempted_fix=attempted_fix,
            why_failed=why_failed,
            timestamp=time.time(),
            file_path=file_path
        )
        
        self.failed_patches.append(patch)
        
        # Trim if needed
        if len(self.failed_patches) > self.max_failed_patches:
            self.failed_patches = self.failed_patches[-self.max_failed_patches:]
        
        self._save()
    
    def get_failed_patches(self, file_path: str = None, limit: int = 50) -> List[Dict]:
        """Get failed patches"""
        patches = self.failed_patches
        
        if file_path:
            patches = [p for p in patches if p.file_path == file_path]
        
        patches = patches[-limit:]
        return [asdict(p) for p in patches]
    
    def should_try_patch(self, error_pattern: str, file_path: str) -> bool:
        """Check if we should try a patch based on history"""
        # Get recent patches for this file
        recent = [p for p in self.failed_patches 
                 if p.file_path == file_path 
                 and time.time() - p.timestamp < 3600]  # Last hour
        
        # If we've failed too many times, don't try again
        if len(recent) >= 3:
            return False
        
        return True
    
    # ==================== FILE CHANGES ====================
    
    def record_file_change(self, file_path: str, change_type: str,
                          hash_before: str, hash_after: str):
        """Record file change"""
        change = FileChange(
            file_path=file_path,
            change_type=change_type,
            timestamp=time.time(),
            hash_before=hash_before,
            hash_after=hash_after,
            backup_available=True
        )
        
        self.file_changes.append(change)
        self._save()
    
    def get_file_changes(self, file_path: str = None, limit: int = 100) -> List[Dict]:
        """Get file changes"""
        changes = self.file_changes
        
        if file_path:
            changes = [c for c in changes if c.file_path == file_path]
        
        changes = changes[-limit:]
        return [asdict(c) for c in changes]
    
    # ==================== OBJECTIVES ====================
    
    def set_objective(self, description: str, priority: int = 3,
                     deadline: float = None, subobjectives: List[str] = None) -> str:
        """Set a new objective"""
        objective_id = f"obj_{int(time.time())}"
        
        obj = Objective(
            objective_id=objective_id,
            description=description,
            priority=priority,
            deadline=deadline,
            status="active",
            subobjectives=subobjectives or [],
            created_at=time.time(),
            updated_at=time.time()
        )
        
        self.objectives[objective_id] = obj
        self._save()
        
        return objective_id
    
    def update_objective_status(self, objective_id: str, status: str):
        """Update objective status"""
        if objective_id in self.objectives:
            self.objectives[objective_id].status = status
            self.objectives[objective_id].updated_at = time.time()
            self._save()
    
    def get_active_objectives(self) -> List[Dict]:
        """Get all active objectives"""
        active = [o for o in self.objectives.values() if o.status == "active"]
        active.sort(key=lambda x: x.priority)
        return [asdict(o) for o in active]
    
    # ==================== PROCEDURAL MEMORY ====================
    
    def learn_procedure(self, name: str, steps: List[Dict], success: bool, 
                       duration: float, tags: List[str] = None):
        """Learn a new procedure"""
        # Check if procedure exists
        procedure_id = hashlib.md5(name.encode()).hexdigest()[:8]
        
        if procedure_id in self.procedures:
            proc = self.procedures[procedure_id]
            proc.last_used = time.time()
            
            if success:
                proc.success_count += 1
            else:
                proc.failure_count += 1
            
            # Update average duration
            total = proc.success_count + proc.failure_count
            proc.avg_duration = (
                (proc.avg_duration * (total - 1) + duration) / total
            )
        else:
            proc = ProceduralMemory(
                procedure_id=procedure_id,
                name=name,
                steps=steps,
                success_count=1 if success else 0,
                failure_count=0 if success else 1,
                avg_duration=duration,
                last_used=time.time(),
                tags=tags or []
            )
            self.procedures[procedure_id] = proc
        
        self._save()
    
    def get_best_procedure(self, tags: List[str] = None) -> Optional[ProceduralMemory]:
        """Get most successful procedure"""
        candidates = list(self.procedures.values())
        
        if tags:
            candidates = [p for p in candidates if any(t in p.tags for t in tags)]
        
        if not candidates:
            return None
        
        # Sort by success rate
        candidates.sort(
            key=lambda p: p.success_count / (p.success_count + p.failure_count + 1),
            reverse=True
        )
        
        return candidates[0]
    
    # ==================== PERSISTENCE ====================
    
    def _save(self):
        """Save memory to disk"""
        try:
            data = {
                "current_tasks": {k: asdict(v) for k, v in self.current_tasks.items()},
                "run_history": [asdict(r) for r in self.run_history],
                "tool_reliability": {k: asdict(v) for k, v in self.tool_reliability.items()},
                "failed_patches": [asdict(p) for p in self.failed_patches],
                "file_changes": [asdict(c) for c in self.file_changes],
                "objectives": {k: asdict(v) for k, v in self.objectives.items()},
                "procedures": {k: asdict(v) for k, v in self.procedures.items()}
            }
            
            with open(self.storage_dir / "agent_state.json", "w") as f:
                json.dump(data, f, indent=2)
        
        except Exception as e:
            logger.error(f"Failed to save agent state: {e}")
    
    def _load(self):
        """Load memory from disk"""
        try:
            path = self.storage_dir / "agent_state.json"
            if not path.exists():
                return
            
            with open(path, "r") as f:
                data = json.load(f)
            
            # Restore data classes
            self.current_tasks = {
                k: TaskState(**v) for k, v in data.get("current_tasks", {}).items()
            }
            
            self.run_history = [
                RunRecord(**r) for r in data.get("run_history", [])
            ]
            
            self.tool_reliability = {
                k: ToolReliability(**v) for k, v in data.get("tool_reliability", {}).items()
            }
            
            self.failed_patches = [
                FailedPatch(**p) for p in data.get("failed_patches", [])
            ]
            
            self.file_changes = [
                FileChange(**c) for c in data.get("file_changes", [])
            ]
            
            self.objectives = {
                k: Objective(**v) for k, v in data.get("objectives", {}).items()
            }
            
            self.procedures = {
                k: ProceduralMemory(**v) for k, v in data.get("procedures", {}).items()
            }
            
            logger.info("🧠 Agent State Memory loaded from disk")
        
        except Exception as e:
            logger.error(f"Failed to load agent state: {e}")
    
    def get_stats(self) -> Dict:
        """Get memory statistics"""
        return {
            "current_tasks": len(self.current_tasks),
            "run_history": len(self.run_history),
            "tools_tracked": len(self.tool_reliability),
            "failed_patches": len(self.failed_patches),
            "file_changes": len(self.file_changes),
            "objectives": len(self.objectives),
            "procedures": len(self.procedures),
            "run_stats": self.get_run_stats()
        }


# ==================== FACTORY ====================

def get_agent_memory(storage_dir: str = "data/agent_memory") -> AgentStateMemory:
    """Get agent state memory instance"""
    return AgentStateMemory(storage_dir)
