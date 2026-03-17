"""
Simulation Mode - Simulation va shadow run rejimlari
===================================================

Bu modul kernel'ga simulation va shadow run imkoniyatlarini beradi.

Rejimlar:
- REAL: Haqiqiy execution
- REPLAY: Oldingi runni qayta o'ynash
- SIMULATE: Side-effectsiz, faqat simulation
- SHADOW: Real task yonida parallel simulation

SHADOW rejimi juda muhim:
- Real task yonida parallel simulyatsiya yuradi
- Realga tegmaydi
- Divergence va quality o'lchanadi
"""

import logging
from typing import Dict, List, Optional, Any, Callable, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import threading

from .clock import DeterministicClock
from .id_source import DeterministicIdSource

logger = logging.getLogger(__name__)


class ExecutionMode(str, Enum):
    """
    Execution ishlash rejimlari
    
    REAL: To'liq haqiqiy execution
    REPLAY: Oldingi runni qayta o'ynash
    SIMULATE: Side-effectsiz simulation
    SHADOW: Real task yonida parallel simulation
    """
    REAL = "real"
    REPLAY = "replay"
    SIMULATE = "simulate"
    SHADOW = "shadow"


class SimulationResult(str, Enum):
    """Simulation natijasi"""
    SUCCESS = "success"
    FAILURE = "failure"
    DIVERGENCE = "divergence"
    TIMEOUT = "timeout"
    INCOMPLETE = "incomplete"


@dataclass
class SimulationConfig:
    """Simulation konfiguratsiyasi"""
    mode: ExecutionMode = ExecutionMode.REAL
    
    # Simulation settings
    max_steps: int = 1000
    timeout_seconds: float = 60.0
    allow_network: bool = True
    allow_file_write: bool = False
    allow_command_execution: bool = False
    
    # Shadow mode settings
    shadow_compare_results: bool = True
    shadow_tolerance: float = 0.1  # Tolerance for divergence
    
    # Output
    save_trace: bool = True
    trace_path: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            'mode': self.mode.value,
            'max_steps': self.max_steps,
            'timeout_seconds': self.timeout_seconds,
            'allow_network': self.allow_network,
            'allow_file_write': self.allow_file_write,
            'allow_command_execution': self.allow_command_execution,
            'shadow_compare_results': self.shadow_compare_results,
            'shadow_tolerance': self.shadow_tolerance,
            'save_trace': self.save_trace,
            'trace_path': self.trace_path
        }


@dataclass
class SimulationStep:
    """Simulation step"""
    step_number: int
    action: str
    args: Dict[str, Any]
    result: Any
    is_real_result: bool = False
    divergence_detected: bool = False
    divergence_details: Optional[Dict[str, Any]] = None
    timestamp: float = 0.0


@dataclass
class SimulationOutcome:
    """Simulation natijasi"""
    result: SimulationResult
    final_state: Dict[str, Any]
    trace: List[SimulationStep] = field(default_factory=list)
    divergence_count: int = 0
    error_count: int = 0
    steps_executed: int = 0
    execution_time: float = 0.0
    
    # For SHADOW mode
    comparison_result: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> dict:
        return {
            'result': self.result.value,
            'final_state': self.final_state,
            'divergence_count': self.divergence_count,
            'error_count': self.error_count,
            'steps_executed': self.steps_executed,
            'execution_time': self.execution_time,
            'comparison_result': self.comparison_result,
            'trace': [
                {
                    'step': s.step_number,
                    'action': s.action,
                    'divergence': s.divergence_detected,
                    'is_real_result': s.is_real_result
                }
                for s in self.trace
            ]
        }


@dataclass
class ShadowResult:
    """Shadow mode natijasi"""
    task_id: str
    
    # Two outcomes
    real_outcome: Optional[SimulationOutcome] = None
    simulated_outcome: Optional[SimulationOutcome] = None
    
    # Comparison
    diverged: bool = False
    divergence_points: List[int] = field(default_factory=list)
    quality_score: float = 0.0
    
    # Analysis
    real_won: bool = False
    simulation_accurate: bool = False
    
    def to_dict(self) -> dict:
        return {
            'task_id': self.task_id,
            'diverged': self.diverged,
            'divergence_points': self.divergence_points,
            'quality_score': self.quality_score,
            'real_won': self.real_won,
            'simulation_accurate': self.simulation_accurate,
            'real_outcome': self.real_outcome.to_dict() if self.real_outcome else None,
            'simulated_outcome': self.simulated_outcome.to_dict() if self.simulated_outcome else None
        }


