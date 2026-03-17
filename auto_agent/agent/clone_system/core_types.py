"""
================================================================================
OMNIAGENT X - SELF-CLONE IMPROVEMENT SYSTEM
================================================================================
World-Class Self-Improvement Architecture

Bu tizim quyidagi 8 ta asosiy qavatni o'z ichiga oladi:
1. Clone Factory - Clone yaratish tizimi
2. Source Clone Layer - Kod nusxasi bilan ishlash
3. Runtime Isolation - Runtime izolyatsiya
4. Clone Knowledge Layer - Clone bilim bazasi
5. Improvement Planner - Yaxshilash rejalashtiruvchi
6. Patch/Build/Extend Layer - O'zgartirish qilish
7. Local Validation - Mahalliy tekshiruv
8. Clone Artifact Store - Natijalar arxivi

PRINCIPLE: Core is sacred, clones are experimental
================================================================================
"""
import os
import sys
import json
import logging
import time
import shutil
import hashlib
import traceback
import subprocess
import tempfile
import threading
import uuid
from typing import Dict, List, Optional, Any, Callable, Set, Union
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from collections import defaultdict
from pathlib import Path
from enum import Enum
import asyncio

logger = logging.getLogger(__name__)

# ================================================================================
# ENUMS - Clone turlari va holatlari
# ================================================================================

class CloneType(Enum):
    """
    Clone turlari - har biri o'z xususiyatlariga ega
    """
    MICRO_PATCH = "micro_patch"          # Kichik va lokal o'zgarishlar (bug fix, prompt tweak)
    CAPABILITY = "capability"            # Yangi ability qo'shadi (DOM memory, repo graph)
    WORKFLOW = "workflow"                # Ishlash usulini o'zgartiradi
    RESEARCH = "research"                # Natija aniq emas, tajriba uchun
    FORK = "fork"                        # Yangi branch/model yaratish


class CloneStatus(Enum):
    """
    Clone holatlari - to'liq lifecycle
    """
    CREATING = "creating"                # Clone yaratilmoqda
    INITIALIZING = "initializing"        # Ishga tushirilmoqda
    ANALYZING = "analyzing"              # Tahlil qilinmoqda
    PLANNING = "planning"                # Rejalashtirilmoqda
    PATCHING = "patching"                # O'zgartirish kiritilmoqda
    VALIDATING = "validating"            # Tekshirilmoqda
    EVALUATING = "evaluating"            # Baholanmoqda
    REPORTING = "reporting"              # Natijalar tayyorlanmoqda
    APPROVED = "approved"                # Tasdiqlangan
    REJECTED = "rejected"                # Rad etilgan
    PROMOTED = "promoted"                # Productionga chiqarilgan
    ROLLED_BACK = "rolled_back"          # Qaytarilgan
    FAILED = "failed"                    # Muvaffaqiyatsiz
    CLEANUP = "cleanup"                  # Tozalanmoqda


class RiskClass(Enum):
    """
    Risk klasslari - o'zgartirish xavfini aniqlash
    """
    LOW = "low"          # Minimal xavf (max 3 fayl)
    MEDIUM = "medium"   # O'rtacha xavf (max 8 fayl)
    HIGH = "high"       # Yuqori xavf (max 20 fayl)
    CRITICAL = "critical"  # Kritik xavf (faqat maxsus ruxsat bilan)


class ChangeType(Enum):
    """
    O'zgartirish turlari
    """
    SMALL_PATCH = "small_patch"
    MULTI_FILE_PATCH = "multi_file_patch"
    NEW_TOOL = "new_tool"
    WORKFLOW_REDESIGN = "workflow_redesign"
    PROMPT_TUNING = "prompt_tuning"
    BENCHMARK_ADDITION = "benchmark_addition"
    ARCHITECTURE_EXTENSION = "architecture_extension"


class ValidationResult(Enum):
    """
    Validatsiya natijalari
    """
    PASS = "pass"
    FAIL = "fail"
    WARNING = "warning"
    SKIP = "skip"


