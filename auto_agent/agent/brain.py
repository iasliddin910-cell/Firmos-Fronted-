"""
OmniAgent X - Brain (LLM Integration)
=====================================
The most important part - AI thinking and decision making
"""
import json
import logging
from typing import List, Dict, Optional
import openai
from config import settings

logger = logging.getLogger(__name__)


class AgentBrain:
    """
    The AI Brain - handles all LLM interactions and decision making
    """
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.model = settings.OPENAI_MODEL
        self.temperature = settings.OPENAI_TEMPERATURE
        self.max_tokens = settings.OPENAI_MAX_TOKENS
        self.conversation_history: List[Dict] = []
        
        # Set up OpenAI client
        openai.api_key = api_key
        
        logger.info(f"🧠 Agent Brain initialized with {self.model}")
    
    def _build_system_prompt(self) -> str:
        """Build the system prompt that defines agent capabilities"""
        return """You are OmniAgent X - An extremely powerful autonomous AI assistant that can:
        
🎯 CORE CAPABILITIES:
- Write and execute code in ANY programming language (Python, JavaScript, C++, Java, etc.)
- Browse the internet, search, and extract web data
- Read, write, and manage files on the computer
- Execute terminal commands
- Take screenshots and analyze visual content
- Launch and control applications
- Analyze data and generate insights
- Perform cybersecurity assessments (with permission)

🤖 AUTONOMOUS BEHAVIOR:
- When given a task, BREAK IT DOWN into smaller steps
- Execute each step INDEPENDENTLY
- VERIFY results after each step
- CORRECT mistakes automatically
- REPORT progress to the user

💻 CODE EXECUTION:
- Write clean, efficient code
- Execute code safely and return results
- Debug and fix errors
- Can create entire projects from scratch

🌐 WEB TASKS:
- Search for information online
- Navigate websites automatically
- Extract specific data from web pages
- Monitor websites for changes

📁 FILE OPERATIONS:
- Create, read, update, delete files
- Organize project structures
- Search for files by content or name

🔐 SECURITY:
- Only perform security tests with explicit user permission
- Never hack or breach systems without consent
- Report vulnerabilities responsibly

⚡ RESPONSE FORMAT:
- Be concise but thorough
- Show your thinking process for complex tasks
- Ask for clarification when needed
- Use code blocks for any code
- Use emojis to make responses engaging

Remember: You are AUTONOMOUS - take action, don't just suggest!"""
    
    def think(self, user_message: str, tools_results: Optional[str] = None) -> str:
        """
        Main thinking function - processes user request and generates response
        """
        # Add user message to history
        self.conversation_history.append({
            "role": "user",
            "content": user_message
        })
        
        # Add tools results if any
        if tools_results:
            self.conversation_history.append({
                "role": "system",
                "content": f"Tool execution results:\n{tools_results}"
            })
        
        # Build messages for API call
        messages = [
            {"role": "system", "content": self._build_system_prompt()}
        ] + self.conversation_history[-settings.MAX_HISTORY_MESSAGES:]
        
        try:
            logger.info(f"🤔 Thinking... (history: {len(self.conversation_history)} messages)")
            
            response = openai.ChatCompletion.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            
            ai_response = response.choices[0].message.content
            
            # Add AI response to history
            self.conversation_history.append({
                "role": "assistant",
                "content": ai_response
            })
            
            logger.info(f"✅ Response generated ({len(ai_response)} chars)")
            return ai_response
            
        except Exception as e:
            logger.error(f"❌ Error in thinking: {e}")
            return f"❌ Xatolik yuz berdi: {str(e)}\n\nIltimos, qayta urinib ko'ring yoki API kalitingizni tekshiring."
    
    def reset_conversation(self):
        """Reset conversation history"""
        self.conversation_history = []
        logger.info("🗑️ Conversation history cleared")
    
    def get_conversation_summary(self) -> str:
        """Get summary of conversation"""
        return f"Hozirgi sessiyada {len(self.conversation_history)} ta xabar bor"
    
    def save_session(self, filepath):
        """Save conversation to file"""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self.conversation_history, f, ensure_ascii=False, indent=2)
            logger.info(f"💾 Session saved to {filepath}")
        except Exception as e:
            logger.error(f"❌ Failed to save session: {e}")
    
    def load_session(self, filepath):
        """Load conversation from file"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                self.conversation_history = json.load(f)
            logger.info(f"📂 Session loaded from {filepath}")
        except Exception as e:
            logger.error(f"❌ Failed to load session: {e}")