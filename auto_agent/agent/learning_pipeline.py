"""OmniAgent X - Enhanced Continuous Learning Pipeline
===============================================
24/7 autonomous learning with all features

EVIDENCE & PROVENANCE LAYER - World No1+ Implementation
=========================================================
This module implements comprehensive evidence tracking and provenance
for all knowledge in the system. Each piece of knowledge now includes:
- Claim-level provenance
- Evidence packets with source snapshots
- Verification receipts
- Lineage tracking for derived knowledge
- Corroboration engine
- Negative evidence registry
- Truth case file system
"""

import os
import json
import logging
import time
import hashlib
import asyncio
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from collections import defaultdict
from pathlib import Path
import threading
import re

logger = logging.getLogger(__name__)


class SourceType(Enum):
    DOCUMENTATION = "documentation"
    BLOG = "blog"
    FORUM = "forum"
    GITHUB = "github"
    STACKOVERFLOW = "stackoverflow"
    PAPER = "paper"
    NEWS = "news"
    WIKI = "wiki"
    API_DOCS = "api_docs"


class TrustLevel(Enum):
    HIGH = 3
    MEDIUM = 2
    LOW = 1
    UNKNOWN = 0


class KnowledgeType(Enum):
    FACT = "fact"
    PROCEDURE = "procedure"
    CONCEPT = "concept"
    OPINION = "opinion"
    CODE = "code"


class ConfidenceLevel(Enum):
    VERY_HIGH = 1.0
    HIGH = 0.8
    MEDIUM = 0.6
    LOW = 0.4
    VERY_LOW = 0.2


class ClaimStatus(Enum):
    VERIFIED = "verified"
    DISPUTED = "disputed"
    WEAKLY_SUPPORTED = "weakly_supported"
    SUPERSEDED = "superseded"
    PENDING = "pending"
    REJECTED = "rejected"


class ClaimKind(Enum):
    FACTUAL = "factual"
    PROCEDURAL = "procedural"
    HYPOTHETICAL = "hypothetical"
    DEPRECATED = "deprecated"
    UNCERTAIN = "uncertain"


class EvidenceType(Enum):
    DIRECT = "direct"           # Direct statement from source
    INFERRED = "inferred"       # Inferred from content
    CORROBORATED = "corroborated"  # Multiple sources confirm
    REFUTING = "refuting"      # Evidence against claim
    DERIVED = "derived"        # Derived from other knowledge
    USER_CORRECTION = "user_correction"  # User provided correction
    PRODUCTION = "production"  # From production outcome
    MANUAL = "manual"          # Manually verified


class VerificationMethod(Enum):
    AUTOMATIC = "automatic"
    MANUAL = "manual"
    PRODUCTION_TESTED = "production_tested"
    CROSS_REFERENCE = "cross_reference"
    USER_CONFIRMATION = "user_confirmation"
    BENCHMARK_VALIDATED = "benchmark_validated"


class ResolutionRule(Enum):
    PREFER_HIGHER_CONFIDENCE = "prefer_higher_confidence"
    PREFER_MORE_EVIDENCE = "prefer_more_evidence"
    PREFER_VERIFIED = "prefer_verified"
    PREFER_OFFICIAL_SOURCE = "prefer_official_source"
    PREFER_RECENT = "prefer_recent"
    PREFER_MORE_USAGE = "prefer_more_usage"
    PREFER_CORROBORATED = "prefer_corroborated"
    MERGE_CLAIMS = "merge_claims"
    DEMOTE_BOTH = "demote_both"


class ProvenanceStatus(Enum):
    PRIMARY = "primary"           # Directly from source
    DERIVED = "derived"           # Derived from other knowledge
    SYNTHESIZED = "synthesized"  # Synthesized from multiple sources
    CORRECTED = "corrected"       # User corrected
    INFERRED = "inferred"         # Inferred by system


# ==================== NEW EVIDENCE & PROVENANCE MODELS ====================

@dataclass
class SourceSnapshot:
    """
    Source Snapshot - Evidence Layer
    ================================
    Represents a captured snapshot of a source at fetch time.
    This is the FIRST link in the evidence chain.
    """
    snapshot_id: str
    source_url: str
    canonical_domain: str
    
    # Raw content captured at fetch time
    raw_content: str
    normalized_content: str
    
    # Content fingerprints
    content_hash: str          # SHA256 of normalized content
    raw_content_hash: str       # SHA256 of raw content
    
    # Fetch metadata
    fetched_at: float
    fetch_method: str           # e.g., "requests", "selenium", "api"
    parser_version: str         # Parser version used
    http_status: int
    fetch_duration_ms: int
    
    # HTTP metadata
    content_type: str = ""
    last_modified: str = ""
    etag: str = ""
    
    # Redirect tracking
    redirect_chain: List[str] = field(default_factory=list)
    
    # Extraction metadata
    extraction_status: str = "success"  # success, partial, failed
    extraction_error: str = ""
    extracted_spans: int = 0
    
    # License/policy
    source_policy_flags: Dict[str, bool] = field(default_factory=dict)
    
    # Parser metadata
    parser_name: str = ""
    parser_config: Dict = field(default_factory=dict)


@dataclass
class Claim:
    """
    Claim - Granular Knowledge Unit
    ===============================
    Each knowledge entry contains multiple claims, not just a blob.
    This enables claim-level provenance and verification.
    """
    claim_id: str
    entry_id: str              # Parent knowledge entry
    
    # Claim content
    claim_text: str
    claim_kind: ClaimKind
    scope: str                 # The specific scope/aspect this claim covers
    
    # Position in source (for traceability)
    span_start: int = 0        # Character offset in source
    span_end: int = 0
    
    # Status and confidence
    status: ClaimStatus = ClaimStatus.PENDING
    confidence: float = 0.5
    
    # Evidence links
    evidence_ids: List[str] = field(default_factory=list)
    supporting_evidence_ids: List[str] = field(default_factory=list)
    refuting_evidence_ids: List[str] = field(default_factory=list)
    
    # Claim relationships
    supports_claims: List[str] = field(default_factory=list)  # Claims this supports
    contradicts_claims: List[str] = field(default_factory=list)  # Contradicted claims
    
    # Supersession tracking
    supersedes_claim_id: str = ""  # If this claim supersedes another
    superseded_by: str = ""         # If this claim is superseded
    
    # Provenance
    provenance_status: ProvenanceStatus = ProvenanceStatus.PRIMARY
    derived_from_entry_id: str = ""  # If derived, from what
    
    # Verification state
    verification_count: int = 0
    last_verified_at: float = 0.0
    verification_method: VerificationMethod = VerificationMethod.AUTOMATIC
    
    # Temporal
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


@dataclass
class EvidenceRecord:
    """
    Evidence Record - Verifiable Proof
    ====================================
    Connects a claim to its source evidence.
    This is the core of the evidence chain.
    """
    evidence_id: str
    claim_id: str
    
    # Source reference
    source_snapshot_id: str
    
    # Evidence content
    evidence_type: EvidenceType
    extracted_span: str         # The specific text/span from source
    extraction_method: str       # How was this extracted
    extractor_version: str       # Extractor version
    
    # Strength assessment
    strength_score: float = 0.5  # 0-1, how strong is this evidence
    direction: str = "support"   # support, refute, neutral
    
    # Context
    context_before: str = ""     # Text before the evidence
    context_after: str = ""      # Text after the evidence
    page_section: str = ""       # Which section of page
    
    # Confidence contribution
    confidence_contribution: float = 0.0
    
    # Verification
    is_verified: bool = False
    verification_method: VerificationMethod = VerificationMethod.AUTOMATIC
    verified_at: float = 0.0
    verified_by: str = ""         # Who/what verified
    
    # Temporal
    created_at: float = field(default_factory=time.time)


@dataclass
class VerificationReceipt:
    """
    Verification Receipt - Audit Trail
    ===================================
    Every verification action creates a receipt.
    This makes confidence explainable and auditable.
    """
    receipt_id: str
    target_type: str             # "claim", "evidence", "entry"
    target_id: str               # ID of verified item
    
    # Verification details
    method: VerificationMethod
    inputs: Dict = field(default_factory=dict)  # What was checked
    
    # Results
    checks_passed: List[str] = field(default_factory=list)
    checks_failed: List[str] = field(default_factory=list)
    
    # Verdict
    result: str                  # "verified", "failed", "partial", "rejected"
    verdict: str = ""            # Human-readable verdict
    confidence_delta: float = 0.0  # How much confidence changed
    
    # Details
    notes: str = ""
    errors: List[str] = field(default_factory=list)
    
    # Who/what verified
    verified_by: str = "system"  # system, user, benchmark
    verification_tool: str = ""
    model_version: str = ""
    
    # Timing
    verified_at: float = field(default_factory=time.time)
    duration_ms: int = 0


@dataclass
class ProvenanceLineage:
    """
    Provenance Lineage - Knowledge Family Tree
    ===========================================
    Tracks the derivation chain of knowledge.
    Essential for understanding where knowledge came from.
    """
    lineage_id: str
    child_entity_id: str        # The derived knowledge
    child_entity_type: str      # "claim", "evidence", "entry"
    
    # Parent reference
    parent_entity_id: str = ""
    parent_entity_type: str = ""
    
    # Additional parents (for multi-source derivation)
    additional_parent_ids: List[str] = field(default_factory=list)
    
    # Transformation details
    relation_type: str = "derived_from"  # derived_from, synthesized_from, corrected_from
    transformation_type: str = ""  # summary, procedure, inference, correction
    transformation_prompt: str = ""  # If LLM-based, what prompt was used
    
    # Tool/model info
    tool_name: str = ""
    tool_version: str = ""
    model_name: str = ""
    model_version: str = ""
    
    # Chain tracking
    lineage_depth: int = 1
    root_entity_id: str = ""    # Original source
    lineage_chain: List[str] = field(default_factory=list)  # Full chain
    
    # Metadata
    created_at: float = field(default_factory=time.time)
    confidence_at_creation: float = 0.5


@dataclass
class TruthCaseFile:
    """
    Truth Case File - Dispute Resolution System
    ===========================================
    For disputed or important knowledge, a case file is maintained.
    This enables audit, governance, and systematic resolution.
    """
    case_id: str
    primary_claim_id: str
    
    # Case summary
    case_summary: str
    case_type: str              # "disputed", "superseded", "verification_needed"
    priority: str = "normal"    # "urgent", "high", "normal", "low"
    
    # Current state
    current_verdict: str = "pending"  # pending, verified, rejected, disputed
    verdict_confidence: float = 0.5
    
    # Evidence bundles
    supporting_evidence_ids: List[str] = field(default_factory=list)
    refuting_evidence_ids: List[str] = field(default_factory=list)
    neutral_evidence_ids: List[str] = field(default_factory=list)
    
    # Source hierarchy
    source_hierarchy: List[Dict] = field(default_factory=list)  # Ranked sources
    
    # Verification receipts
    verification_receipt_ids: List[str] = field(default_factory=list)
    
    # Production outcomes
    production_outcome_ids: List[str] = field(default_factory=list)
    
    # Resolution
    resolution_rule: str = ""   # Which rule was applied
    resolution_evidence: str = ""  # What evidence led to resolution
    resolved_at: float = 0.0
    resolver: str = ""          # Who resolved
    
    # Questions that remain
    unresolved_questions: List[str] = field(default_factory=list)
    next_actions: List[str] = field(default_factory=list)
    
    # Timeline
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    last_activity_at: float = field(default_factory=time.time)


