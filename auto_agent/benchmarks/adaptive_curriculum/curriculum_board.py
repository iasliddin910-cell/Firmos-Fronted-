"""
CurriculumBoard - Task Lifecycle Management Module

Bu modul tasklarni turli holatlarda boshqaradi:
- rising frontier tasks
- unresolved hard clusters
- newly generated candidates
- graduated stable tasks
- retired tasks

Policy 4: Near-frontier zone benchmarkning eng qimmat qismi.
"""

from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import time
import json


class TaskState(Enum):
    """Task lifecycle states"""
    CANDIDATE = "candidate"           # Newly generated, not validated
    VALIDATING = "validating"         # Undergoing validation
    RISING = "rising"                 # Rising frontier task
    STABLE = "stable"                 # Stable benchmark task
    GRADUATING = "graduating"         # Moving to stable
    RETIRING = "retiring"             # About to be retired
    RETIRED = "retired"               # Archived/retired task
    ESCALATING = "escalating"         # Being made harder


class TaskBoard(Enum):
    """Task board categories"""
    FRONTIER_RISING = "frontier_rising"
    UNRESOLVED_HARD = "unresolved_hard"
    NEW_CANDIDATES = "new_candidates"
    STABLE_BENCHMARK = "stable_benchmark"
    RETIRED_ARCHIVE = "retired_archive"


@dataclass
class TaskEntry:
    """An entry in the curriculum board"""
    task_id: str
    state: TaskState
    board: TaskBoard
    difficulty: float
    solve_rate: float
    diagnostic_value: float
    source: str
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    last_evaluated: Optional[float] = None
    evaluation_count: int = 0
    pass_count: int = 0
    fail_count: int = 0
    weight: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BoardStats:
    """Statistics for a board"""
    board: TaskBoard
    task_count: int
    avg_difficulty: float
    avg_solve_rate: float
    avg_diagnostic_value: float
    total_weight: float


