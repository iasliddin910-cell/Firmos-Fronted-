"""
OmniAgent X - Real Retrieval Engine (World No1+)
================================================
Comprehensive retrieval system with:
- Query Understanding Layer
- Multi-channel Candidate Generation
- Intelligent Reranking
- Context Packing
- Retrieval Flight Recorder
- Type-specific Retrieval Heads

Author: OmniAgent X Team
Version: 1.0.0 (No1+ Level)
"""

import os
import json
import logging
import time
import hashlib
import re
from typing import Dict, List, Optional, Any, Set, Tuple, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from collections import defaultdict
from pathlib import Path
import threading

logger = logging.getLogger(__name__)

# Import from learning_pipeline
try:
    from agent.learning_pipeline import (
        KnowledgeEntry,
        KnowledgeType,
        TemporalStatus,
        VolatilityClass,
        ConfidenceLevel,
        SourceType
    )
    from agent.time_aware_truth import (
        TemporalReasoner,
        TimeAwareRetrieval,
        VersionScope
    )
except ImportError:
    KnowledgeEntry = None
    KnowledgeType = None
    TemporalStatus = None
    VolatilityClass = None
    ConfidenceLevel = None
    SourceType = None
    TemporalReasoner = None
    TimeAwareRetrieval = None
    VersionScope = None


# ==================== RETRIEVAL TYPES ====================

class RetrievalIntent(Enum):
    """Query intent types"""
    FACTUAL = "factual"           # Seeking facts/truth
    PROCEDURAL = "procedural"     # Seeking how-to/procedures
    PREFERENCE = "preference"      # Seeking user preferences
    CODE = "code"                 # Seeking code/examples
    COMPARATIVE = "comparative"   # Seeking comparisons
    EXPLANATORY = "explanatory"    # Seeking explanations
    DEBUGGING = "debugging"        # Seeking debug help
    TROUBLESHOOTING = "troubleshooting"  # Seeking troubleshooting
    GENERAL = "general"           # General search


class TaskType(Enum):
    """Current task types for context-aware retrieval"""
    CODING = "coding"
    DEBUGGING = "debugging"
    RESEARCH = "research"
    DOCUMENTATION = "documentation"
    DEPLOYMENT = "deployment"
    DATA_ANALYSIS = "data_analysis"
    SECURITY = "security"
    GENERAL = "general"


@dataclass
class QueryContext:
    """
    Query Context - Additional information for context-aware retrieval
    """
    # Task information
    task_type: TaskType = TaskType.GENERAL
    current_file: str = ""
    current_project: str = ""
    active_language: str = ""
    
    # Environment
    environment: str = ""
    platform: str = ""
    
    # User info
    user_id: str = ""
    user_expertise: str = "intermediate"  # beginner, intermediate, expert
    
    # Request info
    desired_answer_type: str = "text"  # text, code, step-by-step, summary
    urgency: str = "normal"  # low, normal, high, critical
    failure_context: str = ""
    
    # Constraints
    version_constraint: str = ""
    scope_constraint: str = ""


@dataclass
class ParsedQuery:
    """
    Parsed Query - Structured query representation
    """
    original_query: str = ""
    normalized_query: str = ""
    
    # Intent classification
    intent: RetrievalIntent = RetrievalIntent.GENERAL
    task_type: TaskType = TaskType.GENERAL
    
    # Extracted components
    entities: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    synonyms: List[str] = field(default_factory=list)
    
    # Temporal scope
    temporal_scope: str = "current"  # current, historical, any
    temporal_reference: str = ""
    
    # Version scope
    version_constraint: str = ""
    product_name: str = ""
    
    # Constraints
    source_types: List[SourceType] = field(default_factory=list)
    knowledge_types: List[KnowledgeType] = field(default_factory=list)
    required_tags: List[str] = field(default_factory=list)
    
    # Search parameters
    max_results: int = 10
    min_confidence: float = 0.0


@dataclass
class RetrievalSignal:
    """
    Individual retrieval signal score
    """
    signal_name: str
    score: float
    weight: float = 1.0
    details: str = ""
    
    def weighted_score(self) -> float:
        return self.score * self.weight


@dataclass
class ScoredCandidate:
    """
    A candidate knowledge entry with scoring breakdown
    """
    entry: KnowledgeEntry
    final_score: float = 0.0
    
    # Individual signals
    lexical_score: float = 0.0
    semantic_score: float = 0.0
    entity_match_score: float = 0.0
    task_fit_score: float = 0.0
    evidence_strength_score: float = 0.0
    source_authority_score: float = 0.0
    temporal_fit_score: float = 0.0
    success_backing_score: float = 0.0
    
    # Penalties
    contradiction_penalty: float = 0.0
    stale_penalty: float = 0.0
    scope_mismatch_penalty: float = 0.0
    
    # Reason
    selected_reason: str = ""
    matched_terms: List[str] = field(default_factory=list)
    
    def total_signal_score(self) -> float:
        return (
            self.lexical_score +
            self.semantic_score +
            self.entity_match_score +
            self.task_fit_score +
            self.evidence_strength_score +
            self.source_authority_score +
            self.temporal_fit_score +
            self.success_backing_score -
            self.contradiction_penalty -
            self.stale_penalty -
            self.scope_mismatch_penalty
        )


