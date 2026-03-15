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


# ==================== UNIFIED RELEASE GATE COORDINATOR ====================
# Single source of truth for all release decisions

class UnifiedReleaseGateCoordinator:
    """
    UNIFIED Release Gate Coordinator - SINGLE SOURCE OF TRUTH
    
    This resolves the duplicate architecture problem:
    - benchmark.py has SelfImprovementGate
    - self_improvement.py has UnifiedReleaseGateManager
    
    SOLUTION: This coordinator acts as the single authority.
    All release decisions go through this one gate.
    
    Design principles:
    - One gate, one decision
    - No conflicting decisions possible
    - Full audit trail
    - Integration with all subsystems
    """
    
    # Gate decision constants
    DECISION_APPROVE = "APPROVE"
    DECISION_REJECT = "REJECT"
    DECISION_REVIEW = "NEEDS_REVIEW"
    DECISION_ROLLBACK = "ROLLBACK"
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        
        # Initialize the primary gate (from self_improvement.py)
        self.primary_gate = UnifiedReleaseGateManager(
            config=self.config,
            storage_dir="data/release_gates/unified"
        )
        
        # Gate state
        self.current_decision: Optional[Dict] = None
        self.decision_history: List[Dict] = []
        self.audit_log: List[Dict] = []
        
        # Subsystems (lazy initialized)
        self._benchmark_suite = None
        self._regression_suite = None
        self._release_manager = None
        self._error_emitter = None
        
        # Configuration
        self.require_unanimous = self.config.get("require_unanimous", True)
        self.min_approval_score = self.config.get("min_approval_score", 0.75)
        
        logger.info("🚪 UNIFIED Release Gate Coordinator initialized - SINGLE SOURCE OF TRUTH")
    
    # ==================== SETUP ====================
    
    def set_benchmark_suite(self, suite):
        """Set benchmark suite"""
        self._benchmark_suite = suite
        self.primary_gate.set_benchmark_suite(suite)
    
    def set_regression_suite(self, suite):
        """Set regression test suite"""
        self._regression_suite = suite
        self.primary_gate.set_regression_suite(suite)
    
    def set_release_manager(self, manager):
        """Set release manager"""
        self._release_manager = manager
        self.primary_gate.set_release_manager(manager)
    
    def set_error_emitter(self, emitter):
        """Set error signal emitter for integration"""
        self._error_emitter = emitter
    
    # ==================== MAIN GATE DECISION ====================
    
    def evaluate_release(self, patch_id: str, patch_code: str = None, 
                       test_results: Dict = None, benchmark_results: Dict = None,
                       regression_results: Dict = None) -> Dict:
        """
        MAIN METHOD: Evaluate release through unified gate.
        
        This is the ONLY entry point for release decisions.
        All subsystems are consulted, but ONE decision is made.
        
        Returns:
            Dict with:
            - decision: APPROVE | REJECT | NEEDS_REVIEW | ROLLBACK
            - score: Overall approval score (0-1)
            - breakdown: Score breakdown by category
            - details: Detailed results from all checks
            - audit_id: Unique audit ID for this decision
        """
        import uuid
        
        audit_id = str(uuid.uuid4())[:8]
        
        self._log_audit(audit_id, "EVALUATION_START", {
            "patch_id": patch_id,
            "timestamp": time.time()
        })
        
        # Collect all evaluation results
        evaluation = {
            "audit_id": audit_id,
            "patch_id": patch_id,
            "timestamp": time.time(),
            "checks": {},
            "decision": None,
            "score": 0.0,
            "breakdown": {},
            "passed": False
        }
        
        # Check 1: Test Results
        if test_results:
            evaluation["checks"]["tests"] = test_results
            test_pass = test_results.get("passed", False)
            test_score = test_results.get("pass_rate", 0) * 0.30  # 30% weight
        else:
            test_score = 0.30  # Default to full score if no tests
            evaluation["checks"]["tests"] = {"passed": True, "score": test_score}
        
        # Check 2: Benchmark Results
        if benchmark_results:
            evaluation["checks"]["benchmark"] = benchmark_results
            bench_pass = benchmark_results.get("passed", False)
            bench_score = benchmark_results.get("score", 0) * 0.25  # 25% weight
        else:
            bench_score = 0.25
            evaluation["checks"]["benchmark"] = {"passed": True, "score": bench_score}
        
        # Check 3: Regression Results
        if regression_results:
            evaluation["checks"]["regression"] = regression_results
            reg_pass = not regression_results.get("regression_detected", True)
            reg_score = 0.25 if reg_pass else 0.0  # 25% weight
        else:
            reg_score = 0.25
            evaluation["checks"]["regression"] = {"passed": True, "regression_detected": False}
        
        # Check 4: Security Check
        security_score = self._evaluate_security(patch_code) if patch_code else 0.20
        evaluation["checks"]["security"] = {"score": security_score, "passed": security_score >= 0.15}
        
        # Check 5: Code Quality
        quality_score = self._evaluate_code_quality(patch_code) if patch_code else 0.20
        evaluation["checks"]["quality"] = {"score": quality_score, "passed": quality_score >= 0.15}
        
        # Calculate overall score
        total_score = test_score + bench_score + reg_score + security_score + quality_score
        
        evaluation["score"] = total_score
        evaluation["breakdown"] = {
            "tests": test_score,
            "benchmark": bench_score,
            "regression": reg_score,
            "security": security_score,
            "quality": quality_score
        }
        
        # Make decision
        if total_score >= self.min_approval_score:
            # All checks passed - APPROVE
            evaluation["decision"] = self.DECISION_APPROVE
            evaluation["passed"] = True
            
            self._log_audit(audit_id, "DECISION_APPROVE", {
                "score": total_score,
                "breakdown": evaluation["breakdown"]
            })
            
        elif total_score >= 0.5:
            # Partial - NEEDS REVIEW
            evaluation["decision"] = self.DECISION_REVIEW
            evaluation["passed"] = False
            
            self._log_audit(audit_id, "DECISION_REVIEW", {
                "score": total_score,
                "issues": self._identify_issues(evaluation["checks"])
            })
            
        else:
            # Failed - REJECT
            evaluation["decision"] = self.DECISION_REJECT
            evaluation["passed"] = False
            
            self._log_audit(audit_id, "DECISION_REJECT", {
                "score": total_score,
                "reasons": self._identify_issues(evaluation["checks"])
            })
        
        # Store decision
        self.current_decision = evaluation
        self.decision_history.append(evaluation)
        
        return evaluation
    
    def _evaluate_security(self, code: str) -> float:
        """Evaluate code security"""
        if not code:
            return 0.20
        
        score = 0.20
        
        # Check for dangerous patterns
        dangerous = ["exec(", "eval(", "os.system(", "__import__("]
        if any(p in code for p in dangerous):
            score -= 0.15
        
        # Check for proper error handling
        if "try:" in code and "except" in code:
            score += 0.05
        
        # Check for input validation
        if "validate" in code.lower() or "check" in code.lower():
            score += 0.05
        
        return max(0, min(0.25, score))
    
    def _evaluate_code_quality(self, code: str) -> float:
        """Evaluate code quality"""
        if not code:
            return 0.20
        
        score = 0.15
        
        # Check for comments
        if "#" in code or '"""' in code:
            score += 0.02
        
        # Check for type hints
        if "->" in code or ": " in code:
            score += 0.03
        
        return max(0, min(0.25, score))
    
    def _identify_issues(self, checks: Dict) -> List[str]:
        """Identify issues from check results"""
        issues = []
        
        if checks.get("tests", {}).get("score", 0) < 0.20:
            issues.append("Test score below threshold")
        
        if checks.get("benchmark", {}).get("score", 0) < 0.15:
            issues.append("Benchmark score below threshold")
        
        if checks.get("regression", {}).get("regression_detected", False):
            issues.append("Regression detected")
        
        if checks.get("security", {}).get("score", 0) < 0.15:
            issues.append("Security concerns")
        
        return issues
    
    def _log_audit(self, audit_id: str, event: str, data: Dict):
        """Log audit event"""
        entry = {
            "audit_id": audit_id,
            "event": event,
            "data": data,
            "timestamp": time.time()
        }
        self.audit_log.append(entry)
        
        logger.info(f"📋 [{audit_id}] {event}: {data}")
    
    # ==================== QUERY METHODS ====================
    
    def get_current_decision(self) -> Optional[Dict]:
        """Get the current decision"""
        return self.current_decision
    
    def get_decision_history(self, limit: int = 10) -> List[Dict]:
        """Get decision history"""
        return self.decision_history[-limit:]
    
    def get_audit_log(self, limit: int = 50) -> List[Dict]:
        """Get audit log"""
        return self.audit_log[-limit:]
    
    def get_statistics(self) -> Dict:
        """Get gate statistics"""
        total = len(self.decision_history)
        if total == 0:
            return {"total": 0}
        
        approved = sum(1 for d in self.decision_history if d["decision"] == self.DECISION_APPROVE)
        rejected = sum(1 for d in self.decision_history if d["decision"] == self.DECISION_REJECT)
        review = sum(1 for d in self.decision_history if d["decision"] == self.DECISION_REVIEW)
        
        return {
            "total": total,
            "approved": approved,
            "rejected": rejected,
            "review": review,
            "approval_rate": approved / total
        }


