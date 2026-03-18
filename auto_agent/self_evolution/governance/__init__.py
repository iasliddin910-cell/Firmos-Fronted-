"""
Governance Layer - Approval Console and Decision Making
"""

import uuid
import logging
from datetime import datetime, timedelta
from typing import Optional

from ..data_contracts import (
    ApprovalRequest, ApprovalDecision, DestinationType, UpgradeDossier
)

logger = logging.getLogger(__name__)


class ApprovalConsole:
    """Approval Console - Approval boshqaruvi"""
    
    def __init__(self):
        self.approval_requests: dict[str, ApprovalRequest] = {}
        logger.info("✅ ApprovalConsole initialized")
    
    def create_approval_request(
        self,
        dossier_id: str,
        candidate_id: str,
        expires_in_hours: int = 24
    ) -> ApprovalRequest:
        request_id = f"approval_{str(uuid.uuid4())[:12]}"
        expires_at = datetime.now() + timedelta(hours=expires_in_hours)
        
        request = ApprovalRequest(
            id=request_id,
            dossier_id=dossier_id,
            candidate_id=candidate_id,
            expires_at=expires_at
        )
        
        self.approval_requests[request_id] = request
        logger.info(f"✅ Approval request created: {request_id}")
        return request
    
    def approve_request(
        self,
        request_id: str,
        decision: ApprovalDecision,
        destination: Optional[DestinationType] = None,
        reason: str = "",
        approved_by: str = "human"
    ) -> bool:
        request = self.approval_requests.get(request_id)
        if not request:
            return False
        
        request.decision = decision
        request.decision_reason = reason
        request.decided_by = approved_by
        request.decided_at = datetime.now()
        
        if decision == ApprovalDecision.APPROVED and destination:
            request.destination = destination
        
        logger.info(f"✅ Request {request_id}: {decision.value}")
        return True
    
    def get_pending_requests(self) -> list[ApprovalRequest]:
        now = datetime.now()
        return [r for r in self.approval_requests.values() if r.decision is None]
    
    def get_stats(self) -> dict:
        return {"total": len(self.approval_requests), "pending": len(self.get_pending_requests())}


class DecisionEngine:
    """Decision Engine - Avtomatik qaror qabul qilish"""
    
    def __init__(self):
        logger.info("🧠 DecisionEngine initialized")
    
    def analyze_dossier(self, dossier: UpgradeDossier) -> dict:
        analysis = {"recommended_decision": None, "confidence": 0.0, "reasoning": []}
        
        if dossier.trust_score >= 0.85:
            analysis["recommended_decision"] = "main"
            analysis["confidence"] = 0.9
        elif dossier.trust_score >= 0.70:
            analysis["recommended_decision"] = "canary"
            analysis["confidence"] = 0.7
        elif dossier.trust_score >= 0.50:
            analysis["recommended_decision"] = "revise"
            analysis["confidence"] = 0.5
        else:
            analysis["recommended_decision"] = "reject"
            analysis["confidence"] = 0.8
        
        return analysis


class GovernanceLayer:
    """Governance Layer - To'liq governance tizimi"""
    
    def __init__(self):
        self.approval_console = ApprovalConsole()
        self.decision_engine = DecisionEngine()
        logger.info("🏛️ GovernanceLayer initialized")
    
    def submit_for_approval(self, dossier: UpgradeDossier) -> ApprovalRequest:
        return self.approval_console.create_approval_request(dossier.id, dossier.candidate_id)
    
    def get_ai_recommendation(self, dossier: UpgradeDossier) -> dict:
        return self.decision_engine.analyze_dossier(dossier)
    
    def get_pending_count(self) -> int:
        return len(self.approval_console.get_pending_requests())


def create_governance_layer() -> GovernanceLayer:
    return GovernanceLayer()
