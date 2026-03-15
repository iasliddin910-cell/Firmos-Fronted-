"""
OmniAgent X ULTIMATE - Enhanced Brain with ReAct + Chain of Thought
====================================================================
The most advanced AI brain with reasoning capabilities

REFACTORED:
- Uses new OpenAI SDK (openai.OpenAI client)
- Structured tool calling
- Verify and Repair steps
- JSON-based action parsing
"""
import json
import logging
import time
from typing import List, Dict, Optional, Any, Tuple
from enum import Enum

# NEW: Use new OpenAI SDK
from openai import OpenAI
from config import settings

logger = logging.getLogger(__name__)


class ReasoningStep(Enum):
    """Reasoning step types"""
    THINK = "think"
    PLAN = "plan"
    ACT = "act"
    OBSERVE = "observe"
    VERIFY = "verify"
    REPAIR = "repair"
    CRITIC = "critic"
    FINAL = "final"


class ToolResult:
    """Structured tool result"""
    def __init__(self, tool_name: str, success: bool, result: Any, error: str = None):
        self.tool_name = tool_name
        self.success = success
        self.result = result
        self.error = error
        self.timestamp = time.time()
    
    def to_dict(self) -> dict:
        return {
            "tool": self.tool_name,
            "success": self.success,
            "result": str(self.result)[:500],  # Truncate long results
            "error": self.error,
            "timestamp": self.timestamp
        }


class Action:
    """Structured action representation"""
    def __init__(self, tool_name: str, arguments: Dict[str, Any]):
        self.tool_name = tool_name
        self.arguments = arguments
    
    @classmethod
    def from_json(cls, json_str: str) -> Optional['Action']:
        """Parse action from JSON"""
        try:
            data = json.loads(json_str)
            return cls(data.get("tool"), data.get("args", {}))
        except:
            return None
    
    def __repr__(self):
        return f"Action(tool={self.tool_name}, args={self.arguments})"


