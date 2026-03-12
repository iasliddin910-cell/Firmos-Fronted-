"""
OmniAgent X - Telegram Bot (Uzoqdan Boshqarish)
================================================
Telegram orqali kompyuterni boshqarish
"""
import os
import logging
import json
from pathlib import Path
from typing import Optional, Dict
from datetime import datetime

logger = logging.getLogger(__name__)

# Try to import telegram
try:
    from telegram import Update
    from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
    TELEGRAM_AVAILABLE = True
except:
    TELEGRAM_AVAILABLE = False
    logger.warning("python-telegram-bot not available")


class TelegramBot:
    """
    Telegram bot - telefoningizdan OmniAgent ni boshqarish
    """
    
    def __init__(self, token: str, agent):
        if not TELEGRAM_AVAILABLE:
            raise ImportError("python-telegram-bot o'rnatilmagan")
        
        self.token = token
        self.agent = agent
        self.app = None
        self.authorized_users = set()  # User IDs who can use the bot
        
        logger.info("📱 Telegram Bot initialized")
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """ /start command """
        user_id = update.effective_user.id
        
        await update.message.reply_text(
            "🦾 *OmniAgent X Telegram Bot* ga xush kelibsiz!\n\n"
            "Bu bot orqali kompyuteringizni boshqarishingiz mumkin.\n\n"
            "Mavjud buyruqlar:\n"
            "/help - Yordam\n"
            "/screenshot - Screenshot olish\n"
            "/system - Tizim ma'lumot\n"
            "/files - Fayllar ro'yxati\n"
            "Boshqa buyruqlar: Matn yozing, agent javob beradi",
            parse_mode="Markdown"
        )
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """ /help command """
        help_text = """
🦾 *OmniAgent X - Yordam*

*Asosiy buyruqlar:*
/start - Botni ishga tushirish
/help - Yordam
/screenshot - Screenshot olish
/system - Tizim ma'lumot
/files - Fayllar ro'yxati
/execute <kod> - Python kod ishga tushirish

*Foydalanish:*
- Matn yozing - Agent javob beradi
- Screenshot so'rang - Ekran rasmi yuboriladi
- Buyruq bering - Kompyuteringizda bajariladi

*Eslatma:* Faqat ruxsat etilgan foydalanuvchilar ishlatishi mumkin.
"""
        await update.message.reply_text(help_text, parse_mode="Markdown")
    
    async def screenshot_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """ /screenshot command """
        try:
            from agent.tools import ToolsEngine
            tools = ToolsEngine()
            result = tools.take_screenshot()
            
            # Extract filepath
            if "saqlandi:" in result:
                filepath = result.split("saqlandi: ")[1].strip()
                
                # Send photo
                with open(filepath, 'rb') as photo:
                    await update.message.reply_photo(photo, caption="📸 Screenshot")
            else:
                await update.message.reply_text(result)
                
        except Exception as e:
            await update.message.reply_text(f"❌ Xatolik: {str(e)}")
    
    async def system_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """ /system command """
        try:
            from agent.tools import ToolsEngine
            tools = ToolsEngine()
            result = tools.get_system_info()
            await update.message.reply_text(result)
        except Exception as e:
            await update.message.reply_text(f"❌ Xatolik: {str(e)}")
    
    async def files_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """ /files command """
        try:
            from agent.tools import ToolsEngine
            tools = ToolsEngine()
            result = tools.list_directory(".")
            await update.message.reply_text(result[:4000])  # Limit length
        except Exception as e:
            await update.message.reply_text(f"❌ Xatolik: {str(e)}")
    
    async def execute_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """ /execute <code> command """
        try:
            # Extract code from message
            code = update.message.text.replace("/execute", "").strip()
            
            if not code:
                await update.message.reply_text("❌ Kod kiritilmagan. Foydalanish: /execute print('Hello')")
                return
            
            from agent.tools import ToolsEngine
            tools = ToolsEngine()
            result = tools.execute_code(code, "python")
            
            await update.message.reply_text(f"💻 *Natija:*\n\n{result}", parse_mode="Markdown")
            
        except Exception as e:
            await update.message.reply_text(f"❌ Xatolik: {str(e)}")
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle regular messages - forward to agent"""
        try:
            user_message = update.message.text
            
            # Show typing indicator
            await context.bot.send_chat_action(
                chat_id=update.effective_message.chat_id,
                action="typing"
            )
            
            # Process through agent
            response = self.agent.handle_message(user_message)
            
            # Send response (split if too long)
            if len(response) > 4000:
                # Split into chunks
                chunks = [response[i:i+4000] for i in range(0, len(response), 4000)]
                for chunk in chunks:
                    await update.message.reply_text(chunk)
            else:
                await update.message.reply_text(response)
                
        except Exception as e:
            await update.message.reply_text(f"❌ Xatolik: {str(e)}")
    
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Error handler"""
        logger.error(f"Telegram error: {context.error}")
        if update and update.effective_message:
            await update.effective_message.reply_text(
                f"❌ Xatolik yuz berdi: {str(context.error)}"
            )
    
    def run(self):
        """Run the bot"""
        if not TELEGRAM_AVAILABLE:
            logger.error("python-telegram-bot o'rnatilmagan!")
            return
        
        # Create application
        self.app = Application.builder().token(self.token).build()
        
        # Add handlers
        self.app.add_handler(CommandHandler("start", self.start_command))
        self.app.add_handler(CommandHandler("help", self.help_command))
        self.app.add_handler(CommandHandler("screenshot", self.screenshot_command))
        self.app.add_handler(CommandHandler("system", self.system_command))
        self.app.add_handler(CommandHandler("files", self.files_command))
        self.app.add_handler(CommandHandler("execute", self.execute_command))
        
        # Message handler
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
        # Error handler
        self.app.add_error_handler(self.error_handler)
        
        logger.info("📱 Telegram Bot ishga tushirilmoqda...")
        
        # Run (polling)
        self.app.run_polling(poll_interval=1.0)


class TelegramBotManager:
    """
    Telegram bot boshqaruvchisi
    """
    
    def __init__(self):
        self.bot = None
        self.is_running = False
    
    def start_bot(self, token: str, agent) -> str:
        """Botni ishga tushirish"""
        if not token:
            return "❌ Telegram token kiritilmagan. Bot.run(TOKEN) ni chaqiring"
        
        try:
            self.bot = TelegramBot(token, agent)
            # Start in background
            import threading
            thread = threading.Thread(target=self.bot.run, daemon=True)
            thread.start()
            self.is_running = True
            
            return "📱 Telegram Bot ishga tushdi!\n\nEndi telefoningizdan /start yozing"
        
        except Exception as e:
            return f"❌ Xatolik: {str(e)}\n\nKutubxona o'rnatilmagan bo'lishi mumkin:\npip install python-telegram-bot"
    
    def stop_bot(self) -> str:
        """Botni to'xtatish"""
        if self.bot and self.bot.app:
            self.bot.app.stop()
            self.is_running = False
            return "📱 Telegram Bot to'xtatildi"
        return "❌ Bot ishlamaydi"
    
    def get_status(self) -> str:
        """Holatni olish"""
        status = "ishlaydi" if self.is_running else "to'xtatilgan"
        return f"Telegram Bot: {status}"


# Global instance
telegram_manager = TelegramBotManager()

def start_telegram_bot(token: str, agent) -> str:
    """Start Telegram bot"""
    return telegram_manager.start_bot(token, agent)

def stop_telegram_bot() -> str:
    """Stop Telegram bot"""
    return telegram_manager.stop_bot()