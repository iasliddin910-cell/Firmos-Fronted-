"""
OmniAgent X - State Migration System
====================================
Versioned state management and migration framework for kernel.

This module provides a comprehensive system for:
- Versioned state envelopes with metadata
- Schema registry for all state types
- Migration registry for version transitions
- Compatibility gate for restore validation
- Snapshot manifests for checkpoint metadata
- Migration reports for audit trails

Key Components:
- VersionedStateEnvelope: Wrapper for versioned state
- StateSchemaRegistry: Registry for all schemas
- MigrationRegistry: Registry for version migrations
- CompatibilityGate: Compatibility validation
- SnapshotManifest: Checkpoint metadata
- MigrationReport: Migration audit trail
"""

import os
import json
import hashlib
import logging
import time
from typing import Dict, List, Any, Optional, Callable, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from collections import defaultdict
import copy

logger = logging.getLogger(__name__)


# ==================== VERSION TYPES ====================

class SchemaType(Enum):
    """Types of state schemas"""
    TASK_MANAGER = "task_manager_state"
    JOURNAL_ENTRY = "journal_entry"
    CHECKPOINT = "checkpoint"
    HANDOFF_PACKET = "handoff_packet"
    APPROVAL_TICKET = "approval_ticket"
    REPLAY_RECORD = "replay_record"
    BUDGET_LEDGER = "budget_ledger_snapshot"
    FULL_STATE = "full_kernel_state"


class CompatibilityLevel(Enum):
    """Compatibility levels for state"""
    FULL = "full"           # Direct compatibility
    MIGRATABLE = "migratable"  # Can be migrated
    READ_ONLY = "read_only"  # Only replay possible
    INCOMPATIBLE = "incompatible"  # Cannot use


@dataclass
class VersionedStateEnvelope:
    """
    Versioned wrapper for all state.
    
    This ensures every state has:
    - schema_name: What type of state
    - schema_version: Which version
    - created_at: When created
    - writer_kernel_version: What kernel wrote it
    - payload: The actual state data
    - checksum: Integrity check
    """
    schema_name: str
    schema_version: int
    created_at: float
    writer_kernel_version: str
    payload: Dict[str, Any]
    checksum: str = ""
    
    # Metadata fields
    source_schema_version: Optional[int] = None  # Original version before migration
    migration_chain: List[int] = field(default_factory=list)  # Versions passed through
    flags: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.checksum:
            self.checksum = self._compute_checksum()
    
    def _compute_checksum(self) -> str:
        """Compute checksum for payload"""
        content = json.dumps(self.payload, sort_keys=True, default=str)
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def verify_integrity(self) -> bool:
        """Verify envelope integrity"""
        expected = self._compute_checksum()
        return self.checksum == expected
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "schema_name": self.schema_name,
            "schema_version": self.schema_version,
            "created_at": self.created_at,
            "writer_kernel_version": self.writer_kernel_version,
            "payload": self.payload,
            "checksum": self.checksum,
            "source_schema_version": self.source_schema_version,
            "migration_chain": self.migration_chain,
            "flags": self.flags
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'VersionedStateEnvelope':
        """Create from dictionary"""
        return cls(
            schema_name=data["schema_name"],
            schema_version=data["schema_version"],
            created_at=data["created_at"],
            writer_kernel_version=data["writer_kernel_version"],
            payload=data["payload"],
            checksum=data.get("checksum", ""),
            source_schema_version=data.get("source_schema_version"),
            migration_chain=data.get("migration_chain", []),
            flags=data.get("flags", {})
        )


# ==================== STATE SCHEMA ====================

@dataclass
class FieldSchema:
    """Schema for a single field"""
    name: str
    field_type: str  # "str", "int", "list", "dict", "object"
    required: bool = False
    default: Any = None
    deprecated: bool = False
    deprecated_message: str = ""
    description: str = ""


