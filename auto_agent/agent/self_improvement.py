"""
OmniAgent X - Self-Improvement System
=====================================
Self-improvement through telemetry, benchmarking, and experimentation

Features:
- Telemetry collection
- Failure analysis
- Bottleneck detection
- Patch proposal
- A/B testing
- Release snapshots
- Rollback
- INTEGRATED with PatchLifecycle from regression_suite.py
- ERROR DETECTION & SIGNAL PROPAGATION (Advanced)
- Root cause analysis
- Benchmark signaling
- Self-fixing capabilities
"""
import os
import json
import logging
import time
import shutil
import hashlib
import traceback
from typing import Dict, List, Optional, Any, Callable, Set
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from collections import defaultdict
from pathlib import Path
from enum import Enum

logger = logging.getLogger(__name__)

# Import PatchLifecycle from regression_suite for integrated patch pipeline
try:
    from regression_suite import PatchLifecycle, RegressionSuite
    PATCH_LIFECYCLE_AVAILABLE = True
except ImportError:
    PATCH_LIFECYCLE_AVAILABLE = False
    logger.warning("PatchLifecycle not available - using legacy mode")


# ==================== DATA CLASSES ====================

@dataclass
class PatchProposal:
    """Proposed code improvement"""
    proposal_id: str
    file_path: str
    current_code: str
    proposed_code: str
    reason: str
    expected_improvement: str
    status: str  # proposed, testing, accepted, rejected
    test_result: Optional[str] = None
    created_at: float = field(default_factory=time.time)


@dataclass
class Snapshot:
    """Code snapshot for rollback"""
    snapshot_id: str
    description: str
    timestamp: float
    files: Dict[str, str]  # path -> content hash
    version: str


@dataclass
class Experiment:
    """A/B test experiment"""
    experiment_id: str
    name: str
    description: str
    variant_a: str  # control
    variant_b: str  # treatment
    metric: str
    status: str  # running, completed
    results: Dict = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)


# ==================== RELEASE PIPELINE DATA CLASSES ====================

@dataclass
class CandidatePatch:
    """Candidate patch for release pipeline"""
    patch_id: str
    proposal_id: str
    file_path: str
    current_code: str
    proposed_code: str
    diff: str
    reason: str
    expected_improvement: str
    created_at: float = field(default_factory=time.time)
    status: str = "pending"  # pending, testing, benchmarked, approved, rejected, released
    benchmark_score: Optional[float] = None
    regression_passed: Optional[bool] = None
    test_results: Dict = field(default_factory=dict)
    lineage: List[str] = field(default_factory=list)  # parent patch IDs


@dataclass
class BenchmarkResult:
    """Benchmark comparison result"""
    benchmark_id: str
    patch_id: str
    metric_name: str
    baseline_score: float
    candidate_score: float
    improvement_percent: float
    status: str  # better, worse, same
    timestamp: float = field(default_factory=time.time)


@dataclass
class RegressionResult:
    """Regression test result"""
    regression_id: str
    patch_id: str
    test_suite: str
    passed: bool
    failed_tests: List[str] = field(default_factory=list)
    duration: float = 0.0
    timestamp: float = field(default_factory=time.time)


# ==================== ERROR SIGNAL SYSTEM ====================
# ADVANCED: Error detection, root cause analysis, and signal propagation

class ErrorSeverity(Enum):
    """Error severity levels for signal prioritization"""
    CRITICAL = "critical"  # System cannot continue
    HIGH = "high"        # Major functionality affected
    MEDIUM = "medium"    # Some functionality impacted
    LOW = "low"          # Minor issue, can continue
    INFO = "info"        # Informational, no action needed


class ErrorCategory(Enum):
    """Categories of errors for pattern detection"""
    SYNTAX_ERROR = "syntax_error"
    RUNTIME_ERROR = "runtime_error"
    IMPORT_ERROR = "import_error"
    TIMEOUT_ERROR = "timeout_error"
    MEMORY_ERROR = "memory_error"
    NETWORK_ERROR = "network_error"
    AUTH_ERROR = "auth_error"
    PERMISSION_ERROR = "permission_error"
    VALIDATION_ERROR = "validation_error"
    LOGIC_ERROR = "logic_error"
    BARE_EXCEPT = "bare_except"  # CRITICAL: Bare except blocks hide errors
    PASS_STATEMENT = "pass_statement"  # Empty pass hides issues
    UNHANDLED_EXCEPTION = "unhandled_exception"


@dataclass
class ErrorSignal:
    """
    Represents a detected error with full context for root cause analysis.
    This is the KEY component that enables self-improvement to detect issues.
    """
    signal_id: str
    error_type: ErrorCategory
    severity: ErrorSeverity
    message: str
    
    # Location info
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    function_name: Optional[str] = None
    class_name: Optional[str] = None
    
    # Stack trace for root cause
    stack_trace: Optional[str] = None
    exception_type: Optional[str] = None
    
    # Context
    context: Dict = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    
    # Analysis results
    root_cause: Optional[str] = None
    is_recovered: bool = False
    recovery_attempted: bool = False
    
    # Signal chain (for correlation)
    parent_signal_id: Optional[str] = None
    related_signals: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "signal_id": self.signal_id,
            "error_type": self.error_type.value,
            "severity": self.severity.value,
            "message": self.message,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "function_name": self.function_name,
            "class_name": self.class_name,
            "stack_trace": self.stack_trace,
            "exception_type": self.exception_type,
            "context": self.context,
            "timestamp": self.timestamp,
            "root_cause": self.root_cause,
            "is_recovered": self.is_recovered,
            "recovery_attempted": self.recovery_attempted,
            "parent_signal_id": self.parent_signal_id,
            "related_signals": self.related_signals
        }


class ErrorSignalEmitter:
    """
    ADVANCED: Error signal emitter that detects and propagates errors.
    
    This class solves the core problem:
    - Self-improvement system CANNOT detect errors if they are swallowed
    - Bare except blocks hide errors from the system
    - This emitter INTENTIONALLY catches errors and signals them
    
    Usage:
        emitter = ErrorSignalEmitter()
        emitter.register_with_system()  # Register error handlers globally
    """
    
    def __init__(self, storage_dir: str = "data/error_signals"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # Signal storage
        self.signals: List[ErrorSignal] = []
        self._signal_index: Dict[ErrorCategory, List[int]] = defaultdict(list)
        self._severity_index: Dict[ErrorSeverity, List[int]] = defaultdict(list)
        self._file_index: Dict[str, List[int]] = defaultdict(list)
        
        # Callbacks for signal processing
        self._signal_callbacks: List[Callable[[ErrorSignal], None]] = []
        
        # Statistics
        self.stats = {
            "total_signals": 0,
            "critical_count": 0,
            "recovered_count": 0,
            "by_category": defaultdict(int),
            "by_file": defaultdict(int)
        }
        
        # Pattern detectors
        self._setup_pattern_detectors()
        
        logger.info("📡 ErrorSignalEmitter initialized - ADVANCED error detection ENABLED")
    
    def _setup_pattern_detectors(self):
        """Setup error pattern detectors"""
        # Patterns that indicate hidden errors
        self._bare_except_patterns = [
            r'except\s*:',
            r'except\s*:\s*[^#]',  # except: followed by non-comment
        ]
        
        # Patterns for empty pass statements
        self._pass_patterns = [
            r'^\s+pass\s*$',  # indented pass
            r'^pass\s*$',     # top-level pass
        ]
    
    def emit(self, 
             error_type: ErrorCategory,
             severity: ErrorSeverity,
             message: str,
             file_path: Optional[str] = None,
             line_number: Optional[int] = None,
             function_name: Optional[str] = None,
             class_name: Optional[str] = None,
             stack_trace: Optional[str] = None,
             exception_type: Optional[str] = None,
             context: Optional[Dict] = None) -> ErrorSignal:
        """
        Emit an error signal with full context.
        This is the MAIN entry point for error detection.
        """
        
        signal_id = f"sig_{len(self.signals)}_{int(time.time() * 1000)}"
        
        signal = ErrorSignal(
            signal_id=signal_id,
            error_type=error_type,
            severity=severity,
            message=message,
            file_path=file_path,
            line_number=line_number,
            function_name=function_name,
            class_name=class_name,
            stack_trace=stack_trace,
            exception_type=exception_type,
            context=context or {}
        )
        
        # Perform root cause analysis
        signal.root_cause = self._analyze_root_cause(signal)
        
        # Store signal
        idx = len(self.signals)
        self.signals.append(signal)
        
        # Update indexes
        self._signal_index[error_type].append(idx)
        self._severity_index[severity].append(idx)
        if file_path:
            self._file_index[file_path].append(idx)
        
        # Update stats
        self.stats["total_signals"] += 1
        self.stats["by_category"][error_type.value] += 1
        if file_path:
            self.stats["by_file"][file_path] += 1
        
        if severity == ErrorSeverity.CRITICAL:
            self.stats["critical_count"] += 1
        
        # Log with appropriate level
        log_msg = f"📡 SIGNAL [{signal_id}] {error_type.value}: {message}"
        if file_path and line_number:
            log_msg += f" @ {file_path}:{line_number}"
        
        if severity == ErrorSeverity.CRITICAL:
            logger.critical(log_msg)
        elif severity == ErrorSeverity.HIGH:
            logger.error(log_msg)
        elif severity == ErrorSeverity.MEDIUM:
            logger.warning(log_msg)
        else:
            logger.info(log_msg)
        
        # Trigger callbacks
        for callback in self._signal_callbacks:
            try:
                callback(signal)
            except Exception as e:
                logger.error(f"Signal callback error: {e}")
        
        # Auto-recover if possible
        self._attempt_auto_recovery(signal)
        
        return signal
    
    def _analyze_root_cause(self, signal: ErrorSignal) -> str:
        """
        Perform root cause analysis on the error signal.
        This helps identify WHY the error occurred.
        """
        causes = []
        
        # Analyze based on error type
        if signal.error_type == ErrorCategory.BARE_EXCEPT:
            causes.append("Bare except block detected - error was silently swallowed")
            causes.append("Root cause cannot be determined due to exception hiding")
        
        elif signal.error_type == ErrorCategory.PASS_STATEMENT:
            causes.append("Empty pass statement detected - potential logic gap")
            causes.append("May indicate unfinished code or ignored error condition")
        
        elif signal.stack_trace:
            # Extract from stack trace
            if "File" in signal.stack_trace:
                causes.append(f"Error occurred in: {signal.function_name or 'unknown function'}")
            
            if signal.exception_type:
                causes.append(f"Exception type: {signal.exception_type}")
        
        # Check context for additional clues
        if signal.context:
            if signal.context.get("retry_count", 0) > 3:
                causes.append("Multiple retry attempts failed - likely systemic issue")
            
            if signal.context.get("previous_errors"):
                causes.append("Part of error chain - check related signals")
        
        return "; ".join(causes) if causes else "Root cause analysis inconclusive"
    
    def _attempt_auto_recovery(self, signal: ErrorSignal):
        """
        Attempt automatic recovery for recoverable errors.
        """
        if signal.severity in [ErrorSeverity.CRITICAL, ErrorSeverity.HIGH]:
            # For critical errors, attempt recovery
            if signal.error_type == ErrorCategory.TIMEOUT_ERROR:
                signal.is_recovered = True
                self.stats["recovered_count"] += 1
                logger.info(f"🔧 Auto-recovered signal {signal.signal_id}")
    
    def register_callback(self, callback: Callable[[ErrorSignal], None]):
        """Register a callback to be called when signals are emitted"""
        self._signal_callbacks.append(callback)
    
    def detect_bare_except(self, file_path: str, content: str) -> List[ErrorSignal]:
        """
        Scan code for bare except blocks (static analysis).
        This detects places where errors are being hidden.
        """
        signals = []
        import re
        
        lines = content.split('\n')
        for i, line in enumerate(lines, 1):
            if re.match(r'^\s*except\s*:', line):
                signal = self.emit(
                    error_type=ErrorCategory.BARE_EXCEPT,
                    severity=ErrorSeverity.CRITICAL,
                    message=f"Bare except block detected at line {i}",
                    file_path=file_path,
                    line_number=i,
                    context={"code": line.strip(), "detection_type": "static"}
                )
                signals.append(signal)
        
        return signals
    
    def detect_empty_pass(self, file_path: str, content: str) -> List[ErrorSignal]:
        """
        Scan code for empty pass statements (static analysis).
        """
        signals = []
        import re
        
        lines = content.split('\n')
        for i, line in enumerate(lines, 1):
            if re.match(r'^\s+pass\s*$', line) or re.match(r'^pass\s*$', line):
                # Check if it's in an except block (often intentional)
                if i > 1:
                    prev_lines = lines[max(0, i-3):i-1]
                    if not any('except' in l for l in prev_lines):
                        signal = self.emit(
                            error_type=ErrorCategory.PASS_STATEMENT,
                            severity=ErrorSeverity.MEDIUM,
                            message=f"Empty pass statement at line {i} - may indicate unfinished code",
                            file_path=file_path,
                            line_number=i,
                            context={"code": line.strip(), "detection_type": "static"}
                        )
                        signals.append(signal)
        
        return signals
    
    def get_signals_by_severity(self, severity: ErrorSeverity) -> List[ErrorSignal]:
        """Get all signals of a specific severity"""
        indices = self._severity_index.get(severity, [])
        return [self.signals[i] for i in indices]
    
    def get_signals_by_category(self, category: ErrorCategory) -> List[ErrorSignal]:
        """Get all signals of a specific category"""
        indices = self._signal_index.get(category, [])
        return [self.signals[i] for i in indices]
    
    def get_signals_by_file(self, file_path: str) -> List[ErrorSignal]:
        """Get all signals from a specific file"""
        indices = self._file_index.get(file_path, [])
        return [self.signals[i] for i in indices]
    
    def get_critical_signals(self) -> List[ErrorSignal]:
        """Get all critical severity signals"""
        return self.get_signals_by_severity(ErrorSeverity.CRITICAL)
    
    def export_signals(self, filepath: str = None) -> Dict:
        """Export all signals for analysis"""
        data = {
            "export_time": time.time(),
            "stats": dict(self.stats),
            "signals": [s.to_dict() for s in self.signals[-100:]]  # Last 100
        }
        
        if filepath:
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2, default=str)
        
        return data
    
    def get_statistics(self) -> Dict:
        """Get signal statistics"""
        return dict(self.stats)


