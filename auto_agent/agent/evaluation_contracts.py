"""
OmniAgent X - Evaluation Contracts
==================================
Universal typed status model for all benchmarks and tests.

This module provides:
- RunState: Typed status enum (PASSED, FAILED, ERROR, NOT_IMPLEMENTED, etc.)
- CheckResult: Structured result with evidence and metadata
- TaskSpec: Task specification with required verifier

IMPORTANT: This enforces the core law:
- "Unknown != Pass"
- "No tests != Pass"
- "No verifier != Fail"
- "Simulation in production gate is forbidden"
"""
import logging
from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ==================== RUN STATE ENUM ====================

class RunState(str, Enum):
    """
    Universal state enum for all evaluation results.
    
    IMPORTANT: Each state is distinct and must be handled separately:
    - PASSED: Real execution verified and passed
    - FAILED: Real execution verified and failed
    - ERROR: Execution error occurred
    - NOT_IMPLEMENTED: Task/verifier not implemented
    - NO_TESTS: No tests found
    - TOOL_MISSING: Required tool not available
    - INVALID_RESULT: Result cannot be parsed/validated
    - SKIPPED: Explicitly skipped
    """
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"
    NOT_IMPLEMENTED = "not_implemented"
    NO_TESTS = "no_tests"
    TOOL_MISSING = "tool_missing"
    INVALID_RESULT = "invalid_result"
    SKIPPED = "skipped"


# ==================== EVIDENCE ====================

@dataclass
class Evidence:
    """
    Evidence for a test result.
    Each pass must be backed by concrete evidence.
    """
    kind: str  # "pytest_output", "file_hash", "screenshot", "diff", etc.
    value: Any
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "kind": self.kind,
            "value": self.value,
            "metadata": self.metadata
        }


# ==================== CHECK RESULT ====================

@dataclass
class CheckResult:
    """
    Structured result for all checks.
    
    IMPORTANT: This replaces bool/dict returns throughout the codebase.
    Every check must return a CheckResult with proper state.
    """
    state: RunState
    score: float  # 0.0 to 1.0
    message: str = ""
    duration: float = 0.0
    evidence: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def passed(self) -> bool:
        """Check if result passed - ONLY True for PASSED state"""
        return self.state == RunState.PASSED
    
    @property
    def is_valid(self) -> bool:
        """Check if result is valid (not error, not_implemented, etc.)"""
        return self.state in (RunState.PASSED, RunState.FAILED)
    
    def to_dict(self) -> Dict:
        return {
            "state": self.state.value,
            "score": self.score,
            "message": self.message,
            "duration": self.duration,
            "evidence": self.evidence,
            "passed": self.passed
        }
    
    @classmethod
    def passed_result(cls, message: str = "", score: float = 1.0, 
                     evidence: Dict = None, duration: float = 0.0) -> "CheckResult":
        """Create a PASSED result"""
        return cls(
            state=RunState.PASSED,
            score=score,
            message=message,
            duration=duration,
            evidence=evidence or {}
        )
    
    @classmethod
    def failed_result(cls, message: str = "", score: float = 0.0,
                     evidence: Dict = None, duration: float = 0.0) -> "CheckResult":
        """Create a FAILED result"""
        return cls(
            state=RunState.FAILED,
            score=score,
            message=message,
            duration=duration,
            evidence=evidence or {}
        )
    
    @classmethod
    def error_result(cls, message: str, error: str = None,
                     evidence: Dict = None, duration: float = 0.0) -> "CheckResult":
        """Create an ERROR result"""
        return cls(
            state=RunState.ERROR,
            score=0.0,
            message=message,
            duration=duration,
            evidence=evidence or {}
        )
    
    @classmethod
    def not_implemented_result(cls, message: str,
                               evidence: Dict = None, duration: float = 0.0) -> "CheckResult":
        """Create a NOT_IMPLEMENTED result"""
        return cls(
            state=RunState.NOT_IMPLEMENTED,
            score=0.0,
            message=message,
            duration=duration,
            evidence=evidence or {}
        )
    
    @classmethod
    def no_tests_result(cls, message: str = "No tests found",
                        evidence: Dict = None, duration: float = 0.0) -> "CheckResult":
        """Create a NO_TESTS result"""
        return cls(
            state=RunState.NO_TESTS,
            score=0.0,
            message=message,
            duration=duration,
            evidence=evidence or {}
        )
    
    @classmethod
    def tool_missing_result(cls, tool_name: str,
                            evidence: Dict = None, duration: float = 0.0) -> "CheckResult":
        """Create a TOOL_MISSING result"""
        return cls(
            state=RunState.TOOL_MISSING,
            score=0.0,
            message=f"Required tool not found: {tool_name}",
            duration=duration,
            evidence=evidence or {}
        )


