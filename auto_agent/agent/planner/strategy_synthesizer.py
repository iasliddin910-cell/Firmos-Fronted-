"""
Strategy Synthesizer
==================
Generates 3 candidate plans: minimal, balanced, aggressive.

This module is part of the Change Planner system.

Key responsibilities:
- Generate multiple candidate plans
- Score each plan
- Select best strategy
"""

import logging
from typing import Dict, List, Set, Optional, Any
from dataclasses import dataclass

from agent.planner.contracts import (
    ChangeType, ChangePhase, EditPlan, EditContract,
    GoalSpec, ConstraintSpec
)

logger = logging.getLogger(__name__)


class StrategySynthesizer:
    """
    Synthesizes candidate plans.
    
    This is Layer 4 of the Change Planner.
    
    FIXED: Complete multi-plan generation.
    """
    
    def __init__(self):
        self.synthesis_history: List[Dict] = []
    
    def synthesize(
        self,
        goal_spec: GoalSpec,
        constraint_spec: ConstraintSpec,
        change_type: ChangeType,
        contract: EditContract
    ) -> List[EditPlan]:
        """
        Main entry point: Generate candidate plans.
        
        Args:
            goal_spec: Compiled goal specification
            constraint_spec: Extracted constraints
            change_type: Classified change type
            contract: Edit contract
            
        Returns:
            List of 3 candidate EditPlans
        """
        logger.info(f"🧩 StrategySynthesizer: Generating candidate plans...")
        
        # Generate plans
        plans = []
        
        # 1. Minimal plan - least risky
        minimal_plan = self._create_minimal_plan(goal_spec, constraint_spec, change_type, contract)
        plans.append(minimal_plan)
        
        # 2. Balanced plan - risk/reward balance
        balanced_plan = self._create_balanced_plan(goal_spec, constraint_spec, change_type, contract)
        plans.append(balanced_plan)
        
        # 3. Aggressive plan - maximum gain
        aggressive_plan = self._create_aggressive_plan(goal_spec, constraint_spec, change_type, contract)
        plans.append(aggressive_plan)
        
        # Score all plans
        for plan in plans:
            plan.calculate_score()
        
        # Sort by score
        plans.sort(key=lambda p: p.total_score, reverse=True)
        
        # Record history
        self.synthesis_history.append({
            'contract_id': contract.contract_id,
            'change_type': change_type.value,
            'plans_generated': len(plans),
            'best_plan': plans[0].plan_id if plans else None,
            'best_score': plans[0].total_score if plans else 0
        })
        
        logger.info(f"✅ StrategySynthesizer: Generated {len(plans)} plans, "
                   f"best: {plans[0].plan_id} (score: {plans[0].total_score:.1f})")
        
        return plans
    
    def _create_minimal_plan(
        self,
        goal: GoalSpec,
        constraints: ConstraintSpec,
        change_type: ChangeType,
        contract: EditContract
    ) -> EditPlan:
        """Create minimal touch plan."""
        import uuid
        
        plan_id = f"plan_minimal_{uuid.uuid4().hex[:8]}"
        
        # Minimal plan: fewer phases, smaller scope
        phases = self._get_minimal_phases(change_type)
        
        # Score components
        semantic_certainty = 0.9  # High certainty for minimal
        blast_radius = min(goal.max_patch_size // 10, 10)  # Small
        reversibility = 0.95  # Very reversible
        expected_gain = 0.3  # Small but safe gain
        validation_cost = 0.2  # Low validation cost
        
        plan = EditPlan(
            plan_id=plan_id,
            contract_id=contract.contract_id,
            plan_type='minimal',
            phases=phases,
            semantic_certainty=semantic_certainty,
            blast_radius=blast_radius,
            reversibility=reversibility,
            expected_gain=expected_gain,
            validation_cost=validation_cost
        )
        
        # Add phase patches
        plan.phase_patches = self._create_phase_patches(phases, 'minimal')
        
        return plan
    
    def _create_balanced_plan(
        self,
        goal: GoalSpec,
        constraints: ConstraintSpec,
        change_type: ChangeType,
        contract: EditContract
    ) -> EditPlan:
        """Create balanced risk/reward plan."""
        import uuid
        
        plan_id = f"plan_balanced_{uuid.uuid4().hex[:8]}"
        
        # Balanced: more phases, moderate scope
        phases = self._get_balanced_phases(change_type)
        
        # Score components
        semantic_certainty = 0.7
        blast_radius = min(goal.max_patch_size // 5, 30)
        reversibility = 0.8
        expected_gain = 0.6
        validation_cost = 0.5
        
        plan = EditPlan(
            plan_id=plan_id,
            contract_id=contract.contract_id,
            plan_type='balanced',
            phases=phases,
            semantic_certainty=semantic_certainty,
            blast_radius=blast_radius,
            reversibility=reversibility,
            expected_gain=expected_gain,
            validation_cost=validation_cost
        )
        
        plan.phase_patches = self._create_phase_patches(phases, 'balanced')
        
        return plan
    
    def _create_aggressive_plan(
        self,
        goal: GoalSpec,
        constraints: ConstraintSpec,
        change_type: ChangeType,
        contract: EditContract
    ) -> EditPlan:
        """Create aggressive maximum gain plan."""
        import uuid
        
        plan_id = f"plan_aggressive_{uuid.uuid4().hex[:8]}"
        
        # Aggressive: all phases, full scope
        phases = self._get_all_phases()
        
        # Score components
        semantic_certainty = 0.5
        blast_radius = min(goal.max_patch_size // 2, 50)
        reversibility = 0.6
        expected_gain = 1.0
        validation_cost = 0.9
        
        plan = EditPlan(
            plan_id=plan_id,
            contract_id=contract.contract_id,
            plan_type='aggressive',
            phases=phases,
            semantic_certainty=semantic_certainty,
            blast_radius=blast_radius,
            reversibility=reversibility,
            expected_gain=expected_gain,
            validation_cost=validation_cost
        )
        
        plan.phase_patches = self._create_phase_patches(phases, 'aggressive')
        
        return plan
    
    def _get_minimal_phases(self, change_type: ChangeType) -> List[ChangePhase]:
        """Get phases for minimal plan."""
        if change_type == ChangeType.MICRO_PATCH:
            return [ChangePhase.CORE]
        elif change_type == ChangeType.LOCAL_STRUCTURAL:
            return [ChangePhase.CORE, ChangePhase.PROPAGATION]
        else:
            return [ChangePhase.PREPARATION, ChangePhase.CORE]
    
    def _get_balanced_phases(self, change_type: ChangeType) -> List[ChangePhase]:
        """Get phases for balanced plan."""
        if change_type == ChangeType.MICRO_PATCH:
            return [ChangePhase.CORE, ChangePhase.PROPAGATION]
        elif change_type == ChangeType.LOCAL_STRUCTURAL:
            return [ChangePhase.PREPARATION, ChangePhase.CORE, ChangePhase.PROPAGATION]
        else:
            return [ChangePhase.PREPARATION, ChangePhase.CORE, ChangePhase.PROPAGATION, ChangePhase.CLEANUP]
    
    def _get_all_phases(self) -> List[ChangePhase]:
        """Get all phases for aggressive plan."""
        return [
            ChangePhase.PREPARATION,
            ChangePhase.CORE,
            ChangePhase.PROPAGATION,
            ChangePhase.CLEANUP,
            ChangePhase.HARDENING
        ]
    
    def _create_phase_patches(
        self,
        phases: List[ChangePhase],
        plan_type: str
    ) -> Dict[ChangePhase, Dict[str, Any]]:
        """Create patch details for each phase."""
        patches = {}
        
        for phase in phases:
            if phase == ChangePhase.PREPARATION:
                patches[phase] = {
                    'type': 'adapter',
                    'scope': 'minimal' if plan_type == 'minimal' else 'full',
                    'rollback': True
                }
            elif phase == ChangePhase.CORE:
                patches[phase] = {
                    'type': 'core_behavior',
                    'scope': 'local' if plan_type == 'minimal' else 'global',
                    'validation': 'strict' if plan_type == 'minimal' else 'standard'
                }
            elif phase == ChangePhase.PROPAGATION:
                patches[phase] = {
                    'type': 'update_callers',
                    'include_tests': True,
                    'include_docs': plan_type != 'minimal'
                }
            elif phase == ChangePhase.CLEANUP:
                patches[phase] = {
                    'type': 'remove_dead_code',
                    'aggressive': plan_type == 'aggressive'
                }
            elif phase == ChangePhase.HARDENING:
                patches[phase] = {
                    'type': 'add_monitoring',
                    'add_asserts': True,
                    'add_fallback': plan_type == 'aggressive'
                }
        
        return patches
    
    def get_synthesis_stats(self) -> Dict:
        """Get synthesis statistics."""
        return {
            'total_syntheses': len(self.synthesis_history),
            'recent_syntheses': self.synthesis_history[-10:]
        }
