"""
OmniAgent X - Autonomous Engine (REFACTORED)
=============================================
Real autonomous agent with proper planning

REFACTORED:
- Real planner with goal, subtasks, dependency graph
- Step states: pending, running, succeeded, failed, retried, blocked
- Tool selection via registry (not LLM guess)
- Replanning when current plan invalid
- Task journal with full history
"""
import os
import json
import logging
import time
from typing import List, Dict, Optional, Set, Any
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field
from collections import defaultdict

# NEW: Use new OpenAI SDK
from openai import OpenAI
from config import settings

logger = logging.getLogger(__name__)


# ==================== ENUMS & DATA CLASSES ====================

class TaskState(Enum):
    """Task step states"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    RETRIED = "retried"
    BLOCKED = "blocked"
    SKIPPED = "skipped"


class TaskPriority(Enum):
    """Task priority levels"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class SubTask:
    """Individual task step"""
    id: str
    description: str
    tool_name: str
    arguments: Dict[str, Any]
    dependencies: List[str] = field(default_factory=list)
    state: TaskState = TaskState.PENDING
    result: Any = None
    error: str = None
    attempts: int = 0
    max_attempts: int = 3
    success_criteria: str = ""
    rollback_point: str = ""
    
    def can_run(self, completed: Set[str]) -> bool:
        """Check if all dependencies are satisfied"""
        return all(dep_id in completed for dep_id in self.dependencies)


@dataclass
class ExecutionResult:
    """Result of task execution"""
    success: bool
    output: Any
    error: str = None
    duration: float = 0.0
    artifacts: List[str] = field(default_factory=list)


@dataclass
class TaskJournal:
    """Complete task execution journal"""
    task_id: str
    goal: str
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    subtasks: List[SubTask] = field(default_factory=list)
    completed_ids: Set[str] = field(default_factory=set)
    failed_ids: Set[str] = field(default_factory=set)
    replanning_count: int = 0
    final_result: str = ""
    termination_reason: str = ""
    
    def to_dict(self) -> Dict:
        return {
            "task_id": self.task_id,
            "goal": self.goal,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "subtasks": [
                {
                    "id": st.id,
                    "description": st.description,
                    "tool": st.tool_name,
                    "state": st.state.value,
                    "attempts": st.attempts,
                    "result": str(st.result)[:200] if st.result else None,
                    "error": st.error
                }
                for st in self.subtasks
            ],
            "completed": list(self.completed_ids),
            "failed": list(self.failed_ids),
            "replanning_count": self.replanning_count,
            "final_result": self.final_result,
            "termination_reason": self.termination_reason
        }


# ==================== TOOL REGISTRY ====================

