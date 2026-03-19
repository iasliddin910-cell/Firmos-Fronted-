"""
================================================================================
DESTINATION POLICY & PROMOTION EXECUTOR
================================================================================
"""
import os
import json
import logging
import time
import subprocess
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime

from .decision_engine import DestinationType, PromotionResult, BranchInfo, BranchStatus

logger = logging.getLogger(__name__)


class DestinationPolicy:
    """
    Destination Policy Layer
    
    Har upgrade uchun destination policy boshqaradi.
    """
    
    def __init__(self):
        # Known branches
        self.branches: Dict[str, BranchInfo] = {}
        
        # Initialize default main branch
        self._init_default_branches()
        
        logger.info("📍 Destination Policy initialized")
    
    def _init_default_branches(self):
        """Default branch larni yaratish"""
        main = BranchInfo(
            branch_id="main",
            name="main",
            branch_type="main",
            status=BranchStatus.STABLE,
            intended_domain="general",
            constitution={
                "trust_requirement": "high",
                "risk_tolerance": "low",
                "experimental_allowed": False
            }
        )
        self.branches["main"] = main
        
        # Create default canary
        canary = BranchInfo(
            branch_id="canary",
            name="canary",
            branch_type="canary",
            status=BranchStatus.CANARY,
            parent_branch="main",
            intended_domain="testing",
            constitution={
                "trust_requirement": "medium",
                "risk_tolerance": "medium",
                "experimental_allowed": True
            }
        )
        self.branches["canary"] = canary
    
    def get_policy_for_destination(self, destination: DestinationType) -> Dict:
        """Destination uchun policy olish"""
        policies = {
            DestinationType.REJECT: {
                "action": "archive",
                "retention": "indefinite",
                "can_revisit": True
            },
            DestinationType.ARCHIVE_EXPERIMENT: {
                "action": "archive",
                "retention": "90_days",
                "can_revisit": True
            },
            DestinationType.CANARY: {
                "action": "deploy",
                "scope": "limited",
                "monitoring": "required",
                "promotion_criteria": "stable_after_7_days"
            },
            DestinationType.MAIN: {
                "action": "merge",
                "scope": "full",
                "monitoring": "standard",
                "rollback_if_fail": True
            },
            DestinationType.SPECIALIZED_BRANCH: {
                "action": "create_branch",
                "scope": "specialized",
                "domain": "auto_detect"
            },
            DestinationType.NEW_FORK: {
                "action": "create_fork",
                "scope": "independent",
                "inheritance": "selective"
            }
        }
        
        return policies.get(destination, {})
    
    def can_promote(self, destination: DestinationType, approval_level: str) -> bool:
        """Promote mumkinmi"""
        if destination == DestinationType.MAIN:
            return approval_level in ["green", "yellow"]
        
        if destination == DestinationType.CANARY:
            return True
        
        return True