@dataclass
class RetrievalResult:
    """
    Retrieval Result - Final packed answer
    """
    # Core results
    entries: List[ScoredCandidate] = field(default_factory=list)
    
    # Query understanding
    parsed_query: ParsedQuery = None
    
    # Metadata
    total_candidates_considered: int = 0
    retrieval_time_ms: float = 0.0
    
    # Warnings
    warnings: List[str] = field(default_factory=list)
    low_confidence_entries: List[str] = field(default_factory=list)
    disputed_entries: List[str] = field(default_factory=list)
    stale_entries: List[str] = field(default_factory=list)
    
    # Explanation
    selected_count: int = 0
    why_selected: str = ""
    
    # Context pack
    context_pack: Dict = field(default_factory=dict)


# ==================== QUERY UNDERSTANDING LAYER ====================

class QueryUnderstandingLayer:
    """
    Query Understanding Layer - Parse and analyze user queries
    ==========================================================
    Extracts:
    - Intent (factual, procedural, preference, code, etc.)
    - Entities
    - Temporal scope
    - Version constraints
    - Keywords and synonyms
    """
    
    # Synonym mappings
    SYNONYMS = {
        # Setup/Install synonyms
        "install": ["setup", "configure", "setup", "init", "initialize", "deployment"],
        "setup": ["install", "configure", "init", "initialize"],
        "configure": ["setup", "config", "settings"],
        
        # Error synonyms  
        "error": ["bug", "issue", "problem", "fail", "failure", "exception"],
        "bug": ["error", "issue", "problem", "defect"],
        "issue": ["problem", "bug", "error"],
        
        # Latest synonyms
        "latest": ["newest", "current", "recent", "yangi", "eng yangi"],
        "current": ["latest", "present", "hozirgi"],
        
        # Documentation synonyms
        "doc": ["documentation", "docs", "manual", "guide"],
        "documentation": ["doc", "docs", "manual"],
        
        # API synonyms
        "api": ["interface", "endpoint", "service"],
        "function": ["method", "api", "call"],
        
        # Version synonyms
        "version": ["v", "release"],
        "release": ["version", "v"],
    }
    
    # Intent patterns
    INTENT_PATTERNS = {
        RetrievalIntent.PROCEDURAL: [
            "how to", "qanday", " как", "how do i", "how can i",
            "steps to", "procedure", "process", "workflow",
            "install", "setup", "configure", "deploy", "build",
            "execute", "run", "create", "make"
        ],
        RetrievalIntent.FACTUAL: [
            "what is", "nima", "что", "what are", "define",
            "fact", "information", "details", "about",
            "explain", "describe", "tell me about"
        ],
        RetrievalIntent.CODE: [
            "code", "example", "snippet", "implementation",
            "syntax", "function", "class", "method",
            "write code", "create code", "generate code"
        ],
        RetrievalIntent.DEBUGGING: [
            "debug", "error", "bug", "fix", "troubleshoot",
            "not working", "doesn't work", "failed", "crash",
            "exception", "traceback", "stack"
        ],
        RetrievalIntent.COMPARATIVE: [
            "compare", "farq", "difference", "vs", "versus",
            "vs", "or", "yaxshiroq", "better", "worse"
        ],
        RetrievalIntent.PREFERENCE: [
            "prefer", "like", "want", "xo", "my preference",
            "settings", "config", "configuration"
        ]
    }
    
    # Version patterns
    VERSION_PATTERNS = [
        r'python\s*(\d+\.\d+)',
        r'node(?:js)?\s*(\d+\.\d+)',
        r'react\s*(\d+)',
        r'next\.?js\s*(\d+)',
        r'vue\s*(\d+)',
        r'typescript\s*(\d+\.\d+)',
        r'v(\d+\.\d+)',
        r'version\s*(\d+\.\d+)',
    ]
    
    # Temporal patterns
    TEMPORAL_PATTERNS = {
        "current": ["hozir", "current", "now", "latest", "eng yangi", "present", "endigi"],
        "historical": ["avval", "oldin", "previous", "past", "2000", "2020", "2021", "2022", "2023", "2024"],
        "any": ["har qanday", "any", "hammasi", "all"]
    }
    
    def __init__(self):
        logger.info("🔍 Query Understanding Layer initialized")
    
    def parse_query(self, query: str, context: QueryContext = None) -> ParsedQuery:
        """
        Parse query into structured representation
        """
        parsed = ParsedQuery()
        parsed.original_query = query
        parsed.normalized_query = self._normalize(query)
        
        # Extract intent
        parsed.intent = self._classify_intent(query)
        
        # Extract entities
        parsed.entities = self._extract_entities(query)
        
        # Extract keywords
        parsed.keywords = self._extract_keywords(query)
        
        # Add synonyms
        parsed.synonyms = self._expand_with_synonyms(parsed.keywords)
        
        # Extract temporal scope
        parsed.temporal_scope, parsed.temporal_reference = self._extract_temporal_scope(query)
        
        # Extract version constraint
        parsed.version_constraint, parsed.product_name = self._extract_version(query)
        
        # Extract from context if provided
        if context:
            if context.version_constraint:
                parsed.version_constraint = context.version_constraint
            if context.task_type:
                parsed.task_type = context.task_type
        
        return parsed
    
    def _normalize(self, query: str) -> str:
        """Normalize query text"""
        # Convert to lowercase
        normalized = query.lower()
        # Remove extra whitespace
        normalized = " ".join(normalized.split())
        # Remove punctuation (keep alphanumeric and spaces)
        normalized = re.sub(r'[^\w\s]', ' ', normalized)
        return normalized
    
    def _classify_intent(self, query: str) -> RetrievalIntent:
        """Classify query intent"""
        query_lower = query.lower()
        
        # Score each intent
        intent_scores = {}
        for intent, patterns in self.INTENT_PATTERNS.items():
            score = sum(1 for p in patterns if p in query_lower)
            intent_scores[intent] = score
        
        # Return highest scoring intent
        if intent_scores:
            best_intent = max(intent_scores, key=intent_scores.get)
            if intent_scores[best_intent] > 0:
                return best_intent
        
        return RetrievalIntent.GENERAL
    
    def _extract_entities(self, query: str) -> List[str]:
        """Extract named entities from query"""
        entities = []
        
        # Extract product/version combinations
        for pattern in self.VERSION_PATTERNS:
            matches = re.findall(pattern, query, re.IGNORECASE)
            entities.extend(matches)
        
        # Extract quoted terms
        quoted = re.findall(r'"([^"]+)"', query)
        entities.extend(quoted)
        
        # Extract capitalized terms (potential proper nouns)
        capitalized = re.findall(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b', query)
        entities.extend(capitalized)
        
        return list(set(entities))
    
    def _extract_keywords(self, query: str) -> List[str]:
        """Extract keywords from query"""
        normalized = self._normalize(query)
        
        # Split into words
        words = normalized.split()
        
        # Filter out stopwords
        stopwords = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been",
            "being", "have", "has", "had", "do", "does", "did", "will",
            "would", "could", "should", "may", "might", "must", "shall",
            "can", "need", "dare", "ought", "used", "to", "of", "in",
            "for", "on", "with", "at", "by", "from", "as", "into",
            "through", "during", "before", "after", "above", "below",
            "between", "under", "again", "further", "then", "once",
            "here", "there", "when", "where", "why", "how", "all",
            "each", "few", "more", "most", "other", "some", "such",
            "no", "nor", "not", "only", "own", "same", "so", "than",
            "too", "very", "just", "and", "but", "if", "or", "because",
            "until", "while", "what", "which", "who", "whom", "this",
            "that", "these", "those", "am", "va", "yoki", "lekin"
        }
        
        keywords = [w for w in words if w not in stopwords and len(w) > 2]
        
        return keywords
    
    def _expand_with_synonyms(self, keywords: List[str]) -> List[str]:
        """Expand keywords with synonyms"""
        synonyms = set()
        
        for keyword in keywords:
            synonyms.add(keyword)
            # Add direct synonyms
            if keyword in self.SYNONYMS:
                synonyms.update(self.SYNONYMS[keyword])
            
            # Add reverse synonyms
            for key, vals in self.SYNONYMS.items():
                if keyword in vals:
                    synonyms.add(key)
        
        return list(synonyms)
    
    def _extract_temporal_scope(self, query: str) -> Tuple[str, str]:
        """Extract temporal scope from query"""
        query_lower = query.lower()
        
        for scope, patterns in self.TEMPORAL_PATTERNS.items():
            for pattern in patterns:
                if pattern in query_lower:
                    return scope, pattern
        
        return "current", ""
    
    def _extract_version(self, query: str) -> Tuple[str, str]:
        """Extract version constraint from query"""
        for pattern in self.VERSION_PATTERNS:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                version = match.group(1) if match.lastindex else match.group(0)
                # Extract product name
                product = pattern.split()[0].replace("\\s*", "").replace("?", "")
                return version, product
        
        return "", ""


