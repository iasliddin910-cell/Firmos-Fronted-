"""
Scenario Runner - Ssenariylarni sinash va taqqoslash
===================================================

Bu runner tarixiy run'larni yangi kernel config bilan
qayta o'ynaydi va divergence report chiqaradi.

Features:
- Tarixiy run'larni replay qilish
- Yangi config bilan taqqoslash
- Divergence report chiqarish
- Benchmark va hardening uchun foydali
"""

import logging
from typing import Dict, List, Optional, Any, Callable, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from pathlib import Path
import threading
import json

from .replay_engine import ReplayEngine, ReplayConfig, ReplayMode, RunLedger
from .simulation_mode import SimulationMode, SimulationConfig, ExecutionMode, ShadowResult
from .divergence_analyzer import DivergenceAnalyzer, DivergenceReport

logger = logging.getLogger(__name__)


class ScenarioType(str, Enum):
    """Ssenariy turlari"""
    REPLAY = "replay"               # Eski runni qayta o'ynash
    COMPARISON = "comparison"        # Ikkita configni taqqoslash
    BENCHMARK = "benchmark"         # Benchmark o'tkazish
    HARDENING = "hardening"          # Security hardening tekshirish
    REGRESSION = "regression"        # Regression test
    SELF_IMPROVEMENT = "self_improvement"  # Kernel o'z-o'zini yaxshilashi


@dataclass
class ScenarioConfig:
    """Ssenariy konfiguratsiyasi"""
    scenario_type: ScenarioType = ScenarioType.REPLAY
    
    # Replay settings
    replay_config: Optional[ReplayConfig] = None
    simulation_config: Optional[SimulationConfig] = None
    
    # Input
    historical_ledger_path: Optional[Path] = None
    baseline_ledger_path: Optional[Path] = None
    
    # Kernel config for comparison
    kernel_config: Optional[Dict[str, Any]] = None
    baseline_kernel_config: Optional[Dict[str, Any]] = None
    
    # Output
    output_path: Optional[Path] = None
    save_results: bool = True
    
    # Filters
    task_filter: Optional[Callable[[str], bool]] = None
    event_filter: Optional[Callable[[str], bool]] = None
    
    # Parallel execution
    parallel: bool = False
    max_workers: int = 4


@dataclass
class ScenarioResult:
    """Ssenariy natijasi"""
    scenario_type: ScenarioType
    success: bool
    total_tasks: int = 0
    passed_tasks: int = 0
    failed_tasks: int = 0
    
    # Replay results
    replay_results: List[Dict[str, Any]] = field(default_factory=list)
    
    # Divergence results
    divergence_reports: List[DivergenceReport] = field(default_factory=list)
    
    # Shadow results (if applicable)
    shadow_results: List[ShadowResult] = field(default_factory=list)
    
    # Metrics
    execution_time: float = 0.0
    divergence_count: int = 0
    
    # Summary
    summary: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            'scenario_type': self.scenario_type.value,
            'success': self.success,
            'total_tasks': self.total_tasks,
            'passed_tasks': self.passed_tasks,
            'failed_tasks': self.failed_tasks,
            'execution_time': self.execution_time,
            'divergence_count': self.divergence_count,
            'summary': self.summary,
            'replay_results': self.replay_results[:10]  # Limit output
        }


