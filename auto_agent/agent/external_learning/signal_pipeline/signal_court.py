"""
Signal Court - Signalni qaror qilish
"""

import logging
from typing import Dict, Any, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


class SignalDecision(Enum):
    ADOPT_NOW = "adopt_now"
    RESEARCH_MORE = "research_more"
    WATCHLIST = "watchlist"
    REJECT_HYPE = "reject_hype"


class SignalCourt:
    def __init__(self):
        self.adopt_threshold = 0.75
        self.research_threshold = 0.5
        self.watchlist_threshold = 0.35
        self.min_evidence_types = 2
        logger.info("Signal Court initialized")
    
    def judge(self, signal: Dict[str, Any]) -> Tuple[SignalDecision, str]:
        overall = signal.get("overall_score", 0.0)
        evidence_count = self._count_evidence_types(signal)
        
        if self._is_hype(signal):
            return SignalDecision.REJECT_HYPE, "Hype signal"
        
        if evidence_count < self.min_evidence_types:
            if overall >= self.adopt_threshold:
                return SignalDecision.RESEARCH_MORE, "Need more evidence"
        
        if overall >= self.adopt_threshold and evidence_count >= self.min_evidence_types:
            return SignalDecision.ADOPT_NOW, f"High quality with {evidence_count} evidence"
        
        if overall >= self.research_threshold:
            return SignalDecision.RESEARCH_MORE, "Need more research"
        
        if overall >= self.watchlist_threshold:
            return SignalDecision.WATCHLIST, "Worth monitoring"
        
        return SignalDecision.REJECT_HYPE, "Low quality"
    
    def _count_evidence_types(self, signal: Dict[str, Any]) -> int:
        count = 0
        if signal.get("capability_mentions"): count += 1
        if signal.get("user_pain_points"): count += 1
        if signal.get("workflow_innovations"): count += 1
        if signal.get("tool_mentions"): count += 1
        if signal.get("architecture_clues"): count += 1
        if signal.get("performance_claims"): count += 1
        if signal.get("evidence_links"): count += 1
        return count
    
    def _is_hype(self, signal: Dict[str, Any]) -> bool:
        content = signal.get("content_summary", "").lower()
        hype_keywords = ["revolutionary", "game changer", "breakthrough"]
        hype_count = sum(1 for kw in hype_keywords if kw in content)
        if hype_count >= 2 and signal.get("credibility_score", 0) < 0.5:
            return True
        if signal.get("source_type") == "social" and self._count_evidence_types(signal) < 2:
            return True
        return False
