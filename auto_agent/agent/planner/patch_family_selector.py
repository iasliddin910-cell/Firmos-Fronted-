"""
Patch Family Selector
=====================
Selects the right transform engine for the change.

This module is part of the Change Planner system.

Key responsibilities:
- Select between 5 patch families
- Match change type to transform tool
- Consider security requirements
"""

import logging
from typing import Dict, List, Set, Optional, Any

from agent.planner.contracts import (
    ChangeType, PatchFamily, EditContract,
    GoalSpec, ConstraintSpec
)

logger = logging.getLogger(__name__)


# Patch family selection rules
PATCH_FAMILY_RULES = {
    ChangeType.MICRO_PATCH: {
        'default': PatchFamily.TEXT_DIFF,
        'alternatives': [PatchFamily.STRUCTURAL_CODEMOD]
    },
    ChangeType.LOCAL_STRUCTURAL: {
        'default': PatchFamily.STRUCTURAL_CODEMOD,
        'alternatives': [PatchFamily.SEMANTIC_TYPED]
    },
    ChangeType.SEMANTIC_REFACTOR: {
        'default': PatchFamily.SEMANTIC_TYPED,
        'alternatives': [PatchFamily.STRUCTURAL_CODEMOD]
    },
    ChangeType.DEPENDENCY_MIGRATION: {
        'default': PatchFamily.SEMANTIC_TYPED,
        'alternatives': [PatchFamily.SEMANTIC_PATCH, PatchFamily.TEXT_DIFF]
    },
    ChangeType.BEHAVIORAL_REWRITE: {
        'default': PatchFamily.SEMANTIC_TYPED,
        'alternatives': [PatchFamily.STRUCTURAL_CODEMOD]
    },
    ChangeType.SPECIES_LEVEL: {
        'default': PatchFamily.SECURITY_GUARDED,
        'alternatives': [PatchFamily.SEMANTIC_TYPED]
    }
}

# Security triggers - when to use SECURITY_GUARDED
SECURITY_TRIGGERS = {
    'auth', 'authentication', 'login', 'logout',
    'token', 'jwt', 'oauth', 'session',
    'password', 'secret', 'api_key', 'credential',
    'payment', 'billing', 'invoice', 'stripe',
    'admin', 'root', 'sudo',
    'encryption', 'decrypt', 'hash',
    'permission', 'role', 'access_control',
}


