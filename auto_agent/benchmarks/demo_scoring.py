"""
Frontier-Grade Scoring Demo
===========================

This demonstrates the complete frontier-grade scoring system.

Usage:
    python demo_scoring.py

Definition of Done ( hammasi bajarildi ):

1. Har run structured scorecard bilan saqlanadi.         ✅
2. Per-suite, per-capability, per-difficulty scoreboardlar bor.  ✅
3. Global score faqat summary, promotion esa floor policy bilan ishlaydi. ✅
4. Stable va experimental board alohida.                  ✅
5. Integrity/reliability/efficiency alohida ko'rinadi.     ✅
6. Claim-aware minimumlar mavjud.                         ✅
"""

import sys
sys.path.insert(0, '/workspace/project/Firmos-Fronted-/auto_agent')

from benchmarks.scoring import (
    ScoreCard, TaskResult, RunStatus, DifficultyLevel, QualityDimension,
    create_task_result, create_scorecard,
    AggregationEngine, WeightingConfig, create_aggregation_engine,
    RunEvaluator, PromotionPolicy, create_promotion_policy,
    ClaimValidator, ClaimType, create_claim_validator,
)

from benchmarks.leaderboard import (
    LeaderboardManager, BoardEntry, BoardType, SliceType,
    create_leaderboard_manager, create_entry_from_scorecard,
)


def demo_scorecard():
    """Demo 1: ScoreCard yaratish va foydalanish"""
    print("\n" + "="*60)
    print("Demo 1: ScoreCard - Structured Result Schema")
    print("="*60)
    
    # ScoreCard yaratish
    card = create_scorecard(
        run_id="run_001",
        agent_version="v1.0.0",
        config={"model": "gpt-4", "temperature": 0.7}
    )
    
    # TaskResult qo'shish
    tasks = [
        create_task_result(
            task_id="task_001",
            suite="repo_engineering",
            status=RunStatus.PASSED,
            raw_capability_score=0.95,
            difficulty=DifficultyLevel.EASY.value,
            capabilities=["repo_comprehension", "multi_file_patching"],
            cost_usd=0.05,
            time_seconds=30.0,
            steps=25,
        ),
        create_task_result(
            task_id="task_002",
            suite="self_modification",
            status=RunStatus.PASSED,
            raw_capability_score=0.80,
            difficulty=DifficultyLevel.HARD.value,
            capabilities=["self_modification", "recovery"],
            cost_usd=0.50,
            time_seconds=120.0,
            steps=80,
        ),
        create_task_result(
            task_id="task_003",
            suite="browser_workflow",
            status=RunStatus.FAILED,
            raw_capability_score=0.40,
            difficulty=DifficultyLevel.MEDIUM.value,
            capabilities=["browser_automation"],
            cost_usd=0.15,
            time_seconds=45.0,
            steps=35,
            retries=2,
        ),
        create_task_result(
            task_id="task_004",
            suite="tool_creation_use",
            status=RunStatus.PASSED,
            raw_capability_score=0.75,
            difficulty=DifficultyLevel.FRONTIER.value,
            capabilities=["tool_creation", "planning"],
            cost_usd=1.20,
            time_seconds=300.0,
            steps=150,
        ),
    ]
    
    for task in tasks:
        card.add_task_result(task)
    
    # Natijalarni ko'rish
    print(f"\nRun ID: {card.run_id}")
    print(f"Agent Version: {card.agent_version}")
    print(f"Total Tasks: {len(card.task_results)}")
    
    # Global score
    print(f"\n--- Global Score ---")
    print(f"Global Score: {card.get_global_score():.4f}")
    
    # Suite scores
    print(f"\n--- Per-Suite Scores ---")
    for suite, score in card.get_suite_scores().items():
        print(f"  {suite}: {score:.4f}")
    
    # Capability scores
    print(f"\n--- Per-Capability Scores ---")
    for cap, score in card.get_capability_scores().items():
        print(f"  {cap}: {score:.4f}")
    
    # Difficulty scores
    print(f"\n--- Per-Difficulty Scores ---")
    for diff, score in card.get_difficulty_scores().items():
        print(f"  {diff}: {score:.4f}")
    
    # Dimension scores
    print(f"\n--- Quality Dimensions ---")
    for dim, score in card.get_dimension_scores().items():
        print(f"  {dim}: {score:.4f}")
    
    # Floor checks
    print(f"\n--- Floor Analysis ---")
    print(f"Hard/Frontier Average: {card.get_hard_frontier_average():.4f}")
    print(f"Reliability Rate: {card.get_reliability_rate():.4f}")
    print(f"Integrity Rate: {card.get_integrity_rate():.4f}")
    print(f"Total Cost: ${card.get_total_cost():.2f}")
    
    return card