@dataclass
class ConfidenceReceipt:
    """
    Confidence Receipt - Explainable Confidence
    ============================================
    Every confidence score comes with a receipt showing
    exactly how it was calculated.
    """
    receipt_id: str
    entry_id: str
    
    # Components
    source_trust_score: float = 0.0
    freshness_score: float = 0.0
    verification_score: float = 0.0
    evidence_strength_score: float = 0.0
    corroboration_score: float = 0.0
    contradiction_penalty: float = 0.0
    staleness_penalty: float = 0.0
    missing_verification_penalty: float = 0.0
    
    # Totals
    base_score: float = 0.0
    penalties_total: float = 0.0
    bonuses_total: float = 0.0
    final_score: float = 0.5
    
    # Breakdown (for debugging)
    component_details: Dict = field(default_factory=dict)
    
    # Context
    calculated_at: float = field(default_factory=time.time)
    calculation_method: str = "standard"


# ==================== ENHANCED EXISTING MODELS ====================

@dataclass
class Source:
    """
    Source - Enhanced with Provenance Support
    ==========================================
    Now includes snapshot tracking and source-proof capabilities.
    """
    url: str
    name: str
    source_type: SourceType
    trust_level: TrustLevel = TrustLevel.UNKNOWN
    freshness_score: float = 0.5
    relevance_score: float = 0.5
    update_frequency: float = 0.5
    last_scraped: float = 0.0
    page_rank: float = 0.0
    citations: int = 0
    topics: List[str] = field(default_factory=list)
    
    # === PROVENANCE FIELDS (NEW) ===
    # Source identity
    source_id: str = ""              # Unique identifier
    canonical_domain: str = ""        # Normalized domain
    
    # Snapshot tracking
    snapshot_ids: List[str] = field(default_factory=list)  # All snapshots
    last_fetch_hash: str = ""         # Hash of last fetch
    fetch_history_count: int = 0
    
    # Parser/version tracking
    parser_version: str = ""
    preferred_parser: str = ""
    
    # Policy flags
    source_policy_flags: Dict[str, bool] = field(default_factory=dict)
    
    # Quality metrics
    avg_extraction_success_rate: float = 0.0
    total_claims_extracted: int = 0
    verified_claims_count: int = 0


@dataclass
class KnowledgeEntry:
    """
    Knowledge Entry - Enhanced with Evidence Chain
    ===============================================
    Now supports claims, evidence, verification, and lineage.
    """
    entry_id: str
    content: str
    knowledge_type: KnowledgeType
    source: str
    source_url: str
    collected_at: float
    last_verified: float
    confidence: float
    embedding: List[float] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    entities: List[str] = field(default_factory=list)
    relationships: List[Dict] = field(default_factory=list)
    contradiction_hash: str = ""
    stale_score: float = 0.0
    usage_count: int = 0
    success_count: int = 0
    
    # === PROVENANCE FIELDS (NEW) ===
    # Claims (granular knowledge units)
    claim_ids: List[str] = field(default_factory=list)
    
    # Evidence chain
    evidence_ids: List[str] = field(default_factory=list)
    primary_evidence_id: str = ""
    
    # Verification tracking
    verification_ids: List[str] = field(default_factory=list)
    last_verification_method: str = ""
    
    # Corroboration
    corroboration_count: int = 0              # Independent sources confirming
    independent_source_count: int = 0         # How many unique sources
    
    # Refutation tracking
    refutation_count: int = 0                 # Sources contradicting
    
    # Lineage
    derived_from: List[str] = field(default_factory=list)  # Parent entries
    lineage_depth: int = 0
    
    # Provenance status
    provenance_status: ProvenanceStatus = ProvenanceStatus.PRIMARY
    
    # Confidence receipt
    confidence_receipt_id: str = ""
    
    # Case file
    truth_case_file_id: str = ""
    
    # Metadata
    metadata: Dict = field(default_factory=dict)


@dataclass
class Contradiction:
    """
    Contradiction - Enhanced with Evidence
    =======================================
    Now includes evidence bundles and resolution tracking.
    """
    entry_a: str
    entry_b: str
    contradiction_type: str
    severity: float
    detected_at: float
    resolution: str = ""
    
    # === PROVENANCE FIELDS (NEW) ===
    # Evidence for each side
    evidence_a_ids: List[str] = field(default_factory=list)
    evidence_b_ids: List[str] = field(default_factory=list)
    
    # Claim-level tracking
    claim_a_id: str = ""
    claim_b_id: str = ""
    
    # Resolution details
    resolution_rule: str = ""
    resolution_evidence: str = ""
    resolved_at: float = 0.0
    resolver: str = ""              # system, user, manual
    
    # Case file reference
    case_file_id: str = ""
    
    # Proof details
    contradiction_proof: str = ""   # Semantic reason for contradiction
    compared_spans: str = ""        # What was compared


@dataclass
class ProceduralMemory:
    procedure_id: str
    name: str
    steps: List[Dict]
    prerequisites: List[str]
    outcomes: List[str]
    success_rate: float
    last_used: float
    usage_count: int
    verified_against: List[str] = field(default_factory=list)


# ==================== EVIDENCE & PROVENANCE MANAGER ====================

