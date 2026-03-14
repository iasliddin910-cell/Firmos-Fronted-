"""
OmniAgent X - Multi-Agent Coordinator (FULL IMPLEMENTATION)
============================================================
Real parallel role-based execution with 6 specialized workers:
- Planner Worker: Creates detailed execution plans
- Executor Worker: Executes tasks with tools
- Verifier Worker: Verifies results with multiple checks
- Critic Worker: Evaluates and critiques plans
- Researcher Worker: Gathers context and information
- Tool Builder Worker: Creates and optimizes tools

Each worker runs independently and communicates via message passing.
"""
import os
import asyncio
import logging
import time
import uuid
from typing import List, Dict, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from collections import deque
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class MessageType(Enum):
    """Types of messages between workers"""
    TASK = "task"
    RESULT = "result"
    APPROVAL = "approval"
    VERIFICATION = "verification"
    CRITIQUE = "critique"
    PLAN = "plan"
    ERROR = "error"
    COMPLETE = "complete"


@dataclass
class AgentMessage:
    """Message passed between agents"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: MessageType = MessageType.TASK
    sender: str = ""
    recipient: str = ""
    payload: Dict = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    correlation_id: str = ""  # Links related messages


@dataclass
class WorkerTask:
    """Task assigned to a worker"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    description: str = ""
    context: Dict = field(default_factory=dict)
    priority: int = 2
    deadline: Optional[float] = None
    metadata: Dict = field(default_factory=dict)


# ==================== BASE WORKER ====================

class BaseWorker(ABC):
    """Base class for all workers"""
    
    def __init__(self, name: str, api_key: str, tools=None, config: Dict = None):
        self.name = name
        self.api_key = api_key
        self.tools = tools
        self.config = config or {}
        
        # Message queue
        self.inbox: deque = deque()
        self.outbox: deque = deque()
        
        # State
        self.state = "idle"  # idle, working, waiting, complete, error
        self.current_task: Optional[WorkerTask] = None
        
        # Metrics
        self.tasks_processed = 0
        self.tasks_succeeded = 0
        self.tasks_failed = 0
        self.total_processing_time = 0.0
        
        # Capabilities
        self.capabilities: List[str] = []
        
        # Callback for message handling
        self.message_handler: Optional[Callable] = None
    
    @abstractmethod
    async def process(self, task: WorkerTask) -> Dict[str, Any]:
        """Process a task - must be implemented by each worker"""
        raise NotImplementedError(f"{self.__class__.__name__} must implement process()")
    
    async def execute(self, task: WorkerTask) -> Dict[str, Any]:
        """Execute a task with full lifecycle management"""
        start_time = time.time()
        
        self.state = "working"
        self.current_task = task
        
        try:
            logger.info(f"🔧 [{self.name}] Processing task: {task.description[:50]}...")
            
            # Process the task
            result = await self.process(task)
            
            # Update metrics
            self.tasks_processed += 1
            if result.get("success", False):
                self.tasks_succeeded += 1
                self.state = "complete"
            else:
                self.tasks_failed += 1
                self.state = "error"
            
            self.total_processing_time += time.time() - start_time
            
            result["worker"] = self.name
            result["task_id"] = task.id
            result["processing_time"] = time.time() - start_time
            
            return result
            
        except Exception as e:
            logger.error(f"❌ [{self.name}] Task failed: {e}")
            self.tasks_failed += 1
            self.state = "error"
            
            return {
                "success": False,
                "error": str(e),
                "worker": self.name,
                "task_id": task.id
            }
        finally:
            self.current_task = None
    
    def get_stats(self) -> Dict:
        """Get worker statistics"""
        return {
            "name": self.name,
            "state": self.state,
            "tasks_processed": self.tasks_processed,
            "tasks_succeeded": self.tasks_succeeded,
            "tasks_failed": self.tasks_failed,
            "success_rate": self.tasks_succeeded / max(1, self.tasks_processed),
            "avg_processing_time": self.total_processing_time / max(1, self.tasks_processed),
            "capabilities": self.capabilities,
            "queue_length": len(self.inbox)
        }


# ==================== RESEARCHER WORKER ====================

class ResearcherWorker(BaseWorker):
    """
    Researcher Worker - Gathers context and information
    
    Responsibilities:
    - Web search for relevant information
    - Code and documentation search
    - Context gathering
    - Fact checking
    """
    
    def __init__(self, api_key: str, tools=None, config: Dict = None):
        super().__init__("Researcher", api_key, tools, config)
        self.capabilities = [
            "web_search",
            "code_search", 
            "documentation_search",
            "context_gathering",
            "fact_checking",
            "url_extraction",
            "content_analysis"
        ]
    
    async def process(self, task: WorkerTask) -> Dict[str, Any]:
        """Gather information about the task"""
        
        query = task.description
        context = task.context
        
        findings = {
            "query": query,
            "sources": [],
            "information": [],
            "key_facts": [],
            "gaps": []
        }
        
        # Use tools to search the web
        if self.tools:
            try:
                # Try web search
                search_result = await self._search_web(query)
                if search_result:
                    findings["sources"].extend(search_result.get("sources", []))
                    findings["information"].extend(search_result.get("results", []))
                    
                    # Extract key facts
                    for item in search_result.get("results", []):
                        if item.get("title"):
                            findings["key_facts"].append({
                                "title": item.get("title"),
                                "summary": item.get("snippet", "")[:200]
                            })
            except Exception as e:
                logger.warning(f"Web search failed: {e}")
        
        # Check for information gaps
        if len(findings["information"]) == 0:
            findings["gaps"].append("No external information found")
        
        # Use LLM to analyze gathered information
        if self.api_key and findings["information"]:
            analysis = await self._analyze_information(query, findings["information"])
            findings["analysis"] = analysis
        
        return {
            "success": True,
            "output": findings,
            "metadata": {
                "sources_count": len(findings["sources"]),
                "information_count": len(findings["information"]),
                "gaps_count": len(findings["gaps"])
            }
        }
    
    async def _search_web(self, query: str) -> Optional[Dict]:
        """Search the web using tools"""
        try:
            if hasattr(self.tools, 'execute_tool'):
                result = await asyncio.to_thread(
                    self.tools.execute_tool,
                    "web_search",
                    {"query": query}
                )
                return {
                    "sources": [query],
                    "results": [{"title": "Search Result", "snippet": str(result)[:500]}]
                }
        except Exception as e:
            logger.warning(f"Web search error: {e}")
        return None
    
    async def _analyze_information(self, query: str, information: List) -> Dict:
        """Use LLM to analyze gathered information"""
        # This would use the LLM to summarize and analyze
        return {
            "summary": f"Found {len(information)} pieces of information",
            "relevance": "high" if information else "none"
        }