class CurriculumBoard:
    """
    Manages task lifecycle and board organization.
    
    Bu modul:
    1. Tasklarni turli boardlarda joylashtiradi
    2. Tasklarni bir holatdan boshqasiga o'tkazadi
    3. Board statistikasini hisoblaydi
    4. Growth frontni ko'rsatadi
    """
    
    # Thresholds
    STABLE_SOLVE_RATE_MIN = 0.75
    STABLE_SOLVE_RATE_MAX = 0.95
    RETIRE_SOLVE_RATE = 0.90
    RISING_DIAGNOSTIC_MIN = 0.4
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.tasks: Dict[str, TaskEntry] = {}
        self.board_tasks: Dict[TaskBoard, Set[str]] = {
            board: set() for board in TaskBoard
        }
        
    def add_task(
        self,
        task_id: str,
        difficulty: float,
        source: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> TaskEntry:
        """Add a new task to the candidate board"""
        entry = TaskEntry(
            task_id=task_id,
            state=TaskState.CANDIDATE,
            board=TaskBoard.NEW_CANDIDATES,
            difficulty=difficulty,
            solve_rate=0.0,
            diagnostic_value=metadata.get('diagnostic_value', 0.5) if metadata else 0.5,
            source=source,
            metadata=metadata or {}
        )
        
        self.tasks[task_id] = entry
        self.board_tasks[TaskBoard.NEW_CANDIDATES].add(task_id)
        
        return entry
    
    def update_task_metrics(
        self,
        task_id: str,
        passed: bool,
        solve_rate: float,
        diagnostic_value: Optional[float] = None
    ) -> None:
        """Update task metrics after evaluation"""
        if task_id not in self.tasks:
            return
        
        task = self.tasks[task_id]
        task.last_evaluated = time.time()
        task.evaluation_count += 1
        
        if passed:
            task.pass_count += 1
        else:
            task.fail_count += 1
        
        task.solve_rate = solve_rate
        
        if diagnostic_value is not None:
            task.diagnostic_value = diagnostic_value
        
        task.updated_at = time.time()
        
        # Auto-transition based on metrics
        self._check_auto_transition(task)
    
    def _check_auto_transition(self, task: TaskEntry) -> None:
        """Check if task should automatically transition states"""
        # Candidate -> Rising (high diagnostic value)
        if task.state == TaskState.CANDIDATE:
            if task.diagnostic_value >= self.RISING_DIAGNOSTIC_MIN:
                self.transition_task(task.task_id, TaskState.RISING, TaskBoard.FRONTIER_RISING)
        
        # Rising -> Stable (consistent high solve rate)
        elif task.state == TaskState.RISING:
            if task.solve_rate >= self.STABLE_SOLVE_RATE_MIN:
                if task.evaluation_count >= 5:
                    self.transition_task(task.task_id, TaskState.STABLE, TaskBoard.STABLE_BENCHMARK)
        
        # Any -> Retiring (very high solve rate = saturated)
        elif task.solve_rate >= self.RETIRE_SOLVE_RATE and task.state not in [TaskState.RETIRED, TaskState.RETIRING]:
            if task.evaluation_count >= 10:
                self.transition_task(task.task_id, TaskState.RETIRING, TaskBoard.RETIRED_ARCHIVE)
    
    def transition_task(
        self,
        task_id: str,
        new_state: TaskState,
        new_board: TaskBoard
    ) -> bool:
        """Manually transition a task to a new state"""
        if task_id not in self.tasks:
            return False
        
        task = self.tasks[task_id]
        
        # Remove from old board
        old_board = task.board
        if task_id in self.board_tasks[old_board]:
            self.board_tasks[old_board].remove(task_id)
        
        # Update state and board
        task.state = new_state
        task.board = new_board
        task.updated_at = time.time()
        
        # Add to new board
        self.board_tasks[new_board].add(task_id)
        
        return True
    
    def escalate_task(
        self,
        task_id: str,
        target_difficulty: float
    ) -> bool:
        """Escalate a task to harder variant"""
        if task_id not in self.tasks:
            return False
        
        task = self.tasks[task_id]
        
        # Create harder variant (in practice, would call TaskMutator)
        new_task_id = f"{task_id}_harder"
        
        # Add new harder task
        self.add_task(
            task_id=new_task_id,
            difficulty=target_difficulty,
            source=f"escalated_from_{task_id}",
            metadata={
                "parent_task": task_id,
                "escalation_type": "difficulty_increase"
            }
        )
        
        # Mark original as escalating
        self.transition_task(task_id, TaskState.ESCALATING, TaskBoard.FRONTIER_RISING)
        
        return True
    
    def get_board_stats(self, board: TaskBoard) -> BoardStats:
        """Get statistics for a specific board"""
        task_ids = self.board_tasks[board]
        
        if not task_ids:
            return BoardStats(
                board=board,
                task_count=0,
                avg_difficulty=0.0,
                avg_solve_rate=0.0,
                avg_diagnostic_value=0.0,
                total_weight=0.0
            )
        
        tasks = [self.tasks[tid] for tid in task_ids if tid in self.tasks]
        
        return BoardStats(
            board=board,
            task_count=len(tasks),
            avg_difficulty=sum(t.difficulty for t in tasks) / len(tasks),
            avg_solve_rate=sum(t.solve_rate for t in tasks) / len(tasks),
            avg_diagnostic_value=sum(t.diagnostic_value for t in tasks) / len(tasks),
            total_weight=sum(t.weight for t in tasks)
        )
    
    def get_growth_front(self) -> List[TaskEntry]:
        """Get the current growth front (rising + unresolved hard tasks)"""
        front_tasks = []
        
        # Get rising frontier tasks
        for task_id in self.board_tasks[TaskBoard.FRONTIER_RISING]:
            if task_id in self.tasks:
                front_tasks.append(self.tasks[task_id])
        
        # Get unresolved hard tasks
        for task_id in self.board_tasks[TaskBoard.UNRESOLVED_HARD]:
            if task_id in self.tasks:
                front_tasks.append(self.tasks[task_id])
        
        # Sort by diagnostic value
        front_tasks.sort(key=lambda t: t.diagnostic_value, reverse=True)
        
        return front_tasks
    
    def get_stable_benchmark(self) -> List[TaskEntry]:
        """Get all stable benchmark tasks"""
        return [
            self.tasks[tid]
            for tid in self.board_tasks[TaskBoard.STABLE_BENCHMARK]
            if tid in self.tasks
        ]
    
    def get_tasks_for_evaluation(
        self,
        board: Optional[TaskBoard] = None,
        limit: int = 20
    ) -> List[TaskEntry]:
        """Get tasks ready for evaluation"""
        if board is None:
            # Get from all active boards
            active_boards = [
                TaskBoard.FRONTIER_RISING,
                TaskBoard.NEW_CANDIDATES,
                TaskBoard.UNRESOLVED_HARD
            ]
        else:
            active_boards = [board]
        
        tasks = []
        for b in active_boards:
            for task_id in self.board_tasks[b]:
                if task_id in self.tasks:
                    tasks.append(self.tasks[task_id])
        
        # Sort by priority (lower solve rate = higher priority for learning)
        tasks.sort(key=lambda t: (t.solve_rate, -t.diagnostic_value))
        
        return tasks[:limit]
    
    def export_board_state(self) -> Dict[str, Any]:
        """Export current board state"""
        return {
            "boards": {
                board.value: {
                    "task_count": len(task_ids),
                    "task_ids": list(task_ids)
                }
                for board, task_ids in self.board_tasks.items()
            },
            "stats": {
                board.value: {
                    "task_count": stats.task_count,
                    "avg_difficulty": stats.avg_difficulty,
                    "avg_solve_rate": stats.avg_solve_rate,
                    "avg_diagnostic_value": stats.avg_diagnostic_value
                }
                for board in TaskBoard
                if (stats := self.get_board_stats(board)).task_count > 0
            },
            "growth_front_count": len(self.get_growth_front()),
            "stable_benchmark_count": len(self.get_stable_benchmark())
        }
    
    def save_state(self, filepath: str) -> None:
        """Save board state to file"""
        state = {
            "tasks": {
                tid: {
                    "task_id": t.task_id,
                    "state": t.state.value,
                    "board": t.board.value,
                    "difficulty": t.difficulty,
                    "solve_rate": t.solve_rate,
                    "diagnostic_value": t.diagnostic_value,
                    "source": t.source,
                    "created_at": t.created_at,
                    "updated_at": t.updated_at,
                    "last_evaluated": t.last_evaluated,
                    "evaluation_count": t.evaluation_count,
                    "pass_count": t.pass_count,
                    "fail_count": t.fail_count,
                    "weight": t.weight,
                    "metadata": t.metadata
                }
                for tid, t in self.tasks.items()
            }
        }
        
        with open(filepath, 'w') as f:
            json.dump(state, f, indent=2)
    
    def load_state(self, filepath: str) -> None:
        """Load board state from file"""
        with open(filepath, 'r') as f:
            state = json.load(f)
        
        self.tasks = {}
        self.board_tasks = {board: set() for board in TaskBoard}
        
        for tid, tdata in state.get('tasks', {}).items():
            task = TaskEntry(
                task_id=tdata['task_id'],
                state=TaskState(tdata['state']),
                board=TaskBoard(tdata['board']),
                difficulty=tdata['difficulty'],
                solve_rate=tdata['solve_rate'],
                diagnostic_value=tdata['diagnostic_value'],
                source=tdata['source'],
                created_at=tdata['created_at'],
                updated_at=tdata['updated_at'],
                last_evaluated=tdata.get('last_evaluated'),
                evaluation_count=tdata['evaluation_count'],
                pass_count=tdata['pass_count'],
                fail_count=tdata['fail_count'],
                weight=tdata['weight'],
                metadata=tdata.get('metadata', {})
            )
            self.tasks[tid] = task
            self.board_tasks[task.board].add(tid)


__all__ = [
    'CurriculumBoard',
    'TaskState',
    'TaskBoard',
    'TaskEntry',
    'BoardStats'
]
