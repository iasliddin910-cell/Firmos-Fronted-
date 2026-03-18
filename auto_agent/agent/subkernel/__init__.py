"""
OmniAgent X - SUBKERNEL ARCHITECTURE
====================================
Core vs Subkernel Constitution

Bu fayl kernel va subkernel o'rtasidagi aniq boundary'ni belgilaydi.
Bu canonical source of truth - barcha keyingi o'zgarishlar shu asosda qilinadi.

CONSTITUTION PRINCIPLE:
- Kernel barqaror qoladi, capability'lar esa modul sifatida o'sadi
- Core o'zgarmaydi, capability provider'lar almashadi
"""

from enum import Enum
from typing import Set, List, FrozenSet


class SubkernelCategory(str, Enum):
    """Subkernel kategoriyalari - ular qayerda ishlashini aniqlaydi"""
    # UI/Frontend adapters
    ADAPTER = "adapter"
    
    # Execution backends
    EXECUTION = "execution"
    
    # Intelligence/Reasoning
    INTELLIGENCE = "intelligence"
    
    # Storage/Memory
    STORAGE = "storage"
    
    # Monitoring/Health
    MONITORING = "monitoring"
    
    # Policy/Security
    POLICY = "policy"
    
    # Learning/Improvement
    LEARNING = "learning"
    
    # External Integrations
    INTEGRATION = "integration"


class CoreComponent(str, Enum):
    """
    CORE DA QOLADIGAN KOMPONENTLAR
    
    Bu komponentlar O'ZGARMAYDI - ular kernel constitution hisoblanadi.
    Har qanday o'zgarish faqat subkernel orqali amalga oshiriladi.
    """
    
    # === TASK ORCHESTRATION ===
    TASK_LIFECYCLE = "task_lifecycle"           # Task yaratish, bajarish, tugatish
    TASK_QUEUE = "task_queue"                   # Navbat boshqaruvi
    TASK_STATE = "task_state"                   # State machine
    
    # === CONSTITUTION & INVARIANTS ===
    CONSTITUTION = "constitution"               # Asosiy qoidalar
    INVARIANTS = "invariants"                   # O'zgarmas shartlar
    POLICY_DECISION = "policy_decision"         # Policy qarorlar
    
    # === EXECUTION CONTROL ===
    RUN_LEDGER = "run_ledger"                   # Barcha execution'lar ro'yxati
    BUDGET_GATE = "budget_gate"                 # Resource budget
    APPROVAL_WORKFLOW = "approval_workflow"     # Ruxsat olish
    
    # === HEALTH & RECOVERY ===
    HEALTH_SPINE = "health_spine"               # Health monitoring
    RECOVERY_ENGINE = "recovery_engine"          # Xatolardan qayta tiklanish
    ROLLBACK_SYSTEM = "rollback_system"         # Qayta tiklash
    
    # === CHECKPOINT & STATE ===
    CHECKPOINT = "checkpoint"                   # State saqlash
    RESTORE = "restore"                         # State tiklash
    
    # === KERNEL API ===
    KERNEL_API = "kernel_api"                   # Tashqi API surface
    COMMAND_HANDLER = "command_handler"        # Buyruq qabul qilish
    EVENT_STREAM = "event_stream"               # Event stream
    
    # === REPLAY BASE ===
    REPLAY_CLOCK = "replay_clock"               # Vaqt boshqaruvi (base)
    REPLAY_ID = "replay_id"                     # ID generator (base)


