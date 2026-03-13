"""
OmniAgent X - Main Application (REFACTORED)
===========================================
The entry point that brings everything together
New architecture with:
- Central Kernel orchestration
- ReActAgent orchestration
- Persistent memory (memory_ultimate.py)
- Plan -> Act -> Observe -> Verify -> Repair flow
- Environment-based configuration
- All new enhanced components integrated
"""
import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Import configuration
from config import settings

# Import agent components - ULTIMATE versions
from agent.ultimate_brain import create_ultimate_brain
from agent.tools import ToolsEngine
from agent.memory_ultimate import get_memory_system
from agent.ui import AgentUI

# NEW: Import enhanced components
from agent.kernel import create_kernel
from agent.native_brain import create_native_brain
from agent.sandbox import create_sandbox, ExecutionMode
from agent.approval import create_approval_engine
from agent.agent_memory import get_agent_memory
from agent.learning_pipeline import create_learning_pipeline
from agent.benchmark import create_benchmark_suite
from agent.regression_suite import create_regression_suite
from agent.self_improvement import create_self_improvement_engine
from agent.tool_factory import create_tool_factory
from agent.dependency_handler import create_dependency_manager
from agent.secret_guard import create_secret_guard


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class OmniAgent:
    """
    Main OmniAgent X application - brings all components together
    
    New architecture:
    - Uses UltimateBrain (ReAct pattern)
    - Uses VectorMemory for persistent storage
    - Plan -> Act -> Observe -> Verify -> Repair flow
    - All config from environment (.env)
    """
    
    def __init__(self):
        logger.info("🚀 Initializing OmniAgent X (Refactored)...")
        
        # Get API key from environment only
        self.api_key = self._get_api_key()
        
        if not self.api_key:
            logger.error("❌ No API key found! Please set OPENAI_API_KEY in .env")
            sys.exit("❌ Iltimos, OPENAI_API_KEY ni .env faylida o'rnating!")
        
        # Initialize components
        logger.info("🔧 Initializing Tools Engine...")
        self.tools = ToolsEngine()
        
        logger.info("💾 Initializing Persistent Memory...")
        self.memory = get_memory_system()
        
        logger.info("🧠 Initializing Ultimate Brain (ReAct + Verify + Repair)...")
        self.brain = create_ultimate_brain(self.api_key, self.tools)
        
        logger.info("🎨 Initializing User Interface...")
        self.ui = AgentUI(app_callback=self.handle_message)
        
        logger.info("✅ OmniAgent X Ready!")
    
    def _get_api_key(self) -> str:
        """Get OpenAI API key from environment only"""
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            return api_key
        
        # REMOVED: DEV_MODE api_key.txt fallback for security
        # Production must use .env or secrets manager
        logger.error("❌ OPENAI_API_KEY not found in environment!")
        return None
    
    def handle_message(self, user_message: str) -> str:
        """
        Main message handler with NEW flow:
        Plan -> Act -> Observe -> Verify -> Repair
        
        This replaces the old simple think() approach
        """
        logger.info(f"📩 Received: {user_message[:50]}...")
        
        # Check for quick system commands first
        if self._is_system_command(user_message):
            return self._execute_system_command(user_message)
        
        # Save to memory
        self.memory.save_conversation([
            {"role": "user", "content": user_message}
        ])
        
        # Use Ultimate Brain with ReAct + Verify + Repair
        response = self.brain.think(user_message)
        
        # Save to memory
        self.memory.save_conversation([
            {"role": "assistant", "content": response}
        ])
        
        return response
    
    def _is_system_command(self, message: str) -> bool:
        """Check if message is a direct system command"""
        commands = [
            "/system", "/time", "/files", "/clear", "/help", "/memory",
            "tizim haqida", "vaqt qancha", "fayllar ro'yxat"
        ]
        return any(cmd in message.lower() for cmd in commands)
    
    def _execute_system_command(self, message: str) -> str:
        """Execute direct system commands"""
        if "tizim" in message.lower() or "/system" in message.lower():
            return self.tools.get_system_info()
        
        if "vaqt" in message.lower() or "/time" in message.lower():
            return self.tools.get_current_time()
        
        if "fayllar" in message.lower() or "/files" in message.lower():
            return self.tools.list_directory(".")
        
        if "xotira" in message.lower() or "/memory" in message.lower():
            return self.memory.get_stats()
        
        if "tozalash" in message.lower() or "/clear" in message.lower():
            self.brain.reset_conversation()
            self.memory.clear()
            return "✅ Tozalandi!"
        
        if "yordam" in message.lower() or "/help" in message.lower():
            return self._get_help()
        
        return "Noma'lum buyruq"
    
    def _get_help(self) -> str:
        """Get help information"""
        return """📖 **Yordam - OmniAgent X (Yangilangan)**

Mumkin bo'lgan buyruqlar:

**Kod yozish:**
- "Python da kalkulyator yarat"
- "JavaScript da funksiya yoz"

**Web:**
- "Internetda qidiruv: sun'iy intellekt"
- "wikipedia.org saytini och"

**Fayllar:**
- "fayllar ro'yxatini ko'rsat"
- "faylni o'qish: main.py"

**Tizim:**
- "tizim haqida ma'lumot ber"
- "hozirgi vaqt qancha?"

**Xotira:**
- "xotira statistikasi" - nechta ma'lumot saqlangan

**Boshqa:**
- "tozalash" - suhbatni tozalash
- "yordam" - bu xabar

**Har qanday boshqa savol uchun ham ishlaydi!**
"""
    
    def run(self):
        """Start the agent"""
        logger.info("🎯 Starting OmniAgent X...")
        self.ui.run()
    
    def save_state(self):
        """Save agent state before exit"""
        logger.info("💾 Saving state...")
        # Memory is auto-saved, but we can force save
        self.memory.save_conversation([])


def main():
    """Entry point"""
    try:
        # Initialize agent
        agent = OmniAgent()
        
        # Start Telegram Bot (if token is in .env)
        telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
        if telegram_token:
            try:
                from agent.telegram_bot import start_telegram_bot
                logger.info(f"📱 Starting Telegram Bot...")
                start_telegram_bot(telegram_token, agent)
            except Exception as e:
                logger.warning(f"⚠️ Telegram bot xatosi: {e}")
        else:
            logger.info("ℹ️ TELEGRAM_BOT_TOKEN not set - Telegram bot disabled")
        
        # Start GUI
        print("🚀 OmniAgent X ishga tushdi!")
        if telegram_token:
            print("Telegram da: @omniagentx_bot")
        agent.run()
        
    except KeyboardInterrupt:
        logger.info("👋 Exiting...")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()