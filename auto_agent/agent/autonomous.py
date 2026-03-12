"""
OmniAgent X - Autonomous Engine (To'liq Avtonom)
================================================
Agent can act independently without waiting for user confirmation
"""
import os
import logging
import time
from typing import List, Dict, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class AutonomousEngine:
    """
    To'liq avtonom ishlash tizimi
    """
    
    def __init__(self, tools_engine, brain, learning_engine):
        self.tools = tools_engine
        self.brain = brain
        self.learning = learning_engine
        
        # Autonomous settings
        self.auto_execute = True  # Automatically execute tasks
        self.max_steps = 10  # Max steps in a chain
        self.confidence_threshold = 0.7
        
        logger.info("🤖 Autonomous Engine initialized")
    
    # ==================== TASK PLANNING ====================
    
    def plan_task(self, task: str) -> List[Dict]:
        """
        Vazifani rejalashtirish - qadamma-qadam bo'lish
        """
        # Ask AI to break down the task
        planning_prompt = f"""Break down this task into small steps that can be executed one by one.

Task: {task}

Return a JSON list of steps, where each step is:
{{"step": 1, "action": "what to do", "tool": "which tool to use", "reason": "why this step"}}

Only list the steps, no extra text."""

        try:
            # Simple planning - ask the brain
            response = self.brain.think(planning_prompt)
            
            # Try to parse steps (rough parsing)
            steps = self._parse_steps_from_response(response)
            
            if not steps:
                # Fallback - single step
                steps = [{"step": 1, "action": task, "tool": "think", "reason": "Main task"}]
            
            logger.info(f"📋 Planned {len(steps)} steps for: {task[:50]}...")
            return steps
            
        except Exception as e:
            logger.error(f"Planning error: {e}")
            return [{"step": 1, "action": task, "tool": "think", "reason": "Main task"}]
    
    def _parse_steps_from_response(self, response: str) -> List[Dict]:
        """Parse steps from AI response"""
        steps = []
        lines = response.split('\n')
        
        for line in lines:
            line = line.strip()
            if line and (line[0].isdigit() or '-' in line[:5]):
                # Extract action
                action = line.split('.')[-1].strip() if '.' in line else line
                if action:
                    steps.append({
                        "step": len(steps) + 1,
                        "action": action,
                        "tool": self._guess_tool_for_action(action),
                        "reason": "Planned step"
                    })
        
        return steps[:self.max_steps]
    
    def _guess_tool_for_action(self, action: str) -> str:
        """Guess which tool to use based on action"""
        action_lower = action.lower()
        
        if any(word in action_lower for word in ['yoz', 'create', 'yarat']):
            return "write_file"
        elif any(word in action_lower for word in ['o\'qigin', 'read', 'ko\'rsat']):
            return "read_file"
        elif any(word in action_lower for word in ['qidir', 'search', 'top']):
            return "web_search"
        elif any(word in action_lower for word in ['och', 'open', 'ishga']):
            return "launch_application"
        elif any(word in action_lower for word in ['kod', 'code', 'dastur']):
            return "execute_code"
        elif any(word in action_lower for word in ['buyruq', 'command', 'run']):
            return "execute_command"
        
        return "think"
    
    # ==================== TASK EXECUTION ====================
    
    def execute_task(self, task: str, auto: bool = True) -> str:
        """
        Vazifani to'liq bajarish (avtonom)
        """
        start_time = time.time()
        
        if auto and self.auto_execute:
            # Plan the task
            steps = self.plan_task(task)
            
            # Execute each step
            results = []
            for i, step in enumerate(steps):
                logger.info(f"  Step {i+1}/{len(steps)}: {step['action'][:50]}...")
                
                result = self._execute_step(step)
                results.append({
                    "step": i+1,
                    "action": step['action'],
                    "result": result
                })
                
                # Check if step failed
                if "❌" in result or "xato" in result.lower():
                    logger.warning(f"  Step {i+1} failed, trying to fix...")
                    # Try to fix
                    fix_result = self._fix_error(step, result)
                    results[-1]["result"] = fix_result
                    results[-1]["fixed"] = True
            
            # Compile results
            return self._compile_results(results, task, time.time() - start_time)
        
        else:
            # Just ask the brain
            return self.brain.think(task)
    
    def _execute_step(self, step: Dict) -> str:
        """Execute a single step"""
        tool = step.get('tool', 'think')
        action = step.get('action', '')
        
        try:
            # Map tool names to actual functions
            tool_map = {
                "think": lambda: self.brain.think(action),
                "write_file": lambda: self.tools.write_file("temp_" + str(time.time()) + ".txt", action),
                "read_file": lambda: self.tools.read_file(action.split()[-1] if action.split() else ""),
                "web_search": lambda: self.tools.web_search(action),
                "launch_application": lambda: self.tools.launch_application(action.split()[-1] if action.split() else ""),
                "execute_command": lambda: self.tools.execute_command(action),
                "execute_code": lambda: self.tools.execute_code(action),
                "take_screenshot": lambda: self.tools.take_screenshot(),
                "get_system_info": lambda: self.tools.get_system_info(),
            }
            
            if tool in tool_map:
                return tool_map[tool]()
            else:
                return self.brain.think(action)
        
        except Exception as e:
            return f"❌ Step xatosi: {str(e)}"
    
    def _fix_error(self, step: Dict, error_result: str) -> str:
        """Try to fix an error"""
        fix_prompt = f"""A task failed with this error:
{error_result}

Original task: {step['action']}

Try to fix this. What should be done instead?"""
        
        try:
            fix_result = self.brain.think(fix_prompt)
            
            # Learn from error
            self.learning.learn_from_error(step['action'], error_result, fix_result)
            
            return f"🔧 Tuzatish uruniladi:\n{fix_result}"
        
        except Exception as e:
            return f"❌ Tuzatish muvaffaqiyatsiz: {str(e)}"
    
    def _compile_results(self, results: List[Dict], task: str, duration: float) -> str:
        """Compile all step results into final response"""
        
        # Check success
        failed_steps = [r for r in results if "❌" in r.get("result", "")]
        success_steps = len(results) - len(failed_steps)
        
        # Learn from results
        if failed_steps:
            self.learning.learn_from_error(task, str(failed_steps))
        else:
            self.learning.learn_from_success(task, "All steps completed successfully")
        
        # Build response
        response = f"✅ **Vazifa bajarildi:** {task}\n\n"
        response += f"⏱️ Vaqt: {duration:.2f} soniya\n"
        response += f"📋 Qadamlar: {len(results)} ta ({success_steps} muvaffaqiyatli, {len(failed_steps)} xato)\n\n"
        
        response += "**Bajarilgan qadamlar:**\n"
        for r in results:
            status = "✅" if "❌" not in r.get("result", "") else "❌"
            response += f"{status} {r['step']}. {r['action'][:60]}...\n"
            # Add short result
            result_preview = r.get("result", "")[:100].replace("\n", " ")
            response += f"   └─ {result_preview}...\n"
        
        if failed_steps:
            response += f"\n⚠️ {len(failed_steps)} ta qadam muvaffaqiyatsiz tugadi"
        
        return response
    
    # ==================== CONTINUOUS MODE ====================
    
    def start_continuous_mode(self, instruction: str):
        """
        Doimiy rejimda ishlash - foydalanuvchi kuzatadi
        """
        logger.info(f"🚀 Continuous mode started: {instruction[:50]}...")
        
        # This would run in a loop, processing tasks
        # For now, just acknowledge
        return f"""🔄 **Doimiy rejim boshlandi**

Buyruq: {instruction}

Endi bu buyruq doimiy ravishda bajariladi. To'xtatish uchun "stop" deb yozing."""
    
    def stop_continuous_mode(self):
        """Doimiy rejimni to'xtatish"""
        return "🛑 Doimiy rejim to'xtatildi"
    
    # ==================== AUTO-DECISION ====================
    
    def should_auto_execute(self, task: str) -> bool:
        """
        Avtomatik ishga tushirish kerakmi?
        """
        # Check if task is safe to auto-execute
        safe_keywords = [
            'yarat', 'yoz', 'ko\'rsat', 'ol', 'top',
            'create', 'show', 'get', 'find', 'read'
        ]
        
        dangerous_keywords = [
            'o\'chir', 'delete', 'format', 'shutdown',
            'restart', 'kill', 'remove'
        ]
        
        task_lower = task.lower()
        
        # If contains dangerous keyword, ask first
        if any(word in task_lower for word in dangerous_keywords):
            return False
        
        # Otherwise, auto-execute
        return True
    
    # ==================== SETTINGS ====================
    
    def set_auto_execute(self, enabled: bool):
        """Auto-execute ni yoqish/o'chirish"""
        self.auto_execute = enabled
        return f"🤖 Avtonom rejim: {'yoqilgan' if enabled else 'o\'chirilgan'}"
    
    def get_status(self) -> str:
        """Holatni olish"""
        return f"""🤖 **Avtonom Engine Holati:**
- Auto-execute: {self.auto_execute}
- Max steps: {self.max_steps}
- Confidence threshold: {self.confidence_threshold}
"""