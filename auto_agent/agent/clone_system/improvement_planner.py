"""
================================================================================
LAYER 5: IMPROVEMENT PLANNER
================================================================================
Signal yoki candidate kelgach, clone nima qilishini rejalaydi.

Planner quyidagilarni chiqaradi:
- maqsad
- tegishli modullar
- patch turi
- test strategy
- benchmark strategy
- rollback complexity
- blast radius
- expected gain

Plannerning chiqishi:

Masalan:
- change_type: new_tool
- files_to_modify: tool_registry.py, browser_helper.py, tests/...
- risk: medium
- needs_new_benchmark: true
- expected_capability_gain: browser navigation
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

from .core_types import (
    CloneType, CloneStatus, RiskClass, ChangeType,
    CloneMetadata, ChangeBudget, ImprovementPlan, PatchSet
)
from .clone_knowledge import CloneKnowledgeManager

logger = logging.getLogger(__name__)


# ================================================================================
# IMPROVEMENT PLANNER
# ================================================================================

class ImprovementPlanner:
    """
    Improvement Planner - Clone yaxshilash rejalashtiruvchi
    
    Bu class:
    1. Signal/Candidate dan improvement plan yaratadi
    2. Risk va blast radius aniqlaydi
    3. Test va benchmark strategiyasini belgilaydi
    4. Change budget ni hisoblaydi
    5. Rollback yo'lini rejalashtiradi
    """
    
    def __init__(self, knowledge_manager: CloneKnowledgeManager):
        self.knowledge_manager = knowledge_manager
        
        # Planning history
        self.plans: Dict[str, ImprovementPlan] = {}
        
        logger.info("📋 Improvement Planner initialized")
    
    def create_plan(self,
                   clone_id: str,
                   signal: str,
                   clone_type: CloneType,
                   target_capabilities: Optional[List[str]] = None) -> ImprovementPlan:
        """
        Improvement plan yaratish
        
        Args:
            clone_id: Clone ID
            signal: Yaxshilash signal/sababi
            clone_type: Clone turi
            target_capabilities: Target capabilities
        
        Returns:
            ImprovementPlan: Improvement plan
        """
        # Generate plan ID
        plan_id = f"plan_{clone_id}_{int(time.time() * 1000)}"
        
        # Analyze signal
        analysis = self._analyze_signal(signal, clone_type)
        
        # Get knowledge for safe file selection
        safe_files = self.knowledge_manager.get_safe_files(clone_type.value)
        
        # Determine files to modify
        files_to_modify = self._determine_files(analysis, safe_files)
        
        # Calculate risk
        risk = self._calculate_risk(clone_type, len(files_to_modify))
        
        # Create change budget based on risk
        budget = self._create_budget(risk)
        
        # Determine test strategy
        test_strategy = self._determine_test_strategy(clone_type, files_to_modify)
        
        # Determine benchmark strategy
        benchmark_strategy = self._determine_benchmark_strategy(clone_type, target_capabilities)
        
        # Create plan
        plan = ImprovementPlan(
            plan_id=plan_id,
            clone_id=clone_id,
            goal=signal,
            change_type=analysis.get("change_type", ChangeType.SMALL_PATCH),
            files_to_modify=files_to_modify,
            risk=risk,
            blast_radius=analysis.get("blast_radius", "local"),
            rollback_complexity=analysis.get("rollback_complexity", "easy"),
            test_strategy=test_strategy,
            benchmark_strategy=benchmark_strategy,
            expected_gain=analysis.get("expected_gain", ""),
            change_budget=budget,
            status="created"
        )
        
        # Save plan
        self.plans[plan_id] = plan
        
        logger.info(f"📝 Plan created: {plan_id} (risk={risk.value}, files={len(files_to_modify)})")
        
        return plan
    
    def _analyze_signal(self, signal: str, clone_type: CloneType) -> Dict:
        """
        Signalni tahlil qilish
        
        Args:
            signal: Improvement signal
            clone_type: Clone turi
        
        Returns:
            Dict: Tahlil natijasi
        """
        signal_lower = signal.lower()
        
        # Determine change type based on signal
        if any(word in signal_lower for word in ["new tool", "tool", "add capability"]):
            change_type = ChangeType.NEW_TOOL
            blast_radius = "local"
            rollback_complexity = "easy"
            expected_gain = "new capability"
        elif any(word in signal_lower for word in ["workflow", "flow", "process"]):
            change_type = ChangeType.WORKFLOW_REDESIGN
            blast_radius = "medium"
            rollback_complexity = "medium"
            expected_gain = "improved workflow"
        elif any(word in signal_lower for word in ["benchmark", "test", "metric"]):
            change_type = ChangeType.BENCHMARK_ADDITION
            blast_radius = "local"
            rollback_complexity = "easy"
            expected_gain = "better measurement"
        elif any(word in signal_lower for word in ["prompt", "tuning", "tweak"]):
            change_type = ChangeType.PROMPT_TUNING
            blast_radius = "local"
            rollback_complexity = "easy"
            expected_gain = "better response"
        elif any(word in signal_lower for word in ["fix", "bug", "error", "issue"]):
            change_type = ChangeType.SMALL_PATCH
            blast_radius = "local"
            rollback_complexity = "easy"
            expected_gain = "bug fix"
        else:
            change_type = ChangeType.SMALL_PATCH
            blast_radius = "local"
            rollback_complexity = "easy"
            expected_gain = "improvement"
        
        return {
            "change_type": change_type,
            "blast_radius": blast_radius,
            "rollback_complexity": rollback_complexity,
            "expected_gain": expected_gain
        }
    
    def _determine_files(self, analysis: Dict, safe_files: Dict[str, List[str]]) -> List[str]:
        """Fayllarni aniqlash"""
        change_type = analysis.get("change_type", ChangeType.SMALL_PATCH)
        
        files = []
        
        # Default file suggestions based on change type
        if change_type == ChangeType.NEW_TOOL:
            files.extend([
                "agent/tool_factory.py",
                "agent/tools.py"
            ])
        elif change_type == ChangeType.WORKFLOW_REDESIGN:
            files.extend([
                "agent/kernel.py",
                "agent/native_brain.py"
            ])
        elif change_type == ChangeType.BENCHMARK_ADDITION:
            files.extend([
                "agent/benchmark.py",
                "agent/regression_suite.py"
            ])
        elif change_type == ChangeType.PROMPT_TUNING:
            files.extend([
                "agent/prompts.py",
                "agent/native_brain.py"
            ])
        
        # Add files from safe list
        files.extend(safe_files.get("safe", [])[:3])
        
        return list(set(files))[:5]  # Max 5 files
    
    def _calculate_risk(self, clone_type: CloneType, file_count: int) -> RiskClass:
        """Riskni hisoblash"""
        # Base risk by clone type
        type_risk = {
            CloneType.MICRO_PATCH: RiskClass.LOW,
            CloneType.CAPABILITY: RiskClass.MEDIUM,
            CloneType.WORKFLOW: RiskClass.MEDIUM,
            CloneType.RESEARCH: RiskClass.LOW,
            CloneType.FORK: RiskClass.HIGH
        }
        
        base_risk = type_risk.get(clone_type, RiskClass.LOW)
        
        # Adjust by file count
        if file_count > 10:
            return RiskClass.HIGH
        elif file_count > 5:
            if base_risk == RiskClass.LOW:
                return RiskClass.MEDIUM
            return RiskClass.HIGH
        else:
            return base_risk
    
    def _create_budget(self, risk: RiskClass) -> ChangeBudget:
        """Change budget yaratish"""
        budgets = {
            RiskClass.LOW: ChangeBudget(max_files=3, max_capabilities=1, max_tools=2),
            RiskClass.MEDIUM: ChangeBudget(max_files=8, max_capabilities=2, max_tools=5),
            RiskClass.HIGH: ChangeBudget(max_files=20, max_capabilities=3, max_tools=10),
            RiskClass.CRITICAL: ChangeBudget(max_files=50, max_capabilities=5, max_tools=20)
        }
        
        return budgets.get(risk, ChangeBudget())
    
    def _determine_test_strategy(self, clone_type: CloneType, files: List[str]) -> str:
        """Test strategiyasini aniqlash"""
        strategies = {
            CloneType.MICRO_PATCH: "unit_tests + smoke_tests",
            CloneType.CAPABILITY: "unit_tests + integration_tests + smoke_tests",
            CloneType.WORKFLOW: "integration_tests + workflow_tests",
            CloneType.RESEARCH: "exploratory_tests + minimal_validation",
            CloneType.FORK: "full_test_suite"
        }
        
        return strategies.get(clone_type, "unit_tests + smoke_tests")
    
    def _determine_benchmark_strategy(self, clone_type: CloneType, 
                                      capabilities: Optional[List[str]]) -> str:
        """Benchmark strategiyasini aniqlash"""
        if capabilities:
            return f"benchmark_{capabilities[0]}"
        
        strategies = {
            CloneType.MICRO_PATCH: "quick_benchmark",
            CloneType.CAPABILITY: "capability_benchmark",
            CloneType.WORKFLOW: "workflow_benchmark",
            CloneType.RESEARCH: "no_benchmark",
            CloneType.FORK: "full_benchmark_suite"
        }
        
        return strategies.get(clone_type, "standard_benchmark")
    
    def validate_plan(self, plan: ImprovementPlan) -> Dict:
        """
        Planni tekshirish
        
        Args:
            plan: ImprovementPlan
        
        Returns:
            Dict: Validatsiya natijasi
        """
        errors = []
        warnings = []
        
        # Check budget
        if plan.change_budget:
            if not plan.change_budget.is_within_budget():
                errors.append("Change budget exceeded")
        
        # Check files exist
        for file_path in plan.files_to_modify:
            # This would check if file exists in workspace
            pass
        
        # Check risk is appropriate for clone type
        if plan.change_type == ChangeType.ARCHITECTURE_EXTENSION and plan.risk != RiskClass.CRITICAL:
            warnings.append("Architecture extension should have CRITICAL risk")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    def update_plan(self, plan_id: str, **updates) -> Optional[ImprovementPlan]:
        """
        Planni yangilash
        
        Args:
            plan_id: Plan ID
            **updates: Yangilanishlar
        
        Returns:
            ImprovementPlan: Yangilangan plan
        """
        plan = self.plans.get(plan_id)
        if not plan:
            return None
        
        # Update fields
        for key, value in updates.items():
            if hasattr(plan, key):
                setattr(plan, key, value)
        
        plan.status = "updated"
        
        logger.info(f"📝 Plan updated: {plan_id}")
        
        return plan
    
    def get_plan(self, plan_id: str) -> Optional[ImprovementPlan]:
        """Plan olish"""
        return self.plans.get(plan_id)
    
    def get_plans_for_clone(self, clone_id: str) -> List[ImprovementPlan]:
        """Clone uchun planlarni olish"""
        return [p for p in self.plans.values() if p.clone_id == clone_id]


# ================================================================================
# PATCH GENERATOR
# ================================================================================

class PatchGenerator:
    """
    Patch Generator - O'zgartirishlarni generatsiya qilish
    
    Bu class:
    1. Improvement plan asosida patch set yaratadi
    2. Patch intent, why, expected_effect majburiy maydonlarini to'ldiradi
    3. Revert yo'lini belgilaydi
    """
    
    def __init__(self):
        self.patches: Dict[str, PatchSet] = {}
        
        logger.info("🩹 Patch Generator initialized")
    
    def generate_patch(self,
                      plan: ImprovementPlan,
                      intent: str,
                      why: str,
                      expected_effect: str,
                      diffs: Optional[Dict[str, str]] = None) -> PatchSet:
        """
        Patch yaratish
        
        Args:
            plan: ImprovementPlan
            intent: Nima qilmoqchi
            why: Nega
            expected_effect: Kutgan natija
            diffs: O'zgartirishlar
        
        Returns:
            PatchSet: Patch set
        """
        patch_id = f"patch_{plan.plan_id}_{int(time.time() * 1000)}"
        
        # Determine revert path
        revert_path = self._generate_revert_path(plan)
        
        patch = PatchSet(
            patch_id=patch_id,
            clone_id=plan.clone_id,
            plan_id=plan.plan_id,
            intent=intent,
            why=why,
            expected_effect=expected_effect,
            files_touched=plan.files_to_modify,
            diffs=diffs or {},
            risk=plan.risk,
            revert_path=revert_path,
            status="generated"
        )
        
        self.patches[patch_id] = patch
        
        logger.info(f"🩹 Patch generated: {patch_id}")
        
        return patch
    
    def _generate_revert_path(self, plan: ImprovementPlan) -> str:
        """Revert yo'lini generatsiya qilish"""
        return f"git checkout -- {', '.join(plan.files_to_modify)}"
    
    def get_patch(self, patch_id: str) -> Optional[PatchSet]:
        """Patch olish"""
        return self.patches.get(patch_id)
    
    def get_patches_for_clone(self, clone_id: str) -> List[PatchSet]:
        """Clone uchun patchlarni olish"""
        return [p for p in self.patches.values() if p.clone_id == clone_id]


# ================================================================================
# FACTORY FUNCTIONS
# ================================================================================

def create_improvement_planner(knowledge_manager: CloneKnowledgeManager) -> ImprovementPlanner:
    """Improvement Planner yaratish"""
    return ImprovementPlanner(knowledge_manager)


def create_patch_generator() -> PatchGenerator:
    """Patch Generator yaratish"""
    return PatchGenerator()