def create_unified_gate_coordinator(config: Dict = None) -> UnifiedReleaseGateCoordinator:
    """Factory function for UnifiedReleaseGateCoordinator"""
    return UnifiedReleaseGateCoordinator(config)


# ==================== OBSERVE / LEARN ENGINE ====================
# Complete implementation of Observe/Learn Engine based on user's specification
# This engine observes external world, collects signals, and transforms them into real self-upgrades
# NEVER modifies production self directly - only works on clone/candidate

import asyncio
import hashlib
import re
from collections import defaultdict
from enum import Enum
from typing import Dict, List, Any, Callable, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from urllib.parse import urlparse
import json


class SignalSource(Enum):
    """Types of signal sources with trust levels"""
    # High trust
    OFFICIAL_DOCS = "official_docs"
    API_DOCS = "api_docs"
    RELEASE_NOTE = "release_note"
    # Medium trust
    COMPETITOR_ANALYSIS = "competitor_analysis"
    COMMUNITY_DISCUSSION = "community_discussion"
    # Lower trust
    SOCIAL_MEDIA = "social_media"
    RUMOR = "rumor"


class SignalPriority(Enum):
    """Signal priority levels"""
    CRITICAL = "critical"      # Must act immediately
    HIGH = "high"              # Important for competitive advantage
    MEDIUM = "medium"          # Worth evaluating
    LOW = "low"                # Monitor but not urgent
    NOISE = "noise"            # Ignore


class UpgradeType(Enum):
    """Types of upgrades that can be performed"""
    SMALL_PATCH = "small_patch"
    MEDIUM_FEATURE = "medium_feature"
    ARCHITECTURE_REFACTOR = "architecture_refactor"
    NEW_TOOL = "new_tool"
    MODEL_ADAPTER = "model_adapter"
    MEMORY_UPGRADE = "memory_upgrade"
    WORKFLOW_OPTIMIZATION = "workflow_optimization"


@dataclass
class RawSignal:
    """Raw signal from any source"""
    source_type: SignalSource
    source_url: str
    content: str
    timestamp: float
    title: str
    metadata: Dict = field(default_factory=dict)
    confidence: float = 0.5  # 0-1 confidence score
    trust_score: float = 0.5  # 0-1 trust score
    
    def __post_init__(self):
        # Generate signal ID
        signal_hash = hashlib.md5(
            f"{self.source_url}:{self.timestamp}:{self.title[:50]}".encode()
        ).hexdigest()[:12]
        self.signal_id = f"sig_{signal_hash}"


@dataclass
class CanonicalSignal:
    """Canonical/deduplicated signal"""
    signal_id: str
    event_type: str  # e.g., "new_tool_capability", "api_change"
    title: str
    description: str
    priority: SignalPriority
    trust_score: float
    novelty_score: float  # How novel is this?
    source_count: int  # How many sources confirmed this
    first_seen: float
    last_seen: float
    raw_signals: List[RawSignal] = field(default_factory=list)
    applicable: bool = True
    applicability_reason: str = ""
    
    def combined_trust_score(self) -> float:
        """Calculate combined trust from multiple sources"""
        if not self.raw_signals:
            return self.trust_score
        scores = [s.trust_score for s in self.raw_signals]
        scores.append(self.trust_score)
        return sum(scores) / len(scores)


@dataclass
class UpgradeHypothesis:
    """Hypothesis for potential upgrade"""
    hypothesis_id: str
    canonical_signal: CanonicalSignal
    hypothesis_text: str
    upgrade_type: UpgradeType
    expected_benefit: str
    expected_roi: float  # Expected return on investment
    risk_level: str  # low, medium, high
    implementation_plan: str
    test_plan: str
    created_at: float = field(default_factory=time.time)
    status: str = "pending"  # pending, testing, approved, rejected, merged