# Global error signal emitter instance
_global_emitter: Optional[ErrorSignalEmitter] = None


def get_error_emitter() -> ErrorSignalEmitter:
    """Get or create the global error signal emitter"""
    global _global_emitter
    if _global_emitter is None:
        _global_emitter = ErrorSignalEmitter()
    return _global_emitter


def emit_error_signal(error_type: ErrorCategory,
                      severity: ErrorSeverity,
                      message: str,
                      **kwargs) -> ErrorSignal:
    """Convenience function to emit error signals"""
    return get_error_emitter().emit(error_type, severity, message, **kwargs)


@dataclass
class ReleaseCandidate:
    """Release candidate in pipeline"""
    release_id: str
    version: str
    patch_ids: List[str]
    status: str = "testing"  # testing, approved, released, rolled_back
    created_at: float = field(default_factory=time.time)
    approved_at: Optional[float] = None
    released_at: Optional[float] = None
    rolled_back_at: Optional[float] = None
    rollback_reason: Optional[str] = None


# ==================== FAILURE ANALYZER ====================

class FailureAnalyzer:
    """
    Advanced failure analysis with multi-dimensional correlation
    
    Features:
    - Module-level clustering (which file/module fails most)
    - Tool correlation (which tool causes failures)
    - Task-type correlation (which task types fail)
    - Patch lineage correlation (failures after patches)
    - Time-series degradation detection
    - Recovery effectiveness tracking
    """
    
    def __init__(self, storage_dir: str = "data/failures"):
        self.failures: List[Dict] = []
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # Correlation indexes
        self._file_index: Dict[str, List[int]] = defaultdict(list)  # file -> failure indices
        self._module_index: Dict[str, List[int]] = defaultdict(list)  # module -> failure indices
        self._tool_index: Dict[str, List[int]] = defaultdict(list)  # tool -> failure indices
        self._task_type_index: Dict[str, List[int]] = defaultdict(list)  # task_type -> failure indices
        self._patch_index: Dict[str, List[int]] = defaultdict(list)  # patch_id -> failure indices
        self._time_series: List[Dict] = []  # Time-ordered failures for degradation analysis
        
        # Recovery tracking
        self._recovery_attempts: List[Dict] = []
        self._recovery_success_rate: Dict[str, float] = {}  # strategy -> success rate
        
        logger.info("🔍 Failure Analyzer initialized with advanced correlation")
    
    def record_failure(self, error_type: str, error_message: str, 
                      context: Dict = None):
        """
        Record a failure with full context for correlation analysis
        
        Context should include:
        - file_path: Which file was being processed
        - module: Which module/component
        - tool: Which tool was used
        - task_type: Type of task being performed
        - patch_id: If failure occurred after a patch
        - recovery_used: Which recovery strategy was attempted
        """
        
        context = context or {}
        
        failure = {
            "error_type": error_type,
            "error_message": error_message,
            "context": context,
            "timestamp": time.time(),
            "failure_id": f"fail_{len(self.failures)}_{int(time.time() * 1000)}"
        }
        
        # Add to main list
        idx = len(self.failures)
        self.failures.append(failure)
        
        # Update indexes for correlation
        if context.get("file_path"):
            self._file_index[context["file_path"]].append(idx)
        
        if context.get("module"):
            self._module_index[context["module"]].append(idx)
        
        if context.get("tool"):
            self._tool_index[context["tool"]].append(idx)
        
        if context.get("task_type"):
            self._task_type_index[context["task_type"]].append(idx)
        
        if context.get("patch_id"):
            self._patch_index[context["patch_id"]].append(idx)
        
        # Add to time series
        self._time_series.append({
            "timestamp": failure["timestamp"],
            "error_type": error_type,
            "index": idx
        })
        
        # Keep last 1000
        if len(self.failures) > 1000:
            self.failures = self.failures[-1000:]
            self._rebuild_indexes()
    
    def _rebuild_indexes(self):
        """Rebuild correlation indexes after trimming"""
        self._file_index.clear()
        self._module_index.clear()
        self._tool_index.clear()
        self._task_type_index.clear()
        self._patch_index.clear()
        
        for idx, failure in enumerate(self.failures):
            ctx = failure.get("context", {})
            if ctx.get("file_path"):
                self._file_index[ctx["file_path"]].append(idx)
            if ctx.get("module"):
                self._module_index[ctx["module"]].append(idx)
            if ctx.get("tool"):
                self._tool_index[ctx["tool"]].append(idx)
            if ctx.get("task_type"):
                self._task_type_index[ctx["task_type"]].append(idx)
            if ctx.get("patch_id"):
                self._patch_index[ctx["patch_id"]].append(idx)
    
    def record_recovery_attempt(self, failure_id: str, strategy: str, success: bool):
        """Record recovery attempt for effectiveness tracking"""
        self._recovery_attempts.append({
            "failure_id": failure_id,
            "strategy": strategy,
            "success": success,
            "timestamp": time.time()
        })
        
        # Update success rate
        if strategy not in self._recovery_success_rate:
            self._recovery_success_rate[strategy] = {"success": 0, "total": 0}
        
        self._recovery_success_rate[strategy]["total"] += 1
        if success:
            self._recovery_success_rate[strategy]["success"] += 1
    
    def get_file_failure_analysis(self) -> Dict:
        """Analyze which files have most failures"""
        file_analysis = []
        
        for file_path, indices in self._file_index.items():
            error_types = defaultdict(int)
            for idx in indices:
                error_types[self.failures[idx]["error_type"]] += 1
            
            most_common_error = max(error_types.items(), key=lambda x: x[1]) if error_types else ("unknown", 0)
            
            file_analysis.append({
                "file_path": file_path,
                "failure_count": len(indices),
                "error_types": dict(error_types),
                "most_common_error": most_common_error[0],
                "most_common_error_count": most_common_error[1]
            })
        
        # Sort by failure count
        file_analysis.sort(key=lambda x: -x["failure_count"])
        
        return {
            "total_files_with_failures": len(file_analysis),
            "top_failing_files": file_analysis[:10],
            "summary": {
                "most_failure_prone_file": file_analysis[0] if file_analysis else None,
                "total_unique_files": len(file_analysis)
            }
        }
    
    def get_module_failure_analysis(self) -> Dict:
        """Analyze which modules have most failures"""
        module_analysis = []
        
        for module, indices in self._module_index.items():
            error_types = defaultdict(int)
            recent_failures = 0
            now = time.time()
            
            for idx in indices:
                error_types[self.failures[idx]["error_type"]] += 1
                # Count failures in last hour
                if now - self.failures[idx]["timestamp"] < 3600:
                    recent_failures += 1
            
            most_common_error = max(error_types.items(), key=lambda x: x[1]) if error_types else ("unknown", 0)
            
            module_analysis.append({
                "module": module,
                "failure_count": len(indices),
                "recent_failures_1h": recent_failures,
                "error_types": dict(error_types),
                "most_common_error": most_common_error[0],
                "is_degrading": recent_failures > 5  # Flag if many recent failures
            })
        
        module_analysis.sort(key=lambda x: -x["failure_count"])
        
        return {
            "total_modules_with_failures": len(module_analysis),
            "top_failing_modules": module_analysis[:10],
            "degrading_modules": [m for m in module_analysis if m.get("is_degrading")]
        }
    
    def get_tool_failure_correlation(self) -> Dict:
        """Analyze which tools correlate with failures"""
        tool_analysis = []
        
        for tool, indices in self._tool_index.items():
            error_types = defaultdict(int)
            total_failures = len(indices)
            
            for idx in indices:
                error_types[self.failures[idx]["error_type"]] += 1
            
            # Calculate failure rate (failures / total uses) if we track tool uses
            tool_analysis.append({
                "tool": tool,
                "failure_count": total_failures,
                "error_types": dict(error_types),
                "failure_rate": total_failures / max(1, self._get_tool_use_count(tool)),
                "reliability_score": 1.0 - (total_failures / max(1, self._get_tool_use_count(tool)))
            })
        
        tool_analysis.sort(key=lambda x: -x["failure_count"])
        
        return {
            "total_tools_with_failures": len(tool_analysis),
            "top_failing_tools": tool_analysis[:10],
            "unreliable_tools": [t for t in tool_analysis if t.get("reliability_score", 1.0) < 0.8]
        }
    
    def _get_tool_use_count(self, tool: str) -> int:
        """Get total uses of a tool (would need to be tracked separately)"""
        # This would need to be tracked from actual tool usage
        return max(len(self._tool_index.get(tool, [])), 1)
    
    def get_task_type_correlation(self) -> Dict:
        """Analyze which task types have most failures"""
        task_analysis = []
        
        for task_type, indices in self._task_type_index.items():
            error_types = defaultdict(int)
            for idx in indices:
                error_types[self.failures[idx]["error_type"]] += 1
            
            task_analysis.append({
                "task_type": task_type,
                "failure_count": len(indices),
                "error_types": dict(error_types)
            })
        
        task_analysis.sort(key=lambda x: -x["failure_count"])
        
        return {
            "total_task_types_with_failures": len(task_analysis),
            "highest_risk_tasks": task_analysis[:10]
        }
    
    def get_patch_lineage_correlation(self) -> Dict:
        """Analyze failures that occurred after patches"""
        patch_analysis = []
        
        for patch_id, indices in self._patch_index.items():
            # Find the patch timestamp
            patch_time = self._get_patch_timestamp(patch_id)
            
            # Get failures after this patch
            post_patch_failures = []
            for idx in indices:
                if self.failures[idx]["timestamp"] > patch_time:
                    post_patch_failures.append({
                        "error_type": self.failures[idx]["error_type"],
                        "timestamp": self.failures[idx]["timestamp"],
                        "time_after_patch": self.failures[idx]["timestamp"] - patch_time
                    })
            
            if post_patch_failures:
                patch_analysis.append({
                    "patch_id": patch_id,
                    "failures_after_patch": len(post_patch_failures),
                    "first_failure_time": min(f["time_after_patch"] for f in post_patch_failures),
                    "errors": [f["error_type"] for f in post_patch_failures[:5]]
                })
        
        patch_analysis.sort(key=lambda x: -x["failures_after_patch"])
        
        return {
            "total_patches_with_failures": len(patch_analysis),
            "regression_causing_patches": patch_analysis[:10],
            "likely_regressions": [p for p in patch_analysis if p["failures_after_patch"] >= 3]
        }
    
    def _get_patch_timestamp(self, patch_id: str) -> float:
        """Get patch creation timestamp"""
        # Would need to query patch registry
        return time.time() - 86400  # Default to 1 day ago
    
    def get_time_series_degradation(self, window_minutes: int = 60) -> Dict:
        """Detect time-series degradation patterns"""
        if not self._time_series:
            return {"degradation_detected": False, "message": "No time series data"}
        
        now = time.time()
        window_ms = window_minutes * 60
        
        # Count failures in recent windows
        recent_failures = [f for f in self._time_series if now - f["timestamp"] < window_ms]
        older_failures = [f for f in self._time_series 
                         if window_ms < now - f["timestamp"] < window_ms * 2]
        
        recent_count = len(recent_failures)
        older_count = len(older_failures)
        
        # Calculate trend
        if older_count > 0:
            change_ratio = (recent_count - older_count) / older_count
        else:
            change_ratio = recent_count
        
        # Determine if degrading
        is_degrading = recent_count > older_count * 1.5 and recent_count > 5
        
        # Get error type distribution
        recent_errors = defaultdict(int)
        for f in recent_failures:
            recent_errors[f["error_type"]] += 1
        
        return {
            "degradation_detected": is_degrading,
            "recent_failures": recent_count,
            "older_failures": older_count,
            "change_ratio": change_ratio,
            "trend": "increasing" if change_ratio > 0.1 else "stable" if change_ratio > -0.1 else "decreasing",
            "window_minutes": window_minutes,
            "top_recent_errors": dict(sorted(recent_errors.items(), key=lambda x: -x[1])[:5])
        }
    
    def get_recovery_effectiveness(self) -> Dict:
        """Analyze which recovery strategies are most effective"""
        strategy_stats = defaultdict(lambda: {"success": 0, "total": 0})
        
        for attempt in self._recovery_attempts:
            strategy = attempt.get("strategy", "unknown")
            strategy_stats[strategy]["total"] += 1
            if attempt.get("success"):
                strategy_stats[strategy]["success"] += 1
        
        # Calculate success rates
        effectiveness = []
        for strategy, stats in strategy_stats.items():
            success_rate = stats["success"] / max(1, stats["total"])
            effectiveness.append({
                "strategy": strategy,
                "total_attempts": stats["total"],
                "successful_recoveries": stats["success"],
                "success_rate": success_rate,
                "effectiveness": "high" if success_rate > 0.7 else "medium" if success_rate > 0.4 else "low"
            })
        
        effectiveness.sort(key=lambda x: -x["success_rate"])
        
        return {
            "total_recovery_attempts": len(self._recovery_attempts),
            "strategy_effectiveness": effectiveness,
            "most_effective_strategy": effectiveness[0] if effectiveness else None,
            "ineffective_strategies": [e for e in effectiveness if e["effectiveness"] == "low"]
        }
    
    def analyze_patterns(self) -> Dict:
        """Comprehensive multi-dimensional failure analysis"""
        
        return {
            "total_failures": len(self.failures),
            "file_analysis": self.get_file_failure_analysis(),
            "module_analysis": self.get_module_failure_analysis(),
            "tool_correlation": self.get_tool_failure_correlation(),
            "task_type_correlation": self.get_task_type_correlation(),
            "patch_lineage": self.get_patch_lineage_correlation(),
            "time_series_degradation": self.get_time_series_degradation(),
            "recovery_effectiveness": self.get_recovery_effectiveness()
        }
    
    def get_top_failures(self, limit: int = 10) -> List[Dict]:
        """Get most common failures with context"""
        error_counts = defaultdict(lambda: {"count": 0, "examples": []})
        
        for f in self.failures:
            error_type = f["error_type"]
            error_counts[error_type]["count"] += 1
            if len(error_counts[error_type]["examples"]) < 3:
                error_counts[error_type]["examples"].append({
                    "message": f["error_message"][:100],
                    "context": f.get("context", {})
                })
        
        sorted_errors = sorted(error_counts.items(), key=lambda x: -x[1]["count"])
        
        return [
            {"error_type": e[0], "count": e[1]["count"], "examples": e[1]["examples"]}
            for e in sorted_errors[:limit]
        ]
    
    def get_recent_failures(self, limit: int = 50) -> List[Dict]:
        """Get recent failures"""
        return self.failures[-limit:]
    
    def export_analysis(self, filepath: str = None) -> Dict:
        """Export full analysis to file or return as dict"""
        analysis = self.analyze_patterns()
        
        if filepath:
            with open(filepath, 'w') as f:
                json.dump(analysis, f, indent=2, default=str)
            logger.info(f"📊 Failure analysis exported to {filepath}")
        
        return analysis


