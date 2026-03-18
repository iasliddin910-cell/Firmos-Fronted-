"""
Swarm Economist - Parallelism Decision Engine
==========================================

This module decides when parallelism is beneficial:
- Solo recommended
- Duo recommended
- Full swarm recommended
- Serialize fallback

Author: No1 World+ Autonomous System
"""

import asyncio
import logging
import random
from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


# ==================== ENUMS ====================

class ParallelismStrategy(str, Enum):
    """Parallelism strategies"""
    SOLO = "solo"              # Single agent
    DUO = "duo"               # 2 agents
    SWARM = "swarm"           # Multiple agents
    SERIALIZE = "serialize"   # Sequential execution


# ==================== DATA CLASSES ====================

@dataclass
class SwarmRecommendation:
    """Recommendation for parallelism"""
    task_id: str
    strategy: ParallelismStrategy
    recommended_agents: int
    estimated_speedup: float
    estimated_cost: float
    estimated_success_boost: float
    confidence: float
    reasoning: str


@dataclass
class SwarmMetrics:
    """Metrics for swarm performance"""
    task_id: str
    strategy: ParallelismStrategy
    agents_used: int
    duration_seconds: float
    cost: float
    success: bool


# ==================== SWARM ECONOMIST ====================

class SwarmEconomist:
    """
    Parallelism decision engine.
    
    Decides when to use:
    - Solo execution
    - Duo (2 agents)
    - Full swarm
    - Serialize (sequential)
    
    Based on:
    - Task complexity
    - Task type
    - Time constraints
    - Cost constraints
    - Historical performance
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self._config = config or {}
        
        # Performance history
        self._history: List[SwarmMetrics] = []
        
        # Configuration
        self._solo_threshold = self._config.get("solo_threshold", 0.3)  # complexity
        self._duo_threshold = self._config.get("duo_threshold", 0.6)
        self._swarm_threshold = self._config.get("swarm_threshold", 0.85)
        
        # Cost multipliers
        self._cost_multipliers = {
            ParallelismStrategy.SOLO: 1.0,
            ParallelismStrategy.DUO: 1.8,
            ParallelismStrategy.SWARM: 3.5,
            ParallelismStrategy.SERIALIZE: 1.2
        }
        
        # Speedup estimates
        self._speedup_estimates = {
            ParallelismStrategy.SOLO: 1.0,
            ParallelismStrategy.DUO: 1.6,
            ParallelismStrategy.SWARM: 2.5,
            ParallelismStrategy.SERIALIZE: 0.9
        }
        
        # Callbacks
        self._on_recommendation: Optional[Callable] = None
    
    def set_callbacks(self, on_recommendation: Optional[Callable] = None):
        """Set callback functions"""
        self._on_recommendation = on_recommendation
    
    # ==================== RECOMMENDATION ====================
    
    def recommend(self, task_id: str, task_description: str,
                 task_type: str, complexity: float,
                 time_budget_seconds: float = 3600,
                 cost_budget: float = 10.0,
                 urgency: int = 5) -> SwarmRecommendation:
        """
        Recommend parallelism strategy for a task.
        
        Args:
            task_id: Task identifier
            task_description: Task description
            task_type: Type of task
            complexity: Task complexity (0-1)
            time_budget_seconds: Available time
            cost_budget: Available budget
            urgency: Urgency level (1-10)
        """
        
        # Determine base strategy from complexity
        strategy = self._determine_strategy(complexity)
        
        # Adjust for task type
        strategy = self._adjust_for_task_type(strategy, task_type)
        
        # Adjust for constraints
        strategy = self._adjust_for_constraints(strategy, time_budget_seconds, cost_budget)
        
        # Adjust for urgency
        strategy = self._adjust_for_urgency(strategy, urgency)
        
        # Get historical performance
        historical_perf = self._get_historical_performance(strategy, task_type)
        
        # Calculate metrics
        agents = self._get_agent_count(strategy)
        speedup = self._speedup_estimates.get(strategy, 1.0)
        
        # Adjust speedup based on history
        if historical_perf:
            speedup *= historical_perf.get("success_rate", 1.0)
        
        # Calculate cost
        base_cost = self._estimate_base_cost(task_type)
        cost = base_cost * self._cost_multipliers[strategy]
        
        # Calculate success boost
        success_boost = self._calculate_success_boost(strategy, complexity, task_type)
        
        # Calculate confidence
        confidence = self._calculate_confidence(strategy, task_type, historical_perf)
        
        # Generate reasoning
        reasoning = self._generate_reasoning(strategy, complexity, task_type, urgency, cost)
        
        recommendation = SwarmRecommendation(
            task_id=task_id,
            strategy=strategy,
            recommended_agents=agents,
            estimated_speedup=speedup,
            estimated_cost=cost,
            estimated_success_boost=success_boost,
            confidence=confidence,
            reasoning=reasoning
        )
        
        if self._on_recommendation:
            self._on_recommendation(recommendation)
        
        return recommendation
    
    def _determine_strategy(self, complexity: float) -> ParallelismStrategy:
        """Determine base strategy from complexity"""
        
        if complexity < self._solo_threshold:
            return ParallelismStrategy.SOLO
        elif complexity < self._duo_threshold:
            return ParallelismStrategy.DUO
        elif complexity < self._swarm_threshold:
            return ParallelismStrategy.SWARM
        else:
            return ParallelismStrategy.SWARM
    
    def _adjust_for_task_type(self, strategy: ParallelismStrategy, 
                           task_type: str) -> ParallelismStrategy:
        """Adjust strategy based on task type"""
        
        # Tasks that benefit from parallelism
        parallel_benefit_types = [
            "research", "exploration", "multiple_files", 
            "integration", "testing", "debugging"
        ]
        
        # Tasks that don't benefit
        solo_benefit_types = [
            "simple_edit", "format", "validate", 
            "single_file", "quick_fix"
        ]
        
        if task_type in parallel_benefit_types:
            # Increase parallelism
            if strategy == ParallelismStrategy.SOLO:
                return ParallelismStrategy.DUO
            elif strategy == ParallelismStrategy.DUO:
                return ParallelismStrategy.SWARM
        
        elif task_type in solo_benefit_types:
            # Decrease parallelism
            return ParallelismStrategy.SOLO
        
        return strategy
    
    def _adjust_for_constraints(self, strategy: ParallelismStrategy,
                              time_budget: float, cost_budget: float) -> ParallelismStrategy:
        """Adjust strategy based on constraints"""
        
        # Estimate costs
        estimated_cost = self._estimate_base_cost("default") * \
                       self._cost_multipliers[strategy]
        
        # If over budget, reduce parallelism
        if estimated_cost > cost_budget:
            if strategy == ParallelismStrategy.SWARM:
                return ParallelismStrategy.DUO
            elif strategy == ParallelismStrategy.DUO:
                return ParallelismStrategy.SOLO
        
        # If time is very limited, simplify
        if time_budget < 300:  # < 5 minutes
            return ParallelismStrategy.SOLO
        
        return strategy
    
    def _adjust_for_urgency(self, strategy: ParallelismStrategy, 
                          urgency: int) -> ParallelismStrategy:
        """Adjust strategy based on urgency"""
        
        if urgency >= 9:  # Very urgent
            # Use more parallelism to speed up
            if strategy == ParallelismStrategy.SOLO:
                return ParallelismStrategy.DUO
        
        elif urgency <= 2:  # Not urgent
            # Can serialize to save cost
            if strategy == ParallelismStrategy.SWARM:
                return ParallelismStrategy.DUO
        
        return strategy
    
    def _get_agent_count(self, strategy: ParallelismStrategy) -> int:
        """Get agent count for strategy"""
        counts = {
            ParallelismStrategy.SOLO: 1,
            ParallelismStrategy.DUO: 2,
            ParallelismStrategy.SWARM: 4,
            ParallelismStrategy.SERIALIZE: 1
        }
        return counts.get(strategy, 1)
    
    def _estimate_base_cost(self, task_type: str) -> float:
        """Estimate base cost for task type"""
        costs = {
            "research": 5.0,
            "debugging": 3.0,
            "implementation": 2.0,
            "testing": 2.5,
            "review": 1.5,
            "simple_edit": 0.5,
            "default": 1.0
        }
        return costs.get(task_type, 1.0)
    
    def _get_historical_performance(self, strategy: ParallelismStrategy, 
                                   task_type: str) -> Optional[Dict]:
        """Get historical performance for strategy and task type"""
        
        relevant = [
            m for m in self._history[-50:]
            if m.strategy == strategy
        ]
        
        if not relevant:
            return None
        
        successes = sum(1 for m in relevant if m.success)
        avg_cost = sum(m.cost for m in relevant) / len(relevant)
        avg_duration = sum(m.duration_seconds for m in relevant) / len(relevant)
        
        return {
            "success_rate": successes / len(relevant),
            "avg_cost": avg_cost,
            "avg_duration": avg_duration,
            "sample_size": len(relevant)
        }
    
    def _calculate_success_boost(self, strategy: ParallelismStrategy,
                                 complexity: float, task_type: str) -> float:
        """Calculate expected success boost from parallelism"""
        
        # Base boost by complexity
        if complexity > 0.7:
            boost = 0.2  # 20% boost for complex tasks
        elif complexity > 0.4:
            boost = 0.1
        else:
            boost = 0.0
        
        # Adjust by strategy
        if strategy == ParallelismStrategy.SWARM:
            boost *= 1.5
        elif strategy == ParallelismStrategy.DUO:
            boost *= 1.2
        
        # Adjust by task type
        if task_type in ["research", "debugging"]:
            boost *= 1.3
        
        return min(0.5, boost)  # Cap at 50%
    
    def _calculate_confidence(self, strategy: ParallelismStrategy,
                            task_type: str, historical: Optional[Dict]) -> float:
        """Calculate confidence in recommendation"""
        
        base_confidence = 0.6
        
        # More confident if we have history
        if historical and historical.get("sample_size", 0) > 10:
            base_confidence += 0.2
        
        # Less confident for extreme strategies
        if strategy == ParallelismStrategy.SWARM:
            base_confidence -= 0.1
        
        return min(0.95, max(0.3, base_confidence))
    
    def _generate_reasoning(self, strategy: ParallelismStrategy, complexity: float,
                          task_type: str, urgency: int, cost: float) -> str:
        """Generate reasoning for recommendation"""
        
        reasons = []
        
        # Complexity reason
        if complexity > 0.7:
            reasons.append("complex task benefits from multiple perspectives")
        elif complexity < 0.3:
            reasons.append("simple task - single agent sufficient")
        
        # Task type reason
        if task_type in ["research", "debugging"]:
            reasons.append(f"{task_type} tasks benefit from parallelism")
        
        # Urgency reason
        if urgency >= 8:
            reasons.append("high urgency - using parallelism to speed up")
        
        # Cost reason
        if cost > 5:
            reasons.append(f"estimated cost: ${cost:.2f}")
        
        return "; ".join(reasons) if reasons else "standard recommendation"
    
    # ==================== RECORDING ====================
    
    def record_execution(self, task_id: str, strategy: ParallelismStrategy,
                       agents: int, duration: float, cost: float, success: bool):
        """Record execution for learning"""
        
        metrics = SwarmMetrics(
            task_id=task_id,
            strategy=strategy,
            agents_used=agents,
            duration_seconds=duration,
            cost=cost,
            success=success
        )
        
        self._history.append(metrics)
        
        # Keep only last 1000
        if len(self._history) > 1000:
            self._history = self._history[-1000:]
    
    # ==================== ANALYSIS ====================
    
    def analyze_strategy_performance(self) -> Dict:
        """Analyze performance of each strategy"""
        
        results = {}
        
        for strategy in ParallelismStrategy:
            relevant = [m for m in self._history if m.strategy == strategy]
            
            if not relevant:
                continue
            
            successes = sum(1 for m in relevant if m.success)
            
            results[strategy.value] = {
                "total_runs": len(relevant),
                "success_rate": successes / len(relevant),
                "avg_duration": sum(m.duration_seconds for m in relevant) / len(relevant),
                "avg_cost": sum(m.cost for m in relevant) / len(relevant),
                "efficiency": successes / (sum(m.cost for m in relevant) + 0.01)
            }
        
        return results


# ==================== FACTORY ====================

def create_swarm_economist(config: Optional[Dict] = None) -> SwarmEconomist:
    """Factory function to create swarm economist"""
    return SwarmEconomist(config=config)
