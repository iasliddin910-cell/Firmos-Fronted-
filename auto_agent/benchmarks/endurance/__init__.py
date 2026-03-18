"""
Endurance Evaluation Layer - Multi-hour autonomous stability evaluation
====================================================================

This module provides comprehensive endurance testing for long-run autonomous operations.
It evaluates the system's ability to maintain stability, quality, and performance over
extended periods (hours to days) of continuous operation.

Exports:
- EnduranceBenchmarkSuite: Main orchestrator for endurance tests
- SessionAgingAnalyzer: Session aging and decay analysis
- MemoryHealthMonitor: Memory health and rot detection
- RetryStormDetector: Retry storm and pattern detection
- CheckpointIntegrityVerifier: Checkpoint/restore integrity
- AccumulatedChangeRiskAnalyzer: Self-modification risk tracking
- DriftSentinel: Drift detection and mitigation
- SafeModeFallback: Emergency safe mode system
- KernelVitalSigns: Continuous health monitoring

Author: No1 World+ Autonomous System
"""

from benchmarks.endurance.endurance_benchmark import (
    EnduranceBenchmarkSuite,
    EnduranceTaskFamilies,
    SessionState,
    DecayType,
    create_endurance_suite
)

from benchmarks.endurance.session_aging_analyzer import (
    SessionAgingAnalyzer,
    AgingWatcher,
    AgingPhase,
    DecayCategory,
    create_session_analyzer,
    create_aging_watcher
)

from benchmarks.endurance.memory_health_monitor import (
    MemoryHealthMonitor,
    MemoryHealthLevel,
    MemoryIssueType,
    create_memory_health_monitor
)

from benchmarks.endurance.retry_storm_detector import (
    RetryStormDetector,
    RetryPatternType,
    StormSeverity,
    create_retry_storm_detector
)

from benchmarks.endurance.drift_sentinel import (
    DriftSentinel,
    DriftType,
    DriftSeverity,
    MitigationAction,
    create_drift_sentinel
)

from benchmarks.endurance.checkpoint_integrity import (
    CheckpointIntegrityVerifier,
    CheckpointStorage,
    IntegrityStatus,
    IntegrityIssueType,
    create_checkpoint_verifier
)

from benchmarks.endurance.accumulated_change_risk import (
    AccumulatedChangeRiskAnalyzer,
    ChangeType,
    RiskLevel,
    create_change_risk_analyzer
)

from benchmarks.endurance.safe_mode_fallback import (
    SafeModeFallback,
    SafeModeLevel,
    FallbackAction,
    create_safe_mode_fallback
)

from benchmarks.endurance.kernel_vital_signs import (
    KernelVitalSigns,
    VitalStatus,
    MetricType,
    create_kernel_vital_signs
)

__all__ = [
    # Endurance Benchmark
    "EnduranceBenchmarkSuite",
    "EnduranceTaskFamilies",
    "SessionState",
    "DecayType",
    "create_endurance_suite",
    
    # Session Aging
    "SessionAgingAnalyzer",
    "AgingWatcher",
    "AgingPhase",
    "DecayCategory",
    "create_session_analyzer",
    "create_aging_watcher",
    
    # Memory Health
    "MemoryHealthMonitor",
    "MemoryHealthLevel",
    "MemoryIssueType",
    "create_memory_health_monitor",
    
    # Retry Storm
    "RetryStormDetector",
    "RetryPatternType",
    "StormSeverity",
    "create_retry_storm_detector",
    
    # Drift Sentinel
    "DriftSentinel",
    "DriftType",
    "DriftSeverity",
    "MitigationAction",
    "create_drift_sentinel",
    
    # Checkpoint Integrity
    "CheckpointIntegrityVerifier",
    "CheckpointStorage",
    "IntegrityStatus",
    "IntegrityIssueType",
    "create_checkpoint_verifier",
    
    # Change Risk
    "AccumulatedChangeRiskAnalyzer",
    "ChangeType",
    "RiskLevel",
    "create_change_risk_analyzer",
    
    # Safe Mode
    "SafeModeFallback",
    "SafeModeLevel",
    "FallbackAction",
    "create_safe_mode_fallback",
    
    # Vital Signs
    "KernelVitalSigns",
    "VitalStatus",
    "MetricType",
    "create_kernel_vital_signs"
]