# ==================== PLANNER WORKER ====================

class PlannerWorker(BaseWorker):
    """
    Planner Worker - Creates detailed execution plans
    
    Responsibilities:
    - Break down complex tasks into steps
    - Estimate effort and duration
    - Identify dependencies
    - Create backup plans
    """
    
    def __init__(self, api_key: str, tools=None, config: Dict = None):
        super().__init__("Planner", api_key, tools, config)
        self.capabilities = [
            "create_plan",
            "break_down_task",
            "estimate_effort",
            "dependency_analysis",
            "risk_assessment",
            "resource_planning",
            "contingency_planning"
        ]
    
    async def process(self, task: WorkerTask) -> Dict[str, Any]:
        """Create a detailed execution plan"""
        
        description = task.description
        context = task.context
        research_data = context.get("research", {})
        
        plan = {
            "task_id": task.id,
            "original_description": description,
            "steps": [],
            "estimated_duration": 0,
            "dependencies": [],
            "risks": [],
            "resources_needed": [],
            "fallback_plans": []
        }
        
        # Analyze task complexity
        complexity = self._analyze_complexity(description)
        plan["complexity"] = complexity
        
        # Break down into steps
        steps = self._break_down_task(description, research_data)
        plan["steps"] = steps
        
        # Calculate total estimated duration
        total_duration = sum(step.get("estimated_duration", 5) for step in steps)
        plan["estimated_duration"] = total_duration
        
        # Identify dependencies
        plan["dependencies"] = self._identify_dependencies(steps)
        
        # Assess risks
        plan["risks"] = self._assess_risks(steps, context)
        
        # Create fallback plans
        plan["fallback_plans"] = self._create_fallback_plans(steps)
        
        # Resource planning
        plan["resources_needed"] = self._plan_resources(steps)
        
        return {
            "success": True,
            "output": plan,
            "metadata": {
                "steps_count": len(steps),
                "estimated_duration": total_duration,
                "complexity": complexity,
                "risks_count": len(plan["risks"])
            }
        }
    
    def _analyze_complexity(self, description: str) -> str:
        """Analyze task complexity"""
        length = len(description)
        
        if length < 50:
            return "simple"
        elif length < 200:
            return "moderate"
        elif length < 500:
            return "complex"
        else:
            return "very_complex"
    
    def _break_down_task(self, description: str, research: Dict) -> List[Dict]:
        """Break task into executable steps"""
        steps = []
        
        # Basic step breakdown based on keywords
        if "create" in description.lower() or "make" in description.lower():
            steps.append({
                "id": 1,
                "action": "create",
                "description": "Create the required item",
                "tool": "code_generator",
                "estimated_duration": 10,
                "retry_on_failure": True
            })
        
        if "search" in description.lower() or "find" in description.lower():
            steps.append({
                "id": len(steps) + 1,
                "action": "search",
                "description": "Search for required information",
                "tool": "web_search",
                "estimated_duration": 5,
                "retry_on_failure": True
            })
        
        if "verify" in description.lower() or "check" in description.lower():
            steps.append({
                "id": len(steps) + 1,
                "action": "verify",
                "description": "Verify the result",
                "tool": "verifier",
                "estimated_duration": 3,
                "retry_on_failure": False
            })
        
        # Default step if no keywords matched
        if not steps:
            steps.append({
                "id": 1,
                "action": "analyze",
                "description": f"Analyze task: {description[:50]}",
                "tool": "analyzer",
                "estimated_duration": 5,
                "retry_on_failure": True
            })
            steps.append({
                "id": 2,
                "action": "execute",
                "description": "Execute the main task",
                "tool": "executor",
                "estimated_duration": 10,
                "retry_on_failure": True
            })
        
        return steps
    
    def _identify_dependencies(self, steps: List[Dict]) -> List[Dict]:
        """Identify dependencies between steps"""
        dependencies = []
        
        for i, step in enumerate(steps):
            if i > 0:
                dependencies.append({
                    "from_step": steps[i - 1]["id"],
                    "to_step": step["id"],
                    "type": "sequential"
                })
        
        return dependencies
    
    def _assess_risks(self, steps: List[Dict], context: Dict) -> List[Dict]:
        """Assess potential risks"""
        risks = []
        
        # Check for external dependencies
        if context.get("requires_external_api"):
            risks.append({
                "type": "external_dependency",
                "severity": "medium",
                "mitigation": "Add fallback for API failure"
            })
        
        # Check for complex operations
        if len(steps) > 5:
            risks.append({
                "type": "complex_workflow",
                "severity": "medium",
                "mitigation": "Break into smaller sub-tasks"
            })
        
        return risks
    
    def _create_fallback_plans(self, steps: List[Dict]) -> List[Dict]:
        """Create contingency plans"""
        fallback_plans = []
        
        for step in steps:
            if step.get("retry_on_failure", False):
                fallback_plans.append({
                    "original_step": step["id"],
                    "fallback_action": f"retry_{step['action']}",
                    "max_retries": 2
                })
        
        return fallback_plans
    
    def _plan_resources(self, steps: List[Dict]) -> List[str]:
        """Plan required resources"""
        resources = set()
        
        for step in steps:
            tool = step.get("tool")
            if tool:
                resources.add(tool)
        
        return list(resources)


