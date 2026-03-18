"""
OmniAgent X - Time-Aware Truth System
======================================
Comprehensive temporal knowledge management for World No1+ implementation.

This module implements:
- Temporal Truth Model with validity windows
- Current/Historical Truth Split
- Supersession Graph
- Volatility Model with domain-specific decay
- Temporal Query Resolver
- Truth Clock for drift detection
- Time-aware retrieval ranking

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

# Import enums and classes from learning_pipeline
# These are defined there to maintain compatibility
try:
    from agent.learning_pipeline import (
        KnowledgeEntry,
        TemporalStatus,
        TemporalStatus as TimeScopeType,  # Alias for compatibility
        VolatilityClass,
        TruthClock,
        DEFAULT_VOLATILITY_PARAMS,
        VOLATILITY_PARAMS,
        ProceduralMemory
    )
except ImportError:
    # Fallback definitions if import fails
    TemporalStatus = None
    VolatilityClass = None
    TruthClock = None
    KnowledgeEntry = None
    ProceduralMemory = None
    DEFAULT_VOLATILITY_PARAMS = {}
    VOLATILITY_PARAMS = {}


# Alias for clarity
if TemporalStatus:
    class TimeScopeType(Enum):
        """Time scope type for knowledge validity"""
        CURRENT = "current"
        HISTORICAL = "historical"
        FORECAST = "forecast"
        DEPRECATED = "deprecated"
        TIMELESS = "timeless"
        COMPARATIVE = "comparative"
        VERSION_SCOPED = "version_scoped"


# ==================== VERSION SCOPE ====================

@dataclass
class VersionScope:
    """
    Version Scope - Version-specific knowledge tracking
    ==================================================
    Tracks which version(s) a piece of knowledge applies to.
    Essential for accurate code/tech recommendations.
    """
    product_name: str
    component: str = ""
    version: str = ""
    version_min: str = ""
    version_max: str = ""
    version_range: str = ""
    environment_scope: str = ""
    platform_scope: str = ""
    edition: str = ""
    
    def is_version_compatible(self, target_version: str) -> bool:
        if self.version and self.version == target_version:
            return True
        if self.version_range:
            return target_version in self.version_range
        return True
    
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


# ==================== TEMPORAL REASONER ====================

class TemporalReasoner:
    """
    Temporal Reasoner - Answers time-related questions about knowledge
    ================================================================
    This layer answers questions like:
    - "Is this knowledge currently valid?"
    - "When was this knowledge valid?"
    - "What superseded this knowledge?"
    - "Do we need historical or current answer?"
    """
    
    def __init__(self, knowledge_store: Dict[str, Any] = None):
        self.knowledge_store = knowledge_store or {}
        
        # Supersession graph: entry_id -> list of superseded entry IDs
        self.supersession_graph: Dict[str, List[str]] = defaultdict(list)
        
        # Reverse supersession: entry_id -> what superseded it
        self.superseded_by_graph: Dict[str, str] = {}
        
        # Version knowledge index
        self.version_index: Dict[str, List[str]] = defaultdict(list)
        
        logger.info("🕐 Temporal Reasoner initialized")
    
    # ==================== VALIDITY CHECKS ====================
    
    def is_currently_valid(self, entry: Any) -> bool:
        """Check if knowledge is currently valid"""
        current_time = time.time()
        
        # Check temporal status
        if entry.temporal_status == TemporalStatus.SUPERSEDED:
            return False
        if entry.temporal_status == TemporalStatus.RETIRED:
            return False
        if entry.temporal_status == TemporalStatus.ARCHIVED:
            return False
        
        # Check validity window
        if entry.valid_from > 0 and current_time < entry.valid_from:
            return False  # Not yet valid
        if entry.valid_until > 0 and current_time > entry.valid_until:
            return False  # No longer valid
        
        # Check if superseded
        if entry.superseded_by:
            return False
        
        return True
    
    def get_validity_window(self, entry: Any) -> Dict[str, float]:
        """Get the validity window for knowledge"""
        return {
            "valid_from": entry.valid_from,
            "valid_until": entry.valid_until,
            "is_current": self.is_currently_valid(entry),
            "is_historical": entry.is_historical,
            "was_valid_at": self._was_valid_at(entry, entry.verified_at)
        }
    
    def _was_valid_at(self, entry: Any, timestamp: float) -> bool:
        """Check if knowledge was valid at a specific timestamp"""
        if entry.valid_from > 0 and timestamp < entry.valid_from:
            return False
        if entry.valid_until > 0 and timestamp > entry.valid_until:
            return False
        return True
    
    # ==================== SUPERSESSION ====================
    
    def supersede(self, old_entry_id: str, new_entry_id: str, 
                  reason: str = "", effective_date: float = None) -> bool:
        """
        Mark old entry as superseded by new entry.
        Returns True if successful.
        """
        if effective_date is None:
            effective_date = time.time()
        
        # Add to supersession graph
        self.supersession_graph[old_entry_id].append(new_entry_id)
        
        # Add reverse mapping
        self.superseded_by_graph[new_entry_id] = old_entry_id
        
        # Update the old entry if it exists in store
        if old_entry_id in self.knowledge_store:
            old_entry = self.knowledge_store[old_entry_id]
            old_entry.superseded_by = new_entry_id
            old_entry.superseded_at = effective_date
            old_entry.temporal_status = TemporalStatus.SUPERSEDED
            old_entry.is_current = False
            old_entry.is_historical = True
            old_entry.time_scope_type = TimeScopeType.HISTORICAL
            
            # Add timeline event
            old_entry.timeline_events.append({
                "event": "superseded",
                "timestamp": effective_date,
                "superseded_by": new_entry_id,
                "reason": reason
            })
        
        logger.info(f"🔄 {old_entry_id} superseded by {new_entry_id}")
        return True
    
    def get_supersession_chain(self, entry_id: str) -> List[str]:
        """Get the full supersession chain for an entry"""
        chain = []
        current_id = entry_id
        
        while current_id in self.supersession_graph:
            superseded_by = self.supersession_graph[current_id]
            if superseded_by:
                chain.append(superseded_by[0])  # Get latest superseder
                current_id = superseded_by[0]
            else:
                break
        
        return chain
    
    def get_superseded_by(self, entry_id: str) -> Optional[str]:
        """Get what superseded this entry"""
        return self.superseded_by_graph.get(entry_id)
    
    # ==================== VERSION SCOPE ====================
    
    def register_version_knowledge(self, entry: Any):
        """Register knowledge with version scope"""
        if entry.version_scope and entry.version_scope.product_name:
            key = f"{entry.version_scope.product_name}:{entry.version_scope.version or 'any'}"
            self.version_index[key].append(entry.entry_id)
    
    def find_version_knowledge(self, product: str, version: str = None) -> List[str]:
        """Find knowledge for a specific product version"""
        results = []
        
        # Exact version match
        if version:
            key = f"{product}:{version}"
            results.extend(self.version_index.get(key, []))
        
        # Any version
        results.extend(self.version_index.get(f"{product}:any", []))
        
        return results
    
    def check_version_compatibility(self, entry: Any, target_version: str) -> bool:
        """Check if knowledge is compatible with target version"""
        if not entry.version_scope:
            return True  # No version constraint
        
        return entry.version_scope.is_version_compatible(target_version)
    
    # ==================== TEMPORAL QUERIES ====================
    
    def resolve_temporal_intent(self, query: str) -> Dict[str, Any]:
        """
        Parse temporal intent from user query.
        
        Returns:
            {
                "intent": "current" | "historical" | "comparative" | "version_scoped" | "timeless",
                "time_reference": "now" | "2024" | "before" | "after" | etc,
                "version": "3.11" | None,
                "confidence": 0.0-1.0
            }
        """
        query_lower = query.lower()
        
        # Current time indicators
        current_indicators = [
            "hozir", "current", "now", "today", "yangi", "latest", 
            "eng yangi", "currently", "present", "qachon", "endigi"
        ]
        
        # Historical indicators
        historical_indicators = [
            "avval", "oldin", "previous", "past", "before", "qachonlardir",
            "tarixiy", "historical", "eski", "2000", "2020", "2021", "2022", "2023", "2024"
        ]
        
        # Comparative indicators
        comparative_indicators = [
            "farqi", "difference", "vs", "versus", "compare", "qiyos",
            "yaxshi", "better", "yomon", "worse"
        ]
        
        # Version indicators
        version_patterns = [
            r'python\s*(\d+\.\d+)',
            r'react\s*(\d+)',
            r'node\s*(\d+\.\d+)',
            r'next\.?js\s*(\d+)',
            r'version\s*(\d+\.\d+)',
            r'v(\d+\.\d+)'
        ]
        
        # Check for time indicators
        intent = "current"  # Default to current
        time_reference = "now"
        
        for indicator in current_indicators:
            if indicator in query_lower:
                intent = "current"
                time_reference = "now"
                break
        
        for indicator in historical_indicators:
            if indicator in query_lower:
                # Try to extract specific year
                year_match = re.search(r'(20\d{2})', query)
                if year_match:
                    time_reference = year_match.group(1)
                else:
                    time_reference = "past"
                intent = "historical"
                break
        
        for indicator in comparative_indicators:
            if indicator in query_lower:
                intent = "comparative"
                break
        
        # Extract version if present
        version = None
        for pattern in version_patterns:
            match = re.search(pattern, query_lower)
            if match:
                version = match.group(1)
                intent = "version_scoped"
                break
        
        # Check for timeless (mathematical, etc.)
        timeless_patterns = ["always", "eternal", "数学", "matematik", "constant"]
        for pattern in timeless_patterns:
            if pattern in query_lower:
                intent = "timeless"
                break
        
        return {
            "intent": intent,
            "time_reference": time_reference,
            "version": version,
            "confidence": 0.9 if version else 0.7
        }
    
    # ==================== TRUTH CLOCK ====================
    
    def calculate_truth_clock(self, entry: Any) -> TruthClock:
        """Calculate truth clock for an entry"""
        current_time = time.time()
        
        clock = TruthClock(
            confidence=entry.confidence,
            time_confidence=entry.time_confidence,
            drift_risk=entry.drift_risk,
            expiry_pressure=entry.expiry_pressure
        )
        
        clock.calculate_truth_clock(
            current_time=current_time,
            volatility_class=entry.volatility_class,
            last_verified=entry.last_verified
        )
        
        return clock
    
    def get_expiry_warning(self, entry: Any) -> Dict[str, Any]:
        """Get expiry warning for knowledge"""
        clock = self.calculate_truth_clock(entry)
        
        warnings = []
        
        if clock.is_reverify_needed():
            warnings.append("REVERIFICATION NEEDED")
        
        if clock.drift_risk > 0.7:
            warnings.append("HIGH DRIFT RISK")
        
        if clock.expiry_pressure > 0.8:
            warnings.append("EXPIRING SOON")
        
        return {
            "entry_id": entry.entry_id,
            "warnings": warnings,
            "clock_data": clock.to_dict(),
            "days_until_expiry": clock.reverify_debt_days
        }


# ==================== TIME-AWARE RETRIEVAL ====================

class TimeAwareRetrieval:
    """
    Time-Aware Retrieval - Ranks knowledge by temporal relevance
    ============================================================
    Implements scoring formula:
    final_score = semantic_match + confidence + currentness + scope_match + corroboration - staleness_penalty - contradiction_penalty
    """
    
    def __init__(self, knowledge_store: Dict[str, Any] = None, 
                 temporal_reasoner: TemporalReasoner = None):
        self.knowledge_store = knowledge_store or {}
        self.temporal_reasoner = temporal_reasoner or TemporalReasoner(knowledge_store)
        
        logger.info("🔍 Time-Aware Retrieval initialized")
    
    def rank_knowledge(self, query: str, candidate_entries: List[Any],
                       temporal_context: Dict = None) -> List[Tuple[Any, float]]:
        """
        Rank knowledge entries by temporal relevance.
        
        Args:
            query: User query
            candidate_entries: List of candidate knowledge entries
            temporal_context: Expected temporal context (e.g., {"intent": "current"})
        
        Returns:
            List of (entry, score) tuples, sorted by score descending
        """
        if temporal_context is None:
            temporal_context = self.temporal_reasoner.resolve_temporal_intent(query)
        
        scored_entries = []
        
        for entry in candidate_entries:
            score = self._calculate_temporal_score(entry, temporal_context)
            scored_entries.append((entry, score))
        
        # Sort by score descending
        scored_entries.sort(key=lambda x: x[1], reverse=True)
        
        return scored_entries
    
    def _calculate_temporal_score(self, entry: Any, 
                                  temporal_context: Dict) -> float:
        """Calculate temporal score for a single entry"""
        
        # Base score components
        semantic_score = entry.confidence * 0.3
        currentness_score = 0.0
        scope_score = 0.0
        staleness_penalty = 0.0
        
        intent = temporal_context.get("intent", "current")
        
        # Current vs Historical handling
        if intent == "current":
            # Boost current knowledge
            if self.temporal_reasoner.is_currently_valid(entry):
                currentness_score = 0.4
            else:
                staleness_penalty = 0.5
                
        elif intent == "historical":
            # Boost historical knowledge
            if entry.is_historical:
                currentness_score = 0.4
            elif not entry.is_current:
                currentness_score = 0.2
                
        elif intent == "version_scoped":
            # Check version compatibility
            target_version = temporal_context.get("version")
            if target_version and entry.version_scope:
                if self.temporal_reasoner.check_version_compatibility(entry, target_version):
                    scope_score = 0.4
                else:
                    staleness_penalty = 0.6
        
        # Truth clock penalty
        clock = self.temporal_reasoner.calculate_truth_clock(entry)
        if clock.expiry_pressure > 0.5:
            staleness_penalty += clock.expiry_pressure * 0.2
        
        # Temporal status penalty
        if entry.temporal_status == TemporalStatus.STALE_NEEDS_CHECK:
            staleness_penalty += 0.3
        elif entry.temporal_status == TemporalStatus.DISPUTED:
            staleness_penalty += 0.4
        
        # Calculate final score
        final_score = (
            semantic_score + 
            currentness_score + 
            scope_score + 
            entry.corroboration_count * 0.05 -
            staleness_penalty
        )
        
        return max(0.0, min(1.0, final_score))
    
    def filter_by_time_scope(self, entries: List[Any], 
                            time_scope: str) -> List[Any]:
        """Filter entries by time scope"""
        filtered = []
        
        for entry in entries:
            if time_scope == "current":
                if self.temporal_reasoner.is_currently_valid(entry):
                    filtered.append(entry)
            elif time_scope == "historical":
                if entry.is_historical:
                    filtered.append(entry)
            elif time_scope == "all":
                filtered.append(entry)
        
        return filtered


# ==================== SUPERSESSION GRAPH MANAGER ====================

class SupersessionGraphManager:
    """
    Supersession Graph - Tracks knowledge evolution over time
    =========================================================
    Maintains explicit supersession relationships between knowledge entries.
    """
    
    def __init__(self):
        # Graph: entry_id -> list of IDs it superseded
        self.supersedes: Dict[str, List[str]] = defaultdict(list)
        
        # Reverse: entry_id -> what superseded it
        self.superseded_by: Dict[str, str] = {}
        
        # Graph: entry_id -> list of IDs that superseded it
        self.supersession_chain: Dict[str, List[str]] = defaultdict(list)
        
        # Metadata about each supersession
        self.supersession_metadata: Dict[str, Dict] = {}
        
        logger.info("🔗 Supersession Graph Manager initialized")
    
    def add_supersession(self, old_entry_id: str, new_entry_id: str,
                        reason: str = "", effective_date: float = None,
                        scope: str = "full", confidence: float = 1.0):
        """Add a supersession relationship"""
        if effective_date is None:
            effective_date = time.time()
        
        # Add to supersedes graph
        self.supersedes[old_entry_id].append(new_entry_id)
        
        # Add to reverse graph
        self.superseded_by[new_entry_id] = old_entry_id
        
        # Add to chain
        self.supersession_chain[old_entry_id].append(new_entry_id)
        
        # Store metadata
        self.supersession_metadata[f"{old_entry_id}->{new_entry_id}"] = {
            "reason": reason,
            "effective_date": effective_date,
            "scope": scope,
            "confidence": confidence,
            "created_at": time.time()
        }
        
        logger.info(f"🔗 Added supersession: {old_entry_id} -> {new_entry_id}")
    
    def get_current_version(self, entry_id: str) -> str:
        """Get the current (latest) version of knowledge"""
        # Follow the supersession chain forward
        current = entry_id
        
        while current in self.supersession_chain:
            chain = self.supersession_chain[current]
            if chain:
                current = chain[-1]  # Get latest
            else:
                break
        
        return current
    
    def get_history(self, entry_id: str) -> List[Dict]:
        """Get full history of an entry including its supersessions"""
        history = []
        
        # Go backward (what superseded this)
        current = entry_id
        while current in self.superseded_by:
            older = self.superseded_by[current]
            metadata = self.supersession_metadata.get(f"{older}->{current}", {})
            history.append({
                "type": "superseded",
                "entry_id": older,
                "metadata": metadata
            })
            current = older
        
        # Go forward (what this superseded)
        current = entry_id
        while current in self.supersedes:
            newer_list = self.supersedes[current]
            for newer in newer_list:
                metadata = self.supersession_metadata.get(f"{current}->{newer}", {})
                history.append({
                    "type": "supersedes",
                    "entry_id": newer,
                    "metadata": metadata
                })
            current = newer_list[-1] if newer_list else current
        
        return history
    
    def is_superseded(self, entry_id: str) -> bool:
        """Check if entry has been superseded"""
        return entry_id in self.superseded_by
    
    def get_supersession_reason(self, old_id: str, new_id: str) -> str:
        """Get reason for supersession"""
        key = f"{old_id}->{new_id}"
        metadata = self.supersession_metadata.get(key, {})
        return metadata.get("reason", "")


# ==================== VOLATILITY ENGINE ====================

class VolatilityEngine:
    """
    Volatility Engine - Domain-specific decay policies
    ===================================================
    Manages different decay rates for different knowledge domains.
    """
    
    def __init__(self):
        # Domain to volatility class mapping
        self.domain_volatility: Dict[str, VolatilityClass] = {}
        
        # Custom volatility parameters
        self.custom_params: Dict[VolatilityClass, Dict] = {}
        
        # Initialize with defaults
        self._init_domain_mappings()
        
        logger.info("📉 Volatility Engine initialized")
    
    def _init_domain_mappings(self):
        """Initialize default domain mappings"""
        # Programming/Technical
        self.domain_volatility["python"] = VolatilityClass.VOLATILE
        self.domain_volatility["javascript"] = VolatilityClass.VOLATILE
        self.domain_volatility["react"] = VolatilityClass.VOLATILE
        self.domain_volatility["nextjs"] = VolatilityClass.VOLATILE
        self.domain_volatility["api"] = VolatilityClass.VOLATILE
        self.domain_volatility["framework"] = VolatilityClass.VOLATILE
        self.domain_volatility["library"] = VolatilityClass.VOLATILE
        
        # Release/Version info
        self.domain_volatility["release"] = VolatilityClass.HIGHLY_VOLATILE
        self.domain_volatility["version"] = VolatilityClass.HIGHLY_VOLATILE
        self.domain_volatility["changelog"] = VolatilityClass.HIGHLY_VOLATILE
        
        # Pricing/Market
        self.domain_volatility["price"] = VolatilityClass.HIGHLY_VOLATILE
        self.domain_volatility["pricing"] = VolatilityClass.HIGHLY_VOLATILE
        self.domain_volatility["market"] = VolatilityClass.HIGHLY_VOLATILE
        self.domain_volatility["stock"] = VolatilityClass.HIGHLY_VOLATILE
        
        # Facts/Concepts
        self.domain_volatility["fact"] = VolatilityClass.MEDIUM
        self.domain_volatility["concept"] = VolatilityClass.STABLE
        self.domain_volatility["theory"] = VolatilityClass.IMMUTABLE
        
        # Math/Science
        self.domain_volatility["math"] = VolatilityClass.IMMUTABLE
        self.domain_volatility["physics"] = VolatilityClass.IMMUTABLE
        self.domain_volatility["constant"] = VolatilityClass.IMMUTABLE
        
        # User preferences
        self.domain_volatility["preference"] = VolatilityClass.USER_PREFERENCE
        self.domain_volatility["setting"] = VolatilityClass.USER_PREFERENCE
        
        # Procedures
        self.domain_volatility["procedure"] = VolatilityClass.PROCEDURE
        self.domain_volatility["workflow"] = VolatilityClass.PROCEDURE
        self.domain_volatility["deployment"] = VolatilityClass.PROCEDURE
    
    def get_volatility_class(self, entry: Any) -> VolatilityClass:
        """Determine volatility class for an entry"""
        # Check explicit setting
        if entry.volatility_class:
            return entry.volatility_class
        
        # Infer from tags
        if entry.tags:
            for tag in entry.tags:
                if tag.lower() in self.domain_volatility:
                    return self.domain_volatility[tag.lower()]
        
        # Infer from content
        content_lower = entry.content.lower()
        for domain, volatility in self.domain_volatility.items():
            if domain in content_lower:
                return volatility
        
        return VolatilityClass.MEDIUM  # Default
    
    def get_decay_factor(self, entry: Any, current_time: float) -> float:
        """Calculate decay factor based on volatility"""
        volatility = self.get_volatility_class(entry)
        params = self.custom_params.get(volatility, 
                                        VOLATILITY_PARAMS.get(volatility, 
                                                              DEFAULT_VOLATILITY_PARAMS[VolatilityClass.MEDIUM]))
        
        # Time since last verification
        time_since_verify = current_time - entry.last_verified
        days_since = time_since_verify / (24 * 3600)
        
        # Exponential decay
        decay_rate = params.get("decay_rate", 0.1)
        decay_factor = 2 ** (-days_since / params.get("reverify_interval_days", 90))
        
        return max(0.1, decay_factor)
    
    def get_reverify_priority(self, entry: Any) -> int:
        """Get reverification priority (higher = more urgent)"""
        volatility = self.get_volatility_class(entry)
        
        priority_map = {
            VolatilityClass.IMMUTABLE: 1,
            VolatilityClass.STABLE: 2,
            VolatilityClass.MEDIUM: 3,
            VolatilityClass.VOLATILE: 5,
            VolatilityClass.HIGHLY_VOLATILE: 8,
            VolatilityClass.USER_PREFERENCE: 4,
            VolatilityClass.PROCEDURE: 4
        }
        
        return priority_map.get(volatility, 3)


# ==================== TRUTH TIMELINE ====================

@dataclass
class TruthTimelineEvent:
    """Single event in a knowledge's timeline"""
    event_type: str          # observed, verified, superseded, challenged, retired, etc.
    timestamp: float
    details: Dict = field(default_factory=dict)
    triggered_by: str = ""   # system, user, external


