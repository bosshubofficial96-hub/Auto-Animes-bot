"""
Admin Command Handlers for ✦ ＡＵＴＯ ＡＮＩＭＥ ✦
"""

import uuid
from datetime import datetime, timedelta
from typing import Optional, List
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from bot.config import Config
from bot.database.database import DatabaseManager
from bot.database.models import AnimeTask, TaskStatus, RequestStatus
from bot.core.pipeline import Pipeline
from bot.utils.logger import setup_logger
from bot.utils.helpers import generate_task_id, format_size


class AdminHandlers:
    """Handler for all admin commands"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.logger = setup_logger("admin_handlers")
        self.pipeline = None
    
    def set_pipeline(self, pipeline: Pipeline):
        """Set pipeline reference"""
        self.pipeline = pipeline
    
    async def _check_admin(self, update: Update) -> bool:
        """Check if user is admin"""
        user_id = update.effective_user.id
        
        # Check in-memory admin list first
        if user_id in Config.ADMIN_IDS:
            return True
        
        # Check database
        is_admin = await self.db_manager.is_admin(user_id)
        
        if not is_admin:
            await update.message.reply_text(
                "❌ <b>Access Denied!</b>\n\n"
                "This command is only available for bot administrators.\n\n"
                f"{Config.FOOTER}",
                parse_mode=ParseMode.HTML
            )
            return False
        return True
    
    async def add_admin(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Add a new admin: /add_admin <user_id or username>"""
        if not await self._check_admin(update):
            return
        
        if not context.args:
            await update.message.reply_text(
                "❌ <b>Usage:</b> <code>/add_admin &lt;user_id&gt;</code>\n\n"
                "Example: <code>/add_admin 123456789</code>\n"
                "Or: <code>/add_admin @username</code>",
                parse_mode=ParseMode.HTML
            )
            return
        
        target = context.args[0]
        
        # Extract user_id
        user_id = None
        username = None
        
        if target.startswith('@'):
            # Username provided
            try:
                chat = await context.bot.get_chat(target)
                user_id = chat.id
                username = target[1:]
            except Exception as e:
                await update.message.reply_text(f"❌ Invalid username! Error: {e}")
                return
        else:
            try:
                user_id = int(target)
            except ValueError:
                await update.message.reply_text("❌ Invalid user ID! Must be a number.")
                return
        
        # Add to database
        success = await self.db_manager.add_admin(user_id, username, update.effective_user.id)
        
        if success:
            await update.message.reply_text(
                f"✅ <b>Admin Added Successfully!</b>\n\n"
                f"User ID: <code>{user_id}</code>\n"
                f"Username: {username or 'N/A'}\n"
                f"Added by: {update.effective_user.first_name}\n\n"
                f"{Config.FOOTER}",
                parse_mode=ParseMode.HTML
            )
            
            # Log to admin channel
            await self._log_admin_action(
                f"➕ New admin added\n"
                f"User: {user_id}\n"
                f"Added by: {update.effective_user.id}"
            )
        else:
            await update.message.reply_text("❌ Failed to add admin. User might already be an admin.")
    
    async def set_max_requests(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Set max requests per user: /set_max_requests <number>"""
        if not await self._check_admin(update):
            return
        
        if not context.args:
            await update.message.reply_text(
                "❌ <b>Usage:</b> <code>/set_max_requests &lt;number&gt;</code>\n\n"
                "Example: <code>/set_max_requests 10</code>\n"
                f"Current: {Config.MAX_USER_REQUESTS}",
                parse_mode=ParseMode.HTML
            )
            return
        
        try:
            max_requests = int(context.args[0])
            if max_requests < 1 or max_requests > 100:
                raise ValueError
        except ValueError:
            await update.message.reply_text("❌ Please provide a valid number between 1 and 100.")
            return
        
        # Update config
        await self.db_manager.set_config('max_user_requests', str(max_requests))
        Config.MAX_USER_REQUESTS = max_requests
        
        await update.message.reply_text(
            f"✅ <b>Max Requests Updated!</b>\n\n"
            f"New limit: <b>{max_requests}</b> requests per user\n\n"
            f"{Config.FOOTER}",
            parse_mode=ParseMode.HTML
        )
    
    async def view_requests(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """View pending user requests: /view_requests"""
        if not await self._check_admin(update):
            return
        
        pending_requests = await self.db_manager.get_pending_requests()
        
        if not pending_requests:
            await update.message.reply_text(
                "📭 <b>No Pending Requests</b>\n\n"
                "All user requests have been processed.\n\n"
                f"{Config.FOOTER}",
                parse_mode=ParseMode.HTML
            )
            return
        
        # Create keyboard with inline buttons
        keyboard = []
        for req in pending_requests[:20]:  # Limit to 20 per page
            button_text = f"#{req['request_id']} - {req['anime_title'][:30]}"
            keyboard.append([
                InlineKeyboardButton(
                    button_text,
                    callback_data=f"view_req_{req['request_id']}"
                )
            ])
        
        # Add navigation buttons
        keyboard.append([
            InlineKeyboardButton("✅ Approve All", callback_data="approve_all"),
            InlineKeyboardButton("❌ Reject All", callback_data="reject_all")
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"📋 <b>Pending Requests</b> ({len(pending_requests)})\n\n"
            f"Click on any request to view details and take action.\n\n"
            f"{Config.FOOTER}",
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup
        )
    
    async def set_request_time(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Set daily request processing time: /set_request_time <HH:MM>"""
        if not await self._check_admin(update):
            return
        
        if not context.args:
            await update.message.reply_text(
                "❌ <b>Usage:</b> <code>/set_request_time &lt;HH:MM&gt;</code>\n\n"
                "Example: <code>/set_request_time 18:00</code> (6:00 PM IST)\n"
                f"Current: {Config.REQUEST_TIME}",
                parse_mode=ParseMode.HTML
            )
            return
        
        time_str = context.args[0]
        
        # Validate time format
        try:
            datetime.strptime(time_str, "%H:%M")
        except ValueError:
            await update.message.reply_text(
                "❌ Invalid time format! Please use HH:MM (24-hour format).\n"
                "Example: 18:00 for 6:00 PM"
            )
            return
        
        # Update config
        await self.db_manager.set_config('request_time', time_str)
        Config.REQUEST_TIME = time_str
        
        await update.message.reply_text(
            f"✅ <b>Request Time Updated!</b>\n\n"
            f"Daily processing will run at <b>{time_str} IST</b>\n\n"
            f"{Config.FOOTER}",
            parse_mode=ParseMode.HTML
        )
        
        # Restart scheduler if needed
        if self.pipeline:
            # Trigger scheduler restart logic here
            pass
    
    async def del_timer(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Set cleanup timer: /del_timer <duration> (e.g., 12h, 1d)"""
        if not await self._check_admin(update):
            return
        
        if not context.args:
            await update.message.reply_text(
                "❌ <b>Usage:</b> <code>/del_timer &lt;duration&gt;</code>\n\n"
                "Examples:\n"
                "<code>/del_timer 12h</code> - Cleanup after 12 hours\n"
                "<code>/del_timer 1d</code> - Cleanup after 1 day\n"
                "<code>/del_timer 30m</code> - Cleanup after 30 minutes\n\n"
                f"Current: {Config.CLEANUP_HOURS} hours",
                parse_mode=ParseMode.HTML
            )
            return
        
        duration_str = context.args[0].lower()
        
        # Parse duration
        hours = None
        if duration_str.endswith('h'):
            hours = int(duration_str[:-1])
        elif duration_str.endswith('d'):
            hours = int(duration_str[:-1]) * 24
        elif duration_str.endswith('m'):
            hours = int(duration_str[:-1]) / 60
        else:
            try:
                hours = int(duration_str)
            except ValueError:
                await update.message.reply_text("❌ Invalid duration format!")
                return
        
        if hours < 1:
            hours = 1
        
        # Update config
        await self.db_manager.set_config('cleanup_hours', str(int(hours)))
        Config.CLEANUP_HOURS = int(hours)
        
        await update.message.reply_text(
            f"✅ <b>Cleanup Timer Updated!</b>\n\n"
            f"Files will be cleaned up after <b>{hours} hours</b>\n\n"
            f"{Config.FOOTER}",
            parse_mode=ParseMode.HTML
        )
    
    async def add_task(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Manually add a task: /addtask <title> <episode> [quality]"""
        if not await self._check_admin(update):
            return
        
        if len(context.args) < 2:
            await update.message.reply_text(
                "❌ <b>Usage:</b> <code>/addtask &lt;title&gt; &lt;episode&gt; [quality]</code>\n\n"
                "Example:\n"
                "<code>/addtask One Piece 1080 1080p</code>\n"
                "<code>/addtask Demon Slayer 12 720p</code>\n\n"
                f"Qualities: {', '.join(Config.QUALITY_OPTIONS)}",
                parse_mode=ParseMode.HTML
            )
            return
        
        title = context.args[0]
        
        try:
            episode = int(context.args[1])
        except ValueError:
            await update.message.reply_text("❌ Episode must be a number!")
            return
        
        quality = context.args[2] if len(context.args) > 2 else "720p"
        
        if quality not in Config.QUALITY_OPTIONS:
            await update.message.reply_text(f"❌ Invalid quality! Choose from: {', '.join(Config.QUALITY_OPTIONS)}")
            return
        
        # Create task
        task_id = generate_task_id()
        task = AnimeTask(
            task_id=task_id,
            title=title,
            episode=episode,
            quality=quality,
            status=TaskStatus.PENDING,
            requested_by=update.effective_user.id,
            metadata={'admin_added': True}
        )
        
        # Add to pipeline
        if self.pipeline:
            await self.pipeline.add_task(task)
            await update.message.reply_text(
                f"✅ <b>Task Added to Pipeline!</b>\n\n"
                f"📋 Task ID: <code>{task_id}</code>\n"
                f"🎬 Title: {title}\n"
                f"📺 Episode: {episode}\n"
                f"🎯 Quality: {quality}\n\n"
                f"Status: 🔄 Processing started...\n\n"
                f"{Config.FOOTER}",
                parse_mode=ParseMode.HTML
            )
        else:
            await self.db_manager.add_task(task)
            await update.message.reply_text(
                f"✅ <b>Task Added to Database!</b>\n\n"
                f"📋 Task ID: <code>{task_id}</code>\n"
                f"🎬 Title: {title}\n"
                f"📺 Episode: {episode}\n"
                f"🎯 Quality: {quality}\n\n"
                f"Status: ⏳ Pending (pipeline not started)\n\n"
                f"{Config.FOOTER}",
                parse_mode=ParseMode.HTML
            )
        
        # Log action
        await self._log_admin_action(
            f"📋 Task added by admin\n"
            f"Task: {task_id}\n"
            f"Title: {title} EP{episode}\n"
            f"Admin: {update.effective_user.id}"
        )
    
    async def redownload(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Redownload a failed task: /redownload <task_id>"""
        if not await self._check_admin(update):
            return
        
        if not context.args:
            await update.message.reply_text(
                "❌ <b>Usage:</b> <code>/redownload &lt;task_id&gt;</code>\n\n"
                "Example: <code>/redownload abc123def</code>\n\n"
                "Use <code>/stats</code> to see failed tasks.",
                parse_mode=ParseMode.HTML
            )
            return
        
        task_id = context.args[0]
        
        # Get task from database
        task = await self.db_manager.get_task(task_id)
        
        if not task:
            await update.message.reply_text(f"❌ Task <code>{task_id}</code> not found!", parse_mode=ParseMode.HTML)
            return
        
        # Reset task status
        task.status = TaskStatus.PENDING
        task.error_log = None
        task.retry_count += 1
        
        await self.db_manager.add_task(task)
        
        # Add to pipeline
        if self.pipeline:
            await self.pipeline.add_task(task)
            
            await update.message.reply_text(
                f"🔄 <b>Task Reset for Redownload</b>\n\n"
                f"📋 Task ID: <code>{task_id}</code>\n"
                f"🎬 Title: {task.title}\n"
                f"📺 Episode: {task.episode}\n"
                f"🔄 Retry Count: {task.retry_count}\n\n"
                f"Status: 🔄 Processing started...\n\n"
                f"{Config.FOOTER}",
                parse_mode=ParseMode.HTML
            )
        else:
            await update.message.reply_text(
                f"✅ <b>Task Reset</b>\n\n"
                f"Task <code>{task_id}</code> has been reset and will be processed when pipeline starts.\n\n"
                f"{Config.FOOTER}",
                parse_mode=ParseMode.HTML
            )
        
        # Log action
        await self._log_admin_action(
            f"🔄 Task redownload requested\n"
            f"Task: {task_id}\n"
            f"Title: {task.title} EP{task.episode}\n"
            f"Admin: {update.effective_user.id}"
        )
    
    async def broadcast(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Broadcast message to all users: /broadcast <message>"""
        if not await self._check_admin(update):
            return
        
        if not context.args:
            await update.message.reply_text(
                "❌ <b>Usage:</b> <code>/broadcast &lt;message&gt;</code>\n\n"
                "Example: <code>/broadcast Maintenance in 1 hour!</code>\n\n"
                "⚠️ This will send the message to ALL users.",
                parse_mode=ParseMode.HTML
            )
            return
        
        message = ' '.join(context.args)
        
        # Get all users (you'd need a users table for this)
        # For now, just send to admin channel
        await self._log_admin_action(
            f"📢 <b>Broadcast Message</b>\n\n"
            f"{message}\n\n"
            f"— Admin: {update.effective_user.first_name}"
        )
        
        await update.message.reply_text(
            f"✅ <b>Broadcast Sent!</b>\n\n"
            f"Message: {message[:100]}\n\n"
            f"{Config.FOOTER}",
            parse_mode=ParseMode.HTML
        )
    
    async def stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """View bot statistics: /stats"""
        if not await self._check_admin(update):
            return
        
        # Get task stats
        task_stats = await self.db_manager.get_task_stats()
        
        # Get queue status
        queue_status = {}
        if self.pipeline:
            queue_status = await self.pipeline.get_queue_status()
        
        # Get storage info
        storage_info = await self._get_storage_info()
        
        # Build stats message
        message = f"""
📊 <b>Bot Statistics</b>

<b>📋 Tasks:</b>
├─ Pending: {task_stats.get('pending', 0)}
├─ Processing: {task_stats.get('processing', 0)}
├─ Downloading: {task_stats.get('downloading', 0)}
├─ Completed: {task_stats.get('completed', 0)}
└─ Failed: {task_stats.get('failed', 0)}

<b>⚙️ Pipeline:</b>
├─ Active Tasks: {queue_status.get('active_tasks', 0)}
├─ Queue Size: {queue_status.get('queue_size', 0)}
├─ Workers: {queue_status.get('workers', 0)}
└─ Running: {'✅' if queue_status.get('is_running') else '❌'}

<b>💾 Storage:</b>
├─ Downloads: {storage_info['downloads_size']}
├─ Processed: {storage_info['processed_size']}
├─ Free Space: {storage_info['free_space']}
└─ Total Used: {storage_info['total_used']}

<b>⚡ Performance:</b>
├─ Target Speed: {Config.TARGET_SPEED_KBPS} KB/s
├─ Max Downloads: {Config.MAX_CONCURRENT_DOWNLOADS}
└─ Max Uploads: {Config.MAX_CONCURRENT_UPLOADS}

{Config.FOOTER}
        """
        
        await update.message.reply_text(message.strip(), parse_mode=ParseMode.HTML)
    
    async def _get_storage_info(self) -> dict:
        """Get storage information"""
        import shutil
        
        downloads_size = 0
        processed_size = 0
        
        if Config.DOWNLOAD_PATH.exists():
            downloads_size = sum(f.stat().st_size for f in Config.DOWNLOAD_PATH.glob('**/*') if f.is_file())
        
        if Config.PROCESSED_PATH.exists():
            processed_size = sum(f.stat().st_size for f in Config.PROCESSED_PATH.glob('**/*') if f.is_file())
        
        total_used = downloads_size + processed_size
        
        # Get disk free space
        free_space = shutil.disk_usage(Config.BASE_DIR).free
        
        return {
            'downloads_size': format_size(downloads_size),
            'processed_size': format_size(processed_size),
            'total_used': format_size(total_used),
            'free_space': format_size(free_space)
        }
    
    async def _log_admin_action(self, action: str):
        """Log admin action to admin channel"""
        try:
            from telegram import Bot
            bot = Bot(token=Config.BOT_TOKEN)
            await bot.send_message(
                chat_id=Config.ADMIN_LOG_CHANNEL,
                text=f"📝 <b>Admin Action Log</b>\n\n{action}\n\n{Config.FOOTER}",
                parse_mode=ParseMode.HTML
            )
        except Exception as e:
            self.logger.error(f"Failed to log admin action: {e}")