@dataclass
class SchemaDefinition:
    """Definition for a state schema"""
    schema_type: SchemaType
    version: int
    fields: List[FieldSchema]
    required_fields: List[str] = field(default_factory=list)
    deprecated_fields: List[str] = field(default_factory=list)
    compatibility_rule: str = "forward"  # "forward", "backward", "both"
    created_at: float = field(default_factory=time.time)
    
    def get_field(self, name: str) -> Optional[FieldSchema]:
        """Get field schema by name"""
        for f in self.fields:
            if f.name == name:
                return f
        return None
    
    def get_required_fields(self) -> Set[str]:
        """Get set of required field names"""
        return {f.name for f in self.fields if f.required}
    
    def get_deprecated_fields(self) -> Set[str]:
        """Get set of deprecated field names"""
        return {f.name for f in self.fields if f.deprecated}


# ==================== STATE SCHEMA REGISTRY ====================

class StateSchemaRegistry:
    """
    Registry for all state schemas.
    
    Tracks:
    - task_manager_state:v1, v2, v3
    - journal_entry:v1, v2
    - checkpoint:v1, v2
    etc.
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        
        # Schema storage: (schema_type, version) -> SchemaDefinition
        self._schemas: Dict[Tuple[str, int], SchemaDefinition] = {}
        
        # Initialize default schemas
        self._register_default_schemas()
        
        logger.info("StateSchemaRegistry initialized")
    
    def _register_default_schemas(self):
        """Register default schemas for kernel state"""
        
        # Full kernel state v1
        self.register(SchemaDefinition(
            schema_type=SchemaType.FULL_STATE,
            version=1,
            fields=[
                FieldSchema("state_version", "int", required=True),
                FieldSchema("tasks", "list", required=True),
                FieldSchema("pending_tasks", "list"),
                FieldSchema("completed_tasks", "list"),
                FieldSchema("failed_tasks", "list"),
                FieldSchema("background_queue_tasks", "list"),
                FieldSchema("approval_waiting_tasks", "list"),  # Originally dict in some versions
                FieldSchema("state", "str"),
                FieldSchema("kernel_version", "str"),
            ],
            required_fields=["state_version", "tasks"],
            deprecated_fields=["background_queue_tasks"],
            compatibility_rule="forward"
        ))
        
        # Full kernel state v2 (current)
        self.register(SchemaDefinition(
            schema_type=SchemaType.FULL_STATE,
            version=2,
            fields=[
                FieldSchema("state_version", "int", required=True),
                FieldSchema("tasks", "list", required=True),
                FieldSchema("pending_tasks", "list"),
                FieldSchema("completed_tasks", "list"),
                FieldSchema("failed_tasks", "list"),
                FieldSchema("background_tasks", "list"),  # Renamed from background_queue_tasks
                FieldSchema("approval_waiting_tasks", "list"),  # Fixed to list
                FieldSchema("rollback_points", "dict"),  # New field
                FieldSchema("state", "str"),
                FieldSchema("kernel_version", "str"),
                FieldSchema("last_task_id", "int"),
            ],
            required_fields=["state_version", "tasks"],
            compatibility_rule="both"
        ))
        
        # Task state schema
        self.register(SchemaDefinition(
            schema_type=SchemaType.TASK_MANAGER,
            version=1,
            fields=[
                FieldSchema("task_id", "str", required=True),
                FieldSchema("description", "str", required=True),
                FieldSchema("status", "str", required=True),
                FieldSchema("created_at", "float", required=True),
                FieldSchema("updated_at", "float"),
                FieldSchema("result", "object"),
                FieldSchema("error", "str"),
                FieldSchema("retry_count", "int", default=0),
                FieldSchema("rollback_point", "object"),  # Added in v2
            ],
            required_fields=["task_id", "description", "status", "created_at"],
            compatibility_rule="both"
        ))
        
        # Journal entry schema
        self.register(SchemaDefinition(
            schema_type=SchemaType.JOURNAL_ENTRY,
            version=1,
            fields=[
                FieldSchema("task_id", "str", required=True),
                FieldSchema("event_type", "str", required=True),
                FieldSchema("timestamp", "float", required=True),
                FieldSchema("data", "object"),
                FieldSchema("version", "int", default=1),
            ],
            required_fields=["task_id", "event_type", "timestamp"],
            compatibility_rule="both"
        ))
    
    def register(self, schema: SchemaDefinition):
        """Register a schema"""
        key = (schema.schema_type.value, schema.version)
        self._schemas[key] = schema
        logger.debug(f"Registered schema: {schema.schema_type.value}:v{schema.version}")
    
    def get_schema(self, schema_type: SchemaType, version: int) -> Optional[SchemaDefinition]:
        """Get schema by type and version"""
        key = (schema_type.value, version)
        return self._schemas.get(key)
    
    def get_latest_version(self, schema_type: SchemaType) -> Optional[int]:
        """Get latest version for a schema type"""
        versions = [v for (t, v), _ in self._schemas.items() if t == schema_type.value]
        return max(versions) if versions else None
    
    def get_all_versions(self, schema_type: SchemaType) -> List[int]:
        """Get all versions for a schema type"""
        return sorted([v for (t, v), _ in self._schemas.items() if t == schema_type.value])
    
    def validate(self, schema_type: SchemaType, version: int, data: Dict) -> Tuple[bool, List[str]]:
        """
        Validate data against schema.
        
        Returns (is_valid, error_messages)
        """
        schema = self.get_schema(schema_type, version)
        if not schema:
            return False, [f"Schema {schema_type.value}:v{version} not found"]
        
        errors = []
        
        # Check required fields
        for field_name in schema.get_required_fields():
            if field_name not in data:
                errors.append(f"Required field missing: {field_name}")
        
        # Check deprecated fields (warn only)
        for field_name in schema.get_deprecated_fields():
            if field_name in data:
                field_schema = schema.get_field(field_name)
                if field_schema:
                    logger.warning(f"Deprecated field used: {field_name} - {field_schema.deprecated_message}")
        
        return len(errors) == 0, errors


# ==================== MIGRATION ====================

@dataclass
class MigrationStep:
    """A single migration step"""
    from_version: int
    to_version: int
    migrate_fn: Callable[[Dict], Dict]
    description: str
    reversible: bool = True
    rollback_fn: Optional[Callable[[Dict], Dict]] = None


class MigrationRegistry:
    """
    Registry for state migrations.
    
    Manages migrations like:
    - v1 -> v2
    - v2 -> v3
    etc.
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        
        # Migration storage: (schema_type, from_version) -> List[MigrationStep]
        self._migrations: Dict[Tuple[str, int], List[MigrationStep]] = defaultdict(list)
        
        # Register default migrations
        self._register_default_migrations()
        
        logger.info("MigrationRegistry initialized")
    
    def _register_default_migrations(self):
        """Register default migrations for kernel state"""
        
        # Migration from v1 to v2 for FULL_STATE
        self.register_migration(
            schema_type=SchemaType.FULL_STATE,
            from_version=1,
            to_version=2,
            description="Migrate v1 state to v2",
            migrate_fn=self._migrate_v1_to_v2,
            reversible=True,
            rollback_fn=self._migrate_v2_to_v1
        )
    
    def _migrate_v1_to_v2(self, data: Dict) -> Dict:
        """Migrate state from v1 to v2"""
        result = copy.deepcopy(data)
        
        # Fix 1: approval_waiting_tasks - dict to list normalization
        if "approval_waiting_tasks" in result:
            awt = result["approval_waiting_tasks"]
            if isinstance(awt, dict):
                # Convert dict to list
                result["approval_waiting_tasks"] = [
                    {"task_id": k, "data": v} for k, v in awt.items()
                ]
                logger.info("Migrated approval_waiting_tasks from dict to list")
        
        # Fix 2: background_queue_tasks -> background_tasks
        if "background_queue_tasks" in result:
            result["background_tasks"] = result.pop("background_queue_tasks")
            logger.info("Migrated background_queue_tasks to background_tasks")
        
        # Fix 3: Add rollback_points field if tasks exist
        if "tasks" in result and isinstance(result["tasks"], list):
            result["rollback_points"] = {}
            logger.info("Added rollback_points field")
        
        # Fix 4: Add last_task_id
        if "tasks" in result and isinstance(result["tasks"], list):
            if result["tasks"]:
                # Get max task_id
                max_id = 0
                for task in result["tasks"]:
                    if isinstance(task, dict) and "task_id" in task:
                        try:
                            task_num = int(task["task_id"].replace("task_", ""))
                            max_id = max(max_id, task_num)
                        except (ValueError, AttributeError):
                            pass
                result["last_task_id"] = max_id
        
        return result
    
    def _migrate_v2_to_v1(self, data: Dict) -> Dict:
        """Migrate state from v2 to v1 (rollback)"""
        result = copy.deepcopy(data)
        
        # Reverse: background_tasks -> background_queue_tasks
        if "background_tasks" in result:
            result["background_queue_tasks"] = result.pop("background_tasks")
        
        # Remove v2-only fields
        result.pop("rollback_points", None)
        result.pop("last_task_id", None)
        
        return result
    
    def register_migration(
        self,
        schema_type: SchemaType,
        from_version: int,
        to_version: int,
        description: str,
        migrate_fn: Callable[[Dict], Dict],
        reversible: bool = True,
        rollback_fn: Optional[Callable[[Dict], Dict]] = None
    ):
        """Register a migration step"""
        step = MigrationStep(
            from_version=from_version,
            to_version=to_version,
            migrate_fn=migrate_fn,
            description=description,
            reversible=reversible,
            rollback_fn=rollback_fn
        )
        
        key = (schema_type.value, from_version)
        self._migrations[key].append(step)
        
        # Sort by version
        self._migrations[key].sort(key=lambda x: x.to_version)
        
        logger.debug(f"Registered migration: {schema_type.value}:v{from_version} -> v{to_version}")
    
    def get_migration_path(
        self,
        schema_type: SchemaType,
        from_version: int,
        to_version: int
    ) -> Optional[List[MigrationStep]]:
        """Get migration path from one version to another"""
        if from_version == to_version:
            return []
        
        path = []
        current_version = from_version
        
        while current_version < to_version:
            key = (schema_type.value, current_version)
            migrations = self._migrations.get(key, [])
            
            if not migrations:
                return None  # No path available
            
            # Find next migration
            found = False
            for migration in migrations:
                if migration.to_version > current_version:
                    path.append(migration)
                    current_version = migration.to_version
                    found = True
                    break
            
            if not found:
                return None
        
        return path
    
    def migrate(
        self,
        schema_type: SchemaType,
        from_version: int,
        to_version: int,
        data: Dict
    ) -> Tuple[Optional[Dict], Optional[str]]:
        """
        Migrate data from one version to another.
        
        Returns (migrated_data, error_message)
        """
        path = self.get_migration_path(schema_type, from_version, to_version)
        
        if path is None:
            return None, f"No migration path from v{from_version} to v{to_version}"
        
        result = data
        migration_chain = []
        
        for step in path:
            try:
                result = step.migrate_fn(result)
                migration_chain.append(step.to_version)
                logger.info(f"Migrated {schema_type.value}: v{step.from_version} -> v{step.to_version}")
            except Exception as e:
                return None, f"Migration failed at v{step.from_version} -> v{step.to_version}: {str(e)}"
        
        return result, None