class TruthTimeline:
    """
    Truth Timeline - Complete history of knowledge over time
    =========================================================
    Tracks all significant events in a knowledge entry's lifetime.
    """
    
    def __init__(self, entry_id: str):
        self.entry_id = entry_id
        self.events: List[TruthTimelineEvent] = []
    
    def add_event(self, event_type: str, details: Dict = None, 
                 triggered_by: str = "system"):
        """Add an event to the timeline"""
        event = TruthTimelineEvent(
            event_type=event_type,
            timestamp=time.time(),
            details=details or {},
            triggered_by=triggered_by
        )
        self.events.append(event)
        return event
    
    def get_event_summary(self) -> List[Dict]:
        """Get summary of all events"""
        return [
            {
                "event_type": e.event_type,
                "timestamp": e.timestamp,
                "datetime": datetime.fromtimestamp(e.timestamp).isoformat(),
                "details": e.details,
                "triggered_by": e.triggered_by
            }
            for e in self.events
        ]
    
    def get_milestones(self) -> List[Dict]:
        """Get major milestones"""
        milestone_types = ["verified", "superseded", "retired", "challenged"]
        return [
            {
                "event_type": e.event_type,
                "timestamp": e.timestamp,
                "datetime": datetime.fromtimestamp(e.timestamp).isoformat()
            }
            for e in self.events
            if e.event_type in milestone_types
        ]


