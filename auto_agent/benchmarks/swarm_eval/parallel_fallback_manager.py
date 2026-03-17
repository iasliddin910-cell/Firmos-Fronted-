"""
ParallelFallbackManager - Partial Failure Recovery

Bu modul parallel branch yiqilganda qilish kerakligini boshqaradi:
- reassign
- drop branch
- serialize fallback
- partial salvage

Policy 5: Partial failure recovery score'da alohida ko'rinadi.
"""

from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import time


class FallbackStrategy(Enum):
    """Fallback strategies for failed workers"""
    REASSIGN = "reassign"           # Assign to different worker
    DROP_BRANCH = "drop_branch"    # Drop the failed branch
    SERIALIZE = "serialize"         # Fall back to single-agent
    PARTIAL_SALVAGE = "partial_salvage"  # Use partial results
    RETRY = "retry"                # Retry the failed task


@dataclass
class FailureEvent:
    """A worker failure event"""
    worker_id: str
    node_id: str
    failure_time: float
    failure_type: str
    error_message: str
    partial_output: Optional[Dict[str, Any]] = None


@dataclass
class FallbackAction:
    """Action taken as fallback"""
    strategy: FallbackStrategy
    target_worker: Optional[str]
    description: str
    success: bool
    time_taken: float


@dataclass
class RecoveryResult:
    """Result of recovery attempt"""
    original_failure: FailureEvent
    fallback_action: FallbackAction
    recovered: bool
    total_time: float
    quality_preserved: bool


class ParallelFallbackManager:
    """
    Manages fallback when parallel branches fail.
    
    Policy 5: Partial failure recovery score'da alohida ko'rinadi.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.failure_history: List[FailureEvent] = []
        self.recovery_history: List[RecoveryResult] = []
        
    def handle_failure(
        self,
        failure: FailureEvent,
        available_workers: List[str],
        partial_results: Dict[str, Any],
        recovery_func: Optional[Callable] = None
    ) -> FallbackAction:
        """
        Handle a worker failure and determine fallback action.
        
        Args:
            failure: The failure event
            available_workers: List of available workers
            partial_results: Partial results from failed worker
            recovery_func: Optional custom recovery function
            
        Returns:
            FallbackAction to take
        """
        start_time = time.time()
        
        # Record failure
        self.failure_history.append(failure)
        
        # Determine best strategy
        strategy = self._select_strategy(
            failure, available_workers, partial_results
        )
        
        # Execute fallback
        action = self._execute_fallback(
            strategy, failure, available_workers, partial_results, recovery_func
        )
        
        action.time_taken = time.time() - start_time
        
        # Record recovery
        recovery = RecoveryResult(
            original_failure=failure,
            fallback_action=action,
            recovered=action.success,
            total_time=action.time_taken,
            quality_preserved=action.success and len(partial_results) > 0
        )
        self.recovery_history.append(recovery)
        
        return action
    
    def _select_strategy(
        self,
        failure: FailureEvent,
        available_workers: List[str],
        partial_results: Dict[str, Any]
    ) -> FallbackStrategy:
        """Select the best fallback strategy"""
        # Check if we have partial results
        has_partial = partial_results and len(partial_results) > 0
        
        # Check if we have available workers
        has_workers = available_workers and len(available_workers) > 0
        
        if has_partial:
            # Can salvage partial results
            return FallbackStrategy.PARTIAL_SALVAGE
        elif has_workers:
            # Can reassign
            return FallbackStrategy.REASSIGN
        else:
            # Must serialize
            return FallbackStrategy.SERIALIZE
    
    def _execute_fallback(
        self,
        strategy: FallbackStrategy,
        failure: FailureEvent,
        available_workers: List[str],
        partial_results: Dict[str, Any],
        recovery_func: Optional[Callable]
    ) -> FallbackAction:
        """Execute the selected fallback strategy"""
        if strategy == FallbackStrategy.REASSIGN:
            target = available_workers[0] if available_workers else None
            return FallbackAction(
                strategy=strategy,
                target_worker=target,
                description=f"Reassign {failure.node_id} to {target}",
                success=target is not None,
                time_taken=0.0
            )
        
        elif strategy == FallbackStrategy.DROP_BRANCH:
            return FallbackAction(
                strategy=strategy,
                target_worker=None,
                description=f"Drop failed branch {failure.node_id}",
                success=True,
                time_taken=0.0
            )
        
        elif strategy == FallbackStrategy.PARTIAL_SALVAGE:
            return FallbackAction(
                strategy=strategy,
                target_worker=None,
                description=f"Salvage partial results from {failure.worker_id}",
                success=len(partial_results) > 0,
                time_taken=0.0
            )
        
        elif strategy == FallbackStrategy.SERIALIZE:
            return FallbackAction(
                strategy=strategy,
                target_worker="single_agent",
                description="Fallback to single-agent execution",
                success=True,
                time_taken=0.0
            )
        
        elif strategy == FallbackStrategy.RETRY:
            return FallbackAction(
                strategy=strategy,
                target_worker=failure.worker_id,
                description=f"Retry {failure.node_id} with same worker",
                success=True,
                time_taken=0.0
            )
        
        # Default
        return FallbackAction(
            strategy=strategy,
            target_worker=None,
            description="No fallback action",
            success=False,
            time_taken=0.0
        )
    
    def get_recovery_stats(self) -> Dict[str, Any]:
        """Get recovery statistics"""
        if not self.recovery_history:
            return {
                "total_failures": len(self.failure_history),
                "recoveries": 0,
                "recovery_rate": 0.0
            }
        
        total = len(self.recovery_history)
        recovered = sum(1 for r in self.recovery_history if r.recovered)
        quality_preserved = sum(1 for r in self.recovery_history if r.quality_preserved)
        
        strategy_usage = {}
        for recovery in self.recovery_history:
            strategy = recovery.fallback_action.strategy.value
            strategy_usage[strategy] = strategy_usage.get(strategy, 0) + 1
        
        return {
            "total_failures": len(self.failure_history),
            "recoveries": total,
            "recovery_rate": recovered / total if total > 0 else 0.0,
            "quality_preserved_rate": quality_preserved / total if total > 0 else 0.0,
            "strategy_usage": strategy_usage,
            "avg_recovery_time": sum(r.total_time for r in self.recovery_history) / total if total > 0 else 0.0
        }


__all__ = [
    'ParallelFallbackManager',
    'FallbackStrategy',
    'FailureEvent',
    'FallbackAction',
    'RecoveryResult'
]
