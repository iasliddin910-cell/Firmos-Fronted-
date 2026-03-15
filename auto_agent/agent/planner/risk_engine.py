"""
Risk Engine
==========
Calculates blast radius and risk assessment.

This module is part of the Change Planner system.

Key responsibilities:
- Calculate blast radius
- Identify risk factors
- Assess reversibility
- Score overall risk
"""

import logging
from typing import Dict, List, Set, Optional, Any

from agent.planner.contracts import (
    RiskLevel, RiskAssessment, ChangeType,
    GoalSpec, ConstraintSpec, EditContract, EditPlan
)

logger = logging.getLogger(__name__)


# Risk multipliers
RISK_MULTIPLIERS = {
    'security_symbol': 2.0,
    'red_zone': 3.0,
    'hot_path': 1.5,
    'external_api': 1.8,
    'browser_auth': 2.5,
    'migration': 1.7,
}


class RiskEngine:
    """
    Calculates blast radius and risk.
    
    This is Layer 7 of the Change Planner.
    
    FIXED: Complete risk calculation.
    """
    
    def __init__(self):
        self.risk_history: List[Dict] = []
    
    def assess(
        self,
        contract: EditContract,
        plan: EditPlan,
        change_type: ChangeType,
        goal_spec: GoalSpec,
        constraint_spec: ConstraintSpec,
        code_analysis: Optional[Dict] = None
    ) -> RiskAssessment:
        """
        Main entry point: Assess risk.
        
        Args:
            contract: EditContract
            plan: EditPlan
            change_type: Change type
            goal_spec: Goal specification
            constraint_spec: Constraints
            code_analysis: Optional code understanding
            
        Returns:
            RiskAssessment with all metrics
        """
        logger.info(f"⚠️ RiskEngine: Assessing risk...")
        
        # Calculate blast radius
        blast_metrics = self._calculate_blast_radius(
            contract, plan, constraint_spec, code_analysis
        )
        
        # Identify risks
        security_risks, stability_risks, performance_risks = self._identify_risks(
            contract, constraint_spec, code_analysis
        )
        
        # Assess reversibility
        reversible, difficulty = self._assess_reversibility(
            plan, constraint_spec
        )
        
        # Calculate overall risk score
        risk_score = self._calculate_risk_score(
            blast_metrics,
            security_risks,
            stability_risks,
            performance_risks,
            reversible
        )
        
        # Determine risk level
        risk_level = self._determine_risk_level(risk_score)
        
        # Create assessment
        assessment = RiskAssessment(
            risk_level=risk_level,
            touched_symbols=blast_metrics['touched_symbols'],
            transitive_callers=blast_metrics['transitive_callers'],
            runtime_hot_paths=blast_metrics['hot_paths'],
            red_zone_overlap=blast_metrics['red_zone_overlap'],
            config_coupling=blast_metrics['config_coupling'],
            migration_impact=blast_metrics['migration_impact'],
            external_api_risk=blast_metrics['external_api_risk'],
            browser_auth_risk=blast_metrics['browser_auth_risk'],
            security_risks=security_risks,
            stability_risks=stability_risks,
            performance_risks=performance_risks,
            reversible=reversible,
            rollback_difficulty=difficulty,
            risk_score=risk_score
        )
        
        # Record history
        self.risk_history.append({
            'contract_id': contract.contract_id,
            'risk_level': risk_level.value,
            'risk_score': risk_score,
            'blast_radius': blast_metrics['total']
        })
        
        logger.info(f"✅ RiskEngine: Risk level {risk_level.value} (score: {risk_score:.1f})")
        
        return assessment
    
    def _calculate_blast_radius(
        self,
        contract: EditContract,
        plan: EditPlan,
        constraints: ConstraintSpec,
        analysis: Optional[Dict]
    ) -> Dict[str, Any]:
        """Calculate blast radius metrics."""
        metrics = {
            'touched_symbols': set(),
            'transitive_callers': set(),
            'hot_paths': set(),
            'red_zone_overlap': False,
            'config_coupling': False,
            'migration_impact': False,
            'external_api_risk': False,
            'browser_auth_risk': False,
            'total': 0
        }
        
        # Direct touched symbols
        metrics['touched_symbols'] = contract.target_symbols.copy()
        
        # Get transitive callers from constraints
        if analysis:
            call_graph = analysis.get('call_graph', {})
            for symbol in contract.target_symbols:
                callers = call_graph.get(symbol, [])
                metrics['transitive_callers'].update(callers)
        
        # Hot paths overlap
        metrics['hot_paths'] = constraints.hot_paths.intersection(contract.target_symbols)
        
        # Red zone overlap
        red_zone_symbols = {
            s.replace('symbol:', '').replace('function:', '').replace('class:', '')
            for s in constraints.red_zone_modules
        }
        metrics['red_zone_overlap'] = bool(
            contract.target_symbols.intersection(red_zone_symbols)
        )
        
        # Config coupling
        if constraints.dependency_constraints:
            metrics['config_coupling'] = True
        
        # Migration impact
        if constraints.migration_constraints:
            metrics['migration_impact'] = True
        
        # External API risk
        for risk in constraints.data_flow_risks:
            if 'external' in str(risk).lower():
                metrics['external_api_risk'] = True
        
        # Browser auth risk
        for symbol in contract.target_symbols:
            if any(kw in str(symbol).lower() for kw in ['auth', 'browser', 'session']):
                metrics['browser_auth_risk'] = True
        
        # Calculate total
        metrics['total'] = (
            len(metrics['touched_symbols']) +
            len(metrics['transitive_callers']) +
            len(metrics['hot_paths']) * 2 +
            (10 if metrics['red_zone_overlap'] else 0) +
            (5 if metrics['browser_auth_risk'] else 0)
        )
        
        return metrics
    
    def _identify_risks(
        self,
        contract: EditContract,
        constraints: ConstraintSpec,
        analysis: Optional[Dict]
    ) -> tuple:
        """Identify specific risks."""
        security = []
        stability = []
        performance = []
        
        # Security risks
        for symbol in constraints.security_symbols:
            if symbol in contract.target_symbols:
                security.append(f"security_symbol_modified:{symbol}")
        
        if constraints.data_flow_risks:
            security.extend(constraints.data_flow_risks[:3])
        
        # Stability risks
        if constraints.red_zone_modules:
            for zone in constraints.red_zone_modules:
                stability.append(f"red_zone_touched:{zone}")
        
        # Performance risks
        overlap = constraints.hot_paths.intersection(contract.target_symbols)
        for path in overlap:
            performance.append(f"hot_path_modified:{path}")
        
        return security, stability, performance
    
    def _assess_reversibility(
        self,
        plan: EditPlan,
        constraints: ConstraintSpec
    ) -> tuple:
        """Assess reversibility."""
        # More phases = harder to reverse
        phase_count = len(plan.phases)
        
        # Check for irreversible changes
        if constraints.migration_constraints:
            return False, "hard"
        
        if phase_count >= 4:
            return False, "medium"
        
        if phase_count >= 2:
            return True, "easy"
        
        return True, "easy"
    
    def _calculate_risk_score(
        self,
        blast: Dict,
        security: List,
        stability: List,
        performance: List,
        reversible: bool
    ) -> float:
        """Calculate overall risk score (0-100)."""
        score = 0.0
        
        # Base from blast radius
        score += min(blast['total'] * 2, 30)
        
        # Security risks (highest weight)
        score += len(security) * 15
        
        # Stability risks
        score += len(stability) * 10
        
        # Performance risks
        score += len(performance) * 8
        
        # Red zone
        if blast['red_zone_overlap']:
            score += 20
        
        # Browser auth (highest)
        if blast['browser_auth_risk']:
            score += 25
        
        # External API
        if blast['external_api_risk']:
            score += 15
        
        # Non-reversible
        if not reversible:
            score += 10
        
        return min(100, score)
    
    def _determine_risk_level(self, score: float) -> RiskLevel:
        """Determine risk level from score."""
        if score >= 80:
            return RiskLevel.CRITICAL
        elif score >= 60:
            return RiskLevel.HIGH
        elif score >= 40:
            return RiskLevel.MEDIUM
        elif score >= 20:
            return RiskLevel.LOW
        else:
            return RiskLevel.NEGLIGIBLE
    
    def get_risk_stats(self) -> Dict:
        """Get risk assessment statistics."""
        return {
            'total_assessments': len(self.risk_history),
            'recent_assessments': self.risk_history[-10:]
        }
