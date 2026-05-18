"""
Main Entry Point for ✦ ＡＵＴＯ ＡＮＩＭＥ ✦ Bot
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    Defaults
)
from telegram.constants import ParseMode

from bot.config import Config
from bot.database.database import DatabaseManager
from bot.handlers.admin_handlers import AdminHandlers
from bot.handlers.user_handlers import UserHandlers
from bot.handlers.callback_handlers import CallbackHandlers
from bot.handlers.error_handlers import ErrorHandlers
from bot.services.scheduler_service import SchedulerService
from bot.utils.logger import setup_logger


async def main():
    """Main entry point for the bot"""
    
    # Setup logging
    logger = setup_logger()
    logger.info("🚀 Starting ✦ ＡＵＴＯ ＡＮＩＭＥ ✦ Bot...")
    
    # Validate configuration
    try:
        Config.validate()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        return
    
    # Initialize database
    db_manager = DatabaseManager(Config.DATABASE_PATH)
    await db_manager.initialize()
    logger.info("✅ Database initialized")
    
    # Create application
    defaults = Defaults(parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=False)
    application = ApplicationBuilder() \
        .token(Config.BOT_TOKEN) \
        .defaults(defaults) \
        .build()
    
    # Initialize handlers
    admin_handlers = AdminHandlers(db_manager)
    user_handlers = UserHandlers(db_manager)
    callback_handlers = CallbackHandlers(db_manager)
    error_handlers = ErrorHandlers(db_manager)
    
    # Register command handlers
    # Admin commands
    application.add_handler(CommandHandler("add_admin", admin_handlers.add_admin))
    application.add_handler(CommandHandler("set_max_requests", admin_handlers.set_max_requests))
    application.add_handler(CommandHandler("view_requests", admin_handlers.view_requests))
    application.add_handler(CommandHandler("set_request_time", admin_handlers.set_request_time))
    application.add_handler(CommandHandler("del_timer", admin_handlers.del_timer))
    application.add_handler(CommandHandler("addtask", admin_handlers.add_task))
    application.add_handler(CommandHandler("redownload", admin_handlers.redownload))
    application.add_handler(CommandHandler("broadcast", admin_handlers.broadcast))
    application.add_handler(CommandHandler("stats", admin_handlers.stats))
    
    # User commands
    application.add_handler(CommandHandler("start", user_handlers.start))
    application.add_handler(CommandHandler("help", user_handlers.help_command))
    application.add_handler(CommandHandler("request", user_handlers.request_anime))
    application.add_handler(CommandHandler("latest", user_handlers.latest_uploads))
    application.add_handler(CommandHandler("airing", user_handlers.airing_today))
    application.add_handler(CommandHandler("search", user_handlers.search_anime))
    application.add_handler(CommandHandler("status", user_handlers.check_status))
    
    # Message handlers for #request format
    application.add_handler(MessageHandler(
        filters.Regex(r'^#request\s+.+'), user_handlers.request_hashtag
    ))
    
    # Callback query handler for inline buttons
    application.add_handler(CallbackQueryHandler(callback_handlers.handle_callback))
    
    # Error handler
    application.add_error_handler(error_handlers.handle_error)
    
    # Initialize scheduler service
    scheduler_service = SchedulerService(application, db_manager)
    await scheduler_service.initialize()
    
    # Start pipeline worker (if needed)
    # This can be a background task that processes queued items
    
    # Start bot
    logger.info("🤖 Bot is starting...")
    
    # Start polling
    await application.initialize()
    await application.start()
    
    # Start webhook or polling
    await application.updater.start_polling(drop_pending_updates=True)
    
    logger.info(f"✅ ✦ ＡＵＴＯ ＡＮＩＭＥ ✦ is running!")
    
    # Keep bot running
    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        logger.info("🛑 Bot is stopping...")
        await application.updater.stop()
        await application.stop()
        await application.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
