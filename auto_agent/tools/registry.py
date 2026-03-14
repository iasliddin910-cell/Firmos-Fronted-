"""Tool Registry"""
from enum import Enum

class RiskLevel(Enum):
    SAFE = "safe"
    MEDIUM = "medium"
    DANGEROUS = "dangerous"
    BLOCKED = "blocked"

class ToolRegistry:
    def __init__(self):
        self.tools = {
            "think": {"args": {"question": str}},
            "read_file": {"args": {"path": str}},
            "write_file": {"args": {"path": str, "content": str}},
            "execute_code": {"args": {"code": str}},
            "execute_command": {"args": {"command": str}, "risk": RiskLevel.DANGEROUS},
            "web_search": {"args": {"query": str}},
            "screenshot": {"args": {}},
            "get_system_info": {"args": {}},
        }
    
    def get(self, name):
        return self.tools.get(name)

registry = ToolRegistry()