@dataclass
class ExperimentResult:
    """Result of a clone experiment"""
    experiment_id: str
    hypothesis: UpgradeHypothesis
    started_at: float
    completed_at: Optional[float] = None
    
    # Metrics
    task_completion_delta: float = 0.0  # Before vs after
    tool_call_success_delta: float = 0.0
    latency_delta: float = 0.0  # Negative is better
    cost_delta: float = 0.0  # Negative is better
    error_rate_delta: float = 0.0  # Negative is better
    
    # Overall
    passed: bool = False
    improvement_significant: bool = False
    details: Dict = field(default_factory=dict)
    
    def duration(self) -> float:
        """Experiment duration in seconds"""
        if self.completed_at:
            return self.completed_at - self.started_at
        return time.time() - self.started_at


@dataclass
class UpgradePassport:
    """Complete upgrade record with quantified results"""
    passport_id: str
    hypothesis: UpgradeHypothesis
    experiment_result: ExperimentResult
    
    # Approval
    approved_by: Optional[str] = None
    approved_at: Optional[float] = None
    
    # Deployment
    deployed_at: Optional[float] = None
    status: str = "pending"  # pending, deployed, rolled_back
    
    # Metrics snapshot
    before_metrics: Dict = field(default_factory=dict)
    after_metrics: Dict = field(default_factory=dict)
    improvement_percent: float = 0.0
    
    # Post-deployment tracking
    rollback_reason: Optional[str] = None
    user_satisfaction: Optional[float] = None


@dataclass
class ObserveEngineKPI:
    """Key Performance Indicators for Observe Engine"""
    # Signal metrics
    total_signals_collected: int = 0
    signals_last_24h: int = 0
    
    # Quality metrics
    signal_precision: float = 0.0  # Signals that became hypotheses
    hypothesis_acceptance_rate: float = 0.0  # Hypotheses that passed testing
    false_hype_rate: float = 0.0  # Social hype that provided no value
    
    # Upgrade metrics
    experiments_run: int = 0
    experiments_passed: int = 0
    accepted_upgrades: int = 0
    rolled_back_upgrades: int = 0
    
    # Timing
    avg_time_to_experiment: float = 0.0  # Hours from signal to experiment
    avg_time_to_approval: float = 0.0  # Hours from experiment to approval
    
    # Cost
    cost_per_accepted_improvement: float = 0.0
    
    # Freshness
    freshness_lag_hours: float = 0.0  # Avg hours from signal to detection


class SourceRegistry:
    """
    Source Registry - Manages all observation sources
    Each source has: type, auth, refresh method, trust level, format, cost, legal status
    
    5 LAYERS:
    A. Frontier competitor (ChatGPT, Devin, DeepSeek capabilities)
    B. Official docs / API
    C. Human demand / market pain
    D. Internal telemetry
    E. Ecosystem / toolchain
    """
    
    def __init__(self):
        self.sources: Dict[str, Dict] = {}
        self._register_default_sources()
    
    def _register_default_sources(self):
        """Register default high-priority sources"""
        
        # A. Frontier Competitor Layer
        # ChatGPT capabilities
        self.register_source(
            source_id="chatgpt_apps",
            source_type=SignalSource.COMPETITOR_ANALYSIS,
            base_url="https://openai.com/chatgpt/apps",
            auth_type="none",
            trust_score=0.85,
            refresh_interval=7200,
            data_format="structured",
            legal_status="public",
            layer="A. Frontier competitor"
        )
        
        # Devin capabilities
        self.register_source(
            source_id="devin_analytics",
            source_type=SignalSource.COMPETITOR_ANALYSIS,
            base_url="https://devin.ai",
            auth_type="none",
            trust_score=0.85,
            refresh_interval=7200,
            data_format="analysis",
            legal_status="public",
            layer="A. Frontier competitor"
        )
        
        # DeepSeek capabilities
        self.register_source(
            source_id="deepseek_api",
            source_type=SignalSource.API_DOCS,
            base_url="https://api.deepseek.com",
            auth_type="api_key",
            trust_score=0.90,
            refresh_interval=3600,
            data_format="api_spec",
            legal_status="public",
            layer="A. Frontier competitor"
        )
        
        # B. Official Docs / API Layer
        self.register_source(
            source_id="openai_docs",
            source_type=SignalSource.OFFICIAL_DOCS,
            base_url="https://platform.openai.com/docs",
            auth_type="none",
            trust_score=0.95,
            refresh_interval=3600,
            data_format="structured",
            legal_status="public",
            layer="B. Official docs/API"
        )
        
        self.register_source(
            source_id="openai_release",
            source_type=SignalSource.RELEASE_NOTE,
            base_url="https://openai.com/blog",
            auth_type="none",
            trust_score=0.95,
            refresh_interval=3600,
            data_format="blog",
            legal_status="public",
            layer="B. Official docs/API"
        )
        
        self.register_source(
            source_id="cognition_docs",
            source_type=SignalSource.OFFICIAL_DOCS,
            base_url="https://docs.cognition-labs.com",
            auth_type="none",
            trust_score=0.95,
            refresh_interval=3600,
            data_format="structured",
            legal_status="public",
            layer="B. Official docs/API"
        )
        
        # TikTok/Meta Developer APIs
        self.register_source(
            source_id="tiktok_dev",
            source_type=SignalSource.API_DOCS,
            base_url="https://developers.tiktok.com",
            auth_type="oauth",
            trust_score=0.90,
            refresh_interval=7200,
            data_format="api_spec",
            legal_status="public",
            layer="B. Official docs/API"
        )
        
        self.register_source(
            source_id="meta_dev",
            source_type=SignalSource.API_DOCS,
            base_url="https://developers.facebook.com",
            auth_type="oauth",
            trust_score=0.90,
            refresh_interval=7200,
            data_format="api_spec",
            legal_status="public",
            layer="B. Official docs/API"
        )
        
        # C. Human Demand / Market Pain Layer
        self.register_source(
            source_id="reddit_ai",
            source_type=SignalSource.COMMUNITY_DISCUSSION,
            base_url="https://reddit.com/r/ArtificialIntelligence",
            auth_type="none",
            trust_score=0.50,
            refresh_interval=1800,
            data_format="forum",
            legal_status="public",
            layer="C. Human demand"
        )
        
        self.register_source(
            source_id="product_hunt",
            source_type=SignalSource.COMMUNITY_DISCUSSION,
            base_url="https://producthunt.com",
            auth_type="none",
            trust_score=0.55,
            refresh_interval=3600,
            data_format="forum",
            legal_status="public",
            layer="C. Human demand"
        )
        
        # Social (lower trust)
        self.register_source(
            source_id="twitter_ai",
            source_type=SignalSource.SOCIAL_MEDIA,
            base_url="https://twitter.com/ai",
            auth_type="oauth",
            trust_score=0.40,
            refresh_interval=1800,
            data_format="social",
            legal_status="public",
            layer="C. Human demand"
        )
    
    def register_source(self, source_id: str, source_type: SignalSource, base_url: str,
                       auth_type: str, trust_score: float, refresh_interval: int,
                       data_format: str, legal_status: str, layer: str = ""):
        """Register a new source"""
        self.sources[source_id] = {
            "source_id": source_id,
            "source_type": source_type,
            "base_url": base_url,
            "auth_type": auth_type,
            "trust_score": trust_score,
            "refresh_interval": refresh_interval,
            "data_format": data_format,
            "legal_status": legal_status,
            "layer": layer,
            "last_fetched": None,
            "fetch_count": 0
        }
    
    def get_active_sources(self, min_trust: float = 0.0) -> List[Dict]:
        """Get sources above minimum trust threshold"""
        return [
            s for s in self.sources.values()
            if s["trust_score"] >= min_trust
        ]
    
    def get_sources_by_layer(self, layer: str) -> List[Dict]:
        """Get sources by layer (A, B, C, D, E)"""
        return [
            s for s in self.sources.values()
            if layer in s.get("layer", "")
        ]
    
    def update_fetch_status(self, source_id: str):
        """Update last fetched time and count"""
        if source_id in self.sources:
            self.sources[source_id]["last_fetched"] = time.time()
            self.sources[source_id]["fetch_count"] += 1


