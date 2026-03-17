"""
Weighting Policy - Customizable Scoring Policies
=================================================

Flexible weighting policies for different scoring scenarios.

This module provides:
- Predefined weight configurations
- Custom weight builders
- Suite-specific policies
- Difficulty-based policies
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Callable
from enum import Enum


# ==================== WEIGHTING POLICIES ====================

class WeightingPolicy(str, Enum):
    """Predefined weighting policies."""
    DEFAULT = "default"
    FRONTIER = "frontier"
    EFFICIENCY_FOCUSED = "efficiency_focused"
    RELIABILITY_FOCUSED = "reliability_focused"
    COST_SENSITIVE = "cost_sensitive"
    HARD_ONLY = "hard_only"


class SuitePolicy(str, Enum):
    """Suite-specific policies."""
    BALANCED = "balanced"
    SELF_MOD_PRIORITY = "self_mod_priority"
    TOOL_CREATION_PRIORITY = "tool_creation_priority"
    BROWSER_PRIORITY = "browser_priority"


@dataclass
class WeightingPolicyConfig:
    """
    Complete weighting policy configuration.
    """
    # Policy type
    policy: WeightingPolicy = WeightingPolicy.DEFAULT
    
    # Difficulty weights
    difficulty_weights: Dict[str, float] = field(default_factory=lambda: {
        "easy": 1.0,
        "medium": 2.0,
        "hard": 4.0,
        "frontier": 6.0,
    })
    
    # Suite weights
    suite_weights: Dict[str, float] = field(default_factory=dict)
    
    # Capability weights
    capability_weights: Dict[str, float] = field(default_factory=dict)
    
    # Dimension weights
    dimension_weights: Dict[str, float] = field(default_factory=lambda: {
        "capability": 0.35,
        "reliability": 0.20,
        "efficiency": 0.15,
        "integrity": 0.15,
        "generalization": 0.10,
        "safety": 0.05,
    })
    
    # Efficiency thresholds
    cost_baseline: float = 0.10
    time_baseline: float = 60.0
    steps_baseline: int = 50
    
    # Penalty multipliers
    cost_penalty_multiplier: float = 0.5
    time_penalty_multiplier: float = 0.3
    steps_penalty_multiplier: float = 0.2
    
    # Floor minimums
    hard_frontier_minimum: float = 0.60
    reliability_minimum: float = 0.80
    integrity_minimum: float = 0.95
    safety_minimum: float = 0.95
    
    # Additional multipliers
    integrity_multiplier: float = 1.0
    reliability_multiplier: float = 1.0
    generalization_multiplier: float = 1.0
    
    @classmethod
    def from_policy(cls, policy: WeightingPolicy) -> 'WeightingPolicyConfig':
        """Create config from predefined policy."""
        configs = {
            WeightingPolicy.DEFAULT: cls._default_policy,
            WeightingPolicy.FRONTIER: cls._frontier_policy,
            WeightingPolicy.EFFICIENCY_FOCUSED: cls._efficiency_policy,
            WeightingPolicy.RELIABILITY_FOCUSED: cls._reliability_policy,
            WeightingPolicy.COST_SENSITIVE: cls._cost_sensitive_policy,
            WeightingPolicy.HARD_ONLY: cls._hard_only_policy,
        }
        return configs.get(policy, cls._default_policy)()
    
    @staticmethod
    def _default_policy() -> 'WeightingPolicyConfig':
        """Default policy."""
        return WeightingPolicyConfig(
            policy=WeightingPolicy.DEFAULT,
            difficulty_weights={
                "easy": 1.0,
                "medium": 2.0,
                "hard": 4.0,
                "frontier": 6.0,
            },
            dimension_weights={
                "capability": 0.35,
                "reliability": 0.20,
                "efficiency": 0.15,
                "integrity": 0.15,
                "generalization": 0.10,
                "safety": 0.05,
            },
        )
    
    @staticmethod
    def _frontier_policy() -> 'WeightingPolicyConfig':
        """Frontier-grade policy with extra emphasis on frontier tasks."""
        return WeightingPolicyConfig(
            policy=WeightingPolicy.FRONTIER,
            difficulty_weights={
                "easy": 0.5,
                "medium": 1.5,
                "hard": 5.0,
                "frontier": 10.0,
            },
            suite_weights={
                "self_modification": 2.0,
                "tool_creation_use": 1.8,
                "long_horizon_orchestration": 1.5,
            },
            dimension_weights={
                "capability": 0.30,
                "reliability": 0.25,
                "efficiency": 0.10,
                "integrity": 0.20,
                "generalization": 0.10,
                "safety": 0.05,
            },
            hard_frontier_minimum=0.70,
            reliability_minimum=0.85,
            integrity_minimum=0.98,
        )
    
    @staticmethod
    def _efficiency_policy() -> 'WeightingPolicyConfig':
        """Efficiency-focused policy."""
        return WeightingPolicyConfig(
            policy=WeightingPolicy.EFFICIENCY_FOCUSED,
            difficulty_weights={
                "easy": 1.0,
                "medium": 2.0,
                "hard": 4.0,
                "frontier": 6.0,
            },
            dimension_weights={
                "capability": 0.25,
                "reliability": 0.15,
                "efficiency": 0.35,
                "integrity": 0.10,
                "generalization": 0.10,
                "safety": 0.05,
            },
            cost_penalty_multiplier=1.0,
            time_penalty_multiplier=0.8,
            steps_penalty_multiplier=0.8,
        )
    
    @staticmethod
    def _reliability_policy() -> 'WeightingPolicyConfig':
        """Reliability-focused policy."""
        return WeightingPolicyConfig(
            policy=WeightingPolicy.RELIABILITY_FOCUSED,
            difficulty_weights={
                "easy": 1.0,
                "medium": 2.0,
                "hard": 4.0,
                "frontier": 6.0,
            },
            dimension_weights={
                "capability": 0.25,
                "reliability": 0.35,
                "efficiency": 0.10,
                "integrity": 0.15,
                "generalization": 0.10,
                "safety": 0.05,
            },
            reliability_multiplier=1.5,
            reliability_minimum=0.90,
        )
    
    @staticmethod
    def _cost_sensitive_policy() -> 'WeightingPolicyConfig':
        """Cost-sensitive policy."""
        return WeightingPolicyConfig(
            policy=WeightingPolicy.COST_SENSITIVE,
            difficulty_weights={
                "easy": 1.0,
                "medium": 2.0,
                "hard": 4.0,
                "frontier": 6.0,
            },
            dimension_weights={
                "capability": 0.30,
                "reliability": 0.15,
                "efficiency": 0.30,
                "integrity": 0.10,
                "generalization": 0.10,
                "safety": 0.05,
            },
            cost_baseline=0.05,
            time_baseline=30.0,
            steps_baseline=25,
            cost_penalty_multiplier=1.5,
        )
    
    @staticmethod
    def _hard_only_policy() -> 'HardOnlyWeightingPolicyConfig':
        """Hard and frontier tasks only."""
        return HardOnlyWeightingPolicyConfig()


@dataclass
class HardOnlyWeightingPolicyConfig(WeightingPolicyConfig):
    """Policy that only considers hard and frontier tasks."""
    
    def __init__(self):
        super().__init__()
        self.policy = WeightingPolicy.HARD_ONLY
        self.difficulty_weights = {
            "easy": 0.0,
            "medium": 0.0,
            "hard": 4.0,
            "frontier": 6.0,
        }
        self.hard_frontier_minimum = 0.70


# ==================== SUITE POLICIES ====================

class SuiteWeightBuilder:
    """
    Builder for suite-specific weights.
    """
    
    @staticmethod
    def balanced() -> Dict[str, float]:
        """Equal weights for all suites."""
        return {
            "repo_engineering": 1.0,
            "bug_localization_repair": 1.0,
            "terminal_operations": 1.0,
            "browser_workflow": 1.0,
            "long_horizon_orchestration": 1.0,
            "tool_creation_use": 1.0,
            "self_modification": 1.0,
            "knowledge_refresh": 1.0,
        }
    
    @staticmethod
    def self_mod_priority() -> Dict[str, float]:
        """Priority to self-modification suite."""
        return {
            "repo_engineering": 0.8,
            "bug_localization_repair": 0.8,
            "terminal_operations": 0.8,
            "browser_workflow": 0.8,
            "long_horizon_orchestration": 1.2,
            "tool_creation_use": 1.0,
            "self_modification": 2.0,
            "knowledge_refresh": 0.8,
        }
    
    @staticmethod
    def tool_creation_priority() -> Dict[str, float]:
        """Priority to tool creation suite."""
        return {
            "repo_engineering": 0.8,
            "bug_localization_repair": 0.8,
            "terminal_operations": 0.8,
            "browser_workflow": 0.8,
            "long_horizon_orchestration": 1.0,
            "tool_creation_use": 2.0,
            "self_modification": 1.5,
            "knowledge_refresh": 0.8,
        }
    
    @staticmethod
    def autonomy_focused() -> Dict[str, float]:
        """Focus on autonomy-related suites."""
        return {
            "repo_engineering": 1.0,
            "bug_localization_repair": 1.0,
            "terminal_operations": 1.2,
            "browser_workflow": 1.2,
            "long_horizon_orchestration": 1.5,
            "tool_creation_use": 1.5,
            "self_modification": 2.0,
            "knowledge_refresh": 0.8,
        }


# ==================== DIFFICULTY POLICIES ====================

class DifficultyWeightBuilder:
    """
    Builder for difficulty-specific weights.
    """
    
    @staticmethod
    def standard() -> Dict[str, float]:
        """Standard linear weights."""
        return {
            "easy": 1.0,
            "medium": 2.0,
            "hard": 4.0,
            "frontier": 6.0,
        }
    
    @staticmethod
    def aggressive() -> Dict[str, float]:
        """Aggressive weights emphasizing hard/frontier."""
        return {
            "easy": 0.5,
            "medium": 1.5,
            "hard": 5.0,
            "frontier": 10.0,
        }
    
    @staticmethod
    def conservative() -> Dict[str, float]:
        """Conservative weights with less emphasis on frontier."""
        return {
            "easy": 1.2,
            "medium": 2.0,
            "hard": 3.0,
            "frontier": 4.0,
        }
    
    @staticmethod
    def flat() -> Dict[str, float]:
        """Flat weights (all equal)."""
        return {
            "easy": 1.0,
            "medium": 1.0,
            "hard": 1.0,
            "frontier": 1.0,
        }


# ==================== WEIGHTING CALCULATOR ====================

class WeightingCalculator:
    """
    Calculate final weights combining multiple factors.
    """
    
    def __init__(self, config: WeightingPolicyConfig):
        self.config = config
    
    def calculate_task_weight(
        self,
        difficulty: str,
        suite: str,
        capabilities: List[str],
    ) -> float:
        """
        Calculate final weight for a task.
        
        Combines:
        - Difficulty weight
        - Suite weight
        - Capability weights
        """
        # Difficulty weight
        diff_weight = self.config.difficulty_weights.get(difficulty, 1.0)
        
        # Suite weight
        suite_weight = self.config.suite_weights.get(suite, 1.0)
        
        # Capability weights (average)
        cap_weights = [
            self.config.capability_weights.get(cap, 1.0)
            for cap in capabilities
        ]
        avg_cap_weight = sum(cap_weights) / len(cap_weights) if cap_weights else 1.0
        
        # Combine
        return diff_weight * suite_weight * avg_cap_weight
    
    def calculate_adjusted_score(
        self,
        raw_score: float,
        reliability: float,
        efficiency: float,
        integrity: float,
        safety: float,
        generalization: float,
    ) -> float:
        """
        Calculate adjusted score with all multipliers.
        
        Formula:
        adjusted = raw * rel * eff * int * gen * safety
        """
        return (
            raw_score
            * (reliability ** self.config.reliability_multiplier)
            * (efficiency ** self.config.efficiency_multiplier)
            * (integrity ** self.config.integrity_multiplier)
            * generalization
            * safety
        )
    
    def calculate_efficiency_penalty(
        self,
        cost_usd: float,
        time_seconds: float,
        steps: int,
    ) -> float:
        """
        Calculate efficiency penalty.
        
        Returns penalty (0.0 - 1.0) to subtract from score.
        """
        # Cost penalty
        cost_ratio = cost_usd / self.config.cost_baseline if self.config.cost_baseline > 0 else 1.0
        cost_penalty = max(0.0, (cost_ratio - 1.0) * self.config.cost_penalty_multiplier)
        
        # Time penalty
        time_ratio = time_seconds / self.config.time_baseline if self.config.time_baseline > 0 else 1.0
        time_penalty = max(0.0, (time_ratio - 1.0) * self.config.time_penalty_multiplier)
        
        # Steps penalty
        steps_ratio = steps / self.config.steps_baseline if self.config.steps_baseline > 0 else 1.0
        steps_penalty = max(0.0, (steps_ratio - 1.0) * self.config.steps_penalty_multiplier)
        
        # Combined penalty (average)
        return (cost_penalty + time_penalty + steps_penalty) / 3.0
    
    def calculate_global_score(
        self,
        dimension_scores: Dict[str, float],
    ) -> float:
        """
        Calculate global composite score.
        """
        weights = self.config.dimension_weights
        
        return sum(
            dimension_scores.get(dim, 0.0) * weight
            for dim, weight in weights.items()
        )


# ==================== FACTORY ====================

def create_weighting_policy(
    policy: WeightingPolicy = WeightingPolicy.DEFAULT,
) -> WeightingPolicyConfig:
    """Create weighting policy config from policy type."""
    return WeightingPolicyConfig.from_policy(policy)


def create_weighting_calculator(
    config: WeightingPolicyConfig = None,
) -> WeightingCalculator:
    """Create weighting calculator."""
    return WeightingCalculator(config or WeightingPolicyConfig.default())
