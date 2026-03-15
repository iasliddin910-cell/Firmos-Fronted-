"""
OmniAgent X - Telemetry & Efficiency System
=========================================
Comprehensive telemetry collection for benchmark runs.

This module provides:
- TelemetryCollector: Action-level telemetry
- CostEstimator: Token and cost estimation
- ThrashDetector: Pattern-based thrash detection
- EfficiencyScorer: Multi-dimensional efficiency scoring

Core Policy:
    Task success is NOT enough.
    HOW the task was completed matters just as much.
"""
import time
import json
import hashlib
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


# ==================== TELEMETRY SCHEMA ====================

@dataclass
class StepRecord:
    """Single step/action record"""
    step_number: int
    timestamp: str
    action_type: str  # "tool_call", "think", "observe", "verify"
    tool_name: Optional[str]
    input_summary: str
    output_summary: str
    duration_ms: float
    success: bool
    error: Optional[str] = None
    retry_count: int = 0
    context_tokens: int = 0


@dataclass
class FileAccess:
    """File access record"""
    path: str
    operation: str  # "read", "write", "edit"
    size_bytes: int
    timestamp: str
    success: bool


@dataclass
class ToolCall:
    """Tool call record"""
    tool_name: str
    arguments: Dict[str, Any]
    result_summary: str
    success: bool
    duration_ms: float
    error: Optional[str] = None
    retry_count: int = 0


@dataclass
class RecoveryEvent:
    """Recovery event record"""
    event_type: str  # "crash", "timeout", "error", "interruption"
    timestamp: str
    recovery_strategy: str
    successful: bool
    recovery_attempts: int
    recovery_time_ms: float


# ==================== TELEMETRY COLLECTOR ====================