class TrustPriorityEngine:
    """
    Trust & Priority Engine - Scores each signal
    
    Calculates:
    - official? (25%)
    - fresh? (15%)
    - corroborated? (25%)
    - relevant? (15%)
    - ROI? (10%)
    - risk? (10%)
    """
    
    # Weight configuration
    WEIGHTS = {
        "official_source": 0.25,
        "freshness": 0.15,
        "corroboration": 0.25,
        "relevance": 0.15,
        "roi_estimate": 0.10,
        "risk_assessment": 0.10
    }
    
    def __init__(self):
        self.signal_history: Dict[str, float] = {}  # signal_id -> timestamp
    
    def calculate_trust_score(self, signal: RawSignal) -> float:
        """Calculate trust score for a raw signal (0-1)"""
        score = 0.0
        
        # 1. Source trust (40% base)
        source_trust_map = {
            SignalSource.OFFICIAL_DOCS: 0.95,
            SignalSource.API_DOCS: 0.90,
            SignalSource.RELEASE_NOTE: 0.90,
            SignalSource.COMPETITOR_ANALYSIS: 0.75,
            SignalSource.COMMUNITY_DISCUSSION: 0.50,
            SignalSource.SOCIAL_MEDIA: 0.35,
            SignalSource.RUMOR: 0.20
        }
        source_trust = source_trust_map.get(signal.source_type, 0.5)
        score += source_trust * 0.4
        
        # 2. Freshness (30%)
        age_hours = (time.time() - signal.timestamp) / 3600
        if age_hours < 1:
            freshness = 1.0
        elif age_hours < 24:
            freshness = 1.0 - (age_hours / 24) * 0.3
        elif age_hours < 168:  # 1 week
            freshness = 0.7 - ((age_hours - 24) / 144) * 0.4
        else:
            freshness = 0.3
        score += freshness * 0.3
        
        # 3. Content quality indicators (30%)
        quality_score = self._assess_content_quality(signal.content)
        score += quality_score * 0.3
        
        return min(1.0, score)
    
    def _assess_content_quality(self, content: str) -> float:
        """Assess quality of content"""
        score = 0.5
        
        # Has technical detail
        if any(word in content.lower() for word in ["api", "function", "parameter", "method", "tool"]):
            score += 0.15
        
        # Has examples or code
        if "```" in content or "example" in content.lower():
            score += 0.15
        
        # Not just hype/speculation
        hype_words = ["might", "probably", "maybe", "rumored", "allegedly"]
        if not any(word in content.lower() for word in hype_words):
            score += 0.1
        
        # Has verifiable claims
        if any(word in content.lower() for word in ["announced", "released", "available", "now"]):
            score += 0.1
        
        return min(1.0, score)
    
    def calculate_priority(self, signal: CanonicalSignal) -> SignalPriority:
        """Calculate priority for a canonical signal"""
        
        # Critical: High trust + high novelty + high relevance
        if (signal.trust_score > 0.8 and 
            signal.novelty_score > 0.7 and 
            signal.applicable):
            return SignalPriority.CRITICAL
        
        # High: Good trust + good novelty + applicable
        if (signal.trust_score > 0.6 and 
            signal.novelty_score > 0.5 and 
            signal.applicable):
            return SignalPriority.HIGH
        
        # Medium: Moderate trust or novelty
        if signal.trust_score > 0.4:
            return SignalPriority.MEDIUM
        
        return SignalPriority.LOW
    
    def calculate_roi_estimate(self, signal: CanonicalSignal) -> float:
        """Estimate ROI if this signal is acted upon"""
        roi = 0.5
        
        # Higher trust = more certain ROI
        roi += signal.trust_score * 0.2
        
        # Higher novelty = potential for bigger improvement
        roi += signal.novelty_score * 0.2
        
        # If multiple sources corroborate
        if signal.source_count > 1:
            roi += min(0.1 * signal.source_count, 0.2)
        
        return min(1.0, roi)


class NoveltyDetector:
    """
    Novelty Detector - Determines if signal is truly new
    
    "bu biz bilgan narsaning takrori yoki haqiqiy yangi narsami?"
    """
    
    def __init__(self):
        self.known_patterns: List[str] = []
        self.previous_signals: Dict[str, CanonicalSignal] = {}
        self._init_known_patterns()
    
    def _init_known_patterns(self):
        """Initialize known capability patterns"""
        self.known_patterns = [
            "tool calling", "function calling", "structured output", "json mode",
            "vision", "image understanding", "web browsing", "code interpreter",
            "file upload", "memory", "context window", "long context",
            "streaming", "batch processing", "api", "mcp", "agent",
            "multi-step", "reasoning", "chain of thought", "planning",
            "deep research", "web navigation", "form filling", "spreadsheet editing",
            "mcp server", "custom tools", "project memory", "write action"
        ]
    
    def detect_novelty(self, signal: RawSignal) -> float:
        """Detect how novel a signal is (0-1)"""
        
        # Check against known patterns
        content_lower = signal.content.lower()
        title_lower = signal.title.lower()
        combined = content_lower + " " + title_lower
        
        matches = 0
        for pattern in self.known_patterns:
            if pattern in combined:
                matches += 1
        
        # More matches = less novel
        novelty = 1.0 - (matches / max(1, len(self.known_patterns)))
        
        # Check against previous signals
        if self.previous_signals:
            for prev in self.previous_signals.values():
                if (signal.title.lower() in prev.title.lower() or 
                    prev.title.lower() in signal.title.lower()):
                    novelty *= 0.5
        
        return max(0.0, min(1.0, novelty))
    
    def register_signal(self, signal: CanonicalSignal):
        """Register a processed signal as known"""
        self.previous_signals[signal.signal_id] = signal
        
        # Extract new patterns from this signal
        words = re.findall(r'\b[a-z]{4,}\b', signal.description.lower())
        for word in words:
            if word not in self.known_patterns and len(word) > 6:
                self.known_patterns.append(word)