class ToolRegistry:
    """
    Registry for available tools - replaces LLM guessing
    """
    
    def __init__(self):
        self.tools: Dict[str, Dict] = {}
        self._register_default_tools()
    
    def _register_default_tools(self):
        """Register default tools with schemas"""
        self.register(
            name="web_search",
            description="Search the web for information",
            args_schema={
                "query": {"type": "string", "required": True, "description": "Search query"}
            },
            timeout=30,
            side_effect_level="safe",
            approval_level="auto"
        )
        
        self.register(
            name="read_file",
            description="Read content from a file",
            args_schema={
                "path": {"type": "string", "required": True, "description": "File path"}
            },
            timeout=10,
            side_effect_level="safe",
            approval_level="auto"
        )
        
        self.register(
            name="write_file",
            description="Write content to a file",
            args_schema={
                "path": {"type": "string", "required": True, "description": "File path"},
                "content": {"type": "string", "required": True, "description": "File content"}
            },
            timeout=30,
            side_effect_level="medium",
            approval_level="confirm"
        )
        
        self.register(
            name="execute_command",
            description="Execute a terminal command",
            args_schema={
                "command": {"type": "string", "required": True, "description": "Command to execute"}
            },
            timeout=60,
            side_effect_level="high",
            approval_level="confirm"
        )
        
        self.register(
            name="execute_code",
            description="Execute Python or JavaScript code",
            args_schema={
                "code": {"type": "string", "required": True, "description": "Code to execute"},
                "language": {"type": "string", "required": False, "default": "python", "description": "Language"}
            },
            timeout=60,
            side_effect_level="medium",
            approval_level="confirm"
        )
        
        self.register(
            name="take_screenshot",
            description="Take a screenshot of the screen",
            args_schema={},
            timeout=10,
            side_effect_level="safe",
            approval_level="auto"
        )
        
        self.register(
            name="get_system_info",
            description="Get system information",
            args_schema={},
            timeout=10,
            side_effect_level="safe",
            approval_level="auto"
        )
        
        self.register(
            name="think",
            description="Just think about something (no action)",
            args_schema={
                "question": {"type": "string", "required": True, "description": "Question to think about"}
            },
            timeout=30,
            side_effect_level="safe",
            approval_level="auto"
        )
    
    def register(self, name: str, description: str, args_schema: Dict,
                 timeout: int = 30, side_effect_level: str = "safe",
                 approval_level: str = "auto"):
        """Register a new tool"""
        self.tools[name] = {
            "name": name,
            "description": description,
            "args_schema": args_schema,
            "timeout": timeout,
            "side_effect_level": side_effect_level,  # safe, medium, high
            "approval_level": approval_level  # auto, confirm, blocked
        }
    
    def get_tool(self, name: str) -> Optional[Dict]:
        """Get tool by name"""
        return self.tools.get(name)
    
    def validate_args(self, tool_name: str, args: Dict) -> tuple[bool, str]:
        """Validate tool arguments against schema"""
        tool = self.get_tool(tool_name)
        if not tool:
            return False, f"Tool '{tool_name}' not found"
        
        schema = tool["args_schema"]
        
        # Check required args
        for arg_name, arg_spec in schema.items():
            if arg_spec.get("required", False) and arg_name not in args:
                return False, f"Missing required argument: {arg_name}"
        
        # Check types
        for arg_name, arg_value in args.items():
            if arg_name in schema:
                expected_type = schema[arg_name].get("type")
                if expected_type and not isinstance(arg_value, eval(expected_type) if expected_type != "string" else str):
                    # Type coercion
                    pass
        
        return True, "OK"
    
    def list_tools(self) -> List[str]:
        """List all available tools"""
        return list(self.tools.keys())


# ==================== DEPENDENCY GRAPH ====================

