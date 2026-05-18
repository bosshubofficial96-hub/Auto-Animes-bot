"""
Error Handlers for ✦ ＡＵＴＯ ＡＮＩＭＥ ✦
"""

import traceback
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from bot.config import Config
from bot.database.database import DatabaseManager
from bot.database.models import TaskStatus
from bot.utils.logger import setup_logger


class ErrorHandlers:
    """Handler for all bot errors"""

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.logger = setup_logger("error_handlers")

    async def handle_error(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle all errors that occur in the bot"""
        error = context.error
        error_traceback = traceback.format_exc()

        self.logger.error(f"Error occurred: {error}")
        self.logger.debug(f"Traceback: {error_traceback}")

        import html
        update_str = html.escape(str(update)[:300]) if update else "N/A"
        tb_str = html.escape(error_traceback[-500:])
        error_message = (
            f"⚠️ <b>Bot Error Occurred</b>\n\n"
            f"<b>Type:</b> <code>{html.escape(type(error).__name__)}</code>\n"
            f"<b>Message:</b> <code>{html.escape(str(error)[:200])}</code>\n\n"
            f"<b>Update:</b>\n<pre>{update_str}</pre>\n\n"
            f"<b>Traceback:</b>\n<pre>{tb_str}</pre>\n\n"
            f"{Config.FOOTER}"
        )

        await self._send_to_admin_channel(error_message)

        if update and update.effective_chat:
            try:
                await update.effective_chat.send_message(
                    "⚠️ <b>An error occurred while processing your request.</b>\n\n"
                    "Administrators have been notified.\n\n"
                    f"{Config.FOOTER}",
                    parse_mode=ParseMode.HTML
                )
            except Exception:
                pass

        if isinstance(error, TimeoutError):
            await self._handle_timeout_error(update, context)
        elif isinstance(error, ConnectionError):
            await self._handle_connection_error(update, context)
        elif "Rate limit" in str(error) or "Too Many Requests" in str(error):
            await self._handle_rate_limit(update, context)

    async def _send_to_admin_channel(self, message: str):
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
        self.logger.warning("Timeout error occurred")

    async def _handle_connection_error(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.logger.warning("Connection error occurred")
        await self._send_to_admin_channel(
            "🌐 <b>Connection Error Alert</b>\n\n"
            "The bot is experiencing connection issues.\n"
            "Check network and API endpoints."
        )

    async def _handle_rate_limit(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.logger.warning("Rate limit hit")

    async def log_task_failure(self, task_id: str, error: str):
        """Log task failure to database and admin channel"""
        await self.db_manager.update_task_status(task_id, TaskStatus.FAILED, error)
        await self._send_to_admin_channel(
            f"❌ <b>Task Failed</b>\n\n"
            f"Task ID: <code>{task_id}</code>\n"
            f"Error: <code>{error[:200]}</code>\n\n"
            f"Use <code>/redownload {task_id}</code> to retry.\n\n{Config.FOOTER}"
        )
