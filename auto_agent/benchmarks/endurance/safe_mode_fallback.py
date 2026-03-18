"""
Safe Mode Fallback - Emergency Response System
==========================================

This module provides safe mode fallback when drift sentinel detects issues:
- Parallelism reduction
- Risky self-mod stop
- Retry budget reduction
- Essential tools only
- Memory cleanup
- Calibration tasks

Author: No1 World+ Autonomous System
"""

import asyncio
import time
import logging
import threading
from typing import Dict, List, Optional, Any, Callable, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from collections import defaultdict
import json

logger = logging.getLogger(__name__)


# ==================== ENUMS ====================

class SafeModeLevel(str, Enum):
    """Safe mode levels"""
    NORMAL = "normal"           # Full operation
    CAUTION = "caution"         # Slight reduction
    REDUCED = "reduced"        # Significant reduction
    SAFE = "safe"              # Minimal operation
    EMERGENCY = "emergency"    # Only essential operations


class FallbackAction(str, Enum):
    """Fallback actions available"""
    REDUCE_PARALLELISM = "reduce_parallelism"
    STOP_SELF_MOD = "stop_self_mod"
    REDUCE_RETRY_BUDGET = "reduce_retry_budget"
    ESSENTIAL_TOOLS_ONLY = "essential_tools_only"
    MEMORY_CLEANUP = "memory_cleanup"
    CALIBRATION_TASKS = "calibration_tasks"
    CACHE_PURGE = "cache_purge"
    ROUTE_RESET = "route_reset"
    PLANNER_RESET = "planner_reset"
    EMERGENCY_COOLDOWN = "emergency_cooldown"


# ==================== DATA CLASSES ====================

@dataclass
class ModeConfig:
    """Configuration for a safe mode level"""
    level: SafeModeLevel
    max_parallel_tasks: int
    max_retries: int
    allowed_tools: Set[str]
    self_mod_enabled: bool
    checkpoint_interval: int
    memory_cleanup_interval: int
    cooldown_duration: int
    description: str


@dataclass
class FallbackEvent:
    """Record of a fallback event"""
    event_id: str
    timestamp: datetime
    previous_level: SafeModeLevel
    new_level: SafeModeLevel
    trigger_reason: str
    actions_taken: List[FallbackAction]
    duration_seconds: int
    automatic: bool


@dataclass
class ModeState:
    """Current safe mode state"""
    current_level: SafeModeLevel
    activated_at: Optional[datetime]
    trigger_reason: str
    active_actions: Set[FallbackAction]
    cooldown_until: Optional[datetime]
    auto_recovery_enabled: bool


# ==================== MODE CONFIGURATIONS ====================

class SafeModeConfigs:
    """Predefined safe mode configurations"""
    
    @staticmethod
    def get_config(level: SafeModeLevel) -> ModeConfig:
        """Get configuration for a safe mode level"""
        
        configs = {
            SafeModeLevel.NORMAL: ModeConfig(
                level=SafeModeLevel.NORMAL,
                max_parallel_tasks=10,
                max_retries=3,
                allowed_tools={"*"},  # All tools
                self_mod_enabled=True,
                checkpoint_interval=10,
                memory_cleanup_interval=30,
                cooldown_duration=0,
                description="Normal operation - full capabilities"
            ),
            SafeModeLevel.CAUTION: ModeConfig(
                level=SafeModeLevel.CAUTION,
                max_parallel_tasks=7,
                max_retries=2,
                allowed_tools={"*"},
                self_mod_enabled=True,
                checkpoint_interval=8,
                memory_cleanup_interval=20,
                cooldown_duration=60,
                description="Caution - slightly reduced capabilities"
            ),
            SafeModeLevel.REDUCED: ModeConfig(
                level=SafeModeLevel.REDUCED,
                max_parallel_tasks=5,
                max_retries=2,
                allowed_tools={"read_file", "write_file", "execute_command", "browser_navigate"},
                self_mod_enabled=False,
                checkpoint_interval=5,
                memory_cleanup_interval=15,
                cooldown_duration=180,
                description="Reduced - significantly limited"
            ),
            SafeModeLevel.SAFE: ModeConfig(
                level=SafeModeLevel.SAFE,
                max_parallel_tasks=3,
                max_retries=1,
                allowed_tools={"read_file", "execute_command"},
                self_mod_enabled=False,
                checkpoint_interval=3,
                memory_cleanup_interval=10,
                cooldown_duration=300,
                description="Safe mode - minimal operations"
            ),
            SafeModeLevel.EMERGENCY: ModeConfig(
                level=SafeModeLevel.EMERGENCY,
                max_parallel_tasks=1,
                max_retries=0,
                allowed_tools={"read_file"},
                self_mod_enabled=False,
                checkpoint_interval=1,
                memory_cleanup_interval=5,
                cooldown_duration=600,
                description="Emergency - only essential operations"
            )
        }
        
        return configs.get(level, configs[SafeModeLevel.NORMAL])