class DependencyGraph:
    """
    Task dependency graph for parallel execution planning
    """
    
    def __init__(self):
        self.nodes: Dict[str, SubTask] = {}
        self.edges: Dict[str, List[str]] = defaultdict(list)
        self.reverse_edges: Dict[str, List[str]] = defaultdict(list)
    
    def add_task(self, task: SubTask):
        """Add a task to the graph"""
        self.nodes[task.id] = task
        for dep_id in task.dependencies:
            self.edges[dep_id].append(task.id)
            self.reverse_edges[task.id].append(dep_id)
    
    def get_executable_tasks(self, completed: Set[str]) -> List[SubTask]:
        """Get tasks that can be executed (all dependencies met)"""
        executable = []
        for task_id, task in self.nodes.items():
            if task.state == TaskState.PENDING and task.can_run(completed):
                executable.append(task)
        return executable
    
    def get_execution_order(self) -> List[List[SubTask]]:
        """
        Get execution order as list of parallel batches
        Returns: List of task batches that can run in parallel
        """
        batches = []
        completed: Set[str] = set()
        remaining = set(self.nodes.keys())
        
        while remaining:
            # Find all tasks that can run now
            batch = self.get_executable_tasks(completed)
            
            if not batch:
                # Deadlock - remaining tasks have unmet dependencies
                break
            
            batches.append(batch)
            
            # Mark as completed (we'll update actual state during execution)
            for task in batch:
                completed.add(task.id)
                remaining.discard(task.id)
        
        return batches
    
    def mark_completed(self, task_id: str):
        """Mark task as completed"""
        if task_id in self.nodes:
            self.nodes[task_id].state = TaskState.SUCCEEDED
    
    def mark_failed(self, task_id: str, error: str):
        """Mark task as failed"""
        if task_id in self.nodes:
            self.nodes[task_id].state = TaskState.FAILED
            self.nodes[task_id].error = error
    
    def is_valid(self) -> tuple[bool, str]:
        """Check if graph has cycles"""
        # Simple cycle detection
        visited = set()
        rec_stack = set()
        
        def has_cycle(node_id: str) -> bool:
            visited.add(node_id)
            rec_stack.add(node_id)
            
            for neighbor in self.edges.get(node_id, []):
                if neighbor not in visited:
                    if has_cycle(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True
            
            rec_stack.remove(node_id)
            return False
        
        for node in self.nodes:
            if node not in visited:
                if has_cycle(node):
                    return False, "Cycle detected in dependency graph"
        
        return True, "OK"


# ==================== REAL PLANNER ====================

class RealPlanner:
    """
    Real planner that creates structured plans
    """
    
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)
    
    def create_plan(self, goal: str, context: str = "") -> List[SubTask]:
        """
        Create a detailed plan with:
        - Goal definition
        - Subtasks with dependencies
        - Success criteria
        - Rollback points
        """
        context_str = f"\n\nContext:\n{context}" if context else ""
        
        prompt = f"""You are a task planner. Create a detailed execution plan for this goal:

GOAL: {goal}{context_str}

Create a JSON plan with this structure:
{{
    "goal": "clear goal statement",
    "subtasks": [
        {{
            "id": "step_1",
            "description": "what this step does",
            "tool": "tool_name from registry",
            "args": {{"arg1": "value1"}},
            "dependencies": [],
            "success_criteria": "how to know this succeeded",
            "rollback_point": "what to save before this step"
        }},
        {{
            "id": "step_2", 
            "description": "next step",
            "tool": "tool_name",
            "args": {{}},
            "dependencies": ["step_1"],
            "success_criteria": "...",
            "rollback_point": "..."
        }}
    ]
}}

Available tools: web_search, read_file, write_file, execute_command, execute_code, take_screenshot, get_system_info, think

Return ONLY valid JSON:"""

        try:
            response = self.client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "You are a structured task planner. Return valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=2000
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # Parse JSON
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0]
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0]
            
            plan_data = json.loads(result_text)
            
            # Convert to SubTask objects
            subtasks = []
            for st_data in plan_data.get("subtasks", []):
                task = SubTask(
                    id=st_data.get("id", f"task_{len(subtasks)}"),
                    description=st_data.get("description", ""),
                    tool_name=st_data.get("tool", "think"),
                    arguments=st_data.get("args", {}),
                    dependencies=st_data.get("dependencies", []),
                    success_criteria=st_data.get("success_criteria", ""),
                    rollback_point=st_data.get("rollback_point", "")
                )
                subtasks.append(task)
            
            logger.info(f"📋 Created plan with {len(subtasks)} subtasks")
            return subtasks
            
        except Exception as e:
            logger.error(f"Planning error: {e}")
            # Fallback: single task
            return [SubTask(
                id="task_1",
                description=goal,
                tool_name="think",
                arguments={"question": goal}
            )]
    
    def validate_plan(self, subtasks: List[SubTask]) -> tuple[bool, str]:
        """Validate plan structure"""
        if not subtasks:
            return False, "Empty plan"
        
        # Check for circular dependencies
        graph = DependencyGraph()
        for task in subtasks:
            graph.add_task(task)
        
        return graph.is_valid()
    
    def should_replan(self, journal: TaskJournal, error: str) -> bool:
        """
        Determine if we need to replan based on failures
        """
        # If too many failures, replan
        failure_rate = len(journal.failed_ids) / max(len(journal.subtasks), 1)
        
        if failure_rate > 0.5:
            return True, "Too many failures"
        
        if journal.replanning_count >= 3:
            return True, "Max replanning reached"
        
        return False, ""


# ==================== MAIN AUTONOMOUS ENGINE ====================