# ==================== CANDIDATE GENERATION LAYER ====================

class CandidateGenerationLayer:
    """
    Candidate Generation Layer - Multi-channel recall
    ================================================
    Generates candidates from multiple channels:
    - Lexical recall (BM25-like)
    - Semantic recall (embedding)
    - Structured recall (tags, entities)
    - Behavioral recall (past successful patterns)
    """
    
    def __init__(self, knowledge_store: Dict[str, KnowledgeEntry] = None):
        self.knowledge_store = knowledge_store or {}
        
        # Add all entries to indexes if store is provided
        
        # Indexes
        self._build_indexes()
        
        logger.info("📦 Candidate Generation Layer initialized")
    
    def _build_indexes(self):
        """Build inverted indexes for fast lookup"""
        # Keyword -> entry IDs
        self.keyword_index: Dict[str, Set[str]] = defaultdict(set)
        
        # Tag -> entry IDs
        self.tag_index: Dict[str, Set[str]] = defaultdict(set)
        
        # Entity -> entry IDs
        self.entity_index: Dict[str, Set[str]] = defaultdict(set)
        
        # Source type -> entry IDs
        self.source_index: Dict[str, Set[str]] = defaultdict(set)
        
        # Knowledge type -> entry IDs
        self.type_index: Dict[str, Set[str]] = defaultdict(set)
        
        # Build indexes from knowledge store
        for entry_id, entry in self.knowledge_store.items():
            # Index keywords from content
            if entry.content:
                words = entry.content.lower().split()
                for word in words:
                    if len(word) > 2:
                        self.keyword_index[word].add(entry_id)
            
            # Index tags
            if entry.tags:
                for tag in entry.tags:
                    self.tag_index[tag.lower()].add(entry_id)
            
            # Index entities
            if entry.entities:
                for entity in entry.entities:
                    self.entity_index[entity.lower()].add(entry_id)
            
            # Index source
            if entry.source:
                self.source_index[entry.source.lower()].add(entry_id)
            
            # Index knowledge type
            if entry.knowledge_type:
                self.type_index[entry.knowledge_type.value].add(entry_id)
    
    def generate_candidates(self, parsed_query: ParsedQuery,
                           max_candidates: int = 100) -> List[str]:
        """
        Generate candidate entry IDs from multiple channels
        """
        candidate_ids: Set[str] = set()
        
        # Channel 1: Lexical recall
        lexical_candidates = self._lexical_recall(parsed_query)
        candidate_ids.update(lexical_candidates)
        
        # Channel 2: Synonym recall
        synonym_candidates = self._synonym_recall(parsed_query)
        candidate_ids.update(synonym_candidates)
        
        # Channel 3: Entity recall
        entity_candidates = self._entity_recall(parsed_query)
        candidate_ids.update(entity_candidates)
        
        # Channel 4: Tag recall
        tag_candidates = self._tag_recall(parsed_query)
        candidate_ids.update(tag_candidates)
        
        # Channel 5: Type recall (for procedural/code queries)
        type_candidates = self._type_recall(parsed_query)
        candidate_ids.update(type_candidates)
        
        # Limit candidates
        return list(candidate_ids)[:max_candidates]
    
    def _lexical_recall(self, parsed_query: ParsedQuery) -> Set[str]:
        """Lexical keyword matching"""
        candidates = set()
        
        for keyword in parsed_query.keywords:
            if keyword in self.keyword_index:
                candidates.update(self.keyword_index[keyword])
        
        return candidates
    
    def _synonym_recall(self, parsed_query: ParsedQuery) -> Set[str]:
        """Recall using synonyms"""
        candidates = set()
        
        for synonym in parsed_query.synonyms:
            if synonym in self.keyword_index:
                candidates.update(self.keyword_index[synonym])
        
        return candidates
    
    def _entity_recall(self, parsed_query: ParsedQuery) -> Set[str]:
        """Recall using entities"""
        candidates = set()
        
        for entity in parsed_query.entities:
            entity_lower = entity.lower()
            if entity_lower in self.entity_index:
                candidates.update(self.entity_index[entity_lower])
            # Also check partial matches
            for idx_entity, ids in self.entity_index.items():
                if entity_lower in idx_entity or idx_entity in entity_lower:
                    candidates.update(ids)
        
        return candidates
    
    def _tag_recall(self, parsed_query: ParsedQuery) -> Set[str]:
        """Recall using tags"""
        candidates = set()
        
        for keyword in parsed_query.keywords:
            if keyword in self.tag_index:
                candidates.update(self.tag_index[keyword])
        
        return candidates
    
    def _type_recall(self, parsed_query: ParsedQuery) -> Set[str]:
        """Recall using knowledge type"""
        candidates = set()
        
        # Map intent to knowledge types
        type_mapping = {
            RetrievalIntent.PROCEDURAL: ["procedure"],
            RetrievalIntent.FACTUAL: ["fact", "concept"],
            RetrievalIntent.CODE: ["code"],
            RetrievalIntent.PREFERENCE: ["fact"],
        }
        
        if parsed_query.intent in type_mapping:
            for kt in type_mapping[parsed_query.intent]:
                if kt in self.type_index:
                    candidates.update(self.type_index[kt])
        
        return candidates
    
    def add_entry(self, entry: KnowledgeEntry):
        """Add entry to indexes"""
        entry_id = entry.entry_id
        
        # Add to knowledge store
        self.knowledge_store[entry_id] = entry
        
        # Index content keywords
        if entry.content:
            words = entry.content.lower().split()
            for word in words:
                if len(word) > 2:
                    self.keyword_index[word].add(entry_id)
        
        # Index tags
        if entry.tags:
            for tag in entry.tags:
                self.tag_index[tag.lower()].add(entry_id)
        
        # Index entities
        if entry.entities:
            for entity in entry.entities:
                self.entity_index[entity.lower()].add(entry_id)
    
    def remove_entry(self, entry_id: str):
        """Remove entry from indexes"""
        if entry_id in self.knowledge_store:
            del self.knowledge_store[entry_id]
        
        # Remove from all indexes (simplified - rebuild would be cleaner)
        for index in [self.keyword_index, self.tag_index, self.entity_index,
                     self.source_index, self.type_index]:
            for key in list(index.keys()):
                if entry_id in index[key]:
                    index[key].discard(entry_id)