class EvidenceManager:
    """
    Evidence Manager - Core of Provenance System
    ==============================================
    Manages all evidence, claims, snapshots, verification,
    lineage, and case files.
    """
    
    def __init__(self):
        # Storage for all evidence components
        self.source_snapshots: Dict[str, SourceSnapshot] = {}
        self.claims: Dict[str, Claim] = {}
        self.evidence_records: Dict[str, EvidenceRecord] = {}
        self.verification_receipts: Dict[str, VerificationReceipt] = {}
        self.provenance_lineage: Dict[str, ProvenanceLineage] = {}
        self.truth_case_files: Dict[str, TruthCaseFile] = {}
        
        # Indexes for fast lookup
        self.claim_to_evidence: Dict[str, List[str]] = defaultdict(list)
        self.claim_to_verifications: Dict[str, List[str]] = defaultdict(list)
        self.entry_to_claims: Dict[str, List[str]] = defaultdict(list)
        self.claim_to_case_file: Dict[str, str] = {}
        
        logger.info("📋 Evidence Manager initialized")
    
    # ==================== SOURCE SNAPSHOT OPERATIONS ====================
    
    def create_source_snapshot(self, url: str, raw_content: str, normalized_content: str,
                                fetch_method: str, parser_version: str, http_status: int,
                                fetch_duration_ms: int, **kwargs) -> SourceSnapshot:
        """Create a new source snapshot"""
        snapshot_id = f"snap_{hashlib.sha256((url + str(time.time())).encode()).hexdigest()[:16]}"
        
        # Calculate content hashes
        content_hash = hashlib.sha256(normalized_content.encode()).hexdigest()
        raw_content_hash = hashlib.sha256(raw_content.encode()).hexdigest()
        
        # Extract canonical domain
        from urllib.parse import urlparse
        canonical_domain = urlparse(url).netloc
        
        snapshot = SourceSnapshot(
            snapshot_id=snapshot_id,
            source_url=url,
            canonical_domain=canonical_domain,
            raw_content=raw_content,
            normalized_content=normalized_content,
            content_hash=content_hash,
            raw_content_hash=raw_content_hash,
            fetched_at=time.time(),
            fetch_method=fetch_method,
            parser_version=parser_version,
            http_status=http_status,
            fetch_duration_ms=fetch_duration_ms,
            **kwargs
        )
        
        self.source_snapshots[snapshot_id] = snapshot
        return snapshot
    
    def get_snapshot(self, snapshot_id: str) -> Optional[SourceSnapshot]:
        """Get a snapshot by ID"""
        return self.source_snapshots.get(snapshot_id)
    
    def get_latest_snapshot(self, url: str) -> Optional[SourceSnapshot]:
        """Get the latest snapshot for a URL"""
        matching = [s for s in self.source_snapshots.values() if s.source_url == url]
        if matching:
            return sorted(matching, key=lambda s: s.fetched_at, reverse=True)[0]
        return None
    
    # ==================== CLAIM OPERATIONS ====================
    
    def create_claim(self, entry_id: str, claim_text: str, claim_kind: ClaimKind,
                    scope: str = "", span_start: int = 0, span_end: int = 0,
                    provenance_status: ProvenanceStatus = ProvenanceStatus.PRIMARY,
                    derived_from_entry_id: str = "") -> Claim:
        """Create a new claim"""
        claim_id = f"claim_{hashlib.sha256((claim_text + str(time.time())).encode()).hexdigest()[:16]}"
        
        claim = Claim(
            claim_id=claim_id,
            entry_id=entry_id,
            claim_text=claim_text,
            claim_kind=claim_kind,
            scope=scope,
            span_start=span_start,
            span_end=span_end,
            provenance_status=provenance_status,
            derived_from_entry_id=derived_from_entry_id,
        )
        
        self.claims[claim_id] = claim
        self.entry_to_claims[entry_id].append(claim_id)
        
        return claim
    
    def get_claim(self, claim_id: str) -> Optional[Claim]:
        """Get a claim by ID"""
        return self.claims.get(claim_id)
    
    def get_claims_for_entry(self, entry_id: str) -> List[Claim]:
        """Get all claims for an entry"""
        claim_ids = self.entry_to_claims.get(entry_id, [])
        return [self.claims[cid] for cid in claim_ids if cid in self.claims]
    
    def update_claim_status(self, claim_id: str, status: ClaimStatus, 
                           verification_method: VerificationMethod = VerificationMethod.AUTOMATIC):
        """Update claim status and verification info"""
        if claim_id in self.claims:
            claim = self.claims[claim_id]
            claim.status = status
            claim.verification_method = verification_method
            claim.verification_count += 1
            claim.last_verified_at = time.time()
            claim.updated_at = time.time()
    
    # ==================== EVIDENCE RECORD OPERATIONS ====================
    
    def create_evidence_record(self, claim_id: str, source_snapshot_id: str,
                              evidence_type: EvidenceType, extracted_span: str,
                              extraction_method: str, extractor_version: str,
                              direction: str = "support", **kwargs) -> EvidenceRecord:
        """Create a new evidence record"""
        evidence_id = f"ev_{hashlib.sha256((claim_id + str(time.time())).encode()).hexdigest()[:16]}"
        
        evidence = EvidenceRecord(
            evidence_id=evidence_id,
            claim_id=claim_id,
            source_snapshot_id=source_snapshot_id,
            evidence_type=evidence_type,
            extracted_span=extracted_span,
            extraction_method=extraction_method,
            extractor_version=extractor_version,
            direction=direction,
            **kwargs
        )
        
        self.evidence_records[evidence_id] = evidence
        self.claim_to_evidence[claim_id].append(evidence_id)
        
        # Update claim
        if claim_id in self.claims:
            claim = self.claims[claim_id]
            claim.evidence_ids.append(evidence_id)
            if direction == "support":
                claim.supporting_evidence_ids.append(evidence_id)
            elif direction == "refute":
                claim.refuting_evidence_ids.append(evidence_id)
        
        return evidence
    
    def get_evidence(self, evidence_id: str) -> Optional[EvidenceRecord]:
        """Get an evidence record by ID"""
        return self.evidence_records.get(evidence_id)
    
    def get_evidence_for_claim(self, claim_id: str, direction: str = None) -> List[EvidenceRecord]:
        """Get all evidence for a claim"""
        evidence_ids = self.claim_to_evidence.get(claim_id, [])
        evidence_list = [self.evidence_records[eid] for eid in evidence_ids if eid in self.evidence_records]
        
        if direction:
            evidence_list = [e for e in evidence_list if e.direction == direction]
        
        return evidence_list
    
    # ==================== VERIFICATION RECEIPT OPERATIONS ====================
    
    def create_verification_receipt(self, target_type: str, target_id: str,
                                    method: VerificationMethod, inputs: Dict,
                                    checks_passed: List[str], checks_failed: List[str],
                                    result: str, verified_by: str = "system",
                                    **kwargs) -> VerificationReceipt:
        """Create a verification receipt"""
        receipt_id = f"vr_{hashlib.sha256((target_id + str(time.time())).encode()).hexdigest()[:16]}"
        
        receipt = VerificationReceipt(
            receipt_id=receipt_id,
            target_type=target_type,
            target_id=target_id,
            method=method,
            inputs=inputs,
            checks_passed=checks_passed,
            checks_failed=checks_failed,
            result=result,
            verified_by=verified_by,
            **kwargs
        )
        
        self.verification_receipts[receipt_id] = receipt
        
        # Link to claim if applicable
        if target_type == "claim":
            self.claim_to_verifications[target_id].append(receipt_id)
        
        return receipt
    
    def get_verification_receipt(self, receipt_id: str) -> Optional[VerificationReceipt]:
        """Get a verification receipt by ID"""
        return self.verification_receipts.get(receipt_id)
    
    def get_verifications_for_claim(self, claim_id: str) -> List[VerificationReceipt]:
        """Get all verifications for a claim"""
        receipt_ids = self.claim_to_verifications.get(claim_id, [])
        return [self.verification_receipts[rid] for rid in receipt_ids if rid in self.verification_receipts]
    
    # ==================== PROVENANCE LINEAGE OPERATIONS ====================
    
    def create_provenance_lineage(self, child_entity_id: str, child_entity_type: str,
                                 parent_entity_id: str = "", parent_entity_type: str = "",
                                 transformation_type: str = "", tool_name: str = "",
                                 model_name: str = "", **kwargs) -> ProvenanceLineage:
        """Create a provenance lineage record"""
        lineage_id = f"lin_{hashlib.sha256((child_entity_id + str(time.time())).encode()).hexdigest()[:16]}"
        
        # Calculate lineage depth
        lineage_depth = 1
        root_entity_id = child_entity_id
        
        if parent_entity_id and parent_entity_type == "entry":
            # Look for existing lineage
            parent_lineages = [l for l in self.provenance_lineage.values() 
                             if l.child_entity_id == parent_entity_id]
            if parent_lineages:
                parent_lineage = parent_lineages[0]
                lineage_depth = parent_lineage.lineage_depth + 1
                root_entity_id = parent_lineage.root_entity_id
        
        lineage = ProvenanceLineage(
            lineage_id=lineage_id,
            child_entity_id=child_entity_id,
            child_entity_type=child_entity_type,
            parent_entity_id=parent_entity_id,
            parent_entity_type=parent_entity_type,
            transformation_type=transformation_type,
            tool_name=tool_name,
            model_name=model_name,
            lineage_depth=lineage_depth,
            root_entity_id=root_entity_id,
            **kwargs
        )
        
        # Build lineage chain
        if parent_entity_id:
            parent_lineages = [l for l in self.provenance_lineage.values() 
                             if l.child_entity_id == parent_entity_id]
            if parent_lineages:
                lineage.lineage_chain = parent_lineages[0].lineage_chain + [parent_entity_id]
            else:
                lineage.lineage_chain = [parent_entity_id]
        
        self.provenance_lineage[lineage_id] = lineage
        return lineage
    
    def get_lineage(self, lineage_id: str) -> Optional[ProvenanceLineage]:
        """Get a lineage record by ID"""
        return self.provenance_lineage.get(lineage_id)
    
    def get_full_lineage_chain(self, entity_id: str, entity_type: str) -> List[ProvenanceLineage]:
        """Get the full lineage chain for an entity"""
        chain = []
        current_id = entity_id
        
        while True:
            matching = [l for l in self.provenance_lineage.values() 
                      if l.child_entity_id == current_id]
            if not matching:
                break
            
            lineage = matching[0]
            chain.append(lineage)
            
            if lineage.parent_entity_id:
                current_id = lineage.parent_entity_id
            else:
                break
        
        return chain
    
    # ==================== TRUTH CASE FILE OPERATIONS ====================
    
    def create_truth_case_file(self, primary_claim_id: str, case_summary: str,
                               case_type: str, priority: str = "normal") -> TruthCaseFile:
        """Create a new truth case file"""
        case_id = f"case_{hashlib.sha256((primary_claim_id + str(time.time())).encode()).hexdigest()[:16]}"
        
        case_file = TruthCaseFile(
            case_id=case_id,
            primary_claim_id=primary_claim_id,
            case_summary=case_summary,
            case_type=case_type,
            priority=priority,
        )
        
        self.truth_case_files[case_id] = case_file
        self.claim_to_case_file[primary_claim_id] = case_id
        
        return case_file
    
    def get_case_file(self, case_id: str) -> Optional[TruthCaseFile]:
        """Get a case file by ID"""
        return self.truth_case_files.get(case_id)
    
    def get_case_file_for_claim(self, claim_id: str) -> Optional[TruthCaseFile]:
        """Get the case file for a claim"""
        case_id = self.claim_to_case_file.get(claim_id)
        if case_id:
            return self.truth_case_files.get(case_id)
        return None
    
    def add_evidence_to_case(self, case_id: str, evidence_id: str, direction: str = "support"):
        """Add evidence to a case file"""
        if case_id in self.truth_case_files:
            case = self.truth_case_files[case_id]
            if direction == "support":
                case.supporting_evidence_ids.append(evidence_id)
            elif direction == "refute":
                case.refuting_evidence_ids.append(evidence_id)
            else:
                case.neutral_evidence_ids.append(evidence_id)
            case.updated_at = time.time()
            case.last_activity_at = time.time()
    
    def resolve_case(self, case_id: str, verdict: str, resolution_rule: str,
                    resolution_evidence: str, resolver: str = "system"):
        """Resolve a case file"""
        if case_id in self.truth_case_files:
            case = self.truth_case_files[case_id]
            case.current_verdict = verdict
            case.resolution_rule = resolution_rule
            case.resolution_evidence = resolution_evidence
            case.resolved_at = time.time()
            case.resolver = resolver
            case.updated_at = time.time()
    
    # ==================== CORROBORATION ENGINE ====================
    
    def calculate_corroboration(self, claim_id: str) -> Dict:
        """
        Calculate corroboration score for a claim.
        
        Returns:
            Dict with corroboration_count, independent_source_count,
            source_diversity_score, authority_weighted_score
        """
        claim = self.claims.get(claim_id)
        if not claim:
            return {"corroboration_count": 0, "independent_source_count": 0}
        
        evidence = self.get_evidence_for_claim(claim_id, direction="support")
        
        if not evidence:
            return {"corroboration_count": 0, "independent_source_count": 0}
        
        # Count independent sources
        source_domains = set()
        for ev in evidence:
            snapshot = self.source_snapshots.get(ev.source_snapshot_id)
            if snapshot:
                source_domains.add(snapshot.canonical_domain)
        
        # Calculate authority-weighted score
        authority_score = 0.0
        for ev in evidence:
            snapshot = self.source_snapshots.get(ev.source_snapshot_id)
            if snapshot:
                # Higher weight for official domains
                domain = snapshot.canonical_domain.lower()
                if any(o in domain for o in ['official', 'docs', 'api', 'reference', 'spec']):
                    authority_score += 1.0
                else:
                    authority_score += 0.5
        
        return {
            "corroboration_count": len(evidence),
            "independent_source_count": len(source_domains),
            "source_diversity_score": len(source_domains) / max(1, len(evidence)),
            "authority_weighted_score": authority_score / max(1, len(evidence)),
        }
    
    # ==================== NEGATIVE EVIDENCE REGISTRY ====================
    
    def register_refuting_evidence(self, claim_id: str, evidence_id: str):
        """Register refuting evidence for a claim"""
        if claim_id in self.claims:
            claim = self.claims[claim_id]
            if evidence_id not in claim.refuting_evidence_ids:
                claim.refuting_evidence_ids.append(evidence_id)
                
                # Update claim status to disputed if enough refuting evidence
                if len(claim.refuting_evidence_ids) >= 1 and claim.status == ClaimStatus.VERIFIED:
                    claim.status = ClaimStatus.DISPUTED
    
    # ==================== EXTRACT FROM CONTENT ====================
    
    def extract_claims_from_content(self, entry_id: str, content: str, 
                                   source_snapshot_id: str) -> List[Claim]:
        """
        Extract claims from content.
        
        This is a basic implementation - in production, use NLP.
        """
        claims = []
        
        # Simple sentence splitting
        sentences = content.split('. ')
        
        for i, sentence in enumerate(sentences):
            sentence = sentence.strip()
            if len(sentence) < 10:
                continue
            
            # Determine claim kind (basic heuristic)
            if '?' in sentence:
                claim_kind = ClaimKind.HYPOTHETICAL
            elif any(w in sentence.lower() for w in ['deprecated', 'obsolete', 'old']):
                claim_kind = ClaimKind.DEPRECATED
            elif any(w in sentence.lower() for w in ['maybe', 'might', 'could', 'possibly']):
                claim_kind = ClaimKind.UNCERTAIN
            elif any(w in sentence.lower() for w in ['should', 'must', 'need to']):
                claim_kind = ClaimKind.PROCEDURAL
            else:
                claim_kind = ClaimKind.FACTUAL
            
            claim = self.create_claim(
                entry_id=entry_id,
                claim_text=sentence,
                claim_kind=claim_kind,
                scope=f"sentence_{i}",
                span_start=0,  # Would need proper indexing
                span_end=len(sentence)
            )
            
            # Create evidence record for this claim
            self.create_evidence_record(
                claim_id=claim.claim_id,
                source_snapshot_id=source_snapshot_id,
                evidence_type=EvidenceType.DIRECT,
                extracted_span=sentence,
                extraction_method="sentence_split",
                extractor_version="1.0",
                direction="support"
            )
            
            claims.append(claim)
        
        return claims
    
    # ==================== QUERY SUPPORT ====================
    
    def get_evidence_depth(self, claim_id: str) -> int:
        """Get evidence depth (total evidence count) for a claim"""
        return len(self.claim_to_evidence.get(claim_id, []))
    
    def get_verification_recency(self, claim_id: str) -> float:
        """Get time since last verification"""
        claim = self.claims.get(claim_id)
        if not claim or claim.last_verified_at == 0:
            return float('inf')
        return time.time() - claim.last_verified_at
    
    def get_production_backing(self, claim_id: str) -> int:
        """Get production success count backing this claim"""
        # This would link to production outcomes
        # Simplified for now
        return 0


# SOURCE RANKER
class SourceRanker:
    TRUST_WEIGHTS = {
        SourceType.DOCUMENTATION: 0.9,
        SourceType.API_DOCS: 0.9,
        SourceType.PAPER: 0.85,
        SourceType.GITHUB: 0.8,
        SourceType.STACKOVERFLOW: 0.7,
        SourceType.WIKI: 0.65,
        SourceType.BLOG: 0.5,
        SourceType.NEWS: 0.5,
        SourceType.FORUM: 0.3,
    }
    
    def __init__(self):
        self.source_cache: Dict[str, Dict] = {}
    
    def rank_source(self, source: Source, query: str = "") -> Dict:
        trust = self.TRUST_WEIGHTS.get(source.source_type, 0.5)
        age_days = (time.time() - source.last_scraped) / 86400
        freshness = max(0, 1 - (age_days / 365))
        
        relevance = 0.5
        if query and source.topics:
            qt = set(query.lower().split())
            st = set(" ".join(source.topics).lower().split())
            relevance = len(qt & st) / max(1, len(qt))
        
        url_lower = source.url.lower()
        authority = 0.5
        for kw in ["official", "reference", "specification", "rfc", "mdn"]:
            if kw in url_lower:
                authority = min(1.0, authority + 0.1)
        
        quality = min(1.0, source.citations / 100)
        
        overall = trust * 0.3 + freshness * 0.2 + relevance * 0.2 + authority * 0.15 + quality * 0.15
        
        ranking = {
            "url": source.url,
            "trust_score": trust,
            "freshness_score": freshness,
            "relevance_score": relevance,
            "authority_score": authority,
            "quality_score": quality,
            "overall_score": overall
        }
        self.source_cache[source.url] = ranking
        return ranking


