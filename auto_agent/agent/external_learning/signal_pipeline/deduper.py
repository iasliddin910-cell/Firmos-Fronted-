"""
Signal Deduper - Takrorlanishlarni olib tashlash
=============================================
"""

import logging
import hashlib
from typing import Dict, List, Any, Tuple, Optional

logger = logging.getLogger(__name__)


class SignalDeduper:
    """
    Takrorlanishlarni tekshiradi va olib tashlaydi
    """
    
    def __init__(self):
        self.seen_signals: Dict[str, Dict[str, Any]] = {}
        self.content_hashes: Dict[str, str] = {}
        
        logger.info("Signal Deduper initialized")
    
    def check_duplicate(self, signal: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Signal takrorlanganmi tekshiradi
        
        Returns:
            (is_duplicate, duplicate_id)
        """
        signal_id = signal.get("signal_id", "")
        content = signal.get("content_summary", "")
        source = signal.get("source_name", "")
        source_type = signal.get("source_type", "")
        
        # Generate content hash
        content_hash = hashlib.sha256(
            f"{source_type}:{source}:{content[:200]}".encode()
        ).hexdigest()[:16]
        
        # Check if we've seen this exact content
        if content_hash in self.content_hashes:
            dup_id = self.content_hashes[content_hash]
            logger.debug(f"Duplicate found: {signal_id} -> {dup_id}")
            return True, dup_id
        
        # Store for future checks
        self.content_hashes[content_hash] = signal_id
        self.seen_signals[signal_id] = signal
        
        return False, None
    
    def increment_signal_count(self, signal_id: str):
        """Signal ko'rilganlik sonini oshirish"""
        if signal_id in self.seen_signals:
            signal = self.seen_signals[signal_id]
            signal["view_count"] = signal.get("view_count", 0) + 1
    
    def get_similarity(self, signal1: Dict[str, Any], signal2: Dict[str, Any]) -> float:
        """Ikki signal o'rtasidagi o'xshashlikni hisoblash"""
        content1 = signal1.get("content_summary", "").lower()
        content2 = signal2.get("content_summary", "").lower()
        
        if not content1 or not content2:
            return 0.0
        
        # Simple word overlap
        words1 = set(content1.split())
        words2 = set(content2.split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union)
    
    def clear(self):
        """Cacheni tozalash"""
        self.seen_signals.clear()
        self.content_hashes.clear()
        logger.info("Signal Deduper cleared")