# ==================== RERANKING LAYER ====================

class RerankingLayer:
    """
    Reranking Layer - Score and rerank candidates
    =============================================
    Calculates final scores using weighted combination:
    final_score = lexical + semantic + entity + task_fit + evidence + authority + temporal + success - penalties
    """
    
    # Signal weights (can be tuned)
    DEFAULT_WEIGHTS = {
        "lexical": 0.15,
        "semantic": 0.20,
        "entity_match": 0.10,
        "task_fit": 0.15,
        "evidence_strength": 0.15,
        "source_authority": 0.10,
        "temporal_fit": 0.10,
        "success_backing": 0.05
    }
    
    def __init__(self, knowledge_store: Dict[str, KnowledgeEntry] = None,
                 temporal_reasoner: TemporalReasoner = None):
        self.knowledge_store = knowledge_store or {}
        
        # Add all entries to indexes if store is provided
        self.temporal_reasoner = temporal_reasoner or TemporalReasoner(self.knowledge_store)
        self.weights = self.DEFAULT_WEIGHTS.copy()
        
        logger.info("🎯 Reranking Layer initialized")
    
    def rerank(self, parsed_query: ParsedQuery,
               candidate_ids: List[str],
               context: QueryContext = None) -> List[ScoredCandidate]:
        """
        Rerank candidates with weighted scoring
        """
        scored_candidates = []
        
        for entry_id in candidate_ids:
            entry = self.knowledge_store.get(entry_id)
            if not entry:
                continue
            
            # Calculate scores
            scored = self._calculate_scores(entry, parsed_query, context)
            scored.entry = entry
            
            scored_candidates.append(scored)
        
        # Sort by final score
        scored_candidates.sort(key=lambda x: x.final_score, reverse=True)
        
        return scored_candidates
    
    def _calculate_scores(self, entry: KnowledgeEntry,
                         parsed_query: ParsedQuery,
                         context: QueryContext) -> ScoredCandidate:
        """Calculate all signal scores for an entry"""
        scored = ScoredCandidate(entry=entry)
        
        # 1. Lexical score
        scored.lexical_score = self._lexical_score(entry, parsed_query)
        
        # 2. Semantic score (if embeddings available)
        scored.semantic_score = self._semantic_score(entry, parsed_query)
        
        # 3. Entity match score
        scored.entity_match_score = self._entity_match_score(entry, parsed_query)
        
        # 4. Task fit score
        scored.task_fit_score = self._task_fit_score(entry, parsed_query, context)
        
        # 5. Evidence strength score
        scored.evidence_strength_score = self._evidence_strength_score(entry)
        
        # 6. Source authority score
        scored.source_authority_score = self._source_authority_score(entry)
        
        # 7. Temporal fit score
        scored.temporal_fit_score = self._temporal_fit_score(entry, parsed_query)
        
        # 8. Success backing score
        scored.success_backing_score = self._success_backing_score(entry)
        
        # Penalties
        scored.contradiction_penalty = self._contradiction_penalty(entry)
        scored.stale_penalty = self._stale_penalty(entry)
        scored.scope_mismatch_penalty = self._scope_mismatch_penalty(entry, parsed_query)
        
        # Calculate final score
        scored.final_score = scored.total_signal_score()
        
        return scored
    
    def _lexical_score(self, entry: KnowledgeEntry, query: ParsedQuery) -> float:
        """Calculate lexical match score"""
        if not query.keywords:
            return 0.0
        
        content_lower = entry.content.lower() if entry.content else ""
        matched = sum(1 for kw in query.keywords if kw in content_lower)
        
        return matched / len(query.keywords)
    
    def _semantic_score(self, entry: KnowledgeEntry, query: ParsedQuery) -> float:
        """Calculate semantic similarity score"""
        # If embeddings available, use cosine similarity
        if entry.embedding and len(entry.embedding) > 0:
            # For now, return a simple score based on keyword context
            # In production, use actual embedding similarity
            return 0.5  # Placeholder
        
        # Fallback to partial keyword matching
        return self._lexical_score(entry, query) * 0.5
    
    def _entity_match_score(self, entry: KnowledgeEntry, query: ParsedQuery) -> float:
        """Calculate entity match score"""
        if not query.entities:
            return 0.0
        
        entry_entities = set(e.lower() for e in (entry.entities or []))
        query_entities = set(e.lower() for e in query.entities)
        
        if not entry_entities:
            return 0.0
        
        matches = len(entry_entities & query_entities)
        return matches / len(query_entities)
    
    def _task_fit_score(self, entry: KnowledgeEntry,
                       query: ParsedQuery,
                       context: QueryContext) -> float:
        """Calculate task fit score"""
        score = 0.5  # Base score
        
        # Check if entry tags match task type
        if entry.tags and context:
            task_tag_map = {
                TaskType.CODING: ["code", "programming", "implementation"],
                TaskType.DEBUGGING: ["debug", "error", "troubleshooting"],
                TaskType.RESEARCH: ["research", "documentation", "reference"],
                TaskType.DEPLOYMENT: ["deployment", "devops", "infrastructure"],
                TaskType.SECURITY: ["security", "authentication", "encryption"]
            }
            
            task_tags = task_tag_map.get(context.task_type, [])
            entry_tags = set(t.lower() for t in entry.tags)
            
            if any(t in entry_tags for t in task_tags):
                score += 0.3
        
        # Check knowledge type fit
        if entry.knowledge_type:
            type_intent_map = {
                RetrievalIntent.PROCEDURAL: [KnowledgeType.PROCEDURE],
                RetrievalIntent.FACTUAL: [KnowledgeType.FACT, KnowledgeType.CONCEPT],
                RetrievalIntent.CODE: [KnowledgeType.CODE],
            }
            
            expected_types = type_intent_map.get(query.intent, [])
            if entry.knowledge_type in expected_types:
                score += 0.2
        
        return min(1.0, score)
    
    def _evidence_strength_score(self, entry: KnowledgeEntry) -> float:
        """Calculate evidence strength score"""
        score = 0.0
        
        # Corroboration count
        if entry.corroboration_count:
            score += min(0.4, entry.corroboration_count * 0.1)
        
        # Independent source count
        if entry.independent_source_count:
            score += min(0.3, entry.independent_source_count * 0.1)
        
        # Verification recency
        if entry.last_verified:
            days_since = (time.time() - entry.last_verified) / (24 * 3600)
            if days_since < 7:
                score += 0.3
            elif days_since < 30:
                score += 0.2
            elif days_since < 90:
                score += 0.1
        
        return min(1.0, score)
    
    def _source_authority_score(self, entry: KnowledgeEntry) -> float:
        """Calculate source authority score"""
        # Map source types to authority scores
        authority_map = {
            "documentation": 1.0,
            "api_docs": 1.0,
            "github": 0.9,
            "paper": 0.9,
            "blog": 0.7,
            "forum": 0.5,
            "stackoverflow": 0.6,
            "news": 0.5,
            "wiki": 0.7
        }
        
        source_lower = entry.source.lower() if entry.source else ""
        return authority_map.get(source_lower, 0.5)
    
    def _temporal_fit_score(self, entry: KnowledgeEntry, query: ParsedQuery) -> float:
        """Calculate temporal fit score"""
        if query.temporal_scope == "any":
            return 0.5
        
        is_current = self.temporal_reasoner.is_currently_valid(entry)
        
        if query.temporal_scope == "current":
            return 1.0 if is_current else 0.2
        elif query.temporal_scope == "historical":
            return 0.2 if is_current else 1.0
        
        return 0.5
    
    def _success_backing_score(self, entry: KnowledgeEntry) -> float:
        """Calculate success backing score"""
        score = 0.5  # Base
        
        # Success rate
        if entry.usage_count > 0:
            success_rate = entry.success_count / entry.usage_count
            score = 0.3 + (success_rate * 0.5)
        
        # Recent usage bonus
        if entry.usage_count > 5:
            score += 0.2
        
        return min(1.0, score)
    
    def _contradiction_penalty(self, entry: KnowledgeEntry) -> float:
        """Calculate penalty for contradictory evidence"""
        # If entry has refutations
        if entry.refutation_count and entry.refutation_count > 0:
            return min(0.5, entry.refutation_count * 0.1)
        
        return 0.0
    
    def _stale_penalty(self, entry: KnowledgeEntry) -> float:
        """Calculate penalty for stale knowledge"""
        # Check temporal status
        if entry.temporal_status == TemporalStatus.STALE_NEEDS_CHECK:
            return 0.4
        elif entry.temporal_status == TemporalStatus.SUPERSEDED:
            return 0.3
        
        # Check expiry pressure
        if hasattr(entry, 'expiry_pressure') and entry.expiry_pressure:
            return entry.expiry_pressure * 0.3
        
        # Time since verification
        if entry.last_verified:
            days_since = (time.time() - entry.last_verified) / (24 * 3600)
            if days_since > 180:
                return 0.3
            elif days_since > 90:
                return 0.2
        
        return 0.0
    
    def _scope_mismatch_penalty(self, entry: KnowledgeEntry, query: ParsedQuery) -> float:
        """Calculate penalty for scope mismatch"""
        # Version mismatch
        if query.version_constraint and entry.version_scope:
            if not entry.version_scope.is_version_compatible(query.version_constraint):
                return 0.5
        
        return 0.0