# CONTRADICTION DETECTOR
class ContradictionDetector:
    def __init__(self):
        self.contradictions: List[Contradiction] = []
        self.knowledge_store: Dict[str, KnowledgeEntry] = {}
    
    def add_knowledge(self, entry: KnowledgeEntry):
        self.knowledge_store[entry.entry_id] = entry
        entry.contradiction_hash = hashlib.md5(entry.content[:100].encode()).hexdigest()[:8]
        self._check_contradictions(entry)
    
    def _check_contradictions(self, entry: KnowledgeEntry):
        negations = [("not", "is"), ("never", "always"), ("false", "true")]
        
        for eid, existing in self.knowledge_store.items():
            if eid == entry.entry_id:
                continue
            
            sim = self._similarity(entry.content, existing.content)
            if sim > 0.7:
                for neg, pos in negations:
                    if (neg in entry.content.lower() and pos in existing.content.lower()) or \
                       (pos in entry.content.lower() and neg in existing.content.lower()):
                        self.contradictions.append(Contradiction(
                            entry_a=eid,
                            entry_b=entry.entry_id,
                            contradiction_type="negation",
                            severity=0.8,
                            detected_at=time.time()
                        ))
    
    def _similarity(self, t1: str, t2: str) -> float:
        w1, w2 = set(t1.lower().split()), set(t2.lower().split())
        if not w1 or not w2:
            return 0.0
        return len(w1 & w2) / max(len(w1), len(w2))


# STALE KNOWLEDGE PRUNER
class StaleKnowledgePruner:
    def __init__(self, threshold: float = 0.5, prune_days: int = 180):
        self.threshold = threshold
        self.prune_days = prune_days
        self.knowledge: Dict[str, KnowledgeEntry] = {}
    
    def add_knowledge(self, entry: KnowledgeEntry):
        self.knowledge[entry.entry_id] = entry
        self._update_stale(entry)
    
    def _update_stale(self, entry: KnowledgeEntry):
        age = (time.time() - entry.collected_at) / 86400
        age_score = min(1.0, age / self.prune_days)
        usage = 1.0 if entry.usage_count == 0 else 0.0
        success = entry.success_count / max(1, entry.usage_count) if entry.usage_count > 0 else 0.5
        entry.stale_score = age_score * 0.5 + usage * 0.3 + (1-success) * 0.2
    
    def get_stale(self) -> List[KnowledgeEntry]:
        stale = []
        for entry in self.knowledge.values():
            self._update_stale(entry)
            if entry.stale_score >= self.threshold:
                stale.append(entry)
        return stale
    
    def prune(self) -> int:
        stale = self.get_stale()
        count = 0
        for entry in stale:
            if entry.confidence < 0.7:
                del self.knowledge[entry.entry_id]
                count += 1
        return count


# CONFIDENCE SCORER
class ConfidenceScorer:
    """
    Enhanced Confidence Scorer - Explainable Confidence
    ====================================================
    Now produces confidence receipts showing exactly how
    each confidence score was calculated.
    """
    def __init__(self):
        self.weights = {TrustLevel.HIGH: 1.0, TrustLevel.MEDIUM: 0.7, TrustLevel.LOW: 0.4, TrustLevel.UNKNOWN: 0.2}
        
        # Receipt storage
        self.receipts: Dict[str, ConfidenceReceipt] = {}
        
        # Component weights for explainability
        self.component_weights = {
            "source_trust": 0.4,
            "freshness": 0.2,
            "verification": 0.2,
            "evidence_strength": 0.2,
            "corroboration": 0.0,  # Will be set if available
        }
    
    def calculate(self, entry: KnowledgeEntry, source: Source) -> float:
        """
        Calculate confidence with detailed receipt.
        Returns float but also stores a ConfidenceReceipt.
        """
        # Create receipt
        receipt = ConfidenceReceipt(
            receipt_id=f"receipt_{entry.entry_id}_{int(time.time())}",
            entry_id=entry.entry_id
        )
        
        # 1. Source Trust Score
        receipt.source_trust_score = self.weights.get(source.trust_level, 0.2) * self.component_weights["source_trust"]
        
        # 2. Freshness Score
        age = (time.time() - entry.collected_at) / 86400
        receipt.freshness_score = max(0, 1 - (age / 365)) * self.component_weights["freshness"]
        
        # 3. Verification Score
        if entry.last_verified > entry.collected_at:
            vage = (time.time() - entry.last_verified) / 86400
            receipt.verification_score = max(0, 1 - (vage / 180)) * self.component_weights["verification"]
        
        # 4. Evidence Strength Score
        evidence_count = len(entry.evidence_ids)
        receipt.evidence_strength_score = min(1.0, evidence_count / 10) * self.component_weights["evidence_strength"]
        
        # 5. Corroboration Score (NEW)
        if entry.corroboration_count > 0:
            receipt.corroboration_score = min(1.0, entry.corroboration_count / 5) * 0.2
        
        # Calculate base score
        receipt.base_score = (
            receipt.source_trust_score + 
            receipt.freshness_score + 
            receipt.verification_score + 
            receipt.evidence_strength_score +
            receipt.corroboration_score
        )
        
        # 6. Contradiction Penalty
        if entry.contradiction_hash:
            receipt.contradiction_penalty = 0.1  # Base penalty for having contradictions
        
        # 7. Staleness Penalty
        if entry.stale_score > 0.5:
            receipt.staleness_penalty = entry.stale_score * 0.1
        
        # 8. Missing Verification Penalty
        if entry.last_verified == entry.collected_at and entry.provenance_status != ProvenanceStatus.DERIVED:
            receipt.missing_verification_penalty = 0.05
        
        # Calculate totals
        receipt.penalties_total = (
            receipt.contradiction_penalty + 
            receipt.staleness_penalty + 
            receipt.missing_verification_penalty
        )
        
        receipt.bonuses_total = 0.0  # Future use
        
        # Knowledge type adjustment
        knowledge_type_bonus = 0.0
        if entry.knowledge_type == KnowledgeType.FACT:
            knowledge_type_bonus = 0.1
        elif entry.knowledge_type == KnowledgeType.OPINION:
            knowledge_type_bonus = -0.1
        
        # Final score calculation
        receipt.final_score = min(1.0, max(0.0, 
            receipt.base_score - receipt.penalties_total + knowledge_type_bonus
        ))
        
        # Store component details for debugging
        receipt.component_details = {
            "trust_level": source.trust_level.name if hasattr(source.trust_level, 'name') else str(source.trust_level),
            "age_days": age,
            "evidence_count": evidence_count,
            "corroboration_count": entry.corroboration_count,
            "contradiction_present": bool(entry.contradiction_hash),
            "stale_score": entry.stale_score,
            "provenance_status": entry.provenance_status.name if hasattr(entry.provenance_status, 'name') else str(entry.provenance_status),
            "knowledge_type": entry.knowledge_type.name if hasattr(entry.knowledge_type, 'name') else str(entry.knowledge_type),
        }
        
        # Store receipt
        self.receipts[receipt.receipt_id] = receipt
        
        return receipt.final_score
    
    def calculate_with_evidence(self, entry: KnowledgeEntry, source: Source,
                                evidence_records: Dict[str, EvidenceRecord],
                                contradiction_severity: float = 0.0) -> Tuple[float, ConfidenceReceipt]:
        """
        Calculate confidence with full evidence chain.
        
        Args:
            entry: Knowledge entry
            source: Source
            evidence_records: Dictionary of evidence records
            contradiction_severity: Severity of contradictions (0-1)
        
        Returns:
            Tuple of (confidence_score, receipt)
        """
        receipt = ConfidenceReceipt(
            receipt_id=f"receipt_{entry.entry_id}_{int(time.time())}",
            entry_id=entry.entry_id
        )
        
        # 1. Source Trust Score
        receipt.source_trust_score = self.weights.get(source.trust_level, 0.2) * self.component_weights["source_trust"]
        
        # 2. Freshness Score
        age = (time.time() - entry.collected_at) / 86400
        receipt.freshness_score = max(0, 1 - (age / 365)) * self.component_weights["freshness"]
        
        # 3. Verification Score
        if entry.last_verified > entry.collected_at:
            vage = (time.time() - entry.last_verified) / 86400
            receipt.verification_score = max(0, 1 - (vage / 180)) * self.component_weights["verification"]
        
        # 4. Evidence Strength Score (enhanced with actual evidence)
        supporting_evidence = [e for e in evidence_records.values() 
                             if e.claim_id in entry.claim_ids and e.direction == "support"]
        refuting_evidence = [e for e in evidence_records.values() 
                            if e.claim_id in entry.claim_ids and e.direction == "refute"]
        
        if supporting_evidence:
            avg_strength = sum(e.strength_score for e in supporting_evidence) / len(supporting_evidence)
            receipt.evidence_strength_score = min(1.0, avg_strength) * self.component_weights["evidence_strength"]
        
        # 5. Corroboration Score
        receipt.corroboration_score = min(1.0, entry.corroboration_count / 5) * 0.2 if entry.corroboration_count > 0 else 0.0
        
        # Calculate base score
        receipt.base_score = (
            receipt.source_trust_score + 
            receipt.freshness_score + 
            receipt.verification_score + 
            receipt.evidence_strength_score +
            receipt.corroboration_score
        )
        
        # 6. Contradiction Penalty (enhanced)
        receipt.contradiction_penalty = contradiction_severity * 0.2
        
        # 7. Refutation Penalty
        if refuting_evidence:
            refutation_strength = sum(e.strength_score for e in refuting_evidence) / len(refuting_evidence)
            receipt.contradiction_penalty += refutation_strength * 0.15
        
        # 8. Staleness Penalty
        if entry.stale_score > 0.5:
            receipt.staleness_penalty = entry.stale_score * 0.1
        
        # 9. Missing Verification Penalty
        if entry.last_verified == entry.collected_at and entry.provenance_status == ProvenanceStatus.PRIMARY:
            receipt.missing_verification_penalty = 0.05
        
        # Calculate totals
        receipt.penalties_total = (
            receipt.contradiction_penalty + 
            receipt.staleness_penalty + 
            receipt.missing_verification_penalty
        )
        
        # Knowledge type adjustment
        knowledge_type_bonus = 0.0
        if entry.knowledge_type == KnowledgeType.FACT:
            knowledge_type_bonus = 0.1
        elif entry.knowledge_type == KnowledgeType.OPINION:
            knowledge_type_bonus = -0.1
        
        # Final score
        receipt.final_score = min(1.0, max(0.0, 
            receipt.base_score - receipt.penalties_total + knowledge_type_bonus
        ))
        
        # Component details
        receipt.component_details = {
            "supporting_evidence_count": len(supporting_evidence),
            "refuting_evidence_count": len(refuting_evidence),
            "avg_supporting_strength": sum(e.strength_score for e in supporting_evidence) / max(1, len(supporting_evidence)),
            "contradiction_severity": contradiction_severity,
        }
        
        # Store
        self.receipts[receipt.receipt_id] = receipt
        
        return receipt.final_score, receipt
    
    def get_receipt(self, entry_id: str) -> Optional[ConfidenceReceipt]:
        """Get the most recent receipt for an entry"""
        matching = [r for r in self.receipts.values() if r.entry_id == entry_id]
        if matching:
            return sorted(matching, key=lambda r: r.calculated_at, reverse=True)[0]
        return None
    
    def explain_confidence(self, entry_id: str) -> Dict:
        """Get a human-readable explanation of confidence"""
        receipt = self.get_receipt(entry_id)
        if not receipt:
            return {"error": "No receipt found"}
        
        explanation = {
            "entry_id": entry_id,
            "final_score": receipt.final_score,
            "explanation": [],
            "receipt_id": receipt.receipt_id,
        }
        
        if receipt.source_trust_score > 0:
            explanation["explanation"].append(
                f"Source trust contributes +{receipt.source_trust_score:.2f}"
            )
        
        if receipt.freshness_score > 0:
            explanation["explanation"].append(
                f"Freshness contributes +{receipt.freshness_score:.2f}"
            )
        
        if receipt.verification_score > 0:
            explanation["explanation"].append(
                f"Verification contributes +{receipt.verification_score:.2f}"
            )
        
        if receipt.evidence_strength_score > 0:
            explanation["explanation"].append(
                f"Evidence strength contributes +{receipt.evidence_strength_score:.2f}"
            )
        
        if receipt.corroboration_score > 0:
            explanation["explanation"].append(
                f"Corroboration contributes +{receipt.corroboration_score:.2f}"
            )
        
        if receipt.contradiction_penalty > 0:
            explanation["explanation"].append(
                f"Contradiction penalty -{receipt.contradiction_penalty:.2f}"
            )
        
        if receipt.staleness_penalty > 0:
            explanation["explanation"].append(
                f"Staleness penalty -{receipt.staleness_penalty:.2f}"
            )
        
        if receipt.missing_verification_penalty > 0:
            explanation["explanation"].append(
                f"Missing verification penalty -{receipt.missing_verification_penalty:.2f}"
            )
        
        return explanation


