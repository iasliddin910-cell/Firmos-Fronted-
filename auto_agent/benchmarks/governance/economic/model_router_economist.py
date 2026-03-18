"""
Model Router Economist - Cost-Effective Model Selection
==================================================

This module selects the most cost-effective model for each task:
- Cheap model for simple tasks
- Strong model for complex tasks
- Cascade path selection
- Draft/final split
- Verifier escalation

Author: No1 World+ Autonomous System
"""

import asyncio
import logging
import threading
import random
from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from collections import defaultdict
import statistics

logger = logging.getLogger(__name__)


# ==================== ENUMS ====================

class ModelTier(str, Enum):
    """Model tiers"""
    CHEAP = "cheap"           # Fast, low cost
    STANDARD = "standard"     # Balanced
    PREMIUM = "premium"        # High capability
    EXPERT = "expert"         # Maximum capability


class RoutingStrategy(str, Enum):
    """Routing strategies"""
    CHEAP_FIRST = "cheap_first"
    PREMIUM_ONLY = "premium_only"
    CASCADE = "cascade"
    DRAFT_FINAL = "draft_final"
    VERIFIER_ESCALATION = "verifier_escalation"


class TaskComplexity(str, Enum):
    """Task complexity levels"""
    TRIVIAL = "trivial"
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    EXPERT = "expert"


# ==================== DATA CLASSES ====================

@dataclass
class ModelInfo:
    """Information about a model"""
    model_id: str
    tier: ModelTier
    cost_per_1k_input: float
    cost_per_1k_output: float
    latency_ms: int
    capability_score: float  # 0-100
    best_for: List[str]      # Task types
    reliability: float       # 0-1 success rate estimate


@dataclass
class RoutingDecision:
    """Model routing decision"""
    task_id: str
    selected_model: str
    strategy: RoutingStrategy
    estimated_cost: float
    estimated_latency_ms: int
    confidence: float
    fallback_model: Optional[str]
    reasoning: str


@dataclass
class ModelPerformance:
    """Performance metrics for a model"""
    model_id: str
    total_uses: int
    successful_uses: int
    success_rate: float
    avg_latency_ms: float
    avg_cost: float
    total_cost: float
    tasks_by_complexity: Dict[TaskComplexity, int]


# ==================== MODEL REGISTRY ====================

class ModelRegistry:
    """Registry of available models"""
    
    # Default model configurations
    DEFAULT_MODELS = {
        "gpt-4o-mini": ModelInfo(
            model_id="gpt-4o-mini",
            tier=ModelTier.CHEAP,
            cost_per_1k_input=0.15,
            cost_per_1k_output=0.6,
            latency_ms=500,
            capability_score=75,
            best_for=["simple_code", "formatting", "validation"],
            reliability=0.85
        ),
        "gpt-4o": ModelInfo(
            model_id="gpt-4o",
            tier=ModelTier.STANDARD,
            cost_per_1k_input=2.5,
            cost_per_1k_output=10.0,
            latency_ms=1500,
            capability_score=90,
            best_for=["complex_code", "reasoning", "analysis"],
            reliability=0.95
        ),
        "gpt-4-turbo": ModelInfo(
            model_id="gpt-4-turbo",
            tier=ModelTier.PREMIUM,
            cost_per_1k_input=10.0,
            cost_per_1k_output=30.0,
            latency_ms=3000,
            capability_score=95,
            best_for=["expert_reasoning", "multi_step", "critical"],
            reliability=0.98
        ),
        "claude-3-opus": ModelInfo(
            model_id="claude-3-opus",
            tier=ModelTier.EXPERT,
            cost_per_1k_input=15.0,
            cost_per_1k_output=75.0,
            latency_ms=5000,
            capability_score=98,
            best_for=["expert", "research", "critical_analysis"],
            reliability=0.99
        )
    }
    
    def __init__(self, custom_models: Optional[Dict[str, ModelInfo]] = None):
        self._models = dict(self.DEFAULT_MODELS)
        
        if custom_models:
            self._models.update(custom_models)
    
    def get_model(self, model_id: str) -> Optional[ModelInfo]:
        return self._models.get(model_id)
    
    def get_models_by_tier(self, tier: ModelTier) -> List[ModelInfo]:
        return [m for m in self._models.values() if m.tier == tier]
    
    def get_cheapest_model(self) -> ModelInfo:
        return min(self._models.values(), 
                  key=lambda m: m.cost_per_1k_input + m.cost_per_1k_output)
    
    def get_fastest_model(self) -> ModelInfo:
        return min(self._models.values(), key=lambda m: m.latency_ms)
    
    def get_best_model(self) -> ModelInfo:
        return max(self._models.values(), key=lambda m: m.capability_score)
    
    def get_all_models(self) -> Dict[str, ModelInfo]:
        return self._models.copy()


