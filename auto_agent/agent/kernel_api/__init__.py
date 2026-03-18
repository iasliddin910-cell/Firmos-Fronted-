"""
OmniAgent X - Kernel API Surface Contract
========================================
Canonical API interface for the kernel.

This module provides:
- Typed command/query separation
- Response envelopes with consistent structure
- Event streaming for async updates
- Adapter boundaries for external integrations
- API versioning and deprecation policies

Key Components:
- KernelCommand: Typed commands for state mutations
- KernelQuery: Typed queries for read operations
- KernelResponseEnvelope: Consistent response wrapper
- KernelEventStream: Async event streaming
- AdapterBoundary: External integration adapter base
- KernelAPI: Main kernel interface
- APIVersion: Version tracking and deprecation
"""

import os
import json
import logging
import time
import asyncio
import uuid
from typing import Dict, List, Any, Optional, Callable, Set, Union, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from collections import defaultdict
import copy

logger = logging.getLogger(__name__)


# ==================== COMMAND TYPES ====================

class CommandKind(str, Enum):
    """Types of kernel commands"""
    # Task management
    SUBMIT_GOAL = "submit_goal"
    SUBMIT_TASK_GRAPH = "submit_task_graph"
    RESUME_TASK = "resume_task"
    PAUSE_TASK = "pause_task"
    CANCEL_TASK = "cancel_task"
    CREATE_TASK = "create_task"
    
    # Approval
    APPROVE_REQUEST = "approve_request"
    REJECT_REQUEST = "reject_request"
    
    # Checkpoint/Recovery
    RESTORE_CHECKPOINT = "restore_checkpoint"
    SAVE_CHECKPOINT = "save_checkpoint"
    CREATE_SNAPSHOT = "create_snapshot"
    
    # Replay/Simulation
    RUN_REPLAY = "run_replay"
    RUN_SIMULATION = "run_simulation"
    
    # Canary
    RUN_CANARY = "run_canary"
    
    # Mode
    SET_MODE = "set_mode"
    ENTER_SAFE_MODE = "enter_safe_mode"
    
    # Maintenance
    FLUSH_STATE = "flush_state"
    RESET_KERNEL = "reset_kernel"


class QueryKind(str, Enum):
    """Types of kernel queries"""
    # Task queries
    GET_TASK = "get_task"
    GET_TASK_STATUS = "get_task_status"
    GET_RUN_TRACE = "get_run_trace"
    
    # Health queries
    GET_HEALTH = "get_health"
    GET_CAPABILITIES = "get_capabilities"
    
    # Budget queries
    GET_BUDGET = "get_budget"
    GET_BUDGET_STATUS = "get_budget_status"
    
    # State queries
    GET_QUEUE_SUMMARY = "get_queue_summary"
    GET_PENDING_TASKS = "get_pending_tasks"
    GET_COMPLETED_TASKS = "get_completed_tasks"
    
    # Handoff queries
    GET_HANDOFF = "get_handoff"
    GET_PENDING_APPROVALS = "get_pending_approvals"
    
    # Invariant queries
    GET_INVARIANT_REPORT = "get_invariant_report"
    
    # System queries
    GET_KERNEL_STATUS = "get_kernel_status"
    GET_SYSTEM_INFO = "get_system_info"


# ==================== COMMAND / QUERY CLASSES ====================

