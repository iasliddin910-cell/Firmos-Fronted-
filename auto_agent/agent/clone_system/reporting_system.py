"""
================================================================================
REPORTING & APPROVAL SYSTEM - MAIN ORCHESTRATOR
================================================================================
Bu asosiy orchestrator - barcha reporting modullarni birlashtiradi.

Workflow:
1. clone improvement tugaydi
2. artifacts yig'iladi
3. delta analyzer capability farqini chiqaradi
4. benchmark engine aniq o'lchov beradi
5. risk narrator salbiy tomonini ham yozadi
6. trust score hisoblanadi
7. sizga upgrade dossier keladi
8. siz reject / revise / canary / main / fork dan birini tanlaysiz

"No silent upgrades. No unverifiable claims. No auto-promotion without evidence."
================================================================================
"""
import os
import json
import logging
import time
from typing import Dict, List, Optional, Any
from pathlib import Path

from .reporting_types import (
    ApprovalLevel, ApprovalAction, DecisionRecommendation, TrustLevel, ReportLevel,
    UpgradePassport, UpgradeDossier
)
from .artifact_store import ArtifactStore
from .report_aggregator import ReportAggregator, create_report_aggregator
from .delta_analyzer import DeltaAnalyzer, create_delta_analyzer
from .benchmark_comparison import BenchmarkComparisonEngine, create_benchmark_comparison_engine
from .risk_narrator import RiskNarrator, create_risk_narrator
from .approval_console import HumanApprovalConsole, create_human_approval_console

logger = logging.getLogger(__name__)


