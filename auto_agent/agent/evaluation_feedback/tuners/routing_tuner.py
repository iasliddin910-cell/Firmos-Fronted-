"""
Routing Tuner - Tuner for Tool Router Subsystem
================================================

This tuner adjusts tool routing based on benchmark feedback.

When benchmark shows:
- Wrong tool selected -> update routing weights
- Tool thrashing -> add negative priors
- Missing tools -> suggest new tool
- Task-tool mismatch -> update mappings
"""
import logging
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class ToolPreference:
    """Preference score for a tool-task pair"""
    tool_name: str
    task_type: str
    preference_score: float  # 0-1
    usage_count: int = 0
    success_rate: float = 0.5
    avg_latency_ms: float = 0.0


@dataclass
class NegativePrior:
    """Negative prior to avoid certain tool-task combinations"""
    tool_name: str
    task_type: str
    reason: str
    severity: float  # 0-1
    created_at: float = field(default_factory=time.time)


@dataclass
class RoutingAdjustment:
    """Record of a routing adjustment"""
    adjustment_id: str
    adjustment_type: str  # "weight_update", "prior_add", "mapping_update"
    target: str
    old_value: Any
    new_value: Any
    reason: str
    benchmark_evidence: Dict
    timestamp: float = field(default_factory=time.time)


