"""
OmniAgent X - Main Application
===============================
The entry point that brings everything together
"""
import os
import sys
import logging
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Import configuration
from config import settings

# Import agent components
from agent.brain import AgentBrain
from agent.tools import ToolsEngine
from agent.memory import AgentMemory
from agent.ui import AgentUI


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class OmniAgent:
    """
    Main OmniAgent X application - brings all components together
    """
    
    def __init__(self):
        logger.info("🚀 Initializing OmniAgent X...")
        
        # Get API key
        self.api_key = self._get_api_key()
        
        if not self.api_key:
            logger.error("❌ No API key found!")
            sys.exit("❌ Iltimos, OPENAI_API_KEY muhit o'zgaruvchisini o'rnating!")
        
        # Initialize components
        logger.info("🧠 Initializing AI Brain...")
        self.brain = AgentBrain(self.api_key)
        
        logger.info("🔧 Initializing Tools Engine...")
        self.tools = ToolsEngine()
        
        logger.info("💾 Initializing Memory...")
        self.memory = AgentMemory()
        
        logger.info("🎨 Initializing User Interface...")
        self.ui = AgentUI(app_callback=self.handle_message)
        
        logger.info("✅ OmniAgent X ready!")
    
    def _get_api_key(self) -> str:
        """Get OpenAI API key from environment or config"""
        # Try environment variable first
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            return api_key
        
        # Try reading from a local file
        key_file = Path(__file__).parent / "api_key.txt"
        if key_file.exists():
            return key_file.read_text().strip()
        
        return None
    
    def handle_message(self, user_message: str) -> str:
        """
        Main message handler - the brain of the agent
        This is where the magic happens!
        """
        logger.info(f"📩 Received: {user_message[:50]}...")
        
        # Check for quick system commands
        if self._is_system_command(user_message):
            return self._execute_system_command(user_message)
        
        # Let AI think and decide what to do
        response = self.brain.think(user_message)
        
        # Save to memory
        self.memory.add_message("user", user_message)
        self.memory.add_message("assistant", response)
        
        return response
    
    def _is_system_command(self, message: str) -> bool:
        """Check if message is a direct system command"""
        commands = [
            "/system", "/time", "/files", "/clear", "/help",
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
        
        if "tozalash" in message.lower() or "/clear" in message.lower():
            self.brain.reset_conversation()
            self.memory.clear()
            return "✅ Tozalandi!"
        
        if "yordam" in message.lower() or "/help" in message.lower():
            return self._get_help()
        
        return "Noma'lum buyruq"
    
    def _get_help(self) -> str:
        """Get help information"""
        return """📖 **Yordam**

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
        self.memory.save_to_file()
        self.brain.save_session(settings.SESSION_FILE)


def main():
    """Entry point"""
    try:
        # Initialize agent
        agent = OmniAgent()
        
        # Start Telegram Bot (optional - comment out if not needed)
        try:
            from agent.telegram_bot import start_telegram_bot
            bot_token = "8765144389:AAFy-I7PGVkmzjNY_G_j66JsgdZlYQ4Z06k"
            print(f"📱 Telegram Bot: {start_telegram_bot(bot_token, agent)}")
        except Exception as e:
            print(f"⚠️ Telegram bot xatosi: {e}")
        
        # Start GUI
        print("🚀 OmniAgent X ishga tushdi!")
        print("Telegram da: @omniagentx_bot")
        agent.run()
        
    except KeyboardInterrupt:
        logger.info("👋 Exiting...")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()