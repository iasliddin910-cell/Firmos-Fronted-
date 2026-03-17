"""
Calibration Package - External Calibration Layer
========================================

External calibration va shadow twin kernel.

Modules:
- external_benchmark_bridge: Tashqi benchmark adapter
- calibration_pack_manager: Calibration pack management
- reality_gap_report: Gap analysis
- transfer_score: Transfer evaluation
- shadow_twin_kernel: Sandbox testing
"""

from .external_benchmark_bridge import (
    ExternalBenchmarkBridge,
    ExternalBenchmarkType,
    ExternalTask,
    ExternalResult,
    create_bridge,
)

from .calibration_pack_manager import (
    CalibrationPackManager,
    CalibrationPack,
    create_calibration_manager,
)

from .reality_gap_report import (
    RealityGapAnalyzer,
    RealityGapReport,
    GapAnalysis,
    create_gap_analyzer,
)

from .transfer_score import (
    TransferScorer,
    TransferMetrics,
    create_transfer_scorer,
)

from .shadow_twin_kernel import (
    ShadowTwinKernel,
    TwinConfig,
    TwinResult,
    create_shadow_twin,
)

__all__ = [
    # Bridge
    "ExternalBenchmarkBridge",
    "ExternalBenchmarkType",
    "ExternalTask",
    "ExternalResult",
    "create_bridge",
    
    # Pack Manager
    "CalibrationPackManager",
    "CalibrationPack",
    "create_calibration_manager",
    
    # Gap Report
    "RealityGapAnalyzer",
    "RealityGapReport",
    "GapAnalysis",
    "create_gap_analyzer",
    
    # Transfer
    "TransferScorer",
    "TransferMetrics",
    "create_transfer_scorer",
    
    # Shadow Twin
    "ShadowTwinKernel",
    "TwinConfig",
    "TwinResult",
    "create_shadow_twin",
]

__version__ = "1.0.0"
