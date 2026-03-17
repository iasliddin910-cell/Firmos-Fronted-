"""
================================================================================
REPORTING & APPROVAL SYSTEM - UPGRADE REPORTING + HUMAN APPROVAL
================================================================================
Bu bo'lim:

Maqsad:
- improvement'ni tushunarli qilish
- isbotlash
- riskni ochiq ko'rsatish
- yakuniy qarorni sizga berish

Asosiy prinsip:
"No silent upgrades. No unverifiable claims. No auto-promotion without evidence."

6 ta asosiy modul:
1. Report Aggregator - Artifact yig'ish
2. Delta Analyzer - O'zgarish tahlili
3. Benchmark Comparison Engine - Benchmark taqqoslash
4. Before/After Playback Engine - Real farqni ko'rsatish
5. Risk Narrator - Risk hisoboti
6. Human Approval Console - Human Approval
================================================================================
"""
import os
import sys
import json
import logging
import time
import hashlib
from typing import Dict, List, Optional, Any, Callable, Set, Union
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from collections import defaultdict
from pathlib import Path
from enum import Enum
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


# ================================================================================
# ENUMS - Approval va Report uchun
# ================================================================================

class ApprovalLevel(Enum):
    """Approval darajalari"""
    GREEN = "green"   # Past risk - tez approve
    YELLOW = "yellow" # O'rta risk - ko'proq review
    RED = "red"       # Yuqori risk - to'liq audit


class ApprovalAction(Enum):
    """Human Approval Actions"""
    REJECT = "reject"
    REQUEST_REVISION = "request_revision"
    KEEP_AS_EXPERIMENT = "keep_as_experiment"
    APPROVE_FOR_CANARY = "approve_for_canary"
    APPROVE_FOR_MAIN = "approve_for_main"
    CONVERT_TO_FORK = "convert_to_fork"


class DecisionRecommendation(Enum):
    """Decision recommendation"""
    REJECT = "reject"
    REVISE = "revise"
    CANARY = "canary"
    MAIN = "main"
    FORK = "fork"


class TrustLevel(Enum):
    """Trust score darajalari"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ReportLevel(Enum):
    """Report darajalari"""
    SIMPLE = "simple"        # Qisqa summary
    TECHNICAL = "technical"  # Texnik review
    FULL_AUDIT = "full_audit"  # To'liq audit


# ================================================================================
# DATA CLASSES
# ================================================================================

@dataclass
class CodeDelta:
    """Code delta - qaysi fayllar o'zgardi"""
    files_changed: List[str] = field(default_factory=list)
    files_created: List[str] = field(default_factory=list)
    files_deleted: List[str] = field(default_factory=list)
    lines_added: int = 0
    lines_removed: int = 0
    modules_affected: List[str] = field(default_factory=list)


@dataclass
class CapabilityDelta:
    """Capability delta - qaysi ability o'zgardi"""
    capabilities_gained: List[str] = field(default_factory=list)
    capabilities_strengthened: List[str] = field(default_factory=list)
    capabilities_weakened: List[str] = field(default_factory=list)
    new_abilities: List[str] = field(default_factory=list)


@dataclass
class ToolDelta:
    """Tool delta"""
    tools_added: List[str] = field(default_factory=list)
    tools_modified: List[str] = field(default_factory=list)
    tools_removed: List[str] = field(default_factory=list)
    tool_policies_changed: List[str] = field(default_factory=list)


@dataclass
class BehaviorDelta:
    """Behavior delta - amaldagi farq"""
    behavior_changes: List[Dict] = field(default_factory=list)
    before_metrics: Dict = field(default_factory=dict)
    after_metrics: Dict = field(default_factory=dict)


@dataclass
class MetricsImpact:
    """Metrics ta'siri"""
    metric_name: str
    before_value: float
    after_value: float
    improvement_percent: float
    confidence: TrustLevel = TrustLevel.HIGH