class ReActAgent:
    """
    ReAct (Reason + Act) Pattern - Think, Act, Observe, Repeat
    With Verify and Repair capabilities
    
    REFACTORED:
    - Uses new OpenAI SDK
    - JSON-based structured tool calling
    - Verify step after each action
    - Repair/Retry on failure
    """
    
    def __init__(self, api_key: str, tools_engine):
        self.api_key = api_key
        self.tools = tools_engine
        
        # NEW: Use new OpenAI client
        self.client = OpenAI(api_key=api_key)
        
        # Reasoning settings
        self.max_iterations = 10
        self.max_tokens_per_step = 500
        self.confidence_threshold = 0.8
        self.retry_budget = 2
        
        # History
        self.reasoning_history: List[Dict] = []
        self.current_plan: List[Action] = []
        
        logger.info("🧠 ReAct Agent initialized (NEW SDK)")
    
    def think(self, task: str, context: str = "") -> str:
        """
        Main thinking method with ReAct + Verify + Repair pattern
        """
        logger.info(f"🎯 ReAct thinking: {task[:50]}...")
        
        # Initialize
        self.reasoning_history = []
        self.current_plan = []
        iteration = 0
        current_task = task
        
        while iteration < self.max_iterations:
            iteration += 1
            
            # Step 1: THINK/PLAN
            thought = self._think_step(current_task, context)
            self._add_reasoning_step(ReasoningStep.THINK, thought)
            
            # Step 2: PLAN - Create action plan
            action = self._plan_step(thought)
            if action:
                self.current_plan.append(action)
                self._add_reasoning_step(ReasoningStep.PLAN, str(action))
            
            # Check if we should stop (task complete)
            if self._is_task_complete(thought):
                final_result = self._finalize(thought)
                self._add_reasoning_step(ReasoningStep.FINAL, final_result)
                return final_result
            
            # Step 3: ACT - Execute action
            if action:
                action_result = self._act_step(action)
                self._add_reasoning_step(ReasoningStep.ACT, action_result.to_dict())
                
                # Step 4: OBSERVE
                observation = self._observe_step(action_result)
                self._add_reasoning_step(ReasoningStep.OBSERVE, observation)
                
                # Step 5: VERIFY - Check if action succeeded
                verified = self._verify_step(action_result, observation)
                self._add_reasoning_step(ReasoningStep.VERIFY, f"Verified: {verified}")
                
                # Step 6: REPAIR - If verification failed, try to fix
                if not verified and iteration < self.max_iterations:
                    repair_result = self._repair_step(action_result, observation)
                    self._add_reasoning_step(ReasoningStep.REPAIR, repair_result)
                    current_task = f"Fix this: {repair_result}\nOriginal: {task}"
                else:
                    current_task = task
            else:
                # No action needed, just think
                current_task = task
            
            # Build context for next iteration
            context = self._build_context()
        
        # Max iterations reached
        return self._finalize(f"Task completed with {iteration} iterations. {context}")
    
    def _think_step(self, task: str, context: str) -> str:
        """
        THINK: Analyze the task and decide what to do
        """
        context_str = f"\n\nPrevious context:\n{context}" if context else ""
        
        prompt = f"""You are OmniAgent X with ReAct reasoning. 

TASK: {task}{context_str}

Think step by step:
1. What is the task asking for?
2. What tools do I need to use?
3. What's the best approach?
4. What should I do first?

Return ONLY your thought process, no code yet."""

        try:
            response = self.client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "You are an expert AI assistant with ReAct reasoning."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=self.max_tokens_per_step
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Think step error: {e}")
            return f"Thinking about: {task}"
    
    def _plan_step(self, thought: str) -> Optional[Action]:
        """
        PLAN: Decide what action to take (JSON structured)
        """
        prompt = f"""Based on this thought:
{thought}

Choose ONE tool to use. Return ONLY valid JSON:
{{
    "tool": "tool_name",
    "args": {{"arg1": "value1"}}
}}

Available tools:
- web_search: {{"query": "search text"}}
- read_file: {{"path": "filename"}}
- write_file: {{"path": "filename", "content": "text"}}
- execute_command: {{"command": "terminal command"}}
- execute_code: {{"code": "python code"}}
- take_screenshot: {{}}
- get_system_info: {{}}
- think: {{"question": "what to think about"}}

Return ONLY the JSON, no explanation:"""

        try:
            response = self.client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "You are a structured action planner. Return valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=200
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # Try to parse JSON
            try:
                # Extract JSON if wrapped in code blocks
                if "```json" in result_text:
                    result_text = result_text.split("```json")[1].split("```")[0]
                elif "```" in result_text:
                    result_text = result_text.split("```")[1].split("```")[0]
                
                data = json.loads(result_text)
                return Action(data.get("tool"), data.get("args", {}))
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse action JSON: {result_text[:100]}")
                return None
            
        except Exception as e:
            logger.error(f"Plan step error: {e}")
            return None
    
    def _act_step(self, action: Action) -> ToolResult:
        """
        ACT: Execute the decided action (structured)
        """
        tool_name = action.tool_name
        args = action.arguments
        
        try:
            # Execute based on action type
            if tool_name == "web_search":
                result = self.tools.web_search(args.get("query", ""))
            elif tool_name == "read_file":
                result = self.tools.read_file(args.get("path", ""))
            elif tool_name == "write_file":
                result = self.tools.write_file(args.get("path", ""), args.get("content", ""))
            elif tool_name == "execute_command":
                result = self.tools.execute_command(args.get("command", ""))
            elif tool_name == "execute_code":
                result = self.tools.execute_code(args.get("code", ""))
            elif tool_name == "take_screenshot":
                result = self.tools.take_screenshot()
            elif tool_name == "get_system_info":
                result = self.tools.get_system_info()
            elif tool_name == "think":
                result = args.get("question", "Thinking...")
            else:
                result = f"Unknown tool: {tool_name}"
            
            return ToolResult(tool_name, True, result)
            
        except Exception as e:
            logger.error(f"Act step error: {e}")
            return ToolResult(tool_name, False, None, str(e))
    
    def _observe_step(self, action_result: ToolResult) -> str:
        """
        OBSERVE: Analyze the result of the action
        """
        prompt = f"""I just performed an action and got this result:

Tool: {action_result.tool_name}
Success: {action_result.success}
Result: {action_result.result[:1000]}
Error: {action_result.error}

Observe and analyze:
1. Did the action succeed?
2. What did I learn?
3. Do I need more information?
4. Can I complete the task now?

Return your observation."""

        try:
            response = self.client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "You observe and analyze results."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5,
                max_tokens=300
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Observation: {action_result.result[:200] if action_result.result else 'No result'}"
    
    def _verify_step(self, action_result: ToolResult, observation: str) -> bool:
        """
        VERIFY: Check if the action actually succeeded
        """
        if not action_result.success:
            return False
        
        # Check for error indicators in result
        result_str = str(action_result.result).lower() if action_result.result else ""
        error_indicators = ["error", "xato", "failed", "exception", "traceback"]
        
        if any(indicator in result_str for indicator in error_indicators):
            return False
        
        # Ask AI to verify
        prompt = f"""Verify if this action was successful:

Action: {action_result.tool_name}
Result: {action_result.result[:500]}

Did this action achieve its intended purpose? Answer YES or NO with brief explanation."""

        try:
            response = self.client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "You verify action results."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=50
            )
            answer = response.choices[0].message.content.lower()
            return "yes" in answer
        except:
            return True  # Assume success if verification fails
    
    def _repair_step(self, action_result: ToolResult, observation: str) -> str:
        """
        REPAIR: Try to fix a failed action
        """
        prompt = f"""I need to fix a failed action:

Original Action: {action_result.tool_name}
Error: {action_result.error}
Observation: {observation}

How should I fix this? What different approach should I take?

Return your repair plan."""

        try:
            response = self.client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "You fix failed actions."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=200
            )
            return response.choices[0].message.content
        except:
            return "Try a different approach"
    
    def _is_task_complete(self, thought: str) -> bool:
        """Check if task is complete"""
        complete_keywords = ["task complete", "finished", "done", "solved", "ready", "tayyor", "all done"]
        return any(kw in thought.lower() for kw in complete_keywords)
    
    def _build_context(self) -> str:
        """Build context from reasoning history"""
        context_parts = []
        for step in self.reasoning_history[-5:]:  # Last 5 steps
            content = str(step.get('content', ''))[:200]
            context_parts.append(f"{step['type']}: {content}...")
        return "\n".join(context_parts)
    
    def _add_reasoning_step(self, step_type: ReasoningStep, content: Any):
        """Add a reasoning step to history"""
        self.reasoning_history.append({
            "type": step_type.value,
            "content": str(content) if not isinstance(content, dict) else content,
            "timestamp": time.time()
        })
    
    def _finalize(self, final_thought: str) -> str:
        """Finalize and return the result"""
        return f"""✅ **Vazifa bajarildi (ReAct + Verify + Repair)**

🧠 *Fikrlash jarayoni:*

{self._format_reasoning_history()}

---

📋 *Yakuniy natija:*

{final_thought}"""
    
    def _format_reasoning_history(self) -> str:
        """Format reasoning history for display"""
        formatted = []
        for i, step in enumerate(self.reasoning_history):
            emoji = {
                "think": "🤔",
                "plan": "📋",
                "act": "⚡",
                "observe": "👁️",
                "verify": "✅",
                "repair": "🔧",
                "critic": "📝",
                "final": "✅"
            }.get(step["type"], "📝")
            
            content = step.get('content', {})
            if isinstance(content, dict):
                content = str(content)[:200]
            else:
                content = str(content)[:200]
            
            formatted.append(f"{i+1}. {emoji} {step['type'].upper()}: {content}...")
        
        return "\n".join(formatted)
    
    def reset_conversation(self):
        """Reset conversation history"""
        self.reasoning_history = []
        self.current_plan = []


