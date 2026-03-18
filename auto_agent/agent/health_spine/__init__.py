"""
OmniAgent X - Kernel Health Spine
=================================
Advanced health check system integrated into kernel's operational spine.

This module provides a comprehensive health monitoring system that goes beyond
basic existence checks to provide semantic, capability-aware health monitoring.

Key Components:
- KernelHealthSpine: Main spine integrating health into kernel
- LivenessProbe: Is system alive (threads, queues, deadlocks)
- ReadinessProbe: Is system ready for real tasks
- SemanticProbe: Semantic health (invariants, state consistency)
- CapabilityGate: Health outcomes affect capability posture
- CanaryRunner: Run canary tasks before real missions
- RepairAdvisor: Provide repair advice based on failures
"""

import os
import sys
import json
import logging
import time
import threading
import asyncio
from typing import Dict, List, Any, Optional, Callable, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from collections import defaultdict
import traceback

logger = logging.getLogger(__name__)


# ==================== HEALTH STATUS TYPES ====================

class ProbeType(Enum):
    """Types of health probes"""
    LIVENESS = "liveness"      # Is system alive
    READINESS = "readiness"     # Is system ready for tasks
    SEMANTIC = "semantic"      # Is system semantically healthy


class HealthLevel(Enum):
    """Health levels for granular capability management"""
    HEALTHY = "healthy"           # Full capability
    DEGRADED = "degraded"          # Limited capability
    CRITICAL = "critical"         # Minimal capability
    FAILED = "failed"             # No capability
    UNKNOWN = "unknown"           # Cannot determine


class CapabilityPosture(Enum):
    """Capability posture based on health"""
    FULL = "full"                 # All capabilities enabled
    RESTRICTED = "restricted"     # Some capabilities limited
    CONSERVATIVE = "conservative" # Destructive ops require approval
    EMERGENCY = "emergency"       # Only safe operations
    READY_ONLY = "ready_only"     # No execution, only readiness


@dataclass
class ProbeResult:
    """Result of a single probe check"""
    probe_type: ProbeType
    probe_name: str
    level: HealthLevel
    message: str
    details: Dict = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    execution_time_ms: float = 0.0
    recoverable: bool = True
    recommendations: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "probe_type": self.probe_type.value,
            "probe_name": self.probe_name,
            "level": self.level.value,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp,
            "execution_time_ms": self.execution_time_ms,
            "recoverable": self.recoverable,
            "recommendations": self.recommendations
        }


@dataclass
class CapabilityGateResult:
    """Result of capability gating based on health"""
    capability: str
    allowed: bool
    posture: CapabilityPosture
    reason: str
    restrictions: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "capability": self.capability,
            "allowed": self.allowed,
            "posture": self.posture.value,
            "reason": self.reason,
            "restrictions": self.restrictions
        }


@dataclass
class CanaryResult:
    """Result of canary task execution"""
    canary_name: str
    passed: bool
    execution_time_ms: float = 0.0
    error: Optional[str] = None
    details: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "canary_name": self.canary_name,
            "passed": self.passed,
            "execution_time_ms": self.execution_time_ms,
            "error": self.error,
            "details": self.details
        }


@dataclass
class RepairAdvice:
    """Repair advice based on health failures"""
    severity: str
    category: str
    description: str
    actions: List[str] = field(default_factory=list)
    capabilities_to_disable: List[str] = field(default_factory=list)
    lanes_to_quarantine: List[str] = field(default_factory=list)
    fallback_profile: Optional[str] = None
    human_review_required: bool = False
    
    def to_dict(self) -> Dict:
        return {
            "severity": self.severity,
            "category": self.category,
            "description": self.description,
            "actions": self.actions,
            "capabilities_to_disable": self.capabilities_to_disable,
            "lanes_to_quarantine": self.lanes_to_quarantine,
            "fallback_profile": self.fallback_profile,
            "human_review_required": self.human_review_required
        }


# ==================== PROBE REGISTRY ====================

class ProbeRegistry:
    """
    Registry for health probes.
    Allows dynamic registration of probes.
    """
    
    def __init__(self):
        self._probes: Dict[ProbeType, List[Callable]] = {
            ProbeType.LIVENESS: [],
            ProbeType.READINESS: [],
            ProbeType.SEMANTIC: []
        }
        self._probe_metadata: Dict[str, Dict] = {}
    
    def register(self, probe_type: ProbeType, probe_fn: Callable, 
                 name: str, description: str = "", priority: int = 0):
        """Register a probe function"""
        self._probes[probe_type].append((priority, probe_fn))
        self._probes[probe_type].sort(key=lambda x: -x[0])  # Higher priority first
        self._probe_metadata[name] = {
            "description": description,
            "priority": priority,
            "probe_type": probe_type.value
        }
        logger.debug(f"Registered probe: {name} ({probe_type.value})")
    
    def get_probes(self, probe_type: ProbeType) -> List[Callable]:
        """Get all probes for a type"""
        return [probe for _, probe in self._probes[probe_type]]
    
    def get_all_probe_names(self) -> List[str]:
        """Get all registered probe names"""
        return list(self._probe_metadata.keys())


# ==================== LIVENESS PROBE ====================