# ==================== TIME-AWARE PREFERENCE MANAGER ====================

class TimeAwarePreferenceManager:
    """
    Time-Aware Preference Manager - Recency-weighted preferences
    =============================================================
    Manages user preferences with recency weighting.
    Recent preferences have more weight than older ones.
    """
    
    def __init__(self):
        # Preference storage: key -> list of (value, timestamp, weight)
        self.preferences: Dict[str, List[Dict]] = defaultdict(list)
        
        # Current active preferences
        self.current_preferences: Dict[str, Any] = {}
        
        # Decay parameters
        self.recent_window_days = 10      # Recent sessions have strong weight
        self.old_window_days = 180         # Older preferences decay
        self.recent_weight = 0.7           # Weight for recent preferences
        self.old_weight = 0.3             # Weight for old preferences
        
        logger.info("⚙️ Time-Aware Preference Manager initialized")
    
    def record_preference(self, key: str, value: Any, 
                         session_id: str = None,
                         explicit: bool = False):
        """Record a user preference with timestamp"""
        current_time = time.time()
        
        # Weight: explicit preferences get higher weight
        weight = 1.0 if explicit else 0.8
        
        self.preferences[key].append({
            "value": value,
            "timestamp": current_time,
            "session_id": session_id,
            "explicit": explicit,
            "weight": weight
        })
        
        # Update current preference
        self._recalculate_current(key)
        
        logger.info(f"📝 Recorded preference: {key} = {value}")
    
    def _recalculate_current(self, key: str):
        """Recalculate current preference with recency weighting"""
        if not self.preferences[key]:
            self.current_preferences[key] = None
            return
        
        current_time = time.time()
        weighted_sum = 0.0
        weight_total = 0.0
        
        for pref in self.preferences[key]:
            days_old = (current_time - pref["timestamp"]) / (24 * 3600)
            
            # Calculate recency weight
            if days_old <= self.recent_window_days:
                recency_weight = self.recent_weight
            elif days_old <= self.old_window_days:
                # Linear decay
                recency_weight = self.recent_weight - (
                    (self.recent_weight - self.old_weight) * 
                    (days_old - self.recent_window_days) / 
                    (self.old_window_days - self.recent_window_days)
                )
            else:
                recency_weight = self.old_weight * 0.5
            
            # Combined weight
            combined_weight = pref["weight"] * recency_weight
            
            weighted_sum += combined_weight * (1 if isinstance(pref["value"], (int, float)) else 
                                               hash(str(pref["value"])) % 100 / 100)
            weight_total += combined_weight
        
        # For non-numeric values, just take the most recent
        if not all(isinstance(p["value"], (int, float)) for p in self.preferences[key]):
            # Sort by timestamp and weight
            sorted_prefs = sorted(
                self.preferences[key],
                key=lambda x: (x["timestamp"], x["weight"]),
                reverse=True
            )
            self.current_preferences[key] = sorted_prefs[0]["value"]
        else:
            # Use weighted average
            if weight_total > 0:
                self.current_preferences[key] = weighted_sum / weight_total
    
    def get_preference(self, key: str, default: Any = None) -> Any:
        """Get current weighted preference"""
        return self.current_preferences.get(key, default)
    
    def get_preference_history(self, key: str) -> List[Dict]:
        """Get full history of a preference"""
        return self.preferences.get(key, [])
    
    def decay_old_preferences(self):
        """Apply decay to old preferences"""
        current_time = time.time()
        
        for key in self.preferences:
            # Remove very old preferences
            self.preferences[key] = [
                p for p in self.preferences[key]
                if current_time - p["timestamp"] < self.old_window_days * 2
            ]
            
            # Recalculate current
            self._recalculate_current(key)


