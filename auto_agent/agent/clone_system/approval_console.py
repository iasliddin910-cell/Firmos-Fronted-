"""
================================================================================
5. HUMAN APPROVAL CONSOLE
================================================================================
Bu yerda siz qaror qilasiz.

Sizda kamida quyidagi action'lar bo'lishi kerak:
- Reject
- Request revision
- Keep as experiment
- Approve for canary
- Approve for main
- Convert to new fork/model
================================================================================
"""
import os
import json
import logging
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

from .reporting_types import (
    ApprovalLevel, ApprovalAction, DecisionRecommendation,
    UpgradePassport, UpgradeDossier, TrustLevel
)

logger = logging.getLogger(__name__)


class HumanApprovalConsole:
    """
    Human Approval Console
    
    Bu yerda siz qaror qilasiz.
    6 ta asosiy action mavjud.
    """
    
    def __init__(self):
        # Approval history
        self.approvals: Dict[str, Dict] = {}
        
        # Pending approvals
        self.pending: List[str] = []
        
        logger.info("✅ Human Approval Console initialized")
    
    def create_dossier(self,
                     clone_id: str,
                     upgrade_title: str,
                     why_attempted: str,
                     code_delta: Dict,
                     capability_delta: Dict,
                     tool_delta: Dict,
                     metrics: List,
                     risks: List,
                     evidence: List,
                     baseline_metrics: Dict,
                     current_metrics: Dict) -> UpgradeDossier:
        """
        Upgrade Dossier yaratish
        
        Args:
            clone_id: Clone ID
            upgrade_title: Upgrade sarlavhasi
            why_attempted: Nima uchun
            code_delta: Code delta
            capability_delta: Capability delta
            tool_delta: Tool delta
            metrics: Metrikalar
            risks: Risklar
            evidence: Evidence
            baseline_metrics: Asl metrikalar
            current_metrics: Joriy metrikalar
        
        Returns:
            UpgradeDossier: To'liq dossier
        """
        dossier_id = f"dossier_{clone_id}_{int(time.time())}"
        
        from .reporting_types import CodeDelta, CapabilityDelta, ToolDelta, RiskItem
        
        # Convert to data classes
        code = CodeDelta(**code_delta) if code_delta else CodeDelta()
        capability = CapabilityDelta(**capability_delta) if capability_delta else CapabilityDelta()
        tool = ToolDelta(**tool_delta) if tool_delta else ToolDelta()
        
        # Calculate approval level
        from .risk_narrator import create_risk_narrator
        risk_narrator = create_risk_narrator()
        approval_level = risk_narrator.get_approval_level([
            RiskItem(
                risk_type=r.get("risk_type", ""),
                description=r.get("description", ""),
                severity=r.get("severity", ApprovalLevel.YELLOW),
                likelihood=r.get("likelihood", "medium")
            ) for r in risks
        ]) if risks else ApprovalLevel.GREEN
        
        # Generate recommendation
        recommendation = self._generate_recommendation(
            approval_level, metrics, risks
        )
        
        # Calculate trust score
        trust_score = self._calculate_trust_score(
            evidence, metrics, risks
        )
        
        # Build rollback plan
        rollback_plan = self._generate_rollback_plan(code_delta)
        
        dossier = UpgradeDossier(
            dossier_id=dossier_id,
            clone_id=clone_id,
            upgrade_title=upgrade_title,
            why_attempted=why_attempted,
            capability_delta=capability,
            code_delta=code,
            tool_delta=tool,
            evidence=evidence,
            risks=risks,
            metrics=metrics,
            recommendation=recommendation,
            approval_level=approval_level,
            trust_score=trust_score,
            rollback_plan=rollback_plan,
            rollback_easy=code.get("files_changed", []) <= 5 if code else True
        )
        
        # Add to pending
        self.pending.append(dossier_id)
        
        logger.info(f"📋 Dossier created: {dossier_id}")
        
        return dossier
    
    def process_approval(self,
                       dossier_id: str,
                       action: ApprovalAction,
                       approver_name: str,
                       comments: str = "") -> UpgradePassport:
        """
        Approval ni qayta ishlash
        
        Args:
            dossier_id: Dossier ID
            action: Approval action
            approver_name: Kim tasdiqladi
            comments: Izohlar
        
        Returns:
            UpgradePassport: Passport
        """
        # Create passport
        passport = UpgradePassport(
            passport_id=f"passport_{dossier_id}",
            clone_id=dossier_id.replace("dossier_", "").split("_")[0],
            upgrade_title=f"Upgrade {dossier_id}"
        )
        
        # Map action to decision
        action_map = {
            ApprovalAction.REJECT: DecisionRecommendation.REJECT,
            ApprovalAction.REQUEST_REVISION: DecisionRecommendation.REVISE,
            ApprovalAction.KEEP_AS_EXPERIMENT: DecisionRecommendation.FORK,
            ApprovalAction.APPROVE_FOR_CANARY: DecisionRecommendation.CANARY,
            ApprovalAction.APPROVE_FOR_MAIN: DecisionRecommendation.MAIN,
            ApprovalAction.CONVERT_TO_FORK: DecisionRecommendation.FORK
        }
        
        passport.approval_decision = action
        passport.approved_by = approver_name
        passport.approved_at = time.time()
        
        # Set deployment scope
        scope_map = {
            ApprovalAction.REJECT: "rejected",
            ApprovalAction.REQUEST_REVISION: "revision",
            ApprovalAction.KEEP_AS_EXPERIMENT: "experiment",
            ApprovalAction.APPROVE_FOR_CANARY: "canary",
            ApprovalAction.APPROVE_FOR_MAIN: "main",
            ApprovalAction.CONVERT_TO_FORK: "fork"
        }
        passport.deployment_scope = scope_map.get(action, "unknown")
        
        # Save approval
        self.approvals[dossier_id] = {
            "passport": passport.to_dict(),
            "action": action.value,
            "approver": approver_name,
            "comments": comments,
            "timestamp": time.time()
        }
        
        # Remove from pending
        if dossier_id in self.pending:
            self.pending.remove(dossier_id)
        
        logger.info(f"✅ Approval processed: {action.value} by {approver_name}")
        
        return passport
    
    def get_pending_approvals(self) -> List[Dict]:
        """Kutilayotgan approvallar"""
        return [
            {"dossier_id": pid, "status": "pending"}
            for pid in self.pending
        ]
    
    def get_approval_history(self, limit: int = 20) -> List[Dict]:
        """Approval tarixi"""
        history = list(self.approvals.values())
        
        # Sort by timestamp
        history.sort(key=lambda x: x.get("timestamp", 0), reverse=True)
        
        return history[:limit]
    
    def _generate_recommendation(self,
                              approval_level: ApprovalLevel,
                              metrics: List,
                              risks: List) -> DecisionRecommendation:
        """Recommendation generatsiya qilish"""
        # Default recommendation based on level
        if approval_level == ApprovalLevel.RED:
            return DecisionRecommendation.REJECT
        elif approval_level == ApprovalLevel.YELLOW:
            # Check if metrics are good
            improved = sum(1 for m in metrics if m.get("improvement_percent", 0) > 0)
            if improved > len(metrics) / 2:
                return DecisionRecommendation.CANARY
            return DecisionRecommendation.REVISE
        else:
            # GREEN - can go to main
            return DecisionRecommendation.MAIN
    
    def _calculate_trust_score(self,
                              evidence: List,
                              metrics: List,
                              risks: List) -> TrustLevel:
        """Trust score hisoblash"""
        score = 1.0
        
        # Evidence completeness
        if len(evidence) >= 5:
            score += 0.3
        elif len(evidence) >= 3:
            score += 0.1
        
        # Metrics confidence
        high_confidence = sum(1 for m in metrics if m.get("confidence") == "high")
        if high_confidence > len(metrics) / 2:
            score += 0.3
        elif high_confidence > 0:
            score += 0.1
        
        # Risk assessment
        red_risks = sum(1 for r in risks if r.get("severity") == "red")
        if red_risks > 0:
            score -= 0.4
        elif len(risks) > 3:
            score -= 0.2
        
        # Map to level
        if score >= 0.8:
            return TrustLevel.HIGH
        elif score >= 0.5:
            return TrustLevel.MEDIUM
        else:
            return TrustLevel.LOW
    
    def _generate_rollback_plan(self, code_delta: Dict) -> str:
        """Rollback plan generatsiya qilish"""
        files_changed = code_delta.get("files_changed", [])
        files_created = code_delta.get("files_created", [])
        
        plan = []
        
        if files_changed:
            plan.append(f"1. Revert changed files: {', '.join(files_changed[:3])}")
        
        if files_created:
            plan.append(f"2. Delete new files: {', '.join(files_created[:3])}")
        
        if not plan:
            return "No rollback needed - no changes"
        
        return "\n".join(plan)


def create_human_approval_console() -> HumanApprovalConsole:
    """Human Approval Console yaratish"""
    return HumanApprovalConsole()