# ================================================================================
# DATA CLASSES - Asosiy ma'lumot turlari
# ================================================================================

@dataclass
class CloneMetadata:
    """
    Clone metama'lumotlari - har bir clone uchun majburiy metadata
    Bu keyin lineage va audit uchun kerak bo'ladi
    """
    clone_id: str
    parent_version: str
    candidate_id: str
    created_from_commit: str
    reason: str
    risk_level: RiskClass
    ttl: int = 3600  # sekundlarda, default 1 soat
    scope_permissions: Dict[str, bool] = field(default_factory=dict)
    clone_type: CloneType = CloneType.MICRO_PATCH
    
    # Vaqt
    created_at: float = field(default_factory=time.time)
    expires_at: float = field(default_factory=lambda: time.time() + 3600)
    
    # Lineage
    parent_clone_id: Optional[str] = None
    lineage: List[str] = field(default_factory=list)
    
    # Holat
    status: CloneStatus = CloneStatus.CREATING
    
    def to_dict(self) -> Dict:
        return {
            "clone_id": self.clone_id,
            "parent_version": self.parent_version,
            "candidate_id": self.candidate_id,
            "created_from_commit": self.created_from_commit,
            "reason": self.reason,
            "risk_level": self.risk_level.value,
            "ttl": self.ttl,
            "scope_permissions": self.scope_permissions,
            "clone_type": self.clone_type.value,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "parent_clone_id": self.parent_clone_id,
            "lineage": self.lineage,
            "status": self.status.value
        }


@dataclass
class ChangeBudget:
    """
    Change Budget - clone bir urinishda qiladigan o'zgartirishlarni limitlash
    Bu xavfsizlik va nazorat uchun muhim
    """
    max_files: int = 3
    max_capabilities: int = 1
    max_dependencies: int = 2
    max_tools: int = 3
    max_new_benchmarks: int = 2
    
    # Joriy foydalanish
    files_used: int = 0
    capabilities_used: int = 0
    dependencies_used: int = 0
    tools_used: int = 0
    benchmarks_added: int = 0
    
    def can_change_file(self) -> bool:
        return self.files_used < self.max_files
    
    def can_add_capability(self) -> bool:
        return self.capabilities_used < self.max_capabilities
    
    def can_add_dependency(self) -> bool:
        return self.dependencies_used < self.max_dependencies
    
    def can_add_tool(self) -> bool:
        return self.tools_used < self.max_tools
    
    def can_add_benchmark(self) -> bool:
        return self.benchmarks_added < self.max_new_benchmarks
    
    def record_file_change(self):
        if self.can_change_file():
            self.files_used += 1
            return True
        return False
    
    def record_capability_change(self):
        if self.can_add_capability():
            self.capabilities_used += 1
            return True
        return False
    
    def record_dependency(self):
        if self.can_add_dependency():
            self.dependencies_used += 1
            return True
        return False
    
    def record_tool(self):
        if self.can_add_tool():
            self.tools_used += 1
            return True
        return False
    
    def record_benchmark(self):
        if self.can_add_benchmark():
            self.benchmarks_added += 1
            return True
        return False
    
    def is_within_budget(self) -> bool:
        return all([
            self.can_change_file(),
            self.can_add_capability(),
            self.can_add_dependency(),
            self.can_add_tool(),
            self.can_add_benchmark()
        ])
    
    def to_dict(self) -> Dict:
        return {
            "budget": {
                "max_files": self.max_files,
                "max_capabilities": self.max_capabilities,
                "max_dependencies": self.max_dependencies,
                "max_tools": self.max_tools,
                "max_new_benchmarks": self.max_new_benchmarks
            },
            "used": {
                "files": self.files_used,
                "capabilities": self.capabilities_used,
                "dependencies": self.dependencies_used,
                "tools": self.tools_used,
                "benchmarks": self.benchmarks_added
            },
            "within_budget": self.is_within_budget()
        }


