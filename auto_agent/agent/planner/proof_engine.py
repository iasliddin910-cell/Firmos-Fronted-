"""
Proof Engine
============
Pre-commit verification and proof obligations.

This module is part of the Change Planner system.

Key responsibilities:
- Generate proof obligations
- Run verification checks
- Validate before promotion
- Collect evidence
"""

import logging
from typing import Dict, List, Set, Optional, Any, Callable
from dataclasses import dataclass

from agent.planner.contracts import (
    ProofObligation, EditContract, EditPlan,
    GoalSpec, ConstraintSpec, ChangeType
)

logger = logging.getLogger(__name__)


# Verification method templates
VERIFICATION_TEMPLATES = {
    'test_suite': {
        'category': 'test',
        'method': 'run_tests',
        'expected': 'all_pass'
    },
    'codeql_query': {
        'category': 'static_check',
        'method': 'run_codeql',
        'expected': 'no_vulnerabilities'
    },
    'symbol_check': {
        'category': 'symbol_resolution',
        'method': 'verify_symbols',
        'expected': 'all_resolve'
    },
    'benchmark': {
        'category': 'metric',
        'method': 'run_benchmark',
        'expected': 'improvement'
    },
    'lint': {
        'category': 'static_check',
        'method': 'run_linter',
        'expected': 'no_warnings'
    }
}