# ==================== RETRIEVAL FLIGHT RECORDER ====================

class RetrievalFlightRecorder:
    """
    Retrieval Flight Recorder - Track and learn from retrieval outcomes
    ==================================================================
    Records:
    - Query details
    - Candidates considered
    - Final selection
    - Task outcome (did it help?)
    """
    
    def __init__(self, max_history: int = 1000):
        self.max_history = max_history
        self.history: List[Dict] = []
        self.retrieval_stats: Dict[str, Any] = defaultdict(int)
        
        logger.info("✈️ Retrieval Flight Recorder initialized")
    
    def record_retrieval(self, query: str, parsed_query: ParsedQuery,
                        candidates: List[ScoredCandidate],
                        selected: List[ScoredCandidate],
                        context: QueryContext = None):
        """Record a retrieval event"""
        record = {
            "timestamp": time.time(),
            "query": query,
            "intent": parsed_query.intent.value if parsed_query else "unknown",
            "total_candidates": len(candidates),
            "selected_count": len(selected),
            "selected_ids": [s.entry.entry_id for s in selected],
            "top_scores": [s.final_score for s in selected[:5]] if selected else [],
            "context": {
                "task_type": context.task_type.value if context else "general",
                "desired_answer": context.desired_answer_type if context else "text"
            } if context else {}
        }
        
        self.history.append(record)
        
        # Trim history
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]
        
        # Update stats
        self.retrieval_stats["total_retrievals"] += 1
        self.retrieval_stats["total_candidates"] += len(candidates)
    
    def record_outcome(self, query: str, selected_ids: List[str],
                      helped: bool, details: str = ""):
        """Record task outcome"""
        # Find matching record
        for record in reversed(self.history):
            if record["query"] == query:
                record["outcome"] = {
                    "helped": helped,
                    "details": details,
                    "timestamp": time.time()
                }
                break
        
        if helped:
            self.retrieval_stats["successful_retrievals"] += 1
        else:
            self.retrieval_stats["unsuccessful_retrievals"] += 1
    
    def get_insights(self) -> Dict:
        """Get insights from flight recorder"""
        recent = self.history[-100:] if len(self.history) > 100 else self.history
        
        # Analyze patterns
        intent_counts = defaultdict(int)
        avg_candidates = 0
        avg_selected = 0
        
        for record in recent:
            intent_counts[record["intent"]] += 1
            avg_candidates += record["total_candidates"]
            avg_selected += record["selected_count"]
        
        total = len(recent) if recent else 1
        
        return {
            "total_retrievals": self.retrieval_stats["total_retrievals"],
            "intent_distribution": dict(intent_counts),
            "avg_candidates": avg_candidates / total,
            "avg_selected": avg_selected / total,
            "success_rate": (
                self.retrieval_stats.get("successful_retrievals", 0) / 
                max(1, self.retrieval_stats.get("total_retrievals", 1))
            )
        }


