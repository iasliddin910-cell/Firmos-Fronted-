"""
================================================================================
PROMOTION / FORK / NEW-MODEL DECISION SYSTEM
================================================================================
Bu bo'lim oldingi uchalasining yakuniy hukm nuqtasi.

Maqsad:
- approved upgrade'ni qayerga yuborishni tanlash
- main'ga merge qilish-qilmaslikni hal qilish
- canary yoki experiment sifatida ushlab turish
- kerak bo'lsa yangi fork/model yaratish
- rollback nuqtalarini saqlash
- lineage daraxtini yangilash

Asosiy prinsip:
"Every upgrade must have a destination policy"

6 ta asosiy yo'l:
1. Reject
2. Archive as Experiment
3. Canary Deployment
4. Promote to Main
5. Specialized Branch
6. Create New Fork/Model
================================================================================
"""
import os
import json
import logging
import time
import hashlib
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from collections import defaultdict

logger = logging.getLogger(__name__)


# ================================================================================
# ENUMS
# ================================================================================

class DestinationType(Enum):
    """Destination turlari"""
    REJECT = "reject"
    ARCHIVE_EXPERIMENT = "archive_experiment"
    CANARY = "canary"
    MAIN = "main"
    SPECIALIZED_BRANCH = "specialized_branch"
    NEW_FORK = "new_fork"


class BranchStatus(Enum):
    """Branch holatlari"""
    ACTIVE = "active"
    CANARY = "canary"
    STABLE = "stable"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


class MergePolicy(Enum):
    """Merge siyosati"""
    ONE_WAY = "one_way"           # Faqat oladi, qaytarmaydi
    BIDIRECTIONAL = "bidirectional"  # Ikkala tomonga merge mumkin
    PERIODIC_REBASE = "periodic_rebase"  # Main dan oladi, qaytarmaydi
    INDEPENDENT = "independent"    # Butunlay mustaqil


class DecisionResult(Enum):
    """Qaror natijasi"""
    REJECT = "reject"
    EXPERIMENT = "experiment"
    CANARY = "canary"
    MAIN = "main"
    BRANCH = "branch"
    FORK = "fork"


# ================================================================================
# DATA CLASSES
# ================================================================================

@dataclass
class DecisionScore:
    """Decision uchun scores"""
    utility_score: float = 0.0         # Qanchalik foydali (0-1)
    generality_score: float = 0.0       # Umumiylik (0-1)
    risk_score: float = 0.0            # Xavf (0-1)
    reversibility_score: float = 0.0    # Qaytarilish osonligi (0-1)
    trust_score: float = 0.0           # Ishonchlilik (0-1)
    divergence_score: float = 0.0       # Originaldan uzoqlashish (0-1)
    
    # Hisoblangan
    final_recommendation: Optional[DestinationType] = None
    
    def to_dict(self) -> Dict:
        return {
            "utility_score": self.utility_score,
            "generality_score": self.generality_score,
            "risk_score": self.risk_score,
            "reversibility_score": self.reversibility_score,
            "trust_score": self.trust_score,
            "divergence_score": self.divergence_score,
            "final_recommendation": self.final_recommendation.value if self.final_recommendation else None
        }


@dataclass
class PromotionResult:
    """Promotion natijasi"""
    success: bool
    destination: DestinationType
    destination_path: str = ""
    promotion_id: str = ""
    rollback_anchor_id: str = ""
    message: str = ""
    timestamp: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict:
        return {
            "success": self.success,
            "destination": self.destination.value,
            "destination_path": self.destination_path,
            "promotion_id": self.promotion_id,
            "rollback_anchor_id": self.rollback_anchor_id,
            "message": self.message,
            "timestamp": self.timestamp
        }


