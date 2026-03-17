"""
Infra Package - Hardened Eval Sandbox Platform
==========================================

Benchmarkni xavfsiz va izolyatsiyalangan holda ishga tushirish.

Modules:
- isolated_run_context: Per-run isolation
- filesystem_guard: Filesystem boundary enforcement
- network_policy: Network policy enforcement
- clean_env: Clean environment builder
- resource_governor: Resource limits
- snapshot_reset: Clean snapshot and reset
- hidden_asset_vault: Hidden asset protection
- result_integrity: Result integrity signing
- parallel_run_coordinator: Parallel run coordination
- fault_containment: Fault containment

Definition of Done:
1. Har run unique isolated workspace'da ishlaydi.
2. Forbidden path access real enforcement bilan bloklanadi.
3. Task-level network policy ishlaydi.
4. Secrets task env/log/trace'ga tushmaydi.
5. Resource limits enforced bo'ladi.
6. Hidden tests/verifiers agent-visible tree'dan tashqarida turadi.
7. Run crash bo'lsa boshqa runlar davom etadi.
8. Result artifacts integrity hash bilan saqlanadi.
"""

from .isolated_run_context import (
    IsolatedRunContext,
    IsolatedContext,
    create_isolated_context,
)

from .filesystem_guard import (
    FilesystemGuard,
    FilesystemPolicy,
    FilesystemViolation,
    create_filesystem_guard,
)

from .network_policy import (
    NetworkPolicyEnforcer,
    NetworkPolicy,
    NetworkPolicyConfig,
    NetworkViolation,
    create_network_enforcer,
)

from .clean_env import (
    CleanEnvBuilder,
    EnvConfig,
    SecretDetected,
    create_clean_env,
)

from .resource_governor import (
    ResourceGovernor,
    ResourceLimits,
    ResourceExceeded,
    create_resource_governor,
)

from .snapshot_reset import (
    SnapshotResetManager,
    SnapshotConfig,
    create_snapshot_manager,
)

from .hidden_asset_vault import (
    HiddenAssetVault,
    HiddenAsset,
    create_hidden_vault,
)

from .result_integrity import (
    ResultIntegritySigner,
    IntegrityRecord,
    create_integrity_signer,
)

from .parallel_run_coordinator import (
    ParallelRunCoordinator,
    RunSlot,
    create_parallel_coordinator,
)

from .fault_containment import (
    FaultContainmentSupervisor,
    CrashReport,
    create_fault_supervisor,
)

__all__ = [
    # Isolation
    "IsolatedRunContext",
    "IsolatedContext",
    "create_isolated_context",
    
    # Filesystem
    "FilesystemGuard",
    "FilesystemPolicy",
    "FilesystemViolation",
    "create_filesystem_guard",
    
    # Network
    "NetworkPolicyEnforcer",
    "NetworkPolicy",
    "NetworkPolicyConfig",
    "NetworkViolation",
    "create_network_enforcer",
    
    # Environment
    "CleanEnvBuilder",
    "EnvConfig",
    "SecretDetected",
    "create_clean_env",
    
    # Resources
    "ResourceGovernor",
    "ResourceLimits",
    "ResourceExceeded",
    "create_resource_governor",
    
    # Snapshot
    "SnapshotResetManager",
    "SnapshotConfig",
    "create_snapshot_manager",
    
    # Hidden Assets
    "HiddenAssetVault",
    "HiddenAsset",
    "create_hidden_vault",
    
    # Integrity
    "ResultIntegritySigner",
    "IntegrityRecord",
    "create_integrity_signer",
    
    # Parallel
    "ParallelRunCoordinator",
    "RunSlot",
    "create_parallel_coordinator",
    
    # Fault
    "FaultContainmentSupervisor",
    "CrashReport",
    "create_fault_supervisor",
]

__version__ = "1.0.0"
