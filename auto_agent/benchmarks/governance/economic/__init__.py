"""
Economic Governance Layer - Cost-Effective Autonomy
=============================================

This module provides economic governance for autonomous operations:
- Budget management
- Model routing
- Tool ROI analysis
- Queue governance
- Swarm economics
- Cost anomaly detection
- Marginal gain tracking

Author: No1 World+ Autonomous System
"""

from benchmarks.governance.economic.budget_manager import (
    BudgetManager,
    BudgetType,
    BudgetScope,
    BudgetStatus,
    create_budget_manager
)

from benchmarks.governance.economic.model_router_economist import (
    ModelRouterEconomist,
    ModelTier,
    RoutingStrategy,
    TaskComplexity,
    create_model_router
)

from benchmarks.governance.economic.tool_roi_analyzer import (
    ToolROIAnalyzer,
    ToolCategory,
    ToolEfficiency,
    create_tool_roi_analyzer
)

from benchmarks.governance.economic.queue_governor import (
    QueueGovernor,
    TaskPriority,
    TaskCategory,
    create_queue_governor
)

from benchmarks.governance.economic.swarm_economist import (
    SwarmEconomist,
    ParallelismStrategy,
    create_swarm_economist
)

from benchmarks.governance.economic.cost_anomaly_detector import (
    CostAnomalyDetector,
    AnomalyType,
    AnomalySeverity,
    create_cost_anomaly_detector
)

from benchmarks.governance.economic.marginal_gain_tracker import (
    MarginalGainTracker,
    ImprovementType,
    create_marginal_gain_tracker
)

from benchmarks.governance.economic.economic_benchmark import (
    EconomicBenchmarkSuite,
    create_economic_suite
)

__all__ = [
    # Budget
    "BudgetManager",
    "BudgetType",
    "BudgetScope",
    "BudgetStatus",
    "create_budget_manager",
    
    # Model Routing
    "ModelRouterEconomist",
    "ModelTier",
    "RoutingStrategy",
    "TaskComplexity",
    "create_model_router",
    
    # Tool ROI
    "ToolROIAnalyzer",
    "ToolCategory",
    "ToolEfficiency",
    "create_tool_roi_analyzer",
    
    # Queue
    "QueueGovernor",
    "TaskPriority",
    "create_queue_governor",
    
    # Swarm
    "SwarmEconomist",
    "ParallelismStrategy",
    "create_swarm_economist",
    
    # Anomaly Detection
    "CostAnomalyDetector",
    "AnomalyType",
    "AnomalySeverity",
    "create_cost_anomaly_detector",
    
    # Marginal Gains
    "MarginalGainTracker",
    "ImprovementType",
    "create_marginal_gain_tracker",
    
    # Benchmark
    "EconomicBenchmarkSuite",
    "create_economic_suite"
]