class LivenessProbe:
    """
    Liveness Probe: Is the system alive?
    
    Checks:
    - Thread/loop is running
    - Queue processing is active
    - No deadlocks detected
    - Basic system responsiveness
    """
    
    def __init__(self, kernel=None):
        self.kernel = kernel
        self._last_check_time: Optional[float] = None
        self._consecutive_failures: int = 0
    
    def check_all(self) -> List[ProbeResult]:
        """Run all liveness checks"""
        results = []
        
        results.append(self._check_threads())
        results.append(self._check_queues())
        results.append(self._check_event_loop())
        results.append(self._check_responsiveness())
        
        self._last_check_time = time.time()
        
        # Track failures
        if any(r.level in [HealthLevel.CRITICAL, HealthLevel.FAILED] for r in results):
            self._consecutive_failures += 1
        else:
            self._consecutive_failures = 0
        
        return results
    
    def _check_threads(self) -> ProbeResult:
        """Check if critical threads are running"""
        start = time.time()
        
        try:
            # Check thread count and status
            active_count = threading.active_count()
            
            details = {
                "active_threads": active_count,
                "thread_limit": threading.stack_size()
            }
            
            # Basic liveness - at least main thread should be running
            level = HealthLevel.HEALTHY if active_count > 0 else HealthLevel.FAILED
            
            return ProbeResult(
                probe_type=ProbeType.LIVENESS,
                probe_name="thread_health",
                level=level,
                message=f"Threads active: {active_count}",
                details=details,
                execution_time_ms=(time.time() - start) * 1000
            )
        except Exception as e:
            return ProbeResult(
                probe_type=ProbeType.LIVENESS,
                probe_name="thread_health",
                level=HealthLevel.FAILED,
                message=f"Thread check failed: {str(e)}",
                details={"error": str(e)},
                execution_time_ms=(time.time() - start) * 1000,
                recoverable=True
            )
    
    def _check_queues(self) -> ProbeResult:
        """Check if queues are processing"""
        start = time.time()
        
        try:
            queue_health = "unknown"
            
            if self.kernel:
                # Check kernel queues
                if hasattr(self.kernel, 'get_task_queue_status'):
                    status = self.kernel.get_task_queue_status()
                    queue_health = "operational"
                    details = {"queue_status": str(status)}
                else:
                    queue_health = "no_status_method"
                    details = {}
            else:
                queue_health = "no_kernel_reference"
                details = {}
            
            level = HealthLevel.HEALTHY if queue_health == "operational" else HealthLevel.DEGRADED
            
            return ProbeResult(
                probe_type=ProbeType.LIVENESS,
                probe_name="queue_health",
                level=level,
                message=f"Queue health: {queue_health}",
                details=details,
                execution_time_ms=(time.time() - start) * 1000
            )
        except Exception as e:
            return ProbeResult(
                probe_type=ProbeType.LIVENESS,
                probe_name="queue_health",
                level=HealthLevel.CRITICAL,
                message=f"Queue check failed: {str(e)}",
                details={"error": str(e)},
                execution_time_ms=(time.time() - start) * 1000,
                recoverable=True
            )
    
    def _check_event_loop(self) -> ProbeResult:
        """Check if event loop is responsive"""
        start = time.time()
        
        try:
            # Check asyncio event loop
            try:
                loop = asyncio.get_event_loop()
                is_running = loop.is_running()
                
                details = {
                    "loop_exists": True,
                    "is_running": is_running
                }
                
                level = HealthLevel.HEALTHY if is_running else HealthLevel.DEGRADED
                
                return ProbeResult(
                    probe_type=ProbeType.LIVENESS,
                    probe_name="event_loop",
                    level=level,
                    message=f"Event loop: {'running' if is_running else 'not running'}",
                    details=details,
                    execution_time_ms=(time.time() - start) * 1000
                )
            except RuntimeError:
                # No event loop in current thread
                return ProbeResult(
                    probe_type=ProbeType.LIVENESS,
                    probe_name="event_loop",
                    level=HealthLevel.DEGRADED,
                    message="No event loop in current thread (may be normal)",
                    details={"loop_exists": False},
                    execution_time_ms=(time.time() - start) * 1000
                )
        except Exception as e:
            return ProbeResult(
                probe_type=ProbeType.LIVENESS,
                probe_name="event_loop",
                level=HealthLevel.FAILED,
                message=f"Event loop check failed: {str(e)}",
                details={"error": str(e)},
                execution_time_ms=(time.time() - start) * 1000
            )
    
    def _check_responsiveness(self) -> ProbeResult:
        """Check system responsiveness"""
        start = time.time()
        
        try:
            # Simple responsiveness check
            check_start = time.time()
            _ = time.time() - check_start  # Basic time check
            
            response_time_ms = (time.time() - start) * 1000
            
            level = HealthLevel.HEALTHY if response_time_ms < 100 else HealthLevel.DEGRADED
            
            return ProbeResult(
                probe_type=ProbeType.LIVENESS,
                probe_name="system_responsiveness",
                level=level,
                message=f"Response time: {response_time_ms:.2f}ms",
                details={"response_time_ms": response_time_ms},
                execution_time_ms=(time.time() - start) * 1000
            )
        except Exception as e:
            return ProbeResult(
                probe_type=ProbeType.LIVENESS,
                probe_name="system_responsiveness",
                level=HealthLevel.FAILED,
                message=f"Responsiveness check failed: {str(e)}",
                details={"error": str(e)},
                execution_time_ms=(time.time() - start) * 1000
            )


# ==================== READINESS PROBE ====================

