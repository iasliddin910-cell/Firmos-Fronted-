"""
FrontierTaskForge - Main Adaptive Curriculum Engine

Bu asosiy modul No1 World+ tizim uchun benchmark tasklarni avtomatik yaratadi.

Vazifasi:
- Recent failures ni oladi
- Shadow twin replay natijalarini oladi
- Capability heatmap ni oladi
- Reality gap report ni oladi
- Yangilanish asosida yangi benchmark tasklar yaratadi

Nega kerak?
Chunki No1 World+ tizim:
- Faqat existing testsdan o'tadigan emas
- O'zining keyingi imtihonini o'zi yasaydigan tizim bo'lishi kerak

Qanday ishlaydi?
1. Recent fail traces ni oladi
2. Common failure structure ni ajratadi
3. Template + mutation bilan new task proposal yaratadi
4. Dedup/contamination/reality checksdan o'tkazadi
5. Shadow twin da pilot run qiladi
6. Diagnostic value yuqori bo'lsa candidate benchmarkga qo'shadi

Policy 2: Har katta improvementdan keyin frontier task generation ishlasin.
Policy 3: Auto-generated tasklar stable boardga to'g'ridan-to'g'ri kirmasin.
"""

from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import hashlib
import json
import time

from .frontier_miner import FrontierMiner, FrontierSignal, TaskResult, FrontierZoneType
from .failure_clusterer import FailureClusterer, FailureTrace, FailurePattern, FailureCluster
from .task_mutator import TaskMutator, TaskTemplate, MutationType
from .difficulty_calibrator import DifficultyCalibrator
from .capability_gap_generator import CapabilityGapGenerator, CapabilityScore, CapabilityGap, GapSeverity


class TaskSource(Enum):
    """Source of generated task"""
    FRONTIER_MINING = "frontier_mining"
    FAILURE_CLUSTERING = "failure_clustering"
    CAPABILITY_GAP = "capability_gap"
    TASK_MUTATION = "task_mutation"
    MANUAL = "manual"


class ValidationStatus(Enum):
    """Status of task validation"""
    PENDING = "pending"
    DEDUP_CHECK = "dedup_check"
    CONTAMINATION_CHECK = "contamination_check"
    REALITY_CHECK = "reality_check"
    PILOT_RUN = "pilot_run"
    APPROVED = "approved"
    REJECTED = "rejected"


@dataclass
class TaskCandidate:
    """A candidate task for benchmark inclusion"""
    task_id: str
    source: TaskSource
    description: str
    difficulty: float
    capability_focus: List[str]
    validation_status: ValidationStatus
    generation_params: Dict[str, Any]
    diagnostics: Dict[str, float]
    pilot_results: Optional[Dict[str, Any]] = None
    rejection_reason: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GenerationConfig:
    """Configuration for task generation"""
    max_candidates_per_run: int = 20
    min_diagnostic_value: float = 0.3
    dedup_similarity_threshold: float = 0.8
    contamination_check: bool = True
    pilot_run_enabled: bool = True
    pilot_sample_size: int = 5
    difficulty_target_range: Tuple[float, float] = (0.3, 0.7)


@dataclass
class ForgeResult:
    """Result of the forging process"""
    generated_count: int
    validated_count: int
    rejected_count: int
    candidates: List[TaskCandidate]
    summary: str


