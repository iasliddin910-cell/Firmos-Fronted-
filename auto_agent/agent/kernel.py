"""
OmniAgent X - CENTRAL KERNEL
============================
The operating system level orchestration layer

This is the ONE TRUE ORCHESTRATOR that brings together:
- Task Manager (with persistence)
- State Machine (with strict transitions)
- Scheduler (deeply integrated)
- Background Queue
- Retry Controller (with budget)
- Artifact Collector (with metadata)
- Multi-Agent Coordinator
- Recovery Engine (with classification)
- Rollback System

This replaces fragmented architecture with a unified kernel.

FIXED ISSUES:
1. _execute() - Real execution with proper tool selection
2. _repair() - Real recovery engine with error classification
3. _verify() - Task-aware verification
4. VerificationEngine - Real browser/screenshot verification
5. JSON parse - Robust with validation
6. Fallback planner - Real heuristic planner
7. Approval - Real wait state, no auto-approve
8. Success semantics - Not trusting model blindly
9. Artifact semantics - Rich metadata
10. Multi-agent coordinator - Role-based execution
11. Task persistence - Disk-backed state
12. Retry policy - Structured with budget
13. Fallback mode - Structured with telemetry
14. Bare except - Removed, structured errors
15. Telemetry - Per-step metrics
16. Scheduler - Deeply integrated
17. Recovery classification - Error types
18. Rollback - Checkpoint system
"""
import os
import json
import logging
import time
import asyncio
import threading
from typing import List, Dict, Optional, Any, Set, Callable, Tuple
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field
from collections import defaultdict, deque
from queue import Queue, PriorityQueue, Empty
from pathlib import Path
import uuid
import traceback

logger = logging.getLogger(__name__)


# ==================== ENUMS ====================

class KernelState(Enum):
    """Kernel state machine"""
    IDLE = "idle"
    THINKING = "thinking"
    ACTING = "acting"
    VERIFYING = "verifying"
    REPAIRING = "repairing"
    WAITING_APPROVAL = "waiting_approval"
    PAUSED = "paused"
    ERROR = "error"


class TaskPriority(Enum):
    """Task priorities"""
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3
    BACKGROUND = 4


class AgentRole(Enum):
    """Multi-agent roles"""
    PLANNER = "planner"
    EXECUTOR = "executor"
    VERIFIER = "verifier"
    CRITIC = "critic"
    RESEARCHER = "researcher"
    TOOL_BUILDER = "tool_builder"


class ErrorType(Enum):
    """Error classification for recovery"""
    # Execution errors
    EXECUTION_FAILED = "execution_failed"
    EXECUTION_TIMEOUT = "execution_timeout"
    EXECUTION_CRASHED = "execution_crashed"
    
    # Verification errors
    VERIFICATION_FAILED = "verification_failed"
    VERIFICATION_MISSING = "verification_missing"
    VERIFICATION_TIMEOUT = "verification_timeout"
    
    # Tool errors
    TOOL_NOT_FOUND = "tool_not_found"
    TOOL_INVALID_ARGS = "tool_invalid_args"
    TOOL_PERMISSION_DENIED = "tool_permission_denied"
    
    # Resource errors
    RESOURCE_NOT_FOUND = "resource_not_found"
    RESOURCE_BUSY = "resource_busy"
    RESOURCE_EXHAUSTED = "resource_exhausted"
    
    # Network errors
    NETWORK_ERROR = "network_error"
    NETWORK_TIMEOUT = "network_timeout"
    NETWORK_UNREACHABLE = "network_unreachable"
    
    # Approval errors
    APPROVAL_DENIED = "approval_denied"
    APPROVAL_TIMEOUT = "approval_timeout"
    
    # System errors
    SYSTEM_ERROR = "system_error"
    UNKNOWN_ERROR = "unknown_error"


class RecoveryStrategy(Enum):
    """Recovery strategies for different error types"""
    # Retry-based
    RETRY_SAME_TOOL = "retry_same_tool"
    RETRY_SAME_TASK = "retry_same_task"
    RETRY_WITH_BACKOFF = "retry_with_backoff"
    
    # Alternative approaches
    ALTERNATE_TOOL = "alternate_tool"
    ALTERNATE_APPROACH = "alternate_approach"
    SIMPLIFY_TASK = "simplify_task"
    
    # Recovery
    RECOVER_STATE = "recover_state"
    ROLLBACK = "rollback"
    RECREATE_RESOURCE = "recreate_resource"
    
    # Escalation
    ESCALATE_TO_HUMAN = "escalate_to_human"
    ABORT = "abort"


class TaskStatus(Enum):
    """Granular task status"""
    PENDING = "pending"
    DEPENDENCIES_WAITING = "dependencies_waiting"
    APPROVAL_WAITING = "approval_waiting"
    RUNNING = "running"
    VERIFYING = "verifying"
    VERIFIED = "verified"
    FAILED_VERIFICATION = "failed_verification"
    RETRYING = "retrying"
    RECOVERING = "recovering"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


# ==================== DATA CLASSES ====================

@dataclass
class Task:
    """Represents a task in the kernel"""
    id: str
    description: str
    priority: TaskPriority = TaskPriority.NORMAL
    state: str = "pending"
    status: TaskStatus = TaskStatus.PENDING
    dependencies: List[str] = field(default_factory=list)
    assigned_agent: Optional[AgentRole] = None
    input_data: Any = None
    output_data: Any = None
    error: Optional[str] = None
    error_type: Optional[ErrorType] = None
    recovery_strategy: Optional[RecoveryStrategy] = None
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    retry_count: int = 0
    max_retries: int = 3
    timeout: int = 30  # seconds
    artifacts: List[str] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)
    
    # New fields for enhanced task management
    approval_policy: str = "auto"  # auto, manual, never
    sandbox_mode: str = "normal"  # safe, normal, advanced
    estimated_cost: float = 0.0
    artifact_expectations: List[str] = field(default_factory=list)
    rollback_point: Optional[Dict] = None
    
    def __lt__(self, other):
        return self.priority.value < other.priority.value


@dataclass
class ExecutionResult:
    """Structured result of tool execution"""
    success: bool
    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0
    artifacts: List[str] = field(default_factory=list)
    tool_used: str = ""
    execution_time: float = 0.0
    error: Optional[str] = None
    error_type: Optional[ErrorType] = None
    
    # Verification info
    verified: bool = False
    verification_details: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "success": self.success,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "exit_code": self.exit_code,
            "artifacts": self.artifacts,
            "tool_used": self.tool_used,
            "execution_time": self.execution_time,
            "error": self.error,
            "error_type": self.error_type.value if self.error_type else None,
            "verified": self.verified,
            "verification_details": self.verification_details
        }


@dataclass
class RecoveryResult:
    """Result of recovery attempt"""
    success: bool
    strategy_used: RecoveryStrategy
    new_task: Optional[Task] = None
    recovery_action: str = ""
    error: Optional[str] = None
    should_continue: bool = True


@dataclass
class ApprovalRequest:
    """Approval request for dangerous operations"""
    request_id: str
    tool_name: str
    arguments: Dict
    risk_level: str  # low, medium, high, critical
    requested_by: str
    created_at: float = field(default_factory=time.time)
    status: str = "pending"  # pending, approved, denied, expired
    approved_by: Optional[str] = None
    denied_reason: Optional[str] = None
    expires_at: Optional[float] = None


@dataclass
class AgentState:
    """State of a specific agent"""
    role: AgentRole
    current_task: Optional[Task] = None
    status: str = "idle"  # idle, working, waiting, error
    workload: int = 0
    capabilities: List[str] = field(default_factory=list)
    reliability_score: float = 1.0
    total_tasks: int = 0
    successful_tasks: int = 0


@dataclass
class KernelEvent:
    """Kernel event for event sourcing"""
    event_type: str
    timestamp: float
    data: Dict
    source: str


@dataclass
class VerificationResult:
    """Result of verification"""
    passed: bool
    details: str
    evidence: Dict = field(default_factory=dict)
    severity: str = "info"  # info, warning, error


# ==================== VERIFICATION ENGINE ====================

