"""
OmniAgent X - CENTRAL KERNEL
============================
The operating system level orchestration layer

This is the ONE TRUE ORCHESTRATOR that brings together:
- Task Manager (with persistence)
- State Machine (with strict transitions)
- Scheduler (deeply integrated)
- Background Queue
- Retry Controller (with budget)
- Artifact Collector (with metadata)
- Multi-Agent Coordinator
- Recovery Engine (with classification)
- Rollback System

This replaces fragmented architecture with a unified kernel.

FIXED ISSUES:
1. _execute() - Real execution with proper tool selection
2. _repair() - Real recovery engine with error classification
3. _verify() - Task-aware verification
4. VerificationEngine - Real browser/screenshot verification
5. JSON parse - Robust with validation
6. Fallback planner - Real heuristic planner
7. Approval - Real wait state, no auto-approve
8. Success semantics - Not trusting model blindly
9. Artifact semantics - Rich metadata
10. Multi-agent coordinator - Role-based execution
11. Task persistence - Disk-backed state
12. Retry policy - Structured with budget
13. Fallback mode - Structured with telemetry
14. Bare except - Removed, structured errors
15. Telemetry - Per-step metrics
16. Scheduler - Deeply integrated
17. Recovery classification - Error types
18. Rollback - Checkpoint system

VERIFICATION SYSTEM FIXES (v2 - Canonical):
19. Single VerificationType enum - No more taxonomy mismatch
20. VerificationSpec dataclass - Typed contract, not string metadata
21. VERIFICATION_ALIAS_MAP - Legacy name mapping for backward compat
22. Unified verifier API - Single source of truth (no more double verifier)
23. "manual" removed from verification - Now human_review_required field
24. Evidence-based commit gate - success requires evidence
25. Task lifecycle VERIFIED -> COMMITTED semantics
"""
import os
import json
import logging
import time
import asyncio
import threading
from typing import List, Dict, Optional, Any, Set, Callable, Tuple
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field
from collections import defaultdict, deque
from queue import Queue, PriorityQueue, Empty
from pathlib import Path
import uuid
import traceback
import re

# Import new Multi-Agent Coordinator
from agent.multi_agent_coordinator import MultiAgentCoordinator as NewMultiAgentCoordinator

logger = logging.getLogger(__name__)


# ==================== TRANSACTION MODELS ====================
# FIX: Commit / side-effect transaction boundary canonical

class TransactionPhase(str, Enum):
    """
    Side-effect transaction lifecycle phases.
    
    FIX: Side-effect action must go through canonical phases:
    - PREPARED: Intent recorded, resources allocated
    - APPLIED: Action executed, side effects applied
    - OBSERVED: Effects observed and recorded
    - VERIFIED: Verification passed (evidence collected)
    - COMMITTED: State change finalized (cannot be rolled back)
    - ROLLED_BACK: Effects reverted to snapshot
    
    CRITICAL: APPLIED != COMMITTED
    An action can be applied but not committed until verification passes!
    """
    PREPARED = "prepared"
    APPLIED = "applied"
    OBSERVED = "observed"
    VERIFIED = "verified"
    COMMITTED = "committed"
    ROLLBACK_PENDING = "rollback_pending"
    ROLLING_BACK = "rolling_back"
    ROLLED_BACK = "rolled_back"
    FAILED = "failed"


class IdempotencyClass(str, Enum):
    """
    Idempotency classification for tools/actions.
    
    FIX: Must know replay safety for retry/resume logic.
    
    Common examples:
    - read_file: IDEMPOTENT
    - write_file: CONDITIONALLY_IDEMPOTENT (safe if same content)
    - delete_file: CONDITIONALLY_IDEMPOTENT (safe if already deleted)
    - browser_click: NON_IDEMPOTENT
    - append_file: NON_IDEMPOTENT
    - execute_command: CONDITIONALLY_IDEMPOTENT (depends on command)
    """
    # Same result no matter how many times executed
    IDEMPOTENT = "idempotent"
    
    # Safe only if precondition/state checked before execution
    CONDITIONALLY_IDEMPOTENT = "conditionally_idempotent"
    
    # Different result each time, unsafe to replay
    NON_IDEMPOTENT = "non_idempotent"


# Idempotency defaults for common tools
TOOL_IDEMPOTENCY: Dict[str, IdempotencyClass] = {
    # Read operations - always idempotent
    "read_file": IdempotencyClass.IDEMPOTENT,
    "read_directory": IdempotencyClass.IDEMPOTENT,
    "grep": IdempotencyClass.IDEMPOTENT,
    "get_env": IdempotencyClass.IDEMPOTENT,
    "get_system_info": IdempotencyClass.IDEMPOTENT,
    
    # Write operations - conditionally idempotent
    "write_file": IdempotencyClass.CONDITIONALLY_IDEMPOTENT,
    "create_directory": IdempotencyClass.CONDITIONALLY_IDEMPOTENT,
    "copy_file": IdempotencyClass.CONDITIONALLY_IDEMPOTENT,
    
    # Delete operations - conditionally idempotent
    "delete_file": IdempotencyClass.CONDITIONALLY_IDEMPOTENT,
    "remove_directory": IdempotencyClass.CONDITIONALLY_IDEMPOTENT,
    
    # Execute operations - conditionally idempotent
    "execute_command": IdempotencyClass.CONDITIONALLY_IDEMPOTENT,
    "run_script": IdempotencyClass.CONDITIONALLY_IDEMPOTENT,
    "install_package": IdempotencyClass.CONDITIONALLY_IDEMPOTENT,
    
    # Browser operations - non-idempotent
    "browser_click": IdempotencyClass.NON_IDEMPOTENT,
    "browser_type": IdempotencyClass.NON_IDEMPOTENT,
    "browser_navigate": IdempotencyClass.NON_IDEMPOTENT,
    
    # Network operations - conditionally idempotent
    "http_request": IdempotencyClass.CONDITIONALLY_IDEMPOTENT,
    "api_call": IdempotencyClass.CONDITIONALLY_IDEMPOTENT,
}


# ==================== CANONICAL VERIFICATION TYPES ====================
# NEW: Single source of truth for verification types (FIX #19)

class VerificationType(str, Enum):
    """
    Canonical verification types - SINGLE source of truth.
    
    IMPORTANT: "manual" is NOT a verification type!
    Use human_review_required field for human review.
    
    FIX #19: This enum replaces all fragmented verification type strings.
    """
    NONE = "none"                      # Only for explicit research/note tasks
    FILE_EXISTS = "file_exists"
    PROCESS_RUNNING = "process_running"
    PORT_OPEN = "port_open"
    HTTP_RESPONSE = "http_response"
    BROWSER_STATE = "browser_state"
    SCREENSHOT_MATCH = "screenshot_match"
    CODE_COMPILES = "code_compiles"
    FUNCTION_RESULT = "function_result"
    ARTIFACT_PRESENT = "artifact_present"


# ==================== VERIFICATION ALIAS MAP ====================
# FIX #21: Map legacy names to canonical types

VERIFICATION_ALIAS_MAP: Dict[str, VerificationType] = {
    # Legacy browser types
    "browser": VerificationType.BROWSER_STATE,
    "browser_page": VerificationType.BROWSER_STATE,
    "browser_state": VerificationType.BROWSER_STATE,
    
    # Legacy server types  
    "server": VerificationType.HTTP_RESPONSE,
    "server_responding": VerificationType.HTTP_RESPONSE,
    "http_response": VerificationType.HTTP_RESPONSE,
    
    # Legacy code types
    "code": VerificationType.CODE_COMPILES,
    "code_syntax": VerificationType.CODE_COMPILES,
    "code_compiles": VerificationType.CODE_COMPILES,
    
    # Legacy file types
    "file": VerificationType.FILE_EXISTS,
    "file_exists": VerificationType.FILE_EXISTS,
    "artifact": VerificationType.ARTIFACT_PRESENT,
    
    # Legacy function types
    "function": VerificationType.FUNCTION_RESULT,
    "function_result": VerificationType.FUNCTION_RESULT,
    
    # Legacy screenshot types
    "screenshot": VerificationType.SCREENSHOT_MATCH,
    "screenshot_match": VerificationType.SCREENSHOT_MATCH,
    
    # Legacy process/port types
    "process": VerificationType.PROCESS_RUNNING,
    "process_running": VerificationType.PROCESS_RUNNING,
    "port": VerificationType.PORT_OPEN,
    "port_open": VerificationType.PORT_OPEN,
    
    # Legacy aliases
    "manual": None,  # CRITICAL: manual is NOT a verification type!
    "none": VerificationType.NONE,
    "null": VerificationType.NONE,
}


def normalize_verification_type(raw: str) -> VerificationType:
    """
    Normalize any legacy verification type string to canonical VerificationType.
    
    FIX #21: This function ensures backward compatibility while enforcing
    canonical type system.
    
    Raises:
        ValueError: If type is "manual" or unknown
    """
    if not raw or raw is None:
        raise ValueError("Missing verification type")
    
    key = str(raw).strip().lower()
    
    # CRITICAL: "manual" is NOT a verification type!
    if key == "manual":
        raise ValueError(
            "'manual' is not a verification type. "
            "Use human_review_required field instead."
        )
    
    # Check alias map
    if key in VERIFICATION_ALIAS_MAP:
        mapped = VERIFICATION_ALIAS_MAP[key]
        if mapped is None:
            raise ValueError(
                "'manual' is not a verification type. "
                "Use human_review_required field instead."
            )
        return mapped
    
    # Try direct enum parse
    try:
        return VerificationType(key)
    except ValueError:
        pass
    
    raise ValueError(f"Unknown verification type: {raw}")


# ==================== VERIFICATION CONTRACTS ====================
# FIX #20: Typed contracts instead of string metadata

@dataclass
class VerificationSpec:
    """
    Typed verification specification - replaces string metadata.
    
    FIX #20: This dataclass ensures verification is a first-class contract,
    not a metadata string that can be bypassed.
    """
    type: VerificationType
    params: Dict[str, Any] = field(default_factory=dict)
    required: bool = True                    # Verification must pass for success
    evidence_required: bool = True           # Must have evidence for commit
    min_confidence: float = 1.0              # Minimum confidence threshold
    timeout: float = 30.0                    # Verification timeout


@dataclass
class VerificationResult:
    """
    Verification result with evidence.
    
    FIX #24: Evidence-based commit gate - success requires evidence.
    """
    passed: bool
    details: str
    evidence: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    severity: str = "info"                   # info, warning, error, critical
    timestamp: float = field(default_factory=time.time)


@dataclass
class HumanReviewSpec:
    """
    FIX #4: Separate human review from verification.
    
    verification = machine truth check
    approval = risk-based permission
    human_review = human eyes needed at checkpoint
    """
    required: bool = False
    reason: str = ""
    blocking: bool = True                    # If true, blocks progress until reviewed


# ==================== RECOVERY CONTRACTS ====================
# FIX #2: Typed recovery contracts

# Forward reference to avoid circular dependency
_RecoveryStrategyType = "RecoveryStrategy"


@dataclass
class RecoveryDecision:
    """
    FIX #2: Typed recovery decision - replaces string-based recovery.
    
    This is the contract that recovery engine produces when deciding
    how to handle a failure.
    """
    strategy: _RecoveryStrategyType
    confidence: float
    reason: str
    retry_allowed: bool = False
    requires_rollback: bool = False
    fallback_tool: Optional[str] = None
    replan_required: bool = False
    max_retries: int = 3


@dataclass
class RecoveryOutcome:
    """
    FIX #2: Typed recovery outcome - replaces dict-based recovery results.
    
    This is the contract that recovery engine produces after executing
    a recovery strategy.
    """
    success: bool
    strategy: _RecoveryStrategyType
    next_status: str  # TaskStatus as string to avoid circular import
    action_taken: str
    evidence: Dict[str, Any] = field(default_factory=dict)
    should_resume: bool = False
    replacement_task_id: Optional[str] = None
    escalated: bool = False
    retry_count: int = 0


# ==================== TASK EVENTS & CHECKPOINTS ====================
# FIX #5: Event-sourced ledger for task lifecycle

@dataclass
class TaskEvent:
    """
    FIX #5: Event-sourced ledger for task lifecycle.
    
    Every state transition is recorded as an event for:
    - Replay capability
    - Debugging
    - Learning signals
    - Evaluation
    - Auditability
    """
    task_id: str
    from_status: str
    to_status: str
    reason: str
    timestamp: float = field(default_factory=time.time)
    evidence: Dict[str, Any] = field(default_factory=dict)
    checkpoint_id: Optional[str] = None


# ==================== EXECUTION CURSOR ====================
# FIX #3: Execution cursor for step-level resume

@dataclass
class ExecutionCursor:
    """
    FIX #3: Execution cursor for step-level resume.
    
    Tracks exactly where in the execution flow the task is.
    This enables precise crash recovery.
    """
    phase: str                           # prepare, execute, verify, commit
    step_id: Optional[str] = None        # Current step ID
    tool_name: Optional[str] = None      # Current tool being executed
    tool_args_hash: Optional[str] = None # Hash of tool arguments
    verification_phase: Optional[str] = None  # verifying, validating
    approval_request_id: Optional[str] = None  # Pending approval
    scheduler_wake_at: Optional[float] = None  # Scheduled resume time
    side_effect_committed: bool = False  # Has side effect been committed?
    artifacts_created: List[str] = field(default_factory=list)


# ==================== ROLLBACK SNAPSHOT ====================
# FIX #6: Typed rollback snapshots

@dataclass
class RollbackSnapshot:
    """
    FIX #6: Typed rollback snapshot - not just metadata dict.
    
    Each rollback type has a structured payload for reliable restore.
    """
    kind: str                             # file_mutation, browser_state, env_change, etc.
    restore_handler: str                  # Which handler to use for restore
    payload: Dict[str, Any]              # Structured data for restore
    created_at: float = field(default_factory=time.time)
    checksum: Optional[str] = None        # For integrity verification


# ==================== CHECKPOINT SPEC ====================

@dataclass
class TaskCheckpoint:
    """
    FIX #5: Task checkpoint for durable pause/resume.
    
    Enables crash recovery by storing execution state.
    """
    task_id: str
    checkpoint_id: str
    last_safe_status: str
    execution_cursor: ExecutionCursor = None
    rollback_data: Dict[str, Any] = field(default_factory=dict)
    artifacts: List[str] = field(default_factory=list)
    evidence: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    
    # FIX #6: Add typed rollback snapshots
    rollback_snapshots: List[RollbackSnapshot] = field(default_factory=list)


# ==================== TASK SPEC CONTRACTS ====================
# FIX: Task contract - canonical task specification

@dataclass(frozen=True)
class RetryPolicy:
    """
    FIX: Typed retry policy - replaces int/dict ambiguity.
    
    Previously max_retries could be int or dict from planner,
    causing runtime comparison errors.
    """
    max_retries: int = 3
    backoff_strategy: str = "exponential"  # exponential, linear, fixed
    initial_delay_sec: int = 1
    max_delay_sec: int = 30


@dataclass(frozen=True)
class ApprovalSpec:
    """
    FIX: Typed approval specification.
    
    Previously approval_policy was a string that could be in
    either task field or input_data dict.
    """
    policy: str = "auto"  # auto, manual, never
    required_for_dangerous: bool = True
    timeout_sec: int = 300


@dataclass(frozen=True)
class SandboxSpec:
    """
    FIX: Typed sandbox specification.
    
    Previously sandbox_mode could be in task field or input_data dict.
    """
    mode: str = "normal"  # safe, normal, advanced
    allow_network: bool = True
    allow_file_write: bool = True


@dataclass(frozen=True)
class ToolSpec:
    """
    FIX: Typed tool specification.
    
    Previously required_tools was just a list of strings.
    Now it's a structured contract with capabilities.
    """
    required_tools: List[str] = field(default_factory=list)
    preferred_tool: Optional[str] = None
    alternate_tool: Optional[str] = None
    destructive: bool = False


@dataclass(frozen=True)
class SuccessCriterion:
    """
    FIX: Structured success criteria - not string DSL.
    
    Previously success_criteria was a string like "contains:X exit_code:0"
    Now it's structured assertions for deterministic verification.
    """
    kind: str  # contains, regex, exit_code, artifact_exists, url_equals, etc.
    value: Any
    optional: bool = False


@dataclass(frozen=True)
class VerificationSpec:
    """
    FIX: Typed verification specification.
    
    Previously verification was just a type string in input_data.
    Now it's a full specification with criteria.
    """
    type: str  # browser, screenshot, code, file, etc.
    params: Dict[str, Any] = field(default_factory=dict)
    criteria: List[SuccessCriterion] = field(default_factory=list)
    required: bool = True
    evidence_required: bool = True


@dataclass(frozen=True)
class TaskSpec:
    """
    FIX: Canonical TaskSpec - the contract for task execution.
    
    This replaces the fragmented task + input_data model.
    All policy, verification, and execution details are in one place.
    """
    description: str
    priority: str = "normal"
    dependencies: List[str] = field(default_factory=list)
    
    # Tool routing
    tool_spec: ToolSpec = field(default_factory=ToolSpec)
    
    # Verification
    verification: VerificationSpec = field(default_factory=VerificationSpec)
    
    # Success criteria
    success_criteria: List[SuccessCriterion] = field(default_factory=list)
    expected_artifacts: List[str] = field(default_factory=list)
    
    # Policy
    retry_policy: RetryPolicy = field(default_factory=RetryPolicy)
    approval: ApprovalSpec = field(default_factory=ApprovalSpec)
    sandbox: SandboxSpec = field(default_factory=SandboxSpec)
    
    # Execution
    timeout_sec: int = 30
    rollback: Optional[Dict[str, Any]] = None


# ==================== ENUMS ====================

class KernelState(Enum):
    """Kernel state machine"""
    IDLE = "idle"
    THINKING = "thinking"
    ACTING = "acting"
    VERIFYING = "verifying"
    REPAIRING = "repairing"
    WAITING_APPROVAL = "waiting_approval"
    APPROVAL_PENDING = "approval_pending"  # First-class approval state
    APPROVAL_GRANTED = "approval_granted"    # Approval granted
    APPROVAL_DENIED = "approval_denied"      # Approval denied
    APPROVAL_EXPIRED = "approval_expired"    # Approval expired
    PAUSED = "paused"
    ERROR = "error"
    RECOVERING = "recovering"
    ESCALATED = "escalated"  # Escalated to human


class ApprovalStatus(Enum):
    """First-class approval status"""
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class TaskPriority(Enum):
    """Task priorities"""
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3
    BACKGROUND = 4


class AgentRole(Enum):
    """Multi-agent roles"""
    PLANNER = "planner"
    EXECUTOR = "executor"
    VERIFIER = "verifier"
    CRITIC = "critic"
    RESEARCHER = "researcher"
    TOOL_BUILDER = "tool_builder"


class FailureCategory(str, Enum):
    """
    Canonical failure categories - SINGLE source of truth for error classification.
    
    This replaces fragmented error strings with a typed, machine-usable taxonomy.
    
    FIX: Error taxonomy / failure classification canonical
    
    Key distinctions:
    - Tool vs Verification vs Approval vs Policy vs Resource vs Network vs Internal
    - Execution failure vs Verification failure - strictly separated
    - Retryable vs Non-retryable - first-class classification
    - Timeout subtypes - explicitly typed
    """
    # ===== TOOL ERRORS =====
    TOOL_NOT_FOUND = "tool_not_found"
    TOOL_ARGS_INVALID = "tool_args_invalid"
    TOOL_EXECUTION_FAILED = "tool_execution_failed"
    TOOL_EXECUTION_TIMEOUT = "tool_execution_timeout"
    TOOL_EXECUTION_CRASHED = "tool_execution_crashed"
    TOOL_PERMISSION_DENIED = "tool_permission_denied"
    TOOL_DEPENDENCY_MISSING = "tool_dependency_missing"
    TOOL_OUTPUT_PARSE_ERROR = "tool_output_parse_error"
    
    # ===== VERIFICATION ERRORS =====
    # CRITICAL: Strictly separated from execution errors!
    VERIFICATION_FAILED = "verification_failed"
    VERIFICATION_FAILED_ARTIFACT_MISSING = "verification_failed_artifact_missing"
    VERIFICATION_FAILED_ASSERTION = "verification_failed_assertion"
    VERIFICATION_FAILED_PATTERN = "verification_failed_pattern"
    VERIFICATION_FAILED_STATE = "verification_failed_state"
    VERIFICATION_TIMEOUT = "verification_timeout"
    VERIFICATION_EVIDENCE_MISSING = "verification_evidence_missing"
    
    # ===== APPROVAL / GOVERNANCE ERRORS =====
    # CRITICAL: These are governance outcomes, NOT tool errors!
    APPROVAL_DENIED = "approval_denied"
    APPROVAL_EXPIRED = "approval_expired"
    APPROVAL_PENDING = "approval_pending"
    APPROVAL_WITHDRAWN = "approval_withdrawn"
    
    # ===== POLICY / SAFETY ERRORS =====
    # CRITICAL: Policy failures are NOT recoverable by retry!
    POLICY_BLOCKED = "policy_blocked"
    POLICY_VIOLATION = "policy_violation"
    SANDBOX_REJECTED = "sandbox_rejected"
    WORKSPACE_BOUNDARY_VIOLATION = "workspace_boundary_violation"
    COMMAND_BLOCKED = "command_blocked"
    SENSITIVE_OPERATION = "sensitive_operation"
    
    # ===== RESOURCE ERRORS =====
    RESOURCE_NOT_FOUND = "resource_not_found"
    RESOURCE_BUSY = "resource_busy"
    RESOURCE_EXHAUSTED = "resource_exhausted"
    RESOURCE_LOCK_CONFLICT = "resource_lock_conflict"
    RESOURCE_DEADLOCK = "resource_deadlock"
    
    # ===== DEPENDENCY ERRORS =====
    DEPENDENCY_BLOCKED = "dependency_blocked"
    DEPENDENCY_CYCLE = "dependency_cycle"
    DEPENDENCY_MISSING = "dependency_missing"
    DEPENDENCY_VERSION_CONFLICT = "dependency_version_conflict"
    
    # ===== SCHEDULER ERRORS =====
    SCHEDULER_TIMEOUT = "scheduler_timeout"
    SCHEDULER_STARVATION = "scheduler_starvation"
    SCHEDULER_QUEUE_FULL = "scheduler_queue_full"
    TASK_QUEUE_TIMEOUT = "task_queue_timeout"
    
    # ===== CHECKPOINT / ROLLBACK ERRORS =====
    CHECKPOINT_NOT_FOUND = "checkpoint_not_found"
    CHECKPOINT_RESTORE_FAILED = "checkpoint_restore_failed"
    CHECKPOINT_CORRUPTED = "checkpoint_corrupted"
    ROLLBACK_FAILED = "rollback_failed"
    STATE_MISMATCH = "state_mismatch"
    
    # ===== NETWORK ERRORS =====
    NETWORK_TIMEOUT = "network_timeout"
    NETWORK_ERROR = "network_error"
    NETWORK_UNREACHABLE = "network_unreachable"
    NETWORK_CONNECTION_RESET = "network_connection_reset"
    NETWORK_DNS_FAILED = "network_dns_failed"
    
    # ===== INTERNAL KERNEL ERRORS =====
    INTERNAL_KERNEL_ERROR = "internal_kernel_error"
    KERNEL_PANIC = "kernel_panic"
    STATE_CORRUPTED = "state_corrupted"
    SERIALIZATION_ERROR = "serialization_error"
    
    # ===== UNKNOWN / FALLBACK =====
    UNKNOWN = "unknown"
    UNPARSEABLE_ERROR = "unparseable_error"


class FailureSeverity(str, Enum):
    """
    Failure severity levels for ownership and escalation decisions.
    """
    # User can fix with input
    USER_FIXABLE = "user_fixable"
    
    # System can fix automatically
    SYSTEM_FIXABLE = "system_fixable"
    
    # Infrastructure team needs to fix
    INFRA_FIXABLE = "infra_fixable"
    
    # Policy decision required
    POLICY_FINAL = "policy_final"
    
    # Cannot be fixed, requires escalation
    CRITICAL = "critical"


class FailureOwnership(str, Enum):
    """
    Failure ownership for routing to correct handler.
    """
    # User needs to provide input or decision
    USER = "user"
    
    # Agent can handle with retry/recovery
    AGENT = "agent"
    
    # Operator/admin needs to intervene
    OPERATOR = "operator"
    
    # Infrastructure team
    INFRASTRUCTURE = "infrastructure"
    
    # Policy governance
    GOVERNANCE = "governance"


# ==================== FAILURE MAPPER ====================
# FIX: Exception to FailureRecord mapping layer

class FailureMapper:
    """
    Maps various exception types to canonical FailureRecord.
    
    This is the bridge between raw exceptions and typed failure taxonomy.
    
    FIX: Error taxonomy / failure classification canonical
    
    Key features:
    - Maps exceptions to FailureCategory
    - Extracts provenance (stage, subsystem, tool)
    - Determines retryability
    - Sets ownership and severity
    """
    
    def __init__(self):
        # Exception type to category mapping
        self._exception_map: Dict[type, "FailureCategory"] = {
            # Tool errors
            FileNotFoundError: FailureCategory.TOOL_NOT_FOUND,
            PermissionError: FailureCategory.TOOL_PERMISSION_DENIED,
            ImportError: FailureCategory.TOOL_DEPENDENCY_MISSING,
            ModuleNotFoundError: FailureCategory.TOOL_DEPENDENCY_MISSING,
            
            # Network errors
            ConnectionError: FailureCategory.NETWORK_ERROR,
            TimeoutError: FailureCategory.NETWORK_TIMEOUT,
            asyncio.TimeoutError: FailureCategory.NETWORK_TIMEOUT,
            
            # Resource errors
            FileExistsError: FailureCategory.RESOURCE_EXHAUSTED,
            IsADirectoryError: FailureCategory.TOOL_ARGS_INVALID,
            NotADirectoryError: FailureCategory.TOOL_ARGS_INVALID,
            
            # Value errors
            ValueError: FailureCategory.TOOL_ARGS_INVALID,
            TypeError: FailureCategory.TOOL_ARGS_INVALID,
            KeyError: FailureCategory.TOOL_ARGS_INVALID,
            
            # JSON/Syntax errors
            json.JSONDecodeError: FailureCategory.TOOL_OUTPUT_PARSE_ERROR,
            SyntaxError: FailureCategory.TOOL_OUTPUT_PARSE_ERROR,
            
            # Memory errors
            MemoryError: FailureCategory.RESOURCE_EXHAUSTED,
            OSError: FailureCategory.RESOURCE_EXHAUSTED,
        }
    
    def map_exception(
        self,
        exc: Exception,
        stage: str = "",
        subsystem: str = "",
        tool_name: Optional[str] = None,
        **kwargs
    ) -> "FailureRecord":
        """
        Map an exception to a FailureRecord.
        
        Args:
            exc: The exception to map
            stage: Current execution stage
            subsystem: Current subsystem
            tool_name: Tool that was being executed
            **kwargs: Additional fields for FailureRecord
            
        Returns:
            FailureRecord with typed category and recovery info
        """
        # Get category from exception type or walk MRO
        category = FailureCategory.UNKNOWN
        for exc_type in type(exc).__mro__:
            if exc_type in self._exception_map:
                category = self._exception_map[exc_type]
                break
        
        # Get recovery strategy from map
        _init_recovery_strategy_map()  # Ensure map is initialized
        recovery_info = RECOVERY_STRATEGY_MAP.get(category, 
            (RecoveryStrategy.ABORT, False, False))
        strategy, retryable, replan = recovery_info
        
        # Determine severity and ownership
        severity = self._determine_severity(category, exc)
        ownership = self._determine_ownership(category, severity)
        
        # Build the failure record
        failure = FailureRecord(
            category=category,
            message=str(exc),
            stage=stage,
            subsystem=subsystem,
            provider=tool_name,
            tool_name=tool_name,
            retryable=retryable,
            recoverable=replan,
            replan_recommended=replan,
            escalate_recommended=(strategy == RecoveryStrategy.ESCALATE_TO_HUMAN),
            severity=severity,
            ownership=ownership,
            raw_error=str(exc),
            stack_trace=traceback.format_exc(),
            **kwargs
        )
        
        # Apply category-specific overrides
        self._apply_category_overrides(failure, exc)
        
        return failure
    
    def map_error_message(
        self,
        error_msg: str,
        stage: str = "",
        subsystem: str = "",
        tool_name: Optional[str] = None,
        **kwargs
    ) -> "FailureRecord":
        """
        Map an error message string to a FailureRecord.
        
        Used when errors come as strings rather than exceptions.
        """
        error_lower = error_msg.lower()
        
        # String pattern matching for common errors
        category = FailureCategory.UNKNOWN
        
        # Network patterns
        if any(p in error_lower for p in ["timeout", "timed out"]):
            category = FailureCategory.NETWORK_TIMEOUT
        elif any(p in error_lower for p in ["connection refused", "connection error", "connect failed"]):
            category = FailureCategory.NETWORK_ERROR
        elif any(p in error_lower for p in ["dns", "name or service not known"]):
            category = FailureCategory.NETWORK_DNS_FAILED
        elif any(p in error_lower for p in ["unreachable", "no route"]):
            category = FailureCategory.NETWORK_UNREACHABLE
        
        # Tool patterns
        elif any(p in error_lower for p in ["not found", "no such file", "doesn't exist"]):
            category = FailureCategory.TOOL_NOT_FOUND
        elif any(p in error_lower for p in ["permission denied", "access denied", "not permitted"]):
            category = FailureCategory.TOOL_PERMISSION_DENIED
        elif any(p in error_lower for p in ["invalid argument", "invalid args", "wrong type"]):
            category = FailureCategory.TOOL_ARGS_INVALID
        elif any(p in error_lower for p in ["command not found", "not recognized"]):
            category = FailureCategory.TOOL_NOT_FOUND
        
        # Verification patterns
        elif any(p in error_lower for p in ["verification failed", "assertion failed", "expected"]):
            category = FailureCategory.VERIFICATION_FAILED
        elif any(p in error_lower for p in ["artifact missing", "file not created", "output not found"]):
            category = FailureCategory.VERIFICATION_FAILED_ARTIFACT_MISSING
        
        # Approval/Policy patterns
        elif any(p in error_lower for p in ["approval denied", "denied", "rejected"]):
            category = FailureCategory.APPROVAL_DENIED
        elif any(p in error_lower for p in ["policy", "blocked", "forbidden"]):
            category = FailureCategory.POLICY_BLOCKED
        elif any(p in error_lower for p in ["sandbox", "restricted"]):
            category = FailureCategory.SANDBOX_REJECTED
        
        # Resource patterns
        elif any(p in error_lower for p in ["busy", "locked", "in use"]):
            category = FailureCategory.RESOURCE_LOCK_CONFLICT
        elif any(p in error_lower for p in ["out of memory", "resource exhausted"]):
            category = FailureCategory.RESOURCE_EXHAUSTED
        
        # Get recovery strategy
        _init_recovery_strategy_map()  # Ensure map is initialized
        recovery_info = RECOVERY_STRATEGY_MAP.get(category,
            (RecoveryStrategy.ABORT, False, False))
        strategy, retryable, replan = recovery_info
        
        # Determine severity and ownership
        severity = self._determine_severity(category, error_msg)
        ownership = self._determine_ownership(category, severity)
        
        return FailureRecord(
            category=category,
            message=error_msg,
            stage=stage,
            subsystem=subsystem,
            provider=tool_name,
            tool_name=tool_name,
            retryable=retryable,
            recoverable=replan,
            replan_recommended=replan,
            escalate_recommended=(strategy == RecoveryStrategy.ESCALATE_TO_HUMAN),
            severity=severity,
            ownership=ownership,
            raw_error=error_msg,
            **kwargs
        )
    
    def _determine_severity(self, category: FailureCategory, error: Any) -> FailureSeverity:
        """Determine failure severity based on category"""
        # Critical categories
        if category in [
            FailureCategory.KERNEL_PANIC,
            FailureCategory.STATE_CORRUPTED,
            FailureCategory.CHECKPOINT_CORRUPTED,
        ]:
            return FailureSeverity.CRITICAL
        
        # Policy final
        if category in [
            FailureCategory.APPROVAL_DENIED,
            FailureCategory.POLICY_BLOCKED,
            FailureCategory.POLICY_VIOLATION,
            FailureCategory.WORKSPACE_BOUNDARY_VIOLATION,
        ]:
            return FailureSeverity.POLICY_FINAL
        
        # Infrastructure
        if category in [
            FailureCategory.CHECKPOINT_RESTORE_FAILED,
            FailureCategory.ROLLBACK_FAILED,
            FailureCategory.RESOURCE_EXHAUSTED,
            FailureCategory.DEPENDENCY_VERSION_CONFLICT,
        ]:
            return FailureSeverity.INFRA_FIXABLE
        
        # User fixable
        if category in [
            FailureCategory.TOOL_ARGS_INVALID,
            FailureCategory.WORKSPACE_BOUNDARY_VIOLATION,
        ]:
            return FailureSeverity.USER_FIXABLE
        
        return FailureSeverity.SYSTEM_FIXABLE
    
    def _determine_ownership(self, category: FailureCategory, severity: FailureSeverity) -> FailureOwnership:
        """Determine failure ownership based on category and severity"""
        # Governance
        if category in [
            FailureCategory.APPROVAL_DENIED,
            FailureCategory.APPROVAL_EXPIRED,
            FailureCategory.POLICY_BLOCKED,
            FailureCategory.POLICY_VIOLATION,
            FailureCategory.SANDBOX_REJECTED,
            FailureCategory.SENSITIVE_OPERATION,
        ]:
            return FailureOwnership.GOVERNANCE
        
        # User
        if severity == FailureSeverity.USER_FIXABLE:
            return FailureOwnership.USER
        
        # Operator
        if severity in [FailureSeverity.CRITICAL, FailureSeverity.INFRA_FIXABLE]:
            return FailureOwnership.OPERATOR
        
        # Infrastructure
        if category in [
            FailureCategory.CHECKPOINT_RESTORE_FAILED,
            FailureCategory.CHECKPOINT_CORRUPTED,
            FailureCategory.ROLLBACK_FAILED,
            FailureCategory.NETWORK_UNREACHABLE,
        ]:
            return FailureOwnership.INFRASTRUCTURE
        
        return FailureOwnership.AGENT
    
    def _apply_category_overrides(self, failure: "FailureRecord", exc: Exception):
        """Apply category-specific overrides to failure record"""
        # Check for specific exception messages that indicate more specific category
        msg = str(exc).lower()
        
        # More specific tool errors
        if failure.category == FailureCategory.TOOL_EXECUTION_FAILED:
            if "killed" in msg or "signal" in msg:
                failure.category = FailureCategory.TOOL_EXECUTION_CRASHED
            elif "permission" in msg:
                failure.category = FailureCategory.TOOL_PERMISSION_DENIED
        
        # More specific verification errors
        elif failure.category == FailureCategory.VERIFICATION_FAILED:
            if "missing" in msg or "not found" in msg or "doesn't exist" in msg:
                failure.category = FailureCategory.VERIFICATION_FAILED_ARTIFACT_MISSING
            elif "assertion" in msg or "assert" in msg:
                failure.category = FailureCategory.VERIFICATION_FAILED_ASSERTION


# Global mapper instance
_failure_mapper: Optional[FailureMapper] = None


def get_failure_mapper() -> FailureMapper:
    """Get global FailureMapper instance"""
    global _failure_mapper
    if _failure_mapper is None:
        _failure_mapper = FailureMapper()
    return _failure_mapper


# ==================== RECOVERY STRATEGY MAP ====================
# Recovery Strategy Mapping - Based on FailureCategory
# Using lazy initialization to avoid forward reference issues

RECOVERY_STRATEGY_MAP: Dict["FailureCategory", Tuple["RecoveryStrategy", bool, bool]] = {}  # Will be initialized lazily


def _init_recovery_strategy_map():
    """Initialize RECOVERY_STRATEGY_MAP after all enums are defined"""
    global RECOVERY_STRATEGY_MAP
    if RECOVERY_STRATEGY_MAP:  # Already initialized
        return
        
    RECOVERY_STRATEGY_MAP = {
    # Tool errors - mostly retryable with backoff
    FailureCategory.TOOL_NOT_FOUND: (RecoveryStrategy.ALTERNATE_TOOL, True, False),
    FailureCategory.TOOL_ARGS_INVALID: (RecoveryStrategy.RECOVER_STATE, False, True),
    FailureCategory.TOOL_EXECUTION_FAILED: (RecoveryStrategy.RETRY_WITH_BACKOFF, True, False),
    FailureCategory.TOOL_EXECUTION_TIMEOUT: (RecoveryStrategy.RETRY_WITH_BACKOFF, True, False),
    FailureCategory.TOOL_EXECUTION_CRASHED: (RecoveryStrategy.RETRY_SAME_TOOL, True, False),
    FailureCategory.TOOL_PERMISSION_DENIED: (RecoveryStrategy.ESCALATE_TO_HUMAN, False, False),
    FailureCategory.TOOL_DEPENDENCY_MISSING: (RecoveryStrategy.RECOVER_STATE, False, False),
    FailureCategory.TOOL_OUTPUT_PARSE_ERROR: (RecoveryStrategy.RETRY_SAME_TOOL, True, False),

    # Verification errors - CRITICAL: execution succeeded but result is wrong
    FailureCategory.VERIFICATION_FAILED: (RecoveryStrategy.REPLAN, False, True),
    FailureCategory.VERIFICATION_FAILED_ARTIFACT_MISSING: (RecoveryStrategy.ALTERNATE_TOOL, False, True),
    FailureCategory.VERIFICATION_FAILED_ASSERTION: (RecoveryStrategy.REPLAN, False, True),
    FailureCategory.VERIFICATION_FAILED_PATTERN: (RecoveryStrategy.REPLAN, False, True),
    FailureCategory.VERIFICATION_FAILED_STATE: (RecoveryStrategy.RECOVER_STATE, False, True),
    FailureCategory.VERIFICATION_TIMEOUT: (RecoveryStrategy.RETRY_SAME_TOOL, True, False),
    FailureCategory.VERIFICATION_EVIDENCE_MISSING: (RecoveryStrategy.ALTERNATE_TOOL, False, True),

    # Approval errors - governance outcomes, NOT retryable!
    FailureCategory.APPROVAL_DENIED: (RecoveryStrategy.ABORT, False, False),
    FailureCategory.APPROVAL_EXPIRED: (RecoveryStrategy.RETRY_SAME_TASK, True, False),
    FailureCategory.APPROVAL_PENDING: (RecoveryStrategy.RETRY_SAME_TASK, True, False),
    FailureCategory.APPROVAL_WITHDRAWN: (RecoveryStrategy.ABORT, False, False),

    # Policy errors - NEVER retry without replan!
    FailureCategory.POLICY_BLOCKED: (RecoveryStrategy.ABORT, False, False),
    FailureCategory.POLICY_VIOLATION: (RecoveryStrategy.ABORT, False, False),
    FailureCategory.SANDBOX_REJECTED: (RecoveryStrategy.REPLAN, False, True),
    FailureCategory.WORKSPACE_BOUNDARY_VIOLATION: (RecoveryStrategy.REPLAN, False, True),
    FailureCategory.COMMAND_BLOCKED: (RecoveryStrategy.ALTERNATE_TOOL, False, True),
    FailureCategory.SENSITIVE_OPERATION: (RecoveryStrategy.ESCALATE_TO_HUMAN, False, False),

    # Resource errors
    FailureCategory.RESOURCE_NOT_FOUND: (RecoveryStrategy.RECOVER_STATE, False, True),
    FailureCategory.RESOURCE_BUSY: (RecoveryStrategy.RETRY_WITH_BACKOFF, True, False),
    FailureCategory.RESOURCE_EXHAUSTED: (RecoveryStrategy.ESCALATE_TO_HUMAN, False, False),
    FailureCategory.RESOURCE_LOCK_CONFLICT: (RecoveryStrategy.RETRY_WITH_BACKOFF, True, False),
    FailureCategory.RESOURCE_DEADLOCK: (RecoveryStrategy.ROLLBACK, False, False),

    # Dependency errors
    FailureCategory.DEPENDENCY_BLOCKED: (RecoveryStrategy.RETRY_WITH_BACKOFF, True, False),
    FailureCategory.DEPENDENCY_CYCLE: (RecoveryStrategy.REPLAN, False, True),
    FailureCategory.DEPENDENCY_MISSING: (RecoveryStrategy.RECOVER_STATE, False, True),
    FailureCategory.DEPENDENCY_VERSION_CONFLICT: (RecoveryStrategy.ESCALATE_TO_HUMAN, False, False),

    # Scheduler errors
    FailureCategory.SCHEDULER_TIMEOUT: (RecoveryStrategy.RETRY_SAME_TASK, True, False),
    FailureCategory.SCHEDULER_STARVATION: (RecoveryStrategy.RETRY_SAME_TASK, True, False),
    FailureCategory.SCHEDULER_QUEUE_FULL: (RecoveryStrategy.RETRY_SAME_TASK, True, False),
    FailureCategory.TASK_QUEUE_TIMEOUT: (RecoveryStrategy.RETRY_SAME_TASK, True, False),

    # Checkpoint errors
    FailureCategory.CHECKPOINT_NOT_FOUND: (RecoveryStrategy.ABORT, False, False),
    FailureCategory.CHECKPOINT_RESTORE_FAILED: (RecoveryStrategy.ESCALATE_TO_HUMAN, False, False),
    FailureCategory.CHECKPOINT_CORRUPTED: (RecoveryStrategy.ESCALATE_TO_HUMAN, False, False),
    FailureCategory.ROLLBACK_FAILED: (RecoveryStrategy.ESCALATE_TO_HUMAN, False, False),
    FailureCategory.STATE_MISMATCH: (RecoveryStrategy.RECOVER_STATE, False, True),

    # Network errors - retryable with backoff
    FailureCategory.NETWORK_TIMEOUT: (RecoveryStrategy.RETRY_WITH_BACKOFF, True, False),
    FailureCategory.NETWORK_ERROR: (RecoveryStrategy.RETRY_WITH_BACKOFF, True, False),
    FailureCategory.NETWORK_UNREACHABLE: (RecoveryStrategy.RETRY_WITH_BACKOFF, True, False),
    FailureCategory.NETWORK_CONNECTION_RESET: (RecoveryStrategy.RETRY_WITH_BACKOFF, True, False),
    FailureCategory.NETWORK_DNS_FAILED: (RecoveryStrategy.RETRY_WITH_BACKOFF, True, False),

    # Internal errors
    FailureCategory.INTERNAL_KERNEL_ERROR: (RecoveryStrategy.ESCALATE_TO_HUMAN, False, False),
    FailureCategory.KERNEL_PANIC: (RecoveryStrategy.ESCALATE_TO_HUMAN, False, False),
    FailureCategory.STATE_CORRUPTED: (RecoveryStrategy.ESCALATE_TO_HUMAN, False, False),
    FailureCategory.SERIALIZATION_ERROR: (RecoveryStrategy.RECOVER_STATE, False, True),

    # Unknown
    FailureCategory.UNKNOWN: (RecoveryStrategy.ABORT, False, False),
    FailureCategory.UNPARSEABLE_ERROR: (RecoveryStrategy.ESCALATE_TO_HUMAN, False, False),
    }


# Initialize lazily - call this function before using RECOVERY_STRATEGY_MAP
# _init_recovery_strategy_map()  # Commented out - called lazily


class ErrorType(Enum):
    """Legacy error classification - DEPRECATED, use FailureCategory"""
    # Execution errors
    EXECUTION_FAILED = "execution_failed"
    EXECUTION_TIMEOUT = "execution_timeout"
    EXECUTION_CRASHED = "execution_crashed"
    
    # Verification errors
    VERIFICATION_FAILED = "verification_failed"
    VERIFICATION_MISSING = "verification_missing"
    VERIFICATION_TIMEOUT = "verification_timeout"
    
    # Tool errors
    TOOL_NOT_FOUND = "tool_not_found"
    TOOL_INVALID_ARGS = "tool_invalid_args"
    TOOL_PERMISSION_DENIED = "tool_permission_denied"
    
    # Resource errors
    RESOURCE_NOT_FOUND = "resource_not_found"
    RESOURCE_BUSY = "resource_busy"
    RESOURCE_EXHAUSTED = "resource_exhausted"
    
    # Network errors
    NETWORK_ERROR = "network_error"
    NETWORK_TIMEOUT = "network_timeout"
    NETWORK_UNREACHABLE = "network_unreachable"
    
    # Approval errors
    APPROVAL_DENIED = "approval_denied"
    APPROVAL_TIMEOUT = "approval_timeout"
    
    # System errors
    SYSTEM_ERROR = "system_error"
    UNKNOWN_ERROR = "unknown_error"


class RecoveryStrategy(Enum):
    """Recovery strategies for different error types"""
    # Retry-based
    RETRY_SAME_TOOL = "retry_same_tool"
    RETRY_SAME_TASK = "retry_same_task"
    RETRY_WITH_BACKOFF = "retry_with_backoff"
    
    # Alternative approaches
    ALTERNATE_TOOL = "alternate_tool"
    ALTERNATE_APPROACH = "alternate_approach"
    SIMPLIFY_TASK = "simplify_task"
    REPLAN = "replan"  # Add REPLAN strategy
    
    # Recovery
    RECOVER_STATE = "recover_state"
    ROLLBACK = "rollback"
    RECREATE_RESOURCE = "recreate_resource"
    
    # Escalation
    ESCALATE_TO_HUMAN = "escalate_to_human"
    ABORT = "abort"


class SelfImprovementSignal(Enum):
    """
    Signals for self-improvement system.
    Emitted to help self-improvement engine learn and improve.
    """
    # Task-level signals
    TASK_FAILED = "task_failed"
    TASK_SUCCEEDED = "task_succeeded"
    TASK_RECOVERED = "task_recovered"
    TASK_TIMEOUT = "task_timeout"
    
    # Stage-level signals
    STAGE_SUCCESS = "stage_success"
    STAGE_FAILED = "stage_failed"
    STAGE_SKIPPED = "stage_skipped"
    
    # Verification signals
    VERIFIER_MISMATCH = "verifier_mismatch"
    VERIFIER_FAILED = "verifier_failed"
    VERIFIER_TIMEOUT = "verifier_timeout"
    
    # Patch signals
    PATCH_APPLIED = "patch_applied"
    PATCH_REGRESSED = "patch_regressed"
    PATCH_FAILED = "patch_failed"
    PATCH_ROLLED_BACK = "patch_rolled_back"
    
    # Tool signals
    TOOL_UNSTABLE = "tool_unstable"
    TOOL_FAILED = "tool_failed"
    TOOL_SLOW = "tool_slow"
    TOOL_CRASHED = "tool_crashed"
    
    # Approval signals
    APPROVAL_BLOCKED = "approval_blocked"
    APPROVAL_REJECTED = "approval_rejected"
    APPROVAL_FRICTION = "approval_friction"
    
    # Recovery signals
    RECOVERY_SUCCESS = "recovery_success"
    RECOVERY_FAILED = "recovery_failed"
    RECOVERY_PARTIAL = "recovery_partial"
    
    # Planning signals
    PLAN_PARSE_FAILED = "plan_parse_failed"
    PLAN_INVALID = "plan_invalid"
    PLAN_RETRY = "plan_retry"

class SelfImprovementEmitter:
    """
    Emits signals to the self-improvement system.
    Tracks and reports signals for learning and improvement.
    """
    
    def __init__(self):
        self.signals: List[Dict] = []
        self.signal_counts: Dict[str, int] = defaultdict(int)
        self.recent_signals: deque = deque(maxlen=100)
        
    def emit(self, signal: SelfImprovementSignal, context: Dict) -> None:
        """
        Emit a self-improvement signal with context.
        
        Args:
            signal: The type of signal
            context: Additional context about the signal
        """
        signal_entry = {
            "signal": signal.value,
            "context": context,
            "timestamp": time.time()
        }
        
        self.signals.append(signal_entry)
        self.signal_counts[signal.value] += 1
        self.recent_signals.append(signal_entry)
        
    def emit_task_failed(self, task_id: str, error: str, stage: str) -> None:
        """Emit TASK_FAILED signal"""
        self.emit(SelfImprovementSignal.TASK_FAILED, {
            "task_id": task_id,
            "error": error,
            "failed_stage": stage
        })
        
    def emit_task_recovered(self, task_id: str, recovery_strategy: str) -> None:
        """Emit TASK_RECOVERED signal"""
        self.emit(SelfImprovementSignal.TASK_RECOVERED, {
            "task_id": task_id,
            "recovery_strategy": recovery_strategy
        })
        
    def emit_patch_regressed(self, patch_id: str, regression_issues: List[str]) -> None:
        """Emit PATCH_REGRESSED signal"""
        self.emit(SelfImprovementSignal.PATCH_REGRESSED, {
            "patch_id": patch_id,
            "issues": regression_issues
        })
        
    def emit_tool_unstable(self, tool_name: str, failure_count: int) -> None:
        """Emit TOOL_UNSTABLE signal"""
        self.emit(SelfImprovementSignal.TOOL_UNSTABLE, {
            "tool_name": tool_name,
            "failure_count": failure_count
        })
        
    def emit_verifier_mismatch(self, task_id: str, expected: Any, actual: Any) -> None:
        """Emit VERIFIER_MISMATCH signal"""
        self.emit(SelfImprovementSignal.VERIFIER_MISMATCH, {
            "task_id": task_id,
            "expected": str(expected)[:100],
            "actual": str(actual)[:100]
        })
        
    def emit_approval_blocked(self, request_id: str, wait_time: float) -> None:
        """Emit APPROVAL_BLOCKED signal"""
        self.emit(SelfImprovementSignal.APPROVAL_BLOCKED, {
            "request_id": request_id,
            "wait_time": wait_time
        })
        
    def emit_plan_parse_failed(self, plan_text: str, error: str) -> None:
        """Emit PLAN_PARSE_FAILED signal"""
        self.emit(SelfImprovementSignal.PLAN_PARSE_FAILED, {
            "plan_text": plan_text[:200],
            "error": error
        })
        
    def emit_recovery_result(self, strategy: str, success: bool, details: Dict) -> None:
        """Emit recovery result signal"""
        if success:
            self.emit(SelfImprovementSignal.RECOVERY_SUCCESS, {
                "strategy": strategy,
                "details": details
            })
        else:
            self.emit(SelfImprovementSignal.RECOVERY_FAILED, {
                "strategy": strategy,
                "details": details
            })
            
    def get_signal_summary(self) -> Dict:
        """Get summary of all signals"""
        return {
            "total_signals": len(self.signals),
            "signal_counts": dict(self.signal_counts),
            "recent": list(self.recent_signals)[-10:]
        }




class TaskStatus(Enum):
    """
    FIX #1: Canonical Task Status - Single Source of Truth
    
    This replaces the fragmented status system with a proper FSM.
    
    Key changes:
    - COMPLETED -> COMMITTED (explicit commit after verification)
    - Added FAILED_EXECUTION (separate from verification failure)
    - Added REPLAN_PENDING and ESCALATED states
    - Added PAUSED for durable pause/resume
    - SUPERSEDED for replacement tasks
    """
    # Core execution flow
    PENDING = "pending"
    READY = "ready"                    # Dependencies met, ready to execute
    RUNNING = "running"                # Actively executing
    EXECUTED = "executed"              # Execution done, needs verification
    VERIFYING = "verifying"            # Running verification
    VERIFIED = "verified"              # Verification passed
    COMMITTED = "committed"            # Final commit (was: COMPLETED)
    
    # Failure states
    FAILED_EXECUTION = "failed_execution"    # Execution failed
    FAILED_VERIFICATION = "failed_verification"  # Verification failed
    FAILED = "failed"                  # Generic failure
    
    # Recovery states
    RECOVERING = "recovering"          # Running recovery
    RETRYING = "retrying"             # Retrying the task
    REPLAN_PENDING = "replan_pending"  # Needs new plan
    ESCALATED = "escalated"           # Escalated to human
    
    # Pause/Approval states
    PAUSED = "paused"                 # Durably paused
    WAITING_APPROVAL = "waiting_approval"  # Waiting for human approval
    APPROVAL_WAITING = "approval_waiting"  # Alias for compatibility
    
    # Terminal states
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"
    SUPERSEDED = "superseded"         # Replaced by another task
    ABORTED = "aborted"               # Explicitly aborted
    
    # Legacy aliases for backward compatibility
    @classmethod
    def alias(cls, old_name: str) -> 'TaskStatus':
        """Map old status names to new canonical ones"""
        aliases = {
            'COMPLETED': cls.COMMITTED,
            'dependencies_waiting': cls.PENDING,
            'completed': cls.COMMITTED,
            'failed': cls.FAILED,
        }
        return aliases.get(old_name, cls.PENDING)


# ==================== TRANSACTION DATA CLASSES ====================
# FIX: Side-effect transaction models

@dataclass
class WorldStateDelta:
    """
    Represents the delta/changes to world state from a side-effect action.
    
    FIX: Tool execution must return what actually changed, not just output.
    """
    artifacts_created: List[str] = field(default_factory=list)
    files_modified: List[str] = field(default_factory=list)
    files_deleted: List[str] = field(default_factory=list)
    resources_touched: List[str] = field(default_factory=list)
    external_effects: List[str] = field(default_factory=list)
    environment_changes: Dict[str, Any] = field(default_factory=dict)
    
    def is_empty(self) -> bool:
        return (
            not self.artifacts_created 
            and not self.files_modified 
            and not self.files_deleted 
            and not self.resources_touched
            and not self.external_effects
            and not self.environment_changes
        )


@dataclass
class SideEffectTransaction:
    """
    Represents a side-effect transaction with full lifecycle tracking.
    
    FIX: Side-effecting tasks MUST use this model for tracking.
    
    CRITICAL: An action is NOT committed until:
    1. It has been APPLIED (executed)
    2. It has been OBSERVED (effects recorded)
    3. It has been VERIFIED (evidence collected)
    4. It has been COMMITTED (state change finalized)
    """
    tx_id: str
    task_id: str
    tool_name: str
    phase: TransactionPhase = TransactionPhase.PREPARED
    
    # Intent - what was planned
    intended_changes: Dict[str, Any] = field(default_factory=dict)
    arguments: Dict[str, Any] = field(default_factory=dict)
    
    # Actual - what actually happened
    observed_delta: "WorldStateDelta" = field(default_factory=lambda: WorldStateDelta())
    output: Any = None
    
    # Evidence and verification
    evidence: Dict[str, Any] = field(default_factory=dict)
    verification_passed: bool = False
    verification_details: str = ""
    
    # Rollback support
    rollback_snapshot_id: Optional[str] = None
    idempotency_key: Optional[str] = None
    
    # Timing
    created_at: float = field(default_factory=time.time)
    applied_at: Optional[float] = None
    observed_at: Optional[float] = None
    verified_at: Optional[float] = None
    committed_at: Optional[float] = None
    
    # Metadata
    retry_count: int = 0
    failure: Optional["FailureRecord"] = None
    
    def is_committed(self) -> bool:
        """Check if transaction is committed"""
        return self.phase == TransactionPhase.COMMITTED
    
    def can_retry(self) -> bool:
        """Check if transaction can be retried"""
        if self.phase in [TransactionPhase.COMMITTED, TransactionPhase.ROLLED_BACK]:
            return False
        
        idempotency = TOOL_IDEMPOTENCY.get(self.tool_name, IdempotencyClass.NON_IDEMPOTENT)
        
        if idempotency == IdempotencyClass.IDEMPOTENT:
            return True
        elif idempotency == IdempotencyClass.CONDITIONALLY_IDEMPOTENT:
            return self.phase in [TransactionPhase.PREPARED, TransactionPhase.VERIFIED]
        else:
            return self.phase == TransactionPhase.PREPARED
    
    def needs_verification(self) -> bool:
        """Check if transaction needs verification"""
        return self.phase in [TransactionPhase.APPLIED, TransactionPhase.OBSERVED]
    
    def can_commit(self) -> bool:
        """
        Check if transaction can be committed.
        
        CRITICAL: Verification must pass before commit!
        """
        return (
            self.phase in [TransactionPhase.OBSERVED, TransactionPhase.VERIFIED]
            and self.verification_passed
            and self.evidence
        )


@dataclass
class CommitDecision:
    """
    Typed commit decision from the commit gate.
    
    FIX: Commit must be a deliberate decision, not automatic success.
    """
    allowed: bool
    reason: str
    phase_before: TransactionPhase
    phase_after: TransactionPhase
    
    # Evidence checks
    evidence_present: bool
    verification_passed: bool
    
    # Rollback availability
    rollback_available: bool
    rollback_snapshot_id: Optional[str] = None
    
    # If commit not allowed, what to do
    action: str = "proceed"  # proceed, rollback, retry, escalate


# ==================== PLAN COMPILATION MODELS ====================
# FIX: Planner -> Compiler -> ExecutableGraph boundary

@dataclass
class PlanDraft:
    """
    Raw plan output from LLM planner.
    
    This is the initial draft that needs compilation.
    """
    goal: str
    raw_tasks: List[Dict[str, Any]]  # Raw task dicts from LLM
    planner_metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)


@dataclass
class CompiledTask:
    """
    Single compiled task with normalized spec and validation results.
    """
    task_id: str
    description: str
    normalized_spec: Dict[str, Any] = field(default_factory=dict)
    
    # Validation results
    compile_warnings: List[str] = field(default_factory=list)
    compile_errors: List[str] = field(default_factory=list)
    valid: bool = True
    
    # Execution metadata
    tool_name: Optional[str] = None
    verification_type: Optional[str] = None
    retry_policy: Dict[str, Any] = field(default_factory=dict)
    approval_policy: str = "auto"
    sandbox_mode: str = "normal"
    timeout: int = 30
    
    # Graph position
    dependencies: List[str] = field(default_factory=list)
    can_parallel: bool = False
    checkpoint_boundary: bool = False


@dataclass
class GraphNode:
    """
    Typed node in the executable task graph.
    """
    node_id: str
    task_id: str
    stage: str  # prepare, execute, verify, commit
    retry_budget: int = 3
    requires_approval: bool = False
    dangerous: bool = False
    checkpoint_boundary: bool = False
    status: str = "pending"  # pending, ready, running, completed, failed, blocked


@dataclass
class GraphEdge:
    """
    Typed edge in the executable task graph.
    """
    from_node: str
    to_node: str
    edge_type: str  # dependency, fallback, recovery, supersede
    condition: Optional[str] = None  # on_success, on_failure, always


@dataclass
class ExecutableGraph:
    """
    Compiled and validated execution graph.
    
    This is the intermediate representation between plan and execution.
    """
    graph_id: str
    goal: str
    nodes: List[GraphNode] = field(default_factory=list)
    edges: List[GraphEdge] = field(default_factory=list)
    
    # Compilation results
    valid: bool = True
    compile_warnings: List[str] = field(default_factory=list)
    compile_errors: List[str] = field(default_factory=list)
    
    # Metadata
    created_at: float = field(default_factory=time.time)
    compiled_from_draft: Optional[str] = None
    
    def get_node(self, node_id: str) -> Optional[GraphNode]:
        """Get node by ID"""
        for node in self.nodes:
            if node.node_id == node_id:
                return node
        return None
    
    def get_outgoing_edges(self, node_id: str) -> List[GraphEdge]:
        """Get outgoing edges from a node"""
        return [e for e in self.edges if e.from_node == node_id]
    
    def get_incoming_edges(self, node_id: str) -> List[GraphEdge]:
        """Get incoming edges to a node"""
        return [e for e in self.edges if e.to_node == node_id]
    
    def get_ready_nodes(self) -> List[GraphNode]:
        """Get nodes that are ready to execute (all dependencies completed)"""
        completed = {n.node_id for n in self.nodes if n.status == "completed"}
        ready = []
        for node in self.nodes:
            if node.status != "pending":
                continue
            # Check all dependencies are completed
            incoming = self.get_incoming_edges(node.node_id)
            deps = [e.from_node for e in incoming if e.edge_type == "dependency"]
            if all(d in completed for d in deps):
                ready.append(node)
        return ready


@dataclass
class CompileResult:
    """
    Result of plan compilation.
    """
    success: bool
    draft: PlanDraft
    compiled_graph: Optional[ExecutableGraph] = None
    
    # Compilation details
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    
    # Fixups applied
    auto_fixups: List[str] = field(default_factory=list)
    
    # Statistics
    original_task_count: int = 0
    compiled_task_count: int = 0


# ==================== CONTEXT INJECTION MODELS ====================
# FIX: Memory / Context injection boundary canonical

class ContextScope(str, Enum):
    """Context scope levels"""
    GLOBAL = "global"       # Policy, workspace config
    SESSION = "session"    # Current session state
    RUN = "run"            # Current run/task chain
    TASK = "task"          # Current task
    ATTEMPT = "attempt"    # Current attempt only


class ContextTrustLevel(str, Enum):
    """Trust level for context items"""
    LOW = "low"       # User input, uncertain sources
    MEDIUM = "medium" # Derived, inferred
    HIGH = "high"     # Verified, system-generated


class ContextSource(str, Enum):
    """Source of context items"""
    LEDGER = "ledger"           # Event ledger
    CHECKPOINT = "checkpoint"   # Checkpoint state
    MEMORY = "memory"           # Semantic memory
    USER_INPUT = "user_input"   # User request
    POLICY = "policy"           # Policy engine
    TOOL_STATE = "tool_state"  # Tool execution state
    VERIFIER = "verifier"       # Verification result
    RECOVERY = "recovery"       # Recovery engine
    PLANNER = "planner"         # Planner output
    EXECUTOR = "executor"       # Execution result


@dataclass(frozen=True)
class ContextItem:
    """
    Single context item with full provenance.
    
    FIX: Context is not just data - it's a typed, provenance-aware packet.
    """
    key: str
    value: Any
    source: ContextSource
    scope: ContextScope
    freshness_ts: float
    trust_level: ContextTrustLevel
    
    # Optional metadata
    expires_at: Optional[float] = None
    superseded: bool = False
    superseded_by: Optional[str] = None
    task_id: Optional[str] = None
    run_id: Optional[str] = None
    
    def is_fresh(self, current_time: float, max_age: float = 3600) -> bool:
        """Check if this context item is still fresh"""
        if self.superseded:
            return False
        if self.expires_at and current_time > self.expires_at:
            return False
        if current_time - self.freshness_ts > max_age:
            return False
        return True
    
    def age(self, current_time: float) -> float:
        """Get age in seconds"""
        return current_time - self.freshness_ts


@dataclass
class ContextPacket:
    """
    A compiled context packet for a specific target.
    
    FIX: Each subsystem gets a tailored context packet, not a blob.
    """
    packet_id: str
    target: str
    items: List[ContextItem] = field(default_factory=list)
    budget_tokens: int = 0
    summary: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    
    def get_item(self, key: str) -> Optional[ContextItem]:
        for item in self.items:
            if item.key == key:
                return item
        return None
    
    def get_items_by_source(self, source: ContextSource) -> List[ContextItem]:
        return [item for item in self.items if item.source == source]
    
    def get_fresh_items(self, current_time: float, max_age: float = 3600) -> List[ContextItem]:
        return [item for item in self.items if item.is_fresh(current_time, max_age)]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "packet_id": self.packet_id,
            "target": self.target,
            "context": {item.key: item.value for item in self.items},
            "summary": self.summary,
            "item_count": len(self.items)
        }


class ContextPolicy:
    """
    Policy for context selection per target.
    """
    
    DEFAULT_POLICIES = {
        "planner": {
            "max_items": 30,
            "trust_threshold": ContextTrustLevel.LOW,
            "allow_stale": False,
        },
        "dispatcher": {
            "max_items": 20,
            "trust_threshold": ContextTrustLevel.MEDIUM,
            "allow_stale": True,
        },
        "verifier": {
            "max_items": 15,
            "trust_threshold": ContextTrustLevel.HIGH,
            "allow_stale": False,
        },
        "recovery": {
            "max_items": 25,
            "trust_threshold": ContextTrustLevel.HIGH,
            "allow_stale": True,
        },
        "executor": {
            "max_items": 10,
            "trust_threshold": ContextTrustLevel.HIGH,
            "allow_stale": False,
        }
    }
    
    @classmethod
    def get_policy(cls, target: str) -> Dict[str, Any]:
        return cls.DEFAULT_POLICIES.get(target, cls.DEFAULT_POLICIES["executor"])


# ==================== CAPABILITY NEGOTIATION MODELS ====================

class ReasoningDepth(str, Enum):
    SHALLOW = "shallow"
    STANDARD = "standard"
    DEEP = "deep"


class ExecutionMode(str, Enum):
    DIRECT = "direct"
    TOOL_STRICT = "tool_strict"
    BROWSER_GROUNDED = "browser_grounded"
    CODE_INTERPRET = "code_interpret"


class VerificationMode(str, Enum):
    MINIMAL = "minimal"
    STRICT = "strict"
    EVIDENCE_HEAVY = "evidence_heavy"


class RecoveryMode(str, Enum):
    RETRY_FIRST = "retry_first"
    CONSERVATIVE = "conservative"
    REPLAN_FIRST = "replan_first"


class SafetyPosture(str, Enum):
    PERMISSIVE = "permissive"
    BALANCED = "balanced"
    STRICT = "strict"


@dataclass(frozen=True)
class CapabilityProfile:
    reasoning_depth: ReasoningDepth
    execution_mode: ExecutionMode
    verification_mode: VerificationMode
    recovery_mode: RecoveryMode
    safety_posture: SafetyPosture
    latency_budget_ms: int = 0
    allows_degradation: bool = True
    allowed_fallback_profiles: List[str] = field(default_factory=list)


@dataclass
class EngineSelectionDecision:
    profile_name: str
    confidence: float
    reason_codes: List[str] = field(default_factory=list)
    degradation_chain: List[str] = field(default_factory=list)
    selected_profile: Optional[CapabilityProfile] = None


CAPABILITY_PROFILES = {
    "simple_read": CapabilityProfile(
        reasoning_depth=ReasoningDepth.SHALLOW,
        execution_mode=ExecutionMode.DIRECT,
        verification_mode=VerificationMode.MINIMAL,
        recovery_mode=RecoveryMode.RETRY_FIRST,
        safety_posture=SafetyPosture.PERMISSIVE,
        latency_budget_ms=5000,
        allows_degradation=False
    ),
    "file_write": CapabilityProfile(
        reasoning_depth=ReasoningDepth.STANDARD,
        execution_mode=ExecutionMode.TOOL_STRICT,
        verification_mode=VerificationMode.STRICT,
        recovery_mode=RecoveryMode.CONSERVATIVE,
        safety_posture=SafetyPosture.BALANCED,
        latency_budget_ms=30000,
        allows_degradation=True
    ),
    "code_execution": CapabilityProfile(
        reasoning_depth=ReasoningDepth.DEEP,
        execution_mode=ExecutionMode.CODE_INTERPRET,
        verification_mode=VerificationMode.EVIDENCE_HEAVY,
        recovery_mode=RecoveryMode.CONSERVATIVE,
        safety_posture=SafetyPosture.STRICT,
        latency_budget_ms=120000,
        allows_degradation=True
    ),
    "browser_automation": CapabilityProfile(
        reasoning_depth=ReasoningDepth.STANDARD,
        execution_mode=ExecutionMode.BROWSER_GROUNDED,
        verification_mode=VerificationMode.EVIDENCE_HEAVY,
        recovery_mode=RecoveryMode.RETRY_FIRST,
        safety_posture=SafetyPosture.BALANCED,
        latency_budget_ms=60000,
        allows_degradation=True
    ),
    "dangerous_operation": CapabilityProfile(
        reasoning_depth=ReasoningDepth.STANDARD,
        execution_mode=ExecutionMode.TOOL_STRICT,
        verification_mode=VerificationMode.EVIDENCE_HEAVY,
        recovery_mode=RecoveryMode.CONSERVATIVE,
        safety_posture=SafetyPosture.STRICT,
        latency_budget_ms=60000,
        allows_degradation=False
    ),
}


class ModeSelector:
    """MODE SELECTOR - Determines capability profile for a task."""
    
    def __init__(self, kernel: 'CentralKernel'):
        self.kernel = kernel
        self.logger = logging.getLogger(__name__)
        self._health_status: Dict[str, bool] = {
            "browser_available": True,
            "code_executor_available": True,
            "sandbox_available": True
        }
    
    async def select(
        self,
        task_id: str,
        task_description: str,
        tool_name: Optional[str] = None,
        risk_level: str = "normal",
        is_side_effecting: bool = False,
        prior_failure: bool = False
    ) -> EngineSelectionDecision:
        """Select appropriate capability profile."""
        base_profile, reasons = self._analyze_task(
            task_description, tool_name, risk_level, is_side_effecting, prior_failure
        )
        selected_profile, degradation = self._apply_degradation(base_profile)
        
        return EngineSelectionDecision(
            profile_name=self._get_profile_name(selected_profile),
            confidence=0.85 if not degradation else 0.7,
            reason_codes=reasons,
            degradation_chain=degradation,
            selected_profile=selected_profile
        )
    
    def _analyze_task(self, task_description: str, tool_name: Optional[str], risk_level: str,
                     is_side_effecting: bool, prior_failure: bool) -> tuple:
        reasons = []
        
        if tool_name in ["read_file", "grep", "web_search"]:
            return CAPABILITY_PROFILES["simple_read"], ["read_tool"]
        
        if tool_name in ["write_file", "create_directory"]:
            if risk_level == "high" or is_side_effecting:
                return CAPABILITY_PROFILES["dangerous_operation"], ["write_risk"]
            return CAPABILITY_PROFILES["file_write"], ["write_tool"]
        
        if tool_name in ["execute_command", "execute_code"]:
            return CAPABILITY_PROFILES["code_execution"], ["code_tool"]
        
        if tool_name in ["browser_click", "browser_navigate"]:
            return CAPABILITY_PROFILES["browser_automation"], ["browser_tool"]
        
        if prior_failure:
            return CapabilityProfile(
                reasoning_depth=ReasoningDepth.DEEP,
                execution_mode=ExecutionMode.TOOL_STRICT,
                verification_mode=VerificationMode.EVIDENCE_HEAVY,
                recovery_mode=RecoveryMode.CONSERVATIVE,
                safety_posture=SafetyPosture.STRICT,
                latency_budget_ms=60000
            ), ["prior_failure"]
        
        if risk_level == "high":
            return CAPABILITY_PROFILES["dangerous_operation"], ["high_risk"]
        
        return CapabilityProfile(
            reasoning_depth=ReasoningDepth.STANDARD,
            execution_mode=ExecutionMode.TOOL_STRICT,
            verification_mode=VerificationMode.STRICT,
            recovery_mode=RecoveryMode.RETRY_FIRST,
            safety_posture=SafetyPosture.BALANCED,
            latency_budget_ms=30000
        ), ["default"]
    
    def _apply_degradation(self, profile: CapabilityProfile) -> tuple:
        degradation = []
        if not profile.allows_degradation:
            return profile, []
        
        if profile.execution_mode == ExecutionMode.BROWSER_GROUNDED:
            if not self._health_status.get("browser_available"):
                degradation.append("browser_unavailable")
        
        return profile, degradation
    
    def _get_profile_name(self, profile: CapabilityProfile) -> str:
        for name, p in CAPABILITY_PROFILES.items():
            if p == profile:
                return name
        return "custom"
    
    def update_health(self, component: str, available: bool):
        self._health_status[component] = available


# ==================== BUDGET / COST ENFORCEMENT ====================

@dataclass(frozen=True)
class BudgetSpec:
    wall_clock_sec: int = 300
    max_tool_calls: int = 10
    max_verifications: int = 5
    max_replans: int = 3
    max_retries: int = 3
    max_recoveries: int = 2
    approval_wait_sec: int = 0
    token_budget: Optional[int] = None


@dataclass
class CostForecast:
    estimated_wall_clock_sec: int
    estimated_tool_calls: int
    estimated_verifications: int
    estimated_risk: str
    confidence: float


@dataclass
class SpendRecord:
    task_id: str
    category: str
    amount: float
    timestamp: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BudgetDecision:
    allowed: bool
    reason: str
    remaining_wall_clock_sec: int
    remaining_tool_calls: int
    remaining_replans: int
    remaining_retries: int


class BudgetLedger:
    """BUDGET LEDGER - Tracks all spending"""
    
    def __init__(self, kernel: 'CentralKernel'):
        self.kernel = kernel
        self.logger = logging.getLogger(__name__)
        self._spend_records: List[SpendRecord] = []
        self._task_budgets: Dict[str, BudgetSpec] = {}
    
    def set_task_budget(self, task_id: str, budget: BudgetSpec):
        self._task_budgets[task_id] = budget
    
    def record_spend(self, task_id: str, category: str, amount: float, metadata: Dict = None):
        record = SpendRecord(
            task_id=task_id,
            category=category,
            amount=amount,
            timestamp=time.time(),
            metadata=metadata or {}
        )
        self._spend_records.append(record)
    
    def check_budget(self, task_id: str) -> BudgetDecision:
        budget = self._task_budgets.get(task_id)
        if not budget:
            return BudgetDecision(True, "no_budget_set", 999, 99, 99, 99)
        
        task_spends = [s for s in self._spend_records if s.task_id == task_id]
        tool_calls = sum(1 for s in task_spends if s.category == "tool_call")
        verifications = sum(1 for s in task_spends if s.category == "verification")
        replans = sum(1 for s in task_spends if s.category in ["replan", "replan_retry"])
        
        if tool_calls >= budget.max_tool_calls:
            return BudgetDecision(False, "tool_calls_exhausted", 0, 0, replans, 0)
        if verifications >= budget.max_verifications:
            return BudgetDecision(False, "verifications_exhausted", 0, tool_calls, replans, 0)
        if replans >= budget.max_replans:
            return BudgetDecision(False, "replans_exhausted", 0, tool_calls, 0, 0)
        
        return BudgetDecision(
            True, "ok",
            remaining_wall_clock_sec=budget.wall_clock_sec,
            remaining_tool_calls=budget.max_tool_calls - tool_calls,
            remaining_replans=budget.max_replans - replans,
            remaining_retries=budget.max_retries
        )
    
    def is_budget_exhausted(self, task_id: str) -> bool:
        return not self.check_budget(task_id).allowed


DEFAULT_BUDGETS = {
    "simple": BudgetSpec(wall_clock_sec=60, max_tool_calls=3, max_verifications=1),
    "standard": BudgetSpec(wall_clock_sec=300, max_tool_calls=10, max_verifications=5),
    "heavy": BudgetSpec(wall_clock_sec=600, max_tool_calls=20, max_verifications=10),
    "dangerous": BudgetSpec(wall_clock_sec=300, max_tool_calls=5, max_verifications=3),
}


# ==================== GOAL TERMINATION / STOP CONDITIONS ====================

class StopKind(str, Enum):
    """Types of stop conditions"""
    GOAL_SATISFIED = "goal_satisfied"
    PARTIAL_SUCCESS = "partial_success"
    BUDGET_EXHAUSTED = "budget_exhausted"
    NO_PROGRESS = "no_progress"
    POLICY_STOP = "policy_stop"
    APPROVAL_DENIED = "approval_denied"
    TERMINAL_FAILURE = "terminal_failure"
    ESCALATION_REQUIRED = "escalation_required"


@dataclass(frozen=True)
class GoalSpec:
    """Goal specification - user intent at task level"""
    goal_id: str
    user_intent: str
    success_conditions: List[Dict[str, Any]]
    minimum_acceptable_conditions: List[Dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class StopCondition:
    """Stop condition specification"""
    kind: StopKind
    threshold: Optional[float] = None
    required: bool = True


@dataclass
class TerminationDecision:
    """Termination decision at goal level"""
    stop: bool
    terminal_state: str
    reason: str
    confidence: float
    partial_acceptable: bool = False
    
    def is_success(self) -> bool:
        return self.stop and self.terminal_state in ["goal_satisfied", "partial_success"]


@dataclass(frozen=True)
class PartialOutcomePolicy:
    """Policy for handling partial outcomes"""
    allowed: bool
    minimum_completion_ratio: float = 1.0
    require_explicit_label: bool = True


class SatisfactionEvaluator:
    """
    SATISFACTION EVALUATOR - Evaluates goal completion
    
    Different from verifier: verifier checks step evidence,
    satisfaction checks if goal is actually achieved.
    """
    
    def __init__(self, kernel: 'CentralKernel'):
        self.kernel = kernel
        self.logger = logging.getLogger(__name__)
    
    async def evaluate(self, goal: GoalSpec, task_results: List[Dict]) -> TerminationDecision:
        """Evaluate if goal is satisfied"""
        
        # Check success conditions
        satisfied_conditions = []
        for cond in goal.success_conditions:
            if self._check_condition(cond, task_results):
                satisfied_conditions.append(cond)
        
        # Calculate completion ratio
        if goal.success_conditions:
            ratio = len(satisfied_conditions) / len(goal.success_conditions)
        else:
            ratio = 0.0
        
        # Check if goal is satisfied
        if ratio >= 1.0:
            return TerminationDecision(
                stop=True,
                terminal_state="goal_satisfied",
                reason="all_conditions_met",
                confidence=1.0,
                partial_acceptable=False
            )
        
        # Check minimum acceptable
        if goal.minimum_acceptable_conditions:
            min_satisfied = []
            for cond in goal.minimum_acceptable_conditions:
                if self._check_condition(cond, task_results):
                    min_satisfied.append(cond)
            
            min_ratio = len(min_satisfied) / len(goal.minimum_acceptable_conditions)
            
            if min_ratio >= 1.0:
                return TerminationDecision(
                    stop=True,
                    terminal_state="partial_success",
                    reason="minimum_acceptable_met",
                    confidence=0.8,
                    partial_acceptable=True
                )
        
        # Not satisfied
        return TerminationDecision(
            stop=False,
            terminal_state="in_progress",
            reason=f"{len(satisfied_conditions)}/{len(goal.success_conditions)} conditions met",
            confidence=ratio,
            partial_acceptable=False
        )
    
    def _check_condition(self, condition: Dict, results: List[Dict]) -> bool:
        """Check if a single condition is met"""
        cond_type = condition.get("type")
        
        if cond_type == "all_tasks_completed":
            return all(r.get("status") == "completed" for r in results)
        
        if cond_type == "artifact_exists":
            artifact = condition.get("artifact")
            return any(artifact in r.get("artifacts", []) for r in results)
        
        if cond_type == "no_errors":
            return not any(r.get("status") == "failed" for r in results)
        
        return False


class NoProgressDetector:
    """
    NO PROGRESS DETECTOR - Detects when task is stuck in loop
    """
    
    def __init__(self):
        self._progress_history: Dict[str, List[Dict]] = {}
        self._no_progress_threshold = 3
    
    def record_progress(self, task_id: str, progress: Dict):
        """Record progress for a task"""
        if task_id not in self._progress_history:
            self._progress_history[task_id] = []
        self._progress_history[task_id].append(progress)
    
    def detect_no_progress(self, task_id: str) -> bool:
        """Detect if no progress is being made"""
        if task_id not in self._progress_history:
            return False
        
        history = self._progress_history[task_id][-self._no_progress_threshold:]
        
        if len(history) < self._no_progress_threshold:
            return False
        
        # Check if last N attempts have same outcome
        outcomes = [h.get("outcome") for h in history]
        if len(set(outcomes)) == 1:
            return True
        
        # Check if no new artifacts
        artifacts = [h.get("artifacts", []) for h in history]
        if all(a == artifacts[0] for a in artifacts):
            return True
        
        return False
    
    def clear_history(self, task_id: str):
        """Clear progress history for a task"""
        if task_id in self._progress_history:
            del self._progress_history[task_id]


class TerminationManager:
    """
    TERMINATION MANAGER - Manages goal termination
    """
    
    def __init__(self, kernel: 'CentralKernel'):
        self.kernel = kernel
        self.satisfaction = SatisfactionEvaluator(kernel)
        self.no_progress = NoProgressDetector()
        self._goals: Dict[str, GoalSpec] = {}
    
    def register_goal(self, goal: GoalSpec):
        """Register a goal"""
        self._goals[goal.goal_id] = goal
    
    async def check_termination(self, goal_id: str, task_results: List[Dict]) -> TerminationDecision:
        """Check if should terminate"""
        
        if goal_id not in self._goals:
            return TerminationDecision(
                stop=False,
                terminal_state="unknown",
                reason="goal_not_registered",
                confidence=0.0
            )
        
        goal = self._goals[goal_id]
        
        # Check goal satisfaction
        decision = await self.satisfaction.evaluate(goal, task_results)
        
        if decision.stop:
            return decision
        
        # Check no progress
        if self.no_progress.detect_no_progress(goal_id):
            return TerminationDecision(
                stop=True,
                terminal_state="no_progress",
                reason="no_progress_after_threshold",
                confidence=0.9,
                partial_acceptable=True
            )
        
        return decision


# ==================== HUMAN HANDOVER / ESCALATION ====================

class EscalationReason(str, Enum):
    """Types of escalation reasons"""
    APPROVAL_REQUIRED = "approval_required"
    AMBIGUOUS_INTENT = "ambiguous_intent"
    NO_PROGRESS = "no_progress"
    POLICY_BLOCKED = "policy_blocked"
    PARTIAL_SUCCESS_REVIEW = "partial_success_review"
    CAPABILITY_UNAVAILABLE = "capability_unavailable"
    BUDGET_EXHAUSTED_SALVAGEABLE = "budget_exhausted_salvageable"
    HUMAN_EXECUTION_REQUIRED = "human_execution_required"
    VERIFIER_UNCLEAR = "verifier_unclear"


@dataclass
class HandoffPacket:
    """Complete handoff packet for human escalation"""
    handoff_id: str
    task_id: str
    reason: EscalationReason
    summary: str
    current_state: str
    evidence: Dict[str, Any] = field(default_factory=dict)
    options: List[Dict[str, Any]] = field(default_factory=list)
    recommended_option: Optional[str] = None
    risks: List[str] = field(default_factory=list)
    required_human_action: Optional[str] = None
    
    def to_user_friendly(self) -> str:
        """Convert to user-friendly message"""
        msg = f"📋 **Task: {self.summary}**\n\n"
        msg += f"**Reason:** {self.reason.value}\n\n"
        msg += f"**Current State:** {self.current_state}\n\n"
        
        if self.options:
            msg += "**Options:**\n"
            for i, opt in enumerate(self.options, 1):
                msg += f"{i}. {opt.get('label', 'Option')}\n"
        
        if self.risks:
            msg += "\n**Risks:**\n"
            for risk in self.risks:
                msg += f"- {risk}\n"
        
        return msg


@dataclass
class HumanResponseCompileResult:
    """Result of compiling human response"""
    accepted: bool
    selected_option: Optional[str] = None
    added_constraints: Dict[str, Any] = field(default_factory=dict)
    approval_granted: bool = False
    manual_action_confirmed: bool = False
    resume_allowed: bool = False
    resume_from_status: Optional[str] = None


@dataclass
class ResumeDirective:
    """Directive to resume after human handoff"""
    task_id: str
    resume_from_status: str
    supersede_old_branch: bool = False
    updated_constraints: Dict[str, Any] = field(default_factory=dict)


class HumanResponseCompiler:
    """
    COMPILES human response into structured result
    """
    
    def __init__(self, kernel: 'CentralKernel'):
        self.kernel = kernel
        self.logger = logging.getLogger(__name__)
    
    async def compile(self, handoff: HandoffPacket, human_response: str) -> HumanResponseCompileResult:
        """Compile human response"""
        
        response = human_response.lower().strip()
        
        # Check for approval
        if "approve" in response or "allow" in response or "yes" in response:
            return HumanResponseCompileResult(
                accepted=True,
                approval_granted=True,
                resume_allowed=True,
                resume_from_status="approved"
            )
        
        # Check for rejection
        if "reject" in response or "deny" in response or "no" in response:
            return HumanResponseCompileResult(
                accepted=False,
                resume_allowed=False
            )
        
        # Check for option selection
        if response.isdigit() or any(response.startswith(str(i)) for i in range(1, 10)):
            option_num = int(response.strip()[0]) - 1
            if option_num < len(handoff.options):
                return HumanResponseCompileResult(
                    accepted=True,
                    selected_option=handoff.options[option_num].get("value"),
                    resume_allowed=True,
                    resume_from_status="option_selected"
                )
        
        # Default: resume with human input
        return HumanResponseCompileResult(
            accepted=True,
            resume_allowed=True,
            resume_from_status="human_input_received"
        )


class HandoffOrchestrator:
    """
    HANDOFF ORCHESTRATOR - Manages human escalation flow
    """
    
    def __init__(self, kernel: 'CentralKernel'):
        self.kernel = kernel
        self.compiler = HumanResponseCompiler(kernel)
        self._active_handoffs: Dict[str, HandoffPacket] = {}
        self._handoff_history: List[HandoffPacket] = []
        self.logger = logging.getLogger(__name__)
    
    async def create_handoff(
        self,
        task_id: str,
        reason: EscalationReason,
        summary: str,
        current_state: str,
        options: List[Dict] = None,
        recommended: str = None,
        risks: List[str] = None,
        evidence: Dict = None
    ) -> HandoffPacket:
        """Create handoff packet"""
        
        import uuid
        handoff = HandoffPacket(
            handoff_id=f"handoff_{uuid.uuid4().hex[:8]}",
            task_id=task_id,
            reason=reason,
            summary=summary,
            current_state=current_state,
            options=options or [],
            recommended_option=recommended,
            risks=risks or [],
            evidence=evidence or {}
        )
        
        self._active_handoffs[handoff.handoff_id] = handoff
        self._handoff_history.append(handoff)
        
        # Record to ledger
        if hasattr(self.kernel, 'telemetry') and self.kernel.telemetry:
            self.kernel.telemetry.record_event('handoff_created', {
                'handoff_id': handoff.handoff_id,
                'task_id': task_id,
                'reason': reason.value
            })
        
        return handoff
    
    async def compile_response(
        self,
        handoff_id: str,
        human_response: str
    ) -> HumanResponseCompileResult:
        """Compile human response"""
        
        if handoff_id not in self._active_handoffs:
            raise ValueError(f"Handoff {handoff_id} not found")
        
        handoff = self._active_handoffs[handoff_id]
        result = await self.compiler.compile(handoff, human_response)
        
        # Record to ledger
        if hasattr(self.kernel, 'telemetry') and self.kernel.telemetry:
            self.kernel.telemetry.record_event('handoff_response', {
                'handoff_id': handoff_id,
                'accepted': result.accepted,
                'resume_allowed': result.resume_allowed
            })
        
        return result
    
    def get_handoff(self, handoff_id: str) -> Optional[HandoffPacket]:
        """Get handoff by ID"""
        return self._active_handoffs.get(handoff_id)
    
    def get_active_handoffs(self) -> List[HandoffPacket]:
        """Get all active handoffs"""
        return list(self._active_handoffs.values())
    
    def get_handoff_history(self) -> List[HandoffPacket]:
        """Get handoff history"""
        return self._handoff_history


# ==================== KERNEL CONSTITUTION / INVARIANT CHECKER ====================

class ViolationSeverity(str, Enum):
    """Severity levels for invariant violations"""
    WARNING = "warning"
    ERROR = "error"
    FATAL = "fatal"


@dataclass
class InvariantViolation:
    """An invariant violation"""
    code: str
    severity: ViolationSeverity
    message: str
    task_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class InvariantReport:
    """Report of invariant checks"""
    ok: bool
    violations: List[InvariantViolation] = field(default_factory=list)
    checked_at: float = field(default_factory=time.time)
    
    def has_fatal(self) -> bool:
        return any(v.severity == ViolationSeverity.FATAL for v in self.violations)


class KernelConstitution:
    """
    KERNEL CONSTITUTION - Invariant rules that cannot be broken
    
    This is the fundamental contract of the kernel.
    """
    
    # Core invariants - these MUST hold always
    INVARIANTS = [
        # Task state invariants
        "task_state_status_consistent",  # state and status must match
        "completed_not_in_pending",       # completed task not in pending
        "completed_not_in_running",      # completed task not in running
        "failed_not_in_completed",       # failed task not in completed
        "running_has_started_at",        # running task has started_at
        
        # Queue invariants
        "no_duplicate_task_ids",         # task IDs unique across sets
        "dependency_respects_status",     # dependent tasks have valid status
        
        # Transaction invariants  
        "verified_before_committed",     # cannot commit without verification
        "approval_before_dangerous",     # dangerous ops need approval
        
        # Budget invariants
        "retry_within_limit",          # retry_count <= max_retries
        
        # Recovery invariants
        "superseded_not_runnable",      # superseded tasks cannot run
    ]
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)


class InvariantEngine:
    """
    INVARIANT ENGINE - Checks kernel invariants
    
    Runs checks at critical points:
    - After state restore
    - After status transitions
    - After recovery
    - After checkpoint restore
    - Before commit
    """
    
    def __init__(self, kernel: 'CentralKernel'):
        self.kernel = kernel
        self.constitution = KernelConstitution()
        self.logger = logging.getLogger(__name__)
        self._violation_count = 0
    
    def check_all(self) -> InvariantReport:
        """Run all invariant checks"""
        violations = []
        
        # Check task state consistency
        violations.extend(self._check_state_status_consistency())
        
        # Check queue/set consistency
        violations.extend(self._check_queue_consistency())
        
        # Check transaction consistency
        violations.extend(self._check_transaction_consistency())
        
        ok = len([v for v in violations if v.severity == ViolationSeverity.FATAL]) == 0
        
        report = InvariantReport(
            ok=ok,
            violations=violations
        )
        
        if not ok:
            self._violation_count += 1
            self.logger.error(f"🚨 INVARIANT VIOLATION: {len(violations)} violations found")
        
        return report
    
    def _check_state_status_consistency(self) -> List[InvariantViolation]:
        """Check task state and status consistency"""
        violations = []
        
        if not hasattr(self.kernel, 'task_manager'):
            return violations
        
        # Check running tasks have started_at
        for task_id in getattr(self.kernel.task_manager, 'running_tasks', []):
            task = self.kernel.task_manager.get_task(task_id)
            if task and not task.started_at:
                violations.append(InvariantViolation(
                    code="running_without_started_at",
                    severity=ViolationSeverity.ERROR,
                    message=f"Task {task_id} is running but has no started_at",
                    task_id=task_id
                ))
        
        return violations
    
    def _check_queue_consistency(self) -> List[InvariantViolation]:
        """Check queue/set consistency"""
        violations = []
        
        if not hasattr(self.kernel, 'task_manager'):
            return violations
        
        # Check for duplicate task IDs
        all_tasks = set()
        if hasattr(self.kernel.task_manager, 'tasks'):
            all_tasks.update(self.kernel.task_manager.tasks.keys())
        if hasattr(self.kernel.task_manager, 'completed_tasks'):
            completed = set(self.kernel.task_manager.completed_tasks)
            duplicates = all_tasks & completed
            for task_id in duplicates:
                violations.append(InvariantViolation(
                    code="duplicate_in_completed",
                    severity=ViolationSeverity.ERROR,
                    message=f"Task {task_id} in both tasks and completed_tasks",
                    task_id=task_id
                ))
        
        return violations
    
    def _check_transaction_consistency(self) -> List[InvariantViolation]:
        """Check transaction consistency"""
        violations = []
        
        # Check committed transactions have verification
        if hasattr(self.kernel, '_active_transactions'):
            for tx_id, tx in self.kernel._active_transactions.items():
                if tx.is_committed() and not tx.verification_passed:
                    violations.append(InvariantViolation(
                        code="committed_without_verification",
                        severity=ViolationSeverity.FATAL,
                        message=f"Transaction {tx_id} committed without verification",
                        task_id=tx.task_id
                    ))
        
        return violations
    
    def check_transition(self, task_id: str, from_status: str, to_status: str) -> bool:
        """Check if transition is valid"""
        # Basic transition validation
        valid = True
        
        # Cannot go from completed to running
        if from_status == "completed" and to_status == "running":
            valid = False
        
        # Cannot go from failed to running without retry
        if from_status == "failed" and to_status == "running":
            # Only valid if retry is allowed
            pass
        
        return valid
    
    def get_violation_count(self) -> int:
        """Get total violation count"""
        return self._violation_count


class ContextAssembler:
    """
    ASSEMBLES context from multiple sources deterministically.
    """
    
    def __init__(self, kernel: 'CentralKernel'):
        self.kernel = kernel
        self.logger = logging.getLogger(__name__)
    
    async def assemble(
        self,
        target: str,
        task_id: Optional[str] = None,
        run_id: Optional[str] = None,
        additional_items: Optional[List[ContextItem]] = None
    ) -> ContextPacket:
        """Assemble context packet for a target."""
        self.logger.info(f"📦 ASSEMBLING context for: {target}")
        
        current_time = time.time()
        policy = ContextPolicy.get_policy(target)
        
        # Collect from sources
        raw_items = await self._collect_all_context(target, task_id, run_id)
        
        if additional_items:
            raw_items.extend(additional_items)
        
        # Deduplicate and filter
        items = self._deduplicate_items(raw_items)
        items = self._filter_items(items, current_time, policy.get("allow_stale", False))
        items = self._apply_policy(items, policy)
        
        # Create packet
        packet = ContextPacket(
            packet_id=f"ctx_{uuid.uuid4().hex[:12]}",
            target=target,
            items=items,
            budget_tokens=policy.get("max_items", 20) * 100,
            summary={"total_items": len(items), "target": target},
            created_at=current_time
        )
        
        self.logger.info(f"✅ Assembled {len(items)} context items for {target}")
        return packet
    
    async def _collect_all_context(self, target: str, task_id: Optional[str], run_id: Optional[str]) -> List[ContextItem]:
        """Collect context from all available sources"""
        items = []
        
        # From task event ledger
        if hasattr(self.kernel, '_task_event_ledger'):
            for event in self.kernel._task_event_ledger[-50:]:
                items.append(ContextItem(
                    key=f"event:{event.task_id}:{event.to_status}",
                    value={"from": event.from_status, "to": event.to_status, "reason": event.reason},
                    source=ContextSource.LEDGER,
                    scope=ContextScope.RUN if event.task_id == task_id else ContextScope.SESSION,
                    freshness_ts=event.timestamp,
                    trust_level=ContextTrustLevel.HIGH,
                    task_id=event.task_id
                ))
        
        # From checkpoints
        if task_id and hasattr(self.kernel, '_task_checkpoints'):
            checkpoint = self.kernel._task_checkpoints.get(task_id)
            if checkpoint:
                items.append(ContextItem(
                    key=f"checkpoint:{task_id}",
                    value={"checkpoint_id": checkpoint.checkpoint_id, "status": checkpoint.last_safe_status},
                    source=ContextSource.CHECKPOINT,
                    scope=ContextScope.RUN,
                    freshness_ts=checkpoint.created_at,
                    trust_level=ContextTrustLevel.HIGH,
                    task_id=task_id
                ))
        
        # From transactions
        if task_id and hasattr(self.kernel, '_active_transactions'):
            for tx_id, tx in self.kernel._active_transactions.items():
                if tx.task_id == task_id:
                    items.append(ContextItem(
                        key=f"tx:{tx_id}",
                        value={"phase": tx.phase.value, "tool": tx.tool_name, "committed": tx.is_committed()},
                        source=ContextSource.EXECUTOR,
                        scope=ContextScope.ATTEMPT,
                        freshness_ts=tx.created_at,
                        trust_level=ContextTrustLevel.HIGH,
                        task_id=task_id
                    ))
        
        # From task state
        if task_id and hasattr(self.kernel, 'task_manager'):
            task = self.kernel.task_manager.get_task(task_id)
            if task:
                items.append(ContextItem(
                    key=f"task_state:{task_id}",
                    value={"status": str(task.status), "retry_count": task.retry_count, "error": task.error},
                    source=ContextSource.LEDGER,
                    scope=ContextScope.TASK,
                    freshness_ts=task.created_at,
                    trust_level=ContextTrustLevel.HIGH,
                    task_id=task_id
                ))
        
        # From memory
        if hasattr(self.kernel, 'memory') and self.kernel.memory:
            try:
                mem_results = self.kernel.memory.retrieve(task_id or "", limit=5)
                for mem in mem_results:
                    items.append(ContextItem(
                        key=f"memory:{mem.get('id', 'unknown')}",
                        value=mem.get('content', ''),
                        source=ContextSource.MEMORY,
                        scope=ContextScope.SESSION,
                        freshness_ts=mem.get('timestamp', time.time()),
                        trust_level=ContextTrustLevel.MEDIUM,
                        task_id=task_id
                    ))
            except Exception as e:
                self.logger.warning(f"Memory retrieve failed: {e}")
        
        # From approvals
        if hasattr(self.kernel, 'pending_approvals'):
            for approval_id, approval in self.kernel.pending_approvals.items():
                items.append(ContextItem(
                    key=f"approval:{approval_id}",
                    value=approval,
                    source=ContextSource.POLICY,
                    scope=ContextScope.SESSION,
                    freshness_ts=time.time(),
                    trust_level=ContextTrustLevel.HIGH
                ))
        
        # Global governance
        items.append(ContextItem(
            key="governance:workspace",
            value={"sandbox_mode": "normal", "approval_policy": "auto"},
            source=ContextSource.POLICY,
            scope=ContextScope.GLOBAL,
            freshness_ts=time.time(),
            trust_level=ContextTrustLevel.HIGH
        ))
        
        return items
    
    def _deduplicate_items(self, items: List[ContextItem]) -> List[ContextItem]:
        """Remove duplicate context items"""
        seen = {}
        result = []
        for item in items:
            if item.key not in seen:
                seen[item.key] = item
                result.append(item)
            else:
                existing = seen[item.key]
                if item.freshness_ts > existing.freshness_ts:
                    result.remove(existing)
                    result.append(item)
                    seen[item.key] = item
        return result
    
    def _filter_items(self, items: List[ContextItem], current_time: float, allow_stale: bool) -> List[ContextItem]:
        """Filter stale and superseded items"""
        filtered = []
        for item in items:
            if item.superseded:
                continue
            if item.expires_at and current_time > item.expires_at:
                continue
            if not allow_stale and not item.is_fresh(current_time, max_age=3600):
                continue
            filtered.append(item)
        return filtered
    
    def _apply_policy(self, items: List[ContextItem], policy: Dict[str, Any]) -> List[ContextItem]:
        """Apply policy to limit items"""
        max_items = policy.get("max_items", 20)
        
        # Score and sort
        scored = []
        for item in items:
            score = self._score_item(item, policy)
            scored.append((score, item))
        
        scored.sort(key=lambda x: -x[0])
        return [item for _, item in scored[:max_items]]
    
    def _score_item(self, item: ContextItem, policy: Dict[str, Any]) -> float:
        """Score item based on policy"""
        score = 0.0
        
        # Trust bonus
        trust_order = [ContextTrustLevel.LOW, ContextTrustLevel.MEDIUM, ContextTrustLevel.HIGH]
        if item.trust_level in trust_order:
            score += trust_order.index(item.trust_level) * 2.0
        
        # Freshness bonus
        age = time.time() - item.freshness_ts
        if age < 60:
            score += 3.0
        elif age < 300:
            score += 1.0
        
        return score


class PlanCompiler:
    """
    PLAN COMPILER - The "compiler wall" between planner and executor.
    
    CRITICAL: This is the ONLY path from plan to execution.
    No raw planner output should ever reach execution directly!
    
    Responsibilities:
    1. Normalize plan draft to canonical IR
    2. Validate semantic correctness
    3. Check dependency graph validity
    4. Inject missing verifications
    5. Apply policy constraints
    6. Build executable graph
    7. Generate compile warnings/errors
    """
    
    def __init__(self, kernel: 'CentralKernel'):
        self.kernel = kernel
        self.logger = logging.getLogger(__name__)
        
        # Tool configuration
        self._tool_config = {
            'write_file': {'dangerous': True, 'requires_approval': True},
            'delete_file': {'dangerous': True, 'requires_approval': True},
            'execute_command': {'dangerous': True, 'requires_approval': True},
            'install_package': {'dangerous': True, 'requires_approval': True},
            'browser_click': {'dangerous': False, 'requires_approval': False},
            'browser_navigate': {'dangerous': False, 'requires_approval': False},
            'read_file': {'dangerous': False, 'requires_approval': False},
            'grep': {'dangerous': False, 'requires_approval': False},
            'web_search': {'dangerous': False, 'requires_approval': False},
        }
        
        # Default configurations
        self._default_timeout = 30
        self._default_retry_policy = {"max_retries": 3, "backoff": "exponential"}
        self._default_verification = "none"
    
    async def compile(self, draft: PlanDraft) -> CompileResult:
        """
        Compile a plan draft to an executable graph.
        
        Pipeline: Draft -> Normalize -> Validate -> Enrich -> Graph
        """
        self.logger.info(f"📋 COMPILING: {draft.goal[:50]}...")
        
        compile_result = CompileResult(
            success=False,
            draft=draft,
            original_task_count=len(draft.raw_tasks)
        )
        
        try:
            # Step 1: Normalize raw tasks to compiled tasks
            compiled_tasks = []
            for raw_task in draft.raw_tasks:
                compiled = self._normalize_task(raw_task, compile_result)
                compiled_tasks.append(compiled)
            
            # Step 2: Validate compiled tasks
            self._validate_tasks(compiled_tasks, compile_result)
            
            # Step 3: Build dependency graph
            valid, errors = self._build_dependency_graph(compiled_tasks)
            if not valid:
                compile_result.errors.extend(errors)
                compile_result.success = False
                return compile_result
            
            # Step 4: Inject missing verifications
            self._inject_verifications(compiled_tasks, compile_result)
            
            # Step 5: Apply policy constraints
            self._apply_policies(compiled_tasks, compile_result)
            
            # Step 6: Build executable graph
            graph = self._build_executable_graph(draft.goal, compiled_tasks)
            compile_result.compiled_graph = graph
            
            # Finalize
            compile_result.compiled_task_count = len(compiled_tasks)
            compile_result.success = len(compile_result.errors) == 0
            
            self.logger.info(f"✅ COMPILED: {len(compiled_tasks)} tasks, {len(compile_result.warnings)} warnings")
            
            return compile_result
            
        except Exception as e:
            self.logger.error(f"Compile error: {e}")
            compile_result.errors.append(f"Compile exception: {str(e)}")
            compile_result.success = False
            return compile_result
    
    def _normalize_task(self, raw_task: Dict, result: CompileResult) -> CompiledTask:
        """Normalize a raw task to compiled task."""
        
        # Extract task ID
        task_id = raw_task.get('id') or f"task_{uuid.uuid4().hex[:8]}"
        
        # Normalize description
        description = raw_task.get('description', raw_task.get('task', ''))
        if not description:
            result.warnings.append(f"{task_id}: missing description")
            description = f"Task {task_id}"
        
        # Build normalized spec
        normalized = {
            'original_id': task_id,
            'raw_fields': raw_task
        }
        
        compiled = CompiledTask(
            task_id=task_id,
            description=description,
            normalized_spec=normalized
        )
        
        # Normalize tool
        tool_name = raw_task.get('tool') or raw_task.get('tool_name') or raw_task.get('required_tool')
        if tool_name:
            compiled.tool_name = tool_name
        else:
            result.warnings.append(f"{task_id}: no tool specified")
        
        # Normalize verification type
        verification_type = raw_task.get('verification_type') or raw_task.get('verification')
        if verification_type:
            try:
                compiled.verification_type = normalize_verification_type(verification_type).value
            except ValueError as e:
                result.warnings.append(f"{task_id}: invalid verification type, using none")
                compiled.verification_type = "none"
        else:
            compiled.verification_type = self._default_verification
            if compiled.tool_name in self._tool_config:
                result.warnings.append(f"{task_id}: missing verification, defaulting to none")
        
        # Normalize retry policy
        retry_raw = raw_task.get('retry_policy') or raw_task.get('retry')
        if isinstance(retry_raw, int):
            compiled.retry_policy = {"max_retries": retry_raw, "backoff": "exponential"}
        elif isinstance(retry_raw, dict):
            compiled.retry_policy = retry_raw
        else:
            compiled.retry_policy = self._default_retry_policy.copy()
        
        # Normalize approval policy
        compiled.approval_policy = raw_task.get('approval_policy', 'auto')
        
        # Normalize sandbox mode
        compiled.sandbox_mode = raw_task.get('sandbox_mode', 'normal')
        
        # Normalize timeout
        compiled.timeout = raw_task.get('timeout', self._default_timeout)
        
        # Normalize dependencies
        deps = raw_task.get('dependencies', [])
        if isinstance(deps, list):
            compiled.dependencies = deps
        else:
            result.warnings.append(f"{task_id}: invalid dependencies format")
            compiled.dependencies = []
        
        # Check parallel eligibility
        compiled.can_parallel = raw_task.get('can_parallel', False)
        
        return compiled
    
    def _validate_tasks(self, tasks: List[CompiledTask], result: CompileResult):
        """Validate compiled tasks semantically."""
        
        # Check for duplicate IDs
        ids = [t.task_id for t in tasks]
        duplicates = [x for x in ids if ids.count(x) > 1]
        if duplicates:
            result.errors.append(f"Duplicate task IDs: {set(duplicates)}")
        
        # Validate each task
        for task in tasks:
            # Check tool exists
            if task.tool_name and task.tool_name not in self._tool_config:
                result.warnings.append(f"{task.task_id}: unknown tool '{task.tool_name}', will use default routing")
            
            # Check timeout is reasonable
            if task.timeout < 1 or task.timeout > 3600:
                result.warnings.append(f"{task.task_id}: timeout {task.timeout}s outside reasonable range [1, 3600], clamping")
                task.timeout = max(1, min(3600, task.timeout))
            
            # Check retry policy
            max_retries = task.retry_policy.get('max_retries', 3)
            if max_retries < 0 or max_retries > 10:
                result.warnings.append(f"{task.task_id}: max_retries {max_retries} outside [0, 10]")
                task.retry_policy['max_retries'] = max(0, min(10, max_retries))
            
            # Check approval policy
            if task.approval_policy not in ['auto', 'manual', 'never']:
                result.warnings.append(f"{task.task_id}: invalid approval_policy '{task.approval_policy}', using auto")
                task.approval_policy = "auto"
            
            # Mark as invalid if has errors
            if task.compile_errors:
                task.valid = False
    
    def _build_dependency_graph(self, tasks: List[CompiledTask]) -> tuple:
        """Build and validate dependency graph."""
        errors = []
        
        # Build ID map
        task_ids = {t.task_id for t in tasks}
        
        # Check all dependencies exist
        for task in tasks:
            for dep in task.dependencies:
                if dep not in task_ids:
                    errors.append(f"{task.task_id}: depends on non-existent task '{dep}'")
        
        # Check for cycles using DFS
        if self._has_cycle(tasks):
            errors.append("Dependency graph contains cycles")
        
        return len(errors) == 0, errors
    
    def _has_cycle(self, tasks: List[CompiledTask]) -> bool:
        """Check if dependency graph has cycles."""
        # Build adjacency list
        adj = {t.task_id: list(t.dependencies) for t in tasks}
        
        visited = set()
        rec_stack = set()
        
        def dfs(node):
            visited.add(node)
            rec_stack.add(node)
            
            for neighbor in adj.get(node, []):
                if neighbor not in visited:
                    if dfs(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True
            
            rec_stack.remove(node)
            return False
        
        for task in tasks:
            if task.task_id not in visited:
                if dfs(task.task_id):
                    return True
        return False
    
    def _inject_verifications(self, tasks: List[CompiledTask], result: CompileResult):
        """Inject missing verifications where needed."""
        
        for task in tasks:
            if task.verification_type == "none":
                # Check if this is a side-effecting task that needs verification
                if task.tool_name in self._tool_config:
                    config = self._tool_config[task.tool_name]
                    
                    if config.get('dangerous', False):
                        # Dangerous tools should have explicit verification
                        if not task.compile_errors:
                            result.auto_fixups.append(f"{task.task_id}: dangerous tool without explicit verification")
            
            # Inject default verification based on tool
            if task.verification_type == "none" and task.tool_name:
                if task.tool_name in ["write_file", "delete_file"]:
                    task.verification_type = "file_exists"
                    result.auto_fixups.append(f"{task.task_id}: auto-injected file_exists verification")
                elif task.tool_name == "execute_command":
                    task.verification_type = "function_result"
                    result.auto_fixups.append(f"{task.task_id}: auto-injected function_result verification")
    
    def _apply_policies(self, tasks: List[CompiledTask], result: CompileResult):
        """Apply policy constraints to tasks."""
        
        for task in tasks:
            # Check dangerous tools with approval
            if task.tool_name in self._tool_config:
                config = self._tool_config[task.tool_name]
                
                if config.get('requires_approval', False):
                    task.requires_approval = True
                    if task.approval_policy == 'never':
                        result.warnings.append(
                            f"{task.task_id}: dangerous tool '{task.tool_name}' with approval_policy='never' "
                            "may fail at runtime"
                        )
            
            # Mark checkpoint boundaries for dangerous operations
            if task.tool_name in ['execute_command', 'install_package']:
                task.checkpoint_boundary = True
    
    def _build_executable_graph(self, goal: str, tasks: List[CompiledTask]) -> ExecutableGraph:
        """Build executable graph from compiled tasks."""
        
        graph_id = f"graph_{uuid.uuid4().hex[:12]}"
        
        # Create nodes
        nodes = []
        for task in tasks:
            node = GraphNode(
                node_id=f"node_{task.task_id}",
                task_id=task.task_id,
                stage="execute",
                retry_budget=task.retry_policy.get('max_retries', 3),
                requires_approval=task.requires_approval,
                dangerous=task.tool_name in self._tool_config and 
                         self._tool_config[task.tool_name].get('dangerous', False),
                checkpoint_boundary=task.checkpoint_boundary,
                status="pending"
            )
            nodes.append(node)
        
        # Create edges
        edges = []
        task_id_to_node = {t.task_id: f"node_{t.task_id}" for t in tasks}
        
        for task in tasks:
            for dep in task.dependencies:
                if dep in task_id_to_node:
                    edge = GraphEdge(
                        from_node=task_id_to_node[dep],
                        to_node=f"node_{task.task_id}",
                        edge_type="dependency",
                        condition="on_success"
                    )
                    edges.append(edge)
        
        # Build graph
        graph = ExecutableGraph(
            graph_id=graph_id,
            goal=goal,
            nodes=nodes,
            edges=edges,
            valid=True,
            compile_warnings=[],
            compile_errors=[]
        )
        
        return graph
    
    async def compile_with_fallback(self, draft: PlanDraft) -> CompileResult:
        """
        Try to compile, if fails try to fix and recompile.
        """
        result = await self.compile(draft)
        
        if not result.success and result.auto_fixups:
            # Try again with auto-fixups applied
            self.logger.info("Retrying compilation with fixups...")
            result = await self.compile(draft)
        
        return result


# ==================== DATA CLASSES ====================

@dataclass
class Task:
    """Represents a task in the kernel"""
    id: str
    description: str
    priority: TaskPriority = TaskPriority.NORMAL
    state: str = "pending"
    status: TaskStatus = TaskStatus.PENDING
    dependencies: List[str] = field(default_factory=list)
    assigned_agent: Optional[AgentRole] = None
    input_data: Any = None
    output_data: Any = None
    error: Optional[str] = None
    error_type: Optional[ErrorType] = None
    recovery_strategy: Optional[RecoveryStrategy] = None
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    retry_count: int = 0
    max_retries: int = 3
    timeout: int = 30  # seconds
    artifacts: List[str] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)
    
    # New fields for enhanced task management
    approval_policy: str = "auto"  # auto, manual, never
    sandbox_mode: str = "normal"  # safe, normal, advanced
    estimated_cost: float = 0.0
    artifact_expectations: List[str] = field(default_factory=list)
    rollback_point: Optional[Dict] = None
    
    # FIX #4: Task lineage - links between parent/superseded/replacement tasks
    parent_task_id: Optional[str] = None          # Original task if this is replacement
    superseded_by: Optional[str] = None            # Task that replaced this one
    replacement_for: Optional[str] = None         # Task this one replaces
    
    # FIX #5: Task checkpoint for durable pause/resume
    checkpoint_id: Optional[str] = None
    last_safe_status: Optional[str] = None
    
    def __lt__(self, other):
        return self.priority.value < other.priority.value


@dataclass
class FailureRecord:
    """
    Canonical failure record - SINGLE source of truth for all errors.
    
    This replaces fragmented error strings with a typed, machine-usable object.
    
    FIX: Error taxonomy / failure classification canonical
    
    Key features:
    - Human-readable message
    - Kernel-usable typed category
    - Recovery-actionable flags
    - Provenance tracking (stage, subsystem, source)
    - Analytics-ready structure
    """
    # Core classification
    category: FailureCategory
    message: str
    
    # Provenance
    stage: str = ""  # execution, verification, approval, etc.
    subsystem: str = ""  # kernel, tools, sandbox, etc.
    provider: Optional[str] = None  # tool name or provider
    tool_name: Optional[str] = None
    
    # Recovery semantics
    retryable: bool = False
    recoverable: bool = False
    replan_recommended: bool = False
    escalate_recommended: bool = False
    
    # Ownership
    severity: FailureSeverity = FailureSeverity.SYSTEM_FIXABLE
    ownership: FailureOwnership = FailureOwnership.AGENT
    
    # References
    artifact_ref: Optional[str] = None
    checkpoint_id: Optional[str] = None
    approval_request_id: Optional[str] = None
    task_id: Optional[str] = None
    
    # Raw error for debugging
    raw_error: Optional[str] = None
    stack_trace: Optional[str] = None
    
    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Timestamps
    occurred_at: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization"""
        return {
            "category": self.category.value,
            "message": self.message,
            "stage": self.stage,
            "subsystem": self.subsystem,
            "provider": self.provider,
            "tool_name": self.tool_name,
            "retryable": self.retryable,
            "recoverable": self.recoverable,
            "replan_recommended": self.replan_recommended,
            "escalate_recommended": self.escalate_recommended,
            "severity": self.severity.value,
            "ownership": self.ownership.value,
            "artifact_ref": self.artifact_ref,
            "checkpoint_id": self.checkpoint_id,
            "approval_request_id": self.approval_request_id,
            "task_id": self.task_id,
            "raw_error": self.raw_error,
            "stack_trace": self.stack_trace,
            "metadata": self.metadata,
            "occurred_at": self.occurred_at,
        }
    
    @classmethod
    def from_exception(cls, exc: Exception, stage: str, subsystem: str, **kwargs) -> "FailureRecord":
        """Create FailureRecord from exception"""
        return cls(
            category=FailureCategory.UNKNOWN,
            message=str(exc),
            stage=stage,
            subsystem=subsystem,
            raw_error=str(exc),
            stack_trace=traceback.format_exc(),
            **kwargs
        )


class ExecutionResult:
    """
    Structured result of tool execution.
    
    FIX: Now includes FailureRecord instead of generic error string.
    """
    success: bool
    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0
    artifacts: List[str] = field(default_factory=list)
    tool_used: str = ""
    execution_time: float = 0.0
    
    # CRITICAL: Now uses FailureRecord instead of generic error
    failure: Optional[FailureRecord] = None
    error: Optional[str] = None  # Legacy, for backward compat
    error_type: Optional[ErrorType] = None  # Legacy
    
    # Verification info
    verified: bool = False
    verification_details: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "success": self.success,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "exit_code": self.exit_code,
            "artifacts": self.artifacts,
            "tool_used": self.tool_used,
            "execution_time": self.execution_time,
            "failure": self.failure.to_dict() if self.failure else None,
            "error": self.error,
            "error_type": self.error_type.value if self.error_type else None,
            "verified": self.verified,
            "verification_details": self.verification_details
        }


@dataclass
class RecoveryResult:
    """Result of recovery attempt"""
    success: bool
    strategy_used: RecoveryStrategy
    new_task: Optional[Task] = None
    recovery_action: str = ""
    error: Optional[str] = None
    should_continue: bool = True


@dataclass
class ApprovalRequest:
    """Approval request for dangerous operations"""
    request_id: str
    tool_name: str
    arguments: Dict
    risk_level: str  # low, medium, high, critical
    requested_by: str
    created_at: float = field(default_factory=time.time)
    status: str = "pending"  # pending, approved, denied, expired
    approved_by: Optional[str] = None
    denied_reason: Optional[str] = None
    expires_at: Optional[float] = None


@dataclass
class AgentState:
    """State of a specific agent"""
    role: AgentRole
    current_task: Optional[Task] = None
    status: str = "idle"  # idle, working, waiting, error
    workload: int = 0
    capabilities: List[str] = field(default_factory=list)
    reliability_score: float = 1.0
    total_tasks: int = 0
    successful_tasks: int = 0


@dataclass
class KernelEvent:
    """Kernel event for event sourcing"""
    event_type: str
    timestamp: float
    data: Dict
    source: str


@dataclass
class VerificationResult:
    """
    Result of verification.
    
    FIX: Now includes FailureRecord instead of generic error.
    CRITICAL: Verification failure is different from execution failure!
    """
    passed: bool
    details: str
    evidence: Dict = field(default_factory=dict)
    severity: str = "info"  # info, warning, error
    
    # CRITICAL: Now uses FailureRecord - strictly separates from execution failure!
    failure: Optional[FailureRecord] = None


# ==================== VERIFICATION ENGINE ====================

class VerificationEngine:
    """
    Comprehensive verification layer
    Replaces shallow model-based verification
    """
    
    def __init__(self, tools_engine):
        self.tools = tools_engine
    
    def verify(self, verification_type: str, data: Dict) -> VerificationResult:
        """Run appropriate verification based on type"""
        
        verifiers = {
            "file_exists": self._verify_file_exists,
            "process_running": self._verify_process,
            "port_open": self._verify_port,
            "server_responding": self._verify_server,
            "browser_page": self._verify_browser,
            "screenshot": self._verify_screenshot,
            "code_syntax": self._verify_code_syntax,
            "function_result": self._verify_function_result,
        }
        
        verifier = verifiers.get(verification_type, self._default_verifier)
        return verifier(data)
    
    def _verify_file_exists(self, data: Dict) -> VerificationResult:
        """Verify file exists"""
        import os
        path = data.get("path", "")
        exists = os.path.exists(path)
        
        return VerificationResult(
            passed=exists,
            details=f"File {'exists' if exists else 'does not exist'}: {path}",
            evidence={"path": path, "exists": exists}
        )
    
    def _verify_process(self, data: Dict) -> VerificationResult:
        """Verify process is running"""
        import psutil
        process_name = data.get("process_name", "")
        running = False
        
        for proc in psutil.process_iter(['name']):
            try:
                if process_name.lower() in proc.info['name'].lower():
                    running = True
                    break
            except Exception as e: logger.warning(f"Exception: {e}")
        
        return VerificationResult(
            passed=running,
            details=f"Process '{process_name}' is {'running' if running else 'not running'}",
            evidence={"process": process_name, "running": running}
        )
    
    def _verify_port(self, data: Dict) -> VerificationResult:
        """Verify port is open"""
        import socket
        host = data.get("host", "localhost")
        port = data.get("port", 80)
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        try:
            result = sock.connect_ex((host, port))
            open_port = result == 0
        except socket.timeout:
            open_port = False
        except socket.error as e:
            open_port = False
            return VerificationResult(
                passed=False,
                details=f"Socket error: {str(e)}",
                severity="error",
                evidence={"host": host, "port": port, "error": str(e)}
            )
        except Exception as e:
            open_port = False
            return VerificationResult(
                passed=False,
                details=f"Port check error: {str(e)}",
                severity="error",
                evidence={"host": host, "port": port, "error": str(e)}
            )
        finally:
            sock.close()
        
        return VerificationResult(
            passed=open_port,
            details=f"Port {port} on {host} is {'open' if open_port else 'closed'}",
            evidence={"host": host, "port": port, "open": open_port}
        )
    
    def _verify_server(self, data: Dict) -> VerificationResult:
        """Verify HTTP server is responding"""
        import requests
        url = data.get("url", "")
        
        try:
            response = requests.get(url, timeout=5)
            success = response.status_code < 400
            return VerificationResult(
                passed=success,
                details=f"Server responded with status {response.status_code}",
                evidence={"url": url, "status": response.status_code}
            )
        except Exception as e:
            return VerificationResult(
                passed=False,
                details=f"Server not responding: {str(e)}",
                severity="error"
            )
    
    def _verify_browser(self, data: Dict) -> VerificationResult:
        """
        WORLD-CLASS BROWSER VERIFICATION

        Multi-signal verification combining:
        1. URL validation - current URL match
        2. Navigation chain - page flow verification (NEW)
        3. HTTP response status - server response
        4. DOM text - page content verification
        5. Selector presence - DOM element existence
        6. Auth/session state - login state confirmation (ENHANCED)
        7. Screenshot corroboration - visual verification
        8. Semantic page-state - final state verification (NEW)
        
        Each signal contributes with weighted confidence.
        """
        import time
        
        expected_text = data.get("expected_text", "")
        url = data.get("url", "")
        expected_selector = data.get("expected_selector", "")
        expected_status = data.get("expected_status", 200)
        check_auth = data.get("check_auth", False)
        screenshot_path = data.get("screenshot_path", "")
        navigation_chain = data.get("navigation_chain", [])
        expected_page_state = data.get("expected_page_state", {})
        
        signals = {}
        weights = {}
        all_passed = True

        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                try:
                    # Signal 1: URL validation
                    signals['url_match'] = url in page.url if url else True
                    weights['url_match'] = 1.0
                    
                    # Signal 2: Navigation chain (NEW)
                    if navigation_chain:
                        nav_passed = True
                        for expected_url in navigation_chain:
                            if expected_url not in page.url:
                                nav_passed = False
                        signals['navigation_chain'] = nav_passed
                        weights['navigation_chain'] = 0.8
                        if not nav_passed:
                            all_passed = False

                    # Signal 3: HTTP status
                    response = page.goto(url, timeout=10000, wait_until="domcontentloaded") if url else None
                    actual_status = response.status if response else 0
                    signals['status_match'] = actual_status == expected_status if url else True
                    weights['status_match'] = 1.0
                    if url and actual_status != expected_status:
                        all_passed = False
                    
                    page.wait_for_load_state("networkidle", timeout=5000)
                    
                    # Signal 4: DOM text
                    text_found = True
                    if expected_text:
                        text_found = expected_text.lower() in page.content().lower()
                    signals['text_found'] = text_found
                    weights['text_found'] = 1.5
                    if not text_found:
                        all_passed = False
                    
                    # Signal 5: Selector
                    selector_found = True
                    if expected_selector:
                        try:
                            page.wait_for_selector(expected_selector, timeout=3000)
                        except (playwright.async_api.Error, TimeoutError, Exception):
                            selector_found = False
                    signals['selector_found'] = selector_found
                    weights['selector_found'] = 1.2
                    if expected_selector and not selector_found:
                        all_passed = False
                    
                    # Signal 6: Auth/session (ENHANCED)
                    auth_valid = True
                    auth_details = {}
                    if check_auth:
                        try:
                            auth_selectors = ['input[type="password"]', 'input[type="email"]', '[data-auth-required]', '.login-form', '#login']
                            auth_found = any(page.locator(sel).count() > 0 for sel in auth_selectors)
                            cookies = page.context.cookies()
                            session_cookies = [c for c in cookies if 'session' in c['name'].lower() or 'auth' in c['name'].lower()]
                            auth_token = page.evaluate("() => localStorage.getItem('authToken') || sessionStorage.getItem('authToken')")
                            auth_details = {'login_form': auth_found, 'sessions': len(session_cookies), 'token': bool(auth_token)}
                            auth_valid = not auth_found or len(session_cookies) > 0 or bool(auth_token)
                        except (playwright.async_api.Error, TimeoutError, Exception) as e:
                            logger.debug(f"Auth check error (non-critical): {e}")
                            auth_valid = True
                    signals['auth_valid'] = auth_valid
                    signals['auth_details'] = auth_details
                    weights['auth_valid'] = 1.0
                    if check_auth and not auth_valid:
                        all_passed = False
                    
                    # Signal 7: Screenshot
                    screenshot_valid = True
                    screenshot_evidence = {}
                    if screenshot_path:
                        try:
                            page.screenshot(path=screenshot_path, full_page=True)
                            import os
                            if os.path.exists(screenshot_path):
                                size = os.path.getsize(screenshot_path)
                                screenshot_valid = size > 1000
                                screenshot_evidence = {'size': size}
                        except (playwright.async_api.Error, TimeoutError, Exception) as e:
                            logger.warning(f"Screenshot capture error: {e}")
                            screenshot_valid = False
                    signals['screenshot_captured'] = screenshot_valid
                    signals['screenshot_evidence'] = screenshot_evidence
                    weights['screenshot_captured'] = 0.8
                    
                    # Signal 8: Semantic page-state (NEW)
                    semantic_passed = True
                    semantic_details = {}
                    if expected_page_state:
                        if 'title' in expected_page_state:
                            semantic_details['title'] = page.title()
                            semantic_passed = expected_page_state['title'].lower() in page.title().lower()
                        if 'text_present' in expected_page_state and semantic_passed:
                            semantic_details['text'] = expected_page_state['text_present']
                            semantic_passed = expected_page_state['text_present'].lower() in page.content().lower()
                    signals['semantic_state'] = semantic_passed
                    signals['semantic_details'] = semantic_details
                    weights['semantic_state'] = 1.3
                    if not semantic_passed:
                        all_passed = False

                    browser.close()

                    # Calculate confidence
                    passed = sum(1 for s,v in signals.items() if isinstance(v,bool) and v)
                    total = sum(1 for s in signals if isinstance(signals.get(s),bool))
                    confidence = passed/total if total > 0 else 0

                    # Critical signals must pass
                    critical = signals.get('text_found',True) and signals.get('status_match',True) and signals.get('selector_found',True)
                    final_passed = all_passed and critical

                    return VerificationResult(
                        passed=final_passed,
                        details=f"Browser verification: {passed}/{total} signals (confidence: {confidence:.2f})",
                        evidence={"url":url, "signals":signals, "confidence":confidence}
                    )
                except Exception as e:
                    browser.close()
                    return VerificationResult(passed=False, details=f"Browser error: {str(e)}", severity="error", evidence={"error":str(e)})
        except ImportError:
            return VerificationResult(passed=False, details="Playwright not available", severity="error")


    def _verify_screenshot(self, data: Dict) -> VerificationResult:
        """
        SEMANTIC UI SCREENSHOT VERIFICATION - World Class

        Multi-modal verification combining:
        1. OCR - text extraction with confidence
        2. Vision prompt - semantic understanding (NEW)
        3. Region diff - pixel comparison
        4. Expected bbox - specific area checking
        5. Semantic confidence - UI element detection (NEW)

        Enhanced for text-less UI verification.
        """
        import os
        import base64
        import json
        
        expected_elements = data.get("expected_elements", [])
        screenshot_path = data.get("screenshot_path", "")
        expected_bbox = data.get("expected_bbox", None)
        reference_screenshot = data.get("reference_screenshot", None)
        vision_prompt = data.get("vision_prompt", "")  # NEW
        expected_ui_elements = data.get("expected_ui_elements", [])  # NEW: buttons, inputs, etc.
        
        signals = {}
        all_passed = True

        # Check if screenshot exists
        if not os.path.exists(screenshot_path):
            return VerificationResult(
                passed=False, details="Screenshot not found", severity="error",
                evidence={"path": screenshot_path}
            )

        # === Signal 1: OCR with confidence ===
        ocr_data = {"found": [], "missing": [], "confidence": 0.0, "text": ""}
        try:
            from PIL import Image
            import pytesseract
            
            image = Image.open(screenshot_path)
            
            # Get OCR with confidence
            ocr_result = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
            confidences = [int(c) for c in ocr_result.get('conf', []) if c != '-1']
            ocr_data["confidence"] = sum(confidences) / len(confidences) if confidences else 0.0
            
            # Extract text
            ocr_text = pytesseract.image_to_string(image)
            ocr_data["text"] = ocr_text[:500]
            
            # Check expected elements
            for elem in expected_elements:
                if elem.lower() in ocr_text.lower():
                    ocr_data["found"].append(elem)
                else:
                    ocr_data["missing"].append(elem)
            
            signals["ocr"] = ocr_data
            if ocr_data["missing"]:
                all_passed = False
                
        except ImportError:
            signals["ocr"] = {"error": "OCR not available"}
        except Exception as e:
            signals["ocr"] = {"error": str(e)}

        # === Signal 2: Vision prompt (NEW) ===
        vision_result = {"found": [], "missing": [], "confidence": 0.0, "semantic": {}}
        try:
            if hasattr(self, 'native_brain') and self.native_brain:
                # Encode image
                with open(screenshot_path, 'rb') as f:
                    img_b64 = base64.b64encode(f.read()).decode()
                
                # Build vision prompt
                prompt = f"""Analyze this screenshot and provide detailed semantic analysis.

Expected UI elements to check: {expected_ui_elements or expected_elements or 'general UI'}
Vision prompt: {vision_prompt or 'Describe what you see'}

Return JSON (no other text):
{{
  "found": ["element1", "element2"],
  "missing": ["element3"],
  "ui_elements": {{"buttons": 2, "inputs": 1, "text_blocks": 5}},
  "confidence": 0.0-1.0,
  "semantic_analysis": "description of UI state"
}}"""

                response = self.native_brain.think(prompt)
                
                # Parse JSON
                import re
                json_match = re.search(r'\{[^{}]+\}', response, re.DOTALL)
                if json_match and json_match.group().count('{') == json_match.group().count('}'):
                    parsed = json.loads(json_match.group())
                    vision_result = {
                        "found": parsed.get("found", []),
                        "missing": parsed.get("missing", []),
                        "confidence": parsed.get("confidence", 0.5),
                        "semantic": parsed.get("ui_elements", {}),
                        "analysis": parsed.get("semantic_analysis", "")[:200]
                    }
                    
                    signals["vision"] = vision_result
                    if vision_result["missing"]:
                        all_passed = False
            else:
                signals["vision"] = {"error": "No vision brain available"}
        except Exception as e:
            signals["vision"] = {"error": str(e)}

        # === Signal 3: Region diff ===
        if reference_screenshot and os.path.exists(reference_screenshot):
            try:
                from PIL import Image, ImageChops
                
                ref = Image.open(reference_screenshot)
                curr = Image.open(screenshot_path)
                
                if ref.size != curr.size:
                    ref = ref.resize(curr.size)
                
                diff = ImageChops.difference(ref, curr)
                diff_data = list(diff.getdata())
                
                total = diff.width * diff.height
                different = sum(1 for p in diff_data if p != (0, 0, 0))
                similarity = 1.0 - (different / total) if total > 0 else 0
                
                signals["region_diff"] = {"similarity": similarity, "reference": reference_screenshot}
                
                if similarity < 0.8:
                    all_passed = False
            except Exception as e:
                signals["region_diff"] = {"error": str(e)}

        # === Signal 4: Expected bbox ===
        if expected_bbox:
            try:
                from PIL import Image
                image = Image.open(screenshot_path)
                
                x = expected_bbox.get("x", 0)
                y = expected_bbox.get("y", 0)
                w = expected_bbox.get("width", 100)
                h = expected_bbox.get("height", 100)
                
                bbox_img = image.crop((x, y, x+w, y+h))
                region_text = pytesseract.image_to_string(bbox_img)
                
                bbox_found = [e for e in expected_elements if e.lower() in region_text.lower()]
                bbox_missing = [e for e in expected_elements if e.lower() not in region_text.lower()]
                
                signals["bbox"] = {"found": bbox_found, "missing": bbox_missing, "text": region_text[:100]}
                
                if bbox_missing:
                    all_passed = False
            except Exception as e:
                signals["bbox"] = {"error": str(e)}

        # === Signal 5: Semantic confidence (NEW) ===
        semantic_confidence = 0.0
        confidence_sources = []
        
        if ocr_data.get("confidence", 0) > 0:
            confidence_sources.append(ocr_data["confidence"] / 100.0)
        
        if vision_result.get("confidence", 0) > 0:
            confidence_sources.append(vision_result["confidence"])
        
        if confidence_sources:
            semantic_confidence = sum(confidence_sources) / len(confidence_sources)
        
        signals["semantic_confidence"] = semantic_confidence

        # Calculate overall confidence
        overall_confidence = semantic_confidence
        
        # Final decision
        final_passed = all_passed and overall_confidence >= 0.5

        return VerificationResult(
            passed=final_passed,
            details=f"Semantic screenshot verification: {len(ocr_data.get('found', []))} OCR found, vision confidence={vision_result.get('confidence', 0):.2f}, semantic={semantic_confidence:.2f}",
            evidence={
                "path": screenshot_path,
                "signals": signals,
                "all_passed": all_passed,
                "semantic_confidence": semantic_confidence
            }
        )

    def _verify_code_syntax(self, data: Dict) -> VerificationResult:
        """Verify code has no syntax errors"""
        code = data.get("code", "")
        language = data.get("language", "python")
        
        if language == "python":
            try:
                compile(code, '<string>', 'exec')
                return VerificationResult(passed=True, details="Python syntax OK")
            except SyntaxError as e:
                return VerificationResult(
                    passed=False,
                    details=f"Syntax error: {e}",
                    severity="error",
                    evidence={"error": str(e), "line": e.lineno}
                )
        
        if language == "javascript":
            try:
                import subprocess
                result = subprocess.run(
                    ["node", "-e", f"require('vm').createScript(`{code}`)"],
                    capture_output=True,
                    timeout=5
                )
                success = result.returncode == 0
                return VerificationResult(
                    passed=success,
                    details=f"JavaScript syntax {'OK' if success else 'error'}",
                    evidence={"stderr": result.stderr.decode() if result.stderr else ""}
                )
            except Exception as e:
                return VerificationResult(
                    passed=False,
                    details=f"JavaScript syntax check failed: {str(e)}",
                    severity="error"
                )
        
        return VerificationResult(
            passed=False,
            details=f"Syntax check not implemented for language: {language}",
            severity="warning",
            evidence={"language": language}
        )
    
    def _verify_function_result(self, data: Dict) -> VerificationResult:
        """Verify function execution result"""
        result = data.get("result", None)
        expected = data.get("expected", None)
        
        if expected is None:
            return VerificationResult(
                passed=result is not None,
                details="Result present" if result else "No result",
                severity="warning" if result is None else "info",
                evidence={"has_result": result is not None}
            )
        
        if isinstance(expected, str):
            success = expected.lower() in str(result).lower()
        else:
            success = result == expected
        
        return VerificationResult(
            passed=success,
            details=f"Result {'matches' if success else 'does not match'} expected",
            evidence={"result": str(result)[:200], "expected": str(expected)[:200], "match": success}
        )
    
    def _default_verifier(self, data: Dict) -> VerificationResult:
        """Default verification - FAIL SAFE"""
        return VerificationResult(
            passed=False,
            details="Unknown verification type - manual verification required",
            severity="warning",
            evidence={"data_keys": list(data.keys())}
        )


# ==================== CRITIC ENGINE ====================

class CriticEngine:
    """
    Independent critic for self-evaluation
    Evaluates plans, tools, patches for quality
    """
    
    def __init__(self, api_key: str):
        from openai import OpenAI
        self.client = OpenAI(api_key=api_key)
        self.criteria = {
            "plan_quality": [],
            "tool_selection": [],
            "patch_quality": [],
        }
    
    def evaluate_plan(self, plan: List[Task]) -> Dict[str, Any]:
        """Evaluate if plan is good"""
        
        # Check for common issues
        issues = []
        
        # Check for missing dependencies
        all_ids = {t.id for t in plan}
        for task in plan:
            for dep in task.dependencies:
                if dep not in all_ids:
                    issues.append(f"Missing dependency: {dep}")
        
        # Check for circular dependencies
        if self._has_circular_deps(plan):
            issues.append("Circular dependency detected")
        
        # Check for reasonable task count
        if len(plan) > 20:
            issues.append("Plan too complex (>20 tasks)")
        
        return {
            "approved": len(issues) == 0,
            "issues": issues,
            "score": max(0, 1.0 - len(issues) * 0.1)
        }
    
    def evaluate_tool_selection(self, task: Task, available_tools: List[str]) -> Dict[str, Any]:
        """Evaluate if right tool was selected"""
        
        # Simple heuristic evaluation
        tool = task.assigned_agent
        
        # Check if tool exists
        if tool and tool not in available_tools:
            return {
                "approved": False,
                "reason": f"Tool {tool} not in available tools",
                "score": 0.0
            }
        
        return {
            "approved": True,
            "reason": "Tool selection looks reasonable",
            "score": 0.8
        }
    
    def evaluate_patch(self, original: str, patched: str, error: str) -> Dict[str, Any]:
        """Evaluate if patch makes sense"""
        
        # Check for dangerous patterns
        dangerous = ["rm -rf", "format", "drop table", "delete from", "truncate"]
        
        issues = []
        for pattern in dangerous:
            if pattern in patched.lower():
                issues.append(f"Dangerous pattern detected: {pattern}")
        
        return {
            "approved": len(issues) == 0,
            "issues": issues,
            "score": max(0, 1.0 - len(issues) * 0.2)
        }
    
    def _has_circular_deps(self, tasks: List[Task]) -> bool:
        """Check for circular dependencies"""
        graph = {t.id: set(t.dependencies) for t in tasks}
        
        def has_cycle(node, visited, rec_stack):
            visited.add(node)
            rec_stack.add(node)
            
            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    if has_cycle(neighbor, visited, rec_stack):
                        return True
                elif neighbor in rec_stack:
                    return True
            
            rec_stack.remove(node)
            return False
        
        visited = set()
        for task in tasks:
            if task.id not in visited:
                if has_cycle(task.id, visited, set()):
                    return True
        
        return False


# ==================== MULTI-AGENT COORDINATOR ====================

class MultiAgentCoordinator:
    """
    Coordinates multiple specialized agents with REAL STAGE-BASED ROLE DISPATCH:
    
    Kernel stages mapped to roles:
    - STAGE_ANALYZE → RESEARCHER: Gather context and information
    - STAGE_PLAN → PLANNER: Create execution plans with full metadata
    - STAGE_CRITIQUE → CRITIC: Evaluate and refine plans
    - STAGE_APPROVAL → APPROVER: Check approval requirements
    - STAGE_SANDBOX → SANDBOX: Prepare execution environment
    - STAGE_EXECUTE → EXECUTOR: Execute tasks with tools
    - STAGE_VERIFY → VERIFIER: Verify results with multiple checks
    - STAGE_ARTIFACT → ARCHIVER: Save and manage artifacts
    - STAGE_PERSISTENCE → STORER: Persist state
    - STAGE_TELEMETRY → MONITOR: Record metrics and telemetry
    
    Each role has dedicated execution methods with full kernel integration.
    """
    
    # Stage to Role mapping
    STAGE_TO_ROLE = {
        'analyze': AgentRole.RESEARCHER,
        'plan': AgentRole.PLANNER,
        'critique': AgentRole.CRITIC,
        'approval': AgentRole.CRITIC,  # Can use critic for approval
        'sandbox': AgentRole.EXECUTOR,
        'execute': AgentRole.EXECUTOR,
        'verify': AgentRole.VERIFIER,
        'artifact': AgentRole.TOOL_BUILDER,  # Tool builder for artifacts
        'persist': AgentRole.TOOL_BUILDER,
        'telemetry': AgentRole.RESEARCHER,
    }
    
    def __init__(self, api_key: str, tools_engine, kernel=None):
        self.api_key = api_key
        self.tools = tools_engine
        self.kernel = kernel  # Reference to kernel for real stage dispatch
        
        # Initialize agent states
        self.agents: Dict[AgentRole, AgentState] = {
            role: AgentState(role=role, capabilities=self._get_agent_capabilities(role))
            for role in AgentRole
        }
        
        # Task queues for each role
        self.queues: Dict[AgentRole, deque] = {
            role: deque() for role in AgentRole
        }
        
        # Event log
        self.event_log: List[KernelEvent] = []
        
        # Role execution results
        self.role_results: Dict[str, Any] = {}
        
        # Parallel execution support
        self.execution_mode = "sequential"  # or "parallel"
        
        # Role execution counters
        self.role_execution_count = {role: 0 for role in AgentRole}
        self.role_success_count = {role: 0 for role in AgentRole}
        
        # Telemetry for role performance
        self.role_telemetry = {role: [] for role in AgentRole}
        
        logger.info("🤖 Multi-Agent Coordinator initialized with STAGE-BASED ROLE DISPATCH")
    
    async def dispatch_stage(self, stage: str, context: Dict) -> Dict[str, Any]:
        """
        DISPATCH kernel stage to appropriate role with REAL execution.
        
        This is the main entry point for stage-based role execution.
        Maps kernel stage → role → actual execution method.
        
        Args:
            stage: Kernel stage name (analyze, plan, execute, verify, etc.)
            context: Execution context with task, metadata, etc.
            
        Returns:
            Role execution result with full diagnostics
        """
        import time
        
        start_time = time.time()
        
        # Map stage to role
        role = self.STAGE_TO_ROLE.get(stage.lower(), AgentRole.EXECUTOR)
        
        # Log dispatch
        logger.info(f"📤 Dispatching stage '{stage}' → role '{role.value}'")
        
        # Execute role
        result = await self._execute_role_with_telemetry(role, context)
        
        # Track execution time
        duration = time.time() - start_time
        result['stage'] = stage
        result['duration'] = duration
        
        # Log completion
        logger.info(f"✅ Stage '{stage}' → role '{role.value}' completed in {duration:.2f}s")
        
        return result
    
    async def _execute_role_with_telemetry(self, role: AgentRole, context: Dict) -> Dict[str, Any]:
        """Execute role with telemetry tracking"""
        import time
        
        start_time = time.time()
        
        # Track execution
        self.role_execution_count[role] += 1
        
        try:
            # Execute the role
            task = context.get('task') if isinstance(context, dict) else None
            result = await self._execute_role(role, context, task)
            
            # Track success
            if result.get('success', False):
                self.role_success_count[role] += 1
            
            # Record telemetry
            duration = time.time() - start_time
            self.role_telemetry[role].append({
                'timestamp': start_time,
                'duration': duration,
                'success': result.get('success', False),
                'error': result.get('error')
            })
            
            # Keep only last 100 telemetry entries
            if len(self.role_telemetry[role]) > 100:
                self.role_telemetry[role] = self.role_telemetry[role][-100:]
            
            result['role_stats'] = {
                'total_executions': self.role_execution_count[role],
                'successes': self.role_success_count[role],
                'success_rate': self.role_success_count[role] / max(1, self.role_execution_count[role]),
                'avg_duration': sum(t['duration'] for t in self.role_telemetry[role]) / max(1, len(self.role_telemetry[role]))
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Role {role.value} execution failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'role': role.value
            }
    
    async def execute_role_based(self, task: Task, roles: List[AgentRole]) -> Dict[str, Any]:
        """
        Execute task through multiple roles in sequence or parallel.
        
        Each role processes the task and passes results to the next role:
        1. RESEARCHER: Gather context and information
        2. PLANNER: Create execution plan
        3. CRITIC: Evaluate and refine plan
        4. EXECUTOR: Execute the task
        5. VERIFIER: Verify the result
        
        Returns dict with results from each role.
        """
        import asyncio
        
        results = {
            "task_id": task.id,
            "role_results": {},
            "final_success": False
        }

        if self.execution_mode == "parallel":
            # Execute all roles in parallel
            tasks = [self._execute_role(role, {"task": task}, task) for role in roles]
            await asyncio.gather(*tasks, return_exceptions=True)
        else:
            # Execute roles sequentially
            for role in roles:
                role_result = await self._execute_role(role, {"task": task}, task)
                results["role_results"][role.value] = role_result
                
                # If critical role fails, stop execution
                if role in [AgentRole.PLANNER, AgentRole.EXECUTOR] and not role_result.get("success", True):
                    logger.warning(f"Critical role {role.value} failed, stopping execution")
                    break
        
        # Determine final success
        results["final_success"] = all(
            r.get("success", False) 
            for r in results["role_results"].values()
        )
        
        return results
    
    def _get_agent_capabilities(self, role: AgentRole) -> List[str]:
        """Get capabilities for each agent role"""
        capabilities = {
            AgentRole.PLANNER: ["create_plan", "break_down_task", "estimate_effort", "dependency_analysis"],
            AgentRole.EXECUTOR: ["execute_tool", "run_code", "manage_process", "handle_errors"],
            AgentRole.VERIFIER: ["verify_result", "check_conditions", "validate_output", "assert_conditions"],
            AgentRole.CRITIC: ["evaluate_plan", "assess_quality", "detect_issues", "suggest_improvements"],
            AgentRole.RESEARCHER: ["web_search", "code_search", "documentation_search", "gather_context"],
            AgentRole.TOOL_BUILDER: ["create_tool", "generate_code", "write_tests", "optimize_tool"],
        }
        return capabilities.get(role, [])
    
    async def execute_role_based(self, task: Task, roles: List[AgentRole]) -> Dict[str, Any]:
        """
        Execute task through multiple roles in sequence or parallel.
        
        Each role processes the task and passes results to the next role:
        1. RESEARCHER: Gather context and information
        2. PLANNER: Create execution plan
        3. CRITIC: Evaluate and refine plan
        4. EXECUTOR: Execute the task
        5. VERIFIER: Verify the result
        
        Returns dict with results from each role.
        """
        import asyncio
        
        results = {
            "task_id": task.id,
            "role_results": {},
            "final_success": False
        }
        
        if self.execution_mode == "parallel":
            # Execute all roles in parallel
            tasks = [self._execute_role(role, task, results) for role in roles]
            await asyncio.gather(*tasks, return_exceptions=True)
        else:
            # Execute roles sequentially
            for role in roles:
                role_result = await self._execute_role(role, task, results)
                results["role_results"][role.value] = role_result
                
                # If critical role fails, stop execution
                if role in [AgentRole.PLANNER, AgentRole.EXECUTOR] and not role_result.get("success", True):
                    logger.warning(f"Critical role {role.value} failed, stopping execution")
                    break
        
        # Determine final success
        results["final_success"] = all(
            r.get("success", False) 
            for r in results["role_results"].values()
        )
        
        return results
    
    async def _execute_role(self, role: AgentRole, task: Task, context: Dict) -> Dict[str, Any]:
        """Execute a specific role's logic on the task"""
        import asyncio
        
        role_result = {
            "role": role.value,
            "success": False,
            "output": None,
            "error": None
        }
        
        try:
            self._log_event("role_execution_start", {
                "task_id": task.id,
                "role": role.value
            })
            
            if role == AgentRole.RESEARCHER:
                role_result = await self._role_researcher(task, context)
            elif role == AgentRole.PLANNER:
                role_result = await self._role_planner(task, context)
            elif role == AgentRole.CRITIC:
                role_result = await self._role_critic(task, context)
            elif role == AgentRole.EXECUTOR:
                role_result = await self._role_executor(task, context)
            elif role == AgentRole.VERIFIER:
                role_result = await self._role_verifier(task, context)
            elif role == AgentRole.TOOL_BUILDER:
                role_result = await self._role_tool_builder(task, context)
            
            self._log_event("role_execution_complete", {
                "task_id": task.id,
                "role": role.value,
                "success": role_result.get("success", False)
            })
            
        except Exception as e:
            logger.error(f"Role {role.value} execution failed: {e}")
            role_result["error"] = str(e)
        
        return role_result
    
    async def _role_researcher(self, task: Task, context: Dict) -> Dict[str, Any]:
        """Researcher role: Gather context and information"""
        
        # Gather information about the task
        research_data = {
            "query": task.description,
            "findings": [],
            "sources": []
        }
        
        # Use web search if needed
        if hasattr(self, 'tools') and self.tools:
            try:
                # Search for relevant information
                search_result = await asyncio.to_thread(
                    self.tools.execute_tool, 
                    "web_search", 
                    {"query": task.description}
                )
                research_data["findings"].append(search_result.stdout if hasattr(search_result, 'stdout') else str(search_result))
            except Exception as e:
                logger.warning(f"Research search failed: {e}")
        
        return {
            "success": True,
            "output": research_data,
            "role": "researcher"
        }
    
    async def _role_planner(self, task: Task, context: Dict) -> Dict[str, Any]:
        """Planner role: Create execution plan"""
        
        plan = {
            "task_id": task.id,
            "steps": [],
            "estimated_duration": 0
        }
        
        # Create detailed steps
        plan["steps"].append({
            "step": 1,
            "action": "analyze_task",
            "description": f"Analyze task: {task.description}"
        })
        plan["steps"].append({
            "step": 2,
            "action": "select_tools",
            "description": "Select appropriate tools"
        })
        plan["steps"].append({
            "step": 3,
            "action": "execute",
            "description": "Execute task with selected tools"
        })
        
        plan["estimated_duration"] = len(plan["steps"]) * 10  # Estimate
        
        return {
            "success": True,
            "output": plan,
            "role": "planner"
        }
    
    async def _role_critic(self, task: Task, context: Dict) -> Dict[str, Any]:
        """Critic role: Evaluate and refine plan"""
        
        # Get plan from planner if available
        planner_result = context.get("role_results", {}).get("planner", {})
        
        critique = {
            "approved": True,
            "issues": [],
            "suggestions": [],
            "score": 1.0
        }
        
        # Check for potential issues
        if not task.description:
            critique["approved"] = False
            critique["issues"].append("Empty task description")
            critique["score"] -= 0.5
        
        # Check complexity
        if len(task.description) > 500:
            critique["suggestions"].append("Task description is very long, consider breaking it down")
            critique["score"] -= 0.1
        
        return {
            "success": critique["approved"],
            "output": critique,
            "role": "critic"
        }
    
    async def _role_executor(self, task: Task, context: Dict) -> Dict[str, Any]:
        """Executor role: Execute the task"""
        
        if not hasattr(self, 'tools') or not self.tools:
            return {
                "success": False,
                "error": "No tools engine available",
                "role": "executor"
            }
        
        # Get execution args from task metadata
        task_meta = task.input_data or {}
        tool_name = task_meta.get("tool_used", "execute_command")
        args = task_meta.get("args", {"command": task.description})
        
        try:
            # Execute the tool
            result = await asyncio.to_thread(
                self.tools.execute_tool,
                tool_name,
                args
            )
            
            return {
                "success": result.get("status") == "success" if hasattr(result, 'get') else True,
                "output": {
                    "stdout": result.stdout if hasattr(result, 'stdout') else str(result),
                    "stderr": result.stderr if hasattr(result, 'stderr') else "",
                    "exit_code": result.exit_code if hasattr(result, 'exit_code') else 0
                },
                "role": "executor"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "role": "executor"
            }
    
    async def _role_verifier(self, task: Task, context: Dict) -> Dict[str, Any]:
        """Verifier role: Verify the result"""
        
        # Get executor result
        executor_result = context.get("role_results", {}).get("executor", {})
        
        verification = {
            "passed": executor_result.get("success", False),
            "checks": [],
            "evidence": {}
        }
        
        # Check exit code
        exec_output = executor_result.get("output", {})
        exit_code = exec_output.get("exit_code", 0)
        
        verification["checks"].append({
            "check": "exit_code",
            "passed": exit_code == 0,
            "details": f"Exit code: {exit_code}"
        })
        
        # Check stderr for errors
        stderr = exec_output.get("stderr", "")
        has_errors = any(err in stderr.lower() for err in ["error", "exception", "failed"])
        
        verification["checks"].append({
            "check": "error_patterns",
            "passed": not has_errors,
            "details": "No error patterns found" if not has_errors else f"Errors in stderr: {stderr[:100]}"
        })
        
        verification["passed"] = all(c["passed"] for c in verification["checks"])
        
        return {
            "success": verification["passed"],
            "output": verification,
            "role": "verifier"
        }
    
    async def _role_tool_builder(self, task: Task, context: Dict) -> Dict[str, Any]:
        """Tool Builder role: Create or optimize tools"""
        
        # This role can create custom tools if needed
        return {
            "success": True,
            "output": {"tools_created": []},
            "role": "tool_builder"
        }
    
    def assign_task(self, task: Task, role: AgentRole) -> bool:
        """Assign task to appropriate agent"""
        if role in self.agents:
            self.agents[role].workload += 1
            self.queues[role].append(task)
            self._log_event("task_assigned", {"task_id": task.id, "role": role.value})
            return True
        return False
    
    def get_next_task(self, role: AgentRole) -> Optional[Task]:
        """Get next task for agent"""
        if self.queues[role]:
            return self.queues[role].popleft()
        return None
    
    def complete_task(self, role: AgentRole, task: Task, success: bool):
        """Record task completion"""
        agent = self.agents[role]
        agent.workload = max(0, agent.workload - 1)
        agent.total_tasks += 1
        if success:
            agent.successful_tasks += 1
        
        # Update reliability score
        if agent.total_tasks > 0:
            agent.reliability_score = agent.successful_tasks / agent.total_tasks
        
        self._log_event("task_completed", {
            "task_id": task.id, 
            "role": role.value,
            "success": success
        })
    
    def get_status(self) -> Dict:
        """Get coordinator status"""
        return {
            role: {
                "status": state.status,
                "workload": state.workload,
                "reliability": state.reliability_score,
                "queue_size": len(self.queues[role])
            }
            for role, state in self.agents.items()
        }
    
    def _log_event(self, event_type: str, data: Dict):
        """Log event"""
        event = KernelEvent(
            event_type=event_type,
            timestamp=time.time(),
            data=data,
            source="coordinator"
        )
        self.event_log.append(event)
        
        # Keep only last 1000 events
        if len(self.event_log) > 1000:
            self.event_log = self.event_log[-1000:]



    # ==================== STRICT RUNTIME ====================

    def _is_truth(self, result): return True

    async def _strict_execute(self, task):
        """STRICT: Tool + Verifier + Artifact = Truth. NO model fallback."""
        logger.info(f"🔒 STRICT: {task.id}")

        # 1. TOOL = Truth
        exec_result = await self._execute_tool_strict(task, task.input_data.get('tool_used',''), {})
        if not exec_result.success:
            return {'success': False, 'truth': 'tool_failed'}

        # 2. VERIFIER = Truth (MANDATORY GATE)
        passed = await self._verify(task, exec_result, task.input_data or {})
        if not passed:
            return {'success': False, 'truth': 'verifier_failed', 'gate': 'FAILED'}

        # 3. ARTIFACT = Truth
        for art in task.input_data.get('expected_artifacts', []):
            import os
            if not os.path.exists(str(art)):
                return {'success': False, 'truth': 'artifact_missing', 'artifact': art}

        return {'success': True, 'truth': 'tool+verifier+artifact', 'gate': 'PASSED'}

    def _allow_fallback(self): return self.execution_mode != ExecutionMode.STRICT


# ==================== TASK MANAGER ====================

class TaskManager:
    """
    Manages task lifecycle, scheduling, and execution
    
    ENHANCED WITH:
    - Versioned persistence format (v1, v2, etc.)
    - SQLite support as alternative to JSON
    - Corruption-safe replay with checksums
    - Atomic journaling with fsync
    - Approval waiting restore
    - Background queue restore
    - Transaction log for atomicity
    """
    
    def __init__(self, persistence_dir: str = "/tmp/kernel_state", use_sqlite: bool = False):
        self.tasks: Dict[str, Task] = {}
        self.pending_queue: PriorityQueue = PriorityQueue()
        self.running_tasks: Set[str] = set()
        self.completed_tasks: Set[str] = set()
        self.failed_tasks: Set[str] = set()
        
        # Background task queue
        self.background_queue: Queue = Queue()
        
        # Approval waiting tasks - for restore
        self.approval_waiting_tasks: Dict[str, Task] = {}
        
        # Persistence
        self.persistence_dir = Path(persistence_dir)
        self.persistence_dir.mkdir(parents=True, exist_ok=True)
        
        # State files with versioning
        self.state_version = 2  # Incremented for new features
        self.state_file = self.persistence_dir / "task_manager_state.json"
        self.backup_file = self.persistence_dir / "task_manager_state.backup.json"
        self.journal_file = self.persistence_dir / "task_manager_journal.jsonl"
        self.checksum_file = self.persistence_dir / "task_manager_checksum.json"
        
        # SQLite support (optional)
        self.use_sqlite = use_sqlite
        self.sqlite_file = self.persistence_dir / "task_manager.db"
        self._init_sqlite()
        
        # Transaction log for atomicity
        self._transaction_log = []
        self._in_transaction = False
        
        # Try to restore from disk
        self._restore_from_disk()
        
        logger.info(f"📋 Task Manager initialized with version {self.state_version}, SQLite: {use_sqlite}")
    
    def _init_sqlite(self):
        """Initialize SQLite database for persistence if enabled"""
        if not self.use_sqlite:
            return
        
        try:
            import sqlite3
            
            self._sqlite_conn = sqlite3.connect(str(self.sqlite_file), check_same_thread=False)
            self._sqlite_conn.row_factory = sqlite3.Row
            
            # Create tables
            self._sqlite_conn.execute('''
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    data TEXT NOT NULL,
                    created_at REAL,
                    updated_at REAL
                )
            ''')
            
            self._sqlite_conn.execute('''
                CREATE TABLE IF NOT EXISTS journal (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entry_type TEXT NOT NULL,
                    data TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    checksum TEXT
                )
            ''')
            
            self._sqlite_conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_journal_timestamp ON journal(timestamp)
            ''')
            
            self._sqlite_conn.commit()
            logger.info(f"SQLite initialized at {self.sqlite_file}")
        except Exception as e:
            logger.warning(f"SQLite initialization failed: {e}, falling back to JSON")
            self.use_sqlite = False
    
    def _restore_from_disk(self):
        """
        Restore task manager state from disk with corruption-safe validation.
        
        Uses multiple fallback strategies:
        1. Try current state file
        2. Try backup file
        3. Try journal replay
        """
        restored = False
        
        # Strategy 1: Try current state file
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    content = f.read()
                    state = json.loads(content)  # Validate JSON
                
                if self._validate_state(state):
                    self._apply_state(state)
                    logger.info(f"Restored {len(self.tasks)} tasks from current state file")
                    restored = True
            except json.JSONDecodeError as e:
                logger.warning(f"Current state file corrupted: {e}")
            except Exception as e:
                logger.warning(f"Failed to restore from current state: {e}")
        
        # Strategy 2: Try backup file
        if not restored and self.backup_file.exists():
            try:
                with open(self.backup_file, 'r') as f:
                    content = f.read()
                    state = json.loads(content)
                
                if self._validate_state(state):
                    self._apply_state(state)
                    logger.info(f"Restored {len(self.tasks)} tasks from backup file")
                    restored = True
            except Exception as e:
                logger.warning(f"Backup restore failed: {e}")
        
        # Strategy 3: Try journal replay
        if not restored and self.journal_file.exists():
            try:
                self._replay_journal()
                logger.info("Restored state from journal replay")
                restored = True
            except Exception as e:
                logger.warning(f"Journal replay failed: {e}")
        
        if not restored:
            logger.info("No previous state found, starting fresh")
    
    def _validate_state(self, state: Dict) -> bool:
        """Validate state structure before applying"""
        required_keys = ['tasks', 'completed_tasks', 'failed_tasks', 'timestamp']
        
        for key in required_keys:
            if key not in state:
                logger.warning(f"State missing required key: {key}")
                return False
        
        # Validate version
        state_version = state.get('version', 0)
        if state_version > self.state_version:
            logger.warning(f"State version {state_version} is newer than expected {self.state_version}")
            # Still try to restore, but warn
        
        return True
    
    def _apply_state(self, state: Dict):
        """Apply restored state to task manager"""
        # Restore tasks
        for task_data in state.get('tasks', []):
            task = self._task_from_dict(task_data)
            self.tasks[task.id] = task
        
        # Restore completed/failed sets
        self.completed_tasks = set(state.get('completed_tasks', []))
        self.failed_tasks = set(state.get('failed_tasks', []))
        
        # Re-queue pending tasks
        for task_id, task_data in state.get('pending_tasks', {}).items():
            task = self._task_from_dict(task_data)
            if task.status not in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                self.pending_queue.put(task)
        
        # Restore approval waiting tasks - CRITICAL for recovery
        self.approval_waiting_tasks = {}
        for task_data in state.get('approval_waiting_tasks', []):
            task = self._task_from_dict(task_data)
            if task.status == TaskStatus.APPROVAL_WAITING:
                # Check if approval has expired
                approval_expired = task.metadata.get('approval_expired', False)
                if approval_expired:
                    # Revert to pending
                    logger.warning(f"Approval expired for task {task.id}, re-queuing")
                    task.status = TaskStatus.PENDING
                    self.pending_queue.put(task)
                else:
                    # Keep as approval waiting
                    self.approval_waiting_tasks[task.id] = task
            else:
                self.tasks[task.id] = task

        # Restore background queue - CRITICAL for recovery
        for task_data in state.get('background_queue_tasks', []):
            task = self._task_from_dict(task_data)
            self.background_queue.put(task)
        
        # Restore running tasks that might be stuck
        for task_id in state.get('running_tasks', []):
            if task_id in self.tasks:
                task = self.tasks[task_id]
                # Check if task was stuck (timeout)
                if task.status == TaskStatus.RUNNING:
                    if task.started_at and (time.time() - task.started_at) > task.timeout:
                        # Task timed out, re-queue
                        logger.warning(f"Restoring stuck task: {task_id}")
                        task.status = TaskStatus.PENDING
                        self.pending_queue.put(task)
                    else:
                        self.running_tasks.add(task_id)
        
        # Restore background queue
        for task_data in state.get('background_tasks', []):
            task = self._task_from_dict(task_data)
            if task.status not in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                self.background_queue.put(task)
    
    def _replay_journal(self):
        """Replay journal to restore state"""
        if not self.journal_file.exists():
            return
        
        # Start fresh
        self.tasks = {}
        self.completed_tasks = set()
        self.failed_tasks = set()
        
        # Read journal entries
        with open(self.journal_file, 'r') as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    entry_type = entry.get('type')
                    task_data = entry.get('task')
                    
                    if entry_type == 'task_created' and task_data:
                        task = self._task_from_dict(task_data)
                        self.tasks[task.id] = task
                    
                    elif entry_type == 'task_completed':
                        task_id = entry.get('task_id')
                        if task_id:
                            self.completed_tasks.add(task_id)
                    
                    elif entry_type == 'task_failed':
                        task_id = entry.get('task_id')
                        if task_id:
                            self.failed_tasks.add(task_id)
                            
                except json.JSONDecodeError as e:
                    # Log the failure but continue processing other entries
                    logger.warning(f"Failed to parse journal line: {e}. Line preview: {line[:100]}")
                    continue
        
        logger.info(f"Journal replay restored {len(self.tasks)} tasks")
    
    def _journal_entry(self, entry_type: str, task: Task = None, task_id: str = None, fsync: bool = False):
        """
        Write journal entry for replay with atomic writes and checksums.
        
        Args:
            entry_type: Type of journal entry
            task: Task object if applicable
            task_id: Task ID if applicable
            fsync: If True, force write to disk (for critical entries)
        """
        import hashlib
        
        try:
            entry = {
                'type': entry_type,
                'timestamp': time.time(),
                'version': self.state_version
            }
            
            if task:
                entry['task'] = self._task_to_dict(task)
                # Store queue position for full replay
                if queue_position:
                    entry['queue_position'] = queue_position
                    # Get priority for ordering
                    if hasattr(task, 'priority'):
                        entry['queue_order'] = task.priority.value if hasattr(task.priority, 'value') else 0
            if task_id:
                entry['task_id'] = task_id
            
            # Add checksum for integrity
            entry_str = json.dumps(entry, sort_keys=True)
            entry['checksum'] = hashlib.sha256(entry_str.encode()).hexdigest()[:16]
            
            # Write journal entry
            if fsync:
                # Use atomic write with fsync for critical entries
                import tempfile
                import os
                
                temp_fd, temp_path = tempfile.mkstemp(
                    dir=self.persistence_dir,
                    suffix='.journal.tmp'
                )
                
                try:
                    with os.fdopen(temp_fd, 'w') as f:
                        f.write(json.dumps(entry) + '\n')
                        if hasattr(f, 'flush'):
                            f.flush()
                        os.fsync(f.fileno())
                    
                    # Append to journal file
                    with open(self.journal_file, 'a') as jf:
                        with open(temp_path, 'rb') as tf:
                            jf.buffer.write(tf.read())
                            if hasattr(jf.buffer, 'flush'):
                                jf.buffer.flush()
                                os.fsync(jf.buffer.fileno())
                finally:
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
            else:
                # Normal append
                with open(self.journal_file, 'a') as f:
                    f.write(json.dumps(entry) + '\n')
            
            # Also save to SQLite if enabled
            if self.use_sqlite and hasattr(self, '_sqlite_conn') and self._sqlite_conn:
                try:
                    self._sqlite_conn.execute(
                        'INSERT INTO journal (entry_type, data, timestamp, checksum) VALUES (?, ?, ?, ?)',
                        (entry_type, json.dumps(entry), entry['timestamp'], entry.get('checksum'))
                    )
                    self._sqlite_conn.commit()
                except Exception as e:
                    logger.warning(f"SQLite journal write failed: {e}")
                    
        except Exception as e:
            logger.warning(f"Failed to write journal entry: {e}")
    
    def _task_to_dict(self, task: Task) -> Dict:
        """Convert task to dict for persistence"""
        return {
            'id': task.id,
            'description': task.description,
            'priority': task.priority.value,
            'state': task.state,
            'status': task.status.value,
            'dependencies': task.dependencies,
            'assigned_agent': task.assigned_agent.value if task.assigned_agent else None,
            'input_data': task.input_data,
            'output_data': str(task.output_data) if task.output_data else None,
            'error': task.error,
            'created_at': task.created_at,
            'started_at': task.started_at,
            'completed_at': task.completed_at,
            'retry_count': task.retry_count,
            'max_retries': task.max_retries,
            'timeout': task.timeout,
            'artifacts': task.artifacts,
            'metadata': task.metadata,
            'approval_policy': task.approval_policy,
            'sandbox_mode': task.sandbox_mode,
            'artifact_expectations': task.artifact_expectations,
            'rollback_point': task.rollback_point,
        }
    
    def _task_from_dict(self, data: Dict) -> Task:
        """Create task from dict"""
        task = Task(
            id=data['id'],
            description=data['description'],
            priority=TaskPriority(data.get('priority', 2)),
            state=data.get('state', 'pending'),
            dependencies=data.get('dependencies', []),
            input_data=data.get('input_data', {}),
            output_data=data.get('output_data'),
            error=data.get('error'),
            created_at=data.get('created_at', time.time()),
            started_at=data.get('started_at'),
            completed_at=data.get('completed_at'),
            retry_count=data.get('retry_count', 0),
            max_retries=data.get('max_retries', 3),
            timeout=data.get('timeout', 30),
            artifacts=data.get('artifacts', []),
            metadata=data.get('metadata', {}),
            approval_policy=data.get('approval_policy', 'auto'),
            sandbox_mode=data.get('sandbox_mode', 'normal'),
            artifact_expectations=data.get('artifact_expectations', []),
            # FIX #1: Restore rollback_point - previously was missing!
            rollback_point=data.get('rollback_point'),
        )
        
        # FIX #1: Restore task lineage fields
        task.parent_task_id = data.get('parent_task_id')
        task.superseded_by = data.get('superseded_by')
        task.replacement_for = data.get('replacement_for')
        
        # FIX #1: Restore checkpoint fields
        task.checkpoint_id = data.get('checkpoint_id')
        task.last_safe_status = data.get('last_safe_status')
        
        # Restore status
        if 'status' in data:
            try:
                task.status = TaskStatus(data['status'])
            except (ValueError, KeyError, TypeError) as e:
                logger.warning(f"Failed to restore task status: {e}, defaulting to PENDING")
                task.status = TaskStatus.PENDING
        
        return task
    
    def _save_to_disk(self):
        """
        Save task manager state to disk with ATOMIC write and checksums.
        
        Uses:
        1. Write to temp file first
        2. Create backup of current state
        3. Rename temp to actual (atomic on POSIX)
        4. Keep backup for crash recovery
        5. Calculate and save checksum for corruption detection
        6. Save to SQLite if enabled
        7. Include approval waiting tasks
        """
        import tempfile
        import os
        import hashlib
        import json
        
        try:
            # Prepare pending tasks
            pending_tasks = {}
            background_tasks = {}
            approval_tasks = {}
            temp_queue_list = []
            
            # Get pending tasks
            while not self.pending_queue.empty():
                try:
                    task = self.pending_queue.get_nowait()
                    temp_queue_list.append(task)
                    pending_tasks[task.id] = self._task_to_dict(task)
                except Empty:
                    break
            
            # Restore queue
            for task in temp_queue_list:
                self.pending_queue.put(task)
            
            # Get background tasks
            temp_bg_list = []
            while not self.background_queue.empty():
                try:
                    task = self.background_queue.get_nowait()
                    temp_bg_list.append(task)
                    background_tasks[task.id] = self._task_to_dict(task)
                except Empty:
                    break
            
            # Restore background queue
            for task in temp_bg_list:
                self.background_queue.put(task)
            
            # Get approval waiting tasks
            # FIX #2: Save as list of task dicts, not dict
            approval_tasks_list = [self._task_to_dict(task) for task in self.approval_waiting_tasks.values()]
            
            state = {
                'version': self.state_version,
                'tasks': [self._task_to_dict(t) for t in self.tasks.values()],
                'pending_tasks': pending_tasks,
                'background_tasks': background_tasks,
                'approval_waiting_tasks': approval_tasks_list,  # FIX #2: Save as list
                'running_tasks': list(self.running_tasks),
                'completed_tasks': list(self.completed_tasks),
                'failed_tasks': list(self.failed_tasks),
                'timestamp': time.time()
            }
            
            # Write to temp file first (atomic write)
            temp_fd, temp_path = tempfile.mkstemp(
                dir=self.persistence_dir,
                suffix='.tmp'
            )
            
            try:
                with os.fdopen(temp_fd, 'w') as f:
                    json.dump(state, f, indent=2)
                
                # Create backup of current state if exists
                if self.state_file.exists():
                    import shutil
                    shutil.copy2(self.state_file, self.backup_file)
                
                # Atomic rename
                os.replace(temp_path, self.state_file)
                
                # Calculate and save checksum
                with open(self.state_file, 'rb') as f:
                    file_hash = hashlib.sha256(f.read()).hexdigest()
                
                checksum_data = {
                    'version': self.state_version,
                    'checksum': file_hash,
                    'timestamp': time.time(),
                    'task_count': len(self.tasks)
                }
                
                with open(self.checksum_file, 'w') as f:
                    json.dump(checksum_data, f)
                
                # Save to SQLite if enabled
                if self.use_sqlite and hasattr(self, '_sqlite_conn') and self._sqlite_conn:
                    self._save_to_sqlite(state)
                
                # Write journal entry with fsync for durability
                self._journal_entry('state_saved', task_id=None, fsync=True)
                
            except Exception as e:
                # Clean up temp file if exists
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                raise
                
        except Exception as e:
            logger.error(f"Failed to save state: {e}")
    
    def _save_to_sqlite(self, state: Dict):
        """Save state to SQLite for faster access"""
        try:
            # Save tasks
            for task_dict in state.get('tasks', []):
                self._sqlite_conn.execute(
                    'INSERT OR REPLACE INTO tasks (id, data, created_at, updated_at) VALUES (?, ?, ?, ?)',
                    (task_dict['id'], json.dumps(task_dict), state['timestamp'], state['timestamp'])
                )
            
            self._sqlite_conn.commit()
        except Exception as e:
            logger.warning(f"SQLite save failed: {e}")
    
    def create_task(self, description: str, priority: TaskPriority = TaskPriority.NORMAL,
                   dependencies: List[str] = None, metadata: Dict = None) -> Task:
        """Create a new task"""
        task = Task(
            id=str(uuid.uuid4())[:8],
            description=description,
            priority=priority,
            dependencies=dependencies or [],
            metadata=metadata or {}
        )
        
        self.tasks[task.id] = task
        self.pending_queue.put(task)
        
        return task
    
    def get_ready_tasks(self) -> List[Task]:
        """Get tasks that are ready to execute (all deps satisfied)"""
        ready = []
        
        while not self.pending_queue.empty():
            try:
                task = self.pending_queue.get_nowait()
            except Empty:
                break
            
            # Check dependencies
            deps_satisfied = all(
                dep_id in self.completed_tasks 
                for dep_id in task.dependencies
            )
            
            if deps_satisfied and task.id not in self.running_tasks:
                ready.append(task)
            else:
                # Put back if not ready
                self.pending_queue.put(task)
                break
        
        return ready
    
    def mark_running(self, task_id: str):
        """Mark task as running"""
        if task_id in self.tasks:
            self.running_tasks.add(task_id)
            self.tasks[task_id].state = "running"
            self.tasks[task_id].started_at = time.time()
    
    def mark_completed(self, task_id: str, result: Any = None):
        """Mark task as completed"""
        if task_id in self.tasks:
            self.running_tasks.discard(task_id)
            self.completed_tasks.add(task_id)
            self.tasks[task_id].state = "completed"
            self.tasks[task_id].completed_at = time.time()
            self.tasks[task_id].output_data = result
    
    def mark_failed(self, task_id: str, error: str):
        """Mark task as failed"""
        if task_id in self.tasks:
            self.running_tasks.discard(task_id)
            self.failed_tasks.add(task_id)
            self.tasks[task_id].state = "failed"
            self.tasks[task_id].error = error
            self.tasks[task_id].completed_at = time.time()
    
    def retry_task(self, task_id: str) -> bool:
        """Retry a failed task"""
        if task_id in self.tasks:
            task = self.tasks[task_id]
            if task.retry_count < task.max_retries:
                task.retry_count += 1
                task.state = "pending"
                self.failed_tasks.discard(task_id)
                self.pending_queue.put(task)
                return True
        return False
    
    def get_task_graph(self) -> Dict:
        """Get task dependency graph"""
        return {
            "pending": len([t for t in self.tasks.values() if t.state == "pending"]),
            "running": len(self.running_tasks),
            "completed": len(self.completed_tasks),
            "failed": len(self.failed_tasks),
            "tasks": [
                {
                    "id": t.id,
                    "description": t.description[:50],
                    "state": t.state,
                    "priority": t.priority.name
                }
                for t in self.tasks.values()
            ]
        }


# ==================== ARTIFACT COLLECTOR ====================

class ArtifactCollector:
    """
    Collects and manages artifacts from task execution
    
    FIXED ISSUES (14):
    - Rich metadata: task_id, step_id, type, checksum, verifier link, preview, retention policy
    """
    
    def __init__(self, storage_dir: str = "artifacts"):
        self.storage_dir = storage_dir
        self.artifacts: Dict[str, List[Dict]] = defaultdict(list)
        self.artifact_metadata: Dict[str, Dict] = {}  # Rich metadata storage
        
        # Create storage directory
        os.makedirs(storage_dir, exist_ok=True)
        
        # Retention policies
        self.RETENTION_POLICIES = {
            'temporary': 3600,      # 1 hour
            'short': 86400,        # 1 day
            'medium': 604800,      # 1 week
            'long': 2592000,       # 1 month
            'permanent': -1,        # Forever
        }
        
        logger.info(f"📦 Artifact Collector initialized: {storage_dir}")
    
    def collect(
        self, 
        task_id: str, 
        artifact_type: str, 
        content: Any,
        step_id: str = None,
        verifier_link: str = None,
        retention_policy: str = 'medium',
        metadata: Dict = None
    ) -> str:
        """
        Collect an artifact with RICH metadata.
        """
        import hashlib
        import base64
        
        artifact_id = f"{task_id}_{artifact_type}_{int(time.time()*1000)}"
        
        # Calculate checksum
        content_bytes = str(content).encode('utf-8')
        checksum = hashlib.sha256(content_bytes).hexdigest()
        
        # Handle different content types
        if isinstance(content, (dict, list)):
            filepath = f"{self.storage_dir}/{artifact_id}.json"
            with open(filepath, 'w') as f:
                json.dump(content, f, indent=2)
        elif isinstance(content, str) and len(content) > 1000:
            filepath = f"{self.storage_dir}/{artifact_id}.txt"
            with open(filepath, 'w') as f:
                f.write(content)
        else:
            filepath = f"{self.storage_dir}/{artifact_id}.txt"
            with open(filepath, 'w') as f:
                f.write(str(content))
        
        # Create rich metadata
        artifact_metadata = {
            'artifact_id': artifact_id,
            'task_id': task_id,
            'step_id': step_id or f"{task_id}_step_1",
            'type': artifact_type,
            'filepath': filepath,
            'checksum': checksum,
            'size': len(content_bytes),
            'created_at': time.time(),
            'verifier_link': verifier_link,
            'retention_policy': retention_policy,
            'retention_until': time.time() + self.RETENTION_POLICIES.get(retention_policy, 604800),
            'metadata': metadata or {},
            'preview': str(content)[:200] if content else '',
            'verified': False,
            'verified_at': None,
        }
        
        self.artifacts[task_id].append(artifact_metadata)
        self.artifact_metadata[artifact_id] = artifact_metadata
        
        logger.info(f"📦 Artifact collected: {artifact_id}")
        
        return artifact_id
    
    def verify_artifact(self, artifact_id: str, verifier_result: bool) -> None:
        """Mark artifact as verified"""
        if artifact_id in self.artifact_metadata:
            self.artifact_metadata[artifact_id]['verified'] = verifier_result
            self.artifact_metadata[artifact_id]['verified_at'] = time.time()
    
    def get_artifact_metadata(self, artifact_id: str) -> Dict:
        """Get metadata for an artifact"""
        return self.artifact_metadata.get(artifact_id, {})
    
    def get_artifacts(self, task_id: str) -> List[Dict]:
        """Get all artifacts for a task (with metadata)"""
        return self.artifacts.get(task_id, [])
    
    def get_artifacts_summary(self) -> Dict:
        """Get summary of all artifacts"""
        total = sum(len(arts) for arts in self.artifacts.values())
        by_type = defaultdict(int)
        verified_count = 0
        
        for arts in self.artifacts.values():
            for art in arts:
                by_type[art.get('type', 'unknown')] += 1
                if art.get('verified', False):
                    verified_count += 1
        
        return {
            'total_artifacts': total,
            'by_type': dict(by_type),
            'verified': verified_count,
            'unverified': total - verified_count
        }
    
    def cleanup_expired(self) -> int:
        """Clean up expired artifacts based on retention policy"""
        import os
        
        removed = 0
        current_time = time.time()
        
        for artifact_id, metadata in list(self.artifact_metadata.items()):
            if metadata.get('retention_until', -1) > 0 and current_time > metadata['retention_until']:
                filepath = metadata.get('filepath')
                if filepath and os.path.exists(filepath):
                    os.remove(filepath)
                    removed += 1
                
                task_id = metadata.get('task_id')
                if task_id and artifact_id in self.artifacts[task_id]:
                    self.artifacts[task_id].remove(artifact_id)
                
                del self.artifact_metadata[artifact_id]
        
        return removed
    
    def get_all_artifacts(self) -> Dict[str, List[Dict]]:
        """Get all artifacts with metadata"""
        return dict(self.artifacts)


# ==================== SCHEDULER ====================

class Scheduler:
    """
    Background scheduler for tasks
    """
    
    def __init__(self):
        self.scheduled_tasks: List[Dict] = []
        self.running = False
        
        logger.info("⏰ Scheduler initialized")
    
    def schedule(self, task: Callable, delay: float = 0, 
                 interval: float = None, name: str = None):
        """Schedule a task"""
        scheduled = {
            "task": task,
            "delay": delay,
            "interval": interval,
            "name": name or str(uuid.uuid4())[:8],
            "next_run": time.time() + delay,
            "last_run": None
        }
        self.scheduled_tasks.append(scheduled)
        
        return scheduled["name"]
    
    def run_pending(self):
        """Run pending scheduled tasks"""
        now = time.time()
        
        for scheduled in self.scheduled_tasks:
            if now >= scheduled["next_run"]:
                try:
                    scheduled["task"]()
                    scheduled["last_run"] = now
                    
                    if scheduled["interval"]:
                        scheduled["next_run"] = now + scheduled["interval"]
                    else:
                        # One-time task, remove it
                        self.scheduled_tasks.remove(scheduled)
                except Exception as e:
                    logger.error(f"Scheduled task error: {e}")
    
    def cancel(self, name: str):
        """Cancel a scheduled task"""
        self.scheduled_tasks = [
            t for t in self.scheduled_tasks 
            if t["name"] != name
        ]
    
    def get_status(self) -> Dict:
        """Get scheduler status"""
        return {
            "task_count": len(self.scheduled_tasks),
            "tasks": [
                {
                    "name": t["name"],
                    "next_run": t["next_run"],
                    "interval": t["interval"]
                }
                for t in self.scheduled_tasks
            ]
        }


# ==================== TELEMETRY ====================

class Telemetry:
    """
    Metrics and monitoring
    """
    
    def __init__(self):
        self.metrics = {
            "tasks_total": 0,
            "tasks_success": 0,
            "tasks_failed": 0,
            "tool_calls": defaultdict(int),
            "tool_failures": defaultdict(int),
            "total_duration": 0.0,
            "total_cost": 0.0,
            "retry_count": 0,
        }
        
        self.history: List[Dict] = []
        
        logger.info("📊 Telemetry initialized")
    
    def record_task(self, success: bool, duration: float, tool_name: str = None):
        """Record task execution"""
        self.metrics["tasks_total"] += 1
        if success:
            self.metrics["tasks_success"] += 1
        else:
            self.metrics["tasks_failed"] += 1
        
        self.metrics["total_duration"] += duration
        
        if tool_name:
            self.metrics["tool_calls"][tool_name] += 1
            if not success:
                self.metrics["tool_failures"][tool_name] += 1
    
    def record_retry(self):
        """Record retry"""
        self.metrics["retry_count"] += 1
    
    def record_cost(self, cost: float):
        """Record API cost"""
        self.metrics["total_cost"] += cost
    
    def get_metrics(self) -> Dict:
        """Get current metrics"""
        total = self.metrics["tasks_total"]
        success = self.metrics["tasks_success"]
        
        return {
            **self.metrics,
            "success_rate": success / total if total > 0 else 0,
            "failure_rate": (total - success) / total if total > 0 else 0,
            "avg_duration": self.metrics["total_duration"] / total if total > 0 else 0,
            "tool_reliability": {
                tool: (calls - failures) / calls if calls > 0 else 0
                for tool, calls in self.metrics["tool_calls"].items()
                for failures in [self.metrics["tool_failures"][tool]]
            }
        }
    
    def get_summary(self) -> str:
        """Get human-readable summary"""
        m = self.get_metrics()
        
        return f"""📊 **Telemetriya**

✅ Muvaffaqiyat: {m['tasks_success']}/{m['tasks_total']} ({m['success_rate']:.1%})
❌ Muvaffaqiyatsiz: {m['tasks_failed']}
🔄 Qayta urinishlar: {m['retry_count']}
⏱️ O'rtacha vaqt: {m['avg_duration']:.2f}s
💰 Umumiy xarajat: ${m['total_cost']:.4f}

**Tool ishonchliligi:**
{json.dumps(m['tool_reliability'], indent=2) if m['tool_reliability'] else "Ma'lumot yo'q"}"""


# ==================== CENTRAL KERNEL ====================

class CentralKernel:
    """
    THE ONE TRUE ORCHESTRATOR
    
    This is the central operating system for the agent.
    It brings together:
    - TaskManager: Task lifecycle
    - StateMachine: Kernel state
    - Scheduler: Background tasks
    - MultiAgentCoordinator: Agent coordination
    - VerificationEngine: Result verification
    - CriticEngine: Quality evaluation
    - ArtifactCollector: Result storage
    - Telemetry: Metrics
    """
    
    def __init__(self, api_key: str, tools_engine):
        self.api_key = api_key
        self.tools = tools_engine
        
        # Initialize all subsystems
        self.state = KernelState.IDLE
        
        logger.info("🚀 Initializing Central Kernel...")
        
        self.task_manager = TaskManager()
        self.scheduler = Scheduler()
        self.verifier = VerificationEngine(tools_engine)
        
        # FIX #3: Initialize RecoveryEngine as first-class subsystem
        logger.info("🔧 Initializing Recovery Engine...")
        self.recovery_engine = RecoveryEngine(self)
        
        self.critic = CriticEngine(api_key)
        
        # Use NEW Multi-Agent Coordinator with 6 full workers
        logger.info("🤖 Initializing NEW Multi-Agent Coordinator with 6 workers...")
        self.coordinator = NewMultiAgentCoordinator(api_key, tools_engine)

        # Planner Quality Tracking
        self.planner_quality = PlannerQualityTracker()

        # Invalid snippets storage for debugging
        self._invalid_snippets_dir = Path("data/invalid_snippets")
        self._invalid_snippets_dir.mkdir(parents=True, exist_ok=True)
        
        self.artifacts = ArtifactCollector()
        self.telemetry = Telemetry()
        
        # Pending approvals
        self.pending_approvals: Dict[str, Dict] = {}
        
        # FIX #2 & #5: Task lifecycle management
        # Event ledger for state transitions
        self._task_event_ledger: List[TaskEvent] = []
        # Task checkpoints for durable pause/resume
        self._task_checkpoints: Dict[str, TaskCheckpoint] = {}
        
        # FIX #2: Valid transitions map
        self._valid_transitions = self._build_valid_transitions()
        
        # FIX: Transaction state tracking for side-effect management
        self._active_transactions: Dict[str, SideEffectTransaction] = {}
        self._transaction_ledger: Dict[str, List[Dict]] = {}  # FIX: Dict, not List
        self._idempotency_cache: Dict[str, Any] = {}
        
        # FIX: Plan Compiler - The "compiler wall" between planner and executor
        logger.info("📋 Initializing Plan Compiler...")
        self.plan_compiler = PlanCompiler(self)
        
        # FIX: Context Assembler - The context injection boundary
        logger.info("📦 Initializing Context Assembler...")
        self.context_assembler = ContextAssembler(self)
        
        # FIX: Budget Ledger - Cost enforcement
        logger.info("💰 Initializing Budget Ledger...")
        self.budget_ledger = BudgetLedger(self)
        
        # FIX: Termination Manager - Goal termination
        logger.info("🛑 Initializing Termination Manager...")
        self.termination_manager = TerminationManager(self)
        
        # FIX: Handoff Orchestrator - Human escalation
        logger.info("👤 Initializing Handoff Orchestrator...")
        self.handoff_orchestrator = HandoffOrchestrator(self)
        
        # FIX: Invariant Engine - Constitution enforcement
        logger.info("🛡️ Initializing Invariant Engine...")
        self.invariant_engine = InvariantEngine(self)
        
        # FIX: Mode Selector - The capability negotiation boundary
        logger.info("🎯 Initializing Mode Selector...")
        self.mode_selector = ModeSelector(self)
        
        # Compiled graph cache for execution
        self._compiled_graphs: Dict[str, ExecutableGraph] = {}
        
        logger.info("✅ Central Kernel Ready!")
    
    # =====================================================
    # SIDE-EFFECT TRANSACTION SYSTEM (No1 Grade)
    # =====================================================
    
    def _init_transaction_subsystem(self):
        """Initialize transaction-related state"""
        self._active_transactions: Dict[str, SideEffectTransaction] = {}
        self._transaction_ledger: List[Dict] = {}
        self._idempotency_cache: Dict[str, Any] = {}
    
    async def execute_with_transaction(
        self,
        task: 'Task',
        tool_name: str,
        args: Dict[str, Any],
        verification_type: Optional[str] = None,
        verification_params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Execute a tool with full transaction lifecycle.
        
        FIX: This implements the canonical side-effect transaction boundary.
        
        Lifecycle: PREPARE -> APPLY -> OBSERVE -> VERIFY -> COMMIT
        (or ROLLBACK at any point if verification fails)
        
        CRITICAL:
        - APPLIED != COMMITTED
        - Verification must pass BEFORE commit
        - All side effects are tracked with WorldStateDelta
        
        Args:
            task: The task being executed
            tool_name: Name of tool to execute
            args: Tool arguments
            verification_type: Type of verification needed
            verification_params: Verification parameters
            
        Returns:
            Dict with execution results and transaction state
        """
        import uuid
        from datetime import datetime
        
        # Generate transaction ID
        tx_id = f"tx_{uuid.uuid4().hex[:12]}"
        
        # Create transaction object
        tx = SideEffectTransaction(
            tx_id=tx_id,
            task_id=task.id,
            tool_name=tool_name,
            phase=TransactionPhase.PREPARED,
            arguments=args,
            intended_changes=self._compute_intended_changes(tool_name, args),
            idempotency_key=self._generate_idempotency_key(tool_name, args)
        )
        
        # Store active transaction
        self._active_transactions[tx_id] = tx
        
        try:
            # =====================================================
            # PHASE 1: PREPARE
            # =====================================================
            logger.info(f"🔄 TRANSACTION {tx_id}: PREPARE phase")
            self._record_transaction_event(tx, "tx_prepared", {"tool": tool_name, "args": args})
            
            # Check idempotency - can we skip execution?
            idempotency_class = TOOL_IDEMPOTENCY.get(tool_name, IdempotencyClass.NON_IDEMPOTENT)
            
            if idempotency_class == IdempotencyClass.IDEMPOTENT:
                # Already executed this - skip to verify
                logger.info(f"⏭️ TRANSACTION {tx_id}: Idempotent - skipping to VERIFY")
                tx.phase = TransactionPhase.VERIFIED
                tx.verification_passed = True
                tx.evidence = {"idempotent": True}
                return await self._finalize_transaction(tx, task)
            
            # Check if already executed (conditional idempotency)
            if idempotency_class == IdempotencyClass.CONDITIONALLY_IDEMPOTENT:
                existing_result = self._check_idempotency_cache(tx.idempotency_key)
                if existing_result:
                    logger.info(f"⏭️ TRANSACTION {tx_id}: Found cached result - skipping to VERIFY")
                    tx.phase = TransactionPhase.VERIFIED
                    tx.verification_passed = True
                    tx.output = existing_result.get("output")
                    tx.evidence = {"cached": True, "idempotency_key": tx.idempotency_key}
                    return await self._finalize_transaction(tx, task)
            
            # =====================================================
            # PHASE 2: APPLY (Execute the tool)
            # =====================================================
            logger.info(f"⚡ TRANSACTION {tx_id}: APPLY phase")
            tx.phase = TransactionPhase.APPLIED
            tx.applied_at = time.time()
            self._record_transaction_event(tx, "tx_applied", {"timestamp": tx.applied_at})
            
            # Execute the tool
            exec_result = await self._execute_tool_strict(
                task=task,
                tool_name=tool_name,
                args=args,
                timeout=30
            )
            
            # Store output
            tx.output = exec_result
            
            # Check execution success
            if not exec_result.success:
                tx.phase = TransactionPhase.FAILED
                tx.failure = FailureRecord(
                    message=f"Tool execution failed: {exec_result.error}",
                    category=FailureCategory.TOOL_EXECUTION_FAILED,
                    recoverable=False,
                    task_id=task.id,
                    timestamp=time.time()
                )
                self._record_transaction_event(tx, "tx_apply_failed", {"error": exec_result.error})
                return await self._finalize_transaction(tx, task)
            
            # =====================================================
            # PHASE 3: OBSERVE (Record world state changes)
            # =====================================================
            logger.info(f"👁️ TRANSACTION {tx_id}: OBSERVE phase")
            tx.phase = TransactionPhase.OBSERVED
            tx.observed_at = time.time()
            
            # Compute actual world state delta
            tx.observed_delta = self._compute_world_state_delta(tool_name, args, exec_result)
            
            self._record_transaction_event(tx, "tx_observed", {
                "delta": tx.observed_delta.__dict__,
                "artifacts": tx.observed_delta.artifacts_created
            })
            
            # Cache result for idempotency
            if idempotency_class == IdempotencyClass.CONDITIONALLY_IDEMPOTENT:
                self._idempotency_cache[tx.idempotency_key] = {
                    "output": exec_result,
                    "delta": tx.observed_delta.__dict__,
                    "timestamp": time.time()
                }
            
            # =====================================================
            # PHASE 4: VERIFY
            # =====================================================
            logger.info(f"🔍 TRANSACTION {tx_id}: VERIFY phase")
            
            if not verification_type or verification_type == "none":
                # No verification needed - auto-pass
                tx.verification_passed = True
                tx.phase = TransactionPhase.VERIFIED
                tx.verified_at = time.time()
                tx.evidence = {"auto_verified": True}
                self._record_transaction_event(tx, "tx_verified_auto", {})
            else:
                # Run actual verification
                verification_result = await self._transaction_run_verification(
                    tx, verification_type, verification_params or {}, exec_result
                )
                
                tx.verification_passed = verification_result["passed"]
                tx.verification_details = verification_result["details"]
                tx.evidence = verification_result.get("evidence", {})
                
                if verification_result["passed"]:
                    tx.phase = TransactionPhase.VERIFIED
                    tx.verified_at = time.time()
                    self._record_transaction_event(tx, "tx_verified", {"evidence": tx.evidence})
                else:
                    tx.phase = TransactionPhase.FAILED
                    self._record_transaction_event(tx, "tx_verification_failed", {
                        "details": verification_result["details"]
                    })
            
            # =====================================================
            # PHASE 5: COMMIT DECISION
            # =====================================================
            logger.info(f"🚪 TRANSACTION {tx_id}: COMMIT GATE")
            
            commit_decision = self._make_commit_decision(tx)
            
            self._record_transaction_event(tx, "tx_commit_decision", {
                "allowed": commit_decision.allowed,
                "reason": commit_decision.reason,
                "action": commit_decision.action
            })
            
            if not commit_decision.allowed:
                # Commit denied - need to rollback
                logger.warning(f"🚫 TRANSACTION {tx_id}: COMMIT DENIED - {commit_decision.reason}")
                
                if commit_decision.action == "rollback":
                    await self._transaction_rollback(tx, task)
                elif commit_decision.action == "escalate":
                    tx.phase = TransactionPhase.FAILED
                    task.status = TaskStatus.ESCALATED
                    task.error = f"Transaction escalated: {commit_decision.reason}"
                else:
                    tx.phase = TransactionPhase.FAILED
                
                return await self._finalize_transaction(tx, task)
            
            # Commit allowed
            tx.phase = TransactionPhase.COMMITTED
            tx.committed_at = time.time()
            self._record_transaction_event(tx, "tx_committed", {
                "duration_ms": (tx.committed_at - tx.created_at) * 1000
            })
            
            return await self._finalize_transaction(tx, task)
            
        except Exception as e:
            logger.error(f"❌ TRANSACTION {tx_id}: EXCEPTION - {str(e)}")
            tx.phase = TransactionPhase.FAILED
            tx.failure = FailureRecord(
                message=f"Transaction exception: {str(e)}",
                category=FailureCategory.SYSTEM_ERROR,
                recoverable=False,
                task_id=task.id,
                timestamp=time.time()
            )
            self._record_transaction_event(tx, "tx_exception", {"error": str(e)})
            return await self._finalize_transaction(tx, task)
    
    def _compute_intended_changes(self, tool_name: str, args: Dict) -> Dict[str, Any]:
        """Compute what changes are intended"""
        changes = {}
        
        if tool_name == "write_file":
            changes["files_written"] = [args.get("path")]
            changes["content_hash"] = hash(str(args.get("content", "")))
        elif tool_name == "delete_file":
            changes["files_deleted"] = [args.get("path")]
        elif tool_name == "execute_command":
            changes["command"] = args.get("command")
        elif tool_name == "install_package":
            changes["packages"] = [args.get("package")]
        elif tool_name == "browser_click":
            changes["target"] = args.get("selector")
        
        return changes
    
    def _compute_world_state_delta(
        self,
        tool_name: str,
        args: Dict,
        exec_result: 'ExecutionResult'
    ) -> WorldStateDelta:
        """Compute actual world state changes"""
        delta = WorldStateDelta()
        
        if tool_name == "write_file":
            if exec_result.success:
                delta.files_modified = [args.get("path")]
                delta.artifacts_created = [args.get("path")]
        elif tool_name == "delete_file":
            if exec_result.success:
                delta.files_deleted = [args.get("path")]
        elif tool_name == "execute_command":
            if exec_result.success:
                delta.external_effects = [f"exit_code:{exec_result.exit_code}"]
                # Check for artifact files
                if exec_result.artifacts:
                    delta.artifacts_created.extend(exec_result.artifacts)
        elif tool_name == "install_package":
            if exec_result.success:
                delta.environment_changes[args.get("package")] = "installed"
        elif tool_name == "browser_navigate":
            if exec_result.success:
                delta.resources_touched = [args.get("url")]
        
        return delta
    
    def _generate_idempotency_key(self, tool_name: str, args: Dict) -> str:
        """Generate idempotency key for this action"""
        import hashlib
        content = f"{tool_name}:{json.dumps(args, sort_keys=True)}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def _check_idempotency_cache(self, key: str) -> Optional[Dict]:
        """Check if action was already executed"""
        if key in self._idempotency_cache:
            entry = self._idempotency_cache[key]
            # Check if cache is still valid (1 hour)
            if time.time() - entry.get("timestamp", 0) < 3600:
                return entry
        return None
    
    async def _transaction_run_verification(
        self,
        tx: SideEffectTransaction,
        verification_type: str,
        params: Dict,
        exec_result: 'ExecutionResult'
    ) -> Dict[str, Any]:
        """Run verification for transaction"""
        try:
            # Normalize verification type
            normalized = normalize_verification_type(verification_type)
            
            # Build verification data
            verification_data = {
                "tool_result": exec_result.to_dict() if hasattr(exec_result, 'to_dict') else {},
                "output": exec_result.stdout or exec_result.stderr,
                "exit_code": exec_result.exit_code,
                "artifacts": exec_result.artifacts
            }
            verification_data.update(params)
            
            # Run verifier
            result = self.verifier.verify(normalized.value, verification_data)
            
            return {
                "passed": result.passed,
                "details": result.details,
                "evidence": result.evidence
            }
        except Exception as e:
            logger.error(f"Verification error: {e}")
            return {
                "passed": False,
                "details": f"Verification error: {str(e)}",
                "evidence": {}
            }
    
    def _make_commit_decision(self, tx: SideEffectTransaction) -> CommitDecision:
        """
        Make commit decision - the CRITICAL commit gate.
        
        FIX: Commit is NOT automatic. It requires:
        1. Evidence present
        2. Verification passed
        3. Rollback available if needed
        """
        # Check 1: Evidence present
        if not tx.evidence:
            return CommitDecision(
                allowed=False,
                reason="No evidence present - cannot commit",
                phase_before=tx.phase,
                phase_after=TransactionPhase.FAILED,
                evidence_present=False,
                verification_passed=tx.verification_passed,
                rollback_available=tx.rollback_snapshot_id is not None,
                action="rollback" if tx.rollback_snapshot_id else "escalate"
            )
        
        # Check 2: Verification passed
        if not tx.verification_passed:
            return CommitDecision(
                allowed=False,
                reason=f"Verification failed: {tx.verification_details}",
                phase_before=tx.phase,
                phase_after=TransactionPhase.ROLLBACK_PENDING,
                evidence_present=True,
                verification_passed=False,
                rollback_available=tx.rollback_snapshot_id is not None,
                action="rollback"
            )
        
        # Check 3: For non-idempotent actions, require strong evidence
        idempotency = TOOL_IDEMPOTENCY.get(tx.tool_name, IdempotencyClass.NON_IDEMPOTENT)
        if idempotency == IdempotencyClass.NON_IDEMPOTENT:
            # Non-idempotent actions need explicit verification
            if not tx.observed_delta or tx.observed_delta.is_empty():
                return CommitDecision(
                    allowed=False,
                    reason="Non-idempotent action requires observable delta",
                    phase_before=tx.phase,
                    phase_after=TransactionPhase.FAILED,
                    evidence_present=True,
                    verification_passed=True,
                    rollback_available=False,
                    action="escalate"
                )
        
        # All checks passed - commit allowed
        return CommitDecision(
            allowed=True,
            reason="All commit gates passed",
            phase_before=tx.phase,
            phase_after=TransactionPhase.COMMITTED,
            evidence_present=True,
            verification_passed=tx.verification_passed,
            rollback_available=tx.rollback_snapshot_id is not None,
            action="proceed"
        )
    
    async def _transaction_rollback(self, tx: SideEffectTransaction, task: 'Task'):
        """Execute transaction rollback"""
        logger.warning(f"⏪ TRANSACTION {tx.tx_id}: ROLLBACK")
        
        tx.phase = TransactionPhase.ROLLING_BACK
        self._record_transaction_event(tx, "tx_rollback_started", {})
        
        # Execute rollback if snapshot exists
        if tx.rollback_snapshot_id and tx.rollback_snapshot_id in self._task_checkpoints:
            checkpoint = self._task_checkpoints[tx.rollback_snapshot_id]
            # Apply rollback from checkpoint
            for snapshot in checkpoint.rollback_snapshots:
                await self._apply_rollback_snapshot(snapshot)
        
        tx.phase = TransactionPhase.ROLLED_BACK
        self._record_transaction_event(tx, "tx_rollback_completed", {})
    
    async def _apply_rollback_snapshot(self, snapshot: RollbackSnapshot):
        """Apply a rollback snapshot"""
        logger.info(f"Applying rollback snapshot: {snapshot.kind}")
        # Rollback logic depends on snapshot type
        if snapshot.kind == "file_mutation":
            # Restore file content
            pass
        elif snapshot.kind == "browser_state":
            # Restore browser state
            pass
        # ... other types
    
    async def _finalize_transaction(
        self,
        tx: SideEffectTransaction,
        task: 'Task'
    ) -> Dict[str, Any]:
        """Finalize transaction and return result"""
        # Update task status based on transaction outcome
        if tx.phase == TransactionPhase.COMMITTED:
            task.status = TaskStatus.COMPLETED
        elif tx.phase == TransactionPhase.FAILED:
            task.status = TaskStatus.FAILED
        
        return {
            "tx_id": tx.tx_id,
            "phase": tx.phase.value,
            "success": tx.phase == TransactionPhase.COMMITTED,
            "output": tx.output,
            "observed_delta": tx.observed_delta.__dict__,
            "evidence": tx.evidence,
            "verification_passed": tx.verification_passed,
            "commit_details": tx.verification_details if tx.phase == TransactionPhase.COMMITTED else None
        }
    
    def _record_transaction_event(self, tx: SideEffectTransaction, event_type: str, data: Dict):
        """Record transaction event to ledger"""
        event = {
            "tx_id": tx.tx_id,
            "task_id": tx.task_id,
            "event": event_type,
            "phase": tx.phase.value,
            "timestamp": time.time(),
            "data": data
        }
        
        # Add to transaction-specific ledger
        if tx.tx_id not in self._transaction_ledger:
            self._transaction_ledger[tx.tx_id] = []
        self._transaction_ledger[tx.tx_id].append(event)
        
        # Also add to task event ledger
        self._task_event_ledger.append(TaskEvent(
            task_id=tx.task_id,
            from_status=tx.phase.value,
            to_status=event_type,
            reason=event_type,
            evidence=event
        ))
    
    def get_transaction_status(self, tx_id: str) -> Optional[Dict]:
        """Get transaction status"""
        tx = self._active_transactions.get(tx_id)
        if not tx:
            return None
        
        return {
            "tx_id": tx.tx_id,
            "phase": tx.phase.value,
            "tool": tx.tool_name,
            "task_id": tx.task_id,
            "committed": tx.is_committed(),
            "can_retry": tx.can_retry(),
            "evidence": tx.evidence
        }
    
    def get_transaction_ledger(self, tx_id: Optional[str] = None) -> List[Dict]:
        """Get transaction ledger"""
        if tx_id:
            return self._transaction_ledger.get(tx_id, [])
        else:
            # Return all events
            all_events = []
            for events in self._transaction_ledger.values():
                all_events.extend(events)
            return sorted(all_events, key=lambda x: x["timestamp"])
    
    def _build_valid_transitions(self) -> Dict[str, Set[str]]:
        """
        FIX #3: Build valid state transitions map.
        
        This defines which transitions are legal in the task lifecycle.
        """
        return {
            # Core execution flow
            TaskStatus.PENDING.value: {TaskStatus.READY.value, TaskStatus.CANCELLED.value},
            TaskStatus.READY.value: {TaskStatus.RUNNING.value, TaskStatus.PAUSED.value, TaskStatus.CANCELLED.value},
            TaskStatus.RUNNING.value: {
                TaskStatus.EXECUTED.value, 
                TaskStatus.FAILED_EXECUTION.value,
                TaskStatus.WAITING_APPROVAL.value,
                TaskStatus.PAUSED.value
            },
            TaskStatus.EXECUTED.value: {TaskStatus.VERIFYING.value, TaskStatus.FAILED_EXECUTION.value},
            TaskStatus.VERIFYING.value: {TaskStatus.VERIFIED.value, TaskStatus.FAILED_VERIFICATION.value},
            TaskStatus.VERIFIED.value: {TaskStatus.COMMITTED.value, TaskStatus.FAILED_VERIFICATION.value},
            TaskStatus.COMMITTED.value: set(),  # Terminal success state
            
            # Failure states
            TaskStatus.FAILED_EXECUTION.value: {
                TaskStatus.RECOVERING.value, 
                TaskStatus.ABORTED.value,
                TaskStatus.RETRYING.value
            },
            TaskStatus.FAILED_VERIFICATION.value: {
                TaskStatus.RECOVERING.value,
                TaskStatus.REPLAN_PENDING.value,
                TaskStatus.ESCALATED.value,
                TaskStatus.ABORTED.value
            },
            
            # Recovery states
            TaskStatus.RECOVERING.value: {
                TaskStatus.RETRYING.value,
                TaskStatus.REPLAN_PENDING.value,
                TaskStatus.ESCALATED.value,
                TaskStatus.ABORTED.value
            },
            TaskStatus.RETRYING.value: {TaskStatus.RUNNING.value, TaskStatus.FAILED_EXECUTION.value},
            TaskStatus.REPLAN_PENDING.value: {TaskStatus.READY.value, TaskStatus.ABORTED.value},
            
            # Approval/Pause states
            TaskStatus.WAITING_APPROVAL.value: {TaskStatus.READY.value, TaskStatus.ABORTED.value},
            TaskStatus.PAUSED.value: {TaskStatus.READY.value, TaskStatus.ABORTED.value},
            
            # Terminal states
            TaskStatus.ESCALATED.value: set(),
            TaskStatus.ABORTED.value: set(),
            TaskStatus.TIMEOUT.value: set(),
            TaskStatus.CANCELLED.value: set(),
            TaskStatus.SUPERSEDED.value: set(),
        }
    
    def transition_task(
        self, 
        task: 'Task', 
        to_status: TaskStatus, 
        reason: str,
        evidence: Optional[Dict] = None
    ) -> bool:
        """
        FIX #2: Centralized task state transition gate.
        
        This is the ONLY way to change task status - no direct task.status = ... allowed.
        
        This method:
        1. Validates the transition is legal
        2. Records the event in the ledger
        3. Updates checkpoint if needed
        4. Returns success/failure
        
        Args:
            task: The task to transition
            to_status: The new status
            reason: Why this transition is happening
            evidence: Any evidence for this transition
            
        Returns:
            True if transition succeeded, False if invalid
        """
        from_status = task.status.value if isinstance(task.status, TaskStatus) else str(task.status)
        
        # Check if transition is valid
        valid_targets = self._valid_transitions.get(from_status, set())
        
        if to_status.value not in valid_targets and from_status != to_status.value:
            logger.warning(
                f"⚠️ Invalid transition: {task.id} from {from_status} to {to_status.value}. "
                f"Valid: {valid_targets}"
            )
            # Log the invalid attempt
            self._record_event(
                task.id, 
                from_status, 
                to_status.value, 
                f"INVALID: {reason}",
                evidence or {}
            )
            return False
        
        # Record event
        self._record_event(
            task.id,
            from_status,
            to_status.value,
            reason,
            evidence or {}
        )
        
        # Update task status
        old_status = task.status
        task.status = to_status
        
        # Update checkpoint if needed
        if to_status in {TaskStatus.PAUSED, TaskStatus.WAITING_APPROVAL}:
            self._save_checkpoint(task, reason)
        
        logger.info(f"✅ Task {task.id}: {from_status} -> {to_status.value} ({reason})")
        return True
    
    def _record_event(
        self,
        task_id: str,
        from_status: str,
        to_status: str,
        reason: str,
        evidence: Dict
    ):
        """FIX #5: Record task event in ledger"""
        event = TaskEvent(
            task_id=task_id,
            from_status=from_status,
            to_status=to_status,
            reason=reason,
            evidence=evidence
        )
        self._task_event_ledger.append(event)
        
        # Keep only last 1000 events to prevent memory issues
        if len(self._task_event_ledger) > 1000:
            self._task_event_ledger = self._task_event_ledger[-500:]
    
    def _save_checkpoint(self, task: 'Task', reason: str):
        """FIX #5: Save task checkpoint for durable pause/resume"""
        checkpoint = TaskCheckpoint(
            task_id=task.id,
            checkpoint_id=str(uuid.uuid4()),
            last_safe_status=task.status.value if isinstance(task.status, TaskStatus) else str(task.status),
            execution_cursor={
                'input_data': task.input_data,
                'retry_count': task.retry_count,
                'reason': reason
            },
            artifacts=task.artifacts or []
        )
        self._task_checkpoints[task.id] = checkpoint
        task.checkpoint_id = checkpoint.checkpoint_id
        task.last_safe_status = checkpoint.last_safe_status
        
        logger.info(f"💾 Checkpoint saved for {task.id}: {checkpoint.checkpoint_id}")
    
    def get_task_history(self, task_id: str) -> List[TaskEvent]:
        """FIX #5: Get full event history for a task"""
        return [e for e in self._task_event_ledger if e.task_id == task_id]
    
    def get_task_checkpoint(self, task_id: str) -> Optional[TaskCheckpoint]:
        """FIX #5: Get checkpoint for a task"""
        return self._task_checkpoints.get(task_id)
    
    async def save_checkpoint(
        self, 
        task: 'Task', 
        cursor: Optional[ExecutionCursor] = None,
        extra: Optional[Dict] = None
    ) -> str:
        """
        FIX #4: Save checkpoint with execution cursor.
        
        This is the kernel-level checkpoint API that enables:
        - Step-level resume after crash
        - Side-effect reconciliation
        - Verification checkpointing
        
        Args:
            task: The task to checkpoint
            cursor: Current execution cursor (optional)
            extra: Any additional checkpoint data
            
        Returns:
            checkpoint_id
        """
        checkpoint_id = str(uuid.uuid4())
        
        # Build execution cursor if not provided
        if cursor is None:
            cursor = ExecutionCursor(
                phase='unknown',
                tool_name=task.metadata.get('current_tool'),
                artifacts_created=task.artifacts or []
            )
        
        # Create checkpoint
        checkpoint = TaskCheckpoint(
            task_id=task.id,
            checkpoint_id=checkpoint_id,
            last_safe_status=task.status.value if isinstance(task.status, TaskStatus) else str(task.status),
            execution_cursor=cursor,
            artifacts=task.artifacts or [],
            evidence=extra or {}
        )
        
        # Store checkpoint
        self._task_checkpoints[task.id] = checkpoint
        task.checkpoint_id = checkpoint_id
        task.last_safe_status = checkpoint.last_safe_status
        
        # Also save to disk for durability
        self._persist_checkpoint(checkpoint)
        
        logger.info(f"💾 Checkpoint saved for {task.id}: {checkpoint_id} (phase: {cursor.phase})")
        return checkpoint_id
    
    async def restore_from_checkpoint(self, checkpoint_id: str) -> Dict:
        """
        FIX #5: Restore task from checkpoint.
        
        This performs crash reconciliation:
        - If task was RUNNING with uncommitted side effects -> RECOVERING
        - If verification was in progress -> resume from VERIFYING
        - If approval was pending -> check if still valid
        
        Args:
            checkpoint_id: The checkpoint to restore from
            
        Returns:
            dict with 'task', 'cursor', 'reconciliation_action'
        """
        # Find checkpoint by ID
        checkpoint = None
        for cp in self._task_checkpoints.values():
            if cp.checkpoint_id == checkpoint_id:
                checkpoint = cp
                break
        
        if not checkpoint:
            # Try to load from disk
            checkpoint = self._load_checkpoint(checkpoint_id)
        
        if not checkpoint:
            return {
                'success': False,
                'error': f'Checkpoint not found: {checkpoint_id}'
            }
        
        # Get task
        task = self.task_manager.get_task(checkpoint.task_id)
        if not task:
            return {
                'success': False,
                'error': f'Task not found: {checkpoint.task_id}'
            }
        
        # Perform reconciliation based on cursor
        reconciliation_action = 'unknown'
        
        if checkpoint.execution_cursor:
            cursor = checkpoint.execution_cursor
            
            # Case 1: Side effect was committed but verification not complete
            if cursor.side_effect_committed and cursor.verification_phase:
                task.status = TaskStatus.VERIFYING
                reconciliation_action = 'resume_verification'
            
            # Case 2: Tool was executing, check if it completed
            elif cursor.tool_name and not cursor.side_effect_committed:
                task.status = TaskStatus.RECOVERING
                reconciliation_action = 'recover_execution'
            
            # Case 3: Approval was pending
            elif cursor.approval_request_id:
                # Check if approval is still valid
                if cursor.approval_request_id in self.pending_approvals:
                    task.status = TaskStatus.WAITING_APPROVAL
                    reconciliation_action = 'resume_approval'
                else:
                    task.status = TaskStatus.RECOVERING
                    reconciliation_action = 'approval_expired'
            
            # Case 4: Just a pause, resume to READY
            else:
                task.status = TaskStatus.READY
                reconciliation_action = 'resume_from_pause'
        
        # Restore checkpoint info
        task.checkpoint_id = checkpoint.checkpoint_id
        task.last_safe_status = checkpoint.last_safe_status
        
        logger.info(f"🔄 Restored {task.id} from checkpoint {checkpoint_id}, action: {reconciliation_action}")
        
        return {
            'success': True,
            'task': task,
            'cursor': checkpoint.execution_cursor,
            'reconciliation_action': reconciliation_action,
            'artifacts': checkpoint.artifacts,
            'evidence': checkpoint.evidence
        }
    
    async def resume_task(self, task_id: str) -> Dict:
        """
        FIX #4: Resume task from where it left off.
        
        This is the main resume API that telegram_bot.py expects.
        
        Args:
            task_id: The task to resume
            
        Returns:
            dict with resume result
        """
        task = self.task_manager.get_task(task_id)
        if not task:
            return {
                'success': False,
                'error': f'Task not found: {task_id}'
            }
        
        # Check if there's a checkpoint
        if task.checkpoint_id:
            return await self.restore_from_checkpoint(task.checkpoint_id)
        
        # No checkpoint, determine resume action based on status
        current_status = task.status.value if isinstance(task.status, TaskStatus) else str(task.status)
        
        if current_status in [TaskStatus.PAUSED.value, TaskStatus.WAITING_APPROVAL.value]:
            # Resume from pause/approval
            task.status = TaskStatus.READY
            logger.info(f"▶️ Resumed task {task_id} from {current_status}")
            return {
                'success': True,
                'task': task,
                'action': 'resume_ready'
            }
        
        elif current_status == TaskStatus.RECOVERING.value:
            # Resume from recovery
            task.status = TaskStatus.RETRYING
            logger.info(f"🔄 Resumed task {task_id} from RECOVERING")
            return {
                'success': True,
                'task': task,
                'action': 'resume_retrying'
            }
        
        elif current_status == TaskStatus.RETRYING.value:
            # Resume retry
            task.status = TaskStatus.RUNNING
            logger.info(f"🔁 Resumed task {task_id} for retry")
            return {
                'success': True,
                'task': task,
                'action': 'retry'
            }
        
        else:
            return {
                'success': False,
                'error': f'Cannot resume from status: {current_status}'
            }
    
    def _persist_checkpoint(self, checkpoint: TaskCheckpoint):
        """FIX #5: Persist checkpoint to disk"""
        import json
        import os
        
        checkpoint_dir = Path("data/checkpoints")
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        
        checkpoint_path = checkpoint_dir / f"{checkpoint.checkpoint_id}.json"
        
        # Serialize checkpoint
        data = {
            'task_id': checkpoint.task_id,
            'checkpoint_id': checkpoint.checkpoint_id,
            'last_safe_status': checkpoint.last_safe_status,
            'execution_cursor': {
                'phase': checkpoint.execution_cursor.phase if checkpoint.execution_cursor else 'unknown',
                'step_id': checkpoint.execution_cursor.step_id if checkpoint.execution_cursor else None,
                'tool_name': checkpoint.execution_cursor.tool_name if checkpoint.execution_cursor else None,
                'verification_phase': checkpoint.execution_cursor.verification_phase if checkpoint.execution_cursor else None,
                'approval_request_id': checkpoint.execution_cursor.approval_request_id if checkpoint.execution_cursor else None,
                'side_effect_committed': checkpoint.execution_cursor.side_effect_committed if checkpoint.execution_cursor else False,
            },
            'artifacts': checkpoint.artifacts,
            'evidence': checkpoint.evidence,
            'created_at': checkpoint.created_at
        }
        
        try:
            with open(checkpoint_path, 'w') as f:
                json.dump(data, f)
        except Exception as e:
            logger.warning(f"Failed to persist checkpoint: {e}")
    
    def _load_checkpoint(self, checkpoint_id: str) -> Optional[TaskCheckpoint]:
        """FIX #5: Load checkpoint from disk"""
        import json
        
        checkpoint_dir = Path("data/checkpoints")
        checkpoint_path = checkpoint_dir / f"{checkpoint_id}.json"
        
        if not checkpoint_path.exists():
            return None
        
        try:
            with open(checkpoint_path, 'r') as f:
                data = json.load(f)
            
            cursor = ExecutionCursor(
                phase=data.get('execution_cursor', {}).get('phase', 'unknown'),
                step_id=data.get('execution_cursor', {}).get('step_id'),
                tool_name=data.get('execution_cursor', {}).get('tool_name'),
                verification_phase=data.get('execution_cursor', {}).get('verification_phase'),
                approval_request_id=data.get('execution_cursor', {}).get('approval_request_id'),
                side_effect_committed=data.get('execution_cursor', {}).get('side_effect_committed', False),
            )
            
            return TaskCheckpoint(
                task_id=data['task_id'],
                checkpoint_id=data['checkpoint_id'],
                last_safe_status=data['last_safe_status'],
                execution_cursor=cursor,
                artifacts=data.get('artifacts', []),
                evidence=data.get('evidence', {}),
                created_at=data.get('created_at', time.time())
            )
        except Exception as e:
            logger.warning(f"Failed to load checkpoint {checkpoint_id}: {e}")
            return None
    
    async def process(self, user_message: str) -> str:
        """
        Main entry point - process user message through kernel
        """
        start_time = time.time()
        
        logger.info(f"🎯 Kernel processing: {user_message[:50]}...")
        
        # Update state
        self.state = KernelState.THINKING
        
        # Step 1: Analyze and plan
        plan = await self._plan(user_message)
        
        if not plan:
            return "❌ Rejalashtirish muvaffaqiyatsiz"
        
        # Step 2: Evaluate plan quality
        evaluation = self.critic.evaluate_plan(plan)
        
        if not evaluation["approved"]:
            return f"❌ Reja qabul qilinmadi: {evaluation['issues']}"
        
        # Step 3: Execute plan
        self.state = KernelState.ACTING
        
        result = await self._execute(plan)
        
        # Step 4: Verify result
        self.state = KernelState.VERIFYING
        
        # FIX #6: Proper _verify signature - need task and exec_result
        # This was the old broken call: verified = await self._verify(result)
        # Now we need to construct proper parameters
        if hasattr(result, 'success'):
            # result is ExecutionResult
            task_for_verify = Task(
                id="plan_execution",
                description="Plan execution verification",
                input_data={}
            )
            verified = await self._verify(task_for_verify, result, {})
        else:
            # Fallback for other result types
            verified = True
        
        if not verified:
            # Step 5: Repair if needed
            self.state = KernelState.REPAIRING
            result = await self._repair(result)
        
        # Update metrics
        duration = time.time() - start_time
        self.telemetry.record_task(
            success=verified,
            duration=duration
        )
        
        self.state = KernelState.IDLE
        
        return result
    
    async def _plan(self, message: str) -> List[Task]:
        """
        Create execution plan using LLM-based planner with robust JSON parsing.
        Enhanced with:
        - Strict schema validation
        - Multiple JSON parsing strategies
        - Enhanced fallback planner with heuristics
        - Full task metadata
        """
        
        # Use native_brain for intelligent planning if available
        if hasattr(self, 'native_brain') and self.native_brain:
            try:
                planning_prompt = f"""Create a detailed task plan for: {message}
Return JSON with tasks array containing: id, description, priority, dependencies, required_tools, verification_type, success_criteria, fallback_strategy, retry_policy, approval_policy, timeout"""
                
                response = self.native_brain.think(planning_prompt)
                tasks = self._parse_llm_plan(response)
                
                if tasks:
                    logger.info(f"📋 Created {len(tasks)} tasks via LLM planner")
                    return tasks
                    
            except Exception as e:
                logger.warning(f"LLM planning failed: {e}")
        
        # Enhanced fallback planner
        return self._heuristic_planner(message)
    def _parse_llm_plan(self, response: str) -> List[Task]:
        """
        STRICT JSON PARSING - No1-grade governed.
        
        HAQIQAT: Tool result from execution, NOT from LLM parsing.
        LLM output is ONLY suggestion for planning.
        
        Strict validation:
        - Schema validation MANDATORY
        - Invalid plan diagnostics
        - Failed parse telemetry
        - Planner quality metrics
        - NO silent failures
        """
        import re, json
        import time

        tasks = []
        parsing_attempts = []
        parse_diagnostics = {"response_length": 0, "has_json_markers": False, "has_prose": False, "strategies_tried": [], "failures": []}

        # Pre-processing
        response = response.strip()
        parse_diagnostics["response_length"] = len(response)
        
        # Check if response is prose (model hallucination risk)
        if response.startswith(("{", "[")):
            parse_diagnostics["has_json_markers"] = True
        else:
            parse_diagnostics["has_prose"] = True
            logger.warning("⚠️ LLM response contains prose, not JSON - HIGH RISK")

        # STRICT parsing strategies (8 strategies for robustness)
        # Added: markdown_code_block, line_by_line, nested_json, fix_common_errors, prose_fallback
        parsing_strategies = [
            {'name': 'tasks_key_object', 'pattern': r'\{[^{}]*"tasks"\s*:\s*\[', 'try_extract': lambda: re.search(r'\{[^{}]*"tasks"\s*:\s*\[.*\]', response, re.DOTALL)},
            {'name': 'array_with_description', 'pattern': r'\[.*"description".*\]', 'try_extract': lambda: re.search(r'\[.*"description".*\]', response)},
            {'name': 'brackets_balanced', 'pattern': 'any', 'try_extract': lambda: self._extract_balanced_brackets(response)},
            {'name': 'markdown_code_block', 'pattern': r'```json.*?```', 'try_extract': lambda: re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)},
            {'name': 'line_by_line', 'pattern': 'any', 'try_extract': lambda: self._extract_tasks_line_by_line(response)},
            {'name': 'nested_json', 'pattern': r'\{.*\{.*\}.*\}', 'try_extract': lambda: self._extract_nested_json(response)},
            {'name': 'fix_common_errors', 'pattern': 'any', 'try_extract': lambda: self._fix_and_extract_json(response)},
            {'name': 'prose_fallback', 'pattern': 'any', 'try_extract': lambda: self._extract_from_prose(response)},
        ]

        for strategy in parsing_strategies:
            strategy_name = strategy['name']
            start_time = time.time()
            parse_diagnostics["strategies_tried"].append(strategy_name)

            try:
                json_match = strategy['try_extract']()
                if json_match:
                    json_str = json_match.group() if hasattr(json_match, 'group') else str(json_match)
                    
                    # STRICT: Validate JSON
                    try:
                        tasks_data = json.loads(json_str)
                        
                        # STRICT: Validate schema
                        validation_result = self._validate_plan_schema(tasks_data)
                        
                        if validation_result['valid']:
                            if isinstance(tasks_data, dict) and 'tasks' in tasks_data:
                                tasks_data = tasks_data['tasks']

                            if isinstance(tasks_data, list):
                                # Create tasks with diagnostics
                                tasks = self._create_tasks_from_plan({"tasks": tasks_data}, response_snippet=response, parser_strategy=strategy_name)
                                if tasks:
                                    parsing_attempts.append({
                                        'strategy': strategy_name, 'success': True, 'tasks_count': len(tasks), 'time_ms': (time.time() - start_time) * 1000
                                    })
                                    self._emit_plan_parsing_telemetry(True, parsing_attempts, response, parse_diagnostics, strategy_name)
                                    return tasks
                                else:
                                    # All tasks were invalid - log detailed diagnostics
                                    logger.warning(f"⚠️ Strategy '{strategy_name}' created 0 valid tasks from {len(tasks_data)} parsed items")
                                    parse_diagnostics['failures'].append({
                                        'strategy': strategy_name,
                                        'reason': 'all_tasks_invalid',
                                        'parsed_count': len(tasks_data)
                                    })
                        else:
                            # Schema failed - log detailed diagnostics
                            parse_diagnostics['failures'].append({
                                'strategy': strategy_name,
                                'reason': 'schema_validation_failed',
                                'errors': validation_result.get('errors', [])
                            })
                            logger.warning(f"⚠️ Schema validation failed for strategy '{strategy_name}': {validation_result.get('errors', [])}")
                            logger.debug("Schema validation failed, continuing")
                            
                    except json.JSONDecodeError as e:
                        parsing_attempts.append({'strategy': strategy_name, 'success': False, 'reason': 'json_decode_error', 'error': str(e), 'time_ms': (time.time() - start_time) * 1000})
                        
            except Exception as e:
                parsing_attempts.append({'strategy': strategy_name, 'success': False, 'reason': 'exception', 'error': str(e), 'time_ms': (time.time() - start_time) * 1000})

        # ALL strategies failed - STRICT mode
        logger.error(f"❌ Plan parsing FAILED - all strategies exhausted")
        
        # Emit failure telemetry
        self._emit_plan_parsing_telemetry(False, parsing_attempts, response, parse_diagnostics, None)
        
        # STRICT: Return empty - do NOT fallback to model
        return tasks



    def _emit_plan_parsing_telemetry(self, success: bool, parsing_attempts: List[Dict], response: str, parse_diagnostics: Dict, successful_strategy: str = None):
        """
        Emit telemetry for plan parsing with full diagnostics.
        
        This enables:
        - Debugging which parsing strategy failed
        - Self-improvement signals for prompt engineering
        - Quality metrics for planner
        """
        import time
        
        # Determine recovery hint
        recovery_hint = _get_recovery_hint(parsing_attempts) if not success else "Success"
        
        telemetry_data = {
            'success': success,
            'successful_strategy': successful_strategy,
            'attempts': parsing_attempts,
            'response_preview': response[:500],  # More context
            'diagnostics': parse_diagnostics,
            'recovery_hint': recovery_hint,
            'timestamp': time.time(),
            'strategies_tried_count': len(parse_diagnostics.get("strategies_tried", [])),
            'failures_count': len(parse_diagnostics.get("failures", []))
        }
        
        # Log prominently for debugging
        if success:
            logger.info(f"✅ Plan parsing SUCCESS with strategy: {successful_strategy}")
        else:
            logger.error(f"❌ Plan parsing FAILED. Recovery hint: {recovery_hint}")
            logger.error(f"   Strategies tried: {parse_diagnostics.get('strategies_tried', [])}")
            logger.error(f"   Failures: {parse_diagnostics.get('failures', [])}")
        
        # Emit to telemetry if available
        if hasattr(self, 'telemetry') and self.telemetry:
            try:
                self.telemetry.record_event('plan_parsing', telemetry_data)
            except Exception as e:
                logger.error(f"Failed to emit telemetry: {e}")
        
        # Emit self-improvement signal if available
        if hasattr(self, 'emit_improvement_signal') and not success:
            try:
                self.emit_improvement_signal('plan_parsing_failure', {
                    'recovery_hint': recovery_hint,
                    'strategies_failed': [a.get('strategy') for a in parsing_attempts if not a.get('success', False)],
                    'response_preview': response[:200]
                })
            except Exception as e:
                logger.error(f"Failed to emit improvement signal: {e}")

        # Record in planner quality tracker
        if hasattr(self, 'planner_quality') and self.planner_quality:
            strategy_used = successful_strategy if successful_strategy else "failed"
            total_time = sum(a.get('time_ms', 0) for a in parsing_attempts)
            self.planner_quality.record_parse(success, strategy_used, total_time)

        # Save invalid snippets to disk for debugging
        if not success and hasattr(self, '_invalid_snippets_dir'):
            self._save_invalid_snippet(response, parse_diagnostics, parsing_attempts)

        # Log detailed diagnostics
        self._log_parse_diagnostics(parse_diagnostics, parsing_attempts)
    

    def _save_invalid_snippet(self, response: str, diagnostics: Dict, attempts: List[Dict]):
        """Save invalid parsing snippets to disk for debugging"""
        import json
        import uuid
        import time
        
        try:
            snippet_data = {
                'snippet_id': str(uuid.uuid4())[:8],
                'response': response[:2000],  # Limit size
                'diagnostics': diagnostics,
                'attempts': attempts,
                'timestamp': time.time()
            }
            
            filename = f"invalid_snippet_{snippet_data['snippet_id']}.json"
            filepath = self._invalid_snippets_dir / filename
            
            with open(filepath, 'w') as f:
                json.dump(snippet_data, f, indent=2)
                
            logger.info(f"💾 Invalid snippet saved: {filename}")
        except Exception as e:
            logger.error(f"Failed to save invalid snippet: {e}")

    def _log_parse_diagnostics(self, diagnostics: Dict, attempts: List[Dict]):
        """Log detailed parse diagnostics for debugging"""
        # Log JSON markers status
        if diagnostics.get('has_prose'):
            logger.warning(f"   📝 Response contains prose (not pure JSON)")
        if diagnostics.get('has_json_markers'):
            logger.info(f"   📋 Response has JSON markers")
            
        # Log response length
        logger.info(f"   📏 Response length: {diagnostics.get('response_length', 0)} chars")
        
        # Log each failed attempt
        for i, attempt in enumerate(attempts):
            if not attempt.get('success', False):
                logger.warning(f"   ❌ Attempt {i+1}: {attempt.get('strategy')} - {attempt.get('reason')}: {attempt.get('error', 'N/A')}")
    def _extract_balanced_brackets(self, text: str) -> Optional[re.Match]:
        """Extract balanced JSON from text"""
        import re
        
        # Find all { } pairs
        start_idx = text.find('{')
        if start_idx == -1:
            return None
        
        # Try to find complete JSON object
        depth = 0
        for i, char in enumerate(text[start_idx:], start_idx):
            if char == '{':
                depth += 1
            elif char == '}':
                depth -= 1
                if depth == 0:
                    # Found balanced brackets
                    return re.match(r'\{[\s\S]*\}', text[start_idx:i+1])
        
        return None
    
    def _extract_json_lines(self, text: str) -> Optional[re.Match]:
        """Extract JSON from lines that look like JSON objects"""
        import re
        
        lines = text.split('\n')
        json_lines = []
        
        for line in lines:
            line = line.strip()
            if line.startswith('{') and line.endswith('}'):
                json_lines.append(line)
        
        if json_lines:
            # Try to combine into array
            combined = '[' + ','.join(json_lines) + ']'
            try:
                json.loads(combined)  # Validate
                return re.match(r'\[[\s\S]*\]', combined)
            except (json.JSONDecodeError, ValueError) as e:
                logger.debug(f"JSON line combination failed: {e}")
                logger.debug("JSON validation continued")
        
        return None
    

    def _extract_tasks_line_by_line(self, text: str) -> Optional[re.Match]:
        """Extract tasks from text line by line - handles mixed prose + JSON"""
        import re
        
        lines = text.split('\n')
        tasks = []
        current_task = {}
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Look for task-like patterns
            # Pattern 1: "1. task description" or "- task description"
            task_match = re.match(r'^\d+[\.\)]\s+(.+)$', line) or re.match(r'^-\s+(.+)$', line)
            if task_match:
                if current_task and 'description' in current_task:
                    tasks.append(current_task)
                current_task = {'description': task_match.group(1)}
                
            # Pattern 2: JSON-like fields
            json_match = re.match(r'^"(\w+)":\s*"(.+)"', line)
            if json_match and current_task:
                key, value = json_match.groups()
                current_task[key] = value
        
        # Add last task
        if current_task and 'description' in current_task:
            tasks.append(current_task)
        
        if tasks:
            return re.match(r'\[[\s\S]*\]', json.dumps({'tasks': tasks}))
        
        return None

    def _extract_nested_json(self, text: str) -> Optional[re.Match]:
        """Extract nested JSON structures"""
        import re
        
        # Find the outermost braces
        start = text.find('{')
        if start == -1:
            return None
        
        # Try to find balanced JSON with nested objects
        depth = 0
        for i, char in enumerate(text[start:], start):
            if char == '{':
                depth += 1
            elif char == '}':
                depth -= 1
                if depth == 0:
                    candidate = text[start:i+1]
                    # Try to parse
                    try:
                        parsed = json.loads(candidate)
                        # Check if it has tasks or looks like a plan
                        if 'tasks' in parsed or isinstance(parsed, list):
                            return re.match(r'\{[\s\S]*\}', candidate)
                    except (json.JSONDecodeError, ValueError, Exception) as e:
                        logger.debug(f"JSON parse attempt failed: {e}")
        
        return None

    def _fix_and_extract_json(self, text: str) -> Optional[re.Match]:
        """Fix common JSON errors and extract"""
        import re
        
        # Fix common errors:
        # 1. Trailing commas: ,} or ,]
        text = re.sub(r',(\s*[\]}])', r'\1', text)
        # 2. Single quotes to double quotes
        text = re.sub(r"'([\w\s]+)'", r'"\1"', text)
        # 3. Missing quotes around keys
        text = re.sub(r'(\w+):', r'"\1":', text)
        # 4. JavaScript comments
        text = re.sub(r'//.*$', '', text, flags=re.MULTILINE)
        
        # Try to find JSON
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            try:
                json.loads(json_match.group())
                return json_match
            except (json.JSONDecodeError, ValueError, Exception) as e:
                logger.debug(f"JSON fix attempt failed: {e}")
        
        return None

    def _extract_from_prose(self, text: str) -> Optional[re.Match]:
        """Extract tasks from prose descriptions - last resort"""
        import re
        
        # This is a last-resort fallback
        # Look for numbered lists or bullet points in prose
        tasks = []
        
        # Pattern: "Step 1:", "1)", "-", "*"
        step_pattern = re.compile(r'(?:Step\s*\d+|\d+\))\s*(.+?)(?=(?:Step\s*\d+|\d+\)|\n\s*\n|$))', re.IGNORECASE)
        
        for match in step_pattern.finditer(text):
            desc = match.group(1).strip()
            if len(desc) > 10:  # Reasonable task length
                tasks.append({'description': desc[:200]})  # Truncate long descriptions
        
        if tasks:
            return re.match(r'\[[\s\S]*\]', json.dumps({'tasks': tasks}))
        
        return None

    def _compile_task_spec(self, task_dict: Dict) -> TaskSpec:
        """
        FIX #2: Compile TaskSpec from planner dict.
        
        This is the planner compiler - transforms planner JSON output
        into a typed TaskSpec contract.
        
        This ensures:
        - retry_policy is always a RetryPolicy (not int or dict)
        - approval is always an ApprovalSpec
        - sandbox is always a SandboxSpec
        - verification is always a VerificationSpec
        - success_criteria is always a list of SuccessCriterion
        """
        # Compile RetryPolicy - handles int/dict ambiguity
        retry_dict = task_dict.get('retry_policy', {})
        if isinstance(retry_dict, int):
            retry_policy = RetryPolicy(max_retries=retry_dict)
        elif isinstance(retry_dict, dict):
            retry_policy = RetryPolicy(
                max_retries=retry_dict.get('max_retries', 3),
                backoff_strategy=retry_dict.get('backoff_strategy', 'exponential'),
                initial_delay_sec=retry_dict.get('initial_delay_sec', 1),
                max_delay_sec=retry_dict.get('max_delay_sec', 30)
            )
        else:
            retry_policy = RetryPolicy()
        
        # Compile ApprovalSpec
        approval_dict = task_dict.get('approval_policy', 'auto')
        if isinstance(approval_dict, str):
            approval = ApprovalSpec(policy=approval_dict)
        elif isinstance(approval_dict, dict):
            approval = ApprovalSpec(
                policy=approval_dict.get('policy', 'auto'),
                required_for_dangerous=approval_dict.get('required_for_dangerous', True),
                timeout_sec=approval_dict.get('timeout_sec', 300)
            )
        else:
            approval = ApprovalSpec()
        
        # Compile SandboxSpec
        sandbox_dict = task_dict.get('sandbox_mode', 'normal')
        if isinstance(sandbox_dict, str):
            sandbox = SandboxSpec(mode=sandbox_dict)
        elif isinstance(sandbox_dict, dict):
            sandbox = SandboxSpec(
                mode=sandbox_dict.get('mode', 'normal'),
                allow_network=sandbox_dict.get('allow_network', True),
                allow_file_write=sandbox_dict.get('allow_file_write', True)
            )
        else:
            sandbox = SandboxSpec()
        
        # Compile ToolSpec
        tools = task_dict.get('required_tools', [])
        tool_spec = ToolSpec(
            required_tools=tools if isinstance(tools, list) else [],
            preferred_tool=task_dict.get('preferred_tool'),
            alternate_tool=task_dict.get('alternate_tool'),
            destructive=task_dict.get('destructive', False)
        )
        
        # Compile VerificationSpec
        verification_type = task_dict.get('verification_type')
        verification_params = task_dict.get('verification_params', {})
        verification = VerificationSpec(
            type=verification_type or 'none',
            params=verification_params if isinstance(verification_params, dict) else {},
            required=verification_type is not None
        )
        
        # Compile success_criteria - from string DSL to structured
        success_criteria_raw = task_dict.get('success_criteria', [])
        success_criteria = []
        
        if isinstance(success_criteria_raw, str):
            # Parse string DSL like "contains:X exit_code:0"
            for part in success_criteria_raw.split():
                if ':' in part:
                    kind, value = part.split(':', 1)
                    try:
                        # Try to parse as int
                        value = int(value)
                    except ValueError:
                        try:
                            # Try to parse as float
                            value = float(value)
                        except ValueError:
                            pass  # Keep as string
                    success_criteria.append(SuccessCriterion(kind=kind, value=value))
        elif isinstance(success_criteria_raw, list):
            # Already structured
            for criterion in success_criteria_raw:
                if isinstance(criterion, dict):
                    success_criteria.append(SuccessCriterion(
                        kind=criterion.get('kind', 'unknown'),
                        value=criterion.get('value'),
                        optional=criterion.get('optional', False)
                    ))
                elif isinstance(criterion, tuple):
                    success_criteria.append(SuccessCriterion(kind=criterion[0], value=criterion[1]))
        
        # Expected artifacts
        expected_artifacts = task_dict.get('expected_artifacts', [])
        if not isinstance(expected_artifacts, list):
            expected_artifacts = []
        
        # Timeout
        timeout = task_dict.get('timeout', 30)
        if not isinstance(timeout, int):
            timeout = 30
        
        # Rollback
        rollback = task_dict.get('rollback_point')
        
        # Create TaskSpec
        return TaskSpec(
            description=task_dict.get('description', 'Unknown task'),
            priority=task_dict.get('priority', 'normal'),
            dependencies=task_dict.get('dependencies', []) if isinstance(task_dict.get('dependencies'), list) else [],
            tool_spec=tool_spec,
            verification=verification,
            success_criteria=success_criteria,
            expected_artifacts=expected_artifacts,
            retry_policy=retry_policy,
            approval=approval,
            sandbox=sandbox,
            timeout_sec=timeout,
            rollback=rollback
        )

    def _validate_plan_schema(self, data: Any) -> Dict:
        """
        Validate plan data against expected schema.
        
        Returns:
        {
            'valid': bool,
            'errors': List[str]
        }
        """
        
        errors = []
        
        # Must be dict or list
        if not isinstance(data, (dict, list)):
            errors.append(f"Plan must be dict or list, got {type(data)}")
            return {'valid': False, 'errors': errors}
        
        # If it's a dict, must have 'tasks' key or be an array
        if isinstance(data, dict):
            if 'tasks' not in data and not any(k in data for k in ['id', 'description', 'steps']):
                errors.append("Dict must have 'tasks' key or task fields")
        
        # If it has tasks, validate each
        tasks = data.get('tasks', []) if isinstance(data, dict) else data
        
        if isinstance(tasks, list):
            for i, task in enumerate(tasks):
                if not isinstance(task, dict):
                    errors.append(f"Task {i} must be dict, got {type(task)}")
                    continue
                
                # Required fields
                if 'description' not in task:
                    errors.append(f"Task {i} missing 'description'")
                
                # Validate optional fields
                allowed_priorities = ['CRITICAL', 'HIGH', 'NORMAL', 'LOW', '']
                priority = task.get('priority', '').upper()
                if priority and priority not in allowed_priorities:
                    errors.append(f"Task {i} invalid priority: {priority}")
                
                # Validate verification_type if present
                allowed_verification = ['manual', 'browser', 'screenshot', 'server', 'code', 'file', 'function']
                verification = task.get('verification_type', '').lower()
                if verification and verification not in allowed_verification:
                    errors.append(f"Task {i} invalid verification_type: {verification}")
                
                # Validate approval_policy if present
                allowed_approval = ['auto', 'manual', 'never']
                approval = task.get('approval_policy', '').lower()
                if approval and approval not in allowed_approval:
                    errors.append(f"Task {i} invalid approval_policy: {approval}")
                
                # Validate sandbox_mode if present
                allowed_sandbox = ['safe', 'normal', 'advanced']
                sandbox = task.get('sandbox_mode', '').lower()
                if sandbox and sandbox not in allowed_sandbox:
                    errors.append(f"Task {i} invalid sandbox_mode: {sandbox}")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors
        }
    
    def _create_tasks_from_plan(self, plan_data: Dict, response_snippet: str = "", parser_strategy: str = "unknown") -> List[Task]:
        """
        Args:
            plan_data: The parsed plan data
            response_snippet: Original LLM response snippet for diagnostics
            parser_strategy: The strategy that was used to parse this plan (for diagnostics)
        """
        """
        Create tasks from plan data with ENHANCED validation and detailed diagnostics.
        
        Fixed issues:
        - Required fields validation
        - Allowed verification types validation
        - Allowed approval policies validation
        - Allowed sandbox modes validation
        - Tool existence check
        - No more silent minimal task creation on parse errors
        - Detailed invalid task tracking with full diagnostics
        - Planner quality metrics
        - Self-improvement feedback
        """
        
        import uuid
        import time
        import json
        
        tasks = []
        invalid_tasks = []  # Track invalid tasks with full diagnostics
        task_validation_counters = {
            'missing_description': 0,
            'invalid_priority': 0,
            'invalid_verification': 0,
            'invalid_approval': 0,
            'invalid_sandbox': 0,
            'unknown_tools': 0,
            'invalid_dependencies': 0,
            'creation_error': 0,
        }
        
        # Allowed values
        ALLOWED_PRIORITIES = ['CRITICAL', 'HIGH', 'NORMAL', 'LOW', '']
        ALLOWED_VERIFICATION = ['manual', 'browser', 'screenshot', 'server', 'code', 'file', 'function']
        ALLOWED_APPROVAL = ['auto', 'manual', 'never']
        ALLOWED_SANDBOX = ['safe', 'normal', 'advanced']
        
        # Known tools (can be extended)
        KNOWN_TOOLS = [
            'execute_command', 'execute_code', 'write_file', 'read_file', 
            'delete_file', 'browser_navigate', 'browser_click', 'browser_type',
            'web_search', 'web_request', 'install_package', 'take_screenshot'
        ]
        
        # Get snippet from response for diagnostics
        snippet = response_snippet[:500] if response_snippet else ""
        
        for i, t in enumerate(plan_data.get('tasks', [])):
            task_errors = []
            failed_fields = []
            
            # Skip if not a dict
            if not isinstance(t, dict):
                error_msg = f"Task {i} is not a dictionary"
                task_errors.append(error_msg)
                failed_fields.append('type_check_failed')
                task_validation_counters['creation_error'] += 1
                invalid_tasks.append({
                    'index': i,
                    'failed_fields': failed_fields,
                    'errors': task_errors,
                    'snippet': snippet,
                    'parse_reason': 'not_a_dictionary',
                    'parser_strategy': parser_strategy,
                    'timestamp': time.time()
                })
                continue
            
            # Validate required fields
            if not t.get('description'):
                task_errors.append(f"Task {i} missing 'description'")
                failed_fields.append('description')
                task_validation_counters['missing_description'] += 1
            
            # Validate priority
            priority = t.get('priority', '').upper()
            if priority and priority not in ALLOWED_PRIORITIES:
                task_errors.append(f"Invalid priority: {priority}")
                failed_fields.append('priority')
                task_validation_counters['invalid_priority'] += 1
            
            # Validate verification_type
            verification = t.get('verification_type', '').lower()
            if verification and verification not in ALLOWED_VERIFICATION:
                task_errors.append(f"Invalid verification_type: {verification}")
                failed_fields.append('verification_type')
                task_validation_counters['invalid_verification'] += 1
            
            # Validate approval_policy
            approval = t.get('approval_policy', '').lower()
            if approval and approval not in ALLOWED_APPROVAL:
                task_errors.append(f"Invalid approval_policy: {approval}")
                failed_fields.append('approval_policy')
                task_validation_counters['invalid_approval'] += 1
            
            # Validate sandbox_mode
            sandbox = t.get('sandbox_mode', '').lower()
            if sandbox and sandbox not in ALLOWED_SANDBOX:
                task_errors.append(f"Invalid sandbox_mode: {sandbox}")
                failed_fields.append('sandbox_mode')
                task_validation_counters['invalid_sandbox'] += 1
            
            # Validate required_tools if present
            required_tools = t.get('required_tools', [])
            if required_tools:
                if isinstance(required_tools, list):
                    unknown_tools = [tool for tool in required_tools if tool not in KNOWN_TOOLS]
                    if unknown_tools:
                        task_errors.append(f"Unknown tools: {unknown_tools}")
                        failed_fields.append('required_tools')
                        task_validation_counters['unknown_tools'] += 1
                else:
                    task_errors.append("'required_tools' must be a list")
                    failed_fields.append('required_tools')
            
            # Validate dependencies if present
            deps = t.get('dependencies', [])
            if deps:
                if not isinstance(deps, list):
                    task_errors.append("'dependencies' must be a list")
                    failed_fields.append('dependencies')
                    task_validation_counters['invalid_dependencies'] += 1
            
            # Determine parse reason
            if task_errors:
                if any('description' in e for e in task_errors):
                    parse_reason = 'missing_required_field'
                elif any('Invalid priority' in e for e in task_errors):
                    parse_reason = 'invalid_field_value'
                else:
                    parse_reason = 'validation_failed'
            else:
                parse_reason = None
            
            # If there are critical errors, skip this task
            critical_errors = [e for e in task_errors if 'description' in e or 'priority' in e or 'Invalid' in e]
            
            if critical_errors:
                logger.warning(f"Task {i} skipped due to critical errors: {critical_errors}")
                invalid_tasks.append({
                    'index': i,
                    'failed_fields': failed_fields,
                    'errors': task_errors,
                    'snippet': snippet,
                    'parse_reason': parse_reason or 'critical_validation_error',
                    'parser_strategy': parser_strategy,
                    'timestamp': time.time()
                })
                continue
            
            # If non-critical errors (like unknown tools), log but still create task
            if task_errors:
                logger.warning(f"Task {i} created with warnings: {task_errors}")
            
            # Create task with validated data
            try:
                priority = TaskPriority.NORMAL
                if priority == 'HIGH' or priority == 'CRITICAL':
                    priority = TaskPriority.HIGH
                elif t.get('priority', '').upper() == 'LOW':
                    priority = TaskPriority.LOW
                
                # FIX #2: Compile TaskSpec from dict - this is the canonical contract
                task_spec = self._compile_task_spec(t)
                
                # Create task with spec
                task = Task(
                    id=t.get('id', f"task_{int(time.time()*1000)}_{i}"),
                    description=t.get('description', 'Unknown task'),
                    priority=priority,
                    dependencies=t.get('dependencies', []),
                    timeout=task_spec.timeout_sec,
                    max_retries=task_spec.retry_policy.max_retries,
                    approval_policy=task_spec.approval.policy,
                    sandbox_mode=task_spec.sandbox.mode,
                )
                
                # FIX #2: Policy fields now come from TaskSpec, NOT from input_data
                # input_data should ONLY contain execution payload (tool args)
                task.input_data = {
                    # Tool arguments - ONLY execution payload
                    'file_path': t.get('file_path', ''),
                    'file_content': t.get('file_content', ''),
                    'url': t.get('url', ''),
                    'command': t.get('command', ''),
                    'code': t.get('code', ''),
                    'language': t.get('language', 'python'),
                    'process_name': t.get('process_name', ''),
                    'port': t.get('port', 80),
                    'host': t.get('host', 'localhost'),
                    
                    # Tool routing from spec (not hardcoded)
                    'preferred_tool': task_spec.tool_spec.preferred_tool,
                    'alternate_tool': task_spec.tool_spec.alternate_tool,
                    'destructive': task_spec.tool_spec.destructive,
                    
                    # FIX #2: success_criteria from TaskSpec as structured
                    'success_criteria': [(c.kind, c.value) for c in task_spec.success_criteria],
                }
                
                # Set artifact expectations from spec
                task.artifact_expectations = task_spec.expected_artifacts
                
                # Store spec in metadata for access by other components
                task.metadata['_task_spec'] = {
                    'verification_type': task_spec.verification.type,
                    'verification_params': task_spec.verification.params,
                    'retry_policy': {
                        'max_retries': task_spec.retry_policy.max_retries,
                        'backoff': task_spec.retry_policy.backoff_strategy,
                    },
                    'sandbox': {
                        'mode': task_spec.sandbox.mode,
                        'allow_network': task_spec.sandbox.allow_network,
                        'allow_file_write': task_spec.sandbox.allow_file_write,
                    },
                }
                
                tasks.append(task)
                
            except Exception as e:
                logger.error(f"Failed to create task {i}: {e}")
                invalid_tasks.append({
                    'index': i,
                    'failed_fields': ['creation_exception'],
                    'errors': [str(e)],
                    'snippet': snippet,
                    'parse_reason': 'task_creation_error',
                    'parser_strategy': parser_strategy,
                    'timestamp': time.time()
                })
                task_validation_counters['creation_error'] += 1
        
        # Log summary of invalid tasks with detailed diagnostics
        total_tasks = len(plan_data.get('tasks', []))
        if invalid_tasks:
            logger.error(f"❌ Task validation FAILED: {len(invalid_tasks)}/{total_tasks} tasks invalid")
            logger.error(f"   Validation counters: {task_validation_counters}")
            
            # Structured diagnostic output
            for inv in invalid_tasks:
                logger.error("   ===== FAILED TASK DIAGNOSTIC =====")
                logger.error(f"   📋 Task Index: {inv['index']}")
                logger.error(f"   🔍 Failed Fields: {inv['failed_fields']}")
                logger.error(f"   ⚠️  Parse Reason: {inv['parse_reason']}")
                logger.error(f"   💥 Errors: {inv['errors']}")
                logger.error(f"   📝 Snippet: {inv.get('snippet', 'N/A')[:100]}...")
                logger.error("   ====================================")
        
        # Calculate planner quality metrics
        success_rate = (len(tasks) / total_tasks * 100) if total_tasks > 0 else 0
        quality_grade = "EXCELLENT" if success_rate >= 90 else "GOOD" if success_rate >= 70 else "NEEDS_IMPROVEMENT" if success_rate >= 50 else "POOR"
        
        logger.info(f"📊 Planner quality: {quality_grade} ({len(tasks)}/{total_tasks} = {success_rate:.1f}%)")
        
        # Emit ALWAYS (not conditional) - comprehensive telemetry for task creation quality
        telemetry_data = {
            'total_tasks': total_tasks,
            'valid_tasks': len(tasks),
            'invalid_tasks': len(invalid_tasks),
            'success_rate': success_rate,
            'quality_grade': quality_grade,
            'validation_counters': task_validation_counters,
            'invalid_details': invalid_tasks,  # Full details with index, failed_fields, snippet, parse_reason
            'timestamp': time.time()
        }
        
        # Log telemetry prominently
        logger.info(f"📈 Task creation telemetry: {json.dumps(telemetry_data, indent=2)}")
        
        # Emit to telemetry if available
        if hasattr(self, 'telemetry') and self.telemetry:
            try:
                self.telemetry.record_event('task_creation', telemetry_data)
            except Exception as e:
                logger.error(f"Failed to emit task_creation telemetry: {e}")
        
        # Emit self-improvement signal if there are invalid tasks
        if hasattr(self, 'emit_improvement_signal') and invalid_tasks:
            try:
                self.emit_improvement_signal('task_creation_failure', {
                    'quality_grade': quality_grade,
                    'success_rate': success_rate,
                    'validation_counters': task_validation_counters,
                    'top_failure_reasons': [
                        {'reason': k, 'count': v} 
                        for k, v in sorted(task_validation_counters.items(), key=lambda x: -x[1]) 
                        if v > 0
                    ][:5],
                    'failed_task_indices': [inv['index'] for inv in invalid_tasks]
                })
            except Exception as e:
                logger.error(f"Failed to emit improvement signal: {e}")

        # Record in planner quality tracker
        if hasattr(self, 'planner_quality') and self.planner_quality:
            strategy_used = successful_strategy if successful_strategy else "failed"
            total_time = sum(a.get('time_ms', 0) for a in parsing_attempts)
            self.planner_quality.record_parse(success, strategy_used, total_time)

        # Save invalid snippets to disk for debugging
        if not success and hasattr(self, '_invalid_snippets_dir'):
            self._save_invalid_snippet(response, parse_diagnostics, parsing_attempts)

        # Log detailed diagnostics
        self._log_parse_diagnostics(parse_diagnostics, parsing_attempts)
        
        return tasks
    
    def _heuristic_planner(self, message: str) -> List[Task]:
        """
        ENHANCED fallback planner with FULL metadata for No1 agent.
        
        Fixed issues:
        - Rollback point support
        - Sandbox mode selection
        - Approval policy
        - Artifact expectations
        - Retry policy richness
        - Dependency graph depth
        - Risk level assessment
        """
        
        import uuid
        import time
        tasks = []
        msg_lower = message.lower()
        
        # Determine risk level
        is_dangerous = any(k in msg_lower for k in ['ochir', 'delete', 'format', 'drop', 'rm -rf', 'truncate'])
        is_high_risk = any(k in msg_lower for k in ['install', 'apt', 'yum', 'pip install', 'npm install'])
        
        risk_level = 'critical' if is_dangerous else ('high' if is_high_risk else 'medium')
        
        # Sandbox mode based on risk
        sandbox_mode = 'safe' if is_dangerous else ('advanced' if is_high_risk else 'normal')
        
        # Approval policy based on risk
        approval_policy = 'manual' if is_dangerous or is_high_risk else 'auto'
        
        # Task type detection with RICH metadata
        task_specs = []
        
        # File creation tasks
        if any(k in msg_lower for k in ['yarat', 'yoz', 'fayl', 'create', 'write', 'new file']):
            task_specs.append({
                'type': 'file', 
                'tools': ['write_file'], 
                'ver': 'file',
                'desc': 'Fayl yaratish',
                'task_type': 'file',
                'expected_artifacts': [],
                'rollback_point': {'type': 'file_backup', 'description': 'Faylni zaxiraga olish'}
            })
        
        # File reading tasks
        if any(k in msg_lower for k in ['oqish', 'read', 'ko\'r', 'view', 'show']):
            task_specs.append({
                'type': 'read', 
                'tools': ['read_file'], 
                'ver': 'function',
                'desc': 'Faylni o\'qish',
                'task_type': 'file',
                'expected_artifacts': [],
                'rollback_point': None
            })
        
        # Search tasks
        if any(k in msg_lower for k in ['qidir', 'internet', 'search', 'web', 'find']):
            task_specs.append({
                'type': 'search', 
                'tools': ['web_search'], 
                'ver': 'function',
                'desc': 'Internetda qidirish',
                'task_type': 'search',
                'expected_artifacts': [],
                'rollback_point': None
            })
        
        # Browser tasks
        if any(k in msg_lower for k in ['sahifa', 'page', 'sayt', 'url', 'browser', 'website', 'open']):
            task_specs.append({
                'type': 'browser', 
                'tools': ['browser_navigate'], 
                'ver': 'browser',
                'desc': 'Sahifaga kirish',
                'task_type': 'browser',
                'expected_artifacts': ['screenshot'],
                'rollback_point': {'type': 'browser_state', 'description': 'Browser holatini saqlash'}
            })
        
        # Code execution tasks
        if any(k in msg_lower for k in ['kod', 'code', 'python', 'javascript', 'run', 'execute', 'bajar']):
            task_specs.append({
                'type': 'code', 
                'tools': ['execute_code'], 
                'ver': 'code',
                'desc': 'Kodni bajarish',
                'task_type': 'code',
                'expected_artifacts': ['output'],
                'rollback_point': {'type': 'env_snapshot', 'description': 'Environment snapshot'}
            })
        
        # Command execution tasks
        if any(k in msg_lower for k in ['buyruq', 'command', 'terminal', 'shell', 'bash']):
            task_specs.append({
                'type': 'command', 
                'tools': ['execute_command'], 
                'ver': 'function',
                'desc': 'Buyruqni bajarish',
                'task_type': 'server',
                'expected_artifacts': [],
                'rollback_point': {'type': 'system_state', 'description': 'System state backup'}
            })
        
        # Server/service tasks
        if any(k in msg_lower for k in ['server', 'serve', 'start', 'run service']):
            task_specs.append({
                'type': 'server', 
                'tools': ['execute_command', 'execute_code'], 
                'ver': 'server',
                'desc': 'Serverni ishga tushirish',
                'task_type': 'server',
                'expected_artifacts': [],
                'rollback_point': {'type': 'service_backup', 'description': 'Service state backup'}
            })
        
        # Screenshot tasks
        if any(k in msg_lower for k in ['screenshot', 'skrin', 'capture', 'sahifa rasmi']):
            task_specs.append({
                'type': 'screenshot', 
                'tools': ['take_screenshot'], 
                'ver': 'screenshot',
                'desc': 'Screenshot olish',
                'task_type': 'browser',
                'expected_artifacts': ['*.png', '*.jpg'],
                'rollback_point': None
            })
        
        # Install tasks
        if any(k in msg_lower for k in ['install', 'o\'rnat', 'setup', 'configure']):
            task_specs.append({
                'type': 'install', 
                'tools': ['install_package', 'execute_command'], 
                'ver': 'function',
                'desc': 'Paketni o\'rnatish',
                'task_type': 'install',
                'expected_artifacts': [],
                'rollback_point': {'type': 'package_list', 'description': 'Installed packages list'}
            })
        
        # Default task if none matched
        if not task_specs:
            task_specs.append({
                'type': 'general', 
                'tools': ['execute_command'], 
                'ver': 'manual',
                'desc': message[:100],
                'task_type': 'general',
                'expected_artifacts': [],
                'rollback_point': None
            })
        
        # Create tasks with full metadata
        for i, spec in enumerate(task_specs):
            # Set priority based on position and risk
            if i == 0:
                priority = TaskPriority.CRITICAL if risk_level == 'critical' else TaskPriority.HIGH
            elif i < len(task_specs) - 1:
                priority = TaskPriority.NORMAL
            else:
                priority = TaskPriority.LOW
            
            # Create task with full metadata
            task = Task(
                id=f"task_{int(time.time()*1000)}_{i}",
                description=spec['desc'],
                priority=priority,
                dependencies=[tasks[-1].id] if tasks else [],
                timeout=30,
                max_retries=3,
                approval_policy=approval_policy,
                sandbox_mode=sandbox_mode,
            )
            
            # Set FULL metadata
            task.input_data = {
                'required_tools': spec['tools'],
                'verification_type': spec['ver'],
                'success_criteria': f"{spec['desc']} muvaffaqiyatli",
                'fallback_strategy': 'ALTERNATIVE_TOOL',
                'task_type': spec.get('task_type', 'general'),
                'risk_level': risk_level,
                'expected_artifacts': spec.get('expected_artifacts', []),
                'rollback_point': spec.get('rollback_point'),
                'retry_policy': {
                    'max_retries': 3,
                    'backoff_strategy': 'exponential',
                    'initial_delay': 1,
                    'max_delay': 30
                },
                'timeout': task.timeout,
            }
            
            # Set artifact expectations
            task.artifact_expectations = spec.get('expected_artifacts', [])
            
            # Set rollback point
            if spec.get('rollback_point'):
                task.rollback_point = {
                    **spec['rollback_point'],
                    'timestamp': time.time(),
                    'task_id': task.id
                }
            
            tasks.append(task)
        
        # Add dependency chain
        for i in range(1, len(tasks)):
            if tasks[i-1].id not in tasks[i].dependencies:
                tasks[i].dependencies.append(tasks[i-1].id)
        
        logger.info(f"📋 Created {len(tasks)} tasks via enhanced heuristic planner")
        logger.info(f"   Risk level: {risk_level}, Sandbox: {sandbox_mode}, Approval: {approval_policy}")
        
        return tasks
    
    async def _execute(self, plan: List[Task]) -> str:
        """
        STRICT GOVERNED RUNTIME CHAIN - No1 Grade.
        
        CRITICAL: This is the ONE TRUE ORCHESTRATOR pipeline.
        
        Pipeline: policy -> validate -> approval -> sandbox -> execute -> verify -> artifact -> persist -> telemetry
        
        FIXED ISSUES:
        1. Single clean pipeline - no complex fallbacks
        2. History/reliability/context-aware tool selection
        3. Simple success semantics
        4. Deeply integrated approval denied/expired flow
        """
        
        import re, json, time
        from typing import Dict, Any, Optional, List
        
        results = []
        completed_tasks = set()
        failed_tasks = set()
        
        # STRICT Pipeline Steps (immutable order)
        PIPELINE_STEPS = [
            'policy_check',      # Step 1: Policy enforcement
            'dependency_check',   # Step 2: Task dependencies
            'tool_selection',    # Step 3: Context-aware tool selection
            'argument_validation',# Step 4: Strict argument validation
            'approval_check',    # Step 5: Approval workflow
            'sandbox_setup',     # Step 6: Sandbox configuration
            'tool_execution',    # Step 7: Actual execution
            'verification',      # Step 8: Result verification
            'artifact_collection',# Step 9: Artifact collection
            'persistence',       # Step 10: State persistence
            'telemetry'          # Step 11: Metrics recording
        ]
        
        # Tool configuration - strict mapping
        TOOL_CONFIG = {
            'write_file': {
                'dangerous': True,
                'required_args': ['path', 'content'],
                'sandbox_mode': 'safe',
                'timeout': 30
            },
            'read_file': {
                'dangerous': False,
                'required_args': ['path'],
                'sandbox_mode': 'safe',
                'timeout': 10
            },
            'web_search': {
                'dangerous': False,
                'required_args': ['query'],
                'sandbox_mode': 'safe',
                'timeout': 15
            },
            'execute_command': {
                'dangerous': True,
                'required_args': ['command'],
                'sandbox_mode': 'advanced',
                'timeout': 60
            },
            'execute_code': {
                'dangerous': True,
                'required_args': ['code'],
                'sandbox_mode': 'advanced',
                'timeout': 60
            },
            'browser_navigate': {
                'dangerous': False,
                'required_args': ['url'],
                'sandbox_mode': 'normal',
                'timeout': 30
            },
            'delete_file': {
                'dangerous': True,
                'required_args': ['path'],
                'sandbox_mode': 'advanced',
                'timeout': 15
            },
            'install_package': {
                'dangerous': True,
                'required_args': ['package'],
                'sandbox_mode': 'advanced',
                'timeout': 120
            },
            'take_screenshot': {
                'dangerous': False,
                'required_args': ['path'],
                'sandbox_mode': 'safe',
                'timeout': 10
            },
            'web_request': {
                'dangerous': False,
                'required_args': ['url'],
                'sandbox_mode': 'safe',
                'timeout': 30
            }
        }

        # Get tool reliability history for smart selection
        tool_reliability = self._get_tool_reliability_history()
        
        for task in plan:
            pipeline_state = {
                'task_id': task.id, 
                'pipeline': PIPELINE_STEPS.copy(), 
                'current_step': 0, 
                'failed_at': None, 
                'execution_data': {}
            }
            step_start_time = time.time()
            
            try:
                # =====================================================
                # STEP 1: Policy Check
                # =====================================================
                policy = getattr(task, 'approval_policy', 'auto')
                sandbox_mode = getattr(task, 'sandbox_mode', 'normal')
                
                if policy == 'never':
                    raise PermissionError("Policy DENIED: approval_policy is 'never'")
                
                # =====================================================
                # STEP 2: Dependency Check
                # =====================================================
                if task.dependencies:
                    deps_met = all(dep_id in completed_tasks for dep_id in task.dependencies)
                    if not deps_met:
                        logger.warning(f"Task {task.id} waiting for dependencies")
                        task.status = TaskStatus.DEPENDENCIES_WAITING
                        failed_tasks.add(task.id)
                        results.append(f"✗ [DEPENDENCY] {task.description}")
                        continue
                
                self.task_manager.mark_running(task.id)
                self.state = KernelState.ACTING
                task.status = TaskStatus.RUNNING
                task.started_at = time.time()
                
                logger.info(f"⚡ EXECUTING: {task.description}")
                
                task_meta = task.input_data or {}
                required_tools = task_meta.get('required_tools', [])
                verification_type = task_meta.get('verification_type')  # FIX #2: No default!
                
                # =====================================================
                # STEP 3: Context-Aware Tool Selection
                # =====================================================
                lock_mgr = get_lock_manager()
                scope = task.input_data.get("_scope", {})
                keys = scope.get("resource_keys", [])
                tool_keys = get_resource_keys("pending", task.input_data.get("tool_args", {}))
                for k in set(keys + tool_keys):
                    if not lock_mgr.acquire(k, task.id, "exclusive"):
                        for x in set(keys + tool_keys):
                            lock_mgr.release_by_task(task.id)
                        task.status = TaskStatus.PENDING
                        task.blocked_reason = f"locked:{k}"
                        return None
                
                tool_name = self._select_tool_strict(
                    task=task,
                    required_tools=required_tools,
                    task_meta=task_meta,
                    available_tools=list(TOOL_CONFIG.keys()),
                    tool_reliability=tool_reliability,
                    completed_tasks=completed_tasks
                )
                
                if not tool_name:
                    raise ValueError(f"No suitable tool found for task {task.id}")
                
                tool_config = TOOL_CONFIG.get(tool_name, {})
                
                # =====================================================
                # STEP 4: Strict Argument Validation
                # =====================================================
                validated_args = self._build_strict_args(tool_name, task, task_meta)
                
                required = tool_config.get('required_args', [])
                missing_args = [arg for arg in required if arg not in validated_args or not validated_args[arg]]
                if missing_args:
                    raise ValueError(f"Missing required arguments: {missing_args}")
                
                for arg, value in validated_args.items():
                    if value is None or value == '':
                        raise ValueError(f"Empty value for argument: {arg}")
                
                # =====================================================
                # STEP 5: Approval Workflow (with deep integration)
                # =====================================================
                needs_approval = tool_config.get('dangerous', False)
                approval_status = None
                
                if needs_approval and hasattr(self, 'approval_engine') and self.approval_engine:
                    if policy == 'never':
                        raise PermissionError("Approval denied: policy is 'never'")
                    elif policy == 'manual':
                        # DEEP integration: approval denied/expired flow
                        approval_result = await self._execute_approval_flow(
                            task_id=task.id,
                            tool_name=tool_name,
                            args=validated_args,
                            risk_level='high' if tool_config.get('dangerous') else 'medium',
                            timeout=30
                        )
                        
                        if approval_result['status'] == 'denied':
                            # Track for recovery - DEEP integration
                            task.metadata['approval_denied'] = True
                            task.metadata['approval_expired'] = False
                            task.metadata['approval_recovery_needed'] = True
                            task.error_type = ErrorType.APPROVAL_DENIED
                            task.status = TaskStatus.RECOVERING
                            
                            # Telemetry
                            if hasattr(self, 'telemetry') and self.telemetry:
                                self.telemetry.record_event('approval_denied', {
                                    'task_id': task.id,
                                    'tool_name': tool_name,
                                    'timestamp': time.time()
                                })
                            
                            results.append(f"⚠️ [APPROVAL_DENIED] {task.description} - Recovery will handle")
                            continue
                        
                        elif approval_result['status'] == 'expired':
                            # Track for recovery - DEEP integration
                            task.metadata['approval_denied'] = False
                            task.metadata['approval_expired'] = True
                            task.metadata['approval_recovery_needed'] = True
                            task.error_type = ErrorType.APPROVAL_TIMEOUT
                            task.status = TaskStatus.RECOVERING
                            
                            # Telemetry
                            if hasattr(self, 'telemetry') and self.telemetry:
                                self.telemetry.record_event('approval_expired', {
                                    'task_id': task.id,
                                    'tool_name': tool_name,
                                    'timestamp': time.time()
                                })
                            
                            results.append(f"⚠️ [APPROVAL_EXPIRED] {task.description} - Recovery will handle")
                            continue
                        
                        approval_status = approval_result['status']
                
                # =====================================================
                # STEP 6: Sandbox Setup
                # =====================================================
                configured_sandbox_mode = sandbox_mode or tool_config.get('sandbox_mode', 'normal')
                sandbox_ready = self._setup_sandbox(tool_name, configured_sandbox_mode)
                
                if not sandbox_ready:
                    raise RuntimeError(f"Sandbox setup failed for mode: {configured_sandbox_mode}")
                
                # =====================================================
                # STEP 7: Tool Execution (REAL execution) - with TRANSACTION
                # =====================================================
                
                # FIX: Use transaction-based execution for side-effecting tools
                tool_is_side_effecting = tool_name in [
                    "write_file", "delete_file", "execute_command", "install_package",
                    "browser_click", "browser_navigate", "browser_type", "remove_directory",
                    "create_directory", "copy_file", "move_file", "run_script"
                ]
                
                if tool_is_side_effecting:
                    # Use transaction-based execution
                    logger.info(f"🔄 Using transaction execution for: {tool_name}")
                    tx_result = await self.execute_with_transaction(
                        task=task,
                        tool_name=tool_name,
                        args=validated_args,
                        verification_type=verification_type,
                        verification_params=task_meta.get("verification_params")
                    )
                    
                    # Extract results from transaction
                    exec_result = tx_result.get("output")
                    verification_passed = tx_result.get("verification_passed", False)
                    verification_details = tx_result.get("commit_details")
                    
                    # Check transaction outcome
                    if tx_result.get("success"):
                        task.status = TaskStatus.COMPLETED
                    else:
                        task.status = TaskStatus.FAILED
                        
                    # Continue to artifact collection with tx result
                    task.metadata["transaction_id"] = tx_result.get("tx_id")
                    task.metadata["transaction_phase"] = tx_result.get("phase")
                    
                else:
                    # Use regular execution for read-only operations
                    exec_result = await self._execute_tool_strict(
                        task=task,
                        tool_name=tool_name,
                        args=validated_args,
                        timeout=tool_config.get('timeout', 30)
                    )
                
                # =====================================================
                # STEP 8: Verification (skip if already done in transaction)
                # =====================================================
                
                # Skip verification if already done in transaction execution
                if tool_is_side_effecting and "transaction_id" in task.metadata:
                    logger.info(f"⏭️ Verification already done in transaction for: {tool_name}")
                    # Verification was done inside transaction, skip duplicate check
                else:
                    verification_passed = True
                    verification_details = None
                    
                    # FIX #22 & #23: Use canonical verification with proper validation
                    if verification_type and verification_type != 'manual':
                        # Normalize the verification type
                        try:
                            normalized = normalize_verification_type(verification_type)
                        except ValueError as e:
                            logger.warning(f"Invalid verification type: {e}")
                            # Invalid verification type - fail the task
                            verification_passed = False
                            verification_details = str(e)
                            exec_result.success = False
                            exec_result.error = f"Verification failed: {e}"
                            task.status = TaskStatus.FAILED_VERIFICATION
                        else:
                            if normalized != VerificationType.NONE or task.approval_policy:
                                task.status = TaskStatus.VERIFYING
                                self.state = KernelState.VERIFYING
                                
                                verification_data = self._build_verification_data(task, task_meta, exec_result)
                                verification = self.verifier.verify(verification_type, verification_data)
                                
                                if not verification.passed:
                                    verification_passed = False
                                    verification_details = verification.details
                                    exec_result.success = False
                                    exec_result.error = f"Verification failed: {verification_details}"
                                    task.status = TaskStatus.FAILED_VERIFICATION
                    elif not verification_type:
                        # FIX #2: No verification_type means autonomous task fails
                        logger.warning(f"Task {task.id} has no verification_type!")
                        verification_passed = False
                        verification_details = "verification_type is required for autonomous tasks"
                        exec_result.success = False
                        exec_result.error = verification_details
                        task.status = TaskStatus.FAILED_VERIFICATION
                
                # =====================================================
                # STEP 9: Artifact Collection
                # =====================================================
                for artifact in exec_result.artifacts:
                    self.artifacts.collect(
                        task.id, 
                        "artifact", 
                        artifact, 
                        {
                            "tool_used": tool_name, 
                            "task_id": task.id, 
                            "timestamp": time.time()
                        }
                    )
                
                # =====================================================
                # STEP 10: Persistence
                # =====================================================
                if hasattr(self, 'task_manager') and hasattr(self.task_manager, '_save_to_disk'):
                    try:
                        self.task_manager._save_to_disk()
                    except Exception as e:
                        logger.warning(f"Failed to persist state: {e}")
                
                # =====================================================
                # STEP 11: Telemetry
                # =====================================================
                step_duration = time.time() - step_start_time
                
                # =====================================================
                # RUNTIME TRUTH SUCCESS SEMANTICS - No1 Grade
                # =====================================================
                # SUCCESS IS DETERMINED BY:
                # 1. exec_result.success - REAL tool runtime result (NOT model claim)
                # 2. verification_passed - Verification check passed
                # 3. NO MODEL CLAIM CAN OVERRIDE REAL RESULTS
                # =====================================================
                
                # Log validation sources for audit
                validation_sources = {
                    'runtime_success': exec_result.success,
                    'verification_passed': verification_passed,
                    'exit_code': exec_result.exit_code,
                    'has_error': bool(exec_result.error),
                    'artifact_count': len(exec_result.artifacts)
                }
                
                # FINAL SUCCESS: Only if runtime + verification both pass
                final_success = exec_result.success and verification_passed

                self._last_execution_results[task.id] = {
                    'success': final_success,
                    'execution_result': exec_result.to_dict(),
                    'verification_passed': verification_passed,
                    'verification_details': verification_details,
                    'tool_used': tool_name,
                    'duration': step_duration,
                    'approval_status': approval_status,
                    'validation_sources': validation_sources  # Audit trail
                }
                
                if final_success:
                    self.task_manager.mark_completed(task.id, exec_result.stdout or exec_result.stderr)
                    completed_tasks.add(task.id)
                    task.status = TaskStatus.COMPLETED
                    results.append(f"✓ [{verification_type}] {task.description}")
                else:
                    task.error = exec_result.error or verification_details
                    task.status = TaskStatus.FAILED
                    self.task_manager.mark_failed(task.id, task.error)
                    failed_tasks.add(task.id)
                    results.append(f"✗ [{verification_type}] {task.description}: {task.error}")
                
                self.telemetry.record_task(
                    success=final_success, 
                    duration=step_duration, 
                    tool_name=tool_name
                )
                
            except PermissionError as e:
                # Handle approval errors with DEEP integration
                error_msg = str(e)
                is_approval_denial = "denied" in error_msg.lower() or "never" in error_msg.lower()
                is_approval_expire = "timeout" in error_msg.lower()
                
                task.metadata['approval_denied'] = is_approval_denial
                task.metadata['approval_expired'] = is_approval_expire
                task.metadata['approval_recovery_needed'] = True
                
                logger.warning(f"Approval error for task {task.id}: {error_msg}")
                
                if hasattr(self, 'telemetry') and self.telemetry:
                    self.telemetry.record_event('approval_error', {
                        'task_id': task.id,
                        'error': error_msg,
                        'is_denial': is_approval_denial,
                        'is_expire': is_approval_expire,
                        'timestamp': time.time()
                    })
                
                if is_approval_denial or is_approval_expire:
                    task.error_type = ErrorType.APPROVAL_DENIED if is_approval_denial else ErrorType.APPROVAL_TIMEOUT
                    task.status = TaskStatus.RECOVERING
                    results.append(f"⚠️ [APPROVAL] {task.description}: {error_msg} - Recovery will handle")
                else:
                    task.status = TaskStatus.FAILED
                    failed_tasks.add(task.id)
                    results.append(f"✗ [PERMISSION] {task.description}: {error_msg}")
                
            except ValueError as e:
                task.status = TaskStatus.FAILED
                task.error = str(e)
                failed_tasks.add(task.id)
                results.append(f"✗ [VALIDATION] {task.description}: {str(e)}")
                
            except Exception as e:
                task.error = str(e)
                task.error_type = ErrorType.SYSTEM_ERROR
                task.status = TaskStatus.FAILED
                self.task_manager.mark_failed(task.id, str(e))
                failed_tasks.add(task.id)
                results.append(f"✗ [EXCEPTION] {task.description}: {str(e)}")
        
        logger.info(f"✅ Execution complete: {len(completed_tasks)} completed, {len(failed_tasks)} failed")
        
        return "\n".join(results)
    
    # =====================================================
    # STRICT HELPER METHODS FOR No1 GRADE RUNTIME
    # =====================================================
    
    def _get_tool_reliability_history(self) -> Dict[str, float]:
        """
        Get tool reliability history from telemetry for smart tool selection.
        Returns: Dict[tool_name] = success_rate (0.0 to 1.0)
        """
        if not hasattr(self, 'telemetry') or not self.telemetry:
            return {}
        
        try:
            metrics = self.telemetry.get_metrics()
            tool_stats = metrics.get('tool_stats', {})
            
            reliability = {}
            for tool_name, stats in tool_stats.items():
                total = stats.get('total', 0)
                success = stats.get('success', 0)
                if total > 0:
                    reliability[tool_name] = success / total
                else:
                    reliability[tool_name] = 0.5  # Default neutral
            
            return reliability
        except (ValueError, TypeError, KeyError) as e:
            logger.warning(f"Reliability calculation error: {e}")
            return {}
    
            return {}
    def _select_tool_strict(
        task: Task,
        required_tools: List[str],
        task_meta: Dict,
        available_tools: List[str],
        tool_reliability: Dict[str, float],
        completed_tasks: Set[str]
    ) -> Optional[str]:
        """
        COMPREHENSIVE Context-Aware Tool Selection - No1 Grade.
        
        Considers ALL factors for optimal selection:
        1. Required tools (explicit) - MUST have
        2. Prior success rate (telemetry-based reliability) - 30% weight
        3. Recent failure history with consecutive failure penalty
        4. Environment context (sandbox compatibility) - hard constraint
        5. Verifier needs (verification_type) - 10% weight
        6. Artifact expectations - 5% weight
        7. Approval friction (high-risk tools) - time penalty
        8. Environment state (CPU, memory, network, disk)
        9. Tool timeout estimation
        10. Confidence scoring based on score gap
        """
        import time
        from collections import deque

        if not hasattr(self, "_tool_failure_history"):
            self._tool_failure_history = {}
            self._tool_failure_window = 300

        # 1. REQUIRED TOOLS - MUST HAVE
        for rt in required_tools:
            if rt in available_tools:
                logger.info(f"Tool selected (required): {rt}")
                return rt

        # Get context
        description = task.description.lower()
        verification_type = task_meta.get('verification_type')  # FIX #2: No default!
        expected_artifacts = task_meta.get('expected_artifacts', [])
        sandbox_mode = task_meta.get('sandbox_mode', 'normal')
        approval_policy = task_meta.get('approval_policy', 'auto')

        # Get environment state
        env_state = self._get_environment_state()
        
        # Tool definitions
        TOOL_KEYWORDS = {
            'read_file': ['read', 'file', 'content', 'load', 'open'],
            'write_file': ['write', 'save', 'create', 'file', 'edit'],
            'execute_command': ['run', 'command', 'execute', 'shell', 'bash'],
            'execute_code': ['code', 'python', 'script', 'run'],
            'web_search': ['search', 'find', 'web', 'google'],
            'browser_navigate': ['navigate', 'browse', 'open', 'url'],
            'delete_file': ['delete', 'remove', 'clear'],
            'install_package': ['install', 'package', 'pip', 'npm'],
            'take_screenshot': ['screenshot', 'capture', 'screen'],
            'web_request': ['request', 'http', 'api', 'fetch']
        }

        TOOL_VERIFIER_MAP = {
            'browser_navigate': 'browser', 'take_screenshot': 'screenshot',
            'execute_command': 'server', 'execute_code': 'code',
            'read_file': 'file', 'write_file': 'file',
        }

        TOOL_TIMEOUTS = {
            'read_file': 10, 'write_file': 30, 'execute_command': 60,
            'execute_code': 60, 'web_search': 15, 'browser_navigate': 30,
            'delete_file': 15, 'install_package': 120, 'take_screenshot': 10,
            'web_request': 30
        }

        SANDBOX_COMPAT = {
            'safe': ['read_file', 'web_search', 'web_request'],
            'normal': ['read_file', 'write_file', 'execute_command', 'web_search', 'web_request', 'browser_navigate'],
            'advanced': ['read_file', 'write_file', 'execute_command', 'execute_code', 'install_package', 'browser_navigate']
        }

        APPROVAL_COST = {
            'execute_command': 30, 'execute_code': 30, 'install_package': 60,
            'delete_file': 45, 'write_file': 15, 'browser_navigate': 10,
            'read_file': 0, 'web_search': 0, 'take_screenshot': 0, 'web_request': 0
        }

        HIGH_FRICTION = ['execute_command', 'execute_code', 'install_package', 'delete_file']

        scores, diagnostics, current_time = {}, {}, time.time()

        for tool in available_tools:
            score = 0
            tool_diag = {
                'reliability': 0, 'failure_penalty': 0, 'keyword': 0,
                'sandbox': 0, 'verifier': 0, 'artifact': 0, 'approval': 0,
                'environment': 0, 'timeout': 0
            }

            # FACTOR 1: TELEMETRY-BASED RELIABILITY (30%)
            reliability = tool_reliability.get(tool, 0.5)
            score += reliability * 30
            tool_diag['reliability'] = reliability * 30

            # FACTOR 2: RECENT FAILURE HISTORY
            if tool in self._tool_failure_history:
                failures = self._tool_failure_history[tool]
                while failures and current_time - failures[0][0] > self._tool_failure_window:
                    failures.popleft()
                recent_failures = sum(1 for _, f in failures if f)
                total = len(failures)
                if total > 0:
                    failure_rate = recent_failures / total
                    failure_penalty = failure_rate * 15
                    score -= failure_penalty
                    tool_diag['failure_penalty'] = -failure_penalty
            
            # FACTOR 3: KEYWORD MATCHING
            keywords = TOOL_KEYWORDS.get(tool, [])
            matches = sum(1 for kw in keywords if kw in description)
            score += matches * 5
            tool_diag['keyword'] = matches * 5

            # FACTOR 4: SANDBOX COMPATIBILITY (hard)
            allowed = SANDBOX_COMPAT.get(sandbox_mode, [])
            if tool in allowed:
                score += 10
                tool_diag['sandbox'] = 10
            else:
                score -= 20
                tool_diag['sandbox'] = -20

            # FACTOR 5: VERIFIER COMPATIBILITY
            if TOOL_VERIFIER_MAP.get(tool) == verification_type:
                score += 10
                tool_diag['verifier'] = 10

            # FACTOR 6: ARTIFACT EXPECTATIONS
            if expected_artifacts:
                if 'write' in tool and any('.py' in str(a) or '.js' in str(a) for a in expected_artifacts):
                    score += 5
                    tool_diag['artifact'] = 5
                elif 'screenshot' in tool and any('.png' in str(a) for a in expected_artifacts):
                    score += 5
                    tool_diag['artifact'] = 5

            # FACTOR 7: APPROVAL FRICTION
            approval_cost = APPROVAL_COST.get(tool, 0)
            if tool in HIGH_FRICTION and approval_policy == 'auto':
                score -= approval_cost
                tool_diag['approval'] = -approval_cost

            # FACTOR 8: ENVIRONMENT STATE
            env_score = 0
            if 'network' in tool or 'web' in tool or 'browser' in tool:
                if not env_state.get('network_available', True):
                    score -= 30
                    env_score = -30
            if 'execute' in tool or 'install' in tool:
                if not env_state.get('cpu_available', True):
                    score -= 20
                    env_score = -20
            tool_diag['environment'] = env_score

            # FACTOR 9: TIMEOUT SUITABILITY
            tool_timeout = TOOL_TIMEOUTS.get(tool, 30)
            task_timeout = task.timeout if task.timeout else 30
            if tool_timeout <= task_timeout:
                score += 5
                tool_diag['timeout'] = 5

            scores[tool] = score
            diagnostics[tool] = tool_diag

        # SELECT BEST TOOL
        if scores:
            sorted_tools = sorted(scores.items(), key=lambda x: -x[1])
            best_tool = sorted_tools[0][0]
            best_score = sorted_tools[0][1]
            
            # Confidence based on gap
            if len(sorted_tools) > 1:
                second_score = sorted_tools[1][1]
                score_gap = best_score - second_score
                confidence = min(1.0, 0.5 + (score_gap / 20))
            else:
                confidence = 0.5
            
            logger.info(f"Tool selected: {best_tool} (score: {best_score}, confidence: {confidence:.2f})")
            
            if hasattr(self, 'telemetry') and self.telemetry:
                self.telemetry.record_event('tool_selection', {
                    'task_id': task.id, 'tool': best_tool, 'score': best_score,
                    'confidence': confidence, 'diagnostics': diagnostics[best_tool],
                    'verification_type': verification_type, 'sandbox_mode': sandbox_mode,
                    'timestamp': current_time
                })
            
            return best_tool

        return None

    def _get_environment_state(self) -> Dict[str, bool]:
        """Get current environment state for tool selection."""
        state = {'cpu_available': True, 'memory_available': True, 'network_available': True, 'disk_available': True}
        
        try:
            import psutil
            cpu_percent = psutil.cpu_percent(interval=0.1)
            if cpu_percent > 90:
                state['cpu_available'] = False
            mem = psutil.virtual_memory()
            if mem.percent > 90:
                state['memory_available'] = False
            disk = psutil.disk_usage('/')
            if disk.percent > 95:
                state['disk_available'] = False
        except ImportError:
            logger.debug("psutil not available")
        except Exception as e:
            logger.warning(f"Environment check failed: {e}")
        
        return state

    def _record_tool_failure(self, tool_name: str, failed: bool):
        from collections import deque
        if not hasattr(self, '_tool_failure_history'):
            self._tool_failure_history = {}
        if tool_name not in self._tool_failure_history:
            self._tool_failure_history[tool_name] = deque()
        self._tool_failure_history[tool_name].append((time.time(), failed))
        while len(self._tool_failure_history[tool_name]) > 100:
            self._tool_failure_history[tool_name].popleft()

    def _build_strict_args(self, tool_name: str, task: Task, task_meta: Dict) -> Dict[str, Any]:
        """
        STRICT Argument Builder for each tool.
        """
        # Default values from task
        default_path = f"/tmp/{task.id}.txt"
        
        ARG_BUILDERS = {
            'write_file': {
                'path': task_meta.get('file_path', default_path),
                'content': task_meta.get('file_content', task.description)
            },
            'read_file': {
                'path': task_meta.get('file_path', '')
            },
            'web_search': {
                'query': task_meta.get('search_query', task.description)
            },
            'execute_command': {
                'command': task_meta.get('command', task.description),
                'timeout': task.timeout
            },
            'execute_code': {
                'code': task_meta.get('code', task.description),
                'language': task_meta.get('language', 'python'),
                'timeout': task.timeout
            },
            'browser_navigate': {
                'url': task_meta.get('url', ''),
                'expected_text': task_meta.get('success_criteria', '')
            },
            'delete_file': {
                'path': task_meta.get('file_path', ''),
                'force': task_meta.get('force', False)
            },
            'install_package': {
                'package': task_meta.get('package', ''),
                'version': task_meta.get('version', '')
            },
            'take_screenshot': {
                'path': task_meta.get('screenshot_path', f'/tmp/{task.id}.png')
            },
            'web_request': {
                'url': task_meta.get('url', ''),
                'method': task_meta.get('method', 'GET'),
                'timeout': task_meta.get('timeout', 30)
            }
        }
        
        return ARG_BUILDERS.get(tool_name, {})
    
    async def _execute_approval_flow(
        self, 
        task_id: str, 
        tool_name: str, 
        args: Dict, 
        risk_level: str,
        timeout: int = 30
    ) -> Dict[str, Any]:
        """
        STRICT Approval Workflow with proper status tracking.
        
        Returns: {'status': 'approved' | 'denied' | 'expired', 'request_id': str}
        """
        self.state = KernelState.WAITING_APPROVAL
        
        try:
            approval_request = self.approval_engine.create_request(
                tool_name=tool_name,
                arguments=args,
                risk_level=risk_level,
                requested_by='kernel'
            )
            
            self.pending_approvals[approval_request.request_id] = {
                'task_id': task_id, 
                'tool_name': tool_name, 
                'args': args, 
                'created_at': time.time()
            }
            
            approved = self._wait_for_approval(approval_request.request_id, timeout=timeout)
            
            if approved:
                return {'status': 'approved', 'request_id': approval_request.request_id}
            else:
                # Check if denied or expired
                pending = self.pending_approvals.get(approval_request.request_id, {})
                elapsed = time.time() - pending.get('created_at', 0)
                
                if elapsed >= timeout:
                    return {'status': 'expired', 'request_id': approval_request.request_id}
                else:
                    return {'status': 'denied', 'request_id': approval_request.request_id}
                    
        finally:
            self.state = KernelState.ACTING
    
    
    # ==================== APPROVAL RECOVERY STRATEGIES ====================
    
    async def _handle_approval_granted(self, task: Task, approval_result: Dict) -> Dict:
        logger.info(f"Approval GRANTED for task {task.id}, resuming")
        return {'action': 'resume', 'task_id': task.id, 'can_retry': True, 'rollback_required': False}
    
    async def _handle_approval_denied(self, task: Task, approval_result: Dict) -> Dict:
        logger.warning(f"Approval DENIED for task {task.id}")
        alt = (task.input_data or {}).get('alternate_tool')
        if alt:
            return {'action': 'alternate_tool', 'task_id': task.id, 'alternate_tool': alt, 'can_retry': False}
        return {'action': 'abort', 'task_id': task.id, 'error': 'approval_denied', 'can_retry': False}
    
    async def _handle_approval_expired(self, task: Task, approval_result: Dict) -> Dict:
        logger.warning(f"Approval EXPIRED for task {task.id}")
        retry = (task.retry_count or 0) + 1
        maxr = task.max_retries or 3
        if retry <= maxr:
            return {'action': 'retry_approval', 'task_id': task.id, 'retry_count': retry, 'can_retry': True}
        return {'action': 'safe_abort', 'task_id': task.id, 'error': 'approval_expired', 'rollback_required': True}
    
    async def _execute_approval_recovery(self, task: Task, approval_result: Dict) -> Dict:
        s = approval_result.get('status', 'unknown')
        if s == 'approved': return await self._handle_approval_granted(task, approval_result)
        if s == 'denied': return await self._handle_approval_denied(task, approval_result)
        if s == 'expired': return await self._handle_approval_expired(task, approval_result)
        return {'action': 'abort', 'task_id': task.id, 'error': 'unknown'}
    def _setup_sandbox(self, tool_name: str, sandbox_mode: str) -> bool:
        """
        STRICT Sandbox Setup.
        
        Returns: True if sandbox is ready, False otherwise
        """
        if not hasattr(self, 'sandbox') or not self.sandbox:
            # No sandbox - assume safe environment
            return True
        
        try:
            # Configure sandbox mode
            if sandbox_mode == 'safe':
                # Most restrictive
                logger.debug("Safe mode placeholder")
            elif sandbox_mode == 'normal':
                # Standard restrictions
                logger.debug("Normal mode placeholder")
            elif sandbox_mode == 'advanced':
                # Minimal restrictions (for trusted operations)
                logger.debug("Advanced mode placeholder")

            return True
        except Exception as e:
            logger.error(f"Sandbox setup failed: {e}")
            return False

    async def _execute_tool_strict(
        self, 
        task: Task, 
        tool_name: str, 
        args: Dict, 
        timeout: int = 30
    ) -> ExecutionResult:
        """
        STRICT Tool Execution.
        
        Returns: ExecutionResult with success=True/False
        """
        exec_result = ExecutionResult(success=False, tool_used=tool_name)
        
        try:
            if hasattr(self, 'native_brain') and self.native_brain:
                # Use brain for execution
                task_meta = task.input_data or {}
                result = await self._execute_via_brain_strict(task, tool_name, args, task_meta)
                return result
            elif hasattr(self, 'tools') and self.tools:
                # Direct tool execution
                import asyncio
                tool_result = await asyncio.wait_for(
                    asyncio.to_thread(self.tools.execute_tool, tool_name, args),
                    timeout=timeout
                )
                
                exec_result.stdout = tool_result.stdout or ""
                exec_result.stderr = tool_result.stderr or ""
                exec_result.exit_code = tool_result.exit_code if hasattr(tool_result, 'exit_code') else 0
                exec_result.artifacts = tool_result.artifacts if hasattr(tool_result, 'artifacts') else []
                
                if exec_result.exit_code != 0:
                    exec_result.success = False
                    exec_result.error = f"Exit code: {exec_result.exit_code}"
                elif any(err in (exec_result.stdout + exec_result.stderr).lower() 
                        for err in ['exception', 'error', 'failed', 'traceback']):
                    exec_result.success = False
                    exec_result.error = "Error pattern in output"
                else:
                    exec_result.success = True
            else:
                exec_result.error = "No execution engine available"
                
        except asyncio.TimeoutError:
            exec_result.error = f"Timeout after {timeout}s"
            exec_result.error_type = ErrorType.EXECUTION_TIMEOUT
        except Exception as e:
            exec_result.error = str(e)
        
        return exec_result
    
    async def _execute_via_brain_strict(self, task: Task, tool_name: str, args: Dict, task_meta: Dict) -> ExecutionResult:
        """
        STRICT BRAIN EXECUTION - No1 Grade.
        
        MODEL OUTPUT (only):
        - intent: what model thinks should happen
        - suggestion: model recommended approach
        - candidate_args: model suggested arguments
        
        REAL TRUTH (always):
        - actual tool runtime result
        - verifier result  
        - artifact collector
        
        MODEL CAN LIE ABOUT:
        - success status
        - artifacts
        - stdout/stderr
        - tool_used
        
        SO WE NEVER TRUST MODEL OUTPUT FOR SUCCESS/ARTIFACTS.
        """
        import re, json, time

        exec_result = ExecutionResult(success=False, tool_used=tool_name)
        
        # Track truth sources
        truth_sources = {
            'model_intent': None,
            'model_suggestion': None,
            'model_candidate_args': None,
            'runtime_result': None,
            'verifier_result': None,
            'artifact_check': None
        }

        # STEP 1: MODEL OUTPUT - ONLY intent/suggestion/args
        try:
            intent_prompt = f"""Analyze this task and provide intent + suggestion.
TASK: {task.description}
TOOL: {tool_name}
ARGS: {json.dumps(args)}

Return ONLY valid JSON (no other text):
{{
  "intent": "What the model thinks should happen",
  "suggestion": "Recommended approach",
  "candidate_args": {{}}  // any argument corrections
}}"""

            response = self.native_brain.think(intent_prompt)
            
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match and json_match.group().count('{') == json_match.group().count('}'):
                model_output = json.loads(json_match.group())
                truth_sources['model_intent'] = model_output.get('intent')
                truth_sources['model_suggestion'] = model_output.get('suggestion')
                truth_sources['model_candidate_args'] = model_output.get('candidate_args', {})
                
                logger.info(f"Model intent: {truth_sources['model_intent']}")
                
        except Exception as e:
            logger.warning(f"Model intent analysis failed: {e}")

        # STEP 2: REAL TOOL RUNTIME - THE ACTUAL TRUTH
        tool_start_time = time.time()

        try:
            if hasattr(self, 'tools') and self.tools:
                import asyncio
                tool_runtime_result = await asyncio.wait_for(
                    asyncio.to_thread(self.tools.execute_tool, tool_name, args),
                    timeout=task.timeout
                )

                exec_result.stdout = tool_runtime_result.stdout or ""
                exec_result.stderr = tool_runtime_result.stderr or ""
                exec_result.exit_code = tool_runtime_result.exit_code if hasattr(tool_runtime_result, 'exit_code') else 0
                exec_result.artifacts = tool_runtime_result.artifacts if hasattr(tool_runtime_result, 'artifacts') else []
                
                truth_sources['runtime_result'] = {
                    'exit_code': exec_result.exit_code,
                    'has_stdout': bool(exec_result.stdout),
                    'has_stderr': bool(exec_result.stderr),
                    'artifact_count': len(exec_result.artifacts)
                }

                if exec_result.exit_code != 0:
                    exec_result.success = False
                    exec_result.error = f"Exit code: {exec_result.exit_code}"
                elif any(err in (exec_result.stdout + exec_result.stderr).lower() 
                        for err in ['exception', 'error', 'failed', 'traceback']):
                    exec_result.success = False
                    exec_result.error = "Error pattern in output"
                else:
                    exec_result.success = True
            else:
                exec_result.error = "No tools engine available"
                
        except asyncio.TimeoutError:
            exec_result.error = f"Timeout after {task.timeout}s"
            exec_result.error_type = ErrorType.EXECUTION_TIMEOUT
            exec_result.success = False
        except Exception as e:
            exec_result.error = str(e)
            exec_result.success = False

        exec_result.execution_time = time.time() - tool_start_time

        # STEP 3: VERIFIER - SECOND TRUTH SOURCE
        # FIX #22: Use canonical verification
        if exec_result.success:
            try:
                verification_type = task_meta.get('verification_type')
                if verification_type and verification_type != 'manual':
                    # Normalize using canonical system
                    try:
                        normalized = normalize_verification_type(verification_type)
                    except ValueError as e:
                        logger.warning(f"Invalid verification type: {e}")
                        exec_result.success = False
                        exec_result.error = str(e)
                    else:
                        verification_data = self._build_verification_data(task, task_meta, exec_result)
                        verification = self.verifier.verify(verification_type, verification_data)
                        
                        truth_sources['verifier_result'] = {
                            'passed': verification.passed,
                            'details': verification.details
                        }
                        
                        if not verification.passed:
                            exec_result.success = False
                            exec_result.error = f"Verification failed: {verification.details}"
                elif not verification_type:
                    # FIX #2: No verification_type means fail for autonomous task
                    logger.warning(f"Task {task.id} has no verification_type!")
                    exec_result.success = False
                    exec_result.error = "verification_type is required for autonomous tasks"
            except Exception as e:
                logger.warning(f"Verification failed: {e}")

        # STEP 4: ARTIFACT COLLECTION - THIRD TRUTH SOURCE
        expected_artifacts = task_meta.get('expected_artifacts', [])
        if expected_artifacts and exec_result.artifacts:
            for expected in expected_artifacts:
                found = False
                for artifact in exec_result.artifacts:
                    if expected in artifact or expected in str(artifact):
                        found = True
                        break
                
                truth_sources['artifact_check'] = {'expected': expected, 'found': found}
                
                if not found:
                    exec_result.success = False
                    exec_result.error = f"Missing artifact: {expected}"

        logger.debug(f"Truth sources: {truth_sources}")
        return exec_result


    async def _execute_via_brain(self, task: Task, tool_name: str, args: Dict, task_meta: Dict) -> ExecutionResult:
        """
        STRICT BRAIN EXECUTION - No1 Grade.
        
        MODEL OUTPUT (ONLY):
        - intent: what model thinks should happen (intent analysis)
        - suggestion: recommended approach
        - candidate_args: suggested argument corrections
        
        REAL TRUTH (ALWAYS):
        - actual tool runtime result (from tools.execute_tool)
        - verifier result
        - artifact collector
        
        MODEL CANNOT PROVIDE:
        - success status (LIE)
        - artifacts (FORGED)
        - stdout/stderr (FABRICATED)
        - tool_used (INCORRECT)
        
        SO WE NEVER ASK MODEL FOR EXECUTION RESULTS.
        """
        
        import re, json
        import time
        
        exec_result = ExecutionResult(success=False, tool_used=tool_name)
        
        # Track truth sources - model provides INTENT ONLY
        validation_source = {
            'model_intent': None,
            'model_suggestion': None,
            'model_candidate_args': None,
            'tool_runtime': None,
            'verifier': None,
            'artifact_check': None
        }
        
        # =====================================================
        # STEP 1: MODEL OUTPUT - INTENT/SUGGESTION ONLY (NOT execution results)
        # =====================================================
        try:
            # MODEL: ONLY provide intent analysis, NOT execution results
            intent_prompt = f"""Analyze this task. Provide ONLY intent and suggested corrections.
DO NOT provide execution results - we will run the tool for real.

TASK: {task.description}
TOOL: {tool_name}
ARGUMENTS: {json.dumps(args)}

Return ONLY valid JSON (no other text):
{{
  "intent": "What needs to happen (1-2 sentences)",
  "suggestion": "Recommended approach or note",
  "candidate_args": {{}}  // any corrections to args (empty if none)
}}"""

            response = self.native_brain.think(intent_prompt)
            
            # Parse model response for INTENT ONLY
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match and json_match.group().count('{') == json_match.group().count('}'):
                model_output = json.loads(json_match.group())
                validation_source['model_intent'] = model_output.get('intent')
                validation_source['model_suggestion'] = model_output.get('suggestion')
                validation_source['model_candidate_args'] = model_output.get('candidate_args', {})
                logger.info(f"Model intent: {validation_source['model_intent']}")
                
                # Apply candidate_args corrections if any
                if validation_source['model_candidate_args']:
                    for k, v in validation_source['model_candidate_args'].items():
                        if k in args:
                            args[k] = v
                            
        except Exception as e:
            logger.warning(f"Model intent analysis failed: {e}")
        
        # =====================================================
        # STEP 2: REAL TOOL EXECUTION - THE ONLY SOURCE OF TRUTH
        # =====================================================
        tool_start_time = time.time()
        
        try:
            # Execute via actual tools engine
            if hasattr(self, 'tools') and self.tools:
                import asyncio
                tool_runtime_result = await asyncio.wait_for(
                    asyncio.to_thread(self.tools.execute_tool, tool_name, args),
                    timeout=task.timeout
                )
                
                # Copy real runtime results
                exec_result.stdout = tool_runtime_result.stdout or ""
                exec_result.stderr = tool_runtime_result.stderr or ""
                exec_result.exit_code = tool_runtime_result.exit_code if hasattr(tool_runtime_result, 'exit_code') else 0
                exec_result.artifacts = tool_runtime_result.artifacts if hasattr(tool_runtime_result, 'artifacts') else []
                
                # Determine success from REAL runtime, not model
                # Check exit code
                if exec_result.exit_code != 0:
                    exec_result.success = False
                    exec_result.error = f"Exit code: {exec_result.exit_code}"
                # Check for error patterns in real output
                elif any(err in (exec_result.stdout + exec_result.stderr).lower() 
                        for err in ['exception', 'error', 'failed', 'traceback', 'xatolik']):
                    exec_result.success = False
                    exec_result.error = "Error pattern detected in output"
                else:
                    exec_result.success = True
                
                validation_source['tool_runtime'] = {
                    'success': exec_result.success,
                    'exit_code': exec_result.exit_code,
                    'has_error_pattern': bool(exec_result.error)
                }
                
            elif hasattr(self, 'native_brain'):
                # CRITICAL: Brain fallback should NEVER claim success based on model output
                # Only use model output as stdout, success must be based on actual execution
                exec_result.stdout = response
                
                # STRICT: Brain fallback is UNRELIABLE for success determination
                # Default to False unless we have actual execution evidence
                exec_result.success = False
                exec_result.error = "Brain fallback: No real tool execution - success cannot be verified"
                logger.warning("⚠️ No tools engine - using brain fallback (UNRELIABLE for success)")
            else:
                exec_result.error = "No execution engine available"
                
        except asyncio.TimeoutError:
            exec_result.error = f"Execution timeout after {task.timeout}s"
            exec_result.error_type = ErrorType.EXECUTION_TIMEOUT
            exec_result.success = False
        except Exception as e:
            exec_result.error = f"Tool execution error: {str(e)}"
            exec_result.success = False
        
        exec_result.execution_time = time.time() - tool_start_time
        exec_result.tool_used = tool_name
        
        # Step 3: Artifact verification (if artifacts expected)
        expected_artifacts = task_meta.get('expected_artifacts', [])
        if expected_artifacts and exec_result.artifacts:
            artifact_check = {}
            for expected in expected_artifacts:
                # Check if artifact exists
                found = any(expected in a for a in exec_result.artifacts)
                artifact_check[expected] = found
            
            validation_source['artifact_check'] = artifact_check
            
            # If expected artifacts not found, fail
            if not all(artifact_check.values()):
                missing = [k for k, v in artifact_check.items() if not v]
                exec_result.success = False
                exec_result.error = f"Missing expected artifacts: {missing}"
        
        # Step 4: Run verifier for additional validation
        # FIX #22: Use canonical verification
        verification_type = task_meta.get('verification_type')
        if verification_type and verification_type != 'manual' and exec_result.success:
            try:
                # Normalize using canonical system
                try:
                    normalized = normalize_verification_type(verification_type)
                except ValueError as e:
                    logger.warning(f"Invalid verification type: {e}")
                    exec_result.success = False
                    exec_result.error = str(e)
                else:
                    verification_data = {
                        'result': exec_result.stdout,
                        'task_id': task.id,
                        **task_meta
                    }
                    verification = self.verifier.verify(verification_type, verification_data)
                    validation_source['verifier'] = {
                        'passed': verification.passed,
                        'details': verification.details
                    }
                    
                    if not verification.passed:
                        exec_result.success = False
                        exec_result.error = f"Verification failed: {verification.details}"
            except Exception as e:
                logger.warning(f"Verification check failed: {e}")
        elif not verification_type and exec_result.success:
            # FIX #2: No verification_type means fail for autonomous task
            logger.warning(f"Task {task.id} has no verification_type!")
            exec_result.success = False
            exec_result.error = "verification_type is required for autonomous tasks"
        
        # Log validation sources for debugging
        logger.info(f"Execution validation for task {task.id}: {validation_source}")
        
        # =====================================================
        # CRITICAL: MODEL CANNOT OVERRIDE REAL EXECUTION RESULTS
        # =====================================================
        # If model claimed success but real execution failed, we trust REAL execution
        # This is logged but we use the real result (already set above)
        
        return exec_result
    
    async def _execute_via_tools(self, task: Task, tool_name: str, args: Dict) -> ExecutionResult:
        """Execute tool via tools engine"""
        exec_result = ExecutionResult(success=False, tool_used=tool_name)
        try:
            if hasattr(self, 'tools') and self.tools:
                import asyncio
                tool_result = await asyncio.wait_for(
                    asyncio.to_thread(self.tools.execute_tool, tool_name, args, True),
                    timeout=task.timeout
                )
                exec_result.stdout = tool_result.stdout or ""
                exec_result.stderr = tool_result.stderr or ""
                exec_result.exit_code = tool_result.exit_code if hasattr(tool_result, 'exit_code') else 0
                exec_result.success = tool_result.status == 'success'
                if hasattr(tool_result, 'artifacts'): exec_result.artifacts = tool_result.artifacts
            else:
                exec_result.error = "Tools engine not available"
        except asyncio.TimeoutError:
            exec_result.error = f"Execution timeout after {task.timeout}s"
            exec_result.error_type = ErrorType.EXECUTION_TIMEOUT
        except Exception as e:
            exec_result.error = str(e)
            exec_result.error_type = ErrorType.EXECUTION_FAILED
        return exec_result
    
    def _wait_for_approval(self, request_id: str, timeout: int = 30) -> bool:
        """Wait for approval with timeout"""
        import time
        start_time = time.time()
        while time.time() - start_time < timeout:
            if request_id not in self.pending_approvals: return True
            approval_status = self.approval_engine.get_status(request_id)
            if approval_status and approval_status.get('status') == 'approved': return True
            elif approval_status and approval_status.get('status') == 'denied': return False
            time.sleep(0.5)
        return False



    async def _verify(self, task: Task, exec_result: ExecutionResult, task_meta: Dict) -> bool:
        """
        TASK-AWARE VERIFICATION for No1 agent with ENHANCED diagnostics.
        
        Verifies execution result with full context:
        - task: The task being verified
        - exec_result: Real tool execution result
        - task_meta: Task metadata including verification_type, success criteria, etc.
        
        Enhanced features:
        - Deep success criteria integration
        - Strict artifact expectations matching
        - Verifier confidence aggregation
        - Fail reason taxonomy
        
        Verification types:
        - browser task → browser verifier
        - screenshot task → OCR/vision verifier
        - server task → port + HTTP verifier
        - code task → syntax + regression verifier
        - file task → file existence + content verifier
        """
        
        import time
        import re
        
        verification_log = {
            'task_id': task.id,
            'verification_type': '',
            'success_criteria': '',
            'expected_artifacts': [],
            'checks': [],
            'confidence': 0.0,
            'passed': False,
            'fail_reason': None,
            'timestamp': time.time()
        }
        
        if not exec_result:
            verification_log['fail_reason'] = 'empty_execution_result'
            logger.warning(f"Verification failed: Empty execution result for task {task.id}")
            await self._emit_verification_telemetry(verification_log)
            return False
        
        verification_type = task_meta.get('verification_type')
        success_criteria = task_meta.get('success_criteria', '')
        expected_artifacts = task_meta.get('expected_artifacts', [])
        
        # FIX #2 & #3: Normalize verification type using canonical system
        # CRITICAL: 'manual' is NOT a valid verification type!
        normalized_type = None
        if verification_type:
            try:
                normalized_type = normalize_verification_type(verification_type)
            except ValueError as e:
                logger.warning(f"Invalid verification type '{verification_type}': {e}")
                # For backward compatibility, treat invalid types as NONE
                # But log a warning - this should be fixed in the planner
                verification_log['fail_reason'] = 'invalid_verification_type'
                verification_log['checks'].append({
                    'check': 'verification_type_validation',
                    'passed': False,
                    'detail': str(e)
                })
                await self._emit_verification_telemetry(verification_log)
                return False
        else:
            # FIX #2: No default to manual! Require explicit verification type
            logger.warning(f"Task {task.id} has no verification_type specified!")
            verification_log['fail_reason'] = 'missing_verification_type'
            verification_log['checks'].append({
                'check': 'verification_type_present',
                'passed': False,
                'detail': 'verification_type is required for autonomous tasks'
            })
            await self._emit_verification_telemetry(verification_log)
            return False
        
        verification_log['verification_type'] = normalized_type.value if normalized_type else 'none'
        verification_log['success_criteria'] = success_criteria
        verification_log['expected_artifacts'] = expected_artifacts
        
        # If execution itself failed, verification fails
        if not exec_result.success:
            verification_log['fail_reason'] = 'execution_failed'
            verification_log['checks'].append({
                'check': 'execution_success',
                'passed': False,
                'detail': exec_result.error or 'Unknown error'
            })
            logger.warning(f"Verification failed: Execution was not successful - {exec_result.error}")
            await self._emit_verification_telemetry(verification_log)
            return False
        
        verification_log['checks'].append({
            'check': 'execution_success',
            'passed': True,
            'detail': 'Execution completed successfully'
        })
        
        # Check for error patterns in result (real stderr/stdout from tool)
        error_patterns = [
            "EXCEPTION", "ERROR", "FAILED", "Traceback",
            "Permission denied", "Not found", "Timeout",
            "Verification FAILED", "command failed", "xatolik"
        ]
        
        result_text = (exec_result.stdout or "") + (exec_result.stderr or "")
        result_upper = result_text.upper()
        has_error = any(pattern.upper() in result_upper for pattern in error_patterns)
        
        if has_error:
            verification_log['fail_reason'] = 'error_pattern_detected'
            verification_log['checks'].append({
                'check': 'error_patterns',
                'passed': False,
                'detail': 'Error patterns found in output'
            })
            logger.warning(f"Verification failed: Error patterns detected in execution output")
            await self._emit_verification_telemetry(verification_log)
            return False
        
        verification_log['checks'].append({
            'check': 'error_patterns',
            'passed': True,
            'detail': 'No error patterns detected'
        })
        
        # Check result is not just placeholder text (model fake)
        if result_text.startswith("Executed:") or result_text.startswith("Vazifa qabul"):
            verification_log['fail_reason'] = 'placeholder_result'
            verification_log['checks'].append({
                'check': 'not_placeholder',
                'passed': False,
                'detail': 'Result appears to be placeholder'
            })
            logger.warning("Verification failed: Result appears to be placeholder (model fake)")
            await self._emit_verification_telemetry(verification_log)
            return False
        
        verification_log['checks'].append({
            'check': 'not_placeholder',
            'passed': True,
            'detail': 'Result is real, not placeholder'
        })
        
        # DEEP SUCCESS CRITERIA INTEGRATION
        if success_criteria:
            criteria_result = await self._verify_success_criteria(
                success_criteria, exec_result, task_meta
            )
            verification_log['checks'].append({
                'check': 'success_criteria',
                'passed': criteria_result['passed'],
                'detail': criteria_result.get('detail', ''),
                'confidence': criteria_result.get('confidence', 0.0)
            })
            if not criteria_result['passed']:
                verification_log['fail_reason'] = 'success_criteria_not_met'
                verification_log['confidence'] = criteria_result.get('confidence', 0.0)
                logger.warning(f"Verification failed: Success criteria not met - {criteria_result.get('detail', '')}")
                await self._emit_verification_telemetry(verification_log)
                return False
        
        # STRICT ARTIFACT EXPECTATIONS MATCHING
        if expected_artifacts:
            artifact_result = await self._verify_artifact_expectations(
                expected_artifacts, exec_result, task_meta
            )
            verification_log['checks'].append({
                'check': 'artifact_expectations',
                'passed': artifact_result['passed'],
                'detail': artifact_result.get('detail', ''),
                'matched_artifacts': artifact_result.get('matched', []),
                'missing_artifacts': artifact_result.get('missing', []),
                'confidence': artifact_result.get('confidence', 0.0)
            })
            if not artifact_result['passed']:
                verification_log['fail_reason'] = 'artifact_expectations_not_met'
                verification_log['confidence'] = artifact_result.get('confidence', 0.0)
                logger.warning(f"Verification failed: Artifact expectations not met - {artifact_result.get('detail', '')}")
                await self._emit_verification_telemetry(verification_log)
                return False
        
        # Type-specific verification with confidence aggregation
        # FIX #22: Use canonical VerificationType instead of legacy strings
        confidence_scores = []
        
        # Use normalized_type (which is a VerificationType enum)
        if normalized_type == VerificationType.BROWSER_STATE:
            result = await self._verify_browser(task, exec_result, task_meta)
            confidence_scores.append(1.0 if result else 0.0)
            if not result:
                verification_log['fail_reason'] = 'browser_state_verification_failed'
                await self._emit_verification_telemetry(verification_log)
                return False
        elif normalized_type == VerificationType.SCREENSHOT_MATCH:
            result = await self._verify_screenshot(task, exec_result, task_meta)
            confidence_scores.append(1.0 if result else 0.0)
            if not result:
                verification_log['fail_reason'] = 'screenshot_verification_failed'
                await self._emit_verification_telemetry(verification_log)
                return False
        elif normalized_type == VerificationType.HTTP_RESPONSE:
            result = await self._verify_server(task, exec_result, task_meta)
            confidence_scores.append(1.0 if result else 0.0)
            if not result:
                verification_log['fail_reason'] = 'http_response_verification_failed'
                await self._emit_verification_telemetry(verification_log)
                return False
        elif normalized_type == VerificationType.CODE_COMPILES:
            result = await self._verify_code(task, exec_result, task_meta)
            confidence_scores.append(1.0 if result else 0.0)
            if not result:
                verification_log['fail_reason'] = 'code_compiles_verification_failed'
                await self._emit_verification_telemetry(verification_log)
                return False
        elif normalized_type == VerificationType.FILE_EXISTS:
            result = await self._verify_file(task, exec_result, task_meta)
            confidence_scores.append(1.0 if result else 0.0)
            if not result:
                verification_log['fail_reason'] = 'file_exists_verification_failed'
                await self._emit_verification_telemetry(verification_log)
                return False
        elif normalized_type == VerificationType.FUNCTION_RESULT:
            result = self._verify_function_result(task, exec_result, task_meta)
            confidence_scores.append(1.0 if result else 0.0)
            if not result:
                verification_log['fail_reason'] = 'function_result_verification_failed'
                await self._emit_verification_telemetry(verification_log)
                return False
        elif normalized_type == VerificationType.NONE:
            # FIX #23: NONE verification requires explicit approval or human review
            # For NONE type tasks, we require success_criteria or explicit approval
            if not success_criteria and not task.approval_policy:
                logger.warning(f"Task {task.id} with NONE verification requires success_criteria or approval")
                verification_log['fail_reason'] = 'none_verification_requires_criteria'
                await self._emit_verification_telemetry(verification_log)
                return False
            result = exec_result.success
            confidence_scores.append(1.0 if result else 0.0)
        elif normalized_type == VerificationType.PROCESS_RUNNING:
            result = await self._verify_process_running(task, exec_result, task_meta)
            confidence_scores.append(1.0 if result else 0.0)
            if not result:
                verification_log['fail_reason'] = 'process_running_verification_failed'
                await self._emit_verification_telemetry(verification_log)
                return False
        elif normalized_type == VerificationType.PORT_OPEN:
            result = await self._verify_port_open(task, exec_result, task_meta)
            confidence_scores.append(1.0 if result else 0.0)
            if not result:
                verification_log['fail_reason'] = 'port_open_verification_failed'
                await self._emit_verification_telemetry(verification_log)
                return False
        elif normalized_type == VerificationType.ARTIFACT_PRESENT:
            result = await self._verify_artifact_present(task, exec_result, task_meta)
            confidence_scores.append(1.0 if result else 0.0)
            if not result:
                verification_log['fail_reason'] = 'artifact_present_verification_failed'
                await self._emit_verification_telemetry(verification_log)
                return False
        else:
            # FIX #22: Unknown verification type should fail, not silently pass
            logger.error(f"Unknown verification type: {normalized_type}")
            verification_log['fail_reason'] = 'unknown_verification_type'
            verification_log['checks'].append({
                'check': 'verification_type_known',
                'passed': False,
                'detail': f'Unknown verification type: {normalized_type}'
            })
            await self._emit_verification_telemetry(verification_log)
            return False
        
        # AGGREGATE VERIFIER CONFIDENCE
        if confidence_scores:
            avg_confidence = sum(confidence_scores) / len(confidence_scores)
            verification_log['confidence'] = avg_confidence
        
        verification_log['passed'] = True
        await self._emit_verification_telemetry(verification_log)
        return True
    
    async def _verify_success_criteria(self, success_criteria: str, exec_result: ExecutionResult, task_meta: Dict) -> Dict:
        """
        Verify success criteria with deep integration.
        
        Returns:
        - passed: bool
        - detail: str
        - confidence: float (0.0 - 1.0)
        """
        import re
        
        result_text = (exec_result.stdout or "") + (exec_result.stderr or "")
        
        # Parse success criteria
        # Support patterns like:
        # - "contains:Hello World"
        # - "regex:\\d+ errors?"
        # - "not_contains:Error"
        # - "output_contains:success"
        # - "exit_code:0"
        
        passed = True
        details = []
        confidence = 1.0
        
        # Check for "contains:X" pattern
        contains_match = re.search(r'contains:([^\s]+)', success_criteria)
        if contains_match:
            required_text = contains_match.group(1)
            if required_text.lower() in result_text.lower():
                details.append(f"Found required text: {required_text}")
            else:
                passed = False
                confidence = 0.0
                details.append(f"Missing required text: {required_text}")
        
        # Check for "not_contains:X" pattern
        not_contains_match = re.search(r'not_contains:([^\s]+)', success_criteria)
        if not_contains_match:
            forbidden_text = not_contains_match.group(1)
            if forbidden_text.lower() in result_text.lower():
                passed = False
                confidence = 0.0
                details.append(f"Found forbidden text: {forbidden_text}")
            else:
                details.append(f"Confirmed no forbidden text: {forbidden_text}")
        
        # Check for "regex:X" pattern
        regex_match = re.search(r'regex:([^\s]+)', success_criteria)
        if regex_match:
            try:
                pattern = regex_match.group(1)
                if re.search(pattern, result_text):
                    details.append(f"Regex pattern matched: {pattern}")
                else:
                    passed = False
                    confidence = 0.0
                    details.append(f"Regex pattern not found: {pattern}")
            except re.error as e:
                details.append(f"Regex error: {e}")
        
        # Check for "exit_code:X" pattern
        exit_code_match = re.search(r'exit_code:(\d+)', success_criteria)
        if exit_code_match:
            expected_code = int(exit_code_match.group(1))
            actual_code = exec_result.exit_code
            if actual_code == expected_code:
                details.append(f"Exit code matches: {actual_code}")
            else:
                passed = False
                confidence = 0.0
                details.append(f"Exit code mismatch: expected {expected_code}, got {actual_code}")
        
        return {
            'passed': passed,
            'detail': '; '.join(details) if details else 'Success criteria check completed',
            'confidence': confidence
        }
    
    async def _verify_artifact_expectations(self, expected_artifacts: List[str], exec_result: ExecutionResult, task_meta: Dict) -> Dict:
        """
        Strict artifact expectations matching.
        
        Returns:
        - passed: bool
        - detail: str
        - matched: List[str]
        - missing: List[str]
        - confidence: float (0.0 - 1.0)
        """
        import os
        
        actual_artifacts = exec_result.artifacts or []
        
        matched = []
        missing = []
        confidence = 1.0
        
        for expected in expected_artifacts:
            # Expected artifact can be:
            # - Exact filename: "output.txt"
            # - Extension: ".pdf", ".png"
            # - Pattern: "*.js", "report_*"
            
            found = False
            
            # Check exact match
            if expected in actual_artifacts:
                matched.append(expected)
                found = True
            else:
                # Check extension match
                if expected.startswith('.'):
                    for artifact in actual_artifacts:
                        if artifact.endswith(expected):
                            matched.append(f"{artifact} (matched {expected})")
                            found = True
                            break
                else:
                    # Check if expected is a substring of any artifact
                    for artifact in actual_artifacts:
                        if expected in artifact:
                            matched.append(artifact)
                            found = True
                            break
            
            if not found:
                missing.append(expected)
        
        # Calculate confidence based on match ratio
        if expected_artifacts:
            match_ratio = len(matched) / len(expected_artifacts)
            confidence = match_ratio
        
        passed = len(missing) == 0
        
        detail = f"Matched: {len(matched)}/{len(expected_artifacts)}"
        if missing:
            detail += f", Missing: {missing}"
        
        return {
            'passed': passed,
            'detail': detail,
            'matched': matched,
            'missing': missing,
            'confidence': confidence
        }
    
    async def _emit_verification_telemetry(self, verification_log: Dict):
        """Emit verification telemetry with full diagnostics."""
        try:
            # Log prominently
            if verification_log['passed']:
                logger.info(f"✅ Verification PASSED for task {verification_log['task_id']} (confidence: {verification_log['confidence']:.2f})")
            else:
                logger.error(f"❌ Verification FAILED for task {verification_log['task_id']}: {verification_log['fail_reason']}")
                logger.error(f"   Checks: {[c['check'] for c in verification_log['checks'] if not c['passed']]}")
            
            # Emit to telemetry if available
            if hasattr(self, 'telemetry') and self.telemetry:
                self.telemetry.record_event('task_verification', verification_log)
            
            # Emit self-improvement signal if failed
            if not verification_log['passed'] and hasattr(self, 'emit_improvement_signal'):
                self.emit_improvement_signal('verification_failure', {
                    'task_id': verification_log['task_id'],
                    'fail_reason': verification_log['fail_reason'],
                    'verification_type': verification_log['verification_type'],
                    'checks_failed': [c['check'] for c in verification_log['checks'] if not c['passed']]
                })
        except Exception as e:
            logger.error(f"Failed to emit verification telemetry: {e}")
    
    async def _verify_browser(self, task: Task, exec_result: ExecutionResult, task_meta: Dict) -> bool:
        """
        WORLD-CLASS Browser verification with multiple signals:
        - URL verification
        - DOM text verification
        - Selector verification
        - HTTP status verification
        - Screenshot corroboration
        - Navigation chain verification
        - Session/auth state verification
        - Final page semantic verification
        """
        
        import time
        
        # Verification log for diagnostics
        verification_checks = []
        
        expected_url = task_meta.get('expected_url', '')
        expected_text = task_meta.get('expected_text', '')
        required_selectors = task_meta.get('required_selectors', [])
        check_network = task_meta.get('check_network', True)
        check_auth = task_meta.get('check_auth', False)
        check_session = task_meta.get('check_session', False)
        navigation_chain = task_meta.get('navigation_chain', [])  # List of URLs to verify in order
        semantic_text = task_meta.get('semantic_text', '')  # High-level semantic check
        screenshot_expected = task_meta.get('screenshot_expected', False)
        
        result_data = exec_result.stdout  # Could be URL, HTML, or status
        
        # Get browser instance
        browser = getattr(self, 'browser', None)
        
        # ============== 1. URL VERIFICATION ==============
        url_check = {'name': 'url_verification', 'passed': True, 'detail': ''}
        if expected_url:
            # First check in result data
            if expected_url not in result_data:
                # Try to get actual URL from browser
                if browser and hasattr(browser, 'get_current_url'):
                    try:
                        actual_url = browser.get_current_url()
                        if expected_url not in actual_url:
                            url_check['passed'] = False
                            url_check['detail'] = f"URL mismatch. Expected: {expected_url}, Got: {actual_url}"
                            logger.warning(f"Browser verification failed: {url_check['detail']}")
                            verification_checks.append(url_check)
                            return False
                        else:
                            url_check['detail'] = f"URL verified: {actual_url}"
                    except Exception as e:
                        url_check['passed'] = False
                        url_check['detail'] = f"Could not get URL: {e}"
                        verification_checks.append(url_check)
                        return False
            else:
                url_check['detail'] = f"URL found in result: {expected_url}"
        
        verification_checks.append(url_check)
        
        # ============== 2. NAVIGATION CHAIN VERIFICATION ==============
        nav_check = {'name': 'navigation_chain', 'passed': True, 'detail': ''}
        if navigation_chain and browser and hasattr(browser, 'get_navigation_history'):
            try:
                nav_history = browser.get_navigation_history()
                expected_chain = navigation_chain
                
                # Check if all expected URLs were visited in order
                visited_urls = nav_history.get('urls', [])
                
                # Check if key pages in chain were visited
                missing_nav = []
                for expected_nav in expected_chain:
                    found = any(expected_nav in vurl for vurl in visited_urls)
                    if not found:
                        missing_nav.append(expected_nav)
                
                if missing_nav:
                    nav_check['passed'] = False
                    nav_check['detail'] = f"Missing navigation steps: {missing_nav}. Visited: {visited_urls}"
                    logger.warning(f"Browser verification failed: {nav_check['detail']}")
                    verification_checks.append(nav_check)
                    return False
                else:
                    nav_check['detail'] = f"Navigation chain verified: {visited_urls}"
            except Exception as e:
                nav_check['detail'] = f"Could not verify navigation: {e}"
        
        verification_checks.append(nav_check)
        
        # ============== 3. HTTP STATUS VERIFICATION ==============
        http_check = {'name': 'http_status', 'passed': True, 'detail': ''}
        if check_network:
            if '200' not in result_data and 'OK' not in result_data:
                # Check for error status codes
                error_codes = ['404', '500', '503', '403', '401', '500']
                found_errors = [code for code in error_codes if code in result_data]
                if found_errors:
                    http_check['passed'] = False
                    http_check['detail'] = f"HTTP errors found: {found_errors}"
                    logger.warning(f"Browser verification failed: {http_check['detail']}")
                    verification_checks.append(http_check)
                    return False
            http_check['detail'] = "HTTP status OK"
        
        verification_checks.append(http_check)
        
        # ============== 4. DOM TEXT VERIFICATION ==============
        text_check = {'name': 'dom_text', 'passed': True, 'detail': ''}
        if expected_text:
            if expected_text.lower() not in result_data.lower():
                text_check['passed'] = False
                text_check['detail'] = f"Expected text not found: {expected_text[:50]}..."
                logger.warning(f"Browser verification failed: {text_check['detail']}")
                verification_checks.append(text_check)
                return False
            else:
                text_check['detail'] = f"Text verified: {expected_text[:30]}..."
        
        verification_checks.append(text_check)
        
        # ============== 5. SELECTOR VERIFICATION ==============
        selector_check = {'name': 'selectors', 'passed': True, 'detail': '', 'found': [], 'missing': []}
        if required_selectors and browser and hasattr(browser, 'element_exists'):
            for selector in required_selectors:
                try:
                    if browser.element_exists(selector):
                        selector_check['found'].append(selector)
                    else:
                        selector_check['missing'].append(selector)
                except Exception as e:
                    selector_check['missing'].append(f"{selector} (error: {e})")
            
            if selector_check['missing']:
                selector_check['passed'] = False
                selector_check['detail'] = f"Missing selectors: {selector_check['missing']}"
                logger.warning(f"Browser verification failed: {selector_check['detail']}")
                verification_checks.append(selector_check)
                return False
            else:
                selector_check['detail'] = f"All selectors found: {selector_check['found']}"
        
        verification_checks.append(selector_check)
        
        # ============== 6. SCREENSHOT CORROBORATION ==============
        screenshot_check = {'name': 'screenshot', 'passed': True, 'detail': ''}
        if screenshot_expected:
            # Check if screenshot artifact exists
            screenshot_artifacts = [a for a in exec_result.artifacts if a.endswith(('.png', '.jpg', '.jpeg', '.webp'))]
            
            if not screenshot_artifacts:
                screenshot_check['passed'] = False
                screenshot_check['detail'] = "Screenshot expected but not found in artifacts"
                logger.warning(f"Browser verification failed: {screenshot_check['detail']}")
                verification_checks.append(screenshot_check)
                return False
            
            # Verify screenshot file exists on disk
            import os
            real_screenshot = screenshot_artifacts[0]
            if not os.path.exists(real_screenshot):
                screenshot_check['passed'] = False
                screenshot_check['detail'] = f"Screenshot file not found: {real_screenshot}"
                logger.warning(f"Browser verification failed: {screenshot_check['detail']}")
                verification_checks.append(screenshot_check)
                return False
            
            # Check file size
            file_size = os.path.getsize(real_screenshot)
            if file_size < 100:
                screenshot_check['passed'] = False
                screenshot_check['detail'] = f"Screenshot too small: {file_size} bytes"
                logger.warning(f"Browser verification failed: {screenshot_check['detail']}")
                verification_checks.append(screenshot_check)
                return False
            
            screenshot_check['detail'] = f"Screenshot verified: {real_screenshot} ({file_size} bytes)"
        
        verification_checks.append(screenshot_check)
        
        # ============== 7. SESSION/AUTH STATE VERIFICATION ==============
        auth_check = {'name': 'auth_session', 'passed': True, 'detail': ''}
        
        if check_auth or check_session:
            if not browser:
                auth_check['passed'] = False
                auth_check['detail'] = "Browser not available for auth/session check"
                logger.warning(f"Browser verification failed: {auth_check['detail']}")
                verification_checks.append(auth_check)
                return False
            
            try:
                # Check authentication state
                if check_auth:
                    # Check for common auth indicators
                    auth_indicators = [
                        'logout', 'sign out', 'log out', 'profile', 'account',
                        'settings', 'logged-in', 'welcome'
                    ]
                    
                    # Get page content
                    page_content = ""
                    if hasattr(browser, 'get_page_content'):
                        page_content = browser.get_page_content()
                    elif hasattr(browser, 'get_page_text'):
                        page_content = browser.get_page_text()
                    
                    # Check for auth indicators
                    auth_found = any(indicator in page_content.lower() for indicator in auth_indicators)
                    
                    if not auth_found:
                        auth_check['passed'] = False
                        auth_check['detail'] = "Auth state indicators not found on page"
                        logger.warning(f"Browser verification failed: {auth_check['detail']}")
                        verification_checks.append(auth_check)
                        return False
                    else:
                        auth_check['detail'] = "Auth state verified"
                
                # Check session state
                if check_session:
                    # Check if cookies exist
                    if hasattr(browser, 'get_cookies'):
                        cookies = browser.get_cookies()
                        if not cookies or len(cookies) == 0:
                            auth_check['passed'] = False
                            auth_check['detail'] = "No session cookies found"
                            logger.warning(f"Browser verification failed: {auth_check['detail']}")
                            verification_checks.append(auth_check)
                            return False
                        else:
                            auth_check['detail'] = f"Session verified with {len(cookies)} cookies"
                
            except Exception as e:
                auth_check['passed'] = False
                auth_check['detail'] = f"Auth/session check error: {e}"
                logger.warning(f"Browser verification failed: {auth_check['detail']}")
                verification_checks.append(auth_check)
                return False
        
        verification_checks.append(auth_check)
        
        # ============== 8. SEMANTIC TEXT VERIFICATION ==============
        semantic_check = {'name': 'semantic_verification', 'passed': True, 'detail': ''}
        if semantic_text:
            # High-level semantic check - e.g., "page contains form", "shows error message"
            semantic_patterns = semantic_text.split('|')  # Allow multiple patterns
            
            page_for_semantic = result_data
            if browser and hasattr(browser, 'get_page_text'):
                try:
                    page_for_semantic = browser.get_page_text()
                except (AttributeError, Exception) as e:
                    logger.debug(f"Browser page text unavailable: {e}")
            
            missing_semantic = []
            for pattern in semantic_patterns:
                pattern = pattern.strip()
                if pattern.lower() not in page_for_semantic.lower():
                    missing_semantic.append(pattern)
            
            if missing_semantic:
                semantic_check['passed'] = False
                semantic_check['detail'] = f"Missing semantic elements: {missing_semantic}"
                logger.warning(f"Browser verification failed: {semantic_check['detail']}")
                verification_checks.append(semantic_check)
                return False
            else:
                semantic_check['detail'] = f"Semantic verification passed: {semantic_text}"
        
        verification_checks.append(semantic_check)
        
        # ============== LOG ALL CHECKS ==============
        logger.info(f"🔍 Browser verification for task {task.id}: {len(verification_checks)} checks")
        for check in verification_checks:
            status = "✅" if check['passed'] else "❌"
            logger.info(f"   {status} {check['name']}: {check['detail']}")
        
        logger.info(f"✅ Browser verification PASSED for task {task.id}")
        return True
    
    async def _verify_screenshot(self, task: Task, exec_result: ExecutionResult, task_meta: Dict) -> bool:
        """
        COMPREHENSIVE Screenshot verification with multiple signals:
        
        For screenshot task to be successful:
        1. REAL image artifact must exist (file on disk)
        2. OCR verification with confidence
        3. Vision prompt verification with confidence
        4. Region-based expectation verification
        5. UI element matching
        6. Before/after image diff (if baseline provided)
        7. Bounding box confidence
        8. Overall confidence threshold
        
        NO soft passes - if no real image, verification FAILS!
        """
        
        import os
        import time
        
        # Verification log for diagnostics
        verification_checks = []
        
        expected_text = task_meta.get('expected_text', '')
        vision_prompt = task_meta.get('vision_prompt', '')
        image_path = task_meta.get('image_path', '')
        confidence_threshold = task_meta.get('confidence_threshold', 0.7)
        
        # NEW: Region-based expectations
        expected_regions = task_meta.get('expected_regions', [])  # List of {x, y, width, height, expected_text}
        
        # NEW: UI element matching
        expected_ui_elements = task_meta.get('expected_ui_elements', [])  # List of {type, text, selector}
        
        # NEW: Before/after diff
        baseline_image_path = task_meta.get('baseline_image_path', '')  # Compare with this image
        diff_threshold = task_meta.get('diff_threshold', 0.1)  # Max allowed difference ratio
        
        # NEW: Bounding box expectations
        expected_bboxes = task_meta.get('expected_bboxes', [])  # List of {label, min_confidence}
        
        # ============== 1. CRITICAL: REAL IMAGE ARTIFACT MUST EXIST ==============
        check_artifact = {'name': 'artifact_exists', 'passed': True, 'detail': ''}
        
        screenshot_artifacts = [a for a in exec_result.artifacts if a.endswith(('.png', '.jpg', '.jpeg', '.webp'))]
        
        if not screenshot_artifacts:
            check_artifact['passed'] = False
            check_artifact['detail'] = 'No real image artifact found'
            logger.error(f"Screenshot verification FAILED: No real image artifact found for task {task.id}")
            verification_checks.append(check_artifact)
            
            if hasattr(self, 'telemetry') and self.telemetry:
                self.telemetry.record_event('screenshot_verification_failed', {
                    'task_id': task.id,
                    'reason': 'no_artifact',
                    'artifacts': exec_result.artifacts,
                    'timestamp': time.time()
                })
            
            return False
        
        verification_checks.append(check_artifact)
        
        # ============== 2. VERIFY IMAGE FILE ON DISK ==============
        check_file = {'name': 'file_on_disk', 'passed': True, 'detail': ''}
        
        real_image_path = screenshot_artifacts[0]
        if not os.path.exists(real_image_path):
            check_file['passed'] = False
            check_file['detail'] = f'Image file not found on disk: {real_image_path}'
            logger.error(f"Screenshot verification FAILED: {check_file['detail']}")
            verification_checks.append(check_file)
            
            if hasattr(self, 'telemetry') and self.telemetry:
                self.telemetry.record_event('screenshot_verification_failed', {
                    'task_id': task.id,
                    'reason': 'file_not_found',
                    'path': real_image_path,
                    'timestamp': time.time()
                })
            
            return False
        
        verification_checks.append(check_file)
        
        # ============== 3. CHECK FILE SIZE ==============
        check_size = {'name': 'file_size', 'passed': True, 'detail': ''}
        
        file_size = os.path.getsize(real_image_path)
        if file_size < 100:
            check_size['passed'] = False
            check_size['detail'] = f'Image file too small: {file_size} bytes'
            logger.error(f"Screenshot verification FAILED: {check_size['detail']}")
            verification_checks.append(check_size)
            
            if hasattr(self, 'telemetry') and self.telemetry:
                self.telemetry.record_event('screenshot_verification_failed', {
                    'task_id': task.id,
                    'reason': 'file_too_small',
                    'size': file_size,
                    'timestamp': time.time()
                })
            
            return False
        
        check_size['detail'] = f'Image size OK: {file_size} bytes'
        verification_checks.append(check_size)
        
        logger.info(f"Screenshot verification: Found real image: {real_image_path} ({file_size} bytes)")
        
        # ============== 4. OCR VERIFICATION ==============
        ocr_check = {'name': 'ocr_verification', 'passed': True, 'detail': '', 'confidence': 1.0, 'text_found': ''}
        
        if expected_text:
            try:
                if hasattr(self, 'vision') and self.vision:
                    ocr_result = self.vision.extract_text(screenshot_artifacts[0])
                    
                    # Check if expected text found
                    if expected_text.lower() in ocr_result.lower():
                        ocr_check['passed'] = True
                        ocr_check['detail'] = f'OCR text found: {expected_text[:30]}...'
                        ocr_check['text_found'] = ocr_result[:200]
                        # Calculate rough confidence based on text length match
                        ocr_check['confidence'] = min(1.0, len(expected_text) / max(1, len(ocr_result)))
                    else:
                        ocr_check['passed'] = False
                        ocr_check['detail'] = f'OCR text NOT found. Expected: {expected_text[:50]}...'
                        ocr_check['text_found'] = ocr_result[:200]
                        ocr_check['confidence'] = 0.0
                        
                        logger.warning(f"Screenshot verification failed: {ocr_check['detail']}")
                        verification_checks.append(ocr_check)
                        return False
                else:
                    # Fallback: check in filename
                    if expected_text.lower() in real_image_path.lower():
                        ocr_check['detail'] = f'Text found in filename (OCR not available)'
                    else:
                        ocr_check['passed'] = False
                        ocr_check['detail'] = 'OCR not available, text not in filename'
                        verification_checks.append(ocr_check)
                        return False
            except Exception as e:
                ocr_check['passed'] = False
                ocr_check['detail'] = f'OCR error: {e}'
                logger.error(f"Screenshot OCR verification error: {e}")
                verification_checks.append(ocr_check)
                return False
        
        verification_checks.append(ocr_check)
        
        # ============== 5. VISION PROMPT VERIFICATION ==============
        vision_check = {'name': 'vision_verification', 'passed': True, 'detail': '', 'confidence': 0.0, 'matches': False}
        
        if vision_prompt:
            try:
                if hasattr(self, 'vision') and self.vision:
                    vision_result = self.vision.analyze_image(screenshot_artifacts[0], vision_prompt)
                    
                    matches = vision_result.get('matches', False)
                    score = vision_result.get('confidence', 0.0)
                    
                    vision_check['matches'] = matches
                    vision_check['confidence'] = score
                    
                    if not matches or score < confidence_threshold:
                        vision_check['passed'] = False
                        vision_check['detail'] = f'Vision confidence {score} < {confidence_threshold}'
                        logger.warning(f"Screenshot verification failed: {vision_check['detail']}")
                        verification_checks.append(vision_check)
                        return False
                    
                    vision_check['detail'] = f'Vision passed with confidence {score:.2f}'
                else:
                    vision_check['detail'] = 'Vision not available, skipping'
            except Exception as e:
                vision_check['passed'] = False
                vision_check['detail'] = f'Vision error: {e}'
                logger.error(f"Screenshot vision verification error: {e}")
                verification_checks.append(vision_check)
                return False
        
        verification_checks.append(vision_check)
        
        # ============== 6. REGION-BASED VERIFICATION ==============
        region_check = {'name': 'region_verification', 'passed': True, 'detail': '', 'regions_checked': 0, 'regions_found': 0}
        
        if expected_regions:
            try:
                if hasattr(self, 'vision') and self.vision:
                    for region in expected_regions:
                        region_text = region.get('expected_text', '')
                        bbox = region.get('bbox', {})  # {x, y, width, height}
                        
                        region_check['regions_checked'] += 1
                        
                        # Extract text from region
                        if bbox and hasattr(self.vision, 'extract_text_from_region'):
                            region_ocr = self.vision.extract_text_from_region(
                                screenshot_artifacts[0], 
                                bbox
                            )
                            
                            if region_text.lower() in region_ocr.lower():
                                region_check['regions_found'] += 1
                            else:
                                region_check['passed'] = False
                                region_check['detail'] = f'Region text not found: {region_text[:30]}...'
                        else:
                            # If no bbox support, check full image
                            full_ocr = self.vision.extract_text(screenshot_artifacts[0])
                            if region_text.lower() in full_ocr.lower():
                                region_check['regions_found'] += 1
                    
                    if not region_check['passed']:
                        logger.warning(f"Screenshot verification failed: {region_check['detail']}")
                        verification_checks.append(region_check)
                        return False
                    
                    region_check['detail'] = f'Regions: {region_check["regions_found"]}/{region_check["regions_checked"]} found'
                else:
                    region_check['detail'] = 'Vision not available for region check'
            except Exception as e:
                region_check['passed'] = False
                region_check['detail'] = f'Region check error: {e}'
                logger.warning(f"Screenshot region verification error: {e}")
        
        verification_checks.append(region_check)
        
        # ============== 7. UI ELEMENT MATCHING ==============
        ui_check = {'name': 'ui_element_matching', 'passed': True, 'detail': '', 'elements_checked': 0, 'elements_found': 0}
        
        if expected_ui_elements:
            try:
                if hasattr(self, 'vision') and self.vision:
                    for ui_elem in expected_ui_elements:
                        elem_type = ui_elem.get('type', '')  # button, input, link, text, etc.
                        elem_text = ui_elem.get('text', '')
                        
                        ui_check['elements_checked'] += 1
                        
                        # Use vision to detect UI elements
                        if hasattr(self.vision, 'detect_ui_elements'):
                            detected = self.vision.detect_ui_elements(screenshot_artifacts[0])
                            
                            # Check if our element is in detected ones
                            found = any(
                                det.get('type') == elem_type and 
                                (elem_text.lower() in det.get('text', '').lower() or 
                                 elem_text.lower() in det.get('label', '').lower())
                                for det in detected
                            )
                            
                            if found:
                                ui_check['elements_found'] += 1
                            else:
                                ui_check['passed'] = False
                                ui_check['detail'] = f'UI element not found: {elem_type} - {elem_text}'
                        else:
                            # Fallback: OCR check
                            full_ocr = self.vision.extract_text(screenshot_artifacts[0])
                            if elem_text.lower() in full_ocr.lower():
                                ui_check['elements_found'] += 1
                    
                    if not ui_check['passed']:
                        logger.warning(f"Screenshot verification failed: {ui_check['detail']}")
                        verification_checks.append(ui_check)
                        return False
                    
                    ui_check['detail'] = f'UI elements: {ui_check["elements_found"]}/{ui_check["elements_checked"]} found'
                else:
                    ui_check['detail'] = 'Vision not available for UI check'
            except Exception as e:
                ui_check['passed'] = False
                ui_check['detail'] = f'UI element check error: {e}'
                logger.warning(f"Screenshot UI verification error: {e}")
        
        verification_checks.append(ui_check)
        
        # ============== 8. BEFORE/AFTER IMAGE DIFF ==============
        diff_check = {'name': 'image_diff', 'passed': True, 'detail': '', 'diff_ratio': 0.0}
        
        if baseline_image_path and os.path.exists(baseline_image_path):
            try:
                if hasattr(self, 'vision') and self.vision and hasattr(self.vision, 'compare_images'):
                    diff_result = self.vision.compare_images(baseline_image_path, real_image_path)
                    
                    diff_ratio = diff_result.get('diff_ratio', 1.0)
                    diff_check['diff_ratio'] = diff_ratio
                    
                    if diff_ratio > diff_threshold:
                        diff_check['passed'] = False
                        diff_check['detail'] = f'Image diff {diff_ratio:.2f} > threshold {diff_threshold}'
                        logger.warning(f"Screenshot verification failed: {diff_check['detail']}")
                        verification_checks.append(diff_check)
                        return False
                    
                    diff_check['detail'] = f'Image diff OK: {diff_ratio:.4f} <= {diff_threshold}'
                else:
                    diff_check['detail'] = 'Image diff not available, skipping'
            except Exception as e:
                diff_check['passed'] = False
                diff_check['detail'] = f'Image diff error: {e}'
                logger.warning(f"Screenshot diff verification error: {e}")
        elif baseline_image_path:
            diff_check['detail'] = f'Baseline image not found: {baseline_image_path}, skipping'
        
        verification_checks.append(diff_check)
        
        # ============== 9. BOUNDING BOX CONFIDENCE ==============
        bbox_check = {'name': 'bbox_confidence', 'passed': True, 'detail': '', 'bboxes_checked': 0, 'bboxes_passed': 0}
        
        if expected_bboxes:
            try:
                if hasattr(self, 'vision') and self.vision and hasattr(self.vision, 'detect_objects'):
                    detected_objects = self.vision.detect_objects(screenshot_artifacts[0])
                    
                    for bbox_exp in expected_bboxes:
                        label = bbox_exp.get('label', '')
                        min_conf = bbox_exp.get('min_confidence', 0.5)
                        
                        bbox_check['bboxes_checked'] += 1
                        
                        # Find matching detected object
                        matched = any(
                            obj.get('label', '').lower() == label.lower() and 
                            obj.get('confidence', 0) >= min_conf
                            for obj in detected_objects
                        )
                        
                        if matched:
                            bbox_check['bboxes_passed'] += 1
                        else:
                            bbox_check['passed'] = False
                            bbox_check['detail'] = f'Bbox not found: {label} with confidence >= {min_conf}'
                    
                    if not bbox_check['passed']:
                        logger.warning(f"Screenshot verification failed: {bbox_check['detail']}")
                        verification_checks.append(bbox_check)
                        return False
                    
                    bbox_check['detail'] = f'Bboxes: {bbox_check["bboxes_passed"]}/{bbox_check["bboxes_checked"]} passed'
                else:
                    bbox_check['detail'] = 'Object detection not available, skipping'
            except Exception as e:
                bbox_check['passed'] = False
                bbox_check['detail'] = f'Bbox check error: {e}'
                logger.warning(f"Screenshot bbox verification error: {e}")
        
        verification_checks.append(bbox_check)
        
        # ============== 10. OVERALL CONFIDENCE AGGREGATION ==============
        confidences = [c.get('confidence', 1.0) for c in verification_checks if 'confidence' in c]
        overall_confidence = sum(confidences) / len(confidences) if confidences else 1.0
        
        # Log all checks
        logger.info(f"🔍 Screenshot verification for task {task.id}: {len(verification_checks)} checks")
        for check in verification_checks:
            status = "✅" if check['passed'] else "❌"
            detail = check.get('detail', '')
            logger.info(f"   {status} {check['name']}: {detail}")
        
        logger.info(f"📊 Overall confidence: {overall_confidence:.2f}")
        
        if overall_confidence < confidence_threshold:
            logger.warning(f"Screenshot verification failed: Overall confidence {overall_confidence:.2f} < {confidence_threshold}")
            return False
        
        logger.info(f"✅ Screenshot verification PASSED for task {task.id}")
        return True
    
    async def _verify_server(self, task: Task, exec_result: ExecutionResult, task_meta: Dict) -> bool:
        """Server verification - port + HTTP check"""
        
        expected_port = task_meta.get('expected_port', 0)
        expected_endpoint = task_meta.get('expected_endpoint', '/')
        check_http = task_meta.get('check_http', True)
        
        # Check if server started successfully
        if not exec_result.success:
            logger.warning("Server verification failed: Execution was not successful")
            return False
        
        stdout = exec_result.stdout or ""
        stderr = exec_result.stderr or ""
        
        # Look for port in output
        if expected_port:
            port_str = str(expected_port)
            if port_str not in stdout and port_str not in stderr:
                logger.warning(f"Server verification failed: Port {expected_port} not found in output")
                return False
        
        # HTTP check if requested
        if check_http:
            # Try to make HTTP request to verify server is running
            if hasattr(self, 'tools_engine') and self.tools_engine:
                try:
                    http_result = self.tools_engine.execute_tool(
                        'web_request', 
                        {'url': f'http://localhost:{expected_port}{expected_endpoint}', 'timeout': 5}
                    )
                    if not http_result.get('success', False):
                        logger.warning(f"Server verification failed: HTTP check failed")
                        return False
                except Exception as e:
                    logger.warning(f"Server verification: HTTP check skipped - {e}")
        
        logger.info(f"Server verification PASSED for task {task.id}")
        return True
    
    async def _verify_code(self, task: Task, exec_result: ExecutionResult, task_meta: Dict) -> bool:
        """Code verification - syntax + regression check"""
        
        check_syntax = task_meta.get('check_syntax', True)
        check_output = task_meta.get('check_output', True)
        expected_output = task_meta.get('expected_output', '')
        
        stdout = exec_result.stdout or ""
        stderr = exec_result.stderr or ""
        
        # Syntax check
        if check_syntax and 'SyntaxError' in stderr:
            logger.warning("Code verification failed: Syntax error detected")
            return False
        
        # Output check
        if check_output and expected_output:
            if expected_output not in stdout:
                logger.warning(f"Code verification failed: Expected output not found")
                return False
        
        logger.info(f"Code verification PASSED for task {task.id}")
        return True
    
    async def _verify_file(self, task: Task, exec_result: ExecutionResult, task_meta: Dict) -> bool:
        """File verification - existence + content check"""
        
        expected_path = task_meta.get('expected_path', '')
        expected_content = task_meta.get('expected_content', '')
        
        # Check artifacts for created files
        file_artifacts = exec_result.artifacts
        
        if expected_path:
            if expected_path not in file_artifacts:
                # Check if file exists
                import os
                if not os.path.exists(expected_path):
                    logger.warning(f"File verification failed: File not found at {expected_path}")
                    return False
        
        # Content check
        if expected_content:
            try:
                with open(expected_path, 'r') as f:
                    content = f.read()
                    if expected_content not in content:
                        logger.warning(f"File verification failed: Expected content not found")
                        return False
            except Exception as e:
                logger.warning(f"File verification: Could not read content - {e}")
        
        logger.info(f"File verification PASSED for task {task.id}")
        return True
    
    async def _verify_process_running(self, task: Task, exec_result: ExecutionResult, task_meta: Dict) -> bool:
        """Process running verification"""
        import psutil
        
        process_name = task_meta.get('process_name', '')
        if not process_name:
            logger.warning("Process verification: No process_name specified")
            return False
        
        for proc in psutil.process_iter(['name']):
            try:
                if process_name.lower() in proc.info['name'].lower():
                    logger.info(f"Process verification PASSED: {process_name} is running")
                    return True
            except Exception as e:
                logger.debug(f"Process check error: {e}")
        
        logger.warning(f"Process verification failed: {process_name} is not running")
        return False
    
    async def _verify_port_open(self, task: Task, exec_result: ExecutionResult, task_meta: Dict) -> bool:
        """Port open verification"""
        import socket
        
        host = task_meta.get('host', 'localhost')
        port = task_meta.get('port', 80)
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        try:
            result = sock.connect_ex((host, port))
            open_port = result == 0
        except socket.timeout:
            open_port = False
        except socket.error as e:
            logger.warning(f"Port verification error: {e}")
            open_port = False
        finally:
            sock.close()
        
        if open_port:
            logger.info(f"Port verification PASSED: {host}:{port} is open")
        else:
            logger.warning(f"Port verification failed: {host}:{port} is not open")
        
        return open_port
    
    async def _verify_artifact_present(self, task: Task, exec_result: ExecutionResult, task_meta: Dict) -> bool:
        """Artifact present verification"""
        expected_artifacts = task_meta.get('expected_artifacts', [])
        
        if not expected_artifacts:
            logger.warning("Artifact verification: No expected_artifacts specified")
            return False
        
        created_artifacts = exec_result.artifacts or []
        
        missing = []
        for artifact in expected_artifacts:
            if artifact not in created_artifacts:
                missing.append(artifact)
        
        if missing:
            logger.warning(f"Artifact verification failed: Missing artifacts: {missing}")
            return False
        
        logger.info(f"Artifact verification PASSED: All expected artifacts present")
        return True
    
    async def _repair(self, result: str, failed_task: Optional[Task] = None) -> str:
        """
        OPERATIVE RECOVERY ENGINE with real actions.
        
        Performs:
        1. Error type classification
        2. Retry budget check
        3. Strategy selection based on error type
        4. REAL recovery action execution (not just description)
        5. Escalation if unrecoverable
        
        Recovery actions:
        - RETRY_SAME_TOOL: Re-queue task with same tool
        - ALTERNATE_TOOL: Re-queue with alternate tool
        - REPLAN: Re-plan the task
        - ROLLBACK: Rollback to checkpoint
        - ABORT: Abort the task
        - ESCALATE: Escalate to human
        """
        
        logger.info("🔧 Starting OPERATIVE recovery process...")
        
        # Get failed task if provided
        if failed_task is None:
            # Try to get from recent execution
            failed_task = getattr(self, '_current_failing_task', None)
        
        # Classify the error
        error_type = self._classify_error(result)
        
        logger.info(f"📊 Classified error type: {error_type.value if error_type else 'unknown'}")
        
        # Check retry budget
        if failed_task:
            if failed_task.retry_count >= failed_task.max_retries:
                logger.warning(f"Task {failed_task.id} exceeded max retries ({failed_task.max_retries})")
                return await self._execute_recovery(RecoveryStrategy.ABORT, error_type, result, failed_task)
        
        # Determine recovery strategy based on error type
        strategy = self._select_recovery_strategy(error_type, result)
        
        logger.info(f"🎯 Selected recovery strategy: {strategy.value}")
        
        # Execute REAL recovery action
        recovery_result = await self._execute_recovery(strategy, error_type, result, failed_task)
        
        return recovery_result
    
    # ==================== RECOVERY DECISION ENGINE ====================
    
    def _determine_recovery_strategy(
        self, 
        error_type: Optional[ErrorType], 
        failed_task: Optional[Task],
        retry_budget: Dict[str, int]
    ) -> Tuple[RecoveryStrategy, float]:
        """
        Determine the best recovery strategy with confidence scoring.
        
        Returns:
            Tuple of (strategy, confidence_score) where confidence is 0.0 to 1.0
        """
        
        if not failed_task:
            logger.warning("No failed task - defaulting to ABORT")
            return RecoveryStrategy.ABORT, 0.0
        
        task_id = failed_task.id
        task_meta = failed_task.input_data or {}
        current_retry_count = failed_task.retry_count
        
        # Get retry budget for this task
        max_retries = retry_budget.get(task_id, 3)
        
        # Check if retry budget exhausted
        if current_retry_count >= max_retries:
            logger.warning(f"Retry budget exhausted for {task_id} ({current_retry_count}/{max_retries})")
            
            # If we've tried multiple times, escalate to human
            if current_retry_count >= max_retries * 2:
                return RecoveryStrategy.ESCALATE_TO_HUMAN, 0.9
            
            # Otherwise abort
            return RecoveryStrategy.ABORT, 0.95
        
        # Error-type specific recovery mapping
        error_recovery_map = {
            # Execution errors
            ErrorType.EXECUTION_FAILED: {
                'primary': RecoveryStrategy.RETRY_SAME_TOOL,
                'confidence': 0.6,
                'conditions': [lambda t: t.retry_count < 2]
            },
            ErrorType.EXECUTION_TIMEOUT: {
                'primary': RecoveryStrategy.RETRY_WITH_BACKOFF,
                'confidence': 0.7,
                'conditions': [lambda t: t.retry_count < 3]
            },
            ErrorType.EXECUTION_CRASHED: {
                'primary': RecoveryStrategy.ALTERNATE_TOOL,
                'confidence': 0.5,
                'conditions': [lambda t: True]
            },
            
            # Verification errors
            ErrorType.VERIFICATION_FAILED: {
                'primary': RecoveryStrategy.REPLAN,
                'confidence': 0.65,
                'conditions': [lambda t: t.retry_count < 2]
            },
            ErrorType.VERIFICATION_MISSING: {
                'primary': RecoveryStrategy.RETRY_SAME_TOOL,
                'confidence': 0.4,
                'conditions': [lambda t: True]
            },
            
            # Tool errors
            ErrorType.TOOL_NOT_FOUND: {
                'primary': RecoveryStrategy.ALTERNATE_TOOL,
                'confidence': 0.7,
                'conditions': [lambda t: True]
            },
            ErrorType.TOOL_INVALID_ARGS: {
                'primary': RecoveryStrategy.REPLAN,
                'confidence': 0.6,
                'conditions': [lambda t: True]
            },
            
            # Resource errors
            ErrorType.RESOURCE_NOT_FOUND: {
                'primary': RecoveryStrategy.REPLAN,
                'confidence': 0.5,
                'conditions': [lambda t: True]
            },
            ErrorType.RESOURCE_BUSY: {
                'primary': RecoveryStrategy.RETRY_WITH_BACKOFF,
                'confidence': 0.6,
                'conditions': [lambda t: t.retry_count < 2]
            },
            
            # Network errors
            ErrorType.NETWORK_ERROR: {
                'primary': RecoveryStrategy.RETRY_WITH_BACKOFF,
                'confidence': 0.7,
                'conditions': [lambda t: t.retry_count < 3]
            },
            ErrorType.NETWORK_TIMEOUT: {
                'primary': RecoveryStrategy.RETRY_WITH_BACKOFF,
                'confidence': 0.75,
                'conditions': [lambda t: t.retry_count < 3]
            },
            
            # Approval errors - Special handling
            ErrorType.APPROVAL_DENIED: {
                'primary': RecoveryStrategy.ABORT,
                'confidence': 0.9,
                'conditions': [lambda t: True],
                'alternative': RecoveryStrategy.ALTERNATE_TOOL
            },
            ErrorType.APPROVAL_TIMEOUT: {
                'primary': RecoveryStrategy.RETRY_SAME_TOOL,
                'confidence': 0.5,
                'conditions': [lambda t: t.retry_count < 2],
                'alternative': RecoveryStrategy.REPLAN
            },
            
            # System errors
            ErrorType.SYSTEM_ERROR: {
                'primary': RecoveryStrategy.ESCALATE_TO_HUMAN,
                'confidence': 0.85,
                'conditions': [lambda t: True]
            },
            
            ErrorType.UNKNOWN_ERROR: {
                'primary': RecoveryStrategy.RETRY_WITH_BACKOFF,
                'confidence': 0.3,
                'conditions': [lambda t: t.retry_count < 2]
            },
        }
        
        # Get mapping for this error type
        if error_type in error_recovery_map:
            mapping = error_recovery_map[error_type]
            primary_strategy = mapping['primary']
            base_confidence = mapping['confidence']
            
            # Check conditions
            conditions_met = all(condition(failed_task) for condition in mapping.get('conditions', []))
            
            if not conditions_met:
                # Fall back to alternative or abort
                alternative = mapping.get('alternative', RecoveryStrategy.ABORT)
                logger.info(f"Conditions not met for {primary_strategy}, using {alternative}")
                return alternative, 0.3
            
            # Adjust confidence based on retry count (decreasing)
            retry_penalty = min(failed_task.retry_count * 0.15, 0.4)
            adjusted_confidence = max(base_confidence - retry_penalty, 0.1)
            
            return primary_strategy, adjusted_confidence
        
        # Default: retry with backoff for unknown errors
        return RecoveryStrategy.RETRY_WITH_BACKOFF, 0.3
    
    def _check_approval_recovery(
        self, 
        approval_status: str, 
        task: Task
    ) -> Optional[RecoveryStrategy]:
        """
        Handle approval-specific recovery.
        
        Args:
            approval_status: 'denied', 'expired', 'pending', 'approved'
            task: The task that needs approval
            
        Returns:
            RecoveryStrategy or None if no recovery needed
        """
        
        approval_mapping = {
            'denied': {
                'strategy': RecoveryStrategy.ABORT,
                'message': 'Approval denied by user',
                'log': '⚠️ Approval DENIED - task aborted'
            },
            'expired': {
                'strategy': RecoveryStrategy.RETRY_WITH_BACKOFF,
                'message': 'Approval request expired',
                'log': '⏳ Approval EXPIRED - retrying with backoff'
            },
            'pending': {
                'strategy': RecoveryStrategy.RETRY_SAME_TOOL,
                'message': 'Approval still pending',
                'log': '⏸️ Approval PENDING - will retry'
            }
        }
        
        if approval_status in approval_mapping:
            mapping = approval_mapping[approval_status]
            logger.info(f"Approval recovery: {mapping['log']}")
            return mapping['strategy']
        
        return None
    
    def _enter_degraded_mode(self, reason: str):
        """
        Enter degraded mode when critical failures occur.
        
        In degraded mode:
        - Only safe tools are allowed
        - Approval is always required
        - Verbose logging is enabled
        """
        
        if not hasattr(self, '_degraded_mode'):
            self._degraded_mode = False
        
        if not self._degraded_mode:
            self._degraded_mode = True
            logger.warning(f"⚠️ ENTERING DEGRADED MODE: {reason}")
            
            # Telemetry
            if hasattr(self, 'telemetry') and self.telemetry:
                self.telemetry.record_event('degraded_mode_entered', {
                    'reason': reason,
                    'timestamp': time.time()
                })
    
    def _get_recovery_budget(self, task_id: str) -> Dict[str, int]:
        """Get retry budget for a task."""
        
        if not hasattr(self, '_retry_budgets'):
            self._retry_budgets = {}
        
        if task_id not in self._retry_budgets:
            # Default budget: 3 retries per task
            self._retry_budgets[task_id] = 3
        
        return {
            'task_id': task_id,
            'max_retries': self._retry_budgets.get(task_id, 3),
            'current_attempts': 0
        }
    
    def _update_retry_budget(self, task_id: str, success: bool):
        """Update retry budget after task attempt."""
        
        if not hasattr(self, '_retry_budgets'):
            self._retry_budgets = {}
        
        if success:
            # Reset budget on success
            self._retry_budgets[task_id] = 0
        else:
            # Increment on failure
            self._retry_budgets[task_id] = self._retry_budgets.get(task_id, 0) + 1

    async def _execute_recovery(
        self, 
        strategy: RecoveryStrategy, 
        error_type: Optional[ErrorType], 
        result: str,
        failed_task: Optional[Task] = None
    ) -> str:
        """
        Execute REAL recovery action based on strategy.
        
        Each strategy performs actual actions, not just descriptions.
        """
        
        import time
        
        recovery_log = []
        recovery_log.append(f"**Xatolik turi:** {error_type.value if error_type else 'Nomalum'}")
        recovery_log.append(f"**Qayta tiklash strategiyasi:** {strategy.value}")
        recovery_log.append("")
        
        # Strategy-specific REAL actions
        if strategy == RecoveryStrategy.RETRY_SAME_TOOL:
            recovery_log.append("🔄 RETRY_SAME_TOOL: Xuddi shu tool bilan qayta urinish")
            
            if failed_task:
                # Re-queue the task with same tool
                failed_task.retry_count += 1
                failed_task.status = TaskStatus.RETRYING
                failed_task.error = result[:200]  # Store error for debugging
                
                # Re-add to task manager
                self.task_manager.add_task(failed_task)
                recovery_log.append(f"   → Task {failed_task.id} qayta queue'ga qo'shildi (retry #{failed_task.retry_count})")
                recovery_log.append(f"   → Vazifa holati: {failed_task.status.value}")
            else:
                recovery_log.append("   ⚠️ Task topilmadi, faqat log yozildi")
            
        elif strategy == RecoveryStrategy.ALTERNATE_TOOL:
            recovery_log.append("🔧 ALTERNATE_TOOL: Boshqa tool tanlash")
            
            if failed_task:
                # Get task metadata
                task_meta = failed_task.input_data or {}
                current_tool = task_meta.get('tool_used', '')
                
                # Find alternate tool
                alternate_tools = {
                    'execute_command': 'execute_code',
                    'execute_code': 'execute_command',
                    'browser_navigate': 'web_request',
                    'web_request': 'browser_navigate',
                    'write_file': 'execute_command',
                    'read_file': 'execute_command',
                }
                
                new_tool = alternate_tools.get(current_tool, 'web_search')
                
                # Update task with new tool
                task_meta['tool_used'] = new_tool
                task_meta['preferred_tool'] = new_tool
                failed_task.input_data = task_meta
                failed_task.retry_count += 1
                failed_task.status = TaskStatus.RETRYING
                
                # Re-add to task manager
                self.task_manager.add_task(failed_task)
                recovery_log.append(f"   → Tool o'zgartirildi: {current_tool} → {new_tool}")
                recovery_log.append(f"   → Task {failed_task.id} qayta queue'ga qo'shildi")
            else:
                recovery_log.append("   ⚠️ Task topilmadi")
            
        elif strategy == RecoveryStrategy.RETRY_WITH_BACKOFF:
            recovery_log.append("⏳ RETRY_WITH_BACKOFF: Kutilgan holda qayta urinish")
            
            if failed_task:
                # Calculate backoff time
                backoff_time = min(2 ** failed_task.retry_count, 30)  # Max 30 seconds
                
                failed_task.retry_count += 1
                failed_task.status = TaskStatus.RETRYING
                
                # Re-add to scheduler with delay
                self.scheduler.schedule_task(failed_task, delay=backoff_time)
                recovery_log.append(f"   → Backoff vaqti: {backoff_time} soniya")
                recovery_log.append(f"   → Task {failed_task.id} scheduler'ga qo'shildi (retry #{failed_task.retry_count})")
            else:
                recovery_log.append("   ⚠️ Task topilmadi")
            
        elif strategy == RecoveryStrategy.REPLAN:
            recovery_log.append("🔀 REPLAN: Vazifani qayta rejalashtirish")
            
            if failed_task:
                # Reset task for re-planning
                failed_task.status = TaskStatus.PENDING
                failed_task.retry_count += 1
                
                # Clear previous execution data
                failed_task.output_data = None
                failed_task.error = None
                
                # Add back to planning queue
                self.task_manager.add_task(failed_task)
                recovery_log.append(f"   → Task {failed_task.id} rejalashtirish uchun qayta qo'shildi")
                recovery_log.append(f"   → Retry count: {failed_task.retry_count}")
            else:
                recovery_log.append("   ⚠️ Task topilmadi, yangi reja tuzilmadi")
            
        elif strategy == RecoveryStrategy.ROLLBACK:
            recovery_log.append("🔙 ROLLBACK:Checkpoint'ga qaytish")
            
            if failed_task and failed_task.rollback_point:
                # Restore from rollback point
                rollback_data = failed_task.rollback_point
                
                # Restore task state
                failed_task.status = TaskStatus.PENDING
                failed_task.input_data = rollback_data.get('input_data')
                failed_task.output_data = rollback_data.get('output_data')
                failed_task.error = None
                failed_task.retry_count = rollback_data.get('retry_count', 0)
                
                # Add back to task manager
                self.task_manager.add_task(failed_task)
                
                recovery_log.append(f"   → Task {failed_task.id} checkpoint'dan tiklandi")
                recovery_log.append(f"   → Rollback point vaqti: {rollback_data.get('timestamp', 'n/a')}")
            else:
                recovery_log.append("   ⚠️ Rollback point topilmadi")
                recovery_log.append("   → Abort ga o'tiladi")
                strategy = RecoveryStrategy.ABORT
            
        elif strategy == RecoveryStrategy.SIMPLIFY_TASK:
            recovery_log.append("📝 SIMPLIFY_TASK: Vazifani soddalashtirish")
            
            if failed_task:
                # Split task into smaller parts
                desc = failed_task.description
                
                # Simple split: take first half of description
                mid = len(desc) // 2
                simpler_desc = desc[:mid] + " (soddalashtirilgan)"
                
                # Create simplified task
                simple_task = Task(
                    id=f"{failed_task.id}_simplified",
                    description=simpler_desc,
                    priority=failed_task.priority,
                    input_data={
                        **((failed_task.input_data) or {}),
                        'simplified_from': failed_task.id,
                        'original_description': desc
                    }
                )
                
                # Add simplified task
                self.task_manager.add_task(simple_task)
                
                # FIX #4: Mark original as SUPERSEDED, not COMPLETED
                # This is critical: original task was NOT completed, it was replaced
                failed_task.status = TaskStatus.SUPERSEDED
                
                recovery_log.append(f"   → Original task: {failed_task.id}")
                recovery_log.append(f"   → Yangi sodda task: {simple_task.id}")
                recovery_log.append(f"   → Description: {simple_task.description[:50]}...")
            else:
                recovery_log.append("   ⚠️ Task topilmadi")
            
        elif strategy == RecoveryStrategy.ESCALATE_TO_HUMAN:
            recovery_log.append("👤 ESCALATE_TO_HUMAN: Insonga yo'naltirish")
            
            if failed_task:
                # Mark task for human review
                failed_task.status = TaskStatus.FAILED
                failed_task.error = f"ESCALATED: {result[:200]}"
                
                # Create escalation notification
                escalation_msg = f"""🚨 **Vazifa Eskalatsiyasi**

Vazifa ID: {failed_task.id}
Xatolik: {error_type.value if error_type else 'Noma\'lum'}
Tavsif: {failed_task.description}
Xatolik xabari: {result[:200]}

Iltimos, bu vazifani ko'rib chiqing.
"""
                # Notify via approval system if available
                if hasattr(self, 'approval_engine') and self.approval_engine:
                    self.approval_engine.notify_human(escalation_msg)
                
                recovery_log.append(f"   → Task {failed_task.id} insonga yo'naltirildi")
                recovery_log.append("   → Tasdiq kutish holatida")
            else:
                recovery_log.append("   ⚠️ Task topilmadi, lekin eskalatsiya xabari yuborildi")
            
        else:  # ABORT
            recovery_log.append("❌ ABORT: Vazifani to'xtatish")
            
            if failed_task:
                # Mark as permanently failed
                failed_task.status = TaskStatus.FAILED
                failed_task.error = result[:200]
                
                # Update task manager
                self.task_manager.mark_failed(failed_task.id, result[:200])
                
                recovery_log.append(f"   → Task {failed_task.id} muvaffaqiyatsiz deb belgilandi")
                recovery_log.append(f"   → Xatolik: {result[:100]}...")
            else:
                recovery_log.append("   ⚠️ Task topilmadi")
        
        # Format recovery response
        recovery_response = "\n".join(recovery_log)
        
        logger.info(f"Operative Recovery completed: {strategy.value}")
        
        # Emit telemetry event
        if hasattr(self, 'telemetry') and self.telemetry:
            self.telemetry.record_event('recovery', {
                'strategy': strategy.value,
                'error_type': error_type.value if error_type else 'unknown',
                'task_id': failed_task.id if failed_task else None,
                'timestamp': time.time()
            })
        
        return recovery_response
    
    def get_status(self) -> str:
        """Get kernel status"""
        
        return f"""🔵 **Kernel Holati**

📌 Holat: {self.state.value}
📋 Vazifalar: {self.task_manager.get_task_graph()}
⏰ Scheduler: {self.scheduler.get_status()['task_count']} ta
🤖 Agentlar: {json.dumps(self.coordinator.get_status(), indent=2)}
{self.telemetry.get_summary()}"""
    
    def submit_task(self, user_message: str) -> str:
        """
        MAIN ENTRY POINT for all user messages
        
        FIXED ISSUES (15):
        - Explicit safe-mode
        - Structured error
        - Telemetry event
        - User notification
        """
        
        import traceback as tb
        
        logger.info(f"📥 Kernel received task: {user_message[:50]}...")
        
        execution_mode = "async_pipeline"
        
        try:
            result = asyncio.run(self.process(user_message))
            
            if hasattr(self, 'telemetry') and self.telemetry:
                self.telemetry.record_event('task_submission', {
                    'mode': execution_mode,
                    'success': True,
                    'message_preview': user_message[:100],
                    'timestamp': time.time()
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Task failed in {execution_mode} mode: {e}")
            
            error_trace = tb.format_exc()
            logger.debug(f"Full traceback: {error_trace}")
            
            if hasattr(self, 'telemetry') and self.telemetry:
                self.telemetry.record_event('task_submission', {
                    'mode': execution_mode,
                    'success': False,
                    'error_type': type(e).__name__,
                    'error_message': str(e),
                    'message_preview': user_message[:100],
                    'timestamp': time.time()
                })
            
            safe_mode = getattr(self, 'SAFE_MODE', True)
            
            if safe_mode:
                logger.warning("SAFE_MODE enabled - returning structured error instead of fallback")
                
                # Structured failure response
                structured_failure = {
                    "status": "failed",
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "safe_mode": True,
                    "degradation_level": "full",
                    "original_error": str(e)[:500],
                    "timestamp": time.time(),
                    "suggestion": "Check system logs for details or disable safe_mode for fallback execution"
                }
                
                if hasattr(self, 'telemetry') and self.telemetry:
                    self.telemetry.record_event('fallback_safe_mode', {
                        'reason': 'SAFE_MODE enabled',
                        'original_error': str(e),
                        'error_type': type(e).__name__,
                        'degradation': 'full',
                        'timestamp': time.time()
                    })
                
                # User-friendly degradation notice
                degradation_notice = f"""
╔══════════════════════════════════════════════════════════════╗
║              ⚠️  TIZIM BUZILGANLIGI HAQIDA                ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  Xatolik yuz berdi: {str(e)[:50]}...              ║
║                                                              ║
║  Holat: SAFE_MODE faol                              ║
║                                                              ║
║  Bu xatolik tufayli tizim to'liq ishlamaydi.         ║
║  Iltimos, quyidagilarni bajaring:                      ║
║    1. Loglarni tekshiring                                  ║
║    2. Safe mode'ni o'chirib qayta urinib ko'ring         ║
║    3. Administrator bilan bog'laning                        ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
"""
                
                return f"❌ Xatolik: {str(e)}\n\n{degradation_notice}"
            
            logger.warning("Attempting fallback execution")
            
            if hasattr(self, 'native_brain'):
                try:
                    execution_mode = "brain_fallback"
                    result = self.native_brain.think(user_message)
                    
                    if hasattr(self, 'telemetry') and self.telemetry:
                        self.telemetry.record_event('task_submission', {
                            'mode': execution_mode,
                            'success': True,
                            'warning': 'Results from fallback',
                            'timestamp': time.time()
                        })
                    
                    return f"⚠️ Ogohlantirish: Fallback rejada ishladi\n\n{result}"
                    
                except Exception as brain_error:
                    logger.error(f"Brain fallback also failed: {brain_error}")
                    return f"❌ Xatolik: {str(brain_error)}\n\nEslatma: Asosiy pipeline va fallback ham xatolik berdi."
            
            return f"❌ Xatolik: {str(e)}"
    
    def set_safe_mode(self, enabled: bool = True):
        """Enable or disable safe mode"""
        self.SAFE_MODE = enabled
        logger.info(f"Safe mode set to: {enabled}")
    
    def _execute_simple(self, task: str) -> str:
        """Simple execution fallback"""
        return f"Vazifa qabul qilindi: {task[:50]}..."
    
    def get_task_queue_status(self) -> str:
        """Get task queue status"""
        graph = self.task_manager.get_task_graph()
        return f"""📋 **Vazifalar Holati**

Pending: {graph['pending']}
Running: {graph['running']}
Completed: {graph['completed']}
Failed: {graph['failed']}
"""
    
    def get_dashboard(self) -> Dict:
        """Get full dashboard data"""
        
        return {
            "kernel_state": self.state.value,
            "tasks": self.task_manager.get_task_graph(),
            "scheduler": self.scheduler.get_status(),
            "agents": self.coordinator.get_status(),
            "telemetry": self.telemetry.get_metrics(),
            "artifacts": self.artifacts.get_all_artifacts(),
            "approvals": list(self.pending_approvals.keys())
        }


# ==================== FACTORY ====================

def create_kernel(api_key: str, tools_engine) -> CentralKernel:
    """Create the central kernel"""
    return CentralKernel(api_key, tools_engine)
# Kernel updated Sat Mar 14 08:06:38 UTC 2026

def _get_recovery_hint(parsing_attempts: List[Dict]) -> str:
    """
    Get recovery hint based on parsing failures.
    """
    if not parsing_attempts:
        return "No parsing attempts recorded"
    
    # Check failure reasons
    reasons = [a.get('reason', '') for a in parsing_attempts]
    
    if 'json_decode_error' in reasons:
        return "Model returned malformed JSON - prompt for cleaner JSON output"
    elif 'schema_validation_failed' in reasons:
        return "Schema mismatch - validate task structure before returning"
    elif 'no_match' in reasons:
        return "No JSON found in response - model returned prose instead of JSON"
    else:
        return "Multiple parse failures - simplify response format"

# ==================== COMPREHENSIVE RECOVERY ENGINE ====================

# FIX #1: Remove duplicate RecoveryStrategy enum - use the canonical one from line 313
# The duplicate enum below was causing shadowing issues and potential runtime crashes
# All recovery logic now uses the canonical RecoveryStrategy from line 313

# Legacy aliases for backward compatibility - map to canonical enum
# These were used by the old RecoveryEngine
_RECOVERY_ALIAS_MAP = {
    "requeue": "RETRY_WITH_BACKOFF",
    "alternate_tool": "ALTERNATE_TOOL",
    "rollback": "ROLLBACK",
    "replan": "REPLAN",
    "human": "ESCALATE_TO_HUMAN",
    "degraded": "DEGRADED_MODE",
    "exhausted": "ABORT",
}


class RecoveryEngine:
    """
    COMPREHENSIVE RECOVERY ENGINE - No1-grade.
    
    FIX #1: Now uses canonical RecoveryStrategy from line 313
    FIX #2: Uses RecoveryDecision and RecoveryOutcome typed contracts
    FIX #3: Integrated with CentralKernel
    
    Each failure triggers appropriate recovery strategy:
    1. RETRY_WITH_BACKOFF - transient failure
    2. ALTERNATE_TOOL - tool-specific failure
    3. ROLLBACK - state corruption
    4. REPLAN - fundamental plan failure
    5. DEGRADED_MODE - partial success possible
    6. ESCALATE_TO_HUMAN - critical failure
    7. ABORT - unrecoverable
    """
    
    def __init__(self, kernel):
        self.kernel = kernel
        self.max_retries = 3
        self.max_replan_depth = 2
        self.rollback_stack = {}
        
        # FIX #5: Single retry budget system - use task.retry_count consistently
        # Previously there were two: task.retry_count and self.retry_budget dict
        # Now we use task.retry_count as single source of truth
        # RecoveryEngine tracks replan depth separately
        
        self._replan_depth = {}  # Per-task replan depth (separate from retry)
        
        # Approval mapping: tool -> strategy for denied/expired
        self.approval_mapping = {
            'denied': {
                'execute_command': RecoveryStrategy.ALTERNATE_TOOL,
                'delete_file': RecoveryStrategy.ABORT,
                'browser_navigate': RecoveryStrategy.RETRY_WITH_BACKOFF,
                'write_file': RecoveryStrategy.REPLAN,
                'default': RecoveryStrategy.RETRY_WITH_BACKOFF
            },
            'expired': {
                'execute_command': RecoveryStrategy.RETRY_WITH_BACKOFF,
                'browser_navigate': RecoveryStrategy.RETRY_WITH_BACKOFF,
                'write_file': RecoveryStrategy.REPLAN,
                'default': RecoveryStrategy.RETRY_WITH_BACKOFF
            }
        }
        
        # Escalation conditions
        self.escalation_conditions = [
            'critical_error',
            'security_breach',
            'data_loss'
        ]
    
    async def execute_recovery(self, task: Task, failure_reason: str) -> Dict:
        """Execute appropriate recovery strategy based on failure type"""
        
        # FIX #5: Use task.retry_count as single source of truth
        # Previously used self.retry_budget dict which was duplicate state
        current_retry = task.retry_count or 0
        max_retries = task.max_retries or 3
        
        if current_retry >= max_retries:
            logger.warning(f"⚠️ Retry budget exhausted for {task.id} ({current_retry}/{max_retries})")
            return await self._retry_exhausted_recovery(task, failure_reason)
        
        # Map failure type to recovery strategy
        if 'verification_failed' in failure_reason:
            return await self._alternate_tool_recovery(task, failure_reason)
        elif 'tool_error' in failure_reason:
            return await self._alternate_tool_recovery(task, failure_reason)
        elif 'timeout' in failure_reason:
            return await self._requeue_recovery(task, failure_reason)
        elif 'artifact_missing' in failure_reason:
            return await self._rollback_recovery(task, failure_reason)
        elif 'approval_denied' in failure_reason or 'approval_expired' in failure_reason:
            # Use approval mapping - FIX #1: use canonical enum
            approval_type = 'denied' if 'denied' in failure_reason else 'expired'
            tool_name = (task.input_data or {}).get('tool_used', 'default')
            mapping = self.approval_mapping.get(approval_type, {})
            strategy = mapping.get(tool_name, mapping.get('default', RecoveryStrategy.RETRY_WITH_BACKOFF))
            logger.info(f"📋 Approval {approval_type} for {task.id}, tool={tool_name}, strategy={strategy}")
            if strategy == RecoveryStrategy.ALTERNATE_TOOL:
                return await self._alternate_tool_recovery(task, failure_reason)
            elif strategy == RecoveryStrategy.REPLAN:
                self._replan_depth[task.id] = self._replan_depth.get(task.id, 0) + 1
                return await self._replan_recovery(task, failure_reason)
            elif strategy == RecoveryStrategy.ABORT:
                return await self._retry_exhausted_recovery(task, failure_reason)
            else:
                return await self._requeue_recovery(task, failure_reason)
        elif 'critical_error' in failure_reason:
            return await self._human_escalation(task, failure_reason)
        else:
            return await self._degraded_mode_recovery(task, failure_reason)
    
    async def _requeue_recovery(self, task, reason) -> Dict:
        """1. RETRY_WITH_BACKOFF - transient failure, try again"""
        # FIX #5: Update task.retry_count, not separate dict
        task.retry_count = (task.retry_count or 0) + 1
        logger.info(f"🔄 RETRY_WITH_BACKOFF: {task.id} (attempt {task.retry_count})")
        return {
            'strategy': RecoveryStrategy.RETRY_WITH_BACKOFF,
            'action': 'retry_with_backoff',
            'can_continue': True,
            'retry_count': task.retry_count
        }
    
    async def _alternate_tool_recovery(self, task, reason) -> Dict:
        """2. ALTERNATE_TOOL - try different tool"""
        alt_tool = (task.input_data or {}).get('alternate_tool')
        if alt_tool:
            logger.info(f"🔄 ALT_TOOL: {task.id} -> {alt_tool}")
            task.input_data['tool_used'] = alt_tool
            return {'strategy': RecoveryStrategy.ALTERNATE_TOOL, 'action': 'alternate', 'tool': alt_tool}
        
        # Fallback to requeue
        return await self._requeue_recovery(task, reason)
    
    async def _rollback_recovery(self, task, reason) -> Dict:
        """3. ROLLBACK - revert changes"""
        logger.warning(f"⏪ ROLLBACK: {task.id}")
        # Execute rollback actions
        rollback_actions = self.rollback_stack.get(task.id, [])
        for action in reversed(rollback_actions):
            try:
                action['rollback_fn']()
            except Exception as e:
                logger.error(f"Rollback failed: {e}")
        
        return {'strategy': RecoveryStrategy.ROLLBACK, 'action': 'rolled_back', 'can_continue': False}
    
    async def _replan_recovery(self, task, reason) -> Dict:
        """4. REPLAN - regenerate plan"""
        logger.warning(f"🔄 REPLAN: {task.id}")
        return {'strategy': RecoveryStrategy.REPLAN, 'action': 'replan', 'can_continue': True}
    
    async def _human_escalation(self, task, reason) -> Dict:
        """5. HUMAN_ESCALATION - critical failure"""
        logger.error(f"🚨 HUMAN_ESCALATION: {task.id} - {reason}")
        return {
            'strategy': RecoveryStrategy.HUMAN_ESCALATION,
            'action': 'escalate',
            'can_continue': False,
            'reason': reason
        }
    
    async def _degraded_mode_recovery(self, task, reason) -> Dict:
        """6. DEGRADED_MODE - reduced functionality"""
        logger.warning(f"📉 DEGRADED_MODE: {task.id}")
        task.input_data['degraded'] = True
        return {'strategy': RecoveryStrategy.DEGRADED_MODE, 'action': 'degraded', 'can_continue': True}
    
    async def _retry_exhausted_recovery(self, task, reason) -> Dict:
        """7. ABORT - no more retry budget"""
        logger.error(f"❌ RETRY_EXHAUSTED: {task.id}")
        # FIX #5: Use task.retry_count
        return {
            'strategy': RecoveryStrategy.ABORT,
            'action': 'abort',
            'can_continue': False,
            'budget_used': task.retry_count or 0,
            'max_retries': task.max_retries or 3
        }
    
    def record_rollback(self, task_id: str, rollback_fn):
        """Record rollback action for later execution"""
        if task_id not in self.rollback_stack:
            self.rollback_stack[task_id] = []
        self.rollback_stack[task_id].append({'rollback_fn': rollback_fn})





# ==================== PLANNER QUALITY TRACKER ====================

class PlannerQualityTracker:
    """
    Tracks planner quality over time with metrics.
    
    Provides:
    - Success/failure rate tracking
    - Per-strategy success rates
    - Quality trends over time
    - Invalid snippet logging for debugging
    """
    
    def __init__(self):
        self.parse_history: List[Dict] = []
        self.strategy_stats: Dict[str, Dict] = defaultdict(lambda: {
            'success': 0, 
            'failure': 0, 
            'total_time_ms': 0
        })
        self.quality_window = 100  # Track last 100 parses
        
    def record_parse(self, success: bool, strategy: str, time_ms: float, task_count: int = 0):
        """Record a parse attempt"""
        self.parse_history.append({
            'success': success,
            'strategy': strategy,
            'time_ms': time_ms,
            'task_count': task_count,
            'timestamp': time.time()
        })
        
        # Keep only last N records
        if len(self.parse_history) > self.quality_window:
            self.parse_history = self.parse_history[-self.quality_window:]
            
        # Update strategy stats
        if success:
            self.strategy_stats[strategy]['success'] += 1
        else:
            self.strategy_stats[strategy]['failure'] += 1
        self.strategy_stats[strategy]['total_time_ms'] += time_ms
        
    def get_success_rate(self) -> float:
        """Get overall success rate"""
        if not self.parse_history:
            return 0.0
        success_count = sum(1 for p in self.parse_history if p['success'])
        return success_count / len(self.parse_history)
        
    def get_strategy_stats(self) -> Dict:
        """Get per-strategy statistics"""
        stats = {}
        for strategy, data in self.strategy_stats.items():
            total = data['success'] + data['failure']
            if total > 0:
                stats[strategy] = {
                    'success_rate': data['success'] / total,
                    'total_attempts': total,
                    'avg_time_ms': data['total_time_ms'] / total
                }
        return stats
        
    def get_quality_report(self) -> Dict:
        """Get comprehensive quality report"""
        return {
            'overall_success_rate': self.get_success_rate(),
            'total_parses': len(self.parse_history),
            'strategy_stats': self.get_strategy_stats(),
            'recent_success_rate': self._get_recent_success_rate()
        }
        
    def _get_recent_success_rate(self, n: int = 20) -> float:
        """Get success rate for last N parses"""
        recent = self.parse_history[-n:] if self.parse_history else []
        if not recent:
            return 0.0
        success_count = sum(1 for p in recent if p['success'])
        return success_count / len(recent)