@dataclass
class BranchInfo:
    """Branch ma'lumotlari"""
    branch_id: str
    name: str
    branch_type: str  # main, canary, specialized, fork
    status: BranchStatus = BranchStatus.ACTIVE
    
    # Parent
    parent_branch: Optional[str] = None
    
    # Maqsad va scope
    intended_domain: str = ""
    capability_profile: List[str] = field(default_factory=list)
    
    # Constitution
    constitution: Dict = field(default_factory=dict)
    
    # Merge policy
    merge_policy: MergePolicy = MergePolicy.ONE_WAY
    
    # Metrics
    total_promotions: int = 0
    stable_promotions: int = 0
    rolled_back: int = 0
    
    # Vaqt
    created_at: float = field(default_factory=time.time)
    last_promotion_at: float = 0
    
    def to_dict(self) -> Dict:
        return {
            "branch_id": self.branch_id,
            "name": self.name,
            "branch_type": self.branch_type,
            "status": self.status.value,
            "parent_branch": self.parent_branch,
            "intended_domain": self.intended_domain,
            "capability_profile": self.capability_profile,
            "constitution": self.constitution,
            "merge_policy": self.merge_policy.value,
            "total_promotions": self.total_promotions,
            "stable_promotions": self.stable_promotions,
            "rolled_back": self.rolled_back,
            "created_at": self.created_at,
            "last_promotion_at": self.last_promotion_at
        }


@dataclass
class RollbackAnchor:
    """Rollback Anchor"""
    anchor_id: str
    clone_id: str
    promoted_to: DestinationType
    
    # Exact state
    parent_version: str = ""
    config_state: Dict = field(default_factory=dict)
    dependency_fingerprint: str = ""
    tool_manifest: List[str] = field(default_factory=list)
    
    # Recovery
    migration_info: str = ""
    recovery_instructions: str = ""
    lineage_pointer: str = ""
    
    # Vaqt
    created_at: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict:
        return {
            "anchor_id": self.anchor_id,
            "clone_id": self.clone_id,
            "promoted_to": self.promoted_to.value,
            "parent_version": self.parent_version,
            "config_state": self.config_state,
            "dependency_fingerprint": self.dependency_fingerprint,
            "tool_manifest": self.tool_manifest,
            "migration_info": self.migration_info,
            "recovery_instructions": self.recovery_instructions,
            "lineage_pointer": self.lineage_pointer,
            "created_at": self.created_at
        }


@dataclass
class ForkSpec:
    """Fork spetsifikatsiyasi"""
    fork_id: str
    parent_branch: str
    
    # Identity
    name: str
    intended_domain: str
    description: str
    
    # Profile
    capability_profile: List[str] = field(default_factory=list)
    inherited_components: List[str] = field(default_factory=list)
    diverging_configs: Dict = field(default_factory=dict)
    
    # Update policy
    update_policy: str = "periodic"  # periodic, independent, one-way
    
    # Evaluation
    evaluation_profile: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "fork_id": self.fork_id,
            "parent_branch": self.parent_branch,
            "name": self.name,
            "intended_domain": self.intended_domain,
            "description": self.description,
            "capability_profile": self.capability_profile,
            "inherited_components": self.inherited_components,
            "diverging_configs": self.diverging_configs,
            "update_policy": self.update_policy,
            "evaluation_profile": self.evaluation_profile
        }


# ================================================================================
# DECISION ENGINE
# ================================================================================

