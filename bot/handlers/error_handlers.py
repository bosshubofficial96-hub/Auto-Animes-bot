"""
Error Handlers for ✦ ＡＵＴＯ ＡＮＩＭＥ ✦
"""

import traceback
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from bot.config import Config
from bot.database.database import DatabaseManager
from bot.utils.logger import setup_logger


class ErrorHandlers:
    """Handler for all bot errors"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.logger = setup_logger("error_handlers")
    
    async def handle_error(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle all errors that occur in the bot"""
        
        # Get error details
        error = context.error
        error_traceback = traceback.format_exc()
        
        # Log error
        self.logger.error(f"Error occurred: {error}")
        self.logger.debug(f"Traceback: {error_traceback}")
        
        # Prepare error message for admin
        error_message = f"""
⚠️ <b>Bot Error Occurred</b>

<b>Error Type:</b> <code>{type(error).__name__}</code>
<b>Error Message:</b> <code>{str(error)[:200]}</code>

<b>Update:</b>
<pre>{str(update)[:300]}</pre>

<b>Traceback:</b>
<pre>{error_traceback[:500]}</pre>

{Config.FOOTER}
        """
        
        # Send to admin log channel
        await self._send_to_admin_channel(error_message)
        
        # Try to notify user if possible
        if update and update.effective_chat:
            try:
                await update.effective_chat.send_message(
                    "⚠️ <b>An error occurred while processing your request.</b>\n\n"
                    "The bot administrators have been notified and will fix the issue soon.\n\n"
                    f"{Config.FOOTER}",
                    parse_mode=ParseMode.HTML
                )
            except:
                pass
        
        # Handle specific error types
        if isinstance(error, TimeoutError):
            await self._handle_timeout_error(update, context)
        elif isinstance(error, ConnectionError):
            await self._handle_connection_error(update, context)
        elif "Rate limit" in str(error):
            await self._handle_rate_limit(update, context)
    
    async def _send_to_admin_channel(self, message: str):
        """Send error message to admin channel"""
        try:
            from telegram import Bot
            bot = Bot(token=Config.BOT_TOKEN)
            await bot.send_message(
                chat_id=Config.ADMIN_LOG_CHANNEL,
                text=message,
                parse_mode=ParseMode.HTML
            )
        except Exception as e:
            self.logger.critical(f"Failed to send error to admin channel: {e}")
    
    async def _handle_timeout_error(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle timeout errors specifically"""
        self.logger.warning("Timeout error occurred - retrying...")
        
        # Implement retry logic here
        pass
    
    async def _handle_connection_error(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle connection errors"""
        self.logger.warning("Connection error - checking network...")
        
        # Notify admin about connection issues
        await self._send_to_admin_channel(
            "🌐 <b>Connection Error Alert</b>\n\n"
            "The bot is experiencing connection issues.\n"
            "Check network connectivity and API endpoints."
        )
    
    async def _handle_rate_limit(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle rate limit errors"""
        self.logger.warning("Rate limit hit - implementing backoff...")
        
        # Implement exponential backoff
        pass
    
    async def log_task_failure(self, task_id: str, error: str):
        """Log task failure to database and admin channel"""
        # Update task in database
        await self.db_manager.update_task_status(task_id, TaskStatus.FAILED, error)
        
        # Send admin notification
        await self._send_to_admin_channel(
            f"❌ <b>Task Failed</b>\n\n"
            f"Task ID: <code>{task_id}</code>\n"
            f"Error: <code>{error[:200]}</code>\n\n"
            f"Use <code>/redownload {task_id}</code> to retry."
        )
