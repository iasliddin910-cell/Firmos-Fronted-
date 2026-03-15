"""
Change Classifier
=================
Classifies changes into 6 types.

This module is part of the Change Planner system.

Key responsibilities:
- Classify change type (6 types)
- Determine complexity and scope
- Select appropriate strategy
"""

import logging
import re
from typing import Dict, List, Set, Optional, Any

from agent.planner.contracts import ChangeType, GoalSpec, ConstraintSpec

logger = logging.getLogger(__name__)


# Change type indicators
MICRO_PATCH_INDICATORS = {
    'fix', 'bug', 'typo', 'error', 'xato', 'tugrat',
    'log', 'comment', 'doc', 'readme',
    'default', 'flag', 'constant',
}

LOCAL_STRUCTURAL_INDICATORS = {
    'rename', 'extract', 'inline', 'move',
    'pattern', 'refactor', 'extract_method',
    'multiple_files', 'several_files',
}

SEMANTIC_REFACTOR_INDICATORS = {
    'rename_class', 'rename_function', 'rename_method',
    'signature', 'type_change', 'api_migration',
    'interface', 'abstract', 'parent_class',
}

DEPENDENCY_MIGRATION_INDICATORS = {
    'upgrade', 'downgrade', 'migrate', 'library',
    'dependency', 'package', 'version', 'import',
    'require', 'pip_install', 'npm_install',
}

BEHAVIORAL_REWRITE_INDICATORS = {
    'algorithm', 'logic', 'flow', 'behavior',
    'rewrite', 'implement', 'change', 'algoritm',
    'mantiq', 'oqim',
}

SPECIES_LEVEL_INDICATORS = {
    'self', 'core', 'kernel', 'agent',
    'tool_registry', 'self_edit', 'self_improvement',
    'brain', 'orchestrator', 'main',
}


class ChangeClassifier:
    """
    Classifies changes into 6 types.
    
    This is Layer 3 of the Change Planner.
    
    FIXED: Complete classification with all 6 types.
    """
    
    def __init__(self):
        self.classification_history: List[Dict] = []
    
    def classify(
        self,
        goal_spec: GoalSpec,
        constraint_spec: ConstraintSpec,
        code_analysis: Optional[Dict] = None
    ) -> ChangeType:
        """
        Main entry point: Classify change type.
        
        Args:
            goal_spec: Compiled goal specification
            constraint_spec: Extracted constraints
            code_analysis: Optional code understanding results
            
        Returns:
            ChangeType enum value
        """
        logger.info(f"🏷️ ChangeClassifier: Classifying change type...")
        
        # Collect features for classification
        features = self._collect_features(goal_spec, constraint_spec, code_analysis)
        
        # Score each change type
        scores = self._score_change_types(features)
        
        # Get highest scoring type
        change_type = max(scores, key=scores.get)
        
        # Record history
        self.classification_history.append({
            'goal_id': goal_spec.goal_id,
            'change_type': change_type,
            'scores': scores,
            'features': list(features.keys())
        })
        
        logger.info(f"✅ ChangeClassifier: Classified as {change_type.value}")
        
        return change_type
    
    def _collect_features(
        self,
        goal: GoalSpec,
        constraints: ConstraintSpec,
        analysis: Optional[Dict]
    ) -> Dict[str, float]:
        """
        Collect features for classification.
        
        Returns:
            Dictionary of feature -> confidence score
        """
        features = {}
        
        # Goal-based features
        objective = goal.objective.lower()
        
        # Check each indicator set
        for indicator_set, feature_name in [
            (MICRO_PATCH_INDICATORS, 'micro_patch'),
            (LOCAL_STRUCTURAL_INDICATORS, 'local_structural'),
            (SEMANTIC_REFACTOR_INDICATORS, 'semantic_refactor'),
            (DEPENDENCY_MIGRATION_INDICATORS, 'dependency_migration'),
            (BEHAVIORAL_REWRITE_INDICATORS, 'behavioral_rewrite'),
            (SPECIES_LEVEL_INDICATORS, 'species_level'),
        ]:
            score = sum(1 for ind in indicator_set if ind in objective)
            if score > 0:
                features[feature_name] = score
        
        # Constraint-based features
        if constraints.red_zone_modules:
            features['species_level'] = len(constraints.red_zone_modules) * 0.5
        
        if constraints.security_symbols:
            features['species_level'] = max(
                features.get('species_level', 0),
                len(constraints.security_symbols) * 0.3
            )
        
        # Code analysis features
        if analysis:
            # File count
            files = analysis.get('files', [])
            if len(files) > 5:
                features['local_structural'] = len(files) * 0.2
            
            # Dependency changes
            if analysis.get('dependency_changes'):
                features['dependency_migration'] = len(analysis['dependency_changes']) * 0.5
            
            # API changes
            if analysis.get('api_changes'):
                features['semantic_refactor'] = len(analysis['api_changes']) * 0.5
        
        return features
    
    def _score_change_types(self, features: Dict[str, float]) -> Dict[ChangeType, float]:
        """
        Score each change type based on features.
        
        Returns:
            Dictionary of ChangeType -> score
        """
        scores = {
            ChangeType.MICRO_PATCH: features.get('micro_patch', 0),
            ChangeType.LOCAL_STRUCTURAL: features.get('local_structural', 0),
            ChangeType.SEMANTIC_REFACTOR: features.get('semantic_refactor', 0),
            ChangeType.DEPENDENCY_MIGRATION: features.get('dependency_migration', 0),
            ChangeType.BEHAVIORAL_REWRITE: features.get('behavioral_rewrite', 0),
            ChangeType.SPECIES_LEVEL: features.get('species_level', 0),
        }
        
        # Add baseline scores for types not in features
        baseline = 0.1
        for change_type in ChangeType:
            if change_type not in scores or scores[change_type] == 0:
                scores[change_type] = baseline
        
        return scores
    
    def get_classification_stats(self) -> Dict:
        """Get classification statistics."""
        if not self.classification_history:
            return {'total_classifications': 0}
        
        type_counts = {}
        for entry in self.classification_history:
            ct = entry['change_type']
            type_counts[ct] = type_counts.get(ct, 0) + 1
        
        return {
            'total_classifications': len(self.classification_history),
            'type_distribution': type_counts
        }