class DecisionEngine:
    """
    Decision Engine
    
    Yakuniy tavsiya beradi:
    - utility_score
    - generality_score
    - risk_score
    - reversibility_score
    - trust_score
    - divergence_score
    """
    
    def __init__(self):
        logger.info("🎯 Decision Engine initialized")
    
    def analyze(self,
              dossier: Dict,
              approval_level: str = "green") -> DecisionScore:
        """
        Decision tahlil
        
        Args:
            dossier: UpgradeDossier
            approval_level: Approval darajasi
        
        Returns:
            DecisionScore
        """
        score = DecisionScore()
        
        # 1. Utility Score
        score.utility_score = self._calculate_utility(dossier)
        
        # 2. Generality Score
        score.generality_score = self._calculate_generality(dossier)
        
        # 3. Risk Score
        score.risk_score = self._calculate_risk(dossier, approval_level)
        
        # 4. Reversibility Score
        score.reversibility_score = self._calculate_reversibility(dossier)
        
        # 5. Trust Score
        score.trust_score = self._calculate_trust(dossier)
        
        # 6. Divergence Score
        score.divergence_score = self._calculate_divergence(dossier)
        
        # Final recommendation
        score.final_recommendation = self._make_recommendation(score)
        
        logger.info(f"🎯 Decision: {score.final_recommendation.value if score.final_recommendation else 'unknown'}")
        
        return score
    
    def _calculate_utility(self, dossier: Dict) -> float:
        """Utility hisoblash"""
        metrics = dossier.get("metrics", [])
        
        if not metrics:
            return 0.5
        
        # Calculate average improvement
        improvements = []
        for m in metrics:
            improvement = m.get("improvement_percent", 0)
            improvements.append(improvement)
        
        if not improvements:
            return 0.5
        
        avg_improvement = sum(improvements) / len(improvements)
        
        # Normalize to 0-1 (improvement can be negative)
        # Assume -50% to +50% is the range
        utility = (avg_improvement + 50) / 100
        
        return max(0.0, min(1.0, utility))
    
    def _calculate_generality(self, dossier: Dict) -> float:
        """Generality hisoblash"""
        # Check capability delta
        capability = dossier.get("capability_delta", {})
        
        # More general capabilities = higher score
        general_caps = ["memory", "planning", "learning", "benchmarking"]
        specific_caps = ["browser", "code_execution", "tool_creation"]
        
        gained = capability.get("capabilities_gained", [])
        
        general_count = sum(1 for cap in gained if cap in general_caps)
        specific_count = sum(1 for cap in gained if cap in specific_caps)
        
        if general_count + specific_count == 0:
            return 0.5
        
        return general_count / (general_count + specific_count + 1)
    
    def _calculate_risk(self, dossier: Dict, approval_level: str) -> float:
        """Risk hisoblash"""
        risks = dossier.get("risks", [])
        
        if not risks:
            return 0.2
        
        # High risk = high score (0-1)
        red_risks = sum(1 for r in risks if r.get("severity") == "red")
        yellow_risks = sum(1 for r in risks if r.get("severity") == "yellow")
        
        risk_score = (red_risks * 0.5 + yellow_risks * 0.2) / (len(risks) + 1)
        
        return min(1.0, risk_score)
    
    def _calculate_reversibility(self, dossier: Dict) -> float:
        """Reversibility hisoblash"""
        # Simple assessment based on code changes
        code = dossier.get("code_delta", {})
        
        files_changed = len(code.get("files_changed", []))
        files_created = len(code.get("files_created", []))
        files_deleted = len(code.get("files_deleted", []))
        
        total_changes = files_changed + files_created + files_deleted
        
        # Fewer changes = easier to reverse
        if total_changes <= 3:
            return 0.9
        elif total_changes <= 10:
            return 0.6
        else:
            return 0.3
    
    def _calculate_trust(self, dossier: Dict) -> float:
        """Trust hisoblash"""
        trust = dossier.get("trust_score", "medium")
        
        trust_map = {
            "high": 0.9,
            "medium": 0.6,
            "low": 0.3
        }
        
        return trust_map.get(trust, 0.5)
    
    def _calculate_divergence(self, dossier: Dict) -> float:
        """Divergence hisoblash"""
        # Check how different this is from original
        code = dossier.get("code_delta", {})
        
        lines_added = code.get("lines_added", 0)
        lines_removed = code.get("lines_removed", 0)
        
        total_diff = lines_added + lines_removed
        
        # More changes = more divergence
        if total_diff < 50:
            return 0.2
        elif total_diff < 200:
            return 0.5
        else:
            return 0.8
    
    def _make_recommendation(self, score: DecisionScore) -> DestinationType:
        """Recommendation generatsiya"""
        # Formula:
        # - utility high + generality high + risk low -> main
        # - utility high + generality medium + risk medium -> canary
        # - utility high + generality low + divergence high -> fork/model
        # - utility medium + trust low -> experiment
        # - utility low -> reject
        
        u, g, r, rev, t, d = (
            score.utility_score,
            score.generality_score,
            score.risk_score,
            score.reversibility_score,
            score.trust_score,
            score.divergence_score
        )
        
        # Main: high utility, high generality, low risk
        if u > 0.7 and g > 0.6 and r < 0.3:
            return DestinationType.MAIN
        
        # Canary: good utility, some generality, moderate risk
        if u > 0.5 and g > 0.4 and r < 0.6:
            return DestinationType.CANARY
        
        # Fork: high utility but low generality and high divergence
        if u > 0.6 and g < 0.4 and d > 0.6:
            return DestinationType.NEW_FORK
        
        # Specialized branch
        if u > 0.5 and d > 0.4:
            return DestinationType.SPECIALIZED_BRANCH
        
        # Experiment: medium utility, low trust
        if u > 0.3 and t < 0.5:
            return DestinationType.ARCHIVE_EXPERIMENT
        
        # Reject
        return DestinationType.REJECT


def create_decision_engine() -> DecisionEngine:
    """Decision Engine yaratish"""
    return DecisionEngine()
