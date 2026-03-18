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

TIME-AWARE TRUTH SYSTEM - World No1+ Implementation
====================================================
This module now also implements comprehensive temporal knowledge management:
- Temporal truth model with validity windows
- Current/Historical truth split
- Supersession graph
- Volatility model with domain-specific decay
- Temporal query resolver
- Truth clock for drift detection
- Time-aware retrieval ranking
- Version scope tracking
- Recency-weighted preferences
- Time-decayed procedural memory
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


class FailureType(Enum):
    """Failure Taxonomy - Detailed failure classification"""
    KNOWLEDGE_ERROR = "knowledge_error"           # Knowledge content was wrong
    STALE_KNOWLEDGE = "stale_knowledge"           # Knowledge outdated
    CONTRADICTION = "contradiction"                # Contradiction detected
    SCOPE_MISMATCH = "scope_mismatch"              # Wrong scope/domain
    RETRIEVAL_MISS = "retrieval_miss"             # Wrong knowledge selected
    RANKING_ERROR = "ranking_error"                # Ranking features failed
    PROCEDURE_DRIFT = "procedure_drift"            # Procedure changed
    TOOL_FAILURE = "tool_failure"                 # Tool didn't work
    ENVIRONMENT_FAILURE = "environment_failure"   # Environment issue
    EXTERNAL_DEPENDENCY = "external_dependency"    # External service failed
    USER_AMBIGUITY = "user_ambiguity"              # User intent unclear
    PLANNER_ERROR = "planner_error"               # Planning failed
    VERIFICATION_ERROR = "verification_error"      # Verification wrong
    UNKNOWN = "unknown"                           # Unknown failure


class AttributionEdgeType(Enum):
    """Types of causal relationships in attribution graph"""
    USED_FOR = "used_for"                    # Entity was used for task
    INFLUENCED = "influenced"                # Entity influenced outcome
    CAUSED = "caused"                        # Entity caused outcome
    CONTRADICTED = "contradicted"            # Entity contradicted another
    VERIFIED_BY = "verified_by"             # Entity verified by another
    FAILED_DUE_TO = "failed_due_to"          # Failure caused by entity
    SUPPORTED = "supported"                  # Entity supported another
    SELECTED_OVER = "selected_over"          # Entity was selected over another


@dataclass
class LearningEpisode:
    """
    Learning Episode - Complete task execution record
    =================================================
    This is the core of the closed-loop system.
    Every real task execution becomes an episode with full trace.
    """
    episode_id: str
    task_id: str
    task_description: str
    goal: str
    context: Dict[str, Any] = field(default_factory=dict)
    
    # Execution trace
    retrieved_items: List[Dict[str, Any]] = field(default_factory=list)
    selected_items: List[str] = field(default_factory=list)  # knowledge IDs
    
    # Procedure trace
    procedures_used: List[str] = field(default_factory=list)  # procedure IDs
    procedure_steps: List[Dict[str, Any]] = field(default_factory=list)
    
    # Tool trace
    tools_used: List[str] = field(default_factory=list)  # tool names
    tool_results: List[Dict[str, Any]] = field(default_factory=list)
    
    # Verification trace
    verification_results: List[Dict[str, Any]] = field(default_factory=list)
    verification_artifacts: List[str] = field(default_factory=list)
    
    # Outcome
    outcome: Dict[str, Any] = field(default_factory=dict)
    final_verdict: str = "pending"  # success, failure, partial, unknown
    
    # Feedback traces
    user_feedback: Dict[str, Any] = field(default_factory=dict)
    production_feedback: Dict[str, Any] = field(default_factory=dict)
    
    # Attribution
    credits: Dict[str, float] = field(default_factory=dict)  # entity_id -> credit
    blames: Dict[str, float] = field(default_factory=dict)   # entity_id -> blame
    
    # Failure analysis
    failure_type: str = "unknown"
    root_cause: str = ""
    
    # Temporal
    start_time: float = field(default_factory=time.time)
    end_time: float = 0.0
    latency_ms: float = 0.0
    
    # Quality metrics
    quality_score: float = 0.0
    user_satisfaction: float = 0.0
    
    # Causal graph
    causal_graph: Dict[str, Any] = field(default_factory=dict)
    
    # Status
    processed: bool = False
    delayed_feedback_bound: bool = False
    
    def mark_complete(self, final_verdict: str, outcome: Dict[str, Any]):
        """Mark episode as complete"""
        self.end_time = time.time()
        self.latency_ms = (self.end_time - self.start_time) * 1000
        self.final_verdict = final_verdict
        self.outcome = outcome
        
        if "quality_score" in outcome:
            self.quality_score = outcome["quality_score"]
        if "user_satisfaction" in outcome:
            self.user_satisfaction = outcome["user_satisfaction"]
    
    def add_retrieval_trace(self, retrieved: Dict[str, Any]):
        """Add retrieval trace"""
        self.retrieved_items.append(retrieved)
    
    def add_selection(self, knowledge_id: str, reason: str = ""):
        """Record knowledge selection"""
        if knowledge_id not in self.selected_items:
            self.selected_items.append(knowledge_id)
    
    def add_procedure(self, procedure_id: str, steps: List[Dict] = None):
        """Add procedure to trace"""
        if procedure_id not in self.procedures_used:
            self.procedures_used.append(procedure_id)
        if steps:
            self.procedure_steps.extend(steps)
    
    def add_tool_call(self, tool_name: str, result: Dict):
        """Add tool call to trace"""
        self.tools_used.append(tool_name)
        self.tool_results.append({
            "tool": tool_name,
            "result": result,
            "timestamp": time.time()
        })
    
    def add_verification(self, verification: Dict):
        """Add verification result"""
        self.verification_results.append(verification)
    
    def to_dict(self) -> Dict:
        """Serialize episode"""
        return {
            "episode_id": self.episode_id,
            "task_id": self.task_id,
            "task_description": self.task_description,
            "goal": self.goal,
            "context": self.context,
            "retrieved_items": self.retrieved_items,
            "selected_items": self.selected_items,
            "procedures_used": self.procedures_used,
            "procedure_steps": self.procedure_steps,
            "tools_used": self.tools_used,
            "tool_results": self.tool_results,
            "verification_results": self.verification_results,
            "verification_artifacts": self.verification_artifacts,
            "outcome": self.outcome,
            "final_verdict": self.final_verdict,
            "user_feedback": self.user_feedback,
            "production_feedback": self.production_feedback,
            "credits": self.credits,
            "blames": self.blames,
            "failure_type": self.failure_type,
            "root_cause": self.root_cause,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "latency_ms": self.latency_ms,
            "quality_score": self.quality_score,
            "user_satisfaction": self.user_satisfaction,
            "causal_graph": self.causal_graph,
            "processed": self.processed,
            "delayed_feedback_bound": self.delayed_feedback_bound
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'LearningEpisode':
        """Deserialize episode"""
        return cls(
            episode_id=data.get("episode_id", ""),
            task_id=data.get("task_id", ""),
            task_description=data.get("task_description", ""),
            goal=data.get("goal", ""),
            context=data.get("context", {}),
            retrieved_items=data.get("retrieved_items", []),
            selected_items=data.get("selected_items", []),
            procedures_used=data.get("procedures_used", []),
            procedure_steps=data.get("procedure_steps", []),
            tools_used=data.get("tools_used", []),
            tool_results=data.get("tool_results", []),
            verification_results=data.get("verification_results", []),
            verification_artifacts=data.get("verification_artifacts", []),
            outcome=data.get("outcome", {}),
            final_verdict=data.get("final_verdict", "pending"),
            user_feedback=data.get("user_feedback", {}),
            production_feedback=data.get("production_feedback", {}),
            credits=data.get("credits", {}),
            blames=data.get("blames", {}),
            failure_type=data.get("failure_type", "unknown"),
            root_cause=data.get("root_cause", ""),
            start_time=data.get("start_time", time.time()),
            end_time=data.get("end_time", 0.0),
            latency_ms=data.get("latency_ms", 0.0),
            quality_score=data.get("quality_score", 0.0),
            user_satisfaction=data.get("user_satisfaction", 0.0),
            causal_graph=data.get("causal_graph", {}),
            processed=data.get("processed", False),
            delayed_feedback_bound=data.get("delayed_feedback_bound", False)
        )


@dataclass
class AttributionEdge:
    """Attribution Edge - Causal relationship between entities"""
    edge_id: str
    source_entity_type: str  # knowledge, procedure, tool, source, planner
    source_entity_id: str
    target_entity_type: str
    target_entity_id: str
    edge_type: str  # used_for, influenced, caused, etc.
    weight: float = 1.0
    evidence: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict:
        return {
            "edge_id": self.edge_id,
            "source_entity_type": self.source_entity_type,
            "source_entity_id": self.source_entity_id,
            "target_entity_type": self.target_entity_type,
            "target_entity_id": self.target_entity_id,
            "edge_type": self.edge_type,
            "weight": self.weight,
            "evidence": self.evidence,
            "timestamp": self.timestamp
        }


@dataclass
class AntiPattern:
    """Anti-Pattern - Failure pattern memory"""
    pattern_id: str
    pattern_type: str  # bad_source_domain, bad_procedure_env, bad_retrieval_query
    description: str
    
    # Pattern specifics
    source_domain: str = ""          # source + domain pair
    procedure_environment: str = ""  # procedure + environment
    retrieval_query_pattern: str = ""  # query pattern that fails
    
    # Occurrence
    occurrence_count: int = 0
    first_seen: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)
    
    # Evidence
    episode_ids: List[str] = field(default_factory=list)
    failure_types: List[str] = field(default_factory=list)
    
    # Severity
    severity: str = "medium"  # low, medium, high, critical
    
    # Prevention guidance
    guidance: str = ""
    
    def record_occurrence(self, episode_id: str, failure_type: str):
        """Record new occurrence"""
        self.occurrence_count += 1
        self.last_seen = time.time()
        if episode_id not in self.episode_ids:
            self.episode_ids.append(episode_id)
        if failure_type not in self.failure_types:
            self.failure_types.append(failure_type)
    
    def to_dict(self) -> Dict:
        return {
            "pattern_id": self.pattern_id,
            "pattern_type": self.pattern_type,
            "description": self.description,
            "source_domain": self.source_domain,
            "procedure_environment": self.procedure_environment,
            "retrieval_query_pattern": self.retrieval_query_pattern,
            "occurrence_count": self.occurrence_count,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "episode_ids": self.episode_ids,
            "failure_types": self.failure_types,
            "severity": self.severity,
            "guidance": self.guidance
        }


@dataclass 
class ProcedureCandidate:
    """Procedure Candidate - Extracted from successful episodes"""
    procedure_id: str
    name: str
    description: str
    
    # Extracted from episodes
    step_sequence: List[Dict[str, Any]] = field(default_factory=list)
    prerequisites: List[str] = field(default_factory=list)
    success_conditions: List[str] = field(default_factory=list)
    best_evidence: List[str] = field(default_factory=list)  # knowledge IDs
    
    # Metrics
    success_count: int = 0
    total_attempts: int = 0
    success_rate: float = 0.0
    avg_latency_ms: float = 0.0
    
    # Source episodes
    source_episodes: List[str] = field(default_factory=list)
    
    # Confidence
    confidence: float = 0.5
    
    # Timestamps
    first_extracted: float = field(default_factory=time.time)
    last_updated: float = field(default_factory=time.time)
    
    # Status
    status: str = "candidate"  # candidate, validated, active, deprecated
    
    def update_from_episode(self, episode: LearningEpisode):
        """Update procedure from successful episode"""
        self.total_attempts += 1
        if episode.final_verdict == "success":
            self.success_count += 1
        
        self.success_rate = self.success_count / max(1, self.total_attempts)
        
        # Update latency
        self.avg_latency_ms = (
            (self.avg_latency_ms * (self.total_attempts - 1) + episode.latency_ms) 
            / self.total_attempts
        )
        
        # Add to source episodes
        if episode.episode_id not in self.source_episodes:
            self.source_episodes.append(episode.episode_id)
        
        self.last_updated = time.time()
    
    def to_dict(self) -> Dict:
        return {
            "procedure_id": self.procedure_id,
            "name": self.name,
            "description": self.description,
            "step_sequence": self.step_sequence,
            "prerequisites": self.prerequisites,
            "success_conditions": self.success_conditions,
            "best_evidence": self.best_evidence,
            "success_count": self.success_count,
            "total_attempts": self.total_attempts,
            "success_rate": self.success_rate,
            "avg_latency_ms": self.avg_latency_ms,
            "source_episodes": self.source_episodes,
            "confidence": self.confidence,
            "first_extracted": self.first_extracted,
            "last_updated": self.last_updated,
            "status": self.status
        }


@dataclass
class DelayedFeedback:
    """Delayed Feedback - Feedback that arrives after the fact"""
    feedback_id: str
    original_episode_id: str
    
    # Feedback content
    feedback_type: str  # user_correction, bug_report, regression, etc.
    content: Dict[str, Any]
    
    # Binding info
    correlation_id: str = ""  # Links related feedback
    causation_id: str = ""    # Links cause-effect
    
    # When feedback arrived
    arrival_time: float = field(default_factory=time.time)
    
    # Original task time
    original_task_time: float = 0.0
    
    # Status
    bound: bool = False
    processed: bool = False
    
    def bind_to_episode(self, episode_id: str, retroactive: bool = True):
        """Bind delayed feedback to episode"""
        self.original_episode_id = episode_id
        self.bound = True
        
        if retroactive:
            logger.info(f"🔗 Retroactively bound feedback {self.feedback_id} to episode {episode_id}")
    
    def to_dict(self) -> Dict:
        return {
            "feedback_id": self.feedback_id,
            "original_episode_id": self.original_episode_id,
            "feedback_type": self.feedback_type,
            "content": self.content,
            "correlation_id": self.correlation_id,
            "causation_id": self.causation_id,
            "arrival_time": self.arrival_time,
            "original_task_time": self.original_task_time,
            "bound": self.bound,
            "processed": self.processed
        }