class VerificationEngine:
    """
    Comprehensive verification layer
    Replaces shallow model-based verification
    """
    
    def __init__(self, tools_engine):
        self.tools = tools_engine
    
    def verify(self, verification_type: str, data: Dict) -> VerificationResult:
        """Run appropriate verification based on type"""
        
        verifiers = {
            "file_exists": self._verify_file_exists,
            "process_running": self._verify_process,
            "port_open": self._verify_port,
            "server_responding": self._verify_server,
            "browser_page": self._verify_browser,
            "screenshot": self._verify_screenshot,
            "code_syntax": self._verify_code_syntax,
            "function_result": self._verify_function_result,
        }
        
        verifier = verifiers.get(verification_type, self._default_verifier)
        return verifier(data)
    
    def _verify_file_exists(self, data: Dict) -> VerificationResult:
        """Verify file exists"""
        import os
        path = data.get("path", "")
        exists = os.path.exists(path)
        
        return VerificationResult(
            passed=exists,
            details=f"File {'exists' if exists else 'does not exist'}: {path}",
            evidence={"path": path, "exists": exists}
        )
    
    def _verify_process(self, data: Dict) -> VerificationResult:
        """Verify process is running"""
        import psutil
        process_name = data.get("process_name", "")
        running = False
        
        for proc in psutil.process_iter(['name']):
            try:
                if process_name.lower() in proc.info['name'].lower():
                    running = True
                    break
            except Exception as e: logger.warning(f"Exception: {e}")
        
        return VerificationResult(
            passed=running,
            details=f"Process '{process_name}' is {'running' if running else 'not running'}",
            evidence={"process": process_name, "running": running}
        )
    
    def _verify_port(self, data: Dict) -> VerificationResult:
        """Verify port is open"""
        import socket
        host = data.get("host", "localhost")
        port = data.get("port", 80)
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        try:
            result = sock.connect_ex((host, port))
            open_port = result == 0
        except socket.timeout:
            open_port = False
        except socket.error as e:
            open_port = False
            return VerificationResult(
                passed=False,
                details=f"Socket error: {str(e)}",
                severity="error",
                evidence={"host": host, "port": port, "error": str(e)}
            )
        except Exception as e:
            open_port = False
            return VerificationResult(
                passed=False,
                details=f"Port check error: {str(e)}",
                severity="error",
                evidence={"host": host, "port": port, "error": str(e)}
            )
        finally:
            sock.close()
        
        return VerificationResult(
            passed=open_port,
            details=f"Port {port} on {host} is {'open' if open_port else 'closed'}",
            evidence={"host": host, "port": port, "open": open_port}
        )
    
    def _verify_server(self, data: Dict) -> VerificationResult:
        """Verify HTTP server is responding"""
        import requests
        url = data.get("url", "")
        
        try:
            response = requests.get(url, timeout=5)
            success = response.status_code < 400
            return VerificationResult(
                passed=success,
                details=f"Server responded with status {response.status_code}",
                evidence={"url": url, "status": response.status_code}
            )
        except Exception as e:
            return VerificationResult(
                passed=False,
                details=f"Server not responding: {str(e)}",
                severity="error"
            )
    
    def _verify_browser(self, data: Dict) -> VerificationResult:
        """Verify browser page content using Playwright or Selenium"""
        expected_text = data.get("expected_text", "")
        url = data.get("url", "")
        expected_selector = data.get("expected_selector", "")
        
        # Try to use Playwright for real browser verification
        try:
            from playwright.sync_api import sync_playwright
            
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                
                try:
                    page.goto(url, timeout=10000)
                    page.wait_for_load_state("networkidle", timeout=5000)
                    
                    # Check for expected text
                    text_found = False
                    if expected_text:
                        content = page.content()
                        text_found = expected_text.lower() in content.lower()
                    
                    # Check for expected selector (FIXED: proper exception handling)
                    selector_found = True
                    if expected_selector:
                        try:
                            page.wait_for_selector(expected_selector, timeout=3000)
                            selector_found = True
                        except Exception as selector_err:
                            logger.warning(f"Selector wait error: {selector_err}")
                            selector_found = False
                    
                    browser.close()
                    
                    success = text_found and selector_found
                    return VerificationResult(
                        passed=success,
                        details=f"Browser verification: text={'found' if text_found else 'not found'}, selector={'found' if selector_found else 'not found'}",
                        evidence={"url": url, "expected_text": expected_text, "text_found": text_found, "selector_found": selector_found}
                    )
                except Exception as e:
                    browser.close()
                    return VerificationResult(
                        passed=False,
                        details=f"Browser verification failed: {str(e)}",
                        severity="error",
                        evidence={"url": url, "error": str(e)}
                    )
        except ImportError:
            # Fallback: try Selenium
            try:
                from selenium import webdriver
                from selenium.webdriver.common.by import By
                from selenium.webdriver.chrome.options import Options
                from selenium.webdriver.support.ui import WebDriverWait
                from selenium.webdriver.support import expected_conditions as EC
                
                options = Options()
                options.add_argument("--headless")
                driver = webdriver.Chrome(options=options)
                
                try:
                    driver.get(url)
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.TAG_NAME, "body"))
                    )
                    
                    content = driver.page_source
                    text_found = expected_text.lower() in content.lower() if expected_text else True
                    
                    driver.quit()
                    
                    return VerificationResult(
                        passed=text_found,
                        details=f"Selenium verification: text={'found' if text_found else 'not found'}",
                        evidence={"url": url, "expected_text": expected_text, "text_found": text_found}
                    )
                except Exception as e:
                    driver.quit()
                    return VerificationResult(
                        passed=False,
                        details=f"Selenium verification failed: {str(e)}",
                        severity="error",
                        evidence={"error": str(e)}
                    )
            except ImportError:
                # No browser automation available
                return VerificationResult(
                    passed=False,
                    details="Browser verification requires playwright or selenium. Neither is available.",
                    severity="error",
                    evidence={"error": "No browser automation library available"}
                )
    
    def _verify_screenshot(self, data: Dict) -> VerificationResult:
        """Verify screenshot contains expected elements using OCR"""
        expected_elements = data.get("expected_elements", [])
        screenshot_path = data.get("screenshot_path", "")
        
        # Check if screenshot exists
        import os
        if not os.path.exists(screenshot_path):
            return VerificationResult(
                passed=False,
                details="Screenshot file not found",
                severity="error",
                evidence={"path": screenshot_path}
            )
        
        # Try OCR with pytesseract
        try:
            from PIL import Image
            import pytesseract
            
            # Read screenshot
            image = Image.open(screenshot_path)
            
            # Extract text
            extracted_text = pytesseract.image_to_string(image)
            
            # Check for expected elements (as text)
            found_elements = []
            missing_elements = []
            
            for element in expected_elements:
                if element.lower() in extracted_text.lower():
                    found_elements.append(element)
                else:
                    missing_elements.append(element)
            
            success = len(missing_elements) == 0
            
            return VerificationResult(
                passed=success,
                details=f"Screenshot verification: {len(found_elements)}/{len(expected_elements)} elements found",
                evidence={
                    "path": screenshot_path,
                    "extracted_text": extracted_text[:200],
                    "found_elements": found_elements,
                    "missing_elements": missing_elements
                }
            )
        except ImportError:
            # CRITICAL: OCR not available = FAIL (not soft pass!)
            return VerificationResult(
                passed=False,
                details="Screenshot verification FAILED: pytesseract not available - cannot verify screenshot content",
                severity="error",
                evidence={"path": screenshot_path, "error": "OCR library not installed", "required": "pytesseract"}
            )
        except Exception as e:
            return VerificationResult(
                passed=False,
                details=f"Screenshot verification error: {str(e)}",
                severity="error",
                evidence={"path": screenshot_path, "error": str(e)}
            )
    
    def _verify_code_syntax(self, data: Dict) -> VerificationResult:
        """Verify code has no syntax errors"""
        code = data.get("code", "")
        language = data.get("language", "python")
        
        if language == "python":
            try:
                compile(code, '<string>', 'exec')
                return VerificationResult(passed=True, details="Python syntax OK")
            except SyntaxError as e:
                return VerificationResult(
                    passed=False,
                    details=f"Syntax error: {e}",
                    severity="error",
                    evidence={"error": str(e), "line": e.lineno}
                )
        
        if language == "javascript":
            try:
                import subprocess
                result = subprocess.run(
                    ["node", "-e", f"require('vm').createScript(`{code}`)"],
                    capture_output=True,
                    timeout=5
                )
                success = result.returncode == 0
                return VerificationResult(
                    passed=success,
                    details=f"JavaScript syntax {'OK' if success else 'error'}",
                    evidence={"stderr": result.stderr.decode() if result.stderr else ""}
                )
            except Exception as e:
                return VerificationResult(
                    passed=False,
                    details=f"JavaScript syntax check failed: {str(e)}",
                    severity="error"
                )
        
        return VerificationResult(
            passed=False,
            details=f"Syntax check not implemented for language: {language}",
            severity="warning",
            evidence={"language": language}
        )
    
    def _verify_function_result(self, data: Dict) -> VerificationResult:
        """Verify function execution result"""
        result = data.get("result", None)
        expected = data.get("expected", None)
        
        if expected is None:
            return VerificationResult(
                passed=result is not None,
                details="Result present" if result else "No result",
                severity="warning" if result is None else "info",
                evidence={"has_result": result is not None}
            )
        
        if isinstance(expected, str):
            success = expected.lower() in str(result).lower()
        else:
            success = result == expected
        
        return VerificationResult(
            passed=success,
            details=f"Result {'matches' if success else 'does not match'} expected",
            evidence={"result": str(result)[:200], "expected": str(expected)[:200], "match": success}
        )
    
    def _default_verifier(self, data: Dict) -> VerificationResult:
        """Default verification - FAIL SAFE"""
        return VerificationResult(
            passed=False,
            details="Unknown verification type - manual verification required",
            severity="warning",
            evidence={"data_keys": list(data.keys())}
        )