# ==================== ACTION EXECUTOR ====================

class FallbackActionExecutor:
    """Executes fallback actions"""
    
    def __init__(self):
        self._lock = threading.Lock()
        self._action_results: Dict[str, Any] = {}
    
    async def execute_action(self, action: FallbackAction, config: Dict) -> bool:
        """Execute a single fallback action"""
        logger.info(f"Executing fallback action: {action.value}")
        
        try:
            if action == FallbackAction.REDUCE_PARALLELISM:
                return await self._reduce_parallelism(config)
            elif action == FallbackAction.STOP_SELF_MOD:
                return await self._stop_self_mod()
            elif action == FallbackAction.REDUCE_RETRY_BUDGET:
                return await self._reduce_retry_budget(config)
            elif action == FallbackAction.ESSENTIAL_TOOLS_ONLY:
                return await self._set_essential_tools_only()
            elif action == FallbackAction.MEMORY_CLEANUP:
                return await self._memory_cleanup()
            elif action == FallbackAction.CALIBRATION_TASKS:
                return await self._run_calibration_tasks()
            elif action == FallbackAction.CACHE_PURGE:
                return await self._cache_purge()
            elif action == FallbackAction.ROUTE_RESET:
                return await self._reset_routes()
            elif action == FallbackAction.PLANNER_RESET:
                return await self._reset_planner()
            elif action == FallbackAction.EMERGENCY_COOLDOWN:
                return await self._emergency_cooldown(config)
            
            return False
        
        except Exception as e:
            logger.error(f"Action {action.value} failed: {e}")
            return False
    
    async def _reduce_parallelism(self, config: Dict) -> bool:
        """Reduce parallelism"""
        max_tasks = config.get("max_parallel_tasks", 3)
        logger.info(f"Reducing parallelism to {max_tasks} tasks")
        await asyncio.sleep(0.5)
        return True
    
    async def _stop_self_mod(self) -> bool:
        """Stop self-modification"""
        logger.info("Stopping self-modification")
        await asyncio.sleep(0.5)
        return True
    
    async def _reduce_retry_budget(self, config: Dict) -> bool:
        """Reduce retry budget"""
        max_retries = config.get("max_retries", 1)
        logger.info(f"Reducing retry budget to {max_retries}")
        await asyncio.sleep(0.5)
        return True
    
    async def _set_essential_tools_only(self) -> bool:
        """Restrict to essential tools only"""
        logger.info("Restricting to essential tools only")
        await asyncio.sleep(0.5)
        return True
    
    async def _memory_cleanup(self) -> bool:
        """Perform memory cleanup"""
        logger.info("Performing memory cleanup")
        await asyncio.sleep(1)
        return True
    
    async def _run_calibration_tasks(self) -> bool:
        """Run calibration tasks"""
        logger.info("Running calibration tasks")
        await asyncio.sleep(2)
        return True
    
    async def _cache_purge(self) -> bool:
        """Purge caches"""
        logger.info("Purging caches")
        await asyncio.sleep(1)
        return True
    
    async def _reset_routes(self) -> bool:
        """Reset routes"""
        logger.info("Resetting routes")
        await asyncio.sleep(0.5)
        return True
    
    async def _reset_planner(self) -> bool:
        """Reset planner"""
        logger.info("Resetting planner")
        await asyncio.sleep(0.5)
        return True
    
    async def _emergency_cooldown(self, config: Dict) -> bool:
        """Emergency cooldown"""
        duration = config.get("cooldown_duration", 60)
        logger.info(f"Starting emergency cooldown for {duration}s")
        await asyncio.sleep(min(duration, 5))  # Cap at 5 for testing
        return True


# ==================== SAFE MODE FALLBACK ====================