# ==================== CONTEXT PACKER ====================

class ContextPacker:
    """
    Context Packer - Pack retrieval results into structured format
    ==============================================================
    Creates:
    - Compact evidence bundles
    - Selection rationale
    - Warnings and flags
    - Structured answer format
    """
    
    def pack(self, parsed_query: ParsedQuery,
             scored_candidates: List[ScoredCandidate],
             max_entries: int = 5) -> RetrievalResult:
        """Pack results into structured format"""
        result = RetrievalResult()
        result.parsed_query = parsed_query
        
        # Select top candidates
        selected = scored_candidates[:max_entries]
        result.entries = selected
        result.selected_count = len(selected)
        
        # Calculate total considered
        result.total_candidates_considered = len(scored_candidates)
        
        # Add warnings
        for scored in selected:
            entry = scored.entry
            
            # Check for disputes
            if hasattr(entry, 'temporal_status'):
                if entry.temporal_status == TemporalStatus.DISPUTED:
                    result.disputed_entries.append(entry.entry_id)
                    result.warnings.append(f"Entry {entry.entry_id} is disputed")
            
            # Check for staleness
            if scored.stale_penalty > 0.2:
                result.stale_entries.append(entry.entry_id)
                result.warnings.append(f"Entry {entry.entry_id} may be stale")
            
            # Check for low confidence
            if entry.confidence < 0.5:
                result.low_confidence_entries.append(entry.entry_id)
        
        # Generate why selected
        result.why_selected = self._generate_rationale(selected, parsed_query)
        
        # Generate context pack
        result.context_pack = self._create_context_pack(selected, parsed_query)
        
        return result
    
    def _generate_rationale(self, selected: List[ScoredCandidate],
                           query: ParsedQuery) -> str:
        """Generate explanation for selection"""
        if not selected:
            return "No matching entries found."
        
        top = selected[0]
        reasons = []
        
        # Best matching signal
        signals = {
            "lexical": top.lexical_score,
            "semantic": top.semantic_score,
            "evidence": top.evidence_strength_score,
            "authority": top.source_authority_score,
            "temporal": top.temporal_fit_score
        }
        
        best_signal = max(signals, key=signals.get)
        if signals[best_signal] > 0.5:
            reasons.append(f"Strong {best_signal} match")
        
        # Task fit
        if top.task_fit_score > 0.7:
            reasons.append(f"Fits {query.intent.value} intent")
        
        # Temporal fit
        if query.temporal_scope == "current" and top.temporal_fit_score > 0.8:
            reasons.append("Current and up-to-date")
        
        return "; ".join(reasons) if reasons else "Best matching entry"
    
    def _create_context_pack(self, selected: List[ScoredCandidate],
                           query: ParsedQuery) -> Dict:
        """Create compact context pack"""
        pack = {
            "summary": "",
            "entries": [],
            "evidence": [],
            "warnings": []
        }
        
        # Summaries
        summaries = [s.entry.content[:200] for s in selected if s.entry.content]
        pack["summary"] = " | ".join(summaries[:3])
        
        # Entry details
        for scored in selected:
            entry_data = {
                "id": scored.entry.entry_id,
                "content": scored.entry.content[:300],
                "confidence": scored.entry.confidence,
                "score": scored.final_score,
                "matched_terms": scored.matched_terms,
                "why": scored.selected_reason
            }
            pack["entries"].append(entry_data)
        
        # Evidence snippets
        if selected and hasattr(selected[0].entry, "evidence_ids"):
            pack["evidence_count"] = len(selected[0].entry.evidence_ids)
        
        return pack