# ==================== TIME-AWARE PROCEDURE MANAGER ====================

class TimeAwareProcedureManager:
    """
    Time-Aware Procedure Manager - Tracks procedure freshness
    ============================================================
    Manages procedural memory with time decay and drift detection.
    """
    
    def __init__(self):
        self.procedures: Dict[str, ProceduralMemory] = {}
        
        # Drift detection
        self.environment_drift_threshold = 0.7
        
        logger.info("⚙️ Time-Aware Procedure Manager initialized")
    
    def register_procedure(self, procedure: ProceduralMemory):
        """Register a new procedure"""
        procedure.created_at = time.time()
        procedure.last_success_at = time.time()
        
        self.procedures[procedure.procedure_id] = procedure
        
        logger.info(f"📋 Registered procedure: {procedure.name}")
    
    def record_success(self, procedure_id: str, environment: str = None):
        """Record successful procedure execution"""
        if procedure_id not in self.procedures:
            return
        
        current_time = time.time()
        proc = self.procedures[procedure_id]
        
        proc.last_success_at = current_time
        proc.last_used = current_time
        proc.usage_count += 1
        
        if environment:
            proc.environment_last_seen = environment
        
        # Update success rate
        if proc.usage_count > 0:
            proc.success_rate = (
                (proc.success_rate * (proc.usage_count - 1) + 1) / proc.usage_count
            )
        
        # Reset drift score on success
        proc.drift_score = max(0, proc.drift_score - 0.1)
    
    def record_failure(self, procedure_id: str, environment: str = None):
        """Record failed procedure execution"""
        if procedure_id not in self.procedures:
            return
        
        current_time = time.time()
        proc = self.procedures[procedure_id]
        
        proc.last_failure_at = current_time
        proc.last_used = current_time
        
        if environment and environment != proc.environment_last_seen:
            # Environment changed - increase drift
            proc.drift_score = min(1.0, proc.drift_score + 0.2)
        
        # Decrease success rate
        if proc.usage_count > 0:
            proc.success_rate = (
                proc.success_rate * proc.usage_count / (proc.usage_count + 1)
            )
    
    def calculate_decay(self, procedure_id: str) -> float:
        """Calculate procedure decay factor"""
        if procedure_id not in self.procedures:
            return 0.0
        
        proc = self.procedures[procedure_id]
        current_time = time.time()
        
        # Time since last success
        if proc.last_success_at > 0:
            days_since_success = (current_time - proc.last_success_at) / (24 * 3600)
        else:
            days_since_success = (current_time - proc.created_at) / (24 * 3600)
        
        # Base decay
        decay = 1.0
        
        # Decay by age
        if days_since_success > 30:
            decay *= 0.8
        if days_since_success > 60:
            decay *= 0.7
        if days_since_success > 90:
            decay *= 0.5
        
        # Decay by drift
        decay *= (1.0 - proc.drift_score * 0.5)
        
        # Decay by failure
        if proc.last_failure_at > 0 and proc.last_success_at > 0:
            if proc.last_failure_at > proc.last_success_at:
                decay *= 0.7
        
        return max(0.1, decay)
    
    def is_procedure_trusted(self, procedure_id: str) -> bool:
        """Check if procedure is still trusted"""
        if procedure_id not in self.procedures:
            return False
        
        proc = self.procedures[procedure_id]
        
        # Check if deprecated
        if proc.is_deprecated:
            return False
        
        # Check drift score
        if proc.drift_score > self.environment_drift_threshold:
            return False
        
        # Check decay
        decay = self.calculate_decay(procedure_id)
        if decay < 0.3:
            return False
        
        # Check success rate
        if proc.success_rate < 0.5:
            return False
        
        return True
    
    def get_procedure_health(self, procedure_id: str) -> Dict:
        """Get procedure health metrics"""
        if procedure_id not in self.procedures:
            return {}
        
        proc = self.procedures[procedure_id]
        
        return {
            "procedure_id": procedure_id,
            "success_rate": proc.success_rate,
            "drift_score": proc.drift_score,
            "decay_factor": self.calculate_decay(procedure_id),
            "is_trusted": self.is_procedure_trusted(procedure_id),
            "days_since_success": (time.time() - proc.last_success_at) / (24 * 3600),
            "is_deprecated": proc.is_deprecated
        }