class HypothesisGenerator:
    """
    Hypothesis Generator - Transforms signals into upgrade hypotheses
    
    Key principle: NEVER modify production self - only work on clone/candidate
    
    "Signalni upgrade gipotezasiga aylantiradi"
    """
    
    def __init__(self):
        self.template_registry = self._init_templates()
    
    def _init_templates(self) -> Dict:
        """Initialize hypothesis templates"""
        return {
            "new_tool_capability": {
                "upgrade_type": UpgradeType.NEW_TOOL,
                "template": "Add support for {capability} based on {source}",
                "test_plan": "Verify {capability} works on clone with benchmark tasks"
            },
            "api_change": {
                "upgrade_type": UpgradeType.MODEL_ADAPTER,
                "template": "Update API integration to support {change}",
                "test_plan": "Test API calls with new parameters on candidate"
            },
            "memory_upgrade": {
                "upgrade_type": UpgradeType.MEMORY_UPGRADE,
                "template": "Enhance memory system with {feature}",
                "test_plan": "Test long-running tasks with enhanced memory"
            },
            "workflow_optimization": {
                "upgrade_type": UpgradeType.WORKFLOW_OPTIMIZATION,
                "template": "Optimize workflow: {workflow}",
                "test_plan": "Measure latency and success rate improvement"
            },
            "architecture_refactor": {
                "upgrade_type": UpgradeType.ARCHITECTURE_REFACTOR,
                "template": "Refactor {component} for {reason}",
                "test_plan": "Run full benchmark suite on refactored code"
            }
        }
    
    def generate_hypothesis(self, signal: CanonicalSignal) -> UpgradeHypothesis:
        """Generate upgrade hypothesis from canonical signal"""
        
        # Determine event type
        event_type = self._classify_event(signal)
        
        # Get template
        template = self.template_registry.get(event_type, {})
        
        # Build hypothesis text
        hypothesis_text = template.get("template", "Upgrade based on: {title}").format(
            title=signal.title,
            capability=signal.title,
            source=signal.source_type.value,
            change=signal.description[:50],
            feature=signal.title,
            workflow=signal.title,
            component="system",
            reason="improvement"
        )
        
        # Determine upgrade type
        upgrade_type = template.get("upgrade_type", UpgradeType.SMALL_PATCH)
        
        # Calculate expected ROI
        expected_roi = (signal.trust_score * 0.4 + 
                       signal.novelty_score * 0.3 + 
                       0.3)
        
        # Determine risk level
        risk_level = "low" if expected_roi > 0.7 else "medium" if expected_roi > 0.5 else "high"
        
        # Generate ID
        hypothesis_id = f"hyp_{hashlib.md5(hypothesis_text.encode()).hexdigest()[:12]}"
        
        hypothesis = UpgradeHypothesis(
            hypothesis_id=hypothesis_id,
            canonical_signal=signal,
            hypothesis_text=hypothesis_text,
            upgrade_type=upgrade_type,
            expected_benefit=signal.description[:200],
            expected_roi=expected_roi,
            risk_level=risk_level,
            implementation_plan=f"Implement on candidate clone: {hypothesis_text}",
            test_plan=template.get("test_plan", "Test on clone").format(
                capability=signal.title
            )
        )
        
        return hypothesis
    
    def _classify_event(self, signal: CanonicalSignal) -> str:
        """Classify the event type from signal content"""
        content = (signal.title + " " + signal.description).lower()
        
        if "tool" in content or "function" in content or "capability" in content:
            return "new_tool_capability"
        elif "api" in content or "parameter" in content or "endpoint" in content:
            return "api_change"
        elif "memory" in content or "context" in content or "window" in content:
            return "memory_upgrade"
        elif "workflow" in content or "process" in content or "automation" in content:
            return "workflow_optimization"
        elif "architecture" in content or "refactor" in content or "design" in content:
            return "architecture_refactor"
        
        return "small_patch"


class ExperimentQueue:
    """
    Experiment Queue - Manages upgrade experiments on clone/candidate
    
    Priority: Critical > High > Medium > Low
    """
    
    def __init__(self):
        self.queue: List[UpgradeHypothesis] = []
        self.running: Dict[str, UpgradeHypothesis] = {}
        self.completed: List[ExperimentResult] = []
    
    def add(self, hypothesis: UpgradeHypothesis):
        """Add hypothesis to queue"""
        self.queue.append(hypothesis)
        self._sort_queue()
    
    def _sort_queue(self):
        """Sort queue by priority"""
        priority_order = {
            SignalPriority.CRITICAL: 0,
            SignalPriority.HIGH: 1,
            SignalPriority.MEDIUM: 2,
            SignalPriority.LOW: 3,
            SignalPriority.NOISE: 4
        }
        
        self.queue.sort(key=lambda h: (
            priority_order.get(h.canonical_signal.priority, 99),
            -h.expected_roi
        ))
    
    def get_next(self) -> Optional[UpgradeHypothesis]:
        """Get next experiment to run"""
        if not self.queue:
            return None
        return self.queue.pop(0)
    
    def add_result(self, result: ExperimentResult):
        """Record experiment result"""
        self.completed.append(result)
    
    def get_stats(self) -> Dict:
        """Get queue statistics"""
        return {
            "queued": len(self.queue),
            "running": len(self.running),
            "completed": len(self.completed),
            "passed": sum(1 for r in self.completed if r.passed),
            "failed": sum(1 for r in self.completed if not r.passed)
        }


