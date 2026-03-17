"""
External Learning System - The Eyes and Ears of Self-Upgrading Agent
====================================================================

This system observes external AI systems (ChatGPT, Devin, DeepSeek, etc.)
and social signals (Reddit, GitHub, Twitter, etc.) to generate
actionable upgrade candidates.

Architecture:
- Source Watchers: Observe frontier AI, social media, docs, benchmarks
- Signal Pipeline: Extract, normalize, score, and validate signals
- Research Memory: Store observations with deduplication
- Upgrade Generation: Convert signals to upgrade candidates

Key Design Principles:
1. Anti-hype guard: Require multiple evidence types
2. Signal Court: Judge each observation
3. Capability Mapping: Link signals to specific capabilities
4. ROI-based prioritization
"""

import asyncio
import logging
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import json
import os

from .source_watchers import (
    FrontierObserver,
    SocialSignalObserver,
    DocsReleaseWatcher,
    BenchmarkWatcher,
    AccountResearchWorker
)
from .signal_pipeline import (
    SignalNormalizer,
    SignalExtractor,
    SignalDeduper,
    SignalScorer,
    SignalCourt
)
from .research_memory import (
    ObservationStore,
    TrendTracker,
    EvidenceIndex
)
from .upgrade_generation import (
    CapabilityMapper,
    CandidateGenerator,
    ROIRanker
)

logger = logging.getLogger(__name__)


class SignalTier(Enum):
    """Priority tiers for signals"""
    TIER_1 = "tier_1"  # Repeated pain, proven workflow, benchmark-supported
    TIER_2 = "tier_2"  # Strong community demand, research papers
    TIER_3 = "tier_3"  # Viral hype, isolated anecdote


class SignalDecision(Enum):
    """Signal Court decisions"""
    ADOPT_NOW = "adopt_now"          # Immediate implementation candidate
    RESEARCH_MORE = "research_more" # Need more evidence
    WATCHLIST = "watchlist"           # Monitor for now
    REJECT_HYPE = "reject_hype"      # Reject as noise/hype


@dataclass
class ExternalSignal:
    """Normalized external signal structure"""
    signal_id: str
    source_type: str           # frontier, social, docs, benchmark
    source_name: str           # chatgpt, devin, reddit, etc.
    timestamp: datetime
    content_summary: str
    evidence_links: List[str] = field(default_factory=list)
    raw_artifacts: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.5
    topic_tags: List[str] = field(default_factory=list)
    
    # Extracted information
    capability_mentions: List[str] = field(default_factory=list)
    user_pain_points: List[str] = field(default_factory=list)
    workflow_innovations: List[str] = field(default_factory=list)
    tool_mentions: List[str] = field(default_factory=list)
    architecture_clues: List[str] = field(default_factory=list)
    performance_claims: List[str] = field(default_factory=list)
    
    # Scoring
    credibility_score: float = 0.0
    novelty_score: float = 0.0
    relevance_score: float = 0.0
    roi_score: float = 0.0
    implementability_score: float = 0.0
    
    # Court decision
    decision: Optional[SignalDecision] = None
    decision_reason: str = ""
    
    # Capability mapping
    mapped_capabilities: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            "signal_id": self.signal_id,
            "source_type": self.source_type,
            "source_name": self.source_name,
            "timestamp": self.timestamp.isoformat(),
            "content_summary": self.content_summary,
            "evidence_links": self.evidence_links,
            "confidence": self.confidence,
            "topic_tags": self.topic_tags,
            "capability_mentions": self.capability_mentions,
            "user_pain_points": self.user_pain_points,
            "workflow_innovations": self.workflow_innovations,
            "credibility_score": self.credibility_score,
            "novelty_score": self.novelty_score,
            "relevance_score": self.relevance_score,
            "roi_score": self.roi_score,
            "implementability_score": self.implementability_score,
            "decision": self.decision.value if self.decision else None,
            "decision_reason": self.decision_reason,
            "mapped_capabilities": self.mapped_capabilities
        }