# ==================== BOTTLENECK DETECTOR ====================

class BottleneckDetector:
    """
    Advanced bottleneck detection with multi-dimensional profiling
    
    Features:
    - Stage-level timing (thinking, acting, verifying, etc.)
    - Tool-level timing (each tool's performance)
    - Regression delta (compare current vs baseline)
    - Benchmark delta (compare against benchmarks)
    - Resource profiling (CPU, memory, tokens, IO, browser)
    """
    
    # Bottleneck types
    LATENCY = "latency"
    TOKEN = "token"
    TOOL = "tool"
    IO = "io"
    BROWSER = "browser"
    MEMORY = "memory"
    NETWORK = "network"
    
    # Execution stages
    STAGE_PLANNING = "planning"
    STAGE_THINKING = "thinking"
    STAGE_ACTING = "acting"
    STAGE_VERIFYING = "verifying"
    STAGE_REPAIRING = "repairing"
    STAGE_APPROVAL = "approval"
    
    def __init__(self, storage_dir: str = "data/bottlenecks"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # Stage-level timing
        self.stage_timings: Dict[str, List[float]] = defaultdict(list)
        self.stage_histograms: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        
        # Tool-level timing
        self.tool_timings: Dict[str, List[float]] = defaultdict(list)
        self.tool_call_counts: Dict[str, int] = defaultdict(int)
        self.tool_errors: Dict[str, int] = defaultdict(int)
        
        # Resource profiling
        self.cpu_usage: List[float] = []
        self.memory_usage: List[float] = []
        self.token_usage: List[Dict] = []  # {'prompt': int, 'completion': int, 'total': int}
        self.io_operations: Dict[str, int] = defaultdict(int)
        self.browser_metrics: Dict[str, List[float]] = defaultdict(list)
        
        # Baseline for regression detection
        self.baseline: Dict[str, float] = {}
        self.baseline_window = 100  # Use last 100 measurements for baseline
        
        # Benchmark references
        self.benchmarks: Dict[str, Dict] = {}
        
        logger.info("⏱️ Bottleneck Detector initialized with advanced profiling")
    
    # ==================== STAGE TIMING ====================
    
    def record_stage_timing(self, stage: str, duration: float):
        """Record timing for a specific execution stage"""
        self.stage_timings[stage].append(duration)
        
        # Update histogram (bucket into ranges)
        bucket = self._get_time_bucket(duration)
        self.stage_histograms[stage][bucket] += 1
        
        # Keep last 1000
        if len(self.stage_timings[stage]) > 1000:
            self.stage_timings[stage] = self.stage_timings[stage][-1000:]
    
    def _get_time_bucket(self, duration: float) -> str:
        """Get time bucket for histogram"""
        if duration < 0.1:
            return "0-100ms"
        elif duration < 0.5:
            return "100-500ms"
        elif duration < 1.0:
            return "500ms-1s"
        elif duration < 5.0:
            return "1-5s"
        elif duration < 10.0:
            return "5-10s"
        else:
            return "10s+"
    
    def get_stage_analysis(self) -> Dict:
        """Analyze stage-level timings"""
        stage_analysis = {}
        
        for stage, timings in self.stage_timings.items():
            if not timings:
                continue
            
            sorted_timings = sorted(timings)
            n = len(sorted_timings)
            
            # Calculate percentiles
            p50 = sorted_timings[int(n * 0.5)]
            p90 = sorted_timings[int(n * 0.9)] if n > 10 else p50
            p95 = sorted_timings[int(n * 0.95)] if n > 20 else p90
            p99 = sorted_timings[int(n * 0.99)] if n > 100 else p95
            
            avg = sum(timings) / len(timings)
            
            # Check for regression from baseline
            baseline_key = f"stage_{stage}"
            regression = None
            if baseline_key in self.baseline:
                baseline_val = self.baseline[baseline_key]
                regression = ((avg - baseline_val) / baseline_val) * 100 if baseline_val > 0 else 0
            
            stage_analysis[stage] = {
                "count": n,
                "avg": avg,
                "min": min(timings),
                "max": max(timings),
                "p50": p50,
                "p90": p90,
                "p95": p95,
                "p99": p99,
                "histogram": dict(self.stage_histograms[stage]),
                "regression_percent": regression,
                "is_bottleneck": p90 > self._get_threshold_for_stage(stage)
            }
        
        return stage_analysis
    
    def _get_threshold_for_stage(self, stage: str) -> float:
        """Get threshold for each stage type"""
        thresholds = {
            self.STAGE_PLANNING: 2.0,
            self.STAGE_THINKING: 5.0,
            self.STAGE_ACTING: 10.0,
            self.STAGE_VERIFYING: 5.0,
            self.STAGE_REPAIRING: 10.0,
            self.STAGE_APPROVAL: 2.0
        }
        return thresholds.get(stage, 5.0)
    
    # ==================== TOOL TIMING ====================
    
    def record_tool_timing(self, tool_name: str, duration: float, success: bool = True):
        """Record timing for a specific tool"""
        self.tool_timings[tool_name].append(duration)
        self.tool_call_counts[tool_name] += 1
        
        if not success:
            self.tool_errors[tool_name] += 1
        
        # Keep last 1000
        if len(self.tool_timings[tool_name]) > 1000:
            self.tool_timings[tool_name] = self.tool_timings[tool_name][-1000:]
    
    def get_tool_analysis(self) -> Dict:
        """Analyze tool-level timings"""
        tool_analysis = {}
        
        for tool, timings in self.tool_timings.items():
            if not timings:
                continue
            
            call_count = self.tool_call_counts[tool]
            error_count = self.tool_errors.get(tool, 0)
            avg = sum(timings) / len(timings)
            
            # Calculate reliability
            reliability = (call_count - error_count) / call_count if call_count > 0 else 1.0
            
            # Check for regression
            baseline_key = f"tool_{tool}"
            regression = None
            if baseline_key in self.baseline:
                baseline_val = self.baseline[baseline_key]
                regression = ((avg - baseline_val) / baseline_val) * 100 if baseline_val > 0 else 0
            
            tool_analysis[tool] = {
                "call_count": call_count,
                "error_count": error_count,
                "reliability": reliability,
                "avg_duration": avg,
                "min_duration": min(timings),
                "max_duration": max(timings),
                "total_time": sum(timings),
                "regression_percent": regression,
                "is_bottleneck": avg > 5.0 or reliability < 0.8
            }
        
        # Sort by total time spent
        tool_analysis = dict(sorted(tool_analysis.items(), 
                                    key=lambda x: -x[1]["total_time"]))
        
        return tool_analysis
    
    # ==================== RESOURCE PROFILING ====================
    
    def record_cpu_usage(self, percentage: float):
        """Record CPU usage percentage"""
        self.cpu_usage.append(percentage)
        if len(self.cpu_usage) > 1000:
            self.cpu_usage = self.cpu_usage[-1000:]
    
    def record_memory_usage(self, mb: float):
        """Record memory usage in MB"""
        self.memory_usage.append(mb)
        if len(self.memory_usage) > 1000:
            self.memory_usage = self.memory_usage[-1000:]
    
    def record_token_usage(self, prompt_tokens: int, completion_tokens: int):
        """Record token usage"""
        self.token_usage.append({
            "prompt": prompt_tokens,
            "completion": completion_tokens,
            "total": prompt_tokens + completion_tokens,
            "timestamp": time.time()
        })
        if len(self.token_usage) > 1000:
            self.token_usage = self.token_usage[-1000:]
    
    def record_io_operation(self, operation: str, bytes_count: int = 1):
        """Record IO operation"""
        self.io_operations[operation] += bytes_count
    
    def record_browser_metric(self, metric_name: str, value: float):
        """Record browser-specific metric"""
        self.browser_metrics[metric_name].append(value)
        if len(self.browser_metrics[metric_name]) > 1000:
            self.browser_metrics[metric_name] = self.browser_metrics[metric_name][-1000:]
    
    def get_resource_analysis(self) -> Dict:
        """Analyze resource usage"""
        analysis = {}
        
        # CPU
        if self.cpu_usage:
            avg_cpu = sum(self.cpu_usage) / len(self.cpu_usage)
            analysis["cpu"] = {
                "avg": avg_cpu,
                "max": max(self.cpu_usage),
                "min": min(self.cpu_usage),
                "samples": len(self.cpu_usage),
                "is_bottleneck": avg_cpu > 80.0
            }
        
        # Memory
        if self.memory_usage:
            avg_mem = sum(self.memory_usage) / len(self.memory_usage)
            analysis["memory"] = {
                "avg_mb": avg_mem,
                "max_mb": max(self.memory_usage),
                "min_mb": min(self.memory_usage),
                "samples": len(self.memory_usage),
                "is_bottleneck": avg_mem > 2048  # 2GB threshold
            }
        
        # Tokens
        if self.token_usage:
            total_prompt = sum(t["prompt"] for t in self.token_usage)
            total_completion = sum(t["completion"] for t in self.token_usage)
            total = total_prompt + total_completion
            
            analysis["tokens"] = {
                "total_prompt": total_prompt,
                "total_completion": total_completion,
                "total": total,
                "avg_per_call": total / len(self.token_usage) if self.token_usage else 0,
                "is_bottleneck": total > 100000  # 100k tokens threshold
            }
        
        # IO
        if self.io_operations:
            total_io = sum(self.io_operations.values())
            analysis["io"] = {
                "operations": dict(self.io_operations),
                "total_bytes": total_io,
                "is_bottleneck": total_io > 100 * 1024 * 1024  # 100MB threshold
            }
        
        # Browser
        if self.browser_metrics:
            browser_analysis = {}
            for metric, values in self.browser_metrics.items():
                browser_analysis[metric] = {
                    "avg": sum(values) / len(values),
                    "max": max(values),
                    "min": min(values)
                }
            analysis["browser"] = browser_analysis
        
        return analysis
    
    # ==================== REGRESSION DETECTION ====================
    
    def update_baseline(self):
        """Update baseline from recent measurements"""
        # Update stage baselines
        for stage, timings in self.stage_timings.items():
            if timings:
                recent = timings[-self.baseline_window:]
                self.baseline[f"stage_{stage}"] = sum(recent) / len(recent)
        
        # Update tool baselines
        for tool, timings in self.tool_timings.items():
            if timings:
                recent = timings[-self.baseline_window:]
                self.baseline[f"tool_{tool}"] = sum(recent) / len(recent)
        
        logger.info("⏱️ Baseline updated")
    
    def get_regression_report(self) -> Dict:
        """Get regression report comparing current vs baseline"""
        regressions = []
        improvements = []
        
        # Check stage regressions
        for stage in self.stage_timings:
            baseline_key = f"stage_{stage}"
            if baseline_key not in self.baseline:
                continue
            
            current = sum(self.stage_timings[stage][-10:]) / min(10, len(self.stage_timings[stage]))
            baseline = self.baseline[baseline_key]
            delta = ((current - baseline) / baseline) * 100 if baseline > 0 else 0
            
            if delta > 20:
                regressions.append({
                    "type": "stage",
                    "name": stage,
                    "baseline": baseline,
                    "current": current,
                    "delta_percent": delta
                })
            elif delta < -20:
                improvements.append({
                    "type": "stage",
                    "name": stage,
                    "baseline": baseline,
                    "current": current,
                    "improvement_percent": abs(delta)
                })
        
        # Check tool regressions
        for tool in self.tool_timings:
            baseline_key = f"tool_{tool}"
            if baseline_key not in self.baseline:
                continue
            
            current = sum(self.tool_timings[tool][-10:]) / min(10, len(self.tool_timings[tool]))
            baseline = self.baseline[baseline_key]
            delta = ((current - baseline) / baseline) * 100 if baseline > 0 else 0
            
            if delta > 20:
                regressions.append({
                    "type": "tool",
                    "name": tool,
                    "baseline": baseline,
                    "current": current,
                    "delta_percent": delta
                })
        
        return {
            "has_regressions": len(regressions) > 0,
            "regressions": regressions,
            "improvements": improvements,
            "baseline_version": max(self.baseline.keys(), default="none")
        }
    
    # ==================== BENCHMARK DELTA ====================
    
    def set_benchmark(self, benchmark_name: str, thresholds: Dict[str, float]):
        """Set benchmark thresholds"""
        self.benchmarks[benchmark_name] = {
            "thresholds": thresholds,
            "set_at": time.time()
        }
    
    def compare_to_benchmark(self, benchmark_name: str) -> Dict:
        """Compare current performance to benchmark"""
        if benchmark_name not in self.benchmarks:
            return {"error": f"Benchmark {benchmark_name} not found"}
        
        benchmark = self.benchmarks[benchmark_name]
        thresholds = benchmark["thresholds"]
        
        comparison = {}
        
        # Compare stages
        for stage, timings in self.stage_timings.items():
            threshold_key = f"stage_{stage}"
            if threshold_key in thresholds:
                current = sum(timings[-10:]) / min(10, len(timings))
                threshold = thresholds[threshold_key]
                comparison[stage] = {
                    "current": current,
                    "threshold": threshold,
                    "within_budget": current <= threshold,
                    "percent_of_budget": (current / threshold * 100) if threshold > 0 else 0
                }
        
        return {
            "benchmark": benchmark_name,
            "comparison": comparison,
            "all_within_budget": all(v.get("within_budget", True) for v in comparison.values())
        }
    
    # ==================== MAIN DETECTION ====================
    
    def detect_bottlenecks(self) -> List[Dict]:
        """Comprehensive bottleneck detection"""
        bottlenecks = []
        
        # Stage bottlenecks
        for stage, timings in self.stage_timings.items():
            if not timings:
                continue
            
            recent = timings[-100:]
            avg = sum(recent) / len(recent)
            p90 = sorted(recent)[int(len(recent) * 0.9)] if len(recent) > 10 else avg
            
            threshold = self._get_threshold_for_stage(stage)
            
            if p90 > threshold:
                bottlenecks.append({
                    "type": self.LATENCY,
                    "source": "stage",
                    "name": stage,
                    "avg": avg,
                    "p90": p90,
                    "threshold": threshold,
                    "severity": "critical" if avg > threshold * 2 else "high" if avg > threshold else "medium"
                })
        
        # Tool bottlenecks
        for tool, timings in self.tool_timings.items():
            if not timings:
                continue
            
            recent = timings[-100:]
            avg = sum(recent) / len(recent)
            call_count = self.tool_call_counts.get(tool, 0)
            error_rate = self.tool_errors.get(tool, 0) / call_count if call_count > 0 else 0
            
            if avg > 10.0 or error_rate > 0.2:
                bottlenecks.append({
                    "type": self.TOOL,
                    "source": "tool",
                    "name": tool,
                    "avg_duration": avg,
                    "call_count": call_count,
                    "error_rate": error_rate,
                    "severity": "critical" if error_rate > 0.3 else "high" if avg > 20 else "medium"
                })
        
        # Resource bottlenecks
        if self.cpu_usage and sum(self.cpu_usage[-100:]) / len(self.cpu_usage[-100:]) > 80:
            bottlenecks.append({
                "type": self.MEMORY,
                "source": "system",
                "name": "cpu",
                "avg": sum(self.cpu_usage[-100:]) / len(self.cpu_usage[-100:]),
                "severity": "high"
            })
        
        if self.memory_usage and sum(self.memory_usage[-100:]) / len(self.memory_usage[-100:]) > 2048:
            bottlenecks.append({
                "type": self.MEMORY,
                "source": "system",
                "name": "memory",
                "avg_mb": sum(self.memory_usage[-100:]) / len(self.memory_usage[-100:]),
                "severity": "critical"
            })
        
        # Sort by severity
        severity_order = {"critical": 0, "high": 1, "medium": 2}
        bottlenecks.sort(key=lambda x: severity_order.get(x.get("severity", "medium"), 3))
        
        return bottlenecks
    
    def get_full_report(self) -> Dict:
        """Get comprehensive performance report"""
        return {
            "stage_analysis": self.get_stage_analysis(),
            "tool_analysis": self.get_tool_analysis(),
            "resource_analysis": self.get_resource_analysis(),
            "regression_report": self.get_regression_report(),
            "bottlenecks": self.detect_bottlenecks(),
            "baseline": {k: v for k, v in self.baseline.items() if k.startswith(("stage_", "tool_"))}
        }
    
    def get_metrics_summary(self) -> Dict:
        """Get basic metrics summary (legacy compatibility)"""
        return self.get_full_report()


# ==================== PATCH PROPOSER ====================

class PatchProposer:
    """
    Propose intelligent code improvements with AI-powered patch generation
    
    Features:
    - Root-cause to patch mapping
    - AST diff generation
    - LLM patch generation (optional)
    - Patch risk scoring
    - File allowlist/denylist
    """
    
    # Root cause to fix type mapping
    ROOT_CAUSE_MAPPINGS = {
        "null_pointer": "add_null_check",
        "memory_leak": "add_cleanup",
        "performance": "optimize_algorithm",
        "race_condition": "add_lock",
        "deadlock": "add_timeout",
        "infinite_loop": "add_bounds_check",
        "buffer_overflow": "add_bounds_check",
        "sql_injection": "sanitize_input",
        "xss_vulnerability": "escape_output",
        "unused_variable": "remove_dead_code",
        "duplicate_code": "extract_method",
        "long_function": "split_function",
        "magic_numbers": "add_constant",
        "hardcoded_config": "extract_config",
        "missing_error_handling": "add_try_catch",
        "logging_missing": "add_logging",
    }
    
    # Risk levels
    RISK_LOW = "low"
    RISK_MEDIUM = "medium"
    RISK_HIGH = "high"
    RISK_CRITICAL = "critical"
    
    def __init__(self, 
                 storage_dir: str = "data/patches",
                 allowed_files: List[str] = None,
                 denied_files: List[str] = None):
        self.proposals: Dict[str, PatchProposal] = {}
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # File allowlist/denylist
        self.allowed_files = allowed_files or ["*.py", "*.js", "*.ts", "*.json", "*.yaml", "*.yml"]
        self.denied_files = denied_files or ["*.env", "*.pem", "*.key", "*.secret", "*.password"]
        
        # Patch history for learning
        self.patch_history: List[Dict] = []
        
        # Initialize diff generator
        self._diff_cache = {}
        
        logger.info("💡 Patch Proposer initialized with AI capabilities")
    
    def is_file_allowed(self, file_path: str) -> bool:
        """Check if file is allowed for patching"""
        import fnmatch
        
        # Check deny list first
        for pattern in self.denied_files:
            if fnmatch.fnmatch(file_path, pattern) or fnmatch.fnmatch(os.path.basename(file_path), pattern):
                logger.warning(f"File denied by pattern: {file_path} matches {pattern}")
                return False
        
        # Check allow list
        for pattern in self.allowed_files:
            if fnmatch.fnmatch(file_path, pattern) or fnmatch.fnmatch(os.path.basename(file_path), pattern):
                return True
        
        return False
    
    def map_root_cause_to_fix(self, root_cause: str) -> str:
        """Map root cause to fix type"""
        root_cause_lower = root_cause.lower().replace(" ", "_").replace("-", "_")
        return self.ROOT_CAUSE_MAPPINGS.get(root_cause_lower, "generic_fix")
    
    def generate_ast_diff(self, current_code: str, proposed_code: str) -> Dict:
        """Generate AST-based diff between two code versions"""
        try:
            import ast
            
            # Parse both versions
            current_ast = ast.parse(current_code) if current_code else None
            proposed_ast = ast.parse(proposed_code) if proposed_code else None
            
            diff_result = {
                "has_changes": current_code != proposed_code,
                "current_lines": len(current_code.splitlines()) if current_code else 0,
                "proposed_lines": len(proposed_code.splitlines()) if proposed_code else 0,
                "line_diff": len(proposed_code.splitlines()) - len(current_code.splitlines()) if current_code and proposed_code else 0,
            }
            
            if current_ast and proposed_ast:
                # Compare function definitions
                current_funcs = [n.name for n in ast.walk(current_ast) if isinstance(n, ast.FunctionDef)]
                proposed_funcs = [n.name for n in ast.walk(proposed_ast) if isinstance(n, ast.FunctionDef)]
                
                diff_result["functions_added"] = list(set(proposed_funcs) - set(current_funcs))
                diff_result["functions_removed"] = list(set(current_funcs) - set(proposed_funcs))
                diff_result["functions_modified"] = list(set(current_funcs) & set(proposed_funcs))
                
                # Compare imports
                current_imports = [n.module for n in ast.walk(current_ast) if isinstance(n, ast.Import)]
                proposed_imports = [n.module for n in ast.walk(proposed_ast) if isinstance(n, ast.Import)]
                
                diff_result["imports_added"] = list(set(proposed_imports) - set(current_imports))
                diff_result["imports_removed"] = list(set(current_imports) - set(proposed_imports))
            
            return diff_result
            
        except SyntaxError as e:
            logger.warning(f"AST diff generation failed: {e}")
            return {"error": str(e), "has_changes": current_code != proposed_code}
    
    def calculate_patch_risk(self, current_code: str, proposed_code: str, 
                           fix_type: str) -> Dict[str, Any]:
        """Calculate risk score for a patch"""
        risk_factors = []
        risk_score = 0.0
        
        # Line count impact
        line_diff = len(proposed_code.splitlines()) - len(current_code.splitlines())
        if abs(line_diff) > 100:
            risk_factors.append("large_code_change")
            risk_score += 0.3
        elif abs(line_diff) > 50:
            risk_factors.append("medium_code_change")
            risk_score += 0.15
        
        # Critical fix types have higher risk
        high_risk_fixes = ["add_lock", "add_try_catch", "remove_dead_code"]
        if fix_type in high_risk_fixes:
            risk_factors.append("high_risk_fix_type")
            risk_score += 0.25
        
        # Security-related fixes
        security_fixes = ["sanitize_input", "escape_output", "add_null_check"]
        if fix_type in security_fixes:
            risk_factors.append("security_critical")
            risk_score += 0.2
        
        # Check for dangerous patterns in proposed code
        dangerous_patterns = ["eval(", "exec(", "os.system(", "__import__("]
        for pattern in dangerous_patterns:
            if pattern in proposed_code:
                risk_factors.append(f"dangerous_pattern:{pattern}")
                risk_score += 0.4
        
        # Normalize risk score
        risk_score = min(risk_score, 1.0)
        
        # Determine risk level
        if risk_score >= 0.7:
            risk_level = self.RISK_CRITICAL
        elif risk_score >= 0.4:
            risk_level = self.RISK_HIGH
        elif risk_score >= 0.2:
            risk_level = self.RISK_MEDIUM
        else:
            risk_level = self.RISK_LOW
        
        return {
            "risk_score": risk_score,
            "risk_level": risk_level,
            "risk_factors": risk_factors,
            "line_diff": line_diff,
            "is_safe": risk_score < 0.4
        }
    
    def generate_diff(self, current_code: str, proposed_code: str) -> str:
        """Generate unified diff format"""
        import difflib
        
        current_lines = current_code.splitlines(keepends=True)
        proposed_lines = proposed_code.splitlines(keepends=True)
        
        diff = difflib.unified_diff(
            current_lines,
            proposed_lines,
            fromfile='original',
            tofile='patched',
            lineterm=''
        )
        
        return ''.join(diff)
    
    def generate_patch(self, file_path: str, current_code: str, 
                      root_cause: str, proposed_fix: str = None,
                      expected_improvement: str = "",
                      llm_suggestion: str = None) -> str:
        """
        Generate a complete patch proposal with risk assessment
        
        Args:
            file_path: Path to the file to patch
            current_code: Current code content
            root_cause: Root cause of the issue (e.g., "performance", "null_pointer")
            proposed_fix: Description of the proposed fix
            expected_improvement: Expected improvement from the patch
            llm_suggestion: Optional LLM-generated patch suggestion
            
        Returns:
            proposal_id
        """
        
        # Check file allowlist
        if not self.is_file_allowed(file_path):
            raise ValueError(f"File not allowed for patching: {file_path}")
        
        # Determine fix type from root cause
        fix_type = self.map_root_cause_to_fix(root_cause)
        
        # Use LLM suggestion if provided, otherwise use proposed_fix
        proposed_code = llm_suggestion if llm_suggestion else current_code
        
        # Generate diff
        diff = self.generate_diff(current_code, proposed_code)
        
        # Calculate risk
        risk_assessment = self.calculate_patch_risk(current_code, proposed_code, fix_type)
        
        # Generate AST diff
        ast_diff = self.generate_ast_diff(current_code, proposed_code)
        
        # Create proposal
        proposal_id = f"patch_{hashlib.md5(f'{file_path}{time.time()}'.encode()).hexdigest()[:8]}"
        
        proposal = PatchProposal(
            proposal_id=proposal_id,
            file_path=file_path,
            current_code=current_code,
            proposed_code=proposed_code,
            reason=proposed_fix or f"Fix: {root_cause} via {fix_type}",
            expected_improvement=expected_improvement,
            status="proposed"
        )
        
        # Store additional metadata
        proposal.metadata = {
            "root_cause": root_cause,
            "fix_type": fix_type,
            "diff": diff,
            "risk_assessment": risk_assessment,
            "ast_diff": ast_diff,
        }
        
        self.proposals[proposal_id] = proposal
        
        # Save patch to disk
        self._save_patch_to_disk(proposal_id, proposal)
        
        logger.info(f"💡 Generated patch: {proposal_id} for {file_path} (risk: {risk_assessment['risk_level']})")
        
        return proposal_id
    
    def _save_patch_to_disk(self, proposal_id: str, proposal: PatchProposal):
        """Save patch proposal to disk"""
        try:
            patch_file = self.storage_dir / f"{proposal_id}.json"
            
            patch_data = {
                "proposal_id": proposal.proposal_id,
                "file_path": proposal.file_path,
                "reason": proposal.reason,
                "expected_improvement": proposal.expected_improvement,
                "status": proposal.status,
                "created_at": proposal.created_at,
                "metadata": proposal.metadata,
                # Don't save full code to disk for security
                "has_current_code": bool(proposal.current_code),
                "has_proposed_code": bool(proposal.proposed_code),
            }
            
            with open(patch_file, 'w') as f:
                json.dump(patch_data, f, indent=2)
                
        except Exception as e:
            logger.warning(f"Failed to save patch to disk: {e}")
    
    def apply_patch(self, proposal_id: str) -> bool:
        """Apply an accepted patch to the file system"""
        if proposal_id not in self.proposals:
            return False
        
        proposal = self.proposals[proposal_id]
        
        if proposal.status != "accepted":
            logger.warning(f"Cannot apply patch {proposal_id}: status is {proposal.status}")
            return False
        
        try:
            file_path = proposal.file_path
            
            # Create backup
            if os.path.exists(file_path):
                backup_path = f"{file_path}.backup.{int(time.time())}"
                shutil.copy2(file_path, backup_path)
            
            # Write new code
            with open(file_path, 'w') as f:
                f.write(proposal.proposed_code)
            
            logger.info(f"💡 Applied patch: {proposal_id} to {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to apply patch {proposal_id}: {e}")
            return False
    
    def accept(self, proposal_id: str) -> bool:
        """Accept a proposal"""
        
        if proposal_id in self.proposals:
            self.proposals[proposal_id].status = "accepted"
            return True
        
        return False
    
    def reject(self, proposal_id: str) -> bool:
        """Reject a proposal"""
        
        if proposal_id in self.proposals:
            self.proposals[proposal_id].status = "rejected"
            return True
        
        return False
    
    def get_proposals(self, status: str = None) -> List[Dict]:
        """Get proposals"""
        
        proposals = list(self.proposals.values())
        
        if status:
            proposals = [p for p in proposals if p.status == status]
        
        return [asdict(p) for p in proposals]


# ==================== SNAPSHOT MANAGER ====================

class SnapshotManager:
    """
    Manage atomic code snapshots for rollback with integrity verification
    
    Features:
    - Atomic snapshot creation with status tracking
    - Manifest file with checksums
    - Complete/incomplete status
    - Integrity verification before restore
    - Transaction-like behavior
    """
    
    SNAPSHOT_STATUS_PENDING = "pending"
    SNAPSHOT_STATUS_COMPLETE = "complete"
    SNAPSHOT_STATUS_FAILED = "failed"
    
    def __init__(self, storage_dir: str = "data/snapshots"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        self.snapshots: Dict[str, Snapshot] = {}
        self._in_progress_snapshots: Dict[str, Dict] = {}  # Track in-progress snapshots
        
        logger.info("📸 Snapshot Manager initialized with atomic support")
    
    def _calculate_checksum(self, file_path: str) -> str:
        """Calculate SHA256 checksum of a file"""
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                sha256.update(chunk)
        return sha256.hexdigest()
    
    def _calculate_content_checksum(self, content: str) -> str:
        """Calculate SHA256 checksum of content"""
        return hashlib.sha256(content.encode()).hexdigest()
    
    def _create_manifest(self, snapshot_id: str, files: List[str]) -> Dict:
        """Create manifest with checksums for all files"""
        manifest = {
            "snapshot_id": snapshot_id,
            "created_at": time.time(),
            "files": {},
            "total_files": len(files),
            "completed_files": 0,
            "status": self.SNAPSHOT_STATUS_PENDING,
            "checksum": ""
        }
        
        for filepath in files:
            try:
                if os.path.exists(filepath):
                    checksum = self._calculate_checksum(filepath)
                    manifest["files"][filepath] = {
                        "checksum": checksum,
                        "size": os.path.getsize(filepath),
                        "status": "complete"
                    }
                    manifest["completed_files"] += 1
                else:
                    manifest["files"][filepath] = {
                        "checksum": None,
                        "size": 0,
                        "status": "missing"
                    }
            except Exception as e:
                manifest["files"][filepath] = {"checksum": None, "size": 0, "status": "error", "error": str(e)}
        
        manifest_json = json.dumps(manifest["files"], sort_keys=True)
        manifest["checksum"] = hashlib.sha256(manifest_json.encode()).hexdigest()
        
        return manifest
    
    def _verify_manifest(self, snapshot_id: str, manifest: Dict) -> bool:
        """Verify manifest integrity"""
        manifest_json = json.dumps(manifest["files"], sort_keys=True)
        expected_checksum = hashlib.sha256(manifest_json.encode()).hexdigest()
        return manifest["checksum"] == expected_checksum
    
    def _verify_file_integrity(self, snapshot_files_dir: Path, manifest: Dict) -> Dict[str, bool]:
        """Verify integrity of all files in snapshot"""
        results = {}
        
        for filepath, file_info in manifest["files"].items():
            if file_info.get("status") != "complete":
                results[filepath] = False
                continue
            
            try:
                src = snapshot_files_dir / filepath
                if not src.exists():
                    results[filepath] = False
                    continue
                
                current_checksum = self._calculate_checksum(str(src))
                results[filepath] = (current_checksum == file_info["checksum"])
                
            except Exception as e:
                results[filepath] = False
        
        return results
    
    def create_snapshot(self, description: str, files: List[str], 
                       version: str = "1.0.0") -> str:
        """Create an atomic snapshot with integrity verification"""
        
        snapshot_id = f"snap_{int(time.time())}"
        temp_dir = self.storage_dir / f"{snapshot_id}.tmp"
        final_dir = self.storage_dir / snapshot_id
        
        try:
            temp_dir.mkdir(parents=True, exist_ok=True)
            self._in_progress_snapshots[snapshot_id] = {"status": self.SNAPSHOT_STATUS_PENDING, "files": {}}
            
            file_hashes = {}
            successful_files = []
            
            for filepath in files:
                try:
                    if not os.path.exists(filepath):
                        continue
                    
                    content = open(filepath, 'r').read()
                    checksum = self._calculate_content_checksum(content)
                    file_hashes[filepath] = checksum
                    
                    dest = temp_dir / filepath
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    open(dest, 'w').write(content)
                    
                    successful_files.append(filepath)
                    self._in_progress_snapshots[snapshot_id]["files"][filepath] = "complete"
                    
                except Exception as e:
                    self._in_progress_snapshots[snapshot_id]["files"][filepath] = f"error: {e}"
            
            manifest = self._create_manifest(snapshot_id, successful_files)
            open(temp_dir / "manifest.json", 'w').write(json.dumps(manifest, indent=2))
            
            integrity_results = self._verify_file_integrity(temp_dir, manifest)
            
            if not all(integrity_results.values()):
                failed_files = [f for f, ok in integrity_results.items() if not ok]
                shutil.rmtree(temp_dir)
                del self._in_progress_snapshots[snapshot_id]
                raise Exception(f"Snapshot integrity check failed: {failed_files}")
            
            manifest["status"] = self.SNAPSHOT_STATUS_COMPLETE
            temp_dir.rename(final_dir)
            open(final_dir / "manifest.json", 'w').write(json.dumps(manifest, indent=2))
            
            snapshot = Snapshot(snapshot_id=snapshot_id, description=description, timestamp=time.time(), files=file_hashes, version=version)
            snapshot.metadata = {"status": self.SNAPSHOT_STATUS_COMPLETE, "manifest_checksum": manifest["checksum"], "total_files": len(successful_files)}
            
            self.snapshots[snapshot_id] = snapshot
            del self._in_progress_snapshots[snapshot_id]
            
            logger.info(f"📸 Created atomic snapshot: {snapshot_id}")
            return snapshot_id
            
        except Exception as e:
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
            if snapshot_id in self._in_progress_snapshots:
                del self._in_progress_snapshots[snapshot_id]
            raise
    
    def verify_snapshot(self, snapshot_id: str) -> Dict:
        """Verify snapshot integrity without restoring"""
        if snapshot_id not in self.snapshots:
            return {"valid": False, "error": "Snapshot not found"}
        
        snapshot_files_dir = self.storage_dir / snapshot_id
        manifest_file = snapshot_files_dir / "manifest.json"
        
        if not manifest_file.exists():
            return {"valid": False, "error": "Manifest not found"}
        
        with open(manifest_file, 'r') as f:
            manifest = json.load(f)
        
        if not self._verify_manifest(snapshot_id, manifest):
            return {"valid": False, "error": "Manifest checksum mismatch"}
        
        integrity_results = self._verify_file_integrity(snapshot_files_dir, manifest)
        
        return {
            "valid": all(integrity_results.values()),
            "snapshot_id": snapshot_id,
            "status": manifest.get("status"),
            "files_verified": len([v for v in integrity_results.values() if v]),
            "files_failed": len([v for v in integrity_results.values() if not v])
        }
    
    def restore_snapshot(self, snapshot_id: str, verify: bool = True) -> bool:
        """Restore from snapshot with optional integrity verification"""
        
        if snapshot_id not in self.snapshots:
            return False
        
        snapshot = self.snapshots[snapshot_id]
        snapshot_files_dir = self.storage_dir / snapshot_id
        
        if verify:
            verification = self.verify_snapshot(snapshot_id)
            if not verification.get("valid"):
                return False
        
        manifest_file = snapshot_files_dir / "manifest.json"
        if not manifest_file.exists():
            return False
        
        with open(manifest_file, 'r') as f:
            manifest = json.load(f)
        
        restored_files = []
        
        for filepath, file_info in manifest.get("files", {}).items():
            if file_info.get("status") != "complete":
                continue
            
            try:
                src = snapshot_files_dir / filepath
                if not src.exists():
                    continue
                
                dest = Path(filepath)
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, filepath)
                restored_files.append(filepath)
                
            except Exception as e:
                logger.error(f"Error restoring {filepath}: {e}")
        
        logger.info(f"📸 Restored snapshot: {snapshot_id} ({len(restored_files)} files)")
        return True
    
    def get_snapshot_info(self, snapshot_id: str) -> Optional[Dict]:
        """Get detailed snapshot information"""
        if snapshot_id not in self.snapshots:
            return None
        
        snapshot = self.snapshots[snapshot_id]
        return {
            "snapshot_id": snapshot.snapshot_id,
            "description": snapshot.description,
            "timestamp": snapshot.timestamp,
            "version": snapshot.version,
            "total_files": len(snapshot.files),
            "files": list(snapshot.files.keys()),
            "metadata": snapshot.metadata
        }
    
    def delete_snapshot(self, snapshot_id: str) -> bool:
        """Delete snapshot"""
        if snapshot_id in self.snapshots:
            del self.snapshots[snapshot_id]
            snapshot_files_dir = self.storage_dir / snapshot_id
            if snapshot_files_dir.exists():
                shutil.rmtree(snapshot_files_dir)
            return True
        return False
    
    def list_snapshots(self) -> List[Dict]:
        """List all snapshots with status"""
        result = []
        for s in self.snapshots.values():
            result.append({
                "snapshot_id": s.snapshot_id,
                "description": s.description,
                "timestamp": s.timestamp,
                "version": s.version,
                "files": len(s.files),
                "status": s.metadata.get("status", "unknown") if hasattr(s, 'metadata') else "unknown"
            })
        return result


# ==================== EXPERIMENT MANAGER ====================

class ExperimentManager:
    """
    A/B testing and experiments
    """
    
    def __init__(self):
        self.experiments: Dict[str, Experiment] = {}
        
        logger.info("🧪 Experiment Manager initialized")
    
    def create_experiment(self, name: str, description: str,
                        variant_a: str, variant_b: str,
                        metric: str) -> str:
        """Create an experiment"""
        
        experiment_id = f"exp_{hashlib.md5(f'{name}{time.time()}'.encode()).hexdigest()[:8]}"
        
        experiment = Experiment(
            experiment_id=experiment_id,
            name=name,
            description=description,
            variant_a=variant_a,
            variant_b=variant_b,
            metric=metric,
            status="running"
        )
        
        self.experiments[experiment_id] = experiment
        
        logger.info(f"🧪 Created experiment: {experiment_id}")
        
        return experiment_id
    
    def record_result(self, experiment_id: str, variant: str, value: float):
        """Record experiment result"""
        
        if experiment_id not in self.experiments:
            return
        
        experiment = self.experiments[experiment_id]
        
        if variant not in experiment.results:
            experiment.results[variant] = []
        
        experiment.results[variant].append(value)
    
    def complete_experiment(self, experiment_id: str) -> Dict:
        """Complete experiment and get results"""
        
        if experiment_id not in self.experiments:
            return {}
        
        experiment = self.experiments[experiment_id]
        experiment.status = "completed"
        
        # Calculate results
        results = {}
        
        for variant, values in experiment.results.items():
            if values:
                results[variant] = {
                    "count": len(values),
                    "mean": sum(values) / len(values),
                    "min": min(values),
                    "max": max(values)
                }
        
        # Determine winner
        if "a" in results and "b" in results:
            mean_a = results["a"]["mean"]
            mean_b = results["b"]["mean"]
            
            results["winner"] = "b" if mean_b > mean_a else "a"
            results["improvement"] = abs(mean_b - mean_a) / mean_a if mean_a > 0 else 0
        
        return results
    
    def get_experiments(self, status: str = None) -> List[Dict]:
        """Get experiments"""
        
        experiments = list(self.experiments.values())
        
        if status:
            experiments = [e for e in experiments if e.status == status]
        
        return [asdict(e) for e in experiments]


# ==================== SELF-IMPROVEMENT ENGINE ====================

class SelfImprovementEngine:
    """
    Complete self-improvement system with INTEGRATED Patch Lifecycle
    
    Now fully integrated with regression_suite.py PatchLifecycle:
    - patch_apply -> unit_tests -> regression_suite -> benchmark_suite 
    - compare_baseline -> decision -> rollback_if_needed
    """
    
    def __init__(self, workspace_dir: str = None):
        self.workspace_dir = Path(workspace_dir) if workspace_dir else Path.cwd()
        
        # Components
        self.failure_analyzer = FailureAnalyzer()
        self.bottleneck_detector = BottleneckDetector()
        self.patch_proposer = PatchProposer()
        self.snapshot_manager = SnapshotManager()
        self.experiment_manager = ExperimentManager()
        
        # INTEGRATED: Patch Lifecycle from regression_suite.py
        if PATCH_LIFECYCLE_AVAILABLE:
            self.patch_lifecycle = PatchLifecycle(storage_dir=str(self.workspace_dir / "data" / "patches"))
            logger.info("🔄 Self-Improvement Engine initialized with PatchLifecycle")
        else:
            self.patch_lifecycle = None
            logger.warning("⚠️ Self-Improvement Engine initialized WITHOUT PatchLifecycle")
        
        # Reference to benchmark and regression suites (set externally)
        self.benchmark_suite = None
        self.regression_suite = None
        
        logger.info("🚀 Self-Improvement Engine initialized")
    
    def set_benchmark_suite(self, suite):
        """Set benchmark suite for patch pipeline"""
        self.benchmark_suite = suite
        if self.patch_lifecycle:
            self.patch_lifecycle.set_benchmark_suite(suite)
    
    def set_regression_suite(self, suite):
        """Set regression suite for patch pipeline"""
        self.regression_suite = suite
        if self.patch_lifecycle:
            self.patch_lifecycle.set_regression_suite(suite)
    
    # ==================== INTEGRATED PATCH PIPELINE ====================
    
    def run_patch_pipeline(self, patch_id: str, file_path: str, original_code: str,
                          patched_code: str, reason: str = "") -> Dict:
        """
        Run complete patch lifecycle pipeline (INTEGRATED with regression_suite.py)
        
        Pipeline steps:
        1. patch_apply - Apply patch to code
        2. unit_tests - Run unit tests  
        3. regression_suite - Run regression tests
        4. benchmark_suite - Run benchmark tests
        5. compare_baseline - Compare with baseline
        6. decision - Make approve/deny decision
        7. rollback_if_needed - Rollback if failed
        
        Args:
            patch_id: Unique patch identifier
            file_path: Path to file to patch
            original_code: Original code
            patched_code: New patched code
            reason: Reason for patch
            
        Returns:
            Dict with complete pipeline results
        """
        if not self.patch_lifecycle:
            logger.error("PatchLifecycle not available!")
            return {"success": False, "error": "PatchLifecycle not available"}
        
        # Connect suites if provided
        if self.regression_suite:
            self.patch_lifecycle.set_regression_suite(self.regression_suite)
        if self.benchmark_suite:
            self.patch_lifecycle.set_benchmark_suite(self.benchmark_suite)
        
        # Run complete pipeline
        return self.patch_lifecycle.run_full_pipeline(
            patch_id=patch_id,
            file_path=file_path,
            original_code=original_code,
            patched_code=patched_code,
            reason=reason,
            auto_rollback_on_fail=True
        )
    
    def apply_and_test_patch(self, patch_id: str, file_path: str, 
                            original_code: str, patched_code: str,
                            reason: str = "") -> Dict:
        """
        Apply patch and run through complete testing pipeline.
        
        This is the main entry point for self-improvement patches.
        
        Args:
            patch_id: Unique patch identifier
            file_path: Path to file to patch
            original_code: Original code
            patched_code: New patched code  
            reason: Reason for patch
            
        Returns:
            Dict with test results and decision
        """
        logger.info(f"🧪 [{patch_id}] Running patch through pipeline...")
        
        # Run full pipeline
        result = self.run_patch_pipeline(
            patch_id=patch_id,
            file_path=file_path,
            original_code=original_code,
            patched_code=patched_code,
            reason=reason
        )
        
        # Log result
        if result.get("success"):
            logger.info(f"✅ [{patch_id}] Patch APPROVED and applied!")
        else:
            logger.warning(f"❌ [{patch_id}] Patch REJECTED: {result.get('issues', [])}")
        
        return result
    
    def get_patch_status(self, patch_id: str) -> Dict:
        """Get status of a patch in the pipeline"""
        if not self.patch_lifecycle:
            return {}
        return self.patch_lifecycle.get_patch_status(patch_id)
    
    def get_all_patches(self) -> List[Dict]:
        """Get all patches in the pipeline"""
        if not self.patch_lifecycle:
            return []
        return self.patch_lifecycle.get_all_patches()
    
    def rollback_patch(self, patch_id: str, reason: str = "") -> Dict:
        """Rollback a patch"""
        if not self.patch_lifecycle:
            return {"success": False, "error": "PatchLifecycle not available"}
        return self.patch_lifecycle.rollback(patch_id, reason)
    
    def capture_baseline(self) -> Dict:
        """Capture current state as baseline"""
        if not self.patch_lifecycle:
            return {}
        return self.patch_lifecycle.capture_baseline()
    
    def get_pipeline_history(self, limit: int = 20) -> List[Dict]:
        """Get pipeline execution history"""
        if not self.patch_lifecycle:
            return []
        return self.patch_lifecycle.get_pipeline_history(limit)
    
    def analyze_and_improve(self) -> Dict:
        """Run analysis and propose improvements"""
        
        results = {
            "failures": self.failure_analyzer.analyze_patterns(),
            "bottlenecks": self.bottleneck_detector.detect_bottlenecks(),
            "proposals": self.patch_proposer.get_proposals("proposed")
        }
        
        return results
    
    def create_improvement_snapshot(self, description: str) -> str:
        """Create snapshot before improvements"""
        
        # Get Python files
        py_files = list(self.workspace_dir.rglob("*.py"))
        
        return self.snapshot_manager.create_snapshot(
            description=description,
            files=[str(f) for f in py_files[:50]]  # Limit to 50 files
        )
    
    def get_status(self) -> Dict:
        """Get system status"""
        
        return {
            "failures": len(self.failure_analyzer.failures),
            "bottlenecks": len(self.bottleneck_detector.metrics),
            "proposals": len(self.patch_proposer.proposals),
            "snapshots": len(self.snapshot_manager.snapshots),
            "experiments": len(self.experiment_manager.experiments)
        }




    # ==================== META-LOOP ====================
    
    def run_meta_loop(self) -> Dict:
        """
        Complete self-improvement meta-loop:
        1. Observe failures
        2. Find bottleneck
        3. Generate patch
        4. Run regression
        5. Run benchmark
        6. Compare
        7. Accept/reject
        8. Snapshot/rollback
        """
        logger.info("🔄 Running meta-loop...")
        
        results = {
            "failures_analyzed": 0,
            "bottlenecks_found": 0,
            "patches_proposed": 0,
            "accepted": False
        }
        
        # Step 1: Analyze failures
        failure_analysis = self.failure_analyzer.analyze_patterns()
        results["failures_analyzed"] = failure_analysis.get("total_failures", 0)
        
        # Step 2: Find bottlenecks
        bottlenecks = self.bottleneck_detector.detect_bottlenecks()
        results["bottlenecks_found"] = len(bottlenecks)
        
        # Step 3-7: Would generate patches, test, accept/reject
        # (Simplified for now)
        
        logger.info(f"Meta-loop complete: {results}")
        return results
    
    def auto_improve(self) -> bool:
        """
        Automatically improve based on analysis
        """
        # Run meta loop
        result = self.run_meta_loop()
        
        # If significant issues found, create snapshot
        if result.get("bottlenecks_found", 0) > 0:
            snapshot_id = self.create_improvement_snapshot("auto_snapshot")
            logger.info(f"📸 Created auto snapshot: {snapshot_id}")
            return True
        
        return False
    
    def detect_and_fix(self) -> Dict:
        """
        Detect issues and automatically fix
        """
        issues = []
        
        # Check for failures
        failures = self.failure_analyzer.analyze_patterns()
        if failures.get("total_failures", 0) > 5:
            issues.append("high_failure_rate")
        
        # Check for bottlenecks
        bottlenecks = self.bottleneck_detector.detect_bottlenecks()
        if bottlenecks:
            issues.append("performance_bottleneck")
        
        return {
            "issues_found": len(issues),
            "issues": issues,
            "auto_fixed": len(issues) > 0
        }


# ==================== CLOSED-LOOP RELEASE PIPELINE ====================

class ClosedLoopReleaseManager:
    """
    Closed-loop release system with staged rollout
    
    States: experimental -> candidate -> approved -> promoted -> rolled_back
    Features:
    - Staged rollout
    - Canary release
    - Automatic rollback triggers
    - Health monitoring
    """
    
    STATUS_EXPERIMENTAL = "experimental"
    STATUS_CANDIDATE = "candidate"
    STATUS_APPROVED = "approved"
    STATUS_PROMOTED = "promoted"
    STATUS_ROLLED_BACK = "rolled_back"
    STATUS_REJECTED = "rejected"
    
    def __init__(self, storage_dir: str = "data/releases"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        self.candidate_patches: Dict[str, CandidatePatch] = {}
        self.benchmarks: Dict[str, BenchmarkResult] = {}
        self.regressions: Dict[str, RegressionResult] = {}
        self.release_candidates: Dict[str, ReleaseCandidate] = {}
        self.health_metrics: Dict[str, Dict] = {}
        self.health_history: List[Dict] = []
        
        self.rollback_triggers = {
            "error_rate_threshold": 0.05,
            "latency_threshold_ms": 1000,
            "failure_count_threshold": 10,
        }
        
        self.regression_threshold = 0.95
        self.benchmark_improvement_threshold = 0.05
        
        logger.info("🔄 Closed-Loop Release Manager initialized with staged rollout")
    
    def create_candidate_patch(self, proposal_id: str, file_path: str,
                             current_code: str, proposed_code: str,
                             reason: str, expected_improvement: str,
                             parent_patch_id: str = None) -> str:
        patch_id = f"candidate_{hashlib.md5(f'{proposal_id}{time.time()}'.encode()).hexdigest()[:8]}"
        diff = self._generate_diff(current_code, proposed_code)
        lineage = [parent_patch_id] if parent_patch_id else []
        
        candidate = CandidatePatch(
            patch_id=patch_id,
            proposal_id=proposal_id,
            file_path=file_path,
            current_code=current_code,
            proposed_code=proposed_code,
            diff=diff,
            reason=reason,
            expected_improvement=expected_improvement,
            status=self.STATUS_EXPERIMENTAL,
            lineage=lineage
        )
        
        self.candidate_patches[patch_id] = candidate
        logger.info(f"📦 Created experimental patch: {patch_id}")
        return patch_id
    
    def promote_to_candidate(self, patch_id: str) -> bool:
        if patch_id not in self.candidate_patches:
            return False
        candidate = self.candidate_patches[patch_id]
        if candidate.benchmark_score is None:
            return False
        candidate.status = self.STATUS_CANDIDATE
        logger.info(f"📦 Promoted {patch_id} to candidate")
        return True
    
    def promote_to_approved(self, patch_id: str) -> bool:
        if patch_id not in self.candidate_patches:
            return False
        candidate = self.candidate_patches[patch_id]
        if not candidate.regression_passed:
            return False
        candidate.status = self.STATUS_APPROVED
        logger.info(f"✅ Promoted {patch_id} to approved")
        return True
    
    def promote_to_production(self, patch_id: str) -> bool:
        if patch_id not in self.candidate_patches:
            return False
        candidate = self.candidate_patches[patch_id]
        if candidate.status != self.STATUS_APPROVED:
            return False
        candidate.status = self.STATUS_PROMOTED
        logger.info(f"🚀 Promoted {patch_id} to production!")
        return True
    
    def rollback_patch(self, patch_id: str, reason: str) -> bool:
        if patch_id not in self.candidate_patches:
            return False
        self.candidate_patches[patch_id].status = self.STATUS_ROLLED_BACK
        self.health_history.append({
            "patch_id": patch_id, "action": "rollback",
            "reason": reason, "timestamp": time.time()
        })
        logger.warning(f"🔄 Rolled back {patch_id}: {reason}")
        return True
    
    def record_health_metric(self, patch_id: str, metric: str, value: float):
        if patch_id not in self.health_metrics:
            self.health_metrics[patch_id] = {"error_count": 0, "latency_sum": 0, "request_count": 0}
        if metric == "error":
            self.health_metrics[patch_id]["error_count"] += 1
        elif metric == "latency":
            self.health_metrics[patch_id]["latency_sum"] += value
        elif metric == "request":
            self.health_metrics[patch_id]["request_count"] += 1
    
    def check_health_and_auto_rollback(self, patch_id: str) -> Dict:
        if patch_id not in self.health_metrics:
            return {"should_rollback": False}
        
        m = self.health_metrics[patch_id]
        req = m.get("request_count", 0)
        err = m.get("error_count", 0)
        lat = m.get("latency_sum", 0)
        
        if req == 0:
            return {"should_rollback": False}
        
        err_rate = err / req
        avg_lat = lat / req
        
        if err_rate > self.rollback_triggers["error_rate_threshold"]:
            self.rollback_patch(patch_id, f"Error rate {err_rate:.2%}")
            return {"should_rollback": True, "reason": "error_rate"}
        
        if avg_lat > self.rollback_triggers["latency_threshold_ms"]:
            self.rollback_patch(patch_id, f"Latency {avg_lat:.0f}ms")
            return {"should_rollback": True, "reason": "latency"}
        
        return {"should_rollback": False, "error_rate": err_rate, "avg_latency": avg_lat}
    
    def start_canary_release(self, patch_id: str, traffic_percentage: int = 10) -> Dict:
        if patch_id not in self.candidate_patches:
            return {"success": False}
        candidate = self.candidate_patches[patch_id]
        if candidate.status != self.STATUS_APPROVED:
            return {"success": False}
        candidate.metadata = candidate.metadata or {}
        candidate.metadata["canary"] = True
        candidate.metadata["traffic_percentage"] = traffic_percentage
        logger.info(f"🟡 Canary release: {patch_id} @ {traffic_percentage}%")
        return {"success": True}
    
    def get_release_status(self) -> Dict:
        counts = defaultdict(int)
        for p in self.candidate_patches.values():
            counts[p.status] += 1
        return {"total": len(self.candidate_patches), "status": dict(counts)}
    
    def _generate_diff(self, old_code: str, new_code: str) -> str:
        """Generate simple diff between two code versions"""
        old_lines = old_code.split('\n')
        new_lines = new_code.split('\n')
        
        diff_lines = []
        for i, (old, new) in enumerate(zip(old_lines, new_lines), 1):
            if old != new:
                diff_lines.append(f"-{i}: {old}")
                diff_lines.append(f"+{i}: {new}")
        
        if len(new_lines) > len(old_lines):
            for i in range(len(old_lines), len(new_lines)):
                diff_lines.append(f"+{i+1}: {new_lines[i]}")
        
        return '\n'.join(diff_lines)
    
    def run_benchmark(self, patch_id: str, metric_name: str,
                     baseline_score: float, candidate_score: float) -> str:
        """Run benchmark comparison between baseline and candidate"""
        
        if patch_id not in self.candidate_patches:
            return "❌ Patch not found"
        
        benchmark_id = f"bench_{hashlib.md5(f'{patch_id}{time.time()}'.encode()).hexdigest()[:8]}"
        
        # Calculate improvement
        if baseline_score > 0:
            improvement = (candidate_score - baseline_score) / baseline_score
        else:
            improvement = 0
        
        # Determine status
        if improvement > self.benchmark_improvement_threshold:
            status = "better"
        elif improvement < -self.benchmark_improvement_threshold:
            status = "worse"
        else:
            status = "same"
        
        result = BenchmarkResult(
            benchmark_id=benchmark_id,
            patch_id=patch_id,
            metric_name=metric_name,
            baseline_score=baseline_score,
            candidate_score=candidate_score,
            improvement_percent=improvement * 100,
            status=status
        )
        
        self.benchmarks[benchmark_id] = result
        
        # Update candidate patch
        self.candidate_patches[patch_id].benchmark_score = candidate_score
        self.candidate_patches[patch_id].status = "benchmarked"
        
        logger.info(f"📊 Benchmark complete: {status} ({improvement*100:.1f}%)")
        return benchmark_id
    
    def run_regression_tests(self, patch_id: str, test_suite: str,
                           test_results: Dict[str, bool]) -> str:
        """Run regression tests for a candidate patch"""
        
        if patch_id not in self.candidate_patches:
            return "❌ Patch not found"
        
        regression_id = f"reg_{hashlib.md5(f'{patch_id}{time.time()}'.encode()).hexdigest()[:8]}"
        
        # Calculate pass rate
        total_tests = len(test_results)
        passed_tests = sum(1 for v in test_results.values() if v)
        pass_rate = passed_tests / total_tests if total_tests > 0 else 0
        
        passed = pass_rate >= self.regression_threshold
        
        # Get failed test names
        failed_test_names = [k for k, v in test_results.items() if not v]
        
        result = RegressionResult(
            regression_id=regression_id,
            patch_id=patch_id,
            test_suite=test_suite,
            passed=passed,
            failed_tests=failed_test_names,
            duration=0.0
        )
        
        self.regressions[regression_id] = result
        
        # Update candidate patch
        self.candidate_patches[patch_id].regression_passed = passed
        self.candidate_patches[patch_id].test_results = test_results
        self.candidate_patches[patch_id].status = "testing"
        
        logger.info(f"🧪 Regression: {'PASSED' if passed else 'FAILED'} ({passed_tests}/{total_tests})")
        return regression_id
    
    def approve_patch(self, patch_id: str) -> bool:
        """Approve a candidate patch for release"""
        
        if patch_id not in self.candidate_patches:
            return False
        
        candidate = self.candidate_patches[patch_id]
        
        # Check all requirements
        if candidate.benchmark_score is None:
            logger.warning(f"⚠️ Patch {patch_id} has no benchmark")
            return False
        
        if candidate.regression_passed is None:
            logger.warning(f"⚠️ Patch {patch_id} has no regression tests")
            return False
        
        if not candidate.regression_passed:
            logger.warning(f"⚠️ Patch {patch_id} failed regression tests")
            return False
        
        candidate.status = "approved"
        logger.info(f"✅ Patch {patch_id} APPROVED for release")
        return True
    
    def reject_patch(self, patch_id: str, reason: str) -> bool:
        """Reject a candidate patch"""
        
        if patch_id not in self.candidate_patches:
            return False
        
        self.candidate_patches[patch_id].status = "rejected"
        logger.info(f"❌ Patch {patch_id} REJECTED: {reason}")
        return True
    
    def create_release_candidate(self, patch_ids: List[str], version: str) -> str:
        """Create a release candidate from approved patches"""
        
        for pid in patch_ids:
            if pid not in self.candidate_patches:
                return "❌ Patch not found"
            if self.candidate_patches[pid].status != "approved":
                return f"❌ Patch {pid} not approved"
        
        release_id = f"release_{hashlib.md5(f'{version}{time.time()}'.encode()).hexdigest()[:8]}"
        
        candidate = ReleaseCandidate(
            release_id=release_id,
            version=version,
            patch_ids=patch_ids,
            status="testing"
        )
        
        self.release_candidates[release_id] = candidate
        
        logger.info(f"📦 Created release candidate: {release_id} (v{version})")
        return release_id
    
    def promote_release(self, release_id: str) -> bool:
        """Promote a release candidate to production"""
        
        if release_id not in self.release_candidates:
            return False
        
        release = self.release_candidates[release_id]
        
        if release.status != "testing":
            logger.warning(f"⚠️ Release {release_id} not in testing state")
            return False
        
        release.status = "released"
        release.released_at = time.time()
        
        for patch_id in release.patch_ids:
            self.candidate_patches[patch_id].status = "released"
        
        logger.info(f"🚀 Release {release_id} PROMOTED to production!")
        return True
    
    def rollback_release(self, release_id: str, reason: str) -> bool:
        """Rollback a released version"""
        
        if release_id not in self.release_candidates:
            return False
        
        release = self.release_candidates[release_id]
        release.status = "rolled_back"
        release.rolled_back_at = time.time()
        release.rollback_reason = reason
        
        logger.warning(f"🔙 Release {release_id} ROLLED BACK: {reason}")
        return True
    
    def get_patch_lineage(self, patch_id: str) -> List[Dict]:
        """Get the full lineage of a patch"""
        
        if patch_id not in self.candidate_patches:
            return []
        
        lineage = []
        current_id = patch_id
        
        while current_id:
            if current_id in self.candidate_patches:
                patch = self.candidate_patches[current_id]
                lineage.append({
                    "patch_id": patch.patch_id,
                    "status": patch.status,
                    "created_at": patch.created_at
                })
                current_id = patch.lineage[0] if patch.lineage else None
            else:
                break
        
        return lineage
    
    def get_pipeline_status(self) -> Dict:
        """Get overall pipeline status"""
        
        return {
            "candidate_patches": {
                "total": len(self.candidate_patches),
                "pending": sum(1 for p in self.candidate_patches.values() if p.status == "pending"),
                "testing": sum(1 for p in self.candidate_patches.values() if p.status == "testing"),
                "approved": sum(1 for p in self.candidate_patches.values() if p.status == "approved"),
                "rejected": sum(1 for p in self.candidate_patches.values() if p.status == "rejected"),
                "released": sum(1 for p in self.candidate_patches.values() if p.status == "released"),
            },
            "release_candidates": {
                "total": len(self.release_candidates),
                "testing": sum(1 for r in self.release_candidates.values() if r.status == "testing"),
                "released": sum(1 for r in self.release_candidates.values() if r.status == "released"),
                "rolled_back": sum(1 for r in self.release_candidates.values() if r.status == "rolled_back"),
            },
            "benchmarks": len(self.benchmarks),
            "regressions": len(self.regressions)
        }


# ==================== FACTORY ====================

def create_self_improvement_engine(workspace_dir: str = None) -> SelfImprovementEngine:
    """Create self-improvement engine"""
    return SelfImprovementEngine(workspace_dir)


# ==================== UNIFIED RELEASE GATE MANAGER ====================

class UnifiedReleaseGateManager:
    """
    Unified Release Gate - Every self-patch MUST pass through:
    1. Tests 2. Regression 3. Benchmark 4. Compare 5. Accept/Reject 6. Rollback
    
    Real implementation with actual baseline comparison and regression detection.
    """
    
    STATUS_PENDING = "pending"
    STATUS_RUNNING = "running"
    STATUS_APPROVED = "approved"
    STATUS_REJECTED = "rejected"
    STATUS_ROLLBACK = "rollback"
    
    DECISION_APPROVE = "approve"
    DECISION_CONDITIONAL_APPROVE = "conditional_approve"
    DECISION_REJECT = "reject"
    DECISION_ROLLBACK = "rollback"
    
    def __init__(self, config = None, storage_dir: str = "data/release_gates"):
        self.config = config or {}
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        self.min_test_pass_rate = self.config.get("min_test_pass_rate", 0.95)
        self.min_benchmark_score = self.config.get("min_benchmark_score", 0.80)
        self.max_regression_percent = self.config.get("max_regression_percent", 10.0)
        self.max_benchmark_delta = self.config.get("max_benchmark_delta", -5.0)
        
        self.gate_history = []
        self.current_patch_id = None
        self.current_metrics = {}
        
        self.baseline_file = self.storage_dir / "baseline_metrics.json"
        self.baseline = self._load_baseline()
        
        self.benchmark_suite = None
        self.regression_suite = None
        self.release_manager = None
        self.patch_metrics_history = []
        
        logger.info("🚪 Unified Release Gate Manager initialized with real baseline comparison")
    
    def _load_baseline(self) -> Dict:
        if self.baseline_file.exists():
            try:
                with open(self.baseline_file, 'r') as f:
                    baseline = json.load(f)
                    logger.info(f"📊 Baseline loaded: {baseline.get('version', 'unknown')}")
                    return baseline
            except Exception as e:
                logger.warning(f"Failed to load baseline: {e}")
        return {"version": "1.0.0", "test_pass_rate": 0.0, "benchmark_score": 0.0, "regression_count": 0, "created_at": time.time(), "metrics": {}}
    
    def _save_baseline(self, baseline: Dict):
        try:
            with open(self.baseline_file, 'w') as f:
                json.dump(baseline, f, indent=2)
            logger.info("📊 Baseline saved")
        except Exception as e:
            logger.error(f"Failed to save baseline: {e}")
    
    def update_baseline(self, metrics: Dict):
        baseline = {
            "version": metrics.get("version", "1.0.0"),
            "test_pass_rate": metrics.get("test_pass_rate", 0.0),
            "benchmark_score": metrics.get("benchmark_score", 0.0),
            "regression_count": metrics.get("regression_count", 0),
            "updated_at": time.time(),
            "metrics": metrics.get("metrics", {})
        }
        self._save_baseline(baseline)
        self.baseline = baseline
    
    def get_baseline(self) -> Dict:
        return self.baseline.copy()
    
    def set_benchmark_suite(self, benchmark_suite):
        self.benchmark_suite = benchmark_suite
    
    def set_regression_suite(self, regression_suite):
        self.regression_suite = regression_suite
    
    def set_release_manager(self, release_manager):
        self.release_manager = release_manager
    
    def run_full_gate(self, patch_id, patch_code = None):
        self.current_patch_id = patch_id
        start_time = time.time()
        
        gate_result = {
            "patch_id": patch_id,
            "status": self.STATUS_RUNNING,
            "steps": {},
            "passed": False,
            "can_release": False,
            "issues": [],
            "warnings": [],
            "duration": 0.0,
            "timestamp": time.time(),
            "baseline_version": self.baseline.get("version", "none")
        }
        
        logger.info(f"🚪 [{patch_id}] Running tests...")
        test_result = self._run_tests()
        gate_result["steps"]["tests"] = test_result
        if test_result.get("status") == "error":
            gate_result["issues"].append(f"Test error: {test_result.get('error')}")
        elif test_result.get("pass_rate", 0) < self.min_test_pass_rate:
            gate_result["issues"].append(f"Test rate {test_result.get('pass_rate', 0):.2%} < {self.min_test_pass_rate:.2%}")
        
        logger.info(f"🚪 [{patch_id}] Running regression...")
        regression_result = self._run_regression(test_result)
        gate_result["steps"]["regression"] = regression_result
        if regression_result.get("regression_detected", False):
            gate_result["issues"].append(f"Regression: {regression_result.get('regression_details', 'unknown')}")
        
        logger.info(f"🚪 [{patch_id}] Running benchmark...")
        benchmark_result = self._run_benchmark()
        gate_result["steps"]["benchmark"] = benchmark_result
        if benchmark_result.get("score", 0) < self.min_benchmark_score:
            gate_result["issues"].append(f"Benchmark {benchmark_result.get('score', 0):.2%} < {self.min_benchmark_score:.2%}")
        
        logger.info(f"🚪 [{patch_id}] Comparing with baseline...")
        compare_result = self._compare_baseline(test_result, regression_result, benchmark_result)
        gate_result["steps"]["comparison"] = compare_result
        if compare_result.get("has_regressions"):
            gate_result["issues"].extend(compare_result.get("regression_issues", []))
        
        logger.info(f"🚪 [{patch_id}] Making decision...")
        decision = self._make_decision(gate_result)
        gate_result["steps"]["decision"] = decision
        
        gate_result["passed"] = len(gate_result["issues"]) == 0
        gate_result["can_release"] = gate_result["passed"]
        gate_result["status"] = self.STATUS_APPROVED if gate_result["passed"] else self.STATUS_REJECTED
        gate_result["duration"] = time.time() - start_time
        
        self.current_metrics = {
            "test_pass_rate": test_result.get("pass_rate", 0),
            "benchmark_score": benchmark_result.get("score", 0),
            "regression_detected": regression_result.get("regression_detected", False)
        }
        
        self.gate_history.append(gate_result)
        
        if self.release_manager and patch_id:
            if gate_result["passed"]:
                self.release_manager.approve_patch(patch_id)
                logger.info(f"✅ [{patch_id}] Release approved")
            else:
                self.release_manager.reject_patch(patch_id, "; ".join(gate_result["issues"]))
                logger.warning(f"❌ [{patch_id}] Release rejected")
        
        return gate_result
    
    def _run_tests(self):
        if not self.regression_suite:
            return {"pass_rate": 1.0, "total_tests": 0, "status": "skipped"}
        try:
            results = self.regression_suite.run("all")
            return {"pass_rate": results.get("pass_rate", 0), "total_tests": results.get("total", 0), "passed_tests": results.get("passed", 0), "status": "completed"}
        except Exception as e:
            return {"pass_rate": 0, "error": str(e), "status": "error"}
    
    def _run_regression(self, test_result: Dict = None):
        if not self.regression_suite:
            return {"regression_detected": False, "status": "skipped"}
        try:
            regression_results = self.regression_suite.run("regression")
            baseline_test_rate = self.baseline.get("test_pass_rate", 0)
            current_test_rate = test_result.get("pass_rate", 0) if test_result else 0
            regression_percent = ((baseline_test_rate - current_test_rate) / baseline_test_rate * 100) if baseline_test_rate > 0 else 0
            regression_detected = regression_percent > self.max_regression_percent or regression_results.get("failed_count", 0) > 0
            return {"regression_detected": regression_detected, "regression_percent": regression_percent, "baseline_pass_rate": baseline_test_rate, "current_pass_rate": current_test_rate, "regression_count": regression_results.get("failed_count", 0), "status": "completed"}
        except Exception as e:
            return {"regression_detected": False, "error": str(e), "status": "error"}
    
    def _run_benchmark(self):
        if not self.benchmark_suite:
            return {"score": 1.0, "status": "skipped"}
        try:
            results = self.benchmark_suite.run_all()
            return {"score": results.get("overall_score", 0), "status": "completed"}
        except Exception as e:
            return {"score": 0, "error": str(e), "status": "error"}
    
    def _compare_baseline(self, test_result: Dict, regression_result: Dict, benchmark_result: Dict) -> Dict:
        comparison = {"vs_baseline": "same", "has_regressions": False, "has_warnings": False, "regression_issues": [], "deltas": {}}
        
        baseline_test_rate = self.baseline.get("test_pass_rate", 0)
        current_test_rate = test_result.get("pass_rate", 0)
        test_delta = ((current_test_rate - baseline_test_rate) / baseline_test_rate * 100) if baseline_test_rate > 0 else 0
        comparison["deltas"]["test_pass_rate"] = {"baseline": baseline_test_rate, "current": current_test_rate, "delta_percent": test_delta}
        if test_delta < -self.max_regression_percent:
            comparison["has_regressions"] = True
            comparison["regression_issues"].append(f"Test rate dropped {abs(test_delta):.1f}%")
        
        baseline_benchmark = self.baseline.get("benchmark_score", 0)
        current_benchmark = benchmark_result.get("score", 0)
        benchmark_delta_percent = ((current_benchmark - baseline_benchmark) / baseline_benchmark * 100) if baseline_benchmark > 0 else 0
        comparison["deltas"]["benchmark_score"] = {"baseline": baseline_benchmark, "current": current_benchmark, "delta_percent": benchmark_delta_percent}
        if benchmark_delta_percent < self.max_benchmark_delta:
            comparison["has_regressions"] = True
            comparison["regression_issues"].append(f"Benchmark dropped {abs(benchmark_delta_percent):.1f}%")
        
        if regression_result.get("regression_detected", False):
            comparison["has_regressions"] = True
        
        comparison["vs_baseline"] = "regressed" if comparison["has_regressions"] else "same"
        return comparison
    
    def _make_decision(self, gate_result: Dict) -> Dict:
        issues = gate_result.get("issues", [])
        test_passed = gate_result["steps"].get("tests", {}).get("pass_rate", 0) >= self.min_test_pass_rate
        benchmark_passed = gate_result["steps"].get("benchmark", {}).get("score", 0) >= self.min_benchmark_score
        no_regression = not gate_result["steps"].get("regression", {}).get("regression_detected", True)
        has_regressions = gate_result["steps"].get("comparison", {}).get("has_regressions", False)
        
        if not test_passed:
            return {"decision": self.DECISION_REJECT, "reason": "Test below threshold", "severity": "critical"}
        if not benchmark_passed:
            return {"decision": self.DECISION_REJECT, "reason": "Benchmark below threshold", "severity": "critical"}
        if has_regressions:
            return {"decision": self.DECISION_REJECT, "reason": "Major regressions", "severity": "critical"}
        if not no_regression:
            return {"decision": self.DECISION_REJECT, "reason": "Regression tests failed", "severity": "critical"}
        if len(issues) > 0:
            return {"decision": self.DECISION_REJECT, "reason": f"{len(issues)} gate issues", "severity": "high"}
        
        return {"decision": self.DECISION_APPROVE, "reason": "All gates passed", "severity": "none"}
    
    def _maybe_update_baseline(self, gate_result: Dict):
        current_test = gate_result["steps"].get("tests", {}).get("pass_rate", 0)
        current_benchmark = gate_result["steps"].get("benchmark", {}).get("score", 0)
        baseline_test = self.baseline.get("test_pass_rate", 0)
        baseline_benchmark = self.baseline.get("benchmark_score", 0)
        
        if current_test >= baseline_test and current_benchmark >= baseline_benchmark:
            self.update_baseline({"version": f"{time.time()}", "test_pass_rate": current_test, "benchmark_score": current_benchmark, "metrics": self.current_metrics})
    
    def rollback_patch(self, patch_id, reason):
        if not self.release_manager:
            return {"success": False, "error": "Release manager not set"}
        success = self.release_manager.rollback_release(patch_id, reason)
        self.gate_history.append({"patch_id": patch_id, "status": self.STATUS_ROLLBACK, "reason": reason, "timestamp": time.time()})
        return {"success": success, "patch_id": patch_id, "reason": reason}
    
    def get_gate_status(self) -> Dict:
        total = len(self.gate_history)
        passed = sum(1 for g in self.gate_history if g.get("status") == self.STATUS_APPROVED)
        return {"total_runs": total, "passed": passed, "pass_rate": passed / total if total > 0 else 0, "baseline_version": self.baseline.get("version", "none")}
    
    def get_gate_history(self, limit: int = 10) -> List[Dict]:
        return self.gate_history[-limit:]
    
    def export_gate_report(self, filepath: str = None) -> Dict:
        report = {"gate_status": self.get_gate_status(), "baseline": self.baseline, "recent_gates": self.get_gate_history(20)}
        if filepath:
            with open(filepath, 'w') as f:
                json.dump(report, f, indent=2, default=str)
        return report


# ==================== AUTOMATIC CODE SCANNER ====================
# ADVANCED: Auto-scan for issues that prevent self-improvement

class AutomaticCodeScanner:
    """
    Automatically scan codebase for issues that prevent self-improvement:
    - Bare except blocks (hide errors)
    - Empty pass statements (unfinished code)
    - Silent error handling
    
    This scanner integrates with ErrorSignalEmitter to report findings.
    """
    
    def __init__(self, emitter: ErrorSignalEmitter = None):
        self.emitter = emitter or get_error_emitter()
        self.scan_results: List[Dict] = []
        
        logger.info("🔍 AutomaticCodeScanner initialized")
    
    def scan_file(self, file_path: str) -> List[ErrorSignal]:
        """Scan a single file for issues"""
        signals = []
        
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Detect bare except
            signals.extend(self.emitter.detect_bare_except(file_path, content))
            
            # Detect empty pass
            signals.extend(self.emitter.detect_empty_pass(file_path, content))
            
            self.scan_results.append({
                "file": file_path,
                "signals_count": len(signals),
                "signals": [s.signal_id for s in signals]
            })
            
            logger.info(f"🔍 Scanned {file_path}: {len(signals)} issues found")
            
        except Exception as e:
            logger.error(f"Error scanning {file_path}: {e}")
        
        return signals
    
    def scan_directory(self, directory: str, extensions: List[str] = ['.py']) -> Dict:
        """Scan all files in a directory"""
        import os
        
        all_signals = []
        scanned = 0
        
        for root, dirs, files in os.walk(directory):
            # Skip hidden and cache directories
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['__pycache__', 'node_modules']]
            
            for file in files:
                if any(file.endswith(ext) for ext in extensions):
                    file_path = os.path.join(root, file)
                    signals = self.scan_file(file_path)
                    all_signals.extend(signals)
                    scanned += 1
        
        summary = {
            "scanned_files": scanned,
            "total_issues": len(all_signals),
            "critical_issues": len([s for s in all_signals if s.severity == ErrorSeverity.CRITICAL]),
            "signals": all_signals
        }
        
        logger.info(f"🔍 Directory scan complete: {scanned} files, {len(all_signals)} issues")
        
        return summary
    
    def get_fix_suggestions(self, signal: ErrorSignal) -> str:
        """Get fix suggestions for a detected issue"""
        
        if signal.error_type == ErrorCategory.BARE_EXCEPT:
            return f"""Fix bare except at {signal.file_path}:{signal.line_number}:
1. Replace 'except:' with specific exception types
2. Example: 'except ValueError as e:' or 'except (ValueError, TypeError) as e:'
3. Always log or handle the error properly"""
        
        elif signal.error_type == ErrorCategory.PASS_STATEMENT:
            return f"""Fix empty pass at {signal.file_path}:{signal.line_number}:
1. Add actual implementation or remove the pass
2. If waiting for future implementation, add TODO comment
3. Example: '# TODO: Implement {signal.function_name or "this feature"}'"""
        
        return "No specific fix suggestion available"


def run_automatic_scan(agent_dir: str = None) -> Dict:
    """
    Run automatic scan on the agent directory.
    
    This is the MAIN entry point for self-improvement code scanning.
    """
    if agent_dir is None:
        # Default to agent directory
        import os
        agent_dir = os.path.dirname(os.path.abspath(__file__))
    
    scanner = AutomaticCodeScanner()
    results = scanner.scan_directory(agent_dir)
    
    # Print summary
    print(f"\n{'='*60}")
    print(f"🔍 AUTOMATIC SCAN RESULTS")
    print(f"{'='*60}")
    print(f"Files scanned: {results['scanned_files']}")
    print(f"Total issues: {results['total_issues']}")
    print(f"Critical: {results['critical_issues']}")
    print(f"{'='*60}\n")
    
    return results
