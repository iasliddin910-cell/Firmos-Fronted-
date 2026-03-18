"""
Queue Governor - Queue Management and Priority
==========================================

This module manages task queue with priorities:
- Urgent tasks
- High-value tasks
- Cheap quick wins
- Long expensive research
- Batchable tasks
- Can-wait tasks

Author: No1 World+ Autonomous System
"""

import asyncio
import logging
import threading
import time
from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from collections import defaultdict, deque
from queue import PriorityQueue
import heapq

logger = logging.getLogger(__name__)


# ==================== ENUMS ====================

class TaskPriority(str, Enum):
    """Task priority levels"""
    CRITICAL = "critical"       # P0
    URGENT = "urgent"          # P1
    HIGH = "high"              # P2
    NORMAL = "normal"          # P3
    LOW = "low"                # P4
    BATCH = "batch"            # P5
    DEFERRED = "deferred"      # P6


class TaskCategory(str, Enum):
    """Task categories for batching"""
    QUICK_WIN = "quick_win"           # Fast, cheap, high success
    HIGH_VALUE = "high_value"         # Important, worth more resources
    LONG_RUNNING = "long_running"     # Takes a lot of time
    RESEARCH = "research"             # Investigation type
    BATCHABLE = "batchable"           # Can be batched
    CAN_WAIT = "can_wait"             # Not time sensitive


# ==================== DATA CLASSES ====================

@dataclass
class QueuedTask:
    """A task in the queue"""
    task_id: str
    description: str
    task_type: str
    priority: TaskPriority
    category: TaskCategory
    
    # Estimates
    estimated_cost: float
    estimated_duration: float
    estimated_value: float
    
    # Metadata
    created_at: datetime
    deadline: Optional[datetime]
    dependencies: List[str]
    
    # Queue metadata
    enqueued_at: Optional[datetime] = None
    attempts: int = 0
    
    # For priority queue
    def __lt__(self, other):
        # Higher priority value = higher urgency
        return self._priority_value() > other._priority_value()
    
    def _priority_value(self) -> int:
        values = {
            TaskPriority.CRITICAL: 100,
            TaskPriority.URGENT: 80,
            TaskPriority.HIGH: 60,
            TaskPriority.NORMAL: 40,
            TaskPriority.LOW: 20,
            TaskPriority.BATCH: 10,
            TaskPriority.DEFERRED: 0
        }
        return values.get(self.priority, 40)


@dataclass
class QueueStats:
    """Queue statistics"""
    total_enqueued: int
    total_completed: int
    total_failed: int
    avg_wait_time: float
    avg_turnaround: float
    throughput_per_hour: float
    queue_depth: int
    oldes_task_age: float


@dataclass
class BatchGroup:
    """Group of batchable tasks"""
    batch_id: str
    tasks: List[QueuedTask]
    created_at: datetime
    ready_at: datetime


# ==================== QUEUE GOVERNOR ====================