class TelemetryCollector:
    """
    Collects comprehensive telemetry for every benchmark run.
    
    Captures:
    - Timing metrics (wall time, active time, idle time)
    - Token usage (estimated)
    - Tool call counts and failures
    - File access patterns
    - Retry behavior
    - Recovery events
    """
    
    def __init__(self):
        # Timing
        self.start_time = time.time()
        self.active_time = 0.0
        self.idle_time = 0.0
        self.last_active_time = self.start_time
        
        # Steps
        self.steps: List[StepRecord] = []
        self.current_step = 0
        
        # Tools
        self.tool_calls: List[ToolCall] = []
        self.tool_failures: int = 0
        self.tool_retries: int = 0
        
        # Files
        self.file_accesses: List[FileAccess] = []
        self.unique_files_touched: Set[str] = set()
        
        # Commands
        self.command_count: int = 0
        self.browser_actions: int = 0
        
        # Progress tracking
        self.first_progress_time: Optional[float] = None
        self.progress_milestones: List[Dict] = []
        
        # Recovery
        self.recovery_events: List[RecoveryEvent] = []
        
        # Errors
        self.errors_encountered: List[Dict] = []
        
        # Planning
        self.replan_count: int = 0
        self.plan_changes: List[Dict] = []
        
        # Context
        self.context_refresh_count: int = 0
        
        logger.info("📊 TelemetryCollector initialized")
    
    def start_step(self, action_type: str, tool_name: Optional[str] = None) -> int:
        """Start a new step"""
        self.current_step += 1
        self.last_active_time = time.time()
        
        if self.first_progress_time is None:
            self.first_progress_time = time.time()
        
        return self.current_step
    
    def end_step(self, step_number: int, action_type: str, tool_name: Optional[str],
                input_summary: str, output_summary: str, duration_ms: float,
                success: bool, error: Optional[str] = None,
                retry_count: int = 0, context_tokens: int = 0):
        """End a step and record it"""
        step = StepRecord(
            step_number=step_number,
            timestamp=datetime.now().isoformat(),
            action_type=action_type,
            tool_name=tool_name,
            input_summary=input_summary[:200],  # Truncate for storage
            output_summary=output_summary[:200],
            duration_ms=duration_ms,
            success=success,
            error=error,
            retry_count=retry_count,
            context_tokens=context_tokens
        )
        
        self.steps.append(step)
        
        # Update timing
        self.active_time += duration_ms / 1000
    
    def record_tool_call(self, tool_name: str, arguments: Dict,
                       result_summary: str, success: bool,
                       duration_ms: float, error: Optional[str] = None,
                       retry_count: int = 0):
        """Record a tool call"""
        call = ToolCall(
            tool_name=tool_name,
            arguments=arguments,
            result_summary=result_summary[:200],
            success=success,
            duration_ms=duration_ms,
            error=error,
            retry_count=retry_count
        )
        
        self.tool_calls.append(call)
        
        if not success:
            self.tool_failures += 1
        
        if retry_count > 0:
            self.tool_retries += retry_count
    
    def record_file_access(self, path: str, operation: str,
                         size_bytes: int, success: bool):
        """Record file access"""
        access = FileAccess(
            path=path,
            operation=operation,
            size_bytes=size_bytes,
            timestamp=datetime.now().isoformat(),
            success=success
        )
        
        self.file_accesses.append(access)
        
        if success and operation in ("write", "edit"):
            self.unique_files_touched.add(path)
    
    def record_command(self):
        """Record command execution"""
        self.command_count += 1
    
    def record_browser_action(self):
        """Record browser action"""
        self.browser_actions += 1
    
    def record_recovery(self, event_type: str, recovery_strategy: str,
                      successful: bool, attempts: int, recovery_time_ms: float):
        """Record recovery event"""
        event = RecoveryEvent(
            event_type=event_type,
            timestamp=datetime.now().isoformat(),
            recovery_strategy=recovery_strategy,
            successful=successful,
            recovery_attempts=attempts,
            recovery_time_ms=recovery_time_ms
        )
        
        self.recovery_events.append(event)
    
    def record_error(self, error_type: str, error_message: str,
                    context: Dict):
        """Record an error"""
        self.errors_encountered.append({
            "type": error_type,
            "message": error_message,
            "context": context,
            "timestamp": datetime.now().isoformat()
        })
    
    def record_replan(self, reason: str):
        """Record a replanning event"""
        self.replan_count += 1
        self.plan_changes.append({
            "reason": reason,
            "timestamp": datetime.now().isoformat()
        })
    
    def record_context_refresh(self):
        """Record context refresh"""
        self.context_refresh_count += 1
    
    def record_progress_milestone(self, milestone: str, details: Dict):
        """Record a progress milestone"""
        self.progress_milestones.append({
            "milestone": milestone,
            "details": details,
            "timestamp": datetime.now().isoformat(),
            "time_since_start": time.time() - self.start_time
        })
    
    def get_summary(self) -> Dict:
        """Get telemetry summary"""
        end_time = time.time()
        total_time = end_time - self.start_time
        self.idle_time = total_time - self.active_time
        
        # Calculate derived metrics
        total_tool_calls = len(self.tool_calls)
        successful_tool_calls = sum(1 for c in self.tool_calls if c.success)
        
        unique_file_reads = len(set(
            f.path for f in self.file_accesses 
            if f.operation == "read"
        ))
        unique_file_writes = len(set(
            f.path for f in self.file_accesses 
            if f.operation in ("write", "edit")
        ))
        
        first_progress_latency = (
            self.first_progress_time - self.start_time 
            if self.first_progress_time else None
        )
        
        return {
            # Timing
            "wall_time_sec": total_time,
            "active_execution_sec": self.active_time,
            "idle_wait_sec": self.idle_time,
            
            # Steps
            "total_steps": len(self.steps),
            
            # Tools
            "tool_calls_total": total_tool_calls,
            "tool_calls_succeeded": successful_tool_calls,
            "tool_calls_failed": self.tool_failures,
            "tool_calls_retried": self.tool_retries,
            "retry_rate": self.tool_retries / total_tool_calls if total_tool_calls > 0 else 0,
            
            # Files
            "files_read_unique": unique_file_reads,
            "files_written_unique": unique_file_writes,
            "files_touched_total": len(self.unique_files_touched),
            "file_accesses_total": len(self.file_accesses),
            
            # Commands
            "command_count": self.command_count,
            "browser_actions": self.browser_actions,
            
            # Recovery
            "recovery_events": len(self.recovery_events),
            "successful_recoveries": sum(1 for r in self.recovery_events if r.successful),
            
            # Errors
            "errors_encountered": len(self.errors_encountered),
            
            # Planning
            "replan_count": self.replan_count,
            "context_refresh_count": self.context_refresh_count,
            
            # Progress
            "first_progress_latency_sec": first_progress_latency,
            "progress_milestones": len(self.progress_milestones),
        }
    
    def to_dict(self) -> Dict:
        """Export full telemetry"""
        return {
            "summary": self.get_summary(),
            "steps": [
                {
                    "step_number": s.step_number,
                    "timestamp": s.timestamp,
                    "action_type": s.action_type,
                    "tool_name": s.tool_name,
                    "duration_ms": s.duration_ms,
                    "success": s.success,
                    "error": s.error,
                    "retry_count": s.retry_count
                }
                for s in self.steps
            ],
            "tool_calls": [
                {
                    "tool_name": c.tool_name,
                    "success": c.success,
                    "duration_ms": c.duration_ms,
                    "error": c.error,
                    "retry_count": c.retry_count
                }
                for c in self.tool_calls
            ],
            "recovery_events": [
                {
                    "event_type": r.event_type,
                    "successful": r.successful,
                    "recovery_attempts": r.recovery_attempts,
                    "recovery_time_ms": r.recovery_time_ms
                }
                for r in self.recovery_events
            ],
            "errors": self.errors_encountered
        }