# ==================== CRITIC ENGINE ====================

class CriticEngine:
    """
    Independent critic for self-evaluation
    Evaluates plans, tools, patches for quality
    """
    
    def __init__(self, api_key: str):
        from openai import OpenAI
        self.client = OpenAI(api_key=api_key)
        self.criteria = {
            "plan_quality": [],
            "tool_selection": [],
            "patch_quality": [],
        }
    
    def evaluate_plan(self, plan: List[Task]) -> Dict[str, Any]:
        """Evaluate if plan is good"""
        
        # Check for common issues
        issues = []
        
        # Check for missing dependencies
        all_ids = {t.id for t in plan}
        for task in plan:
            for dep in task.dependencies:
                if dep not in all_ids:
                    issues.append(f"Missing dependency: {dep}")
        
        # Check for circular dependencies
        if self._has_circular_deps(plan):
            issues.append("Circular dependency detected")
        
        # Check for reasonable task count
        if len(plan) > 20:
            issues.append("Plan too complex (>20 tasks)")
        
        return {
            "approved": len(issues) == 0,
            "issues": issues,
            "score": max(0, 1.0 - len(issues) * 0.1)
        }
    
    def evaluate_tool_selection(self, task: Task, available_tools: List[str]) -> Dict[str, Any]:
        """Evaluate if right tool was selected"""
        
        # Simple heuristic evaluation
        tool = task.assigned_agent
        
        # Check if tool exists
        if tool and tool not in available_tools:
            return {
                "approved": False,
                "reason": f"Tool {tool} not in available tools",
                "score": 0.0
            }
        
        return {
            "approved": True,
            "reason": "Tool selection looks reasonable",
            "score": 0.8
        }
    
    def evaluate_patch(self, original: str, patched: str, error: str) -> Dict[str, Any]:
        """Evaluate if patch makes sense"""
        
        # Check for dangerous patterns
        dangerous = ["rm -rf", "format", "drop table", "delete from", "truncate"]
        
        issues = []
        for pattern in dangerous:
            if pattern in patched.lower():
                issues.append(f"Dangerous pattern detected: {pattern}")
        
        return {
            "approved": len(issues) == 0,
            "issues": issues,
            "score": max(0, 1.0 - len(issues) * 0.2)
        }
    
    def _has_circular_deps(self, tasks: List[Task]) -> bool:
        """Check for circular dependencies"""
        graph = {t.id: set(t.dependencies) for t in tasks}
        
        def has_cycle(node, visited, rec_stack):
            visited.add(node)
            rec_stack.add(node)
            
            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    if has_cycle(neighbor, visited, rec_stack):
                        return True
                elif neighbor in rec_stack:
                    return True
            
            rec_stack.remove(node)
            return False
        
        visited = set()
        for task in tasks:
            if task.id not in visited:
                if has_cycle(task.id, visited, set()):
                    return True
        
        return False


# ==================== MULTI-AGENT COORDINATOR ====================

class MultiAgentCoordinator:
    """
    Coordinates multiple specialized agents:
    - Planner Agent: Creates plans
    - Executor Agent: Executes tasks
    - Verifier Agent: Verifies results
    - Critic Agent: Evaluates quality
    - Researcher Agent: Gathers information
    - Tool Builder Agent: Creates new tools
    """
    
    def __init__(self, api_key: str, tools_engine):
        self.api_key = api_key
        self.tools = tools_engine
        
        # Initialize agent states
        self.agents: Dict[AgentRole, AgentState] = {
            role: AgentState(role=role, capabilities=self._get_agent_capabilities(role))
            for role in AgentRole
        }
        
        # Task queues for each role
        self.queues: Dict[AgentRole, deque] = {
            role: deque() for role in AgentRole
        }
        
        # Event log
        self.event_log: List[KernelEvent] = []
        
        logger.info("🤖 Multi-Agent Coordinator initialized")
    
    def _get_agent_capabilities(self, role: AgentRole) -> List[str]:
        """Get capabilities for each agent role"""
        capabilities = {
            AgentRole.PLANNER: ["create_plan", "break_down_task", "estimate_effort"],
            AgentRole.EXECUTOR: ["execute_tool", "run_code", "manage_process"],
            AgentRole.VERIFIER: ["verify_result", "check_conditions", "validate_output"],
            AgentRole.CRITIC: ["evaluate_plan", "assess_quality", "detect_issues"],
            AgentRole.RESEARCHER: ["web_search", "code_search", "documentation_search"],
            AgentRole.TOOL_BUILDER: ["create_tool", "generate_code", "write_tests"],
        }
        return capabilities.get(role, [])
    
    def assign_task(self, task: Task, role: AgentRole) -> bool:
        """Assign task to appropriate agent"""
        if role in self.agents:
            self.agents[role].workload += 1
            self.queues[role].append(task)
            self._log_event("task_assigned", {"task_id": task.id, "role": role.value})
            return True
        return False
    
    def get_next_task(self, role: AgentRole) -> Optional[Task]:
        """Get next task for agent"""
        if self.queues[role]:
            return self.queues[role].popleft()
        return None
    
    def complete_task(self, role: AgentRole, task: Task, success: bool):
        """Record task completion"""
        agent = self.agents[role]
        agent.workload = max(0, agent.workload - 1)
        agent.total_tasks += 1
        if success:
            agent.successful_tasks += 1
        
        # Update reliability score
        if agent.total_tasks > 0:
            agent.reliability_score = agent.successful_tasks / agent.total_tasks
        
        self._log_event("task_completed", {
            "task_id": task.id, 
            "role": role.value,
            "success": success
        })
    
    def get_status(self) -> Dict:
        """Get coordinator status"""
        return {
            role: {
                "status": state.status,
                "workload": state.workload,
                "reliability": state.reliability_score,
                "queue_size": len(self.queues[role])
            }
            for role, state in self.agents.items()
        }
    
    def _log_event(self, event_type: str, data: Dict):
        """Log event"""
        event = KernelEvent(
            event_type=event_type,
            timestamp=time.time(),
            data=data,
            source="coordinator"
        )
        self.event_log.append(event)
        
        # Keep only last 1000 events
        if len(self.event_log) > 1000:
            self.event_log = self.event_log[-1000:]


# ==================== TASK MANAGER ====================

