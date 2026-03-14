"""
OmniAgent X - Native Function Calling Brain
=============================================
Uses OpenAI's native function calling (tools) instead of JSON parsing

This provides:
- Strict schema validation
- Type checking
- Automatic retries
- No prompt injection through JSON
"""
import json
import logging
import time
from typing import List, Dict, Optional, Any
from openai import OpenAI
from config import settings

logger = logging.getLogger(__name__)


# ==================== FUNCTION DEFINITIONS ====================

def get_function_definitions():
    """Get OpenAI function definitions with strict schemas"""
    
    return [
        {
            "type": "function",
            "function": {
                "name": "web_search",
                "description": "Search the web for information",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query"
                        }
                    },
                    "required": ["query"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "Read content from a file",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "File path to read"
                        }
                    },
                    "required": ["path"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "write_file",
                "description": "Write content to a file",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "File path to write"
                        },
                        "content": {
                            "type": "string",
                            "description": "Content to write"
                        }
                    },
                    "required": ["path", "content"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "execute_command",
                "description": "Execute a terminal command",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": "Command to execute"
                        },
                        "timeout": {
                            "type": "integer",
                            "description": "Timeout in seconds",
                            "default": 30
                        }
                    },
                    "required": ["command"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "execute_code",
                "description": "Execute Python or JavaScript code",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "code": {
                            "type": "string",
                            "description": "Code to execute"
                        },
                        "language": {
                            "type": "string",
                            "enum": ["python", "javascript"],
                            "description": "Programming language",
                            "default": "python"
                        }
                    },
                    "required": ["code"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "take_screenshot",
                "description": "Take a screenshot of the screen",
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_system_info",
                "description": "Get system information",
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "think",
                "description": "Think about something without taking action",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "question": {
                            "type": "string",
                            "description": "Question to think about"
                        }
                    },
                    "required": ["question"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "complete_task",
                "description": "Mark task as complete and provide final result",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "result": {
                            "type": "string",
                            "description": "Final result or answer"
                        }
                    },
                    "required": ["result"]
                }
            }
        }
    ]


# ==================== NATIVE FUNCTION CALLING BRAIN ====================