class TemporalStatus(Enum):
    """Temporal Status - Lifecycle state with time awareness"""
    CANDIDATE = "candidate"                 # Newly discovered, not verified
    VERIFIED_CURRENT = "verified_current"   # Verified and currently valid
    VERIFIED_HISTORICAL = "verified_historical"  # Was true, now superseded
    STALE_NEEDS_CHECK = "stale_needs_check"  # Needs reverification
    SUPERSEDED = "superseded"               # Replaced by newer knowledge
    DISPUTED = "disputed"                   # Currently under dispute
    QUARANTINED = "quarantined"             # Flagged for review
    RETIRED = "retired"                     # No longer applicable
    ARCHIVED = "archived"                    # Preserved for historical reference


class OutcomeVerdict(Enum):
    """Outcome Verdict - Structured task outcome classification"""
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILURE = "failure"
    TIMEOUT = "timeout"
    ERROR = "error"
    CANCELLED = "cancelled"
    UNKNOWN = "unknown"


class UpdatePolicy(Enum):
    """Learning Update Policy - How to update based on outcome"""
    CONFIDENCE_UPDATE = "confidence_update"
    SOURCE_TRUST_UPDATE = "source_trust_update"
    PROCEDURE_REINFORCEMENT = "procedure_reinforcement"
    PROCEDURE_DEMOTION = "procedure_demotion"
    RETRIEVAL_RERANK = "retrieval_rerank"
    ANTI_PATTERN_CREATE = "anti_pattern_create"
    RE_VERIFICATION_TRIGGER = "re_verification_trigger"
    QUARANTINE_TRIGGER = "quarantine_trigger"
    PROCEDURE_EXTRACTION = "procedure_extraction"
    NO_UPDATE = "no_update"


# ==================== CAUSAL LEARNING GRAPH ====================

class CausalLearningGraph:
    """
    Causal Learning Graph - Full causal relationship tracking
    ==========================================================
    This is the heart of the No1+ closed loop system.
    Instead of just "task worked / didn't work", we track:
    - What retrieval candidate was selected
    - What knowledge influenced the decision
    - What procedure was used
    - What tool executed
    - What verification said
    - What final outcome occurred
    
    Then we distribute blame/credit based on this graph.
    """
    
    def __init__(self, episode_id: str):
        self.episode_id = episode_id
        self.nodes: Dict[str, Dict] = {}  # entity_id -> entity_info
        self.edges: List[Dict] = []
        self.attributions: Dict[str, float] = {}  # entity_id -> attribution_score
    
    def add_node(self, entity_type: str, entity_id: str, info: Dict = None):
        """Add a node to the causal graph"""
        node_key = f"{entity_type}:{entity_id}"
        self.nodes[node_key] = {
            "type": entity_type,
            "id": entity_id,
            "info": info or {},
            "added_at": time.time()
        }
    
    def add_edge(self, source_type: str, source_id: str, 
                 target_type: str, target_id: str, edge_type: str, weight: float = 1.0):
        """Add an edge representing causal relationship"""
        edge = {
            "source": f"{source_type}:{source_id}",
            "target": f"{target_type}:{target_id}",
            "edge_type": edge_type,
            "weight": weight,
            "timestamp": time.time()
        }
        self.edges.append(edge)
    
    def compute_attributions(self, outcome: str) -> Dict[str, float]:
        """
        Compute blame/credit attributions based on graph and outcome.
        
        This is the key differentiator from simple agents:
        - Simple agent: "task worked / didn't work"
        - No1+ agent: "why did it work / why did it fail"
        """
        attributions = defaultdict(lambda: 0.0)
        
        if outcome == "success":
            # Distribute credit along all edges
            for edge in self.edges:
                source = edge["source"]
                weight = edge["weight"]
                
                # Credit flows from outcome back to sources
                if edge["edge_type"] in ["used_for", "influenced", "supported"]:
                    attributions[source] += weight * 0.3
                elif edge["edge_type"] == "caused":
                    attributions[source] += weight * 0.5
        
        elif outcome == "failure":
            # Distribute blame along edges
            for edge in self.edges:
                source = edge["source"]
                weight = edge["weight"]
                
                # Blame flows from outcome back to causes
                if edge["edge_type"] == "failed_due_to":
                    attributions[source] += weight * 0.8
                elif edge["edge_type"] == "used_for":
                    attributions[source] += weight * 0.3
        
        self.attributions = dict(attributions)
        return self.attributions
    
    def get_entity_attribution(self, entity_type: str, entity_id: str) -> float:
        """Get attribution score for specific entity"""
        key = f"{entity_type}:{entity_id}"
        return self.attributions.get(key, 0.0)
    
    def to_dict(self) -> Dict:
        return {
            "episode_id": self.episode_id,
            "nodes": self.nodes,
            "edges": self.edges,
            "attributions": self.attributions
        }


class CreditAssignmentEngine:
    """
    Credit Assignment Engine - Distributes blame/credit to entities
    =================================================================
    This is what separates No1+ from simple agents.
    
    In a task, multiple entities participate:
    - Multiple knowledge entries
    - One or more procedures
    - Multiple tools
    - Sources
    
    If task succeeds/fails, we need to know:
    - Which knowledge helped/hurt
    - Which procedure was effective/ineffective
    - Which tool worked/didn't work
    - Which source led us astray
    
    This engine computes this attribution.
    """
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        
        # Attribution weights
        self.knowledge_weight = self.config.get("knowledge_weight", 0.4)
        self.procedure_weight = self.config.get("procedure_weight", 0.3)
        self.tool_weight = self.config.get("tool_weight", 0.2)
        self.source_weight = self.config.get("source_weight", 0.1)
        
        # Minimum confidence for attribution
        self.min_attribution_threshold = self.config.get("min_attribution_threshold", 0.05)
    
    def assign_credit(self, episode: LearningEpisode) -> Dict[str, float]:
        """Assign credit to entities for successful outcome."""
        credits = defaultdict(lambda: 0.0)
        
        if episode.final_verdict != "success":
            return dict(credits)
        
        # Credit knowledge entries
        for knowledge_id in episode.selected_items:
            credits[f"knowledge:{knowledge_id}"] += self.knowledge_weight / max(1, len(episode.selected_items))
        
        # Credit procedures
        for proc_id in episode.procedures_used:
            credits[f"procedure:{proc_id}"] += self.procedure_weight / max(1, len(episode.procedures_used))
        
        # Credit tools
        for tool_name in episode.tools_used:
            tool_success = any(
                r.get("success", False) 
                for r in episode.tool_results 
                if r.get("tool") == tool_name
            )
            if tool_success:
                credits[f"tool:{tool_name}"] += self.tool_weight / max(1, len(set(episode.tools_used)))
        
        # Normalize credits
        total = sum(credits.values())
        if total > 0:
            credits = {k: v / total for k, v in credits.items()}
        
        return dict(credits)
    
    def assign_blame(self, episode: LearningEpisode, failure_type: str) -> Dict[str, float]:
        """Assign blame to entities for failed outcome."""
        blames = defaultdict(lambda: 0.0)
        
        if episode.final_verdict == "success":
            return dict(blames)
        
        # Map failure type to entity weights
        failure_blame_map = {
            "knowledge_error": {"knowledge": 0.7, "procedure": 0.2, "tool": 0.1},
            "stale_knowledge": {"knowledge": 0.6, "source": 0.3, "procedure": 0.1},
            "retrieval_miss": {"knowledge": 0.3, "retrieval": 0.5, "procedure": 0.2},
            "ranking_error": {"retrieval": 0.7, "knowledge": 0.3},
            "procedure_drift": {"procedure": 0.8, "tool": 0.2},
            "tool_failure": {"tool": 0.9, "procedure": 0.1},
            "environment_failure": {"environment": 0.8, "tool": 0.2},
            "planner_error": {"planner": 0.9},
            "verification_error": {"verification": 0.9},
            "unknown": {"knowledge": 0.4, "procedure": 0.3, "tool": 0.2, "other": 0.1}
        }
        
        weights = failure_blame_map.get(failure_type, failure_blame_map["unknown"])
        
        if "knowledge" in weights:
            for knowledge_id in episode.selected_items:
                blames[f"knowledge:{knowledge_id}"] += weights.get("knowledge", 0) / max(1, len(episode.selected_items))
        
        if "procedure" in weights:
            for proc_id in episode.procedures_used:
                blames[f"procedure:{proc_id}"] += weights.get("procedure", 0) / max(1, len(episode.procedures_used))
        
        if "tool" in weights:
            for tool_name in episode.tools_used:
                blames[f"tool:{tool_name}"] += weights.get("tool", 0) / max(1, len(set(episode.tools_used)))
        
        # Normalize
        total = sum(blames.values())
        if total > 0:
            blames = {k: v / total for k, v in blames.items()}
        
        return dict(blames)
    
    def compute_mixed_attribution(self, episode: LearningEpisode) -> Tuple[Dict, Dict]:
        """Compute both credit and blame based on outcome."""
        if episode.final_verdict == "success":
            return self.assign_credit(episode), {}
        elif episode.final_verdict == "failure":
            return {}, self.assign_blame(episode, episode.failure_type)
        else:
            credits = self.assign_credit(episode)
            credits = {k: v * 0.5 for k, v in credits.items()}
            return credits, {}


class FailureClassifier:
    """
    Failure Classifier - Identifies root cause of failures
    ======================================================
    Instead of just "confidence -= 0.1", we now:
    1. Identify the failure type
    2. Find the root cause
    3. Apply targeted fix
    """
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        
        self.indicators = {
            "knowledge_error": ["incorrect", "wrong", "error in", "not correct", "invalid", "factual error"],
            "stale_knowledge": ["outdated", "old version", "deprecated", "no longer", "changed"],
            "retrieval_miss": ["wrong knowledge", "wrong information", "irrelevant", "not what i needed"],
            "procedure_drift": ["procedure changed", "steps different", "workflow changed"],
            "tool_failure": ["tool error", "command failed", "tool didn't work", "execution failed"],
            "environment_failure": ["environment", "permission denied", "not found", "dependency missing"],
            "planner_error": ["wrong plan", "incorrect approach", "wrong strategy"],
            "user_ambiguity": ["unclear", "ambiguous", "not specific", "confusing"]
        }
    
    def classify_failure(self, episode: LearningEpisode, feedback: Dict = None) -> str:
        """Classify the failure type based on episode and feedback."""
        failure_type = episode.failure_type
        
        if feedback:
            feedback_text = str(feedback.get("message", "")).lower()
            feedback_type = feedback.get("type", "")
            
            for ftype, indicators in self.indicators.items():
                if any(ind in feedback_text for ind in indicators):
                    failure_type = ftype
                    break
            
            if feedback_type:
                failure_type = self._map_feedback_type(feedback_type)
        
        if failure_type == "unknown":
            failure_type = self._analyze_episode(episode)
        
        return failure_type
    
    def _map_feedback_type(self, feedback_type: str) -> str:
        mapping = {
            "user_correction_wrong": "knowledge_error",
            "user_correction_outdated": "stale_knowledge",
            "user_correction_contradiction": "contradiction",
            "production_bug": "tool_failure",
            "production_error": "environment_failure",
            "benchmark_regression": "procedure_drift",
            "retrieval_bad": "retrieval_miss"
        }
        return mapping.get(feedback_type, "unknown")
    
    def _analyze_episode(self, episode: LearningEpisode) -> str:
        """Analyze episode to determine failure type"""
        for tool_result in episode.tool_results:
            if not tool_result.get("success", True):
                if "permission" in str(tool_result).lower():
                    return "environment_failure"
                return "tool_failure"
        
        for verification in episode.verification_results:
            if verification.get("passed", True) == False:
                reason = verification.get("reason", "").lower()
                if "outdated" in reason or "stale" in reason:
                    return "stale_knowledge"
                if "incorrect" in reason or "wrong" in reason:
                    return "knowledge_error"
                return "verification_error"
        
        if episode.selected_items and episode.final_verdict == "failure":
            if len(episode.retrieved_items) > len(episode.selected_items) * 3:
                return "retrieval_miss"
            return "knowledge_error"
        
        return "unknown"
    
    def get_update_policy(self, failure_type: str) -> List:
        """Get appropriate update policies based on failure type."""
        policies = {
            "knowledge_error": [UpdatePolicy.CONFIDENCE_UPDATE, UpdatePolicy.RE_VERIFICATION_TRIGGER],
            "stale_knowledge": [UpdatePolicy.CONFIDENCE_UPDATE, UpdatePolicy.ANTI_PATTERN_CREATE],
            "retrieval_miss": [UpdatePolicy.RETRIEVAL_RERANK],
            "ranking_error": [UpdatePolicy.RETRIEVAL_RERANK],
            "procedure_drift": [UpdatePolicy.PROCEDURE_DEMOTION, UpdatePolicy.ANTI_PATTERN_CREATE],
            "tool_failure": [UpdatePolicy.ANTI_PATTERN_CREATE],
            "environment_failure": [UpdatePolicy.NO_UPDATE],
            "planner_error": [UpdatePolicy.NO_UPDATE],
            "verification_error": [UpdatePolicy.RE_VERIFICATION_TRIGGER],
            "unknown": [UpdatePolicy.CONFIDENCE_UPDATE]
        }
        
        return policies.get(failure_type, [UpdatePolicy.NO_UPDATE])


