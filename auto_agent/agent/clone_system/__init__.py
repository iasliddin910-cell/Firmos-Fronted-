"""
================================================================================
SELF-CLONE IMPROVEMENT SYSTEM
================================================================================
World-Class Self-Improvement Architecture for OmniAgent X

Bu modul 8 ta asosiy qavatni o'z ichiga oladi:
1. Clone Factory - Clone yaratish tizimi
2. Source Clone Layer - Kod nusxasi bilan ishlash
3. Runtime Isolation - Runtime izolyatsiya
4. Clone Knowledge Layer - Clone bilim bazasi
5. Improvement Planner - Yaxshilash rejalashtiruvchi
6. Patch/Build/Extend Layer - O'zgartirish qilish
7. Local Validation - Mahalliy tekshiruv
8. Clone Artifact Store - Natijalar arxivi

Usage:
    from agent.clone_system import SelfCloneSystem, CloneType, CloneStatus
    
    # Create system
    system = create_self_clone_system("/path/to/workspace")
    
    # Create clone
    clone = system.create_clone(
        clone_type=CloneType.CAPABILITY,
        reason="Add new browser capability"
    )
    
    # Run improvement
    result = system.run_improvement_cycle(
        clone_id=clone.clone_id,
        signal="Add DOM memory layer",
        patch_content={"agent/memory.py": "..."}
    )
    
    # Validate
    report = system.validate_clone(clone.clone_id)
    
    # Promote or reject
    if report.can_proceed:
        system.promote_clone(clone.clone_id)
    else:
        system.reject_clone(clone.clone_id, "Validation failed")

================================================================================
"""

# Core types
from .core_types import (
    # Enums
    CloneType,
    CloneStatus,
    RiskClass,
    ChangeType,
    ValidationResult,
    # Data classes
    CloneMetadata,
    ChangeBudget,
    ImprovementPlan,
    PatchSet,
    ValidationReport,
    CloneArtifact,
    ToolSpec,
    CloneLineage,
)

# Layers
from .clone_factory import (
    CloneFactory,
    SourceCloneManager,
    create_clone_factory,
    create_source_clone_manager,
)

from .runtime_isolation import (
    RuntimeIsolator,
    RuntimeLimits,
    CloneRuntime,
    SecretScopeManager,
    create_runtime_isolator,
    create_secret_scope_manager,
)

from .clone_knowledge import (
    RepositoryMapper,
    SelfModelGraph,
    CloneKnowledgeManager,
    create_knowledge_manager,
)

from .improvement_planner import (
    ImprovementPlanner,
    PatchGenerator,
    create_improvement_planner,
    create_patch_generator,
)

from .patch_build_extend import (
    PatchExecutor,
    ToolOnboarding,
    BenchmarkAdder,
    create_patch_executor,
    create_tool_onboarding,
    create_benchmark_adder,
)

from .local_validation import (
    LocalValidator,
    ValidationGate,
    create_local_validator,
    create_validation_gate,
)

from .artifact_store import (
    ArtifactStore,
    LineageRegistry,
    ReportGenerator,
    create_artifact_store,
    create_lineage_registry,
    create_report_generator,
)

# Main system
from .self_clone_system import (
    SelfCloneSystem,
    create_self_clone_system,
)

# Reporting & Approval System
from .reporting_types import (
    ApprovalLevel,
    ApprovalAction,
    DecisionRecommendation,
    TrustLevel,
    ReportLevel,
    CodeDelta,
    CapabilityDelta,
    ToolDelta,
    BehaviorDelta,
    MetricsImpact,
    RiskItem,
    EvidenceItem,
    UpgradePassport,
    UpgradeDossier,
)

from .report_aggregator import ReportAggregator, create_report_aggregator
from .delta_analyzer import DeltaAnalyzer, create_delta_analyzer
from .benchmark_comparison import BenchmarkComparisonEngine, create_benchmark_comparison_engine
from .risk_narrator import RiskNarrator, create_risk_narrator
from .approval_console import HumanApprovalConsole, create_human_approval_console
from .reporting_system import ReportingApprovalSystem, create_reporting_approval_system

# Version
__version__ = "1.0.0"
__author__ = "OmniAgent X Team"

__all__ = [
    # Reporting types
    "ApprovalLevel",
    "ApprovalAction",
    "DecisionRecommendation",
    "TrustLevel",
    "ReportLevel",
    "CodeDelta",
    "CapabilityDelta",
    "ToolDelta",
    "BehaviorDelta",
    "MetricsImpact",
    "RiskItem",
    "EvidenceItem",
    "UpgradePassport",
    "UpgradeDossier",
    # Modules
    "ReportAggregator",
    "create_report_aggregator",
    "DeltaAnalyzer",
    "create_delta_analyzer",
    "BenchmarkComparisonEngine",
    "create_benchmark_comparison_engine",
    "RiskNarrator",
    "create_risk_narrator",
    "HumanApprovalConsole",
    "create_human_approval_console",
    "ReportingApprovalSystem",
    "create_reporting_approval_system",
]