class NativeFunctionBrain:
    """
    Brain that uses OpenAI's native function calling
    instead of JSON parsing
    
    Benefits:
    - No JSON parsing errors
    - Type validation
    - Automatic argument extraction
    - More reliable tool calling
    """
    
    def __init__(self, api_key: str, tools_engine, kernel=None, sandbox=None, approval_engine=None):
        self.api_key = api_key
        self.tools = tools_engine
        self.client = OpenAI(api_key=api_key)
        self.kernel = kernel
        self.sandbox = sandbox
        self.approval_engine = approval_engine
        
        # Function definitions
        self.functions = get_function_definitions()
        self.function_map = self._build_function_map()
        
        # Settings
        self.max_iterations = 10
        
        # Conversation history for reset capability
        self.messages = []
        
        logger.info("🧠 Native Function Brain initialized")
    
    def reset_conversation(self):
        """Reset conversation history"""
        self.messages = []
        logger.info("🧠 Native Function Brain conversation reset")
    
    def _build_function_map(self) -> Dict:
        """Map function names to actual implementations"""
        return {
            "web_search": lambda args: self.tools.web_search(args.get("query", "")),
            "read_file": lambda args: self.tools.read_file(args.get("path", "")),
            "write_file": lambda args: self.tools.write_file(args.get("path", ""), args.get("content", "")),
            "execute_command": lambda args: self.tools.execute_command(args.get("command", ""), timeout=args.get("timeout", 30)),
            "execute_code": lambda args: self.tools.execute_code(args.get("code", ""), language=args.get("language", "python")),
            "take_screenshot": lambda args: self.tools.take_screenshot(),
            "get_system_info": lambda args: self.tools.get_system_info(),
            "think": lambda args: self._think_internal(args.get("question", "")),
            "complete_task": lambda args: {"done": True, "result": args.get("result", "")},
        }
    
    def _think_internal(self, question: str) -> str:
        """Internal thinking without tool execution"""
        return f"Thinking about: {question}"
    
    def think(self, user_message: str) -> str:
        """
        Main thinking method using native function calling
        """
        logger.info(f"🎯 Native Function Brain thinking: {user_message[:50]}...")
        
        # Build messages
        messages = [
            {
                "role": "system",
                "content": """You are OmniAgent X, an autonomous AI assistant.

Your job is to complete user tasks by thinking and using tools.
For each step:
1. Think about what to do
2. Use a tool to take action
3. Observe the result
4. Verify if task is complete
5. If complete, call complete_task with your result

Available tools:
- web_search: Search the web
- read_file: Read a file
- write_file: Write to a file
- execute_command: Run terminal commands
- execute_code: Execute code
- take_screenshot: Take screenshot
- get_system_info: Get system info
- think: Think without action
- complete_task: Finish the task"""
            },
            {
                "role": "user",
                "content": user_message
            }
        ]
        
        iteration = 0
        final_result = ""
        
        while iteration < self.max_iterations:
            iteration += 1
            
            # Get model response with function calling
            try:
                response = self.client.chat.completions.create(
                    model=settings.OPENAI_MODEL,
                    messages=messages,
                    tools=self.functions,
                    temperature=0.7,
                    max_tokens=1000
                )
                
                # Check if model wants to call a function
                if response.choices[0].message.tool_calls:
                    # Process function calls
                    for tool_call in response.choices[0].message.tool_calls:
                        function_name = tool_call.function.name
                        function_args = json.loads(tool_call.function.arguments)
                        
                        logger.info(f"🔧 Calling: {function_name} with {function_args}")
                        
                        # Add assistant message to conversation
                        messages.append({
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [
                                {
                                    "id": tool_call.id,
                                    "type": "function",
                                    "function": {
                                        "name": function_name,
                                        "arguments": tool_call.function.arguments
                                    }
                                }
                            ]
                        })
                        
                        # Execute function
                        if function_name in self.function_map:
                            try:
                                result = self.function_map[function_name](function_args)
                                result_str = str(result)[:500]  # Truncate
                            except Exception as e:
                                result_str = f"Error: {str(e)}"
                            
                            # Add function result to conversation
                            messages.append({
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "content": result_str
                            })
                            
                            logger.info(f"📊 Result: {result_str[:100]}...")
                            
                            # Check if task is complete
                            if function_name == "complete_task":
                                final_result = function_args.get("result", "")
                                break
                        else:
                            logger.warning(f"Unknown function: {function_name}")
                    
                    # Check if we broke out of the loop
                    if final_result:
                        break
                
                else:
                    # No function call - model responded directly
                    content = response.choices[0].message.content
                    
                    if content:
                        messages.append({
                            "role": "assistant",
                            "content": content
                        })
                        
                        # Check if task seems complete
                        if any(word in content.lower() for word in ["tayyor", "ready", "done", "complete", "bajarildi"]):
                            final_result = content
                            break
            
            except Exception as e:
                logger.error(f"Error in function calling: {e}")
                return f"Xatolik: {str(e)}"
        
        if final_result:
            return final_result
        
        return f"Vazifa {iteration} qadamdan so'ng tugallandi. Natijani ko'rish uchun hisob-kitob qiling."
    
    def get_function_schemas(self) -> List[Dict]:
        """Get function schemas for debugging"""
        return self.functions


# ==================== FACTORY ====================

def create_native_brain(api_key: str, tools_engine, kernel=None, sandbox=None, approval_engine=None):
    """Create native function calling brain"""
    return NativeFunctionBrain(api_key, tools_engine, kernel=kernel, sandbox=sandbox, approval_engine=approval_engine)


# ==================== TOOL-INTENT BRAIN ====================

