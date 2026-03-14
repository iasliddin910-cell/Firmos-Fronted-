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
import traceback
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
        # LAYER 5: CENTRAL KERNEL (THE HEART)
        # =============================================
        
        # 7. Central Kernel - Orchestration (MUST be created first)
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
        # LAYER 6: BRAIN (Native Function Calling)
        # =============================================
        
        # 8. Native Brain - Tool calling via OpenAI functions (created AFTER kernel)
        logger.info("🧠 Initializing Native Brain (Function Calling)...")
        from agent.native_brain import create_native_brain
        self.brain = create_native_brain(self.api_key, self.tools, kernel=self.kernel, sandbox=self.sandbox, approval_engine=self.approval_engine)
        
        # Connect kernel to brain (bi-directional)
        self.kernel.native_brain = self.brain
        
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
        
        # =============================================
        # LAYER 10: HEALTH CHECK (CRITICAL)
        # =============================================
        
        # Deep health check after all modules initialized
        logger.info("🏥 Running deep health check...")
        from agent.health_check import create_health_checker
        self.health_checker = create_health_checker()
        
        # Run comprehensive health verification
        health_result = self.health_checker.check_all(self)
        
        # Log health status
        logger.info(f"🏥 Health Status: {health_result['status']}")
        for result in health_result.get('results', []):
            status_icon = "✅" if result['status'] == 'healthy' else "⚠️" if result['status'] == 'degraded' else "❌"
            logger.info(f"  {status_icon} {result['module']}: {result['message']}")
        
        # Enable safe mode if critical failures detected
        if health_result['status'] == 'unhealthy':
            logger.error("❌ Critical failures detected - enabling safe mode")
            self.health_checker.enable_safe_mode()
            self.safe_mode = True
        else:
            self.safe_mode = False
        
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
        
        # Check if in safe mode (kernel failed)
        if getattr(self, 'safe_mode', False):
            logger.warning("⚠️ Running in SAFE MODE - using brain fallback")
            return self._safe_mode_handle(user_message)
        
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
            
            # Log kernel failure to telemetry
            if hasattr(self, 'health_checker'):
                from agent.health_check import HealthTelemetry
                telemetry = HealthTelemetry()
                telemetry.log_event("FAILURE", "kernel_runtime", {
                    "error": str(e),
                    "traceback": traceback.format_exc()
                })
            
            # Fallback to brain if kernel fails
            logger.info("🔄 Falling back to brain...")
            result = self.brain.think(user_message)
            
            # Secret redaction
            if hasattr(self, "secret_guard"):
                result = self.secret_guard.redact(result)
            return result
    
    def _safe_mode_handle(self, user_message: str) -> str:
        """
        Handle messages in safe mode (kernel failed)
        Uses brain fallback with limited functionality
        """
        logger.warning(f"🛡️ SAFE MODE: Processing '{user_message[:30]}...'")
        
        try:
            # Use brain as fallback
            result = self.brain.think(user_message)
            
            # Secret redaction
            if hasattr(self, "secret_guard"):
                result = self.secret_guard.redact(result)
                
            return result
            
        except Exception as e:
            logger.error(f"Safe mode error: {e}")
            return f"⚠️ Safe Mode: Tizim cheklangan holatda. Xatolik: {str(e)}"
    
    def submit_task(self, task: str) -> str:
        """Public method for external callers (Telegram, etc.)"""
        return self.handle_message(task)
    
    def _is_system_command(self, message: str) -> bool:
        """Check if message is a direct system command"""
        commands = [
            "/system", "/time", "/files", "/clear", "/help", "/memory",
            "/status", "/health", "/approve", "/deny", "/jobs",
            "tizim haqida", "vaqt qancha", "fayllar ro'yxat"
        ]
        return any(cmd in message.lower() for cmd in commands)
    
    def _execute_system_command(self, message: str) -> str:
        """Execute direct system commands"""
        
        # Status command - show kernel status
        if "/status" in message.lower():
            status = self.kernel.get_status() if hasattr(self.kernel, 'get_status') else "N/A"
            
            # Add health check info
            health_info = ""
            if hasattr(self, 'health_checker'):
                health = self.health_checker.check_all(self)
                health_info = f"\n\n🏥 Health: {health['status']}"
                health_info += f"\n- Healthy: {health['healthy']}"
                health_info += f"\n- Degraded: {health['degraded']}"
                health_info += f"\n- Failed: {health['failed']}"
                
                if hasattr(self, 'safe_mode') and self.safe_mode:
                    health_info += "\n⚠️ SAFE MODE ACTIVE"
            
            return f"Status: {status}{health_info}"
        
        # Health command - show detailed health status
        if "/health" in message.lower():
            if hasattr(self, 'health_checker'):
                health = self.health_checker.check_all(self)
                result = f"🏥 **Health Status: {health['status']}**\n\n"
                result += f"Total Checks: {health['total_checks']}\n"
                result += f"✅ Healthy: {health['healthy']}\n"
                result += f"⚠️ Degraded: {health['degraded']}\n"
                result += f"❌ Failed: {health['failed']}\n\n"
                result += "**Module Details:**\n"
                for r in health.get('results', []):
                    icon = "✅" if r['status'] == 'healthy' else "⚠️" if r['status'] == 'degraded' else "❌"
                    result += f"{icon} {r['module']}: {r['message']}\n"
                
                if health.get('failed_modules'):
                    result += f"\n⚠️ Failed Modules: {', '.join(health['failed_modules'])}"
                
                if hasattr(self, 'safe_mode') and self.safe_mode:
                    result += "\n\n⚠️ **SAFE MODE ACTIVE**"
                
                return result
            return "Health checker not available"
        
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