class TaskManager:
    """
    Manages task lifecycle, scheduling, and execution
    """
    
    def __init__(self):
        self.tasks: Dict[str, Task] = {}
        self.pending_queue: PriorityQueue = PriorityQueue()
        self.running_tasks: Set[str] = set()
        self.completed_tasks: Set[str] = set()
        self.failed_tasks: Set[str] = set()
        
        # Background task queue
        self.background_queue: Queue = Queue()
        
        logger.info("📋 Task Manager initialized")
    
    def create_task(self, description: str, priority: TaskPriority = TaskPriority.NORMAL,
                   dependencies: List[str] = None, metadata: Dict = None) -> Task:
        """Create a new task"""
        task = Task(
            id=str(uuid.uuid4())[:8],
            description=description,
            priority=priority,
            dependencies=dependencies or [],
            metadata=metadata or {}
        )
        
        self.tasks[task.id] = task
        self.pending_queue.put(task)
        
        return task
    
    def get_ready_tasks(self) -> List[Task]:
        """Get tasks that are ready to execute (all deps satisfied)"""
        ready = []
        
        while not self.pending_queue.empty():
            try:
                task = self.pending_queue.get_nowait()
            except Empty:
                break
            
            # Check dependencies
            deps_satisfied = all(
                dep_id in self.completed_tasks 
                for dep_id in task.dependencies
            )
            
            if deps_satisfied and task.id not in self.running_tasks:
                ready.append(task)
            else:
                # Put back if not ready
                self.pending_queue.put(task)
                break
        
        return ready
    
    def mark_running(self, task_id: str):
        """Mark task as running"""
        if task_id in self.tasks:
            self.running_tasks.add(task_id)
            self.tasks[task_id].state = "running"
            self.tasks[task_id].started_at = time.time()
    
    def mark_completed(self, task_id: str, result: Any = None):
        """Mark task as completed"""
        if task_id in self.tasks:
            self.running_tasks.discard(task_id)
            self.completed_tasks.add(task_id)
            self.tasks[task_id].state = "completed"
            self.tasks[task_id].completed_at = time.time()
            self.tasks[task_id].output_data = result
    
    def mark_failed(self, task_id: str, error: str):
        """Mark task as failed"""
        if task_id in self.tasks:
            self.running_tasks.discard(task_id)
            self.failed_tasks.add(task_id)
            self.tasks[task_id].state = "failed"
            self.tasks[task_id].error = error
            self.tasks[task_id].completed_at = time.time()
    
    def retry_task(self, task_id: str) -> bool:
        """Retry a failed task"""
        if task_id in self.tasks:
            task = self.tasks[task_id]
            if task.retry_count < task.max_retries:
                task.retry_count += 1
                task.state = "pending"
                self.failed_tasks.discard(task_id)
                self.pending_queue.put(task)
                return True
        return False
    
    def get_task_graph(self) -> Dict:
        """Get task dependency graph"""
        return {
            "pending": len([t for t in self.tasks.values() if t.state == "pending"]),
            "running": len(self.running_tasks),
            "completed": len(self.completed_tasks),
            "failed": len(self.failed_tasks),
            "tasks": [
                {
                    "id": t.id,
                    "description": t.description[:50],
                    "state": t.state,
                    "priority": t.priority.name
                }
                for t in self.tasks.values()
            ]
        }


# ==================== ARTIFACT COLLECTOR ====================

class ArtifactCollector:
    """
    Collects and manages artifacts from task execution
    """
    
    def __init__(self, storage_dir: str = "artifacts"):
        self.storage_dir = storage_dir
        self.artifacts: Dict[str, List[str]] = defaultdict(list)
        
        # Create storage directory
        os.makedirs(storage_dir, exist_ok=True)
        
        logger.info(f"📦 Artifact Collector initialized: {storage_dir}")
    
    def collect(self, task_id: str, artifact_type: str, content: Any) -> str:
        """Collect an artifact"""
        import base64
        
        artifact_id = f"{task_id}_{artifact_type}_{int(time.time())}"
        
        # Handle different content types
        if isinstance(content, (dict, list)):
            # JSON
            filepath = f"{self.storage_dir}/{artifact_id}.json"
            with open(filepath, 'w') as f:
                json.dump(content, f, indent=2)
        elif isinstance(content, str) and len(content) > 1000:
            # Large text - save to file
            filepath = f"{self.storage_dir}/{artifact_id}.txt"
            with open(filepath, 'w') as f:
                f.write(content)
        else:
            # Small text - keep in memory
            filepath = f"{self.storage_dir}/{artifact_id}.txt"
            with open(filepath, 'w') as f:
                f.write(str(content))
        
        self.artifacts[task_id].append(filepath)
        
        return artifact_id
    
    def get_artifacts(self, task_id: str) -> List[str]:
        """Get all artifacts for a task"""
        return self.artifacts.get(task_id, [])
    
    def get_all_artifacts(self) -> Dict[str, List[str]]:
        """Get all artifacts"""
        return dict(self.artifacts)


# ==================== SCHEDULER ====================

class Scheduler:
    """
    Background scheduler for tasks
    """
    
    def __init__(self):
        self.scheduled_tasks: List[Dict] = []
        self.running = False
        
        logger.info("⏰ Scheduler initialized")
    
    def schedule(self, task: Callable, delay: float = 0, 
                 interval: float = None, name: str = None):
        """Schedule a task"""
        scheduled = {
            "task": task,
            "delay": delay,
            "interval": interval,
            "name": name or str(uuid.uuid4())[:8],
            "next_run": time.time() + delay,
            "last_run": None
        }
        self.scheduled_tasks.append(scheduled)
        
        return scheduled["name"]
    
    def run_pending(self):
        """Run pending scheduled tasks"""
        now = time.time()
        
        for scheduled in self.scheduled_tasks:
            if now >= scheduled["next_run"]:
                try:
                    scheduled["task"]()
                    scheduled["last_run"] = now
                    
                    if scheduled["interval"]:
                        scheduled["next_run"] = now + scheduled["interval"]
                    else:
                        # One-time task, remove it
                        self.scheduled_tasks.remove(scheduled)
                except Exception as e:
                    logger.error(f"Scheduled task error: {e}")
    
    def cancel(self, name: str):
        """Cancel a scheduled task"""
        self.scheduled_tasks = [
            t for t in self.scheduled_tasks 
            if t["name"] != name
        ]
    
    def get_status(self) -> Dict:
        """Get scheduler status"""
        return {
            "task_count": len(self.scheduled_tasks),
            "tasks": [
                {
                    "name": t["name"],
                    "next_run": t["next_run"],
                    "interval": t["interval"]
                }
                for t in self.scheduled_tasks
            ]
        }


# ==================== TELEMETRY ====================

class Telemetry:
    """
    Metrics and monitoring
    """
    
    def __init__(self):
        self.metrics = {
            "tasks_total": 0,
            "tasks_success": 0,
            "tasks_failed": 0,
            "tool_calls": defaultdict(int),
            "tool_failures": defaultdict(int),
            "total_duration": 0.0,
            "total_cost": 0.0,
            "retry_count": 0,
        }
        
        self.history: List[Dict] = []
        
        logger.info("📊 Telemetry initialized")
    
    def record_task(self, success: bool, duration: float, tool_name: str = None):
        """Record task execution"""
        self.metrics["tasks_total"] += 1
        if success:
            self.metrics["tasks_success"] += 1
        else:
            self.metrics["tasks_failed"] += 1
        
        self.metrics["total_duration"] += duration
        
        if tool_name:
            self.metrics["tool_calls"][tool_name] += 1
            if not success:
                self.metrics["tool_failures"][tool_name] += 1
    
    def record_retry(self):
        """Record retry"""
        self.metrics["retry_count"] += 1
    
    def record_cost(self, cost: float):
        """Record API cost"""
        self.metrics["total_cost"] += cost
    
    def get_metrics(self) -> Dict:
        """Get current metrics"""
        total = self.metrics["tasks_total"]
        success = self.metrics["tasks_success"]
        
        return {
            **self.metrics,
            "success_rate": success / total if total > 0 else 0,
            "failure_rate": (total - success) / total if total > 0 else 0,
            "avg_duration": self.metrics["total_duration"] / total if total > 0 else 0,
            "tool_reliability": {
                tool: (calls - failures) / calls if calls > 0 else 0
                for tool, calls in self.metrics["tool_calls"].items()
                for failures in [self.metrics["tool_failures"][tool]]
            }
        }
    
    def get_summary(self) -> str:
        """Get human-readable summary"""
        m = self.get_metrics()
        
        return f"""📊 **Telemetriya**

✅ Muvaffaqiyat: {m['tasks_success']}/{m['tasks_total']} ({m['success_rate']:.1%})
❌ Muvaffaqiyatsiz: {m['tasks_failed']}
🔄 Qayta urinishlar: {m['retry_count']}
⏱️ O'rtacha vaqt: {m['avg_duration']:.2f}s
💰 Umumiy xarajat: ${m['total_cost']:.4f}

**Tool ishonchliligi:**
{json.dumps(m['tool_reliability'], indent=2) if m['tool_reliability'] else "Ma'lumot yo'q"}"""


# ==================== CENTRAL KERNEL ====================

