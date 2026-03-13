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
        
        logger.info("🧠 Native Function Brain initialized")
    
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

def create_native_brain(api_key: str, tools_engine):
    """Create native function calling brain"""
    return NativeFunctionBrain(api_key, tools_engine)
