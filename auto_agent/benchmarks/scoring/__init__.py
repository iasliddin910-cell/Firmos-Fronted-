"""
Scoring Package - Multi-Axis Score Aggregation System
====================================================

Frontier-grade scoring system for autonomous agents.

Modules:
- scorecard: Structured result schema for benchmark runs
- aggregation_engine: Weighted aggregation engine
- weighting_policy: Customizable weighting policies
- promotion_policy: Promotion decision engine
- claim_validator: System claim validation

Usage:
    from scoring import ScoreCard, create_task_result, create_scorecard
    from scoring import AggregationEngine, WeightingCalculator
    from scoring import RunEvaluator, create_promotion_policy
    from scoring import ClaimValidator

Definition of Done:
1. Har run structured scorecard bilan saqlanadi.
2. Per-suite, per-capability, per-difficulty scoreboardlar bor.
3. Global score faqat summary, promotion esa floor policy bilan ishlaydi.
4. Stable va experimental board alohida.
5. Integrity/reliability/efficiency alohida ko'rinadi.
6. Claim-aware minimumlar mavjud.
"""

from .scorecard import (
    ScoreCard,
    TaskResult,
    RunStatus,
    QualityDimension,
    DifficultyLevel,
    create_task_result,
    create_scorecard,
)

from .aggregation_engine import (
    AggregationEngine,
    AdvancedAggregator,
    RegressionDetector,
    WeightingConfig,
    create_aggregation_engine,
)

from .weighting_policy import (
    WeightingPolicy,
    WeightingPolicyConfig,
    WeightingCalculator,
    create_weighting_policy,
    create_weighting_calculator,
)

from .promotion_policy import (
    PromotionPolicy,
    PromotionResult,
    PromotionDecision,
    BoardType,
    FloorPolicies,
    RunEvaluator,
    MultiCandidateDecider,
    create_promotion_policy,
    create_evaluator,
)

from .claim_validator import (
    ClaimType,
    ClaimRequirement,
    ClaimValidationResult,
    ClaimValidator,
    ClaimAwareScorer,
    create_claim_validator,
    validate_claims,
)

__all__ = [
    # ScoreCard
    "ScoreCard",
    "TaskResult",
    "RunStatus",
    "QualityDimension",
    "DifficultyLevel",
    "create_task_result",
    "create_scorecard",
    
    # Aggregation
    "AggregationEngine",
    "AdvancedAggregator",
    "RegressionDetector",
    "WeightingConfig",
    "create_aggregation_engine",
    
    # Weighting
    "WeightingPolicy",
    "WeightingPolicyConfig",
    "WeightingCalculator",
    "create_weighting_policy",
    "create_weighting_calculator",
    
    # Promotion
    "PromotionPolicy",
    "PromotionResult",
    "PromotionDecision",
    "BoardType",
    "FloorPolicies",
    "RunEvaluator",
    "MultiCandidateDecider",
    "create_promotion_policy",
    "create_evaluator",
    
    # Claims
    "ClaimType",
    "ClaimRequirement",
    "ClaimValidationResult",
    "ClaimValidator",
    "ClaimAwareScorer",
    "create_claim_validator",
    "validate_claims",
]

__version__ = "1.0.0"