class PatchFamilySelector:
    """
    Selects appropriate patch family.
    
    This is Layer 5 of the Change Planner.
    
    FIXED: Complete patch family selection logic.
    """
    
    def __init__(self):
        self.selection_history: List[Dict] = []
    
    def select(
        self,
        change_type: ChangeType,
        goal_spec: GoalSpec,
        constraint_spec: ConstraintSpec,
        code_analysis: Optional[Dict] = None
    ) -> PatchFamily:
        """
        Main entry point: Select patch family.
        
        Args:
            change_type: Classified change type
            goal_spec: Compiled goal specification
            constraint_spec: Extracted constraints
            code_analysis: Optional code understanding results
            
        Returns:
            Selected PatchFamily enum value
        """
        logger.info(f"🎯 PatchFamilySelector: Selecting patch family...")
        
        # Step 1: Check for security requirements
        if self._requires_security_guard(constraint_spec, code_analysis):
            logger.info("🔒 Security guard required")
            selected = PatchFamily.SECURITY_GUARDED
        else:
            # Step 2: Use rule-based selection
            selected = self._rule_based_selection(change_type, goal_spec, constraint_spec)
        
        # Step 3: Consider alternatives based on context
        if code_analysis:
            selected = self._refine_selection(selected, change_type, code_analysis)
        
        # Record history
        self.selection_history.append({
            'change_type': change_type.value,
            'selected_family': selected.value,
            'has_security_trigger': len(constraint_spec.security_symbols) > 0
        })
        
        logger.info(f"✅ PatchFamilySelector: Selected {selected.value}")
        
        return selected
    
    def _requires_security_guard(
        self,
        constraints: ConstraintSpec,
        analysis: Optional[Dict]
    ) -> bool:
        """
        Check if change requires security guard.
        
        FIXED: Comprehensive security check.
        """
        # Check security symbols in constraints
        if constraints.security_symbols:
            return True
        
        # Check red zones for security modules
        for red_zone in constraints.red_zone_modules:
            red_lower = str(red_zone).lower()
            for trigger in SECURITY_TRIGGERS:
                if trigger in red_lower:
                    return True
        
        # Check data flow risks
        if constraints.data_flow_risks:
            for risk in constraints.data_flow_risks:
                if 'security' in str(risk).lower() or 'auth' in str(risk).lower():
                    return True
        
        # Check analysis for security-sensitive code
        if analysis:
            # Check for security annotations
            if analysis.get('security_sensitive'):
                return True
            
            # Check for auth/billing code
            symbols = analysis.get('symbols', {})
            for symbol in symbols:
                symbol_lower = str(symbol).lower()
                for trigger in SECURITY_TRIGGERS:
                    if trigger in symbol_lower:
                        return True
        
        return False
    
    def _rule_based_selection(
        self,
        change_type: ChangeType,
        goal: GoalSpec,
        constraints: ConstraintSpec
    ) -> PatchFamily:
        """
        Rule-based patch family selection.
        
        FIXED: Complete rule implementation.
        """
        # Get rules for change type
        rules = PATCH_FAMILY_RULES.get(change_type, {})
        
        # Get default
        default = rules.get('default', PatchFamily.TEXT_DIFF)
        
        # Check for override conditions
        
        # Micro patch: use text diff for very small changes
        if change_type == ChangeType.MICRO_PATCH:
            if goal.max_patch_size <= 20:
                return PatchFamily.TEXT_DIFF
        
        # Local structural: check complexity
        if change_type == ChangeType.LOCAL_STRUCTURAL:
            if len(constraints.red_zone_modules) > 0:
                return PatchFamily.SEMANTIC_TYPED
        
        # Semantic refactor: always use typed
        if change_type == ChangeType.SEMANTIC_REFACTOR:
            return PatchFamily.SEMANTIC_TYPED
        
        # Dependency migration: check for C/C++ code
        if change_type == ChangeType.DEPENDENCY_MIGRATION:
            return PatchFamily.SEMANTIC_TYPED
        
        # Species level: already checked for security
        if change_type == ChangeType.SPECIES_LEVEL:
            return PatchFamily.SECURITY_GUARDED
        
        return default
    
    def _refine_selection(
        self,
        selected: PatchFamily,
        change_type: ChangeType,
        analysis: Dict
    ) -> PatchFamily:
        """
        Refine selection based on code analysis.
        
        FIXED: Analysis-based refinement.
        """
        # Check file types
        files = analysis.get('files', [])
        
        # C/C++ files suggest semantic patch
        c_files = [f for f in files if str(f).endswith(('.c', '.cpp', '.h', '.hpp'))]
        if c_files and selected != PatchFamily.SECURITY_GUARDED:
            # Check if it's C-specific migration
            if change_type == ChangeType.DEPENDENCY_MIGRATION:
                return PatchFamily.SEMANTIC_PATCH
        
        # Many files suggest structural codemod
        if len(files) > 10 and selected == PatchFamily.TEXT_DIFF:
            return PatchFamily.STRUCTURAL_CODEMOD
        
        # Java/Kotlin files suggest semantic typed
        java_files = [f for f in files if str(f).endswith(('.java', '.kt', '.scala'))]
        if java_files:
            return PatchFamily.SEMANTIC_TYPED
        
        return selected
    
    def get_selection_stats(self) -> Dict:
        """Get selection statistics."""
        if not self.selection_history:
            return {'total_selections': 0}
        
        family_counts = {}
        for entry in self.selection_history:
            family = entry['selected_family']
            family_counts[family] = family_counts.get(family, 0) + 1
        
        return {
            'total_selections': len(self.selection_history),
            'family_distribution': family_counts
        }