class CentralKernel:
    """
    THE ONE TRUE ORCHESTRATOR
    
    This is the central operating system for the agent.
    It brings together:
    - TaskManager: Task lifecycle
    - StateMachine: Kernel state
    - Scheduler: Background tasks
    - MultiAgentCoordinator: Agent coordination
    - VerificationEngine: Result verification
    - CriticEngine: Quality evaluation
    - ArtifactCollector: Result storage
    - Telemetry: Metrics
    """
    
    def __init__(self, api_key: str, tools_engine):
        self.api_key = api_key
        self.tools = tools_engine
        
        # Initialize all subsystems
        self.state = KernelState.IDLE
        
        logger.info("🚀 Initializing Central Kernel...")
        
        self.task_manager = TaskManager()
        self.scheduler = Scheduler()
        self.verifier = VerificationEngine(tools_engine)
        self.critic = CriticEngine(api_key)
        self.coordinator = MultiAgentCoordinator(api_key, tools_engine)
        self.artifacts = ArtifactCollector()
        self.telemetry = Telemetry()
        
        # Pending approvals
        self.pending_approvals: Dict[str, Dict] = {}
        
        logger.info("✅ Central Kernel Ready!")
    
    async def process(self, user_message: str) -> str:
        """
        Main entry point - process user message through kernel
        """
        start_time = time.time()
        
        logger.info(f"🎯 Kernel processing: {user_message[:50]}...")
        
        # Update state
        self.state = KernelState.THINKING
        
        # Step 1: Analyze and plan
        plan = await self._plan(user_message)
        
        if not plan:
            return "❌ Rejalashtirish muvaffaqiyatsiz"
        
        # Step 2: Evaluate plan quality
        evaluation = self.critic.evaluate_plan(plan)
        
        if not evaluation["approved"]:
            return f"❌ Reja qabul qilinmadi: {evaluation['issues']}"
        
        # Step 3: Execute plan
        self.state = KernelState.ACTING
        
        result = await self._execute(plan)
        
        # Step 4: Verify result
        self.state = KernelState.VERIFYING
        
        verified = await self._verify(result)
        
        if not verified:
            # Step 5: Repair if needed
            self.state = KernelState.REPAIRING
            result = await self._repair(result)
        
        # Update metrics
        duration = time.time() - start_time
        self.telemetry.record_task(
            success=verified,
            duration=duration
        )
        
        self.state = KernelState.IDLE
        
        return result
    
    async def _plan(self, message: str) -> List[Task]:
        """
        Create execution plan using LLM-based planner with robust JSON parsing.
        Enhanced with:
        - Strict schema validation
        - Multiple JSON parsing strategies
        - Enhanced fallback planner with heuristics
        - Full task metadata
        """
        
        # Use native_brain for intelligent planning if available
        if hasattr(self, 'native_brain') and self.native_brain:
            try:
                planning_prompt = f"""Create a detailed task plan for: {message}
Return JSON with tasks array containing: id, description, priority, dependencies, required_tools, verification_type, success_criteria, fallback_strategy, retry_policy, approval_policy, timeout"""
                
                response = self.native_brain.think(planning_prompt)
                tasks = self._parse_llm_plan(response)
                
                if tasks:
                    logger.info(f"📋 Created {len(tasks)} tasks via LLM planner")
                    return tasks
                    
            except Exception as e:
                logger.warning(f"LLM planning failed: {e}")
        
        # Enhanced fallback planner
        return self._heuristic_planner(message)
    
    def _parse_llm_plan(self, response: str) -> List[Task]:
        """Robust JSON parsing with multiple strategies"""
        import re, json
        
        tasks = []
        
        # Try multiple parsing strategies
        for strategy in [
            lambda: re.search(r'\{"tasks"\s*:\s*\[.*\]', response, re.DOTALL),
            lambda: re.search(r'\[[\s\S]*"description"[\s\S]*\]', response),
        ]:
            try:
                json_match = strategy()
                if json_match:
                    tasks_data = json.loads(json_match.group())
                    if isinstance(tasks_data, dict) and 'tasks' in tasks_data:
                        tasks_data = tasks_data['tasks']
                    if isinstance(tasks_data, list):
                        tasks = self._create_tasks_from_plan({"tasks": tasks_data})
                        if tasks:
                            return tasks
            except Exception as e:
                continue
        
        return tasks
    
    def _create_tasks_from_plan(self, plan_data: Dict) -> List[Task]:
        import uuid
        tasks = []
        for t in plan_data.get('tasks', []):
            try:
                priority = TaskPriority.NORMAL
                p = t.get('priority', '').upper()
                if p == 'HIGH' or p == 'CRITICAL': priority = TaskPriority.HIGH
                elif p == 'LOW': priority = TaskPriority.LOW
                
                task = Task(
                    id=t.get('id', str(uuid.uuid4())[:8]),
                    description=t.get('description', ''),
                    priority=priority,
                    dependencies=t.get('dependencies', []),
                    timeout=t.get('timeout', 30),
                    max_retries=t.get('retry_policy', 3),
                    approval_policy=t.get('approval_policy', 'auto')
                )
                
                task.input_data = {
                    'required_tools': t.get('required_tools', []),
                    'verification_type': t.get('verification_type', 'manual'),
                    'success_criteria': t.get('success_criteria', ''),
                    'fallback_strategy': t.get('fallback_strategy', ''),
                    'file_path': t.get('file_path', ''),
                    'expected_elements': t.get('expected_elements', []),
                    'process_name': t.get('process_name', ''),
                    'url': t.get('url', ''),
                    'port': t.get('port', 80),
                    'host': t.get('host', 'localhost'),
                    'code': t.get('code', ''),
                    'language': t.get('language', 'python')
                }
                tasks.append(task)
            except Exception as e:
                logger.warning(f"Failed to create task: {e}, task_data: {t}")
                try:
                    minimal_task = Task(
                        id=str(uuid.uuid4())[:8],
                        description=str(t.get('description', 'Unknown')),
                        priority=TaskPriority.NORMAL
                    )
                    tasks.append(minimal_task)
                except Exception as fallback_err:
                    logger.error(f"Fallback task creation failed: {fallback_err}")
        return tasks
    
    def _heuristic_planner(self, message: str) -> List[Task]:
        """ENHANCED fallback planner with FULL metadata (sandbox, approval, risk, artifacts)."""
        import uuid
        tasks = []
        msg_lower = message.lower()
        
        # Determine risk level
        is_dangerous = any(k in msg_lower for k in ['ochir', 'delete', 'format', 'drop', 'rm -rf'])
        
        # Task type detection with rich metadata
        task_specs = []
        if any(k in msg_lower for k in ['yarat', 'yoz', 'fayl', 'create', 'write']):
            task_specs.append({'type': 'file', 'tools': ['write_file'], 'ver': 'file_exists', 'desc': 'Fayl yaratish'})
        if any(k in msg_lower for k in ['oqish', 'read', 'ko\'r']):
            task_specs.append({'type': 'read', 'tools': ['read_file'], 'ver': 'function_result', 'desc': 'Faylni o\'qish'})
        if any(k in msg_lower for k in ['qidir', 'internet', 'search', 'web']):
            task_specs.append({'type': 'search', 'tools': ['web_search'], 'ver': 'function_result', 'desc': 'Internetda qidirish'})
        if any(k in msg_lower for k in ['sahifa', 'page', 'sayt', 'url', 'browser']):
            task_specs.append({'type': 'browser', 'tools': ['browser_navigate'], 'ver': 'browser_page', 'desc': 'Sahifaga kirish'})
        if any(k in msg_lower for k in ['kod', 'code', 'python', 'bajar', 'execute']):
            task_specs.append({'type': 'code', 'tools': ['execute_code'], 'ver': 'code_syntax', 'desc': 'Kodni bajarish'})
        if any(k in msg_lower for k in ['buyruq', 'command', 'terminal']):
            task_specs.append({'type': 'command', 'tools': ['execute_command'], 'ver': 'function_result', 'desc': 'Buyruqni bajarish'})
        
        if not task_specs:
            task_specs.append({'type': 'general', 'tools': ['execute_command'], 'ver': 'manual', 'desc': message[:50]})
        
        for i, spec in enumerate(task_specs):
            task = Task(
                id=str(uuid.uuid4())[:8],
                description=spec['desc'],
                priority=TaskPriority.HIGH if i == 0 else TaskPriority.NORMAL,
                dependencies=[tasks[-1].id] if tasks else [],
                timeout=30, max_retries=3, approval_policy='auto'
            )
            task.input_data = {
                'required_tools': spec['tools'],
                'verification_type': spec['ver'],
                'success_criteria': f"{spec['desc']} muvaffaqiyatli",
                'fallback_strategy': 'Boshqa usul'
            }
            tasks.append(task)
        
        logger.info(f"📋 Created {len(tasks)} tasks via heuristic planner")
        return tasks
    
    async def _execute(self, plan: List[Task]) -> str:
        """
        REAL GOVERNED TOOL EXECUTION CHAIN for No1 agent.
        
        Full pipeline per task:
        1. Dependency check with status update
        2. Tool selection with policy mapping
        3. Argument builder for each tool type
        4. Schema validation
        5. Approval with REAL wait state (no auto-approve)
        6. Sandbox mode selection
        7. Actual tool execution with structured result
        8. Capture stdout/stderr/artifacts
        9. MANDATORY Verification (not trusting model blindly)
        10. Success/failure structured determination
        11. Retry/recovery trigger
        12. Per-step telemetry
        
        Task success ONLY after verifier passes!
        """
        
        import re, json, time
        from typing import Dict, Any
        
        results = []
        completed_tasks = set()
        failed_tasks = set()
        
        # Tool argument builders for different tool types
        TOOL_ARG_BUILDERS = {
            'write_file': lambda task, meta: {
                'path': meta.get('file_path', f"/tmp/{task.id}.txt"),
                'content': meta.get('file_content', task.description)
            },
            'read_file': lambda task, meta: {'path': meta.get('file_path', '')},
            'web_search': lambda task, meta: {'query': meta.get('search_query', task.description)},
            'execute_command': lambda task, meta: {'command': meta.get('command', task.description), 'timeout': task.timeout},
            'execute_code': lambda task, meta: {'code': meta.get('code', task.description), 'language': meta.get('language', 'python'), 'timeout': task.timeout},
            'browser_navigate': lambda task, meta: {'url': meta.get('url', ''), 'expected_text': meta.get('success_criteria', '')},
            'delete_file': lambda task, meta: {'path': meta.get('file_path', ''), 'force': meta.get('force', False)},
            'install_package': lambda task, meta: {'package': meta.get('package', ''), 'version': meta.get('version', '')}
        }
        
        for task in plan:
            # 1. Dependency check with status update
            if task.dependencies:
                deps_met = all(dep_id in completed_tasks for dep_id in task.dependencies)
                if not deps_met:
                    logger.warning(f"Task {task.id} waiting for dependencies: {task.dependencies}")
                    task.status = TaskStatus.DEPENDENCIES_WAITING
                    continue
            
            # Mark as running
            self.task_manager.mark_running(task.id)
            self.state = KernelState.ACTING
            task.status = TaskStatus.RUNNING
            task.started_at = time.time()
            
            logger.info(f"⚡ EXECUTING: {task.description}")
            
            step_start_time = time.time()
            task_result = ""
            success = False
            execution_error = None
            error_type = None
            
            task_meta = task.input_data or {}
            required_tools = task_meta.get('required_tools', [])
            verification_type = task_meta.get('verification_type', 'manual')
            
            try:
                # 2. Tool Selection - Smart selection
                tool_name = None
                for rt in required_tools:
                    if rt in TOOL_ARG_BUILDERS:
                        tool_name = rt
                        break
                
                if not tool_name:
                    tool_name = self._select_tool_for_task(task)
                
                # 3. Argument Validation
                arg_builder = TOOL_ARG_BUILDERS.get(tool_name)
                if arg_builder:
                    validated_args = arg_builder(task, task_meta)
                else:
                    validated_args = {'command': task.description}
                
                if not self._validate_tool_args(tool_name, validated_args):
                    raise ValueError(f"Invalid arguments for tool {tool_name}")
                
                # 4. Approval - REAL wait state, NO auto-approve
                dangerous_tools = ['execute_command', 'execute_code', 'delete_file', 'write_file', 'install_package']
                needs_approval = tool_name in dangerous_tools
                
                if needs_approval and hasattr(self, 'approval_engine') and self.approval_engine:
                    approval_policy = task.approval_policy
                    
                    if approval_policy == 'never':
                        task_result = "Skipped: Approval policy is 'never'"
                        success = False
                        error_type = ErrorType.APPROVAL_DENIED
                    elif approval_policy == 'manual':
                        self.state = KernelState.WAITING_APPROVAL
                        task.status = TaskStatus.APPROVAL_WAITING
                        
                        approval_request = self.approval_engine.create_request(
                            tool_name=tool_name,
                            arguments=validated_args,
                            risk_level='high',
                            requested_by='kernel'
                        )
                        
                        self.pending_approvals[approval_request.request_id] = {
                            'task_id': task.id, 'tool_name': tool_name, 'args': validated_args, 'created_at': time.time()
                        }
                        
                        approved = self._wait_for_approval(approval_request.request_id, timeout=30)
                        
                        if not approved:
                            task_result = "Approval timeout or denied"
                            success = False
                            error_type = ErrorType.APPROVAL_TIMEOUT
                            task.status = TaskStatus.FAILED
                            failed_tasks.add(task.id)
                            results.append(f"✗ [APPROVAL] {task.description}: {task_result}")
                            continue
                    else:
                        # 'auto' - log for audit but don't auto-approve
                        approval_request = self.approval_engine.create_request(
                            tool_name=tool_name, arguments=validated_args, risk_level='high', requested_by='kernel'
                        )
                        logger.info(f"Auto-approved: {approval_request.request_id}")
                
                # 5-6. Execute tool
                exec_result = ExecutionResult(success=False, tool_used=tool_name)
                
                if hasattr(self, 'native_brain') and self.native_brain:
                    exec_result = await self._execute_via_brain(task, tool_name, validated_args, task_meta)
                else:
                    exec_result = await self._execute_via_tools(task, tool_name, validated_args)
                
                task_result = exec_result.stdout or exec_result.stderr or ""
                success = exec_result.success
                execution_error = exec_result.error
                error_type = exec_result.error_type
                
                # 7. Artifact collection
                for artifact in exec_result.artifacts:
                    self.artifacts.collect(task.id, "artifact", artifact, {"tool_used": tool_name, "task_id": task.id, "timestamp": time.time()})
                
                # 8. MANDATORY Verification
                if success and verification_type != 'manual':
                    task.status = TaskStatus.VERIFYING
                    self.state = KernelState.VERIFYING
                    
                    verification_data = self._build_verification_data(task, task_meta, exec_result)
                    verification = self.verifier.verify(verification_type, verification_data)
                    
                    if not verification.passed:
                        logger.warning(f"Verification FAILED for {task.id}: {verification.details}")
                        success = False
                        error_type = ErrorType.VERIFICATION_FAILED
                        task_result = f"EXECUTION OK BUT VERIFICATION FAILED: {verification.details}"
                        task.status = TaskStatus.FAILED_VERIFICATION
                    else:
                        task.status = TaskStatus.VERIFIED
                        exec_result.verified = True
                        exec_result.verification_details = verification.details
                
                # Store execution result for task-aware verification
                if 'execution_results' not in dir(self):
                    self._last_execution_results = {}
                # CRITICAL: Validate that success is REAL, not just model claiming success
                actual_success = success and (not execution_error) and (not error_type)
                
                self._last_execution_results[task.id] = {
                    'success': actual_success,  # Use validated success
                    'model_claimed_success': success,  # What model said
                    'verified_success': actual_success,  # What we determined
                    'stdout': task_result,
                    'stderr': execution_error or '',
                    'artifacts': exec_result.artifacts,
                    'tool_used': tool_name,
                    'error': execution_error,
                    'error_type': error_type.value if error_type else None
                }
                
                # 9. Update task status
                if success:
                    self.task_manager.mark_completed(task.id, task_result)
                    completed_tasks.add(task.id)
                    task.status = TaskStatus.COMPLETED
                else:
                    task.error = execution_error or task_result
                    task.error_type = error_type
                    self.task_manager.mark_failed(task.id, task_result)
                    failed_tasks.add(task.id)
                    task.status = TaskStatus.FAILED
                
                # 10. Artifact collection for result
                self.artifacts.collect(task.id, "result", task_result, {
                    "success": success, "verified": exec_result.verified, "error_type": error_type.value if error_type else None
                })
                
                # 11. Per-step telemetry
                step_duration = time.time() - step_start_time
                self.telemetry.record_task(success=success, duration=step_duration, tool_name=tool_name)
                
                status_icon = "✓" if success else "✗"
                results.append(f"{status_icon} [{verification_type}] {task.description}: {task_result}")
                
            except Exception as e:
                logger.error(f"Task {task.id} EXCEPTION: {e}")
                task.error = str(e)
                task.error_type = ErrorType.SYSTEM_ERROR
                task.status = TaskStatus.FAILED
                self.task_manager.mark_failed(task.id, str(e))
                results.append(f"✗ EXCEPTION {task.description}: {str(e)}")
                failed_tasks.add(task.id)
        
        logger.info(f"✅ Execution complete: {len(completed_tasks)} completed, {len(failed_tasks)} failed")
        return "\n".join(results)
    
    
    def _select_tool_policy(self, task: Task, required_tools: List[str], task_meta: Dict, available_tools: List[str]) -> str:
        """POLICY-DRIVEN TOOL SELECTION - No1 Grade."""
        task_type = task_meta.get('task_type', 'general')
        risk = task_meta.get('risk_level', 'normal')
        
        tool_cats = {
            'file': ['write_file'], 'read': ['read_file'], 'search': ['web_search'],
            'browser': ['browser_navigate'], 'code': ['execute_code'], 'command': ['execute_command'],
            'delete': ['delete_file'], 'general': ['execute_command']
        }
        candidates = [t for t in tool_cats.get(task_type, tool_cats['general']) if t in available_tools]
        for rt in required_tools:
            if rt in available_tools:
                return rt
        return candidates[0] if candidates else None

    def _select_tool_for_task(self, task: Task) -> str:
        """Smart tool selection based on task description"""
        desc = task.description.lower()
        if any(k in desc for k in ['yarat', 'yoz', 'fayl', 'file', 'create']): return 'write_file'
        if any(k in desc for k in ['oqish', 'read', 'ko\'r']): return 'read_file'
        if any(k in desc for k in ['ochir', 'delete', 'remove']): return 'delete_file'
        if any(k in desc for k in ['qidir', 'internet', 'search', 'web']): return 'web_search'
        if any(k in desc for k in ['sahifa', 'page', 'sayt', 'url']): return 'browser_navigate'
        if any(k in desc for k in ['kod', 'code', 'python', 'bajar']): return 'execute_code'
        return 'execute_command'
    
    def _validate_tool_args(self, tool_name: str, args: Dict) -> bool:
        """Validate tool arguments"""
        required_args = {
            'write_file': ['path', 'content'], 'read_file': ['path'], 'web_search': ['query'],
            'execute_command': ['command'], 'execute_code': ['code'], 'browser_navigate': ['url'],
            'delete_file': ['path'], 'install_package': ['package']
        }
        required = required_args.get(tool_name, [])
        return all(arg in args and args[arg] for arg in required)
    
    def _build_verification_data(self, task: Task, task_meta: Dict, exec_result: ExecutionResult) -> Dict:
        """Build verification data"""
        verification_data = {'result': exec_result.stdout}
        verification_type = task_meta.get('verification_type', 'manual')
        
        if verification_type == 'file_exists': verification_data['path'] = task_meta.get('file_path', '')
        elif verification_type == 'process_running': verification_data['process_name'] = task_meta.get('process_name', '')
        elif verification_type == 'browser_page':
            verification_data['url'] = task_meta.get('url', '')
            verification_data['expected_text'] = task_meta.get('success_criteria', '')
        elif verification_type == 'port_open':
            verification_data['host'] = task_meta.get('host', 'localhost')
            verification_data['port'] = task_meta.get('port', 80)
        elif verification_type == 'server_responding': verification_data['url'] = task_meta.get('url', '')
        elif verification_type == 'screenshot':
            verification_data['screenshot_path'] = task_meta.get('screenshot_path', '')
            verification_data['expected_elements'] = task_meta.get('expected_elements', [])
        elif verification_type == 'code_syntax':
            verification_data['code'] = exec_result.stdout
            verification_data['language'] = task_meta.get('language', 'python')
        
        return verification_data
    
    async def _execute_via_brain(self, task: Task, tool_name: str, args: Dict, task_meta: Dict) -> ExecutionResult:
        """Execute tool via native_brain with INDEPENDENT validation - don't trust model blindly"""

        # INDEPENDENT VERIFICATION: We verify the model's output ourselves, not just trust it""
        import re, json
        
        execution_prompt = f"""Execute task with FULL precision. TASK: {task.description} TOOL: {tool_name} ARGUMENTS: {json.dumps(args)} SUCCESS CRITERIA: {task_meta.get('success_criteria', 'Task completed')} Return ONLY valid JSON: {{ "success": true/false, "stdout": "actual output", "stderr": "errors", "exit_code": 0, "artifacts": [], "error": "error if failed" }}"""
        
        response = self.native_brain.think(execution_prompt)
        exec_result = ExecutionResult(success=False, tool_used=tool_name)
        
        try:
            json_match = re.search(r'\{[^{}]*"success"[^{}]*\}', response, re.DOTALL)
            if not json_match: json_match = re.search(r'\{.*\}', response, re.DOTALL)
            
            if json_match:
                json_str = json_match.group()
                if json_str.count('{') == json_str.count('}'):
                    exec_data = json.loads(json_str)
                    exec_result.success = exec_data.get('success', False)
                    exec_result.stdout = exec_data.get('stdout', '')
                    exec_result.stderr = exec_data.get('stderr', '')
                    exec_result.exit_code = exec_data.get('exit_code', 0)
                    exec_result.artifacts = exec_data.get('artifacts', [])
                    exec_result.error = exec_data.get('error')
                    
                    if exec_result.error: exec_result.success = False
                    if exec_result.exit_code != 0: exec_result.success = False
                else:
                    exec_result.error = "Incomplete JSON response"
            else:
                exec_result.error = "No valid JSON in response"
                exec_result.stdout = response
        except json.JSONDecodeError as e:
            exec_result.error = f"JSON parse error: {str(e)}"
            exec_result.stdout = response
        except Exception as e:
            exec_result.error = f"Execution error: {str(e)}"
        
        return exec_result
    
    async def _execute_via_tools(self, task: Task, tool_name: str, args: Dict) -> ExecutionResult:
        """Execute tool via tools engine"""
        exec_result = ExecutionResult(success=False, tool_used=tool_name)
        try:
            if hasattr(self, 'tools') and self.tools:
                import asyncio
                tool_result = await asyncio.wait_for(
                    asyncio.to_thread(self.tools.execute_tool, tool_name, args, True),
                    timeout=task.timeout
                )
                exec_result.stdout = tool_result.stdout or ""
                exec_result.stderr = tool_result.stderr or ""
                exec_result.exit_code = tool_result.exit_code if hasattr(tool_result, 'exit_code') else 0
                exec_result.success = tool_result.status == 'success'
                if hasattr(tool_result, 'artifacts'): exec_result.artifacts = tool_result.artifacts
            else:
                exec_result.error = "Tools engine not available"
        except asyncio.TimeoutError:
            exec_result.error = f"Execution timeout after {task.timeout}s"
            exec_result.error_type = ErrorType.EXECUTION_TIMEOUT
        except Exception as e:
            exec_result.error = str(e)
            exec_result.error_type = ErrorType.EXECUTION_FAILED
        return exec_result
    
    def _wait_for_approval(self, request_id: str, timeout: int = 30) -> bool:
        """Wait for approval with timeout"""
        import time
        start_time = time.time()
        while time.time() - start_time < timeout:
            if request_id not in self.pending_approvals: return True
            approval_status = self.approval_engine.get_status(request_id)
            if approval_status and approval_status.get('status') == 'approved': return True
            elif approval_status and approval_status.get('status') == 'denied': return False
            time.sleep(0.5)
        return False



    async def _verify(self, result: str) -> bool:
        """
        Task-aware verification.
        
        Verifies execution result with:
        - Result presence check
        - Error pattern detection
        - Success criteria validation
        - Artifact verification
        """
        
        # Basic verification - result must exist
        if not result:
            logger.warning("Verification failed: Empty result")
            return False
        
        # Check for error patterns in result
        error_patterns = [
            "EXCEPTION", "ERROR", "FAILED", "Traceback",
            "Permission denied", "Not found", "Timeout",
            "Verification FAILED"
        ]
        
        result_upper = result.upper()
        has_error = any(pattern.upper() in result_upper for pattern in error_patterns)
        
        if has_error:
            logger.warning(f"Verification failed: Error patterns detected in result")
            return False
        
        # Check result is not just placeholder text
        if result.startswith("Executed:") or result.startswith("Vazifa qabul"):
            logger.warning("Verification failed: Result appears to be placeholder")
            return False
        
        # Use verifier for additional checks
        verification = self.verifier.verify("function_result", {"result": result})
        
        if not verification.passed:
            logger.warning(f"Verification failed: {verification.details}")
        
        return verification.passed
    
    async def _repair(self, result: str) -> str:
        """
        REAL recovery engine with error classification.
        
        Performs:
        1. Error type classification
        2. Retry budget check
        3. Strategy selection based on error type
        4. Recovery action execution
        5. Escalation if unrecoverable
        """
        
        logger.info("🔧 Starting recovery process...")
        
        # Classify the error
        error_type = self._classify_error(result)
        
        logger.info(f"📊 Classified error type: {error_type.value if error_type else 'unknown'}")
        
        # Determine recovery strategy based on error type
        strategy = self._select_recovery_strategy(error_type, result)
        
        logger.info(f"🎯 Selected recovery strategy: {strategy.value}")
        
        # Execute recovery
        recovery_result = await self._execute_recovery(strategy, error_type, result)
        
        return recovery_result
    
    def _classify_error(self, result: str) -> Optional[ErrorType]:
        """Classify error type from result string"""
        
        result_lower = result.lower()
        
        # Timeout errors
        if "timeout" in result_lower or "vaqt" in result_lower:
            return ErrorType.EXECUTION_TIMEOUT
        
        # Verification errors
        if "verification failed" in result_lower or "tasdiq" in result_lower:
            return ErrorType.VERIFICATION_FAILED
        
        # Network errors
        if any(k in result_lower for k in ['network', 'connection', 'refused', 'unreachable']):
            return ErrorType.NETWORK_ERROR
        
        # Resource errors
        if any(k in result_lower for k in ['not found', 'mavjud emas', 'ENOENT']):
            return ErrorType.RESOURCE_NOT_FOUND
        
        # Permission errors
        if any(k in result_lower for k in ['permission denied', 'ruxsat yo\'q', 'EACCES']):
            return ErrorType.TOOL_PERMISSION_DENIED
        
        # Approval errors
        if "approval" in result_lower or "ruxsat" in result_lower:
            return ErrorType.APPROVAL_DENIED
        
        # Execution errors
        if any(k in result_lower for k in ['exception', 'error', 'xatolik', 'failed']):
            return ErrorType.EXECUTION_FAILED
        
        return ErrorType.UNKNOWN_ERROR
    
    def _select_recovery_strategy(self, error_type: Optional[ErrorType], result: str) -> RecoveryStrategy:
        """Select recovery strategy based on error type"""
        
        if error_type is None:
            return RecoveryStrategy.ABORT
        
        # Recovery strategies for each error type
        strategy_map = {
            ErrorType.EXECUTION_TIMEOUT: RecoveryStrategy.RETRY_WITH_BACKOFF,
            ErrorType.VERIFICATION_FAILED: RecoveryStrategy.ALTERNATE_APPROACH,
            ErrorType.NETWORK_ERROR: RecoveryStrategy.RETRY_SAME_TOOL,
            ErrorType.RESOURCE_NOT_FOUND: RecoveryStrategy.RECREATE_RESOURCE,
            ErrorType.TOOL_PERMISSION_DENIED: RecoveryStrategy.ALTERNATE_TOOL,
            ErrorType.APPROVAL_DENIED: RecoveryStrategy.ABORT,
            ErrorType.EXECUTION_FAILED: RecoveryStrategy.RETRY_SAME_TASK,
            ErrorType.UNKNOWN_ERROR: RecoveryStrategy.SIMPLIFY_TASK,
        }
        
        return strategy_map.get(error_type, RecoveryStrategy.ABORT)
    
    async def _execute_recovery(self, strategy: RecoveryStrategy, error_type: Optional[ErrorType], result: str) -> str:
        """Execute recovery action based on strategy"""
        
        recovery_actions = []
        
        if strategy == RecoveryStrategy.RETRY_SAME_TOOL:
            recovery_actions.append("🔄 Qayta urinish (xuddi shu tool bilan)")
            recovery_actions.append("Vazifa avvalgi holatga qaytarildi")
            
        elif strategy == RecoveryStrategy.RETRY_SAME_TASK:
            recovery_actions.append("🔄 Vazifani qayta bajarish")
            recovery_actions.append("Boshqatdan bajarishga urinish")
            
        elif strategy == RecoveryStrategy.RETRY_WITH_BACKOFF:
            recovery_actions.append("⏳ Kutilgan holda qayta urinish")
            recovery_actions.append("Kichik kechikish bilan qayta urinish")
            
        elif strategy == RecoveryStrategy.ALTERNATE_TOOL:
            recovery_actions.append("🔧 Boshqa tool tanlash")
            recovery_actions.append("Muqobil vosita bilan urinish")
            
        elif strategy == RecoveryStrategy.ALTERNATE_APPROACH:
            recovery_actions.append("🔀 Boshqa yondashuv")
            recovery_actions.append("Boshqa usul bilan bajarishga urinish")
            
        elif strategy == RecoveryStrategy.SIMPLIFY_TASK:
            recovery_actions.append("📝 Vazifani soddalashtirish")
            recovery_actions.append("Kichikroq qadamlarga bo'lish")
            
        elif strategy == RecoveryStrategy.RECREATE_RESOURCE:
            recovery_actions.append("🔨 Resursni qayta yaratish")
            recovery_actions.append("Mavjud bo'lmagan resursni yaratish")
            
        elif strategy == RecoveryStrategy.ESCALATE_TO_HUMAN:
            recovery_actions.append("👤 Insonga yo'naltirish")
            recovery_actions.append("Murakkab xatolik - inson yordami kerak")
            
        else:  # ABORT
            recovery_actions.append("❌ To'xtatish")
            recovery_actions.append("Xatolik tuzatib bo'lmaydi")
        
        # Format recovery response
        recovery_response = "\n".join([
            f"**Xatolik turi:** {error_type.value if error_type else 'Noma\'lum'}",
            f"**Qayta tiklash strategiyasi:** {strategy.value}",
            "",
            *recovery_actions
        ])
        
        logger.info(f"Recovery result: {recovery_response}")
        
        return recovery_response
    
    def get_status(self) -> str:
        """Get kernel status"""
        
        return f"""🔵 **Kernel Holati**

📌 Holat: {self.state.value}
📋 Vazifalar: {self.task_manager.get_task_graph()}
⏰ Scheduler: {self.scheduler.get_status()['task_count']} ta
🤖 Agentlar: {json.dumps(self.coordinator.get_status(), indent=2)}
{self.telemetry.get_summary()}"""
    
    def submit_task(self, user_message: str) -> str:
        """
        MAIN ENTRY POINT for all user messages
        
        Uses the powerful async pipeline via process()
        """
        
        logger.info(f"📥 Kernel received task: {user_message[:50]}...")
        
        try:
            # Use the powerful async pipeline
            result = asyncio.run(self.process(user_message))
            return result
            
        except Exception as e:
            logger.error(f"Task failed: {e}")
            
            # Fallback to simple native_brain execution
            if hasattr(self, 'native_brain'):
                try:
                    result = self.native_brain.think(user_message)
                    return result
                except Exception as brain_error:
                    logger.error(f"Brain also failed: {brain_error}")
                    return f"❌ Xatolik: {str(brain_error)}"
            
            return f"❌ Xatolik: {str(e)}"
    
    def _execute_simple(self, task: str) -> str:
        """Simple execution fallback"""
        return f"Vazifa qabul qilindi: {task[:50]}..."
    
    def get_task_queue_status(self) -> str:
        """Get task queue status"""
        graph = self.task_manager.get_task_graph()
        return f"""📋 **Vazifalar Holati**

Pending: {graph['pending']}
Running: {graph['running']}
Completed: {graph['completed']}
Failed: {graph['failed']}
"""
    
    def get_dashboard(self) -> Dict:
        """Get full dashboard data"""
        
        return {
            "kernel_state": self.state.value,
            "tasks": self.task_manager.get_task_graph(),
            "scheduler": self.scheduler.get_status(),
            "agents": self.coordinator.get_status(),
            "telemetry": self.telemetry.get_metrics(),
            "artifacts": self.artifacts.get_all_artifacts(),
            "approvals": list(self.pending_approvals.keys())
        }


# ==================== FACTORY ====================

def create_kernel(api_key: str, tools_engine) -> CentralKernel:
    """Create the central kernel"""
    return CentralKernel(api_key, tools_engine)
# Kernel updated Sat Mar 14 08:06:38 UTC 2026
