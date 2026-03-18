"""
Tool ROI Analyzer - Tool Efficiency Analysis
===========================================

This module analyzes tool efficiency and ROI:
- Average cost per tool
- Success uplift
- Latency
- Failure rate
- Best-fit task types
- Replacement scores

Author: No1 World+ Autonomous System
"""

import asyncio
import logging
import threading
import time
from typing import Dict, List, Optional, Any, Callable, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from collections import defaultdict, deque
import statistics
import json

logger = logging.getLogger(__name__)


# ==================== ENUMS ====================

class ToolCategory(str, Enum):
    """Tool categories"""
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    BROWSER = "browser"
    SEARCH = "search"
    ANALYSIS = "analysis"
    REPAIR = "repair"


class ToolEfficiency(str, Enum):
    """Tool efficiency rating"""
    EXCELLENT = "excellent"
    GOOD = "good"
    AVERAGE = "average"
    POOR = "poor"


# ==================== DATA CLASSES ====================

@dataclass
class ToolMetrics:
    """Metrics for a single tool"""
    tool_id: str
    category: ToolCategory
    
    # Usage stats
    total_uses: int
    successful_uses: int
    failed_uses: int
    
    # Performance
    avg_latency_ms: float
    median_latency_ms: float
    p95_latency_ms: float
    
    # Cost
    avg_tokens: int
    avg_cost: float
    total_cost: float
    
    # Success
    success_rate: float
    
    # Task fit
    best_task_types: List[str]
    task_type_distribution: Dict[str, int]


@dataclass
class ToolROI:
    """ROI calculation for a tool"""
    tool_id: str
    
    # Raw metrics
    success_rate: float
    avg_latency_ms: float
    avg_cost: float
    
    # Efficiency scores
    efficiency_score: float      # 0-100
    speed_score: float           # 0-100
    cost_score: float            # 0-100
    reliability_score: float    # 0-100
    
    # Uplift
    success_uplift: float       # How much this tool helps vs baseline
    time_saved_ms: float        # vs average
    
    # Recommendation
    recommendation: str          # "use", "use_sparingly", "replace", "avoid"
    replacement_candidates: List[str]


@dataclass
class ToolComparison:
    """Comparison between tools"""
    task_type: str
    tools_ranked: List[Tuple[str, float]]  # tool_id, score
    recommended: str
    alternatives: List[str]


# ==================== TOOL ANALYZER ====================

class ToolAnalyzer:
    """Analyzes individual tool performance"""
    
    def __init__(self, tool_id: str, category: ToolCategory):
        self.tool_id = tool_id
        self.category = category
        
        self._lock = threading.Lock()
        
        # Raw data
        self._latencies: deque = deque(maxlen=1000)
        self._costs: deque = deque(maxlen=1000)
        self._results: deque = deque(maxlen=1000)  # True/False
        self._task_types: Dict[str, int] = defaultdict(int)
    
    def record_use(self, success: bool, latency_ms: float, cost: float, 
                  task_type: str, tokens: int = 0):
        """Record a tool use"""
        with self._lock:
            self._latencies.append(latency_ms)
            self._costs.append(cost)
            self._results.append(success)
            self._task_types[task_type] += 1
    
    def get_metrics(self) -> ToolMetrics:
        """Get current metrics"""
        with self._lock:
            if not self._results:
                return ToolMetrics(
                    tool_id=self.tool_id,
                    category=self.category,
                    total_uses=0,
                    successful_uses=0,
                    failed_uses=0,
                    avg_latency_ms=0,
                    median_latency_ms=0,
                    p95_latency_ms=0,
                    avg_tokens=0,
                    avg_cost=0,
                    total_cost=0,
                    success_rate=0,
                    best_task_types=[],
                    task_type_distribution={}
                )
            
            successes = sum(1 for r in self._results if r)
            failures = len(self._results) - successes
            
            latencies = list(self._latencies)
            costs = list(self._costs)
            
            return ToolMetrics(
                tool_id=self.tool_id,
                category=self.category,
                total_uses=len(self._results),
                successful_uses=successes,
                failed_uses=failures,
                avg_latency_ms=statistics.mean(latencies),
                median_latency_ms=statistics.median(latencies),
                p95_latency_ms=sorted(latencies)[int(len(latencies) * 0.95)] if latencies else 0,
                avg_tokens=0,  # Would track separately
                avg_cost=statistics.mean(costs),
                total_cost=sum(costs),
                success_rate=successes / len(self._results),
                best_task_types=self._get_best_task_types(),
                task_type_distribution=dict(self._task_types)
            )
    
    def _get_best_task_types(self) -> List[str]:
        """Get task types where this tool performs best"""
        if not self._task_types:
            return []
        
        # Sort by count
        sorted_types = sorted(self._task_types.items(), key=lambda x: x[1], reverse=True)
        return [t[0] for t in sorted_types[:3]]