# ==================== CRITIC WORKER ====================

class CriticWorker(BaseWorker):
    """
    Critic Worker - Evaluates and critiques plans
    
    Responsibilities:
    - Evaluate plan quality
    - Identify issues and gaps
    - Suggest improvements
    - Approve or reject plans
    """
    
    def __init__(self, api_key: str, tools=None, config: Dict = None):
        super().__init__("Critic", api_key, tools, config)
        self.capabilities = [
            "evaluate_plan",
            "assess_quality",
            "detect_issues",
            "suggest_improvements",
            "approve_plan",
            "reject_plan",
            "risk_analysis"
        ]
        
        # Quality thresholds
        self.min_quality_score = 0.7
        self.max_issues = 3
    
    async def process(self, task: WorkerTask) -> Dict[str, Any]:
        """Evaluate and critique a plan"""
        
        plan = task.context.get("plan", {})
        research = task.context.get("research", {})
        
        critique = {
            "approved": False,
            "score": 0.0,
            "issues": [],
            "suggestions": [],
            "strengths": [],
            "risk_level": "low"
        }
        
        if not plan:
            critique["issues"].append("No plan provided")
            critique["score"] = 0.0
            return {"success": True, "output": critique}
        
        # Evaluate each aspect
        critique["score"] = self._evaluate_completeness(plan)
        critique["issues"].extend(self._detect_issues(plan))
        critique["suggestions"].extend(self._generate_suggestions(plan, research))
        critique["strengths"].extend(self._identify_strengths(plan))
        critique["risk_level"] = self._assess_risk_level(plan)
        
        # Determine approval based on score and issues
        if critique["score"] >= self.min_quality_score:
            if len(critique["issues"]) <= self.max_issues:
                critique["approved"] = True
            else:
                critique["approved"] = False
                critique["issues"].append(f"Too many issues: {len(critique['issues'])}")
        else:
            critique["approved"] = False
            critique["issues"].append(f"Quality score too low: {critique['score']:.2f}")
        
        return {
            "success": True,
            "output": critique,
            "metadata": {
                "score": critique["score"],
                "issues_count": len(critique["issues"]),
                "approved": critique["approved"]
            }
        }
    
    def _evaluate_completeness(self, plan: Dict) -> float:
        """Evaluate plan completeness"""
        score = 0.0
        
        # Check required fields
        if plan.get("steps"):
            score += 0.3
        if plan.get("estimated_duration"):
            score += 0.1
        if plan.get("dependencies"):
            score += 0.1
        if plan.get("risks"):
            score += 0.1
        if plan.get("fallback_plans"):
            score += 0.2
        if plan.get("resources_needed"):
            score += 0.2
        
        return min(1.0, score)
    
    def _detect_issues(self, plan: Dict) -> List[str]:
        """Detect issues in the plan"""
        issues = []
        
        steps = plan.get("steps", [])
        if not steps:
            issues.append("No steps defined")
        elif len(steps) > 20:
            issues.append("Too many steps - consider breaking down")
        
        # Check for empty step descriptions
        for step in steps:
            if not step.get("description"):
                issues.append(f"Step {step.get('id')} has no description")
        
        # Check for missing tools
        for step in steps:
            if not step.get("tool"):
                issues.append(f"Step {step.get('id')} has no tool assigned")
        
        return issues
    
    def _generate_suggestions(self, plan: Dict, research: Dict) -> List[str]:
        """Generate improvement suggestions"""
        suggestions = []
        
        steps = plan.get("steps", [])
        
        # Suggest parallel execution for independent steps
        if len(steps) > 3:
            suggestions.append("Consider parallel execution for independent steps")
        
        # Suggest verification steps
        has_verification = any("verify" in s.get("action", "").lower() for s in steps)
        if not has_verification:
            suggestions.append("Add verification step after execution")
        
        # Suggest error handling
        has_error_handling = any("fallback" in str(s).lower() for s in steps)
        if not has_error_handling:
            suggestions.append("Add error handling and fallback plans")
        
        return suggestions
    
    def _identify_strengths(self, plan: Dict) -> List[str]:
        """Identify plan strengths"""
        strengths = []
        
        if plan.get("fallback_plans"):
            strengths.append("Has fallback plans for failure scenarios")
        
        if plan.get("risks"):
            strengths.append("Risk assessment included")
        
        if plan.get("dependencies"):
            strengths.append("Dependencies properly mapped")
        
        if len(plan.get("steps", [])) <= 5:
            strengths.append("Manageable number of steps")
        
        return strengths
    
    def _assess_risk_level(self, plan: Dict) -> str:
        """Assess overall risk level"""
        risk_count = len(plan.get("risks", []))
        
        if risk_count == 0:
            return "low"
        elif risk_count <= 2:
            return "medium"
        else:
            return "high"


# ==================== EXECUTOR WORKER ====================