def demo_aggregation_engine():
    """Demo 2: Aggregation Engine"""
    print("\n" + "="*60)
    print("Demo 2: Weighted Aggregation Engine")
    print("="*60)
    
    # Engine yaratish
    engine = create_aggregation_engine(WeightingConfig.frontier_grade())
    
    # Mock task results
    results = [
        {
            "task_id": "task_001",
            "suite": "repo_engineering",
            "difficulty": "easy",
            "capabilities": ["repo_comprehension"],
            "raw_capability_score": 0.95,
            "reliability_score": 1.0,
            "efficiency_score": 0.9,
            "integrity_score": 1.0,
            "safety_score": 1.0,
            "generalization_score": 0.85,
        },
        {
            "task_id": "task_002",
            "suite": "self_modification",
            "difficulty": "hard",
            "capabilities": ["self_modification"],
            "raw_capability_score": 0.75,
            "reliability_score": 0.85,
            "efficiency_score": 0.7,
            "integrity_score": 1.0,
            "safety_score": 1.0,
            "generalization_score": 0.8,
        },
        {
            "task_id": "task_003",
            "suite": "browser_workflow",
            "difficulty": "medium",
            "capabilities": ["browser_automation"],
            "raw_capability_score": 0.65,
            "reliability_score": 0.9,
            "efficiency_score": 0.8,
            "integrity_score": 0.95,
            "safety_score": 1.0,
            "generalization_score": 0.7,
        },
    ]
    
    # Aggregate
    aggregated = engine.aggregate_task_results(results)
    
    print("\n--- Aggregated Results ---")
    print(f"Global Score: {aggregated['global_score']:.4f}")
    
    print("\nSuite Scores:")
    for suite, score in aggregated['suite_scores'].items():
        print(f"  {suite}: {score:.4f}")
    
    print("\nDifficulty Scores:")
    for diff, score in aggregated['difficulty_scores'].items():
        print(f"  {diff}: {score:.4f}")
    
    print("\nDimension Scores:")
    for dim, score in aggregated['dimension_scores'].items():
        print(f"  {dim}: {score:.4f}")
    
    print("\nFloor Checks:")
    for check, result in aggregated['floor_checks'].items():
        passed = "PASS" if result.get("passed", False) else "FAIL"
        print(f"  [{passed}] {check}")
    
    # Efficiency penalty demo
    penalty = engine.calculate_efficiency_penalty(
        cost_usd=0.50,
        time_seconds=120.0,
        steps=100,
    )
    print(f"\nEfficiency Penalty (cost=$0.50, time=120s, steps=100): {penalty:.4f}")
    
    return aggregated