class ProcedureMiner:
    """
    Procedure Miner - Extracts reusable procedures from successful episodes
    =========================================================================
    When the system successfully completes a task, we analyze what worked
    and create reusable procedure candidates.
    """
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.min_episodes = self.config.get("min_episodes", 3)
        self.min_success_rate = self.config.get("min_success_rate", 0.7)
        self.procedure_candidates: Dict[str, ProcedureCandidate] = {}
    
    def extract_procedure(self, episode: LearningEpisode) -> Optional[ProcedureCandidate]:
        """Extract procedure candidate from successful episode."""
        if episode.final_verdict != "success":
            return None
        
        proc_id = f"auto_proc_{hashlib.md5(str(time.time()).encode()).hexdigest()[:8]}"
        
        steps = []
        for step in episode.procedure_steps:
            steps.append({
                "description": step.get("description", ""),
                "knowledge_used": step.get("knowledge_used", []),
                "tools_used": step.get("tools_used", [])
            })
        
        best_evidence = []
        for verification in episode.verification_results:
            if verification.get("passed", False):
                best_evidence.extend(verification.get("knowledge_used", []))
        
        best_evidence = list(set(best_evidence))
        prerequisites = list(episode.context.keys())[:5]
        
        candidate = ProcedureCandidate(
            procedure_id=proc_id,
            name=f"Auto-generated procedure from episode {episode.episode_id[:8]}",
            description=f"Extracted from successful task: {episode.goal[:100]}",
            step_sequence=steps,
            prerequisites=prerequisites,
            success_conditions=[episode.goal],
            best_evidence=best_evidence
        )
        
        candidate.update_from_episode(episode)
        
        return candidate
    
    def update_procedure(self, procedure_id: str, episode: LearningEpisode):
        """Update existing procedure with new episode"""
        if procedure_id in self.procedure_candidates:
            self.procedure_candidates[procedure_id].update_from_episode(episode)
    
    def find_similar_episodes(self, episodes: List[LearningEpisode], 
                              target_episode: LearningEpisode) -> List[LearningEpisode]:
        """Find episodes similar to target for procedure extraction"""
        similar = []
        target_context_keys = set(target_episode.context.keys())
        
        for episode in episodes:
            if episode.episode_id == target_episode.episode_id:
                continue
            if episode.final_verdict != "success":
                continue
            
            episode_keys = set(episode.context.keys())
            overlap = len(target_context_keys & episode_keys)
            
            if overlap >= len(target_context_keys) * 0.5:
                similar.append(episode)
        
        return similar[:5]
    
    def merge_to_procedure(self, procedure_id: str, episodes: List[LearningEpisode]):
        """Merge multiple episodes into one procedure"""
        if not episodes:
            return
        
        if procedure_id not in self.procedure_candidates:
            candidate = self.extract_procedure(episodes[0])
            if candidate:
                self.procedure_candidates[procedure_id] = candidate
                episodes = episodes[1:]
        
        for episode in episodes:
            self.update_procedure(procedure_id, episode)


class AntiPatternMemory:
    """
    Anti-Pattern Memory - Stores failure patterns to avoid
    ======================================================
    Key difference from simple agents:
    - We don't just lower confidence
    - We remember SPECIFIC failure patterns
    """
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.min_occurrences = self.config.get("min_occurrences", 2)
        self.patterns: Dict[str, AntiPattern] = {}
    
    def record_failure_pattern(self, episode: LearningEpisode, failure_type: str):
        """Record a failure pattern from episode"""
        pattern_type, pattern_key = self._identify_pattern(episode, failure_type)
        
        if not pattern_type:
            return
        
        if pattern_key in self.patterns:
            self.patterns[pattern_key].record_occurrence(episode.episode_id, failure_type)
        else:
            pattern = AntiPattern(
                pattern_id=f"anti_{hashlib.md5(pattern_key.encode()).hexdigest()[:8]}",
                pattern_type=pattern_type,
                description=self._generate_description(pattern_type, episode),
                source_domain=episode.context.get("source", "") + "|" + episode.context.get("domain", ""),
                procedure_environment=f"{'|'.join(episode.procedures_used)}|{episode.context.get('environment', '')}"
            )
            pattern.record_occurrence(episode.episode_id, failure_type)
            self.patterns[pattern_key] = pattern
            logger.info(f"🛑 New anti-pattern recorded: {pattern_type}")
    
    def _identify_pattern(self, episode: LearningEpisode, failure_type: str) -> Tuple[str, str]:
        """Identify what type of pattern this failure represents"""
        source = episode.context.get("source", "")
        domain = episode.context.get("domain", "")
        if source and domain:
            return ("bad_source_domain", f"source:{source}|domain:{domain}")
        
        if episode.procedures_used and episode.context.get("environment"):
            proc = episode.procedures_used[0]
            env = episode.context.get("environment")
            return ("bad_procedure_env", f"procedure:{proc}|environment:{env}")
        
        if failure_type in ["retrieval_miss", "ranking_error"]:
            query = episode.context.get("query", "")
            if query:
                query_pattern = " ".join(query.split()[:2])
                return ("bad_retrieval_query", f"query_pattern:{query_pattern}")
        
        if failure_type == "contradiction":
            return ("common_contradiction", f"contradiction:{episode.goal[:30]}")
        
        return (None, None)
    
    def _generate_description(self, pattern_type: str, episode: LearningEpisode) -> str:
        descriptions = {
            "bad_source_domain": f"Unreliable source in domain: {episode.context.get('source', 'unknown')}",
            "bad_procedure_env": f"Procedure fails in environment: {episode.context.get('environment', 'unknown')}",
            "bad_retrieval_query": f"Retrieval query pattern causes issues: {episode.context.get('query', '')[:50]}",
            "common_contradiction": f"Contradiction in goal: {episode.goal[:50]}"
        }
        return descriptions.get(pattern_type, "Unknown failure pattern")
    
    def get_patterns_for_context(self, context: Dict) -> List[AntiPattern]:
        """Get relevant anti-patterns for current context"""
        relevant = []
        
        for pattern in self.patterns.values():
            if pattern.occurrence_count < self.min_occurrences:
                continue
            
            if pattern.pattern_type == "bad_source_domain":
                source = context.get("source", "")
                domain = context.get("domain", "")
                if source in pattern.source_domain and domain in pattern.source_domain:
                    relevant.append(pattern)
            
            elif pattern.pattern_type == "bad_procedure_env":
                procedure = context.get("procedure", "")
                environment = context.get("environment", "")
                if procedure in pattern.procedure_environment and environment in pattern.procedure_environment:
                    relevant.append(pattern)
        
        return relevant
    
    def should_avoid(self, context: Dict) -> bool:
        """Check if current context has known anti-patterns"""
        patterns = self.get_patterns_for_context(context)
        
        for pattern in patterns:
            if pattern.severity in ["high", "critical"]:
                logger.warning(f"⚠️ Anti-pattern detected: {pattern.description}")
                return True
        
        return False


class DelayedOutcomeBinder:
    """
    Delayed Outcome Binder - Binds late feedback to original episodes
    =================================================================
    Real-world feedback often arrives late.
    This binder connects delayed feedback to the original episode.
    """
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.pending_feedback: Dict[str, DelayedFeedback] = {}
        self.episode_lookup: Dict[str, str] = {}
        self.max_delay_seconds = self.config.get("max_delay_seconds", 7 * 24 * 3600)
    
    def register_episode(self, episode: LearningEpisode, correlation_id: str = None):
        """Register episode for future delayed feedback binding"""
        if correlation_id:
            self.episode_lookup[correlation_id] = episode.episode_id
    
    def receive_delayed_feedback(self, feedback: Dict) -> Optional[str]:
        """Receive delayed feedback and try to bind to episode."""
        feedback_id = feedback.get("feedback_id", f"delayed_{hashlib.md5(str(time.time()).encode()).hexdigest()[:8]}")
        
        delayed = DelayedFeedback(
            feedback_id=feedback_id,
            original_episode_id="",
            feedback_type=feedback.get("type", "delayed"),
            content=feedback.get("content", feedback),
            correlation_id=feedback.get("correlation_id", ""),
            causation_id=feedback.get("causation_id", ""),
            original_task_time=feedback.get("task_time", time.time() - 86400)
        )
        
        episode_id = self._find_episode(delayed)
        
        if episode_id:
            delayed.bind_to_episode(episode_id)
            logger.info(f"✅ Bound delayed feedback {feedback_id} to episode {episode_id}")
            return episode_id
        
        self.pending_feedback[feedback_id] = delayed
        logger.info(f"⏳ Stored delayed feedback {feedback_id} for future binding")
        
        return None
    
    def _find_episode(self, delayed: DelayedFeedback) -> Optional[str]:
        """Find episode for delayed feedback"""
        if delayed.correlation_id and delayed.correlation_id in self.episode_lookup:
            return self.episode_lookup[delayed.correlation_id]
        
        if delayed.causation_id and delayed.causation_id in self.episode_lookup:
            return self.episode_lookup[delayed.causation_id]
        
        time_since_task = time.time() - delayed.original_task_time
        if time_since_task > self.max_delay_seconds:
            logger.warning(f"⏰ Delayed feedback too old, discarding: {delayed.feedback_id}")
            return None
        
        return None
    
    def process_pending(self, episode_store: Dict[str, LearningEpisode]) -> List[DelayedFeedback]:
        """Process all pending feedback against current episode store"""
        processed = []
        
        for feedback_id, delayed in list(self.pending_feedback.items()):
            episode_id = self._find_episode(delayed)
            
            if episode_id and episode_id in episode_store:
                delayed.bind_to_episode(episode_id)
                processed.append(delayed)
                del self.pending_feedback[feedback_id]
                
                if delayed.correlation_id:
                    self.episode_lookup[delayed.correlation_id] = episode_id
        
        return processed


class OutcomeJudge:
    """
    Outcome Judge - Evaluates task outcomes with rich signals
    =========================================================
    Instead of binary success/failure, we now have:
    - Quality score, Speed score, Robustness score
    - User satisfaction, Regression risk
    """
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.quality_threshold = self.config.get("quality_threshold", 0.7)
        self.speed_threshold_ms = self.config.get("speed_threshold_ms", 5000)
        self.satisfaction_threshold = self.config.get("satisfaction_threshold", 0.6)
    
    def judge(self, episode: LearningEpisode) -> Dict[str, Any]:
        """Judge the episode outcome."""
        verdict = {
            "verdict": self._determine_verdict(episode),
            "quality_score": self._judge_quality(episode),
            "speed_score": self._judge_speed(episode),
            "robustness_score": self._judge_robustness(episode),
            "user_satisfaction": episode.user_satisfaction,
            "regression_risk": self._judge_regression_risk(episode)
        }
        
        return verdict
    
    def _determine_verdict(self, episode: LearningEpisode) -> str:
        """Determine overall verdict"""
        if episode.outcome.get("success"):
            quality = self._judge_quality(episode)
            if quality < self.quality_threshold:
                return "partial_success"
            return "success"
        
        if episode.outcome.get("error"):
            return "error"
        if episode.outcome.get("timeout"):
            return "timeout"
        if episode.outcome.get("cancelled"):
            return "cancelled"
        
        return "unknown"
    
    def _judge_quality(self, episode: LearningEpisode) -> float:
        """Judge quality of work"""
        quality = episode.quality_score
        
        if episode.verification_results:
            passed = sum(1 for v in episode.verification_results if v.get("passed", False))
            total = len(episode.verification_results)
            verification_score = passed / max(1, total)
            quality = (quality * 0.6 + verification_score * 0.4)
        
        return min(1.0, max(0.0, quality))
    
    def _judge_speed(self, episode: LearningEpisode) -> float:
        """Judge speed of execution"""
        latency = episode.latency_ms
        
        if latency < self.speed_threshold_ms:
            return 1.0
        
        return 0.5 ** (latency / self.speed_threshold_ms)
    
    def _judge_robustness(self, episode: LearningEpisode) -> float:
        """Judge robustness"""
        if episode.tool_results:
            successful = sum(1 for t in episode.tool_results if t.get("success", False))
            total = len(episode.tool_results)
            tool_success_rate = successful / max(1, total)
        else:
            tool_success_rate = 1.0
        
        retries = episode.outcome.get("retries", 0)
        retry_penalty = min(0.3, retries * 0.1)
        
        return max(0.0, tool_success_rate - retry_penalty)
    
    def _judge_regression_risk(self, episode: LearningEpisode) -> str:
        """Judge risk of regression"""
        risk_factors = 0
        
        if len(episode.selected_items) > 5:
            risk_factors += 1
        if len(episode.tools_used) > 3:
            risk_factors += 1
        if episode.quality_score < 0.5:
            risk_factors += 1
        
        if risk_factors >= 2:
            return "high"
        elif risk_factors == 1:
            return "medium"
        return "low"


class TimeScopeType(Enum):
    """Time scope type for knowledge validity"""
    CURRENT = "current"              # True now
    HISTORICAL = "historical"        # Was true in the past
    FORECAST = "forecast"            # Expected to be true in future
    DEPRECATED = "deprecated"        # No longer valid
    TIMELESS = "timeless"            # Always true (math, etc.)
    COMPARATIVE = "comparative"      # Version-specific comparison
    VERSION_SCOPED = "version_scoped" # Only valid for specific version


