"""Safety Governor - Risk Engine"""
from enum import Enum

class RiskLevel(Enum):
    SAFE = "safe"
    MEDIUM = "medium"
    DANGEROUS = "dangerous"
    BLOCKED = "blocked"

class RiskEngine:
    def __init__(self):
        self.denylist = ["rm -rf /", "format", "del /"]
    
    def evaluate(self, tool, args):
        if tool == "execute_command":
            cmd = str(args.get("command", "")).lower()
            for p in self.denylist:
                if p in cmd:
                    return RiskLevel.BLOCKED
            return RiskLevel.DANGEROUS
        return RiskLevel.SAFE
    
    def should_block(self, risk):
        return risk == RiskLevel.BLOCKED

risk_engine = RiskEngine()
