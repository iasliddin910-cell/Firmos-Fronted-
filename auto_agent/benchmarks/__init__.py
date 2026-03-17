"""
OmniAgent X - Benchmarks Package
================================

This package contains all benchmark suites for agent evaluation.

Subpackages:
- self_mod: Self-modification benchmark tasks
- tool_creation: Tool-creation benchmark tasks  
- meta_verifiers: Meta-verification components
- adaptive_curriculum: Adaptive curriculum engine for benchmark evolution
- swarm_eval: Multi-agent evaluation framework

Main modules:
- meta_capability_benchmark: Complete meta-capability evaluation system
"""
from .meta_capability_benchmark import (
    SelfModificationBenchmark,
    ToolCreationBenchmark,
    DeltaHarness,
    MetaPolicy,
    LineageTracker,
    MetaLeaderboard,
    create_meta_capability_suite,
    create_self_modification_benchmark,
    create_tool_creation_benchmark
)

# Import adaptive curriculum
try:
    from .adaptive_curriculum import (
        AdaptiveCurriculumEngine,
        AdaptiveCurriculumConfig,
        CurriculumReport,
        FrontierMiner,
        FailureClusterer,
        TaskMutator,
        DifficultyCalibrator,
        CapabilityGapGenerator,
        FrontierTaskForge,
        CurriculumBoard,
        AutoRetirePolicy
    )
    _has_adaptive = True
except ImportError:
    _has_adaptive = False

# Import swarm eval
try:
    from .swarm_eval import (
        SwarmBenchmarkSuite,
        WorkGraphPlanner,
        MergeCourt,
        SwarmTelemetry,
        DuplicateEffortDetector,
        RoleRouterEvaluator,
        ParallelFallbackManager,
        NetParallelGainScore,
        ArbitrationPolicy,
        WorkerRole,
        TaskType,
        WorkGraph,
        MultiAgentResult
    )
    _has_swarm = True
except ImportError:
    _has_swarm = False

__all__ = [
    "SelfModificationBenchmark",
    "ToolCreationBenchmark", 
    "DeltaHarness",
    "MetaPolicy",
    "LineageTracker",
    "MetaLeaderboard",
    "create_meta_capability_suite",
    "create_self_modification_benchmark",
    "create_tool_creation_benchmark",
    # Adaptive curriculum
    "AdaptiveCurriculumEngine",
    "AdaptiveCurriculumConfig",
    "CurriculumReport",
    # Swarm eval
    "SwarmBenchmarkSuite",
    "WorkGraphPlanner",
    "MergeCourt",
    "SwarmTelemetry",
    "DuplicateEffortDetector",
    "RoleRouterEvaluator",
    "ParallelFallbackManager",
    "NetParallelGainScore",
    "ArbitrationPolicy",
    "WorkerRole",
    "TaskType",
    "WorkGraph",
    "MultiAgentResult"
]