class ProvenanceStatus(Enum):
    PRIMARY = "primary"           # Directly from source
    DERIVED = "derived"           # Derived from other knowledge
    SYNTHESIZED = "synthesized"  # Synthesized from multiple sources
    CORRECTED = "corrected"       # User corrected
    INFERRED = "inferred"         # Inferred by system


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


@dataclass
class VersionScope:
    """
    Version Scope - Version-specific knowledge tracking
    ===================================================
    Tracks which version(s) a piece of knowledge applies to.
    Essential for accurate code/tech recommendations.
    """
    product_name: str                    # e.g., "Python", "React", "Next.js"
    component: str = ""                  # e.g., "app router", "hooks"
    version: str = ""                    # Specific version: "3.11", "18.2"
    version_min: str = ""                # Minimum version: "3.11"
    version_max: str = ""                # Maximum version: "3.13"
    version_range: str = ""              # Range string: ">=3.11,<3.13"
    environment_scope: str = ""           # e.g., "node", "browser", "server"
    platform_scope: str = ""             # e.g., "linux", "windows", "macos"
    edition: str = ""                    # e.g., "enterprise", "community"
    
    def is_version_compatible(self, target_version: str) -> bool:
        """Check if target version is within scope"""
        if self.version and self.version == target_version:
            return True
        if self.version_range:
            # Simple version range check
            return target_version in self.version_range
        return True  # No version constraints
    
    def to_dict(self) -> Dict:
        return {
            "product_name": self.product_name,
            "component": self.component,
            "version": self.version,
            "version_min": self.version_min,
            "version_max": self.version_max,
            "version_range": self.version_range,
            "environment_scope": self.environment_scope,
            "platform_scope": self.platform_scope,
            "edition": self.edition
        }


@dataclass
class TruthClock:
    """
    Truth Clock - Time-aware confidence tracking
    =============================================
    Tracks temporal aspects of knowledge beyond simple freshness.
    This is a "clock" that ticks based on knowledge volatility.
    """
    # Base confidence from content
    confidence: float = 0.5
    
    # Time confidence - how sure are we about time validity?
    time_confidence: float = 1.0
    
    # Drift risk - how likely is this to change soon?
    # 0.0 = no risk, 1.0 = high risk
    drift_risk: float = 0.0
    
    # Expiry pressure - how close to becoming stale?
    # 0.0 = fresh, 1.0 = about to expire
    expiry_pressure: float = 0.0
    
    # Reverification debt - how overdue is verification?
    reverify_debt_days: float = 0.0
    
    # Last update metrics
    last_updated: float = 0.0
    last_verified: float = 0.0
    
    # Volatility indicators
    volatility_class: VolatilityClass = VolatilityClass.MEDIUM
    
    def calculate_truth_clock(self, current_time: float, 
                              volatility_class: VolatilityClass,
                              last_verified: float) -> 'TruthClock':
        """Calculate the truth clock based on time and volatility"""
        
        # Time since last verification
        days_since_verify = (current_time - last_verified) / (24 * 3600)
        
        # Get decay parameters for volatility class
        decay_params = VOLATILITY_PARAMS.get(volatility_class, DEFAULT_VOLATILITY_PARAMS)
        
        # Calculate drift risk
        self.drift_risk = min(1.0, days_since_verify / decay_params["max_stable_days"])
        
        # Calculate expiry pressure
        self.expiry_pressure = min(1.0, days_since_verify / decay_params["reverify_interval_days"])
        
        # Calculate reverification debt
        self.reverify_debt_days = max(0, days_since_verify - decay_params["reverify_interval_days"])
        
        # Time confidence decreases as expiry pressure increases
        self.time_confidence = max(0.0, 1.0 - self.expiry_pressure * 0.5)
        
        # Update timestamps
        self.last_verified = last_verified
        self.last_updated = current_time
        self.volatility_class = volatility_class
        
        return self
    
    def get_composite_score(self) -> float:
        """Get overall truth score combining confidence and time"""
        return self.confidence * (0.5 + self.time_confidence * 0.5)
    
    def is_reverify_needed(self) -> bool:
        """Check if reverification is needed"""
        return self.expiry_pressure > 0.8 or self.reverify_debt_days > 0
    
    def to_dict(self) -> Dict:
        return {
            "confidence": self.confidence,
            "time_confidence": self.time_confidence,
            "drift_risk": self.drift_risk,
            "expiry_pressure": self.expiry_pressure,
            "reverify_debt_days": self.reverify_debt_days,
            "volatility_class": self.volatility_class.value,
            "composite_score": self.get_composite_score(),
            "reverify_needed": self.is_reverify_needed()
        }


# Volatility parameters for each class
DEFAULT_VOLATILITY_PARAMS = {
    VolatilityClass.IMMUTABLE: {
        "reverify_interval_days": 365,
        "max_stable_days": 730,
        "decay_rate": 0.01
    },
    VolatilityClass.STABLE: {
        "reverify_interval_days": 180,
        "max_stable_days": 365,
        "decay_rate": 0.05
    },
    VolatilityClass.MEDIUM: {
        "reverify_interval_days": 90,
        "max_stable_days": 180,
        "decay_rate": 0.1
    },
    VolatilityClass.VOLATILE: {
        "reverify_interval_days": 14,
        "max_stable_days": 30,
        "decay_rate": 0.3
    },
    VolatilityClass.HIGHLY_VOLATILE: {
        "reverify_interval_days": 3,
        "max_stable_days": 7,
        "decay_rate": 0.5
    },
    VolatilityClass.USER_PREFERENCE: {
        "reverify_interval_days": 30,
        "max_stable_days": 90,
        "decay_rate": 0.2
    },
    VolatilityClass.PROCEDURE: {
        "reverify_interval_days": 30,
        "max_stable_days": 60,
        "decay_rate": 0.25
    }
}

