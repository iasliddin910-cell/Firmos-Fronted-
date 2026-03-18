"""
OmniAgent X - SubkernelSpec
===========================
Typed capability unit specification

Har bir subkernel bu spec bilan ta'riflanadi.
Bu kernelga subkernel haqida to'liq ma'lumot beradi.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Set, FrozenSet
from enum import Enum

from agent.subkernel import (
    SubkernelCategory, 
    SubkernelStatus, 
    TrustLevel,
    SubkernelInterface,
    PluggableCapability,
    CAPABILITY_TO_CATEGORY
)


@dataclass(frozen=True)
class SubkernelSpec:
    """
    Subkernel Specification - typed unit for capability
    
    Bu dataclass har bir subkernel uchun majburiy specification.
    Kernel bu orqali subkernel haqida hamma narsani biladi.
    """
    
    # === IDENTIFICATION ===
    name: str                              # Subkernel nomi (e.g., "browser_execution")
    capability_type: PluggableCapability   # Capability turi
    version: str                           # Version (e.g., "1.0.0")
    
    # === CLASSIFICATION ===
    category: SubkernelCategory           # Qaysi kategoriyaga tegishli
    trust_class: TrustLevel               # Trust level
    interfaces: FrozenSet[SubkernelInterface]  # Implement qilgan interface'lar
    
    # === DEPENDENCIES ===
    dependencies: FrozenSet[str] = field(default_factory=frozenset)  # Kerakli boshqa subkernel'lar
    optional_dependencies: FrozenSet[str] = field(default_factory=frozenset)  # Ixtiyoriy
    
    # === CAPABILITIES ===
    replay_safe: bool = False              # Replay'da ishlaydi
    can_degrade: bool = True               # Degraded mode'da ishlaydi
    can_quarantine: bool = True            # Quarantine'da ishlaydi
    supports_simulation: bool = False       # Simulation mode support
    
    # === HEALTH ===
    health_probes: FrozenSet[str] = field(default_factory=frozenset)  # Health probe nomlari
    health_interval_seconds: int = 60      # Health check interval
    
    # === METADATA ===
    description: str = ""                  # Taqdimot
    author: str = ""                        # Muallif
    license: str = ""                       # Licenziya
    
    # === CONFIGURATION ===
    config_schema: Dict[str, Any] = field(default_factory=dict)  # Config schema
    default_config: Dict[str, Any] = field(default_factory=dict)  # Default config
    
    # === RUNTIME ===
    startup_priority: int = 100            # Startup tartibi (0 = eng birinchi)
    shutdown_priority: int = 100           # Shutdown tartibi
    
    # === COMPATIBILITY ===
    kernel_api_version: str = "2.0"        # Kerakli kernel API version
    min_kernel_version: str = "1.0"        # Minimal kernel version
    
    # === CONSTRAINTS ===
    resource_limits: Dict[str, Any] = field(default_factory=dict)  # Resource cheklovlar
    execution_mode: str = "normal"         # normal, sandboxed, isolated
    
    def __post_init__(self):
        """Validate spec after creation"""
        # Auto-set category if not provided
        if self.category is None:
            object.__setattr__(self, 'category', CAPABILITY_TO_CATEGORY.get(self.capability_type, SubkernelCategory.INTEGRATION))
    
    def get_interfaces(self) -> Set[SubkernelInterface]:
        """Get all implemented interfaces"""
        return set(self.interfaces)
    
    def has_interface(self, interface: SubkernelInterface) -> bool:
        """Check if has specific interface"""
        return interface in self.interfaces
    
    def is_healthy_requirement(self, probe: str) -> bool:
        """Check if probe is required for health"""
        return probe in self.health_probes
    
    def validate_version(self, kernel_version: str) -> bool:
        """Validate kernel version compatibility"""
        # Simple version check - could be more sophisticated
        if self.min_kernel_version:
            # Parse versions and compare
            try:
                required = tuple(map(int, self.min_kernel_version.split('.')))
                current = tuple(map(int, kernel_version.split('.')))
                return current >= required
            except:
                return True  # Skip on parse error
        return True


@dataclass
class PluginManifest:
    """
    Plugin Manifest - Subkernel ro'yxatdan o'tish uchun majburiy manifest
    
    Har yangi subkernel qo'shilganda bu manifest to'ldiriladi.
    Bu kernelga subkernel haqida to'liq ma'lumot beradi.
    """
    
    # === SUBKERNEL INFO ===
    spec: SubkernelSpec                    # SubkernelSpec
    
    # === REGISTRATION ===
    registered_at: str = ""               # Ro'yxatdan o'tgan vaqt
    registration_source: str = ""          # Qayerdan kelgan (file, remote, dynamic)
    
    # === RUNTIME STATE ===
    status: SubkernelStatus = SubkernelStatus.DISCOVERED
    current_version: str = ""              # Hozirgi version
    
    # === HEALTH STATE ===
    last_health_check: Optional[float] = None  # Oxirgi health check vaqti
    health_score: float = 1.0              # Health ball (0-1)
    consecutive_failures: int = 0          # Ketma-ket muvaffaqiyatsizliklar
    
    # === RESOURCE STATE ===
    memory_usage_mb: float = 0.0           # Xotira ishlatish
    cpu_usage_percent: float = 0.0        # CPU ishlatish
    
    # === ERROR STATE ===
    last_error: Optional[str] = None       # Oxirgi xato
    error_count: int = 0                   # Jami xatolar soni
    
    # === CAPABILITY STATE ===
    is_active: bool = False                # Faolmi
    is_loaded: bool = False                # Yuklanganmi
    load_error: Optional[str] = None       # Yuklash xatosi
    
    # === DEGRADATION STATE ===
    degradation_reason: Optional[str] = None  # Degradasiya sababi
    degraded_at: Optional[float] = None    # Degradasiya vaqti
    
    # === QUARANTINE STATE ===
    quarantine_reason: Optional[str] = None  # Karantin sababi
    quarantined_at: Optional[float] = None  # Karantin vaqti
    
    # === METRICS ===
    total_calls: int = 0                    # Jami chaqiruvlar
    successful_calls: int = 0              # Muvaffaqiyatli chaqiruvlar
    failed_calls: int = 0                  # Muvaffaqiyatsiz chaqiruvlar
    total_latency_ms: float = 0.0          # Umumiy kechikish
    
    def get_success_rate(self) -> float:
        """Get success rate"""
        if self.total_calls == 0:
            return 1.0
        return self.successful_calls / self.total_calls
    
    def get_average_latency(self) -> float:
        """Get average latency"""
        if self.total_calls == 0:
            return 0.0
        return self.total_latency_ms / self.total_calls
    
    def is_healthy(self) -> bool:
        """Check if subkernel is healthy"""
        return (
            self.status in (SubkernelStatus.READY, SubkernelStatus.ACTIVE) and
            self.health_score >= 0.7 and
            self.consecutive_failures < 3
        )
    
    def should_quarantine(self) -> bool:
        """Check if should be quarantined"""
        return (
            self.consecutive_failures >= 5 or
            self.status == SubkernelStatus.FAILED
        )
    
    def get_health_summary(self) -> Dict[str, Any]:
        """Get health summary"""
        return {
            "name": self.spec.name,
            "status": self.status.value,
            "health_score": self.health_score,
            "is_healthy": self.is_healthy(),
            "consecutive_failures": self.consecutive_failures,
            "total_calls": self.total_calls,
            "success_rate": self.get_success_rate(),
            "avg_latency_ms": self.get_average_latency(),
            "last_error": self.last_error,
            "degradation_reason": self.degradation_reason,
        }


# Factory functions for creating specs
def create_browser_execution_spec() -> SubkernelSpec:
    """Browser Execution subkernel spec"""
    return SubkernelSpec(
        name="browser_execution",
        capability_type=PluggableCapability.BROWSER_EXECUTION,
        version="1.0.0",
        category=SubkernelCategory.EXECUTION,
        trust_class=TrustLevel.INTERNAL_TRUSTED,
        interfaces=frozenset({
            SubkernelInterface.INITIALIZABLE,
            SubkernelInterface.HEALTHY,
            SubkernelInterface.REPLAYABLE,
            SubkernelInterface.DEGRADABLE,
        }),
        dependencies=frozenset({"tool_engine", "sandbox"}),
        replay_safe=False,  # Browser ops non-idempotent
        can_degrade=True,
        health_probes=frozenset({"browser_available", "page_load"}),
        description="Browser automation and web interaction",
        startup_priority=50,
    )


def create_code_execution_spec() -> SubkernelSpec:
    """Code Execution subkernel spec"""
    return SubkernelSpec(
        name="code_execution",
        capability_type=PluggableCapability.CODE_EXECUTION,
        version="1.0.0",
        category=SubkernelCategory.EXECUTION,
        trust_class=TrustLevel.INTERNAL_TRUSTED,
        interfaces=frozenset({
            SubkernelInterface.INITIALIZABLE,
            SubkernelInterface.HEALTHY,
            SubkernelInterface.REPLAYABLE,
            SubkernelInterface.DEGRADABLE,
        }),
        dependencies=frozenset({"sandbox", "dependency_handler"}),
        replay_safe=True,  # Code execution can be replayed
        can_degrade=True,
        health_probes=frozenset({"interpreter_available", "package_ready"}),
        description="Python code execution and interpretation",
        startup_priority=50,
    )


def create_native_brain_spec() -> SubkernelSpec:
    """Native Brain (LLM) subkernel spec"""
    return SubkernelSpec(
        name="native_brain",
        capability_type=PluggableCapability.NATIVE_BRAIN,
        version="1.0.0",
        category=SubkernelCategory.INTELLIGENCE,
        trust_class=TrustLevel.CORE_TRUSTED,
        interfaces=frozenset({
            SubkernelInterface.INITIALIZABLE,
            SubkernelInterface.HEALTHY,
            SubkernelInterface.METRICABLE,
        }),
        dependencies=frozenset(),
        replay_safe=False,  # LLM responses are non-deterministic
        can_degrade=False,   # Core brain cannot degrade
        health_probes=frozenset({"api_available", "response_valid"}),
        description="OpenAI GPT function calling brain",
        startup_priority=10,  # Start early
    )


def create_tool_engine_spec() -> SubkernelSpec:
    """Tool Engine subkernel spec"""
    return SubkernelSpec(
        name="tool_engine",
        capability_type=PluggableCapability.TOOL_ENGINE,
        version="1.0.0",
        category=SubkernelCategory.EXECUTION,
        trust_class=TrustLevel.CORE_TRUSTED,
        interfaces=frozenset({
            SubkernelInterface.INITIALIZABLE,
            SubkernelInterface.HEALTHY,
            SubkernelInterface.REPLAYABLE,
            SubkernelInterface.METRICABLE,
        }),
        dependencies=frozenset({"sandbox", "approval_engine"}),
        replay_safe=False,  # Tool execution is non-idempotent
        can_degrade=True,
        health_probes=frozenset({"tools_loaded"}),
        description="Core tool execution engine",
        startup_priority=20,
    )


def create_sandbox_spec() -> SubkernelSpec:
    """Sandbox subkernel spec"""
    return SubkernelSpec(
        name="sandbox",
        capability_type=PluggableCapability.SANDBOX,
        version="1.0.0",
        category=SubkernelCategory.POLICY,
        trust_class=TrustLevel.CORE_TRUSTED,
        interfaces=frozenset({
            SubkernelInterface.INITIALIZABLE,
            SubkernelInterface.HEALTHY,
        }),
        dependencies=frozenset(),
        replay_safe=True,
        can_degrade=False,  # Cannot degrade - core security
        health_probes=frozenset({"sandbox_initialized"}),
        description="Execution sandbox for safety",
        startup_priority=5,  # Start first!
    )


def create_health_check_spec() -> SubkernelSpec:
    """Health Check subkernel spec"""
    return SubkernelSpec(
        name="health_check",
        capability_type=PluggableCapability.HEALTH_CHECK,
        version="1.0.0",
        category=SubkernelCategory.MONITORING,
        trust_class=TrustLevel.CORE_TRUSTED,
        interfaces=frozenset({
            SubkernelInterface.INITIALIZABLE,
            SubkernelInterface.HEALTHY,
            SubkernelInterface.METRICABLE,
        }),
        dependencies=frozenset(),
        replay_safe=True,
        can_degrade=False,
        health_probes=frozenset({"self_check"}),
        description="Health monitoring and probes",
        startup_priority=3,  # Very early
    )


def create_replay_engine_spec() -> SubkernelSpec:
    """Replay Engine subkernel spec"""
    return SubkernelSpec(
        name="replay_engine",
        capability_type=PluggableCapability.REPLAY_ENGINE,
        version="1.0.0",
        category=SubkernelCategory.INTEGRATION,
        trust_class=TrustLevel.INTERNAL_TRUSTED,
        interfaces=frozenset({
            SubkernelInterface.INITIALIZABLE,
            SubkernelInterface.HEALTHY,
            SubkernelInterface.REPLAYABLE,
        }),
        dependencies=frozenset({"replay_clock", "replay_id"}),
        replay_safe=True,
        can_degrade=True,
        health_probes=frozenset({"replay_available"}),
        description="Deterministic replay and simulation",
        startup_priority=30,
        supports_simulation=True,
    )


def create_memory_spec() -> SubkernelSpec:
    """Memory subkernel spec"""
    return SubkernelSpec(
        name="semantic_memory",
        capability_type=PluggableCapability.SEMANTIC_MEMORY,
        version="1.0.0",
        category=SubkernelCategory.STORAGE,
        trust_class=TrustLevel.CORE_TRUSTED,
        interfaces=frozenset({
            SubkernelInterface.INITIALIZABLE,
            SubkernelInterface.HEALTHY,
            SubkernelInterface.REPLAYABLE,
            SubkernelInterface.METRICABLE,
        }),
        dependencies=frozenset(),
        replay_safe=True,
        can_degrade=True,
        health_probes=frozenset({"storage_available"}),
        description="Semantic memory and knowledge base",
        startup_priority=40,
    )


# Registry of known subkernel specs
BUILTIN_SUBKERNEL_SPECS: Dict[str, SubkernelSpec] = {
    "browser_execution": create_browser_execution_spec(),
    "code_execution": create_code_execution_spec(),
    "native_brain": create_native_brain_spec(),
    "tool_engine": create_tool_engine_spec(),
    "sandbox": create_sandbox_spec(),
    "health_check": create_health_check_spec(),
    "replay_engine": create_replay_engine_spec(),
    "semantic_memory": create_memory_spec(),
}