# ==================== COST ESTIMATOR ====================

class CostEstimator:
    """
    Estimates cost for benchmark runs.
    
    Accounts for:
    - Token usage (input + output)
    - API calls
    - Compute time
    - Tool execution time
    """
    
    # Pricing (example values - should be configurable)
    TOKEN_PRICING = {
        "gpt-4": {"input": 0.03, "output": 0.06},  # per 1K tokens
        "gpt-4-turbo": {"input": 0.01, "output": 0.03},
        "gpt-3.5-turbo": {"input": 0.001, "output": 0.002},
    }
    
    def __init__(self, model_name: str = "gpt-4"):
        self.model_name = model_name
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_api_calls = 0
        
        logger.info(f"💰 CostEstimator initialized for {model_name}")
    
    def add_api_call(self, input_tokens: int, output_tokens: int):
        """Record an API call"""
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        self.total_api_calls += 1
    
    def estimate_cost(self) -> Dict[str, float]:
        """Estimate total cost"""
        pricing = self.TOKEN_PRICING.get(self.model_name, 
                                        self.TOKEN_PRICING["gpt-4"])
        
        input_cost = (self.total_input_tokens / 1000) * pricing["input"]
        output_cost = (self.total_output_tokens / 1000) * pricing["output"]
        
        return {
            "model": self.model_name,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_api_calls": self.total_api_calls,
            "input_cost_usd": input_cost,
            "output_cost_usd": output_cost,
            "total_cost_usd": input_cost + output_cost,
            "avg_tokens_per_call": (
                (self.total_input_tokens + self.total_output_tokens) / self.total_api_calls
                if self.total_api_calls > 0 else 0
            )
        }
    
    def get_efficiency_metrics(self, task_success: bool) -> Dict[str, float]:
        """Get cost efficiency metrics"""
        cost = self.estimate_cost()
        
        if not task_success:
            return {
                "cost_per_success": 0,
                "tokens_per_success": 0,
                "cost_per_step": 0
            }
        
        return {
            "cost_per_success": cost["total_cost_usd"],
            "tokens_per_success": (
                self.total_input_tokens + self.total_output_tokens
            ),
            "cost_per_step": cost["total_cost_usd"] / max(1, self.total_api_calls)
        }


# ==================== THRASH DETECTOR ====================