class AutonomousEngine:
    """
    DEPRECATED: This class is now integrated into kernel.py
    Use CentralKernel instead for all orchestration needs.
    All functionality has been moved to kernel for unified architecture.
    """
    # This class is kept for backward compatibility only
    """
    REFACTORED: Full autonomous engine with real planning
    
    Features:
    - Real planner with dependency graph
    - Tool registry (not LLM guess)
    - Task states with proper tracking
    - Replanning capability
    - Full task journal
    """
    
    def __init__(self, tools_engine, brain, learning_engine, api_key: str):
        self.tools = tools_engine
        self.brain = brain
        self.learning = learning_engine
        
        # Core components
        self.tool_registry = ToolRegistry()
        self.planner = RealPlanner(api_key)
        
        # Settings
        self.auto_execute = True
        self.max_iterations = 10
        self.confidence_threshold = 0.7
        
        # Current task
        self.current_journal: Optional[TaskJournal] = None
        
        logger.info("🤖 Autonomous Engine initialized (REFACTORED)")
    
    def execute_task(self, task: str, auto: bool = True) -> str:
        """
        Execute task with full planning and tracking
        """
        start_time = time.time()
        
        if not (auto and self.auto_execute):
            return self.brain.think(task)
        
        # Create journal
        task_id = f"task_{int(time.time())}"
        self.current_journal = TaskJournal(
            task_id=task_id,
            goal=task
        )
        
        # Plan the task
        logger.info(f"📋 Planning: {task[:50]}...")
        subtasks = self.planner.create_plan(task)
        
        if not subtasks:
            return "❌ Rejalashuv muvaffaqiyatsiz"
        
        # Validate plan
        valid, msg = self.planner.validate_plan(subtasks)
        if not valid:
            logger.warning(f"Plan validation failed: {msg}")
            # Try with simpler plan
            subtasks = [SubTask(id="task_1", description=task, tool_name="think", arguments={"question": task})]
        
        self.current_journal.subtasks = subtasks
        
        # Execute tasks
        result = self._execute_plan(subtasks)
        
        # Finalize
        self.current_journal.end_time = time.time()
        self.current_journal.final_result = result
        
        # Save to learning
        if self.current_journal.failed_ids:
            self.learning.learn_from_error(task, f"Failed: {self.current_journal.failed_ids}")
        else:
            self.learning.learn_from_success(task, "All tasks completed")
        
        duration = time.time() - start_time
        
        return self._format_result(result, duration)
    
    def _execute_plan(self, subtasks: List[SubTask]) -> str:
        """Execute all subtasks with dependency tracking"""
        
        # Build dependency graph
        graph = DependencyGraph()
        for task in subtasks:
            graph.add_task(task)
        
        # Get execution order
        execution_order = graph.get_execution_order()
        
        completed: Set[str] = set()
        
        for batch_idx, batch in enumerate(execution_order):
            logger.info(f"  📦 Batch {batch_idx + 1}/{len(execution_order)}: {len(batch)} tasks")
            
            # Execute each task in batch (can be parallel, but we do sequential)
            for task in batch:
                result = self._execute_subtask(task)
                
                # Update journal
                self.current_journal.subtasks = subtasks
                
                if result.success:
                    completed.add(task.id)
                    self.current_journal.completed_ids.add(task.id)
                    graph.mark_completed(task.id)
                else:
                    self.current_journal.failed_ids.add(task.id)
                    graph.mark_failed(task.id, result.error)
                    
                    # Check if we should replan
                    should_replan, reason = self.planner.should_replan(
                        self.current_journal, result.error
                    )
                    
                    if should_replan:
                        logger.warning(f"  🔄 Replanning: {reason}")
                        self.current_journal.replanning_count += 1
                        
                        if self.current_journal.replanning_count < self.max_iterations:
                            # Try to create new plan
                            new_tasks = self.planner.create_plan(
                                self.current_journal.goal,
                                f"Previous plan failed. Error: {result.error}"
                            )
                            if new_tasks:
                                # Add new tasks to graph
                                for nt in new_tasks:
                                    if nt.id not in completed:
                                        graph.add_task(nt)
                                        subtasks.append(nt)
                                continue
                    
                    # Max iterations reached
                    self.current_journal.termination_reason = reason
                    return f"❌ To'xtatildi: {reason}"
        
        return "✅ Barcha qadamlar bajarildi"
    
    def _execute_subtask(self, task: SubTask) -> ExecutionResult:
        """Execute a single subtask"""
        start_time = time.time()
        
        task.state = TaskState.RUNNING
        task.attempts += 1
        
        logger.info(f"    ▶ {task.id}: {task.description[:40]}...")
        
        # Validate tool exists
        tool_def = self.tool_registry.get_tool(task.tool_name)
        if not tool_def:
            return ExecutionResult(
                success=False,
                error=f"Tool '{task.tool_name}' not found in registry",
                duration=time.time() - start_time
            )
        
        # Validate args
        valid, msg = self.tool_registry.validate_args(task.tool_name, task.arguments)
        if not valid:
            return ExecutionResult(
                success=False,
                error=f"Invalid args: {msg}",
                duration=time.time() - start_time
            )
        
        # Execute via tools engine
        try:
            result = self._call_tool(task.tool_name, task.arguments)
            
            task.state = TaskState.SUCCEEDED
            task.result = result
            
            return ExecutionResult(
                success=True,
                output=result,
                duration=time.time() - start_time
            )
            
        except Exception as e:
            task.state = TaskState.FAILED
            task.error = str(e)
            
            # Retry if attempts remaining
            if task.attempts < task.max_attempts:
                task.state = TaskState.RETRIED
                logger.warning(f"    ⚠️ Retry {task.attempts}/{task.max_attempts}")
            
            return ExecutionResult(
                success=False,
                error=str(e),
                duration=time.time() - start_time
            )
    
    def _call_tool(self, tool_name: str, args: Dict) -> Any:
        """Call tool via tools engine"""
        tool_map = {
            "think": lambda: self.brain.think(args.get("question", "")),
            "write_file": lambda: self.tools.write_file(args.get("path", ""), args.get("content", "")),
            "read_file": lambda: self.tools.read_file(args.get("path", "")),
            "web_search": lambda: self.tools.web_search(args.get("query", "")),
            "execute_command": lambda: self.tools.execute_command(args.get("command", "")),
            "execute_code": lambda: self.tools.execute_code(args.get("code", "")),
            "take_screenshot": lambda: self.tools.take_screenshot(),
            "get_system_info": lambda: self.tools.get_system_info(),
        }
        
        if tool_name in tool_map:
            return tool_map[tool_name]()
        
        return f"Tool '{tool_name}' not implemented"
    
    def _format_result(self, result: str, duration: float) -> str:
        """Format execution result"""
        journal = self.current_journal
        
        response = f"""🤖 **Avtonom Vazifa Natijasi**

🎯 **Maqsad:** {journal.goal}

⏱️ **Vaqt:** {duration:.2f} soniya
📊 **Qadamlar:** {len(journal.subtasks)} ta
✅ **Muvaffaqiyatli:** {len(journal.completed_ids)} ta
❌ **Muvaffaqiyatsiz:** {len(journal.failed_ids)} ta

---

**Bajarilgan qadamlar:**\n"""
        
        for task in journal.subtasks:
            status = {
                TaskState.SUCCEEDED: "✅",
                TaskState.FAILED: "❌",
                TaskState.RUNNING: "⏳",
                TaskState.PENDING: "⏸️",
                TaskState.RETRIED: "🔄",
                TaskState.BLOCKED: "🚫"
            }.get(task.state, "❓")
            
            response += f"\n{status} **{task.id}:** {task.description[:50]}...\n"
            
            if task.result:
                response += f"   └─ {str(task.result)[:100]}...\n"
            elif task.error:
                response += f"   └─ ❌ {task.error[:100]}...\n"
        
        if journal.failed_ids:
            response += f"\n⚠️ **Sabab:** {journal.termination_reason}"
        
        response += f"\n\n**Yakuniy natija:** {result}"
        
        return response
    
    def get_journal(self) -> Optional[Dict]:
        """Get current task journal"""
        if self.current_journal:
            return self.current_journal.to_dict()
        return None
    
    def set_auto_execute(self, enabled: bool):
        self.auto_execute = enabled
        return f"🤖 Auto-execute: {'on' if enabled else 'off'}"
    
    def get_status(self) -> str:
        return f"""🤖 **Autonomous Engine Status:**
- Auto-execute: {self.auto_execute}
- Max iterations: {self.max_iterations}
- Current task: {len(self.current_journal.subtasks) if self.current_journal else 0} steps
- Tools registered: {len(self.tool_registry.tools)}
"""


# Factory function
def create_autonomous_engine(tools_engine, brain, learning_engine, api_key: str):
    """Create autonomous engine"""
    return AutonomousEngine(tools_engine, brain, learning_engine, api_key)