def demo_promotion_policy():
    """Demo 3: Promotion Policy Engine"""
    print("\n" + "="*60)
    print("Demo 3: Promotion Policy Engine")
    print("="*60)
    
    # Policy yaratish
    policy = create_promotion_policy("frontier")
    evaluator = RunEvaluator(policy)
    
    # Mock scorecard data (yaxshi natija)
    good_scorecard = {
        "global_score": 0.82,
        "dimension_scores": {
            "capability": 0.85,
            "reliability": 0.88,
            "efficiency": 0.75,
            "integrity": 0.98,
            "safety": 0.98,
            "generalization": 0.78,
        },
        "suite_scores": {
            "repo_engineering": 0.85,
            "bug_localization_repair": 0.80,
            "terminal_operations": 0.75,
            "browser_workflow": 0.72,
            "long_horizon_orchestration": 0.70,
            "tool_creation_use": 0.68,
            "self_modification": 0.65,
            "knowledge_refresh": 0.75,
        },
        "difficulty_scores": {
            "easy": 0.92,
            "medium": 0.85,
            "hard": 0.72,
            "frontier": 0.65,
        },
    }
    
    # evaluate
    result = evaluator.evaluate(good_scorecard)
    
    print(f"\n--- Promotion Evaluation ---")
    print(f"Decision: {result.decision.value}")
    print(f"Board: {result.board.value}")
    print(f"Reason: {result.reason}")
    
    print(f"\nPassed Floors: {result.passed_floors}")
    print(f"Failed Floors: {result.failed_floors}")
    
    print(f"\nWarnings:")
    for warning in result.warnings:
        print(f"  - {warning}")
    
    # Yomon natija bilan ham sinab ko'ramiz
    print("\n--- Bad Scorecard Evaluation ---")
    bad_scorecard = {
        "global_score": 0.75,
        "dimension_scores": {
            "capability": 0.80,
            "reliability": 0.65,
            "efficiency": 0.60,
            "integrity": 0.85,
            "safety": 0.95,
            "generalization": 0.65,
        },
        "suite_scores": {
            "self_modification": 0.30,
        },
        "difficulty_scores": {
            "hard": 0.45,
            "frontier": 0.35,
        },
    }
    
    bad_result = evaluator.evaluate(bad_scorecard)
    print(f"Decision: {bad_result.decision.value}")
    print(f"Reason: {bad_result.reason}")
    print(f"Failed Floors: {bad_result.failed_floors}")


def demo_claim_validator():
    """Demo 4: Claim Validator"""
    print("\n" + "="*60)
    print("Demo 4: Claim Validator")
    print("="*60)
    
    # Validator yaratish
    validator = create_claim_validator()
    
    # Test scorecard data
    scorecard = {
        "global_score": 0.82,
        "dimension_scores": {
            "capability": 0.85,
            "reliability": 0.88,
            "efficiency": 0.75,
            "integrity": 0.98,
            "safety": 0.98,
            "generalization": 0.78,
        },
        "suite_scores": {
            "repo_engineering": 0.88,
            "bug_localization_repair": 0.85,
            "terminal_operations": 0.80,
            "browser_workflow": 0.78,
            "long_horizon_orchestration": 0.75,
            "tool_creation_use": 0.70,
            "self_modification": 0.62,
            "knowledge_refresh": 0.80,
        },
        "difficulty_scores": {
            "easy": 0.95,
            "medium": 0.88,
            "hard": 0.75,
            "frontier": 0.68,
        },
    }
    
    # Claims to validate
    claims = [
        ClaimType.NO1_AUTONOMOUS,
        ClaimType.SELF_MODIFYING,
        ClaimType.REPO_ENGINEERING,
    ]
    
    print("\n--- Claim Validation ---")
    results = validator.validate_multiple(claims, scorecard)
    
    for claim, result in results.items():
        status = "VALID" if result.is_valid else "INVALID"
        print(f"\n{claim}: {status}")
        print(f"  Score: {result.score:.2f}")
        print(f"  Reason: {result.reason}")
        
        if result.failed_checks:
            print(f"  Failed: {result.failed_checks}")


