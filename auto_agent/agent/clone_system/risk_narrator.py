"""
================================================================================
4. RISK NARRATOR
================================================================================
Bu modul risklarni ochiq yozadi.

Risk Narrator quyidagilarni ochiq yozadi:
- qaysi regressiya ehtimoli bor
- qaysi modul high-risk
- qayerda coverage past
- qaysi testlar hali yo'q
- qaysi natija noaniq
- qaysi improvement faqat limited benchmark'da ishladi
- rollback osonmi qiyinmi

Qattiq qoida:
Report faqat yaxshi tomonni emas, salbiy tomonini ham chiqarishi shart.
================================================================================
"""
import os
import json
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from collections import defaultdict

from .reporting_types import RiskItem, ApprovalLevel

logger = logging.getLogger(__name__)


class RiskNarrator:
    """
    Risk Narrator - Risk hisoboti
    
    Bu modul barcha risklarni ochiq yozadi va
    ularni ochiq-oydin ko'rsatadi.
    """
    
    def __init__(self):
        # Risk categories
        self.risk_categories = {
            "regression": "Potential regression in existing functionality",
            "unknown": "Unknown or unverified behavior",
            "coverage": "Limited test coverage",
            "complexity": "Code complexity increase",
            "dependency": "Dependency changes",
            "performance": "Performance impact",
            "security": "Security implications",
            "rollback": "Rollback difficulty"
        }
        
        # High risk modules
        self.high_risk_modules = [
            "kernel", "core", "main", "security", "auth",
            "database", "migration", "deploy", "production"
        ]
        
        logger.info("⚠️ Risk Narrator initialized")
    
    def analyze_risks(self,
                     code_delta: Dict,
                     capability_delta: Dict,
                     metrics: List,
                     test_coverage: float = 0.5) -> List[RiskItem]:
        """
        Risklarni tahlil qilish
        
        Args:
            code_delta: Code delta
            capability_delta: Capability delta
            metrics: Metrikalar
            test_coverage: Test qamrovi (0-1)
        
        Returns:
            List[RiskItem]: Risklar ro'yxati
        """
        risks = []
        
        # 1. Regression risks
        if code_delta.get("files_changed"):
            risks.extend(self._check_regression_risk(code_delta))
        
        # 2. Coverage risks
        if test_coverage < 0.8:
            risks.append(RiskItem(
                risk_type="coverage",
                description=f"Test coverage is only {test_coverage*100:.0f}%",
                severity=ApprovalLevel.YELLOW if test_coverage > 0.5 else ApprovalLevel.RED,
                likelihood="high",
                affected_modules=code_delta.get("modules_affected", []),
                mitigation="Add more tests before approval"
            ))
        
        # 3. Unknown/uncertain metrics
        uncertain_metrics = [m for m in metrics if m.get("confidence") == "low"]
        if uncertain_metrics:
            risks.append(RiskItem(
                risk_type="unknown",
                description=f"{len(uncertain_metrics)} metrics have low confidence",
                severity=ApprovalLevel.YELLOW,
                likelihood="medium",
                affected_modules=[],
                mitigation="Run more benchmarks to increase confidence"
            ))
        
        # 4. Performance risks
        worsened_metrics = [m for m in metrics if m.get("improvement_percent", 0) < 0]
        if worsened_metrics:
            risks.append(RiskItem(
                risk_type="regression",
                description=f"{len(worsened_metrics)} metrics worsened",
                severity=ApprovalLevel.YELLOW,
                likelihood="high",
                affected_modules=[],
                mitigation="Fix regressions before approval"
            ))
        
        # 5. High-risk module modifications
        high_risk_touched = self._check_high_risk_modules(code_delta)
        if high_risk_touched:
            risks.append(RiskItem(
                risk_type="complexity",
                description=f"High-risk modules modified: {', '.join(high_risk_touched)}",
                severity=ApprovalLevel.RED,
                likelihood="medium",
                affected_modules=high_risk_touched,
                mitigation="Extra review required for these modules"
            ))
        
        # 6. Complexity risk
        if code_delta.get("files_created", []) or code_delta.get("lines_added", 0) > 500:
            risks.append(RiskItem(
                risk_type="complexity",
                description="Large amount of new code added",
                severity=ApprovalLevel.YELLOW,
                likelihood="medium",
                affected_modules=code_delta.get("modules_affected", []),
                mitigation="Break into smaller changes"
            ))
        
        # 7. Rollback difficulty
        rollback_easy = self._assess_rollback_ease(code_delta)
        if not rollback_easy:
            risks.append(RiskItem(
                risk_type="rollback",
                description="Rollback may be difficult",
                severity=ApprovalLevel.YELLOW,
                likelihood="medium",
                affected_modules=code_delta.get("modules_affected", []),
                mitigation="Document rollback steps clearly"
            ))
        
        logger.info(f"📋 Found {len(risks)} potential risks")
        
        return risks
    
    def _check_regression_risk(self, code_delta: Dict) -> List[RiskItem]:
        """Regression risk tekshirish"""
        risks = []
        
        files_changed = code_delta.get("files_changed", [])
        
        if files_changed:
            # Check for core files
            core_files = [f for f in files_changed if any(
                core in f.lower() for core in self.high_risk_modules
            )]
            
            if core_files:
                risks.append(RiskItem(
                    risk_type="regression",
                    description=f"Core files modified: {len(core_files)}",
                    severity=ApprovalLevel.RED,
                    likelihood="high",
                    affected_modules=core_files,
                    mitigation="Thorough regression testing required"
                ))
        
        return risks
    
    def _check_high_risk_modules(self, code_delta: Dict) -> List[str]:
        """High-risk modullarni tekshirish"""
        modules = code_delta.get("modules_affected", [])
        
        return [m for m in modules if any(
            risk in m.lower() for risk in self.high_risk_modules
        )]
    
    def _assess_rollback_ease(self, code_delta: Dict) -> bool:
        """Rollback osonligini baholash"""
        # Simple assessment
        files_created = len(code_delta.get("files_created", []))
        files_deleted = len(code_delta.get("files_deleted", []))
        files_changed = len(code_delta.get("files_changed", []))
        
        # If many new files and deletions, rollback is harder
        total_changes = files_created + files_deleted + files_changed
        
        return total_changes <= 5
    
    def generate_risk_summary(self, risks: List[RiskItem]) -> str:
        """Risk xulosasi"""
        if not risks:
            return "✅ No significant risks identified"
        
        # Group by severity
        red_risks = [r for r in risks if r.severity == ApprovalLevel.RED]
        yellow_risks = [r for r in risks if r.severity == ApprovalLevel.YELLOW]
        
        lines = []
        
        if red_risks:
            lines.append(f"🔴 HIGH RISKS ({len(red_risks)}):")
            for r in red_risks:
                lines.append(f"  - {r.description}")
        
        if yellow_risks:
            lines.append(f"🟡 MEDIUM RISKS ({len(yellow_risks)}):")
            for r in yellow_risks:
                lines.append(f"  - {r.description}")
        
        return "\n".join(lines)
    
    def get_approval_level(self, risks: List[RiskItem]) -> ApprovalLevel:
        """Approval level hisoblash"""
        if not risks:
            return ApprovalLevel.GREEN
        
        # Check for RED risks
        if any(r.severity == ApprovalLevel.RED for r in risks):
            return ApprovalLevel.RED
        
        # Check for YELLOW risks
        if any(r.severity == ApprovalLevel.YELLOW for r in risks):
            return ApprovalLevel.YELLOW
        
        return ApprovalLevel.GREEN


def create_risk_narrator() -> RiskNarrator:
    """Risk Narrator yaratish"""
    return RiskNarrator()