# ==================== COMPREHENSIVE TIME-AWARE KNOWLEDGE MANAGER ====================

class TimeAwareKnowledgeManager:
    """
    Comprehensive Time-Aware Knowledge Manager
    ============================================
    Unifies all time-aware components for complete temporal knowledge management.
    """
    
    def __init__(self, data_dir: Path = None):
        self.data_dir = data_dir or Path(__file__).parent.parent / "data" / "temporal"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Core components
        self.knowledge_store: Dict[str, KnowledgeEntry] = {}
        self.temporal_reasoner = TemporalReasoner(self.knowledge_store)
        self.time_aware_retrieval = TimeAwareRetrieval(
            self.knowledge_store, 
            self.temporal_reasoner
        )
        self.supersession_manager = SupersessionGraphManager()
        self.volatility_engine = VolatilityEngine()
        self.preference_manager = TimeAwarePreferenceManager()
        self.procedure_manager = TimeAwareProcedureManager()
        
        # Load persisted data
        self._load_data()
        
        logger.info("🧠 Time-Aware Knowledge Manager initialized (No1+ Level)")
    
    def _load_data(self):
        """Load persisted temporal data"""
        # Load knowledge entries with temporal fields
        knowledge_file = self.data_dir / "temporal_knowledge.json"
        if knowledge_file.exists():
            try:
                with open(knowledge_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Reconstruct knowledge entries
                    logger.info(f"📂 Loaded {len(data)} temporal knowledge entries")
            except Exception as e:
                logger.error(f"Error loading temporal data: {e}")
    
    def _save_data(self):
        """Persist temporal data"""
        knowledge_file = self.data_dir / "temporal_knowledge.json"
        try:
            # Convert to JSON-serializable format
            data = {}
            for entry_id, entry in self.knowledge_store.items():
                entry_dict = {
                    "entry_id": entry.entry_id,
                    "content": entry.content,
                    "temporal_status": entry.temporal_status.value,
                    "valid_from": entry.valid_from,
                    "valid_until": entry.valid_until,
                    "is_current": entry.is_current,
                    "is_historical": entry.is_historical,
                    "volatility_class": entry.volatility_class.value,
                    "time_confidence": entry.time_confidence,
                    "drift_risk": entry.drift_risk,
                    "expiry_pressure": entry.expiry_pressure,
                    "timeline_events": entry.timeline_events
                }
                data[entry_id] = entry_dict
            
            with open(knowledge_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                
            logger.info(f"💾 Saved {len(data)} temporal knowledge entries")
        except Exception as e:
            logger.error(f"Error saving temporal data: {e}")
    
    # ==================== KNOWLEDGE OPERATIONS ====================
    
    def add_temporal_knowledge(self, entry: KnowledgeEntry) -> str:
        """Add knowledge with temporal tracking"""
        current_time = time.time()
        
        # Set temporal timestamps
        entry.observed_at = current_time
        entry.asserted_at = current_time
        entry.valid_from = current_time
        entry.verified_at = current_time
        entry.last_verified = current_time
        
        # Set initial temporal status
        entry.temporal_status = TemporalStatus.VERIFIED_CURRENT
        entry.time_scope_type = TimeScopeType.CURRENT
        entry.is_current = True
        entry.is_historical = False
        
        # Calculate initial truth clock
        clock = self.temporal_reasoner.calculate_truth_clock(entry)
        entry.time_confidence = clock.time_confidence
        entry.drift_risk = clock.drift_risk
        entry.expiry_pressure = clock.expiry_pressure
        
        # Add initial timeline event
        entry.timeline_events.append({
            "event": "observed",
            "timestamp": current_time,
            "details": {"status": "new_knowledge"}
        })
        
        # Store
        self.knowledge_store[entry.entry_id] = entry
        
        # Register version knowledge
        if entry.version_scope:
            self.temporal_reasoner.register_version_knowledge(entry)
        
        # Save
        self._save_data()
        
        logger.info(f"✅ Added temporal knowledge: {entry.entry_id}")
        return entry.entry_id
    
    def supersede_knowledge(self, old_entry_id: str, new_entry_id: str,
                           reason: str = "") -> bool:
        """Mark old knowledge as superseded by new"""
        current_time = time.time()
        
        # Get entries
        old_entry = self.knowledge_store.get(old_entry_id)
        new_entry = self.knowledge_store.get(new_entry_id)
        
        if not old_entry or not new_entry:
            logger.warning(f"⚠️ Cannot supersede: entry not found")
            return False
        
        # Update temporal reasoner
        self.temporal_reasoner.supersede(old_entry_id, new_entry_id, reason, current_time)
        
        # Update supersession manager
        self.supersession_manager.add_supersession(
            old_entry_id, new_entry_id, reason, current_time
        )
        
        # Update old entry
        old_entry.superseded_by = new_entry_id
        old_entry.superseded_at = current_time
        old_entry.temporal_status = TemporalStatus.SUPERSEDED
        old_entry.is_current = False
        old_entry.is_historical = True
        old_entry.time_scope_type = TimeScopeType.HISTORICAL
        
        # Add timeline event
        old_entry.timeline_events.append({
            "event": "superseded",
            "timestamp": current_time,
            "superseded_by": new_entry_id,
            "reason": reason
        })
        
        # Update new entry
        new_entry.supersedes = old_entry_id
        
        # Save
        self._save_data()
        
        logger.info(f"🔄 Superseded: {old_entry_id} -> {new_entry_id}")
        return True
    
    def query_with_temporal_awareness(self, query: str, 
                                       candidates: List[KnowledgeEntry] = None) -> List[Tuple[KnowledgeEntry, float]]:
        """
        Query knowledge with temporal awareness.
        
        Returns ranked list of (entry, score) tuples.
        """
        # Get temporal context from query
        temporal_context = self.temporal_reasoner.resolve_temporal_intent(query)
        
        # Use all knowledge if no candidates provided
        if candidates is None:
            candidates = list(self.knowledge_store.values())
        
        # Rank with time-aware retrieval
        results = self.time_aware_retrieval.rank_knowledge(
            query, candidates, temporal_context
        )
        
        return results
    
    def verify_knowledge(self, entry_id: str, success: bool = True):
        """Verify knowledge and update temporal metrics"""
        current_time = time.time()
        
        entry = self.knowledge_store.get(entry_id)
        if not entry:
            return
        
        # Update verification timestamps
        entry.last_verified = current_time
        entry.verified_at = current_time
        
        # Update temporal status if verified
        if success:
            if entry.temporal_status == TemporalStatus.CANDIDATE:
                entry.temporal_status = TemporalStatus.VERIFIED_CURRENT
            elif entry.temporal_status == TemporalStatus.STALE_NEEDS_CHECK:
                entry.temporal_status = TemporalStatus.VERIFIED_CURRENT
        
        # Recalculate truth clock
        clock = self.temporal_reasoner.calculate_truth_clock(entry)
        entry.time_confidence = clock.time_confidence
        entry.drift_risk = clock.drift_risk
        entry.expiry_pressure = clock.expiry_pressure
        
        # Add timeline event
        entry.timeline_events.append({
            "event": "verified",
            "timestamp": current_time,
            "success": success
        })
        
        # Save
        self._save_data()
        
        logger.info(f"✅ Verified knowledge: {entry_id}")
    
    def get_knowledge_status(self, entry_id: str) -> Dict:
        """Get comprehensive status of knowledge"""
        entry = self.knowledge_store.get(entry_id)
        if not entry:
            return {}
        
        clock = self.temporal_reasoner.calculate_truth_clock(entry)
        
        return {
            "entry_id": entry_id,
            "content": entry.content[:100] + "...",
            "temporal_status": entry.temporal_status.value,
            "is_current": entry.is_current,
            "is_historical": entry.is_historical,
            "valid_from": datetime.fromtimestamp(entry.valid_from).isoformat() if entry.valid_from else None,
            "valid_until": datetime.fromtimestamp(entry.valid_until).isoformat() if entry.valid_until else None,
            "clock": clock.to_dict(),
            "superseded_by": entry.superseded_by,
            "timeline_events": entry.timeline_events[-5:]  # Last 5 events
        }
    
    def get_expiring_knowledge(self, threshold: float = 0.7) -> List[KnowledgeEntry]:
        """Get knowledge that needs reverification"""
        expiring = []
        
        for entry in self.knowledge_store.values():
            clock = self.temporal_reasoner.calculate_truth_clock(entry)
            if clock.expiry_pressure > threshold:
                expiring.append(entry)
        
        # Sort by expiry pressure
        expiring.sort(
            key=lambda e: self.temporal_reasoner.calculate_truth_clock(e).expiry_pressure,
            reverse=True
        )
        
        return expiring
    
    def get_system_health(self) -> Dict:
        """Get overall time-aware system health"""
        total = len(self.knowledge_store)
        current = sum(1 for e in self.knowledge_store.values() if e.is_current)
        historical = sum(1 for e in self.knowledge_store.values() if e.is_historical)
        superseded = sum(1 for e in self.knowledge_store.values() 
                       if e.temporal_status == TemporalStatus.SUPERSEDED)
        
        expiring = len(self.get_expiring_knowledge())
        
        return {
            "total_knowledge": total,
            "current": current,
            "historical": historical,
            "superseded": superseded,
            "expiring_soon": expiring,
            "supersession_relations": len(self.supersession_manager.supersedes),
            "version_indexed": len(self.temporal_reasoner.version_index)
        }


# ==================== FACTORY FUNCTION ====================

def create_time_aware_knowledge_manager(data_dir: Path = None) -> TimeAwareKnowledgeManager:
    """Factory function to create TimeAwareKnowledgeManager"""
    return TimeAwareKnowledgeManager(data_dir)


# ==================== EXPORTS ====================

__all__ = [
    "TemporalStatus",
    "VolatilityClass", 
    "TimeScopeType",
    "VersionScope",
    "TruthClock",
    "TemporalReasoner",
    "TimeAwareRetrieval",
    "SupersessionGraphManager",
    "VolatilityEngine",
    "TruthTimeline",
    "TimeAwarePreferenceManager",
    "TimeAwareProcedureManager",
    "TimeAwareKnowledgeManager",
    "create_time_aware_knowledge_manager"
]