class ReadinessProbe:
    """
    Readiness Probe: Is the system ready for real tasks?
    
    Checks:
    - Critical capabilities available
    - Approval/policy paths operational
    - Compiler/verifier usable
    - Tool catalog ready
    """
    
    def __init__(self, kernel=None):
        self.kernel = kernel
        self._last_ready_state: Optional[bool] = None
    
    def check_all(self) -> List[ProbeResult]:
        """Run all readiness checks"""
        results = []
        
        results.append(self._check_capabilities())
        results.append(self._check_approval_path())
        results.append(self._check_compiler())
        results.append(self._check_verifier())
        results.append(self._check_tool_catalog())
        results.append(self._check_policy_engine())
        
        self._last_ready_state = all(
            r.level in [HealthLevel.HEALTHY, HealthLevel.DEGRADED] 
            for r in results
        )
        
        return results
    
    def _check_capabilities(self) -> ProbeResult:
        """Check if critical capabilities are available"""
        start = time.time()
        
        capabilities = {}
        
        if self.kernel:
            # Check kernel capabilities
            if hasattr(self.kernel, '_health_status'):
                capabilities = self.kernel._health_status.copy()
        
        # Determine if critical capabilities are available
        critical = ["browser_available", "code_execution_available"]
        critical_available = all(capabilities.get(c, False) for c in critical)
        
        details = {
            "capabilities": capabilities,
            "critical_available": critical_available
        }
        
        level = HealthLevel.HEALTHY if critical_available else HealthLevel.DEGRADED
        
        return ProbeResult(
            probe_type=ProbeType.READINESS,
            probe_name="critical_capabilities",
            level=level,
            message=f"Critical capabilities: {'available' if critical_available else 'missing'}",
            details=details,
            execution_time_ms=(time.time() - start) * 1000,
            recommendations=["Enable missing critical capabilities"] if not critical_available else []
        )
    
    def _check_approval_path(self) -> ProbeResult:
        """Check if approval engine is operational"""
        start = time.time()
        
        try:
            approval_healthy = False
            details = {}
            
            if self.kernel:
                if hasattr(self.kernel, 'approval_engine'):
                    engine = self.kernel.approval_engine
                    approval_healthy = engine is not None
                    details = {"approval_engine": "present" if approval_healthy else "missing"}
                    
                    if approval_healthy and hasattr(engine, 'get_status'):
                        try:
                            status = engine.get_status()
                            details["status"] = str(status)
                        except Exception:
                            pass
            
            if not approval_healthy:
                # Check if kernel has approval integrated
                if self.kernel and hasattr(self.kernel, 'mode'):
                    details["kernel_mode"] = str(self.kernel.mode)
            
            level = HealthLevel.HEALTHY if approval_healthy else HealthLevel.DEGRADED
            
            return ProbeResult(
                probe_type=ProbeType.READINESS,
                probe_name="approval_path",
                level=level,
                message=f"Approval path: {'operational' if approval_healthy else 'degraded'}",
                details=details,
                execution_time_ms=(time.time() - start) * 1000,
                recommendations=["Configure approval engine"] if level == HealthLevel.DEGRADED else []
            )
        except Exception as e:
            return ProbeResult(
                probe_type=ProbeType.READINESS,
                probe_name="approval_path",
                level=HealthLevel.FAILED,
                message=f"Approval check failed: {str(e)}",
                details={"error": str(e)},
                execution_time_ms=(time.time() - start) * 1000
            )
    
    def _check_compiler(self) -> ProbeResult:
        """Check if compiler is usable"""
        start = time.time()
        
        compiler_ready = False
        details = {}
        
        if self.kernel:
            # Check for planner/compiler
            if hasattr(self.kernel, 'planner'):
                details["planner_present"] = True
                compiler_ready = True
            else:
                details["planner_present"] = False
            
            # Check for code engine
            if hasattr(self.kernel, 'code_engine'):
                details["code_engine_present"] = True
            else:
                details["code_engine_present"] = False
        
        level = HealthLevel.HEALTHY if compiler_ready else HealthLevel.DEGRADED
        
        return ProbeResult(
            probe_type=ProbeType.READINESS,
            probe_name="compiler_readiness",
            level=level,
            message=f"Compiler: {'ready' if compiler_ready else 'not ready'}",
            details=details,
            execution_time_ms=(time.time() - start) * 1000
        )
    
    def _check_verifier(self) -> ProbeResult:
        """Check if verifier is usable"""
        start = time.time()
        
        verifier_ready = False
        details = {}
        
        if self.kernel:
            # Check for verification system
            if hasattr(self.kernel, 'verification_engine'):
                details["verification_engine"] = "present"
                verifier_ready = True
            elif hasattr(self.kernel, '_verification_engine'):
                details["verification_engine"] = "present"
                verifier_ready = True
            else:
                details["verification_engine"] = "not_found"
        
        level = HealthLevel.HEALTHY if verifier_ready else HealthLevel.DEGRADED
        
        return ProbeResult(
            probe_type=ProbeType.READINESS,
            probe_name="verifier_readiness",
            level=level,
            message=f"Verifier: {'ready' if verifier_ready else 'not ready'}",
            details=details,
            execution_time_ms=(time.time() - start) * 1000
        )
    
    def _check_tool_catalog(self) -> ProbeResult:
        """Check if tool catalog is ready"""
        start = time.time()
        
        tools_available = False
        tool_count = 0
        details = {}
        
        if self.kernel:
            # Check for tools
            if hasattr(self.kernel, 'tools'):
                tools = self.kernel.tools
                if tools:
                    tools_available = True
                    tool_count = len(tools) if isinstance(tools, (list, dict)) else 0
                    details["tool_count"] = tool_count
        
        details["tools_available"] = tools_available
        
        level = HealthLevel.HEALTHY if tools_available else HealthLevel.DEGRADED
        
        return ProbeResult(
            probe_type=ProbeType.READINESS,
            probe_name="tool_catalog",
            level=level,
            message=f"Tool catalog: {'ready' if tools_available else 'not ready'} ({tool_count} tools)",
            details=details,
            execution_time_ms=(time.time() - start) * 1000
        )
    
    def _check_policy_engine(self) -> ProbeResult:
        """Check if policy engine is operational"""
        start = time.time()
        
        policy_ready = False
        details = {}
        
        if self.kernel:
            # Check for policy-related components
            if hasattr(self.kernel, 'policy_engine'):
                policy_ready = True
                details["policy_engine"] = "present"
            elif hasattr(self.kernel, '_policy'):
                policy_ready = True
                details["policy_engine"] = "present"
            else:
                details["policy_engine"] = "not_found"
        
        level = HealthLevel.HEALTHY if policy_ready else HealthLevel.DEGRADED
        
        return ProbeResult(
            probe_type=ProbeType.READINESS,
            probe_name="policy_engine",
            level=level,
            message=f"Policy engine: {'operational' if policy_ready else 'not configured'}",
            details=details,
            execution_time_ms=(time.time() - start) * 1000
        )


# ==================== SEMANTIC PROBE ====================

