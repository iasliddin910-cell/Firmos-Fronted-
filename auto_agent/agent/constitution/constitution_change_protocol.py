"""
OmniAgent X - Constitution Change Protocol
=====================================
Bu fayl konstitutsiyani o'zgartirish protokolini belgilaydi.

Constitution o'zgartirish 4 bosqichda o'tadi:
1. Constitution Change Proposal yaratish
2. Impact analysis
3. Protected review
4. Explicit adoption
"""
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from .constitution_rules import CONSTITUTION_RULES, RuleMetadata


class ChangeType(Enum):
    """O'zgartirish turlari"""
    ADD_RULE = "add_rule"           # Yangi qonun qo'shish
    MODIFY_RULE = "modify_rule"     # Qonunni o'zgartirish
    REMOVE_RULE = "remove_rule"     # Qonunni olib tashlash
    CHANGE_PROFILE = "change_profile"  # Profil o'zgartirish
    CHANGE_BUDGET = "change_budget"   # Budget o'zgartirish
    CHANGE_ZONE = "change_zone"        # Protected zone o'zgartirish


class ChangeStatus(Enum):
    """O'zgartirish holati"""
    DRAFT = "draft"
    PROPOSED = "proposed"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    ADOPTED = "adopted"


class ImpactLevel(Enum):
    """Ta'sir darajasi"""
    LOW = "low"       # Kam ta'sir
    MEDIUM = "medium" # O'rtacha ta'sir
    HIGH = "high"     # Yuqori ta'sir
    CRITICAL = "critical"  # Kritik ta'sir


@dataclass
class ImpactAnalysis:
    """Ta'sir tahlili"""
    affected_modules: List[str] = field(default_factory=list)
    affected_rules: List[str] = field(default_factory=list)
    invariant_risks: List[str] = field(default_factory=list)
    backward_compatible: bool = True
    impact_level: ImpactLevel = ImpactLevel.LOW
    mitigation_plan: str = ""


@dataclass
class ConstitutionChangeProposal:
    """Constitution o'zgartirish taklifi"""
    proposal_id: str
    title: str
    description: str
    
    # O'zgartirish tafsilotlari
    change_type: ChangeType
    rule_id: Optional[str] = None  # Qaysi qonun
    new_rule: Optional[RuleMetadata] = None  # Yangi qonun (agar ADD)
    old_rule: Optional[RuleMetadata] = None   # Eski qonun (agar MODIFY/REMOVE)
    
    # Nega o'zgaradi
    reason: str = ""
    risks: List[str] = field(default_factory=list)
    evidence: List[str] = field(default_factory=list)
    benefits: List[str] = field(default_factory=list)
    
    # Impact analysis
    impact_analysis: Optional[ImpactAnalysis] = None
    
    # Holat
    status: ChangeStatus = ChangeStatus.DRAFT
    proposer: str = "agent"
    reviewers: List[str] = field(default_factory=list)
    approver: Optional[str] = None
    
    # Vaqt
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    reviewed_at: Optional[str] = None
    adopted_at: Optional[str] = None
    
    # Version
    constitution_version: str = "1.0.0"


@dataclass
class ConstitutionalReview:
    """Constitutional review"""
    review_id: str
    proposal_id: str
    
    # Review natijalari
    technical_soundness: bool = True
    safety_assessment: bool = True
    backward_compatibility: bool = True
    
    # Reviewer
    reviewer: str = ""
    review_notes: str = ""
    approval: bool = False
    
    # Vaqt
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None


