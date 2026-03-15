"""
Goal Compiler
=============
Converts user request → Technical goal specification.

This module is part of the Change Planner system.

Key responsibilities:
- Parse natural language requests
- Extract specific technical objectives
- Define target metrics
- Set scope boundaries
- Define acceptance criteria
"""

import re
import logging
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass, field

from agent.planner.contracts import GoalSpec

logger = logging.getLogger(__name__)


# Keywords for goal extraction
PERFORMANCE_KEYWORDS = {
    'fast': 'performance',
    'slow': 'performance',
    'speed': 'performance',
    'latency': 'performance',
    'optimize': 'performance',
    'performance': 'performance',
    'tezo': 'performance',  # Uzbek
    'tezlashtir': 'performance',  # Uzbek
}

QUALITY_KEYWORDS = {
    'fix': 'bugfix',
    'bug': 'bugfix',
    'error': 'bugfix',
    'xato': 'bugfix',  # Uzbek
    'tugrat': 'bugfix',  # Uzbek
    'refactor': 'refactor',
    'clean': 'refactor',
    'improve': 'improvement',
    'yaxshilat': 'improvement',  # Uzbek
}

SECURITY_KEYWORDS = {
    'security': 'security',
    'safe': 'security',
    'secure': 'security',
    'xavfsiz': 'security',  # Uzbek
    'auth': 'security',
    'token': 'security',
    'parol': 'security',  # Uzbek
    'password': 'security',
}

SCOPE_MARKERS = {
    'only': 'restrict',
    'just': 'restrict',
    'exclude': 'forbid',
    'without': 'forbid',
    'except': 'forbid',
    'faqat': 'restrict',  # Uzbek
    'oldin': 'forbid',  # Uzbek
}


