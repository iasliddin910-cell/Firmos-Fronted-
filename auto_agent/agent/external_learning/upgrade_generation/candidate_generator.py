"""
Candidate Generator - Upgrade candidate yaratish
"""

import logging
import hashlib
from datetime import datetime
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class CandidateGenerator:
    def __init__(self):
        self.implementation_types = ["prompt", "workflow", "tool", "memory", "planner", "benchmark"]
        logger.info("Candidate Generator initialized")
    
    async def generate(self, signal: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        candidate_id = hashlib.sha256(
            f"{signal.get('signal_id')}{datetime.now().isoformat()}".encode()
        ).hexdigest()[:16]
        
        title = self._generate_title(signal)
        why_now = self._generate_why_now(signal)
        impl_type = self._determine_implementation_type(signal)
        
        candidate = {
            "candidate_id": candidate_id,
            "title": title,
            "why_now": why_now,
            "source_signals": [signal.get("signal_id", "")],
            "capabilities_affected": signal.get("mapped_capabilities", []),
            "expected_user_value": signal.get("content_summary", "")[:200],
            "implementation_type": impl_type,
            "risk_level": "medium",
            "status": "pending",
            "created_at": datetime.now().isoformat()
        }
        
        logger.info(f"Generated candidate: {candidate_id} - {title}")
        return candidate
    
    def _generate_title(self, signal: Dict[str, Any]) -> str:
        caps = signal.get("mapped_capabilities", [])
        if caps:
            return f"Enhance {caps[0].replace('_', ' ').title()}"
        return "New Feature Enhancement"
    
    def _generate_why_now(self, signal: Dict[str, Any]) -> str:
        return "External signal indicates opportunity for improvement"
    
    def _determine_implementation_type(self, signal: Dict[str, Any]) -> str:
        if signal.get("tool_mentions"):
            return "tool"
        if signal.get("workflow_innovations"):
            return "workflow"
        return "prompt"