@dataclass
class KernelCommand:
    """
    A typed command for kernel operations.
    
    Commands are operations that mutate state.
    """
    command_id: str
    kind: CommandKind
    payload: Dict[str, Any]
    issued_at: float = field(default_factory=time.time)
    source: str = "unknown"
    
    # Optional correlation
    correlation_id: Optional[str] = None
    reply_to: Optional[str] = None
    
    def __post_init__(self):
        if not self.command_id:
            self.command_id = str(uuid.uuid4())
    
    def to_dict(self) -> Dict:
        return {
            "command_id": self.command_id,
            "kind": self.kind.value,
            "payload": self.payload,
            "issued_at": self.issued_at,
            "source": self.source,
            "correlation_id": self.correlation_id,
            "reply_to": self.reply_to
        }
    
    @classmethod
    def submit_goal(cls, goal: str, source: str = "unknown") -> 'KernelCommand':
        return cls(
            command_id=str(uuid.uuid4()),
            kind=CommandKind.SUBMIT_GOAL,
            payload={"goal": goal},
            source=source
        )
    
    @classmethod
    def submit_task(cls, task_data: Dict, source: str = "unknown") -> 'KernelCommand':
        return cls(
            command_id=str(uuid.uuid4()),
            kind=CommandKind.CREATE_TASK,
            payload=task_data,
            source=source
        )
    
    @classmethod
    def resume_task(cls, task_id: str, source: str = "unknown") -> 'KernelCommand':
        return cls(
            command_id=str(uuid.uuid4()),
            kind=CommandKind.RESUME_TASK,
            payload={"task_id": task_id},
            source=source
        )
    
    @classmethod
    def cancel_task(cls, task_id: str, reason: str = "", source: str = "unknown") -> 'KernelCommand':
        return cls(
            command_id=str(uuid.uuid4()),
            kind=CommandKind.CANCEL_TASK,
            payload={"task_id": task_id, "reason": reason},
            source=source
        )


@dataclass
class KernelQuery:
    """
    A typed query for kernel read operations.
    
    Queries are operations that don't mutate state.
    """
    query_id: str
    kind: QueryKind
    params: Dict[str, Any] = field(default_factory=dict)
    issued_at: float = field(default_factory=time.time)
    source: str = "unknown"
    
    def __post_init__(self):
        if not self.query_id:
            self.query_id = str(uuid.uuid4())
    
    def to_dict(self) -> Dict:
        return {
            "query_id": self.query_id,
            "kind": self.kind.value,
            "params": self.params,
            "issued_at": self.issued_at,
            "source": self.source
        }
    
    @classmethod
    def get_task(cls, task_id: str, source: str = "unknown") -> 'KernelQuery':
        return cls(
            query_id=str(uuid.uuid4()),
            kind=QueryKind.GET_TASK,
            params={"task_id": task_id},
            source=source
        )
    
    @classmethod
    def get_health(cls, source: str = "unknown") -> 'KernelQuery':
        return cls(
            query_id=str(uuid.uuid4()),
            kind=QueryKind.GET_HEALTH,
            params={},
            source=source
        )
    
    @classmethod
    def get_capabilities(cls, source: str = "unknown") -> 'KernelQuery':
        return cls(
            query_id=str(uuid.uuid4()),
            kind=QueryKind.GET_CAPABILITIES,
            params={},
            source=source
        )


# ==================== RESPONSE ENVELOPE ====================

class ResponseStatus(str, Enum):
    """Response status codes"""
    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"
    PENDING = "pending"
    TIMEOUT = "timeout"
    REJECTED = "rejected"


@dataclass
class KernelResponseEnvelope:
    """
    Consistent response wrapper for all kernel operations.
    """
    ok: bool
    status: ResponseStatus
    result: Any = None
    error: Optional[Dict[str, Any]] = None
    trace_ref: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    
    # Metadata
    operation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    issued_at: float = field(default_factory=time.time)
    execution_time_ms: float = 0.0
    
    # Version info
    api_version: str = "v1"
    
    def to_dict(self) -> Dict:
        return {
            "ok": self.ok,
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
            "trace_ref": self.trace_ref,
            "warnings": self.warnings,
            "operation_id": self.operation_id,
            "issued_at": self.issued_at,
            "execution_time_ms": self.execution_time_ms,
            "api_version": self.api_version
        }
    
    @classmethod
    def success(cls, result: Any = None, trace_ref: Optional[str] = None, 
                warnings: Optional[List[str]] = None) -> 'KernelResponseEnvelope':
        return cls(
            ok=True,
            status=ResponseStatus.SUCCESS,
            result=result,
            trace_ref=trace_ref,
            warnings=warnings or []
        )
    
    @classmethod
    def failure(cls, error: Dict[str, Any], result: Any = None,
                warnings: Optional[List[str]] = None) -> 'KernelResponseEnvelope':
        return cls(
            ok=False,
            status=ResponseStatus.FAILURE,
            result=result,
            error=error,
            warnings=warnings or []
        )
    
    @classmethod
    def partial(cls, result: Any, warnings: List[str]) -> 'KernelResponseEnvelope':
        return cls(
            ok=True,
            status=ResponseStatus.PARTIAL,
            result=result,
            warnings=warnings
        )
    
    @classmethod
    def pending(cls, operation_id: str) -> 'KernelResponseEnvelope':
        return cls(
            ok=True,
            status=ResponseStatus.PENDING,
            result={"operation_id": operation_id}
        )