# ==================== TOOL ROI ANALYZER ====================

class ToolROIAnalyzer:
    """
    Tool ROI analysis system.
    
    Features:
    - Per-tool metrics tracking
    - Success rate analysis
    - Latency analysis
    - Cost analysis
    - ROI scoring
    - Replacement recommendations
    - Task-specific recommendations
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self._config = config or {}
        
        # Tool analyzers
        self._analyzers: Dict[str, ToolAnalyzer] = {}
        self._category_analyzers: Dict[ToolCategory, Dict[str, ToolAnalyzer]] = defaultdict(dict)
        
        # Baselines for comparison
        self._baselines = {
            "success_rate": 0.7,
            "avg_latency_ms": 2000,
            "avg_cost": 0.01
        }
        
        # Callbacks
        self._on_low_efficiency: Optional[Callable] = None
    
    def set_callbacks(self, on_low_efficiency: Optional[Callable] = None):
        """Set callback functions"""
        self._on_low_efficiency = on_low_efficiency
    
    # ==================== REGISTRATION ====================
    
    def register_tool(self, tool_id: str, category: ToolCategory):
        """Register a tool for tracking"""
        if tool_id not in self._analyzers:
            self._analyzers[tool_id] = ToolAnalyzer(tool_id, category)
            self._category_analyzers[category][tool_id] = self._analyzers[tool_id]
            logger.info(f"Registered tool: {tool_id} ({category.value})")
    
    # ==================== RECORDING ====================
    
    def record_tool_use(self, tool_id: str, task_type: str, success: bool,
                       latency_ms: float, cost: float = 0, tokens: int = 0):
        """Record a tool use"""
        
        # Auto-register if not seen before
        if tool_id not in self._analyzers:
            self.register_tool(tool_id, ToolCategory.EXECUTE)  # Default
        
        self._analyzers[tool_id].record_use(success, latency_ms, cost, task_type, tokens)
    
    # ==================== ANALYSIS ====================
    
    def analyze_tool(self, tool_id: str) -> Optional[ToolROI]:
        """Analyze ROI for a specific tool"""
        
        if tool_id not in self._analyzers:
            return None
        
        metrics = self._analyzers[tool_id].get_metrics()
        
        # Calculate scores
        speed_score = self._calculate_speed_score(metrics.avg_latency_ms)
        cost_score = self._calculate_cost_score(metrics.avg_cost)
        reliability_score = self._calculate_reliability_score(metrics.success_rate)
        
        # Overall efficiency
        efficiency = (speed_score * 0.3 + cost_score * 0.3 + reliability_score * 0.4)
        
        # Success uplift
        success_uplift = metrics.success_rate - self._baselines["success_rate"]
        
        # Time saved
        time_saved_ms = self._baselines["avg_latency_ms"] - metrics.avg_latency_ms
        
        # Recommendation
        recommendation = self._get_recommendation(efficiency, reliability_score)
        
        # Find replacement candidates
        replacements = self._find_replacements(tool_id, metrics.category)
        
        return ToolROI(
            tool_id=tool_id,
            success_rate=metrics.success_rate,
            avg_latency_ms=metrics.avg_latency_ms,
            avg_cost=metrics.avg_cost,
            efficiency_score=efficiency,
            speed_score=speed_score,
            cost_score=cost_score,
            reliability_score=reliability_score,
            success_uplift=success_uplift,
            time_saved_ms=time_saved_ms,
            recommendation=recommendation,
            replacement_candidates=replacements
        )
    
    def analyze_all_tools(self) -> Dict[str, ToolROI]:
        """Analyze all tools"""
        return {
            tool_id: self.analyze_tool(tool_id)
            for tool_id in self._analyzers.keys()
            if self.analyze_tool(tool_id) is not None
        }
    
    def analyze_category(self, category: ToolCategory) -> List[ToolROI]:
        """Analyze tools in a category"""
        tools = []
        
        for tool_id, analyzer in self._category_analyzers[category].items():
            roi = self.analyze_tool(tool_id)
            if roi:
                tools.append(roi)
        
        return sorted(tools, key=lambda x: x.efficiency_score, reverse=True)
    
    # ==================== SCORING ====================
    
    def _calculate_speed_score(self, latency_ms: float) -> float:
        """Calculate speed score (0-100)"""
        if latency_ms == 0:
            return 100
        
        # Exponential decay based on latency
        baseline = self._baselines["avg_latency_ms"]
        
        if latency_ms <= baseline:
            return 100 * (1 - latency_ms / (baseline * 1.5))
        else:
            return max(0, 100 * (baseline / latency_ms))
    
    def _calculate_cost_score(self, cost: float) -> float:
        """Calculate cost score (0-100)"""
        if cost == 0:
            return 100
        
        baseline = self._baselines["avg_cost"]
        
        if cost <= baseline:
            return 100 * (1 - cost / (baseline * 2))
        else:
            return max(0, 100 * (baseline / cost))
    
    def _calculate_reliability_score(self, success_rate: float) -> float:
        """Calculate reliability score (0-100)"""
        return success_rate * 100
    
    def _get_recommendation(self, efficiency: float, reliability: float) -> str:
        """Get recommendation based on scores"""
        
        if efficiency >= 80 and reliability >= 90:
            return "use"
        elif efficiency >= 60 and reliability >= 70:
            return "use_sparingly"
        elif efficiency >= 40:
            return "replace"
        else:
            return "avoid"
    
    def _find_replacements(self, tool_id: str, category: ToolCategory) -> List[str]:
        """Find potential replacement tools"""
        
        category_tools = self.analyze_category(category)
        
        # Find better alternatives
        current_roi = self.analyze_tool(tool_id)
        
        if not current_roi:
            return []
        
        replacements = [
            t.tool_id for t in category_tools 
            if t.efficiency_score > current_roi.efficiency_score
        ][:3]  # Top 3
        
        return replacements
    
    # ==================== COMPARISON ====================
    
    def compare_for_task(self, task_type: str) -> ToolComparison:
        """Compare tools for a specific task type"""
        
        tool_scores = []
        
        for tool_id, analyzer in self._analyzers.items():
            metrics = analyzer.get_metrics()
            
            if metrics.task_type_distribution.get(task_type, 0) > 0:
                # Has been used for this task type
                roi = self.analyze_tool(tool_id)
                if roi:
                    # Score based on efficiency and task fit
                    task_count = metrics.task_type_distribution[task_type]
                    score = roi.efficiency_score * (1 + task_count / 100)
                    tool_scores.append((tool_id, score))
        
        # Sort by score
        tool_scores.sort(key=lambda x: x[1], reverse=True)
        
        recommended = tool_scores[0][0] if tool_scores else ""
        alternatives = [t[0] for t in tool_scores[1:4]]
        
        return ToolComparison(
            task_type=task_type,
            tools_ranked=tool_scores,
            recommended=recommended,
            alternatives=alternatives
        )
    
    def get_best_tool_for_category(self, category: ToolCategory) -> Optional[str]:
        """Get best tool for a category"""
        
        tools = self.analyze_category(category)
        
        if not tools:
            return None
        
        return tools[0].tool_id
    
    # ==================== BASELINES ====================
    
    def update_baselines(self, success_rate: Optional[float] = None,
                        latency_ms: Optional[float] = None,
                        cost: Optional[float] = None):
        """Update baseline values"""
        
        if success_rate is not None:
            self._baselines["success_rate"] = success_rate
        if latency_ms is not None:
            self._baselines["avg_latency_ms"] = latency_ms
        if cost is not None:
            self._baselines["avg_cost"] = cost
    
    # ==================== EXPORT ====================
    
    def export_metrics(self) -> Dict:
        """Export all metrics"""
        return {
            tool_id: analyzer.get_metrics().__dict__
            for tool_id, analyzer in self._analyzers.items()
        }
    
    def get_efficiency_report(self) -> Dict:
        """Get efficiency report"""
        
        all_roi = self.analyze_all_tools()
        
        # Group by recommendation
        grouped = defaultdict(list)
        for tool_id, roi in all_roi.items():
            grouped[roi.recommendation].append(tool_id)
        
        return {
            "total_tools": len(all_roi),
            "excellent_tools": len([r for r in all_roi.values() if r.efficiency_score >= 80]),
            "poor_tools": len([r for r in all_roi.values() if r.efficiency_score < 40]),
            "by_recommendation": dict(grouped),
            "avg_efficiency": statistics.mean([r.efficiency_score for r in all_roi.values()]) if all_roi else 0
        }


# ==================== FACTORY ====================

def create_tool_roi_analyzer(config: Optional[Dict] = None) -> ToolROIAnalyzer:
    """Factory function to create tool ROI analyzer"""
    return ToolROIAnalyzer(config=config)