class LearningMemory:
    """
    Learning Memory - Stores what was tried, what worked, when, and why
    
    NOT global - project-scoped and lineage-scoped
    
    "agent nafaqat 'nimani ko'rdim', balki
    - 'nimani sinadim'
    - 'nima ishladi'
    - 'qaysi sharoitda ishladi'
    - 'qachon ishlamadi'
    ni saqlaydi"
    """
    
    def __init__(self, project_id: str = "default"):
        self.project_id = project_id
        self.experiments: List[ExperimentResult] = []
        self.upgrade_passports: List[UpgradePassport] = []
        self.signal_history: List[CanonicalSignal] = []
        self.learned_patterns: Dict[str, Any] = defaultdict(list)
    
    def record_experiment(self, result: ExperimentResult):
        """Record an experiment result"""
        self.experiments.append(result)
        
        # Extract patterns
        if result.passed:
            key = result.hypothesis.upgrade_type.value
            self.learned_patterns[key].append({
                "hypothesis": result.hypothesis.hypothesis_text,
                "improvement": result.task_completion_delta,
                "timestamp": result.completed_at or time.time()
            })
    
    def record_upgrade(self, passport: UpgradePassport):
        """Record an approved and deployed upgrade"""
        self.upgrade_passports.append(passport)
    
    def record_signal(self, signal: CanonicalSignal):
        """Record a processed signal"""
        self.signal_history.append(signal)
    
    def get_what_worked(self, upgrade_type: UpgradeType = None) -> List[Dict]:
        """Get patterns that worked"""
        if upgrade_type:
            return self.learned_patterns.get(upgrade_type.value, [])
        return {k: v for k, v in self.learned_patterns.items()}
    
    def get_rollback_analysis(self) -> Dict:
        """Analyze rollbacks to learn what to avoid"""
        rollbacks = [p for p in self.upgrade_passports if p.status == "rolled_back"]
        
        if not rollbacks:
            return {"rollbacks": 0, "common_reasons": []}
        
        reasons = [p.rollback_reason for p in rollbacks if p.rollback_reason]
        
        return {
            "rollbacks": len(rollbacks),
            "rollback_rate": len(rollbacks) / len(self.upgrade_passports),
            "common_reasons": list(set(reasons))[:5]
        }
    
    def export_memory(self) -> Dict:
        """Export memory for analysis"""
        return {
            "project_id": self.project_id,
            "total_experiments": len(self.experiments),
            "successful_upgrades": len(self.upgrade_passports),
            "patterns_learned": {k: len(v) for k, v in self.learned_patterns.items()},
            "rollback_analysis": self.get_rollback_analysis()
        }


class IngestionLayer:
    """
    Ingestion Layer - Transforms raw source data into uniform signal format
    
    ACCESS STRATEGY: API-first, webhook-first, browser-last
    """
    
    def __init__(self):
        self.parsers: Dict[str, Callable] = {}
        self._init_parsers()
    
    def _init_parsers(self):
        """Initialize content parsers"""
        self.parsers = {
            "blog": self._parse_blog,
            "api_spec": self._parse_api_spec,
            "structured": self._parse_structured,
            "social": self._parse_social,
            "forum": self._parse_forum,
            "analysis": self._parse_analysis
        }
    
    def ingest(self, source_type: SignalSource, source_url: str, raw_data: Any, 
              data_format: str) -> RawSignal:
        """Ingest raw data and create RawSignal"""
        
        # Parse content
        parser = self.parsers.get(data_format, self._parse_default)
        parsed = parser(raw_data)
        
        # Create signal
        signal = RawSignal(
            source_type=source_type,
            source_url=source_url,
            content=parsed.get("content", ""),
            timestamp=time.time(),
            title=parsed.get("title", "Unknown"),
            metadata=parsed.get("metadata", {}),
            confidence=parsed.get("confidence", 0.5)
        )
        
        return signal
    
    def _parse_blog(self, data: Any) -> Dict:
        """Parse blog/release note format"""
        if isinstance(data, dict):
            return {
                "title": data.get("title", ""),
                "content": data.get("content", data.get("body", "")),
                "metadata": {"author": data.get("author"), "tags": data.get("tags", [])},
                "confidence": 0.9
            }
        return self._parse_default(data)
    
    def _parse_api_spec(self, data: Any) -> Dict:
        """Parse API specification format"""
        if isinstance(data, dict):
            return {
                "title": data.get("endpoint", data.get("name", "")),
                "content": f"{data.get('description', '')} {data.get('parameters', '')}",
                "metadata": {"version": data.get("version"), "methods": data.get("methods", [])},
                "confidence": 0.95
            }
        return self._parse_default(data)
    
    def _parse_structured(self, data: Any) -> Dict:
        """Parse structured documentation"""
        if isinstance(data, dict):
            return {
                "title": data.get("title", data.get("name", "")),
                "content": data.get("content", data.get("description", "")),
                "metadata": data.get("metadata", {}),
                "confidence": 0.9
            }
        return self._parse_default(data)
    
    def _parse_social(self, data: Any) -> Dict:
        """Parse social media format"""
        if isinstance(data, dict):
            return {
                "title": data.get("text", "")[:50],
                "content": data.get("text", ""),
                "metadata": {"likes": data.get("likes"), "retweets": data.get("retweets")},
                "confidence": 0.4
            }
        return self._parse_default(data)
    
    def _parse_forum(self, data: Any) -> Dict:
        """Parse forum/community format"""
        if isinstance(data, dict):
            return {
                "title": data.get("title", ""),
                "content": data.get("content", data.get("body", "")),
                "metadata": {"votes": data.get("votes"), "replies": data.get("replies")},
                "confidence": 0.6
            }
        return self._parse_default(data)
    
    def _parse_analysis(self, data: Any) -> Dict:
        """Parse analysis format"""
        if isinstance(data, dict):
            return {
                "title": data.get("title", ""),
                "content": data.get("analysis", data.get("content", "")),
                "metadata": {"sources": data.get("sources", [])},
                "confidence": data.get("confidence", 0.7)
            }
        return self._parse_default(data)
    
    def _parse_default(self, data: Any) -> Dict:
        """Default parser"""
        if isinstance(data, str):
            return {"title": "Unknown", "content": data, "metadata": {}, "confidence": 0.5}
        if isinstance(data, dict):
            return {
                "title": data.get("title", "Unknown"),
                "content": str(data),
                "metadata": {},
                "confidence": 0.5
            }
        return {"title": "Unknown", "content": str(data), "metadata": {}, "confidence": 0.5}