class QueueGovernor:
    """
    Queue management and priority system.
    
    Features:
    - Priority-based scheduling
    - Category-based batching
    - Dependency management
    - Deadline tracking
    - Throughput optimization
    - Load balancing
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self._config = config or {}
        
        # Queue
        self._queue: List[QueuedTask] = []
        self._by_id: Dict[str, QueuedTask] = {}
        self._by_category: Dict[TaskCategory, List[QueuedTask]] = defaultdict(list)
        
        # Statistics
        self._completed: deque = deque(maxlen=1000)
        self._failed: deque = deque(maxlen=1000)
        
        # Configuration
        self._max_queue_size = self._config.get("max_queue_size", 1000)
        self._batch_size = self._config.get("batch_size", 10)
        self._batch_timeout = self._config.get("batch_timeout", 60)  # seconds
        
        # Callbacks
        self._on_queue_full: Optional[Callable] = None
        self._on_batch_ready: Optional[Callable] = None
    
    def set_callbacks(self,
                     on_queue_full: Optional[Callable] = None,
                     on_batch_ready: Optional[Callable] = None):
        """Set callback functions"""
        self._on_queue_full = on_queue_full
        self._on_batch_ready = on_batch_ready
    
    # ==================== ENQUEUE ====================
    
    def enqueue(self, task_id: str, description: str, task_type: str,
                estimated_cost: float = 1.0, estimated_duration: float = 60,
                estimated_value: float = 100, priority: Optional[TaskPriority] = None,
                deadline: Optional[datetime] = None, 
                dependencies: Optional[List[str]] = None) -> bool:
        """Add task to queue"""
        
        # Check if already in queue
        if task_id in self._by_id:
            logger.warning(f"Task {task_id} already in queue")
            return False
        
        # Check queue size
        if len(self._queue) >= self._max_queue_size:
            if self._on_queue_full:
                self._on_queue_full(len(self._queue))
            return False
        
        # Determine priority if not specified
        if priority is None:
            priority = self._determine_priority(estimated_value, estimated_cost, deadline)
        
        # Determine category
        category = self._determine_category(estimated_cost, estimated_duration, estimated_value)
        
        # Create task
        task = QueuedTask(
            task_id=task_id,
            description=description,
            task_type=task_type,
            priority=priority,
            category=category,
            estimated_cost=estimated_cost,
            estimated_duration=estimated_duration,
            estimated_value=estimated_value,
            created_at=datetime.now(),
            deadline=deadline,
            dependencies=dependencies or [],
            enqueued_at=datetime.now()
        )
        
        # Check dependencies
        if dependencies:
            for dep_id in dependencies:
                if dep_id not in self._by_id:
                    # Dependency not in queue - check if completed
                    if not any(t.task_id == dep_id for t in self._completed):
                        logger.warning(f"Dependency {dep_id} not satisfied for {task_id}")
                        return False
        
        # Add to queue
        heapq.heappush(self._queue, task)
        self._by_id[task_id] = task
        self._by_category[category].append(task)
        
        logger.info(f"Task {task_id} enqueued: priority={priority.value}, category={category.value}")
        return True
    
    def _determine_priority(self, value: float, cost: float, 
                          deadline: Optional[datetime]) -> TaskPriority:
        """Determine task priority"""
        
        # High value
        if value > 1000:
            return TaskPriority.CRITICAL
        
        # Has deadline
        if deadline:
            time_until_deadline = (deadline - datetime.now()).total_seconds()
            if time_until_deadline < 300:  # < 5 min
                return TaskPriority.URGENT
            elif time_until_deadline < 3600:  # < 1 hour
                return TaskPriority.HIGH
        
        # High value/cost ratio
        roi = value / max(cost, 0.01)
        if roi > 100:
            return TaskPriority.HIGH
        elif roi > 10:
            return TaskPriority.NORMAL
        
        return TaskPriority.NORMAL
    
    def _determine_category(self, cost: float, duration: float, 
                          value: float) -> TaskCategory:
        """Determine task category"""
        
        # Quick win: cheap, fast, high success probability
        if cost < 1 and duration < 300:
            return TaskCategory.QUICK_WIN
        
        # High value
        if value > 500:
            return TaskCategory.HIGH_VALUE
        
        # Long running
        if duration > 1800:  # > 30 min
            return TaskCategory.LONG_RUNNING
        
        # Research
        if "research" in str(value).lower():
            return TaskCategory.RESEARCH
        
        # Batchable
        if cost < 5:
            return TaskCategory.BATCHABLE
        
        return TaskCategory.CAN_WAIT
    
    # ==================== DEQUEUE ====================
    
    def dequeue(self, max_parallel: int = 1) -> List[QueuedTask]:
        """Get next tasks to execute"""
        
        ready_tasks = []
        
        while len(ready_tasks) < max_parallel and self._queue:
            task = heapq.heappop(self._queue)
            
            # Check if dependencies are met
            deps_met = all(
                dep_id in self._by_id and self._completed 
                for dep_id in task.dependencies
            )
            
            # Remove from category index
            if task in self._by_category[task.category]:
                self._by_category[task.category].remove(task)
            
            # Check if ready
            if deps_met:
                ready_tasks.append(task)
                del self._by_id[task.task_id]
            else:
                # Put back
                heapq.heappush(self._queue, task)
                break
        
        return ready_tasks
    
    def peek(self, count: int = 1) -> List[QueuedTask]:
        """Peek at next tasks without removing"""
        
        # Sort by priority
        sorted_queue = sorted(self._queue)
        return sorted_queue[:count]
    
    # ==================== COMPLETION ====================
    
    def complete(self, task_id: str, success: bool):
        """Mark task as completed"""
        
        task = None
        
        # Find in completed or by_id
        for t in list(self._completed) + list(self._by_id.values()):
            if t.task_id == task_id:
                task = t
                break
        
        if task:
            task.attempts += 1
            
            if success:
                task.enqueued_at = datetime.now()
                self._completed.append(task)
                
                # Remove from queue if still there
                if task_id in self._by_id:
                    del self._by_id[task_id]
                
                logger.info(f"Task {task_id} completed successfully")
            else:
                self._failed.append(task)
                logger.warning(f"Task {task_id} failed")
    
    # ==================== BATCHING ====================
    
    def get_batch(self, category: TaskCategory, 
                 max_size: Optional[int] = None) -> List[QueuedTask]:
        """Get batch of tasks from same category"""
        
        size = max_size or self._batch_size
        
        batch_tasks = []
        
        # Get tasks from category
        category_tasks = self._by_category.get(category, [])
        
        for task in category_tasks[:size]:
            if task in self._queue:
                batch_tasks.append(task)
                heapq.heappush(self._queue, task)
        
        return batch_tasks
    
    # ==================== QUERIES ====================
    
    def get_stats(self) -> QueueStats:
        """Get queue statistics"""
        
        total_enqueued = len(self._by_id) + len(self._completed) + len(self._failed)
        
        # Calculate wait times
        wait_times = []
        turnaround_times = []
        
        for task in list(self._completed)[-100:]:
            if task.enqueued_at:
                wait = (task.enqueued_at - task.created_at).total_seconds()
                turnaround = (datetime.now() - task.created_at).total_seconds()
                wait_times.append(wait)
                turnaround_times.append(turnaround)
        
        # Calculate throughput
        if turnaround_times:
            time_span = max(turnaround_times) if turnaround_times else 1
            throughput = len(turnaround_times) / (time_span / 3600) if time_span > 0 else 0
        else:
            throughput = 0
        
        # Oldest task
        oldest_age = 0
        if self._queue:
            oldest = min(self._queue, key=lambda t: t.created_at)
            oldest_age = (datetime.now() - oldest.created_at).total_seconds()
        
        return QueueStats(
            total_enqueued=total_enqueued,
            total_completed=len(self._completed),
            total_failed=len(self._failed),
            avg_wait_time=statistics.mean(wait_times) if wait_times else 0,
            avg_turnaround=statistics.mean(turnaround_times) if turnaround_times else 0,
            throughput_per_hour=throughput,
            queue_depth=len(self._queue),
            oldes_task_age=oldest_age
        )
    
    def get_next_task_info(self) -> Optional[Dict]:
        """Get info about next task"""
        
        if not self._queue:
            return None
        
        next_task = min(self._queue)
        
        return {
            "task_id": next_task.task_id,
            "priority": next_task.priority.value,
            "category": next_task.category.value,
            "estimated_cost": next_task.estimated_cost,
            "estimated_value": next_task.estimated_value,
            "age_seconds": (datetime.now() - next_task.created_at).total_seconds()
        }
    
    def get_queue_depth(self) -> int:
        """Get current queue depth"""
        return len(self._queue)
    
    def is_empty(self) -> bool:
        """Check if queue is empty"""
        return len(self._queue) == 0
    
    # ==================== MANAGEMENT ====================
    
    def remove(self, task_id: str) -> bool:
        """Remove task from queue"""
        
        if task_id not in self._by_id:
            return False
        
        task = self._by_id[task_id]
        
        # Remove from category
        if task in self._by_category[task.category]:
            self._by_category[task.category].remove(task)
        
        del self._by_id[task_id]
        
        # Rebuild queue
        self._queue = [t for t in self._queue if t.task_id != task_id]
        heapq.heapify(self._queue)
        
        return True
    
    def clear(self):
        """Clear queue"""
        self._queue.clear()
        self._by_id.clear()
        self._by_category.clear()
        
        logger.info("Queue cleared")


# ==================== FACTORY ====================

def create_queue_governor(config: Optional[Dict] = None) -> QueueGovernor:
    """Factory function to create queue governor"""
    return QueueGovernor(config=config)


# Need statistics
import statistics
