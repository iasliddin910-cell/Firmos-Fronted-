"""
Swarm Evaluation Layer - Multi-Agent Evaluation Framework

Bu modul multi-agent tizimlarni baholash uchun to'liq framework.

Policy 1: Multi-agent claim evalsiz qabul qilinmaydi.
Policy 2: Parallel run single-agent baseline bilan solishtiriladi.
Policy 3: Duplicate effort penalti oladi.
Policy 4: Merge without court taqiqlanadi.
Policy 5: Partial failure recovery score'da alohida ko'rinadi.
Policy 6: Net-parallel-gain bo'lmasa stable promote yo'q.
"""

from .swarm_benchmark import (
    SwarmBenchmarkSuite,
    WorkerRole,
    TaskType,
    EvaluationMetric,
    WorkNode,
    WorkGraph,
    WorkerExecution,
    MultiAgentResult,
    SwarmBenchmarkTask
)

from .work_graph_planner import (
    WorkGraphPlanner,
    ContractType,
    ArtifactContract,
    NodeDependency
)

from .merge_court import (
    MergeCourt,
    MergeDecision,
    ConflictType,
    BranchDiff,
    MergeConflict,
    MergeRuling
)

from .swarm_telemetry import (
    SwarmTelemetry,
    MetricType,
    WorkerMetric,
    SwarmTelemetryEvent
)

from .duplicate_effort_detector import (
    DuplicateEffortDetector,
    DuplicateType,
    DuplicateInstance
)

from .role_router_evaluator import (
    RoleRouterEvaluator,
    RoutingDecision,
    RoleRoute
)

from .parallel_fallback_manager import (
    ParallelFallbackManager,
    FallbackStrategy,
    FailureEvent,
    FallbackAction,
    RecoveryResult
)

from .net_parallel_gain_score import (
    NetParallelGainScore,
    GainType,
    BaselineMetrics,
    MultiAgentMetrics,
    GainScore
)

from .arbitration_policy import (
    ArbitrationPolicy,
    AuthorityRole,
    Decision,
    ArbitrationCase
)


__all__ = [
    # Swarm Benchmark
    'SwarmBenchmarkSuite',
    'WorkerRole',
    'TaskType',
    'EvaluationMetric',
    'WorkNode',
    'WorkGraph',
    'WorkerExecution',
    'MultiAgentResult',
    'SwarmBenchmarkTask',
    
    # Work Graph Planner
    'WorkGraphPlanner',
    'ContractType',
    'ArtifactContract',
    'NodeDependency',
    
    # Merge Court
    'MergeCourt',
    'MergeDecision',
    'ConflictType',
    'BranchDiff',
    'MergeConflict',
    'MergeRuling',
    
    # Swarm Telemetry
    'SwarmTelemetry',
    'MetricType',
    'WorkerMetric',
    'SwarmTelemetryEvent',
    
    # Duplicate Effort Detector
    'DuplicateEffortDetector',
    'DuplicateType',
    'DuplicateInstance',
    
    # Role Router Evaluator
    'RoleRouterEvaluator',
    'RoutingDecision',
    'RoleRoute',
    
    # Parallel Fallback Manager
    'ParallelFallbackManager',
    'FallbackStrategy',
    'FailureEvent',
    'FallbackAction',
    'RecoveryResult',
    
    # Net Parallel Gain Score
    'NetParallelGainScore',
    'GainType',
    'BaselineMetrics',
    'MultiAgentMetrics',
    'GainScore',
    
    # Arbitration Policy
    'ArbitrationPolicy',
    'AuthorityRole',
    'Decision',
    'ArbitrationCase'
]