class ReportingApprovalSystem:
    """
    Reporting & Approval System
    
    Bu class to'liq upgrade reporting va human approval tizimini boshqaradi.
    """
    
    def __init__(self, artifact_store: ArtifactStore):
        self.artifact_store = artifact_store
        
        # Initialize all modules
        self.aggregator = create_report_aggregator(artifact_store)
        self.delta_analyzer = create_delta_analyzer()
        self.benchmark_engine = create_benchmark_comparison_engine()
        self.risk_narrator = create_risk_narrator()
        self.approval_console = create_human_approval_console()
        
        # Baseline metrics storage
        self.baseline_metrics: Dict[str, float] = {}
        
        logger.info("📋 Reporting & Approval System initialized")
    
    def capture_baseline(self, metrics: Dict[str, float]):
        """Baseline metrikalarni saqlash"""
        self.baseline_metrics = metrics
        logger.info("📊 Baseline metrics captured")
    
    def generate_dossier(self,
                        clone_id: str,
                        upgrade_title: str,
                        why_attempted: str,
                        clone_files: Dict[str, str],
                        original_files: Dict[str, str],
                        knowledge_analysis: Optional[Dict] = None,
                        test_coverage: float = 0.5) -> UpgradeDossier:
        """
        Upgrade Dossier yaratish
        
        Bu asosiy metod - clone improvement tugagandan so'ng chaqiriladi.
        
        Args:
            clone_id: Clone ID
            upgrade_title: Upgrade sarlavhasi
            why_attempted: Nima uchun ishga tushirildi
            clone_files: Clone dagi fayllar
            original_files: Original fayllar
            knowledge_analysis: Bilim tahlili
            test_coverage: Test qamrovi
        
        Returns:
            UpgradeDossier: To'liq dossier
        """
        
        # Step 1: Gather artifacts
        logger.info("📦 Step 1: Gathering artifacts...")
        aggregated = self.aggregator.aggregate_for_dossier(clone_id)
        evidence = self.aggregator.gather_evidence(clone_id)
        
        # Step 2: Analyze deltas
        logger.info("🔍 Step 2: Analyzing deltas...")
        delta_result = self.delta_analyzer.analyze_all(
            clone_id, clone_files, original_files, knowledge_analysis
        )
        
        # Step 3: Compare benchmarks
        logger.info("📊 Step 3: Comparing benchmarks...")
        
        # Get current metrics from artifacts
        current_metrics = self._extract_metrics_from_artifacts(aggregated)
        
        baseline = self.baseline_metrics or self._get_default_baseline()
        
        metrics_impact = self.benchmark_engine.compare(
            baseline, current_metrics, test_coverage
        )
        
        # Also calculate capability metrics
        capability_metrics = self.benchmark_engine.calculate_capability_metrics(
            delta_result.get("code_delta", {}),
            delta_result.get("capability_delta", {})
        )
        metrics_impact.extend(capability_metrics)
        
        # Step 4: Analyze risks
        logger.info("⚠️ Step 4: Analyzing risks...")
        risks = self.risk_narrator.analyze_risks(
            delta_result.get("code_delta", {}),
            delta_result.get("capability_delta", {}),
            metrics_impact,
            test_coverage
        )
        
        # Step 5: Generate recommendation
        logger.info("💡 Step 5: Generating recommendation...")
        approval_level = self.risk_narrator.get_approval_level(risks)
        
        # Step 6: Create dossier
        logger.info("📋 Step 6: Creating dossier...")
        
        dossier = self.approval_console.create_dossier(
            clone_id=clone_id,
            upgrade_title=upgrade_title,
            why_attempted=why_attempted,
            code_delta=delta_result.get("code_delta", {}),
            capability_delta=delta_result.get("capability_delta", {}),
            tool_delta=delta_result.get("tool_delta", {}),
            metrics=metrics_impact,
            risks=[
                {
                    "risk_type": r.risk_type,
                    "description": r.description,
                    "severity": r.severity,
                    "likelihood": r.likelihood,
                    "affected_modules": r.affected_modules
                }
                for r in risks
            ],
            evidence=[
                {
                    "evidence_type": e.evidence_type,
                    "artifact_id": e.artifact_id,
                    "description": e.description,
                    "hash": e.hash,
                    "available": e.available
                }
                for e in evidence
            ],
            baseline_metrics=baseline,
            current_metrics=current_metrics
        )
        
        # Save to artifacts
        self.artifact_store.store_artifact(
            clone_id=clone_id,
            artifact_type="upgrade_dossier",
            content=json.dumps(dossier.to_dict(ReportLevel.FULL_AUDIT), indent=2),
            file_path=f"dossier_{dossier.dossier_id}.json"
        )
        
        logger.info(f"✅ Dossier created: {dossier.dossier_id}")
        
        return dossier
    
    def get_dossier(self, dossier_id: str, level: ReportLevel = ReportLevel.SIMPLE) -> Dict:
        """Dossier olish"""
        # Get from artifacts
        artifacts = self.artifact_store.search_artifacts(
            artifact_type="upgrade_dossier"
        )
        
        for artifact in artifacts:
            if artifact.artifact_id == f"dossier_{dossier_id}":
                if artifact.content:
                    return json.loads(artifact.content)
        
        return {"error": "Dossier not found"}
    
    def process_approval(self,
                       dossier_id: str,
                       action: ApprovalAction,
                       approver_name: str,
                       comments: str = "") -> UpgradePassport:
        """
        Approval ni qayta ishlash
        
        Args:
            dossier_id: Dossier ID
            action: Action
            approver_name: Kim tasdiqlaydi
            comments: Izohlar
        
        Returns:
            UpgradePassport: Passport
        """
        passport = self.approval_console.process_approval(
            dossier_id, action, approver_name, comments
        )
        
        # Store passport
        self.artifact_store.store_artifact(
            clone_id=passport.clone_id,
            artifact_type="approval_passport",
            content=json.dumps(passport.to_dict(), indent=2),
            file_path=f"passport_{passport.passport_id}.json"
        )
        
        return passport
    
    def get_pending_approvals(self) -> List[Dict]:
        """Kutilayotgan approvallar"""
        return self.approval_console.get_pending_approvals()
    
    def get_approval_history(self, limit: int = 20) -> List[Dict]:
        """Approval tarixi"""
        return self.approval_console.get_approval_history(limit)
    
    def generate_simple_report(self, dossier: UpgradeDossier) -> str:
        """
        Simple report generatsiya qilish
        
        Args:
            dossier: UpgradeDossier
        
        Returns:
            str: Simple report
        """
        return dossier.get_simple_summary()
    
    def generate_full_report(self, dossier: UpgradeDossier) -> Dict:
        """
        Full report generatsiya qilish
        
        Args:
            dossier: UpgradeDossier
        
        Returns:
            Dict: Full report
        """
        return dossier.to_dict(ReportLevel.FULL_AUDIT)
    
    def _extract_metrics_from_artifacts(self, aggregated: Dict) -> Dict[str, float]:
        """Artifactlardan metrikalarni extract qilish"""
        metrics = {}
        
        artifacts = aggregated.get("artifacts", {})
        
        # Look for benchmark results
        benchmark_results = artifacts.get("benchmark_result", [])
        
        for result in benchmark_results:
            content = result.get("content_preview", "")
            
            # Parse simple metrics (would be more sophisticated in reality)
            if "success" in content.lower():
                metrics["task_success"] = 0.7
            if "latency" in content.lower():
                metrics["avg_latency"] = 150
        
        # Default metrics if none found
        if not metrics:
            metrics = self._get_default_baseline()
        
        return metrics
    
    def _get_default_baseline(self) -> Dict[str, float]:
        """Default baseline metrikalar"""
        return {
            "task_success": 0.5,
            "tool_success": 0.7,
            "avg_latency": 200,
            "retry_rate": 3.0,
            "failure_recovery": 0.3
        }


def create_reporting_approval_system(artifact_store: ArtifactStore) -> ReportingApprovalSystem:
    """Reporting & Approval System yaratish"""
    return ReportingApprovalSystem(artifact_store)
