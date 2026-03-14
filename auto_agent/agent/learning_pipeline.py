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
    procedure_id: str
    name: str
    steps: List[Dict]
    prerequisites: List[str]
    outcomes: List[str]
    success_rate: float
    last_used: float
    usage_count: int
    verified_against: List[str] = field(default_factory=list)


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
        if pid in self.procedures:
            p = self.procedures[pid]
            p.usage_count += 1
            if success:
                p.success_count += 1
            p.success_rate = p.success_count / p.usage_count
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
        results = []
        qterms = set(query.lower().split())
        
        for entry in self.knowledge.values():
            if entry.confidence < min_confidence:
                continue
            
            eterms = set(entry.content.lower().split())
            if qterms & eterms:
                entry.usage_count += 1
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
