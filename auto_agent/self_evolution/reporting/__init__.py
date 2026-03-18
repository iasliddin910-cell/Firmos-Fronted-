"""
Reporting Layer - Upgrade Dossier and Report Generation
=====================================================
Bu qatlam upgrade hisobotlarini yaratadi.
"""

import uuid
import logging
from datetime import datetime
from typing import Optional
from pathlib import Path

from ..data_contracts import (
    UpgradeDossier, UpgradeCandidate, CloneRun, EvaluationBundle
)

logger = logging.getLogger(__name__)


class DossierBuilder:
    """Dossier Builder - Upgrade hisoboti yaratish"""
    
    def __init__(self):
        self.dossiers: dict[str, UpgradeDossier] = {}
        logger.info("📄 DossierBuilder initialized")
    
    def build_dossier(
        self,
        candidate: UpgradeCandidate,
        clone: CloneRun,
        evaluation: EvaluationBundle
    ) -> UpgradeDossier:
        dossier_id = f"dossier_{str(uuid.uuid4())[:12]}"
        
        summary = f"""
Upgrade Candidate: {candidate.title}
Nimani o'zgartiradi: {candidate.why_now}
Baho: Trust Score: {evaluation.trust_score:.2f}
Tavsiya: {candidate.implementation_type} upgrade
        """.strip()
        
        capability_delta = {"added": clone.added_tools, "modified": clone.touched_modules}
        technical_delta = {"files_changed": len(clone.touched_modules)}
        
        risks = []
        if evaluation.trust_score < 0.7:
            risks.append({"type": "trust", "severity": "medium", "description": f"Trust score past: {evaluation.trust_score:.2f}"})
        
        regressions = [{"type": "test_failure", "description": r} for r in evaluation.regressions]
        
        recommendation = "APPROVE" if evaluation.trust_score >= 0.7 else "REVISE"
        decision_options = ["reject", "revise", "canary", "main"] if evaluation.trust_score >= 0.7 else ["reject", "revise"]
        
        rollback_plan = f"Rollback uchun {clone.clone_id} clone ni o'chiring"
        
        dossier = UpgradeDossier(
            id=dossier_id,
            candidate_id=candidate.id,
            clone_id=clone.clone_id,
            executive_summary=summary,
            capability_delta=capability_delta,
            technical_delta=technical_delta,
            risks=risks,
            regressions=regressions,
            recommendation=recommendation,
            decision_options=decision_options,
            rollback_plan=rollback_plan,
            trust_score=evaluation.trust_score,
            evaluation_bundle_id=evaluation.id
        )
        
        self.dossiers[dossier_id] = dossier
        logger.info(f"📄 Dossier built: {dossier_id}")
        
        return dossier
    
    def get_dossier(self, dossier_id: str) -> Optional[UpgradeDossier]:
        return self.dossiers.get(dossier_id)


class RiskNarrator:
    """Risk Narrator - Risk xikoyalar"""
    
    def __init__(self):
        logger.info("⚠️ RiskNarrator initialized")
    
    def narrate_risks(self, risks: list[dict], trust_score: float) -> str:
        if not risks:
            return "Xavflar aniqlanmadi."
        
        narration = f"Umumiy xavf bahosi: {trust_score:.2f}\n\nAniqlangan xavflar:\n"
        
        for i, risk in enumerate(risks, 1):
            emoji = "🔴" if risk.get("severity") == "high" else "🟡"
            narration += f"{i}. {emoji} {risk.get('type')}: {risk.get('description')}\n"
        
        return narration


class ReportingLayer:
    """Reporting Layer - To'liq reporting tizimi"""
    
    def __init__(self):
        self.dossier_builder = DossierBuilder()
        self.risk_narrator = RiskNarrator()
        logger.info("📋 ReportingLayer initialized")
    
    def create_full_report(
        self,
        candidate: UpgradeCandidate,
        clone: CloneRun,
        evaluation: EvaluationBundle
    ) -> dict:
        dossier = self.dossier_builder.build_dossier(candidate, clone, evaluation)
        risk_narration = self.risk_narrator.narrate_risks(dossier.risks, dossier.trust_score)
        
        report = {
            "dossier": dossier.to_dict(),
            "risk_narration": risk_narration,
            "generated_at": datetime.now().isoformat()
        }
        
        logger.info(f"📋 Full report created for {candidate.id}")
        return report
    
    def get_dossier(self, dossier_id: str) -> Optional[UpgradeDossier]:
        return self.dossier_builder.get_dossier(dossier_id)
    
    def get_stats(self) -> dict:
        return {"dossiers_created": len(self.dossier_builder.dossiers)}


def create_reporting_layer() -> ReportingLayer:
    return ReportingLayer()