class RoutingTuner:
    """
    Tuner that adjusts tool routing based on benchmark feedback.
    
    This closes the loop between benchmark results and tool selection.
    """
    
    def __init__(self):
        # Tool preferences (task_type -> tool -> preference)
        self.preferences: Dict[str, Dict[str, ToolPreference]] = defaultdict(dict)
        
        # Negative priors
        self.negative_priors: List[NegativePrior] = []
        
        # Tool-task mappings
        self.task_tool_mappings: Dict[str, List[str]] = {
            "web_search": ["browser", "curl", "search_api"],
            "file_read": ["file_reader", "grep"],
            "code_execute": ["code_interpreter", "sandbox"],
            "data_parse": ["parser", "code_interpreter"],
            "browser_automation": ["browser", "playwright"],
            "shell_command": ["terminal", "bash"]
        }
        
        # Adjustment history
        self.adjustment_history: List[RoutingAdjustment] = []
        
        # Statistics
        self.stats = {
            "total_adjustments": 0,
            "weight_updates": 0,
            "negative_priors_added": 0,
            "mappings_updated": 0
        }
        
        logger.info("🎯 RoutingTuner initialized - ADVANCED routing tuning ENABLED")
    
    def analyze_benchmark_feedback(self, benchmark_result: Dict) -> Dict:
        """
        Analyze benchmark result and determine needed routing adjustments.
        """
        suggestions = {
            "weight_updates": [],
            "negative_priors": [],
            "mapping_updates": []
        }
        
        # Extract metrics
        wrong_tool_count = benchmark_result.get("wrong_tool_count", 0)
        tool_thrash_count = benchmark_result.get("tool_thrash_count", 0)
        missing_tool_count = benchmark_result.get("missing_tool_count", 0)
        task_type = benchmark_result.get("task_type", "unknown")
        
        # Check for wrong tool selection
        if wrong_tool_count > 0:
            wrong_tools = benchmark_result.get("wrong_tools_used", [])
            correct_tools = benchmark_result.get("correct_tools", [])
            
            for wrong_tool in wrong_tools:
                suggestions["negative_priors"].append({
                    "tool": wrong_tool,
                    "task_type": task_type,
                    "reason": f"Wrong tool selected ({wrong_tool_count} times)",
                    "severity": min(1.0, wrong_tool_count * 0.2)
                })
            
            # Suggest weight updates for correct tools
            for correct_tool in correct_tools:
                suggestions["weight_updates"].append({
                    "tool": correct_tool,
                    "task_type": task_type,
                    "adjustment": 0.2,  # Increase preference
                    "reason": f"Correct tool should be preferred"
                })
        
        # Check for tool thrashing
        if tool_thrash_count > 2:
            thrashing_tools = benchmark_result.get("thrashing_tools", [])
            
            for tool in thrashing_tools:
                suggestions["negative_priors"].append({
                    "tool": tool,
                    "task_type": task_type,
                    "reason": f"Tool causing thrashing ({tool_thrash_count} retries)",
                    "severity": min(1.0, tool_thrash_count * 0.15)
                })
        
        # Check for missing tools
        if missing_tool_count > 0:
            suggestions["mapping_updates"].append({
                "task_type": task_type,
                "reason": f"Missing tool for task type ({missing_tool_count} cases)",
                "suggest_new": True
            })
        
        return suggestions
    
    def update_weight(
        self,
        tool_name: str,
        task_type: str,
        adjustment: float,
        reason: str,
        benchmark_evidence: Optional[Dict] = None
    ) -> bool:
        """Update tool preference weight"""
        # Get or create preference
        if task_type not in self.preferences:
            self.preferences[task_type] = {}
        
        if tool_name in self.preferences[task_type]:
            pref = self.preferences[task_type][tool_name]
            old_score = pref.preference_score
            new_score = max(0.0, min(1.0, old_score + adjustment))
            pref.preference_score = new_score
        else:
            self.preferences[task_type][tool_name] = ToolPreference(
                tool_name=tool_name,
                task_type=task_type,
                preference_score=0.5 + adjustment
            )
            old_score = 0.5
        
        # Record adjustment
        adjustment_record = RoutingAdjustment(
            adjustment_id=f"adj_{len(self.adjustment_history)}",
            adjustment_type="weight_update",
            target=f"{tool_name}:{task_type}",
            old_value=old_score,
            new_value=self.preferences[task_type][tool_name].preference_score,
            reason=reason,
            benchmark_evidence=benchmark_evidence or {}
        )
        self.adjustment_history.append(adjustment_record)
        self.stats["total_adjustments"] += 1
        self.stats["weight_updates"] += 1
        
        logger.info(f"🎯 Updated routing weight: {tool_name} for {task_type} = "
                   f"{self.preferences[task_type][tool_name].preference_score:.2f}")
        
        return True
    
    def add_negative_prior(
        self,
        tool_name: str,
        task_type: str,
        reason: str,
        severity: float = 0.5,
        benchmark_evidence: Optional[Dict] = None
    ) -> bool:
        """Add a negative prior to avoid a tool-task combination"""
        # Check if already exists
        for prior in self.negative_priors:
            if prior.tool_name == tool_name and prior.task_type == task_type:
                # Update existing
                prior.severity = max(prior.severity, severity)
                return False
        
        # Add new
        prior = NegativePrior(
            tool_name=tool_name,
            task_type=task_type,
            reason=reason,
            severity=severity
        )
        self.negative_priors.append(prior)
        
        # Record adjustment
        adjustment_record = RoutingAdjustment(
            adjustment_id=f"adj_{len(self.adjustment_history)}",
            adjustment_type="prior_add",
            target=f"{tool_name}:{task_type}",
            old_value=None,
            new_value=severity,
            reason=reason,
            benchmark_evidence=benchmark_evidence or {}
        )
        self.adjustment_history.append(adjustment_record)
        self.stats["total_adjustments"] += 1
        self.stats["negative_priors_added"] += 1
        
        logger.info(f"🎯 Added negative prior: {tool_name} for {task_type} "
                   f"(severity: {severity:.2f})")
        
        return True
    
    def update_task_mapping(
        self,
        task_type: str,
        recommended_tools: List[str],
        reason: str,
        benchmark_evidence: Optional[Dict] = None
    ) -> bool:
        """Update task-tool mapping"""
        old_tools = self.task_tool_mappings.get(task_type, [])
        
        # Update mapping
        self.task_tool_mappings[task_type] = recommended_tools
        
        # Record adjustment
        adjustment_record = RoutingAdjustment(
            adjustment_id=f"adj_{len(self.adjustment_history)}",
            adjustment_type="mapping_update",
            target=f"mapping:{task_type}",
            old_value=old_tools,
            new_value=recommended_tools,
            reason=reason,
            benchmark_evidence=benchmark_evidence or {}
        )
        self.adjustment_history.append(adjustment_record)
        self.stats["total_adjustments"] += 1
        self.stats["mappings_updated"] += 1
        
        logger.info(f"🎯 Updated task mapping: {task_type} -> {recommended_tools}")
        
        return True
    
    def apply_suggestions(self, suggestions: Dict) -> List[str]:
        """Apply all suggested adjustments"""
        applied = []
        
        # Apply weight updates
        for update in suggestions.get("weight_updates", []):
            self.update_weight(
                tool_name=update["tool"],
                task_type=update["task_type"],
                adjustment=update["adjustment"],
                reason=update["reason"]
            )
            applied.append(f"weight:{update['tool']}")
        
        # Apply negative priors
        for prior in suggestions.get("negative_priors", []):
            self.add_negative_prior(
                tool_name=prior["tool"],
                task_type=prior["task_type"],
                reason=prior["reason"],
                severity=prior.get("severity", 0.5)
            )
            applied.append(f"prior:{prior['tool']}")
        
        # Apply mapping updates
        for mapping in suggestions.get("mapping_updates", []):
            if mapping.get("suggest_new"):
                applied.append(f"mapping:{mapping['task_type']} - needs new tool")
        
        return applied
    
    def get_tool_for_task(self, task_type: str) -> Optional[str]:
        """Get best tool for a task type, considering preferences and negatives"""
        # Get candidates
        candidates = self.task_tool_mappings.get(task_type, [])
        
        best_tool = None
        best_score = -1.0
        
        for tool in candidates:
            # Check negative priors
            for prior in self.negative_priors:
                if prior.tool_name == tool and prior.task_type == task_type:
                    # Skip if severe negative
                    if prior.severity > 0.7:
                        continue
            
            # Get preference score
            score = 0.5  # default
            if task_type in self.preferences and tool in self.preferences[task_type]:
                score = self.preferences[task_type][tool].preference_score
            
            if score > best_score:
                best_score = score
                best_tool = tool
        
        return best_tool
    
    def get_routing_config(self) -> Dict:
        """Get current routing configuration"""
        return {
            "preferences": {
                task_type: {
                    tool: {
                        "score": pref.preference_score,
                        "usage_count": pref.usage_count,
                        "success_rate": pref.success_rate
                    }
                    for tool, pref in tools.items()
                }
                for task_type, tools in self.preferences.items()
            },
            "negative_priors": [
                {
                    "tool": p.tool_name,
                    "task_type": p.task_type,
                    "reason": p.reason,
                    "severity": p.severity
                }
                for p in self.negative_priors
            ],
            "mappings": self.task_tool_mappings,
            "stats": self.stats
        }


def create_routing_tuner() -> RoutingTuner:
    """Factory function"""
    return RoutingTuner()
