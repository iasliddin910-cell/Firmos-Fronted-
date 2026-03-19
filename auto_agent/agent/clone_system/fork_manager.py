"""
================================================================================
FORK MANAGER & ROLLBACK ANCHOR
================================================================================
"""
import os
import json
import logging
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from .decision_engine import ForkSpec, MergePolicy, BranchInfo, BranchStatus

logger = logging.getLogger(__name__)


class ForkManager:
    """
    Fork Manager
    
    Yangi fork/model yaratish va boshqarish.
    """
    
    def __init__(self):
        # Forks storage
        self.forks: Dict[str, ForkSpec] = {}
        self.branches: Dict[str, BranchInfo] = {}
        
        # Initialize default
        self._init_default()
        
        logger.info("🍴 Fork Manager initialized")
    
    def _init_default(self):
        """Default branch larni sozlash"""
        # Main branch
        self.branches["main"] = BranchInfo(
            branch_id="main",
            name="main",
            branch_type="main",
            status=BranchStatus.STABLE,
            intended_domain="general",
            constitution={
                "trust_requirement": "high",
                "risk_tolerance": "low",
                "experimental_allowed": False,
                "promotion_criteria": "strict"
            }
        )
        
        # Code specialized
        self.branches["code"] = BranchInfo(
            branch_id="code",
            name="F1-Code",
            branch_type="specialized",
            parent_branch="main",
            intended_domain="coding",
            capability_profile=["code_execution", "code_generation", "debugging"],
            constitution={
                "trust_requirement": "medium",
                "risk_tolerance": "medium",
                "experimental_allowed": True,
                "promotion_criteria": "code_benchmarks"
            }
        )
        
        # Research specialized
        self.branches["research"] = BranchInfo(
            branch_id="research",
            name="F1-Research",
            branch_type="specialized",
            parent_branch="main",
            intended_domain="research",
            capability_profile=["web_browsing", "data_analysis", "summarization"],
            constitution={
                "trust_requirement": "medium",
                "risk_tolerance": "high",
                "experimental_allowed": True,
                "promotion_criteria": "research_metrics"
            }
        )
    
    def create_fork(self,
                   parent_branch: str,
                   name: str,
                   intended_domain: str,
                   description: str,
                   capability_profile: List[str],
                   update_policy: str = "periodic") -> ForkSpec:
        """Yangi fork yaratish"""
        fork_id = f"fork_{name.lower()}_{int(time.time())}"
        
        fork = ForkSpec(
            fork_id=fork_id,
            parent_branch=parent_branch,
            name=name,
            intended_domain=intended_domain,
            description=description,
            capability_profile=capability_profile,
            update_policy=update_policy
        )
        
        self.forks[fork_id] = fork
        
        # Also create branch
        branch = BranchInfo(
            branch_id=fork_id,
            name=name,
            branch_type="fork",
            parent_branch=parent_branch,
            intended_domain=intended_domain,
            capability_profile=capability_profile,
            constitution={
                "trust_requirement": "medium",
                "risk_tolerance": "medium",
                "experimental_allowed": True
            }
        )
        self.branches[fork_id] = branch
        
        logger.info(f"🍴 Fork created: {name} (from {parent_branch})")
        
        return fork
    
    def get_fork(self, fork_id: str) -> Optional[ForkSpec]:
        return self.forks.get(fork_id)
    
    def get_all_forks(self) -> List[ForkSpec]:
        return list(self.forks.values())
    
    def get_branch(self, branch_id: str) -> Optional[BranchInfo]:
        return self.branches.get(branch_id)
    
    def get_all_branches(self) -> List[BranchInfo]:
        return list(self.branches.values())
    
    def get_specialized_branches(self) -> List[BranchInfo]:
        return [b for b in self.branches.values() if b.branch_type == "specialized"]
    
    def suggest_fork_domain(self, capability_profile: List[str]) -> Optional[str]:
        """Fork domain taklif qilish"""
        if "code_execution" in capability_profile or "code_generation" in capability_profile:
            return "code"
        if "web_browsing" in capability_profile or "research" in str(capability_profile):
            return "research"
        if "autonomous" in str(capability_profile).lower():
            return "autonomous"
        return None
    
    def get_fork_statistics(self) -> Dict:
        return {
            "total_forks": len(self.forks),
            "total_branches": len(self.branches),
            "by_type": {
                "main": sum(1 for b in self.branches.values() if b.branch_type == "main"),
                "specialized": sum(1 for b in self.branches.values() if b.branch_type == "specialized"),
                "fork": sum(1 for b in self.branches.values() if b.branch_type == "fork")
            }
        }


class RollbackAnchorManager:
    """
    Rollback Anchor Manager
    """
    
    def __init__(self):
        self.anchors: Dict[str, Dict] = {}
        logger.info("⚓ Rollback Anchor Manager initialized")
    
    def create_anchor(self,
                     clone_id: str,
                     promoted_to: str,
                     parent_version: str,
                     config_state: Dict,
                     dependencies: List[str],
                     tool_manifest: List[str],
                     lineage: List[str]) -> str:
        """Rollback anchor yaratish"""
        anchor_id = f"anchor_{clone_id}_{int(time.time())}"
        
        anchor = {
            "anchor_id": anchor_id,
            "clone_id": clone_id,
            "promoted_to": promoted_to,
            "parent_version": parent_version,
            "config_state": config_state,
            "dependencies": dependencies,
            "tool_manifest": tool_manifest,
            "lineage": lineage,
            "recovery_instructions": f"Revert to {parent_version}, restore config and dependencies",
            "created_at": time.time()
        }
        
        self.anchors[anchor_id] = anchor
        logger.info(f"⚓ Rollback anchor created: {anchor_id}")
        
        return anchor_id
    
    def get_anchor(self, anchor_id: str) -> Optional[Dict]:
        return self.anchors.get(anchor_id)
    
    def get_anchors_for_clone(self, clone_id: str) -> List[Dict]:
        return [a for a in self.anchors.values() if a.get("clone_id") == clone_id]
    
    def get_latest_anchor(self, destination: str) -> Optional[Dict]:
        matching = [a for a in self.anchors.values() if a.get("promoted_to") == destination]
        if matching:
            return max(matching, key=lambda x: x.get("created_at", 0))
        return None
    
    def get_rollback_history(self, limit: int = 20) -> List[Dict]:
        anchors = list(self.anchors.values())
        anchors.sort(key=lambda x: x.get("created_at", 0), reverse=True)
        return anchors[:limit]


def create_fork_manager() -> ForkManager:
    return ForkManager()


def create_rollback_anchor_manager() -> RollbackAnchorManager:
    return RollbackAnchorManager()