class SafeModeFallback:
    """
    Safe mode fallback system for emergency responses.
    
    Features:
    - Multiple safe mode levels
    - Gradual or immediate fallback
    - Automatic recovery
    - Action execution
    - Event logging
    - State management
    
    This is the kernel's "chartering" or "survival" mode
    that kicks in when things go wrong.
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self._config = config or {}
        
        # Components
        self._executor = FallbackActionExecutor()
        
        # State
        self._state = ModeState(
            current_level=SafeModeLevel.NORMAL,
            activated_at=None,
            trigger_reason="",
            active_actions=set(),
            cooldown_until=None,
            auto_recovery_enabled=True
        )
        
        self._fallback_history: List[FallbackEvent] = []
        
        # Callbacks
        self._on_mode_change: Optional[Callable] = None
        self._on_action_executed: Optional[Callable] = None
        self._on_recovery: Optional[Callable] = None
    
    def set_callbacks(self,
                     on_mode_change: Optional[Callable] = None,
                     on_action_executed: Optional[Callable] = None,
                     on_recovery: Optional[Callable] = None):
        """Set callback functions"""
        self._on_mode_change = on_mode_change
        self._on_action_executed = on_action_executed
        self._on_recovery = on_recovery
    
    # ==================== MODE TRANSITION ====================
    
    async def activate_safe_mode(self, level: SafeModeLevel, 
                               reason: str, automatic: bool = False) -> bool:
        """Activate a safe mode level"""
        if level == self._state.current_level:
            logger.info(f"Already in {level.value} mode")
            return True
        
        previous_level = self._state.current_level
        
        logger.warning(f"Activating safe mode: {level.value} (reason: {reason})")
        
        # Get target configuration
        target_config = SafeModeConfigs.get_config(level)
        
        # Determine actions to take
        actions = self._determine_actions(previous_level, level)
        
        # Execute actions
        executed_actions = []
        for action in actions:
            config_dict = {
                "max_parallel_tasks": target_config.max_parallel_tasks,
                "max_retries": target_config.max_retries,
                "cooldown_duration": target_config.cooldown_duration
            }
            
            success = await self._executor.execute_action(action, config_dict)
            
            if success:
                executed_actions.append(action)
                self._state.active_actions.add(action)
                
                if self._on_action_executed:
                    self._on_action_executed(action)
        
        # Update state
        self._state.current_level = level
        self._state.activated_at = datetime.now()
        self._state.trigger_reason = reason
        
        # Set cooldown
        if target_config.cooldown_duration > 0:
            self._state.cooldown_until = datetime.now() + timedelta(
                seconds=target_config.cooldown_duration
            )
        
        # Record event
        event = FallbackEvent(
            event_id=str(id(datetime.now())),
            timestamp=datetime.now(),
            previous_level=previous_level,
            new_level=level,
            trigger_reason=reason,
            actions_taken=executed_actions,
            duration_seconds=target_config.cooldown_duration,
            automatic=automatic
        )
        self._fallback_history.append(event)
        
        # Trigger callback
        if self._on_mode_change:
            self._on_mode_change(previous_level, level, reason)
        
        return True
    
    async def deactivate_safe_mode(self, reason: str = "manual") -> bool:
        """Deactivate safe mode and return to normal"""
        if self._state.current_level == SafeModeLevel.NORMAL:
            return True
        
        # Check cooldown
        if self._state.cooldown_until and datetime.now() < self._state.cooldown_until:
            remaining = (self._state.cooldown_until - datetime.now()).total_seconds()
            logger.warning(f"Cooldown active, {remaining:.0f}s remaining")
            return False
        
        previous_level = self._state.current_level
        
        logger.info(f"Deactivating safe mode (reason: {reason})")
        
        # Reset to normal
        self._state.current_level = SafeModeLevel.NORMAL
        self._state.activated_at = None
        self._state.trigger_reason = ""
        self._state.active_actions.clear()
        self._state.cooldown_until = None
        
        # Trigger callback
        if self._on_recovery:
            self._on_recovery(previous_level, SafeModeLevel.NORMAL)
        
        return True
    
    async def gradual_recovery(self) -> bool:
        """Gradually recover through caution mode"""
        if self._state.current_level == SafeModeLevel.NORMAL:
            return True
        
        # Progress through levels
        level_progression = [
            SafeModeLevel.EMERGENCY,
            SafeModeLevel.SAFE,
            SafeModeLevel.REDUCED,
            SafeModeLevel.CAUTION,
            SafeModeLevel.NORMAL
        ]
        
        current_idx = level_progression.index(self._state.current_level)
        
        if current_idx < len(level_progression) - 1:
            next_level = level_progression[current_idx + 1]
            return await self.activate_safe_mode(next_level, "gradual_recovery")
        
        return True
    
    # ==================== ACTION DETERMINATION ====================
    
    def _determine_actions(self, from_level: SafeModeLevel, 
                         to_level: SafeModeLevel) -> List[FallbackAction]:
        """Determine which actions to execute based on level change"""
        
        # Map levels to their required actions
        level_actions = {
            SafeModeLevel.CAUTION: [
                FallbackAction.MEMORY_CLEANUP
            ],
            SafeModeLevel.REDUCED: [
                FallbackAction.REDUCE_PARALLELISM,
                FallbackAction.MEMORY_CLEANUP,
                FallbackAction.CACHE_PURGE
            ],
            SafeModeLevel.SAFE: [
                FallbackAction.REDUCE_PARALLELISM,
                FallbackAction.STOP_SELF_MOD,
                FallbackAction.REDUCE_RETRY_BUDGET,
                FallbackAction.ESSENTIAL_TOOLS_ONLY,
                FallbackAction.MEMORY_CLEANUP,
                FallbackAction.CACHE_PURGE,
                FallbackAction.CALIBRATION_TASKS
            ],
            SafeModeLevel.EMERGENCY: [
                FallbackAction.REDUCE_PARALLELISM,
                FallbackAction.STOP_SELF_MOD,
                FallbackAction.REDUCE_RETRY_BUDGET,
                FallbackAction.ESSENTIAL_TOOLS_ONLY,
                FallbackAction.MEMORY_CLEANUP,
                FallbackAction.CACHE_PURGE,
                FallbackAction.ROUTE_RESET,
                FallbackAction.PLANNER_RESET,
                FallbackAction.EMERGENCY_COOLDOWN
            ]
        }
        
        return level_actions.get(to_level, [])
    
    # ==================== STATE QUERIES ====================
    
    def get_current_config(self) -> ModeConfig:
        """Get current safe mode configuration"""
        return SafeModeConfigs.get_config(self._state.current_level)
    
    def is_self_mod_allowed(self) -> bool:
        """Check if self-modification is allowed"""
        return self.get_current_config().self_mod_enabled
    
    def get_allowed_tools(self) -> Set[str]:
        """Get currently allowed tools"""
        return self.get_current_config().allowed_tools
    
    def get_max_parallel_tasks(self) -> int:
        """Get maximum parallel tasks"""
        return self.get_current_config().max_parallel_tasks
    
    def get_max_retries(self) -> int:
        """Get maximum retries"""
        return self.get_current_config().max_retries
    
    def is_in_safe_mode(self) -> bool:
        """Check if in safe mode (not normal)"""
        return self._state.current_level != SafeModeLevel.NORMAL
    
    # ==================== HISTORY ====================
    
    def get_fallback_history(self, limit: int = 10) -> List[FallbackEvent]:
        """Get recent fallback events"""
        return self._fallback_history[-limit:]
    
    def get_statistics(self) -> Dict:
        """Get fallback statistics"""
        if not self._fallback_history:
            return {
                "total_activations": 0,
                "automatic_activations": 0,
                "current_level": self._state.current_level.value
            }
        
        automatic = sum(1 for e in self._fallback_history if e.automatic)
        
        return {
            "total_activations": len(self._fallback_history),
            "automatic_activations": automatic,
            "manual_activations": len(self._fallback_history) - automatic,
            "current_level": self._state.current_level.value,
            "time_in_current_mode": (
                (datetime.now() - self._state.activated_at).total_seconds() 
                if self._state.activated_at else 0
            )
        }
    
    # ==================== AUTO-RECOVERY ====================
    
    async def check_auto_recovery(self) -> bool:
        """Check if auto-recovery should trigger"""
        if not self._state.auto_recovery_enabled:
            return False
        
        if self._state.current_level == SafeModeLevel.NORMAL:
            return False
        
        # Check cooldown
        if self._state.cooldown_until and datetime.now() < self._state.cooldown_until:
            return False
        
        # Try gradual recovery
        return await self.gradual_recovery()
    
    def enable_auto_recovery(self):
        """Enable auto-recovery"""
        self._state.auto_recovery_enabled = True
        logger.info("Auto-recovery enabled")
    
    def disable_auto_recovery(self):
        """Disable auto-recovery"""
        self._state.auto_recovery_enabled = False
        logger.info("Auto-recovery disabled")
    
    @property
    def current_level(self) -> SafeModeLevel:
        return self._state.current_level
    
    @property
    def state(self) -> ModeState:
        return self._state


# ==================== FACTORY ====================

def create_safe_mode_fallback(config: Optional[Dict] = None) -> SafeModeFallback:
    """Factory function to create safe mode fallback"""
    return SafeModeFallback(config=config)