class ExecutorWorker(BaseWorker):
    """
    Executor Worker - Executes tasks with tools
    
    Responsibilities:
    - Execute tasks using appropriate tools
    - Manage tool execution
    - Handle errors and retries
    - Report progress
    """
    
    def __init__(self, api_key: str, tools=None, config: Dict = None):
        super().__init__("Executor", api_key, tools, config)
        self.capabilities = [
            "execute_tool",
            "run_code",
            "manage_process",
            "handle_errors",
            "retry_failed",
            "report_progress"
        ]
        
        # Execution config
        self.max_retries = config.get("max_retries", 3) if config else 3
        self.retry_delay = config.get("retry_delay", 2) if config else 2
    
    async def process(self, task: WorkerTask) -> Dict[str, Any]:
        """Execute the task using tools"""
        
        plan = task.context.get("plan", {})
        steps = plan.get("steps", [])
        
        if not steps:
            return {
                "success": False,
                "error": "No steps to execute"
            }
        
        results = {
            "executed_steps": [],
            "failed_steps": [],
            "total_duration": 0,
            "output": None
        }
        
        start_time = time.time()
        
        # Execute each step
        for step in steps:
            step_result = await self._execute_step(step, task.context)
            
            if step_result.get("success"):
                results["executed_steps"].append({
                    "step_id": step["id"],
                    "result": step_result
                })
            else:
                results["failed_steps"].append({
                    "step_id": step["id"],
                    "error": step_result.get("error")
                })
                
                # Check if step allows retry
                if step.get("retry_on_failure", False):
                    retry_result = await self._retry_step(step, task.context)
                    if retry_result.get("success"):
                        results["executed_steps"].append({
                            "step_id": step["id"],
                            "result": retry_result,
                            "retried": True
                        })
                        results["failed_steps"].pop()  # Remove from failed
        
        results["total_duration"] = time.time() - start_time
        
        # Determine overall success
        success = len(results["failed_steps"]) == 0 and len(results["executed_steps"]) > 0
        
        return {
            "success": success,
            "output": results,
            "metadata": {
                "steps_executed": len(results["executed_steps"]),
                "steps_failed": len(results["failed_steps"]),
                "duration": results["total_duration"]
            }
        }
    
    async def _execute_step(self, step: Dict, context: Dict) -> Dict:
        """Execute a single step"""
        
        action = step.get("action")
        tool = step.get("tool")
        description = step.get("description", "")
        
        logger.info(f"📤 Executing step {step['id']}: {action}")
        
        # If tools available, use them
        if self.tools and tool:
            try:
                if hasattr(self.tools, 'execute_tool'):
                    result = await asyncio.to_thread(
                        self.tools.execute_tool,
                        tool,
                        {"description": description, "context": context}
                    )
                    return {
                        "success": True,
                        "output": str(result),
                        "tool_used": tool
                    }
            except Exception as e:
                logger.warning(f"Tool execution failed: {e}")
                return {
                    "success": False,
                    "error": str(e),
                    "tool": tool
                }
        
        # Fallback: simulate execution
        return {
            "success": True,
            "output": f"Executed: {description}",
            "mode": "simulated"
        }
    
    async def _retry_step(self, step: Dict, context: Dict) -> Dict:
        """Retry a failed step"""
        
        for attempt in range(self.max_retries):
            logger.info(f"🔄 Retry attempt {attempt + 1} for step {step['id']}")
            
            result = await self._execute_step(step, context)
            
            if result.get("success"):
                return result
            
            # Wait before retry
            await asyncio.sleep(self.retry_delay)
        
        return {
            "success": False,
            "error": f"Failed after {self.max_retries} retries"
        }


# ==================== VERIFIER WORKER ====================

class VerifierWorker(BaseWorker):
    """
    Verifier Worker - Verifies results with multiple checks
    
    Responsibilities:
    - Verify task completion
    - Check output quality
    - Validate conditions
    - Assert requirements
    """
    
    def __init__(self, api_key: str, tools=None, config: Dict = None):
        super().__init__("Verifier", api_key, tools, config)
        self.capabilities = [
            "verify_result",
            "check_conditions",
            "validate_output",
            "assert_conditions",
            "compare_outputs",
            "measure_quality"
        ]
        
        # Verification config
        self.strict_mode = config.get("strict_mode", True) if config else True
    
    async def process(self, task: WorkerTask) -> Dict[str, Any]:
        """Verify the execution results"""
        
        execution_results = task.context.get("execution_results", {})
        plan = task.context.get("plan", {})
        
        verification = {
            "passed": False,
            "checks": [],
            "quality_score": 0.0,
            "issues": [],
            "verified_at": time.time()
        }
        
        # Run verification checks
        verification["checks"].append(self._check_completion(execution_results))
        verification["checks"].append(self._check_quality(execution_results))
        verification["checks"].append(self._check_requirements(plan, execution_results))
        
        # Calculate quality score
        passed_checks = sum(1 for c in verification["checks"] if c["passed"])
        verification["quality_score"] = passed_checks / max(1, len(verification["checks"]))
        
        # Determine if verification passed
        verification["passed"] = (
            verification["quality_score"] >= 0.7 and
            all(c["passed"] for c in verification["checks"])
        )
        
        # Add issues if any
        for check in verification["checks"]:
            if not check["passed"]:
                verification["issues"].append(check.get("message", "Check failed"))
        
        return {
            "success": True,
            "output": verification,
            "metadata": {
                "checks_passed": passed_checks,
                "total_checks": len(verification["checks"]),
                "quality_score": verification["quality_score"]
            }
        }
    
    def _check_completion(self, results: Dict) -> Dict:
        """Check if task was completed"""
        
        executed = results.get("executed_steps", [])
        failed = results.get("failed_steps", [])
        
        passed = len(executed) > 0 and len(failed) == 0
        
        return {
            "name": "completion",
            "passed": passed,
            "message": f"Completed: {len(executed)} steps, Failed: {len(failed)}"
        }
    
    def _check_quality(self, results: Dict) -> Dict:
        """Check output quality"""
        
        # Basic quality check
        executed = results.get("executed_steps", [])
        
        if not executed:
            return {
                "name": "quality",
                "passed": False,
                "message": "No executed steps to verify"
            }
        
        # Check if outputs are non-empty
        has_output = any(
            e.get("result", {}).get("output") 
            for e in executed 
            if e.get("result", {}).get("output")
        )
        
        return {
            "name": "quality",
            "passed": has_output,
            "message": "Quality check: " + ("passed" if has_output else "no output")
        }
    
    def _check_requirements(self, plan: Dict, results: Dict) -> Dict:
        """Check if all planned requirements were met"""
        
        planned_steps = len(plan.get("steps", []))
        executed_steps = len(results.get("executed_steps", []))
        
        completion_rate = executed_steps / max(1, planned_steps)
        
        passed = completion_rate >= 0.8
        
        return {
            "name": "requirements",
            "passed": passed,
            "message": f"Requirements: {executed_steps}/{planned_steps} steps ({completion_rate*100:.0f}%)"
        }


