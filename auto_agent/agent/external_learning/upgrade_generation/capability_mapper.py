"""
Capability Mapper - Signalni capabilityga boglash
"""

import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


class CapabilityMapper:
    def __init__(self):
        self.capability_mapping = {
            "code_planning": ["planning", "reasoning", "multi-step"],
            "repo_graph": ["repo", "graph", "context"],
            "autonomous_debugging": ["debug", "fix", "repair"],
            "browser_memory": ["browser", "session", "navigation"],
            "web_research": ["research", "search", "web"],
            "tool_invention": ["tool", "create", "new capability"],
            "code_generation": ["code", "write", "generate"]
        }
        logger.info("Capability Mapper initialized")
    
    def map(self, signal: Dict[str, Any]) -> List[str]:
        capabilities = []
        content = signal.get("content_summary", "").lower()
        
        for cap, keywords in self.capability_mapping.items():
            if any(kw in content for kw in keywords):
                capabilities.append(cap)
        
        return capabilities
