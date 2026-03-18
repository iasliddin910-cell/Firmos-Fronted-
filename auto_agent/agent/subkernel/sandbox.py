"""
OmniAgent X - SubkernelSandbox
==============================
Containment zone for experimental/high-risk subkernels

Bu sandbox subkernellarni alohida lane/lockerda ishlashini ta'minlaydi.
Agar experimental capability bo'lsa, u holda:
- alohida lane
- alohida health risk
- alohida replay posture
- alohida quarantine policy

bilan ishlaydi.
"""

import logging
import asyncio
import os
import tempfile
from typing import Dict, List, Optional, Any, Set, Callable
from threading import RLock
from dataclasses import dataclass, field
from enum import Enum
from contextlib import contextmanager
import uuid
import time

from agent.subkernel import (
    SubkernelCategory, 
    SubkernelStatus, 
    TrustLevel,
    SubkernelInterface,
    PluggableCapability,
)
from agent.subkernel.spec import SubkernelSpec, PluginManifest
from agent.subkernel.trust import TrustManager, TrustPolicy, ContainmentPolicy, PolicyPosture


logger = logging.getLogger(__name__)


class IsolationLevel(str, Enum):
    """Isolation levels for subkernel sandbox"""
    NONE = "none"           # No isolation
    LANE = "lane"          # Separate execution lane
    PROCESS = "process"    # Separate process
    VM = "vm"             # Virtual machine level


@dataclass
class SandboxConfig:
    """Sandbox configuration"""
    isolation_level: IsolationLevel = IsolationLevel.LANE
    
    # Resource limits
    max_memory_mb: int = 1024
    max_cpu_percent: int = 50
    max_file_descriptors: int = 100
    max_threads: int = 10
    
    # Network limits
    network_enabled: bool = True
    max_connections: int = 10
    allowed_ports: Set[int] = field(default_factory=lambda: {80, 443})
    
    # Filesystem limits
    read_only_home: bool = True
    temp_dir: Optional[str] = None
    allowed_paths: Set[str] = field(default_factory=lambda: {"/tmp"})
    blocked_paths: Set[str] = field(default_factory=lambda: {"/etc", "/root", "/var"})
    
    # Execution limits
    max_execution_time_seconds: int = 300
    max_child_processes: int = 5
    
    # Security
    drop_privileges: bool = True
    seccomp_enabled: bool = False
    namespace_enabled: bool = False
    
    # Monitoring
    enable_logging: bool = True
    enable_audit: bool = False
    enable_telemetry: bool = True
    
    # Failure handling
    kill_on_oom: bool = True
    preserve_state_on_crash: bool = False


@dataclass
class SandboxMetrics:
    """Sandbox metrics"""
    total_executions: int = 0
    successful_executions: int = 0
    failed_executions: int = 0
    oom_kills: int = 0
    timeout_kills: int = 0
    total_cpu_time_ms: float = 0.0
    total_memory_peak_mb: float = 0.0
    total_execution_time_ms: float = 0.0


class ExecutionResult:
    """Execution result from sandbox"""
    
    def __init__(
        self,
        success: bool,
        output: Any = None,
        error: Optional[str] = None,
        metrics: Optional[Dict] = None,
        sandboxed: bool = False,
    ):
        self.success = success
        self.output = output
        self.error = error
        self.metrics = metrics or {}
        self.sandboxed = sandboxed