class PromotionExecutor:
    """
    Promotion Executor
    
    Qaror qabul qilingach, amaliy harakatni bajaradi.
    """
    
    def __init__(self, 
                 workspace_root: str,
                 destination_policy: DestinationPolicy):
        self.workspace_root = Path(workspace_root)
        self.destination_policy = destination_policy
        
        # Promotion history
        self.promotions: Dict[str, Dict] = {}
        
        logger.info("🚀 Promotion Executor initialized")
    
    def execute_promotion(self,
                         clone_id: str,
                         destination: DestinationType,
                         dossier: Dict,
                         decision_scores: Dict) -> PromotionResult:
        """
        Promotion ni bajarish
        
        Args:
            clone_id: Clone ID
            destination: Destination
            dossier: UpgradeDossier
            decision_scores: Decision scores
        
        Returns:
            PromotionResult
        """
        promotion_id = f"promo_{clone_id}_{int(time.time())}"
        
        try:
            # 1. Clone final freeze
            logger.info(f"1. Freezing clone {clone_id}...")
            
            # 2. All artifacts hashed
            artifacts_hash = self._hash_artifacts(clone_id)
            logger.info(f"2. Artifacts hashed: {artifacts_hash[:16]}...")
            
            # 3. Approval attached
            # (Already in dossier)
            
            # 4. Destination chosen
            dest_path = self._get_destination_path(destination)
            logger.info(f"3. Destination: {dest_path}")
            
            # 5. Create rollback anchor
            rollback_id = self._create_rollback_anchor(
                clone_id, destination, dossier
            )
            logger.info(f"4. Rollback anchor: {rollback_id}")
            
            # 6. Execute promotion based on type
            if destination == DestinationType.CANARY:
                result = self._promote_to_canary(clone_id, dossier)
            elif destination == DestinationType.MAIN:
                result = self._promote_to_main(clone_id, dossier)
            elif destination == DestinationType.SPECIALIZED_BRANCH:
                result = self._promote_to_branch(clone_id, dossier)
            elif destination == DestinationType.NEW_FORK:
                result = self._promote_to_fork(clone_id, dossier)
            else:
                result = self._archive_clone(clone_id, destination)
            
            logger.info(f"5. Promotion executed: {result}")
            
            # 7. Record promotion
            self.promotions[promotion_id] = {
                "clone_id": clone_id,
                "destination": destination.value,
                "destination_path": dest_path,
                "rollback_anchor_id": rollback_id,
                "artifacts_hash": artifacts_hash,
                "timestamp": time.time()
            }
            
            return PromotionResult(
                success=True,
                destination=destination,
                destination_path=dest_path,
                promotion_id=promotion_id,
                rollback_anchor_id=rollback_id,
                message="Promotion successful"
            )
            
        except Exception as e:
            logger.error(f"Promotion failed: {e}")
            return PromotionResult(
                success=False,
                destination=destination,
                message=f"Promotion failed: {str(e)}"
            )
    
    def _hash_artifacts(self, clone_id: str) -> str:
        """Artifacts ni hash qilish"""
        import hashlib
        
        # Simple hash of clone_id
        return hashlib.sha256(clone_id.encode()).hexdigest()
    
    def _get_destination_path(self, destination: DestinationType) -> str:
        """Destination path olish"""
        paths = {
            DestinationType.REJECT: "archive/rejected/",
            DestinationType.ARCHIVE_EXPERIMENT: "archive/experiments/",
            DestinationType.CANARY: "branches/canary/",
            DestinationType.MAIN: "branches/main/",
            DestinationType.SPECIALIZED_BRANCH: "branches/specialized/",
            DestinationType.NEW_FORK: "forks/"
        }
        
        return paths.get(destination, "unknown/")
    
    def _create_rollback_anchor(self,
                                clone_id: str,
                                destination: DestinationType,
                                dossier: Dict) -> str:
        """Rollback anchor yaratish"""
        anchor_id = f"anchor_{clone_id}_{int(time.time())}"
        
        # Store anchor info
        anchor_data = {
            "anchor_id": anchor_id,
            "clone_id": clone_id,
            "destination": destination.value,
            "created_at": time.time()
        }
        
        logger.info(f"Created rollback anchor: {anchor_id}")
        
        return anchor_id
    
    def _promote_to_canary(self, clone_id: str, dossier: Dict) -> str:
        """Canary ga promote qilish"""
        # In reality, this would:
        # 1. Cherry-pick changes to canary branch
        # 2. Deploy to limited environment
        # 3. Set up monitoring
        
        logger.info(f"Promoting {clone_id} to canary")
        return "canary/promoted"
    
    def _promote_to_main(self, clone_id: str, dossier: Dict) -> str:
        """Main ga promote qilish"""
        # In reality, this would:
        # 1. Merge to main branch
        # 2. Tag release
        # 3. Deploy
        
        logger.info(f"Promoting {clone_id} to main")
        return "main/promoted"
    
    def _promote_to_branch(self, clone_id: str, dossier: Dict) -> str:
        """Specialized branch ga promote qilish"""
        logger.info(f"Creating specialized branch for {clone_id}")
        return "branches/specialized/created"
    
    def _promote_to_fork(self, clone_id: str, dossier: Dict) -> str:
        """Fork yaratish"""
        logger.info(f"Creating new fork for {clone_id}")
        return "forks/new/created"
    
    def _archive_clone(self, clone_id: str, destination: DestinationType) -> str:
        """Clone ni arxivlash"""
        logger.info(f"Archiving {clone_id} as {destination.value}")
        return "archived"
    
    def get_promotion_status(self, promotion_id: str) -> Optional[Dict]:
        """Promotion holatini olish"""
        return self.promotions.get(promotion_id)
    
    def get_promotion_history(self, limit: int = 20) -> List[Dict]:
        """Promotion tarixi"""
        history = list(self.promotions.values())
        history.sort(key=lambda x: x.get("timestamp", 0), reverse=True)
        return history[:limit]


def create_destination_policy() -> DestinationPolicy:
    """Destination Policy yaratish"""
    return DestinationPolicy()


def create_promotion_executor(workspace_root: str, 
                             destination_policy: DestinationPolicy) -> PromotionExecutor:
    """Promotion Executor yaratish"""
    return PromotionExecutor(workspace_root, destination_policy)
