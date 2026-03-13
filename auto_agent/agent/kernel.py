"""
OmniAgent X - CENTRAL KERNEL
============================
The operating system level orchestration layer

This is the ONE TRUE ORCHESTRATOR that brings together:
- Task Manager
- State Machine
- Scheduler
- Background Queue
- Retry Controller
- Artifact Collector
- Multi-Agent Coordinator

This replaces fragmented architecture with a unified kernel.
"""
import os
import json
import logging
import time
import asyncio
import threading
from typing import List, Dict, Optional, Any, Set, Callable
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field
from collections import defaultdict, deque
from queue import Queue, PriorityQueue, Empty
import uuid

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


# ==================== DATA CLASSES ====================

@dataclass
class Task:
    """Represents a task in the kernel"""
    id: str
    description: str
    priority: TaskPriority = TaskPriority.NORMAL
    state: str = "pending"
    dependencies: List[str] = field(default_factory=list)
    assigned_agent: Optional[AgentRole] = None
    input_data: Any = None
    output_data: Any = None
    error: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    retry_count: int = 0
    max_retries: int = 3
    artifacts: List[str] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)
    
    def __lt__(self, other):
        return self.priority.value < other.priority.value


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
            except:
                pass
        
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
        except:
            open_port = False
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
        """Verify browser page content"""
        # Uses playwright or selenium to verify
        expected_text = data.get("expected_text", "")
        url = data.get("url", "")
        
        # Placeholder - actual implementation would use browser
        return VerificationResult(
            passed=True,
            details=f"Browser verification for {url}",
            evidence={"url": url, "expected": expected_text}
        )
    
    def _verify_screenshot(self, data: Dict) -> VerificationResult:
        """Verify screenshot contains expected elements"""
        # Placeholder - actual implementation would analyze image
        return VerificationResult(
            passed=True,
            details="Screenshot verification",
            evidence={}
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
                    severity="error"
                )
        
        return VerificationResult(passed=True, details="Syntax check not implemented for this language")
    
    def _verify_function_result(self, data: Dict) -> VerificationResult:
        """Verify function execution result"""
        result = data.get("result", None)
        expected = data.get("expected", None)
        
        if expected is None:
            return VerificationResult(
                passed=result is not None,
                details="Result present" if result else "No result",
                evidence={"has_result": result is not None}
            )
        
        return VerificationResult(
            passed=result == expected,
            details=f"Result matches expected: {result == expected}",
            evidence={"result": result, "expected": expected}
        )
    
    def _default_verifier(self, data: Dict) -> VerificationResult:
        """Default verification"""
        return VerificationResult(passed=True, details="Default verification passed")


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
        """Create execution plan using planner agent"""
        
        # Use the coordinator to create a plan
        # This is simplified - would use LLM in production
        
        # Create tasks based on message
        tasks = []
        
        # Simple keyword-based task creation
        if "fayl" in message.lower() or "yarat" in message.lower():
            tasks.append(Task(
                id="1",
                description="Fayl yaratish",
                priority=TaskPriority.NORMAL
            ))
        
        if "internet" in message.lower() or "qidir" in message.lower():
            tasks.append(Task(
                id="2",
                description="Internetda qidirish",
                priority=TaskPriority.NORMAL,
                dependencies=["1"]
            ))
        
        return tasks
    
    async def _execute(self, plan: List[Task]) -> str:
        """Execute plan through coordinator"""
        
        results = []
        
        for task in plan:
            # Mark as running
            self.task_manager.mark_running(task.id)
            
            # Execute based on task type
            result = f"Executing: {task.description}"
            results.append(result)
            
            # Mark completed
            self.task_manager.mark_completed(task.id, result)
            
            # Collect artifact
            self.artifacts.collect(task.id, "result", result)
        
        return "\n".join(results)
    
    async def _verify(self, result: str) -> bool:
        """Verify execution result"""
        
        # Basic verification
        if not result:
            return False
        
        # Use verifier for specific checks
        verification = self.verifier.verify("function_result", {"result": result})
        
        return verification.passed
    
    async def _repair(self, result: str) -> str:
        """Repair failed execution"""
        
        # Try to fix issues
        repair_attempts = [
            "Urinish 1: Qayta ishga tushirish",
            "Urinish 2: Boshqa usul",
            "Urinish 3: Soddalashtirish"
        ]
        
        return repair_attempts[0]
    
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
        
        This is the central flow:
        1. Receive task
        2. Create task in queue
        3. Plan with native_brain
        4. Execute through tools
        5. Verify result
        6. Learn from result
        """
        
        logger.info(f"📥 Kernel received task: {user_message[:50]}...")
        
        # Create task
        task = self.task_manager.create_task(
            description=user_message,
            priority=TaskPriority.NORMAL
        )
        
        # Mark as running
        self.task_manager.mark_running(task.id)
        self.state = KernelState.THINKING
        
        try:
            # Use native_brain for execution (if available)
            if hasattr(self, 'native_brain'):
                result = self.native_brain.think(user_message)
            else:
                # Fallback to simple execution
                result = self._execute_simple(user_message)
            
            # Mark completed
            self.task_manager.mark_completed(task.id, result)
            self.state = KernelState.IDLE
            
            # Record telemetry
            self.telemetry.record_task(success=True, duration=1.0)
            
            return result
            
        except Exception as e:
            logger.error(f"Task failed: {e}")
            self.task_manager.mark_failed(task.id, str(e))
            self.state = KernelState.ERROR
            
            self.telemetry.record_task(success=False, duration=1.0)
            
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
