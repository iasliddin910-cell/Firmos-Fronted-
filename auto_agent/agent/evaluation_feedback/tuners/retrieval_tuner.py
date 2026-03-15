"""
Retrieval Tuner - Tuner for Memory/Retrieval Subsystem
================================================

This tuner adjusts retrieval parameters based on benchmark feedback.

When benchmark shows:
- Irrelevant files returned -> adjust relevance weights
- Late discovery of correct files -> adjust ranking
- Repeated rediscovery -> improve caching
- Wrong file selection -> adjust priors
"""
import logging
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class RetrievalWeight:
    """Weight configuration for retrieval"""
    weight_name: str
    value: float  # 0-1
    adjust_count: int = 0


@dataclass
class RetrievalPriors:
    """Prior beliefs about file relevance"""
    pattern: str  # regex or path pattern
    priority: float  # 0-1
    reason: str


@dataclass
class RetrievalAdjustment:
    """Record of a retrieval adjustment"""
    adjustment_id: str
    adjustment_type: str
    target: str
    old_value: Any
    new_value: Any
    reason: str
    benchmark_evidence: Dict
    timestamp: float = field(default_factory=time.time)


class RetrievalTuner:
    """
    Tuner that adjusts retrieval parameters based on benchmark feedback.
    
    This closes the loop between benchmark results and memory retrieval.
    """
    
    def __init__(self):
        # Retrieval weights
        self.weights = {
            "relevance": RetrievalWeight("relevance", 0.5),
            "recency": RetrievalWeight("recency", 0.2),
            "frequency": RetrievalWeight("frequency", 0.15),
            "path_match": RetrievalWeight("path_match", 0.15),
            "symbol_match": RetrievalWeight("symbol_match", 0.3),
            "file_type_match": RetrievalWeight("file_type_match", 0.1)
        }
        
        # Prior beliefs
        self.priors: List[RetrievalPriors] = []
        
        # Bad patterns to suppress
        self.bad_patterns: Dict[str, float] = {}  # pattern -> suppression strength
        
        # Adjustment history
        self.adjustment_history: List[RetrievalAdjustment] = []
        
        # Statistics
        self.stats = {
            "total_adjustments": 0,
            "weight_updates": 0,
            "prior_added": 0,
            "bad_patterns_added": 0
        }
        
        logger.info("🎯 RetrievalTuner initialized - ADVANCED retrieval tuning ENABLED")
    
    def analyze_benchmark_feedback(self, benchmark_result: Dict) -> Dict:
        """
        Analyze benchmark result and determine needed retrieval adjustments.
        """
        suggestions = {
            "weight_updates": [],
            "prior_adds": [],
            "bad_patterns": []
        }
        
        # Extract metrics
        irrelevant_count = benchmark_result.get("irrelevant_file_count", 0)
        late_discovery_count = benchmark_result.get("late_discovery_count", 0)
        rediscovery_count = benchmark_result.get("rediscovery_count", 0)
        wrong_file_count = benchmark_result.get("wrong_file_count", 0)
        
        # Check for irrelevant files
        if irrelevant_count > 2:
            irrelevant_files = benchmark_result.get("irrelevant_files", [])
            
            # Increase relevance weight
            suggestions["weight_updates"].append({
                "weight": "relevance",
                "adjustment": min(0.2, irrelevant_count * 0.05),
                "reason": f"Too many irrelevant files ({irrelevant_count})"
            })
            
            # Add bad patterns from irrelevant files
            for fpath in irrelevant_files[:3]:
                suggestions["bad_patterns"].append({
                    "pattern": fpath,
                    "suppression": min(1.0, irrelevant_count * 0.1),
                    "reason": f"File returned incorrectly: {fpath}"
                })
        
        # Check for late discovery
        if late_discovery_count > 0:
            suggestions["weight_updates"].append({
                "weight": "path_match",
                "adjustment": 0.1,
                "reason": f"Correct files discovered late ({late_discovery_count})"
            })
            suggestions["weight_updates"].append({
                "weight": "symbol_match",
                "adjustment": 0.1,
                "reason": "Need better symbol-based ranking"
            })
        
        # Check for rediscovery
        if rediscovery_count > 2:
            suggestions["weight_updates"].append({
                "weight": "recency",
                "adjustment": 0.1,
                "reason": f"Files being rediscovered ({rediscovery_count} times)"
            })
        
        # Check for wrong file selection
        if wrong_file_count > 0:
            wrong_files = benchmark_result.get("wrong_files", [])
            
            # Add priors for correct file types
            correct_patterns = benchmark_result.get("correct_file_patterns", [])
            for pattern in correct_patterns:
                suggestions["prior_adds"].append({
                    "pattern": pattern,
                    "priority": 0.8,
                    "reason": f"Correct file pattern: {pattern}"
                })
        
        return suggestions
    
    def adjust_weight(
        self,
        weight_name: str,
        adjustment: float,
        reason: str,
        benchmark_evidence: Optional[Dict] = None
    ) -> bool:
        """Adjust a retrieval weight"""
        if weight_name not in self.weights:
            logger.warning(f"⚠️ Unknown weight: {weight_name}")
            return False
        
        weight = self.weights[weight_name]
        old_value = weight.value
        new_value = max(0.0, min(1.0, old_value + adjustment))
        
        weight.value = new_value
        weight.adjust_count += 1
        
        # Record adjustment
        adjustment_record = RetrievalAdjustment(
            adjustment_id=f"adj_{len(self.adjustment_history)}",
            adjustment_type="weight_update",
            target=weight_name,
            old_value=old_value,
            new_value=new_value,
            reason=reason,
            benchmark_evidence=benchmark_evidence or {}
        )
        self.adjustment_history.append(adjustment_record)
        self.stats["total_adjustments"] += 1
        self.stats["weight_updates"] += 1
        
        logger.info(f"🎯 Adjusted retrieval weight: {weight_name} = {new_value:.2f} "
                   f"(was {old_value:.2f})")
        
        return True
    
    def add_prior(
        self,
        pattern: str,
        priority: float,
        reason: str,
        benchmark_evidence: Optional[Dict] = None
    ) -> bool:
        """Add a prior belief"""
        # Check if exists
        for prior in self.priors:
            if prior.pattern == pattern:
                prior.priority = max(prior.priority, priority)
                return False
        
        # Add new
        prior = RetrievalPriors(
            pattern=pattern,
            priority=priority,
            reason=reason
        )
        self.priors.append(prior)
        
        # Record
        adjustment_record = RetrievalAdjustment(
            adjustment_id=f"adj_{len(self.adjustment_history)}",
            adjustment_type="prior_add",
            target=pattern,
            old_value=None,
            new_value=priority,
            reason=reason,
            benchmark_evidence=benchmark_evidence or {}
        )
        self.adjustment_history.append(adjustment_record)
        self.stats["total_adjustments"] += 1
        self.stats["prior_added"] += 1
        
        logger.info(f"🎯 Added retrieval prior: {pattern} = {priority:.2f}")
        
        return True
    
    def add_bad_pattern(
        self,
        pattern: str,
        suppression: float,
        reason: str,
        benchmark_evidence: Optional[Dict] = None
    ) -> bool:
        """Add a pattern to suppress"""
        self.bad_patterns[pattern] = suppression
        
        # Record
        adjustment_record = RetrievalAdjustment(
            adjustment_id=f"adj_{len(self.adjustment_history)}",
            adjustment_type="bad_pattern_add",
            target=pattern,
            old_value=None,
            new_value=suppression,
            reason=reason,
            benchmark_evidence=benchmark_evidence or {}
        )
        self.adjustment_history.append(adjustment_record)
        self.stats["total_adjustments"] += 1
        self.stats["bad_patterns_added"] += 1
        
        logger.info(f"🎯 Added bad pattern suppression: {pattern} = {suppression:.2f}")
        
        return True
    
    def apply_suggestions(self, suggestions: Dict) -> List[str]:
        """Apply all suggested adjustments"""
        applied = []
        
        # Apply weight updates
        for update in suggestions.get("weight_updates", []):
            self.adjust_weight(
                weight_name=update["weight"],
                adjustment=update["adjustment"],
                reason=update["reason"]
            )
            applied.append(f"weight:{update['weight']}")
        
        # Apply prior adds
        for prior in suggestions.get("prior_adds", []):
            self.add_prior(
                pattern=prior["pattern"],
                priority=prior["priority"],
                reason=prior["reason"]
            )
            applied.append(f"prior:{prior['pattern']}")
        
        # Apply bad patterns
        for pattern in suggestions.get("bad_patterns", []):
            self.add_bad_pattern(
                pattern=pattern["pattern"],
                suppression=pattern["suppression"],
                reason=pattern["reason"]
            )
            applied.append(f"bad_pattern:{pattern['pattern']}")
        
        return applied
    
    def get_retrieval_config(self) -> Dict:
        """Get current retrieval configuration"""
        return {
            "weights": {
                name: {
                    "value": w.value,
                    "adjust_count": w.adjust_count
                }
                for name, w in self.weights.items()
            },
            "priors": [
                {
                    "pattern": p.pattern,
                    "priority": p.priority,
                    "reason": p.reason
                }
                for p in self.priors
            ],
            "bad_patterns": self.bad_patterns,
            "stats": self.stats
        }


def create_retrieval_tuner() -> RetrievalTuner:
    """Factory function"""
    return RetrievalTuner()