@dataclass
class RiskItem:
    """Risk item"""
    risk_type: str
    description: str
    severity: ApprovalLevel
    likelihood: str  # high, medium, low
    affected_modules: List[str] = field(default_factory=list)
    mitigation: str = ""


@dataclass
class EvidenceItem:
    """Evidence item"""
    evidence_type: str  # benchmark, replay, log, screenshot
    artifact_id: str
    description: str
    hash: str = ""
    available: bool = True


@dataclass
class UpgradePassport:
    """Upgrade Passport - har approved clone uchun"""
    passport_id: str
    clone_id: str
    upgrade_title: str
    
    # Lineage
    parent_lineage: List[str] = field(default_factory=list)
    
    # O'zgarishlar
    what_changed: List[str] = field(default_factory=list)
    why_changed: str = ""
    
    # Metrikalar
    metrics_delta: List[MetricsImpact] = field(default_factory=list)
    
    # Risk
    risk_level: ApprovalLevel = ApprovalLevel.GREEN
    trust_score: TrustLevel = TrustLevel.HIGH
    
    # Rollback
    rollback_recipe: str = ""
    
    # Approval
    approval_decision: ApprovalAction = ApprovalAction.REJECT
    approved_by: str = ""
    approved_at: float = 0
    
    # Deployment
    deployment_scope: str = ""  # canary, main, experiment, fork
    
    def to_dict(self) -> Dict:
        return {
            "passport_id": self.passport_id,
            "clone_id": self.clone_id,
            "upgrade_title": self.upgrade_title,
            "parent_lineage": self.parent_lineage,
            "what_changed": self.what_changed,
            "why_changed": self.why_changed,
            "metrics_delta": [
                {
                    "metric_name": m.metric_name,
                    "before_value": m.before_value,
                    "after_value": m.after_value,
                    "improvement_percent": m.improvement_percent,
                    "confidence": m.confidence.value
                }
                for m in self.metrics_delta
            ],
            "risk_level": self.risk_level.value,
            "trust_score": self.trust_score.value,
            "rollback_recipe": self.rollback_recipe,
            "approval_decision": self.approval_decision.value,
            "approved_by": self.approved_by,
            "approved_at": self.approved_at,
            "deployment_scope": self.deployment_scope
        }


