"""
Analytics Package - Eval Intelligence & Analytics Layer
==================================================

Benchmark data'ni insight'ga aylantiradi.

Modules:
- trace_schema: Standard trace format
- run_explorer: Run analysis view
- failure_path_analyzer: Failure pattern analysis
- success_pattern_miner: Success pattern mining
- patch_analytics: Patch analysis
- tool_analytics: Tool usage analysis
- drift_detector: Capability drift detection
- experiment_comparator: Experiment comparison
- cohort_analyzer: Cohort analysis
- anomaly_detector: Anomaly detection

Definition of Done:
1. Har benchmark run standart trace bilan saqlanadi.
2. Run explorer orqali bitta run'ni timeline ko'rishda tahlil qila olasan.
3. Failure va success pattern reportlari mavjud.
4. Patch impact va tool effectiveness reportlari mavjud.
5. Drift va anomaly detector ishlaydi.
6. Experiment A/B solishtirish structured tarzda ishlaydi.
"""

from .trace_schema import (
    TaskTrace,
    RunTrace,
    ToolCall,
    Phase,
    Outcome,
    ErrorType,
    TraceStorage,
    create_task_trace,
    create_run_trace,
    create_trace_storage,
)

from .run_explorer import (
    RunExplorer,
    RunSummary,
    TaskSummary,
    create_run_explorer,
)

from .failure_path_analyzer import (
    FailurePathAnalyzer,
    FailurePattern,
    FailureInsight,
    create_failure_analyzer,
)

from .success_pattern_miner import (
    SuccessPatternMiner,
    SuccessPattern,
    SuccessInsight,
    create_success_miner,
)

from .patch_analytics import (
    PatchAnalytics,
    PatchMetrics,
    create_patch_analytics,
)

from .tool_analytics import (
    ToolAnalytics,
    ToolMetrics,
    create_tool_analytics,
)

from .drift_detector import (
    DriftDetector,
    DriftSignal,
    DriftReport,
    create_drift_detector,
)

from .experiment_comparator import (
    ExperimentComparator,
    ComparisonResult,
    create_comparator,
)

from .cohort_analyzer import (
    CohortAnalyzer,
    create_cohort_analyzer,
)

from .anomaly_detector import (
    AnomalyDetector,
    Anomaly,
    create_anomaly_detector,
)

__all__ = [
    # Trace Schema
    "TaskTrace",
    "RunTrace",
    "ToolCall",
    "Phase",
    "Outcome",
    "ErrorType",
    "TraceStorage",
    "create_task_trace",
    "create_run_trace",
    "create_trace_storage",
    
    # Run Explorer
    "RunExplorer",
    "RunSummary",
    "TaskSummary",
    "create_run_explorer",
    
    # Failure Analysis
    "FailurePathAnalyzer",
    "FailurePattern",
    "FailureInsight",
    "create_failure_analyzer",
    
    # Success Mining
    "SuccessPatternMiner",
    "SuccessPattern",
    "SuccessInsight",
    "create_success_miner",
    
    # Patch Analytics
    "PatchAnalytics",
    "PatchMetrics",
    "create_patch_analytics",
    
    # Tool Analytics
    "ToolAnalytics",
    "ToolMetrics",
    "create_tool_analytics",
    
    # Drift Detection
    "DriftDetector",
    "DriftSignal",
    "DriftReport",
    "create_drift_detector",
    
    # Experiment Comparison
    "ExperimentComparator",
    "ComparisonResult",
    "create_comparator",
    
    # Cohort Analysis
    "CohortAnalyzer",
    "create_cohort_analyzer",
    
    # Anomaly Detection
    "AnomalyDetector",
    "Anomaly",
    "create_anomaly_detector",
]

__version__ = "1.0.0"