class GoalCompiler:
    """
    Compiles user requests into GoalSpec.
    
    This is Layer 1 of the Change Planner.
    
    FIXED: Complete implementation with all required fields.
    """
    
    def __init__(self):
        self.compilation_history: List[Dict] = []
    
    def compile(self, request: str, context: Optional[Dict] = None) -> GoalSpec:
        """
        Main entry point: Convert request to GoalSpec.
        
        Args:
            request: Natural language request
            context: Optional context (current codebase, recent changes, etc.)
            
        Returns:
            GoalSpec with all required fields
        """
        logger.info(f"🎯 GoalCompiler: Compiling request: {request[:100]}...")
        
        # Step 1: Extract objective
        objective = self._extract_objective(request)
        
        # Step 2: Extract target metric
        target_metric = self._extract_metric(request)
        
        # Step 3: Determine scope
        allowed_scope, forbidden_scope = self._extract_scope(request, context)
        
        # Step 4: Extract constraints
        max_patch_size = self._extract_patch_size(request)
        rollback_class = self._extract_rollback_class(request)
        
        # Step 5: Generate acceptance criteria
        acceptance_criteria = self._generate_acceptance_criteria(request)
        
        # Create GoalSpec
        goal_spec = GoalSpec(
            objective=objective,
            target_metric=target_metric,
            allowed_scope=allowed_scope,
            forbidden_scope=forbidden_scope,
            max_patch_size=max_patch_size,
            rollback_class=rollback_class,
            acceptance_criteria=acceptance_criteria
        )
        
        # Record history
        self.compilation_history.append({
            'request': request,
            'goal_id': goal_spec.goal_id,
            'objective': objective
        })
        
        logger.info(f"✅ GoalCompiler: Created goal {goal_spec.goal_id}")
        
        return goal_spec
    
    def _extract_objective(self, request: str) -> str:
        """
        Extract the core objective from request.
        
        Converts "make it faster" → "optimize_performance"
        """
        request_lower = request.lower()
        
        # Check performance keywords
        for keyword in PERFORMANCE_KEYWORDS:
            if keyword in request_lower:
                return "optimize_performance"
        
        # Check quality keywords
        for keyword in QUALITY_KEYWORDS:
            if keyword in request_lower:
                return self._map_quality_keyword(keyword)
        
        # Check security keywords
        for keyword in SECURITY_KEYWORDS:
            if keyword in request_lower:
                return "improve_security"
        
        # Default: generic improvement
        return "general_improvement"
    
    def _map_quality_keyword(self, keyword: str) -> str:
        """Map quality keywords to objectives."""
        mapping = {
            'fix': 'fix_bug',
            'bug': 'fix_bug',
            'error': 'fix_bug',
            'xato': 'fix_bug',
            'tugrat': 'fix_bug',
            'refactor': 'refactor_code',
            'clean': 'refactor_code',
            'improve': 'improve_quality',
            'yaxshilat': 'improve_quality',
        }
        return mapping.get(keyword, 'general_improvement')
    
    def _extract_metric(self, request: str) -> Optional[str]:
        """
        Extract specific metrics from request.
        
        Examples:
            "reduce latency p95 by 20%" → "latency_p95_reduction >= 20%"
            "fix all critical bugs" → "critical_bugs = 0"
        """
        request_lower = request.lower()
        
        # Latency metrics
        latency_match = re.search(r'latency[_\s]?p(\d+)\s*<?=?\s*(\d+)', request_lower)
        if latency_match:
            percentile = latency_match.group(1)
            value = latency_match.group(2)
            return f"latency_p{percentile} < {value}ms"
        
        # Percentage improvements
        pct_match = re.search(r'(\d+)%\s*(?:kamaytir|reduce|decrease)', request_lower)
        if pct_match:
            pct = pct_match.group(1)
            return f"reduction >= {pct}%"
        
        # Error count
        if 'error' in request_lower or 'xato' in request_lower:
            if '0' in request or 'hech' in request_lower:
                return "errors = 0"
        
        # Speed improvement
        speed_match = re.search(r'(\d+)\s*(?:barobar|times|x)', request_lower)
        if speed_match:
            multiplier = speed_match.group(1)
            return f"speedup >= {multiplier}x"
        
        return None
    
    def _extract_scope(self, request: str, context: Optional[Dict]) -> tuple:
        """
        Extract allowed and forbidden scopes.
        
        Returns:
            (allowed_scope, forbidden_scope)
        """
        allowed = set()
        forbidden = set()
        
        request_lower = request.lower()
        
        # Extract explicit scope mentions
        # Example: "only in api.py" or "exclude test_*.py"
        
        # Check for "only" / "just" - restrict to specific files
        only_match = re.search(r'(?:only|just|faqat)\s+([^,\.]+)', request_lower)
        if only_match:
            scope = only_match.group(1).strip()
            allowed.add(scope)
        
        # Check for "exclude" / "without" / "except"
        exclude_match = re.search(r'(?:exclude|without|except|oldin)\s+([^,\.]+)', request_lower)
        if exclude_match:
            scope = exclude_match.group(1).strip()
            forbidden.add(scope)
        
        # Add context-based scope if available
        if context:
            if 'current_file' in context:
                allowed.add(context['current_file'])
            if 'module' in context:
                allowed.add(context['module'])
        
        return allowed, forbidden
    
    def _extract_patch_size(self, request: str) -> int:
        """
        Estimate maximum patch size.
        
        Based on request complexity.
        """
        request_lower = request.lower()
        
        # Small changes
        if any(kw in request_lower for kw in ['fix', 'typo', 'bug', 'xato', 'tugrat']):
            return 50
        
        # Medium changes
        if any(kw in request_lower for kw in ['refactor', 'improve', 'yaxshilat']):
            return 200
        
        # Large changes
        if any(kw in request_lower for kw in ['rewrite', 'migrate', 'migratsiya']):
            return 1000
        
        # Default
        return 100
    
    def _extract_rollback_class(self, request: str) -> str:
        """
        Determine rollback strategy.
        
        Options:
        - snapshot: Full state rollback
        - incremental: Step-by-step rollback
        - atomic: All-or-nothing
        """
        request_lower = request.lower()
        
        if 'atomic' in request_lower or 'hammasi' in request_lower:
            return 'atomic'
        
        if 'safe' in request_lower or 'xavfsiz' in request_lower:
            return 'incremental'
        
        return 'snapshot'
    
    def _generate_acceptance_criteria(self, request: str) -> List[str]:
        """
        Generate acceptance criteria from request.
        
        FIXED: Comprehensive criteria generation.
        """
        criteria = []
        request_lower = request.lower()
        
        # Performance criteria
        if 'fast' in request_lower or 'tez' in request_lower:
            criteria.append("performance_improvement_verified")
            criteria.append("no_regression_in_other_metrics")
        
        # Bugfix criteria
        if 'fix' in request_lower or 'bug' in request_lower or 'tugrat' in request_lower:
            criteria.append("all_tests_pass")
            criteria.append("no_new_warnings")
        
        # Security criteria
        if 'security' in request_lower or 'xavfsiz' in request_lower:
            criteria.append("security_scan_passed")
            criteria.append("no_vulnerabilities_introduced")
        
        # Refactor criteria
        if 'refactor' in request_lower:
            criteria.append("all_callers_updated")
            criteria.append("no_breaking_changes")
        
        # Default criteria
        if not criteria:
            criteria = [
                "code_compiles",
                "all_tests_pass",
                "no_regression"
            ]
        
        return criteria
    
    def get_compilation_stats(self) -> Dict:
        """Get compilation statistics."""
        return {
            'total_compilations': len(self.compilation_history),
            'recent_compilations': self.compilation_history[-10:]
        }