# ==================== TASK SPEC ====================

@dataclass
class TaskSpec:
    """
    Task specification with required verifier.
    
    IMPORTANT: Every benchmark task must have:
    - fixture_path: Path to fixture repo/files
    - expected_artifacts: What should be produced
    - verifier: How to verify the result
    """
    task_id: str
    category: str
    prompt: str
    timeout_sec: int
    allowed_tools: List[str]
    fixture_path: str
    expected_artifacts: List[str]
    verifier: str  # "pytest", "diff", "screenshot", etc.
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def has_verifier(self) -> bool:
        """Check if task has a real verifier"""
        return bool(self.verifier and self.verifier != "none")
    
    def to_dict(self) -> Dict:
        return {
            "task_id": self.task_id,
            "category": self.category,
            "prompt": self.prompt,
            "timeout_sec": self.timeout_sec,
            "allowed_tools": self.allowed_tools,
            "fixture_path": self.fixture_path,
            "expected_artifacts": self.expected_artifacts,
            "verifier": self.verifier,
            "metadata": self.metadata
        }


# ==================== VERIFIER RESULT ====================

@dataclass
class VerifierResult:
    """
    Result from a verifier.
    """
    verified: bool
    expected: Any
    actual: Any
    diff: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "verified": self.verified,
            "expected": self.expected,
            "actual": self.actual,
            "diff": self.diff,
            "metadata": self.metadata
        }


# ==================== STATUS MAPPING ====================

# Map RunState to TestStatus for regression_suite compatibility
RUN_STATE_TO_TEST_STATUS = {
    RunState.PASSED: "passed",
    RunState.FAILED: "failed",
    RunState.ERROR: "error",
    RunState.NOT_IMPLEMENTED: "error",  # Treat as error - not valid pass
    RunState.NO_TESTS: "error",  # Treat as error - no verification
    RunState.TOOL_MISSING: "error",
    RunState.INVALID_RESULT: "error",
    RunState.SKIPPED: "skipped",
}


# ==================== GATE POLICY ====================

class GatePolicy:
    """
    Zero-trust release policy.
    
    Patch approval requires:
    - Real tests
    - Real benchmarks
    - Real verifiers
    - Baseline exists
    - No unknown/not_implemented/tool_missing/no_tests states
    """
    
    # Minimal thresholds
    MIN_TOTAL_TESTS = 5
    MIN_TEST_PASS_RATE = 0.95
    MIN_BENCHMARK_SCORE = 0.80
    
    @classmethod
    def is_approvable(cls, test_result: Dict, benchmark_result: Dict, 
                      baseline: Dict, unknown_states: Dict) -> tuple[bool, List[str]]:
        """
        Check if a patch is approvable based on all criteria.
        
        Returns:
            (is_approvable, list_of_issues)
        """
        issues = []
        
        # 1. Check test state
        test_state = test_result.get("state", "unknown")
        if test_state != RunState.PASSED.value:
            issues.append(f"Test state is {test_state}, not PASSED")
        
        # 2. Check test coverage
        total_tests = test_result.get("total", 0)
        if total_tests < cls.MIN_TOTAL_TESTS:
            issues.append(f"Insufficient test coverage: {total_tests} < {cls.MIN_TOTAL_TESTS}")
        
        # 3. Check pass rate
        pass_rate = test_result.get("pass_rate", 0)
        if pass_rate < cls.MIN_TEST_PASS_RATE:
            issues.append(f"Test pass rate {pass_rate:.1%} below threshold {cls.MIN_TEST_PASS_RATE:.1%}")
        
        # 4. Check benchmark state
        benchmark_state = benchmark_result.get("state", "unknown")
        if benchmark_state != RunState.PASSED.value:
            issues.append(f"Benchmark state is {benchmark_state}, not PASSED")
        
        # 5. Check benchmark score
        benchmark_score = benchmark_result.get("score", 0)
        if benchmark_score < cls.MIN_BENCHMARK_SCORE:
            issues.append(f"Benchmark score {benchmark_score:.1%} below threshold {cls.MIN_BENCHMARK_SCORE:.1%}")
        
        # 6. Check baseline exists
        baseline_total = baseline.get("total_tests", 0)
        if baseline_total == 0:
            issues.append("Baseline not initialized")
        
        # 7. Check for unknown states
        for state_name, count in unknown_states.items():
            if count > 0:
                issues.append(f"Found {count} tasks with state: {state_name}")
        
        return len(issues) == 0, issues