# ==================== REAL RETRIEVAL ENGINE ====================

class RealRetrievalEngine:
    """
    Real Retrieval Engine - Main retrieval system
    =============================================
    Combines all layers for world-class retrieval:
    1. Query Understanding
    2. Candidate Generation
    3. Reranking
    4. Context Packing
    5. Flight Recording
    """
    
    def __init__(self, knowledge_store: Dict[str, KnowledgeEntry] = None,
                 data_dir: Path = None):
        self.data_dir = data_dir or Path(__file__).parent.parent / "data" / "retrieval"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Core components
        self.knowledge_store = knowledge_store or {}
        
        # Add all entries to indexes if store is provided
        
        # Initialize layers
        self.query_understanding = QueryUnderstandingLayer()
        self.candidate_generation = CandidateGenerationLayer(self.knowledge_store)
        self.temporal_reasoner = TemporalReasoner(self.knowledge_store)
        self.reranking = RerankingLayer(self.knowledge_store, self.temporal_reasoner)
        self.flight_recorder = RetrievalFlightRecorder()
        self.context_packer = ContextPacker()
        
        # Build indexes from existing knowledge
        for entry_id, entry in self.knowledge_store.items():
            self.candidate_generation.add_entry(entry)
        
        logger.info("🔎 Real Retrieval Engine initialized (No1+ Level)")
    
    def retrieve(self, query: str, context: QueryContext = None,
                max_results: int = 10) -> RetrievalResult:
        """
        Main retrieval method
        """
        start_time = time.time()
        
        # Step 1: Parse query
        parsed_query = self.query_understanding.parse_query(query, context)
        
        # Step 2: Generate candidates
        candidate_ids = self.candidate_generation.generate_candidates(
            parsed_query, max_candidates=100
        )
        
        # Step 3: Rerank candidates
        scored_candidates = self.reranking.rerank(
            parsed_query, candidate_ids, context
        )
        
        # Step 4: Pack context
        result = self.context_packer.pack(parsed_query, scored_candidates, max_results)
        
        # Step 5: Record retrieval
        result.retrieval_time_ms = (time.time() - start_time) * 1000
        self.flight_recorder.record_retrieval(
            query, parsed_query, scored_candidates, result.entries, context
        )
        
        return result
    
    def add_knowledge(self, entry: KnowledgeEntry):
        """Add knowledge to retrieval system"""
        self.knowledge_store[entry.entry_id] = entry
        self.candidate_generation.add_entry(entry)
    
    def remove_knowledge(self, entry_id: str):
        """Remove knowledge from retrieval system"""
        if entry_id in self.knowledge_store:
            del self.knowledge_store[entry_id]
        self.candidate_generation.remove_entry(entry_id)
    
    def record_outcome(self, query: str, selected_ids: List[str],
                      helped: bool, details: str = ""):
        """Record retrieval outcome for learning"""
        self.flight_recorder.record_outcome(query, selected_ids, helped, details)
    
    def get_system_stats(self) -> Dict:
        """Get retrieval system statistics"""
        return {
            "total_knowledge": len(self.knowledge_store),
            "flight_recorder": self.flight_recorder.get_insights(),
            "index_stats": {
                "keywords": len(self.candidate_generation.keyword_index),
                "tags": len(self.candidate_generation.tag_index),
                "entities": len(self.candidate_generation.entity_index)
            }
        }


