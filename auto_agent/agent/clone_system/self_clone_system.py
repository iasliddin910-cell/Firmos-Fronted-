"""
================================================================================
SELF-CLONE IMPROVEMENT SYSTEM - MAIN ORCHESTRATOR
================================================================================
Bu asosiy orchestrator - barcha 8 ta qavatni birlashtiradi.

Asosiy prinsip:
"Core is sacred, clones are experimental"

Self-improvement hech qachon jonli agentning o'zida sodir bo'lmasligi kerak;
u har doim izolyatsiyalangan, auditli, qaytariladigan clone muhitida bo'lishi kerak.
================================================================================
"""
import os
import sys
import json
import logging
import time
import asyncio
from typing import Dict, List, Optional, Any, Callable, Set, Union
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from collections import defaultdict
from pathlib import Path
from enum import Enum

from .core_types import (
    CloneType, CloneStatus, RiskClass, ChangeType, ValidationResult,
    CloneMetadata, ChangeBudget, ImprovementPlan, PatchSet, ValidationReport
)

# Import all layers
from .clone_factory import CloneFactory, SourceCloneManager, create_clone_factory, create_source_clone_manager
from .runtime_isolation import (
    RuntimeIsolator, SecretScopeManager, 
    create_runtime_isolator, create_secret_scope_manager
)
from .clone_knowledge import CloneKnowledgeManager, create_knowledge_manager
from .improvement_planner import ImprovementPlanner, PatchGenerator, create_improvement_planner, create_patch_generator
from .patch_build_extend import (
    PatchExecutor, ToolOnboarding, BenchmarkAdder,
    create_patch_executor, create_tool_onboarding, create_benchmark_adder
)
from .local_validation import LocalValidator, ValidationGate, create_local_validator, create_validation_gate
from .artifact_store import (
    ArtifactStore, LineageRegistry, ReportGenerator,
    create_artifact_store, create_lineage_registry, create_report_generator
)

logger = logging.getLogger(__name__)


# ================================================================================
# SELF-CLONE SYSTEM - ASOSIY ORCHESTRATOR
# ================================================================================