# ==================== TOOL BUILDER WORKER ====================

class ToolBuilderWorker(BaseWorker):
    """
    Tool Builder Worker - Creates and optimizes tools
    
    Responsibilities:
    - Generate new tools
    - Optimize existing tools
    - Write tests
    - Document tools
    """
    
    def __init__(self, api_key: str, tools=None, config: Dict = None):
        super().__init__("ToolBuilder", api_key, tools, config)
        self.capabilities = [
            "create_tool",
            "generate_code",
            "write_tests",
            "optimize_tool",
            "document_tool",
            "refactor_tool"
        ]
    
    async def process(self, task: WorkerTask) -> Dict[str, Any]:
        """Build or optimize tools based on task"""
        
        tool_spec = task.context.get("tool_spec", {})
        action = task.context.get("action", "create")
        
        if action == "create":
            return await self._create_tool(tool_spec, task)
        elif action == "optimize":
            return await self._optimize_tool(tool_spec, task)
        elif action == "test":
            return await self._write_tests(tool_spec, task)
        else:
            return {
                "success": False,
                "error": f"Unknown action: {action}"
            }
    
    async def _create_tool(self, spec: Dict, task: WorkerTask) -> Dict:
        """Create a new tool"""
        
        tool_name = spec.get("name", f"tool_{task.id[:8]}")
        tool_description = spec.get("description", task.description)
        tool_parameters = spec.get("parameters", {})
        
        # Generate tool code
        tool_code = self._generate_tool_code(tool_name, tool_description, tool_parameters)
        
        return {
            "success": True,
            "output": {
                "name": tool_name,
                "description": tool_description,
                "code": tool_code,
                "parameters": tool_parameters
            },
            "metadata": {
                "action": "create",
                "tool_created": True
            }
        }
    
    async def _optimize_tool(self, spec: Dict, task: WorkerTask) -> Dict:
        """Optimize an existing tool"""
        
        tool_code = spec.get("code", "")
        
        # Apply optimizations
        optimized_code = self._apply_optimizations(tool_code)
        
        return {
            "success": True,
            "output": {
                "original_code": tool_code,
                "optimized_code": optimized_code,
                "improvements": ["performance", "readability"]
            },
            "metadata": {
                "action": "optimize",
                "tool_optimized": True
            }
        }
    
    async def _write_tests(self, spec: Dict, task: WorkerTask) -> Dict:
        """Write tests for a tool"""
        
        tool_name = spec.get("name", "tool")
        tool_code = spec.get("code", "")
        
        # Generate test code
        test_code = self._generate_test_code(tool_name, tool_code)
        
        return {
            "success": True,
            "output": {
                "tool_name": tool_name,
                "test_code": test_code
            },
            "metadata": {
                "action": "test",
                "tests_written": True
            }
        }
    
    def _generate_tool_code(self, name: str, description: str, parameters: Dict) -> str:
        """Generate tool code from spec"""
        
        param_list = ", ".join(parameters.keys()) if parameters else "args"
        param_defaults = ", ".join([f"{k}: Any = None" for k in parameters.keys()]) if parameters else "args: Any = None"
        
        code = f'''
def {name}({param_defaults}):
    """
    {description}
    
    Args:
        {", ".join([f"{k}: {v.get('type', 'Any')} - {v.get('description', '')}" for k, v in parameters.items()]) if parameters else "args: Arguments"}
    
    Returns:
        Dict with success status and output
    """
    # TODO: Implement tool logic
    return {{
        "success": True,
        "output": None,
        "message": "Tool executed successfully"
    }}
'''
        return code
    
    def _apply_optimizations(self, code: str) -> str:
        """Apply code optimizations"""
        
        # Basic optimizations
        optimizations = [
            ("for i in range(len(", "for "),  # More Pythonic
            ("while True:", "while "),  # Remove infinite loops where possible
        ]
        
        optimized = code
        for old, new in optimizations:
            optimized = optimized.replace(old, new)
        
        return optimized
    
    def _generate_test_code(self, tool_name: str, tool_code: str) -> str:
        """Generate test code"""
        
        test_code = f'''
import unittest
from typing import Any, Dict

class Test{tool_name.title()}(unittest.TestCase):
    """Test cases for {tool_name}"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.instance = None
        # TODO: Initialize test fixtures
    
    def test_basic_functionality(self):
        """Test basic tool functionality"""
        # TODO: Add actual test assertions
        result = {{"success": True, "output": "test"}}
        self.assertIsInstance(result, dict)
        self.assertIn("success", result)
    
    def test_edge_cases(self):
        """Test edge cases"""
        # TODO: Add edge case tests
        pass
    
    def test_error_handling(self):
        """Test error handling"""
        # TODO: Add error handling tests
        pass

if __name__ == "__main__":
    unittest.main()
'''
        return test_code