@dataclass
class UpgradeDossier:
    """
    Upgrade Dossier - To'liq upgrade hisoboti
    
    6 qatlamli struktura:
    1. Executive Summary
    2. Capability Delta
    3. Technical Delta
    4. Evidence Bundle
    5. Risk + Rollback View
    6. Decision Actions
    """
    dossier_id: str
    clone_id: str
    created_at: float = field(default_factory=time.time)
    
    # 1. Executive Summary
    upgrade_title: str = ""
    why_attempted: str = ""
    
    # 2. Capability Delta
    capability_delta: Optional[CapabilityDelta] = None
    
    # 3. Technical Delta
    code_delta: Optional[CodeDelta] = None
    tool_delta: Optional[ToolDelta] = None
    
    # 4. Evidence Bundle
    evidence: List[EvidenceItem] = field(default_factory=list)
    
    # 5. Risk + Rollback View
    risks: List[RiskItem] = field(default_factory=list)
    rollback_plan: str = ""
    rollback_easy: bool = True
    
    # 6. Metrics
    metrics: List[MetricsImpact] = field(default_factory=list)
    
    # 7. Recommendation
    recommendation: DecisionRecommendation = DecisionRecommendation.CANARY
    recommendation_reason: str = ""
    
    # 8. Trust Score
    trust_score: TrustLevel = TrustLevel.HIGH
    trust_factors: Dict = field(default_factory=dict)
    
    # Metadata
    approval_level: ApprovalLevel = ApprovalLevel.GREEN
    report_level: ReportLevel = ReportLevel.SIMPLE
    
    def to_dict(self, level: ReportLevel = ReportLevel.SIMPLE) -> Dict:
        """Report darajasiga qarab chiqarish"""
        result = {
            "dossier_id": self.dossier_id,
            "clone_id": self.clone_id,
            "created_at": self.created_at,
            "approval_level": self.approval_level.value,
            "trust_score": self.trust_score.value
        }
        
        # Simple Summary
        if level in [ReportLevel.SIMPLE, ReportLevel.TECHNICAL, ReportLevel.FULL_AUDIT]:
            result["summary"] = {
                "upgrade_title": self.upgrade_title,
                "why_attempted": self.why_attempted,
                "recommendation": self.recommendation.value,
                "risk_level": self.approval_level.value
            }
            
            # Metrics summary
            if self.metrics:
                improved = [m for m in self.metrics if m.improvement_percent > 0]
                worsened = [m for m in self.metrics if m.improvement_percent < 0]
                result["metrics_summary"] = {
                    "improved_count": len(improved),
                    "worsened_count": len(worsened),
                    "top_improvements": [
                        {"name": m.metric_name, "change": f"+{m.improvement_percent:.1f}%"}
                        for m in sorted(improved, key=lambda x: x.improvement_percent, reverse=True)[:3]
                    ]
                }
            
            # Risks summary
            if self.risks:
                high_risks = [r for r in self.risks if r.severity == ApprovalLevel.RED]
                result["risks_summary"] = {
                    "total": len(self.risks),
                    "high_risk": len(high_risks),
                    "main_risks": [r.description for r in high_risks[:3]]
                }
        
        # Technical Review
        if level in [ReportLevel.TECHNICAL, ReportLevel.FULL_AUDIT]:
            result["technical"] = {
                "code_delta": asdict(self.code_delta) if self.code_delta else {},
                "tool_delta": asdict(self.tool_delta) if self.tool_delta else {},
                "capability_delta": asdict(self.capability_delta) if self.capability_delta else {},
                "rollback_plan": self.rollback_plan,
                "rollback_easy": self.rollback_easy
            }
            
            result["evidence"] = [
                {
                    "type": e.evidence_type,
                    "description": e.description,
                    "available": e.available
                }
                for e in self.evidence
            ]
        
        # Full Audit
        if level == ReportLevel.FULL_AUDIT:
            result["full_audit"] = {
                "all_metrics": [
                    {
                        "metric_name": m.metric_name,
                        "before": m.before_value,
                        "after": m.after_value,
                        "change": m.improvement_percent,
                        "confidence": m.confidence.value
                    }
                    for m in self.metrics
                ],
                "all_risks": [asdict(r) for r in self.risks],
                "trust_factors": self.trust_factors,
                "recommendation_reason": self.recommendation_reason
            }
        
        return result
    
    def get_simple_summary(self) -> str:
        """Qisqa summary matni"""
        improved = sum(1 for m in self.metrics if m.improvement_percent > 0)
        worsened = sum(1 for m in self.metrics if m.improvement_percent < 0)
        
        summary = f"""
🎯 **{self.upgrade_title}**

📋 {self.why_attempted}

📊 Metrikalar:
   ✅ Yaxshilandi: {improved} ta
   ❌ Yomonlashdi: {worsened} ta

⚠️ Risk: {self.approval_level.value.upper()}
📈 Trust: {self.trust_score.value.upper()}

💡 Tavsiya: {self.recommendation.value.upper()}
"""
        return summary


# ================================================================================
# EXPORTS
# ================================================================================

__all__ = [
    # Enums
    "ApprovalLevel",
    "ApprovalAction",
    "DecisionRecommendation",
    "TrustLevel",
    "ReportLevel",
    # Data Classes
    "CodeDelta",
    "CapabilityDelta",
    "ToolDelta",
    "BehaviorDelta",
    "MetricsImpact",
    "RiskItem",
    "EvidenceItem",
    "UpgradePassport",
    "UpgradeDossier",
]