# ==================== COMPATIBILITY GATE ====================

class CompatibilityGate:
    """
    Gate for validating state compatibility before restore.
    
    Determines:
    - Is state directly compatible?
    - Can it be migrated?
    - Is only read-only replay possible?
    - Should it be rejected?
    """
    
    def __init__(self):
        self.schema_registry = StateSchemaRegistry()
        self.migration_registry = MigrationRegistry()
        
        logger.info("CompatibilityGate initialized")
    
    def check_compatibility(
        self,
        schema_type: SchemaType,
        state_version: int,
        target_version: Optional[int] = None
    ) -> Tuple[CompatibilityLevel, List[str]]:
        """
        Check compatibility level for state.
        
        Returns (compatibility_level, messages)
        """
        messages = []
        
        # Get target version (default to latest)
        if target_version is None:
            target_version = self.schema_registry.get_latest_version(schema_type)
        
        if target_version is None:
            return CompatibilityLevel.INCOMPATIBLE, ["No schema registered for this type"]
        
        # Check if schema exists
        current_schema = self.schema_registry.get_schema(schema_type, state_version)
        if not current_schema:
            # Try to find migration path
            path = self.migration_registry.get_migration_path(schema_type, state_version, target_version)
            if path:
                messages.append(f"State v{state_version} can be migrated to v{target_version}")
                return CompatibilityLevel.MIGRATABLE, messages
            else:
                messages.append(f"No schema or migration found for v{state_version}")
                return CompatibilityLevel.INCOMPATIBLE, messages
        
        # Check compatibility
        if state_version == target_version:
            messages.append(f"State is at target version v{target_version}")
            return CompatibilityLevel.FULL, messages
        elif state_version < target_version:
            # Check if migration possible
            path = self.migration_registry.get_migration_path(schema_type, state_version, target_version)
            if path:
                messages.append(f"State can be migrated from v{state_version} to v{target_version}")
                return CompatibilityLevel.MIGRATABLE, messages
            else:
                messages.append(f"No migration path available")
                return CompatibilityLevel.READ_ONLY, messages
        else:
            # State is newer than target
            messages.append(f"State is newer than target (v{state_version} > v{target_version})")
            return CompatibilityLevel.READ_ONLY, messages
    
    def validate_and_migrate(
        self,
        schema_type: SchemaType,
        data: Dict,
        target_version: Optional[int] = None
    ) -> Tuple[Optional[Dict], CompatibilityLevel, List[str]]:
        """
        Validate state and migrate if needed.
        
        Returns (processed_data, compatibility_level, messages)
        """
        # Extract version from data
        state_version = data.get("state_version", 1)
        
        # Check compatibility
        compatibility, messages = self.check_compatibility(schema_type, state_version, target_version)
        
        if compatibility == CompatibilityLevel.INCOMPATIBLE:
            return None, compatibility, messages
        
        if compatibility == CompatibilityLevel.FULL:
            # Validate against schema
            is_valid, errors = self.schema_registry.validate(schema_type, state_version, data)
            if not is_valid:
                messages.extend(errors)
                return None, CompatibilityLevel.INCOMPATIBLE, messages
            return data, compatibility, messages
        
        if compatibility == CompatibilityLevel.MIGRATABLE:
            # Get target version
            if target_version is None:
                target_version = self.schema_registry.get_latest_version(schema_type)
            
            # Migrate
            migrated_data, error = self.migration_registry.migrate(
                schema_type, state_version, target_version, data
            )
            
            if error:
                messages.append(f"Migration failed: {error}")
                return None, CompatibilityLevel.INCOMPATIBLE, messages
            
            messages.append(f"Successfully migrated to v{target_version}")
            return migrated_data, CompatibilityLevel.FULL, messages
        
        # READ_ONLY - return data as-is but mark as read-only
        return data, compatibility, messages