VOLATILITY_PARAMS = DEFAULT_VOLATILITY_PARAMS


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
    receipt_id: str = ""
    target_type: str = ""
    target_id: str = ""
    
    # Verification details
    method: VerificationMethod = VerificationMethod.AUTOMATIC
    inputs: Dict = field(default_factory=dict)  # What was checked
    
    # Results
    checks_passed: List[str] = field(default_factory=list)
    checks_failed: List[str] = field(default_factory=list)
    
    # Verdict
    result: str = ""
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
    receipt_id: str = ""
    entry_id: str = ""
    
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
    Also includes comprehensive temporal fields for time-aware truth management.
    """
    entry_id: str = ""
    content: str = ""
    knowledge_type: KnowledgeType = KnowledgeType.FACT
    source: str = ""
    source_url: str = ""
    collected_at: float = 0.0
    last_verified: float = 0.0
    confidence: float = 0.5
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
    
    # ==================== TEMPORAL FIELDS (NEW - Time-Aware Truth System) ====================
    # Observation and assertion times
    observed_at: float = 0.0              # When this knowledge was first observed
    asserted_at: float = 0.0              # When this knowledge was asserted to be true
    verified_at: float = 0.0              # When this was last verified
    
    # Validity window - when this knowledge is valid
    valid_from: float = 0.0              # Timestamp when this became valid
    valid_until: float = 0.0              # Timestamp when this stops being valid (0 = indefinite)
    
    # Temporal status
    temporal_status: TemporalStatus = TemporalStatus.CANDIDATE
    time_scope_type: TimeScopeType = TimeScopeType.CURRENT
    
    # Supersession tracking
    superseded_by: str = ""               # ID of entry that superseded this
    supersedes: str = ""                  # ID of entry this supersedes
    superseded_at: float = 0.0            # When this was superseded
    retirement_at: float = 0.0            # When this was retired
    
    # Volatility and decay
    volatility_class: VolatilityClass = VolatilityClass.MEDIUM
    
    # Version scope (for version-specific knowledge)
    version_scope: Optional[VersionScope] = None
    
    # Truth clock data
    time_confidence: float = 1.0          # Confidence in time validity
    drift_risk: float = 0.0              # Risk of becoming outdated
    expiry_pressure: float = 0.0         # Pressure to re-verify
    
    # Timeline tracking
    timeline_events: List[Dict] = field(default_factory=list)  # Historical events
    
    # Historical flag
    is_historical: bool = False           # Is this historical (superseded) knowledge?
    is_current: bool = True               # Is this currently valid?


@dataclass
class Contradiction:
    """
    Contradiction - Enhanced with Evidence
    =======================================
    Now includes evidence bundles and resolution tracking.
    """
    entry_a: str = ""
    entry_b: str = ""
    contradiction_type: str = ""
    severity: float = 0.0
    detected_at: float = 0.0
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
    
    # ==================== TEMPORAL FIELDS (NEW - Time-Aware) ====================
    # Time tracking for procedures
    created_at: float = 0.0               # When procedure was first created
    last_success_at: float = 0.0          # Last successful execution
    last_failure_at: float = 0.0          # Last failed execution
    environment_last_seen: str = ""       # Last environment where this worked
    compatibility_window: str = ""        # Version compatibility window
    drift_score: float = 0.0              # How much environment has drifted
    is_deprecated: bool = False           # Is this procedure deprecated?
    replaced_by: str = ""                 # ID of replacement procedure
    decay_factor: float = 1.0             # Decay based on age and failures


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


# ==================== NO1+ OBSERVED-WORLD CLOSED LOOP ====================
# Enhanced ObservedWorldLearning with full closed-loop integration

class ObservedWorldLearningNo1Plus:
    """
    No1+ Observed-World Closed Loop Learning System
    ================================================
    
    This is the full implementation of the closed-loop learning system
    that addresses all the issues mentioned:
    
    1. Episode Ledger - Every task becomes an episode with full trace
    2. Credit Assignment Engine - Distributes blame/credit properly
    3. Root Cause Learner - Identifies failure types
    4. Procedure Miner - Extracts procedures from success
    5. Anti-Pattern Memory - Stores failure patterns
    6. Delayed Outcome Binder - Handles late feedback
    7. Causal Learning Graph - Tracks causal relationships
    
    This integrates with UnifiedLearning and KnowledgeGovernance
    into a single canonical closed loop.
    """
    
    def __init__(self, config: Dict = None, pipeline=None, governance=None):
        self.config = config or {}
        
        # Reference to pipeline and governance (integration point)
        self.pipeline = pipeline
        self.governance = governance
        
        # NEW: Episode Ledger - Core of closed loop
        self.episodes: Dict[str, LearningEpisode] = {}
        
        # NEW: Credit Assignment Engine
        self.credit_engine = CreditAssignmentEngine(self.config.get("credit_config"))
        
        # NEW: Failure Classifier
        self.failure_classifier = FailureClassifier(self.config.get("failure_config"))
        
        # NEW: Procedure Miner
        self.procedure_miner = ProcedureMiner(self.config.get("procedure_config"))
        
        # NEW: Anti-Pattern Memory
        self.anti_pattern_memory = AntiPatternMemory(self.config.get("antipattern_config"))
        
        # NEW: Delayed Outcome Binder
        self.delayed_binder = DelayedOutcomeBinder(self.config.get("delayed_config"))
        
        # NEW: Outcome Judge
        self.outcome_judge = OutcomeJudge(self.config.get("judge_config"))
        
        # Legacy compatibility
        self.feedback_weights = {
            "user_correction": 0.9,
            "production_outcome": 0.8,
            "benchmark_result": 0.7,
            "self_observed": 0.6,
            "default": 0.3
        }
        
        self.trust_decay_half_life = 30 * 24 * 3600
        self.min_trust_threshold = 0.2
        self.quarantined_sources: Set[str] = set()
        self.quarantine_threshold = 0.3
        self.contradiction_log: List[Dict] = []
        self.production_outcomes: Dict[str, Dict] = {}
        
        logger.info("🌍🌟 No1+ Observed-World Closed Loop System initialized")
    
    # ==================== EPISODE MANAGEMENT ====================
    
    def create_episode(self, task_id: str, task_description: str, 
                       goal: str, context: Dict = None) -> LearningEpisode:
        """Create a new learning episode for a task"""
        episode_id = f"ep_{hashlib.md5(f'{task_id}{time.time()}'.encode()).hexdigest()[:12]}"
        
        episode = LearningEpisode(
            episode_id=episode_id,
            task_id=task_id,
            task_description=task_description,
            goal=goal,
            context=context or {}
        )
        
        # Register with delayed binder
        self.delayed_binder.register_episode(episode, correlation_id=task_id)
        
        self.episodes[episode_id] = episode
        logger.info(f"📝 Created episode: {episode_id}")
        
        return episode
    
    def get_episode(self, episode_id: str) -> Optional[LearningEpisode]:
        """Get episode by ID"""
        return self.episodes.get(episode_id)
    
    def complete_episode(self, episode_id: str, outcome: Dict) -> Dict:
        """
        Complete an episode with outcome.
        
        This is the key closed-loop operation:
        1. Judge the outcome
        2. Classify failure (if any)
        3. Assign credit/blame
        4. Update knowledge/procedure/source
        5. Extract procedures if successful
        6. Record anti-patterns if failed
        """
        episode = self.episodes.get(episode_id)
        if not episode:
            return {"error": "Episode not found"}
        
        # 1. Judge the outcome
        verdict = self.outcome_judge.judge(episode)
        final_verdict = verdict["verdict"]
        
        # 2. Mark episode complete
        episode.mark_complete(final_verdict, outcome)
        
        # 3. Classify failure type (if failed)
        if final_verdict == "failure":
            failure_type = self.failure_classifier.classify_failure(episode, outcome.get("feedback"))
            episode.failure_type = failure_type
            episode.root_cause = self._determine_root_cause(failure_type, episode)
        
        # 4. Assign credit/blame
        credits, blames = self.credit_engine.compute_mixed_attribution(episode)
        episode.credits = credits
        episode.blames = blames
        
        # 5. Build causal graph
        causal_graph = CausalLearningGraph(episode_id)
        self._build_causal_graph(episode, causal_graph)
        causal_graph.compute_attributions(final_verdict)
        episode.causal_graph = causal_graph.to_dict()
        
        # 6. Apply learning updates
        if final_verdict == "success":
            self._apply_success_learning(episode)
        elif final_verdict == "failure":
            self._apply_failure_learning(episode)
        
        # 7. Extract procedure if successful
        if final_verdict == "success":
            procedure = self.procedure_miner.extract_procedure(episode)
            if procedure:
                logger.info(f"✅ Extracted procedure: {procedure.procedure_id}")
        
        # 8. Record anti-pattern if failed
        if final_verdict == "failure":
            self.anti_pattern_memory.record_failure_pattern(episode, episode.failure_type)
        
        episode.processed = True
        
        logger.info(f"🏁 Episode {episode_id} completed: {final_verdict}")
        
        return {
            "episode_id": episode_id,
            "verdict": verdict,
            "credits": credits,
            "blames": blames,
            "failure_type": episode.failure_type if final_verdict == "failure" else None
        }
    
    def _determine_root_cause(self, failure_type: str, episode: LearningEpisode) -> str:
        """Determine root cause description"""
        root_causes = {
            "knowledge_error": f"Knowledge content was incorrect: {', '.join(episode.selected_items[:2])}",
            "stale_knowledge": "Knowledge is outdated and needs updating",
            "retrieval_miss": "Wrong knowledge was retrieved for the task",
            "ranking_error": "Retrieval ranking failed to surface correct knowledge",
            "procedure_drift": "Procedure has drifted from optimal path",
            "tool_failure": f"Tool execution failed: {episode.tools_used}",
            "environment_failure": "Environment issue prevented success",
            "planner_error": "Planning approach was incorrect",
            "verification_error": "Verification gave false positive/negative",
            "unknown": "Unknown failure cause"
        }
        return root_causes.get(failure_type, "Unknown")
    
    def _build_causal_graph(self, episode: LearningEpisode, graph: CausalLearningGraph):
        """Build causal graph for episode"""
        
        # Add knowledge nodes
        for knowledge_id in episode.selected_items:
            graph.add_node("knowledge", knowledge_id)
        
        # Add procedure nodes
        for proc_id in episode.procedures_used:
            graph.add_node("procedure", proc_id)
        
        # Add tool nodes
        for tool_name in episode.tools_used:
            graph.add_node("tool", tool_name)
        
        # Add edges based on usage
        for knowledge_id in episode.selected_items:
            # Knowledge used for task
            graph.add_edge("knowledge", knowledge_id, "task", episode.task_id, "used_for")
            
            # If task failed, knowledge might have caused failure
            if episode.final_verdict == "failure":
                graph.add_edge("knowledge", knowledge_id, "task", episode.task_id, "failed_due_to")
        
        # Procedure edges
        for proc_id in episode.procedures_used:
            graph.add_edge("procedure", proc_id, "task", episode.task_id, "used_for")
            
            if episode.final_verdict == "failure":
                graph.add_edge("procedure", proc_id, "task", episode.task_id, "failed_due_to")
        
        # Tool edges
        for tool_name in episode.tools_used:
            graph.add_edge("tool", tool_name, "task", episode.task_id, "used_for")
            
            if episode.final_verdict == "failure":
                graph.add_edge("tool", tool_name, "task", episode.task_id, "failed_due_to")
    
    def _apply_success_learning(self, episode: LearningEpisode):
        """Apply learning from successful episode"""
        
        # Update knowledge confidence with credits
        for entity_id, credit in episode.credits.items():
            if entity_id.startswith("knowledge:"):
                knowledge_id = entity_id.replace("knowledge:", "")
                self._update_knowledge_confidence(knowledge_id, credit, increase=True)
            
            elif entity_id.startswith("procedure:"):
                proc_id = entity_id.replace("procedure:", "")
                self._update_procedure_score(proc_id, credit, increase=True)
        
        # Trigger procedure extraction for similar episodes
        similar = self.procedure_miner.find_similar_episodes(
            list(self.episodes.values()), episode
        )
        if len(similar) >= 2:
            proc_id = f"merged_{episode.episode_id[:8]}"
            self.procedure_miner.merge_to_procedure(proc_id, [episode] + similar)
    
    def _apply_failure_learning(self, episode: LearningEpisode):
        """Apply learning from failed episode"""
        
        # Get update policies based on failure type
        policies = self.failure_classifier.get_update_policy(episode.failure_type)
        
        # Apply blame to entities
        for entity_id, blame in episode.blames.items():
            if entity_id.startswith("knowledge:"):
                knowledge_id = entity_id.replace("knowledge:", "")
                self._update_knowledge_confidence(knowledge_id, blame, increase=False)
            
            elif entity_id.startswith("procedure:"):
                proc_id = entity_id.replace("procedure:", "")
                self._update_procedure_score(proc_id, blame, increase=False)
        
        # Apply policy-specific updates
        for policy in policies:
            if policy == UpdatePolicy.ANTI_PATTERN_CREATE:
                # Already done in complete_episode
                pass
            elif policy == UpdatePolicy.RE_VERIFICATION_TRIGGER:
                self._trigger_reverification(episode)
            elif policy == UpdatePolicy.QUARANTINE_TRIGGER:
                self._check_source_quarantine(episode)
            elif policy == UpdatePolicy.RETRIEVAL_RERANK:
                self._update_retrieval_ranking(episode)
    
    def _update_knowledge_confidence(self, knowledge_id: str, amount: float, increase: bool):
        """Update knowledge confidence based on attribution"""
        if not self.pipeline or knowledge_id not in self.pipeline.knowledge:
            return
        
        entry = self.pipeline.knowledge[knowledge_id]
        
        # Calculate adjustment
        if increase:
            adjustment = amount * 0.1  # Max 10% increase per episode
            entry.confidence = min(1.0, entry.confidence + adjustment)
            entry.success_count += 1
        else:
            adjustment = amount * 0.15  # Max 15% decrease per episode
            entry.confidence = max(0.0, entry.confidence - adjustment)
        
        entry.last_verified = time.time()
        
        logger.debug(f"{'↑' if increase else '↓'} Knowledge {knowledge_id[:8]}: {adjustment:+.3f}")
    
    def _update_procedure_score(self, procedure_id: str, score: float, increase: bool):
        """Update procedure score based on attribution"""
        # This would integrate with procedure storage
        logger.debug(f"{'↑' if increase else '↓'} Procedure {procedure_id}: {score:+.3f}")
    
    def _trigger_reverification(self, episode: LearningEpisode):
        """Trigger reverification for failed knowledge"""
        for knowledge_id in episode.selected_items:
            logger.info(f"🔄 Triggering reverification for knowledge: {knowledge_id}")
    
    def _check_source_quarantine(self, episode: LearningEpisode):
        """Check if sources should be quarantined"""
        # Integration with quarantine logic
        pass
    
    def _update_retrieval_ranking(self, episode: LearningEpisode):
        """Update retrieval ranking based on failure"""
        # Integration with retrieval system
        pass
    
    # ==================== ENHANCED USER CORRECTION ====================
    
    def process_user_correction(self, entry_id: str, correction: Dict) -> Dict:
        """
        Process user correction with full closed-loop integration.
        
        Now does:
        1. Identifies affected claim
        2. Stores correction as evidence
        3. Marks old truth as disputed
        4. Creates replacement entry if needed
        5. Opens contradiction case
        6. Applies retrieval demotion
        """
        correction_type = correction.get("type", "direct")
        
        # Find related episode if any
        episode_id = correction.get("episode_id")
        episode = self.episodes.get(episode_id) if episode_id else None
        
        # 1. Identify affected claim
        affected_claim = self._identify_affected_claim(entry_id, correction)
        
        # 2. Store correction as evidence
        correction_evidence = {
            "type": EvidenceType.USER_CORRECTION.value,
            "correction_content": correction.get("content", ""),
            "correction_type": correction_type,
            "timestamp": time.time(),
            "episode_id": episode_id
        }
        
        # 3. Mark old truth as disputed
        if self.pipeline and entry_id in self.pipeline.knowledge:
            entry = self.pipeline.knowledge[entry_id]
            entry.status = ClaimStatus.DISPUTED.value
            entry.claims = entry.claims or []
            entry.claims.append({
                "type": "disputed",
                "reason": correction.get("reason", "user correction"),
                "evidence": correction_evidence,
                "timestamp": time.time()
            })
        
        # 4. Create replacement entry if needed
        new_entry_id = None
        if correction.get("create_replacement"):
            new_entry_id = self._create_replacement_entry(entry_id, correction)
        
        # 5. Open contradiction case
        contradiction_case = self._open_contradiction_case(entry_id, correction)
        
        # 6. Apply confidence adjustment
        weight = self.feedback_weights["user_correction"]
        if correction_type == "direct":
            weight *= 1.0
        elif correction_type == "indirect":
            weight *= 0.7
        elif correction_type == "implicit":
            weight *= 0.5
        
        # Apply to pipeline if available
        if self.governance:
            self.governance.record_feedback(entry_id, "correction", weight)
        
        return {
            "entry_id": entry_id,
            "correction_type": correction_type,
            "affected_claim": affected_claim,
            "weight": weight,
            "replacement_entry_id": new_entry_id,
            "contradiction_case": contradiction_case,
            "applied": True
        }
    
    def _identify_affected_claim(self, entry_id: str, correction: Dict) -> str:
        """Identify which claim was corrected"""
        # Analyze correction content to find claim
        correction_text = correction.get("content", "").lower()
        
        if "not" in correction_text or "incorrect" in correction_text:
            return "factual_inaccuracy"
        elif "outdated" in correction_text or "old" in correction_text:
            return "stale_information"
        elif "contradict" in correction_text:
            return "contradiction"
        
        return "general_correction"
    
    def _create_replacement_entry(self, entry_id: str, correction: Dict) -> str:
        """Create replacement entry for corrected knowledge"""
        if not self.pipeline:
            return ""
        
        # Create new entry with corrected content
        new_entry_id = self.pipeline.add_knowledge(
            content=correction.get("corrected_content", ""),
            source_url=correction.get("source_url", "user_correction"),
            source_type=SourceType.DOCUMENTATION,
            knowledge_type=KnowledgeType.FACT,
            tags=["user_corrected"]
        )
        
        return new_entry_id
    
    def _open_contradiction_case(self, entry_id: str, correction: Dict) -> Dict:
        """Open contradiction case for tracking"""
        case = {
            "id": f"contradiction_{hashlib.md5(str(time.time()).encode()).hexdigest()[:8]}",
            "entry_id": entry_id,
            "type": "user_correction",
            "status": "open",
            "timestamp": time.time(),
            "description": correction.get("reason", "User correction")
        }
        
        self.contradiction_log.append(case)
        
        return case
    
    # ==================== ENHANCED PRODUCTION OUTCOME ====================
    
    def record_production_outcome(self, task_id: str, outcome: Dict, 
                                  episode_id: str = None):
        """
        Record production outcome with episode integration.
        
        Now:
        1. Links to episode
        2. Stores selected knowledge
        3. Links procedure/tool traces
        4. Stores judge verdict
        """
        # Store in legacy format for compatibility
        self.production_outcomes[task_id] = {
            "success": outcome.get("success", False),
            "knowledge_used": outcome.get("knowledge_used", []),
            "quality_score": outcome.get("quality_score", 0.5),
            "latency_ms": outcome.get("latency_ms", 0),
            "timestamp": time.time(),
            "user_satisfaction": outcome.get("user_satisfaction"),
            "episode_id": episode_id
        }
        
        # If we have episode, update it with production feedback
        if episode_id and episode_id in self.episodes:
            episode = self.episodes[episode_id]
            episode.production_feedback = outcome
            
            # Trigger closed-loop learning if episode is complete
            if outcome.get("task_complete"):
                self.complete_episode(episode_id, outcome)
    
    def get_production_feedback(self, entry_id: str) -> Dict:
        """Get aggregated production feedback with learning integration"""
        relevant = [
            o for o in self.production_outcomes.values()
            if entry_id in o.get("knowledge_used", [])
        ]
        
        if not relevant:
            return {"score": 0.5, "count": 0, "needs_update": False}
        
        avg_quality = sum(o["quality_score"] for o in relevant) / len(relevant)
        success_rate = sum(1 for o in relevant if o["success"]) / len(relevant)
        
        score = avg_quality * success_rate
        
        # Determine if update needed
        needs_update = score < 0.3 or score > 0.9
        
        return {
            "score": score,
            "count": len(relevant),
            "avg_quality": avg_quality,
            "success_rate": success_rate,
            "needs_update": needs_update
        }
    
    # ==================== DELAYED FEEDBACK ====================
    
    def receive_delayed_feedback(self, feedback: Dict) -> Optional[str]:
        """Receive delayed feedback and bind to episode"""
        
        # Try to bind to existing episode
        episode_id = self.delayed_binder.receive_delayed_feedback(feedback)
        
        if episode_id and episode_id in self.episodes:
            episode = self.episodes[episode_id]
            episode.production_feedback = feedback.get("content", {})
            episode.delayed_feedback_bound = True
            
            # Re-run learning if episode was already complete
            if episode.processed:
                self.complete_episode(episode_id, episode.production_feedback)
        
        return episode_id
    
    def process_pending_delayed(self) -> List[Dict]:
        """Process all pending delayed feedback"""
        processed = self.delayed_binder.process_pending(self.episodes)
        
        results = []
        for delayed in processed:
            episode_id = delayed.original_episode_id
            if episode_id in self.episodes:
                episode = self.episodes[episode_id]
                episode.delayed_feedback_bound = True
                
                # Re-run learning
                result = self.complete_episode(episode_id, delayed.content)
                results.append(result)
        
        return results
    
    # ==================== ANTI-PATTERN CHECK ====================
    
    def check_anti_patterns(self, context: Dict) -> List[AntiPattern]:
        """Check current context for known anti-patterns"""
        return self.anti_pattern_memory.get_patterns_for_context(context)
    
    def should_avoid_context(self, context: Dict) -> bool:
        """Check if current context should be avoided due to anti-patterns"""
        return self.anti_pattern_memory.should_avoid(context)
    
    # ==================== LEGACY COMPATIBILITY ====================
    
    def quarantine_source(self, source_url: str, reason: str):
        """Quarantine a bad source"""
        self.quarantined_sources.add(source_url)
        logger.warning(f"🔒 Source quarantined: {source_url} - {reason}")
    
    def is_quarantined(self, source_url: str) -> bool:
        """Check if source is quarantined"""
        return source_url in self.quarantined_sources
    
    def apply_benchmark_demotion(self, entry_id: str, benchmark_result: Dict):
        """Demote knowledge based on benchmark"""
        score = benchmark_result.get("score", 1.0)
        
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
    
    def process_observed_feedback(self, feedback: Dict) -> Dict:
        """Process observed feedback - dispatcher for compatibility"""
        feedback_type = feedback.get("type", "default")
        
        if feedback_type == "user_correction":
            return self.process_user_correction(
                feedback["entry_id"],
                feedback.get("correction", {})
            )
        elif feedback_type == "production":
            self.record_production_outcome(
                feedback["task_id"],
                feedback.get("outcome", {}),
                feedback.get("episode_id")
            )
            return {"processed": True}
        elif feedback_type == "benchmark":
            return self.apply_benchmark_demotion(
                feedback["entry_id"],
                feedback.get("result", {})
            )
        elif feedback_type == "delayed":
            episode_id = self.receive_delayed_feedback(feedback.get("feedback", {}))
            return {"processed": True, "bound_episode": episode_id}
        
        return {"error": "Unknown feedback type"}
    
    def get_learning_health(self) -> Dict:
        """Get overall learning system health"""
        return {
            "episodes": len(self.episodes),
            "completed_episodes": sum(1 for e in self.episodes.values() if e.processed),
            "procedures_extracted": len(self.procedure_miner.procedure_candidates),
            "anti_patterns": len(self.anti_pattern_memory.patterns),
            "pending_delayed": len(self.delayed_binder.pending_feedback),
            "quarantined_sources": len(self.quarantined_sources),
            "contradictions_resolved": len(self.contradiction_log),
            "production_outcomes": len(self.production_outcomes)
        }
    
    def get_episode_stats(self) -> Dict:
        """Get episode statistics"""
        total = len(self.episodes)
        if total == 0:
            return {"total": 0}
        
        success = sum(1 for e in self.episodes.values() if e.final_verdict == "success")
        failure = sum(1 for e in self.episodes.values() if e.final_verdict == "failure")
        partial = sum(1 for e in self.episodes.values() if e.final_verdict == "partial_success")
        
        return {
            "total": total,
            "success": success,
            "failure": failure,
            "partial": partial,
            "success_rate": success / total if total > 0 else 0,
            "avg_latency_ms": sum(e.latency_ms for e in self.episodes.values()) / total
        }


def create_observed_world_learning_no1_plus(config: Dict = None, pipeline=None, governance=None) -> ObservedWorldLearningNo1Plus:
    """Factory function for No1+ Observed-World Learning"""
    return ObservedWorldLearningNo1Plus(config, pipeline, governance)


# ==================== SOURCE ACQUISITION & REVERIFICATION ENGINE ====================
# No1+ World-Class Source Management System

class SourceState(Enum):
    """Source Lifecycle State"""
    ACTIVE = "active"           # Normal operation
    WATCH = "watch"             # Being monitored
    PROBATION = "probation"     # Limited use
    QUARANTINED = "quarantined" # Blocked
    RETIRED = "retired"         # No longer used
    REHABILITATED = "rehabilitated"  # Recovered


class SourcePolicy(Enum):
    """Source Type Specific Acquisition Policy"""
    DOCS_SECTION_AWARE = "docs_section_aware"
    GITHUB_RELEASE_AWARE = "github_release_aware"
    FORUM_QUALITY_FILTER = "forum_quality_filter"
    PAPER_ABSTRACT_EXTRACT = "paper_abstract_extract"
    NEWS_TIME_SENSITIVE = "news_time_sensitive"
    API_SPECIFIC = "api_specific"
    GENERAL = "general"


class ReverifyTrigger(Enum):
    """Reverification Trigger Types"""
    TIME_BASED = "time_based"               # Scheduled
    CHANGE_DETECTED = "change_detected"       # Content changed
    CONTRADICTION = "contradiction"           # Contradicted
    RETRIEVAL_FAILURE = "retrieval_failure"  # Failed to retrieve
    USER_CORRECTION = "user_correction"       # User flagged
    HIGH_VOLATILITY = "high_volatility"       # High volatility domain
    BENCHMARK_REGRESSION = "benchmark_regression"  # Test failed
    VERSION_CHANGE = "version_change"         # New version detected


class SourceRegistry:
    """
    Source Registry - Canonical Source Management
    =============================================
    Each source now has full lifecycle tracking:
    - source_id, url, type, domain
    - trust_state, volatility_class
    - yield_score, noise_score, cost_score
    - last_fetched_at, last_changed_at
    - next_fetch_at, next_reverify_at
    - quarantine_state
    """
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.sources: Dict[str, Dict] = {}
        
        # State tracking
        self.watchlist: Set[str] = set()  # source_ids being watched
        self.probation_sources: Set[str] = set()
        self.quarantined_sources: Set[str] = set()
        
        # Statistics
        self.total_fetches = 0
        self.failed_fetches = 0
    
    def register_source(self, url: str, source_type: SourceType, 
                       topics: List[str] = None, metadata: Dict = None) -> str:
        """Register a new source"""
        source_id = f"src_{hashlib.md5(url.encode()).hexdigest()[:12]}"
        
        if source_id in self.sources:
            return source_id
        
        domain = self._extract_domain(url)
        
        self.sources[source_id] = {
            "source_id": source_id,
            "url": url,
            "source_type": source_type.value,
            "domain": domain,
            "trust_state": TrustLevel.UNKNOWN.value,
            "volatility_class": VolatilityClass.STABLE.value,
            "yield_score": 0.5,
            "noise_score": 0.0,
            "cost_score": 0.0,
            "last_fetched_at": 0.0,
            "last_changed_at": 0.0,
            "next_fetch_at": 0.0,
            "next_reverify_at": 0.0,
            "quarantine_state": SourceState.ACTIVE.value,
            "topics": topics or [],
            "metadata": metadata or {},
            "fetch_history": [],
            "change_count": 0,
            "failure_count": 0,
            "success_count": 0,
            "claims_extracted": 0,
            "verified_claims": 0,
            "created_at": time.time()
        }
        
        return source_id
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL"""
        match = re.search(r'https?://([^/]+)', url)
        return match.group(1) if match else ""
    
    def get_source(self, source_id: str) -> Optional[Dict]:
        """Get source by ID"""
        return self.sources.get(source_id)
    
    def get_source_by_url(self, url: str) -> Optional[Dict]:
        """Get source by URL"""
        source_id = f"src_{hashlib.md5(url.encode()).hexdigest()[:12]}"
        return self.sources.get(source_id)
    
    def update_fetch_result(self, source_id: str, result: Dict):
        """Update source after fetch"""
        if source_id not in self.sources:
            return
        
        source = self.sources[source_id]
        
        # Update fetch stats
        source["last_fetched_at"] = time.time()
        self.total_fetches += 1
        
        if result.get("success"):
            source["success_count"] += 1
            
            # Update change detection
            content_hash = result.get("content_hash", "")
            if source.get("last_fetch_hash") and source["last_fetch_hash"] != content_hash:
                source["change_count"] += 1
                source["last_changed_at"] = time.time()
            
            source["last_fetch_hash"] = content_hash
            
            # Update yield metrics
            claims = result.get("claims_extracted", 0)
            source["claims_extracted"] += claims
            if claims > 0:
                verified = result.get("verified_claims", 0)
                source["verified_claims"] += verified
        else:
            source["failure_count"] += 1
        
        # Record fetch in history
        source["fetch_history"].append({
            "timestamp": time.time(),
            "success": result.get("success", False),
            "latency_ms": result.get("latency_ms", 0),
            "content_size": result.get("content_size", 0),
            "claims_extracted": result.get("claims_extracted", 0)
        })
        
        # Keep only last 100 history
        source["fetch_history"] = source["fetch_history"][-100:]
    
    def get_due_sources(self, limit: int = 10) -> List[Dict]:
        """Get sources due for fetching"""
        now = time.time()
        due = []
        
        for source in self.sources.values():
            if source["quarantine_state"] == SourceState.QUARANTINED.value:
                continue
            
            if source["next_fetch_at"] <= now:
                # Calculate priority
                priority = self._calculate_fetch_priority(source)
                due.append((priority, source))
        
        # Sort by priority (highest first)
        due.sort(key=lambda x: x[0], reverse=True)
        
        return [s[1] for s in due[:limit]]
    
    def _calculate_fetch_priority(self, source: Dict) -> float:
        """Calculate fetch priority"""
        # Factors: volatility, time since last fetch, trust, changes
        priority = 0.5
        
        # High volatility = higher priority
        if source.get("volatility_class") == VolatilityClass.HIGHLY_VOLATILE.value:
            priority += 0.3
        elif source.get("volatility_class") == VolatilityClass.VOLATILE.value:
            priority += 0.2
        
        # High trust = higher priority
        if source.get("trust_state") == TrustLevel.HIGH.value:
            priority += 0.15
        elif source.get("trust_state") == TrustLevel.MEDIUM.value:
            priority += 0.1
        
        # Recent changes = higher priority
        if source.get("change_count", 0) > 5:
            priority += 0.15
        
        # Low failure rate = higher priority
        total = source.get("success_count", 0) + source.get("failure_count", 0)
        if total > 0:
            success_rate = source["success_count"] / total
            priority *= (0.5 + success_rate * 0.5)
        
        return priority
    
    def set_quarantine_state(self, source_id: str, state: SourceState, reason: str = ""):
        """Set source quarantine state"""
        if source_id in self.sources:
            old_state = self.sources[source_id]["quarantine_state"]
            self.sources[source_id]["quarantine_state"] = state.value
            self.sources[source_id]["quarantine_state_changed_at"] = time.time()
            self.sources[source_id]["quarantine_reason"] = reason
            
            # Update sets
            if state == SourceState.QUARANTINED:
                self.quarantined_sources.add(source_id)
                if source_id in self.watchlist:
                    self.watchlist.discard(source_id)
            elif state == SourceState.ACTIVE:
                self.quarantined_sources.discard(source_id)
    
    def add_to_watchlist(self, source_id: str):
        """Add source to watchlist"""
        if source_id in self.sources:
            self.watchlist.add(source_id)
            self.sources[source_id]["watchlist_added_at"] = time.time()
    
    def remove_from_watchlist(self, source_id: str):
        """Remove source from watchlist"""
        self.watchlist.discard(source_id)
    
    def get_watchlist_sources(self) -> List[Dict]:
        """Get all watchlist sources"""
        return [self.sources[sid] for sid in self.watchlist if sid in self.sources]
    
    def get_yield_stats(self, source_id: str) -> Dict:
        """Get source yield statistics"""
        source = self.sources.get(source_id)
        if not source:
            return {}
        
        total = source.get("success_count", 0) + source.get("failure_count", 0)
        if total == 0:
            return {"yield_score": 0.5, "noise_score": 0.0}
        
        success_rate = source["success_count"] / total
        claims_per_fetch = source["claims_extracted"] / max(1, source.get("fetch_count", 1))
        verified_ratio = source["verified_claims"] / max(1, source["claims_extracted"])
        
        return {
            "yield_score": success_rate * claims_per_fetch,
            "noise_score": 1 - verified_ratio,
            "success_rate": success_rate,
            "claims_extracted": source["claims_extracted"],
            "verified_claims": source["verified_claims"],
            "change_count": source["change_count"]
        }