def demo_leaderboard():
    """Demo 5: Leaderboard Manager"""
    print("\n" + "="*60)
    print("Demo 5: Leaderboard Manager")
    print("="*60)
    
    # Manager yaratish
    manager = create_leaderboard_manager()
    
    # Entry yaratish
    entries = [
        {
            "run_id": "run_001",
            "agent_version": "v1.0.0",
            "global_score": 0.75,
            "dimension_scores": {
                "capability": 0.80,
                "reliability": 0.75,
                "efficiency": 0.70,
                "integrity": 0.95,
                "safety": 0.98,
                "generalization": 0.70,
            },
            "suite_scores": {
                "repo_engineering": 0.80,
                "self_modification": 0.60,
            },
            "capability_scores": {
                "repo_comprehension": 0.85,
                "self_modification": 0.60,
            },
            "difficulty_scores": {
                "easy": 0.90,
                "hard": 0.60,
            },
            "summary": {
                "total_tasks": 50,
                "passed_tasks": 40,
                "failed_tasks": 10,
            },
            "tags": [],
        },
        {
            "run_id": "run_002",
            "agent_version": "v1.1.0",
            "global_score": 0.82,
            "dimension_scores": {
                "capability": 0.85,
                "reliability": 0.82,
                "efficiency": 0.75,
                "integrity": 0.98,
                "safety": 0.98,
                "generalization": 0.75,
            },
            "suite_scores": {
                "repo_engineering": 0.85,
                "self_modification": 0.65,
            },
            "capability_scores": {
                "repo_comprehension": 0.88,
                "self_modification": 0.65,
            },
            "difficulty_scores": {
                "easy": 0.92,
                "hard": 0.68,
            },
            "summary": {
                "total_tasks": 50,
                "passed_tasks": 43,
                "failed_tasks": 7,
            },
            "tags": [],
        },
    ]
    
    # Add to experimental
    print("\n--- Adding Entries ---")
    for entry_data in entries:
        entry = create_entry_from_scorecard(entry_data)
        manager.add_to_experimental(entry)
        print(f"Added: {entry.run_id} (score: {entry.global_score:.2f})")
    
    # Get experimental board
    print("\n--- Experimental Board ---")
    exp_board = manager.get_experimental_board()
    for i, entry in enumerate(exp_board, 1):
        print(f"  {i}. {entry.run_id}: {entry.global_score:.4f}")
    
    # Get hard/frontier slice
    print("\n--- Hard/Frontier Slice ---")
    hf_board = manager.get_experimental_board(SliceType.HARD_FRONTIER)
    print(f"Entries: {len(hf_board)}")
    
    # Compare runs
    print("\n--- Compare Runs ---")
    comparison = manager.compare_runs("run_001", "run_002")
    print(f"Global Delta: {comparison.get('global_delta', 0):.4f}")
    print("Dimension Deltas:")
    for dim, delta in comparison.get("dimension_deltas", {}).items():
        print(f"  {dim}: {delta:+.4f}")
    
    # Get trend
    print("\n--- Historical Trend ---")
    trend = manager.get_historical_trend("global_score")
    for t in trend:
        print(f"  {t['run_id']}: {t['value']:.4f}")


def main():
    """Run all demos"""
    print("\n" + "="*60)
    print("FRONTIER-GRADE SCORING SYSTEM DEMO")
    print("="*60)
    print("\nBu tizim quyidagilarni taqdim etadi:")
    print("1. ScoreCard: Structured benchmark natijalari")
    print("2. Aggregation Engine: Og'irlikli agregatsiya")
    print("3. Promotion Policy: Promotion qarorlari")
    print("4. Claim Validator: Claim tekshirish")
    print("5. Leaderboard: Stable/experimental boards")
    
    # Demos
    demo_scorecard()
    demo_aggregation_engine()
    demo_promotion_policy()
    demo_claim_validator()
    demo_leaderboard()
    
    print("\n" + "="*60)
    print("DEMO COMPLETE!")
    print("="*60)
    print("\nDefinition of Done (hammasi bajarildi):")
    print("1. Har run structured scorecard bilan saqlanadi. [DONE]")
    print("2. Per-suite, per-capability, per-difficulty scoreboardlar bor. [DONE]")
    print("3. Global score faqat summary, promotion esa floor policy bilan ishlaydi. [DONE]")
    print("4. Stable va experimental board alohida. [DONE]")
    print("5. Integrity/reliability/efficiency alohida ko'rinadi. [DONE]")
    print("6. Claim-aware minimumlar mavjud. [DONE]")


if __name__ == "__main__":
    main()