# ==================== TASK ANALYZER ====================

class TaskAnalyzer:
    """Analyzes task complexity"""
    
    # Complexity indicators
    COMPLEXITY_KEYWORDS = {
        TaskComplexity.TRIVIAL: ["format", "validate", "check", "simple"],
        TaskComplexity.SIMPLE: ["write", "read", "list", "find"],
        TaskComplexity.MODERATE: ["implement", "fix", "refactor", "analyze"],
        TaskComplexity.COMPLEX: ["design", "architect", "debug", "optimize"],
        TaskComplexity.EXPERT: ["research", "invent", "create", "prove"]
    }
    
    def __init__(self):
        self._complexity_history: List[Tuple[str, TaskComplexity]] = []
    
    def analyze_complexity(self, task_description: str, 
                         task_type: str) -> TaskComplexity:
        """Analyze task complexity"""
        
        # Base complexity by task type
        type_complexity = {
            "file_operation": TaskComplexity.SIMPLE,
            "code": TaskComplexity.MODERATE,
            "browser": TaskComplexity.MODERATE,
            "terminal": TaskComplexity.SIMPLE,
            "research": TaskComplexity.COMPLEX,
            "analysis": TaskComplexity.COMPLEX,
            "debug": TaskComplexity.COMPLEX,
            "design": TaskComplexity.EXPERT,
            "review": TaskComplexity.MODERATE
        }
        
        complexity = type_complexity.get(task_type, TaskComplexity.MODERATE)
        
        # Adjust based on keywords
        desc_lower = task_description.lower()
        
        for kw_level, keywords in self.COMPLEXITY_KEYWORDS.items():
            if any(kw in desc_lower for kw in keywords):
                # Higher complexity wins
                if kw_level.value > complexity.value:
                    complexity = kw_level
        
        return complexity
    
    def get_complexity_multipliers(self, complexity: TaskComplexity) -> Dict:
        """Get cost and time multipliers based on complexity"""
        multipliers = {
            TaskComplexity.TRIVIAL: {"cost": 0.2, "time": 0.3},
            TaskComplexity.SIMPLE: {"cost": 0.4, "time": 0.5},
            TaskComplexity.MODERATE: {"cost": 1.0, "time": 1.0},
            TaskComplexity.COMPLEX: {"cost": 2.0, "time": 2.0},
            TaskComplexity.EXPERT: {"cost": 4.0, "time": 4.0}
        }
        return multipliers.get(complexity, {"cost": 1.0, "time": 1.0})


# ==================== MODEL ROUTER ECONOMIST ====================