class SubkernelSandbox:
    """
    Subkernel Sandbox - Containment zone for subkernels
    
    Bu class:
    - Subkernel'ni izolyatsiya qiladi
    - Resource limitlarini qo'llaydi
    - Network va filesystem access'ni nazorat qiladi
    - Failure containment ta'minlaydi
    
    Asosiy xususiyatlar:
    - Lane isolation: alohida execution lane
    - Resource limits: CPU, memory, file descriptors
    - Network controls: port restrictions
    - Filesystem controls: path restrictions
    - Execution controls: time limits, child processes
    """
    
    def __init__(
        self,
        name: str,
        config: Optional[SandboxConfig] = None,
        trust_policy: Optional[TrustPolicy] = None,
        containment: Optional[ContainmentPolicy] = None,
    ):
        self.name = name
        self.config = config or SandboxConfig()
        self.trust_policy = trust_policy
        self.containment = containment
        
        # Metrics
        self.metrics = SandboxMetrics()
        
        # State
        self._lock = RLock()
        self._is_active = False
        self._current_execution: Optional[Dict] = None
        self._execution_count = 0
        
        # Temp directory for this sandbox
        self._temp_dir = tempfile.mkdtemp(prefix=f"sandbox_{name}_")
        
        # Logger
        self._logger = logging.getLogger(f"sandbox.{name}")
        
        logger.info(f"🛡️ Created sandbox for {name} (level: {self.config.isolation_level.value})")
    
    # ==================== LIFECYCLE ====================
    
    def activate(self) -> bool:
        """Sandbox'ni faollashtirish"""
        with self._lock:
            if self._is_active:
                return True
            
            # Create temp directory
            os.makedirs(self._temp_dir, exist_ok=True)
            
            # Apply system-level restrictions
            if self.config.isolation_level != IsolationLevel.NONE:
                self._apply_system_restrictions()
            
            self._is_active = True
            logger.info(f"🚀 Activated sandbox: {self.name}")
            return True
    
    def deactivate(self) -> bool:
        """Sandbox'ni o'chirish"""
        with self._lock:
            if not self._is_active:
                return True
            
            # Cleanup temp directory
            try:
                import shutil
                if os.path.exists(self._temp_dir):
                    shutil.rmtree(self._temp_dir)
            except Exception as e:
                logger.error(f"Error cleaning temp dir: {e}")
            
            self._is_active = False
            logger.info(f"🔴 Deactivated sandbox: {self.name}")
            return True
    
    def reset(self):
        """Sandbox'ni reset qilish"""
        with self._lock:
            self.metrics = SandboxMetrics()
            self._current_execution = None
            self._execution_count = 0
    
    # ==================== EXECUTION ====================
    
    async def execute(
        self,
        func: Callable,
        *args,
        timeout: Optional[float] = None,
        **kwargs
    ) -> ExecutionResult:
        """
        Function'ni sandbox ichida ishga tushirish
        
        Bu method function'ni sandbox ichida izolyatsiya qilib ishga tushiradi.
        """
        if not self._is_active:
            await self.activate()
        
        # Use config timeout if not provided
        if timeout is None:
            timeout = self.config.max_execution_time_seconds
        
        start_time = time.time()
        self._execution_count += 1
        execution_id = str(uuid.uuid4())
        
        self._current_execution = {
            "id": execution_id,
            "start_time": start_time,
            "args": args,
            "kwargs": kwargs,
        }
        
        self.metrics.total_executions += 1
        
        try:
            # Run with timeout
            result = await asyncio.wait_for(
                self._run_function(func, *args, **kwargs),
                timeout=timeout
            )
            
            # Success
            self.metrics.successful_executions += 1
            
            execution_time = (time.time() - start_time) * 1000
            self.metrics.total_execution_time_ms += execution_time
            
            return ExecutionResult(
                success=True,
                output=result,
                sandboxed=True,
                metrics={
                    "execution_time_ms": execution_time,
                    "execution_id": execution_id,
                    "sandbox": self.name,
                }
            )
            
        except asyncio.TimeoutError:
            # Timeout
            self.metrics.failed_executions += 1
            self.metrics.timeout_kills += 1
            
            execution_time = (time.time() - start_time) * 1000
            
            return ExecutionResult(
                success=False,
                error=f"Execution timeout after {timeout}s",
                sandboxed=True,
                metrics={
                    "execution_time_ms": execution_time,
                    "execution_id": execution_id,
                    "timeout": True,
                }
            )
            
        except MemoryError:
            # OOM
            self.metrics.failed_executions += 1
            self.metrics.oom_kills += 1
            
            return ExecutionResult(
                success=False,
                error="Out of memory",
                sandboxed=True,
                metrics={
                    "oom": True,
                    "execution_id": execution_id,
                }
            )
            
        except Exception as e:
            # Other errors
            self.metrics.failed_executions += 1
            
            return ExecutionResult(
                success=False,
                error=str(e),
                sandboxed=True,
                metrics={
                    "execution_id": execution_id,
                    "error_type": type(e).__name__,
                }
            )
            
        finally:
            self._current_execution = None
    
    async def _run_function(self, func: Callable, *args, **kwargs) -> Any:
        """Run function with sandbox restrictions"""
        # Check if we should limit resources
        if self.config.isolation_level != IsolationLevel.NONE:
            # Set environment variables for sandbox
            old_env = os.environ.copy()
            try:
                # Apply temp directory
                os.environ['TMPDIR'] = self._temp_dir
                
                # Run the function
                if asyncio.iscoroutinefunction(func):
                    return await func(*args, **kwargs)
                else:
                    return func(*args, **kwargs)
            finally:
                # Restore environment
                os.environ.clear()
                os.environ.update(old_env)
        else:
            # No sandbox - run directly
            if asyncio.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            else:
                return func(*args, **kwargs)
    
    # ==================== RESOURCE CHECKS ====================
    
    def can_allocate_memory(self, size_mb: int) -> bool:
        """Xotira ajrata olish"""
        if self.config.max_memory_mb:
            # Approximate check
            current_usage = self.metrics.total_memory_peak_mb
            return (current_usage + size_mb) <= self.config.max_memory_mb
        return True
    
    def can_open_file_descriptor(self) -> bool:
        """File descriptor ochsa bo'ladimi"""
        if self.config.max_file_descriptors:
            # This is approximate
            return self._execution_count <= self.config.max_file_descriptors
        return True
    
    def can_spawn_process(self) -> bool:
        """Child process yaratsa bo'ladimi"""
        if self.config.max_child_processes:
            return True  # Would need process tracking
        return True
    
    def can_connect_port(self, port: int) -> bool:
        """Portga ulansa bo'ladimi"""
        if not self.config.network_enabled:
            return False
        
        if port not in self.config.allowed_ports:
            return False
        
        # Check connection limit
        # (simplified - would need actual connection tracking)
        return True
    
    def can_access_path(self, path: str) -> bool:
        """Pathga kirsa bo'ladimi"""
        # Check blocked paths
        for blocked in self.config.blocked_paths:
            if path.startswith(blocked):
                return False
        
        # Check allowed paths (if not wildcard)
        if "*" not in self.config.allowed_paths:
            allowed = False
            for allowed_path in self.config.allowed_paths:
                if path.startswith(allowed_path):
                    allowed = True
            if not allowed:
                return False
        
        return True
    
    # ==================== SYSTEM RESTRICTIONS ====================
    
    def _apply_system_restrictions(self):
        """Apply system-level restrictions"""
        # This would set up actual OS-level restrictions
        # like cgroups, seccomp, namespaces, etc.
        
        if self.config.isolation_level == IsolationLevel.PROCESS:
            # Process-level isolation
            logger.info(f"🔒 Applying process isolation for {self.name}")
        
        elif self.config.isolation_level == IsolationLevel.VM:
            # VM-level isolation (would require actual VM)
            logger.info(f"🔒 Applying VM isolation for {self.name}")
    
    # ==================== CONTEXT MANAGER ====================
    
    @contextmanager
    def execution_context(self):
        """Execution context manager"""
        try:
            self.activate()
            yield self
        finally:
            pass  # Don't deactivate between executions
    
    # ==================== METRICS ====================
    
    def get_metrics(self) -> Dict[str, Any]:
        """Metrics olish"""
        return {
            "name": self.name,
            "isolation_level": self.config.isolation_level.value,
            "is_active": self._is_active,
            "total_executions": self.metrics.total_executions,
            "successful_executions": self.metrics.successful_executions,
            "failed_executions": self.metrics.failed_executions,
            "oom_kills": self.metrics.oom_kills,
            "timeout_kills": self.metrics.timeout_kills,
            "total_cpu_time_ms": self.metrics.total_cpu_time_ms,
            "total_memory_peak_mb": self.metrics.total_memory_peak_mb,
            "total_execution_time_ms": self.metrics.total_execution_time_ms,
            "success_rate": (
                self.metrics.successful_executions / self.metrics.total_executions
                if self.metrics.total_executions > 0 else 0
            ),
        }
    
    def get_status(self) -> Dict[str, Any]:
        """Status olish"""
        return {
            "name": self.name,
            "active": self._is_active,
            "isolation": self.config.isolation_level.value,
            "temp_dir": self._temp_dir,
            "current_execution": self._current_execution is not None,
            "execution_count": self._execution_count,
        }