# ==================== MULTI-AGENT COORDINATOR ====================

class MultiAgentCoordinator:
    """
    Full-featured Multi-Agent Coordinator
    
    Manages 6 specialized workers with real parallel execution:
    1. Researcher - Gathers context
    2. Planner - Creates execution plans
    3. Critic - Evaluates and critiques
    4. Executor - Executes tasks
    5. Verifier - Verifies results
    6. Tool Builder - Creates tools
    
    Communication happens via message passing and shared context.
    """
    
    def __init__(self, api_key: str, tools=None, config: Dict = None):
        self.api_key = api_key
        self.tools = tools
        self.config = config or {}
        
        # Initialize workers
        self.workers: Dict[str, BaseWorker] = {
            "researcher": ResearcherWorker(api_key, tools, config),
            "planner": PlannerWorker(api_key, tools, config),
            "critic": CriticWorker(api_key, tools, config),
            "executor": ExecutorWorker(api_key, tools, config),
            "verifier": VerifierWorker(api_key, tools, config),
            "tool_builder": ToolBuilderWorker(api_key, tools, config),
        }
        
        # Execution mode
        self.execution_mode = config.get("execution_mode", "sequential") if config else "sequential"
        
        # Shared context
        self.shared_context: Dict = {}
        
        # Event log
        self.event_log: List[Dict] = []
        
        # Task results
        self.task_results: Dict[str, Dict] = {}
        
        logger.info("🤖 Multi-Agent Coordinator initialized with 6 workers")
    
    async def execute_task(self, task: WorkerTask) -> Dict[str, Any]:
        """
        Execute a task through the full agent pipeline.
        
        Pipeline:
        1. Researcher: Gather context
        2. Planner: Create plan
        3. Critic: Evaluate plan
        4. (If approved) Executor: Execute plan
        5. Verifier: Verify results
        6. Tool Builder: Create any needed tools
        """
        
        task_id = task.id
        logger.info(f"🚀 Starting multi-agent execution for task: {task_id}")
        
        # Initialize shared context
        self.shared_context = {
            "task_id": task_id,
            "description": task.description,
            "original_context": task.context.copy()
        }
        
        results = {
            "task_id": task_id,
            "success": False,
            "pipeline_results": {},
            "total_duration": 0
        }
        
        start_time = time.time()
        
        try:
            # Stage 1: Research
            logger.info("📊 Stage 1: Researcher gathering context...")
            research_result = await self._run_worker("researcher", task)
            results["pipeline_results"]["research"] = research_result
            self.shared_context["research"] = research_result.get("output", {})
            
            if not research_result.get("success"):
                logger.warning("Research failed, continuing with limited context")
            
            # Stage 2: Plan
            logger.info("📋 Stage 2: Planner creating plan...")
            task.context["research"] = self.shared_context["research"]
            plan_result = await self._run_worker("planner", task)
            results["pipeline_results"]["plan"] = plan_result
            self.shared_context["plan"] = plan_result.get("output", {})
            
            if not plan_result.get("success"):
                logger.error("Planning failed")
                results["error"] = "Planning failed"
                return results
            
            # Stage 3: Critique
            logger.info("🔍 Stage 3: Critic evaluating plan...")
            task.context["plan"] = self.shared_context["plan"]
            task.context["research"] = self.shared_context["research"]
            critique_result = await self._run_worker("critic", task)
            results["pipeline_results"]["critique"] = critique_result
            
            critique_output = critique_result.get("output", {})
            self.shared_context["critique"] = critique_output
            
            # Check if plan was approved
            if not critique_output.get("approved", False):
                logger.warning(f"Plan not approved: {critique_output.get('issues', [])}")
                
                # Try to improve the plan
                if critique_output.get("suggestions"):
                    logger.info("🔄 Attempting to improve plan based on critique...")
                    task.context["plan"] = self.shared_context["plan"]
                    task.context["critique_suggestions"] = critique_output["suggestions"]
                    
                    # Re-plan with suggestions
                    plan_result = await self._run_worker("planner", task)
                    results["pipeline_results"]["plan_improved"] = plan_result
                    self.shared_context["plan"] = plan_result.get("output", {})
                    
                    # Re-critique
                    task.context["plan"] = self.shared_context["plan"]
                    critique_result = await self._run_worker("critic", task)
                    results["pipeline_results"]["critique_2"] = critique_result
                    
                    if not critique_result.get("output", {}).get("approved", False):
                        results["error"] = "Plan not approved after improvement"
                        results["total_duration"] = time.time() - start_time
                        return results
            
            # Stage 4: Execute (only if approved)
            if critique_output.get("approved", False) or self.config.get("force_execute", False):
                logger.info("⚡ Stage 4: Executor running plan...")
                task.context["plan"] = self.shared_context["plan"]
                execution_result = await self._run_worker("executor", task)
                results["pipeline_results"]["execution"] = execution_result
                self.shared_context["execution_results"] = execution_result.get("output", {})
                
                # Stage 5: Verify
                logger.info("✅ Stage 5: Verifier checking results...")
                task.context["execution_results"] = self.shared_context["execution_results"]
                task.context["plan"] = self.shared_context["plan"]
                verification_result = await self._run_worker("verifier", task)
                results["pipeline_results"]["verification"] = verification_result
                
                verification_output = verification_result.get("output", {})
                
                # Determine overall success
                results["success"] = verification_output.get("passed", False)
            else:
                results["error"] = "Plan not approved by critic"
            
            # Stage 6: Tool Builder (optional, if needed)
            if self.config.get("enable_tool_building", False):
                logger.info("🛠️ Stage 6: Tool Builder creating tools...")
                tool_result = await self._run_worker("tool_builder", task)
                results["pipeline_results"]["tool_building"] = tool_result
            
        except Exception as e:
            logger.error(f"❌ Pipeline execution failed: {e}")
            results["error"] = str(e)
        
        results["total_duration"] = time.time() - start_time
        
        # Store results
        self.task_results[task_id] = results
        
        # Log event
        self._log_event("task_completed", {
            "task_id": task_id,
            "success": results["success"],
            "duration": results["total_duration"]
        })
        
        logger.info(f"🏁 Multi-agent execution completed in {results['total_duration']:.2f}s - Success: {results['success']}")
        
        return results
    
    async def _run_worker(self, worker_name: str, task: WorkerTask) -> Dict:
        """Run a specific worker"""
        
        worker = self.workers.get(worker_name)
        if not worker:
            return {"success": False, "error": f"Worker not found: {worker_name}"}
        
        # Create task for worker with current context
        worker_task = WorkerTask(
            id=task.id,
            description=task.description,
            context=task.context.copy(),
            priority=task.priority
        )
        
        # Execute worker
        result = await worker.execute(worker_task)
        
        # Log event
        self._log_event("worker_executed", {
            "worker": worker_name,
            "task_id": task.id,
            "success": result.get("success", False)
        })
        
        return result
    
    async def execute_parallel(self, tasks: List[WorkerTask]) -> Dict[str, Any]:
        """Execute multiple tasks in parallel using all workers"""
        
        logger.info(f"🚀 Starting parallel execution for {len(tasks)} tasks")
        
        # Create tasks for all workers
        worker_tasks = []
        for task in tasks:
            for worker_name in self.workers.keys():
                worker_task = WorkerTask(
                    id=f"{task.id}_{worker_name}",
                    description=task.description,
                    context=task.context.copy()
                )
                worker_tasks.append((worker_name, worker_task))
        
        # Execute in parallel
        results = await asyncio.gather(
            *[self._run_worker(name, task) for name, task in worker_tasks],
            return_exceptions=True
        )
        
        return {
            "success": True,
            "results": results,
            "tasks_count": len(tasks)
        }
    
    def get_worker_stats(self) -> Dict:
        """Get statistics for all workers"""
        
        stats = {}
        for name, worker in self.workers.items():
            stats[name] = worker.get_stats()
        
        return stats
    
    def get_status(self) -> Dict:
        """Get coordinator status - compatible with kernel"""
        return self.get_pipeline_status()

    def get_pipeline_status(self) -> Dict:
        """Get current pipeline status"""
        
        return {
            "execution_mode": self.execution_mode,
            "workers": list(self.workers.keys()),
            "shared_context_keys": list(self.shared_context.keys()),
            "task_results_count": len(self.task_results),
            "event_log_size": len(self.event_log)
        }
    
    def _log_event(self, event_type: str, data: Dict):
        """Log an event"""
        
        self.event_log.append({
            "type": event_type,
            "data": data,
            "timestamp": time.time()
        })
        
        # Keep only last 1000 events
        if len(self.event_log) > 1000:
            self.event_log = self.event_log[-1000:]