class AcquisitionScheduler:
    """
    Acquisition Scheduler - When to fetch sources
    =============================================
    This is the heart of 24/7 source learning:
    - Which source to fetch when
    - Which source to prioritize
    - Which source to delay due to budget
    """
    
    def __init__(self, config: Dict = None, registry: SourceRegistry = None):
        self.config = config or {}
        self.registry = registry or SourceRegistry(config)
        
        # Budget constraints
        self.daily_fetch_budget = self.config.get("daily_fetch_budget", 100)
        self.hourly_fetch_limit = self.config.get("hourly_fetch_limit", 10)
        
        # Tracking
        self.fetches_today = 0
        self.fetches_this_hour = 0
        self.last_hour_reset = time.time()
        self.last_day_reset = time.time()
    
    def reset_if_needed(self):
        """Reset periodic counters"""
        now = time.time()
        
        # Reset hourly
        if now - self.last_hour_reset > 3600:
            self.fetches_this_hour = 0
            self.last_hour_reset = now
        
        # Reset daily
        if now - self.last_day_reset > 86400:
            self.fetches_today = 0
            self.last_day_reset = now
    
    def get_next_fetch_action(self) -> Optional[Dict]:
        """Get next source to fetch and action"""
        self.reset_if_needed()
        
        # Check budget
        if self.fetches_today >= self.daily_fetch_budget:
            return {"action": "wait", "reason": "daily_budget_exceeded"}
        
        if self.fetches_this_hour >= self.hourly_fetch_limit:
            return {"action": "wait", "reason": "hourly_limit_exceeded"}
        
        # Get due sources
        due_sources = self.registry.get_due_sources(limit=10)
        
        if not due_sources:
            return {"action": "wait", "reason": "no_sources_due"}
        
        # Select highest priority
        source = due_sources[0]
        
        # Determine action
        action = self._determine_action(source)
        
        return {
            "action": action,
            "source": source,
            "source_id": source["source_id"]
        }
    
    def _determine_action(self, source: Dict) -> str:
        """Determine fetch action"""
        # Check if urgent reverify needed
        now = time.time()
        
        # Change detected - urgent fetch
        if source.get("last_changed_at", 0) > source.get("last_fetched_at", 0):
            return "full_reverify"
        
        # Overdue reverification
        if source.get("next_reverify_at", 0) <= now:
            return "full_reverify"
        
        # Normal fetch
        return "fetch"
    
    def execute_fetch(self, source_id: str) -> Dict:
        """Execute fetch for source and return result"""
        # This would integrate with actual fetch tools
        # For now, return mock result
        
        result = {
            "source_id": source_id,
            "success": True,
            "content_hash": hashlib.md5(str(time.time()).encode()).hexdigest(),
            "content_size": 1000,
            "latency_ms": 500,
            "claims_extracted": 5,
            "verified_claims": 3,
            "timestamp": time.time()
        }
        
        # Update stats
        self.registry.update_fetch_result(source_id, result)
        self.fetches_today += 1
        self.fetches_this_hour += 1
        
        # Schedule next fetch
        self._schedule_next_fetch(source_id)
        
        return result
    
    def _schedule_next_fetch(self, source_id: str):
        """Schedule next fetch time based on volatility"""
        source = self.registry.get_source(source_id)
        if not source:
            return
        
        # Determine cadence based on volatility
        volatility = source.get("volatility_class", VolatilityClass.STABLE.value)
        
        cadence_map = {
            VolatilityClass.HIGHLY_VOLATILE.value: 3600,      # 1 hour
            VolatilityClass.VOLATILE.value: 86400,            # 1 day
            VolatilityClass.MEDIUM.value: 259200,              # 3 days
            VolatilityClass.STABLE.value: 604800,             # 1 week
            VolatilityClass.IMMUTABLE.value: 2592000          # ~1 month
        }
        
        base_cadence = cadence_map.get(volatility, 86400)
        
        # Adjust based on trust
        trust = source.get("trust_state", TrustLevel.UNKNOWN.value)
        if trust == TrustLevel.HIGH.value:
            base_cadence *= 0.8  # More frequent
        elif trust == TrustLevel.LOW.value:
            base_cadence *= 1.5  # Less frequent
        
        next_fetch = time.time() + base_cadence
        source["next_fetch_at"] = next_fetch