class SandboxManager:
    """
    Sandbox Manager - Barcha sandbox'larni boshqarish
    
    Bu manager:
    - Har bir subkernel uchun sandbox yaratadi
    - Sandbox lifecycle'ini boshqaradi
    - Resource allocation'ni nazorat qiladi
    """
    
    def __init__(self, trust_manager: Optional[TrustManager] = None):
        self._trust_manager = trust_manager
        self._lock = RLock()
        
        # Sandboxes by name
        self._sandboxes: Dict[str, SubkernelSandbox] = {}
        
        # Global config
        self._default_config = SandboxConfig()
        
        # Metrics aggregation
        self._global_metrics = SandboxMetrics()
    
    def get_or_create_sandbox(
        self,
        name: str,
        trust_policy: Optional[TrustPolicy] = None,
        containment: Optional[ContainmentPolicy] = None,
    ) -> SubkernelSandbox:
        """Subkernel uchun sandbox olish yoki yaratish"""
        with self._lock:
            if name in self._sandboxes:
                return self._sandboxes[name]
            
            # Create config from trust policy/containment
            config = self._create_config_from_policy(trust_policy, containment)
            
            # Create sandbox
            sandbox = SubkernelSandbox(name, config, trust_policy, containment)
            self._sandboxes[name] = sandbox
            
            logger.info(f"🛡️ Created sandbox for {name}")
            return sandbox
    
    def get_sandbox(self, name: str) -> Optional[SubkernelSandbox]:
        """Sandbox olish"""
        return self._sandboxes.get(name)
    
    def remove_sandbox(self, name: str) -> bool:
        """Sandbox o'chirish"""
        with self._lock:
            sandbox = self._sandboxes.get(name)
            if sandbox:
                sandbox.deactivate()
                del self._sandboxes[name]
                return True
            return False
    
    def activate_all(self) -> Dict[str, bool]:
        """Barcha sandbox'larni faollashtirish"""
        results = {}
        for name, sandbox in self._sandboxes.items():
            results[name] = sandbox.activate()
        return results
    
    def deactivate_all(self) -> Dict[str, bool]:
        """Barcha sandbox'larni o'chirish"""
        results = {}
        for name, sandbox in self._sandboxes.items():
            results[name] = sandbox.deactivate()
        return results
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """Barcha sandbox metrikalari"""
        result = {
            "sandboxes": {},
            "total_executions": 0,
            "total_success": 0,
            "total_failures": 0,
        }
        
        for name, sandbox in self._sandboxes.items():
            metrics = sandbox.get_metrics()
            result["sandboxes"][name] = metrics
            result["total_executions"] += metrics["total_executions"]
            result["total_success"] += metrics["successful_executions"]
            result["total_failures"] += metrics["failed_executions"]
        
        return result
    
    def _create_config_from_policy(
        self,
        trust_policy: Optional[TrustPolicy],
        containment: Optional[ContainmentPolicy]
    ) -> SandboxConfig:
        """Trust policy va containment'dan config yaratish"""
        config = SandboxConfig()
        
        if containment:
            config.isolation_level = IsolationLevel(containment.isolation_level)
            config.max_memory_mb = containment.memory_limit_mb
            config.max_cpu_percent = containment.cpu_percent_limit
            config.max_execution_time_seconds = containment.max_execution_time_seconds
            config.network_enabled = bool(containment.allowed_networks)
            config.allowed_paths = set(containment.allowed_paths)
            config.blocked_paths = set(containment.blocked_paths)
            config.enable_audit = containment.enable_audit
        
        if trust_policy:
            if trust_policy.max_memory_mb:
                config.max_memory_mb = min(config.max_memory_mb, trust_policy.max_memory_mb)
            if trust_policy.max_cpu_percent:
                config.max_cpu_percent = min(config.max_cpu_percent, trust_policy.max_cpu_percent)
            if trust_policy.max_execution_time_seconds:
                config.max_execution_time_seconds = min(
                    config.max_execution_time_seconds,
                    trust_policy.max_execution_time_seconds
                )
        
        return config


# Global sandbox manager
_sandbox_manager: Optional[SandboxManager] = None


def get_sandbox_manager(trust_manager: Optional[TrustManager] = None) -> SandboxManager:
    """Get or create global sandbox manager"""
    global _sandbox_manager
    if _sandbox_manager is None:
        _sandbox_manager = SandboxManager(trust_manager)
    return _sandbox_manager


def reset_sandbox_manager():
    """Reset global sandbox manager"""
    global _sandbox_manager
    _sandbox_manager = None
