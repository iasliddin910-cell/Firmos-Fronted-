"""
Change Planner & Patch Strategy Engine
======================================
The surgical brain of the self-modifying system.

This module implements:
1. Change Planner - decides WHERE, HOW, and WHEN to patch
2. Patch Family Selector - selects the right transform engine
3. Phase-based patching - staged execution for safety
4. Risk Engine - blast radius calculation
5. Proof Obligations - verification before promotion

Key Components:
- GoalCompiler: Request → GoalSpec
- ConstraintMiner: Extract constraints from code understanding
- ChangeClassifier: Classify change type (6 types)
- StrategySynthesizer: Generate 3 candidate plans
- PatchFamilySelector: Select transform engine
- PhasePatcher: 5-phase staged execution
- RiskEngine: Blast radius calculation
- ProofEngine: Pre-commit verification
- ChangePlanner: Main orchestrator (8 layers)
"""

from agent.planner.contracts import (
    GoalSpec,
    EditContract,
    EditPlan,
    ProofObligation,
    RiskAssessment,
    PatchFamily,
    ChangeType,
    ChangePhase,
    RiskLevel,
    ConstraintSpec,
    PlannerMetrics
)

from .goal_compiler import GoalCompiler
from .constraint_miner import ConstraintMiner
from .change_classifier import ChangeClassifier
from .strategy_synthesizer import StrategySynthesizer
from .patch_family_selector import PatchFamilySelector
from .phase_patcher import PhasePatcher
from .risk_engine import RiskEngine
from .proof_engine import ProofEngine
from .change_planner import ChangePlanner, PlanningResult

__all__ = [
    # Contracts
    'GoalSpec',
    'EditContract', 
    'EditPlan',
    'ProofObligation',
    'RiskAssessment',
    'PatchFamily',
    'ChangeType',
    'ChangePhase',
    'RiskLevel',
    'ConstraintSpec',
    'PlannerMetrics',
    
    # Core modules
    'ChangePlanner',
    'PlanningResult',
    'GoalCompiler',
    'ConstraintMiner', 
    'ChangeClassifier',
    'StrategySynthesizer',
    'PatchFamilySelector',
    'PhasePatcher',
    'RiskEngine',
    'ProofEngine',
]
