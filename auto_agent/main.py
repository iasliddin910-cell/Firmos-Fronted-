"""
OmniAgent X - Main Application (FINAL ARCHITECTURE)
================================================
The operating system entrypoint for the agent

Correct flow:
1. secret_guard
2. sandbox
3. approval_engine
4. tools_engine
5. native_brain
6. kernel (CENTRAL)
7. memory systems
8. learning_pipeline
9. benchmark + regression
10. self_improvement
11. tool_factory
12. ui + telegram
"""
import os
import sys
import asyncio
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Import configuration
from config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class OmniAgent:
    """
    Main OmniAgent X application - Complete Architecture
    
    All components integrated with kernel as central orchestration
    """
    
    def __init__(self):
        logger.info("🚀 Initializing OmniAgent X (Complete Architecture)...")
        
        # =============================================
        # LAYER 1: SECURITY
        # =============================================
        
        # 1. Secret Guard - First and always active
        logger.info("🔐 Initializing Secret Guard...")
        from agent.secret_guard import create_secret_guard
        self.secret_guard = create_secret_guard()
        
        # =============================================
        # LAYER 2: SANDBOX & EXECUTION
        # =============================================
        
        # 2. Sandbox - Command execution isolation
        logger.info("🛡️ Initializing Sandbox...")
        from agent.sandbox import create_sandbox, ExecutionMode
        workspace = str(Path(__file__).parent)
        self.sandbox = create_sandbox(workspace, ExecutionMode.NORMAL)
        
        # 3. Approval Engine - Tool approval workflow
        logger.info("✅ Initializing Approval Engine...")
        from agent.approval import create_approval_engine
        self.approval_engine = create_approval_engine()
        
        # =============================================
        # LAYER 3: CORE TOOLS
        # =============================================
        
        # 4. Tools Engine - Core tool execution
        logger.info("🔧 Initializing Tools Engine...")
        from agent.tools import ToolsEngine
        self.tools = ToolsEngine(
            sandbox=self.sandbox,
            approval_engine=self.approval_engine,
            secret_guard=self.secret_guard
        )
        
        # 5. API Key - Get from environment
        self.api_key = self._get_api_key()
        
        if not self.api_key:
            logger.error("❌ No API key found!")
            sys.exit("❌ Set OPENAI_API_KEY in .env!")
        
        # =============================================
        # LAYER 4: MEMORY SYSTEMS
        # =============================================
        
        # 6. Memory Systems
        logger.info("💾 Initializing Memory Systems...")
        
        # Semantic memory (knowledge)
        from agent.memory_ultimate import get_memory_system
        self.memory = get_memory_system()
        
        # Agent state memory (task-state, run history, etc.)
        from agent.agent_memory import get_agent_memory
        self.agent_memory = get_agent_memory()
        
        # =============================================
        # LAYER 5: BRAIN (Native Function Calling)
        # =============================================
        
        # 7. Native Brain - Tool calling via OpenAI functions
        logger.info("🧠 Initializing Native Brain (Function Calling)...")
        from agent.native_brain import create_native_brain
        self.brain = create_native_brain(self.api_key, self.tools, kernel=self.kernel, sandbox=self.sandbox, approval_engine=self.approval_engine)
        
        # =============================================
        # LAYER 6: CENTRAL KERNEL (THE HEART)
        # =============================================
        
        # 8. Central Kernel - Orchestration
        logger.info("⚡ Initializing Central Kernel...")
        from agent.kernel import create_kernel
        self.kernel = create_kernel(self.api_key, self.tools)
        
        # Connect kernel to other components
        self.kernel.approval_engine = self.approval_engine
        self.kernel.secret_guard = self.secret_guard
        self.kernel.sandbox = self.sandbox
        self.kernel.agent_memory = self.agent_memory
        self.kernel.memory = self.memory
        
        # =============================================
        # LAYER 7: LEARNING & IMPROVEMENT
        # =============================================
        
        # 9. Learning Pipeline
        logger.info("📚 Initializing Learning Pipeline...")
        from agent.learning_pipeline import create_learning_pipeline
        self.learning_pipeline = create_learning_pipeline(self.api_key)
        
        # 10. Benchmark & Regression
        logger.info("📊 Initializing Benchmark & Regression...")
        from agent.benchmark import create_benchmark_suite
        from agent.regression_suite import create_regression_suite
        self.benchmark_suite = create_benchmark_suite(self.brain)
        self.regression_suite = create_regression_suite()
        
        # Connect to kernel
        self.kernel.benchmark_suite = self.benchmark_suite
        self.kernel.regression_suite = self.regression_suite
        
        # 11. Self-Improvement
        logger.info("🔄 Initializing Self-Improvement Engine...")
        from agent.self_improvement import create_self_improvement_engine
        self.self_improvement = create_self_improvement_engine()
        
        # Connect to kernel
        self.kernel.self_improvement = self.self_improvement
        
        # 12. Tool Factory
        logger.info("🏭 Initializing Tool Factory...")
        from agent.tool_factory import create_tool_factory
        self.tool_factory = create_tool_factory(self.api_key)
        
        # Connect to kernel
        self.kernel.tool_factory = self.tool_factory
        
        # =============================================
        # LAYER 8: DEPENDENCY & CODE EXECUTION
        # =============================================
        
        # 13. Dependency Handler
        logger.info("📦 Initializing Dependency Handler...")
        from agent.dependency_handler import create_dependency_manager
        self.dependency_manager = create_dependency_manager(workspace)
        
        # 14. Code Interpreter (Enhanced)
        logger.info("💻 Initializing Code Interpreter...")
        from agent.code_interpreter import CodeInterpreter
        self.code_interpreter = CodeInterpreter(Path(workspace) / "data" / "code_workspace")
        
        # =============================================
        # LAYER 9: UI & TELEGRAM
        # =============================================
        
        # 15. User Interface
        logger.info("🎨 Initializing User Interface...")
        from agent.ui import AgentUI
        self.ui = AgentUI(app_callback=self.handle_message)
        
        # 16. Telegram Bot
        self.telegram_bot = None
        telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
        if telegram_token:
            logger.info("📱 Initializing Telegram Bot...")
            from agent.telegram_bot import start_telegram_bot
            self.telegram_bot = start_telegram_bot(telegram_token, self)
        
        logger.info("=" * 50)
        logger.info("✅ OmniAgent X Ready! (Complete Architecture)")
        logger.info("=" * 50)
    
    def _get_api_key(self) -> str:
        """Get API key from environment only"""
        # Use secret guard for secure access
        return self.secret_guard.get_env("OPENAI_API_KEY")
    
    def handle_message(self, user_message: str) -> str:
        """
        MAIN ENTRY POINT
        
        All user messages go through kernel now!
        Not brain.think() - but kernel.submit_task()
        """
        logger.info(f"📩 Received: {user_message[:50]}...")
        
        # Check for quick system commands first
        if self._is_system_command(user_message):
            return self._execute_system_command(user_message)
        
        # Save to memory
        self.memory.save_conversation([
            {"role": "user", "content": user_message}
        ])
        
        # =============================================
        # CENTRAL FLOW: kernel.submit_task()
        # NOT brain.think()
        # =============================================
        
        try:
            # Use kernel as central orchestrator
            result = self.kernel.submit_task(user_message)
            
            # Save to memory
            self.memory.save_conversation([
                {"role": "assistant", "content": result}
            ])
            
            # Also save to agent memory
            self.agent_memory.complete_task(
                task_id=user_message[:20],
                status="completed"
            )
            
            # Secret redaction
        if hasattr(self, "secret_guard"):
            result = self.secret_guard.redact(result)
        return result
            
        except Exception as e:
            logger.error(f"Error in kernel: {e}")
            # Fallback to brain if kernel fails
            result = self.brain.think(user_message)
            # Secret redaction
        if hasattr(self, "secret_guard"):
            result = self.secret_guard.redact(result)
        return result
    
    def submit_task(self, task: str) -> str:
        """Public method for external callers (Telegram, etc.)"""
        return self.handle_message(task)
    
    def _is_system_command(self, message: str) -> bool:
        """Check if message is a direct system command"""
        commands = [
            "/system", "/time", "/files", "/clear", "/help", "/memory",
            "/status", "/approve", "/deny", "/jobs",
            "tizim haqida", "vaqt qancha", "fayllar ro'yxat"
        ]
        return any(cmd in message.lower() for cmd in commands)
    
    def _execute_system_command(self, message: str) -> str:
        """Execute direct system commands"""
        
        # Status command - show kernel status
        if "/status" in message.lower():
            return self.kernel.get_status()
        
        # Approve command
        if "/approve" in message.lower():
            parts = message.split()
            if len(parts) > 1:
                request_id = parts[1]
                self.approval_engine.approve(request_id, "cli")
                return f"Approved: {request_id}"
            return "Usage: /approve <request_id>"
        
        # Deny command
        if "/deny" in message.lower():
            parts = message.split()
            if len(parts) > 1:
                request_id = parts[1]
                reason = " ".join(parts[2:]) if len(parts) > 2 else "No reason"
                self.approval_engine.deny(request_id, reason, "cli")
                return f"Denied: {request_id}"
            return "Usage: /deny <request_id> [reason]"
        
        # Jobs command
        if "/jobs" in message.lower():
            return self.kernel.get_task_queue_status()
        
        if "tizim" in message.lower() or "/system" in message.lower():
            return self.tools.get_system_info()
        
        if "vaqt" in message.lower() or "/time" in message.lower():
            from datetime import datetime
            return f"Hozirgi vaqt: {datetime.now()}"
        
        if "fayllar" in message.lower() or "/files" in message.lower():
            return self.tools.list_directory(".")
        
        if "xotira" in message.lower() or "/memory" in message.lower():
            return self.agent_memory.get_stats()
        
        if "tozalash" in message.lower() or "/clear" in message.lower():
            self.brain.reset_conversation()
            self.memory.clear()
            return "✅ Tozalandi!"
        
        if "yordam" in message.lower() or "/help" in message.lower():
            return self._get_help()
        
        return "Noma'lum buyruq"
    
    def _get_help(self) -> str:
        """Get help information"""
        return """📖 **OmniAgent X - To'liq Arxitektura**

**Kernel buyruqlari:**
- /status - Tizim holati
- /jobs - Joriy vazifalar
- /approve <id> - Ruxsat berish
- /deny <id> [sabab] - Rad etish

**Boshqa buyruqlar:**
- tizim haqida
- xotira statistikasi
- tozalash
- yordam

**Asosiy oqim:**
Barcha buyruqlar Central Kernel orqali o'tadi!
"""
    
    def run(self):
        """Start the agent"""
        logger.info("🎯 Starting OmniAgent X...")
        
        # Start Telegram Bot if available
        if self.telegram_bot:
            logger.info("📱 Telegram bot active")
        
        # Start UI
        self.ui.run()
    
    def save_state(self):
        """Save agent state before exit"""
        logger.info("💾 Saving state...")
        
        # Save memory
        self.memory.save_conversation([])
        
        # Save agent memory
        self.agent_memory.save_state()


def main():
    """Entry point"""
    try:
        # Initialize agent with complete architecture
        agent = OmniAgent()
        
        # Run agent
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