# ==================== EVENT STREAM ====================

class EventType(str, Enum):
    """Kernel event types"""
    TASK_CREATED = "task_created"
    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    TASK_WAITING_APPROVAL = "task_waiting_approval"
    TASK_CANCELLED = "task_cancelled"
    APPROVAL_REQUESTED = "approval_requested"
    APPROVAL_GRANTED = "approval_granted"
    APPROVAL_DENIED = "approval_denied"
    HANDOFF_CREATED = "handoff_created"
    HANDOFF_COMPLETED = "handoff_completed"
    HEALTH_PROBE_STARTED = "health_probe_started"
    HEALTH_PROBE_PASSED = "health_probe_passed"
    HEALTH_PROBE_FAILED = "health_probe_failed"
    CAPABILITY_GATED = "capability_gated"
    REPLAY_STARTED = "replay_started"
    REPLAY_COMPLETED = "replay_completed"
    REPLAY_FAILED = "replay_failed"
    DIVERGENCE_DETECTED = "divergence_detected"
    CANARY_STARTED = "canary_started"
    CANARY_PASSED = "canary_passed"
    CANARY_FAILED = "canary_failed"
    BUDGET_EXHAUSTED = "budget_exhausted"
    MODE_CHANGED = "mode_changed"
    CHECKPOINT_SAVED = "checkpoint_saved"
    CHECKPOINT_RESTORED = "checkpoint_restored"


@dataclass
class KernelEvent:
    """A kernel event for streaming"""
    event_type: EventType
    data: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)
    source: str = "kernel"
    trace_ref: Optional[str] = None
    correlation_id: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "event_type": self.event_type.value,
            "data": self.data,
            "timestamp": self.timestamp,
            "source": self.source,
            "trace_ref": self.trace_ref,
            "correlation_id": self.correlation_id
        }


class KernelEventStream:
    """Event stream for async kernel updates."""
    
    def __init__(self, max_history: int = 1000):
        self._subscribers: Dict[EventType, List[Callable]] = defaultdict(list)
        self._global_subscribers: List[Callable] = []
        self._event_history: List[KernelEvent] = []
        self._max_history = max_history
        self._lock = asyncio.Lock()
        
        logger.info("KernelEventStream initialized")
    
    async def publish(self, event: KernelEvent):
        """Publish an event to all subscribers"""
        async with self._lock:
            self._event_history.append(event)
            if len(self._event_history) > self._max_history:
                self._event_history = self._event_history[-self._max_history:]
        
        await self._notify_subscribers(event)
    
    def publish_sync(self, event: KernelEvent):
        """Synchronous publish for non-async contexts"""
        self._event_history.append(event)
        if len(self._event_history) > self._max_history:
            self._event_history = self._event_history[-self._max_history:]
        
        for callback in self._subscribers.get(event.event_type, []):
            try:
                callback(event)
            except Exception as e:
                logger.error(f"Event subscriber error: {e}")
        
        for callback in self._global_subscribers:
            try:
                callback(event)
            except Exception as e:
                logger.error(f"Global event subscriber error: {e}")
    
    async def _notify_subscribers(self, event: KernelEvent):
        """Notify relevant subscribers"""
        for callback in self._subscribers.get(event.event_type, []):
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(event)
                else:
                    callback(event)
            except Exception as e:
                logger.error(f"Event subscriber error: {e}")
        
        for callback in self._global_subscribers:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(event)
                else:
                    callback(event)
            except Exception as e:
                logger.error(f"Global event subscriber error: {e}")
    
    def subscribe(self, event_type: EventType, callback: Callable):
        """Subscribe to specific event type"""
        self._subscribers[event_type].append(callback)
    
    def subscribe_all(self, callback: Callable):
        """Subscribe to all events"""
        self._global_subscribers.append(callback)
    
    def get_history(self, event_type: Optional[EventType] = None, 
                   limit: int = 100) -> List[KernelEvent]:
        """Get event history"""
        if event_type:
            events = [e for e in self._event_history if e.event_type == event_type]
        else:
            events = self._event_history
        return events[-limit:]


