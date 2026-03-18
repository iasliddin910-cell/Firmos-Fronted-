"""
Budget Manager - Task and Run Budget Enforcement
============================================

This module manages budgets for tasks, runs, and time periods:
- Token budget
- Dollar budget
- Wall-time budget
- Tool-call budget
- Parallel slot budget

Author: No1 World+ Autonomous System
"""

import asyncio
import time
import logging
import threading
from typing import Dict, List, Optional, Any, Callable, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from collections import defaultdict, deque
import json

logger = logging.getLogger(__name__)


# ==================== ENUMS ====================

class BudgetType(str, Enum):
    """Types of budgets"""
    TOKEN = "token"
    DOLLAR = "dollar"
    WALL_TIME = "wall_time"
    TOOL_CALL = "tool_call"
    PARALLEL_SLOT = "parallel_slot"


class BudgetScope(str, Enum):
    """Budget scope"""
    TASK = "task"
    RUN = "run"
    SESSION = "session"
    DAY = "day"


class BudgetStatus(str, Enum):
    """Budget status"""
    HEALTHY = "healthy"
    WARNING = "warning"
    EXHAUSTED = "exhausted"
    OVERRUN = "overrun"


# ==================== DATA CLASSES ====================

@dataclass
class BudgetLimit:
    """Budget limit configuration"""
    budget_type: BudgetType
    scope: BudgetScope
    limit: float
    soft_limit: float  # Warning threshold
    unit: str
    reset_period: Optional[str] = None  # "hourly", "daily", "never"


@dataclass
class BudgetUsage:
    """Current budget usage"""
    budget_type: BudgetType
    scope: str
    used: float
    limit: float
    remaining: float
    status: BudgetStatus
    percent_used: float
    started_at: datetime
    

@dataclass
class BudgetAllocation:
    """Allocation for a specific task"""
    task_id: str
    token_budget: float
    dollar_budget: float
    time_budget_seconds: float
    tool_call_budget: int
    parallelism: int
    priority: int  # 1-10


@dataclass
class BudgetReport:
    """Comprehensive budget report"""
    timestamp: datetime
    
    # Overall status
    overall_status: BudgetStatus
    total_spent: float
    total_budget: float
    utilization_percent: float
    
    # Per-type breakdown
    token_usage: Optional[BudgetUsage]
    dollar_usage: Optional[BudgetUsage]
    time_usage: Optional[BudgetUsage]
    tool_call_usage: Optional[BudgetUsage]
    parallelism_usage: Optional[BudgetUsage]
    
    # Projections
    projected_exhaustion: Optional[datetime]
    burn_rate: float
    
    # Warnings
    active_warnings: List[str]
    
    # Recommendations
    recommendations: List[str]


# ==================== BUDGET TRACKER ====================

class BudgetTracker:
    """Tracks usage for a specific budget type"""
    
    def __init__(self, budget_type: BudgetType, limit: float, soft_limit: float):
        self._type = budget_type
        self._limit = limit
        self._soft_limit = soft_limit
        self._lock = threading.Lock()
        self._used = 0.0
        self._started_at = datetime.now()
        self._usage_history: deque = deque(maxlen=100)
    
    def consume(self, amount: float) -> bool:
        """Consume budget, returns True if within limits"""
        with self._lock:
            if self._used + amount > self._limit:
                return False
            self._used += amount
            self._usage_history.append({
                "timestamp": datetime.now(),
                "amount": amount,
                "total": self._used
            })
            return True
    
    def get_usage(self) -> BudgetUsage:
        """Get current usage"""
        with self._lock:
            remaining = self._limit - self._used
            percent = (self._used / self._limit * 100) if self._limit > 0 else 0
            
            status = BudgetStatus.HEALTHY
            if remaining <= 0:
                status = BudgetStatus.EXHAUSTED
            elif percent >= 100:
                status = BudgetStatus.OVERRUN
            elif percent >= self._soft_limit:
                status = BudgetStatus.WARNING
            
            return BudgetUsage(
                budget_type=self._type,
                scope="current",
                used=self._used,
                limit=self._limit,
                remaining=remaining,
                status=status,
                percent_used=percent,
                started_at=self._started_at
            )
    
    def reset(self):
        """Reset budget"""
        with self._lock:
            self._used = 0.0
            self._started_at = datetime.now()
            self._usage_history.clear()
    
    @property
    def limit(self) -> float:
        return self._limit
    
    @limit.setter
    def limit(self, value: float):
        self._limit = value
    
    @property
    def soft_limit(self) -> float:
        return self._soft_limit
    
    @soft_limit.setter
    def soft_limit(self, value: float):
        self._soft_limit = value


