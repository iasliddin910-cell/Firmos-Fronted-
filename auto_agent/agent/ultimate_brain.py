"""
OmniAgent X ULTIMATE - Enhanced Brain with ReAct + Chain of Thought
====================================================================
The most advanced AI brain with reasoning capabilities
"""
import json
import logging
import time
from typing import List, Dict, Optional, Any, Tuple
from enum import Enum
import openai
from config import settings

logger = logging.getLogger(__name__)


class ReasoningStep(Enum):
    """Reasoning step types"""
    THINK = "think"
    ACT = "act"
    OBSERVE = "observe"
    REPEAT = "repeat"
    FINAL = "final"


class ReActAgent:
    """
    ReAct (Reason + Act) Pattern - Think, Act, Observe, Repeat
    The most advanced reasoning engine
    """
    
    def __init__(self, api_key: str, tools_engine):
        self.api_key = api_key
        self.tools = tools_engine
        openai.api_key = api_key
        
        # Reasoning settings
        self.max_iterations = 10
        self.max_tokens_per_step = 500
        self.confidence_threshold = 0.8
        
        # History
        self.reasoning_history: List[Dict] = []
        
        logger.info("🧠 ReAct Agent initialized")
    
    def think(self, task: str, context: str = "") -> str:
        """
        Main thinking method with ReAct pattern
        """
        logger.info(f"🎯 ReAct thinking: {task[:50]}...")
        
        # Initialize
        self.reasoning_history = []
        iteration = 0
        current_task = task
        
        while iteration < self.max_iterations:
            iteration += 1
            
            # Step 1: THINK
            thought = self._think_step(current_task, context)
            self._add_reasoning_step(ReasoningStep.THINK, thought)
            
            # Check if we should stop (task complete)
            if self._is_task_complete(thought):
                final_result = self._finalize(thought)
                self._add_reasoning_step(ReasoningStep.FINAL, final_result)
                return final_result
            
            # Step 2: ACT
            action_result = self._act_step(thought)
            self._add_reasoning_step(ReasoningStep.ACT, action_result)
            
            # Step 3: OBSERVE
            observation = self._observe_step(action_result)
            self._add_reasoning_step(ReasoningStep.OBSERVE, observation)
            
            # Step 4: REPEAT or continue
            context = self._build_context()
            
            # Check for errors
            if self._has_error(observation):
                # Try to fix
                current_task = f"Fix this error: {observation}\nOriginal task: {task}"
                logger.warning(f"  ⚠️ Error detected, trying to fix...")
            else:
                # Continue with task
                current_task = task
        
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
            response = openai.ChatCompletion.create(
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
    
    def _act_step(self, thought: str) -> str:
        """
        ACT: Execute the decided action
        """
        # Extract what action to take from thought
        prompt = f"""Based on this thought process:
{thought}

What specific action should I take? Choose ONE of:
- web_search: <query> - Search the web
- read_file: <filepath> - Read a file
- write_file: <filepath> <content> - Write a file
- execute_command: <command> - Run terminal command
- execute_code: <code> - Run code
- take_screenshot - Take a screenshot
- get_system_info - Get system info
- think: <question> - Just think about something

Return ONLY the action in this format:
ACTION: <action_type>
TARGET: <what to act on>
CONTENT: <details if needed>"""

        try:
            response = openai.ChatCompletion.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "You are an AI that decides actions."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=200
            )
            
            result_text = response.choices[0].message.content
            
            # Execute the action
            return self._execute_action(result_text)
            
        except Exception as e:
            logger.error(f"Act step error: {e}")
            return f"❌ Action error: {str(e)}"
    
    def _execute_action(self, action_spec: str) -> str:
        """Execute the specified action"""
        lines = action_spec.split('\n')
        action_type = ""
        target = ""
        
        for line in lines:
            if line.startswith("ACTION:"):
                action_type = line.replace("ACTION:", "").strip()
            elif line.startswith("TARGET:"):
                target = line.replace("TARGET:", "").strip()
        
        # Execute based on action type
        try:
            if "web_search" in action_type.lower():
                return self.tools.web_search(target)
            elif "read_file" in action_type.lower():
                return self.tools.read_file(target)
            elif "write_file" in action_type.lower():
                parts = target.split(" ", 1)
                if len(parts) == 2:
                    return self.tools.write_file(parts[0], parts[1])
                return "❌ Write file needs filename and content"
            elif "execute_command" in action_type.lower():
                return self.tools.execute_command(target)
            elif "execute_code" in action_type.lower():
                return self.tools.execute_code(target)
            elif "screenshot" in action_type.lower():
                return self.tools.take_screenshot()
            elif "system_info" in action_type.lower():
                return self.tools.get_system_info()
            else:
                return f"Thinking: {action_spec}"
        except Exception as e:
            return f"❌ Execution error: {str(e)}"
    
    def _observe_step(self, action_result: str) -> str:
        """
        OBSERVE: Analyze the result of the action
        """
        prompt = f"""I just performed an action and got this result:

{action_result[:1000]}

Observe and analyze:
1. Did the action succeed?
2. What did I learn?
3. Do I need more information?
4. Can I complete the task now?

Return your observation."""

        try:
            response = openai.ChatCompletion.create(
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
            return f"Observation: {action_result[:200]}"
    
    def _is_task_complete(self, thought: str) -> bool:
        """Check if task is complete"""
        complete_keywords = ["task complete", "finished", "done", "solved", "ready", "tayyor"]
        return any(kw in thought.lower() for kw in complete_keywords)
    
    def _has_error(self, observation: str) -> bool:
        """Check if there's an error"""
        error_keywords = ["error", "xato", "failed", "muvaffaqiyatsiz", "not working"]
        return any(kw in observation.lower() for kw in error_keywords)
    
    def _build_context(self) -> str:
        """Build context from reasoning history"""
        context_parts = []
        for step in self.reasoning_history[-5:]:  # Last 5 steps
            context_parts.append(f"{step['type']}: {step['content'][:200]}")
        return "\n".join(context_parts)
    
    def _add_reasoning_step(self, step_type: ReasoningStep, content: str):
        """Add a reasoning step to history"""
        self.reasoning_history.append({
            "type": step_type.value,
            "content": content,
            "timestamp": time.time()
        })
    
    def _finalize(self, final_thought: str) -> str:
        """Finalize and return the result"""
        return f"""✅ **Vazifa bajarildi (ReAct Pattern)**

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
                "act": "⚡",
                "observe": "👁️",
                "repeat": "🔄",
                "final": "✅"
            }.get(step["type"], "📝")
            
            content = step["content"][:300].replace("\n", " ")
            formatted.append(f"{i+1}. {emoji} {step['type'].upper()}: {content}...")
        
        return "\n".join(formatted)


class ChainOfThought:
    """
    Chain of Thought reasoning - step by step thinking
    """
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        openai.api_key = api_key
        logger.info("🔗 Chain of Thought initialized")
    
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
            response = openai.ChatCompletion.create(
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
            response = openai.ChatCompletion.create(
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
    """
    
    def __init__(self, api_key: str, tools_engine):
        self.api_key = api_key
        self.tools = tools_engine
        
        # Initialize reasoning systems
        self.react = ReActAgent(api_key, tools_engine)
        self.cot = ChainOfThought(api_key)
        
        logger.info("🧠 Ultimate Brain initialized")
    
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


# Factory function
def create_ultimate_brain(api_key: str, tools_engine):
    """Create the ultimate brain"""
    return UltimateBrain(api_key, tools_engine)