class ProofEngine:
    """
    Manages proof obligations and verification.
    
    This is Layer 8 of the Change Planner.
    
    FIXED: Complete proof generation and verification.
    """
    
    def __init__(self):
        self.proof_history: List[Dict] = []
        self.obligation_cache: Dict[str, List[ProofObligation]] = {}
    
    def generate_obligations(
        self,
        contract: EditContract,
        plan: EditPlan,
        change_type: ChangeType,
        goal_spec: GoalSpec,
        constraint_spec: ConstraintSpec
    ) -> List[ProofObligation]:
        """
        Generate proof obligations for the contract.
        
        Args:
            contract: EditContract
            plan: EditPlan
            change_type: Change type
            goal_spec: Goal specification
            constraint_spec: Constraints
            
        Returns:
            List of ProofObligation
        """
        logger.info(f"📋 ProofEngine: Generating proof obligations...")
        
        obligations = []
        import uuid
        
        # 1. Test obligations
        test_obligations = self._generate_test_obligations(
            contract, constraint_spec
        )
        obligations.extend(test_obligations)
        
        # 2. Static check obligations
        static_obligations = self._generate_static_obligations(
            contract, constraint_spec, change_type
        )
        obligations.extend(static_obligations)
        
        # 3. Symbol resolution obligations
        symbol_obligations = self._generate_symbol_obligations(
            contract, constraint_spec
        )
        obligations.extend(symbol_obligations)
        
        # 4. Metric obligations
        metric_obligations = self._generate_metric_obligations(
            goal_spec, constraint_spec
        )
        obligations.extend(metric_obligations)
        
        # 5. Security obligations (if applicable)
        if constraint_spec.security_symbols:
            security_obligations = self._generate_security_obligations(
                contract, constraint_spec
            )
            obligations.extend(security_obligations)
        
        # Record
        self.obligation_cache[contract.contract_id] = obligations
        
        logger.info(f"✅ ProofEngine: Generated {len(obligations)} proof obligations")
        
        return obligations
    
    def _generate_test_obligations(
        self,
        contract: EditContract,
        constraints: ConstraintSpec
    ) -> List[ProofObligation]:
        """Generate test-related obligations."""
        obligations = []
        import uuid
        
        # Required tests from constraints
        for i, test in enumerate(constraints.required_tests[:5]):
            obligations.append(ProofObligation(
                obligation_id=f"test_{uuid.uuid4().hex[:8]}",
                description=f"Run test: {test}",
                category='test',
                verification_method='test_suite',
                expected_result=f"{test} passes",
                blocking=True,
                severity='required'
            ))
        
        # Default test obligation if none specified
        if not obligations:
            obligations.append(ProofObligation(
                obligation_id=f"test_{uuid.uuid4().hex[:8]}",
                description="Run all project tests",
                category='test',
                verification_method='test_suite',
                expected_result="all tests pass",
                blocking=True,
                severity='required'
            ))
        
        return obligations
    
    def _generate_static_obligations(
        self,
        contract: EditContract,
        constraints: ConstraintSpec,
        change_type: ChangeType
    ) -> List[ProofObligation]:
        """Generate static check obligations."""
        obligations = []
        import uuid
        
        # Lint check
        obligations.append(ProofObligation(
            obligation_id=f"lint_{uuid.uuid4().hex[:8]}",
            description="Run linter",
            category='static_check',
            verification_method='lint',
            expected_result="no critical warnings",
            blocking=True,
            severity='required'
        ))
        
        # Type check for typed changes
        if change_type.value in ['semantic_refactor', 'species_level']:
            obligations.append(ProofObligation(
                obligation_id=f"type_{uuid.uuid4().hex[:8]}",
                description="Run type checker",
                category='static_check',
                verification_method='type_check',
                expected_result="no type errors",
                blocking=True,
                severity='required'
            ))
        
        return obligations
    
    def _generate_symbol_obligations(
        self,
        contract: EditContract,
        constraints: ConstraintSpec
    ) -> List[ProofObligation]:
        """Generate symbol resolution obligations."""
        obligations = []
        import uuid
        
        # Check target symbols
        for symbol in list(contract.target_symbols)[:3]:
            obligations.append(ProofObligation(
                obligation_id=f"symbol_{uuid.uuid4().hex[:8]}",
                description=f"Verify symbol resolves: {symbol}",
                category='symbol_resolution',
                verification_method='symbol_check',
                expected_result=f"{symbol} resolves",
                blocking=False,
                severity='recommended'
            ))
        
        return obligations
    
    def _generate_metric_obligations(
        self,
        goal_spec: GoalSpec,
        constraints: ConstraintSpec
    ) -> List[ProofObligation]:
        """Generate metric obligations."""
        obligations = []
        import uuid
        
        # Target metric from goal
        if goal_spec.target_metric:
            obligations.append(ProofObligation(
                obligation_id=f"metric_{uuid.uuid4().hex[:8]}",
                description=f"Verify metric: {goal_spec.target_metric}",
                category='metric',
                verification_method='benchmark',
                expected_result=goal_spec.target_metric,
                blocking=True,
                severity='required'
            ))
        
        # Performance baseline
        if constraints.hot_paths:
            obligations.append(ProofObligation(
                obligation_id=f"perf_{uuid.uuid4().hex[:8]}",
                description="Verify performance baseline maintained",
                category='metric',
                verification_method='benchmark',
                expected_result="performance >= baseline",
                blocking=True,
                severity='required'
            ))
        
        return obligations
    
    def _generate_security_obligations(
        self,
        contract: EditContract,
        constraints: ConstraintSpec
    ) -> List[ProofObligation]:
        """Generate security obligations."""
        obligations = []
        import uuid
        
        # Security scan
        obligations.append(ProofObligation(
            obligation_id=f"security_{uuid.uuid4().hex[:8]}",
            description="Run security scan",
            category='static_check',
            verification_method='codeql_query',
            expected_result="no security vulnerabilities",
            blocking=True,
            severity='required'
        ))
        
        # Check for specific security risks
        for symbol in list(constraints.security_symbols)[:2]:
            obligations.append(ProofObligation(
                obligation_id=f"sec_{uuid.uuid4().hex[:8]}",
                description=f"Verify security of: {symbol}",
                category='static_check',
                verification_method='codeql_query',
                expected_result=f"{symbol} secure",
                blocking=True,
                severity='required'
            ))
        
        return obligations
    
    async def verify_obligations(
        self,
        obligations: List[ProofObligation],
        verifier: Callable
    ) -> Dict[str, bool]:
        """
        Verify all obligations.
        
        Args:
            obligations: List of ProofObligation
            verifier: Verification function
            
        Returns:
            Dictionary of obligation_id -> passed
        """
        logger.info(f"🔍 ProofEngine: Verifying {len(obligations)} obligations...")
        
        results = {}
        
        for obligation in obligations:
            try:
                # Run verification
                passed, evidence = await verifier(obligation)
                
                # Update obligation
                obligation.passed = passed
                obligation.evidence = evidence
                
                results[obligation.obligation_id] = passed
                
                if not passed:
                    logger.warning(f"  ⚠️ Obligation failed: {obligation.description}")
                else:
                    logger.info(f"  ✅ Obligation passed: {obligation.description}")
                    
            except Exception as e:
                logger.error(f"  ❌ Obligation error: {obligation.description} - {e}")
                results[obligation.obligation_id] = False
        
        # Record history
        self.proof_history.append({
            'total': len(obligations),
            'passed': sum(1 for v in results.values() if v),
            'failed': sum(1 for v in results.values() if not v)
        })
        
        return results
    
    def can_promote(
        self,
        contract: EditContract,
        verification_results: Dict[str, bool]
    ) -> tuple:
        """
        Determine if patch can be promoted.
        
        Args:
            contract: EditContract
            verification_results: Results from verification
            
        Returns:
            (can_promote, reason)
        """
        # Get obligations for contract
        obligations = self.obligation_cache.get(contract.contract_id, [])
        
        # Check blocking obligations
        blocking_failed = []
        for obligation in obligations:
            if obligation.blocking:
                passed = verification_results.get(obligation.obligation_id, False)
                if not passed:
                    blocking_failed.append(obligation.description)
        
        if blocking_failed:
            return False, f"Blocking obligations failed: {', '.join(blocking_failed)}"
        
        # Check required obligations
        required_failed = []
        for obligation in obligations:
            if obligation.severity == 'required':
                passed = verification_results.get(obligation.obligation_id, False)
                if not passed:
                    required_failed.append(obligation.description)
        
        if required_failed:
            return False, f"Required obligations failed: {', '.join(required_failed)}"
        
        return True, "All blocking obligations passed"
    
    def get_proof_stats(self) -> Dict:
        """Get proof verification statistics."""
        return {
            'total_verifications': len(self.proof_history),
            'recent_verifications': self.proof_history[-10:]
        }