# PROCEDURAL MEMORY
class ProceduralMemoryManager:
    def __init__(self):
        self.procedures: Dict[str, ProceduralMemory] = {}
    
    def add(self, proc: ProceduralMemory):
        self.procedures[proc.procedure_id] = proc
    
    def find(self, name: str) -> Optional[ProceduralMemory]:
        for p in self.procedures.values():
            if name.lower() in p.name.lower():
                return p
        return None
    
    def record_execution(self, pid: str, success: bool, duration: float):
        if pid in self.procedures:
            p = self.procedures[pid]
            p.usage_count += 1
            if success:
                p.success_count += 1
            p.success_rate = p.success_count / p.usage_count
            p.last_used = time.time()


# MAIN LEARNING PIPELINE
class ContinuousLearningPipeline:
    """
    Continuous Learning Pipeline - Enhanced with Evidence & Provenance
    ==================================================================
    Now includes full evidence chain tracking, provenance, and
    evidence-aware querying.
    """
    def __init__(self, api_key: str = None):
        self.api_key = api_key
        self.source_ranker = SourceRanker()
        self.contradiction_detector = ContradictionDetector()
        self.stale_pruner = StaleKnowledgePruner()
        self.confidence_scorer = ConfidenceScorer()
        self.procedural = ProceduralMemoryManager()
        
        # NEW: Evidence Manager for provenance tracking
        self.evidence_manager = EvidenceManager()
        
        self.knowledge: Dict[str, KnowledgeEntry] = {}
        self.sources: Dict[str, Source] = {}
        
        self.learning_enabled = True
        self.learning_interval = 3600
        self.last_learning = 0.0
        
        self.topics = ["ai", "machine learning", "python", "software engineering"]
        
        # NEW: Reverification policies
        self.reverification_policies = {
            "single_source_weak": 7,        # days
            "official_doc_backed": 90,       # days
            "disputed": 1,                   # days
            "superseded_candidate": 14,      # days
            "production_backed": 180,        # days
        }
        
        self._start_background()
        
        logger.info("🔬 Continuous Learning Pipeline with Evidence & Provenance initialized")
    
    def _start_background(self):
        def loop():
            while self.learning_enabled:
                try:
                    self._periodic_learning()
                except Exception as e:
                    logger.warning(f"Learning error: {e}")
                time.sleep(self.learning_interval)
        
        threading.Thread(target=loop, daemon=True).start()
    
    def _periodic_learning(self):
        if time.time() - self.last_learning < self.learning_interval:
            return
        
        logger.info("Running periodic learning...")
        
        # Prune stale
        pruned = self.stale_pruner.prune()
        if pruned > 0:
            logger.info(f"Pruned {pruned} stale entries")
        
        # NEW: Evidence-based reverification
        self._run_evidence_based_reverification()
        
        self.last_learning = time.time()
    
    def _run_evidence_based_reverification(self):
        """
        Run reverification based on evidence quality, not just age.
        
        This is a key part of the Evidence & Provenance Layer.
        """
        for entry_id, entry in self.knowledge.items():
            days_since_verify = (time.time() - entry.last_verified) / 86400
            
            # Determine reverification urgency based on evidence quality
            reverify_days = self._get_reverification_interval(entry)
            
            if days_since_verify >= reverify_days:
                self._flag_for_evidence_based_reverification(entry)
    
    def _get_reverification_interval(self, entry: KnowledgeEntry) -> int:
        """
        Get reverification interval based on evidence quality.
        
        This is the evidence-policy based approach requested.
        """
        # Check for disputed status
        if entry.metadata.get("disputed", False):
            return self.reverification_policies["disputed"]
        
        # Check for superseded candidate
        if entry.metadata.get("superseded_candidate", False):
            return self.reverification_policies["superseded_candidate"]
        
        # Check for production backing
        if entry.success_count >= 5 and entry.usage_count >= 10:
            production_success_rate = entry.success_count / entry.usage_count
            if production_success_rate >= 0.8:
                return self.reverification_policies["production_backed"]
        
        # Check evidence quality
        evidence_count = len(entry.evidence_ids)
        corroboration_count = entry.corroboration_count
        
        # Strong evidence (official doc + corroboration)
        if evidence_count >= 2 and corroboration_count >= 2:
            return self.reverification_policies["official_doc_backed"]
        
        # Single source weak claim
        if evidence_count <= 1 and corroboration_count == 0:
            return self.reverification_policies["single_source_weak"]
        
        # Default medium interval
        return 30
    
    def _flag_for_evidence_based_reverification(self, entry: KnowledgeEntry):
        """
        Flag entry for reverification with evidence-quality context.
        """
        # Mark in metadata
        if not hasattr(entry, 'metadata'):
            entry.metadata = {}
        
        entry.metadata["needs_verification"] = True
        entry.metadata["reverification_reason"] = self._get_reverification_reason(entry)
        
        logger.info(f"🔔 Flagged {entry.entry_id} for reverification: {entry.metadata['reverification_reason']}")
    
    def _get_reverification_reason(self, entry: KnowledgeEntry) -> str:
        """Get human-readable reason for reverification"""
        evidence_count = len(entry.evidence_ids)
        corroboration_count = entry.corroboration_count
        
        if entry.metadata.get("disputed", False):
            return "disputed_claim_requires_attention"
        
        if evidence_count <= 1 and corroboration_count == 0:
            return "single_source_weak_claim"
        
        if evidence_count >= 2 and corroboration_count >= 2:
            return "strong_evidence_periodic_check"
        
        return "routine_verification"
    
    def add_knowledge(self, content: str, source_url: str, source_type: SourceType,
                     knowledge_type: KnowledgeType, tags: List[str] = None,
                     raw_content: str = "", fetch_method: str = "unknown",
                     parser_version: str = "1.0") -> str:
        """
        Add knowledge with full evidence chain.
        
        NEW: Creates source snapshot, claims, and evidence records.
        """
        entry_id = hashlib.md5(content.encode()).hexdigest()[:16]
        
        # Get or create source
        source = self.sources.get(source_url)
        if not source:
            source = Source(
                url=source_url, 
                name=source_url, 
                source_type=source_type,
                source_id=f"src_{hashlib.md5(source_url.encode()).hexdigest()[:16]}"
            )
            self.sources[source_url] = source
        
        # NEW: Create source snapshot
        snapshot = None
        if raw_content:
            normalized_content = content.strip()
            snapshot = self.evidence_manager.create_source_snapshot(
                url=source_url,
                raw_content=raw_content,
                normalized_content=normalized_content,
                fetch_method=fetch_method,
                parser_version=parser_version,
                http_status=200,
                fetch_duration_ms=0
            )
            
            # Update source with snapshot tracking
            source.snapshot_ids.append(snapshot.snapshot_id)
            source.last_fetch_hash = snapshot.content_hash
        
        # Create entry
        entry = KnowledgeEntry(
            entry_id=entry_id,
            content=content,
            knowledge_type=knowledge_type,
            source=source.name,
            source_url=source_url,
            collected_at=time.time(),
            last_verified=time.time(),
            confidence=0.5,
            tags=tags or [],
            provenance_status=ProvenanceStatus.PRIMARY
        )
        
        # NEW: Extract claims from content
        if snapshot:
            claims = self.evidence_manager.extract_claims_from_content(
                entry_id=entry_id,
                content=content,
                source_snapshot_id=snapshot.snapshot_id
            )
            entry.claim_ids = [c.claim_id for c in claims]
            entry.evidence_ids = [e.claim_id for c in claims for e in self.evidence_manager.get_evidence_for_claim(c.claim_id)]
            
            # Update source claims count
            source.total_claims_extracted += len(claims)
        
        # Calculate confidence with evidence
        if entry.evidence_ids:
            entry.confidence, receipt = self.confidence_scorer.calculate_with_evidence(
                entry, source, self.evidence_manager.evidence_records
            )
            entry.confidence_receipt_id = receipt.receipt_id
        else:
            entry.confidence = self.confidence_scorer.calculate(entry, source)
        
        # NEW: Create provenance lineage for primary knowledge
        self.evidence_manager.create_provenance_lineage(
            child_entity_id=entry_id,
            child_entity_type="entry",
            transformation_type="primary_extraction",
            tool_name="learning_pipeline",
            tool_version="2.0"
        )
        
        self.knowledge[entry_id] = entry
        self.contradiction_detector.add_knowledge(entry)
        self.stale_pruner.add_knowledge(entry)
        
        logger.info(f"📝 Added knowledge {entry_id} with {len(entry.claim_ids)} claims, {len(entry.evidence_ids)} evidence")
        
        return entry_id
    
    def add_derived_knowledge(self, content: str, parent_entry_ids: List[str],
                             knowledge_type: KnowledgeType, transformation_type: str = "summary",
                             tool_name: str = "", model_name: str = "") -> str:
        """
        Add derived knowledge with full lineage tracking.
        
        NEW: Tracks the derivation chain.
        """
        entry_id = hashlib.md5(content.encode()).hexdigest()[:16]
        
        # Create entry as derived
        entry = KnowledgeEntry(
            entry_id=entry_id,
            content=content,
            knowledge_type=knowledge_type,
            source="derived",
            source_url="",
            collected_at=time.time(),
            last_verified=0.0,
            confidence=0.5,
            provenance_status=ProvenanceStatus.DERIVED,
            derived_from=parent_entry_ids,
            lineage_depth=1
        )
        
        # Calculate lineage depth based on parents
        max_parent_depth = 0
        for parent_id in parent_entry_ids:
            if parent_id in self.knowledge:
                parent = self.knowledge[parent_id]
                max_parent_depth = max(max_parent_depth, parent.lineage_depth)
        
        entry.lineage_depth = max_parent_depth + 1
        
        # Calculate confidence based on parent confidences
        if parent_entry_ids:
            parent_confidences = [self.knowledge[pid].confidence for pid in parent_entry_ids 
                               if pid in self.knowledge]
            if parent_confidences:
                entry.confidence = min(parent_confidences) * 0.9  # Derived is slightly less confident
        
        # NEW: Create provenance lineage
        for parent_id in parent_entry_ids:
            self.evidence_manager.create_provenance_lineage(
                child_entity_id=entry_id,
                child_entity_type="entry",
                parent_entity_id=parent_id,
                parent_entity_type="entry",
                transformation_type=transformation_type,
                tool_name=tool_name,
                model_name=model_name,
                lineage_depth=entry.lineage_depth
            )
        
        self.knowledge[entry_id] = entry
        
        return entry_id
    
    def process_evidence_based_feedback(self, feedback: Dict) -> Dict:
        """
        Process feedback through evidence workflow.
        
        NEW: Feedback creates evidence, not just mutates confidence.
        """
        feedback_type = feedback.get("type", "default")
        
        result = {
            "processed": False,
            "evidence_created": False,
            "case_file_id": None
        }
        
        if feedback_type == "user_correction":
            entry_id = feedback.get("entry_id")
            correction = feedback.get("correction", {})
            
            # NEW: Create evidence from user correction
            correction_text = correction.get("text", "")
            
            # Create a snapshot for the correction
            snapshot = self.evidence_manager.create_source_snapshot(
                url="user_correction",
                raw_content=correction_text,
                normalized_content=correction_text,
                fetch_method="user_feedback",
                parser_version="1.0",
                http_status=0,
                fetch_duration_ms=0
            )
            
            # Create claim for correction
            claim = self.evidence_manager.create_claim(
                entry_id=entry_id,
                claim_text=correction_text,
                claim_kind=ClaimKind.FACTUAL,
                provenance_status=ProvenanceStatus.CORRECTED
            )
            
            # Create evidence record
            evidence = self.evidence_manager.create_evidence_record(
                claim_id=claim.claim_id,
                source_snapshot_id=snapshot.snapshot_id,
                evidence_type=EvidenceType.USER_CORRECTION,
                extracted_span=correction_text,
                extraction_method="user_feedback",
                extractor_version="1.0",
                direction="support"
            )
            
            # Update entry
            if entry_id in self.knowledge:
                entry = self.knowledge[entry_id]
                entry.claim_ids.append(claim.claim_id)
                entry.evidence_ids.append(evidence.evidence_id)
                entry.confidence = self.confidence_scorer.calculate(entry, 
                    self.sources.get(entry.source_url, Source(url="", name="", source_type=SourceType.DOCUMENTATION)))
            
            # Create verification receipt
            receipt = self.evidence_manager.create_verification_receipt(
                target_type="claim",
                target_id=claim.claim_id,
                method=VerificationMethod.USER_CONFIRMATION,
                inputs={"original_content": correction.get("original", "")},
                checks_passed=["user_confirmation"],
                checks_failed=[],
                result="verified",
                verified_by="user"
            )
            
            result["evidence_created"] = True
            result["evidence_id"] = evidence.evidence_id
            result["claim_id"] = claim.claim_id
        
        elif feedback_type == "contradiction":
            entry_a_id = feedback.get("entry_a")
            entry_b_id = feedback.get("entry_b")
            
            # NEW: Create truth case file for disputed knowledge
            case_file = self.evidence_manager.create_truth_case_file(
                primary_claim_id=entry_a_id,
                case_summary=f"Contradiction between {entry_a_id} and {entry_b_id}",
                case_type="disputed",
                priority="high"
            )
            
            # Add evidence from both entries to case
            if entry_a_id in self.knowledge:
                entry_a = self.knowledge[entry_a_id]
                for ev_id in entry_a.evidence_ids:
                    self.evidence_manager.add_evidence_to_case(case_file.case_id, ev_id, "support")
            
            if entry_b_id in self.knowledge:
                entry_b = self.knowledge[entry_b_id]
                for ev_id in entry_b.evidence_ids:
                    self.evidence_manager.add_evidence_to_case(case_file.case_id, ev_id, "refute")
            
            # Update entry metadata
            if entry_a_id in self.knowledge:
                self.knowledge[entry_a_id].metadata["disputed"] = True
                self.knowledge[entry_a_id].truth_case_file_id = case_file.case_id
            
            result["case_file_id"] = case_file.case_id
        
        result["processed"] = True
        return result
    
    def query(self, query: str, min_confidence: float = 0.3) -> List[KnowledgeEntry]:
        """
        Query knowledge with evidence-aware ranking.
        
        NEW: Uses evidence depth, source authority, verification recency,
        corroboration, and contradiction pressure.
        """
        results = []
        qterms = set(query.lower().split())
        
        for entry in self.knowledge.values():
            if entry.confidence < min_confidence:
                continue
            
            eterms = set(entry.content.lower().split())
            if not (qterms & eterms):
                continue
            
            # Calculate evidence-aware score
            evidence_score = self._calculate_evidence_score(entry)
            
            # Combine with confidence
            final_score = (
                entry.confidence * 0.4 +           # Base confidence
                evidence_score * 0.6                # Evidence strength
            )
            
            entry.usage_count += 1
            results.append((entry, final_score))
        
        # Sort by final score
        results.sort(key=lambda x: x[1], reverse=True)
        
        return [entry for entry, _ in results[:10]]
    
    def _calculate_evidence_score(self, entry: KnowledgeEntry) -> float:
        """
        Calculate evidence strength score for an entry.
        
        This implements evidence-aware retrieval.
        """
        score = 0.0
        
        # 1. Evidence depth (0-0.2)
        evidence_count = len(entry.evidence_ids)
        score += min(0.2, evidence_count * 0.05)
        
        # 2. Corroboration (0-0.2)
        score += min(0.2, entry.corroboration_count * 0.05)
        
        # 3. Verification recency (0-0.2)
        if entry.last_verified > 0:
            days_since_verify = (time.time() - entry.last_verified) / 86400
            verification_score = max(0, 1 - (days_since_verify / 180))
            score += verification_score * 0.2
        
        # 4. Source authority (0-0.2)
        source = self.sources.get(entry.source_url)
        if source:
            source_authority = SourceRanker.TRUST_WEIGHTS.get(source.source_type, 0.5)
            score += source_authority * 0.2
        
        # 5. Production backing (0-0.1)
        if entry.usage_count > 0:
            success_rate = entry.success_count / entry.usage_count
            score += success_rate * 0.1
        
        # 6. Provenance bonus (0-0.1)
        if entry.provenance_status == ProvenanceStatus.PRIMARY:
            score += 0.1
        
        # 7. Contradiction penalty (0 to -0.2)
        if entry.metadata.get("disputed", False):
            score -= 0.2
        elif entry.contradiction_hash:
            score -= 0.1
        
        return max(0.0, min(1.0, score))
    
    def query_with_provenance(self, query: str, min_confidence: float = 0.3) -> List[Dict]:
        """
        Query with full provenance information.
        
        NEW: Returns detailed provenance for each result.
        """
        entries = self.query(query, min_confidence)
        
        results = []
        for entry in entries:
            result = {
                "entry": entry,
                "provenance": self._get_entry_provenance(entry)
            }
            results.append(result)
        
        return results
    
    def _get_entry_provenance(self, entry: KnowledgeEntry) -> Dict:
        """Get full provenance information for an entry"""
        # Get claims
        claims = self.evidence_manager.get_claims_for_entry(entry.entry_id)
        
        # Get evidence
        evidence_list = []
        for claim in claims:
            evidence = self.evidence_manager.get_evidence_for_claim(claim.claim_id)
            for ev in evidence:
                snapshot = self.evidence_manager.get_snapshot(ev.source_snapshot_id)
                evidence_list.append({
                    "evidence_id": ev.evidence_id,
                    "claim_id": claim.claim_id,
                    "type": ev.evidence_type.value if hasattr(ev.evidence_type, 'value') else ev.evidence_type,
                    "direction": ev.direction,
                    "strength": ev.strength_score,
                    "source_url": snapshot.source_url if snapshot else "unknown",
                    "extracted_span": ev.extracted_span[:100] if ev.extracted_span else ""
                })
        
        # Get lineage
        lineage = self.evidence_manager.get_full_lineage_chain(entry.entry_id, "entry")
        
        return {
            "entry_id": entry.entry_id,
            "provenance_status": entry.provenance_status.value if hasattr(entry.provenance_status, 'value') else entry.provenance_status,
            "lineage_depth": entry.lineage_depth,
            "derived_from": entry.derived_from,
            "claim_count": len(claims),
            "evidence_count": len(evidence_list),
            "corroboration_count": entry.corroboration_count,
            "refutation_count": entry.refutation_count,
            "evidence": evidence_list,
            "lineage": [{"lineage_id": l.lineage_id, "parent_id": l.parent_entity_id, 
                        "transformation": l.transformation_type} for l in lineage],
            "confidence_receipt_id": entry.confidence_receipt_id
        }
    
    def explain_knowledge(self, entry_id: str) -> Dict:
        """
        Explain a knowledge entry - where it came from, evidence, confidence.
        
        NEW: Full explainability for No1+ agents.
        """
        if entry_id not in self.knowledge:
            return {"error": "Entry not found"}
        
        entry = self.knowledge[entry_id]
        
        # Get confidence explanation
        confidence_explanation = self.confidence_scorer.explain_confidence(entry_id)
        
        # Get provenance
        provenance = self._get_entry_provenance(entry)
        
        # Get case file if exists
        case_file = None
        if entry.truth_case_file_id:
            case_file = self.evidence_manager.get_case_file(entry.truth_case_file_id)
        
        return {
            "entry_id": entry_id,
            "content": entry.content,
            "confidence": entry.confidence,
            "confidence_explanation": confidence_explanation,
            "provenance": provenance,
            "case_file": {
                "id": case_file.case_id if case_file else None,
                "status": case_file.current_verdict if case_file else None
            } if case_file else None,
            "usage": {
                "usage_count": entry.usage_count,
                "success_count": entry.success_count,
                "success_rate": entry.success_count / max(1, entry.usage_count)
            }
        }
    
    def add_procedure(self, name: str, steps: List[Dict], 
                    prerequisites: List[str] = None, outcomes: List[str] = None) -> str:
        
        proc_id = hashlib.md5(name.encode()).hexdigest()[:16]
        
        proc = ProceduralMemory(
            procedure_id=proc_id,
            name=name,
            steps=steps,
            prerequisites=prerequisites or [],
            outcomes=outcomes or [],
            success_rate=0.5,
            last_used=time.time(),
            usage_count=0
        )
        
        self.procedural.add(proc)
        return proc_id
    
    def get_stats(self) -> Dict:
        conf_dist = {"vh": 0, "h": 0, "m": 0, "l": 0, "vl": 0}
        
        for e in self.knowledge.values():
            if e.confidence >= 0.9: conf_dist["vh"] += 1
            elif e.confidence >= 0.7: conf_dist["h"] += 1
            elif e.confidence >= 0.5: conf_dist["m"] += 1
            elif e.confidence >= 0.3: conf_dist["l"] += 1
            else: conf_dist["vl"] += 1
        
        return {
            "total_knowledge": len(self.knowledge),
            "total_sources": len(self.sources),
            "total_procedures": len(self.procedural.procedures),
            "contradictions": len(self.contradiction_detector.contradictions),
            "confidence_distribution": conf_dist,
            "last_learning": self.last_learning,
            "learning_enabled": self.learning_enabled
        }