class ModelRouterEconomist:
    """
    Cost-effective model selection system.
    
    Features:
    - Task complexity analysis
    - Model tier selection
    - Cascade routing
    - Draft/final split
    - Performance tracking
    - ROI calculation
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self._config = config or {}
        
        # Components
        self._registry = ModelRegistry()
        self._task_analyzer = TaskAnalyzer()
        
        # Performance tracking
        self._performance: Dict[str, ModelPerformance] = {}
        
        # Default strategy
        self._default_strategy = RoutingStrategy(
            self._config.get("default_strategy", "cheap_first")
        )
        
        # Callbacks
        self._on_escalation: Optional[Callable] = None
    
    def set_callbacks(self, on_escalation: Optional[Callable] = None):
        """Set callback functions"""
        self._on_escalation = on_escalation
    
    # ==================== ROUTING ====================
    
    def route(self, task_id: str, task_description: str, 
             task_type: str, task_value: float = 100.0,
             urgency: int = 5) -> RoutingDecision:
        """Route task to appropriate model"""
        
        # Analyze complexity
        complexity = self._task_analyzer.analyze_complexity(task_description, task_type)
        multipliers = self._task_analyzer.get_complexity_multipliers(complexity)
        
        # Determine strategy
        strategy = self._determine_strategy(task_value, urgency, complexity)
        
        # Select model based on strategy
        if strategy == RoutingStrategy.CHEAP_FIRST:
            return self._route_cheap_first(task_id, complexity, multipliers, task_value)
        
        elif strategy == RoutingStrategy.PREMIUM_ONLY:
            return self._route_premium_only(task_id, complexity, multipliers)
        
        elif strategy == RoutingStrategy.CASCADE:
            return self._route_cascade(task_id, complexity, multipliers)
        
        elif strategy == RoutingStrategy.DRAFT_FINAL:
            return self._route_draft_final(task_id, complexity, multipliers)
        
        elif strategy == RoutingStrategy.VERIFIER_ESCALATION:
            return self._route_verifier_escalation(task_id, complexity, multipliers)
        
        # Default to cheap first
        return self._route_cheap_first(task_id, complexity, multipliers, task_value)
    
    def _determine_strategy(self, task_value: float, urgency: int,
                          complexity: TaskComplexity) -> RoutingStrategy:
        """Determine routing strategy based on task characteristics"""
        
        # High value, high urgency = premium
        if task_value > 1000 and urgency >= 8:
            return RoutingStrategy.PREMIUM_ONLY
        
        # Expert complexity = cascade
        if complexity == TaskComplexity.EXPERT:
            return RoutingStrategy.CASCADE
        
        # Very high value = draft/final
        if task_value > 500:
            return RoutingStrategy.DRAFT_FINAL
        
        # Very urgent = premium
        if urgency >= 9:
            return RoutingStrategy.PREMIUM_ONLY
        
        # Default: cheap first
        return RoutingStrategy.CHEAP_FIRST
    
    def _route_cheap_first(self, task_id: str, complexity: TaskComplexity,
                          multipliers: Dict, task_value: float) -> RoutingDecision:
        """Route: try cheap, escalate if needed"""
        
        # Select cheap model for simple/trivial tasks
        if complexity in [TaskComplexity.TRIVIAL, TaskComplexity.SIMPLE]:
            model = self._registry.get_cheapest_model()
            fallback = self._registry.get_models_by_tier(ModelTier.STANDARD)[0] \
                     if self._registry.get_models_by_tier(ModelTier.STANDARD) else None
            
            estimated_cost = (model.cost_per_1k_input * 0.5 + 
                           model.cost_per_1k_output * 0.5) * multipliers["cost"]
            estimated_latency = model.latency_ms * multipliers["time"]
            
            return RoutingDecision(
                task_id=task_id,
                selected_model=model.model_id,
                strategy=RoutingStrategy.CHEAP_FIRST,
                estimated_cost=estimated_cost,
                estimated_latency_ms=estimated_latency,
                confidence=0.7,
                fallback_model=fallback.model_id if fallback else None,
                reasoning=f"Simple task - use cheap model, fallback to standard if needed"
            )
        
        # Moderate complexity - use standard
        elif complexity == TaskComplexity.MODERATE:
            models = self._registry.get_models_by_tier(ModelTier.STANDARD)
            if not models:
                models = list(self._registry.get_all_models().values())
            
            model = models[0]
            fallback = self._registry.get_models_by_tier(ModelTier.PREMIUM)[0] \
                     if self._registry.get_models_by_tier(ModelTier.PREMIUM) else None
            
            return RoutingDecision(
                task_id=task_id,
                selected_model=model.model_id,
                strategy=RoutingStrategy.CHEAP_FIRST,
                estimated_cost=(model.cost_per_1k_input + model.cost_per_1k_output) * multipliers["cost"],
                estimated_latency_ms=model.latency_ms * multipliers["time"],
                confidence=0.8,
                fallback_model=fallback.model_id if fallback else None,
                reasoning="Moderate task - use standard model"
            )
        
        # Complex = premium
        else:
            models = self._registry.get_models_by_tier(ModelTier.PREMIUM)
            if not models:
                models = list(self._registry.get_all_models().values())
            
            model = models[0]
            
            return RoutingDecision(
                task_id=task_id,
                selected_model=model.model_id,
                strategy=RoutingStrategy.CHEAP_FIRST,
                estimated_cost=(model.cost_per_1k_input + model.cost_per_1k_output) * multipliers["cost"],
                estimated_latency_ms=model.latency_ms * multipliers["time"],
                confidence=0.9,
                fallback_model=None,
                reasoning="Complex task - use premium model directly"
            )
    
    def _route_premium_only(self, task_id: str, complexity: TaskComplexity,
                          multipliers: Dict) -> RoutingDecision:
        """Route: always use premium"""
        
        models = self._registry.get_models_by_tier(ModelTier.PREMIUM)
        if not models:
            models = list(self._registry.get_all_models().values())
        
        model = max(models, key=lambda m: m.capability_score)
        
        return RoutingDecision(
            task_id=task_id,
            selected_model=model.model_id,
            strategy=RoutingStrategy.PREMIUM_ONLY,
            estimated_cost=(model.cost_per_1k_input + model.cost_per_1k_output) * multipliers["cost"],
            estimated_latency_ms=model.latency_ms * multipliers["time"],
            confidence=0.95,
            fallback_model=None,
            reasoning="High priority/urgency - use premium"
        )
    
    def _route_cascade(self, task_id: str, complexity: TaskComplexity,
                      multipliers: Dict) -> RoutingDecision:
        """Route: start cheap, escalate through tiers"""
        
        # Start with cheap
        cheap = self._registry.get_cheapest_model()
        
        return RoutingDecision(
            task_id=task_id,
            selected_model=cheap.model_id,
            strategy=RoutingStrategy.CASCADE,
            estimated_cost=(cheap.cost_per_1k_input + cheap.cost_per_1k_output) * multipliers["cost"] * 1.5,
            estimated_latency_ms=cheap.latency_ms * multipliers["time"] * 2,
            confidence=0.6,
            fallback_model=self._registry.get_best_model().model_id,
            reasoning="Cascade: start cheap, escalate if needed"
        )
    
    def _route_draft_final(self, task_id: str, complexity: TaskComplexity,
                          multipliers: Dict) -> RoutingDecision:
        """Route: draft with cheap, final with premium"""
        
        cheap = self._registry.get_cheapest_model()
        
        return RoutingDecision(
            task_id=task_id,
            selected_model=cheap.model_id,
            strategy=RoutingStrategy.DRAFT_FINAL,
            estimated_cost=(cheap.cost_per_1k_input + cheap.cost_per_1k_output) * multipliers["cost"] * 0.6 +
                         (self._registry.get_best_model().cost_per_1k_input * 0.4),
            estimated_latency_ms=cheap.latency_ms * multipliers["time"] * 1.5,
            confidence=0.75,
            fallback_model=self._registry.get_best_model().model_id,
            reasoning="Draft/final: cheap draft, premium final verification"
        )
    
    def _route_verifier_escalation(self, task_id: str, complexity: TaskComplexity,
                                   multipliers: Dict) -> RoutingDecision:
        """Route: cheap + verifier escalation"""
        
        cheap = self._registry.get_cheapest_model()
        
        return RoutingDecision(
            task_id=task_id,
            selected_model=cheap.model_id,
            strategy=RoutingStrategy.VERIFIER_ESCALATION,
            estimated_cost=(cheap.cost_per_1k_input + cheap.cost_per_1k_output) * multipliers["cost"] * 1.2,
            estimated_latency_ms=cheap.latency_ms * multipliers["time"] * 1.3,
            confidence=0.65,
            fallback_model=self._registry.get_models_by_tier(ModelTier.PREMIUM)[0].model_id
                         if self._registry.get_models_by_tier(ModelTier.PREMIUM) else None,
            reasoning="Verifier escalation: cheap first, premium verifier if confidence low"
        )
    
    # ==================== PERFORMANCE TRACKING ====================
    
    def record_result(self, task_id: str, model_id: str, success: bool,
                     latency_ms: float, cost: float, complexity: TaskComplexity):
        """Record task result for performance tracking"""
        
        if model_id not in self._performance:
            self._performance[model_id] = ModelPerformance(
                model_id=model_id,
                total_uses=0,
                successful_uses=0,
                success_rate=0.0,
                avg_latency_ms=0.0,
                avg_cost=0.0,
                total_cost=0.0,
                tasks_by_complexity=defaultdict(int)
            )
        
        perf = self._performance[model_id]
        perf.total_uses += 1
        
        if success:
            perf.successful_uses += 1
        
        # Update success rate
        perf.success_rate = perf.successful_uses / perf.total_uses
        
        # Update average latency
        perf.avg_latency_ms = ((perf.avg_latency_ms * (perf.total_uses - 1)) + latency_ms) / perf.total_uses
        
        # Update average cost
        perf.avg_cost = ((perf.avg_cost * (perf.total_uses - 1)) + cost) / perf.total_uses
        perf.total_cost += cost
        
        # Track complexity distribution
        perf.tasks_by_complexity[complexity] += 1
    
    def get_model_performance(self, model_id: str) -> Optional[ModelPerformance]:
        """Get performance metrics for a model"""
        return self._performance.get(model_id)
    
    def get_roi_scores(self) -> Dict[str, float]:
        """Calculate ROI score for each model (success_rate / cost)"""
        scores = {}
        
        for model_id, perf in self._performance.items():
            if perf.avg_cost > 0:
                scores[model_id] = perf.success_rate / perf.avg_cost
            else:
                scores[model_id] = 0
        
        return scores
    
    def get_recommended_model(self, complexity: TaskComplexity) -> str:
        """Get recommended model for complexity level"""
        
        # Filter by complexity
        tier_mapping = {
            TaskComplexity.TRIVIAL: ModelTier.CHEAP,
            TaskComplexity.SIMPLE: ModelTier.CHEAP,
            TaskComplexity.MODERATE: ModelTier.STANDARD,
            TaskComplexity.COMPLEX: ModelTier.PREMIUM,
            TaskComplexity.EXPERT: ModelTier.EXPERT
        }
        
        tier = tier_mapping.get(complexity, ModelTier.STANDARD)
        
        # Get models of that tier with best ROI
        models = self._registry.get_models_by_tier(tier)
        
        if not models:
            return self._registry.get_cheapest_model().model_id
        
        # Use performance data if available
        best_model = models[0]
        best_roi = 0
        
        for model in models:
            perf = self._performance.get(model.model_id)
            if perf and perf.avg_cost > 0:
                roi = perf.success_rate / perf.avg_cost
                if roi > best_roi:
                    best_roi = roi
                    best_model = model
        
        return best_model.model_id
    
    # ==================== ESTIMATION ====================
    
    def estimate_cost(self, model_id: str, input_tokens: int, 
                     output_tokens: int) -> float:
        """Estimate cost for a model with given token counts"""
        
        model = self._registry.get_model(model_id)
        
        if not model:
            return 0
        
        input_cost = (input_tokens / 1000) * model.cost_per_1k_input
        output_cost = (output_tokens / 1000) * model.cost_per_1k_output
        
        return input_cost + output_cost
    
    def estimate_latency(self, model_id: str, output_tokens: int) -> int:
        """Estimate latency for a model"""
        
        model = self._registry.get_model(model_id)
        
        if not model:
            return 0
        
        # Approximate: base latency + output time
        return model.latency_ms + (output_tokens * 10)  # ~10ms per token


# ==================== FACTORY ====================

def create_model_router(config: Optional[Dict] = None) -> ModelRouterEconomist:
    """Factory function to create model router"""
    return ModelRouterEconomist(config=config)
