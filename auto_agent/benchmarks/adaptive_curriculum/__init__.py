"""
Adaptive Curriculum Engine - Main Integration Module

Bu modul barcha adaptive curriculum komponentlarini birlashtiradi:
- FrontierMiner: Frontier zonani topadi
- FailureClusterer: Failure patternlarni klasterlaydi
- TaskMutator: Tasklarni mutate qiladi
- DifficultyCalibrator: Qiyinlikni kalibrovka qiladi
- CapabilityGapGenerator: Gap-driven task yaratadi
- FrontierTaskForge: Asosiy engine
- CurriculumBoard: Task lifecycle
- AutoRetirePolicy: Saturated task management

Policy 1: Static benchmark yetmaydi.
Policy 2: Har katta improvementdan keyin frontier task generation ishlasin.
Policy 3: Auto-generated tasklar stable boardga to'g'ridan-to'g'ri kirmasin.
Policy 4: Near-frontier zone benchmarkning eng qimmat qismi.
Policy 5: Easy saturated tasklar weight yo'qotsin yoki retire qilinsin.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
import time

from .frontier_miner import FrontierMiner, FrontierSignal, TaskResult
from .failure_clusterer import FailureClusterer, FailureTrace
from .task_mutator import TaskMutator, TaskTemplate
from .difficulty_calibrator import DifficultyCalibrator, DifficultyPrediction
from .capability_gap_generator import CapabilityGapGenerator, CapabilityScore
from .frontier_task_forge import (
    FrontierTaskForge, 
    TaskCandidate, 
    GenerationConfig,
    ForgeResult
)
from .curriculum_board import (
    CurriculumBoard,
    TaskState,
    TaskBoard,
    TaskEntry
)
from .auto_retire_policy import (
    AutoRetirePolicy,
    RetirePolicy,
    RetireRecommendation
)


@dataclass
class AdaptiveCurriculumConfig:
    """Configuration for the adaptive curriculum engine"""
    # Generation settings
    max_candidates_per_run: int = 20
    min_diagnostic_value: float = 0.3
    
    # Calibration settings
    min_runs_for_calibration: int = 5
    
    # Board settings
    auto_retire_enabled: bool = True
    retire_threshold: float = 0.90
    
    # Policy settings
    run_frontier_mining_after_improvement: bool = True
    run_failure_clustering: bool = True
    run_capability_gap_analysis: bool = True


@dataclass
class CurriculumReport:
    """Comprehensive report from the curriculum engine"""
    timestamp: float
    frontier_zones: List[Dict[str, Any]]
    failure_clusters: List[Dict[str, Any]]
    capability_gaps: List[Dict[str, Any]]
    generated_candidates: int
    validated_candidates: int
    board_stats: Dict[str, Any]
    retire_actions: List[Dict[str, Any]]
    summary: str


class AdaptiveCurriculumEngine:
    """
    Main adaptive curriculum engine that orchestrates all components.
    
    Bu engine quyidagilarni bajaradi:
    1. Benchmark natijalarini tahlil qiladi
    2. Frontier zonani topadi
    3. Failure patternlarni klasterlaydi
    4. Capability gaplarni aniqlaydi
    5. Yangi tasklar generatsiya qiladi
    6. Tasklarni boardda boshqaradi
    7. Saturated tasklarni retire qiladi
    """
    
    def __init__(self, config: Optional[AdaptiveCurriculumConfig] = None):
        self.config = config or AdaptiveCurriculumConfig()
        
        # Initialize all components
        self.frontier_miner = FrontierMiner()
        self.failure_clusterer = FailureClusterer()
        self.task_mutator = TaskMutator()
        self.difficulty_calibrator = DifficultyCalibrator()
        self.capability_gap_generator = CapabilityGapGenerator()
        
        # Initialize forge with config
        forge_config = GenerationConfig(
            max_candidates_per_run=self.config.max_candidates_per_run,
            min_diagnostic_value=self.config.min_diagnostic_value,
            pilot_run_enabled=False  # Disable for now
        )
        self.forge = FrontierTaskForge(forge_config)
        
        # Initialize board
        self.board = CurriculumBoard()
        
        # Initialize retire policy
        retire_policy = RetirePolicy(
            auto_retire_enabled=self.config.auto_retire_enabled,
            solve_rate_threshold=self.config.retire_threshold
        )
        self.retire_policy = AutoRetirePolicy(retire_policy)
        
        # State
        self.last_run_time: Optional[float] = None
        self.run_count: int = 0
    
    def run(
        self,
        benchmark_results: Optional[List[TaskResult]] = None,
        failure_traces: Optional[List[FailureTrace]] = None,
        capability_scores: Optional[List[CapabilityScore]] = None,
        existing_tasks: Optional[List[Dict[str, Any]]] = None
    ) -> CurriculumReport:
        """
        Run the complete adaptive curriculum pipeline.
        
        Args:
            benchmark_results: Results from benchmark evaluation
            failure_traces: Failure traces from runs
            capability_scores: Current capability scores
            existing_tasks: Existing tasks for dedup
            
        Returns:
            CurriculumReport with full analysis
        """
        self.run_count += 1
        start_time = time.time()
        
        # Step 1: Analyze frontier zones
        frontier_zones = []
        if benchmark_results:
            frontier_report = self.frontier_miner.get_frontier_report(benchmark_results)
            frontier_zones = frontier_report.get('zones', [])
            
            # Add frontier tasks to board
            for zone in frontier_zones:
                for task_id in zone.get('task_ids', []):
                    self.board.add_task(
                        task_id=task_id,
                        difficulty=zone.get('avg_solve_rate', 0.5),
                        source='frontier_mining',
                        metadata={'zone_type': zone.get('type')}
                    )
        
        # Step 2: Cluster failures
        failure_clusters = []
        if failure_traces:
            cluster_report = self.failure_clusterer.get_cluster_report(failure_traces)
            failure_clusters = cluster_report.get('clusters', [])
        
        # Step 3: Analyze capability gaps
        capability_gaps = []
        if capability_scores:
            gaps = self.capability_gap_generator.analyze_capability_gaps(capability_scores)
            capability_gaps = [
                {
                    'capability': g.capability.value,
                    'severity': g.severity.value,
                    'gap_size': g.gap_size,
                    'priority': g.priority
                }
                for g in gaps
            ]
        
        # Step 4: Generate new candidates
        forge_result = self.forge.generate(
            benchmark_results=benchmark_results,
            failure_traces=failure_traces,
            capability_scores=capability_scores,
            existing_tasks=existing_tasks
        )
        
        # Add generated candidates to board
        for candidate in forge_result.candidates:
            self.board.add_task(
                task_id=candidate.task_id,
                difficulty=candidate.difficulty,
                source=candidate.source.value,
                metadata={
                    'capability_focus': candidate.capability_focus,
                    'diagnostics': candidate.diagnostics
                }
            )
        
        # Step 5: Run auto-retirement
        retire_actions = []
        if self.config.auto_retire_enabled:
            # Get tasks from board
            tasks_data = {
                tid: {
                    'task_id': tid,
                    'solve_rate': entry.solve_rate,
                    'evaluation_count': entry.evaluation_count,
                    'diagnostic_value': entry.diagnostic_value,
                    'weight': entry.weight
                }
                for tid, entry in self.board.tasks.items()
            }
            
            retire_result = self.retire_policy.run_auto_retirement(tasks_data)
            retire_actions = retire_result.get('actions', [])
        
        # Update last run time
        self.last_run_time = time.time()
        
        # Generate report
        board_export = self.board.export_board_state()
        
        return CurriculumReport(
            timestamp=start_time,
            frontier_zones=frontier_zones,
            failure_clusters=failure_clusters,
            capability_gaps=capability_gaps,
            generated_candidates=forge_result.generated_count,
            validated_candidates=forge_result.validated_count,
            board_stats=board_export,
            retire_actions=retire_actions,
            summary=self._generate_summary(forge_result, frontier_zones, capability_gaps)
        )
    
    def run_after_improvement(
        self,
        improvement_type: str,
        benchmark_results: Optional[List[TaskResult]] = None,
        capability_scores: Optional[List[CapabilityScore]] = None
    ) -> CurriculumReport:
        """
        Run curriculum after an improvement was made.
        
        Policy 2: Har katta improvementdan keyin frontier task generation ishlasin.
        
        Args:
            improvement_type: Type of improvement made
            benchmark_results: Updated benchmark results
            capability_scores: Updated capability scores
            
        Returns:
            CurriculumReport
        """
        return self.run(
            benchmark_results=benchmark_results,
            capability_scores=capability_scores
        )
    
    def _generate_summary(
        self,
        forge_result: ForgeResult,
        frontier_zones: List[Dict[str, Any]],
        capability_gaps: List[Dict[str, Any]]
    ) -> str:
        """Generate summary of the run"""
        lines = [
            f"Adaptive Curriculum Run #{self.run_count}",
            f"Generated: {forge_result.generated_count} candidates",
            f"Validated: {forge_result.validated_count} candidates",
            f"Frontier zones: {len(frontier_zones)}",
            f"Capability gaps: {len(capability_gaps)}"
        ]
        
        if capability_gaps:
            top_gaps = capability_gaps[:3]
            lines.append("Top gaps:")
            for gap in top_gaps:
                lines.append(f"  - {gap['capability']}: {gap['severity']}")
        
        return "\n".join(lines)
    
    def get_board_state(self) -> Dict[str, Any]:
        """Get current board state"""
        return self.board.export_board_state()
    
    def get_frontier_tasks(self, limit: int = 20) -> List[TaskEntry]:
        """Get current frontier tasks"""
        return self.board.get_tasks_for_evaluation(
            board=TaskBoard.FRONTIER_RISING,
            limit=limit
        )
    
    def get_tasks_for_eval(self, limit: int = 20) -> List[TaskEntry]:
        """Get tasks ready for evaluation"""
        return self.board.get_tasks_for_evaluation(limit=limit)
    
    def export_tasks(self, format: str = "benchmark") -> List[Dict[str, Any]]:
        """
        Export tasks in specified format.
        
        Args:
            format: Export format ("benchmark", "json", "csv")
            
        Returns:
            List of exported tasks
        """
        if format == "benchmark":
            return self.forge.export_candidates()
        else:
            return [
                {
                    "task_id": entry.task_id,
                    "difficulty": entry.difficulty,
                    "state": entry.state.value,
                    "board": entry.board.value,
                    "solve_rate": entry.solve_rate,
                    "weight": entry.weight
                }
                for entry in self.board.tasks.values()
            ]


__all__ = [
    'AdaptiveCurriculumEngine',
    'AdaptiveCurriculumConfig',
    'CurriculumReport',
    # Re-export all components
    'FrontierMiner',
    'FailureClusterer',
    'TaskMutator',
    'DifficultyCalibrator',
    'CapabilityGapGenerator',
    'FrontierTaskForge',
    'CurriculumBoard',
    'AutoRetirePolicy'
]
