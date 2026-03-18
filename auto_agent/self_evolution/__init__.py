"""
Unified Master Architecture - Self Evolution System
====================================================
Bu World No1+ darajasida self-evolving platforma!
"""

import logging
from pathlib import Path

from .data_contracts import *
from .intake import SignalIngest, TriageEngine, SignalCourt
from .candidates import CandidateRegistry, CandidateQueue, CandidateFactory, LifecycleManager
from .clones import ExecutionLayer
from .evaluation import EvaluationLayer
from .reporting import ReportingLayer
from .governance import GovernanceLayer
from .promotion import PromotionLayer
from .memory import MemoryLayer
from .orchestrator import CentralOrchestrator

logger = logging.getLogger(__name__)


def create_self_evolution_system(workspace_path: str) -> dict:
    """To'liq Self-Evolution System yaratish"""
    logger.info("🚀 Creating Self-Evolution System...")
    
    workspace = Path(workspace_path)
    workspace.mkdir(parents=True, exist_ok=True)
    
    # Intake
    intake_system = {"ingest": SignalIngest(), "triage": TriageEngine(), "court": SignalCourt()}
    
    # Candidates
    registry = CandidateRegistry()
    candidate_system = {"registry": registry, "queue": CandidateQueue(registry), "factory": CandidateFactory(registry), "lifecycle": LifecycleManager(registry, CandidateQueue(registry))}
    
    # Execution
    execution_layer = ExecutionLayer(workspace_path)
    
    # Evaluation
    evaluation_layer = EvaluationLayer(workspace_path)
    
    # Reporting
    reporting_layer = ReportingLayer()
    
    # Governance
    governance_layer = GovernanceLayer()
    
    # Promotion
    promotion_layer = PromotionLayer(workspace_path)
    
    # Memory
    memory_layer = MemoryLayer(str(workspace / "memory"))
    
    # Orchestrator
    orchestrator = CentralOrchestrator(workspace_path)
    orchestrator.connect_layers({
        "intake": intake_system,
        "candidates": candidate_system,
        "execution": execution_layer,
        "evaluation": evaluation_layer,
        "reporting": reporting_layer,
        "governance": governance_layer,
        "promotion": promotion_layer,
        "memory": memory_layer
    })
    
    logger.info("✅ Self-Evolution System created!")
    
    return {"orchestrator": orchestrator, "intake": intake_system, "candidates": candidate_system, "execution": execution_layer, "evaluation": evaluation_layer, "reporting": reporting_layer, "governance": governance_layer, "promotion": promotion_layer, "memory": memory_layer}


__all__ = ["create_self_evolution_system", "Observation", "UpgradeCandidate", "CloneRun", "EvaluationBundle", "UpgradeDossier", "PromotionRecord", "SystemState"]
