"""
Event Taxonomy - Kengaytirilgan replay event turlari
====================================================

Bu modul replay uchun kerakli barcha event turlarini
o'z ichiga oladi. Hozirgi kernel'dagi sayoz event taxonomy
o'rniga to'liq taxonomy.

Event turlari:
- TASK_LIFECYCLE: Task yaratish, tugatish, muvaffaqiyatsizlik
- DECISION: Qaror qabul qilish (route, recovery, verification)
- EXECUTION: Tool chaqiruvlari va natijalari
- STATE_TRANSITION: Holat o'zgarishlari
- TRANSACTION: Transaction bosqichlari
- RECOVERY: Recovery harakatlari
- VERIFICATION: Verification natijalari
- CHECKPOINT: Checkpoint olish va tiklash
- APPROVAL: Approval kutish
- QUEUE: Queue boshqaruvi
"""

import json
import logging
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import hashlib
import threading

logger = logging.getLogger(__name__)


class EventCategory(str, Enum):
    """Event katigoriyalari"""
    TASK_LIFECYCLE = "task_lifecycle"
    DECISION = "decision"
    EXECUTION = "execution"
    STATE_TRANSITION = "state_transition"
    TRANSACTION = "transaction"
    RECOVERY = "recovery"
    VERIFICATION = "verification"
    CHECKPOINT = "checkpoint"
    APPROVAL = "approval"
    QUEUE = "queue"
    SYSTEM = "system"


class TaskEventType(str, Enum):
    """Task lifecycle eventlari"""
    TASK_CREATED = "task_created"
    TASK_QUEUED = "task_queued"
    TASK_STARTED = "task_started"
    TASK_RUNNING = "task_running"
    TASK_APPROVAL_WAITING = "task_approval_waiting"
    TASK_APPROVED = "task_approved"
    TASK_REJECTED = "task_rejected"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    TASK_CANCELLED = "task_cancelled"
    TASK_TIMEOUT = "task_timeout"
    TASK_RETRY = "task_retry"
    TASK_RESUMED = "task_resumed"


class DecisionEventType(str, Enum):
    """Decision eventlari"""
    ROUTE_SELECTED = "route_selected"
    ARGS_COMPILED = "args_compiled"
    RECOVERY_DECIDED = "recovery_decided"
    VERIFICATION_DECIDED = "verification_decided"
    TERMINATION_DECIDED = "termination_decided"
    ESCALATION_DECIDED = "escalation_decided"
    MODE_SELECTED = "mode_selected"
    PLANNER_SELECTED = "planner_selected"


class ExecutionEventType(str, Enum):
    """Execution eventlari"""
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    TOOL_ERROR = "tool_error"
    TOOL_RETRY = "tool_retry"
    COMMAND_STARTED = "command_started"
    COMMAND_COMPLETED = "command_completed"
    BROWSER_ACTION = "browser_action"
    FILE_OPERATION = "file_operation"


class TransactionEventType(str, Enum):
    """Transaction eventlari"""
    TX_PREPARED = "tx_prepared"
    TX_APPLIED = "tx_applied"
    TX_OBSERVED = "tx_observed"
    TX_VERIFIED = "tx_verified"
    TX_COMMITTED = "tx_committed"
    TX_ROLLBACK_STARTED = "tx_rollback_started"
    TX_ROLLED_BACK = "tx_rolled_back"
    TX_FAILED = "tx_failed"


class RecoveryEventType(str, Enum):
    """Recovery eventlari"""
    RECOVERY_STARTED = "recovery_started"
    RECOVERY_STRATEGY_SELECTED = "recovery_strategy_selected"
    RECOVERY_ACTION_TAKEN = "recovery_action_taken"
    RECOVERY_SUCCEEDED = "recovery_succeeded"
    RECOVERY_FAILED = "recovery_failed"
    ROLLBACK_INITIATED = "rollback_initiated"
    ROLLBACK_COMPLETED = "rollback_completed"
    CHECKPOINT_CREATED = "checkpoint_created"
    CHECKPOINT_RESTORED = "checkpoint_restored"


class VerificationEventType(str, Enum):
    """Verification eventlari"""
    VERIFICATION_STARTED = "verification_started"
    VERIFICATION_PASSED = "verification_passed"
    VERIFICATION_FAILED = "verification_failed"
    EVIDENCE_COLLECTED = "evidence_collected"
    ASSERTION_EVALUATED = "assertion_evaluated"


