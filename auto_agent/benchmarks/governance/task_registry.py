"""
TaskRegistry - Central Task Registry
===================================

Markaziy reestr - har benchmark taski uchun metadata.

Bu tizim benchmarkning yuragi:
- Task metadata markaziy saqlash
- Ownership tracking
- Lifecycle state
- Version history
- Provenance tracking

Definition of Done:
1. Har task registry'da metadata bilan turadi.
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Any, Optional, Set
from enum import Enum
from datetime import datetime
import json
import os


# ==================== TASK LIFECYCLE STATE ====================

class TaskState(str, Enum):
    """Task hayot sikli state'lari."""
    DRAFT = "draft"           # Yangi yozilayotgan
    CANDIDATE = "candidate"   # Validatsiya jarayonida
    VALIDATED = "validated"   # Validatsiyadan o'tgan
    STABLE = "stable"        # Official leaderboardda
    QUARANTINED = "quarantined"  # Flaky yoki shubhali
    DEPRECATED = "deprecated" # Eskirgan, lekin hali o'chirilmagan
    ARCHIVED = "archived"     # To'liq arxivlangan
    REJECTED = "reject"      # Rad etilgan


class FlakeStatus(str, Enum):
    """Flakiness status."""
    UNKNOWN = "unknown"
    STABLE = "stable"
    FLaky_OCCASIONAL = "flaky_occasional"
    FLaky_FREQUENT = "flaky_frequent"
    QUARANTINED = "quarantined"


class ContaminationRisk(str, Enum):
    """Contamination risk level."""
    UNKNOWN = "unknown"
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# ==================== TASK METADATA ====================

@dataclass
class TaskMetadata:
    """
    Har task uchun to'liq metadata.
    
    Bu benchmarkning fundamental entity'si.
    """
    # Identity
    task_id: str
    suite: str
    version: str = "1.0.0"
    
    # Ownership
    owner: str = ""
    owner_email: str = ""
    
    # Lifecycle
    state: str = TaskState.DRAFT.value
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    last_validated_at: Optional[str] = None
    
    # Quality
    flake_status: str = FlakeStatus.UNKNOWN.value
    contamination_risk: str = ContaminationRisk.UNKNOWN.value
    
    # Content
    difficulty: str = "medium"
    capabilities: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    
    # Provenance
    rationale: str = ""  # Nima uchun yaratilgan
    failure_mode: str = ""  # Qaysi failure mode'ni ushlaydi
    source_task_id: Optional[str] = None  # Agar fork qilingan bo'lsa
    
    # Deprecation
    deprecation_reason: Optional[str] = None
    deprecated_at: Optional[str] = None
    
    # Validation
    schema_valid: bool = False
    fixture_valid: bool = False
    verifier_valid: bool = False
    
    # Metrics
    pass_rate: float = 0.0
    avg_time_seconds: float = 0.0
    avg_cost_usd: float = 0.0
    
    # Additional
    hidden_test_count: int = 0
    allowed_edit_scope: List[str] = field(default_factory=list)
    forbidden_paths: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TaskMetadata':
        """Create from dictionary."""
        return cls(**data)


# ==================== TASK REGISTRY ====================