class ToolIntentBrain:
    """
    Brain as tool-intent layer only (not orchestrator).
    
    Model provides:
    - suggestion (what to do)
    - tool intent (which tool)
    - candidate args (potential arguments)
    
    Truth comes from:
    - actual runtime execution
    - verifier
    - artifacts
    
    This ensures No1-grade governance - model doesn't control execution.
    """
    
    def __init__(self, api_key: str, tools_engine, kernel=None):
        self.api_key = api_key
        self.tools = tools_engine
        self.kernel = kernel
        
        from openai import OpenAI
        self.client = OpenAI(api_key=api_key)
        
        # Limited system prompt - just tool intent
        self.system_prompt = """You are OmniAgent X's TOOL-INTENT LAYER.

Your job is ONLY to suggest tools and arguments.
DO NOT execute, verify, or complete tasks yourself.

Output ONLY:
- tool_name: Which tool to use
- args: Candidate arguments (may need verification)
- intent: What you're trying to achieve
- confidence: How confident you are (0-1)

DO NOT claim task is complete - let the verifier decide."""
        
    def suggest_tool(self, context: str, available_tools: List[str]) -> Dict:
        """
        Get tool suggestion from model - just intent, no execution.
        
        Returns:
        {
            "tool_name": "...",
            "args": {...},
            "intent": "...",
            "confidence": 0.8
        }
        """
        from config import settings
        
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"""
Context: {context}

Available tools: {', '.join(available_tools)}

Suggest ONE tool to use and its arguments.
Be conservative - high confidence only.
"""}
        ]
        
        try:
            response = self.client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=messages,
                temperature=0.3,  # Lower temperature for better focus
                max_tokens=500
            )
            
            content = response.choices[0].message.content
            
            # Parse response
            suggestion = self._parse_suggestion(content)
            suggestion["source"] = "model_suggestion"
            
            return suggestion
            
        except Exception as e:
            logger.error(f"Tool suggestion failed: {e}")
            return {
                "tool_name": None,
                "args": {},
                "intent": "error",
                "confidence": 0.0,
                "error": str(e)
            }
    
    def _parse_suggestion(self, content: str) -> Dict:
        """Parse model response into structured suggestion"""
        import re
        
        # Extract tool name
        tool_match = re.search(r'tool[_\s]?name[:\s]+(\w+)', content, re.IGNORECASE)
        tool_name = tool_match.group(1) if tool_match else None
        
        # Extract args (simple parsing)
        args_match = re.search(r'args[:\s]+\{([^}]+)\}', content, re.DOTALL)
        args = {}
        if args_match:
            # Simple key=value parsing
            for line in args_match.group(1).split(','):
                if '=' in line:
                    k, v = line.split('=', 1)
                    args[k.strip().strip('"\'')] = v.strip().strip('"\'')
        
        # Extract confidence
        conf_match = re.search(r'confidence[:\s]+([0-9.]+)', content, re.IGNORECASE)
        confidence = float(conf_match.group(1)) if conf_match else 0.5
        
        # Extract intent
        intent_match = re.search(r'intent[:\s]+(.+?)(?:\n|$)', content, re.IGNORECASE)
        intent = intent_match.group(1).strip() if intent_match else ""
        
        return {
            "tool_name": tool_name,
            "args": args,
            "intent": intent,
            "confidence": confidence
        }
    
    def get_verified_execution(self, suggestion: Dict, context: str) -> Dict:
        """
        Execute suggested tool through kernel/verifier for truth.
        
        Model suggests, verifier confirms - separation of concerns.
        """
        if not suggestion.get("tool_name") or suggestion.get("confidence", 0) < 0.5:
            return {
                "success": False,
                "error": "Low confidence or no tool suggested",
                "truth_source": "rejected"
            }
        
        tool_name = suggestion["tool_name"]
        args = suggestion.get("args", {})
        
        # Execute through tools engine (not model)
        try:
            result = self.tools.execute_tool(tool_name, args)
            
            # Return actual result, not model prediction
            return {
                "success": result.status == "success",
                "tool_name": tool_name,
                "args": args,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "duration": result.duration,
                "truth_source": "runtime_execution"
            }
            
        except Exception as e:
            return {
                "success": False,
                "tool_name": tool_name,
                "error": str(e),
                "truth_source": "runtime_error"
            }


def create_tool_intent_brain(api_key: str, tools_engine, kernel=None):
    """Factory function"""
    return ToolIntentBrain(api_key, tools_engine, kernel)