class SelfCloneSystem:
    """
    Self-Clone Improvement System - To'liq Arxitektura
    
    Bu class 8 ta qavatni birlashtiradi:
    1. Clone Factory - Clone yaratish
    2. Source Clone Layer - Kod nusxasi
    3. Runtime Isolation - Runtime izolyatsiya
    4. Clone Knowledge - Bilim bazasi
    5. Improvement Planner - Rejalashtiruvchi
    6. Patch/Build/Extend - O'zgartirish
    7. Local Validation - Tekshiruv
    8. Artifact Store - Arxiv
    
    ISH FLOW:
    1. UpgradeCandidate keladi
    2. Clone factory yangi isolated clone yaratadi
    3. Clone repo graph va architecture'ni tushunadi
    4. Improvement plan tuzadi
    5. Patch/tool/workflow o'zgarishini kiritadi
    6. Tests va benchmarklar qo'shadi
    7. O'zgarishni local eval qiladi
    8. Natijani saqlaydi
    9. Report system'ga topshiradi
    
    Original esa umuman tegilmagan holda qoladi.
    """
    
    def __init__(self, 
                 workspace_root: str,
                 storage_root: str = "data/clones",
                 config: Optional[Dict] = None):
        """
        Self-Clone System ni ishga tushirish
        
        Args:
            workspace_root: Asosiy workspace yo'li
            storage_root: Clone storage yo'li
            config: Konfiguratsiya
        """
        self.workspace_root = Path(workspace_root)
        self.storage_root = Path(storage_root)
        self.config = config or {}
        
        # ========================================
        # LAYER 1: CLONE FACTORY
        # ========================================
        logger.info("📦 Initializing Layer 1: Clone Factory...")
        self.factory = create_clone_factory(
            workspace_root=str(self.workspace_root),
            storage_root=str(self.storage_root),
            max_clones=self.config.get("max_clones", 10),
            default_ttl=self.config.get("default_ttl", 3600)
        )
        
        # ========================================
        # LAYER 2: SOURCE CLONE MANAGER
        # ========================================
        logger.info("📂 Initializing Layer 2: Source Clone Manager...")
        self.source_manager = create_source_clone_manager(
            workspace_root=str(self.workspace_root),
            factory=self.factory
        )
        
        # ========================================
        # LAYER 3: RUNTIME ISOLATION
        # ========================================
        logger.info("🛡️ Initializing Layer 3: Runtime Isolation...")
        self.runtime_isolator = create_runtime_isolator(self.factory)
        self.secret_manager = create_secret_scope_manager()
        
        # ========================================
        # LAYER 4: KNOWLEDGE MANAGER
        # ========================================
        logger.info("🧠 Initializing Layer 4: Clone Knowledge...")
        self.knowledge_manager = create_knowledge_manager(str(self.workspace_root))
        
        # ========================================
        # LAYER 5: IMPROVEMENT PLANNER
        # ========================================
        logger.info("📋 Initializing Layer 5: Improvement Planner...")
        self.planner = create_improvement_planner(self.knowledge_manager)
        self.patch_generator = create_patch_generator()
        
        # ========================================
        # LAYER 6: PATCH/BUILD/EXTEND
        # ========================================
        logger.info("🔧 Initializing Layer 6: Patch/Build/Extend...")
        self.patch_executor = None  # Will be created per-clone
        self.tool_onboarding = create_tool_onboarding(self.factory, self.source_manager)
        self.benchmark_adder = create_benchmark_adder(self.factory)
        
        # ========================================
        # LAYER 7: LOCAL VALIDATION
        # ========================================
        logger.info("🔬 Initializing Layer 7: Local Validation...")
        self.validator = create_local_validator(self.factory)
        self.validation_gate = create_validation_gate()
        
        # ========================================
        # LAYER 8: ARTIFACT STORE
        # ========================================
        logger.info("📦 Initializing Layer 8: Artifact Store...")
        self.artifact_store = create_artifact_store(self.factory)
        self.lineage_registry = create_lineage_registry()
        self.report_generator = create_report_generator(self.artifact_store, self.lineage_registry)
        
        logger.info("✅ Self-Clone System initialized with all 8 layers!")
    
    # ========================================================================
    # PUBLIC API
    # ========================================================================
    
    def create_clone(self,
                   clone_type: CloneType,
                   reason: str,
                   candidate_id: Optional[str] = None,
                   parent_clone_id: Optional[str] = None,
                   risk_level: Optional[RiskClass] = None,
                   ttl: Optional[int] = None) -> CloneMetadata:
        """
        Clone yaratish - ASOSIY KIRISH NUQTASI
        
        Args:
            clone_type: Clone turi
            reason: Clone yaratish sababi
            candidate_id: Upgrade candidate ID
            parent_clone_id: Parent clone ID
            risk_level: Risk klassi (auto-calculated if None)
            ttl: Time to live
        
        Returns:
            CloneMetadata: Clone metama'lumotlari
        """
        # Auto-calculate risk if not provided
        if risk_level is None:
            risk_level = self._calculate_initial_risk(clone_type)
        
        # Create clone
        metadata = self.factory.create_clone(
            clone_type=clone_type,
            reason=reason,
            candidate_id=candidate_id,
            parent_clone_id=parent_clone_id,
            risk_level=risk_level,
            ttl=ttl
        )
        
        # Update status
        self.factory.update_clone_status(metadata.clone_id, CloneStatus.INITIALIZING)
        
        # Create source snapshot
        self.source_manager.create_source_snapshot(metadata.clone_id)
        
        # Create runtime
        self.runtime_isolator.create_runtime(metadata.clone_id)
        
        # Create secrets for candidate
        if candidate_id:
            self.secret_manager.create_candidate_secrets(candidate_id, metadata.scope_permissions)
        
        # Update status
        self.factory.update_clone_status(metadata.clone_id, CloneStatus.ANALYZING)
        
        # Store artifact
        self.artifact_store.store_artifact(
            clone_id=metadata.clone_id,
            artifact_type="metadata",
            content=json.dumps(metadata.to_dict(), indent=2),
            file_path="metadata.json"
        )
        
        logger.info(f"✅ Clone created and initialized: {metadata.clone_id}")
        
        return metadata
    
    def run_improvement_cycle(self,
                           clone_id: str,
                           signal: str,
                           patch_content: Optional[Dict[str, str]] = None) -> Dict:
        """
        To'liq improvement cycle - ASOSIY ISH METODI
        
        Bu method to'liq pipeline ni ishga tushiradi:
        1. Clone ni tahlil qiladi
        2. Improvement plan yaratadi
        3. Patch qo'llaydi
        4. Validation dan o'tkazadi
        5. Natijalarni saqlaydi
        
        Args:
            clone_id: Clone ID
            signal: Improvement signal
            patch_content: O'zgartirishlar (file_path -> content)
        
        Returns:
            Dict: Natijalar
        """
        result = {
            "clone_id": clone_id,
            "signal": signal,
            "success": False,
            "stages": {}
        }
        
        try:
            # Get metadata
            metadata = self.factory.get_clone(clone_id)
            if not metadata:
                result["error"] = "Clone not found"
                return result
            
            # ========================================
            # STAGE 1: Knowledge Analysis
            # ========================================
            logger.info(f"🔍 Stage 1: Knowledge Analysis for {clone_id}")
            self.factory.update_clone_status(clone_id, CloneStatus.ANALYZING)
            
            knowledge = self.knowledge_manager.analyze_for_clone(clone_id)
            
            self.artifact_store.store_artifact(
                clone_id=clone_id,
                artifact_type="knowledge_analysis",
                content=json.dumps(knowledge, indent=2, default=str),
                file_path="knowledge.json"
            )
            
            result["stages"]["knowledge_analysis"] = "completed"
            
            # ========================================
            # STAGE 2: Planning
            # ========================================
            logger.info(f"📋 Stage 2: Planning for {clone_id}")
            self.factory.update_clone_status(clone_id, CloneStatus.PLANNING)
            
            plan = self.planner.create_plan(
                clone_id=clone_id,
                signal=signal,
                clone_type=metadata.clone_type
            )
            
            self.artifact_store.store_artifact(
                clone_id=clone_id,
                artifact_type="improvement_plan",
                content=json.dumps(plan.to_dict(), indent=2, default=str),
                file_path="plan.json"
            )
            
            result["stages"]["planning"] = "completed"
            result["plan_id"] = plan.plan_id
            
            # ========================================
            # STAGE 3: Patching
            # ========================================
            logger.info(f"🩹 Stage 3: Patching for {clone_id}")
            self.factory.update_clone_status(clone_id, CloneStatus.PATCHING)
            
            # Create patch executor
            runtime = self.runtime_isolator.get_runtime(clone_id)
            patch_executor = create_patch_executor(
                self.factory,
                self.source_manager,
                runtime
            )
            
            # Generate patch
            if patch_content:
                patch = self.patch_generator.generate_patch(
                    plan=plan,
                    intent=signal,
                    why="Signal-driven improvement",
                    expected_effect=plan.expected_gain,
                    diffs=patch_content
                )
                
                # Apply patch
                apply_result = patch_executor.apply_patch(patch)
                
                result["stages"]["patching"] = apply_result
                
                # Store patch
                self.artifact_store.store_artifact(
                    clone_id=clone_id,
                    artifact_type="patch_diff",
                    content=json.dumps(patch.to_dict(), indent=2, default=str),
                    file_path="patch.json"
                )
            else:
                result["stages"]["patching"] = "no_patch_provided"
            
            # ========================================
            # STAGE 4: Validation
            # ========================================
            logger.info(f"🔬 Stage 4: Validation for {clone_id}")
            self.factory.update_clone_status(clone_id, CloneStatus.VALIDATING)
            
            validation_report = self.validator.validate_clone(clone_id)
            
            self.artifact_store.store_artifact(
                clone_id=clone_id,
                artifact_type="validation_report",
                content=json.dumps(validation_report.to_dict(), indent=2, default=str),
                file_path="validation.json"
            )
            
            result["stages"]["validation"] = validation_report.to_dict()
            
            # Check if can proceed
            can_proceed = self.validation_gate.can_proceed(
                metadata.clone_type.value,
                validation_report
            )
            
            if not can_proceed["can_proceed"]:
                result["error"] = f"Validation failed: {can_proceed['reason']}"
                result["blocking_issues"] = self.validation_gate.get_blocking_issues(validation_report)
                self.factory.update_clone_status(clone_id, CloneStatus.FAILED)
                return result
            
            # ========================================
            # STAGE 5: Artifact Storage
            # ========================================
            logger.info(f"💾 Stage 5: Storing artifacts for {clone_id}")
            self.factory.update_clone_status(clone_id, CloneStatus.REPORTING)
            
            # Register lineage
            self.lineage_registry.register_candidate({
                "clone_id": clone_id,
                "parent_clone_id": metadata.parent_clone_id,
                "root_clone_id": metadata.lineage[0] if metadata.lineage else clone_id,
                "reason": signal,
                "risk": metadata.risk_level.value
            })
            
            result["stages"]["reporting"] = "completed"
            
            # Update status
            self.factory.update_clone_status(clone_id, CloneStatus.APPROVED)
            
            result["success"] = True
            logger.info(f"✅ Improvement cycle completed for {clone_id}")
            
        except Exception as e:
            logger.error(f"❌ Improvement cycle failed: {e}")
            result["error"] = str(e)
            result["traceback"] = traceback.format_exc()
            
            # Store error
            self.artifact_store.store_artifact(
                clone_id=clone_id,
                artifact_type="error",
                content=traceback.format_exc(),
                file_path="error.log"
            )
            
            self.factory.update_clone_status(clone_id, CloneStatus.FAILED)
        
        return result
    
    def add_tool_to_clone(self,
                         clone_id: str,
                         tool_name: str,
                         description: str,
                         implementation: str) -> bool:
        """
        Clone ga tool qo'shish
        
        Args:
            clone_id: Clone ID
            tool_name: Tool nomi
            description: Tavsif
            implementation: Implementatsiya
        
        Returns:
            bool: Muvaffaqiyat
        """
        try:
            # Create spec
            spec = self.tool_onboarding.create_tool_spec(
                tool_name=tool_name,
                description=description,
                when_to_call="When needed",
                input_schema={},
                output_schema={}
            )
            
            # Create wrapper
            success = self.tool_onboarding.create_tool_wrapper(
                clone_id=clone_id,
                spec=spec,
                implementation=implementation
            )
            
            if success:
                # Store artifact
                self.artifact_store.store_artifact(
                    clone_id=clone_id,
                    artifact_type="tool_manifest",
                    content=json.dumps(spec.to_dict(), indent=2),
                    file_path=f"tools/{tool_name}.json"
                )
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to add tool: {e}")
            return False
    
    def validate_clone(self, clone_id: str) -> ValidationReport:
        """
        Clone ni tekshirish
        
        Args:
            clone_id: Clone ID
        
        Returns:
            ValidationReport: Tekshiruv natijasi
        """
        return self.validator.validate_clone(clone_id)
    
    def get_clone_report(self, clone_id: str) -> Dict:
        """
        Clone report olish
        
        Args:
            clone_id: Clone ID
        
        Returns:
            Dict: Report
        """
        return self.report_generator.generate_clone_report(clone_id)
    
    def promote_clone(self, clone_id: str) -> bool:
        """
        Clone ni productionga chiqarish (promote)
        
        Bu faqat clone ichidagi o'zgarishlarni
        asosiy tizimga qo'llamaydi!
        
        Args:
            clone_id: Clone ID
        
        Returns:
            bool: Muvaffaqiyat
        """
        try:
            metadata = self.factory.get_clone(clone_id)
            if not metadata:
                return False
            
            # Get diffs
            diffs = self.source_manager.get_all_diffs(clone_id)
            
            # Store final report
            report = self.get_clone_report(clone_id)
            self.artifact_store.store_artifact(
                clone_id=clone_id,
                artifact_type="final_report",
                content=json.dumps(report, indent=2, default=str),
                file_path="final_report.json"
            )
            
            # Mark in lineage
            self.lineage_registry.mark_promoted(clone_id)
            
            # Update status
            self.factory.update_clone_status(clone_id, CloneStatus.PROMOTED)
            
            logger.info(f"🌟 Clone {clone_id} promoted!")
            
            # Return diffs for manual review
            return {
                "promoted": True,
                "diffs": diffs,
                "clone_id": clone_id
            }
            
        except Exception as e:
            logger.error(f"Failed to promote clone: {e}")
            return False
    
    def reject_clone(self, clone_id: str, reason: str) -> bool:
        """
        Clone ni rad etish
        
        Args:
            clone_id: Clone ID
            reason: Rad etish sababi
        
        Returns:
            bool: Muvaffaqiyat
        """
        try:
            # Mark in lineage
            self.lineage_registry.mark_rejected(clone_id)
            
            # Update status
            self.factory.update_clone_status(clone_id, CloneStatus.REJECTED)
            
            # Store rejection reason
            self.artifact_store.store_artifact(
                clone_id=clone_id,
                artifact_type="rejection",
                content=reason,
                file_path="rejection.txt"
            )
            
            logger.info(f"❌ Clone {clone_id} rejected: {reason}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to reject clone: {e}")
            return False
    
    def cleanup_clone(self, clone_id: str) -> bool:
        """
        Clone ni tozalash
        
        Args:
            clone_id: Clone ID
        
        Returns:
            bool: Muvaffaqiyat
        """
        try:
            # Destroy runtime
            self.runtime_isolator.destroy_runtime(clone_id)
            
            # Cleanup worktree
            self.source_manager.cleanup_worktree(clone_id)
            
            # Cleanup factory
            self.factory.cleanup_clone(clone_id, reason="manual_cleanup")
            
            # Artifacts are kept for history
            
            logger.info(f"🧹 Clone {clone_id} cleaned up")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to cleanup clone: {e}")
            return False
    
    def get_system_status(self) -> Dict:
        """
        Tizim holatini olish
        
        Returns:
            Dict: Status
        """
        return {
            "factory": self.factory.get_clone_stats(),
            "active_clones": self.factory.get_active_clones(),
            "runtimes": self.runtime_isolator.get_all_runtimes(),
            "artifacts": self.artifact_store.get_artifact_stats(),
            "lineage": self.lineage_registry.get_statistics()
        }
    
    def get_executive_summary(self) -> str:
        """Executive summary olish"""
        return self.report_generator.generate_executive_summary()
    
    # ========================================================================
    # PRIVATE METHODS
    # ========================================================================
    
    def _calculate_initial_risk(self, clone_type: CloneType) -> RiskClass:
        """Initial risk hisoblash"""
        risk_map = {
            CloneType.MICRO_PATCH: RiskClass.LOW,
            CloneType.CAPABILITY: RiskClass.MEDIUM,
            CloneType.WORKFLOW: RiskClass.MEDIUM,
            CloneType.RESEARCH: RiskClass.LOW,
            CloneType.FORK: RiskClass.HIGH
        }
        return risk_map.get(clone_type, RiskClass.LOW)
    
    def shutdown(self):
        """Tizimni to'xtatish"""
        logger.info("🛑 Shutting down Self-Clone System...")
        
        # Cleanup all runtimes
        for clone_id in list(self.runtime_isolator.active_runtimes.keys()):
            self.runtime_isolator.destroy_runtime(clone_id)
        
        # Shutdown factory
        self.factory.shutdown()
        
        logger.info("✅ Self-Clone System shutdown complete")


# ========================================================================
# FACTORY FUNCTION
# ========================================================================

def create_self_clone_system(workspace_root: str, **kwargs) -> SelfCloneSystem:
    """
    Self-Clone System yaratish
    
    Args:
        workspace_root: Workspace yo'li
        **kwargs: Qo'shimcha konfiguratsiya
    
    Returns:
        SelfCloneSystem
    """
    return SelfCloneSystem(workspace_root, **kwargs)