def create_learning_pipeline(api_key: str = None) -> ContinuousLearningPipeline:
    return ContinuousLearningPipeline(api_key=api_key)


# ==================== KNOWLEDGE GOVERNANCE ====================

class KnowledgeGovernance:
    """
    24/7 Knowledge Governance System:
    - Source trust decay over time
    - Bad-source quarantine
    - Confidence recalibration
    - Knowledge promotion/demotion
    - Observed-world feedback loop
    """
    
    def __init__(self, pipeline):
        self.pipeline = pipeline
        self.quarantined_sources = set()
        self.trust_decay_rate = 0.01  # Per day
        self.promotion_threshold = 0.8
        self.demotion_threshold = 0.3
        self.feedback_weights = {
            "success": 0.1,
            "failure": -0.1,
            "contradiction": -0.2,
            "verification": 0.05,
            "partial": 0.05,
            "outdated": -0.15,
            "accurate": 0.15,
            "helpful": 0.05,
            "not_helpful": -0.1,
            "error": -0.15
        }
        # Feedback queue for observed-world closed loop
        self.feedback_queue: List[Dict] = []
        
    def governance_loop(self):
        """Main governance loop - run periodically"""
        # 1. Apply trust decay
        self._apply_trust_decay()
        
        # 2. Check for bad sources
        self._check_bad_sources()
        
        # 3. Recalibrate confidence
        self._recalibrate_confidence()
        
        # 4. Promote/demote knowledge
        self._promote_demote()
        
        # 5. Process observed feedback
        self._process_feedback()
        
    def _apply_trust_decay(self):
        """Apply trust decay to sources over time"""
        days_since_update = (time.time() - self.pipeline.last_learning) / 86400
        
        for source in self.pipeline.sources.values():
            if source.trust_level == TrustLevel.HIGH:
                # High trust decays slower
                decay = self.trust_decay_rate * days_since_update * 0.5
            else:
                decay = self.trust_decay_rate * days_since_update
                
            new_level = max(0, source.trust_level.value - int(decay * 10))
            source.trust_level = TrustLevel(new_level)
                
    def _check_bad_sources(self):
        """Quarantine sources with low trust"""
        for source in self.pipeline.sources.values():
            if source.trust_level == TrustLevel.LOW:
                self.quarantined_sources.add(source.url)
                logger.warning(f"Quarantined source: {source.url}")
                
    def _recalibrate_confidence(self):
        """Recalculate confidence based on usage and success"""
        for entry in self.pipeline.knowledge.values():
            # Adjust based on success rate
            if entry.usage_count > 0:
                success_rate = entry.success_count / entry.usage_count
                # Blend with original confidence
                entry.confidence = (entry.confidence * 0.7 + success_rate * 0.3)
                
    def _promote_demote(self):
        """Promote high-confidence, demote low-confidence knowledge"""
        promoted = 0
        demoted = 0
        
        for entry in self.pipeline.knowledge.values():
            if entry.confidence >= self.promotion_threshold:
                entry.confidence = min(1.0, entry.confidence + 0.05)
                promoted += 1
            elif entry.confidence <= self.demotion_threshold:
                entry.confidence = max(0.0, entry.confidence - 0.05)
                demoted += 1
                
        if promoted or demoted:
            logger.info(f"Governance: {promoted} promoted, {demoted} demoted")
    
    # Feedback types for observed-world closed loop
    class FeedbackType(Enum):
        """Types of feedback from observed world"""
        SUCCESS = "success"           # Task completed successfully
        FAILURE = "failure"           # Task failed
        PARTIAL_SUCCESS = "partial"    # Task partially completed
        CONTRADICTION = "contradiction"  # Found contradicting evidence
        VERIFICATION = "verification" # Manually verified
        OUTDATED = "outdated"         # Information is outdated
        ACCURATE = "accurate"         # Confirmed accurate
        HELPFUL = "helpful"           # User marked as helpful
        NOT_HELPFUL = "not_helpful"   # User marked as not helpful
        ERROR = "error"               # Error when using knowledge
    
    def _process_feedback(self):
        """
        Process observed-world feedback from real task execution.
        
        This is the critical 24/7 learning loop that integrates
        actual task outcomes into knowledge quality.
        """
        # Process pending feedback queue
        for feedback in list(self.feedback_queue):
            try:
                self._apply_feedback(feedback)
                self.feedback_queue.remove(feedback)
            except Exception as e:
                logger.error(f"Failed to process feedback: {e}")
        
        # Process task outcomes if available
        self._process_task_outcomes()
        
        # Update source trust based on aggregate feedback
        self._update_source_trust_from_feedback()
        
        # Check for knowledge that needs re-verification
        self._flag_for_reverification()
    
    def _apply_feedback(self, feedback: Dict):
        """Apply a single feedback item to knowledge entries"""
        entry_id = feedback.get("entry_id")
        feedback_type = feedback.get("type")
        details = feedback.get("details", {})
        
        if entry_id not in self.pipeline.knowledge:
            logger.warning(f"Feedback for unknown entry: {entry_id}")
            return
        
        entry = self.pipeline.knowledge[entry_id]
        
        # Calculate feedback weight
        weight = self.feedback_weights.get(feedback_type, 0)
        
        # Adjust confidence based on feedback type
        if feedback_type == self.FeedbackType.SUCCESS.value:
            entry.success_count += 1
            entry.usage_count += 1
            # Positive reinforcement
            entry.confidence = min(1.0, entry.confidence + weight)
            entry.last_verified = time.time()
            
        elif feedback_type == self.FeedbackType.FAILURE.value:
            entry.usage_count += 1
            # Negative reinforcement
            entry.confidence = max(0.0, entry.confidence + weight)
            
        elif feedback_type == self.FeedbackType.CONTRADICTION.value:
            # Check for contradiction and flag
            self._handle_contradiction_feedback(entry, details)
            entry.confidence = max(0.0, entry.confidence - 0.2)
            
        elif feedback_type == self.FeedbackType.OUTDATED.value:
            # Mark as stale, trigger re-verification
            entry.stale_score = 1.0
            entry.last_verified = time.time()
            
        elif feedback_type == self.FeedbackType.ACCURATE.value:
            # Manual verification - boost confidence
            entry.confidence = min(1.0, entry.confidence + 0.15)
            entry.last_verified = time.time()
            
        elif feedback_type == self.FeedbackType.HELPFUL.value:
            # User feedback - positive signal
            entry.confidence = min(1.0, entry.confidence + 0.05)
            
        elif feedback_type == self.FeedbackType.NOT_HELPFUL.value:
            # User feedback - negative signal
            entry.confidence = max(0.0, entry.confidence - 0.1)
        
        logger.info(f"Applied feedback: {entry_id} {feedback_type} -> confidence: {entry.confidence:.3f}")
    
    def _handle_contradiction_feedback(self, entry: KnowledgeEntry, details: Dict):
        """Handle feedback about contradicting information"""
        contradicting_entry_id = details.get("contradicting_entry_id")
        
        if contradicting_entry_id and contradicting_entry_id in self.pipeline.knowledge:
            # Create contradiction record
            contradiction = Contradiction(
                entry_a=entry.entry_id,
                entry_b=contradicting_entry_id,
                contradiction_type="feedback_reported",
                severity=0.9,  # High severity since reported by user
                detected_at=time.time(),
                resolution="pending"
            )
            self.pipeline.contradiction_detector.contradictions.append(contradiction)
            logger.warning(f"Contradiction detected via feedback: {entry.entry_id} vs {contradicting_entry_id}")
    
    def _process_task_outcomes(self):
        """Process task execution outcomes from the observed world"""
        # Check for task outcome file (written by agent)
        task_file = Path("/tmp/learning_task_outcomes.json")
        
        if not task_file.exists():
            return
        
        try:
            with open(task_file) as f:
                outcomes = json.load(f)
            
            for outcome in outcomes:
                entry_id = outcome.get("knowledge_entry_id")
                if not entry_id:
                    continue
                    
                if outcome.get("success"):
                    self.record_feedback(entry_id, "success")
                else:
                    self.record_feedback(entry_id, "failure")
            
            # Clear processed outcomes
            task_file.unlink()
            
        except Exception as e:
            logger.debug(f"Could not process task outcomes: {e}")
    
    def _update_trust_from_outcome(self, source: str, success: bool):
        """Update source trust based on task outcome"""
        if source not in self.source_trust:
            self.source_trust[source] = 0.5
        if success:
            self.source_trust[source] = min(1.0, self.source_trust[source] + 0.05)
        else:
            self.source_trust[source] = max(0.0, self.source_trust[source] - 0.1)
        logger.info(f"Source trust: {source} -> {self.source_trust[source]:.3f}")

    def _update_procedural_memory(self, entry_id: str, outcome: Dict):
        """Update procedural memory with task execution details"""
        if outcome.get("success") and outcome.get("steps"):
            self.procedural_memory[entry_id] = {
                "steps": outcome["steps"],
                "success_rate": outcome.get("success_rate", 1.0),
                "last_used": time.time(),
                "task_type": outcome.get("task_type", "unknown")
            }

    def _handle_contradiction(self, entry_id: str, contradicts_with: str):
        """Handle contradiction between knowledge entries"""
        entry = self.pipeline.knowledge.get(entry_id)
        other = self.pipeline.knowledge.get(contradicts_with)
        if entry and other:
            entry.contradictions.append(contradicts_with)
            other.contradictions.append(entry_id)
            entry.confidence = max(0.0, entry.confidence - 0.2)
            other.confidence = max(0.0, other.confidence - 0.2)
            logger.warning(f"Contradiction: {entry_id} <-> {contradicts_with}")

    def _evaluate_knowledge_promotion(self, entry, outcome: Dict):
        """Evaluate and promote/demote knowledge based on outcome"""
        if hasattr(entry, 'usage_count') and entry.usage_count > 0:
            success_rate = entry.success_count / entry.usage_count
            if success_rate > 0.9 and entry.usage_count > 5:
                entry.trust_level = "high"
                entry.priority = "high"
            elif success_rate < 0.5 and entry.usage_count > 3:
                entry.trust_level = "low"
                entry.priority = "low"
                entry.needs_review = True


    def _update_source_trust_from_feedback(self):
        """Update source trust based on aggregate feedback"""
        source_performance = defaultdict(lambda: {"success": 0, "failure": 0})
        
        # Aggregate feedback by source
        for entry in self.pipeline.knowledge.values():
            if entry.usage_count > 0:
                source = entry.source
                source_performance[source]["total"] = source_performance[source].get("total", 0) + entry.usage_count
                source_performance[source]["success"] += entry.success_count
        
        # Adjust trust based on performance
        for source_url, perf in source_performance.items():
            if source_url in self.pipeline.sources:
                source = self.pipeline.sources[source_url]
                total = perf.get("total", 0)
                
                if total >= 5:  # Need minimum sample size
                    success_rate = perf["success"] / total
                    
                    # Adjust trust level
                    if success_rate >= 0.9:
                        source.trust_level = TrustLevel.HIGH
                    elif success_rate >= 0.7:
                        source.trust_level = TrustLevel.MEDIUM
                    elif success_rate < 0.3:
                        source.trust_level = TrustLevel.LOW
                        self.quarantined_sources.add(source_url)
                    else:
                        source.trust_level = TrustLevel.MEDIUM
    
    def _flag_for_reverification(self):
        """Flag knowledge entries that need re-verification"""
        current_time = time.time()
        
        for entry in self.pipeline.knowledge.values():
            # Flag if:
            # 1. Not verified in 180 days
            # 2. Has high usage but declining success rate
            # 3. Marked as potentially outdated
            
            days_since_verify = (current_time - entry.last_verified) / 86400
            
            if days_since_verify > 180:
                entry.metadata["needs_verification"] = True
                entry.metadata["verification_reason"] = "stale"
                
            elif entry.usage_count >= 10:
                success_rate = entry.success_count / entry.usage_count
                if success_rate < 0.5:
                    entry.metadata["needs_verification"] = True
                    entry.metadata["verification_reason"] = "declining_success"
    
    def queue_feedback(self, entry_id: str, feedback_type: str, details: Dict = None):
        """Queue feedback for processing in governance loop"""
        feedback = {
            "entry_id": entry_id,
            "type": feedback_type,
            "details": details or {},
            "timestamp": time.time()
        }
        self.feedback_queue.append(feedback)
        logger.debug(f"Queued feedback: {entry_id} - {feedback_type}")
    
    def record_feedback(self, entry_id: str, feedback_type: str):
        """Record feedback on a knowledge entry"""
        if entry_id not in self.pipeline.knowledge:
            return
            
        entry = self.pipeline.knowledge[entry_id]
        weight = self.feedback_weights.get(feedback_type, 0)
        
        entry.confidence = max(0, min(1, entry.confidence + weight))
        logger.info(f"Feedback recorded: {entry_id} {feedback_type} -> {entry.confidence}")