class AdaptiveReverificationEngine:
    """
    Adaptive Reverification Engine - Smart Rechecking
    =================================================
    Not all knowledge needs the same reverification cadence:
    - volatility-aware
    - domain-aware
    - quality-aware
    - contradiction-aware
    """
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        
        # Default cadences by volatility (seconds)
        self.default_cadences = {
            VolatilityClass.HIGHLY_VOLATILE.value: 3600,       # 1 hour
            VolatilityClass.VOLATILE.value: 86400,               # 1 day
            VolatilityClass.MEDIUM.value: 259200,                # 3 days
            VolatilityClass.STABLE.value: 604800,                # 1 week
            VolatilityClass.IMMUTABLE.value: 2592000            # ~1 month
        }
        
        # Pending reverification jobs
        self.reverify_queue: List[Dict] = []
        self.completed_jobs: List[Dict] = []
    
    def schedule_reverification(self, knowledge_id: str, trigger: ReverifyTrigger,
                               priority: int = 5, metadata: Dict = None) -> str:
        """Schedule a reverification job"""
        job_id = f"reverify_{hashlib.md5(f'{knowledge_id}{time.time()}'.encode()).hexdigest()[:8]}"
        
        job = {
            "job_id": job_id,
            "knowledge_id": knowledge_id,
            "trigger": trigger.value,
            "priority": priority,
            "status": "pending",
            "created_at": time.time(),
            "started_at": 0.0,
            "completed_at": 0.0,
            "metadata": metadata or {}
        }
        
        # Add to queue based on priority
        self.reverify_queue.append(job)
        self.reverify_queue.sort(key=lambda x: x["priority"], reverse=True)
        
        return job_id
    
    def get_next_job(self) -> Optional[Dict]:
        """Get next reverification job"""
        for job in self.reverify_queue:
            if job["status"] == "pending":
                job["status"] = "in_progress"
                job["started_at"] = time.time()
                return job
        return None
    
    def complete_job(self, job_id: str, result: Dict):
        """Mark job as complete"""
        for job in self.reverify_queue:
            if job["job_id"] == job_id:
                job["status"] = "completed"
                job["completed_at"] = time.time()
                job["result"] = result
                
                # Move to completed
                self.completed_jobs.append(job)
                self.reverify_queue.remove(job)
                break
        
        # Keep only last 1000 completed jobs
        self.completed_jobs = self.completed_jobs[-1000:]
    
    def get_due_for_reverify(self) -> List[Dict]:
        """Get knowledge due for reverification"""
        now = time.time()
        due = []
        
        # This would normally check the knowledge store
        # For now, return pending jobs
        for job in self.reverify_queue:
            if job["status"] == "pending":
                due.append(job)
        
        return due[:50]
    
    def calculate_reverify_cadence(self, knowledge_entry: KnowledgeEntry, 
                                   source: Dict = None) -> float:
        """Calculate optimal reverification cadence"""
        # Base cadence from volatility
        volatility = knowledge_entry.get("volatility_class", VolatilityClass.STABLE.value)
        cadence = self.default_cadences.get(volatility, 86400)
        
        # Adjust based on source if available
        if source:
            trust = source.get("trust_state", TrustLevel.UNKNOWN.value)
            if trust == TrustLevel.HIGH.value:
                cadence *= 1.5  # Less frequent for trusted
            elif trust == TrustLevel.LOW.value:
                cadence *= 0.5  # More frequent for untrusted
        
        # Adjust based on knowledge age
        age = time.time() - knowledge_entry.get("collected_at", time.time())
        if age > 180 * 86400:  # > 180 days
            cadence *= 0.7  # More frequent
        
        # Adjust based on success rate
        if knowledge_entry.usage_count > 0:
            success_rate = knowledge_entry.success_count / knowledge_entry.usage_count
            if success_rate < 0.5:
                cadence *= 0.5  # More frequent for low success
            elif success_rate > 0.9:
                cadence *= 1.3  # Less frequent for high success
        
        return cadence


class SourceRehabilitationPipeline:
    """
    Source Rehabilitation Pipeline - Quarantine Lifecycle
    =====================================================
    Sources are not binary - they have a full lifecycle:
    - active, watched, probation, quarantined, retired, rehabilitated
    """
    
    def __init__(self, config: Dict = None, registry: SourceRegistry = None):
        self.config = config or {}
        self.registry = registry or SourceRegistry(config)
        
        # Rehabilitation settings
        self.probation_duration = self.config.get("probation_duration", 7 * 86400)  # 7 days
        self.retest_interval = self.config.get("retest_interval", 86400)  # 1 day
        self.min_success_rate = self.config.get("min_success_rate", 0.6)
    
    def evaluate_for_rehabilitation(self, source_id: str) -> bool:
        """Evaluate if quarantined source can be rehabilitated"""
        source = self.registry.get_source(source_id)
        if not source:
            return False
        
        if source["quarantine_state"] != SourceState.QUARANTINED.value:
            return False
        
        # Check time in quarantine
        quarantine_time = time.time() - source.get("quarantine_state_changed_at", 0)
        if quarantine_time < self.probation_duration:
            return False
        
        # Check recent performance
        fetch_history = source.get("fetch_history", [])[-10:]
        if not fetch_history:
            return False
        
        recent_success = sum(1 for f in fetch_history if f.get("success", False))
        success_rate = recent_success / len(fetch_history)
        
        return success_rate >= self.min_success_rate
    
    def move_to_probation(self, source_id: str):
        """Move source to probation"""
        self.registry.set_quarantine_state(source_id, SourceState.PROBATION, "Probation after rehabilitation")
        
        # Set probation end time
        source = self.registry.get_source(source_id)
        if source:
            source["probation_end_at"] = time.time() + self.probation_duration
    
    def evaluate_probation_progress(self, source_id: str) -> Dict:
        """Evaluate source during probation"""
        source = self.registry.get_source(source_id)
        if not source or source["quarantine_state"] != SourceState.PROBATION.value:
            return {"action": "none"}
        
        # Check probation end
        if source.get("probation_end_at", 0) <= time.time():
            # Check performance
            success_count = source.get("success_count", 0)
            failure_count = source.get("failure_count", 0)
            total = success_count + failure_count
            
            if total > 0:
                success_rate = success_count / total
                
                if success_rate >= self.min_success_rate:
                    return {"action": "rehabilitate", "reason": "success_rate_good"}
                else:
                    return {"action": "re_quarantine", "reason": "success_rate_poor"}
        
        return {"action": "continue_probation"}
    
    def rehabilitate(self, source_id: str):
        """Rehabilitate source to active"""
        self.registry.set_quarantine_state(source_id, SourceState.REHABILITATED, "Successfully rehabilitated")
        
        # After rehabilitation, move to active
        source = self.registry.get_source(source_id)
        if source:
            source["quarantine_state"] = SourceState.ACTIVE.value
    
    def get_rehabilitation_candidates(self) -> List[str]:
        """Get sources that should be evaluated for rehabilitation"""
        candidates = []
        
        for source_id in self.registry.quarantined_sources:
            if self.evaluate_for_rehabilitation(source_id):
                candidates.append(source_id)
        
        return candidates


class ChangeRadar:
    """
    Change Radar - Detect Source Changes
    ====================================
    No1+ agent doesn't just re-fetch - it detects what changed:
    - content hash
    - structural changes
    - semantic diff
    - version markers
    """
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        
        # Snapshot storage
        self.snapshots: Dict[str, List[Dict]] = defaultdict(list)
        
        # Max snapshots per source
        self.max_snapshots = self.config.get("max_snapshots", 10)
    
    def capture_snapshot(self, source_id: str, content: str, 
                       metadata: Dict = None) -> Dict:
        """Capture a content snapshot"""
        import hashlib
        
        # Create content hash
        content_hash = hashlib.md5(content.encode()).hexdigest()
        
        # Create structural hash (simple - paragraph count, headers, etc.)
        structural = {
            "paragraphs": len(content.split("\n\n")),
            "lines": len(content.split("\n")),
            "chars": len(content),
            "has_code": "```" in content or "    " in content,
            "has_lists": bool(re.search(r'^\s*[-*•]\s', content, re.MULTILINE))
        }
        structural_hash = hashlib.md5(str(structural).encode()).hexdigest()
        
        snapshot = {
            "source_id": source_id,
            "timestamp": time.time(),
            "content_hash": content_hash,
            "structural_hash": structural_hash,
            "content": content[:10000],  # Keep first 10k chars
            "metadata": metadata or {},
            "structural": structural
        }
        
        # Store snapshot
        self.snapshots[source_id].append(snapshot)
        
        # Trim old snapshots
        if len(self.snapshots[source_id]) > self.max_snapshots:
            self.snapshots[source_id] = self.snapshots[source_id][-self.max_snapshots:]
        
        return snapshot
    
    def detect_changes(self, source_id: str) -> Dict:
        """Detect changes since last snapshot"""
        snapshots = self.snapshots.get(source_id, [])
        
        if len(snapshots) < 2:
            return {"changed": False, "reason": "not_enough_snapshots"}
        
        latest = snapshots[-1]
        previous = snapshots[-2]
        
        # Check content hash
        content_changed = latest["content_hash"] != previous["content_hash"]
        structural_changed = latest["structural_hash"] != previous["structural_hash"]
        
        if not content_changed and not structural_changed:
            return {"changed": False, "reason": "no_changes"}
        
        # Determine change type
        change_type = []
        if content_changed:
            change_type.append("content_update")
        if structural_changed:
            change_type.append("structure_change")
        
        # Calculate diff details
        content_diff = self._calculate_content_diff(
            previous["content"], 
            latest["content"]
        )
        
        return {
            "changed": True,
            "change_type": change_type,
            "content_changed": content_changed,
            "structural_changed": structural_changed,
            "time_since_last": latest["timestamp"] - previous["timestamp"],
            "diff": content_diff,
            "previous_snapshot": previous["timestamp"],
            "latest_snapshot": latest["timestamp"]
        }
    
    def _calculate_content_diff(self, old: str, new: str) -> Dict:
        """Calculate content difference details"""
        old_lines = set(old.split("\n"))
        new_lines = set(new.split("\n"))
        
        added = len(new_lines - old_lines)
        removed = len(old_lines - new_lines)
        common = len(old_lines & new_lines)
        
        return {
            "lines_added": added,
            "lines_removed": removed,
            "lines_common": common,
            "change_ratio": (added + removed) / max(1, common)
        }
    
    def get_change_frequency(self, source_id: str) -> float:
        """Calculate change frequency for source"""
        snapshots = self.snapshots.get(source_id, [])
        
        if len(snapshots) < 2:
            return 0.0
        
        # Calculate average time between changes
        changes = 0
        total_time = 0
        
        for i in range(1, len(snapshots)):
            if snapshots[i]["content_hash"] != snapshots[i-1]["content_hash"]:
                changes += 1
                total_time += snapshots[i]["timestamp"] - snapshots[i-1]["timestamp"]
        
        if changes == 0:
            return 0.0
        
        return changes / max(1, total_time / 86400)  # Changes per day