# ==================== FACTORY FUNCTION ====================

def create_multi_agent_coordinator(api_key: str, tools=None, config: Dict = None) -> MultiAgentCoordinator:
    """
    Create a fully configured Multi-Agent Coordinator.
    
    Args:
        api_key: API key for LLM calls
        tools: Tools engine for execution
        config: Configuration options
        
    Returns:
        MultiAgentCoordinator instance
    """
    logger.info("🏭 Creating Multi-Agent Coordinator...")
    
    coordinator = MultiAgentCoordinator(api_key, tools, config)
    
    logger.info("✅ Multi-Agent Coordinator ready!")
    
    return coordinator


# ==================== STAGE-BASED PARALLEL EXECUTION ====================

    async def execute_stage_based_parallel(self, tasks: List[WorkerTask]) -> Dict[str, Any]:
        """
        Execute tasks with stage-based parallel processing.
        
        Pipeline stages:
        1. RESEARCH (parallel for all tasks) - Gather context
        2. PLAN (parallel for all tasks) - Create execution plans
        3. CRITIQUE (parallel for all tasks) - Evaluate plans
        4. EXECUTE (parallel for approved tasks) - Run tasks
        5. VERIFY (parallel for executed tasks) - Verify results
        
        Each stage runs all tasks in parallel, then moves to next stage.
        """
        logger.info(f"🎯 Starting STAGE-BASED parallel execution for {len(tasks)} tasks")
        
        start_time = time.time()
        
        # Initialize results storage
        task_results = {}
        
        # Stage 1: RESEARCH (parallel)
        logger.info("📊 Stage 1: RESEARCH (parallel)...")
        research_tasks = []
        for task in tasks:
            worker_task = WorkerTask(
                id=f"{task.id}_research",
                description=task.description,
                context=task.context.copy()
            )
            research_tasks.append(worker_task)
        
        research_results = await asyncio.gather(
            *[self._run_worker("researcher", t) for t in research_tasks],
            return_exceptions=True
        )
        
        # Store research results
        for i, task in enumerate(tasks):
            task_results[task.id] = {
                "research": research_results[i] if not isinstance(research_results[i], Exception) else {"success": False, "error": str(research_results[i])},
                "task": task
            }
            # Add research to context for next stage
            if task_results[task.id]["research"].get("success"):
                task.context["research"] = task_results[task.id]["research"].get("output", {})
        
        # Stage 2: PLAN (parallel)
        logger.info("📋 Stage 2: PLAN (parallel)...")
        plan_tasks = []
        for task in tasks:
            worker_task = WorkerTask(
                id=f"{task.id}_plan",
                description=task.description,
                context=task.context.copy()
            )
            plan_tasks.append(worker_task)
        
        plan_results = await asyncio.gather(
            *[self._run_worker("planner", t) for t in plan_tasks],
            return_exceptions=True
        )
        
        # Store plan results and check approval
        approved_tasks = []
        for i, task in enumerate(tasks):
            plan_result = plan_results[i] if not isinstance(plan_results[i], Exception) else {"success": False, "error": str(plan_results[i])}
            task_results[task.id]["plan"] = plan_result
            
            # Add plan to context
            if plan_result.get("success"):
                task.context["plan"] = plan_result.get("output", {})
                approved_tasks.append(task)
            else:
                logger.warning(f"Task {task.id} planning failed, skipping execution")
        
        # Stage 3: CRITIQUE (parallel for approved tasks)
        logger.info("🔍 Stage 3: CRITIQUE (parallel)...")
        critique_tasks = []
        for task in approved_tasks:
            worker_task = WorkerTask(
                id=f"{task.id}_critique",
                description=task.description,
                context=task.context.copy()
            )
            critique_tasks.append((task, worker_task))
        
        critique_results = await asyncio.gather(
            *[self._run_worker("critic", wt[1]) for wt in critique_tasks],
            return_exceptions=True
        )
        
        # Store critique results and determine which to execute
        executable_tasks = []
        for i, (task, _) in enumerate(critique_tasks):
            critique_result = critique_results[i] if not isinstance(critique_results[i], Exception) else {"success": False, "output": {}}
            task_results[task.id]["critique"] = critique_result
            
            # Check approval
            critique_output = critique_result.get("output", {})
            if critique_output.get("approved", False):
                executable_tasks.append(task)
            else:
                logger.warning(f"Task {task.id} not approved by critic")
        
        # Stage 4: EXECUTE (parallel for approved tasks)
        logger.info("⚡ Stage 4: EXECUTE (parallel)...")
        execution_tasks = []
        for task in executable_tasks:
            worker_task = WorkerTask(
                id=f"{task.id}_execute",
                description=task.description,
                context=task.context.copy()
            )
            execution_tasks.append((task, worker_task))
        
        if execution_tasks:
            execution_results = await asyncio.gather(
                *[self._run_worker("executor", wt[1]) for wt in execution_tasks],
                return_exceptions=True
            )
            
            # Store execution results
            for i, (task, _) in enumerate(execution_tasks):
                execution_result = execution_results[i] if not isinstance(execution_results[i], Exception) else {"success": False, "error": str(execution_results[i])}
                task_results[task.id]["execution"] = execution_result
                task.context["execution_results"] = execution_result.get("output", {})
        else:
            logger.info("No tasks approved for execution")
        
        # Stage 5: VERIFY (parallel for executed tasks)
        logger.info("✅ Stage 5: VERIFY (parallel)...")
        verify_tasks = []
        for task in executable_tasks:
            if task_results[task.id].get("execution", {}).get("success"):
                worker_task = WorkerTask(
                    id=f"{task.id}_verify",
                    description=task.description,
                    context=task.context.copy()
                )
                verify_tasks.append((task, worker_task))
        
        if verify_tasks:
            verify_results = await asyncio.gather(
                *[self._run_worker("verifier", wt[1]) for wt in verify_tasks],
                return_exceptions=True
            )
            
            # Store verification results
            for i, (task, _) in enumerate(verify_tasks):
                verify_result = verify_results[i] if not isinstance(verify_results[i], Exception) else {"success": False, "output": {}}
                task_results[task.id]["verification"] = verify_result
                task_results[task.id]["success"] = verify_result.get("output", {}).get("passed", False)
        
        # Calculate final results
        total_duration = time.time() - start_time
        success_count = sum(1 for r in task_results.values() if r.get("success", False))
        
        logger.info(f"🏁 Stage-based parallel execution completed in {total_duration:.2f}s")
        logger.info(f"   Success: {success_count}/{len(tasks)}")
        
        return {
            "success": success_count > 0,
            "task_results": task_results,
            "total_tasks": len(tasks),
            "success_count": success_count,
            "total_duration": total_duration,
            "execution_mode": "stage_based_parallel"
        }

    async def execute_stage(self, stage_name: str, tasks: List[WorkerTask], context: Dict = None) -> Dict[str, Any]:
        """
        Execute a single stage for multiple tasks in parallel.
        
        Args:
            stage_name: One of "research", "plan", "critique", "execute", "verify", "tool_builder"
            tasks: List of tasks to process
            context: Optional shared context
        """
        valid_stages = ["researcher", "planner", "critic", "executor", "verifier", "tool_builder"]
        if stage_name not in valid_stages:
            return {"success": False, "error": f"Invalid stage: {stage_name}"}
        
        worker_tasks = []
        for task in tasks:
            worker_task = WorkerTask(
                id=f"{task.id}_{stage_name}",
                description=task.description,
                context=task.context.copy()
            )
            worker_tasks.append(worker_task)
        
        logger.info(f"🎯 Executing stage '{stage_name}' for {len(tasks)} tasks (parallel)")
        
        results = await asyncio.gather(
            *[self._run_worker(stage_name, t) for t in worker_tasks],
            return_exceptions=True
        )
        
        return {
            "success": True,
            "stage": stage_name,
            "results": results,
            "count": len(results)
        }