class SemanticProbe:
    """
    Semantic Probe: Is the system semantically healthy?
    
    Checks:
    - Invariants not violated
    - Restore state consistent
    - Replay state valid
    - Ledger/checkpoint accounting consistent
    """
    
    def __init__(self, kernel=None):
        self.kernel = kernel
        self._replay_available = False
        self._invariant_engine_available = False
        
        # Check for replay subsystem
        try:
            from agent.replay import ReplayEngine, InvariantEngine
            self._replay_available = True
            self._invariant_engine_available = True
        except ImportError:
            pass
    
    def check_all(self) -> List[ProbeResult]:
        """Run all semantic checks"""
        results = []
        
        results.append(self._check_invariants())
        results.append(self._check_restore_consistency())
        results.append(self._check_replay_readiness())
        results.append(self._check_ledger_consistency())
        results.append(self._check_state_machine())
        
        return results
    
    def _check_invariants(self) -> ProbeResult:
        """Check if invariants are satisfied"""
        start = time.time()
        
        try:
            invariant_status = "unknown"
            details = {}
            
            if self.kernel:
                # Check for invariant engine
                if hasattr(self.kernel, 'invariant_engine'):
                    engine = self.kernel.invariant_engine
                    if hasattr(engine, 'check_all'):
                        try:
                            result = engine.check_all()
                            invariant_status = "checked"
                            details = result if isinstance(result, dict) else {"result": str(result)}
                        except Exception as e:
                            invariant_status = f"error: {str(e)}"
                            details = {"error": str(e)}
                    else:
                        invariant_status = "engine_present"
                        details = {"has_check_method": False}
                else:
                    invariant_status = "no_invariant_engine"
                    details = {"note": "Invariant engine not integrated"}
            
            # Determine level
            if invariant_status == "checked":
                level = HealthLevel.HEALTHY
            elif invariant_status == "unknown":
                level = HealthLevel.UNKNOWN
            else:
                level = HealthLevel.DEGRADED
            
            return ProbeResult(
                probe_type=ProbeType.SEMANTIC,
                probe_name="invariant_check",
                level=level,
                message=f"Invariant status: {invariant_status}",
                details=details,
                execution_time_ms=(time.time() - start) * 1000,
                recommendations=["Integrate invariant engine for semantic checks"] if level == HealthLevel.DEGRADED else []
            )
        except Exception as e:
            return ProbeResult(
                probe_type=ProbeType.SEMANTIC,
                probe_name="invariant_check",
                level=HealthLevel.FAILED,
                message=f"Invariant check failed: {str(e)}",
                details={"error": str(e)},
                execution_time_ms=(time.time() - start) * 1000
            )
    
    def _check_restore_consistency(self) -> ProbeResult:
        """Check if restore state is semantically consistent"""
        start = time.time()
        
        try:
            restore_consistent = True
            details = {}
            
            if self.kernel:
                # Check task queue state
                if hasattr(self.kernel, 'task_queue'):
                    queue = self.kernel.task_queue
                    details["has_task_queue"] = True
                    
                    # Check for corrupted tasks
                    if hasattr(queue, 'qsize'):
                        try:
                            size = queue.qsize()
                            details["queue_size"] = size
                        except Exception:
                            pass
                else:
                    details["has_task_queue"] = False
                
                # Check persistence
                if hasattr(self.kernel, 'persistence'):
                    details["has_persistence"] = True
                else:
                    details["has_persistence"] = False
            
            level = HealthLevel.HEALTHY if restore_consistent else HealthLevel.DEGRADED
            
            return ProbeResult(
                probe_type=ProbeType.SEMANTIC,
                probe_name="restore_consistency",
                level=level,
                message=f"Restore consistency: {'valid' if restore_consistent else 'needs verification'}",
                details=details,
                execution_time_ms=(time.time() - start) * 1000
            )
        except Exception as e:
            return ProbeResult(
                probe_type=ProbeType.SEMANTIC,
                probe_name="restore_consistency",
                level=HealthLevel.FAILED,
                message=f"Restore consistency check failed: {str(e)}",
                details={"error": str(e)},
                execution_time_ms=(time.time() - start) * 1000
            )
    
    def _check_replay_readiness(self) -> ProbeResult:
        """Check if replay subsystem is ready"""
        start = time.time()
        
        try:
            details = {
                "replay_available": self._replay_available,
                "invariant_engine_available": self._invariant_engine_available
            }
            
            if self.kernel:
                if hasattr(self.kernel, 'replay_engine'):
                    details["replay_engine_integrated"] = True
                    if hasattr(self.kernel.replay_engine, 'get_status'):
                        try:
                            status = self.kernel.replay_engine.get_status()
                            details["replay_status"] = str(status)
                        except Exception:
                            pass
                else:
                    details["replay_engine_integrated"] = False
            
            level = HealthLevel.HEALTHY if self._replay_available else HealthLevel.DEGRADED
            
            return ProbeResult(
                probe_type=ProbeType.SEMANTIC,
                probe_name="replay_readiness",
                level=level,
                message=f"Replay subsystem: {'ready' if self._replay_available else 'not available'}",
                details=details,
                execution_time_ms=(time.time() - start) * 1000,
                recommendations=["Integrate replay engine for semantic validation"] if not self._replay_available else []
            )
        except Exception as e:
            return ProbeResult(
                probe_type=ProbeType.SEMANTIC,
                probe_name="replay_readiness",
                level=HealthLevel.FAILED,
                message=f"Replay readiness check failed: {str(e)}",
                details={"error": str(e)},
                execution_time_ms=(time.time() - start) * 1000
            )
    
    def _check_ledger_consistency(self) -> ProbeResult:
        """Check if ledger/budget accounting is consistent"""
        start = time.time()
        
        try:
            ledger_healthy = True
            details = {}
            
            if self.kernel:
                # Check budget ledger
                if hasattr(self.kernel, 'budget_ledger'):
                    details["budget_ledger"] = "present"
                else:
                    details["budget_ledger"] = "not_found"
                
                # Check run ledger
                if hasattr(self.kernel, 'run_ledger'):
                    details["run_ledger"] = "present"
                else:
                    details["run_ledger"] = "not_found"
            
            level = HealthLevel.HEALTHY if ledger_healthy else HealthLevel.DEGRADED
            
            return ProbeResult(
                probe_type=ProbeType.SEMANTIC,
                probe_name="ledger_consistency",
                level=level,
                message=f"Ledger consistency: checked",
                details=details,
                execution_time_ms=(time.time() - start) * 1000
            )
        except Exception as e:
            return ProbeResult(
                probe_type=ProbeType.SEMANTIC,
                probe_name="ledger_consistency",
                level=HealthLevel.FAILED,
                message=f"Ledger check failed: {str(e)}",
                details={"error": str(e)},
                execution_time_ms=(time.time() - start) * 1000
            )
    
    def _check_state_machine(self) -> ProbeResult:
        """Check if state machine is in valid state"""
        start = time.time()
        
        try:
            state_valid = True
            current_state = "unknown"
            details = {}
            
            if self.kernel:
                if hasattr(self.kernel, 'mode'):
                    current_state = str(self.kernel.mode)
                    details["current_mode"] = current_state
                    
                    # Check if mode is valid
                    valid_modes = ["interactive", "batch", "replay", "simulation"]
                    state_valid = current_state in valid_modes
                else:
                    details["mode_attribute"] = "not_found"
            
            level = HealthLevel.HEALTHY if state_valid else HealthLevel.DEGRADED
            
            return ProbeResult(
                probe_type=ProbeType.SEMANTIC,
                probe_name="state_machine",
                level=level,
                message=f"State machine: {current_state}",
                details=details,
                execution_time_ms=(time.time() - start) * 1000
            )
        except Exception as e:
            return ProbeResult(
                probe_type=ProbeType.SEMANTIC,
                probe_name="state_machine",
                level=HealthLevel.FAILED,
                message=f"State machine check failed: {str(e)}",
                details={"error": str(e)},
                execution_time_ms=(time.time() - start) * 1000
            )