class ConstitutionChangeProtocol:
    """
    Constitution o'zgartirish protokoli
    
    Bu klass constitutional change workflow'ni boshqaradi.
    """
    
    def __init__(self):
        self.proposals: Dict[str, ConstitutionChangeProposal] = {}
        self.reviews: Dict[str, ConstitutionalReview] = {}
        self.version_history: List[Dict[str, Any]] = []
        
        # Current constitution version
        self.current_version = "1.0.0"
    
    # =============================================
    # 1-BOSQICH: Proposal yaratish
    # =============================================
    
    def create_proposal(
        self,
        title: str,
        description: str,
        change_type: ChangeType,
        reason: str,
        proposer: str = "agent",
        rule_id: Optional[str] = None,
        new_rule: Optional[RuleMetadata] = None,
        old_rule: Optional[RuleMetadata] = None
    ) -> ConstitutionChangeProposal:
        """Constitution Change Proposal yaratish"""
        
        proposal_id = f"CCP-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        proposal = ConstitutionChangeProposal(
            proposal_id=proposal_id,
            title=title,
            description=description,
            change_type=change_type,
            rule_id=rule_id,
            new_rule=new_rule,
            old_rule=old_rule,
            reason=reason,
            proposer=proposer,
            status=ChangeStatus.DRAFT
        )
        
        self.proposals[proposal_id] = proposal
        return proposal
    
    def add_evidence(self, proposal_id: str, evidence: str) -> bool:
        """Proposal'ga dalil qo'shish"""
        if proposal_id not in self.proposals:
            return False
        
        proposal = self.proposals[proposal_id]
        proposal.evidence.append(evidence)
        proposal.updated_at = datetime.now().isoformat()
        return True
    
    def add_risk(self, proposal_id: str, risk: str) -> bool:
        """Proposal'ga risk qo'shish"""
        if proposal_id not in self.proposals:
            return False
        
        proposal = self.proposals[proposal_id]
        proposal.risks.append(risk)
        proposal.updated_at = datetime.now().isoformat()
        return True
    
    def add_benefit(self, proposal_id: str, benefit: str) -> bool:
        """Proposal'ga foyda qo'shish"""
        if proposal_id not in self.proposals:
            return False
        
        proposal = self.proposals[proposal_id]
        proposal.benefits.append(benefit)
        proposal.updated_at = datetime.now().isoformat()
        return True
    
    # =============================================
    # 2-BOSQICH: Impact Analysis
    # =============================================
    
    def perform_impact_analysis(self, proposal_id: str) -> Optional[ImpactAnalysis]:
        """Ta'sir tahlili o'tkazish"""
        
        if proposal_id not in self.proposals:
            return None
        
        proposal = self.proposals[proposal_id]
        
        # Ta'sirlanadigan modullarni aniqlash
        affected_modules = []
        affected_rules = []
        invariant_risks = []
        
        if proposal.change_type == ChangeType.ADD_RULE:
            affected_rules.append(proposal.rule_id or "new_rule")
            # Yangi qonun mavjud qonunlar bilan ziddiyatli emasligini tekshirish
            for existing_rule in CONSTITUTION_RULES.values():
                if existing_rule.rule_class.name == proposal.new_rule.rule_class.name:
                    invariant_risks.append(f"Potential conflict with {existing_rule.rule_id}")
        
        elif proposal.change_type == ChangeType.MODIFY_RULE:
            affected_rules.append(proposal.rule_id or "")
            invariant_risks.append(f"Modified rule may affect {proposal.rule_id} dependent modules")
        
        elif proposal.change_type == ChangeType.REMOVE_RULE:
            affected_rules.append(proposal.rule_id or "")
            invariant_risks.append(f"Removing rule may break dependent systems")
        
        elif proposal.change_type == ChangeType.CHANGE_BUDGET:
            affected_modules.append("budget_manager")
            invariant_risks.append("Budget changes may affect system stability")
        
        # Impact level hisoblash
        impact_level = ImpactLevel.LOW
        if len(affected_modules) > 3 or len(invariant_risks) > 2:
            impact_level = ImpactLevel.HIGH
        elif len(affected_modules) > 1 or len(invariant_risks) > 0:
            impact_level = ImpactLevel.MEDIUM
        
        impact_analysis = ImpactAnalysis(
            affected_modules=affected_modules,
            affected_rules=affected_rules,
            invariant_risks=invariant_risks,
            backward_compatible=len(invariant_risks) == 0,
            impact_level=impact_level
        )
        
        proposal.impact_analysis = impact_analysis
        return impact_analysis
    
    # =============================================
    # 3-BOSQICH: Protected Review
    # =============================================
    
    def submit_for_review(self, proposal_id: str) -> bool:
        """Review uchun taqdim etish"""
        
        if proposal_id not in self.proposals:
            return False
        
        proposal = self.proposals[proposal_id]
        
        # Impact analysis majburiy
        if proposal.impact_analysis is None:
            self.perform_impact_analysis(proposal_id)
        
        proposal.status = ChangeStatus.UNDER_REVIEW
        return True
    
    def create_review(
        self,
        proposal_id: str,
        reviewer: str = "human_reviewer"
    ) -> Optional[ConstitutionalReview]:
        """Review yaratish"""
        
        if proposal_id not in self.proposals:
            return None
        
        review_id = f"Review-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        review = ConstitutionalReview(
            review_id=review_id,
            proposal_id=proposal_id,
            reviewer=reviewer
        )
        
        self.reviews[review_id] = review
        return review
    
    def complete_review(
        self,
        review_id: str,
        approval: bool,
        review_notes: str,
        technical_soundness: bool = True,
        safety_assessment: bool = True,
        backward_compatibility: bool = True
    ) -> bool:
        """Review'ni yakunlash"""
        
        if review_id not in self.reviews:
            return False
        
        review = self.reviews[review_id]
        review.approval = approval
        review.review_notes = review_notes
        review.technical_soundness = technical_soundness
        review.safety_assessment = safety_assessment
        review.backward_compatibility = backward_compatibility
        review.completed_at = datetime.now().isoformat()
        
        # Proposal'ni yangilash
        proposal_id = review.proposal_id
        if proposal_id in self.proposals:
            proposal = self.proposals[proposal_id]
            if approval:
                proposal.status = ChangeStatus.APPROVED
            else:
                proposal.status = ChangeStatus.REJECTED
        
        return True
    
    # =============================================
    # 4-BOSQICH: Explicit Adoption
    # =============================================
    
    def adopt_change(self, proposal_id: str, approver: str = "human") -> bool:
        """O'zgartirishni qabul qilish"""
        
        if proposal_id not in self.proposals:
            return False
        
        proposal = self.proposals[proposal_id]
        
        # Faqat approved proposal qabul qilinadi
        if proposal.status != ChangeStatus.APPROVED:
            return False
        
        # Version yangilash
        old_version = self.current_version
        self._bump_version()
        
        # Adoption
        proposal.status = ChangeStatus.ADOPTED
        proposal.adopted_at = datetime.now().isoformat()
        proposal.approver = approver
        
        # Historyga qo'shish
        self.version_history.append({
            "proposal_id": proposal_id,
            "old_version": old_version,
            "new_version": self.current_version,
            "adopted_at": proposal.adopted_at,
            "adopted_by": approver
        })
        
        return True
    
    def _bump_version(self):
        """Version ni oshirish"""
        parts = self.current_version.split(".")
        if len(parts) == 3:
            major, minor, patch = parts
            # Minor version oshirish (constitutional changes)
            self.current_version = f"{major}.{int(minor)+1}.{patch}"
    
    # =============================================
    # YORDAMCHI METODLAR
    # =============================================
    
    def get_proposal(self, proposal_id: str) -> Optional[ConstitutionChangeProposal]:
        """Proposal olish"""
        return self.proposals.get(proposal_id)
    
    def get_proposals_by_status(self, status: ChangeStatus) -> List[ConstitutionChangeProposal]:
        """Holat bo'yicha proposallar"""
        return [p for p in self.proposals.values() if p.status == status]
    
    def get_pending_proposals(self) -> List[ConstitutionChangeProposal]:
        """Kutilayotgan proposallar"""
        return self.get_proposals_by_status(ChangeStatus.UNDER_REVIEW)
    
    def get_version_history(self) -> List[Dict[str, Any]]:
        """Version tarixi"""
        return self.version_history.copy()
    
    def get_current_version(self) -> str:
        """Joriy version"""
        return self.current_version