@dataclass
class ImprovementPlan:
    """
    Improvement Plan - clone nima qilishini rejalaydi
    """
    plan_id: str
    clone_id: str
    
    # Maqsad
    goal: str
    change_type: ChangeType
    
    # Tegishli modullar
    files_to_modify: List[str] = field(default_factory=list)
    files_to_create: List[str] = field(default_factory=list)
    files_to_delete: List[str] = field(default_factory=list)
    
    # Risk
    risk: RiskClass = RiskClass.LOW
    blast_radius: str = "local"
    rollback_complexity: str = "easy"
    
    # Strategiya
    test_strategy: str = ""
    benchmark_strategy: str = ""
    expected_gain: str = ""
    
    # Budget
    change_budget: Optional[ChangeBudget] = None
    
    # Holat
    status: str = "draft"
    created_at: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict:
        return {
            "plan_id": self.plan_id,
            "clone_id": self.clone_id,
            "goal": self.goal,
            "change_type": self.change_type.value,
            "files_to_modify": self.files_to_modify,
            "files_to_create": self.files_to_create,
            "files_to_delete": self.files_to_delete,
            "risk": self.risk.value,
            "blast_radius": self.blast_radius,
            "rollback_complexity": self.rollback_complexity,
            "test_strategy": self.test_strategy,
            "benchmark_strategy": self.benchmark_strategy,
            "expected_gain": self.expected_gain,
            "change_budget": self.change_budget.to_dict() if self.change_budget else None,
            "status": self.status,
            "created_at": self.created_at
        }


@dataclass
class PatchSet:
    """
    Patch Set - bir set ichidagi o'zgartirishlar
    Har change set uchun majburiy: intent, why, expected effect, files touched, risk, revert path
    """
    patch_id: str
    clone_id: str
    plan_id: str
    
    # Majburiy maydonlar
    intent: str  # Nima qilmoqchi
    why: str    # Nega
    expected_effect: str  # Kutgan natija
    
    # Fayllar
    files_touched: List[str] = field(default_factory=list)
    files_created: List[str] = field(default_factory=list)
    
    # O'zgartirishlar
    diffs: Dict[str, str] = field(default_factory=dict)  # file -> diff
    
    # Risk va revert
    risk: RiskClass = RiskClass.LOW
    revert_path: str = ""
    
    # Holat
    status: str = "pending"
    created_at: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict:
        return {
            "patch_id": self.patch_id,
            "clone_id": self.clone_id,
            "plan_id": self.plan_id,
            "intent": self.intent,
            "why": self.why,
            "expected_effect": self.expected_effect,
            "files_touched": self.files_touched,
            "files_created": self.files_created,
            "diffs": self.diffs,
            "risk": self.risk.value,
            "revert_path": self.revert_path,
            "status": self.status,
            "created_at": self.created_at
        }


@dataclass
class ValidationReport:
    """
    Validation Report - mahalliy tekshiruv natijalari
    """
    validation_id: str
    clone_id: str
    patch_id: Optional[str]
    
    # Natijalar
    syntax_check: ValidationResult = ValidationResult.SKIP
    lint_check: ValidationResult = ValidationResult.SKIP
    typecheck: ValidationResult = ValidationResult.SKIP
    import_health: ValidationResult = ValidationResult.SKIP
    unit_tests: ValidationResult = ValidationResult.SKIP
    smoke_tests: ValidationResult = ValidationResult.SKIP
    tool_loading: ValidationResult = ValidationResult.SKIP
    config_validation: ValidationResult = ValidationResult.SKIP
    
    # Xatolar
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    # Umumiy
    overall: ValidationResult = ValidationResult.SKIP
    can_proceed: bool = False
    
    # Vaqt
    duration: float = 0.0
    completed_at: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict:
        return {
            "validation_id": self.validation_id,
            "clone_id": self.clone_id,
            "patch_id": self.patch_id,
            "checks": {
                "syntax": self.syntax_check.value,
                "lint": self.lint_check.value,
                "typecheck": self.typecheck.value,
                "import_health": self.import_health.value,
                "unit_tests": self.unit_tests.value,
                "smoke_tests": self.smoke_tests.value,
                "tool_loading": self.tool_loading.value,
                "config_validation": self.config_validation.value
            },
            "errors": self.errors,
            "warnings": self.warnings,
            "overall": self.overall.value,
            "can_proceed": self.can_proceed,
            "duration": self.duration,
            "completed_at": self.completed_at
        }