# ==================== TYPE-SPECIFIC RETRIEVAL ====================

class TypeSpecificRetrieval:
    """
    Type-specific retrieval heads
    ==============================
    Specialized retrieval for different knowledge types:
    - Fact retrieval: truth + evidence + freshness
    - Procedure retrieval: goal + environment + success
    - Preference retrieval: recency + explicitness + user
    - Code retrieval: API + version + examples
    """
    
    def __init__(self, retrieval_engine: RealRetrievalEngine):
        self.engine = retrieval_engine
        logger.info("🎯 Type-Specific Retrieval initialized")
    
    def retrieve_facts(self, query: str, context: QueryContext = None,
                      max_results: int = 5) -> RetrievalResult:
        """Retrieve factual knowledge"""
        # Add fact-specific context
        if context:
            context.desired_answer_type = "fact"
        
        # Override intent
        result = self.engine.retrieve(query, context, max_results)
        
        # Filter for factual content
        result.entries = [
            e for e in result.entries
            if e.entry.knowledge_type in [KnowledgeType.FACT, KnowledgeType.CONCEPT]
        ][:max_results]
        
        return result
    
    def retrieve_procedures(self, query: str, context: QueryContext = None,
                          max_results: int = 5) -> RetrievalResult:
        """Retrieve procedural knowledge"""
        if context:
            context.desired_answer_type = "procedure"
        
        result = self.engine.retrieve(query, context, max_results)
        
        # Filter for procedural content
        result.entries = [
            e for e in result.entries
            if e.entry.knowledge_type == KnowledgeType.PROCEDURE
        ][:max_results]
        
        return result
    
    def retrieve_code(self, query: str, context: QueryContext = None,
                    max_results: int = 5) -> RetrievalResult:
        """Retrieve code examples"""
        if context:
            context.desired_answer_type = "code"
        
        result = self.engine.retrieve(query, context, max_results)
        
        # Filter for code content
        result.entries = [
            e for e in result.entries
            if e.entry.knowledge_type == KnowledgeType.CODE
        ][:max_results]
        
        return result
    
    def retrieve_preferences(self, query: str, user_id: str = "",
                          max_results: int = 3) -> RetrievalResult:
        """Retrieve user preferences"""
        result = self.engine.retrieve(query, None, max_results)
        
        # Filter for recent preferences
        # (In production, use actual preference store)
        return result


# ==================== FACTORY FUNCTION ====================

def create_retrieval_engine(knowledge_store: Dict[str, KnowledgeEntry] = None,
                           data_dir: Path = None) -> RealRetrievalEngine:
    """Factory function to create RealRetrievalEngine"""
    return RealRetrievalEngine(knowledge_store, data_dir)


# ==================== EXPORTS ====================

__all__ = [
    "RetrievalIntent",
    "TaskType", 
    "QueryContext",
    "ParsedQuery",
    "RetrievalSignal",
    "ScoredCandidate",
    "RetrievalResult",
    "QueryUnderstandingLayer",
    "CandidateGenerationLayer",
    "RerankingLayer",
    "RetrievalFlightRecorder",
    "ContextPacker",
    "RealRetrievalEngine",
    "TypeSpecificRetrieval",
    "create_retrieval_engine"
]