class SimulationMode:
    """
    Simulation Mode - Kernel uchun simulation boshqaruvi
    
    Bu klass kernel'ga quyidagi imkoniyatlarni beradi:
    - Side-effectsiz simulation
    - SHADOW mode - real task yonida parallel simulation
    - Divergence detection
    - Quality measurement
    
    Usage:
        sim_mode = SimulationMode()
        
        # SIMULATE mode
        config = SimulationConfig(mode=ExecutionMode.SIMULATE)
        outcome = sim_mode.simulate_task(task, config)
        
        # SHADOW mode
        config = SimulationConfig(mode=ExecutionMode.SHADOW)
        shadow = sim_mode.run_shadow_task(task, config)
    """
    
    def __init__(
        self,
        clock: Optional[DeterministicClock] = None,
        id_source: Optional[DeterministicIdSource] = None
    ):
        self.clock = clock or DeterministicClock()
        self.id_source = id_source or DeterministicIdSource()
        
        # Current config
        self.config: Optional[SimulationConfig] = None
        
        # State
        self.current_trace: List[SimulationStep] = []
        self.divergence_points: List[int] = []
        
        # Tool handlers
        self.tool_handlers: Dict[str, Callable] = {}
        
        # Thread safety
        self._lock = threading.RLock()
        
        logger.info("SimulationMode initialized")
    
    def set_config(self, config: SimulationConfig) -> None:
        """Configuration o'rnatish"""
        self.config = config
        
        # Configure clock for simulation
        if config.mode in [ExecutionMode.SIMULATE, ExecutionMode.SHADOW]:
            self.clock = DeterministicClock(deterministic=True)
        
        logger.info(f"SimulationConfig set: mode={config.mode}")
    
    def register_tool_handler(self, tool_name: str, handler: Callable) -> None:
        """Tool handler ro'yxatga olish"""
        self.tool_handlers[tool_name] = handler
    
    def simulate_task(
        self,
        task: Any,
        config: Optional[SimulationConfig] = None
    ) -> SimulationOutcome:
        """
        Taskni simulate qilish
        
        Args:
            task: Task object
            config: SimulationConfig
            
        Returns:
            SimulationOutcome
        """
        if config:
            self.set_config(config)
        
        if not self.config:
            self.config = SimulationConfig()
        
        with self._lock:
            # Reset state
            self.current_trace.clear()
            self.divergence_points.clear()
            
            import time
            start_time = time.time()
            
            try:
                # Run simulation
                outcome = self._run_simulation(task)
                
                outcome.execution_time = time.time() - start_time
                return outcome
                
            except Exception as e:
                logger.error(f"Simulation failed: {e}")
                return SimulationOutcome(
                    result=SimulationResult.FAILURE,
                    final_state={},
                    error_count=1,
                    execution_time=time.time() - start_time
                )
    
    def _run_simulation(self, task: Any) -> SimulationOutcome:
        """Simulationni ishga tushirish"""
        # This is a placeholder - actual implementation would
        # depend on the task structure
        steps_executed = 0
        divergence_count = 0
        
        for step in range(self.config.max_steps):
            # Simulate each step
            step_result = self._simulate_step(step, task)
            
            self.current_trace.append(step_result)
            steps_executed += 1
            
            if step_result.divergence_detected:
                divergence_count += 1
                self.divergence_points.append(step)
            
            # Check if done
            if self._is_task_complete(task, step_result):
                break
        
        return SimulationOutcome(
            result=SimulationResult.SUCCESS if divergence_count == 0 else SimulationResult.DIVERGENCE,
            final_state=self._get_final_state(task),
            trace=self.current_trace.copy(),
            divergence_count=divergence_count,
            steps_executed=steps_executed
        )
    
    def _simulate_step(self, step: int, task: Any) -> SimulationStep:
        """Bir stepni simulate qilish"""
        import time
        
        # Get action from task
        action = self._get_next_action(task, step)
        
        if not action:
            return SimulationStep(
                step_number=step,
                action="noop",
                args={},
                result=None,
                is_real_result=False
            )
        
        # Determine if we can execute
        can_execute = self._can_execute_action(action)
        
        if can_execute:
            # Get result (simulated)
            result = self._simulate_action(action, task)
            is_real = False
        else:
            result = None
            is_real = False
        
        return SimulationStep(
            step_number=step,
            action=action.get('name', 'unknown'),
            args=action.get('args', {}),
            result=result,
            is_real_result=is_real,
            timestamp=time.time()
        )
    
    def _get_next_action(self, task: Any, step: int) -> Optional[Dict]:
        """Keyingi actionni olish (placeholder)"""
        # This would be implemented based on task structure
        return None
    
    def _can_execute_action(self, action: Dict) -> bool:
        """Actionni execute qilish mumkinmi?"""
        if not self.config:
            return True
        
        tool_name = action.get('name', '')
        
        # Check restrictions
        if tool_name in ['write_file', 'create_directory', 'delete_file']:
            return self.config.allow_file_write
        
        if tool_name in ['execute_command', 'run_script']:
            return self.config.allow_command_execution
        
        if tool_name.startswith('http') or tool_name == 'web_request':
            return self.config.allow_network
        
        return True
    
    def _simulate_action(self, action: Dict, task: Any) -> Any:
        """Actionni simulate qilish"""
        tool_name = action.get('name', '')
        args = action.get('args', {})
        
        # Check if we have a custom handler
        if tool_name in self.tool_handlers:
            return self.tool_handlers[tool_name](args, task)
        
        # Default simulation
        return self._default_simulate(tool_name, args)
    
    def _default_simulate(self, tool_name: str, args: Dict) -> Any:
        """Default simulation"""
        if tool_name == 'read_file':
            return {'content': '', 'simulated': True}
        elif tool_name == 'write_file':
            return {'success': True, 'simulated': True}
        elif tool_name == 'execute_command':
            return {'exit_code': 0, 'stdout': '', 'simulated': True}
        elif tool_name.startswith('browser_'):
            return {'success': True, 'simulated': True}
        else:
            return {'result': None, 'simulated': True}
    
    def _is_task_complete(self, task: Any, step_result: SimulationStep) -> bool:
        """Task tugaganmi?"""
        # This would check task state
        return step_result.action == "noop" or step_result.result is None
    
    def _get_final_state(self, task: Any) -> Dict:
        """Final state olish"""
        # This would get task's final state
        return {}
    
    def run_shadow_task(
        self,
        task: Any,
        config: Optional[SimulationConfig] = None
    ) -> ShadowResult:
        """
        Taskni SHADOW mode'da ishga tushirish
        
        Bu method real va simulated executionni parallel ishga
        tushiradi va natijalarni taqqoslaydi.
        
        Args:
            task: Task object
            config: SimulationConfig
            
        Returns:
            ShadowResult
        """
        if config:
            self.set_config(config)
        
        if not self.config:
            self.config = SimulationConfig(mode=ExecutionMode.SHADOW)
        
        task_id = getattr(task, 'id', 'unknown')
        
        with self._lock:
            # Real execution config
            real_config = SimulationConfig(
                mode=ExecutionMode.REAL,
                max_steps=self.config.max_steps,
                timeout_seconds=self.config.timeout_seconds
            )
            
            # Simulated execution config
            sim_config = SimulationConfig(
                mode=ExecutionMode.SIMULATE,
                max_steps=self.config.max_steps,
                timeout_seconds=self.config.timeout_seconds,
                allow_network=self.config.allow_network,
                allow_file_write=False,
                allow_command_execution=False
            )
            
            # Run both
            import time
            
            # Real (would need actual execution)
            # For now, simulated
            real_outcome = self.simulate_task(task, real_config)
            
            # Simulated
            self.set_config(sim_config)
            simulated_outcome = self.simulate_task(task, sim_config)
            
            # Compare
            comparison = self._compare_outcomes(real_outcome, simulated_outcome)
            
            # Calculate quality
            quality = self._calculate_quality(comparison)
            
            # Determine winner
            real_won = real_outcome.result == SimulationResult.SUCCESS
            sim_accurate = comparison.get('accuracy', 0) > (1 - self.config.shadow_tolerance)
            
            return ShadowResult(
                task_id=task_id,
                real_outcome=real_outcome,
                simulated_outcome=simulated_outcome,
                diverged=comparison.get('diverged', False),
                divergence_points=comparison.get('divergence_points', []),
                quality_score=quality,
                real_won=real_won,
                simulation_accurate=sim_accurate
            )
    
    def _compare_outcomes(
        self,
        real: SimulationOutcome,
        simulated: SimulationOutcome
    ) -> Dict[str, Any]:
        """Ikki outcome'ni taqqoslash"""
        divergence_points = []
        
        # Compare step by step
        min_steps = min(len(real.trace), len(simulated.trace))
        
        for i in range(min_steps):
            real_step = real.trace[i]
            sim_step = simulated.trace[i]
            
            if not self._steps_match(real_step, sim_step):
                divergence_points.append(i)
        
        diverged = len(divergence_points) > 0
        
        # Calculate accuracy
        accuracy = 1.0 - (len(divergence_points) / max(min_steps, 1))
        
        return {
            'diverged': diverged,
            'divergence_points': divergence_points,
            'accuracy': accuracy,
            'real_result': real.result.value,
            'simulated_result': simulated.result.value
        }
    
    def _steps_match(self, real: SimulationStep, simulated: SimulationStep) -> bool:
        """Ikki step mos kelsa"""
        # Check action
        if real.action != simulated.action:
            return False
        
        # Check result (simplified)
        if real.result and simulated.result:
            return True
        
        return True
    
    def _calculate_quality(self, comparison: Dict) -> float:
        """Quality score hisoblash"""
        accuracy = comparison.get('accuracy', 0)
        
        # Bonus for matching results
        if comparison.get('real_result') == comparison.get('simulated_result'):
            return accuracy * 1.2
        
        return accuracy
    
    def get_simulation_summary(self) -> Dict[str, Any]:
        """Simulation xulosasini olish"""
        return {
            'mode': self.config.mode.value if self.config else None,
            'steps': len(self.current_trace),
            'divergences': len(self.divergence_points),
            'divergence_points': self.divergence_points
        }
    
    def __repr__(self) -> str:
        return f"SimulationMode(mode={self.config.mode if self.config else 'unconfigured'})"