class ThrashDetector:
    """
    Detects thrashing patterns in agent behavior.
    
    Thrash indicators:
    - Duplicate file reads (5+ times same file)
    - Duplicate tool calls
    - Repeated errors (3+ times same error)
    - Frequent replanning
    - No progress loops (10+ steps without progress)
    - Repeated patch/revert cycles
    """
    
    def __init__(self):
        # Track patterns
        self.file_read_counts: Dict[str, int] = defaultdict(int)
        self.tool_call_patterns: Dict[str, int] = defaultdict(int)
        self.error_patterns: Dict[str, int] = defaultdict(int)
        
        # Thrash events
        self.thrash_events: List[Dict] = []
        
        # Thresholds
        self.DUPLICATE_FILE_READ_THRESHOLD = 5
        self.DUPLICATE_TOOL_CALL_THRESHOLD = 5
        self.REPEATED_ERROR_THRESHOLD = 3
        self.NO_PROGRESS_STEP_THRESHOLD = 10
        
        logger.info("🔍 ThrashDetector initialized")
    
    def analyze_step(self, step: StepRecord):
        """Analyze a step for thrash patterns"""
        # Track file reads
        if step.tool_name in ("read_file", "file_editor"):
            # Extract file path from input
            file_path = step.input_summary.split("path:")[-1][:100] if "path:" in step.input_summary else "unknown"
            self.file_read_counts[file_path] += 1
            
            if self.file_read_counts[file_path] >= self.DUPLICATE_FILE_READ_THRESHOLD:
                self.thrash_events.append({
                    "type": "duplicate_file_read",
                    "path": file_path,
                    "count": self.file_read_counts[file_path],
                    "step": step.step_number,
                    "severity": "high"
                })
        
        # Track tool call patterns
        if step.tool_name:
            tool_key = f"{step.tool_name}:{step.input_summary[:50]}"
            self.tool_call_patterns[tool_key] += 1
            
            if self.tool_call_patterns[tool_key] >= self.DUPLICATE_TOOL_CALL_THRESHOLD:
                self.thrash_events.append({
                    "type": "duplicate_tool_call",
                    "tool": step.tool_name,
                    "count": self.tool_call_patterns[tool_key],
                    "step": step.step_number,
                    "severity": "medium"
                })
        
        # Track errors
        if step.error:
            error_key = step.error[:100]
            self.error_patterns[error_key] += 1
            
            if self.error_patterns[error_key] >= self.REPEATED_ERROR_THRESHOLD:
                self.thrash_events.append({
                    "type": "repeated_error",
                    "error": error_key,
                    "count": self.error_patterns[error_key],
                    "step": step.step_number,
                    "severity": "high"
                })
    
    def analyze_progress(self, steps: List[StepRecord]) -> List[Dict]:
        """Analyze for no-progress loops"""
        consecutive_failures = 0
        
        for step in steps:
            if not step.success:
                consecutive_failures += 1
                
                if consecutive_failures >= self.NO_PROGRESS_STEP_THRESHOLD:
                    self.thrash_events.append({
                        "type": "no_progress_loop",
                        "steps": consecutive_failures,
                        "step": step.step_number,
                        "severity": "high"
                    })
            else:
                consecutive_failures = 0
        
        return self.thrash_events
    
    def get_thrash_score(self) -> float:
        """
        Calculate thrash score (0-1, higher is worse).
        """
        if not self.thrash_events:
            return 0.0
        
        # Weight by severity
        severity_weights = {
            "high": 1.0,
            "medium": 0.5,
            "low": 0.25
        }
        
        weighted_score = sum(
            severity_weights.get(e.get("severity", "low"), 0.25)
            for e in self.thrash_events
        )
        
        return min(1.0, weighted_score / 10)  # Normalize
    
    def get_report(self) -> Dict:
        """Get full thrash report"""
        return {
            "thrash_score": self.get_thrash_score(),
            "total_events": len(self.thrash_events),
            "events_by_type": {
                "duplicate_file_read": sum(1 for e in self.thrash_events if e["type"] == "duplicate_file_read"),
                "duplicate_tool_call": sum(1 for e in self.thrash_events if e["type"] == "duplicate_tool_call"),
                "repeated_error": sum(1 for e in self.thrash_events if e["type"] == "repeated_error"),
                "no_progress_loop": sum(1 for e in self.thrash_events if e["type"] == "no_progress_loop"),
            },
            "events": self.thrash_events
        }