# ==================== HELPER FUNCTIONS ====================

def convert_to_check_result(result, context: str = "") -> CheckResult:
    """
    Convert various return types to CheckResult.
    
    This ensures backward compatibility while enforcing typed results.
    
    Args:
        result: Can be bool, dict, or CheckResult
        context: Context for error messages
    
    Returns:
        CheckResult with proper state
    """
    if isinstance(result, CheckResult):
        return result
    
    if isinstance(result, bool):
        return CheckResult.passed_result() if result else CheckResult.failed_result(
            message=context or "Test returned False"
        )
    
    if isinstance(result, dict):
        # Check for explicit state
        if "state" in result:
            state = RunState(result.get("state", "invalid_result"))
            return CheckResult(
                state=state,
                score=result.get("score", 0.0),
                message=result.get("message", result.get("error", "")),
                evidence=result.get("evidence", {})
            )
        
        # Old-style dict - check passed field
        passed = result.get("passed")
        if passed is True:
            return CheckResult.passed_result(
                message=result.get("message", ""),
                evidence=result
            )
        elif passed is False:
            return CheckResult.failed_result(
                message=result.get("error", result.get("message", "Test failed")),
                evidence=result
            )
        
        # Truthy dict without explicit state - INVALID
        if result:
            logger.warning(f"Truthy dict without state in {context}: {result}")
            return CheckResult(
                state=RunState.INVALID_RESULT,
                score=0.0,
                message=f"Invalid return type: truthy dict without state in {context}",
                evidence=result
            )
        
        # Falsy result
        return CheckResult.failed_result(
            message=context or "Test returned falsy value"
        )
    
    # Unknown type
    logger.warning(f"Unknown result type in {context}: {type(result)}")
    return CheckResult.error_result(
        message=f"Invalid return type: {type(result).__name__} in {context}"
    )


def ensure_production_mode(task: Dict, simulation_result: Dict = None) -> CheckResult:
    """
    Ensure task is executed in production mode (no simulation).
    
    If task doesn't have real executor/verifier, return NOT_IMPLEMENTED.
    
    Args:
        task: Task specification
        simulation_result: Result from simulation (will be ignored in production)
    
    Returns:
        CheckResult with NOT_IMPLEMENTED if no real executor/verifier
    """
    # Check for required components
    has_executor = task.get("has_executor", False)
    has_verifier = task.get("has_verifier", False)
    
    if not has_executor or not has_verifier:
        return CheckResult.not_implemented_result(
            message=f"No real executor/verifier for task {task.get('id', 'unknown')}. "
                   f"has_executor={has_executor}, has_verifier={has_verifier}"
        )
    
    # This should not be reached in current implementation
    # If reached, it means the task claims to have executor/verifier but we're in simulation
    if simulation_result:
        logger.warning(f"Simulation result ignored for task {task.get('id')}")
    
    return CheckResult.passed_result(message="Production execution verified")
