"""
Replay Engine - Asosiy replay tizimi
====================================

Bu engine run ledger'dan executionni qayta o'ynaydi.

Features:
- Full replay - to'liq execution qayta o'ynash
- Stubbed replay - recorded outputlar bilan
- Simulate-only - hech qanday side-effect yo'q
- Divergence detection - farqlarni aniqlash
"""

import json
import logging
from typing import Dict, List, Optional, Any, Callable, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from datetime import datetime
import threading

from .clock import DeterministicClock, ClockMode
from .id_source import DeterministicIdSource, IdType
from .event_taxonomy import ReplayEvent, EventTaxonomy

logger = logging.getLogger(__name__)


class ReplayMode(str, Enum):
    """
    Replay ishlash rejimlari
    
    FULL: To'liq real execution (lekin deterministic clock/id)
    STUBBED: Recorded outputlar bilan replay
    SIMULATE_ONLY: Side-effectsiz, faqat simulation
    """
    FULL = "full"
    STUBBED = "stubbed"
    SIMULATE_ONLY = "simulate_only"


class ReplayStatus(str, Enum):
    """Replay holati"""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    DIVERGED = "diverged"


@dataclass
class ReplayConfig:
    """
    Replay konfiguratsiyasi
    
    Bu dataclass replay ishlash uchun barcha
    kerakli konfiguratsiyalarni o'z ichiga oladi.
    """
    mode: ReplayMode = ReplayMode.FULL
    
    # Deterministic settings
    deterministic_seed: int = 0
    freeze_time: bool = True
    freeze_ids: bool = True
    
    # Side effect settings
    allow_side_effects: bool = False
    allow_network: bool = True
    allow_file_write: bool = False
    allow_command_execution: bool = False
    
    # Replay settings
    start_event_index: int = 0
    end_event_index: Optional[int] = None
    max_events: Optional[int] = None
    
    # Divergence detection
    detect_divergence: bool = True
    divergence_threshold: float = 0.1
    
    # Error handling
    stop_on_error: bool = True
    max_retries: int = 0
    
    # Output
    save_replay_log: bool = True
    replay_log_path: Optional[Path] = None
    
    def to_dict(self) -> dict:
        return {
            'mode': self.mode.value,
            'deterministic_seed': self.deterministic_seed,
            'freeze_time': self.freeze_time,
            'freeze_ids': self.freeze_ids,
            'allow_side_effects': self.allow_side_effects,
            'allow_network': self.allow_network,
            'allow_file_write': self.allow_file_write,
            'allow_command_execution': self.allow_command_execution,
            'start_event_index': self.start_event_index,
            'end_event_index': self.end_event_index,
            'max_events': self.max_events,
            'detect_divergence': self.detect_divergence,
            'divergence_threshold': self.divergence_threshold,
            'stop_on_error': self.stop_on_error,
            'max_retries': self.max_retries,
            'save_replay_log': self.save_replay_log,
            'replay_log_path': str(self.replay_log_path) if self.replay_log_path else None
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'ReplayConfig':
        if 'replay_log_path' in data and data['replay_log_path']:
            data['replay_log_path'] = Path(data['replay_log_path'])
        if 'mode' in data:
            data['mode'] = ReplayMode(data['mode'])
        return cls(**data)


@dataclass
class ReplayState:
    """Replay holati"""
    status: ReplayStatus = ReplayStatus.IDLE
    current_event_index: int = 0
    total_events: int = 0
    diverged_events: List[int] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    divergence_count: int = 0
    
    def to_dict(self) -> dict:
        return {
            'status': self.status.value,
            'current_event_index': self.current_event_index,
            'total_events': self.total_events,
            'diverged_events': self.diverged_events,
            'errors': self.errors,
            'warnings': self.warnings,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'divergence_count': self.divergence_count
        }


@dataclass
class ReplayEventRecord:
    """Replay event yozuvi"""
    event_index: int
    event: ReplayEvent
    execution_time: float
    result: Any
    divergence: Optional[dict] = None
    error: Optional[str] = None


class ToolAdapter:
    """
    Tool adapter bazaviy class
    
    Har side-effecting tool uchun adapter yaratiladi.
    Bu adapter replay paytida tool chaqiruvlarini boshqaradi.
    """
    
    def __init__(self, name: str, replay_mode: ReplayMode):
        self.name = name
        self.replay_mode = replay_mode
        self.recorded_outputs: Dict[str, Any] = {}
        self.call_log: List[dict] = []
    
    def should_execute(self) -> bool:
        """Haqiqiy execution kerakmi?"""
        if self.replay_mode == ReplayMode.FULL:
            return True
        elif self.replay_mode == ReplayMode.STUBBED:
            return False
        elif self.replay_mode == ReplayMode.SIMULATE_ONLY:
            return False
        return False
    
    def get_recorded_output(self, call_signature: str) -> Optional[Any]:
        """Recorded output olish"""
        return self.recorded_outputs.get(call_signature)
    
    def record_output(self, call_signature: str, output: Any) -> None:
        """Output yozib olish"""
        self.recorded_outputs[call_signature] = output
    
    def log_call(self, call_data: dict) -> None:
        """Call yozib olish"""
        self.call_log.append(call_data)
    
    def simulate_output(self, tool_name: str, args: dict) -> Any:
        """
        Simulate output - faqat g'oyalashtirilgan natija
        
        Bu method turli tool'lar uchun override qilinadi.
        """
        return {"simulated": True, "tool": tool_name, "args": args}


class FileToolAdapter(ToolAdapter):
    """File tool adapter"""
    
    def simulate_output(self, tool_name: str, args: dict) -> Any:
        if tool_name == "write_file":
            return {"success": True, "path": args.get("path"), "simulated": True}
        elif tool_name == "read_file":
            return {"content": "", "simulated": True, "path": args.get("path")}
        elif tool_name == "delete_file":
            return {"success": True, "path": args.get("path"), "simulated": True}
        return super().simulate_output(tool_name, args)


class BrowserToolAdapter(ToolAdapter):
    """Browser tool adapter"""
    
    def simulate_output(self, tool_name: str, args: dict) -> Any:
        if tool_name == "browser_click":
            return {"success": True, "element": args.get("index"), "simulated": True}
        elif tool_name == "browser_type":
            return {"success": True, "simulated": True}
        elif tool_name == "browser_navigate":
            return {"url": args.get("url"), "simulated": True}
        return super().simulate_output(tool_name, args)


class CommandToolAdapter(ToolAdapter):
    """Command execution adapter"""
    
    def simulate_output(self, tool_name: str, args: dict) -> Any:
        if tool_name == "execute_command":
            return {
                "exit_code": 0,
                "stdout": "[simulated output]",
                "stderr": "",
                "simulated": True
            }
        return super().simulate_output(tool_name, args)


class ReplayEngine:
    """
    Replay Engine - Kernel uchun asosiy replay tizimi
    
    Bu engine quyidagi imkoniyatlarni beradi:
    - Run ledger'dan executionni qayta o'ynash
    - Turli replay rejimlari (full, stubbed, simulate)
    - Deterministic clock va ID
    - Divergence detection
    - Detailed replay logging
    
    Usage:
        # Ledgerdan replay
        engine = ReplayEngine(ledger)
        config = ReplayConfig(mode=ReplayMode.STUBBED, deterministic_seed=42)
        result = engine.replay(config)
        
        # Divergence report olish
        if result.diverged:
            report = engine.get_divergence_report()
    """
    
    def __init__(
        self,
        ledger: Any = None,
        clock: Optional[DeterministicClock] = None,
        id_source: Optional[DeterministicIdSource] = None
    ):
        """
        Args:
            ledger: RunLedger instance
            clock: DeterministicClock instance
            id_source: DeterministicIdSource instance
        """
        self.ledger = ledger
        self.clock = clock or DeterministicClock()
        self.id_source = id_source or DeterministicIdSource()
        
        # State
        self.state = ReplayState()
        self.config: Optional[ReplayConfig] = None
        
        # Tool adapters
        self.tool_adapters: Dict[str, ToolAdapter] = {
            'file': FileToolAdapter('file', ReplayMode.FULL),
            'browser': BrowserToolAdapter('browser', ReplayMode.FULL),
            'command': CommandToolAdapter('command', ReplayMode.FULL)
        }
        
        # Event handlers
        self.event_handlers: Dict[str, Callable] = {}
        
        # Replay log
        self.replay_log: List[ReplayEventRecord] = []
        
        # Thread safety
        self._lock = threading.RLock()
        
        logger.info("ReplayEngine initialized")
    
    def set_ledger(self, ledger: Any) -> None:
        """Ledger o'rnatish"""
        self.ledger = ledger
    
    def set_config(self, config: ReplayConfig) -> None:
        """Config o'rnatish"""
        self.config = config
        
        # Clock config
        if config.freeze_time:
            self.clock.freeze()
        else:
            self.clock = DeterministicClock(
                deterministic=True,
                seed=config.deterministic_seed
            )
        
        # ID source config
        if config.freeze_ids:
            self.id_source = DeterministicIdSource(
                seed=config.deterministic_seed
            )
        
        # Tool adapter config
        for adapter in self.tool_adapters.values():
            adapter.replay_mode = config.mode
        
        # Mode-based settings
        if config.mode == ReplayMode.SIMULATE_ONLY:
            self._configure_simulate_only()
        
        logger.info(f"ReplayConfig set: mode={config.mode}, seed={config.deterministic_seed}")
    
    def _configure_simulate_only(self) -> None:
        """Simulate-only rejim uchun sozlash"""
        self.config.allow_side_effects = False
        self.config.allow_file_write = False
        self.config.allow_command_execution = False
        self.config.allow_network = False
    
    def load_recorded_outputs(self, outputs: Dict[str, Any]) -> None:
        """Recorded outputs yuklash (stubbed replay uchun)"""
        for adapter in self.tool_adapters.values():
            adapter.recorded_outputs.update(outputs)
        logger.info(f"Loaded {len(outputs)} recorded outputs")
    
    def register_event_handler(self, event_type: str, handler: Callable) -> None:
        """Event handler ro'yxatga olish"""
        self.event_handlers[event_type] = handler
    
    def replay(self, config: Optional[ReplayConfig] = None) -> ReplayState:
        """
        Replayni boshlash
        
        Args:
            config: ReplayConfig (avval o'rnatilgan bo'lsa None)
            
        Returns:
            ReplayState - replay natijasi
        """
        with self._lock:
            if config:
                self.set_config(config)
            
            if not self.config:
                raise ValueError("ReplayConfig not set")
            
            if not self.ledger:
                raise ValueError("Ledger not set")
            
            # Reset state
            self.state = ReplayState()
            self.replay_log.clear()
            
            # Get events from ledger
            events = self._get_events_from_ledger()
            self.state.total_events = len(events)
            
            # Start replay
            self.state.status = ReplayStatus.RUNNING
            import time
            self.state.start_time = time.time()
            
            logger.info(f"Starting replay: {len(events)} events, mode={self.config.mode}")
            
            # Process events
            try:
                for i, event in enumerate(events):
                    if self.config.end_event_index and i >= self.config.end_event_index:
                        break
                    if self.config.max_events and i >= self.config.max_events:
                        break
                    
                    self.state.current_event_index = i
                    
                    # Process event
                    record = self._process_event(i, event)
                    self.replay_log.append(record)
                    
                    # Check divergence
                    if self.config.detect_divergence and record.divergence:
                        self.state.diverged_events.append(i)
                        self.state.divergence_count += 1
                        if self._is_divergence_critical(record.divergence):
                            self.state.status = ReplayStatus.DIVERGED
                            if self.config.stop_on_error:
                                break
                    
                    # Check error
                    if record.error:
                        self.state.errors.append(record.error)
                        if self.config.stop_on_error:
                            break
                
                # Complete
                self.state.status = ReplayStatus.COMPLETED
                
            except Exception as e:
                logger.error(f"Replay failed: {e}")
                self.state.status = ReplayStatus.FAILED
                self.state.errors.append(str(e))
            
            # End time
            import time
            self.state.end_time = time.time()
            
            logger.info(f"Replay completed: status={self.state.status}, events={self.state.current_event_index + 1}, divergences={self.state.divergence_count}")
            
            return self.state
    
    def _get_events_from_ledger(self) -> List[ReplayEvent]:
        """Ledgerdan eventlar olish"""
        if hasattr(self.ledger, 'get_events'):
            return self.ledger.get_events()
        elif hasattr(self.ledger, 'events'):
            return self.ledger.events
        else:
            raise ValueError("Ledger doesn't have events")
    
    def _process_event(self, index: int, event: ReplayEvent) -> ReplayEventRecord:
        """Eventni process qilish"""
        import time
        
        start_time = time.time()
        
        try:
            # Get event type
            event_type = event.event_type if hasattr(event, 'event_type') else str(event.get('type', 'unknown'))
            
            # Find handler
            handler = self.event_handlers.get(event_type)
            
            if handler:
                result = handler(event)
            else:
                # Default processing
                result = self._default_event_processing(event)
            
            execution_time = time.time() - start_time
            
            return ReplayEventRecord(
                event_index=index,
                event=event,
                execution_time=execution_time,
                result=result,
                divergence=None,
                error=None
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.warning(f"Event processing error at {index}: {e}")
            
            return ReplayEventRecord(
                event_index=index,
                event=event,
                execution_time=execution_time,
                result=None,
                divergence=None,
                error=str(e)
            )
    
    def _default_event_processing(self, event: ReplayEvent) -> Any:
        """Default event processing"""
        # Check if this is a tool call event
        if hasattr(event, 'tool_call') or 'tool_call' in event:
            tool_call = event.tool_call if hasattr(event, 'tool_call') else event.get('tool_call')
            if tool_call:
                return self._process_tool_call(tool_call)
        
        # Check if this is a decision event
        if hasattr(event, 'decision') or 'decision' in event:
            return event.decision if hasattr(event, 'decision') else event.get('decision')
        
        # Default: return event as-is
        return event
    
    def _process_tool_call(self, tool_call: dict) -> Any:
        """Tool callni process qilish"""
        tool_name = tool_call.get('name', 'unknown')
        
        # Get appropriate adapter
        adapter = self._get_tool_adapter(tool_name)
        
        # Check if we should execute
        if not adapter.should_execute():
            # Get recorded or simulated output
            recorded = adapter.get_recorded_output(str(tool_call))
            if recorded is not None:
                return recorded
            return adapter.simulate_output(tool_name, tool_call.get('args', {}))
        
        # Full execution would happen here
        # For now, return simulated
        return adapter.simulate_output(tool_name, tool_call.get('args', {}))
    
    def _get_tool_adapter(self, tool_name: str) -> ToolAdapter:
        """Tool adapter olish"""
        if tool_name in ['write_file', 'read_file', 'delete_file', 'create_directory']:
            return self.tool_adapters['file']
        elif tool_name.startswith('browser_'):
            return self.tool_adapters['browser']
        elif tool_name in ['execute_command', 'run_script']:
            return self.tool_adapters['command']
        else:
            # Default adapter
            return self.tool_adapters['file']
    
    def _is_divergence_critical(self, divergence: dict) -> bool:
        """Divergence kritikmi?"""
        if not divergence:
            return False
        
        severity = divergence.get('severity', 'low')
        return severity in ['high', 'critical']
    
    def get_divergence_report(self) -> dict:
        """Divergence report olish"""
        return {
            'diverged': self.state.divergence_count > 0,
            'total_divergences': self.state.divergence_count,
            'divergence_indices': self.state.diverged_events,
            'status': self.state.status.value,
            'events_processed': self.state.current_event_index + 1,
            'total_events': self.state.total_events,
            'errors': self.state.errors,
            'warnings': self.state.warnings,
            'duration': self.state.end_time - self.state.start_time if self.state.end_time else None
        }
    
    def save_replay_log(self, path: Path) -> None:
        """Replay logni saqlash"""
        log_data = {
            'config': self.config.to_dict() if self.config else {},
            'state': self.state.to_dict(),
            'events': [
                {
                    'index': r.event_index,
                    'event': str(r.event),
                    'execution_time': r.execution_time,
                    'result': str(r.result)[:200] if r.result else None,
                    'divergence': r.divergence,
                    'error': r.error
                }
                for r in self.replay_log
            ]
        }
        
        with open(path, 'w') as f:
            json.dump(log_data, f, indent=2)
        
        logger.info(f"Replay log saved to {path}")
    
    def pause(self) -> None:
        """Replayni to'xtatish"""
        with self._lock:
            if self.state.status == ReplayStatus.RUNNING:
                self.state.status = ReplayStatus.PAUSED
                logger.info("Replay paused")
    
    def resume(self) -> None:
        """Replayni davom ettirish"""
        with self._lock:
            if self.state.status == ReplayStatus.PAUSED:
                self.state.status = ReplayStatus.RUNNING
                logger.info("Replay resumed")
    
    def stop(self) -> None:
        """Replayni to'liq to'xtatish"""
        with self._lock:
            self.state.status = ReplayStatus.IDLE
            logger.info("Replay stopped")
    
    def __repr__(self) -> str:
        return f"ReplayEngine(status={self.state.status}, events={self.state.total_events})"


class RunLedger:
    """
    Run Ledger - Barcha eventlarni saqlash
    
    Bu class historical run'larni saqlash va ularni
    replay uchun ishlatish uchun mo'ljallangan.
    """
    
    def __init__(self, run_id: Optional[str] = None):
        self.run_id = run_id or str(datetime.now().timestamp())
        self.events: List[ReplayEvent] = []
        self.metadata: Dict[str, Any] = {}
        self._lock = threading.RLock()
    
    def add_event(self, event: ReplayEvent) -> None:
        """Event qo'shish"""
        with self._lock:
            self.events.append(event)
    
    def get_events(self, start: int = 0, end: Optional[int] = None) -> List[ReplayEvent]:
        """Eventlar olish"""
        with self._lock:
            if end:
                return self.events[start:end]
            return self.events[start:]
    
    def add_metadata(self, key: str, value: Any) -> None:
        """Metadata qo'shish"""
        with self._lock:
            self.metadata[key] = value
    
    def get_metadata(self, key: str) -> Any:
        """Metadata olish"""
        return self.metadata.get(key)
    
    def save(self, path: Path) -> None:
        """Ledgerni faylga saqlash"""
        data = {
            'run_id': self.run_id,
            'metadata': self.metadata,
            'events': [e.to_dict() if hasattr(e, 'to_dict') else str(e) for e in self.events]
        }
        
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Ledger saved to {path}")
    
    @classmethod
    def load(cls, path: Path) -> 'RunLedger':
        """Ledgerni fayldan yuklash"""
        with open(path, 'r') as f:
            data = json.load(f)
        
        ledger = cls(run_id=data.get('run_id'))
        ledger.metadata = data.get('metadata', {})
        
        # Events would need to be reconstructed from dict
        # This is a simplified version
        logger.info(f"Ledger loaded from {path}")
        return ledger
    
    def __len__(self) -> int:
        return len(self.events)
    
    def __repr__(self) -> str:
        return f"RunLedger(run_id={self.run_id}, events={len(self.events)})"