# ==================== UNIFIED LEARNING SYSTEM ====================

class UnifiedLearning:
    """
    Unified learning system that combines:
    - ContinuousLearningPipeline (main pipeline)
    - KnowledgeGovernance (governance)
    - SelfLearningEngine (helper)
    """
    
    def __init__(self, api_key: str = None, data_dir: str = None):
        self.api_key = api_key
        
        # Main pipeline
        self.pipeline = ContinuousLearningPipeline(api_key)
        
        # Governance
        self.governance = KnowledgeGovernance(self.pipeline)
        
        # Start governance loop
        self._start_governance()
        
    def _start_governance(self):
        """Start governance in background"""
        def loop():
            while True:
                try:
                    self.governance.governance_loop()
                except Exception as e:
                    logger.warning(f"Governance error: {e}")
                time.sleep(3600)  # Hourly
                
        threading.Thread(target=loop, daemon=True).start()
        
    def learn(self, content: str, source_url: str, source_type: SourceType,
              knowledge_type: KnowledgeType, tags: List[str] = None) -> str:
        """Add knowledge to pipeline"""
        return self.pipeline.add_knowledge(content, source_url, source_type, knowledge_type, tags)
        
    def query(self, query: str, min_confidence: float = 0.3) -> List[KnowledgeEntry]:
        """Query knowledge"""
        return self.pipeline.query(query, min_confidence)
        
    def record_success(self, entry_id: str):
        """Record successful use of knowledge"""
        if entry_id in self.pipeline.knowledge:
            entry = self.pipeline.knowledge[entry_id]
            entry.success_count += 1
            self.governance.record_feedback(entry_id, "success")
            
    def record_failure(self, entry_id: str):
        """Record failed use of knowledge"""
        if entry_id in self.pipeline.knowledge:
            entry = self.pipeline.knowledge[entry_id]
            entry.usage_count += 1
            self.governance.record_feedback(entry_id, "failure")
            
    def get_stats(self) -> Dict:
        """Get unified stats"""
        stats = self.pipeline.get_stats()
        stats["quarantined_sources"] = len(self.governance.quarantined_sources)
        return stats


