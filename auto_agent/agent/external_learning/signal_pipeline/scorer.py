"""
Signal Scorer - Signalni baholash
"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class SignalScorer:
    """Signalni 5 ta asosiy o'lchov bo'yicha baholaydi"""
    
    def __init__(self):
        self.credibility_weights = {
            "benchmark": 0.9,
            "docs": 0.85,
            "frontier": 0.8,
            "github": 0.75,
            "account_research": 0.7,
            "social": 0.5,
            "manual": 0.6
        }
        logger.info("Signal Scorer initialized")
    
    def score(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        credibility = self._calc_credibility(signal)
        novelty = self._calc_novelty(signal)
        relevance = self._calc_relevance(signal)
        roi = self._calc_roi(signal)
        implementability = self._calc_implementability(signal)
        
        signal["credibility_score"] = credibility
        signal["novelty_score"] = novelty
        signal["relevance_score"] = relevance
        signal["roi_score"] = roi
        signal["implementability_score"] = implementability
        
        overall = (credibility * 0.25 + novelty * 0.15 + relevance * 0.25 + roi * 0.20 + implementability * 0.15)
        signal["overall_score"] = overall
        
        return signal
    
    def _calc_credibility(self, signal: Dict[str, Any]) -> float:
        source_type = signal.get("source_type", "manual")
        base = self.credibility_weights.get(source_type, 0.5)
        confidence = signal.get("confidence", 0.5)
        evidence_links = signal.get("evidence_links", [])
        link_bonus = min(len(evidence_links) * 0.05, 0.2)
        return min(base + confidence * 0.2 + link_bonus, 1.0)
    
    def _calc_novelty(self, signal: Dict[str, Any]) -> float:
        novelty = 0.5
        emerging_topics = ["agent", "multi_agent", "planning"]
        for tag in signal.get("topic_tags", []):
            if tag in emerging_topics:
                novelty += 0.15
        return max(min(novelty, 1.0), 0.0)
    
    def _calc_relevance(self, signal: Dict[str, Any]) -> float:
        relevance = 0.5
        target_caps = ["code", "coding", "programming", "agent", "autonomous", "memory", "context", "browser", "web", "planning", "reasoning", "tool"]
        content = signal.get("content_summary", "").lower()
        matches = sum(1 for cap in target_caps if cap in content)
        relevance += matches * 0.1
        return min(relevance, 1.0)
    
    def _calc_roi(self, signal: Dict[str, Any]) -> float:
        roi = 0.5
        roi += len(signal.get("user_pain_points", [])) * 0.1
        roi += len(signal.get("workflow_innovations", [])) * 0.1
        roi += len(signal.get("tool_mentions", [])) * 0.05
        return min(roi, 1.0)
    
    def _calc_implementability(self, signal: Dict[str, Any]) -> float:
        impl = 0.6
        if signal.get("architecture_clues"):
            impl -= 0.2
        if signal.get("tool_mentions"):
            impl += 0.1
        if signal.get("performance_claims"):
            impl += 0.1
        return max(min(impl, 1.0), 0.1)