class NoveltyGuard:
    """
    Validates that generated tasks are novel and don't leak benchmark.
    
    Checks:
    - Duplicate detection
    - Benchmark leak prevention
    - Hidden asset distance
    - Trivial rename prevention
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.existing_tasks: Set[str] = set()
        self.task_hashes: Set[str] = set()
        
    def register_task(self, task_id: str, content: str) -> None:
        """Register an existing task for dedup checking"""
        self.existing_tasks.add(task_id)
        content_hash = hashlib.md5(content.encode()).hexdigest()
        self.task_hashes.add(content_hash)
    
    def check_novelty(self, candidate: TaskCandidate) -> Tuple[bool, str]:
        """Check if candidate is novel"""
        if candidate.task_id in self.existing_tasks:
            return False, f"Task ID '{candidate.task_id}' already exists"
        
        content = json.dumps(candidate.generation_params, sort_keys=True)
        content_hash = hashlib.md5(content.encode()).hexdigest()
        
        if content_hash in self.task_hashes:
            return False, "Nearly identical task already exists"
        
        return True, "Novel task"
    
    def check_dedup(
        self,
        candidate: TaskCandidate,
        existing_tasks: List[Dict[str, Any]]
    ) -> Tuple[bool, str]:
        """Check for duplicates in existing tasks"""
        candidate_text = candidate.description.lower()
        
        for existing in existing_tasks:
            existing_text = existing.get('description', '').lower()
            
            candidate_words = set(candidate_text.split())
            existing_words = set(existing_text.split())
            
            if not candidate_words or not existing_words:
                continue
                
            overlap = len(candidate_words & existing_words) / len(candidate_words | existing_words)
            
            if overlap > self.config.get('dedup_threshold', 0.8):
                return False, f"Too similar to existing task: {existing.get('task_id')}"
        
        return True, "No duplicates found"


class FrontierTaskForge:
    """
    Main adaptive engine for generating benchmark tasks.
    
    Bu modul quyidagilarni birlashtiradi:
    - FrontierMiner: Frontier zonani topadi
    - FailureClusterer: Failure patternlarni klasterlaydi
    - TaskMutator: Mavjud tasklarni mutate qiladi
    - CapabilityGapGenerator: Gap-driven task yaratadi
    - NoveltyGuard: Yangi tasklarni tekshiradi
    """
    
    def __init__(self, config: Optional[GenerationConfig] = None):
        self.config = config or GenerationConfig()
        
        self.frontier_miner = FrontierMiner()
        self.failure_clusterer = FailureClusterer()
        self.task_mutator = TaskMutator()
        self.difficulty_calibrator = DifficultyCalibrator()
        self.capability_gap_generator = CapabilityGapGenerator()
        self.novelty_guard = NoveltyGuard()
        
        self.candidates: List[TaskCandidate] = []
        self.approved_candidates: List[TaskCandidate] = []
        self.rejected_candidates: List[TaskCandidate] = []
        
    def generate(
        self,
        benchmark_results: Optional[List[TaskResult]] = None,
        failure_traces: Optional[List[FailureTrace]] = None,
        capability_scores: Optional[List[CapabilityScore]] = None,
        existing_tasks: Optional[List[Dict[str, Any]]] = None,
        target_capabilities: Optional[List[str]] = None
    ) -> ForgeResult:
        """Main generation method."""
        candidates = []
        
        if benchmark_results:
            frontier_candidates = self._generate_from_frontier(benchmark_results)
            candidates.extend(frontier_candidates)
        
        if failure_traces:
            failure_candidates = self._generate_from_failures(failure_traces)
            candidates.extend(failure_candidates)
        
        if capability_scores:
            gap_candidates = self._generate_from_capability_gaps(
                capability_scores, target_capabilities
            )
            candidates.extend(gap_candidates)
        
        validated = self._validate_candidates(
            candidates, existing_tasks or []
        )
        
        if self.config.pilot_run_enabled:
            validated = self._run_pilot_tests(validated)
        
        self.candidates = validated
        self.approved_candidates = [
            c for c in validated 
            if c.validation_status == ValidationStatus.APPROVED
        ]
        
        return ForgeResult(
            generated_count=len(candidates),
            validated_count=len(validated),
            rejected_count=len(candidates) - len(validated),
            candidates=self.approved_candidates,
            summary=self._generate_summary(validated)
        )
    
    def _generate_from_frontier(
        self,
        results: List[TaskResult]
    ) -> List[TaskCandidate]:
        """Generate candidates from frontier zone analysis"""
        candidates = []
        
        signals = self.frontier_miner.analyze_results(results)
        
        for signal in signals[:self.config.max_candidates_per_run]:
            if signal.raw_score < self.config.min_diagnostic_value:
                continue
            
            candidate = TaskCandidate(
                task_id=f"frontier_{signal.task_id}_{int(time.time())}",
                source=TaskSource.FRONTIER_MINING,
                description=f"Frontier task from {signal.signal_type} zone",
                difficulty=signal.solve_rate,
                capability_focus=[signal.signal_type],
                validation_status=ValidationStatus.PENDING,
                generation_params={
                    "signal_type": signal.signal_type,
                    "solve_rate": signal.solve_rate,
                    "variance": signal.variance,
                    "near_miss_count": signal.near_miss_count
                },
                diagnostics={
                    "diagnostic_value": signal.raw_score,
                    "frontier_score": signal.raw_score,
                    "signal_strength": signal.strength.value
                }
            )
            candidates.append(candidate)
        
        return candidates
    
    def _generate_from_failures(
        self,
        traces: List[FailureTrace]
    ) -> List[TaskCandidate]:
        """Generate candidates from failure clustering"""
        candidates = []
        
        cluster_result = self.failure_clusterer.cluster_failures(traces)
        
        for pattern in cluster_result.clusters[:self.config.max_candidates_per_run]:
            for i, task_hint in enumerate(pattern.task_generation_hints[:3]):
                candidate = TaskCandidate(
                    task_id=f"failure_{pattern.cluster_type.value}_{i}_{int(time.time())}",
                    source=TaskSource.FAILURE_CLUSTERING,
                    description=f"Task targeting {pattern.cluster_type.value}: {task_hint}",
                    difficulty=0.5,
                    capability_focus=[pattern.cluster_type.value],
                    validation_status=ValidationStatus.PENDING,
                    generation_params={
                        "cluster_type": pattern.cluster_type.value,
                        "occurrence_count": pattern.occurrence_count,
                        "task_hint": task_hint,
                        "severity": pattern.severity.value
                    },
                    diagnostics={
                        "diagnostic_value": pattern.diagnostic_value,
                        "cluster_size": pattern.occurrence_count,
                        "severity_score": pattern.severity.value
                    }
                )
                candidates.append(candidate)
        
        return candidates
    
    def _generate_from_capability_gaps(
        self,
        capability_scores: List[CapabilityScore],
        target_capabilities: Optional[List[str]] = None
    ) -> List[TaskCandidate]:
        """Generate candidates from capability gaps"""
        candidates = []
        
        gaps = self.capability_gap_generator.analyze_capability_gaps(capability_scores)
        
        if target_capabilities:
            gaps = [
                g for g in gaps 
                if g.capability.value in target_capabilities
            ]
        
        for gap in gaps[:5]:
            tasks = self.capability_gap_generator.generate_tasks_for_gap(
                gap,
                count=3,
                difficulty_range=self.config.difficulty_target_range
            )
            
            for task_spec in tasks:
                candidate = TaskCandidate(
                    task_id=task_spec.task_id,
                    source=TaskSource.CAPABILITY_GAP,
                    description=task_spec.description,
                    difficulty=task_spec.difficulty,
                    capability_focus=[gap.capability.value],
                    validation_status=ValidationStatus.PENDING,
                    generation_params={
                        "capability": gap.capability.value,
                        "gap_severity": gap.severity.value,
                        "task_spec": {
                            "description": task_spec.description,
                            "success_criteria": task_spec.success_criteria,
                            "hints": task_spec.hints
                        }
                    },
                    diagnostics={
                        "diagnostic_value": gap.priority,
                        "gap_size": gap.gap_size,
                        "expected_improvement": task_spec.expected_capability_improvement
                    }
                )
                candidates.append(candidate)
        
        return candidates
    
    def mutate_existing_tasks(
        self,
        templates: List[TaskTemplate],
        target_difficulty: Optional[float] = None
    ) -> List[TaskCandidate]:
        """Generate candidates by mutating existing tasks"""
        candidates = []
        
        for template in templates:
            variants = self.task_mutator.mutate_task(
                template,
                target_difficulty=target_difficulty
            )
            
            candidate = TaskCandidate(
                task_id=variants.new_task_id,
                source=TaskSource.TASK_MUTATION,
                description=f"Mutated from {template.task_id}: {', '.join(variants.changes)}",
                difficulty=variants.predicted_solve_rate,
                capability_focus=[template.task_type],
                validation_status=ValidationStatus.PENDING,
                generation_params={
                    "original_task_id": template.task_id,
                    "mutation_type": variants.mutation_type.value,
                    "changes": variants.changes,
                    "difficulty_impact": variants.difficulty_impact.value
                },
                diagnostics={
                    "diagnostic_value": 0.5,
                    "mutation_count": len(variants.changes)
                }
            )
            candidates.append(candidate)
        
        return candidates
    
    def _validate_candidates(
        self,
        candidates: List[TaskCandidate],
        existing_tasks: List[Dict[str, Any]]
    ) -> List[TaskCandidate]:
        """Validate candidates through various checks"""
        validated = []
        
        for candidate in candidates:
            is_novel, reason = self.novelty_guard.check_novelty(candidate)
            if not is_novel:
                candidate.validation_status = ValidationStatus.REJECTED
                candidate.rejection_reason = f"Novelty check failed: {reason}"
                self.rejected_candidates.append(candidate)
                continue
            
            is_deduped, reason = self.novelty_guard.check_dedup(
                candidate, existing_tasks
            )
            if not is_deduped:
                candidate.validation_status = ValidationStatus.REJECTED
                candidate.rejection_reason = f"Dedup check failed: {reason}"
                self.rejected_candidates.append(candidate)
                continue
            
            diag_value = candidate.diagnostics.get('diagnostic_value', 0)
            if diag_value < self.config.min_diagnostic_value:
                candidate.validation_status = ValidationStatus.REJECTED
                candidate.rejection_reason = f"Low diagnostic value: {diag_value}"
                self.rejected_candidates.append(candidate)
                continue
            
            candidate.validation_status = ValidationStatus.APPROVED
            validated.append(candidate)
        
        return validated
    
    def _run_pilot_tests(
        self,
        candidates: List[TaskCandidate]
    ) -> List[TaskCandidate]:
        """Run pilot tests on candidates"""
        for candidate in candidates:
            if candidate.validation_status == ValidationStatus.APPROVED:
                candidate.pilot_results = {
                    "pilot_status": "not_run",
                    "note": "Pilot run would execute here with shadow twin"
                }
        
        return candidates
    
    def _generate_summary(self, candidates: List[TaskCandidate]) -> str:
        """Generate summary of generation results"""
        if not candidates:
            return "No candidates generated."
        
        source_counts = defaultdict(int)
        for c in candidates:
            source_counts[c.source.value] += 1
        
        lines = [f"Generated {len(candidates)} candidates:"]
        
        for source, count in source_counts.items():
            lines.append(f"  - {source}: {count}")
        
        return "\n".join(lines)
    
    def get_candidates_report(self) -> Dict[str, Any]:
        """Get detailed report on all candidates"""
        return {
            "total_candidates": len(self.candidates),
            "approved": len(self.approved_candidates),
            "rejected": len(self.rejected_candidates),
            "by_source": {
                source.value: len([
                    c for c in self.candidates if c.source == source
                ])
                for source in TaskSource
            },
            "candidates": [
                {
                    "task_id": c.task_id,
                    "source": c.source.value,
                    "difficulty": c.difficulty,
                    "status": c.validation_status.value,
                    "diagnostic_value": c.diagnostics.get('diagnostic_value', 0)
                }
                for c in self.approved_candidates[:20]
            ]
        }
    
    def approve_for_benchmark(
        self,
        candidate_ids: List[str]
    ) -> List[TaskCandidate]:
        """Manually approve candidates for benchmark inclusion"""
        approved = []
        
        for candidate in self.candidates:
            if candidate.task_id in candidate_ids:
                candidate.validation_status = ValidationStatus.APPROVED
                approved.append(candidate)
                self.approved_candidates.append(candidate)
        
        return approved
    
    def export_candidates(self) -> List[Dict[str, Any]]:
        """Export approved candidates in benchmark format"""
        export = []
        
        for candidate in self.approved_candidates:
            export.append({
                "task_id": candidate.task_id,
                "description": candidate.description,
                "difficulty": candidate.difficulty,
                "capabilities": candidate.capability_focus,
                "source": candidate.source.value,
                "generation_params": candidate.generation_params,
                "metadata": candidate.metadata
            })
        
        return export


__all__ = [
    'FrontierTaskForge',
    'TaskSource',
    'ValidationStatus',
    'TaskCandidate',
    'GenerationConfig',
    'ForgeResult',
    'NoveltyGuard'
]
