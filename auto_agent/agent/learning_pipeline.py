"""OmniAgent X - Enhanced Continuous Learning Pipeline
===============================================
24/7 autonomous learning with all features
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
    PREFERENCE = "preference"


class KnowledgeStatus(Enum):
    """Knowledge lifecycle status - canonical state machine"""
    CANDIDATE = "candidate"       # Newly discovered, not verified
    VERIFIED = "verified"         # Verified and trusted
    STALE = "stale"               # Outdated, needs re-verification
    DISPUTED = "disputed"         # Contradiction detected
    QUARANTINED = "quarantined"   # Flagged for review
    RETIRED = "retired"           # No longer relevant


class LearningEventType(Enum):
    """Learning event types - history-rich system"""
    KNOWLEDGE_ADDED = "knowledge_added"
    KNOWLEDGE_VERIFIED = "knowledge_verified"
    KNOWLEDGE_RETRIEVED = "knowledge_retrieved"
    KNOWLEDGE_SELECTED = "knowledge_selected"
    KNOWLEDGE_EXECUTED = "knowledge_executed"
    KNOWLEDGE_SUCCEEDED = "knowledge_succeeded"
    KNOWLEDGE_FAILED = "knowledge_failed"
    CONTRADICTION_DETECTED = "contradiction_detected"
    SOURCE_QUARANTINED = "source_quarantined"
    KNOWLEDGE_REVERIFIED = "knowledge_reverified"
    KNOWLEDGE_RETIRED = "knowledge_retired"


class ConfidenceLevel(Enum):
    VERY_HIGH = 1.0
    HIGH = 0.8
    MEDIUM = 0.6
    LOW = 0.4
    VERY_LOW = 0.2


@dataclass
class Source:
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


@dataclass
class KnowledgeEntry:
    """Canonical Knowledge Record - single source of truth for all knowledge"""
    # Required fields (no defaults)
    entry_id: str
    content: str
    knowledge_type: KnowledgeType
    source: str
    source_url: str
    collected_at: float
    last_verified: float
    confidence: float
    
    # Lifecycle status - canonical state machine
    status: KnowledgeStatus = KnowledgeStatus.CANDIDATE
    
    # Learning signals - separated concerns
    retrieval_count: int = 0        # How many times retrieved
    selection_count: int = 0        # How many times selected from results
    execution_count: int = 0        # How many times actually used
    success_count: int = 0          # How many times succeeded
    failure_count: int = 0          # How many times failed
    
    # Additional data
    embedding: List[float] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    entities: List[str] = field(default_factory=list)
    relationships: List[Dict] = field(default_factory=list)
    
    # Governance data
    contradiction_hash: str = ""
    stale_score: float = 0.0
    
    # Metadata and contradictions - schema-driven
    metadata: Dict[str, Any] = field(default_factory=dict)
    contradictions: List[str] = field(default_factory=list)
    
    # Truth Ledger - history tracking
    first_seen_at: float = field(default_factory=time.time)
    verified_at: Optional[float] = None
    valid_from: Optional[float] = None
    valid_until: Optional[float] = None
    
    # Lineage
    supersedes: Optional[str] = None
    superseded_by: Optional[str] = None
    
    # Task domains
    task_domains: List[str] = field(default_factory=list)
    
    # Evidence
    evidence_count: int = 0
    
    # Invariant check
    def __post_init__(self):
        """Validate invariants"""
        # success_count <= execution_count
        if self.success_count > self.execution_count:
            self.success_count = self.execution_count
        # failure_count <= execution_count
        if self.failure_count > self.execution_count:
            self.failure_count = self.execution_count
        # selection_count <= retrieval_count
        if self.selection_count > self.retrieval_count:
            self.selection_count = self.retrieval_count
        # verified_at >= collected_at
        if self.verified_at and self.verified_at < self.collected_at:
            self.verified_at = self.collected_at
    
    @property
    def usage_count(self) -> int:
        """Backward compatibility - returns retrieval_count"""
        return self.retrieval_count
    
    @usage_count.setter
    def usage_count(self, value: int):
        """Backward compatibility - sets retrieval_count"""
        self.retrieval_count = value


@dataclass
class Contradiction:
    entry_a: str
    entry_b: str
    contradiction_type: str
    severity: float
    detected_at: float
    resolution: str = ""


@dataclass
class ProceduralMemory:
    """Canonical Procedure Record - for procedure knowledge"""
    # Required fields
    procedure_id: str
    name: str
    steps: List[Dict]
    
    # Goal signature - what this procedure achieves
    goal_signature: str = ""
    
    # Procedure details
    prerequisites: List[str] = field(default_factory=list)
    outcomes: List[str] = field(default_factory=list)
    required_tools: List[str] = field(default_factory=list)
    expected_artifacts: List[str] = field(default_factory=list)
    success_criteria: str = ""
    
    # Learning signals - REAL signals
    success_count: int = 0        # How many times succeeded
    failure_count: int = 0        # How many times failed
    execution_count: int = 0       # Total executions
    success_rate: float = 0.0
    
    # Performance metrics
    median_latency: float = 0.0
    last_used: float = 0.0
    last_success_at: Optional[float] = None
    
    # Domain
    domains: List[str] = field(default_factory=list)
    
    # Failure modes
    failure_modes: List[str] = field(default_factory=list)
    
    # Verification
    verified_against: List[str] = field(default_factory=list)
    verified_at: Optional[float] = None
    
    # Lifecycle
    status: KnowledgeStatus = KnowledgeStatus.CANDIDATE
    
    def __post_init__(self):
        """Calculate derived fields"""
        if self.execution_count > 0:
            self.success_rate = self.success_count / self.execution_count


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
    def __init__(self):
        self.weights = {TrustLevel.HIGH: 1.0, TrustLevel.MEDIUM: 0.7, TrustLevel.LOW: 0.4, TrustLevel.UNKNOWN: 0.2}
    
    def calculate(self, entry: KnowledgeEntry, source: Source) -> float:
        trust = self.weights.get(source.trust_level, 0.2) * 0.4
        age = (time.time() - entry.collected_at) / 86400
        fresh = max(0, 1 - (age / 365)) * 0.2
        
        ver = 0.0
        if entry.last_verified > entry.collected_at:
            vage = (time.time() - entry.last_verified) / 86400
            ver = max(0, 1 - (vage / 180)) * 0.2
        
        evi = min(1.0, len(entry.relationships) / 10) * 0.2 if entry.relationships else 0.0
        
        total = trust + fresh + ver + evi
        
        if entry.knowledge_type == KnowledgeType.FACT:
            total *= 1.1
        elif entry.knowledge_type == KnowledgeType.OPINION:
            total *= 0.8
        
        return min(1.0, total)


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
        """Record procedure execution - FIXED: using correct fields"""
        if pid in self.procedures:
            p = self.procedures[pid]
            p.execution_count += 1
            if success:
                p.success_count += 1
                p.last_success_at = time.time()
            else:
                p.failure_count += 1
            # Recalculate success rate
            if p.execution_count > 0:
                p.success_rate = p.success_count / p.execution_count
            p.last_used = time.time()


# MAIN LEARNING PIPELINE
class ContinuousLearningPipeline:
    def __init__(self, api_key: str = None):
        self.api_key = api_key
        self.source_ranker = SourceRanker()
        self.contradiction_detector = ContradictionDetector()
        self.stale_pruner = StaleKnowledgePruner()
        self.confidence_scorer = ConfidenceScorer()
        self.procedural = ProceduralMemoryManager()
        
        self.knowledge: Dict[str, KnowledgeEntry] = {}
        self.sources: Dict[str, Source] = {}
        
        self.learning_enabled = True
        self.learning_interval = 3600
        self.last_learning = 0.0
        
        self.topics = ["ai", "machine learning", "python", "software engineering"]
        
        self._start_background()
        
        logger.info("Continuous Learning Pipeline initialized")
    
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
        
        self.last_learning = time.time()
    
    def add_knowledge(self, content: str, source_url: str, source_type: SourceType,
                     knowledge_type: KnowledgeType, tags: List[str] = None) -> str:
        
        entry_id = hashlib.md5(content.encode()).hexdigest()[:16]
        
        source = self.sources.get(source_url)
        if not source:
            source = Source(url=source_url, name=source_url, source_type=source_type)
            self.sources[source_url] = source
        
        entry = KnowledgeEntry(
            entry_id=entry_id,
            content=content,
            knowledge_type=knowledge_type,
            source=source.name,
            source_url=source_url,
            collected_at=time.time(),
            last_verified=time.time(),
            confidence=0.5,
            tags=tags or []
        )
        
        entry.confidence = self.confidence_scorer.calculate(entry, source)
        
        self.knowledge[entry_id] = entry
        self.contradiction_detector.add_knowledge(entry)
        self.stale_pruner.add_knowledge(entry)
        
        return entry_id
    
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
    
    def query(self, query: str, min_confidence: float = 0.3) -> List[KnowledgeEntry]:
        """Query knowledge - returns retrieved entries"""
        results = []
        qterms = set(query.lower().split())
        
        for entry in self.knowledge.values():
            if entry.confidence < min_confidence:
                continue
            
            # Skip non-active knowledge
            if entry.status in [KnowledgeStatus.RETIRED, KnowledgeStatus.QUARANTINED]:
                continue
                
            eterms = set(entry.content.lower().split())
            if qterms & eterms:
                # FIXED: Proper signal - retrieval_count, not usage_count
                entry.retrieval_count += 1
                results.append(entry)
        
        results.sort(key=lambda x: x.confidence, reverse=True)
        return results[:10]
    
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
        
        # FIXED: Initialize missing attributes
        self.source_trust: Dict[str, float] = {}  # source_url -> trust_score
        self.procedural_memory: Dict[str, Dict] = {}  # entry_id -> procedure_data
        self.knowledge_events: List[Dict] = []  # Truth Ledger events
        
    def record_event(self, event_type: LearningEventType, entry_id: str, details: Dict = None):
        """Record a learning event - history-rich system"""
        event = {
            "event_type": event_type.value,
            "entry_id": entry_id,
            "timestamp": time.time(),
            "details": details or {}
        }
        self.knowledge_events.append(event)
        
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
        """Record successful use of knowledge - proper signal semantics"""
        if entry_id in self.pipeline.knowledge:
            entry = self.pipeline.knowledge[entry_id]
            # FIXED: Proper signal semantics
            entry.execution_count += 1
            entry.success_count += 1
            # Record event for Truth Ledger
            self.governance.record_event(
                LearningEventType.KNOWLEDGE_SUCCEEDED,
                entry_id,
                {"execution_count": entry.execution_count}
            )
            
    def record_failure(self, entry_id: str):
        """Record failed use of knowledge - proper signal semantics"""
        if entry_id in self.pipeline.knowledge:
            entry = self.pipeline.knowledge[entry_id]
            # FIXED: Proper signal semantics
            entry.execution_count += 1
            entry.failure_count += 1
            # Record event for Truth Ledger
            self.governance.record_event(
                LearningEventType.KNOWLEDGE_FAILED,
                entry_id,
                {"execution_count": entry.execution_count}
            )
            
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