# ==================== SNAPSHOT MANIFEST ====================

@dataclass
class SnapshotManifest:
    """
    Metadata for a snapshot/checkpoint.
    
    Contains:
    - Which queue models were used
    - Which task status enum version
    - Which subsystems were active
    - Which optional sections exist
    - Which migrations have been applied
    """
    snapshot_id: str
    created_at: float
    kernel_version: str
    
    # Schema versions
    task_manager_version: int
    journal_version: int
    checkpoint_version: int
    
    # State info
    task_count: int
    pending_task_count: int
    completed_task_count: int
    failed_task_count: int
    
    # Subsystems
    active_subsystems: List[str] = field(default_factory=list)
    optional_sections: List[str] = field(default_factory=list)
    
    # Migration info
    migrations_applied: List[str] = field(default_factory=list)
    
    # Checksum
    state_checksum: str = ""
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "snapshot_id": self.snapshot_id,
            "created_at": self.created_at,
            "kernel_version": self.kernel_version,
            "task_manager_version": self.task_manager_version,
            "journal_version": self.journal_version,
            "checkpoint_version": self.checkpoint_version,
            "task_count": self.task_count,
            "pending_task_count": self.pending_task_count,
            "completed_task_count": self.completed_task_count,
            "failed_task_count": self.failed_task_count,
            "active_subsystems": self.active_subsystems,
            "optional_sections": self.optional_sections,
            "migrations_applied": self.migrations_applied,
            "state_checksum": self.state_checksum
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'SnapshotManifest':
        """Create from dictionary"""
        return cls(
            snapshot_id=data["snapshot_id"],
            created_at=data["created_at"],
            kernel_version=data["kernel_version"],
            task_manager_version=data["task_manager_version"],
            journal_version=data["journal_version"],
            checkpoint_version=data["checkpoint_version"],
            task_count=data["task_count"],
            pending_task_count=data["pending_task_count"],
            completed_task_count=data["completed_task_count"],
            failed_task_count=data["failed_task_count"],
            active_subsystems=data.get("active_subsystems", []),
            optional_sections=data.get("optional_sections", []),
            migrations_applied=data.get("migrations_applied", []),
            state_checksum=data.get("state_checksum", "")
        )
    
    @classmethod
    def create(
        cls,
        kernel_version: str,
        task_manager_version: int,
        state_data: Dict,
        active_subsystems: Optional[List[str]] = None
    ) -> 'SnapshotManifest':
        """Create a new manifest from current state"""
        import uuid
        
        # Count tasks
        tasks = state_data.get("tasks", [])
        pending = state_data.get("pending_tasks", [])
        completed = state_data.get("completed_tasks", [])
        failed = state_data.get("failed_tasks", [])
        
        # Compute checksum
        content = json.dumps(state_data, sort_keys=True, default=str)
        checksum = hashlib.sha256(content.encode()).hexdigest()[:16]
        
        return cls(
            snapshot_id=str(uuid.uuid4()),
            created_at=time.time(),
            kernel_version=kernel_version,
            task_manager_version=task_manager_version,
            journal_version=1,
            checkpoint_version=1,
            task_count=len(tasks) + len(pending) + len(completed) + len(failed),
            pending_task_count=len(pending),
            completed_task_count=len(completed),
            failed_task_count=len(failed),
            active_subsystems=active_subsystems or [],
            migrations_applied=[f"v{task_manager_version}"],
            state_checksum=checksum
        )