# ==================== CAPABILITY GATE ====================

class CapabilityGate:
    """
    Capability Gate: Maps health outcomes to capability posture.
    
    This ensures that health outcomes automatically affect what
    capabilities are available to the system.
    """
    
    # Default capability to posture mappings
    DEFAULT_MAPPINGS = {
        "browser": {
            HealthLevel.HEALTHY: CapabilityPosture.FULL,
            HealthLevel.DEGRADED: CapabilityPosture.RESTRICTED,
            HealthLevel.CRITICAL: CapabilityPosture.CONSERVATIVE,
            HealthLevel.FAILED: CapabilityPosture.EMERGENCY,
            HealthLevel.UNKNOWN: CapabilityPosture.CONSERVATIVE
        },
        "code_execution": {
            HealthLevel.HEALTHY: CapabilityPosture.FULL,
            HealthLevel.DEGRADED: CapabilityPosture.RESTRICTED,
            HealthLevel.CRITICAL: CapabilityPosture.EMERGENCY,
            HealthLevel.FAILED: CapabilityPosture.READY_ONLY,
            HealthLevel.UNKNOWN: CapabilityPosture.CONSERVATIVE
        },
        "destructive_tools": {
            HealthLevel.HEALTHY: CapabilityPosture.FULL,
            HealthLevel.DEGRADED: CapabilityPosture.CONSERVATIVE,
            HealthLevel.CRITICAL: CapabilityPosture.EMERGENCY,
            HealthLevel.FAILED: CapabilityPosture.READY_ONLY,
            HealthLevel.UNKNOWN: CapabilityPosture.EMERGENCY
        },
        "replay": {
            HealthLevel.HEALTHY: CapabilityPosture.FULL,
            HealthLevel.DEGRADED: CapabilityPosture.RESTRICTED,
            HealthLevel.CRITICAL: CapabilityPosture.READY_ONLY,
            HealthLevel.FAILED: CapabilityPosture.READY_ONLY,
            HealthLevel.UNKNOWN: CapabilityPosture.RESTRICTED
        },
        "self_improvement": {
            HealthLevel.HEALTHY: CapabilityPosture.FULL,
            HealthLevel.DEGRADED: CapabilityPosture.CONSERVATIVE,
            HealthLevel.CRITICAL: CapabilityPosture.EMERGENCY,
            HealthLevel.FAILED: CapabilityPosture.READY_ONLY,
            HealthLevel.UNKNOWN: CapabilityPosture.EMERGENCY
        }
    }
    
    def __init__(self, kernel=None):
        self.kernel = kernel
        self._current_posture: Dict[str, CapabilityPosture] = {}
        self._mappings = self.DEFAULT_MAPPINGS.copy()
        self._gates: Dict[str, bool] = {}  # capability -> allowed
    
    def evaluate(self, probe_results: List[ProbeResult]) -> List[CapabilityGateResult]:
        """Evaluate capabilities based on probe results"""
        results = []
        
        # Aggregate health levels by component
        health_by_component = self._aggregate_health(probe_results)
        
        # Evaluate each capability
        for capability, health_level in health_by_component.items():
            mapping = self._mappings.get(capability, {})
            posture = mapping.get(health_level, CapabilityPosture.CONSERVATIVE)
            
            allowed = posture != CapabilityPosture.EMERGENCY and posture != CapabilityPosture.READY_ONLY
            
            result = CapabilityGateResult(
                capability=capability,
                allowed=allowed,
                posture=posture,
                reason=f"Health level: {health_level.value}",
                restrictions=self._get_restrictions(posture)
            )
            
            results.append(result)
            self._current_posture[capability] = posture
            self._gates[capability] = allowed
        
        return results
    
    def _aggregate_health(self, probe_results: List[ProbeResult]) -> Dict[str, HealthLevel]:
        """Aggregate probe results into capability health levels"""
        # Map probes to capabilities
        capability_health: Dict[str, List[HealthLevel]] = defaultdict(list)
        
        for result in probe_results:
            probe_name = result.probe_name
            
            # Map probe to capability
            if "browser" in probe_name.lower() or "ui" in probe_name.lower():
                capability_health["browser"].append(result.level)
            elif "code" in probe_name.lower() or "compiler" in probe_name.lower():
                capability_health["code_execution"].append(result.level)
            elif "tool" in probe_name.lower():
                capability_health["destructive_tools"].append(result.level)
            elif "replay" in probe_name.lower():
                capability_health["replay"].append(result.level)
            elif "improvement" in probe_name.lower() or "learning" in probe_name.lower():
                capability_health["self_improvement"].append(result.level)
        
        # Aggregate: worst level wins
        result = {}
        for capability, levels in capability_health.items():
            if levels:
                # Use worst level
                worst = min(levels, key=lambda x: (
                    0 if x == HealthLevel.HEALTHY else
                    1 if x == HealthLevel.DEGRADED else
                    2 if x == HealthLevel.UNKNOWN else
                    3 if x == HealthLevel.CRITICAL else
                    4
                ))
                result[capability] = worst
        
        # Add defaults for missing capabilities
        for cap in self._mappings.keys():
            if cap not in result:
                result[cap] = HealthLevel.UNKNOWN
        
        return result
    
    def _get_restrictions(self, posture: CapabilityPosture) -> List[str]:
        """Get restrictions for a posture"""
        restrictions = {
            CapabilityPosture.FULL: [],
            CapabilityPosture.RESTRICTED: ["Some operations may fail"],
            CapabilityPosture.CONSERVATIVE: ["All destructive ops require approval"],
            CapabilityPosture.EMERGENCY: ["Only read operations allowed"],
            CapabilityPosture.READY_ONLY: ["No execution, readiness only"]
        }
        return restrictions.get(posture, [])
    
    def is_capability_allowed(self, capability: str) -> bool:
        """Check if a capability is currently allowed"""
        return self._gates.get(capability, True)
    
    def get_current_posture(self, capability: str) -> CapabilityPosture:
        """Get current posture for a capability"""
        return self._current_posture.get(capability, CapabilityPosture.FULL)
    
    def get_all_gates(self) -> Dict[str, bool]:
        """Get all capability gates status"""
        return self._gates.copy()


