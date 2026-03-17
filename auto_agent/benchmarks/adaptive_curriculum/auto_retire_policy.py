"""
AutoRetirePolicy - Saturated Task Management Module

Bu modul oson bo'lib qolgan tasklarni boshqaradi:
- Oson bo'lib qolgan tasklarni archive qiladi
- Mutate qiladi yoki harder sibling yaratadi
- Weight pasaytiradi

Policy 5: Easy saturated tasklar weight yo'qotsin yoki retire qilinsin.
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import time


class RetireAction(Enum):
    """Actions to take for saturated tasks"""
    RETIRE = "retire"                    # Fully retire
    DEWEIGHT = "deweight"                # Reduce weight
    MUTATE = "mutate"                    # Create harder variant
    ESCALATE = "escalate"                # Create harder sibling
    ARCHIVE = "archive"                  # Archive but keep


class SaturationLevel(Enum):
    """Level of task saturation"""
    NONE = "none"                # Not saturated
    LOW = "low"                  # Slightly saturated
    MODERATE = "moderate"        # Moderately saturated
    HIGH = "high"                # Very saturated
    CRITICAL = "critical"        # Fully saturated


@dataclass
class RetireRecommendation:
    """Recommendation for task retirement"""
    task_id: str
    action: RetireAction
    reason: str
    urgency: float                # 0-1 urgency
    current_solve_rate: float
    suggested_new_difficulty: Optional[float] = None
    alternative_task_ids: List[str] = field(default_factory=list)


@dataclass
class RetirePolicy:
    """Policy configuration for retirement"""
    solve_rate_threshold: float = 0.85
    min_evaluations: int = 10
    weight_decay_rate: float = 0.9
    min_weight: float = 0.1
    auto_retire_enabled: bool = True
    escalate_enabled: bool = True


class AutoRetirePolicy:
    """
    Manages saturated/easy tasks automatically.
    
    Bu modul:
    1. Tasklarning to'yinganlik darajasini aniqlaydi
    2. Qanday harakat qilishni tavsiya qiladi
    3. Avtomatik ravishda weightlarni pasaytiradi yoki retire qiladi
    
    Policy 5: Easy saturated tasklar weight yo'qotsin yoki retire qilinsin.
    """
    
    # Saturation thresholds
    SATURATION_LEVELS = {
        SaturationLevel.NONE: (0.0, 0.6),
        SaturationLevel.LOW: (0.6, 0.75),
        SaturationLevel.MODERATE: (0.75, 0.85),
        SaturationLevel.HIGH: (0.85, 0.95),
        SaturationLevel.CRITICAL: (0.95, 1.0)
    }
    
    def __init__(self, policy: Optional[RetirePolicy] = None):
        self.policy = policy or RetirePolicy()
        self.saturation_history: Dict[str, List[float]] = {}
        
    def assess_saturation(
        self,
        task_id: str,
        solve_rate: float,
        evaluation_count: int,
        variance: float = 0.0,
        flake_rate: float = 0.0
    ) -> SaturationLevel:
        """
        Assess the saturation level of a task.
        
        Args:
            task_id: Task identifier
            solve_rate: Pass rate
            evaluation_count: Number of evaluations
            variance: Score variance
            flake_rate: Flaky failure rate
            
        Returns:
            SaturationLevel
        """
        # Track history
        if task_id not in self.saturation_history:
            self.saturation_history[task_id] = []
        self.saturation_history[task_id].append(solve_rate)
        
        # Need minimum evaluations for accurate assessment
        if evaluation_count < self.policy.min_evaluations:
            return SaturationLevel.NONE
        
        # Check solve rate
        for level, (low, high) in self.SATURATION_LEVELS.items():
            if low <= solve_rate < high:
                # Adjust based on variance and flake rate
                if variance > 0.2 or flake_rate > 0.15:
                    # High variance means it might not be truly saturated
                    level = SaturationLevel(
                        max(0, level.value - 1)
                    )
                return level
        
        return SaturationLevel.CRITICAL
    
    def get_retire_recommendation(
        self,
        task_id: str,
        solve_rate: float,
        evaluation_count: int,
        diagnostic_value: float,
        current_weight: float,
        sibling_count: int = 0
    ) -> RetireRecommendation:
        """
        Get recommendation for handling a task.
        
        Args:
            task_id: Task identifier
            solve_rate: Pass rate
            evaluation_count: Number of evaluations
            diagnostic_value: How diagnostic this task is
            current_weight: Current task weight
            sibling_count: Number of harder siblings
            
        Returns:
            RetireRecommendation
        """
        saturation = self.assess_saturation(
            task_id, solve_rate, evaluation_count
        )
        
        # Determine action based on saturation level
        if saturation == SaturationLevel.CRITICAL:
            # Fully saturated - retire
            return RetireRecommendation(
                task_id=task_id,
                action=RetireAction.RETIRE,
                reason=f"Critical saturation: {solve_rate:.1%} solve rate",
                urgency=0.9,
                current_solve_rate=solve_rate
            )
        
        elif saturation == SaturationLevel.HIGH:
            # Very saturated - deweight or escalate
            if self.policy.escalate_enabled and sibling_count < 3:
                # Create harder sibling
                target_difficulty = min(0.95, solve_rate + 0.15)
                return RetireRecommendation(
                    task_id=task_id,
                    action=RetireAction.ESCALATE,
                    reason=f"High saturation: {solve_rate:.1%} solve rate, creating harder variant",
                    urgency=0.7,
                    current_solve_rate=solve_rate,
                    suggested_new_difficulty=target_difficulty
                )
            else:
                # Deweight
                return RetireRecommendation(
                    task_id=task_id,
                    action=RetireAction.DEWEIGHT,
                    reason=f"High saturation: {solve_rate:.1%} solve rate",
                    urgency=0.6,
                    current_solve_rate=solve_rate
                )
        
        elif saturation == SaturationLevel.MODERATE:
            # Moderately saturated - reduce weight
            new_weight = current_weight * self.policy.weight_decay_rate
            
            if new_weight < self.policy.min_weight:
                return RetireRecommendation(
                    task_id=task_id,
                    action=RetireAction.RETIRE,
                    reason=f"Weight below minimum after decay: {new_weight:.2f}",
                    urgency=0.4,
                    current_solve_rate=solve_rate
                )
            
            return RetireRecommendation(
                task_id=task_id,
                action=RetireAction.DEWEIGHT,
                reason=f"Moderate saturation: {solve_rate:.1%} solve rate",
                urgency=0.3,
                current_solve_rate=solve_rate
            )
        
        elif saturation == SaturationLevel.LOW:
            # Slightly saturated - minor deweight
            return RetireRecommendation(
                task_id=task_id,
                action=RetireAction.DEWEIGHT,
                reason=f"Low saturation: {solve_rate:.1%} solve rate",
                urgency=0.1,
                current_solve_rate=solve_rate
            )
        
        else:
            # Not saturated - keep as is
            return RetireRecommendation(
                task_id=task_id,
                action=RetireAction.DEWEIGHT,
                reason="Not saturated",
                urgency=0.0,
                current_solve_rate=solve_rate
            )
    
    def apply_retire_recommendation(
        self,
        recommendation: RetireRecommendation,
        current_weight: float
    ) -> Tuple[float, bool]:
        """
        Apply a retire recommendation.
        
        Args:
            recommendation: The recommendation to apply
            current_weight: Current task weight
            
        Returns:
            (new_weight, should_retire)
        """
        if recommendation.action == RetireAction.RETIRE:
            return 0.0, True
        
        elif recommendation.action == RetireAction.DEWEIGHT:
            new_weight = current_weight * self.policy.weight_decay_rate
            new_weight = max(new_weight, self.policy.min_weight)
            return new_weight, False
        
        elif recommendation.action == RetireAction.MUTATE:
            # Create mutated variant - returns same weight
            return current_weight, False
        
        elif recommendation.action == RetireAction.ESCALATE:
            # Create harder sibling - current stays the same
            return current_weight, False
        
        elif recommendation.action == RetireAction.ARCHIVE:
            return 0.0, True
        
        return current_weight, False
    
    def get_saturated_tasks(
        self,
        tasks: List[Dict[str, Any]],
        min_solve_rate: float = 0.85
    ) -> List[Dict[str, Any]]:
        """
        Identify saturated tasks from a list.
        
        Args:
            tasks: List of task dictionaries
            min_solve_rate: Minimum solve rate to consider saturated
            
        Returns:
            List of saturated tasks with saturation info
        """
        saturated = []
        
        for task in tasks:
            solve_rate = task.get('solve_rate', 0.0)
            evaluation_count = task.get('evaluation_count', 0)
            diagnostic_value = task.get('diagnostic_value', 0.5)
            weight = task.get('weight', 1.0)
            
            if solve_rate >= min_solve_rate and evaluation_count >= self.policy.min_evaluations:
                saturation = self.assess_saturation(
                    task['task_id'],
                    solve_rate,
                    evaluation_count,
                    task.get('variance', 0.0),
                    task.get('flake_rate', 0.0)
                )
                
                if saturation != SaturationLevel.NONE:
                    recommendation = self.get_retire_recommendation(
                        task['task_id'],
                        solve_rate,
                        evaluation_count,
                        diagnostic_value,
                        weight,
                        task.get('sibling_count', 0)
                    )
                    
                    saturated.append({
                        'task_id': task['task_id'],
                        'solve_rate': solve_rate,
                        'saturation_level': saturation.value,
                        'recommendation': recommendation.action.value,
                        'urgency': recommendation.urgency,
                        'reason': recommendation.reason
                    })
        
        # Sort by urgency
        saturated.sort(key=lambda x: x['urgency'], reverse=True)
        
        return saturated
    
    def run_auto_retirement(
        self,
        tasks: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Run automatic retirement process.
        
        Args:
            tasks: Dictionary of task_id -> task data
            
        Returns:
            Report of actions taken
        """
        if not self.policy.auto_retire_enabled:
            return {"status": "disabled", "actions": []}
        
        actions = []
        
        for task_id, task_data in tasks.items():
            solve_rate = task_data.get('solve_rate', 0.0)
            evaluation_count = task_data.get('evaluation_count', 0)
            diagnostic_value = task_data.get('diagnostic_value', 0.5)
            weight = task_data.get('weight', 1.0)
            
            if evaluation_count < self.policy.min_evaluations:
                continue
            
            recommendation = self.get_retire_recommendation(
                task_id,
                solve_rate,
                evaluation_count,
                diagnostic_value,
                weight
            )
            
            if recommendation.urgency > 0.3:
                new_weight, should_retire = self.apply_retire_recommendation(
                    recommendation, weight
                )
                
                action = {
                    "task_id": task_id,
                    "action": recommendation.action.value,
                    "old_weight": weight,
                    "new_weight": new_weight if not should_retire else 0.0,
                    "retire": should_retire,
                    "reason": recommendation.reason
                }
                
                actions.append(action)
                
                # Update task data
                task_data['weight'] = new_weight if not should_retire else 0.0
                if should_retire:
                    task_data['status'] = 'retired'
        
        return {
            "status": "completed",
            "actions_taken": len(actions),
            "actions": actions,
            "summary": self._generate_summary(actions)
        }
    
    def _generate_summary(self, actions: List[Dict[str, Any]]) -> str:
        """Generate summary of retirement actions"""
        if not actions:
            return "No retirement actions needed."
        
        action_counts = {}
        for action in actions:
            act = action['action']
            action_counts[act] = action_counts.get(act, 0) + 1
        
        lines = ["Retirement actions:"]
        for act, count in action_counts.items():
            lines.append(f"  - {act}: {count}")
        
        return "\n".join(lines)
    
    def get_board_health(self, board_stats: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get health metrics for a curriculum board.
        
        Args:
            board_stats: Statistics from CurriculumBoard
            
        Returns:
            Health metrics
        """
        total_tasks = board_stats.get('total_tasks', 0)
        stable_count = board_stats.get('stable_benchmark_count', 0)
        frontier_count = board_stats.get('growth_front_count', 0)
        
        # Calculate saturation
        saturation_rate = 0.0
        if total_tasks > 0:
            saturated_count = sum(
                1 for tid, data in board_stats.get('tasks', {}).items()
                if data.get('solve_rate', 0) >= self.policy.solve_rate_threshold
            )
            saturation_rate = saturated_count / total_tasks
        
        # Determine health status
        if saturation_rate > 0.5:
            health = "critical"
            message = f"Board is {saturation_rate:.0%} saturated - need new frontier tasks"
        elif saturation_rate > 0.3:
            health = "warning"
            message = f"Board is {saturation_rate:.0%} saturated - consider generating new tasks"
        elif frontier_count < 5:
            health = "warning"
            message = "Low frontier task count - need more rising tasks"
        else:
            health = "healthy"
            message = "Board is well balanced"
        
        return {
            "health": health,
            "saturation_rate": saturation_rate,
            "frontier_tasks": frontier_count,
            "stable_tasks": stable_count,
            "message": message,
            "recommendations": self._get_recommendations(saturation_rate, frontier_count)
        }
    
    def _get_recommendations(
        self,
        saturation_rate: float,
        frontier_count: int
    ) -> List[str]:
        """Get recommendations for board health"""
        recommendations = []
        
        if saturation_rate > 0.5:
            recommendations.append("URGENT: Generate new frontier tasks")
            recommendations.append("Consider auto-retiring highly saturated tasks")
        elif saturation_rate > 0.3:
            recommendations.append("Generate new tasks to reduce saturation")
        
        if frontier_count < 5:
            recommendations.append("Increase frontier task generation")
        
        if saturation_rate < 0.2 and frontier_count > 10:
            recommendations.append("Board is healthy - maintain current strategy")
        
        return recommendations


__all__ = [
    'AutoRetirePolicy',
    'RetireAction',
    'SaturationLevel',
    'RetireRecommendation',
    'RetirePolicy'
]