# Global protocol
_protocol: Optional[ConstitutionChangeProtocol] = None


def get_constitution_change_protocol() -> ConstitutionChangeProtocol:
    """Global protocol olish"""
    global _protocol
    if _protocol is None:
        _protocol = ConstitutionChangeProtocol()
    return _protocol


def create_constitution_change_proposal(
    title: str,
    description: str,
    change_type: ChangeType,
    reason: str,
    rule_id: Optional[str] = None
) -> ConstitutionChangeProposal:
    """Constitution change proposal yaratish (tez funksiya)"""
    protocol = get_constitution_change_protocol()
    return protocol.create_proposal(title, description, change_type, reason, rule_id=rule_id)


# ============================================
# PREDEFINED CONSTITUTIONAL CHANGES
# ============================================

def propose_add_rule(
    rule: RuleMetadata,
    reason: str,
    evidence: List[str]
) -> ConstitutionChangeProposal:
    """Yangi qonun qo'shish taklifi"""
    protocol = get_constitution_change_protocol()
    
    proposal = protocol.create_proposal(
        title=f"Add Rule: {rule.name}",
        description=rule.description,
        change_type=ChangeType.ADD_RULE,
        reason=reason,
        new_rule=rule,
        rule_id=rule.rule_id
    )
    
    for ev in evidence:
        protocol.add_evidence(proposal.proposal_id, ev)
    
    return proposal


def propose_modify_rule(
    rule_id: str,
    old_rule: RuleMetadata,
    new_description: str,
    reason: str,
    evidence: List[str]
) -> ConstitutionChangeProposal:
    """Qonunni o'zgartirish taklifi"""
    protocol = get_constitution_change_protocol()
    
    new_rule = RuleMetadata(
        rule_id=old_rule.rule_id,
        name=old_rule.name,
        description=new_description,
        rule_class=old_rule.rule_class,
        profiles=old_rule.profiles,
        severity_on_violation=old_rule.severity_on_violation
    )
    
    proposal = protocol.create_proposal(
        title=f"Modify Rule: {rule_id}",
        description=new_description,
        change_type=ChangeType.MODIFY_RULE,
        reason=reason,
        rule_id=rule_id,
        new_rule=new_rule,
        old_rule=old_rule
    )
    
    for ev in evidence:
        protocol.add_evidence(proposal.proposal_id, ev)
    
    return proposal