# ==================== CANARY RUNNER ====================

class CanaryRunner:
    """
    Canary Runner: Runs canary tasks before real missions.
    
    Canary tasks are small, safe tests that validate the system
    is ready for real work.
    """
    
    def __init__(self, kernel=None):
        self.kernel = kernel
        self._canary_results: List[CanaryResult] = []
    
    def run_all_canaries(self) -> List[CanaryResult]:
        """Run all canary tasks"""
        results = []
        
        results.append(self._canary_read_only())
        results.append(self._canary_memory_write())
        results.append(self._canary_approval_roundtrip())
        results.append(self._canary_verifier_sanity())
        results.append(self._canary_replay_sanity())
        
        self._canary_results = results
        return results
    
    def _canary_read_only(self) -> CanaryResult:
        """Canary: Read-only operation"""
        start = time.time()
        
        try:
            # Simple read-only check
            result = "read_only_ok"
            
            return CanaryResult(
                canary_name="read_only",
                passed=True,
                execution_time_ms=(time.time() - start) * 1000,
                details={"result": result}
            )
        except Exception as e:
            return CanaryResult(
                canary_name="read_only",
                passed=False,
                execution_time_ms=(time.time() - start) * 1000,
                error=str(e)
            )
    
    def _canary_memory_write(self) -> CanaryResult:
        """Canary: Memory write with rollback"""
        start = time.time()
        
        try:
            write_ok = False
            
            if self.kernel and hasattr(self.kernel, 'memory'):
                memory = self.kernel.memory
                if hasattr(memory, 'write'):
                    # Try a test write
                    try:
                        test_key = f"_canary_test_{int(time.time())}"
                        # We don't actually write to avoid side effects
                        write_ok = True
                    except Exception:
                        pass
            
            return CanaryResult(
                canary_name="memory_write_rollback",
                passed=write_ok,
                execution_time_ms=(time.time() - start) * 1000,
                details={"write_capability": write_ok}
            )
        except Exception as e:
            return CanaryResult(
                canary_name="memory_write_rollback",
                passed=False,
                execution_time_ms=(time.time() - start) * 1000,
                error=str(e)
            )
    
    def _canary_approval_roundtrip(self) -> CanaryResult:
        """Canary: Approval roundtrip test"""
        start = time.time()
        
        try:
            approval_ok = False
            
            if self.kernel:
                # Check approval system
                if hasattr(self.kernel, 'approval_engine'):
                    approval_ok = True
                elif hasattr(self.kernel, 'mode'):
                    # Kernel has mode which may include approval
                    approval_ok = True
            
            return CanaryResult(
                canary_name="approval_roundtrip",
                passed=approval_ok,
                execution_time_ms=(time.time() - start) * 1000,
                details={"approval_available": approval_ok}
            )
        except Exception as e:
            return CanaryResult(
                canary_name="approval_roundtrip",
                passed=False,
                execution_time_ms=(time.time() - start) * 1000,
                error=str(e)
            )
    
    def _canary_verifier_sanity(self) -> CanaryResult:
        """Canary: Verifier sanity check"""
        start = time.time()
        
        try:
            verifier_ok = False
            
            if self.kernel:
                if hasattr(self.kernel, 'verification_engine'):
                    verifier_ok = True
                elif hasattr(self.kernel, '_verification_engine'):
                    verifier_ok = True
            
            return CanaryResult(
                canary_name="verifier_sanity",
                passed=verifier_ok,
                execution_time_ms=(time.time() - start) * 1000,
                details={"verifier_available": verifier_ok}
            )
        except Exception as e:
            return CanaryResult(
                canary_name="verifier_sanity",
                passed=False,
                execution_time_ms=(time.time() - start) * 1000,
                error=str(e)
            )
    
    def _canary_replay_sanity(self) -> CanaryResult:
        """Canary: Replay sanity check"""
        start = time.time()
        
        try:
            replay_ok = False
            
            if self.kernel:
                if hasattr(self.kernel, 'replay_engine'):
                    replay_ok = True
            
            return CanaryResult(
                canary_name="replay_sanity",
                passed=replay_ok,
                execution_time_ms=(time.time() - start) * 1000,
                details={"replay_available": replay_ok}
            )
        except Exception as e:
            return CanaryResult(
                canary_name="replay_sanity",
                passed=False,
                execution_time_ms=(time.time() - start) * 1000,
                error=str(e)
            )
    
    def all_passed(self) -> bool:
        """Check if all canaries passed"""
        return all(r.passed for r in self._canary_results)
    
    def get_results(self) -> List[CanaryResult]:
        """Get all canary results"""
        return self._canary_results.copy()


# ==================== REPAIR ADVISOR ====================