@dataclass
class CloneArtifact:
    """
    Clone Artifact - har clone nima qilganini saqlash
    """
    artifact_id: str
    clone_id: str
    
    # Turi
    artifact_type: str  # patch, test_result, benchmark, log, screenshot, trace, doc, tool_manifest, error, metric
    
    # Mazmuni
    content: Any
    file_path: Optional[str] = None
    
    # Metadata
    size: int = 0
    mime_type: Optional[str] = None
    
    # Vaqt
    created_at: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict:
        return {
            "artifact_id": self.artifact_id,
            "clone_id": self.clone_id,
            "artifact_type": self.artifact_type,
            "file_path": self.file_path,
            "size": self.size,
            "mime_type": self.mime_type,
            "created_at": self.created_at
        }


@dataclass
class ToolSpec:
    """
    Tool Spec - yangi tool qo'shish uchun spetsifikatsiya
    """
    tool_name: str
    description: str
    when_to_call: str
    input_schema: Dict = field(default_factory=dict)
    output_schema: Dict = field(default_factory=dict)
    side_effects: List[str] = field(default_factory=list)
    required_permissions: List[str] = field(default_factory=list)
    failure_modes: List[str] = field(default_factory=list)
    timeout: int = 30
    audit_required: bool = False
    
    def to_dict(self) -> Dict:
        return {
            "tool_name": self.tool_name,
            "description": self.description,
            "when_to_call": self.when_to_call,
            "input_schema": self.input_schema,
            "output_schema": self.output_schema,
            "side_effects": self.side_effects,
            "required_permissions": self.required_permissions,
            "failure_modes": self.failure_modes,
            "timeout": self.timeout,
            "audit_required": self.audit_required
        }


@dataclass
class CloneLineage:
    """
    Clone Lineage - clone'lar shajarasi
    Har clone bilishi kerak: kimdan tug'ilgan, qaysi signal sabab bo'lgan, etc.
    """
    lineage_id: str
    clone_id: str
    
    # Parent info
    parent_clone_id: Optional[str] = None
    root_clone_id: Optional[str] = None
    
    # Sabab
    signal_reason: str = ""
    benchmark_affected: Optional[str] = None
    
    # Holat
    merged: bool = False
    rejected: bool = False
    forked: bool = False
    forked_to: Optional[str] = None
    
    # Vaqt
    created_at: float = field(default_factory=time.time)
    promoted_at: Optional[float] = None
    
    def to_dict(self) -> Dict:
        return {
            "lineage_id": self.lineage_id,
            "clone_id": self.clone_id,
            "parent_clone_id": self.parent_clone_id,
            "root_clone_id": self.root_clone_id,
            "signal_reason": self.signal_reason,
            "benchmark_affected": self.benchmark_affected,
            "merged": self.merged,
            "rejected": self.rejected,
            "forked": self.forked,
            "forked_to": self.forked_to,
            "created_at": self.created_at,
            "promoted_at": self.promoted_at
        }


# ================================================================================
# EXPORTS
# ================================================================================

__all__ = [
    # Enums
    "CloneType",
    "CloneStatus", 
    "RiskClass",
    "ChangeType",
    "ValidationResult",
    # Data Classes
    "CloneMetadata",
    "ChangeBudget",
    "ImprovementPlan",
    "PatchSet",
    "ValidationReport",
    "CloneArtifact",
    "ToolSpec",
    "CloneLineage",
]
