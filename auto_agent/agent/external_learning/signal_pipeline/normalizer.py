"""
Signal Normalizer - Signalni bir xil formatga keltirish
"""

import logging
from datetime import datetime
from typing import Dict, List, Any
import hashlib

logger = logging.getLogger(__name__)


class SignalNormalizer:
    """Signalni bir xil formatga keltiradi"""
    
    def __init__(self):
        self.source_type_mapping = {
            "frontier": "frontier",
            "social": "social", 
            "docs": "docs",
            "benchmark": "benchmark",
            "account_research": "account_research",
            "manual": "manual"
        }
        logger.info("Signal Normalizer initialized")
    
    def normalize(self, raw_data: Dict[str, Any], source_type: str) -> Dict[str, Any]:
        signal_id = self._generate_signal_id(raw_data, source_type)
        normalized_type = self.source_type_mapping.get(source_type, "unknown")
        
        content = self._extract_content(raw_data)
        source_name = self._extract_source(raw_data, source_type)
        evidence_links = self._extract_links(raw_data)
        timestamp = self._extract_timestamp(raw_data)
        confidence = self._extract_confidence(raw_data)
        topic_tags = self._extract_tags(content)
        
        return {
            "signal_id": signal_id,
            "source_type": normalized_type,
            "source_name": source_name,
            "timestamp": timestamp,
            "content_summary": content,
            "evidence_links": evidence_links,
            "confidence": confidence,
            "topic_tags": topic_tags,
            "raw_data": raw_data
        }
    
    def _generate_signal_id(self, raw_data: Dict[str, Any], source_type: str) -> str:
        content = str(raw_data.get("content", ""))
        source = str(raw_data.get("source", ""))
        id_string = f"{source_type}{source}{content}{datetime.now().isoformat()}"
        return hashlib.sha256(id_string.encode()).hexdigest()[:16]
    
    def _extract_content(self, raw_data: Dict[str, Any]) -> str:
        for field in ["content", "text", "description", "title", "body"]:
            if field in raw_data and raw_data[field]:
                return str(raw_data[field])[:2000]
        return str(raw_data)
    
    def _extract_source(self, raw_data: Dict[str, Any], source_type: str) -> str:
        for field in ["source", "source_name", "platform", "author", "account"]:
            if field in raw_data and raw_data[field]:
                return str(raw_data[field])
        return source_type
    
    def _extract_links(self, raw_data: Dict[str, Any]) -> List[str]:
        links = []
        if "url" in raw_data and raw_data["url"]:
            links.append(str(raw_data["url"]))
        if "urls" in raw_data and isinstance(raw_data["urls"], list):
            links.extend([str(u) for u in raw_data["urls"]])
        return list(set(links))[:10]
    
    def _extract_timestamp(self, raw_data: Dict[str, Any]) -> datetime:
        for field in ["timestamp", "created_at", "date", "time"]:
            if field in raw_data and raw_data[field]:
                try:
                    if isinstance(raw_data[field], str):
                        return datetime.fromisoformat(raw_data[field].replace("Z", "+00:00"))
                except:
                    pass
        return datetime.now()
    
    def _extract_confidence(self, raw_data: Dict[str, Any]) -> float:
        for field in ["confidence", "score", "reliability"]:
            if field in raw_data:
                try:
                    return float(raw_data[field])
                except:
                    pass
        return 0.5
    
    def _extract_tags(self, content: str) -> List[str]:
        tags = []
        content_lower = content.lower()
        topic_keywords = {
            "coding": ["code", "programming", "developer", "coding", "function"],
            "agent": ["agent", "autonomous", "assistant"],
            "memory": ["memory", "context", "long context"],
            "benchmark": ["benchmark", "swe-bench", "humaneval"],
            "tool": ["tool", "function", "capability"],
            "browser": ["browser", "web", "scrape"],
            "planning": ["plan", "reasoning"],
            "multi_agent": ["multi", "agent", "orchestrat"]
        }
        for topic, keywords in topic_keywords.items():
            if any(kw in content_lower for kw in keywords):
                tags.append(topic)
        return list(set(tags))