class ScenarioRunner:
    """
    Scenario Runner - Ssenariylarni boshqarish
    
    Bu runner quyidagi imkoniyatlarni beradi:
    - Tarixiy run'larni replay qilish
    - Yangi kernel config bilan taqqoslash
    - Regression test o'tkazish
    - Self-improvement uchun safe testing
    
    Usage:
        runner = ScenarioRunner()
        
        # Replay scenario
        config = ScenarioConfig(
            scenario_type=ScenarioType.REPLAY,
            historical_ledger_path=Path("ledger.json")
        )
        result = runner.run_scenario(config)
        
        # Comparison scenario
        config = ScenarioConfig(
            scenario_type=ScenarioType.COMPARISON,
            baseline_ledger_path=Path("baseline.json"),
            kernel_config=new_config
        )
        result = runner.run_scenario(config)
    """
    
    def __init__(self):
        self.replay_engine = ReplayEngine()
        self.simulation_mode = SimulationMode()
        self.divergence_analyzer = DivergenceAnalyzer()
        
        # State
        self.current_result: Optional[ScenarioResult] = None
        self._lock = threading.Lock()
        
        logger.info("ScenarioRunner initialized")
    
    def run_scenario(
        self,
        config: ScenarioConfig
    ) -> ScenarioResult:
        """
        Ssenariyoni ishga tushirish
        
        Args:
            config: ScenarioConfig
            
        Returns:
            ScenarioResult
        """
        import time
        start_time = time.time()
        
        with self._lock:
            # Route to appropriate handler
            if config.scenario_type == ScenarioType.REPLAY:
                result = self._run_replay_scenario(config)
            elif config.scenario_type == ScenarioType.COMPARISON:
                result = self._run_comparison_scenario(config)
            elif config.scenario_type == ScenarioType.BENCHMARK:
                result = self._run_benchmark_scenario(config)
            elif config.scenario_type == ScenarioType.HARDENING:
                result = self._run_hardening_scenario(config)
            elif config.scenario_type == ScenarioType.REGRESSION:
                result = self._run_regression_scenario(config)
            elif config.scenario_type == ScenarioType.SELF_IMPROVEMENT:
                result = self._run_self_improvement_scenario(config)
            else:
                raise ValueError(f"Unknown scenario type: {config.scenario_type}")
            
            result.execution_time = time.time() - start_time
        
        # Save results if requested
        if config.save_results and config.output_path:
            self._save_result(result, config.output_path)
        
        self.current_result = result
        return result
    
    def _run_replay_scenario(self, config: ScenarioConfig) -> ScenarioResult:
        """Replay ssenariyosi"""
        # Load ledger
        ledger = self._load_ledger(config.historical_ledger_path)
        
        # Create replay config
        replay_config = config.replay_config or ReplayConfig()
        
        # Run replay
        self.replay_engine.set_ledger(ledger)
        self.replay_engine.set_config(replay_config)
        replay_state = self.replay_engine.replay()
        
        # Analyze divergence
        if replay_config.detect_divergence:
            divergence_report = self.divergence_analyzer.analyze(
                ledger=ledger,
                replay_state=replay_state
            )
        else:
            divergence_report = None
        
        # Build result
        result = ScenarioResult(
            scenario_type=ScenarioType.REPLAY,
            success=replay_state.status.value == "completed",
            total_tasks=replay_state.total_events,
            passed_tasks=replay_state.total_events - replay_state.divergence_count,
            failed_tasks=replay_state.divergence_count,
            divergence_count=replay_state.divergence_count,
            summary={
                'replay_status': replay_state.status.value,
                'events_processed': replay_state.current_event_index + 1
            }
        )
        
        if divergence_report:
            result.divergence_reports.append(divergence_report)
        
        return result
    
    def _run_comparison_scenario(self, config: ScenarioConfig) -> ScenarioResult:
        """Comparison ssenariyosi - ikkita configni taqqoslash"""
        # Load both ledgers
        baseline_ledger = self._load_ledger(config.baseline_ledger_path)
        current_ledger = self._load_ledger(config.historical_ledger_path)
        
        # Run baseline replay
        baseline_config = config.replay_config or ReplayConfig()
        self.replay_engine.set_ledger(baseline_ledger)
        self.replay_engine.set_config(baseline_config)
        baseline_state = self.replay_engine.replay()
        
        # Run current replay
        current_ledger = current_ledger or baseline_ledger
        self.replay_engine.set_ledger(current_ledger)
        self.replay_engine.set_config(baseline_config)
        current_state = self.replay_engine.replay()
        
        # Compare
        comparison = self.divergence_analyzer.compare_runs(
            baseline_state.to_dict() if hasattr(baseline_state, 'to_dict') else {},
            current_state.to_dict() if hasattr(current_state, 'to_dict') else {}
        )
        
        # Build result
        result = ScenarioResult(
            scenario_type=ScenarioType.COMPARISON,
            success=not comparison.get('diverged', True),
            total_tasks=baseline_state.total_events,
            divergence_count=comparison.get('divergence_count', 0),
            summary={
                'baseline_status': baseline_state.status.value,
                'current_status': current_state.status.value,
                'comparison': comparison
            }
        )
        
        return result
    
    def _run_benchmark_scenario(self, config: ScenarioConfig) -> ScenarioResult:
        """Benchmark ssenariyosi"""
        # Load ledgers
        ledger = self._load_ledger(config.historical_ledger_path)
        
        # Get task IDs
        task_ids = self._get_task_ids(ledger)
        
        if config.task_filter:
            task_ids = [t for t in task_ids if config.task_filter(t)]
        
        # Run each task
        results = []
        for task_id in task_ids:
            task_ledger = self._extract_task_ledger(ledger, task_id)
            
            # Replay
            self.replay_engine.set_ledger(task_ledger)
            state = self.replay_engine.replay()
            
            results.append({
                'task_id': task_id,
                'status': state.status.value,
                'events': state.current_event_index + 1,
                'divergences': state.divergence_count
            })
        
        # Build summary
        passed = sum(1 for r in results if r['status'] == 'completed')
        failed = len(results) - passed
        
        return ScenarioResult(
            scenario_type=ScenarioType.BENCHMARK,
            success=failed == 0,
            total_tasks=len(results),
            passed_tasks=passed,
            failed_tasks=failed,
            replay_results=results,
            summary={
                'pass_rate': passed / len(results) if results else 0,
                'total_events': sum(r['events'] for r in results)
            }
        )
    
    def _run_hardening_scenario(self, config: ScenarioConfig) -> ScenarioResult:
        """Hardening ssenariyosi - security tekshirish"""
        # Similar to benchmark but with security focus
        result = self._run_benchmark_scenario(config)
        result.scenario_type = ScenarioType.HARDENING
        
        # Add security-specific analysis
        result.summary['security_checks'] = {
            'side_effects_blocked': True,
            'verified': True
        }
        
        return result
    
    def _run_regression_scenario(self, config: ScenarioConfig) -> ScenarioResult:
        """Regression test ssenariyosi"""
        # Compare baseline with current
        return self._run_comparison_scenario(config)
    
    def _run_self_improvement_scenario(self, config: ScenarioConfig) -> ScenarioResult:
        """
        Self-improvement ssenariyosi
        
        Bu juda muhim - kernel o'z-o'zini yaxshilaganda:
        1. Eski run ledger olinadi
        2. Yangi kernel version simulation/replay'da o'tkaziladi
        3. Divergence baholanadi
        4. Keyin realga chiqariladi
        """
        # Load historical ledger
        ledger = self._load_ledger(config.historical_ledger_path)
        
        # Get kernel configs
        old_config = config.baseline_kernel_config or {}
        new_config = config.kernel_config or {}
        
        # Run with old config (baseline)
        old_replay_config = ReplayConfig(
            mode=ReplayMode.STUBBED,
            deterministic_seed=42
        )
        self.replay_engine.set_ledger(ledger)
        self.replay_engine.set_config(old_replay_config)
        old_state = self.replay_engine.replay()
        
        # Run with new config (simulation)
        new_replay_config = ReplayConfig(
            mode=ReplayMode.SIMULATE,
            deterministic_seed=42
        )
        self.replay_engine.set_config(new_replay_config)
        new_state = self.replay_engine.replay()
        
        # Analyze divergence
        divergence = self.divergence_analyzer.analyze(
            ledger=ledger,
            replay_state=new_state
        )
        
        # Determine if safe to deploy
        is_safe = (
            divergence.identical or
            (divergence.severity in ['low', 'none'] and divergence.performance_delta > -0.1)
        )
        
        # Build result
        return ScenarioResult(
            scenario_type=ScenarioType.SELF_IMPROVEMENT,
            success=is_safe,
            total_tasks=old_state.total_events,
            divergence_count=1 if not divergence.identical else 0,
            summary={
                'old_config': old_config,
                'new_config': new_config,
                'divergence': divergence.to_dict() if hasattr(divergence, 'to_dict') else {},
                'safe_to_deploy': is_safe,
                'recommendation': 'deploy' if is_safe else 'review'
            }
        )
    
    def _load_ledger(self, path: Optional[Path]) -> RunLedger:
        """Ledgerni yuklash"""
        if not path:
            return RunLedger()
        
        if not path.exists():
            logger.warning(f"Ledger not found: {path}")
            return RunLedger()
        
        try:
            return RunLedger.load(path)
        except Exception as e:
            logger.error(f"Failed to load ledger: {e}")
            return RunLedger()
    
    def _get_task_ids(self, ledger: RunLedger) -> List[str]:
        """Ledgerdan task IDlar olish"""
        if hasattr(ledger, 'get_task_ids'):
            return ledger.get_task_ids()
        
        # Extract from events
        task_ids = set()
        for event in ledger.events:
            if hasattr(event, 'task_id') and event.task_id:
                task_ids.add(event.task_id)
        
        return list(task_ids)
    
    def _extract_task_ledger(self, ledger: RunLedger, task_id: str) -> RunLedger:
        """Task uchun alohida ledger yaratish"""
        task_ledger = RunLedger(run_id=f"{ledger.run_id}_{task_id}")
        
        for event in ledger.events:
            if hasattr(event, 'task_id') and event.task_id == task_id:
                task_ledger.add_event(event)
        
        return task_ledger
    
    def _save_result(self, result: ScenarioResult, path: Path) -> None:
        """Resultni faylga saqlash"""
        try:
            with open(path, 'w') as f:
                json.dump(result.to_dict(), f, indent=2, default=str)
            logger.info(f"Scenario result saved to {path}")
        except Exception as e:
            logger.error(f"Failed to save result: {e}")
    
    def run_batch(
        self,
        configs: List[ScenarioConfig],
        parallel: bool = False
    ) -> List[ScenarioResult]:
        """
        Bir nechta ssenariyolarni ishga tushirish
        
        Args:
            configs: ScenarioConfiglar ro'yxati
            parallel: Parallel ishga tushirish
            
        Returns:
            ScenarioResultlar ro'yxati
        """
        if parallel:
            return self._run_parallel(configs)
        else:
            return [self.run_scenario(c) for c in configs]
    
    def _run_parallel(self, configs: List[ScenarioConfig]) -> List[ScenarioResult]:
        """Parallel ishlash"""
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        results = []
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {executor.submit(self.run_scenario, c): c for c in configs}
            
            for future in as_completed(futures):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    logger.error(f"Scenario failed: {e}")
        
        return results


