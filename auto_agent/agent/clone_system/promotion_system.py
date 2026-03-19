"""
================================================================================
PROMOTION / FORK / NEW-MODEL DECISION SYSTEM - MAIN ORCHESTRATOR
================================================================================
Bu asosiy orchestrator - barcha promotion modullarni birlashtiradi.

Workflow:
1. clone approved bo'ladi
2. decision engine utility, risk, trust, divergence'ni hisoblaydi
3. tavsiya beradi: reject / experiment / canary / main / branch / fork
4. siz yakuniy qarorni tanlaysiz
5. promotion executor tanlangan yo'lni atomik bajaradi
6. rollback anchor yaratiladi
7. lineage daraxti yangilanadi
8. model oilasi tartibli ravishda o'sadi
================================================================================
"""
import os
import json
import logging
import time
from typing import Dict, List, Optional, Any
from pathlib import Path

from .decision_engine import (
    DecisionEngine, create_decision_engine,
    DestinationType, DecisionScore
)
from .promotion_executor import (
    DestinationPolicy, PromotionExecutor,
    create_destination_policy, create_promotion_executor
)
from .fork_manager import (
    ForkManager, RollbackAnchorManager,
    create_fork_manager, create_rollback_anchor_manager
)
from .reporting_system import ReportingApprovalSystem

logger = logging.getLogger(__name__)


class PromotionDecisionSystem:
    """
    Promotion / Fork / New-Model Decision System
    
    Bu class to'liq promotion va fork boshqaruv tizimini boshqaradi.
    """
    
    def __init__(self, 
                 workspace_root: str,
                 reporting_system: Optional[ReportingApprovalSystem] = None):
        self.workspace_root = Path(workspace_root)
        self.reporting_system = reporting_system
        
        # Initialize all modules
        self.decision_engine = create_decision_engine()
        self.destination_policy = create_destination_policy()
        self.promotion_executor = create_promotion_executor(
            workspace_root, self.destination_policy
        )
        self.fork_manager = create_fork_manager()
        self.rollback_manager = create_rollback_anchor_manager()
        
        logger.info("🎯 Promotion Decision System initialized")
    
    def analyze_and_recommend(self, dossier: Dict) -> Dict:
        """
        Dossier ni tahlil qilib, tavsiya beradi
        
        Args:
            dossier: UpgradeDossier
        
        Returns:
            Dict: Decision scores and recommendation
        """
        # Get approval level
        approval_level = dossier.get("approval_level", "green")
        
        # Analyze with decision engine
        scores = self.decision_engine.analyze(dossier, approval_level)
        
        # Get policy for destination
        recommendation = scores.final_recommendation
        policy = self.destination_policy.get_policy_for_destination(recommendation)
        
        result = {
            "recommendation": recommendation.value if recommendation else "unknown",
            "scores": scores.to_dict(),
            "policy": policy,
            "available_destinations": [d.value for d in DestinationType]
        }
        
        logger.info(f"🎯 Recommendation: {result['recommendation']}")
        
        return result
    
    def execute_promotion(self,
                         clone_id: str,
                         destination: DestinationType,
                         dossier: Dict,
                         approver: str) -> Dict:
        """
        Promotion ni bajarish
        
        Args:
            clone_id: Clone ID
            destination: Destination
            dossier: UpgradeDossier
            approver: Kim tasdiqladi
        
        Returns:
            Dict: Promotion result
        """
        # First analyze to get scores
        scores = self.decision_engine.analyze(dossier)
        
        # Execute promotion
        result = self.promotion_executor.execute_promotion(
            clone_id=clone_id,
            destination=destination,
            dossier=dossier,
            decision_scores=scores.to_dict()
        )
        
        # If success, create rollback anchor
        if result.success:
            self.rollback_manager.create_anchor(
                clone_id=clone_id,
                promoted_to=destination.value,
                parent_version=dossier.get("version", "unknown"),
                config_state={},
                dependencies=[],
                tool_manifest=[],
                lineage=[]
            )
        
        return result.to_dict()
    
    def create_fork(self,
                   parent_branch: str,
                   name: str,
                   intended_domain: str,
                   description: str,
                   capability_profile: List[str]) -> Dict:
        """
        Yangi fork yaratish
        
        Args:
            parent_branch: Parent branch
            name: Fork nomi
            intended_domain: Domain
            description: Tavsif
            capability_profile: Capability profili
        
        Returns:
            Dict: Fork info
        """
        fork = self.fork_manager.create_fork(
            parent_branch=parent_branch,
            name=name,
            intended_domain=intended_domain,
            description=description,
            capability_profile=capability_profile
        )
        
        return fork.to_dict()
    
    def get_model_family_status(self) -> Dict:
        """
        Model oilasi holatini olish
        
        Returns:
            Dict: Model family status
        """
        branches = self.fork_manager.get_all_branches()
        forks = self.fork_manager.get_all_forks()
        
        return {
            "total_branches": len(branches),
            "total_forks": len(forks),
            "branches": [b.to_dict() for b in branches],
            "forks": [f.to_dict() for f in forks],
            "fork_stats": self.fork_manager.get_fork_statistics()
        }
    
    def suggest_destination(self, dossier: Dict) -> str:
        """
        Destination taklif qilish
        
        Args:
            dossier: UpgradeDossier
        
        Returns:
            str: Taklif
        """
        result = self.analyze_and_recommend(dossier)
        return result.get("recommendation", "unknown")
    
    def get_rollback_plan(self, clone_id: str) -> Optional[Dict]:
        """
        Rollback plan olish
        
        Args:
            clone_id: Clone ID
        
        Returns:
            Dict: Rollback plan
        """
        anchors = self.rollback_manager.get_anchors_for_clone(clone_id)
        
        if anchors:
            return anchors[0]
        
        return None
    
    def get_promotion_history(self, limit: int = 20) -> List[Dict]:
        """Promotion tarixi"""
        return self.promotion_executor.get_promotion_history(limit)


def create_promotion_decision_system(workspace_root: str,
                                    reporting_system: Optional[ReportingApprovalSystem] = None) -> PromotionDecisionSystem:
    """
    Promotion Decision System yaratish
    
    Args:
        workspace_root: Workspace yo'li
        reporting_system: Reporting system (ixtiyoriy)
    
    Returns:
        PromotionDecisionSystem
    """
    return PromotionDecisionSystem(workspace_root, reporting_system)