# ==================== EFFICIENCY SCORER ====================

class EfficiencyScorer:
    """
    Computes multi-dimensional efficiency scores.
    
    Dimensions:
    - step_efficiency: Success per step
    - cost_efficiency: Success per token
    - latency_efficiency: Success per time
    - focus_efficiency: Minimal unnecessary work
    """
    
    def __init__(self):
        self.telemetry: Optional[TelemetryCollector] = None
        self.cost_estimator: Optional[CostEstimator] = None
        self.thrash_detector: Optional[ThrashDetector] = None
    
    def set_telemetry(self, telemetry: TelemetryCollector):
        """Set telemetry source"""
        self.telemetry = telemetry
    
    def set_cost_estimator(self, estimator: CostEstimator):
        """Set cost estimator"""
        self.cost_estimator = estimator
    
    def set_thrash_detector(self, detector: ThrashDetector):
        """Set thrash detector"""
        self.thrash_detector = detector
    
    def compute_scores(self, task_success: bool) -> Dict[str, float]:
        """
        Compute all efficiency scores.
        
        Returns:
            {
                "step_efficiency": 0-1,
                "cost_efficiency": 0-1,
                "latency_efficiency": 0-1,
                "focus_efficiency": 0-1,
                "total_efficiency": 0-1,
                "thrash_penalty": 0-1
            }
        """
        if not task_success:
            return {
                "step_efficiency": 0.0,
                "cost_efficiency": 0.0,
                "latency_efficiency": 0.0,
                "focus_efficiency": 0.0,
                "total_efficiency": 0.0,
                "thrash_penalty": 1.0
            }
        
        if not self.telemetry:
            return {"error": "No telemetry set"}
        
        summary = self.telemetry.get_summary()
        
        # Step efficiency: lower steps is better
        total_steps = max(1, summary["total_steps"])
        step_efficiency = min(1.0, 20 / total_steps)  # 20 steps = perfect, more = worse
        
        # Cost efficiency: fewer tokens is better
        if self.cost_estimator:
            cost_info = self.cost_estimator.estimate_cost()
            total_tokens = cost_info["total_input_tokens"] + cost_info["total_output_tokens"]
            cost_efficiency = min(1.0, 10000 / max(1, total_tokens))  # 10K tokens = perfect
        else:
            cost_efficiency = 0.5  # Unknown
        
        # Latency efficiency: faster is better
        wall_time = max(0.1, summary["wall_time_sec"])
        latency_efficiency = min(1.0, 60 / wall_time)  # 60 sec = perfect, more = worse
        
        # Focus efficiency: fewer unnecessary touches is better
        unique_files = max(1, summary["files_touched_total"])
        total_file_ops = max(1, summary["file_accesses_total"])
        file_ratio = unique_files / total_file_ops
        focus_efficiency = file_ratio  # Higher ratio = more focused
        
        # Thrash penalty
        thrash_penalty = 0.0
        if self.thrash_detector:
            thrash_penalty = self.thrash_detector.get_thrash_score()
        
        # Combined efficiency (weighted)
        total_efficiency = (
            0.25 * step_efficiency +
            0.25 * cost_efficiency +
            0.25 * latency_efficiency +
            0.25 * focus_efficiency
        )
        
        return {
            "step_efficiency": step_efficiency,
            "cost_efficiency": cost_efficiency,
            "latency_efficiency": latency_efficiency,
            "focus_efficiency": focus_efficiency,
            "total_efficiency": total_efficiency,
            "thrash_penalty": thrash_penalty,
            "effective_efficiency": max(0, total_efficiency - thrash_penalty * 0.5)
        }
    
    def get_final_task_score(self, capability_score: float, efficiency_score: float,
                           reliability_score: float = 1.0) -> Dict[str, float]:
        """
        Compute final task score with all dimensions.
        
        Formula:
        final = 0.60 * capability + 0.25 * efficiency + 0.15 * reliability
        """
        final_score = (
            0.60 * capability_score +
            0.25 * efficiency_score +
            0.15 * reliability_score
        )
        
        return {
            "capability_score": capability_score,
            "efficiency_score": efficiency_score,
            "reliability_score": reliability_score,
            "final_score": final_score,
            "dimensions": {
                "capability_weight": 0.60,
                "efficiency_weight": 0.25,
                "reliability_weight": 0.15
            }
        }