@dataclass
class UpgradeCandidate:
    """Actionable upgrade candidate structure"""
    candidate_id: str
    title: str
    why_now: str
    source_signals: List[str] = field(default_factory=list)
    capabilities_affected: List[str] = field(default_factory=list)
    expected_user_value: str = ""
    implementation_type: str = ""  # prompt, workflow, tool, memory, planner, etc.
    risk_level: str = "medium"     # low, medium, high
    eval_plan: str = ""
    rollback_complexity: str = "medium"
    
    # Priority
    priority_score: float = 0.0
    tier: SignalTier = SignalTier.TIER_3
    status: str = "pending"        # pending, approved, rejected, implemented
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            "candidate_id": self.candidate_id,
            "title": self.title,
            "why_now": self.why_now,
            "source_signals": self.source_signals,
            "capabilities_affected": self.capabilities_affected,
            "expected_user_value": self.expected_user_value,
            "implementation_type": self.implementation_type,
            "risk_level": self.risk_level,
            "eval_plan": self.eval_plan,
            "rollback_complexity": self.rollback_complexity,
            "priority_score": self.priority_score,
            "tier": self.tier.value,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }


class ExternalLearningSystem:
    """
    External Learning System - Main Controller
    
    Observes external AI systems and social signals to generate
    actionable upgrade candidates for the agent.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the External Learning System
        
        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
        self._running = False
        self._watch_tasks: List[asyncio.Task] = []
        
        logger.info("🚀 Initializing External Learning System...")
        
        # Initialize components
        self._init_watchers()
        self._init_signal_pipeline()
        self._init_research_memory()
        self._init_upgrade_generation()
        
        logger.info("✅ External Learning System initialized")
    
    def _init_watchers(self):
        """Initialize source watchers"""
        logger.info("📡 Initializing Source Watchers...")
        
        # Frontier AI Observer
        self.frontier_observer = FrontierObserver(
            watch_targets=self.config.get("frontier_targets", [
                "chatgpt", "devin", "deepseek", "claude", "gemini",
                "openai", "anthropic", "google_deepmind"
            ])
        )
        
        # Social Signal Observer
        self.social_observer = SocialSignalObserver(
            watch_targets=self.config.get("social_targets", [
                "reddit", "twitter", "github", "youtube"
            ])
        )
        
        # Docs/Release Watcher
        self.docs_watcher = DocsReleaseWatcher(
            watch_targets=self.config.get("docs_targets", [
                "openai", "anthropic", "google_ai", "meta_ai"
            ])
        )
        
        # Benchmark Watcher
        self.benchmark_watcher = BenchmarkWatcher(
            benchmarks=self.config.get("benchmarks", [
                "swe_bench", "humaneval", "mmlu", "gpqa", "math_benchmark"
            ])
        )
        
        # Account-Based Research Worker (optional, requires user consent)
        self.account_worker = None
        if self.config.get("enable_account_research", False):
            self.account_worker = AccountResearchWorker(
                session_config=self.config.get("session_config", {})
            )
    
    def _init_signal_pipeline(self):
        """Initialize signal processing pipeline"""
        logger.info("🔄 Initializing Signal Pipeline...")
        
        # Normalizer - Convert raw content to standardized format
        self.normalizer = SignalNormalizer()
        
        # Extractor - Extract key information from signals
        self.extractor = SignalExtractor()
        
        # Deduper - Remove duplicate signals
        self.deduper = SignalDeduper()
        
        # Scorer - Score signals across multiple dimensions
        self.scorer = SignalScorer()
        
        # Signal Court - Judge signals
        self.signal_court = SignalCourt()
    
    def _init_research_memory(self):
        """Initialize research memory components"""
        logger.info("💾 Initializing Research Memory...")
        
        # Observation Store - Store all observations
        storage_path = self.config.get("storage_path", "data/external_learning")
        self.observation_store = ObservationStore(storage_path)
        
        # Trend Tracker - Track trends over time
        self.trend_tracker = TrendTracker(self.observation_store)
        
        # Evidence Index - Index evidence for quick lookup
        self.evidence_index = EvidenceIndex(self.observation_store)
    
    def _init_upgrade_generation(self):
        """Initialize upgrade generation components"""
        logger.info("🎯 Initializing Upgrade Generation...")
        
        # Capability Mapper - Map signals to capabilities
        self.capability_mapper = CapabilityMapper()
        
        # Candidate Generator - Generate upgrade candidates
        self.candidate_generator = CandidateGenerator()
        
        # ROI Ranker - Rank candidates by ROI
        self.roi_ranker = ROIRanker()
    
    # ==================== CORE METHODS ====================
    
    async def start(self):
        """Start the external learning system"""
        if self._running:
            logger.warning("External Learning System is already running")
            return
        
        logger.info("▶️ Starting External Learning System...")
        self._running = True
        
        # Start source watchers
        self._watch_tasks = [
            asyncio.create_task(self._watch_frontier()),
            asyncio.create_task(self._watch_social()),
            asyncio.create_task(self._watch_docs()),
            asyncio.create_task(self._watch_benchmarks())
        ]
        
        # Start account worker if enabled
        if self.account_worker:
            self._watch_tasks.append(
                asyncio.create_task(self._account_research())
            )
        
        logger.info("✅ External Learning System started")
    
    async def stop(self):
        """Stop the external learning system"""
        if not self._running:
            return
        
        logger.info("⏹️ Stopping External Learning System...")
        self._running = False
        
        # Cancel all watch tasks
        for task in self._watch_tasks:
            task.cancel()
        
        # Wait for tasks to complete
        await asyncio.gather(*self._watch_tasks, return_exceptions=True)
        
        logger.info("✅ External Learning System stopped")
    
    async def _watch_frontier(self):
        """Watch frontier AI systems"""
        while self._running:
            try:
                # Fetch frontier observations
                observations = await self.frontier_observer.fetch()
                
                for obs in observations:
                    await self._process_observation(obs, "frontier")
                
                await asyncio.sleep(self.config.get("frontier_interval", 3600))
                
            except Exception as e:
                logger.error(f"Error in frontier watcher: {e}")
                await asyncio.sleep(60)
    
    async def _watch_social(self):
        """Watch social media and community signals"""
        while self._running:
            try:
                # Fetch social signals
                signals = await self.social_observer.fetch()
                
                for signal in signals:
                    await self._process_observation(signal, "social")
                
                await asyncio.sleep(self.config.get("social_interval", 1800))
                
            except Exception as e:
                logger.error(f"Error in social watcher: {e}")
                await asyncio.sleep(60)
    
    async def _watch_docs(self):
        """Watch documentation and release notes"""
        while self._running:
            try:
                # Fetch docs updates
                updates = await self.docs_watcher.fetch()
                
                for update in updates:
                    await self._process_observation(update, "docs")
                
                await asyncio.sleep(self.config.get("docs_interval", 7200))
                
            except Exception as e:
                logger.error(f"Error in docs watcher: {e}")
                await asyncio.sleep(60)
    
    async def _watch_benchmarks(self):
        """Watch benchmark leaderboards"""
        while self._running:
            try:
                # Fetch benchmark changes
                changes = await self.benchmark_watcher.fetch()
                
                for change in changes:
                    await self._process_observation(change, "benchmark")
                
                await asyncio.sleep(self.config.get("benchmark_interval", 14400))
                
            except Exception as e:
                logger.error(f"Error in benchmark watcher: {e}")
                await asyncio.sleep(60)
    
    async def _account_research(self):
        """Run account-based research (requires user consent)"""
        if not self.account_worker:
            return
        
        while self._running:
            try:
                # Run research on configured accounts
                research_results = await self.account_worker.research()
                
                for result in research_results:
                    await self._process_observation(result, "account_research")
                
                await asyncio.sleep(self.config.get("account_interval", 86400))
                
            except Exception as e:
                logger.error(f"Error in account research: {e}")
                await asyncio.sleep(60)
    
    async def _process_observation(self, raw_data: Dict[str, Any], source_type: str):
        """
        Process a raw observation through the signal pipeline
        
        Args:
            raw_data: Raw observation data
            source_type: Type of source (frontier, social, docs, benchmark)
        """
        try:
            # Step 1: Normalize
            normalized = self.normalizer.normalize(raw_data, source_type)
            
            # Step 2: Extract key information
            extracted = self.extractor.extract(normalized)
            
            # Step 3: Check for duplicates
            is_dup, dup_id = self.deduper.check_duplicate(extracted)
            if is_dup:
                logger.debug(f"Duplicate signal found: {dup_id}")
                # Update duplicate count
                self.observation_store.increment_signal_count(dup_id)
                return
            
            # Step 4: Score the signal
            scored = self.scorer.score(extracted)
            
            # Step 5: Signal Court decision
            decision, reason = self.signal_court.judge(scored)
            scored.decision = decision
            scored.decision_reason = reason
            
            # Step 6: Map to capabilities
            capabilities = self.capability_mapper.map(scored)
            scored.mapped_capabilities = capabilities
            
            # Step 7: Store in research memory
            self.observation_store.store_signal(scored)
            
            # Step 8: Update trend tracker
            self.trend_tracker.update(scored)
            
            # Step 9: Index evidence
            self.evidence_index.index(scored)
            
            # Step 10: Generate upgrade candidate if Adopt Now
            if decision == SignalDecision.ADOPT_NOW:
                candidate = await self._generate_candidate(scored)
                if candidate:
                    self.roi_ranker.add_candidate(candidate)
                    logger.info(f"🎯 New upgrade candidate: {candidate.title}")
            
            logger.debug(f"Processed signal: {scored.signal_id} - Decision: {decision.value}")
            
        except Exception as e:
            logger.error(f"Error processing observation: {e}")
    
    async def _generate_candidate(self, signal: ExternalSignal) -> Optional[UpgradeCandidate]:
        """Generate an upgrade candidate from a signal"""
        return await self.candidate_generator.generate(signal)
    
    # ==================== PUBLIC API ====================
    
    def get_latest_signals(self, limit: int = 10, decision: Optional[SignalDecision] = None) -> List[ExternalSignal]:
        """
        Get latest signals
        
        Args:
            limit: Maximum number of signals to return
            decision: Filter by decision type
            
        Returns:
            List of external signals
        """
        return self.observation_store.get_latest(limit, decision)
    
    def get_upgrade_candidates(self, status: Optional[str] = None, limit: int = 10) -> List[UpgradeCandidate]:
        """
        Get upgrade candidates
        
        Args:
            status: Filter by status (pending, approved, rejected, implemented)
            limit: Maximum number of candidates
            
        Returns:
            List of upgrade candidates
        """
        candidates = self.roi_ranker.get_candidates(status)
        return sorted(candidates, key=lambda x: x.priority_score, reverse=True)[:limit]
    
    def get_top_candidate(self) -> Optional[UpgradeCandidate]:
        """Get the highest priority candidate"""
        candidates = self.get_upgrade_candidates(status="pending", limit=1)
        return candidates[0] if candidates else None
    
    def approve_candidate(self, candidate_id: str) -> bool:
        """Approve an upgrade candidate"""
        return self.roi_ranker.update_status(candidate_id, "approved")
    
    def reject_candidate(self, candidate_id: str, reason: str = "") -> bool:
        """Reject an upgrade candidate"""
        return self.roi_ranker.update_status(candidate_id, "rejected", reason)
    
    def get_trends(self, capability: Optional[str] = None, days: int = 30) -> Dict[str, Any]:
        """
        Get trend information
        
        Args:
            capability: Filter by capability
            days: Number of days to look back
            
        Returns:
            Trend information
        """
        return self.trend_tracker.get_trends(capability, days)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get system statistics"""
        return {
            "total_signals": self.observation_store.get_total_count(),
            "adopted_count": len(self.observation_store.get_by_decision(SignalDecision.ADOPT_NOW)),
            "rejected_count": len(self.observation_store.get_by_decision(SignalDecision.REJECT_HYPE)),
            "pending_candidates": len(self.get_upgrade_candidates(status="pending")),
            "approved_candidates": len(self.get_upgrade_candidates(status="approved")),
            "implemented_candidates": len(self.get_upgrade_candidates(status="implemented"))
        }
    
    def search_evidence(self, query: str, limit: int = 10) -> List[ExternalSignal]:
        """Search for evidence"""
        return self.evidence_index.search(query, limit)
    
    async def manual_observation(self, content: str, source: str, source_type: str = "manual") -> ExternalSignal:
        """
        Manually add an observation
        
        Args:
            content: Observation content
            source: Source name
            source_type: Type of source
            
        Returns:
            Created signal
        """
        raw_data = {
            "content": content,
            "source": source,
            "source_type": source_type
        }
        
        # Create signal ID
        signal_id = hashlib.sha256(
            f"{content}{source}{datetime.now().isoformat()}".encode()
        ).hexdigest()[:16]
        
        # Create ExternalSignal
        signal = ExternalSignal(
            signal_id=signal_id,
            source_type=source_type,
            source_name=source,
            timestamp=datetime.now(),
            content_summary=content,
            confidence=0.5
        )
        
        # Process through pipeline
        await self._process_observation(
            {"content": content, "source": source},
            source_type
        )
        
        return signal
    
    def save_state(self):
        """Save system state"""
        logger.info("💾 Saving External Learning System state...")
        self.observation_store.save()
        self.evidence_index.save()
    
    def load_state(self):
        """Load system state"""
        logger.info("📂 Loading External Learning System state...")
        self.observation_store.load()
        self.evidence_index.load()


def create_external_learning_system(config: Optional[Dict[str, Any]] = None) -> ExternalLearningSystem:
    """
    Factory function to create External Learning System
    
    Args:
        config: Configuration dictionary
        
    Returns:
        Initialized ExternalLearningSystem
    """
    return ExternalLearningSystem(config)