# ==================== MIGRATION REPORT ====================

@dataclass
class FieldChange:
    """Record of a single field change"""
    field_name: str
    change_type: str  # "added", "removed", "renamed", "type_changed", "normalized"
    old_value: Any = None
    new_value: Any = None
    description: str = ""


@dataclass
class MigrationReport:
    """
    Report of a migration operation.
    
    Contains:
    - Which fields were renamed
    - Which deprecated fields were removed
    - Which defaults were injected
    - Which state could not be recovered
    - Which sections were quarantined
    """
    migration_id: str
    schema_type: str
    from_version: int
    to_version: int
    started_at: float
    completed_at: float
    
    # Changes
    fields_added: List[str] = field(default_factory=list)
    fields_removed: List[str] = field(default_factory=list)
    fields_renamed: List[FieldChange] = field(default_factory=list)
    fields_normalized: List[FieldChange] = field(default_factory=list)
    defaults_injected: List[str] = field(default_factory=list)
    
    # Issues
    unrecovered_fields: List[str] = field(default_factory=list)
    quarantined_sections: List[str] = field(default_factory=list)
    
    # Outcome
    success: bool = True
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "migration_id": self.migration_id,
            "schema_type": self.schema_type,
            "from_version": self.from_version,
            "to_version": self.to_version,
            "duration_sec": self.completed_at - self.started_at,
            "success": self.success,
            "error_message": self.error_message,
            "fields_added": self.fields_added,
            "fields_removed": self.fields_removed,
            "fields_renamed": [
                {"field": f.field_name, "description": f.description}
                for f in self.fields_renamed
            ],
            "fields_normalized": [
                {"field": f.field_name, "change_type": f.change_type, "description": f.description}
                for f in self.fields_normalized
            ],
            "defaults_injected": self.defaults_injected,
            "unrecovered_fields": self.unrecovered_fields,
            "quarantined_sections": self.quarantined_sections
        }
    
    def add_field_normalized(self, field_name: str, change_type: str, old_value: Any, new_value: Any, description: str):
        """Add a field normalization record"""
        self.fields_normalized.append(FieldChange(
            field_name=field_name,
            change_type=change_type,
            old_value=old_value,
            new_value=new_value,
            description=description
        ))
    
    def add_field_renamed(self, old_name: str, new_name: str):
        """Add a field rename record"""
        self.fields_renamed.append(FieldChange(
            field_name=f"{old_name} -> {new_name}",
            change_type="renamed",
            old_value=old_name,
            new_value=new_name,
            description=f"Field renamed from {old_name} to {new_name}"
        ))
    
    @property
    def duration_sec(self) -> float:
        """Get migration duration in seconds"""
        return self.completed_at - self.started_at