# ==================== RETRY BUDGET ====================

class RetryBudget:
    """
    Manages retry budgets for different failure types.
    
    Policies:
    - network_timeout: max 2 retries
    - file_lock: max 1 retry
    - invalid_schema: 0 retries
    - same_shell_error: max 1 retry
    """
    
    DEFAULT_BUDGETS = {
        "network_timeout": 2,
        "file_lock": 1,
        "permission_denied": 1,
        "invalid_schema": 0,
        "syntax_error": 0,
        "same_shell_error": 1,
        "tool_crash": 2,
        "unknown": 1
    }
    
    def __init__(self, custom_budgets: Optional[Dict[str, int]] = None):
        self.budgets = custom_budgets or self.DEFAULT_BUDGETS
        self.retry_counts: Dict[str, int] = {}
        
        logger.info("⏱️ RetryBudget initialized")
    
    def can_retry(self, error_type: str) -> bool:
        """Check if can retry this error type"""
        max_retries = self.budgets.get(error_type, self.budgets["unknown"])
        current_retries = self.retry_counts.get(error_type, 0)
        
        return current_retries < max_retries
    
    def record_retry(self, error_type: str) -> bool:
        """Record a retry attempt, returns True if allowed"""
        if self.can_retry(error_type):
            self.retry_counts[error_type] = self.retry_counts.get(error_type, 0) + 1
            return True
        return False
    
    def get_remaining(self, error_type: str) -> int:
        """Get remaining retries for error type"""
        max_retries = self.budgets.get(error_type, self.budgets["unknown"])
        current_retries = self.retry_counts.get(error_type, 0)
        return max(0, max_retries - current_retries)
    
    def should_stop_with_error(self, error_type: str) -> bool:
        """Check if should stop and report error"""
        return not self.can_retry(error_type)


# ==================== POLICY BUDGET MANAGER ====================

class PolicyBudgetManager:
    """
    Manages all budget policies for a run.
    """
    
    def __init__(self):
        self.retry_budget = RetryBudget()
        self.token_budget: Optional[int] = None
        self.step_budget: Optional[int] = None
        self.latency_budget_sec: Optional[float] = None
        
        # Per-task budgets (can be customized)
        self.task_budgets: Dict[str, Dict] = {}
        
        logger.info("📋 PolicyBudgetManager initialized")
    
    def set_task_budgets(self, task_id: str, budgets: Dict):
        """Set budgets for a specific task"""
        self.task_budgets[task_id] = budgets
    
    def check_token_budget(self, current_tokens: int) -> tuple[bool, str]:
        """Check if within token budget"""
        if self.token_budget and current_tokens > self.token_budget:
            return False, f"Token budget exceeded: {current_tokens} > {self.token_budget}"
        return True, "OK"
    
    def check_step_budget(self, current_steps: int) -> tuple[bool, str]:
        """Check if within step budget"""
        if self.step_budget and current_steps > self.step_budget:
            return False, f"Step budget exceeded: {current_steps} > {self.step_budget}"
        return True, "OK"
    
    def check_latency_budget(self, elapsed_sec: float) -> tuple[bool, str]:
        """Check if within latency budget"""
        if self.latency_budget_sec and elapsed_sec > self.latency_budget_sec:
            return False, f"Latency budget exceeded: {elapsed_sec:.1f}s > {self.latency_budget_sec}s"
        return True, "OK"


# ==================== FACTORY ====================

def create_telemetry_collector() -> TelemetryCollector:
    """Create a telemetry collector"""
    return TelemetryCollector()


def create_efficiency_scorer(telemetry: TelemetryCollector) -> EfficiencyScorer:
    """Create efficiency scorer with telemetry"""
    scorer = EfficiencyScorer()
    scorer.set_telemetry(telemetry)
    return scorer