# ==================== BUDGET MANAGER ====================

class BudgetManager:
    """
    Main budget management system.
    
    Features:
    - Multiple budget types (token, dollar, time, tool-call, parallelism)
    - Scope-based budgets (task, run, session, day)
    - Soft and hard limits
    - Automatic enforcement
    - Projection and burn rate calculation
    - Callback notifications
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self._config = config or {}
        
        # Budget trackers
        self._trackers: Dict[BudgetType, BudgetTracker] = {}
        self._scope_budgets: Dict[str, Dict[BudgetType, BudgetTracker]] = defaultdict(dict)
        
        # Default limits from config
        self._defaults = {
            BudgetType.TOKEN: self._config.get("default_token_budget", 100000),
            BudgetType.DOLLAR: self._config.get("default_dollar_budget", 10.0),
            BudgetType.WALL_TIME: self._config.get("default_time_budget", 3600),
            BudgetType.TOOL_CALL: self._config.get("default_tool_call_budget", 100),
            BudgetType.PARALLEL_SLOT: self._config.get("default_parallelism", 10)
        }
        
        self._soft_limit_pct = self._config.get("soft_limit_percent", 80)
        
        # Callbacks
        self._on_warning: Optional[Callable] = None
        self._on_exhausted: Optional[Callable] = None
        self._on_overrun: Optional[Callable] = None
    
    def set_callbacks(self,
                     on_warning: Optional[Callable] = None,
                     on_exhausted: Optional[Callable] = None,
                     on_overrun: Optional[Callable] = None):
        """Set callback functions"""
        self._on_warning = on_warning
        self._on_exhausted = on_exhausted
        self._on_overrun = on_overrun
    
    # ==================== BUDGET SETUP ====================
    
    def set_global_budget(self, budget_type: BudgetType, limit: float,
                         soft_limit: Optional[float] = None):
        """Set global budget for a type"""
        soft = soft_limit or (limit * self._soft_limit_pct / 100)
        
        if budget_type in self._trackers:
            self._trackers[budget_type].limit = limit
            self._trackers[budget_type].soft_limit = soft
        else:
            self._trackers[budget_type] = BudgetTracker(budget_type, limit, soft)
        
        logger.info(f"Set {budget_type.value} budget: {limit} (soft: {soft})")
    
    def set_scope_budget(self, scope: str, budget_type: BudgetType, limit: float,
                        soft_limit: Optional[float] = None):
        """Set budget for a specific scope (task, run, etc.)"""
        soft = soft_limit or (limit * self._soft_limit_pct / 100)
        
        if budget_type in self._scope_budgets[scope]:
            self._scope_budgets[scope][budget_type].limit = limit
            self._scope_budgets[scope][budget_type].soft_limit = soft
        else:
            self._scope_budgets[scope][budget_type] = BudgetTracker(budget_type, limit, soft)
    
    def get_or_create_tracker(self, budget_type: BudgetType, 
                             scope: Optional[str] = None) -> BudgetTracker:
        """Get or create a budget tracker"""
        if scope and scope in self._scope_budgets:
            if budget_type in self._scope_budgets[scope]:
                return self._scope_budgets[scope][budget_type]
        
        if budget_type not in self._trackers:
            default_limit = self._defaults.get(budget_type, 1000)
            soft = default_limit * self._soft_limit_pct / 100
            self._trackers[budget_type] = BudgetTracker(budget_type, default_limit, soft)
        
        return self._trackers[budget_type]
    
    # ==================== BUDGET CONSUMPTION ====================
    
    def consume(self, budget_type: BudgetType, amount: float, 
               scope: Optional[str] = None) -> bool:
        """Consume budget, returns True if within limits"""
        tracker = self.get_or_create_tracker(budget_type, scope)
        
        success = tracker.consume(amount)
        
        if not success:
            usage = tracker.get_usage()
            
            if usage.status == BudgetStatus.EXHAUSTED:
                if self._on_exhausted:
                    self._on_exhausted(budget_type, scope, usage)
            elif usage.status == BudgetStatus.OVERRUN:
                if self._on_overrun:
                    self._on_overrun(budget_type, scope, usage)
        
        return success
    
    def try_consume(self, budget_type: BudgetType, amount: float,
                   scope: Optional[str] = None) -> bool:
        """Try to consume budget without triggering callbacks"""
        tracker = self.get_or_create_tracker(budget_type, scope)
        return tracker.consume(amount)
    
    def check_available(self, budget_type: BudgetType, amount: float,
                       scope: Optional[str] = None) -> bool:
        """Check if amount is available"""
        tracker = self.get_or_create_tracker(budget_type, scope)
        usage = tracker.get_usage()
        return usage.remaining >= amount
    
    # ==================== TASK BUDGET ALLOCATION ====================
    
    def allocate_task_budget(self, task_id: str, task_value: float,
                           task_difficulty: str, urgency: int) -> BudgetAllocation:
        """Allocate budget for a task based on its characteristics"""
        
        # Base budgets
        token_budget = 50000
        dollar_budget = 5.0
        time_budget = 1800  # 30 minutes
        tool_call_budget = 50
        parallelism = 1
        
        # Adjust based on task value
        if task_value > 1000:
            token_budget *= 2
            dollar_budget *= 2
            time_budget *= 2
            parallelism = min(3, parallelism + 1)
        
        # Adjust based on difficulty
        difficulty_multipliers = {
            "easy": 0.5,
            "medium": 1.0,
            "hard": 2.0,
            "expert": 3.0
        }
        mult = difficulty_multipliers.get(task_difficulty, 1.0)
        
        token_budget *= mult
        dollar_budget *= mult
        time_budget *= mult
        tool_call_budget *= int(mult)
        
        # Adjust based on urgency (1-10)
        if urgency >= 8:
            time_budget *= 0.5  # More urgent = less time
            parallelism = min(5, parallelism + 2)
        
        # Priority for scheduling
        priority = min(10, max(1, int(task_value / 100 + urgency / 2)))
        
        return BudgetAllocation(
            task_id=task_id,
            token_budget=token_budget,
            dollar_budget=dollar_budget,
            time_budget_seconds=time_budget,
            tool_call_budget=tool_call_budget,
            parallelism=parallelism,
            priority=priority
        )
    
    # ==================== QUERIES ====================
    
    def get_usage(self, budget_type: Optional[BudgetType] = None,
                 scope: Optional[str] = None) -> Dict:
        """Get budget usage"""
        if budget_type:
            tracker = self.get_or_create_tracker(budget_type, scope)
            return tracker.get_usage().__dict__
        
        # Get all usages
        result = {}
        
        for bt in BudgetType:
            tracker = self.get_or_create_tracker(bt, scope)
            result[bt.value] = tracker.get_usage().__dict__
        
        return result
    
    def get_report(self) -> BudgetReport:
        """Get comprehensive budget report"""
        
        usages = {}
        total_spent = 0
        total_budget = 0
        
        for budget_type in BudgetType:
            tracker = self.get_or_create_tracker(budget_type)
            usage = tracker.get_usage()
            usages[budget_type.value] = usage
            
            # Add to totals (convert all to dollar-equivalent)
            if budget_type == BudgetType.DOLLAR:
                total_spent += usage.used
                total_budget += usage.limit
            elif budget_type == BudgetType.TOKEN:
                # Approximate: 1000 tokens = $0.01
                total_spent += usage.used / 1000 * 0.01
                total_budget += usage.limit / 1000 * 0.01
            elif budget_type == BudgetType.WALL_TIME:
                # Time doesn't add to cost directly
                pass
            elif budget_type == BudgetType.TOOL_CALL:
                # Approximate: 1 tool call = $0.001
                total_spent += usage.used * 0.001
                total_budget += usage.limit * 0.001
        
        utilization = (total_spent / total_budget * 100) if total_budget > 0 else 0
        
        # Determine overall status
        statuses = [u.status for u in usages.values()]
        
        if BudgetStatus.OVERRUN in statuses:
            overall = BudgetStatus.OVERRUN
        elif BudgetStatus.EXHAUSTED in statuses:
            overall = BudgetStatus.EXHAUSTED
        elif BudgetStatus.WARNING in statuses:
            overall = BudgetStatus.WARNING
        else:
            overall = BudgetStatus.HEALTHY
        
        # Generate warnings
        warnings = []
        if overall == BudgetStatus.WARNING:
            warnings.append("Budget usage above soft limit")
        elif overall == BudgetStatus.EXHAUSTED:
            warnings.append("Budget exhausted - new tasks may be rejected")
        elif overall == BudgetStatus.OVERRUN:
            warnings.append("Budget overrun - immediate action required")
        
        # Calculate burn rate (spend per minute)
        tracker = self.get_or_create_tracker(BudgetType.DOLLAR)
        usage = tracker.get_usage()
        
        elapsed = (datetime.now() - usage.started_at).total_seconds() / 60
        burn_rate = usage.used / elapsed if elapsed > 0 else 0
        
        return BudgetReport(
            timestamp=datetime.now(),
            overall_status=overall,
            total_spent=total_spent,
            total_budget=total_budget,
            utilization_percent=utilization,
            token_usage=usages.get(BudgetType.TOKEN.value),
            dollar_usage=usages.get(BudgetType.DOLLAR.value),
            time_usage=usages.get(BudgetType.WALL_TIME.value),
            tool_call_usage=usages.get(BudgetType.TOOL_CALL.value),
            parallelism_usage=usages.get(BudgetType.PARALLEL_SLOT.value),
            projected_exhaustion=None,  # Would calculate based on burn rate
            burn_rate=burn_rate,
            active_warnings=warnings,
            recommendations=self._generate_recommendations(overall, usages)
        )
    
    def _generate_recommendations(self, status: BudgetStatus, 
                                usages: Dict) -> List[str]:
        """Generate recommendations"""
        recs = []
        
        if status == BudgetStatus.OVERRUN:
            recs.append("CRITICAL: Stop non-essential tasks immediately")
            recs.append("Consider scaling down parallelism")
        
        elif status == BudgetStatus.EXHAUSTED:
            recs.append("Review task allocation strategy")
            recs.append("Consider using cheaper models for simple tasks")
        
        elif status == BudgetStatus.WARNING:
            recs.append("Monitor budget closely")
            recs.append("Consider preemptive optimization")
        
        else:
            recs.append("Budget usage is healthy")
        
        return recs
    
    # ==================== RESET ====================
    
    def reset(self, budget_type: Optional[BudgetType] = None,
             scope: Optional[str] = None):
        """Reset budgets"""
        if budget_type:
            tracker = self.get_or_create_tracker(budget_type, scope)
            tracker.reset()
        elif scope and scope in self._scope_budgets:
            for tracker in self._scope_budgets[scope].values():
                tracker.reset()
        else:
            for tracker in self._trackers.values():
                tracker.reset()
            for scope_budgets in self._scope_budgets.values():
                for tracker in scope_budgets.values():
                    tracker.reset()
        
        logger.info(f"Budgets reset: type={budget_type}, scope={scope}")
    
    def reset_scope(self, scope: str):
        """Reset all budgets for a scope"""
        if scope in self._scope_budgets:
            for tracker in self._scope_budgets[scope].values():
                tracker.reset()


# ==================== FACTORY ====================

def create_budget_manager(config: Optional[Dict] = None) -> BudgetManager:
    """Factory function to create budget manager"""
    return BudgetManager(config=config)
