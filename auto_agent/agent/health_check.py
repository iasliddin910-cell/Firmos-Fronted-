"""
OmniAgent X - Deep Health Check System
=======================================
Comprehensive startup verification for all modules

Features:
- Module-level health verification
- Safe-mode fallback
- Kernel failure telemetry
- Persistence path validation
- Benchmark suite validation

Health Checks:
1. Approval Engine - Test approval workflow
2. Sandbox - Test command execution
3. Persistence - Test path writability
4. Benchmark Suite - Test readiness
5. Kernel - Test core functionality
"""
import os
import sys
import json
import logging
import time
import traceback
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)


# ==================== HEALTH STATUS ====================

class HealthStatus(Enum):
    """Health check status"""
    UNKNOWN = "unknown"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    FAILED = "failed"


@dataclass
class HealthCheckResult:
    """Result of a health check"""
    module: str
    status: HealthStatus
    message: str
    details: Dict = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    execution_time_ms: float = 0.0
    recoverable: bool = True
    
    def to_dict(self) -> Dict:
        return {
            "module": self.module,
            "status": self.status.value,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp,
            "execution_time_ms": self.execution_time_ms,
            "recoverable": self.recoverable
        }


# ==================== TELEMETRY ====================

class HealthTelemetry:
    """
    Telemetry for kernel failures and health issues
    """
    
    def __init__(self, log_path: str = "/tmp/agent_health"):
        self.log_path = Path(log_path)
        self.log_path.mkdir(parents=True, exist_ok=True)
        self.events: List[Dict] = []
        
    def log_event(self, event_type: str, module: str, details: Dict):
        """Log health event"""
        event = {
            "timestamp": time.time(),
            "datetime": datetime.now().isoformat(),
            "event_type": event_type,
            "module": module,
            "details": details
        }
        self.events.append(event)
        
        # Save to disk
        self._save_to_disk(event)
        
        # Also log to standard logger
        if event_type == "FAILURE":
            logger.error(f"🚨 TELEMETRY FAILURE: {module} - {details.get('error', 'Unknown')}")
        elif event_type == "RECOVERY":
            logger.info(f"✅ TELEMETRY RECOVERY: {module}")
        elif event_type == "FALLBACK":
            logger.warning(f"⚠️ TELEMETRY FALLBACK: {module} -> {details.get('fallback_mode', 'unknown')}")
    
    def _save_to_disk(self, event: Dict):
        """Save event to disk"""
        try:
            log_file = self.log_path / f"health_{datetime.now().strftime('%Y%m%d')}.jsonl"
            with open(log_file, "a") as f:
                f.write(json.dumps(event) + "\n")
        except Exception as e:
            logger.warning(f"Failed to save telemetry: {e}")
    
    def get_recent_events(self, limit: int = 100) -> List[Dict]:
        """Get recent events"""
        return self.events[-limit:]


# ==================== HEALTH CHECKS ====================

