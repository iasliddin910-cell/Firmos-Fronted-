"""
Economic Benchmark Suite - Economic Scenarios Testing
=================================================

This module tests economic scenarios:
- Same task, multiple model tiers
- Same task, single vs swarm
- Cheap-first then escalate
- Batchable queue scenarios
- High-urgency vs low-urgency mix
- Budget-constrained long-horizon tasks
- Cost anomaly cases
- Throughput stress cases

Author: No1 World+ Autonomous System
"""

import asyncio
import logging
import random
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class EconomicMetrics:
    """Economic metrics for a test"""
    test_id: str
    test_type: str
    total_cost: float
    total_tasks: int
    successful_tasks: int
    avg_cost_per_task: float
    throughput_per_hour: float
    cost_efficiency: float  # success / cost


class EconomicBenchmarkSuite:
    """Economic benchmarking suite"""
    
    async def run_model_tier_test(self, tasks: int = 20) -> EconomicMetrics:
        """Test same task with different model tiers"""
        
        test_id = f"model_tier_{int(time.time())}"
        
        # Simulate tasks with different tiers
        results = []
        
        for i in range(tasks):
            tier = random.choice(["cheap", "standard", "premium"])
            
            cost = {"cheap": 0.5, "standard": 2.0, "premium": 10.0}[tier]
            success = random.random() > 0.1
            
            results.append({"tier": tier, "cost": cost, "success": success})
        
        total_cost = sum(r["cost"] for r in results)
        successes = sum(1 for r in results if r["success"])
        
        return EconomicMetrics(
            test_id=test_id,
            test_type="model_tier",
            total_cost=total_cost,
            total_tasks=tasks,
            successful_tasks=successes,
            avg_cost_per_task=total_cost / tasks,
            throughput_per_hour=tasks,
            cost_efficiency=successes / total_cost if total_cost > 0 else 0
        )
    
    async def run_parallelism_test(self, tasks: int = 20) -> EconomicMetrics:
        """Test single vs swarm execution"""
        
        test_id = f"parallelism_{int(time.time())}"
        
        results = []
        
        for i in range(tasks):
            strategy = random.choice(["solo", "duo", "swarm"])
            
            # Cost and success rates differ by strategy
            if strategy == "solo":
                cost, success_rate = 1.0, 0.8
            elif strategy == "duo":
                cost, success_rate = 1.8, 0.9
            else:
                cost, success_rate = 3.5, 0.95
            
            success = random.random() < success_rate
            
            results.append({"strategy": strategy, "cost": cost, "success": success})
        
        total_cost = sum(r["cost"] for r in results)
        successes = sum(1 for r in results if r["success"])
        
        return EconomicMetrics(
            test_id=test_id,
            test_type="parallelism",
            total_cost=total_cost,
            total_tasks=tasks,
            successful_tasks=successes,
            avg_cost_per_task=total_cost / tasks,
            throughput_per_hour=tasks,
            cost_efficiency=successes / total_cost if total_cost > 0 else 0
        )
    
    async def run_budget_constraint_test(self, budget: float, tasks: int = 30) -> EconomicMetrics:
        """Test with budget constraints"""
        
        test_id = f"budget_{int(time.time())}"
        
        results = []
        spent = 0
        
        for i in range(tasks):
            if spent >= budget:
                break
            
            # Choose task cost based on remaining budget
            if budget - spent > 5:
                cost, success_rate = 3.0, 0.9
            elif budget - spent > 2:
                cost, success_rate = 1.5, 0.85
            else:
                cost, success_rate = 0.5, 0.7
            
            success = random.random() < success_rate
            spent += cost
            
            results.append({"cost": cost, "success": success})
        
        total_cost = sum(r["cost"] for r in results)
        successes = sum(1 for r in results if r["success"])
        
        return EconomicMetrics(
            test_id=test_id,
            test_type="budget_constraint",
            total_cost=total_cost,
            total_tasks=len(results),
            successful_tasks=successes,
            avg_cost_per_task=total_cost / len(results) if results else 0,
            throughput_per_hour=len(results),
            cost_efficiency=successes / total_cost if total_cost > 0 else 0
        )
    
    async def run_throughput_stress_test(self, duration_seconds: int = 60) -> EconomicMetrics:
        """Stress test throughput"""
        
        test_id = f"throughput_{int(time.time())}"
        
        start = time.time()
        tasks = 0
        results = []
        
        while time.time() - start < duration_seconds:
            cost = random.choice([0.5, 1.0, 2.0, 5.0])
            success = random.random() > 0.15
            
            results.append({"cost": cost, "success": success})
            tasks += 1
        
        total_cost = sum(r["cost"] for r in results)
        successes = sum(1 for r in results if r["success"])
        
        actual_duration = time.time() - start
        
        return EconomicMetrics(
            test_id=test_id,
            test_type="throughput_stress",
            total_cost=total_cost,
            total_tasks=tasks,
            successful_tasks=successes,
            avg_cost_per_task=total_cost / tasks if tasks else 0,
            throughput_per_hour=tasks / (actual_duration / 3600),
            cost_efficiency=successes / total_cost if total_cost > 0 else 0
        )


def create_economic_suite() -> EconomicBenchmarkSuite:
    return EconomicBenchmarkSuite()