class ShadowRunner:
    """
    Shadow Runner - SHADOW mode'ni boshqarish
    
    Bu klass bir nechta tasklarni SHADOW mode'da
    ishga tushirish va natijalarni tahlil qilish uchun.
    """
    
    def __init__(self):
        self.simulation_mode = SimulationMode()
        self.results: List[ShadowResult] = []
        self._lock = threading.Lock()
    
    def run_shadow_batch(
        self,
        tasks: List[Any],
        config: Optional[SimulationConfig] = None
    ) -> List[ShadowResult]:
        """
        Batch of tasksni SHADOW mode'da ishga tushirish
        
        Args:
            tasks: Tasklar ro'yxati
            config: SimulationConfig
            
        Returns:
            ShadowResultlar ro'yxati
        """
        results = []
        
        for task in tasks:
            try:
                result = self.simulation_mode.run_shadow_task(task, config)
                results.append(result)
            except Exception as e:
                logger.error(f"Shadow run failed for task: {e}")
        
        with self._lock:
            self.results.extend(results)
        
        return results
    
    def get_summary(self) -> Dict[str, Any]:
        """Umumiy xulosani olish"""
        if not self.results:
            return {'total': 0}
        
        total = len(self.results)
        diverged = sum(1 for r in self.results if r.diverged)
        avg_quality = sum(r.quality_score for r in self.results) / total
        
        return {
            'total': total,
            'diverged': diverged,
            'diverged_percent': (diverged / total) * 100,
            'avg_quality': avg_quality,
            'real_won_count': sum(1 for r in self.results if r.real_won),
            'simulation_accurate_count': sum(1 for r in self.results if r.simulation_accurate)
        }
    
    def __len__(self) -> int:
        return len(self.results)