class QueueEventType(str, Enum):
    """Queue eventlari"""
    TASK_ENQUEUED = "task_enqueued"
    TASK_DEQUEUED = "task_dequeued"
    TASK_REPRIORITIZED = "task_reprioritized"
    QUEUE_REORDERED = "queue_reordered"
    QUEUE_POSITION_CHANGED = "queue_position_changed"


@dataclass
class ReplayEvent:
    """
    Replay Event - To'liq replay uchun event
    
    Bu class historical run'dagi har bir eventni
    to'liq ma'lumotlar bilan saqlaydi.
    """
    # Event identity
    event_id: str
    event_type: str
    category: str
    timestamp: float
    
    # Context
    task_id: Optional[str] = None
    session_id: Optional[str] = None
    run_id: Optional[str] = None
    
    # Event data
    data: Dict[str, Any] = field(default_factory=dict)
    result: Optional[Any] = None
    error: Optional[str] = None
    
    # Deterministic info
    deterministic_time: Optional[float] = None
    sequence_number: int = 0
    
    # Provenance
    source: str = "kernel"
    checksum: Optional[str] = None
    
    def __post_init__(self):
        """Event yaratilgandan so'ng"""
        if not self.checksum:
            self.checksum = self._compute_checksum()
    
    def _compute_checksum(self) -> str:
        """Event checksum hisoblash"""
        content = json.dumps({
            'event_id': self.event_id,
            'event_type': self.event_type,
            'task_id': self.task_id,
            'timestamp': self.timestamp,
            'data': self.data
        }, sort_keys=True)
        
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def to_dict(self) -> dict:
        """Eventni dictga aylantirish"""
        return {
            'event_id': self.event_id,
            'event_type': self.event_type,
            'category': self.category,
            'timestamp': self.timestamp,
            'task_id': self.task_id,
            'session_id': self.session_id,
            'run_id': self.run_id,
            'data': self.data,
            'result': self.result,
            'error': self.error,
            'deterministic_time': self.deterministic_time,
            'sequence_number': self.sequence_number,
            'source': self.source,
            'checksum': self.checksum
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'ReplayEvent':
        """Dict'dan event yaratish"""
        return cls(**data)
    
    def with_sequence(self, seq: int) -> 'ReplayEvent':
        """Sequence number qo'shish"""
        self.sequence_number = seq
        return self


class EventTaxonomy:
    """
    Event Taxonomy - Barcha event turlari va ularning
    o'zaro aloqalarini boshqaradi
    
    Bu class:
    - Event turlarini ro'yxatlaydi
    - Event oqimini boshqaradi
    - Replay uchun to'liq event history yaratadi
    """
    
    # Event type to category mapping
    TYPE_TO_CATEGORY: Dict[str, str] = {
        # Task lifecycle
        'task_created': EventCategory.TASK_LIFECYCLE,
        'task_queued': EventCategory.TASK_LIFECYCLE,
        'task_started': EventCategory.TASK_LIFECYCLE,
        'task_running': EventCategory.TASK_LIFECYCLE,
        'task_approval_waiting': EventCategory.TASK_LIFECYCLE,
        'task_approved': EventCategory.TASK_LIFECYCLE,
        'task_rejected': EventCategory.TASK_LIFECYCLE,
        'task_completed': EventCategory.TASK_LIFECYCLE,
        'task_failed': EventCategory.TASK_LIFECYCLE,
        'task_cancelled': EventCategory.TASK_LIFECYCLE,
        'task_timeout': EventCategory.TASK_LIFECYCLE,
        'task_retry': EventCategory.TASK_LIFECYCLE,
        'task_resumed': EventCategory.TASK_LIFECYCLE,
        
        # Decision
        'route_selected': EventCategory.DECISION,
        'args_compiled': EventCategory.DECISION,
        'recovery_decided': EventCategory.DECISION,
        'verification_decided': EventCategory.DECISION,
        'termination_decided': EventCategory.DECISION,
        'escalation_decided': EventCategory.DECISION,
        'mode_selected': EventCategory.DECISION,
        'planner_selected': EventCategory.DECISION,
        
        # Execution
        'tool_call': EventCategory.EXECUTION,
        'tool_result': EventCategory.EXECUTION,
        'tool_error': EventCategory.EXECUTION,
        'tool_retry': EventCategory.EXECUTION,
        'command_started': EventCategory.EXECUTION,
        'command_completed': EventCategory.EXECUTION,
        'browser_action': EventCategory.EXECUTION,
        'file_operation': EventCategory.EXECUTION,
        
        # Transaction
        'tx_prepared': EventCategory.TRANSACTION,
        'tx_applied': EventCategory.TRANSACTION,
        'tx_observed': EventCategory.TRANSACTION,
        'tx_verified': EventCategory.TRANSACTION,
        'tx_committed': EventCategory.TRANSACTION,
        'tx_rollback_started': EventCategory.TRANSACTION,
        'tx_rolled_back': EventCategory.TRANSACTION,
        'tx_failed': EventCategory.TRANSACTION,
        
        # Recovery
        'recovery_started': EventCategory.RECOVERY,
        'recovery_strategy_selected': EventCategory.RECOVERY,
        'recovery_action_taken': EventCategory.RECOVERY,
        'recovery_succeeded': EventCategory.RECOVERY,
        'recovery_failed': EventCategory.RECOVERY,
        'rollback_initiated': EventCategory.RECOVERY,
        'rollback_completed': EventCategory.RECOVERY,
        'checkpoint_created': EventCategory.RECOVERY,
        'checkpoint_restored': EventCategory.RECOVERY,
        
        # Verification
        'verification_started': EventCategory.VERIFICATION,
        'verification_passed': EventCategory.VERIFICATION,
        'verification_failed': EventCategory.VERIFICATION,
        'evidence_collected': EventCategory.VERIFICATION,
        'assertion_evaluated': EventCategory.VERIFICATION,
        
        # Queue
        'task_enqueued': EventCategory.QUEUE,
        'task_dequeued': EventCategory.QUEUE,
        'task_reprioritized': EventCategory.QUEUE,
        'queue_reordered': EventCategory.QUEUE,
        'queue_position_changed': EventCategory.QUEUE,
    }
    
    def __init__(self):
        self.events: List[ReplayEvent] = []
        self._lock = threading.RLock()
        self._sequence = 0
    
    def add_event(
        self,
        event_type: str,
        task_id: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
        run_id: Optional[str] = None,
        **kwargs
    ) -> ReplayEvent:
        """
        Event qo'shish
        
        Args:
            event_type: Event turi
            task_id: Task ID
            data: Event ma'lumotlari
            session_id: Session ID
            run_id: Run ID
            
        Returns:
            Yaratilgan event
        """
        import time
        import uuid
        
        with self._lock:
            self._sequence += 1
            
            event = ReplayEvent(
                event_id=str(uuid.uuid4()),
                event_type=event_type,
                category=self.get_category(event_type),
                timestamp=time.time(),
                task_id=task_id,
                session_id=session_id,
                run_id=run_id,
                data=data or {},
                sequence_number=self._sequence,
                **kwargs
            )
            
            self.events.append(event)
            return event
    
    def get_category(self, event_type: str) -> str:
        """Event turi uchun category olish"""
        return self.TYPE_TO_CATEGORY.get(event_type, EventCategory.SYSTEM)
    
    def get_events_by_type(self, event_type: str) -> List[ReplayEvent]:
        """Event turi bo'yicha filterlash"""
        with self._lock:
            return [e for e in self.events if e.event_type == event_type]
    
    def get_events_by_category(self, category: str) -> List[ReplayEvent]:
        """Category bo'yicha filterlash"""
        with self._lock:
            return [e for e in self.events if e.category == category]
    
    def get_events_by_task(self, task_id: str) -> List[ReplayEvent]:
        """Task ID bo'yicha filterlash"""
        with self._lock:
            return [e for e in self.events if e.task_id == task_id]
    
    def get_events_in_range(self, start: float, end: float) -> List[ReplayEvent]:
        """Vaqt oralig'ida filterlash"""
        with self._lock:
            return [e for e in self.events if start <= e.timestamp <= end]
    
    def get_task_lifecycle(self, task_id: str) -> List[ReplayEvent]:
        """Taskning to'liq lifecycle'ini olish"""
        with self._lock:
            return sorted(
                [e for e in self.events if e.task_id == task_id],
                key=lambda e: e.sequence_number
            )
    
    def get_decision_sequence(self, task_id: str) -> List[ReplayEvent]:
        """Task bo'yicha barcha qarorlarni olish"""
        with self._lock:
            return sorted(
                [e for e in self.events 
                 if e.task_id == task_id and e.category == EventCategory.DECISION],
                key=lambda e: e.sequence_number
            )
    
    def get_execution_trace(self, task_id: str) -> List[ReplayEvent]:
        """Taskning execution trace'ini olish"""
        with self._lock:
            return sorted(
                [e for e in self.events 
                 if e.task_id == task_id and e.category == EventCategory.EXECUTION],
                key=lambda e: e.sequence_number
            )
    
    def get_transaction_history(self, task_id: str) -> List[ReplayEvent]:
        """Taskning transaction historysini olish"""
        with self._lock:
            return sorted(
                [e for e in self.events 
                 if e.task_id == task_id and e.category == EventCategory.TRANSACTION],
                key=lambda e: e.sequence_number
            )
    
    def verify_integrity(self) -> Tuple[bool, List[str]]:
        """
        Event taxonomy integritysini tekshirish
        
        Returns:
            (is_valid, list of errors)
        """
        errors = []
        
        with self._lock:
            # Check sequence numbers
            for i, event in enumerate(self.events):
                if event.sequence_number != i + 1:
                    errors.append(f"Sequence gap at index {i}: expected {i+1}, got {event.sequence_number}")
            
            # Check checksums
            for event in self.events:
                expected = event._compute_checksum()
                if event.checksum != expected:
                    errors.append(f"Checksum mismatch for event {event.event_id}")
            
            # Check required fields
            for event in self.events:
                if not event.event_id:
                    errors.append(f"Missing event_id at sequence {event.sequence_number}")
                if not event.event_type:
                    errors.append(f"Missing event_type at sequence {event.sequence_number}")
            
            return len(errors) == 0, errors
    
    def to_json(self, path: str) -> None:
        """Event taxonomyni JSON faylga saqlash"""
        with self._lock:
            data = {
                'events': [e.to_dict() for e in self.events],
                'metadata': {
                    'total_events': len(self.events),
                    'categories': list(set(e.category for e in self.events)),
                    'event_types': list(set(e.event_type for e in self.events))
                }
            }
        
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Event taxonomy saved to {path}")
    
    @classmethod
    def from_json(cls, path: str) -> 'EventTaxonomy':
        """JSON fayldan event taxonomy yuklash"""
        with open(path, 'r') as f:
            data = json.load(f)
        
        taxonomy = cls()
        
        for event_data in data.get('events', []):
            event = ReplayEvent.from_dict(event_data)
            taxonomy.events.append(event)
        
        logger.info(f"Event taxonomy loaded from {path}: {len(taxonomy.events)} events")
        return taxonomy
    
    def __len__(self) -> int:
        return len(self.events)
    
    def __repr__(self) -> str:
        return f"EventTaxonomy(events={len(self.events)})"


# Helper functions for creating events

def create_task_event(
    event_type: str,
    task_id: str,
    data: Optional[Dict[str, Any]] = None,
    **kwargs
) -> ReplayEvent:
    """Task event yaratish uchun yordamchi funksiya"""
    return ReplayEvent(
        event_id=f"evt_{task_id}_{event_type}",
        event_type=event_type,
        category=EventCategory.TASK_LIFECYCLE,
        timestamp=__import__('time').time(),
        task_id=task_id,
        data=data or {},
        **kwargs
    )


def create_decision_event(
    event_type: str,
    task_id: str,
    decision_data: Dict[str, Any],
    **kwargs
) -> ReplayEvent:
    """Decision event yaratish uchun yordamchi funksiya"""
    return ReplayEvent(
        event_id=f"dec_{task_id}_{event_type}",
        event_type=event_type,
        category=EventCategory.DECISION,
        timestamp=__import__('time').time(),
        task_id=task_id,
        data=decision_data,
        **kwargs
    )


def create_execution_event(
    tool_name: str,
    task_id: str,
    args: Dict[str, Any],
    result: Any = None,
    error: Optional[str] = None,
    **kwargs
) -> ReplayEvent:
    """Execution event yaratish uchun yordamchi funksiya"""
    return ReplayEvent(
        event_id=f"exec_{task_id}_{tool_name}",
        event_type="tool_call",
        category=EventCategory.EXECUTION,
        timestamp=__import__('time').time(),
        task_id=task_id,
        data={'tool': tool_name, 'args': args},
        result=result,
        error=error,
        **kwargs
    )