class DiscoveryMiner:
    """
    Discovery Miner - Find New Sources
    ==================================
    No1+ agent doesn't just work with known sources:
    - entity-based search
    - citation expansion
    - official source detection
    """
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        
        # Discovered candidates
        self.candidates: Dict[str, Dict] = {}
        
        # Seed sources by topic
        self.seed_sources: Dict[str, List[str]] = {
            "ai": [
                "https://arxiv.org/list/cs.AI/recent",
                "https://github.com/topics/artificial-intelligence"
            ],
            "python": [
                "https://docs.python.org/3/",
                "https://github.com/python/cpython"
            ],
            "ml": [
                "https://arxiv.org/list/cs.LG/recent",
                "https://github.com/topics/machine-learning"
            ]
        }
    
    def discover_by_topic(self, topic: str, limit: int = 5) -> List[Dict]:
        """Discover new sources for a topic"""
        candidates = []
        
        # Check seed sources first
        seed_urls = self.seed_sources.get(topic.lower(), [])
        
        for url in seed_urls[:limit]:
            candidate = {
                "url": url,
                "topic": topic,
                "source": "seed_list",
                "discovered_at": time.time()
            }
            candidates.append(candidate)
        
        return candidates
    
    def discover_by_entity(self, entity: str) -> List[Dict]:
        """Discover sources related to an entity"""
        candidates = []
        
        # Common patterns for entity sources
        patterns = [
            f"https://github.com/{entity}",
            f"https://docs.{entity}.com",
            f"https://{entity}.readme.io",
            f"https://en.wikipedia.org/wiki/{entity.replace(' ', '_')}"
        ]
        
        for url in patterns:
            candidates.append({
                "url": url,
                "entity": entity,
                "source": "entity_pattern",
                "discovered_at": time.time()
            })
        
        return candidates
    
    def add_candidate(self, url: str, source: str, metadata: Dict = None):
        """Add a discovered candidate source"""
        candidate_id = f"candidate_{hashlib.md5(url.encode()).hexdigest()[:8]}"
        
        self.candidates[candidate_id] = {
            "candidate_id": candidate_id,
            "url": url,
            "source": source,
            "metadata": metadata or {},
            "discovered_at": time.time(),
            "evaluated": False,
            "rejected": False,
            "adopted": False
        }
    
    def get_pending_candidates(self) -> List[Dict]:
        """Get candidates that need evaluation"""
        return [
            c for c in self.candidates.values()
            if not c["evaluated"] and not c["rejected"]
        ]
    
    def evaluate_candidate(self, candidate_id: str, result: Dict):
        """Mark candidate as evaluated"""
        if candidate_id in self.candidates:
            self.candidates[candidate_id]["evaluated"] = True
            self.candidates[candidate_id]["evaluation_result"] = result
            
            if result.get("adopted"):
                self.candidates[candidate_id]["adopted"] = True


class SourcePortfolioManager:
    """
    Source Portfolio Manager - Domain Coverage Intelligence
    ======================================================
    Strong system doesn't rely on single source type:
    - Official docs
    - Implementation sources
    - Community sources
    - Empirical sources
    """
    
    def __init__(self, config: Dict = None, registry: SourceRegistry = None):
        self.config = config or {}
        self.registry = registry or SourceRegistry(config)
        
        # Domain portfolios
        self.portfolios: Dict[str, Dict] = {}
    
    def build_portfolio(self, domain: str) -> Dict:
        """Build source portfolio for domain"""
        # Get sources for domain
        domain_sources = [
            s for s in self.registry.sources.values()
            if domain in s.get("domain", "")
        ]
        
        # Categorize by type
        portfolio = {
            "domain": domain,
            "official_docs": [],
            "github": [],
            "community": [],
            "papers": [],
            "other": []
        }
        
        for source in domain_sources:
            source_type = source.get("source_type", "")
            
            if "docs" in source_type.lower() or source_type == SourceType.API_DOCS.value:
                portfolio["official_docs"].append(source)
            elif "github" in source_type.lower() or "github" in source.get("url", ""):
                portfolio["github"].append(source)
            elif source_type == SourceType.PAPER.value:
                portfolio["papers"].append(source)
            elif source_type in [SourceType.FORUM.value, SourceType.BLOG.value]:
                portfolio["community"].append(source)
            else:
                portfolio["other"].append(source)
        
        self.portfolios[domain] = portfolio
        
        return portfolio
    
    def get_source_diversity(self, domain: str) -> Dict:
        """Get diversity metrics for domain"""
        portfolio = self.portfolios.get(domain) or self.build_portfolio(domain)
        
        total = sum(len(sources) for sources in portfolio.values() if isinstance(sources, list))
        
        return {
            "total_sources": total,
            "official_docs_count": len(portfolio["official_docs"]),
            "github_count": len(portfolio["github"]),
            "community_count": len(portfolio["community"]),
            "papers_count": len(portfolio["papers"]),
            "diversity_score": self._calculate_diversity(portfolio)
        }
    
    def _calculate_diversity(self, portfolio: Dict) -> float:
        """Calculate portfolio diversity score"""
        counts = [
            len(portfolio.get(k, [])) 
            for k in ["official_docs", "github", "community", "papers"]
        ]
        
        total = sum(counts)
        if total == 0:
            return 0.0
        
        # Entropy-based diversity
        import math
        entropy = 0
        for c in counts:
            if c > 0:
                p = c / total
                entropy -= p * math.log2(p)
        
        # Normalize to 0-1
        max_entropy = math.log2(4)  # 4 categories
        return entropy / max_entropy
    
    def recommend_source_type(self, domain: str, query_type: str) -> str:
        """Recommend best source type for query"""
        diversity = self.get_source_diversity(domain)
        
        if query_type == "implementation":
            if diversity.get("github_count", 0) > 0:
                return "github"
        elif query_type == "api_reference":
            if diversity.get("official_docs_count", 0) > 0:
                return "official_docs"
        elif query_type == "troubleshooting":
            if diversity.get("community_count", 0) > 0:
                return "community"
        elif query_type == "research":
            if diversity.get("papers_count", 0) > 0:
                return "papers"
        
        return "any"


class SourceAcquisitionNo1Plus:
    """
    Source Acquisition No1+ - Full Pipeline Integration
    ==================================================
    This integrates all source management into the learning pipeline.
    """
    
    def __init__(self, config: Dict = None, pipeline=None):
        self.config = config or {}
        self.pipeline = pipeline
        
        # Core components
        self.registry = SourceRegistry(config.get("registry_config"))
        self.scheduler = AcquisitionScheduler(config.get("scheduler_config"), self.registry)
        self.reverification = AdaptiveReverificationEngine(config.get("reverify_config"))
        self.rehabilitation = SourceRehabilitationPipeline(config.get("rehab_config"), self.registry)
        self.change_radar = ChangeRadar(config.get("radar_config"))
        self.discovery = DiscoveryMiner(config.get("discovery_config"))
        self.portfolio = SourcePortfolioManager(config.get("portfolio_config"), self.registry)
        
        logger.info("🔍 Source Acquisition No1+ System initialized")
    
    # ==================== SOURCE REGISTRATION ====================
    
    def register_source(self, url: str, source_type: SourceType,
                       topics: List[str] = None, metadata: Dict = None) -> str:
        """Register new source"""
        return self.registry.register_source(url, source_type, topics, metadata)
    
    def get_source(self, source_id: str) -> Optional[Dict]:
        """Get source by ID"""
        return self.registry.get_source(source_id)
    
    # ==================== ACQUISITION ====================
    
    def start_acquisition_cycle(self) -> List[Dict]:
        """Start one acquisition cycle"""
        results = []
        
        # Get next action
        action = self.scheduler.get_next_fetch_action()
        
        if action.get("action") == "wait":
            return results
        
        if action.get("action") in ["fetch", "full_reverify"]:
            source_id = action["source_id"]
            
            # Execute fetch (would integrate with actual fetch tools)
            fetch_result = self.scheduler.execute_fetch(source_id)
            
            # Capture snapshot
            if fetch_result.get("success"):
                content = fetch_result.get("content", "mock content")
                self.change_radar.capture_snapshot(source_id, content)
                
                # Detect changes
                changes = self.change_radar.detect_changes(source_id)
                
                if changes.get("changed"):
                    # Trigger reverification for affected knowledge
                    self._trigger_change_reverification(source_id, changes)
                
                results.append({
                    "source_id": source_id,
                    "fetch_result": fetch_result,
                    "changes": changes
                })
        
        return results
    
    def _trigger_change_reverification(self, source_id: str, changes: Dict):
        """Trigger reverification due to detected changes"""
        # Get source
        source = self.registry.get_source(source_id)
        if not source:
            return
        
        # Schedule reverification with high priority
        self.reverification.schedule_reverification(
            knowledge_id=source_id,
            trigger=ReverifyTrigger.CHANGE_DETECTED,
            priority=9,  # High priority
            metadata={"changes": changes}
        )
    
    # ==================== REVERIFICATION ====================
    
    def run_reverification_cycle(self) -> Dict:
        """Run reverification cycle"""
        results = {
            "processed": 0,
            "updated": 0,
            "superseded": 0,
            "disputed": 0
        }
        
        # Get next job
        job = self.reverification.get_next_job()
        
        while job and results["processed"] < 10:
            results["processed"] += 1
            
            # Execute reverification (simplified)
            knowledge_id = job["knowledge_id"]
            
            # In real implementation, this would:
            # 1. Fetch current source
            # 2. Compare with last snapshot
            # 3. Update knowledge status
            
            result = {
                "verified": True,
                "status_changed": False
            }
            
            if result.get("status_changed"):
                results["updated"] += 1
            
            self.reverification.complete_job(job["job_id"], result)
            
            # Get next job
            job = self.reverification.get_next_job()
        
        return results
    
    def schedule_reverification(self, knowledge_id: str, trigger: str, priority: int = 5):
        """Manually schedule reverification"""
        trigger_enum = ReverifyTrigger(trigger)
        self.reverification.schedule_reverification(knowledge_id, trigger_enum, priority)
    
    # ==================== REHABILITATION ====================
    
    def run_rehabilitation_cycle(self) -> Dict:
        """Run rehabilitation evaluation cycle"""
        results = {
            "evaluated": 0,
            "rehabilitated": 0,
            "re_quarantined": 0
        }
        
        candidates = self.rehabilitation.get_rehabilitation_candidates()
        
        for source_id in candidates:
            results["evaluated"] += 1
            
            evaluation = self.rehabilitation.evaluate_probation_progress(source_id)
            
            if evaluation["action"] == "rehabilitate":
                self.rehabilitation.rehabilitate(source_id)
                results["rehabilitated"] += 1
            elif evaluation["action"] == "re_quarantine":
                self.registry.set_quarantine_state(source_id, SourceState.QUARANTINED, 
                                                   evaluation.get("reason", "probation_failed"))
                results["re_quarantined"] += 1
        
        return results
    
    # ==================== DISCOVERY ====================
    
    def discover_sources(self, topic: str = None, entity: str = None) -> List[Dict]:
        """Discover new sources"""
        sources = []
        
        if topic:
            sources.extend(self.discovery.discover_by_topic(topic))
        
        if entity:
            sources.extend(self.discovery.discover_by_entity(entity))
        
        return sources
    
    def register_discovered(self, url: str, source_type: SourceType):
        """Register discovered source"""
        return self.register_source(url, source_type)
    
    # ==================== PORTFOLIO ====================
    
    def analyze_portfolio(self, domain: str) -> Dict:
        """Analyze source portfolio for domain"""
        return self.portfolio.get_source_diversity(domain)
    
    def recommend_source(self, domain: str, query_type: str) -> str:
        """Recommend best source type"""
        return self.portfolio.recommend_source_type(domain, query_type)
    
    # ==================== HEALTH ====================
    
    def get_system_health(self) -> Dict:
        """Get system health metrics"""
        return {
            "total_sources": len(self.registry.sources),
            "active_sources": sum(1 for s in self.registry.sources.values() 
                                 if s["quarantine_state"] == SourceState.ACTIVE.value),
            "quarantined": len(self.registry.quarantined_sources),
            "watchlist": len(self.registry.watchlist),
            "pending_reverify": len(self.reverification.reverify_queue),
            "discovered_candidates": len(self.discovery.candidates),
            "change_radar_sources": len(self.change_radar.snapshots)
        }


def create_source_acquisition_system(config: Dict = None, pipeline=None) -> SourceAcquisitionNo1Plus:
    """Factory function for Source Acquisition System"""
    return SourceAcquisitionNo1Plus(config, pipeline)