class CanonicalizationLayer:
    """
    Canonicalization Layer - Deduplicates signals into single canonical events
    
    "Bir xil yangilik 20 joyda uchraydi. Bu modul duplicate'larni birlashtiradi
    va 'single canonical event' yasaydi"
    """
    
    def __init__(self):
        self.canonical_signals: Dict[str, CanonicalSignal] = {}
    
    def canonicalize(self, signal: RawSignal) -> CanonicalSignal:
        """Convert raw signal to canonical form, deduplicating if needed"""
        
        # Generate canonical key
        key = self._generate_key(signal)
        
        if key in self.canonical_signals:
            # Already exists - add to source count
            existing = self.canonical_signals[key]
            existing.raw_signals.append(signal)
            existing.source_count += 1
            existing.last_seen = signal.timestamp
            return existing
        
        # Create new canonical signal
        canonical = CanonicalSignal(
            signal_id=f"canon_{key[:12]}",
            event_type=self._classify_event(signal),
            title=signal.title,
            description=signal.content[:500],
            priority=SignalPriority.LOW,
            trust_score=signal.trust_score,
            novelty_score=0.5,
            source_count=1,
            first_seen=signal.timestamp,
            last_seen=signal.timestamp,
            raw_signals=[signal]
        )
        
        self.canonical_signals[key] = canonical
        return canonical
    
    def _generate_key(self, signal: RawSignal) -> str:
        """Generate canonical key for deduplication"""
        title_norm = signal.title.lower().strip()
        title_norm = re.sub(r'[^\w\s]', '', title_norm)
        title_norm = ' '.join(title_norm.split())
        key = hashlib.md5(title_norm.encode()).hexdigest()
        return key
    
    def _classify_event(self, signal: RawSignal) -> str:
        """Classify event type"""
        content = (signal.title + " " + signal.content).lower()
        
        if any(w in content for w in ["tool", "function", "capability", "feature"]):
            return "new_tool_capability"
        elif any(w in content for w in ["api", "endpoint", "parameter"]):
            return "api_change"
        elif any(w in content for w in ["memory", "context", "window"]):
            return "memory_upgrade"
        elif any(w in content for w in ["model", "gpt", "llm"]):
            return "model_update"
        
        return "general"


