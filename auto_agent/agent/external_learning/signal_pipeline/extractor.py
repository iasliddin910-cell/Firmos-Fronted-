"""
Signal Extractor - Signaldan asosiy ma'lumotlarni ajratib olish
===========================================================
"""

import logging
import re
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


class SignalExtractor:
    """
    Signaldan asosiy ma'lumotlarni ajratib oladi:
    - Capability mentions
    - User pain points
    - Workflow innovations
    - Tool mentions
    - Architecture clues
    - Performance claims
    """
    
    def __init__(self):
        # Extraction patterns
        self.capability_patterns = [
            r"\b(code|coding|program)\b.*\b(generation|write|create)\b",
            r"\b(reasoning|think|reason)\b",
            r"\b(memory|context|window)\b",
            r"\b(tool|function|capability)\b",
            r"\b(browse|web|scrape)\b",
            r"\b(agent|autonomous|auto)\b",
            r"\b(plan|planning|reason)\b",
            r"\b(debug|fix|repair)\b",
            r"\b(test|testing)\b",
            r"\b(refactor|optimize)\b"
        ]
        
        self.pain_patterns = [
            r"\b(not working|doesn't work|broken|failed)\b",
            r"\b(error|bug|issue|problem)\b",
            r"\b(frustrat|annoying|slow)\b",
            r"\b(can't|unable|cannot)\b.*\b(do|make|use)\b",
            r"\b(hallucin|wrong|incorrect)\b",
            r"\b(context|memory).*?(lost|forget|limit)\b"
        ]
        
        self.workflow_patterns = [
            r"\b(multi-step|chain|pipeline)\b",
            r"\b(parallel|concurrent)\b",
            r"\b(orchestrat|coordinat)\b",
            r"\b(workflow|autonomous)\b",
            r"\b(iterat|loop|repeat)\b"
        ]
        
        self.tool_patterns = [
            r"\b(new|add|create).*?tool",
            r"\b(tool|capability).*?(add|new|enabled)\b",
            r"\b(function|call|api)\b"
        ]
        
        self.architecture_patterns = [
            r"\b(moe|mixture of expert)\b",
            r"\b(memory.*layer|cache)\b",
            r"\b(graph|vector|embed)\b",
            r"\b(parallel|speculative)\b"
        ]
        
        self.performance_patterns = [
            r"\b(faster|quicker|speed)\b",
            r"\b(cheaper| cheaper|low.*cost)\b",
            r"\b(accuracy|performance|score)\b.*?\d+%?",
            r"\b(improv|enhanc|boost)\b"
        ]
        
        logger.info("Signal Extractor initialized")
    
    def extract(self, normalized_signal: Dict[str, Any]) -> Dict[str, Any]:
        """Signaldan ma'lumotlarni ajratib olish"""
        content = normalized_signal.get("content_summary", "")
        
        # Extract capabilities
        capabilities = self._extract_patterns(content, self.capability_patterns)
        
        # Extract pain points
        pain_points = self._extract_patterns(content, self.pain_patterns)
        
        # Extract workflow innovations
        workflows = self._extract_patterns(content, self.workflow_patterns)
        
        # Extract tool mentions
        tools = self._extract_patterns(content, self.tool_patterns)
        
        # Extract architecture clues
        architecture = self._extract_patterns(content, self.architecture_patterns)
        
        # Extract performance claims
        performance = self._extract_patterns(content, self.performance_patterns)
        
        # Add to signal
        normalized_signal["capability_mentions"] = capabilities
        normalized_signal["user_pain_points"] = pain_points
        normalized_signal["workflow_innovations"] = workflows
        normalized_signal["tool_mentions"] = tools
        normalized_signal["architecture_clues"] = architecture
        normalized_signal["performance_claims"] = performance
        
        logger.debug(f"Extracted: {len(capabilities)} capabilities, {len(pain_points)} pain points")
        
        return normalized_signal
    
    def _extract_patterns(self, content: str, patterns: List[str]) -> List[str]:
        """Pattern bo'yicha matndan ma'lumot olish"""
        results = []
        content_lower = content.lower()
        
        for pattern in patterns:
            match = re.search(pattern, content_lower)
            if match:
                results.append(match.group())
        
        return list(set(results))