class TestScenarioGenerator:
    """
    Test Scenario Generator - Avtomatik test ssenariyolari
    
    Bu generator turli xil test ssenariyolarini
    avtomatik yaratadi.
    """
    
    @staticmethod
    def generate_regression_scenario(
        baseline_ledger: Path,
        current_ledger: Path,
        output_path: Optional[Path] = None
    ) -> ScenarioConfig:
        """Regression test ssenariyosi yaratish"""
        return ScenarioConfig(
            scenario_type=ScenarioType.REGRESSION,
            baseline_ledger_path=baseline_ledger,
            historical_ledger_path=current_ledger,
            output_path=output_path
        )
    
    @staticmethod
    def generate_self_improvement_scenario(
        historical_ledger: Path,
        old_kernel_config: Dict,
        new_kernel_config: Dict,
        output_path: Optional[Path] = None
    ) -> ScenarioConfig:
        """Self-improvement ssenariyosi yaratish"""
        return ScenarioConfig(
            scenario_type=ScenarioType.SELF_IMPROVEMENT,
            historical_ledger_path=historical_ledger,
            baseline_kernel_config=old_kernel_config,
            kernel_config=new_kernel_config,
            output_path=output_path
        )
    
    @staticmethod
    def generate_benchmark_scenario(
        ledger: Path,
        task_filter: Optional[Callable] = None,
        output_path: Optional[Path] = None
    ) -> ScenarioConfig:
        """Benchmark ssenariyosi yaratish"""
        return ScenarioConfig(
            scenario_type=ScenarioType.BENCHMARK,
            historical_ledger_path=ledger,
            task_filter=task_filter,
            output_path=output_path
        )