class TaskRegistry:
    """
    Markaziy task registry.
    
    Barcha benchmark tasklarining markaziy manbai.
    
    Definition of Done:
    1. Har task registry'da metadata bilan turadi.
    """
    
    def __init__(self, storage_path: str = None):
        self.storage_path = storage_path
        self.tasks: Dict[str, TaskMetadata] = {}
        self._load()
    
    # ==================== CRUD OPERATIONS ====================
    
    def register_task(self, metadata: TaskMetadata) -> None:
        """Yangi task ro'yxatga olish."""
        metadata.updated_at = datetime.utcnow().isoformat()
        self.tasks[metadata.task_id] = metadata
        self._save()
    
    def update_task(self, task_id: str, updates: Dict[str, Any]) -> bool:
        """Taskni yangilash."""
        if task_id not in self.tasks:
            return False
        
        task = self.tasks[task_id]
        for key, value in updates.items():
            if hasattr(task, key):
                setattr(task, key, value)
        
        task.updated_at = datetime.utcnow().isoformat()
        self._save()
        return True
    
    def get_task(self, task_id: str) -> Optional[TaskMetadata]:
        """Taskni olish."""
        return self.tasks.get(task_id)
    
    def delete_task(self, task_id: str) -> bool:
        """Taskni o'chirish (faqat draft/rejected)."""
        if task_id not in self.tasks:
            return False
        
        task = self.tasks[task_id]
        if task.state not in [TaskState.DRAFT.value, TaskState.REJECTED.value]:
            return False
        
        del self.tasks[task_id]
        self._save()
        return True
    
    # ==================== QUERY OPERATIONS ====================
    
    def get_by_state(self, state: str) -> List[TaskMetadata]:
        """State bo'yicha tasklarni olish."""
        return [t for t in self.tasks.values() if t.state == state]
    
    def get_by_suite(self, suite: str) -> List[TaskMetadata]:
        """Suite bo'yicha tasklarni olish."""
        return [t for t in self.tasks.values() if t.suite == suite]
    
    def get_by_owner(self, owner: str) -> List[TaskMetadata]:
        """Owner bo'yicha tasklarni olish."""
        return [t for t in self.tasks.values() if t.owner == owner]
    
    def get_by_difficulty(self, difficulty: str) -> List[TaskMetadata]:
        """Difficulty bo'yicha tasklarni olish."""
        return [t for t in self.tasks.values() if t.difficulty == difficulty]
    
    def get_quarantined(self) -> List[TaskMetadata]:
        """Quarantined tasklarni olish."""
        return self.get_by_state(TaskState.QUARANTINED.value)
    
    def get_deprecated(self) -> List[TaskMetadata]:
        """Deprecated tasklarni olish."""
        return self.get_by_state(TaskState.DEPRECATED.value)
    
    def get_stable(self) -> List[TaskMetadata]:
        """Stable tasklarni olish."""
        return self.get_by_state(TaskState.STABLE.value)
    
    def get_candidates(self) -> List[TaskMetadata]:
        """Candidate tasklarni olish."""
        return self.get_by_state(TaskState.CANDIDATE.value)
    
    def get_ownerless(self) -> List[TaskMetadata]:
        """Owner bo'lmagan tasklarni olish."""
        return [t for t in self.tasks.values() if not t.owner]
    
    def get_flaky(self) -> List[TaskMetadata]:
        """Flaky tasklarni olish."""
        return [
            t for t in self.tasks.values()
            if t.flake_status in [FlakeStatus.FLAKY_OCCASIONAL.value, FlakeStatus.FLAKY_FREQUENT.value]
        ]
    
    def get_contamination_risk(self, risk: str) -> List[TaskMetadata]:
        """Contamination risk bo'yicha tasklarni olish."""
        return [t for t in self.tasks.values() if t.contamination_risk == risk]
    
    # ==================== STATE TRANSITIONS ====================
    
    def transition_state(
        self,
        task_id: str,
        new_state: str,
        reason: str = "",
        user: str = "system",
    ) -> bool:
        """
        Task state'ni o'zgartirish.
        
        Returns True if transition is valid and successful.
        """
        if task_id not in self.tasks:
            return False
        
        task = self.tasks[task_id]
        old_state = task.state
        
        # Validate transition
        if not self._is_valid_transition(old_state, new_state):
            return False
        
        # Apply transition
        task.state = new_state
        task.updated_at = datetime.utcnow().isoformat()
        
        # Handle special states
        if new_state == TaskState.DEPRECATED.value:
            task.deprecated_at = datetime.utcnow().isoformat()
            task.deprecation_reason = reason
        elif new_state == TaskState.STABLE.value:
            task.last_validated_at = datetime.utcnow().isoformat()
        
        # Log transition
        self._log_transition(task_id, old_state, new_state, reason, user)
        
        self._save()
        return True
    
    def _is_valid_transition(self, old_state: str, new_state: str) -> bool:
        """State transition validmi?"""
        valid_transitions = {
            TaskState.DRAFT.value: [TaskState.CANDIDATE.value, TaskState.REJECTED.value],
            TaskState.CANDIDATE.value: [TaskState.VALIDATED.value, TaskState.REJECTED.value],
            TaskState.VALIDATED.value: [TaskState.STABLE.value, TaskState.REJECTED.value],
            TaskState.STABLE.value: [TaskState.QUARANTINED.value, TaskState.DEPRECATED.value],
            TaskState.QUARANTINED.value: [TaskState.STABLE.value, TaskState.DEPRECATED.value],
            TaskState.DEPRECATED.value: [TaskState.ARCHIVED.value, TaskState.STABLE.value],
            TaskState.ARCHIVED.value: [],
            TaskState.REJECTED.value: [TaskState.DRAFT.value],
        }
        
        return new_state in valid_transitions.get(old_state, [])
    
    def _log_transition(
        self,
        task_id: str,
        old_state: str,
        new_state: str,
        reason: str,
        user: str,
    ) -> None:
        """State transitionni loglash."""
        # Simple logging - in production, use proper logging
        print(f"[LIFECYCLE] {task_id}: {old_state} -> {new_state} by {user}: {reason}")
    
    # ==================== BULK OPERATIONS ====================
    
    def get_all_tasks(self) -> List[TaskMetadata]:
        """Barcha tasklarni olish."""
        return list(self.tasks.values())
    
    def get_task_ids(self) -> Set[str]:
        """Barcha task IDlarni olish."""
        return set(self.tasks.keys())
    
    def get_suite_summary(self) -> Dict[str, int]:
        """Suite bo'yicha task soni."""
        summary = {}
        for task in self.tasks.values():
            suite = task.suite
            summary[suite] = summary.get(suite, 0) + 1
        return summary
    
    def get_state_summary(self) -> Dict[str, int]:
        """State bo'yicha task soni."""
        summary = {}
        for task in self.tasks.values():
            state = task.state
            summary[state] = summary.get(state, 0) + 1
        return summary
    
    def get_difficulty_summary(self) -> Dict[str, int]:
        """Difficulty bo'yicha task soni."""
        summary = {}
        for task in self.tasks.values():
            diff = task.difficulty
            summary[diff] = summary.get(diff, 0) + 1
        return summary
    
    # ==================== PERSISTENCE ====================
    
    def _get_storage_path(self) -> str:
        """Storage pathni olish."""
        if self.storage_path:
            return self.storage_path
        return "benchmarks/registry/task_registry.json"
    
    def _save(self) -> None:
        """Registry'ni saqlash."""
        path = self._get_storage_path()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        
        data = {
            task_id: metadata.to_dict()
            for task_id, metadata in self.tasks.items()
        }
        
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _load(self) -> None:
        """Registry'ni yuklash."""
        path = self._get_storage_path()
        
        if not os.path.exists(path):
            return
        
        try:
            with open(path, 'r') as f:
                data = json.load(f)
            
            for task_id, task_data in data.items():
                self.tasks[task_id] = TaskMetadata.from_dict(task_data)
        except Exception as e:
            print(f"Error loading registry: {e}")
    
    # ==================== EXPORT ====================
    
    def export_stable_pack(self) -> List[str]:
        """Stable tasklarni ID list sifatida export qilish."""
        return [t.task_id for t in self.get_stable()]
    
    def export_candidate_pack(self) -> List[str]:
        """Candidate tasklarni ID list sifatida export qilish."""
        return [t.task_id for t in self.get_candidates()]
    
    def to_dict(self) -> Dict[str, Any]:
        """To'liq registryni dict sifatida export qilish."""
        return {
            task_id: metadata.to_dict()
            for task_id, metadata in self.tasks.items()
        }


