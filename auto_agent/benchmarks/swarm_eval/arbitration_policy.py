"""
ArbitrationPolicy - Consensus/Arbitration

Bu modul workerlar qarama-qarshi xulosa chiqarsa qanday hal qilishni boshqaradi:
- verifier ustunmi?
- critic ustunmi?
- tests ustunmi?
- hidden verifier ustunmi?

Policy 9: Arbitration correctness eval yo'q.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum


class AuthorityRole(Enum):
    """Roles that can have final authority"""
    VERIFIER = "verifier"
    CRITIC = "critic"
    TESTS = "tests"
    HIDDEN_VERIFIER = "hidden_verifier"
    COORDINATOR = "coordinator"


class Decision(Enum):
    """Arbitration decisions"""
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_REVIEW = "needs_review"
    ESCALATE = "escalate"


@dataclass
class ArbitrationCase:
    """A case requiring arbitration"""
    case_id: str
    parties: List[Dict[str, Any]]  # Each party's decision
    evidence: Dict[str, Any]
    decision: Optional[Decision] = None
    authority_used: Optional[AuthorityRole] = None


class ArbitrationPolicy:
    """
    Manages arbitration when workers disagree.
    
    Agar workerlar qarama-qarshi xulosa chiqarsa:
    - verifier ustunmi?
    - critic ustunmi?
    - tests ustunmi?
    - hidden verifier ustunmi?
    """
    
    # Default authority hierarchy
    DEFAULT_HIERARCHY = [
        AuthorityRole.TESTS,           # Tests have highest authority
        AuthorityRole.VERIFIER,       # Then verifier
        AuthorityRole.HIDDEN_VERIFIER, # Then hidden verifier
        AuthorityRole.CRITIC,         # Then critic
        AuthorityRole.COORDINATOR    # Finally coordinator
    ]
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.hierarchy = self.config.get('hierarchy', self.DEFAULT_HIERARCHY)
        self.cases: List[ArbitrationCase] = []
        
    def arbitrate(
        self,
        parties: List[Dict[str, Any]],
        evidence: Optional[Dict[str, Any]] = None
    ) -> ArbitrationCase:
        """
        Arbitrate between parties with conflicting decisions.
        
        Args:
            parties: List of parties with their decisions
            evidence: Additional evidence for arbitration
            
        Returns:
            ArbitrationCase with final decision
        """
        case_id = f"case_{len(self.cases)}"
        
        case = ArbitrationCase(
            case_id=case_id,
            parties=parties,
            evidence=evidence or {}
        )
        
        # Apply hierarchy
        decision, authority = self._apply_hierarchy(parties)
        
        case.decision = decision
        case.authority_used = authority
        
        self.cases.append(case)
        
        return case
    
    def _apply_hierarchy(
        self,
        parties: List[Dict[str, Any]]
    ) -> tuple:
        """Apply authority hierarchy to resolve conflict"""
        # Find which authorities are present
        present_authorities = {}
        
        for party in parties:
            role = party.get('role', '')
            decision = party.get('decision', '')
            
            try:
                authority = AuthorityRole(role)
                if authority not in present_authorities:
                    present_authorities[authority] = []
                present_authorities[authority].append(decision)
            except ValueError:
                continue
        
        # Apply hierarchy in order
        for authority in self.hierarchy:
            if authority in present_authorities:
                decisions = present_authorities[authority]
                
                # Check if there's consensus
                if len(set(decisions)) == 1:
                    # Consensus found
                    if decisions[0] == 'approve':
                        return Decision.APPROVED, authority
                    else:
                        return Decision.REJECTED, authority
        
        # No consensus - escalate
        return Decision.ESCALATE, AuthorityRole.COORDINATOR
    
    def get_arbitration_stats(self) -> Dict[str, Any]:
        """Get arbitration statistics"""
        if not self.cases:
            return {"total_cases": 0}
        
        decisions = {}
        authorities = {}
        
        for case in self.cases:
            if case.decision:
                d = case.decision.value
                decisions[d] = decisions.get(d, 0) + 1
            
            if case.authority_used:
                a = case.authority_used.value
                authorities[a] = authorities.get(a, 0) + 1
        
        return {
            "total_cases": len(self.cases),
            "decisions": decisions,
            "authorities_used": authorities
        }


__all__ = [
    'ArbitrationPolicy',
    'AuthorityRole',
    'Decision',
    'ArbitrationCase'
]