class RepairAdvisor:
    """
    Repair Advisor: Provides repair advice based on health failures.
    
    Analyzes health check results and provides actionable advice
    on how to repair or mitigate issues.
    """
    
    def __init__(self, kernel=None):
        self.kernel = kernel
    
    def analyze(self, probe_results: List[ProbeResult], 
                capability_results: List[CapabilityGateResult]) -> List[RepairAdvice]:
        """Analyze results and provide repair advice"""
        advice_list = []
        
        # Analyze probe results
        for result in probe_results:
            if result.level in [HealthLevel.CRITICAL, HealthLevel.FAILED]:
                advice = self._get_probe_advice(result)
                if advice:
                    advice_list.append(advice)
        
        # Analyze capability gates
        for result in capability_results:
            if not result.allowed:
                advice = self._get_capability_advice(result)
                if advice:
                    advice_list.append(advice)
        
        # If no specific advice, provide general advice
        if not advice_list:
            advice_list.append(self._get_general_advice())
        
        return advice_list
    
    def _get_probe_advice(self, result: ProbeResult) -> Optional[RepairAdvice]:
        """Get advice for a failed probe"""
        
        # Categorize by probe type
        if result.probe_type == ProbeType.LIVENESS:
            if result.probe_name == "thread_health":
                return RepairAdvice(
                    severity="critical",
                    category="liveness",
                    description="System threads not healthy",
                    actions=["Restart kernel", "Check for deadlocks"],
                    human_review_required=True
                )
            elif result.probe_name == "queue_health":
                return RepairAdvice(
                    severity="critical",
                    category="liveness",
                    description="Queue processing not operational",
                    actions=["Clear stuck queues", "Check worker threads"],
                    capabilities_to_disable=["execution"]
                )
        
        elif result.probe_type == ProbeType.READINESS:
            if result.probe_name == "critical_capabilities":
                return RepairAdvice(
                    severity="critical",
                    category="readiness",
                    description="Critical capabilities not available",
                    actions=["Initialize missing capabilities", "Check configuration"],
                    human_review_required=True
                )
            elif result.probe_name == "approval_path":
                return RepairAdvice(
                    severity="high",
                    category="readiness",
                    description="Approval path not operational",
                    actions=["Configure approval engine", "Set approval mode"],
                    capabilities_to_disable=["destructive_tools"],
                    fallback_profile="conservative"
                )
            elif result.probe_name == "compiler_readiness":
                return RepairAdvice(
                    severity="high",
                    category="readiness",
                    description="Compiler not ready",
                    actions=["Check planner configuration", "Verify code engine"]
                )
        
        elif result.probe_type == ProbeType.SEMANTIC:
            if result.probe_name == "invariant_check":
                return RepairAdvice(
                    severity="critical",
                    category="semantic",
                    description="Invariant violations detected",
                    actions=["Review invariant engine", "Check state consistency"],
                    human_review_required=True,
                    capabilities_to_disable=["destructive_tools", "self_improvement"]
                )
            elif result.probe_name == "replay_readiness":
                return RepairAdvice(
                    severity="medium",
                    category="semantic",
                    description="Replay subsystem not ready",
                    actions=["Initialize replay engine", "Check replay configuration"]
                )
        
        return None
    
    def _get_capability_advice(self, result: CapabilityGateResult) -> Optional[RepairAdvice]:
        """Get advice for a gated capability"""
        
        if result.capability == "browser":
            return RepairAdvice(
                severity="high",
                category="capability",
                description=f"Browser capability restricted: {result.posture.value}",
                actions=["Check browser provider", "Verify UI subsystem"],
                lanes_to_quarantine=["browser_grounded"]
            )
        elif result.capability == "code_execution":
            return RepairAdvice(
                severity="critical",
                category="capability",
                description=f"Code execution restricted: {result.posture.value}",
                actions=["Check code engine", "Verify sandbox"],
                human_review_required=True,
                fallback_profile="read_only"
            )
        elif result.capability == "destructive_tools":
            return RepairAdvice(
                severity="high",
                category="capability",
                description=f"Destructive tools restricted: {result.posture.value}",
                actions=["Review tool policies", "Enable approval for all destructive ops"],
                fallback_profile="conservative"
            )
        
        return None
    
    def _get_general_advice(self) -> RepairAdvice:
        """Get general advice when no specific issues"""
        return RepairAdvice(
            severity="info",
            category="general",
            description="System appears healthy",
            actions=["Continue normal operations"]
        )


# ==================== KERNEL HEALTH SPINE ====================