# ==================== OWNER MANAGEMENT ====================

@dataclass
class Owner:
    """Benchmark owner (person yoki team)."""
    name: str
    email: str
    role: str = "maintainer"  # maintainer, contributor, reviewer
    assigned_tasks: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


class OwnerManager:
    """Ownerlarni boshqarish."""
    
    def __init__(self, storage_path: str = None):
        self.storage_path = storage_path or "benchmarks/registry/owners.json"
        self.owners: Dict[str, Owner] = {}
        self._load()
    
    def register_owner(self, owner: Owner) -> None:
        """Ownerni ro'yxatga olish."""
        self.owners[owner.email] = owner
        self._save()
    
    def assign_task(self, owner_email: str, task_id: str) -> bool:
        """Taskni owner'ga assign qilish."""
        if owner_email not in self.owners:
            return False
        
        owner = self.owners[owner_email]
        if task_id not in owner.assigned_tasks:
            owner.assigned_tasks.append(task_id)
            self._save()
        return True
    
    def get_tasks_by_owner(self, owner_email: str) -> List[str]:
        """Ownerni tasklarini olish."""
        if owner_email not in self.owners:
            return []
        return self.owners[owner_email].assigned_tasks
    
    def _save(self) -> None:
        """Saqlash."""
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
        with open(self.storage_path, 'w') as f:
            json.dump({k: asdict(v) for k, v in self.owners.items()}, f, indent=2)
    
    def _load(self) -> None:
        """Yuklash."""
        if not os.path.exists(self.storage_path):
            return
        with open(self.storage_path, 'r') as f:
            data = json.load(f)
            for email, owner_data in data.items():
                self.owners[email] = Owner(**owner_data)


# ==================== FACTORY ====================

def create_task_metadata(
    task_id: str,
    suite: str,
    owner: str = "",
    difficulty: str = "medium",
    capabilities: List[str] = None,
    rationale: str = "",
    failure_mode: str = "",
) -> TaskMetadata:
    """TaskMetadata yaratish uchun factory."""
    return TaskMetadata(
        task_id=task_id,
        suite=suite,
        owner=owner,
        difficulty=difficulty,
        capabilities=capabilities or [],
        rationale=rationale,
        failure_mode=failure_mode,
    )


def create_task_registry(storage_path: str = None) -> TaskRegistry:
    """TaskRegistry yaratish."""
    return TaskRegistry(storage_path)


def create_owner_manager(storage_path: str = None) -> OwnerManager:
    """OwnerManager yaratish."""
    return OwnerManager(storage_path)