class PluggableCapability(str, Enum):
    """
    SUBKERNEL / PLUGIN BO'LIB AJRATILADIGAN CAPABILITY'LAR
    
    Bu capability'lar kernel ichidan chiqariladi va subkernel sifatida ishlaydi.
    Ularni kernel bevosita EMAS, balkim subkernel registry orqali chaqiriladi.
    """
    
    # === EXECUTION BACKENDS ===
    BROWSER_EXECUTION = "browser_execution"     # Browser automation
    CODE_EXECUTION = "code_execution"           # Code interpreter
    COMMAND_EXECUTION = "command_execution"     # Terminal commands
    TOOL_ENGINE = "tool_engine"                 # Tools collection
    
    # === INTELLIGENCE ===
    NATIVE_BRAIN = "native_brain"               # OpenAI function calling
    PLANNER = "planner"                         # Task planning
    VERIFICATION = "verification"               # Task verification
    
    # === WEB & SEARCH ===
    WEB_SEARCH = "web_search"                    # Internet search
    WEB_SCRAPING = "web_scraping"               # Web scraping
    API_CLIENT = "api_client"                   # API calls
    
    # === STORAGE & MEMORY ===
    SEMANTIC_MEMORY = "semantic_memory"         # Knowledge base
    AGENT_MEMORY = "agent_memory"               # Task/run history
    CONVERSATION = "conversation"               # Chat history
    
    # === MONITORING ===
    HEALTH_CHECK = "health_check"               # Health probes
    TELEMETRY = "telemetry"                     # Metrics collection
    LOGGING = "logging"                         # Centralized logging
    
    # === SECURITY ===
    SECRET_GUARD = "secret_guard"               # Secret redaction
    SANDBOX = "sandbox"                        # Execution sandbox
    APPROVAL_ENGINE = "approval_engine"        # Approval workflow
    
    # === LEARNING ===
    LEARNING_PIPELINE = "learning_pipeline"     # Learning system
    SELF_IMPROVEMENT = "self_improvement"       # Self-patching
    BENCHMARK = "benchmark"                     # Benchmark suite
    REGRESSION = "regression"                   # Regression testing
    
    # === UI/ADAPTERS ===
    UI = "ui"                                   # GUI interface
    TELEGRAM = "telegram"                       # Telegram bot
    CLI = "cli"                                 # Command line
    VOICE = "voice"                             # Voice interface
    VISION = "vision"                           # Vision/OCR
    
    # === EXTERNAL INTEGRATIONS ===
    REPLAY_ENGINE = "replay_engine"             # Replay system
    SCENARIO_RUNNER = "scenario_runner"        # Scenario runner
    DIVERGENCE = "divergence_analyzer"         # Divergence detection
    
    # === TOOL FACTORY ===
    TOOL_FACTORY = "tool_factory"               # Dynamic tool creation
    
    # === DEPENDENCY ===
    DEPENDENCY_HANDLER = "dependency_handler"    # Package management
    
    # === MULTI-AGENT ===
    MULTI_AGENT = "multi_agent_coordinator"     # Multi-agent coordination


# Mapping: PluggableCapability -> SubkernelCategory
CAPABILITY_TO_CATEGORY: dict = {
    # Execution -> EXECUTION
    PluggableCapability.BROWSER_EXECUTION: SubkernelCategory.EXECUTION,
    PluggableCapability.CODE_EXECUTION: SubkernelCategory.EXECUTION,
    PluggableCapability.COMMAND_EXECUTION: SubkernelCategory.EXECUTION,
    PluggableCapability.TOOL_ENGINE: SubkernelCategory.EXECUTION,
    
    # Intelligence -> INTELLIGENCE
    PluggableCapability.NATIVE_BRAIN: SubkernelCategory.INTELLIGENCE,
    PluggableCapability.PLANNER: SubkernelCategory.INTELLIGENCE,
    PluggableCapability.VERIFICATION: SubkernelCategory.INTELLIGENCE,
    
    # Storage -> STORAGE
    PluggableCapability.SEMANTIC_MEMORY: SubkernelCategory.STORAGE,
    PluggableCapability.AGENT_MEMORY: SubkernelCategory.STORAGE,
    PluggableCapability.CONVERSATION: SubkernelCategory.STORAGE,
    
    # Monitoring -> MONITORING
    PluggableCapability.HEALTH_CHECK: SubkernelCategory.MONITORING,
    PluggableCapability.TELEMETRY: SubkernelCategory.MONITORING,
    PluggableCapability.LOGGING: SubkernelCategory.MONITORING,
    
    # Policy -> POLICY
    PluggableCapability.SECRET_GUARD: SubkernelCategory.POLICY,
    PluggableCapability.SANDBOX: SubkernelCategory.POLICY,
    PluggableCapability.APPROVAL_ENGINE: SubkernelCategory.POLICY,
    
    # Learning -> LEARNING
    PluggableCapability.LEARNING_PIPELINE: SubkernelCategory.LEARNING,
    PluggableCapability.SELF_IMPROVEMENT: SubkernelCategory.LEARNING,
    PluggableCapability.BENCHMARK: SubkernelCategory.LEARNING,
    PluggableCapability.REGRESSION: SubkernelCategory.LEARNING,
    
    # Adapters -> ADAPTER
    PluggableCapability.UI: SubkernelCategory.ADAPTER,
    PluggableCapability.TELEGRAM: SubkernelCategory.ADAPTER,
    PluggableCapability.CLI: SubkernelCategory.ADAPTER,
    PluggableCapability.VOICE: SubkernelCategory.ADAPTER,
    PluggableCapability.VISION: SubkernelCategory.ADAPTER,
    
    # Integration -> INTEGRATION
    PluggableCapability.WEB_SEARCH: SubkernelCategory.INTEGRATION,
    PluggableCapability.WEB_SCRAPING: SubkernelCategory.INTEGRATION,
    PluggableCapability.API_CLIENT: SubkernelCategory.INTEGRATION,
    PluggableCapability.REPLAY_ENGINE: SubkernelCategory.INTEGRATION,
    PluggableCapability.SCENARIO_RUNNER: SubkernelCategory.INTEGRATION,
    PluggableCapability.DIVERGENCE: SubkernelCategory.INTEGRATION,
    PluggableCapability.TOOL_FACTORY: SubkernelCategory.INTEGRATION,
    PluggableCapability.DEPENDENCY_HANDLER: SubkernelCategory.INTEGRATION,
    PluggableCapability.MULTI_AGENT: SubkernelCategory.INTEGRATION,
}