# ==================== ADAPTER BOUNDARY ====================

@dataclass
class AdapterConfig:
    """Configuration for an adapter"""
    adapter_name: str
    adapter_type: str
    version: str
    capabilities: List[str] = field(default_factory=list)
    rate_limit: Optional[int] = None


class AdapterBoundary:
    """Base class for external adapters."""
    
    def __init__(self, config: AdapterConfig, kernel_api: Optional['KernelAPI'] = None):
        self.config = config
        self.kernel_api = kernel_api
        self._enabled = True
        
        logger.info(f"AdapterBoundary initialized: {config.adapter_name}")
    
    def is_enabled(self) -> bool:
        return self._enabled
    
    def enable(self):
        self._enabled = True
    
    def disable(self):
        self._enabled = False
    
    def validate_command(self, command: Dict) -> Tuple[bool, Optional[str]]:
        if not self._enabled:
            return False, "Adapter is disabled"
        if "kind" not in command:
            return False, "Command missing 'kind' field"
        return True, None
    
    def validate_query(self, query: Dict) -> Tuple[bool, Optional[str]]:
        if not self._enabled:
            return False, "Adapter is disabled"
        if "kind" not in query:
            return False, "Query missing 'kind' field"
        return True, None
    
    def adapt_command_to_kernel(self, raw_command: Dict) -> KernelCommand:
        return KernelCommand(
            command_id=raw_command.get("command_id", str(uuid.uuid4())),
            kind=CommandKind(raw_command["kind"]),
            payload=raw_command.get("payload", {}),
            source=self.config.adapter_name
        )
    
    def adapt_query_to_kernel(self, raw_query: Dict) -> KernelQuery:
        return KernelQuery(
            query_id=raw_query.get("query_id", str(uuid.uuid4())),
            kind=QueryKind(raw_query["kind"]),
            params=raw_query.get("params", {}),
            source=self.config.adapter_name
        )
    
    def adapt_response_from_kernel(self, response: KernelResponseEnvelope) -> Dict:
        return response.to_dict()


# ==================== API VERSIONING ====================

@dataclass
class APIVersion:
    """API version information"""
    version: str
    deprecated: bool = False
    deprecation_warning: Optional[str] = None
    removal_version: Optional[str] = None
    migration_guide: Optional[str] = None


class DeprecationPolicy:
    """API versioning and deprecation policy manager."""
    
    def __init__(self):
        self._versions: Dict[str, APIVersion] = {
            "v1": APIVersion(version="v1", deprecated=False)
        }
        self._current_version = "v1"
        
        logger.info("DeprecationPolicy initialized")
    
    def register_version(self, version: APIVersion):
        self._versions[version.version] = version
    
    def deprecate_version(self, version: str, removal_version: str, 
                         migration_guide: str):
        if version in self._versions:
            self._versions[version].deprecated = True
            self._versions[version].removal_version = removal_version
            self._versions[version].migration_guide = migration_guide
            self._versions[version].deprecation_warning = (
                f"API version {version} is deprecated. "
                f"It will be removed in {removal_version}."
            )
    
    def get_version(self, version: str) -> Optional[APIVersion]:
        return self._versions.get(version)
    
    def get_current_version(self) -> str:
        return self._current_version
    
    def set_current_version(self, version: str):
        if version in self._versions:
            self._current_version = version
    
    def is_supported(self, version: str) -> bool:
        return version in self._versions and not self._versions[version].deprecated
    
    def get_deprecation_warning(self, version: str) -> Optional[str]:
        v = self._versions.get(version)
        return v.deprecation_warning if v else None