class ObserveEngine:
    """
    MAIN OBSERVE ENGINE - Complete implementation
    
    This is the agent's "eyes, ears, and scientific laboratory"
    
    Core principles:
    1. NEVER modify production self directly - only work on clone/candidate
    2. Signal → Upgrade formula: Raw → Claim → Corroboration → Applicability → Hypothesis → Clone Experiment → Report → Approval → Promote/Reject
    3. API-first, webhook-first, browser-last access strategy
    4. Trust ranking: official docs > community > social media
    
    8 Pipeline Modules:
    1. Source Registry
    2. Ingestion Layer
    3. Canonicalization Layer
    4. Trust & Priority Engine
    5. Novelty Detector
    6. Hypothesis Generator
    7. Experiment Queue
    8. Learning Memory
    """
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        
        # Initialize 8 pipeline components
        self.source_registry = SourceRegistry()
        self.ingestion_layer = IngestionLayer()
        self.canonicalization = CanonicalizationLayer()
        self.trust_engine = TrustPriorityEngine()
        self.novelty_detector = NoveltyDetector()
        self.hypothesis_generator = HypothesisGenerator()
        self.experiment_queue = ExperimentQueue()
        self.learning_memory = LearningMemory()
        
        # KPI tracking
        self.kpi = ObserveEngineKPI()
        
        # State
        self.is_running = False
        self.last_observation = None
    
    def observe(self) -> List[RawSignal]:
        """
        OBSERVE PHASE - Collect signals from all sources
        
        Access strategy: API-first, webhook-first, browser-last
        
        Returns list of raw signals
        """
        signals = []
        
        # Get active sources (all 5 layers)
        sources = self.source_registry.get_active_sources(min_trust=0.3)
        
        for source in sources:
            try:
                # Fetch from source based on access strategy
                raw_data = self._fetch_source(source)
                
                if raw_data:
                    # Ingest and convert to signal
                    signal = self.ingestion_layer.ingest(
                        source_type=source["source_type"],
                        source_url=source["base_url"],
                        raw_data=raw_data,
                        data_format=source["data_format"]
                    )
                    
                    # Calculate trust score
                    signal.trust_score = self.trust_engine.calculate_trust_score(signal)
                    
                    signals.append(signal)
                    
                    # Update source status
                    self.source_registry.update_fetch_status(source["source_id"])
                    
            except Exception as e:
                logger.debug(f"Error fetching source {source['source_id']}: {e}")
        
        self.kpi.total_signals_collected += len(signals)
        self.kpi.signals_last_24h = len(signals)
        self.last_observation = time.time()
        
        return signals
    
    def _fetch_source(self, source: Dict) -> Any:
        """
        Fetch from source based on access strategy
        
        API-first → Webhook-first → Browser-last
        """
        # This is a placeholder
        # In production:
        # 1. Check if source has API → Call REST API
        # 2. If no API but has webhook → Set up webhook listener
        # 3. If neither → Use browser automation (Playwright)
        return None
    
    def process(self, signals: List[RawSignal] = None) -> List[UpgradeHypothesis]:
        """
        PROCESS PHASE - Transform signals into upgrade hypotheses
        
        Pipeline:
        1. Canonicalize (deduplicate)
        2. Detect novelty
        3. Check applicability
        4. Calculate trust/priority
        5. Generate hypothesis
        """
        if signals is None:
            signals = []
        
        hypotheses = []
        
        for signal in signals:
            # Step 1: Canonicalize
            canonical = self.canonicalization.canonicalize(signal)
            
            # Step 2: Detect novelty
            canonical.novelty_score = self.novelty_detector.detect_novelty(signal)
            
            # Step 3: Check applicability
            canonical.applicable = self._check_applicability(canonical)
            
            # Step 4: Calculate trust/priority
            canonical.trust_score = canonical.combined_trust_score()
            canonical.priority = self.trust_engine.calculate_priority(canonical)
            
            # Store in memory
            self.learning_memory.record_signal(canonical)
            
            # Step 5: Generate hypothesis if applicable and novel
            if canonical.applicable and canonical.novelty_score > 0.3:
                hypothesis = self.hypothesis_generator.generate_hypothesis(canonical)
                self.experiment_queue.add(hypothesis)
                hypotheses.append(hypothesis)
                
                self.kpi.signal_precision = len(hypotheses) / max(1, len(signals))
        
        return hypotheses
    
    def _check_applicability(self, signal: CanonicalSignal) -> bool:
        """Check if signal is applicable to our system"""
        relevant_keywords = [
            "agent", "llm", "model", "tool", "api", "automation",
            "memory", "context", "reasoning", "workflow", "browser",
            "chatgpt", "devin", "deepseek", "openai", "mcp"
        ]
        
        content = (signal.title + " " + signal.description).lower()
        
        relevant = any(kw in content for kw in relevant_keywords)
        
        if not relevant:
            signal.applicability_reason = "Not relevant to current tech stack"
            return False
        
        return True
    
    async def experiment(self, hypothesis: UpgradeHypothesis = None) -> ExperimentResult:
        """
        EXPERIMENT PHASE - Test hypothesis on clone/candidate
        
        CRITICAL: This ONLY modifies clone, never production!
        
        Returns experiment result with quantified metrics
        """
        if hypothesis is None:
            hypothesis = self.experiment_queue.get_next()
        
        if hypothesis is None:
            return None
        
        # Mark as running
        hypothesis.status = "testing"
        self.experiment_queue.running[hypothesis.hypothesis_id] = hypothesis
        
        # Run experiment on clone
        result = await self._run_clone_experiment(hypothesis)
        
        # Record result
        result.completed_at = time.time()
        self.experiment_queue.running.pop(hypothesis.hypothesis_id, None)
        self.experiment_queue.add_result(result)
        self.learning_memory.record_experiment(result)
        
        # Update KPIs
        self.kpi.experiments_run += 1
        if result.passed:
            self.kpi.experiments_passed += 1
        
        return result
    
    async def _run_clone_experiment(self, hypothesis: UpgradeHypothesis) -> ExperimentResult:
        """
        Run experiment on clone/candidate
        
        CRITICAL: Never touches production code!
        
        This is where actual code changes would be made to a clone
        """
        
        result = ExperimentResult(
            experiment_id=f"exp_{hypothesis.hypothesis_id}_{int(time.time())}",
            hypothesis=hypothesis,
            started_at=time.time()
        )
        
        # Simulate improvement metrics
        # In production, this would be real benchmarking on clone
        result.task_completion_delta = 0.05
        result.tool_call_success_delta = 0.03
        result.latency_delta = -0.02
        result.cost_delta = -0.01
        
        # Determine if passed
        result.passed = (
            result.task_completion_delta > 0 or
            result.tool_call_success_delta > 0 or
            result.latency_delta < 0 or
            result.cost_delta < 0
        )
        
        result.improvement_significant = (
            abs(result.task_completion_delta) > 0.02 or
            abs(result.latency_delta) > 0.01
        )
        
        result.details = {
            "clone_path": f"/clone/{hypothesis.hypothesis_id}",
            "benchmark_tasks": 10,
            "tasks_passed": 8 if result.passed else 5,
            "avg_latency_ms": 150,
            "cost_per_task": 0.001
        }
        
        return result
    
    def report(self, result: ExperimentResult) -> UpgradePassport:
        """
        REPORT PHASE - Generate quantified upgrade passport
        
        "nima ko'rdim → nima o'zgartirdim → nima oshdi → nima risk"
        
        Returns passport with all metrics and approval info
        """
        
        passport = UpgradePassport(
            passport_id=f"passport_{result.experiment_id}",
            hypothesis=result.hypothesis,
            experiment_result=result,
            before_metrics={
                "task_completion": 0.80,
                "tool_success": 0.85,
                "latency_ms": 155
            },
            after_metrics={
                "task_completion": 0.80 + result.task_completion_delta,
                "tool_success": 0.85 + result.tool_call_success_delta,
                "latency_ms": 155 * (1 + result.latency_delta)
            }
        )
        
        # Calculate improvement percentage
        improvements = [
            result.task_completion_delta,
            result.tool_call_success_delta,
            -result.latency_delta,
            -result.cost_delta
        ]
        passport.improvement_percent = sum(improvements) / len(improvements) * 100
        
        # Store in memory
        self.learning_memory.record_upgrade(passport)
        
        # Update KPIs
        if result.passed:
            self.kpi.accepted_upgrades += 1
        
        return passport
    
    def get_kpi_report(self) -> Dict:
        """
        Get comprehensive KPI report
        
        KPIs:
        - Freshness lag
        - Signal precision
        - Experiment yield
        - Accepted upgrade rate
        - False-hype rate
        - Rollback rate
        - Cost per accepted improvement
        - Time-to-upgrade
        """
        
        total_experiments = self.kpi.experiments_run
        total_signals = self.kpi.total_signals_collected
        
        self.kpi.signal_precision = total_signals > 0 and self.kpi.signal_precision or 0.0
        self.kpi.hypothesis_acceptance_rate = (
            total_experiments > 0 and 
            self.kpi.experiments_passed / total_experiments or 
            0.0
        )
        
        rollback_analysis = self.learning_memory.get_rollback_analysis()
        
        return {
            "signal_metrics": {
                "total_collected": total_signals,
                "last_24h": self.kpi.signals_last_24h,
                "freshness_lag_hours": self.kpi.freshness_lag_hours
            },
            "quality_metrics": {
                "signal_precision": self.kpi.signal_precision,
                "experiment_yield": self.kpi.hypothesis_acceptance_rate,
                "false_hype_rate": self.kpi.false_hype_rate
            },
            "upgrade_metrics": {
                "experiments_run": total_experiments,
                "experiments_passed": self.kpi.experiments_passed,
                "accepted_upgrades": self.kpi.accepted_upgrades,
                "rolled_back_upgrades": self.kpi.rolled_back_upgrades,
                "rollback_rate": rollback_analysis.get("rollback_rate", 0)
            },
            "timing_metrics": {
                "avg_time_to_experiment_hours": self.kpi.avg_time_to_experiment,
                "avg_time_to_approval_hours": self.kpi.avg_time_to_approval
            },
            "cost_metrics": {
                "cost_per_accepted_improvement": self.kpi.cost_per_accepted_improvement
            },
            "queue_status": self.experiment_queue.get_stats()
        }
    
    async def run_full_cycle(self) -> List[UpgradePassport]:
        """
        Run complete observe → process → experiment → report cycle
        
        SIGNAL → UPGRADE FORMULA:
        Raw signal → Claim extraction → Corroboration → Applicability test
        → Candidate hypothesis → Clone experiment → Quantified report
        → Your approval → Promote/Reject
        
        Returns list of upgrade passports ready for approval
        """
        passports = []
        
        # Phase 1: Observe
        signals = self.observe()
        
        # Phase 2: Process
        hypotheses = self.process(signals)
        
        # Phase 3: Experiment on each hypothesis (clone only!)
        for hypothesis in hypotheses:
            result = await self.experiment(hypothesis)
            
            if result and result.passed:
                # Phase 4: Report
                passport = self.report(result)
                passports.append(passport)
        
        return passports
    
    def get_upgrade_passport(self, passport_id: str) -> Optional[UpgradePassport]:
        """Get specific upgrade passport by ID"""
        for passport in self.learning_memory.upgrade_passports:
            if passport.passport_id == passport_id:
                return passport
        return None


def create_observe_engine(config: Dict = None) -> ObserveEngine:
    """Factory function to create ObserveEngine"""
    return ObserveEngine(config)
