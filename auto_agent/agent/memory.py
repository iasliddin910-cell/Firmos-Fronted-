"""
OmniAgent X - Memory (Chat History Management)
===============================================
Manages conversation history and persistent storage
"""
import json
import logging
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
from config import settings

logger = logging.getLogger(__name__)


class AgentMemory:
    """
    Manages conversation history and learned information
    """
    
    def __init__(self):
        self.messages: List[Dict] = []
        self.learnings: Dict = {}  # Key information the agent remembers
        self.session_start = datetime.now()
        logger.info("💾 Agent Memory initialized")
    
    def add_message(self, role: str, content: str):
        """Add a message to history"""
        self.messages.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        
        # Keep only last N messages
        if len(self.messages) > settings.MAX_HISTORY_MESSAGES:
            self.messages = self.messages[-settings.MAX_HISTORY_MESSAGES:]
    
    def get_history(self, limit: Optional[int] = None) -> List[Dict]:
        """Get conversation history"""
        if limit:
            return self.messages[-limit:]
        return self.messages
    
    def get_context_string(self) -> str:
        """Get conversation history as a string for context"""
        history_text = []
        for msg in self.messages[-10:]:  # Last 10 messages
            role_emoji = {"user": "👤", "assistant": "🤖", "system": "⚙️"}.get(msg["role"], "📝")
            history_text.append(f"{role_emoji} {msg['role'].upper()}: {msg['content'][:200]}")
        
        return "\n".join(history_text)
    
    def learn(self, key: str, value: any):
        """Store important information"""
        self.learnings[key] = value
        logger.info(f"📚 Learned: {key}")
    
    def recall(self, key: str) -> any:
        """Retrieve learned information"""
        return self.learnings.get(key)
    
    def clear(self):
        """Clear all memory"""
        self.messages = []
        self.learnings = {}
        logger.info("🗑️ Memory cleared")
    
    def save_to_file(self, filepath: Optional[Path] = None):
        """Save memory to file"""
        if filepath is None:
            filepath = settings.SESSION_FILE
        
        try:
            data = {
                "session_start": self.session_start.isoformat(),
                "messages": self.messages,
                "learnings": self.learnings
            }
            
            filepath.parent.mkdir(parents=True, exist_ok=True)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"💾 Memory saved to {filepath}")
            return True
        
        except Exception as e:
            logger.error(f"❌ Failed to save memory: {e}")
            return False
    
    def load_from_file(self, filepath: Optional[Path] = None):
        """Load memory from file"""
        if filepath is None:
            filepath = settings.SESSION_FILE
        
        if not filepath.exists():
            logger.info("No saved session found")
            return False
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.messages = data.get("messages", [])
            self.learnings = data.get("learnings", {})
            self.session_start = datetime.fromisoformat(data.get("session_start", datetime.now().isoformat()))
            
            logger.info(f"📂 Memory loaded from {filepath}")
            return True
        
        except Exception as e:
            logger.error(f"❌ Failed to load memory: {e}")
            return False
    
    def get_stats(self) -> str:
        """Get memory statistics"""
        return f"""💾 Xotira statistikasi:
- Xabarlar soni: {len(self.messages)}
- O'rganilgan ma'lumotlar: {len(self.learnings)}
- Sessiya boshlanishi: {self.session_start.strftime('%H:%M:%S')}
"""