# ==================== KERNEL API ====================

class KernelAPI:
    """
    The canonical API interface for the kernel.
    
    All external integrations should use this API.
    """
    
    def __init__(self, kernel=None):
        self.kernel = kernel
        self.event_stream = KernelEventStream()
        self.deprecation_policy = DeprecationPolicy()
        self._adapters: Dict[str, AdapterBoundary] = {}
        
        # Register handlers
        self._command_handlers = {}
        self._query_handlers = {}
        self._register_handlers()
        
        logger.info("KernelAPI initialized")
    
    def _register_handlers(self):
        """Register command and query handlers"""
        self._command_handlers = {
            CommandKind.SUBMIT_GOAL: self._handle_submit_goal,
            CommandKind.CREATE_TASK: self._handle_create_task,
            CommandKind.RESUME_TASK: self._handle_resume_task,
            CommandKind.PAUSE_TASK: self._handle_pause_task,
            CommandKind.CANCEL_TASK: self._handle_cancel_task,
            CommandKind.APPROVE_REQUEST: self._handle_approve,
            CommandKind.REJECT_REQUEST: self._handle_reject,
            CommandKind.RESTORE_CHECKPOINT: self._handle_restore,
            CommandKind.RUN_REPLAY: self._handle_replay,
            CommandKind.RUN_CANARY: self._handle_canary,
            CommandKind.SET_MODE: self._handle_set_mode,
        }
        
        self._query_handlers = {
            QueryKind.GET_TASK: self._handle_get_task,
            QueryKind.GET_TASK_STATUS: self._handle_get_task_status,
            QueryKind.GET_HEALTH: self._handle_get_health,
            QueryKind.GET_CAPABILITIES: self._handle_get_capabilities,
            QueryKind.GET_BUDGET: self._handle_get_budget,
            QueryKind.GET_QUEUE_SUMMARY: self._handle_get_queue_summary,
            QueryKind.GET_KERNEL_STATUS: self._handle_get_kernel_status,
        }
    
    # Command handlers
    async def execute_command(self, command: KernelCommand) -> KernelResponseEnvelope:
        start_time = time.time()
        try:
            handler = self._command_handlers.get(command.kind)
            if not handler:
                return KernelResponseEnvelope.failure(
                    error={"code": "UNKNOWN_COMMAND", "message": f"Unknown command: {command.kind}"}
                )
            
            if asyncio.iscoroutinefunction(handler):
                result = await handler(command.payload)
            else:
                result = handler(command.payload)
            
            execution_time = (time.time() - start_time) * 1000
            return KernelResponseEnvelope.success(
                result=result,
                trace_ref=command.correlation_id,
                execution_time_ms=execution_time
            )
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            return KernelResponseEnvelope.failure(
                error={"code": "EXECUTION_ERROR", "message": str(e)},
                execution_time_ms=execution_time
            )
    
    def _handle_submit_goal(self, payload: Dict) -> Dict:
        goal = payload.get("goal", "")
        logger.info(f"Submitting goal: {goal}")
        if self.kernel:
            task_id = self.kernel.submit_task({"description": goal})
            return {"task_id": task_id, "status": "submitted"}
        return {"status": "simulated", "task_id": "simulated_task"}
    
    def _handle_create_task(self, payload: Dict) -> Dict:
        logger.info(f"Creating task: {payload}")
        if self.kernel:
            task_id = self.kernel.submit_task(payload)
            return {"task_id": task_id, "status": "created"}
        return {"status": "simulated", "task_id": "simulated_task"}
    
    def _handle_resume_task(self, payload: Dict) -> Dict:
        task_id = payload.get("task_id")
        logger.info(f"Resuming task: {task_id}")
        return {"task_id": task_id, "status": "resumed"}
    
    def _handle_pause_task(self, payload: Dict) -> Dict:
        task_id = payload.get("task_id")
        return {"task_id": task_id, "status": "paused"}
    
    def _handle_cancel_task(self, payload: Dict) -> Dict:
        task_id = payload.get("task_id")
        return {"task_id": task_id, "status": "cancelled"}
    
    def _handle_approve(self, payload: Dict) -> Dict:
        request_id = payload.get("request_id")
        return {"request_id": request_id, "status": "approved"}
    
    def _handle_reject(self, payload: Dict) -> Dict:
        request_id = payload.get("request_id")
        return {"request_id": request_id, "status": "rejected"}
    
    def _handle_restore(self, payload: Dict) -> Dict:
        checkpoint_id = payload.get("checkpoint_id")
        return {"checkpoint_id": checkpoint_id, "status": "restored"}
    
    def _handle_replay(self, payload: Dict) -> Dict:
        scenario_id = payload.get("scenario_id")
        return {"scenario_id": scenario_id, "status": "completed"}
    
    def _handle_canary(self, payload: Dict) -> Dict:
        return {"status": "passed", "tests": 5}
    
    def _handle_set_mode(self, payload: Dict) -> Dict:
        mode = payload.get("mode")
        return {"mode": mode, "status": "set"}
    
    # Query handlers
    async def execute_query(self, query: KernelQuery) -> KernelResponseEnvelope:
        start_time = time.time()
        try:
            handler = self._query_handlers.get(query.kind)
            if not handler:
                return KernelResponseEnvelope.failure(
                    error={"code": "UNKNOWN_QUERY", "message": f"Unknown query: {query.kind}"}
                )
            
            if asyncio.iscoroutinefunction(handler):
                result = await handler(query.params)
            else:
                result = handler(query.params)
            
            execution_time = (time.time() - start_time) * 1000
            return KernelResponseEnvelope.success(
                result=result,
                execution_time_ms=execution_time
            )
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            return KernelResponseEnvelope.failure(
                error={"code": "EXECUTION_ERROR", "message": str(e)},
                execution_time_ms=execution_time
            )
    
    def _handle_get_task(self, params: Dict) -> Dict:
        task_id = params.get("task_id")
        return {"task_id": task_id, "task": None}
    
    def _handle_get_task_status(self, params: Dict) -> Dict:
        task_id = params.get("task_id")
        return {"task_id": task_id, "status": "unknown"}
    
    def _handle_get_health(self, params: Dict) -> Dict:
        if self.kernel and hasattr(self.kernel, 'check_health'):
            return self.kernel.check_health()
        return {"status": "unknown", "posture": "unknown"}
    
    def _handle_get_capabilities(self, params: Dict) -> Dict:
        if self.kernel and hasattr(self.kernel, 'get_capability_status'):
            return self.kernel.get_capability_status()
        return {}
    
    def _handle_get_budget(self, params: Dict) -> Dict:
        return {"budget": "unknown", "remaining": 0}
    
    def _handle_get_queue_summary(self, params: Dict) -> Dict:
        return {"pending": 0, "running": 0, "completed": 0, "failed": 0}
    
    def _handle_get_kernel_status(self, params: Dict) -> Dict:
        status = "running"
        if self.kernel and hasattr(self.kernel, 'state'):
            status = str(self.kernel.state)
        return {"status": status, "version": "2.0.0"}
    
    # Adapter management
    def register_adapter(self, adapter: AdapterBoundary):
        self._adapters[adapter.config.adapter_name] = adapter
    
    def get_adapter(self, name: str) -> Optional[AdapterBoundary]:
        return self._adapters.get(name)
    
    # Convenience methods
    async def submit_goal(self, goal: str) -> KernelResponseEnvelope:
        command = KernelCommand.submit_goal(goal)
        return await self.execute_command(command)
    
    async def get_health(self) -> KernelResponseEnvelope:
        query = KernelQuery.get_health()
        return await self.execute_query(query)
    
    async def get_task(self, task_id: str) -> KernelResponseEnvelope:
        query = KernelQuery.get_task(task_id)
        return await self.execute_query(query)


# ==================== FACTORY ====================

def create_kernel_api(kernel=None) -> KernelAPI:
    return KernelAPI(kernel)


def create_adapter(config: AdapterConfig, kernel_api: KernelAPI) -> AdapterBoundary:
    return AdapterBoundary(config, kernel_api)
