"""
TaskMutator - Task Mutation Engine

Bu modul mavjud benchmark tasklaridan yangi variantlar yaratadi.
Mutation turlari:
- config o'zgartirish
- symptom o'zgartirish
- repo layout o'zgartirish
- hidden edge case qo'shish
- time budget qisqartirish
- misdirection (ko'rsatma berish)
- resource constraint o'zgartirish

Policy 3: Auto-generated tasklar stable boardga to'g'ridan-to'g'ri kirmasin.
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import random
import hashlib
import json


class MutationType(Enum):
    """Types of task mutations"""
    CONFIG_CHANGE = "config_change"
    SYMPTOM_SHIFT = "symptom_shift"
    REPO_RESTRUCTURE = "repo_restructure"
    EDGE_CASE_INJECT = "edge_case_inject"
    TIME_BUDGET_TIGHTEN = "time_budget_tighten"
    LATENCY_INJECT = "latency_inject"
    MISDIRECTION = "misdirection"
    RESOURCE_CONSTRAINT = "resource_constraint"
    AMBIGUITY_ADD = "ambiguity_add"
    PARTIAL_INFO = "partial_info"
    NOISE_INJECT = "noise_inject"
    DEPENDENCY_SHIFT = "dependency_shift"


class DifficultyImpact(Enum):
    """Impact on task difficulty"""
    SIGNIFICANT_INCREASE = "significant_increase"
    MODERATE_INCREASE = "moderate_increase"
    SLIGHT_INCREASE = "slight_increase"
    NO_CHANGE = "no_change"
    SLIGHT_DECREASE = "slight_decrease"


@dataclass
class MutationConfig:
    """Configuration for a specific mutation"""
    mutation_type: MutationType
    parameters: Dict[str, Any]
    difficulty_impact: DifficultyImpact
    expected_solve_rate_change: float  # e.g., -0.1 means 10% harder


@dataclass
class MutatedTask:
    """A task that has been mutated"""
    original_task_id: str
    new_task_id: str
    mutation_type: MutationType
    changes: List[str]
    difficulty_impact: DifficultyImpact
    predicted_solve_rate: float
    mutation_hash: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskTemplate:
    """Template for a task that can be mutated"""
    task_id: str
    task_type: str
    description: str
    difficulty: float
    capabilities_required: List[str]
    config: Dict[str, Any]
    expected_solution: Optional[str] = None
    hints: List[str] = field(default_factory=list)
    constraints: Dict[str, Any] = field(default_factory=dict)


class TaskMutator:
    """
    Mutates existing tasks to create new variants.
    
    Bu modul benchmarkni jonlantiradi va yangi tasklar yaratadi
    mavjud tasklardan controlled mutation orqali.
    """
    
    # Mutation parameters
    MAX_MUTATIONS_PER_TASK = 3
    DIFFICULTY_VARIANCE = 0.15
    
    # Templates for different mutation types
    MUTATION_TEMPLATES = {
        MutationType.CONFIG_CHANGE: [
            {"param": "timeout", "range": [5, 30], "impact": DifficultyImpact.MODERATE_INCREASE},
            {"param": "max_retries", "range": [1, 5], "impact": DifficultyImpact.SLIGHT_INCREASE},
            {"param": "parallel_workers", "range": [1, 8], "impact": DifficultyImpact.MODERATE_INCREASE},
        ],
        MutationType.SYMPTOM_SHIFT: [
            {"from": "error message", "to": "silent failure", "impact": DifficultyImpact.SIGNIFICANT_INCREASE},
            {"from": "crash", "to": "hang", "impact": DifficultyImpact.MODERATE_INCREASE},
            {"from": "clear error", "to": "misleading error", "impact": DifficultyImpact.SIGNIFICANT_INCREASE},
        ],
        MutationType.TIME_BUDGET_TIGHTEN: [
            {"factor": 0.5, "impact": DifficultyImpact.SIGNIFICANT_INCREASE},
            {"factor": 0.7, "impact": DifficultyImpact.MODERATE_INCREASE},
            {"factor": 0.8, "impact": DifficultyImpact.SLIGHT_INCREASE},
        ],
        MutationType.AMBIGUITY_ADD: [
            {"type": "unclear_requirement", "impact": DifficultyImpact.MODERATE_INCREASE},
            {"type": "multiple_valid_solutions", "impact": DifficultyImpact.SLIGHT_INCREASE},
            {"type": "conflicting_hints", "impact": DifficultyImpact.SIGNIFICANT_INCREASE},
        ],
        MutationType.PARTIAL_INFO: [
            {"missing": "error_details", "impact": DifficultyImpact.MODERATE_INCREASE},
            {"missing": "context", "impact": DifficultyImpact.SLIGHT_INCREASE},
            {"missing": "expected_output", "impact": DifficultyImpact.SIGNIFICANT_INCREASE},
        ],
        MutationType.NOISE_INJECT: [
            {"type": "extra_files", "count": [3, 10], "impact": DifficultyImpact.SLIGHT_INCREASE},
            {"type": "misleading_comments", "count": [2, 5], "impact": DifficultyImpact.MODERATE_INCREASE},
            {"type": "fake_errors", "count": [1, 3], "impact": DifficultyImpact.SLIGHT_INCREASE},
        ],
    }
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.rng = random.Random(self.config.get('seed', 42))
        
    def mutate_task(
        self,
        template: TaskTemplate,
        mutation_types: Optional[List[MutationType]] = None,
        target_difficulty: Optional[float] = None
    ) -> MutatedTask:
        """
        Create a mutated variant of a task.
        
        Args:
            template: Original task template
            mutation_types: Types of mutations to apply (random if not specified)
            target_difficulty: Target difficulty for the mutated task
            
        Returns:
            MutatedTask with new configuration
        """
        if mutation_types is None:
            mutation_types = self._select_mutations(template)
        
        changes = []
        new_config = template.config.copy()
        difficulty_delta = 0.0
        
        for mut_type in mutation_types[:self.MAX_MUTATIONS_PER_TASK]:
            config_delta, change_desc = self._apply_mutation(
                mut_type, new_config, template
            )
            changes.append(change_desc)
            difficulty_delta += config_delta
        
        # Calculate new task ID
        mutation_hash = self._generate_mutation_hash(template.task_id, mutation_types)
        new_task_id = f"{template.task_id}_mut_{mutation_hash[:8]}"
        
        # Predict new solve rate
        predicted_solve_rate = max(0.01, min(0.99, 
            template.difficulty - difficulty_delta
        ))
        
        # Determine difficulty impact
        if difficulty_delta > 0.1:
            difficulty_impact = DifficultyImpact.SIGNIFICANT_INCREASE
        elif difficulty_delta > 0.05:
            difficulty_impact = DifficultyImpact.MODERATE_INCREASE
        elif difficulty_delta > 0:
            difficulty_impact = DifficultyImpact.SLIGHT_INCREASE
        else:
            difficulty_impact = DifficultyImpact.NO_CHANGE
        
        return MutatedTask(
            original_task_id=template.task_id,
            new_task_id=new_task_id,
            mutation_type=mutation_types[0] if mutation_types else MutationType.CONFIG_CHANGE,
            changes=changes,
            difficulty_impact=difficulty_impact,
            predicted_solve_rate=predicted_solve_rate,
            mutation_hash=mutation_hash,
            metadata={
                "original_difficulty": template.difficulty,
                "difficulty_delta": difficulty_delta,
                "mutation_types": [m.value for m in mutation_types]
            }
        )
    
    def mutate_task_batch(
        self,
        templates: List[TaskTemplate],
        mutations_per_task: int = 3,
        difficulty_target: Optional[float] = None
    ) -> List[MutatedTask]:
        """
        Create multiple mutated variants from a list of templates.
        
        Args:
            templates: Original task templates
            mutations_per_task: Number of variants to create per template
            difficulty_target: Target difficulty for all variants
            
        Returns:
            List of MutatedTask variants
        """
        variants = []
        
        for template in templates:
            # Select diverse mutation types
            mutation_types_list = self._generate_mutation_combinations(
                mutations_per_task
            )
            
            for mutation_types in mutation_types_list:
                variant = self.mutate_task(
                    template,
                    mutation_types,
                    difficulty_target
                )
                variants.append(variant)
        
        return variants
    
    def create_sibling_ladder(
        self,
        template: TaskTemplate,
        levels: int = 4
    ) -> List[MutatedTask]:
        """
        Create a difficulty ladder (sibling chain) for a task.
        
        Creates: easy -> medium -> hard -> frontier variants
        
        Args:
            template: Original task template
            levels: Number of difficulty levels
            
        Returns:
            List of MutatedTask from easy to hard
        """
        ladder = []
        base_difficulty = template.difficulty
        
        # Create difficulty progression
        if base_difficulty < 0.3:
            # Easy base - create harder variants
            difficulties = [base_difficulty + i * 0.15 for i in range(levels)]
        elif base_difficulty > 0.7:
            # Hard base - create easier variants first
            difficulties = [base_difficulty - i * 0.15 for i in range(levels)][::-1]
        else:
            # Medium base - create both directions
            difficulties = [
                base_difficulty - 0.1,
                base_difficulty,
                base_difficulty + 0.1,
                base_difficulty + 0.2
            ][:levels]
        
        for i, target_diff in enumerate(difficulties):
            # Select appropriate mutations for this difficulty level
            mutation_types = self._select_mutations_for_difficulty(target_diff, i)
            
            variant = self.mutate_task(
                template,
                mutation_types,
                target_diff
            )
            ladder.append(variant)
        
        return ladder
    
    def _select_mutations(
        self,
        template: TaskTemplate
    ) -> List[MutationType]:
        """Select appropriate mutations for a task"""
        # Weight mutations based on task type
        weights = {
            MutationType.CONFIG_CHANGE: 0.2,
            MutationType.SYMPTOM_SHIFT: 0.15,
            MutationType.EDGE_CASE_INJECT: 0.15,
            MutationType.TIME_BUDGET_TIGHTEN: 0.1,
            MutationType.AMBIGUITY_ADD: 0.15,
            MutationType.PARTIAL_INFO: 0.1,
            MutationType.NOISE_INJECT: 0.1,
            MutationType.DEPENDENCY_SHIFT: 0.05,
        }
        
        # Select 1-2 mutations
        count = self.rng.randint(1, 2)
        selected = self.rng.choices(
            list(weights.keys()),
            weights=list(weights.values()),
            k=count
        )
        
        return selected
    
    def _generate_mutation_combinations(
        self,
        count: int
    ) -> List[List[MutationType]]:
        """Generate diverse mutation combinations"""
        all_types = list(MutationType)
        combinations = []
        
        for _ in range(count):
            # Random combination of 1-2 mutations
            num_mutations = self.rng.randint(1, 2)
            combo = self.rng.sample(all_types, num_mutations)
            combinations.append(combo)
        
        return combinations
    
    def _select_mutations_for_difficulty(
        self,
        target_difficulty: float,
        level: int
    ) -> List[MutationType]:
        """Select mutations based on target difficulty"""
        if target_difficulty < 0.3:
            # Easy tasks - minor mutations
            return [MutationType.NOISE_INJECT]
        elif target_difficulty < 0.5:
            # Medium tasks - moderate mutations
            return [
                MutationType.CONFIG_CHANGE,
                MutationType.AMBIGUITY_ADD
            ]
        elif target_difficulty < 0.7:
            # Hard tasks - significant mutations
            return [
                MutationType.SYMPTOM_SHIFT,
                MutationType.PARTIAL_INFO,
                MutationType.TIME_BUDGET_TIGHTEN
            ]
        else:
            # Frontier tasks - major mutations
            return [
                MutationType.SYMPTOM_SHIFT,
                MutationType.AMBIGUITY_ADD,
                MutationType.PARTIAL_INFO
            ]
    
    def _apply_mutation(
        self,
        mut_type: MutationType,
        config: Dict[str, Any],
        template: TaskTemplate
    ) -> Tuple[float, str]:
        """Apply a specific mutation and return difficulty delta"""
        
        if mut_type == MutationType.CONFIG_CHANGE:
            return self._mutate_config(config)
        elif mut_type == MutationType.SYMPTOM_SHIFT:
            return self._mutate_symptom(template)
        elif mut_type == MutationType.TIME_BUDGET_TIGHTEN:
            return self._tighten_time_budget(config)
        elif mut_type == MutationType.AMBIGUITY_ADD:
            return self._add_ambiguity(template)
        elif mut_type == MutationType.PARTIAL_INFO:
            return self._remove_info(template)
        elif mut_type == MutationType.NOISE_INJECT:
            return self._inject_noise(config)
        elif mut_type == MutationType.EDGE_CASE_INJECT:
            return self._inject_edge_case(template)
        else:
            return 0.0, "no change"
    
    def _mutate_config(self, config: Dict[str, Any]) -> Tuple[float, str]:
        """Mutate task configuration"""
        templates = self.MUTATION_TEMPLATES[MutationType.CONFIG_CHANGE]
        choice = self.rng.choice(templates)
        
        param = choice["param"]
        value_range = choice["range"]
        
        new_value = self.rng.randint(value_range[0], value_range[1])
        config[param] = new_value
        
        return (
            0.05 if choice["impact"] == DifficultyImpact.MODERATE_INCREASE else 0.02,
            f"config: {param} = {new_value}"
        )
    
    def _mutate_symptom(self, template: TaskTemplate) -> Tuple[float, str]:
        """Shift the symptom of a problem"""
        templates = self.MUTATION_TEMPLATES[MutationType.SYMPTOM_SHIFT]
        choice = self.rng.choice(templates)
        
        # Add symptom shift to metadata
        if "symptom_shift" not in template.constraints:
            template.constraints["symptom_shift"] = []
        
        shift = f"{choice['from']} -> {choice['to']}"
        template.constraints["symptom_shift"].append(shift)
        
        impact_value = {
            DifficultyImpact.SIGNIFICANT_INCREASE: 0.15,
            DifficultyImpact.MODERATE_INCREASE: 0.1,
            DifficultyImpact.SLIGHT_INCREASE: 0.05
        }.get(choice["impact"], 0.05)
        
        return impact_value, f"symptom: {shift}"
    
    def _tighten_time_budget(self, config: Dict[str, Any]) -> Tuple[float, str]:
        """Tighten the time budget"""
        templates = self.MUTATION_TEMPLATES[MutationType.TIME_BUDGET_TIGHTEN]
        choice = self.rng.choice(templates)
        
        factor = choice["factor"]
        current_timeout = config.get("timeout", 60)
        new_timeout = int(current_timeout * factor)
        
        config["timeout"] = new_timeout
        
        impact_value = {
            DifficultyImpact.SIGNIFICANT_INCREASE: 0.15,
            DifficultyImpact.MODERATE_INCREASE: 0.1,
            DifficultyImpact.SLIGHT_INCREASE: 0.05
        }.get(choice["impact"], 0.1)
        
        return impact_value, f"time_budget: {current_timeout} -> {new_timeout}s"
    
    def _add_ambiguity(self, template: TaskTemplate) -> Tuple[float, str]:
        """Add ambiguity to the task"""
        templates = self.MUTATION_TEMPLATES[MutationType.AMBIGUITY_ADD]
        choice = self.rng.choice(templates)
        
        if "ambiguity" not in template.constraints:
            template.constraints["ambiguity"] = []
        
        ambiguity = choice["type"]
        template.constraints["ambiguity"].append(ambiguity)
        
        impact_value = {
            DifficultyImpact.SIGNIFICANT_INCREASE: 0.12,
            DifficultyImpact.MODERATE_INCREASE: 0.08,
            DifficultyImpact.SLIGHT_INCREASE: 0.03
        }.get(choice["impact"], 0.08)
        
        return impact_value, f"ambiguity: {ambiguity}"
    
    def _remove_info(self, template: TaskTemplate) -> Tuple[float, str]:
        """Remove partial information"""
        templates = self.MUTATION_TEMPLATES[MutationType.PARTIAL_INFO]
        choice = self.rng.choice(templates)
        
        missing = choice["missing"]
        
        if "hidden_info" not in template.constraints:
            template.constraints["hidden_info"] = []
        
        template.constraints["hidden_info"].append(missing)
        
        impact_value = {
            DifficultyImpact.SIGNIFICANT_INCREASE: 0.15,
            DifficultyImpact.MODERATE_INCREASE: 0.08,
            DifficultyImpact.SLIGHT_INCREASE: 0.03
        }.get(choice["impact"], 0.08)
        
        return impact_value, f"missing: {missing}"
    
    def _inject_noise(self, config: Dict[str, Any]) -> Tuple[float, str]:
        """Inject noise/distraction files"""
        templates = self.MUTATION_TEMPLATES[MutationType.NOISE_INJECT]
        choice = self.rng.choice(templates)
        
        count_range = choice["count"]
        noise_count = self.rng.randint(count_range[0], count_range[1])
        
        config["noise_files"] = noise_count
        
        return 0.03, f"noise: {noise_count} distraction files"
    
    def _inject_edge_case(self, template: TaskTemplate) -> Tuple[float, str]:
        """Inject hidden edge case"""
        edge_cases = [
            "empty_input",
            "null_value",
            "unicode_characters",
            "very_long_input",
            "special_characters",
            "race_condition"
        ]
        
        edge_case = self.rng.choice(edge_cases)
        
        if "edge_cases" not in template.constraints:
            template.constraints["edge_cases"] = []
        
        template.constraints["edge_cases"].append(edge_case)
        
        return 0.1, f"edge_case: {edge_case}"
    
    def _generate_mutation_hash(
        self,
        task_id: str,
        mutation_types: List[MutationType]
    ) -> str:
        """Generate a unique hash for the mutation"""
        data = f"{task_id}:{':'.join(m.value for m in mutation_types)}"
        return hashlib.sha256(data.encode()).hexdigest()
    
    def validate_mutation(
        self,
        original: TaskTemplate,
        mutated: MutatedTask
    ) -> Tuple[bool, str]:
        """
        Validate that a mutation is valid and meaningful.
        
        Returns:
            (is_valid, reason)
        """
        # Check that task ID changed
        if mutated.new_task_id == original.task_id:
            return False, "Task ID did not change"
        
        # Check that there are actual changes
        if not mutated.changes:
            return False, "No mutations applied"
        
        # Check that solve rate changed in expected direction
        if mutated.difficulty_impact == DifficultyImpact.SIGNIFICANT_INCREASE:
            if mutated.predicted_solve_rate >= original.difficulty:
                return False, "Difficulty should increase but solve rate did not decrease"
        
        return True, "Valid mutation"


__all__ = [
    'TaskMutator',
    'MutationType',
    'DifficultyImpact',
    'MutationConfig',
    'MutatedTask',
    'TaskTemplate'
]
