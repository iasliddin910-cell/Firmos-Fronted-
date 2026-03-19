"""
ROI Ranker - Candidate larni ROI bo'yicha saralash
"""

import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class ROIRanker:
    def __init__(self):
        self.candidates: Dict[str, Dict[str, Any]] = {}
        logger.info("ROI Ranker initialized")
    
    def add_candidate(self, candidate: Dict[str, Any]):
        cid = candidate.get("candidate_id")
        if cid:
            self.candidates[cid] = candidate
    
    def get_candidates(self, status: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        cands = list(self.candidates.values())
        if status:
            cands = [c for c in cands if c.get("status") == status]
        return sorted(cands, key=lambda x: x.get("priority_score", 0), reverse=True)[:limit]
    
    def update_status(self, candidate_id: str, new_status: str, reason: str = "") -> bool:
        if candidate_id in self.candidates:
            self.candidates[candidate_id]["status"] = new_status
            if reason:
                self.candidates[candidate_id]["status_reason"] = reason
            return True
        return False
