"""
RoleRouterEvaluator - Role Routing Quality Evaluation

Bu modul qaysi task qaysi workerga yuborilganini to'g'ri baholaydi:
- patch design criticga ketmasligi kerak
- browser triage executor/researcher kombinatsiyasiga ketishi mumkin
- tool creation tool builderga borishi kerak
- final acceptance verifierda bo'lishi kerak

Policy 5: Partial failure recovery score'da alohida ko'rinadi.
"""

from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum


class RoutingDecision(Enum):
    """Routing decision outcomes"""
    CORRECT = "correct"
    SUBOPTIMAL = "suboptimal"
    INCORRECT = "incorrect"


@dataclass
class RoleRoute:
    """A single role routing decision"""
    task: str
    assigned_role: str
    optimal_role: str
    decision: RoutingDecision
    reasoning: str
    score: float


class RoleRouterEvaluator:
    """
    Evaluates role routing quality.
    
    Qaysi worker qaysi taskni olishi kerakligini baholaydi.
    """
    
    # Role-task mappings
    ROLE_TASK_MAPPINGS = {
        "researcher": {
            "keywords": ["research", "analyze", "investigate", "find", "search", "explore", "diagnose"],
            "weight": 1.0
        },
        "executor": {
            "keywords": ["implement", "execute", "run", "patch", "fix", "create", "build", "write"],
            "weight": 1.0
        },
        "verifier": {
            "keywords": ["verify", "test", "check", "validate", "ensure", "confirm", "pass"],
            "weight": 1.0
        },
        "critic": {
            "keywords": ["review", "critique", "assess", "evaluate", "judge", "analyze quality"],
            "weight": 1.0
        },
        "planner": {
            "keywords": ["plan", "design", "organize", "coordinate", "schedule", "strategy"],
            "weight": 1.0
        },
        "tool_builder": {
            "keywords": ["build tool", "create tool", "implement tool", "tool definition", "new tool"],
            "weight": 1.0
        },
        "merger": {
            "keywords": ["merge", "combine", "integrate", "unite", "consolidate"],
            "weight": 1.0
        },
        "coordinator": {
            "keywords": ["coordinate", "manage", "oversee", "delegate", "route"],
            "weight": 1.0
        }
    }
    
    # Anti-patterns (wrong routing)
    ANTI_PATTERNS = {
        "researcher": ["patch", "fix", "implement", "build tool"],
        "executor": ["plan", "design", "review quality"],
        "verifier": ["research", "find", "implement"],
        "critic": ["implement", "execute", "build"],
        "planner": ["execute", "implement", "verify"],
        "tool_builder": ["verify", "test", "review"],
        "merger": ["research", "implement"],
        "coordinator": ["implement", "fix", "patch"]
    }
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.routes: List[RoleRoute] = []
        
    def evaluate_routing(
        self,
        task: str,
        assigned_role: str
    ) -> RoleRoute:
        """Evaluate a single routing decision"""
        # Find optimal role
        optimal_role = self._find_optimal_role(task)
        
        # Determine decision
        if assigned_role == optimal_role:
            decision = RoutingDecision.CORRECT
            score = 1.0
            reasoning = f"Correctly assigned to {assigned_role}"
        elif self._is_suboptimal(assigned_role, task):
            decision = RoutingDecision.SUBOPTIMAL
            score = 0.5
            reasoning = f"Suboptimal: {assigned_role} could handle but {optimal_role} is better"
        else:
            decision = RoutingDecision.INCORRECT
            score = 0.0
            reasoning = f"Should be assigned to {optimal_role}, not {assigned_role}"
        
        route = RoleRoute(
            task=task,
            assigned_role=assigned_role,
            optimal_role=optimal_role,
            decision=decision,
            reasoning=reasoning,
            score=score
        )
        
        self.routes.append(route)
        return route
    
    def _find_optimal_role(self, task: str) -> str:
        """Find the optimal role for a task"""
        task_lower = task.lower()
        best_role = "executor"  # default
        best_score = 0.0
        
        for role, mapping in self.ROLE_TASK_MAPPINGS.items():
            score = 0.0
            for keyword in mapping["keywords"]:
                if keyword in task_lower:
                    score += mapping["weight"]
            
            if score > best_score:
                best_score = score
                best_role = role
        
        return best_role
    
    def _is_suboptimal(self, role: str, task: str) -> bool:
        """Check if routing is suboptimal"""
        task_lower = task.lower()
        
        # Check if role can handle but isn't optimal
        for optimal_role, mapping in self.ROLE_TASK_MAPPINGS.items():
            if role != optimal_role:
                for keyword in mapping["keywords"]:
                    if keyword in task_lower:
                        # Role can partially handle
                        return True
        
        return False
    
    def evaluate_batch(
        self,
        routes: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """Evaluate multiple routing decisions"""
        results = []
        
        for route_data in routes:
            result = self.evaluate_routing(
                route_data["task"],
                route_data["assigned_role"]
            )
            results.append(result)
        
        # Calculate aggregate metrics
        total = len(results)
        correct = sum(1 for r in results if r.decision == RoutingDecision.CORRECT)
        suboptimal = sum(1 for r in results if r.decision == RoutingDecision.SUBOPTIMAL)
        incorrect = sum(1 for r in results if r.decision == RoutingDecision.INCORRECT)
        
        avg_score = sum(r.score for r in results) / total if total > 0 else 0.0
        
        return {
            "total_routes": total,
            "correct": correct,
            "suboptimal": suboptimal,
            "incorrect": incorrect,
            "accuracy": correct / total if total > 0 else 0.0,
            "average_score": avg_score,
            "routing_quality": self._score_to_quality(avg_score)
        }
    
    def _score_to_quality(self, score: float) -> str:
        """Convert score to quality label"""
        if score >= 0.9:
            return "excellent"
        elif score >= 0.7:
            return "good"
        elif score >= 0.5:
            return "fair"
        else:
            return "poor"
    
    def get_routing_report(self) -> Dict[str, Any]:
        """Get routing evaluation report"""
        if not self.routes:
            return {"total_routes": 0}
        
        return self.evaluate_batch([
            {"task": r.task, "assigned_role": r.assigned_role}
            for r in self.routes
        ])


__all__ = [
    'RoleRouterEvaluator',
    'RoutingDecision',
    'RoleRoute'
]