class SubkernelStatus(str, Enum):
    """Subkernel holatlari"""
    DISCOVERED = "discovered"           # Topilgan, lekin hali tekshirilmagan
    VALIDATING = "validating"           # Validatsiya jarayonida
    INITIALIZING = "initializing"      # Ishga tushirilmoqda
    READY = "ready"                     # Tayyor
    ACTIVE = "active"                  # Faol
    DEGRADED = "degraded"              # Cheklangan rejimda
    QUARANTINED = "quarantined"         # Izolyatsiya qilingan
    DISABLED = "disabled"               # O'chirilgan
    UNLOADED = "unloaded"              # Yuklanmagan
    FAILED = "failed"                   # Xato


class TrustLevel(str, Enum):
    """
    Trust class - subkernelga qancha ishonch bor
    """
    CORE_TRUSTED = "core_trusted"       # Kernel bilan birga keladi, ishonchli
    INTERNAL_TRUSTED = "internal_trusted"  # Ichki, sinovdan o'tgan
    EXPERIMENTAL = "experimental"      # Tajriba uchun
    READ_ONLY = "read_only"             # Faqat o'qish
    DESTRUCTIVE_HIGH_RISK = "destructive"  # Xavfli operatsiyalar


# Interface nomlari - subkernel qaysi interface'larni implement qiladi
class SubkernelInterface(str, Enum):
    """Subkernel implement qilishi mumkin bo'lgan interface'lar"""
    # Majburiy interface'lar
    INITIALIZABLE = "initializable"     # init() methodi
    HEALTHY = "healthy"                 # health_check() methodi
    
    # Ixtiyoriy interface'lar
    REPLAYABLE = "replayable"           # Replay'da ishlaydi
    DEGRADABLE = "degradable"           # Degraded mode'da ishlaydi
    QUARANTINEABLE = "quarantineable"   # Quarantine'da ishlaydi
    VERSIONED = "versioned"             # Versioning support
    METRICABLE = "metricable"           # Metrics beradi
    RECOVERABLE = "recoverable"         # O'zi tiklanadi


# Kernel API versions - backward compatibility uchun
KERNEL_API_VERSIONS: Set[str] = {"1.0", "1.1", "2.0"}


def get_subkernel_category(capability: PluggableCapability) -> SubkernelCategory:
    """Capability uchun category olish"""
    return CAPABILITY_TO_CATEGORY.get(capability, SubkernelCategory.INTEGRATION)


def is_core_component(component: str) -> bool:
    """Bu component core'da qoladimi?"""
    try:
        CoreComponent(component)
        return True
    except ValueError:
        return False


def is_pluggable_capability(capability: str) -> bool:
    """Bu capability pluggable mi?"""
    try:
        PluggableCapability(capability)
        return True
    except ValueError:
        return False


# Export all submodules
from agent.subkernel.spec import (
    SubkernelSpec,
    PluginManifest,
    create_browser_execution_spec,
    create_code_execution_spec,
    create_native_brain_spec,
    create_tool_engine_spec,
    create_sandbox_spec,
    create_health_check_spec,
    create_replay_engine_spec,
    create_memory_spec,
    BUILTIN_SUBKERNEL_SPECS,
)

from agent.subkernel.registry import (
    CapabilityRegistry,
    get_capability_registry,
    reset_capability_registry,
    RegistryEvent,
    CapabilityInfo,
)

from agent.subkernel.lifecycle import (
    LifecycleManager,
    get_lifecycle_manager,
    reset_lifecycle_manager,
    LifecycleEvent,
    LifecycleTransition,
    SubkernelProvider,
)

from agent.subkernel.trust import (
    TrustManager,
    get_trust_manager,
    reset_trust_manager,
    TrustPolicy,
    ContainmentPolicy,
    TRUST_POLICIES,
    CONTAINMENT_BY_TRUST,
    PolicyPosture,
    AccessLevel,
)

from agent.subkernel.sandbox import (
    SubkernelSandbox,
    SandboxManager,
    get_sandbox_manager,
    reset_sandbox_manager,
    SandboxConfig,
    SandboxMetrics,
    ExecutionResult,
    IsolationLevel,
)

from agent.subkernel.gateway import (
    SubkernelGateway,
    create_subkernel_gateway,
    KernelSubkernelMixin,
)