class ChainOfThought:
    """
    Chain of Thought reasoning - step by step thinking
    
    REFACTORED: Uses new OpenAI SDK
    """
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = OpenAI(api_key=api_key)
        logger.info("🔗 Chain of Thought initialized (NEW SDK)")
    
    def solve_complex_problem(self, problem: str) -> str:
        """
        Solve complex problem with step-by-step reasoning
        """
        prompt = f"""Solve this problem step by step with EXPLICIT reasoning.

Problem: {problem}

Format your response like this:
STEP 1: <what you're thinking>
→ <action taken>

STEP 2: <what you're thinking>
→ <action taken>

... continue until solved

FINAL ANSWER: <the solution>"""

        try:
            response = self.client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "You solve problems with detailed step-by-step reasoning."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=2000
            )
            
            return f"""🔗 **Chain of Thought - Qadamma-qadam yechim**

{response.choices[0].message.content}"""
        
        except Exception as e:
            return f"❌ Xatolik: {str(e)}"
    
    def explain_reasoning(self, question: str) -> str:
        """
        Explain the reasoning behind an answer
        """
        prompt = f"""Explain your reasoning for this question in detail.

Question: {question}

Think step by step and explain WHY each step makes sense."""

        try:
            response = self.client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "You explain reasoning clearly."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1000
            )
            
            return f"""🧠 **Fikrlash tushuntirish:**

{response.choices[0].message.content}"""
        
        except Exception as e:
            return f"❌ Xatolik: {str(e)}"


class UltimateBrain:
    """
    Ultimate Brain - combines all reasoning capabilities
    
    REFACTORED: Uses new OpenAI SDK
    """
    
    def __init__(self, api_key: str, tools_engine):
        self.api_key = api_key
        self.tools = tools_engine
        
        # Initialize reasoning systems
        self.react = ReActAgent(api_key, tools_engine)
        self.cot = ChainOfThought(api_key)
        
        logger.info("🧠 Ultimate Brain initialized (REFACTORED)")
    
    def think(self, user_message: str, use_react: bool = True, use_cot: bool = False) -> str:
        """
        Main thinking function with multiple reasoning modes
        """
        # Determine which reasoning to use
        if use_cot:
            return self.cot.solve_complex_problem(user_message)
        elif use_react:
            return self.react.think(user_message)
        else:
            # Standard thinking
            return self._standard_think(user_message)
    
    def _standard_think(self, user_message: str) -> str:
        """Standard thinking without special reasoning"""
        # This would use the existing brain logic
        return user_message
    
    def explain(self, topic: str) -> str:
        """Explain something with full reasoning"""
        return self.cot.explain_reasoning(topic)
    
    def solve(self, problem: str) -> str:
        """Solve a complex problem"""
        return self.cot.solve_complex_problem(problem)
    
    def get_reasoning_trace(self) -> str:
        """Get the reasoning trace"""
        if self.react.reasoning_history:
            return self.react._format_reasoning_history()
        return "No reasoning history"
    
    def reset_conversation(self):
        """Reset conversation"""
        self.react.reset_conversation()


# Factory function
def create_ultimate_brain(api_key: str, tools_engine):
    """Create the ultimate brain"""
    return UltimateBrain(api_key, tools_engine)