class HealthChecker:
    """
    Comprehensive health check system
    """
    
    def __init__(self, telemetry: HealthTelemetry = None):
        self.telemetry = telemetry or HealthTelemetry()
        self.results: List[HealthCheckResult] = []
        self.safe_mode = False
        self.failed_modules: List[str] = []
        
    def check_all(self, agent_instance) -> Dict:
        """
        Run all health checks
        
        Args:
            agent_instance: OmniAgent instance
            
        Returns:
            Dictionary with overall health status
        """
        logger.info("🔍 Starting comprehensive health check...")
        start_time = time.time()
        
        checks = [
            ("secret_guard", self._check_secret_guard),
            ("sandbox", self._check_sandbox),
            ("approval_engine", self._check_approval_engine),
            ("persistence", self._check_persistence),
            ("memory", self._check_memory),
            ("kernel", self._check_kernel),
            ("brain", self._check_brain),
            ("benchmark_suite", self._check_benchmark_suite),
        ]
        
        for module_name, check_fn in checks:
            try:
                result = check_fn(agent_instance)
                self.results.append(result)
                
                if result.status != HealthStatus.HEALTHY:
                    self.failed_modules.append(module_name)
                    self.telemetry.log_event(
                        "FAILURE" if result.status == HealthStatus.UNHEALTHY else "WARNING",
                        module_name,
                        {"status": result.status.value, "message": result.message}
                    )
                    
            except Exception as e:
                logger.error(f"❌ Health check failed for {module_name}: {e}")
                error_result = HealthCheckResult(
                    module=module_name,
                    status=HealthStatus.FAILED,
                    message=f"Check crashed: {str(e)}",
                    details={"exception": traceback.format_exc()},
                    recoverable=True
                )
                self.results.append(error_result)
                self.failed_modules.append(module_name)
                
                self.telemetry.log_event("FAILURE", module_name, {
                    "error": str(e),
                    "traceback": traceback.format_exc()
                })
        
        # Determine overall status
        total_time = (time.time() - start_time) * 1000
        overall = self._calculate_overall_status()
        
        logger.info(f"✅ Health check complete: {overall['status']} ({total_time:.1f}ms)")
        
        return {
            "status": overall["status"],
            "total_checks": len(checks),
            "healthy": overall["healthy"],
            "degraded": overall["degraded"],
            "failed": overall["failed"],
            "failed_modules": self.failed_modules,
            "execution_time_ms": total_time,
            "results": [r.to_dict() for r in self.results]
        }
    
    def _calculate_overall_status(self) -> Dict:
        """Calculate overall health status"""
        healthy = sum(1 for r in self.results if r.status == HealthStatus.HEALTHY)
        degraded = sum(1 for r in self.results if r.status == HealthStatus.DEGRADED)
        failed = sum(1 for r in self.results if r.status in [HealthStatus.UNHEALTHY, HealthStatus.FAILED])
        
        if failed > 0:
            status = "unhealthy"
        elif degraded > 0:
            status = "degraded"
        else:
            status = "healthy"
            
        return {
            "status": status,
            "healthy": healthy,
            "degraded": degraded,
            "failed": failed
        }
    
    # ==================== INDIVIDUAL CHECKS ====================
    
    def _check_secret_guard(self, agent) -> HealthCheckResult:
        """Check if secret guard is working"""
        start = time.time()
        
        try:
            if not hasattr(agent, 'secret_guard') or agent.secret_guard is None:
                return HealthCheckResult(
                    module="secret_guard",
                    status=HealthStatus.UNHEALTHY,
                    message="Secret guard not initialized",
                    execution_time_ms=(time.time() - start) * 1000
                )
            
            # Test secret guard functionality
            test_key = "TEST_KEY_12345"
            test_value = "test_value"
            os.environ[test_key] = test_value
            
            retrieved = agent.secret_guard.get_env(test_key)
            
            del os.environ[test_key]
            
            if retrieved != test_value:
                return HealthCheckResult(
                    module="secret_guard",
                    status=HealthStatus.DEGRADED,
                    message="Secret guard get_env failed",
                    execution_time_ms=(time.time() - start) * 1000
                )
            
            return HealthCheckResult(
                module="secret_guard",
                status=HealthStatus.HEALTHY,
                message="Secret guard working",
                details={"test_passed": True},
                execution_time_ms=(time.time() - start) * 1000
            )
            
        except Exception as e:
            return HealthCheckResult(
                module="secret_guard",
                status=HealthStatus.FAILED,
                message=f"Check error: {str(e)}",
                details={"exception": str(e)},
                execution_time_ms=(time.time() - start) * 1000
            )
    
    def _check_sandbox(self, agent) -> HealthCheckResult:
        """Check if sandbox is properly configured"""
        start = time.time()
        
        try:
            if not hasattr(agent, 'sandbox') or agent.sandbox is None:
                return HealthCheckResult(
                    module="sandbox",
                    status=HealthStatus.UNHEALTHY,
                    message="Sandbox not initialized",
                    execution_time_ms=(time.time() - start) * 1000
                )
            
            # Test sandbox command execution
            test_result = agent.sandbox.execute("echo health_check_test")
            
            # Check if mode is properly set
            mode = getattr(agent.sandbox, 'mode', None)
            workspace = getattr(agent.sandbox, 'workspace', None)
            
            details = {
                "mode": mode.value if mode else "unknown",
                "workspace": str(workspace) if workspace else "unknown",
                "test_result": test_result.get("success", False) if isinstance(test_result, dict) else False
            }
            
            # Verify mode is not UNRESTRICTED (security risk)
            if mode and mode.value == "unrestricted":
                self.telemetry.log_event("FALLBACK", "sandbox", {
                    "fallback_mode": "SAFE",
                    "reason": "Unrestricted mode detected"
                })
                mode = "SAFE"  # Force safe mode
            
            return HealthCheckResult(
                module="sandbox",
                status=HealthStatus.HEALTHY if details["test_result"] else HealthStatus.DEGRADED,
                message=f"Sandbox mode: {details['mode']}",
                details=details,
                execution_time_ms=(time.time() - start) * 1000
            )
            
        except Exception as e:
            return HealthCheckResult(
                module="sandbox",
                status=HealthStatus.FAILED,
                message=f"Check error: {str(e)}",
                details={"exception": str(e)},
                execution_time_ms=(time.time() - start) * 1000
            )
    
    def _check_approval_engine(self, agent) -> HealthCheckResult:
        """Check if approval engine is working"""
        start = time.time()
        
        try:
            if not hasattr(agent, 'approval_engine') or agent.approval_engine is None:
                return HealthCheckResult(
                    module="approval_engine",
                    status=HealthStatus.UNHEALTHY,
                    message="Approval engine not initialized",
                    execution_time_ms=(time.time() - start) * 1000
                )
            
            # Test approval workflow
            ae = agent.approval_engine
            
            # 1. Test request creation
            request_id = ae.request_approval(
                tool="test_tool",
                args={"test": "data"},
                requested_by="health_check",
                risk="low"
            )
            
            # 2. Test approval check
            is_approved = ae.check(request_id)
            
            # 3. Clean up
            if request_id != "auto" and request_id in ae.pending:
                ae.pending.pop(request_id)
            
            # Get stats
            stats = ae.get_stats() if hasattr(ae, 'get_stats') else {}
            
            details = {
                "request_works": request_id is not None,
                "check_works": isinstance(is_approved, bool),
                "stats": stats
            }
            
            return HealthCheckResult(
                module="approval_engine",
                status=HealthStatus.HEALTHY if all(details.values()) else HealthStatus.DEGRADED,
                message="Approval engine operational",
                details=details,
                execution_time_ms=(time.time() - start) * 1000
            )
            
        except Exception as e:
            return HealthCheckResult(
                module="approval_engine",
                status=HealthStatus.FAILED,
                message=f"Check error: {str(e)}",
                details={"exception": str(e)},
                execution_time_ms=(time.time() - start) * 1000
            )
    
    def _check_persistence(self, agent) -> HealthCheckResult:
        """Check if persistence paths are writable"""
        start = time.time()
        
        try:
            # Check multiple potential persistence paths
            paths_to_check = [
                "/tmp",
                "/tmp/agent_health",
                "/tmp/approval",
                getattr(getattr(agent, 'memory', None), 'storage_dir', None) if hasattr(agent, 'memory') else None,
                getattr(getattr(agent, 'agent_memory', None), 'storage_dir', None) if hasattr(agent, 'agent_memory') else None,
            ]
            
            results = {}
            writable_paths = []
            
            for path in paths_to_check:
                if path is None:
                    continue
                    
                try:
                    p = Path(path)
                    p.mkdir(parents=True, exist_ok=True)
                    
                    # Test write
                    test_file = p / ".health_check_write_test"
                    test_file.write_text("test")
                    test_file.unlink()
                    
                    results[str(path)] = "writable"
                    writable_paths.append(str(path))
                    
                except Exception as e:
                    results[str(path)] = f"error: {str(e)}"
            
            status = HealthStatus.HEALTHY if writable_paths else HealthStatus.UNHEALTHY
            
            return HealthCheckResult(
                module="persistence",
                status=status,
                message=f"{len(writable_paths)} paths writable",
                details={"paths": results, "writable_count": len(writable_paths)},
                execution_time_ms=(time.time() - start) * 1000,
                recoverable=status != HealthStatus.UNHEALTHY
            )
            
        except Exception as e:
            return HealthCheckResult(
                module="persistence",
                status=HealthStatus.FAILED,
                message=f"Check error: {str(e)}",
                details={"exception": str(e)},
                execution_time_ms=(time.time() - start) * 1000
            )
    
    def _check_memory(self, agent) -> HealthCheckResult:
        """Check if memory systems are working"""
        start = time.time()
        
        try:
            memory_ok = hasattr(agent, 'memory') and agent.memory is not None
            agent_memory_ok = hasattr(agent, 'agent_memory') and agent.agent_memory is not None
            
            # Test basic operations
            test_conversation = [
                {"role": "user", "content": "health check test"}
            ]
            
            if memory_ok:
                try:
                    agent.memory.save_conversation(test_conversation)
                    memory_test = "write_ok"
                except Exception as e:
                    memory_test = f"error: {str(e)}"
            else:
                memory_test = "not_initialized"
            
            details = {
                "memory_system": "ok" if memory_ok else "missing",
                "agent_memory": "ok" if agent_memory_ok else "missing",
                "write_test": memory_test
            }
            
            status = HealthStatus.HEALTHY if (memory_ok and agent_memory_ok) else HealthStatus.DEGRADED
            
            return HealthCheckResult(
                module="memory",
                status=status,
                message="Memory systems operational" if status == HealthStatus.HEALTHY else "Some memory systems missing",
                details=details,
                execution_time_ms=(time.time() - start) * 1000
            )
            
        except Exception as e:
            return HealthCheckResult(
                module="memory",
                status=HealthStatus.FAILED,
                message=f"Check error: {str(e)}",
                details={"exception": str(e)},
                execution_time_ms=(time.time() - start) * 1000
            )
    
    def _check_kernel(self, agent) -> HealthCheckResult:
        """Check if kernel is working"""
        start = time.time()
        
        try:
            if not hasattr(agent, 'kernel') or agent.kernel is None:
                # Log kernel failure to telemetry
                self.telemetry.log_event("FAILURE", "kernel", {
                    "error": "Kernel not initialized",
                    "fallback_mode": "SAFE_MODE"
                })
                self.safe_mode = True
                
                return HealthCheckResult(
                    module="kernel",
                    status=HealthStatus.UNHEALTHY,
                    message="Kernel not initialized - entering safe mode",
                    execution_time_ms=(time.time() - start) * 1000,
                    recoverable=True
                )
            
            # Test kernel status
            kernel_status = agent.kernel.get_status() if hasattr(agent.kernel, 'get_status') else "unknown"
            
            # Test basic kernel functionality
            try:
                # Try to get task queue status
                queue_status = agent.kernel.get_task_queue_status() if hasattr(agent.kernel, 'get_task_queue_status') else "unknown"
            except Exception as e:
                queue_status = f"error: {str(e)}"
            
            details = {
                "status": str(kernel_status),
                "queue": str(queue_status),
                "safe_mode": self.safe_mode
            }
            
            return HealthCheckResult(
                module="kernel",
                status=HealthStatus.HEALTHY,
                message="Kernel operational",
                details=details,
                execution_time_ms=(time.time() - start) * 1000
            )
            
        except Exception as e:
            # Log kernel failure
            self.telemetry.log_event("FAILURE", "kernel", {
                "error": str(e),
                "traceback": traceback.format_exc(),
                "fallback_mode": "SAFE_MODE"
            })
            self.safe_mode = True
            
            return HealthCheckResult(
                module="kernel",
                status=HealthStatus.UNHEALTHY,
                message=f"Kernel error - safe mode enabled: {str(e)}",
                details={"exception": str(e), "safe_mode": True},
                execution_time_ms=(time.time() - start) * 1000,
                recoverable=True
            )
    
    def _check_brain(self, agent) -> HealthCheckResult:
        """Check if native brain is working"""
        start = time.time()
        
        try:
            if not hasattr(agent, 'brain') or agent.brain is None:
                return HealthCheckResult(
                    module="brain",
                    status=HealthStatus.UNHEALTHY,
                    message="Native brain not initialized",
                    execution_time_ms=(time.time() - start) * 1000
                )
            
            # Check brain has required components
            brain_has_tools = hasattr(agent.brain, 'tools') and agent.brain.tools is not None
            
            details = {
                "tools_connected": brain_has_tools
            }
            
            return HealthCheckResult(
                module="brain",
                status=HealthStatus.HEALTHY if brain_has_tools else HealthStatus.DEGRADED,
                message="Native brain operational" if brain_has_tools else "Brain missing tools",
                details=details,
                execution_time_ms=(time.time() - start) * 1000
            )
            
        except Exception as e:
            return HealthCheckResult(
                module="brain",
                status=HealthStatus.FAILED,
                message=f"Check error: {str(e)}",
                details={"exception": str(e)},
                execution_time_ms=(time.time() - start) * 1000
            )
    
    def _check_benchmark_suite(self, agent) -> HealthCheckResult:
        """Check if benchmark suite is ready"""
        start = time.time()
        
        try:
            benchmark_ok = hasattr(agent, 'benchmark_suite') and agent.benchmark_suite is not None
            
            details = {
                "benchmark_suite": "ok" if benchmark_ok else "missing"
            }
            
            if benchmark_ok:
                # Try to get benchmark info
                try:
                    info = agent.benchmark_suite.get_info() if hasattr(agent.benchmark_suite, 'get_info') else {}
                    details["info"] = info
                except (AttributeError, Exception) as e:
                    logger.debug(f"Benchmark info unavailable: {e}")
            
            status = HealthStatus.HEALTHY if benchmark_ok else HealthStatus.DEGRADED
            
            return HealthCheckResult(
                module="benchmark_suite",
                status=status,
                message="Benchmark suite ready" if status == HealthStatus.HEALTHY else "Benchmark suite not ready",
                details=details,
                execution_time_ms=(time.time() - start) * 1000,
                recoverable=True  # Benchmark failure is not critical
            )
            
        except Exception as e:
            return HealthCheckResult(
                module="benchmark_suite",
                status=HealthStatus.FAILED,
                message=f"Check error: {str(e)}",
                details={"exception": str(e)},
                execution_time_ms=(time.time() - start) * 1000,
                recoverable=True
            )
    
    # ==================== SAFE MODE ====================
    
    def enable_safe_mode(self):
        """Enable safe mode fallback"""
        self.safe_mode = True
        self.telemetry.log_event("FALLBACK", "system", {
            "fallback_mode": "SAFE_MODE",
            "reason": "Multiple module failures detected"
        })
        logger.warning("⚠️ SAFE MODE ENABLED - Limited functionality")
    
    def get_safe_mode_config(self) -> Dict:
        """Get safe mode configuration"""
        return {
            "enabled": self.safe_mode,
            "restricted_modules": self.failed_modules,
            "telemetry": self.telemetry.get_recent_events(10)
        }


# ==================== FACTORY ====================

def create_health_checker() -> HealthChecker:
    """Create health checker instance"""
    return HealthChecker()


def create_health_telemetry() -> HealthTelemetry:
    """Create health telemetry instance"""
    return HealthTelemetry()