def create_unified_learning(api_key: str = None, data_dir: str = None):
    """Factory function for unified learning"""
    return UnifiedLearning(api_key, data_dir)


# ==================== OBSERVED-WORLD LEARNING SYSTEM ====================
# Advanced 24/7 learning with production feedback

class ObservedWorldLearning:
    """
    Observed-World Learning System - Advanced 24/7 Learning
    
    Features:
    - User correction feedback weighting
    - Production task outcome feedback
    - Benchmark-driven knowledge demotion
    - Bad source quarantine
    - Trust decay over time
    - Self-observed contradiction resolution
    """
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        
        # Feedback weights
        self.feedback_weights = {
            "user_correction": 0.9,      # User corrections are most valuable
            "production_outcome": 0.8,   # Production results
            "benchmark_result": 0.7,     # Benchmark performance
            "self_observed": 0.6,        # Self-observed errors
            "default": 0.3               # Default weight
        }
        
        # Trust decay configuration
        self.trust_decay_half_life = 30 * 24 * 3600  # 30 days
        self.min_trust_threshold = 0.2
        
        # Quarantine
        self.quarantined_sources: Set[str] = set()
        self.quarantine_threshold = 0.3
        
        # Contradiction resolution
        self.contradiction_log: List[Dict] = []
        
        # Production feedback cache
        self.production_outcomes: Dict[str, Dict] = {}
        
        logger.info("🌍 Observed-World Learning System initialized")
    
    # ==================== USER CORRECTION FEEDBACK ====================
    
    def process_user_correction(self, entry_id: str, correction: Dict) -> Dict:
        """
        Process user correction feedback with high weight.
        
        User corrections are the most valuable feedback source.
        """
        correction_type = correction.get("type", "direct")
        
        # Higher weight for direct corrections
        weight = self.feedback_weights["user_correction"]
        
        if correction_type == "direct":
            weight *= 1.0
        elif correction_type == "indirect":
            weight *= 0.7
        elif correction_type == "implicit":
            weight *= 0.5
        
        return {
            "entry_id": entry_id,
            "correction_type": correction_type,
            "weight": weight,
            "applied": True
        }
    
    # ==================== PRODUCTION OUTCOME FEEDBACK ====================
    
    def record_production_outcome(self, task_id: str, outcome: Dict):
        """
        Record production task outcome.
        
        Tracks:
        - task success/failure
        - knowledge used
        - outcome quality
        - latency
        """
        self.production_outcomes[task_id] = {
            "success": outcome.get("success", False),
            "knowledge_used": outcome.get("knowledge_used", []),
            "quality_score": outcome.get("quality_score", 0.5),
            "latency_ms": outcome.get("latency_ms", 0),
            "timestamp": time.time(),
            "user_satisfaction": outcome.get("user_satisfaction")
        }
    
    def get_production_feedback(self, entry_id: str) -> Dict:
        """Get aggregated production feedback for a knowledge entry"""
        relevant = [
            o for o in self.production_outcomes.values()
            if entry_id in o.get("knowledge_used", [])
        ]
        
        if not relevant:
            return {"score": 0.5, "count": 0}
        
        avg_quality = sum(o["quality_score"] for o in relevant) / len(relevant)
        success_rate = sum(1 for o in relevant if o["success"]) / len(relevant)
        
        return {
            "score": avg_quality * success_rate,
            "count": len(relevant),
            "avg_quality": avg_quality,
            "success_rate": success_rate
        }
    
    # ==================== BENCHMARK-DRIVEN DEMOTION ====================
    
    def apply_benchmark_demotion(self, entry_id: str, benchmark_result: Dict):
        """
        Demote knowledge based on benchmark performance.
        
        If benchmark shows degradation, reduce knowledge confidence.
        """
        score = benchmark_result.get("score", 1.0)
        
        # Demotion factor based on score
        if score < 0.5:
            demotion_factor = 0.3
        elif score < 0.7:
            demotion_factor = 0.6
        else:
            demotion_factor = 1.0
        
        return {
            "entry_id": entry_id,
            "demotion_factor": demotion_factor,
            "benchmark_score": score
        }
    
    # ==================== BAD SOURCE QUARANTINE ====================
    
    def quarantine_source(self, source_url: str, reason: str):
        """Quarantine a bad source"""
        self.quarantined_sources.add(source_url)
        
        logger.warning(f"🔒 Source quarantined: {source_url} - {reason}")
    
    def is_quarantined(self, source_url: str) -> bool:
        """Check if source is quarantined"""
        return source_url in self.quarantined_sources
    
    def auto_quarantine_bad_sources(self, knowledge_entries: Dict[str, Any]) -> int:
        """
        Automatically quarantine sources with high failure rates.
        """
        source_stats = defaultdict(lambda: {"total": 0, "failures": 0})
        
        for entry in knowledge_entries.values():
            source = entry.get("source", "")
            if source:
                source_stats[source]["total"] += 1
                if entry.get("success_count", 0) < entry.get("usage_count", 1) * 0.3:
                    source_stats[source]["failures"] += 1
        
        quarantined = 0
        for source, stats in source_stats.items():
            if stats["total"] >= 5:  # Minimum samples
                failure_rate = stats["failures"] / stats["total"]
                if failure_rate > self.quarantine_threshold:
                    self.quarantine_source(source, f"Failure rate: {failure_rate:.1%}")
                    quarantined += 1
        
        return quarantined
    
    # ==================== TRUST DECAY ====================
    
    def apply_trust_decay(self, entry: KnowledgeEntry) -> float:
        """
        Apply trust decay based on time since last verification.
        
        Older, unverified knowledge decays in confidence.
        """
        time_since_verify = time.time() - entry.last_verified
        
        # Exponential decay
        decay_factor = 0.5 ** (time_since_verify / self.trust_decay_half_life)
        
        # Don't decay below minimum threshold
        decay_factor = max(decay_factor, self.min_trust_threshold)
        
        return decay_factor
    
    def get_decayed_confidence(self, entry: KnowledgeEntry) -> float:
        """Get confidence with decay applied"""
        base_confidence = entry.confidence
        decay_factor = self.apply_trust_decay(entry)
        
        return base_confidence * decay_factor
    
    # ==================== SELF-OBSERVED CONTRADICTION ====================
    
    def detect_self_observed_contradiction(self, entry_a: KnowledgeEntry, 
                                          entry_b: KnowledgeEntry) -> Dict:
        """
        Detect and resolve contradictions from self-observation.
        
        When agent uses two conflicting pieces of knowledge.
        """
        # Calculate semantic similarity
        similarity = self._calculate_similarity(entry_a.content, entry_b.content)
        
        if similarity > 0.8:
            # Check for negation
            negations = [("not", "is"), ("false", "true"), ("no", "yes")]
            has_negation = any(
                (neg[0] in entry_a.content.lower() and neg[1] in entry_b.content.lower()) or
                (neg[1] in entry_a.content.lower() and neg[0] in entry_b.content.lower())
                for neg in negations
            )
            
            if has_negation:
                contradiction = {
                    "entry_a": entry_a.entry_id,
                    "entry_b": entry_b.entry_id,
                    "type": "self_observed",
                    "severity": "high",
                    "resolution": None
                }
                
                # Try to resolve based on evidence
                if entry_a.usage_count > entry_b.usage_count:
                    contradiction["resolution"] = "prefer_a"
                    entry_b.confidence *= 0.5
                elif entry_b.usage_count > entry_a.usage_count:
                    contradiction["resolution"] = "prefer_b"
                    entry_a.confidence *= 0.5
                else:
                    contradiction["resolution"] = "demote_both"
                    entry_a.confidence *= 0.7
                    entry_b.confidence *= 0.7
                
                self.contradiction_log.append(contradiction)
                return contradiction
        
        return {"type": "none"}
    
    def _calculate_similarity(self, text_a: str, text_b: str) -> float:
        """Calculate semantic similarity between two texts"""
        words_a = set(text_a.lower().split())
        words_b = set(text_b.lower().split())
        
        if not words_a or not words_b:
            return 0.0
        
        intersection = len(words_a & words_b)
        union = len(words_a | words_b)
        
        return intersection / union if union > 0 else 0.0
    
    # ==================== MASTER LEARNING METHOD ====================
    
    def process_observed_feedback(self, feedback: Dict) -> Dict:
        """
        Process all types of observed-world feedback.
        
        Combines user corrections, production outcomes, benchmarks, 
        and self-observations into unified learning signal.
        """
        feedback_type = feedback.get("type", "default")
        
        if feedback_type == "user_correction":
            result = self.process_user_correction(
                feedback["entry_id"],
                feedback.get("correction", {})
            )
        elif feedback_type == "production":
            self.record_production_outcome(
                feedback["task_id"],
                feedback.get("outcome", {})
            )
            result = {"processed": True}
        elif feedback_type == "benchmark":
            result = self.apply_benchmark_demotion(
                feedback["entry_id"],
                feedback.get("result", {})
            )
        elif feedback_type == "contradiction":
            result = self.detect_self_observed_contradiction(
                feedback["entry_a"],
                feedback["entry_b"]
            )
        else:
            result = {"error": "Unknown feedback type"}
        
        return result
    
    def get_learning_health(self) -> Dict:
        """Get overall learning system health"""
        return {
            "quarantined_sources": len(self.quarantined_sources),
            "contradictions_resolved": len(self.contradiction_log),
            "production_outcomes": len(self.production_outcomes),
            "feedback_weights": self.feedback_weights
        }


def create_observed_world_learning(config: Dict = None) -> ObservedWorldLearning:
    """Factory function for ObservedWorldLearning"""
    return ObservedWorldLearning(config)