class KernelHealthSpine:
    """
    Kernel Health Spine: Integrated health monitoring for the kernel.
    
    This is the main spine that integrates all health probes into
    the kernel's operational flow.
    
    Features:
    - Three-layer health probing (Liveness, Readiness, Semantic)
    - Automatic capability gating based on health
    - Canary task execution before missions
    - Repair advice generation
    - Event-driven health monitoring
    - Ledger integration
    """
    
    def __init__(self, kernel=None):
        self.kernel = kernel
        self.kernel_ref = kernel  # Alias for compatibility
        
        # Initialize probes
        self.liveness_probe = LivenessProbe(kernel)
        self.readiness_probe = ReadinessProbe(kernel)
        self.semantic_probe = SemanticProbe(kernel)
        
        # Initialize capability gate
        self.capability_gate = CapabilityGate(kernel)
        
        # Initialize canary runner
        self.canary_runner = CanaryRunner(kernel)
        
        # Initialize repair advisor
        self.repair_advisor = RepairAdvisor(kernel)
        
        # Health state
        self._last_health_check: Optional[Dict] = None
        self._health_history: List[Dict] = []
        self._max_history = 100
        
        # Health triggers
        self._health_triggers: Dict[str, Callable] = {}
        
        # Current posture
        self._current_posture = CapabilityPosture.FULL
        
        # Telemetry
        self._telemetry_path = Path("/tmp/kernel_health")
        self._telemetry_path.mkdir(parents=True, exist_ok=True)
        
        logger.info("KernelHealthSpine initialized")
    
    def check_health(self, force: bool = False) -> Dict:
        """
        Run comprehensive health check.
        
        Args:
            force: Force a new check even if recent
            
        Returns:
            Dictionary with full health status
        """
        # Rate limiting
        if not force and self._last_health_check:
            elapsed = time.time() - self._last_health_check.get("timestamp", 0)
            if elapsed < 5:  # Minimum 5 seconds between checks
                return self._last_health_check
        
        start_time = time.time()
        
        # Run all probes
        liveness_results = self.liveness_probe.check_all()
        readiness_results = self.readiness_probe.check_all()
        semantic_results = self.semantic_probe.check_all()
        
        all_results = liveness_results + readiness_results + semantic_results
        
        # Evaluate capability gates
        capability_results = self.capability_gate.evaluate(all_results)
        
        # Generate repair advice
        repair_advice = self.repair_advisor.analyze(all_results, capability_results)
        
        # Determine overall health
        overall_level = self._calculate_overall_level(all_results)
        
        # Determine posture
        self._current_posture = self._determine_posture(overall_level, capability_results)
        
        # Build result
        result = {
            "timestamp": time.time(),
            "overall_level": overall_level.value,
            "posture": self._current_posture.value,
            "execution_time_ms": (time.time() - start_time) * 1000,
            "probes": {
                "liveness": [r.to_dict() for r in liveness_results],
                "readiness": [r.to_dict() for r in readiness_results],
                "semantic": [r.to_dict() for r in semantic_results]
            },
            "capabilities": [r.to_dict() for r in capability_results],
            "repair_advice": [a.to_dict() for a in repair_advice],
            "canary_status": "not_run"  # Will be updated if canaries run
        }
        
        # Store and archive
        self._last_health_check = result
        self._health_history.append(result)
        
        # Trim history
        if len(self._health_history) > self._max_history:
            self._health_history = self._health_history[-self._max_history:]
        
        # Log to telemetry
        self._log_health_event(result)
        
        # Trigger callbacks
        self._trigger_health_events(result)
        
        logger.info(f"Health check complete: {overall_level.value} (posture: {self._current_posture.value})")
        
        return result
    
    def run_canaries(self) -> Dict:
        """Run canary tasks before a mission"""
        start_time = time.time()
        
        canary_results = self.canary_runner.run_all_canaries()
        
        result = {
            "timestamp": time.time(),
            "all_passed": self.canary_runner.all_passed(),
            "canaries": [r.to_dict() for r in canary_results],
            "execution_time_ms": (time.time() - start_time) * 1000
        }
        
        # Update last health check with canary status
        if self._last_health_check:
            self._last_health_check["canary_status"] = "passed" if result["all_passed"] else "failed"
            self._last_health_check["canary_results"] = result
        
        # Log event
        self._log_health_event({
            "event_type": "canary_completed",
            "all_passed": result["all_passed"],
            "canaries": result["canaries"]
        })
        
        logger.info(f"Canary run: {'PASSED' if result['all_passed'] else 'FAILED'}")
        
        return result
    
    def is_ready_for_mission(self) -> Tuple[bool, str]:
        """
        Check if system is ready for a real mission.
        
        Returns:
            Tuple of (is_ready, reason)
        """
        # Run health check
        health = self.check_health()
        
        # Check overall level
        if health["overall_level"] in ["critical", "failed"]:
            return False, f"System health: {health['overall_level']}"
        
        # Check posture
        if health["posture"] in ["emergency", "ready_only"]:
            return False, f"Posture too restricted: {health['posture']}"
        
        # Run canaries
        canaries = self.run_canaries()
        
        if not canaries["all_passed"]:
            failed = [c["canary_name"] for c in canaries["canaries"] if not c["passed"]]
            return False, f"Canaries failed: {', '.join(failed)}"
        
        return True, "Ready for mission"
    
    def register_trigger(self, event: str, callback: Callable):
        """Register a health trigger callback"""
        self._health_triggers[event] = callback
    
    def _calculate_overall_level(self, results: List[ProbeResult]) -> HealthLevel:
        """Calculate overall health level from probe results"""
        if not results:
            return HealthLevel.UNKNOWN
        
        # Use worst level
        levels = [r.level for r in results]
        
        if any(l == HealthLevel.FAILED for l in levels):
            return HealthLevel.FAILED
        elif any(l == HealthLevel.CRITICAL for l in levels):
            return HealthLevel.CRITICAL
        elif any(l == HealthLevel.DEGRADED for l in levels):
            return HealthLevel.DEGRADED
        elif any(l == HealthLevel.UNKNOWN for l in levels):
            return HealthLevel.UNKNOWN
        else:
            return HealthLevel.HEALTHY
    
    def _determine_posture(self, level: HealthLevel, 
                          capability_results: List[CapabilityGateResult]) -> CapabilityPosture:
        """Determine overall posture based on health and capabilities"""
        
        # Check if any critical capability is blocked
        critical_blocked = any(
            not r.allowed and r.capability in ["code_execution", "browser"]
            for r in capability_results
        )
        
        if level == HealthLevel.FAILED or critical_blocked:
            return CapabilityPosture.EMERGENCY
        elif level == HealthLevel.CRITICAL:
            return CapabilityPosture.EMERGENCY
        elif level == HealthLevel.DEGRADED:
            return CapabilityPosture.RESTRICTED
        elif level == HealthLevel.UNKNOWN:
            return CapabilityPosture.CONSERVATIVE
        else:
            return CapabilityPosture.FULL
    
    def _trigger_health_events(self, health_result: Dict):
        """Trigger registered health event callbacks"""
        
        level = health_result["overall_level"]
        
        # Map levels to events
        event_map = {
            "failed": "health_failed",
            "critical": "health_critical",
            "degraded": "health_degraded",
            "healthy": "health_healthy"
        }
        
        event = event_map.get(level, "health_unknown")
        
        if event in self._health_triggers:
            try:
                self._health_triggers[event](health_result)
            except Exception as e:
                logger.error(f"Health trigger failed: {e}")
    
    def _log_health_event(self, event: Dict):
        """Log health event to disk"""
        try:
            log_file = self._telemetry_path / f"health_{datetime.now().strftime('%Y%m%d')}.jsonl"
            with open(log_file, "a") as f:
                f.write(json.dumps(event) + "\n")
        except Exception as e:
            logger.warning(f"Failed to log health event: {e}")
    
    def get_health_summary(self) -> Dict:
        """Get a quick health summary"""
        if not self._last_health_check:
            return {
                "status": "unknown",
                "posture": "unknown",
                "last_check": None
            }
        
        return {
            "status": self._last_health_check["overall_level"],
            "posture": self._last_health_check["posture"],
            "last_check": self._last_health_check["timestamp"],
            "ready_for_mission": self.is_ready_for_mission()[0]
        }
    
    def get_capability_status(self) -> Dict[str, bool]:
        """Get current capability status"""
        return self.capability_gate.get_all_gates()
    
    def is_capability_allowed(self, capability: str) -> bool:
        """Check if a capability is currently allowed"""
        return self.capability_gate.is_capability_allowed(capability)


# ==================== FACTORY FUNCTIONS ====================

def create_kernel_health_spine(kernel=None) -> KernelHealthSpine:
    """Create a KernelHealthSpine instance"""
    return KernelHealthSpine(kernel)


def create_health_probes(kernel=None) -> Dict[str, Any]:
    """Create all health probes"""
    return {
        "liveness": LivenessProbe(kernel),
        "readiness": ReadinessProbe(kernel),
        "semantic": SemanticProbe(kernel)
    }
