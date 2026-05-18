"""
Main Entry Point for ✦ ＡＵＴＯ ＡＮＩＭＥ ✦ Bot
"""

import asyncio
import logging
import sys
from pathlib import Path

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
    logger = setup_logger()
    logger.info("🚀 Starting ✦ ＡＵＴＯ ＡＮＩＭＥ ✦ Bot...")

    try:
        Config.validate()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        return

    db_manager = DatabaseManager(Config.DATABASE_PATH)
    await db_manager.initialize()
    logger.info("✅ Database initialized")

    defaults = Defaults(parse_mode=ParseMode.HTML, disable_web_page_preview=True)
    application = ApplicationBuilder() \
        .token(Config.BOT_TOKEN) \
        .defaults(defaults) \
        .build()

    # Initialize handlers
    admin_handlers = AdminHandlers(db_manager)
    user_handlers = UserHandlers(db_manager)
    callback_handlers = CallbackHandlers(db_manager)
    error_handlers = ErrorHandlers(db_manager)

    # Share pipeline reference (set after pipeline is started)
    # Admin commands
    application.add_handler(CommandHandler("add_admin", admin_handlers.add_admin))
    application.add_handler(CommandHandler("remove_admin", admin_handlers.remove_admin))
    application.add_handler(CommandHandler("list_admins", admin_handlers.list_admins))
    application.add_handler(CommandHandler("panel", admin_handlers.admin_panel))
    application.add_handler(CommandHandler("ahelp", admin_handlers.help_admin))

    # Request management
    application.add_handler(CommandHandler("view_requests", admin_handlers.view_requests))
    application.add_handler(CommandHandler("approve", admin_handlers.approve_request))
    application.add_handler(CommandHandler("reject", admin_handlers.reject_request))
    application.add_handler(CommandHandler("auto_approve", admin_handlers.set_auto_approve))

    # Task management
    application.add_handler(CommandHandler("addtask", admin_handlers.add_task))
    application.add_handler(CommandHandler("tasks", admin_handlers.view_tasks))
    application.add_handler(CommandHandler("taskinfo", admin_handlers.task_info))
    application.add_handler(CommandHandler("failed", admin_handlers.failed_tasks))
    application.add_handler(CommandHandler("redownload", admin_handlers.redownload))
    application.add_handler(CommandHandler("cancel_task", admin_handlers.cancel_task))
    application.add_handler(CommandHandler("set_source", admin_handlers.set_source_url))

    # Settings
    application.add_handler(CommandHandler("set_max_requests", admin_handlers.set_max_requests))
    application.add_handler(CommandHandler("set_max_daily", admin_handlers.set_max_daily))
    application.add_handler(CommandHandler("set_request_time", admin_handlers.set_request_time))
    application.add_handler(CommandHandler("del_timer", admin_handlers.del_timer))
    application.add_handler(CommandHandler("set_quality", admin_handlers.set_quality))
    application.add_handler(CommandHandler("maintenance", admin_handlers.maintenance_mode))
    application.add_handler(CommandHandler("config", admin_handlers.show_config))
    application.add_handler(CommandHandler("setconfig", admin_handlers.set_config_key))
    application.add_handler(CommandHandler("reload", admin_handlers.reload_config))

    # Channel routing
    application.add_handler(CommandHandler("set_channel", admin_handlers.set_channel))
    application.add_handler(CommandHandler("remove_channel", admin_handlers.remove_channel))
    application.add_handler(CommandHandler("channels", admin_handlers.list_channels))

    # User management
    application.add_handler(CommandHandler("users", admin_handlers.list_users))
    application.add_handler(CommandHandler("userinfo", admin_handlers.user_info))
    application.add_handler(CommandHandler("ban", admin_handlers.ban_user))
    application.add_handler(CommandHandler("unban", admin_handlers.unban_user))
    application.add_handler(CommandHandler("reset_user", admin_handlers.reset_user_requests))

    # Broadcast
    application.add_handler(CommandHandler("broadcast", admin_handlers.broadcast))
    application.add_handler(CommandHandler("broadcast_photo", admin_handlers.broadcast_photo))

    # Statistics & storage
    application.add_handler(CommandHandler("stats", admin_handlers.stats))
    application.add_handler(CommandHandler("dstats", admin_handlers.detailed_stats))
    application.add_handler(CommandHandler("storage", admin_handlers.storage_info))
    application.add_handler(CommandHandler("cleanup", admin_handlers.cleanup_now))
    application.add_handler(CommandHandler("backup", admin_handlers.backup_db))
    application.add_handler(CommandHandler("clear_queue", admin_handlers.clear_queue))
    application.add_handler(CommandHandler("reset_counter", admin_handlers.reset_daily_counter))

    # Pipeline control
    application.add_handler(CommandHandler("pipeline", admin_handlers.pipeline_status))
    application.add_handler(CommandHandler("start_pipeline", admin_handlers.start_pipeline))
    application.add_handler(CommandHandler("stop_pipeline", admin_handlers.stop_pipeline))

    # Source search
    application.add_handler(CommandHandler("nyaa", admin_handlers.search_nyaa))

    # Scheduler & system
    application.add_handler(CommandHandler("scheduler", admin_handlers.scheduler_info))
    application.add_handler(CommandHandler("run_now", admin_handlers.run_now))
    application.add_handler(CommandHandler("botinfo", admin_handlers.bot_info))
    application.add_handler(CommandHandler("ping", admin_handlers.ping))
    application.add_handler(CommandHandler("logs", admin_handlers.logs))

    # User commands
    application.add_handler(CommandHandler("start", user_handlers.start))
    application.add_handler(CommandHandler("help", user_handlers.help_command))
    application.add_handler(CommandHandler("request", user_handlers.request_anime))
    application.add_handler(CommandHandler("latest", user_handlers.latest_uploads))
    application.add_handler(CommandHandler("airing", user_handlers.airing_today))
    application.add_handler(CommandHandler("search", user_handlers.search_anime))
    application.add_handler(CommandHandler("status", user_handlers.check_status))
    application.add_handler(CommandHandler("trending", user_handlers.trending_anime))
    application.add_handler(CommandHandler("seasonal", user_handlers.seasonal_anime))
    application.add_handler(CommandHandler("myreqs", user_handlers.my_requests))

    # Message handlers
    application.add_handler(MessageHandler(
        filters.Regex(r'^#request\s+.+'), user_handlers.request_hashtag
    ))

    # Callback query handler
    application.add_handler(CallbackQueryHandler(callback_handlers.handle_callback))

    # Error handler
    application.add_error_handler(error_handlers.handle_error)

    # Initialize scheduler
    scheduler_service = SchedulerService(application, db_manager)
    await scheduler_service.initialize()

    logger.info("🤖 Bot is starting...")

    await application.initialize()
    await application.start()
    await application.updater.start_polling(drop_pending_updates=True)

    logger.info("✅ ✦ ＡＵＴＯ ＡＮＩＭＥ ✦ is running!")

    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        logger.info("🛑 Bot is stopping...")
        await application.updater.stop()
        await application.stop()
        await application.shutdown()
        await scheduler_service.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
