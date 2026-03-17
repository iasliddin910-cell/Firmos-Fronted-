"""
Governance Package - Benchmark Governance System
==========================================

Benchmarkni mahsulot sifatida boshqarish tizimi.

Modules:
- task_registry: Task markaziy reestr
- release_pipeline: Release jarayoni
- dedup_analyzer: Duplicate aniqlash
- contamination_guard: Contamination tekshirish
- dataset_health: Sog'liq metrikalari

Definition of Done:
1. Har task registry'da metadata bilan turadi.
2. Task lifecycle state'lari mavjud.
3. Stable pack release pipeline orqali chiqadi.
4. Dedup va contamination scan ishlaydi.
5. Dataset health report mavjud.
6. Deprecated/quarantined tasklar boarddan ajratiladi.
"""

from .task_registry import (
    TaskRegistry,
    TaskMetadata,
    TaskState,
    FlakeStatus,
    ContaminationRisk,
    Owner,
    OwnerManager,
    create_task_metadata,
    create_task_registry,
    create_owner_manager,
)

from .release_pipeline import (
    BenchmarkReleasePipeline,
    ReleaseManager,
    ReleaseType,
    ReleaseStage,
    ValidationResult,
    ReleaseCandidate,
    create_release_pipeline,
    create_release_manager,
)

from .dedup_analyzer import (
    DedupAnalyzer,
    DuplicateGroup,
    OverlapResult,
    create_dedup_analyzer,
)

from .contamination_guard import (
    ContaminationGuard,
    ContaminationResult,
    ExposureLevel,
    ContaminationType,
    ExposureTracker,
    create_contamination_guard,
)

from .dataset_health import (
    DatasetHealthReport,
    HealthReport,
    HealthMetrics,
    create_health_report,
)

__all__ = [
    # Task Registry
    "TaskRegistry",
    "TaskMetadata",
    "TaskState",
    "FlakeStatus",
    "ContaminationRisk",
    "Owner",
    "OwnerManager",
    "create_task_metadata",
    "create_task_registry",
    "create_owner_manager",
    
    # Release Pipeline
    "BenchmarkReleasePipeline",
    "ReleaseManager",
    "ReleaseType",
    "ReleaseStage",
    "ValidationResult",
    "ReleaseCandidate",
    "create_release_pipeline",
    "create_release_manager",
    
    # Dedup
    "DedupAnalyzer",
    "DuplicateGroup",
    "OverlapResult",
    "create_dedup_analyzer",
    
    # Contamination
    "ContaminationGuard",
    "ContaminationResult",
    "ExposureLevel",
    "ContaminationType",
    "ExposureTracker",
    "create_contamination_guard",
    
    # Health
    "DatasetHealthReport",
    "HealthReport",
    "HealthMetrics",
    "create_health_report",
]

__version__ = "1.0.0"