# ==================== STATE MANAGER ====================

class StateManager:
    """
    Main state management class that ties everything together.
    
    Provides:
    - State saving with versioning
    - State loading with migration
    - Compatibility checking
    - Manifest generation
    """
    
    KERNEL_VERSION = "2.0.0"  # Update this with each kernel release
    
    def __init__(self):
        self.schema_registry = StateSchemaRegistry()
        self.migration_registry = MigrationRegistry()
        self.compatibility_gate = CompatibilityGate()
        
        logger.info("StateManager initialized")
    
    def wrap_state(self, schema_type: SchemaType, payload: Dict, source_version: Optional[int] = None) -> VersionedStateEnvelope:
        """
        Wrap state in a versioned envelope.
        """
        version = source_version
        if version is None:
            version = self.schema_registry.get_latest_version(schema_type)
        if version is None:
            version = 1
        
        envelope = VersionedStateEnvelope(
            schema_name=schema_type.value,
            schema_version=version,
            created_at=time.time(),
            writer_kernel_version=self.KERNEL_VERSION,
            payload=payload
        )
        
        return envelope
    
    def unwrap_and_migrate(
        self,
        envelope: VersionedStateEnvelope,
        target_version: Optional[int] = None
    ) -> Tuple[Optional[Dict], MigrationReport]:
        """
        Unwrap envelope and migrate to target version.
        
        Returns (migrated_data, migration_report)
        """
        import uuid
        
        # Create report
        report = MigrationReport(
            migration_id=str(uuid.uuid4()),
            schema_type=envelope.schema_name,
            from_version=envelope.schema_version,
            to_version=target_version or envelope.schema_version,
            started_at=time.time(),
            completed_at=time.time()
        )
        
        try:
            schema_type = SchemaType(envelope.schema_name)
            
            # Check compatibility
            compatibility, messages = self.compatibility_gate.check_compatibility(
                schema_type,
                envelope.schema_version,
                target_version
            )
            
            if compatibility == CompatibilityLevel.INCOMPATIBLE:
                report.success = False
                report.error_message = "; ".join(messages)
                report.completed_at = time.time()
                return None, report
            
            if compatibility == CompatibilityLevel.MIGRATABLE:
                # Get target version
                if target_version is None:
                    target_version = self.schema_registry.get_latest_version(schema_type)
                
                # Migrate
                migrated_data, error = self.migration_registry.migrate(
                    schema_type,
                    envelope.schema_version,
                    target_version,
                    envelope.payload
                )
                
                if error:
                    report.success = False
                    report.error_message = error
                    report.completed_at = time.time()
                    return None, report
                
                # Record changes
                if "approval_waiting_tasks" in envelope.payload:
                    old_val = envelope.payload["approval_waiting_tasks"]
                    new_val = migrated_data.get("approval_waiting_tasks")
                    if type(old_val) != type(new_val):
                        report.add_field_normalized(
                            "approval_waiting_tasks",
                            "type_changed",
                            type(old_val).__name__,
                            type(new_val).__name__,
                            "Normalized from dict to list"
                        )
                
                if "background_queue_tasks" in envelope.payload:
                    report.add_field_renamed("background_queue_tasks", "background_tasks")
                
                report.completed_at = time.time()
                return migrated_data, report
            
            # FULL or READ_ONLY - return as-is
            report.completed_at = time.time()
            return envelope.payload, report
            
        except Exception as e:
            report.success = False
            report.error_message = str(e)
            report.completed_at = time.time()
            return None, report
    
    def create_snapshot_manifest(
        self,
        state_data: Dict,
        active_subsystems: Optional[List[str]] = None
    ) -> SnapshotManifest:
        """Create a snapshot manifest"""
        return SnapshotManifest.create(
            kernel_version=self.KERNEL_VERSION,
            task_manager_version=state_data.get("state_version", 2),
            state_data=state_data,
            active_subsystems=active_subsystems
        )


# ==================== FACTORY ====================

def create_state_manager() -> StateManager:
    """Create a StateManager instance"""
    return StateManager()


def get_schema_registry() -> StateSchemaRegistry:
    """Get the global schema registry"""
    return StateSchemaRegistry()


def get_migration_registry() -> MigrationRegistry:
    """Get the global migration registry"""
    return MigrationRegistry()


def get_compatibility_gate() -> CompatibilityGate:
    """Get a compatibility gate instance"""
    return CompatibilityGate()
