"""
Deterministic Replay and Simulation Subsystem
==============================================

Bu subsystem kernel'ga quyidagi imkoniyatlarni beradi:
- Deterministic replay - aniq qaysi joyda xato bo'lganini qayta o'ynash
- Simulation mode - real side-effect qilmasdan sinash
- Recovery/replan o'zgarishi foyda berdimi yo'qmi tekshirish
- "bu bug qayta chiqadimi?" degan savolga aniq javob berish

Componentlar:
- DeterministicClock: Vaqt manbai
- DeterministicIdSource: Task ID / event ID generator
- ReplayEngine: Run ledger'dan executionni qayta o'ynash
- SimulationMode: Turli rejimlar (REAL, REPLAY, SIMULATE, SHADOW)
- ScenarioRunner: Ssenariylarni sinash
- DivergenceAnalyzer: Farqlarni aniqlash
"""

from .clock import DeterministicClock
from .id_source import DeterministicIdSource
from .replay_engine import ReplayEngine, ReplayConfig, ReplayMode
from .simulation_mode import SimulationMode, ExecutionMode
from .scenario_runner import ScenarioRunner
from .divergence_analyzer import DivergenceAnalyzer, DivergenceReport
from .event_taxonomy import ReplayEvent, EventTaxonomy

__all__ = [
    'DeterministicClock',
    'DeterministicIdSource',
    'ReplayEngine',
    'ReplayConfig',
    'ReplayMode',
    'SimulationMode',
    'ExecutionMode',
    'ScenarioRunner',
    'DivergenceAnalyzer',
    'DivergenceReport',
    'ReplayEvent',
    'EventTaxonomy',
]
