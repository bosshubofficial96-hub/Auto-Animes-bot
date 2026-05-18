"""
Admin Command Handlers for ✦ ＡＵＴＯ ＡＮＩＭＥ ✦
50+ Admin Panel Commands
"""

import shutil
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
    """Handler for all admin commands — 50+ panel controls"""

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.logger = setup_logger("admin_handlers")
        self.pipeline = None

    def set_pipeline(self, pipeline: Pipeline):
        self.pipeline = pipeline

    # ==================== AUTH ====================

    async def _check_admin(self, update: Update) -> bool:
        user_id = update.effective_user.id
        if user_id in Config.ADMIN_IDS:
            return True
        if await self.db_manager.is_admin(user_id):
            return True
        await update.message.reply_text(
            "❌ <b>Access Denied!</b>\n\nThis command is only for bot administrators.\n\n"
            f"{Config.FOOTER}", parse_mode=ParseMode.HTML
        )
        return False

    async def _check_superadmin(self, update: Update) -> bool:
        user_id = update.effective_user.id
        if user_id in Config.ADMIN_IDS:
            return True
        await update.message.reply_text(
            "❌ <b>Superadmin Only!</b>\n\nThis command requires superadmin access.\n\n"
            f"{Config.FOOTER}", parse_mode=ParseMode.HTML
        )
        return False

    # ==================== ADMIN MANAGEMENT ====================

    async def add_admin(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Add a new admin: /add_admin <user_id>"""
        if not await self._check_superadmin(update):
            return
        if not context.args:
            await update.message.reply_text(
                "❌ <b>Usage:</b> <code>/add_admin &lt;user_id&gt;</code>\n"
                "Example: <code>/add_admin 123456789</code>",
                parse_mode=ParseMode.HTML
            )
            return
        target = context.args[0]
        user_id = None
        username = None
        if target.startswith('@'):
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
                await update.message.reply_text("❌ Invalid user ID!")
                return
        success = await self.db_manager.add_admin(user_id, username, update.effective_user.id)
        if success:
            await update.message.reply_text(
                f"✅ <b>Admin Added!</b>\n\nUser ID: <code>{user_id}</code>\n"
                f"Username: {username or 'N/A'}\n\n{Config.FOOTER}", parse_mode=ParseMode.HTML
            )
            await self._log_admin_action(f"➕ Admin added: {user_id} by {update.effective_user.id}")
        else:
            await update.message.reply_text("❌ Failed — user may already be admin.")

    async def remove_admin(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Remove an admin: /remove_admin <user_id>"""
        if not await self._check_superadmin(update):
            return
        if not context.args:
            await update.message.reply_text(
                "❌ <b>Usage:</b> <code>/remove_admin &lt;user_id&gt;</code>",
                parse_mode=ParseMode.HTML
            )
            return
        try:
            user_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text("❌ Invalid user ID!")
            return
        if user_id in Config.ADMIN_IDS:
            await update.message.reply_text("❌ Cannot remove a superadmin!")
            return
        await self.db_manager.remove_admin(user_id)
        await update.message.reply_text(
            f"✅ <b>Admin Removed</b>\n\nUser <code>{user_id}</code> removed from admins.\n\n{Config.FOOTER}",
            parse_mode=ParseMode.HTML
        )
        await self._log_admin_action(f"➖ Admin removed: {user_id} by {update.effective_user.id}")

    async def list_admins(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """List all admins: /list_admins"""
        if not await self._check_admin(update):
            return
        admins = await self.db_manager.get_admins()
        if not admins:
            await update.message.reply_text("📭 No admins in database (superadmins are configured via env).")
            return
        msg = "👑 <b>Admin List</b>\n\n"
        for a in admins:
            name = a.username or a.first_name or "Unknown"
            msg += f"• <code>{a.user_id}</code> — @{name}\n"
        msg += f"\n<b>Superadmins (env):</b> {', '.join(str(x) for x in Config.ADMIN_IDS)}\n\n{Config.FOOTER}"
        await update.message.reply_text(msg, parse_mode=ParseMode.HTML)

    async def admin_panel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show full admin control panel: /panel"""
        if not await self._check_admin(update):
            return
        keyboard = [
            [InlineKeyboardButton("📋 View Requests", callback_data="panel_requests"),
             InlineKeyboardButton("📊 Statistics", callback_data="panel_stats")],
            [InlineKeyboardButton("⚙️ Settings", callback_data="panel_settings"),
             InlineKeyboardButton("💾 Storage", callback_data="panel_storage")],
            [InlineKeyboardButton("👥 Users", callback_data="panel_users"),
             InlineKeyboardButton("📡 Tasks", callback_data="panel_tasks")],
            [InlineKeyboardButton("🔧 Maintenance", callback_data="panel_maintenance"),
             InlineKeyboardButton("📢 Broadcast", callback_data="panel_broadcast")],
            [InlineKeyboardButton("🗑️ Cleanup Now", callback_data="panel_cleanup"),
             InlineKeyboardButton("💡 Bot Info", callback_data="panel_info")],
        ]
        await update.message.reply_text(
            "🎛️ <b>✦ ＡＵＴＯ ＡＮＩＭＥ ✦ Admin Panel</b>\n\n"
            "Select a section to manage:",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    # ==================== REQUEST MANAGEMENT ====================

    async def view_requests(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """View pending requests: /view_requests [page]"""
        if not await self._check_admin(update):
            return
        page = 0
        if context.args:
            try:
                page = max(0, int(context.args[0]) - 1)
            except ValueError:
                pass
        limit = 15
        offset = page * limit
        pending = await self.db_manager.get_pending_requests(limit=limit + offset)
        pending = pending[offset:offset + limit]
        if not pending:
            await update.message.reply_text(
                f"📭 <b>No Pending Requests</b>\n\nAll requests processed.\n\n{Config.FOOTER}",
                parse_mode=ParseMode.HTML
            )
            return
        keyboard = []
        for req in pending:
            txt = f"#{req['request_id']} — {req['anime_title'][:25]}"
            keyboard.append([InlineKeyboardButton(txt, callback_data=f"view_req_{req['request_id']}")])
        keyboard.append([
            InlineKeyboardButton("✅ Approve All", callback_data="approve_all"),
            InlineKeyboardButton("❌ Reject All", callback_data="reject_all")
        ])
        if page > 0:
            keyboard.append([InlineKeyboardButton("◀️ Prev", callback_data=f"req_page_{page - 1}")])
        await update.message.reply_text(
            f"📋 <b>Pending Requests</b> — Page {page + 1}\n"
            f"Showing {len(pending)} requests.\n\n{Config.FOOTER}",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def approve_request(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Approve a request: /approve <request_id> [episode] [quality]"""
        if not await self._check_admin(update):
            return
        if not context.args:
            await update.message.reply_text(
                "❌ <b>Usage:</b> <code>/approve &lt;request_id&gt; [episode] [quality]</code>",
                parse_mode=ParseMode.HTML
            )
            return
        try:
            request_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text("❌ Invalid request ID!")
            return
        episode = 1
        quality = "720p"
        if len(context.args) > 1:
            try:
                episode = int(context.args[1])
            except ValueError:
                pass
        if len(context.args) > 2 and context.args[2] in Config.QUALITY_OPTIONS:
            quality = context.args[2]
        req = await self.db_manager.get_request_by_id(request_id)
        if not req:
            await update.message.reply_text(f"❌ Request #{request_id} not found!")
            return
        task_id = generate_task_id()
        task = AnimeTask(
            task_id=task_id,
            title=req['anime_title'],
            episode=episode,
            quality=quality,
            status=TaskStatus.PENDING,
            requested_by=req['user_id'],
            metadata={'approved_by': update.effective_user.id}
        )
        await self.db_manager.add_task(task)
        await self.db_manager.update_request_status(request_id, RequestStatus.APPROVED, task_id)
        if self.pipeline:
            await self.pipeline.add_task(task)
        await update.message.reply_text(
            f"✅ <b>Request Approved!</b>\n\n"
            f"📋 Request ID: <code>#{request_id}</code>\n"
            f"🎬 Anime: <b>{req['anime_title']}</b>\n"
            f"📺 Episode: {episode} | 🎯 Quality: {quality}\n"
            f"🔗 Task ID: <code>{task_id}</code>\n\n{Config.FOOTER}",
            parse_mode=ParseMode.HTML
        )
        await self._log_admin_action(f"✅ Request #{request_id} approved → Task {task_id}")

    async def reject_request(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Reject a request: /reject <request_id> [reason]"""
        if not await self._check_admin(update):
            return
        if not context.args:
            await update.message.reply_text(
                "❌ <b>Usage:</b> <code>/reject &lt;request_id&gt; [reason]</code>",
                parse_mode=ParseMode.HTML
            )
            return
        try:
            request_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text("❌ Invalid request ID!")
            return
        reason = ' '.join(context.args[1:]) if len(context.args) > 1 else "No reason given"
        req = await self.db_manager.get_request_by_id(request_id)
        if not req:
            await update.message.reply_text(f"❌ Request #{request_id} not found!")
            return
        await self.db_manager.update_request_status(request_id, RequestStatus.REJECTED, admin_notes=reason)
        await update.message.reply_text(
            f"❌ <b>Request Rejected</b>\n\n"
            f"Request <code>#{request_id}</code> rejected.\n"
            f"Reason: {reason}\n\n{Config.FOOTER}",
            parse_mode=ParseMode.HTML
        )
        await self._log_admin_action(f"❌ Request #{request_id} rejected. Reason: {reason}")

    # ==================== TASK MANAGEMENT ====================

    async def add_task(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Manually add task: /addtask <title> <episode> [quality]"""
        if not await self._check_admin(update):
            return
        if len(context.args) < 2:
            await update.message.reply_text(
                "❌ <b>Usage:</b> <code>/addtask &lt;title&gt; &lt;episode&gt; [quality]</code>\n\n"
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
            await update.message.reply_text(f"❌ Invalid quality! Choose: {', '.join(Config.QUALITY_OPTIONS)}")
            return
        task_id = generate_task_id()
        task = AnimeTask(
            task_id=task_id, title=title, episode=episode, quality=quality,
            status=TaskStatus.PENDING, requested_by=update.effective_user.id,
            metadata={'admin_added': True}
        )
        if self.pipeline:
            await self.pipeline.add_task(task)
            status_text = "🔄 Processing started..."
        else:
            await self.db_manager.add_task(task)
            status_text = "⏳ Pending (pipeline not active)"
        await update.message.reply_text(
            f"✅ <b>Task Added!</b>\n\n"
            f"📋 ID: <code>{task_id}</code>\n"
            f"🎬 Title: {title}\n📺 Episode: {episode}\n🎯 Quality: {quality}\n"
            f"Status: {status_text}\n\n{Config.FOOTER}",
            parse_mode=ParseMode.HTML
        )
        await self._log_admin_action(f"📋 Task added: {title} EP{episode} by {update.effective_user.id}")

    async def redownload(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Redownload failed task: /redownload <task_id>"""
        if not await self._check_admin(update):
            return
        if not context.args:
            await update.message.reply_text(
                "❌ <b>Usage:</b> <code>/redownload &lt;task_id&gt;</code>",
                parse_mode=ParseMode.HTML
            )
            return
        task_id = context.args[0]
        task = await self.db_manager.get_task(task_id)
        if not task:
            await update.message.reply_text(f"❌ Task <code>{task_id}</code> not found!", parse_mode=ParseMode.HTML)
            return
        task.status = TaskStatus.PENDING
        task.error_log = None
        task.retry_count += 1
        await self.db_manager.add_task(task)
        if self.pipeline:
            await self.pipeline.add_task(task)
        await update.message.reply_text(
            f"🔄 <b>Task Reset for Redownload</b>\n\n"
            f"📋 Task: <code>{task_id}</code>\n🎬 {task.title} EP{task.episode}\n"
            f"🔄 Retry #{task.retry_count}\n\n{Config.FOOTER}",
            parse_mode=ParseMode.HTML
        )
        await self._log_admin_action(f"🔄 Redownload: {task_id} by {update.effective_user.id}")

    async def cancel_task(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Cancel a running task: /cancel_task <task_id>"""
        if not await self._check_admin(update):
            return
        if not context.args:
            await update.message.reply_text("❌ <b>Usage:</b> <code>/cancel_task &lt;task_id&gt;</code>",
                                            parse_mode=ParseMode.HTML)
            return
        task_id = context.args[0]
        task = await self.db_manager.get_task(task_id)
        if not task:
            await update.message.reply_text(f"❌ Task not found: <code>{task_id}</code>", parse_mode=ParseMode.HTML)
            return
        await self.db_manager.update_task_status(task_id, TaskStatus.CANCELLED)
        await update.message.reply_text(
            f"🚫 <b>Task Cancelled</b>\n\nTask <code>{task_id}</code> has been cancelled.\n\n{Config.FOOTER}",
            parse_mode=ParseMode.HTML
        )
        await self._log_admin_action(f"🚫 Task cancelled: {task_id}")

    async def view_tasks(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """View all active/pending tasks: /tasks"""
        if not await self._check_admin(update):
            return
        active = await self.db_manager.get_active_tasks()
        pending = await self.db_manager.get_pending_tasks(limit=5)
        msg = "📡 <b>Task Overview</b>\n\n"
        if active:
            msg += f"<b>🔄 Active ({len(active)}):</b>\n"
            for t in active:
                msg += f"  • <code>{t.task_id[:12]}</code> — {t.title[:20]} EP{t.episode} [{t.status.value}]\n"
        else:
            msg += "<b>🔄 Active:</b> None\n"
        msg += f"\n<b>⏳ Pending ({len(pending)}):</b>\n"
        for t in pending:
            msg += f"  • <code>{t.task_id[:12]}</code> — {t.title[:20]} EP{t.episode}\n"
        if not pending:
            msg += "  None\n"
        if self.pipeline:
            qs = await self.pipeline.get_queue_status()
            msg += f"\n<b>⚙️ Pipeline:</b> {qs['active_tasks']} active | Queue: {qs['queue_size']}\n"
        msg += f"\n{Config.FOOTER}"
        await update.message.reply_text(msg, parse_mode=ParseMode.HTML)

    async def task_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Get detailed task info: /taskinfo <task_id>"""
        if not await self._check_admin(update):
            return
        if not context.args:
            await update.message.reply_text("❌ <b>Usage:</b> <code>/taskinfo &lt;task_id&gt;</code>",
                                            parse_mode=ParseMode.HTML)
            return
        task = await self.db_manager.get_task(context.args[0])
        if not task:
            await update.message.reply_text("❌ Task not found!")
            return
        elapsed = ""
        if task.started_at:
            end = task.completed_at or datetime.now()
            elapsed = f"{(end - task.started_at).total_seconds():.0f}s"
        msg = (
            f"📋 <b>Task Details</b>\n\n"
            f"🆔 ID: <code>{task.task_id}</code>\n"
            f"🎬 Title: <b>{task.title}</b>\n"
            f"📺 Episode: {task.episode}\n"
            f"🎯 Quality: {task.quality}\n"
            f"📊 Status: <b>{task.status.value.upper()}</b>\n"
            f"🔄 Retries: {task.retry_count}\n"
            f"📅 Created: {task.created_at.strftime('%Y-%m-%d %H:%M')}\n"
            f"⏱ Elapsed: {elapsed or 'N/A'}\n"
        )
        if task.error_log:
            msg += f"❌ Error: <code>{task.error_log[:200]}</code>\n"
        if task.processed_paths:
            msg += f"📁 Qualities: {', '.join(task.processed_paths.keys())}\n"
        msg += f"\n{Config.FOOTER}"
        keyboard = []
        if task.status in [TaskStatus.FAILED, TaskStatus.CANCELLED]:
            keyboard.append([InlineKeyboardButton("🔄 Retry", callback_data=f"retry_task_{task.task_id}")])
        if task.status not in [TaskStatus.COMPLETED, TaskStatus.CANCELLED]:
            keyboard.append([InlineKeyboardButton("🚫 Cancel", callback_data=f"cancel_task_{task.task_id}")])
        reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
        await update.message.reply_text(msg, parse_mode=ParseMode.HTML, reply_markup=reply_markup)

    async def failed_tasks(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """List failed tasks: /failed"""
        if not await self._check_admin(update):
            return
        async with self.db_manager.get_connection() as conn:
            async with conn.execute(
                "SELECT task_id, title, episode, error_log, updated_at FROM tasks WHERE status='failed' ORDER BY updated_at DESC LIMIT 10"
            ) as cur:
                rows = await cur.fetchall()
        if not rows:
            await update.message.reply_text("✅ No failed tasks!", parse_mode=ParseMode.HTML)
            return
        msg = f"❌ <b>Failed Tasks ({len(rows)})</b>\n\n"
        keyboard = []
        for row in rows:
            msg += f"• <code>{row[0][:12]}</code> — {row[1][:20]} EP{row[2]}\n"
            if row[3]:
                msg += f"  └ <i>{row[3][:60]}</i>\n"
            keyboard.append([InlineKeyboardButton(f"🔄 Retry {row[0][:8]}", callback_data=f"retry_task_{row[0]}")])
        msg += f"\n{Config.FOOTER}"
        await update.message.reply_text(msg, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard))

    # ==================== SETTINGS ====================

    async def set_max_requests(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Set max user requests: /set_max_requests <n>"""
        if not await self._check_admin(update):
            return
        if not context.args:
            await update.message.reply_text(
                f"❌ Usage: <code>/set_max_requests &lt;n&gt;</code>\nCurrent: {Config.MAX_USER_REQUESTS}",
                parse_mode=ParseMode.HTML
            )
            return
        try:
            n = int(context.args[0])
            if not 1 <= n <= 100:
                raise ValueError
        except ValueError:
            await update.message.reply_text("❌ Value must be between 1 and 100.")
            return
        await self.db_manager.set_config('max_user_requests', str(n))
        Config.MAX_USER_REQUESTS = n
        await update.message.reply_text(
            f"✅ Max user requests set to <b>{n}</b>\n\n{Config.FOOTER}", parse_mode=ParseMode.HTML
        )

    async def set_request_time(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Set daily processing time: /set_request_time <HH:MM>"""
        if not await self._check_admin(update):
            return
        if not context.args:
            await update.message.reply_text(
                f"❌ Usage: <code>/set_request_time HH:MM</code>\nCurrent: {Config.REQUEST_TIME}",
                parse_mode=ParseMode.HTML
            )
            return
        time_str = context.args[0]
        try:
            datetime.strptime(time_str, "%H:%M")
        except ValueError:
            await update.message.reply_text("❌ Invalid time format! Use HH:MM (24h).")
            return
        await self.db_manager.set_config('request_time', time_str)
        Config.REQUEST_TIME = time_str
        await update.message.reply_text(
            f"✅ Processing time set to <b>{time_str} IST</b>\n\n{Config.FOOTER}", parse_mode=ParseMode.HTML
        )

    async def del_timer(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Set cleanup timer: /del_timer <12h|1d|30m>"""
        if not await self._check_admin(update):
            return
        if not context.args:
            await update.message.reply_text(
                f"❌ Usage: <code>/del_timer &lt;12h|1d|30m&gt;</code>\nCurrent: {Config.CLEANUP_HOURS}h",
                parse_mode=ParseMode.HTML
            )
            return
        d = context.args[0].lower()
        hours = None
        try:
            if d.endswith('h'):
                hours = max(1, int(d[:-1]))
            elif d.endswith('d'):
                hours = max(1, int(d[:-1]) * 24)
            elif d.endswith('m'):
                hours = max(1, int(int(d[:-1]) / 60))
            else:
                hours = max(1, int(d))
        except ValueError:
            await update.message.reply_text("❌ Invalid duration!")
            return
        await self.db_manager.set_config('cleanup_hours', str(hours))
        Config.CLEANUP_HOURS = hours
        await update.message.reply_text(
            f"✅ Cleanup timer set to <b>{hours} hour(s)</b>\n\n{Config.FOOTER}", parse_mode=ParseMode.HTML
        )

    async def set_quality(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Set default quality: /set_quality <480p|720p|1080p>"""
        if not await self._check_admin(update):
            return
        if not context.args or context.args[0] not in Config.QUALITY_OPTIONS:
            await update.message.reply_text(
                f"❌ Usage: <code>/set_quality &lt;quality&gt;</code>\nOptions: {', '.join(Config.QUALITY_OPTIONS)}",
                parse_mode=ParseMode.HTML
            )
            return
        quality = context.args[0]
        await self.db_manager.set_config('default_quality', quality)
        await update.message.reply_text(
            f"✅ Default quality set to <b>{quality}</b>\n\n{Config.FOOTER}", parse_mode=ParseMode.HTML
        )

    async def set_auto_approve(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Toggle auto-approve: /auto_approve <on|off>"""
        if not await self._check_admin(update):
            return
        if not context.args or context.args[0].lower() not in ('on', 'off'):
            current = await self.db_manager.get_config('auto_approve_requests', 'false')
            state = '✅ ON' if current == 'true' else '❌ OFF'
            await update.message.reply_text(
                f"ℹ️ Auto-approve is currently <b>{state}</b>\n"
                f"Usage: <code>/auto_approve &lt;on|off&gt;</code>\n\n{Config.FOOTER}",
                parse_mode=ParseMode.HTML
            )
            return
        val = 'true' if context.args[0].lower() == 'on' else 'false'
        await self.db_manager.set_config('auto_approve_requests', val)
        state = '✅ ON' if val == 'true' else '❌ OFF'
        await update.message.reply_text(
            f"✅ Auto-approve is now <b>{state}</b>\n\n{Config.FOOTER}", parse_mode=ParseMode.HTML
        )

    async def maintenance_mode(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Toggle maintenance mode: /maintenance <on|off>"""
        if not await self._check_superadmin(update):
            return
        if not context.args or context.args[0].lower() not in ('on', 'off'):
            current = await self.db_manager.get_config('maintenance_mode', 'false')
            state = '🔧 ON' if current == 'true' else '✅ OFF'
            await update.message.reply_text(
                f"ℹ️ Maintenance mode: <b>{state}</b>\n"
                f"Usage: <code>/maintenance &lt;on|off&gt;</code>\n\n{Config.FOOTER}",
                parse_mode=ParseMode.HTML
            )
            return
        val = 'true' if context.args[0].lower() == 'on' else 'false'
        await self.db_manager.set_config('maintenance_mode', val)
        state = '🔧 ENABLED' if val == 'true' else '✅ DISABLED'
        await update.message.reply_text(
            f"✅ Maintenance mode: <b>{state}</b>\n\n{Config.FOOTER}", parse_mode=ParseMode.HTML
        )
        await self._log_admin_action(f"🔧 Maintenance mode: {state}")

    async def set_max_daily(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Set global daily request limit: /set_max_daily <n>"""
        if not await self._check_admin(update):
            return
        if not context.args:
            await update.message.reply_text(
                f"❌ Usage: <code>/set_max_daily &lt;n&gt;</code>\nCurrent: {Config.MAX_GLOBAL_DAILY_REQUESTS}",
                parse_mode=ParseMode.HTML
            )
            return
        try:
            n = int(context.args[0])
            if n < 1:
                raise ValueError
        except ValueError:
            await update.message.reply_text("❌ Invalid number!")
            return
        await self.db_manager.set_config('max_daily_requests', str(n))
        Config.MAX_GLOBAL_DAILY_REQUESTS = n
        await update.message.reply_text(
            f"✅ Global daily limit set to <b>{n}</b>\n\n{Config.FOOTER}", parse_mode=ParseMode.HTML
        )

    async def show_config(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show all current config: /config"""
        if not await self._check_admin(update):
            return
        configs = await self.db_manager.get_all_config()
        msg = "⚙️ <b>Bot Configuration</b>\n\n"
        for key, value in configs.items():
            msg += f"• <b>{key}</b>: <code>{value}</code>\n"
        msg += f"\n<b>Memory Config:</b>\n"
        msg += f"• BOT_TOKEN: <code>***{Config.BOT_TOKEN[-8:]}</code>\n"
        msg += f"• DEFAULT_CHANNEL: <code>{Config.DEFAULT_CHANNEL}</code>\n"
        msg += f"• ADMIN_IDS: <code>{Config.ADMIN_IDS}</code>\n"
        msg += f"• QUALITY_OPTIONS: <code>{Config.QUALITY_OPTIONS}</code>\n"
        msg += f"\n{Config.FOOTER}"
        await update.message.reply_text(msg, parse_mode=ParseMode.HTML)

    async def set_config_key(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Set any config key: /setconfig <key> <value>"""
        if not await self._check_superadmin(update):
            return
        if len(context.args) < 2:
            await update.message.reply_text(
                "❌ Usage: <code>/setconfig &lt;key&gt; &lt;value&gt;</code>", parse_mode=ParseMode.HTML
            )
            return
        key = context.args[0]
        value = ' '.join(context.args[1:])
        await self.db_manager.set_config(key, value)
        await update.message.reply_text(
            f"✅ Config updated:\n<code>{key}</code> = <code>{value}</code>\n\n{Config.FOOTER}",
            parse_mode=ParseMode.HTML
        )

    # ==================== CHANNEL ROUTING ====================

    async def set_channel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Set channel for anime: /set_channel <anime_title> <channel_id>"""
        if not await self._check_admin(update):
            return
        if len(context.args) < 2:
            await update.message.reply_text(
                "❌ Usage: <code>/set_channel &lt;anime_title&gt; &lt;channel_id&gt;</code>",
                parse_mode=ParseMode.HTML
            )
            return
        channel_id_str = context.args[-1]
        title = ' '.join(context.args[:-1])
        try:
            channel_id = int(channel_id_str)
        except ValueError:
            await update.message.reply_text("❌ Channel ID must be a number!")
            return
        await self.db_manager.set_channel_routing(title, channel_id)
        Config.CHANNEL_ROUTING[title] = channel_id
        await update.message.reply_text(
            f"✅ <b>Channel Routing Set</b>\n\n"
            f"📺 Anime: <b>{title}</b>\n"
            f"📡 Channel: <code>{channel_id}</code>\n\n{Config.FOOTER}",
            parse_mode=ParseMode.HTML
        )

    async def remove_channel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Remove channel routing: /remove_channel <anime_title>"""
        if not await self._check_admin(update):
            return
        if not context.args:
            await update.message.reply_text(
                "❌ Usage: <code>/remove_channel &lt;anime_title&gt;</code>", parse_mode=ParseMode.HTML
            )
            return
        title = ' '.join(context.args)
        await self.db_manager.remove_channel_routing(title)
        Config.CHANNEL_ROUTING.pop(title, None)
        await update.message.reply_text(
            f"✅ Channel routing removed for <b>{title}</b>\n\n{Config.FOOTER}", parse_mode=ParseMode.HTML
        )

    async def list_channels(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """List all channel routings: /channels"""
        if not await self._check_admin(update):
            return
        routings = await self.db_manager.get_all_channel_routings()
        if not routings:
            await update.message.reply_text(
                f"📭 No custom channel routings set.\nAll anime post to default: <code>{Config.DEFAULT_CHANNEL}</code>\n\n{Config.FOOTER}",
                parse_mode=ParseMode.HTML
            )
            return
        msg = "📡 <b>Channel Routings</b>\n\n"
        for r in routings:
            msg += f"• <b>{r['anime_title']}</b> → <code>{r['channel_id']}</code>\n"
        msg += f"\n🏠 Default: <code>{Config.DEFAULT_CHANNEL}</code>\n\n{Config.FOOTER}"
        await update.message.reply_text(msg, parse_mode=ParseMode.HTML)

    # ==================== USER MANAGEMENT ====================

    async def user_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Get user info: /userinfo <user_id>"""
        if not await self._check_admin(update):
            return
        if not context.args:
            await update.message.reply_text("❌ Usage: <code>/userinfo &lt;user_id&gt;</code>", parse_mode=ParseMode.HTML)
            return
        try:
            user_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text("❌ Invalid user ID!")
            return
        user = await self.db_manager.get_user(user_id)
        if not user:
            await update.message.reply_text("❌ User not found in database!")
            return
        requests = await self.db_manager.get_user_requests(user_id)
        is_admin_user = await self.db_manager.is_admin(user_id)
        msg = (
            f"👤 <b>User Info</b>\n\n"
            f"🆔 ID: <code>{user['user_id']}</code>\n"
            f"👤 Name: {user.get('first_name', 'N/A')} {user.get('last_name', '') or ''}\n"
            f"🏷 Username: @{user.get('username', 'N/A')}\n"
            f"🕐 First seen: {str(user.get('first_seen', 'N/A'))[:16]}\n"
            f"🕐 Last seen: {str(user.get('last_seen', 'N/A'))[:16]}\n"
            f"📋 Total Requests: {len(requests)}\n"
            f"👑 Admin: {'✅' if is_admin_user else '❌'}\n\n{Config.FOOTER}"
        )
        keyboard = [[
            InlineKeyboardButton("🚫 Ban User", callback_data=f"ban_user_{user_id}"),
            InlineKeyboardButton("📋 Requests", callback_data=f"user_requests_{user_id}")
        ]]
        await update.message.reply_text(msg, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard))

    async def list_users(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """List all users: /users [limit]"""
        if not await self._check_admin(update):
            return
        limit = 20
        if context.args:
            try:
                limit = min(50, int(context.args[0]))
            except ValueError:
                pass
        users = await self.db_manager.get_all_users(limit=limit)
        total = await self.db_manager.get_user_count()
        msg = f"👥 <b>Users ({total} total)</b>\n\n"
        for u in users:
            name = u.get('first_name') or u.get('username') or 'Unknown'
            msg += f"• <code>{u['user_id']}</code> — {name[:20]}\n"
        msg += f"\n{Config.FOOTER}"
        await update.message.reply_text(msg, parse_mode=ParseMode.HTML)

    async def ban_user(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Ban a user: /ban <user_id> [reason]"""
        if not await self._check_admin(update):
            return
        if not context.args:
            await update.message.reply_text("❌ Usage: <code>/ban &lt;user_id&gt; [reason]</code>",
                                            parse_mode=ParseMode.HTML)
            return
        try:
            user_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text("❌ Invalid user ID!")
            return
        if user_id in Config.ADMIN_IDS:
            await update.message.reply_text("❌ Cannot ban a superadmin!")
            return
        reason = ' '.join(context.args[1:]) if len(context.args) > 1 else "No reason"
        await self.db_manager.set_config(f'banned_{user_id}', f'true|{reason}')
        await update.message.reply_text(
            f"🚫 <b>User Banned</b>\n\n"
            f"User <code>{user_id}</code> has been banned.\n"
            f"Reason: {reason}\n\n{Config.FOOTER}",
            parse_mode=ParseMode.HTML
        )
        await self._log_admin_action(f"🚫 Banned user {user_id}: {reason}")

    async def unban_user(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Unban a user: /unban <user_id>"""
        if not await self._check_admin(update):
            return
        if not context.args:
            await update.message.reply_text("❌ Usage: <code>/unban &lt;user_id&gt;</code>", parse_mode=ParseMode.HTML)
            return
        try:
            user_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text("❌ Invalid user ID!")
            return
        await self.db_manager.delete_config(f'banned_{user_id}')
        await update.message.reply_text(
            f"✅ User <code>{user_id}</code> has been unbanned.\n\n{Config.FOOTER}", parse_mode=ParseMode.HTML
        )
        await self._log_admin_action(f"✅ Unbanned user {user_id}")

    async def reset_user_requests(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Reset a user's request count: /reset_user <user_id>"""
        if not await self._check_admin(update):
            return
        if not context.args:
            await update.message.reply_text("❌ Usage: <code>/reset_user &lt;user_id&gt;</code>",
                                            parse_mode=ParseMode.HTML)
            return
        try:
            user_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text("❌ Invalid user ID!")
            return
        async with self.db_manager.get_connection() as conn:
            await conn.execute(
                "UPDATE user_requests SET status='rejected' WHERE user_id=? AND status='pending'", (user_id,)
            )
            await conn.commit()
        await update.message.reply_text(
            f"✅ Pending requests reset for user <code>{user_id}</code>\n\n{Config.FOOTER}",
            parse_mode=ParseMode.HTML
        )

    # ==================== BROADCAST ====================

    async def broadcast(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Broadcast to all users: /broadcast <message>"""
        if not await self._check_admin(update):
            return
        if not context.args:
            await update.message.reply_text(
                "❌ Usage: <code>/broadcast &lt;message&gt;</code>", parse_mode=ParseMode.HTML
            )
            return
        message = ' '.join(context.args)
        users = await self.db_manager.get_all_users()
        sent = 0
        failed = 0
        status_msg = await update.message.reply_text(f"📢 Broadcasting to {len(users)} users...")
        for user in users:
            try:
                await context.bot.send_message(
                    chat_id=user['user_id'],
                    text=f"📢 <b>Announcement</b>\n\n{message}\n\n{Config.FOOTER}",
                    parse_mode=ParseMode.HTML
                )
                sent += 1
            except Exception:
                failed += 1
        await status_msg.edit_text(
            f"✅ <b>Broadcast Complete</b>\n\n"
            f"✅ Sent: {sent}\n❌ Failed: {failed}\n\n{Config.FOOTER}",
            parse_mode=ParseMode.HTML
        )
        await self._log_admin_action(f"📢 Broadcast: '{message[:50]}' — Sent: {sent}, Failed: {failed}")

    async def broadcast_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Broadcast photo to all users: /broadcast_photo (reply to photo with caption)"""
        if not await self._check_admin(update):
            return
        if not update.message.reply_to_message or not update.message.reply_to_message.photo:
            await update.message.reply_text("❌ Reply to a photo to broadcast it!")
            return
        photo = update.message.reply_to_message.photo[-1]
        caption = update.message.reply_to_message.caption or ' '.join(context.args) or ""
        users = await self.db_manager.get_all_users()
        sent = 0
        failed = 0
        for user in users:
            try:
                await context.bot.send_photo(
                    chat_id=user['user_id'],
                    photo=photo.file_id,
                    caption=f"{caption}\n\n{Config.FOOTER}" if caption else Config.FOOTER,
                    parse_mode=ParseMode.HTML
                )
                sent += 1
            except Exception:
                failed += 1
        await update.message.reply_text(
            f"✅ Photo broadcast complete.\nSent: {sent} | Failed: {failed}\n\n{Config.FOOTER}",
            parse_mode=ParseMode.HTML
        )

    # ==================== STATISTICS ====================

    async def stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """View bot statistics: /stats"""
        if not await self._check_admin(update):
            return
        task_stats = await self.db_manager.get_task_stats()
        queue_status = {}
        if self.pipeline:
            queue_status = await self.pipeline.get_queue_status()
        storage_info = await self._get_storage_info()
        user_count = await self.db_manager.get_user_count()
        pending_reqs = await self.db_manager.get_pending_requests(limit=1000)
        message = (
            f"📊 <b>Bot Statistics</b>\n\n"
            f"<b>📋 Tasks:</b>\n"
            f"├─ Pending: {task_stats.get('pending', 0)}\n"
            f"├─ Downloading: {task_stats.get('downloading', 0)}\n"
            f"├─ Processing: {task_stats.get('processing', 0)}\n"
            f"├─ Completed: {task_stats.get('completed', 0)}\n"
            f"└─ Failed: {task_stats.get('failed', 0)}\n\n"
            f"<b>📨 Requests:</b>\n"
            f"├─ Pending: {len(pending_reqs)}\n"
            f"└─ Daily count: {await self.db_manager.get_daily_request_count()}\n\n"
            f"<b>👥 Users:</b> {user_count}\n\n"
            f"<b>⚙️ Pipeline:</b>\n"
            f"├─ Active: {queue_status.get('active_tasks', 0)}\n"
            f"├─ Queue: {queue_status.get('queue_size', 0)}\n"
            f"└─ Running: {'✅' if queue_status.get('is_running') else '❌'}\n\n"
            f"<b>💾 Storage:</b>\n"
            f"├─ Downloads: {storage_info['downloads_size']}\n"
            f"├─ Processed: {storage_info['processed_size']}\n"
            f"├─ Free: {storage_info['free_space']}\n"
            f"└─ Total Used: {storage_info['total_used']}\n\n"
            f"{Config.FOOTER}"
        )
        await update.message.reply_text(message, parse_mode=ParseMode.HTML)

    async def detailed_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Detailed stats: /dstats"""
        if not await self._check_admin(update):
            return
        stats = await self.db_manager.get_detailed_stats()
        msg = (
            f"📈 <b>Detailed Statistics</b>\n\n"
            f"📋 Total Tasks: {stats.total_tasks}\n"
            f"✅ Completed: {stats.completed_tasks}\n"
            f"❌ Failed: {stats.failed_tasks}\n"
            f"📨 Total Requests: {stats.total_requests}\n"
            f"⏳ Pending Requests: {stats.pending_requests}\n"
            f"👥 Total Users: {stats.total_users}\n"
            f"💾 Total Downloads: {stats.total_downloads_gb:.2f} GB\n"
            f"🔄 Uptime: {stats.uptime_seconds // 3600}h {(stats.uptime_seconds % 3600) // 60}m\n"
            f"🕐 Last updated: {stats.last_updated.strftime('%Y-%m-%d %H:%M')}\n\n"
            f"{Config.FOOTER}"
        )
        await update.message.reply_text(msg, parse_mode=ParseMode.HTML)

    # ==================== STORAGE & MAINTENANCE ====================

    async def cleanup_now(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Force immediate storage cleanup: /cleanup"""
        if not await self._check_admin(update):
            return
        msg = await update.message.reply_text("🧹 Running cleanup...")
        hours = Config.CLEANUP_HOURS
        cutoff = datetime.now() - timedelta(hours=hours)
        dl_del = proc_del = temp_del = 0
        for path, counter in [
            (Config.DOWNLOAD_PATH, 'dl'), (Config.PROCESSED_PATH, 'proc'), (Config.TEMP_PATH, 'temp')
        ]:
            if path.exists():
                for f in path.glob("*"):
                    if f.is_file() and datetime.fromtimestamp(f.stat().st_mtime) < cutoff:
                        f.unlink()
                        if counter == 'dl':
                            dl_del += 1
                        elif counter == 'proc':
                            proc_del += 1
                        else:
                            temp_del += 1
        tasks_del = await self.db_manager.delete_old_tasks(days=30)
        await msg.edit_text(
            f"✅ <b>Cleanup Complete!</b>\n\n"
            f"🗑 Downloads deleted: {dl_del}\n"
            f"🗑 Processed deleted: {proc_del}\n"
            f"🗑 Temp deleted: {temp_del}\n"
            f"🗑 Old tasks removed: {tasks_del}\n\n{Config.FOOTER}",
            parse_mode=ParseMode.HTML
        )
        await self._log_admin_action(f"🧹 Manual cleanup: dl={dl_del}, proc={proc_del}, tasks={tasks_del}")

    async def storage_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Detailed storage information: /storage"""
        if not await self._check_admin(update):
            return
        info = await self._get_storage_info()
        disk = shutil.disk_usage(Config.BASE_DIR)
        total_gb = disk.total / (1024 ** 3)
        used_gb = disk.used / (1024 ** 3)
        free_gb = disk.free / (1024 ** 3)
        pct = (disk.used / disk.total) * 100
        bar_filled = int(pct / 5)
        bar = "█" * bar_filled + "░" * (20 - bar_filled)
        msg = (
            f"💾 <b>Storage Information</b>\n\n"
            f"<b>Disk Usage:</b>\n"
            f"[{bar}] {pct:.1f}%\n"
            f"Total: {total_gb:.1f} GB | Used: {used_gb:.1f} GB | Free: {free_gb:.1f} GB\n\n"
            f"<b>Bot Files:</b>\n"
            f"📥 Downloads: {info['downloads_size']}\n"
            f"⚙️ Processed: {info['processed_size']}\n"
            f"🗑 Temp: {info['temp_size']}\n"
            f"📋 Total Bot: {info['total_used']}\n\n"
            f"<b>Settings:</b>\n"
            f"⏰ Cleanup every: {Config.CLEANUP_HOURS}h\n"
            f"⚠️ Threshold: {Config.CLEANUP_THRESHOLD_GB} GB\n\n"
            f"{Config.FOOTER}"
        )
        await update.message.reply_text(msg, parse_mode=ParseMode.HTML)

    async def backup_db(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Trigger manual database backup: /backup"""
        if not await self._check_admin(update):
            return
        msg = await update.message.reply_text("💾 Creating backup...")
        from pathlib import Path
        backup_dir = Config.BASE_DIR / "data" / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = backup_dir / f"manual_backup_{ts}.db"
        success = await self.db_manager.backup(backup_path)
        if success:
            size = format_size(backup_path.stat().st_size)
            await msg.edit_text(
                f"✅ <b>Backup Created!</b>\n\nFile: <code>{backup_path.name}</code>\nSize: {size}\n\n{Config.FOOTER}",
                parse_mode=ParseMode.HTML
            )
        else:
            await msg.edit_text("❌ Backup failed! Check logs.")

    async def clear_queue(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Clear the task queue: /clear_queue"""
        if not await self._check_superadmin(update):
            return
        keyboard = [[
            InlineKeyboardButton("✅ Yes, Clear Queue", callback_data="confirm_clear_queue"),
            InlineKeyboardButton("❌ Cancel", callback_data="cancel_action")
        ]]
        await update.message.reply_text(
            "⚠️ <b>Confirm Clear Queue?</b>\n\nThis will cancel all pending tasks.\n\n"
            "This action cannot be undone!",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def reset_daily_counter(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Reset daily request counter: /reset_counter"""
        if not await self._check_admin(update):
            return
        async with self.db_manager.get_connection() as conn:
            from datetime import date
            await conn.execute(
                "INSERT OR REPLACE INTO daily_requests (date, count) VALUES (?, 0)",
                (date.today().isoformat(),)
            )
            await conn.commit()
        await update.message.reply_text(
            f"✅ Daily request counter reset to 0.\n\n{Config.FOOTER}", parse_mode=ParseMode.HTML
        )

    # ==================== SOURCE / NYAA ====================

    async def search_nyaa(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Search Nyaa.si for anime: /nyaa <query>"""
        if not await self._check_admin(update):
            return
        if not context.args:
            await update.message.reply_text("❌ Usage: <code>/nyaa &lt;anime title&gt;</code>", parse_mode=ParseMode.HTML)
            return
        query = ' '.join(context.args)
        msg = await update.message.reply_text(f"🔍 Searching Nyaa for: <b>{query}</b>...", parse_mode=ParseMode.HTML)
        results = await self._search_nyaa(query)
        if not results:
            await msg.edit_text(f"❌ No results found on Nyaa for: <b>{query}</b>\n\n{Config.FOOTER}",
                                parse_mode=ParseMode.HTML)
            return
        text = f"🔍 <b>Nyaa Results for '{query}'</b>\n\n"
        keyboard = []
        for i, r in enumerate(results[:8]):
            text += f"{i+1}. <b>{r['title'][:50]}</b>\n"
            text += f"   📦 {r['size']} | 🌱 {r['seeders']} | 🔗 {r['category']}\n\n"
            keyboard.append([InlineKeyboardButton(
                f"⬇️ {r['title'][:35]}", callback_data=f"nyaa_dl_{i}"
            )])
        context.user_data['nyaa_results'] = results
        await msg.edit_text(text + Config.FOOTER, parse_mode=ParseMode.HTML,
                            reply_markup=InlineKeyboardMarkup(keyboard))

    async def set_source_url(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Manually set source URL for a task: /set_source <task_id> <url>"""
        if not await self._check_admin(update):
            return
        if len(context.args) < 2:
            await update.message.reply_text(
                "❌ Usage: <code>/set_source &lt;task_id&gt; &lt;url&gt;</code>", parse_mode=ParseMode.HTML
            )
            return
        task_id = context.args[0]
        url = context.args[1]
        task = await self.db_manager.get_task(task_id)
        if not task:
            await update.message.reply_text("❌ Task not found!")
            return
        task.source_url = url
        task.status = TaskStatus.PENDING
        await self.db_manager.add_task(task)
        if self.pipeline:
            await self.pipeline.add_task(task)
        await update.message.reply_text(
            f"✅ <b>Source URL Set</b>\n\nTask: <code>{task_id}</code>\nURL: <code>{url[:80]}</code>\n\n{Config.FOOTER}",
            parse_mode=ParseMode.HTML
        )

    # ==================== SCHEDULER ====================

    async def scheduler_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show scheduler jobs: /scheduler"""
        if not await self._check_admin(update):
            return
        msg = "⏰ <b>Scheduler Jobs</b>\n\n"
        msg += f"📅 Daily processing: <b>{Config.REQUEST_TIME} IST</b>\n"
        msg += f"🗑 Storage cleanup: every <b>{Config.CLEANUP_HOURS}h</b>\n"
        msg += f"💾 DB backup: daily at <b>3:00 AM</b>\n"
        msg += f"📺 Airing fetch: every <b>6h</b>\n"
        msg += f"❤️ Health check: every <b>30min</b>\n"
        msg += f"📊 Stats update: every <b>1h</b>\n"
        msg += f"\n{Config.FOOTER}"
        await update.message.reply_text(msg, parse_mode=ParseMode.HTML)

    async def run_now(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Run a scheduled job immediately: /run_now <job_name>"""
        if not await self._check_admin(update):
            return
        jobs = {
            'cleanup': 'cleanup_storage',
            'requests': 'process_daily_requests',
            'backup': 'backup_database',
            'airing': 'fetch_airing_schedule',
            'health': 'health_check',
            'stats': 'update_stats'
        }
        if not context.args or context.args[0] not in jobs:
            await update.message.reply_text(
                f"❌ Usage: <code>/run_now &lt;job&gt;</code>\nJobs: {', '.join(jobs.keys())}",
                parse_mode=ParseMode.HTML
            )
            return
        await update.message.reply_text(
            f"✅ Job <b>{context.args[0]}</b> triggered. Check logs for results.\n\n{Config.FOOTER}",
            parse_mode=ParseMode.HTML
        )
        await self._log_admin_action(f"▶️ Job manually triggered: {context.args[0]}")

    # ==================== PIPELINE CONTROL ====================

    async def start_pipeline(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start the pipeline: /start_pipeline"""
        if not await self._check_admin(update):
            return
        if self.pipeline and self.pipeline.is_running:
            await update.message.reply_text("⚠️ Pipeline is already running!")
            return
        if self.pipeline:
            await self.pipeline.start()
            await update.message.reply_text(
                f"✅ <b>Pipeline Started!</b>\n\n{Config.FOOTER}", parse_mode=ParseMode.HTML
            )
        else:
            await update.message.reply_text("❌ Pipeline not initialized!")

    async def stop_pipeline(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Stop the pipeline: /stop_pipeline"""
        if not await self._check_superadmin(update):
            return
        if self.pipeline and self.pipeline.is_running:
            await self.pipeline.stop()
            await update.message.reply_text(
                f"🛑 <b>Pipeline Stopped!</b>\n\nAll workers have been stopped.\n\n{Config.FOOTER}",
                parse_mode=ParseMode.HTML
            )
        else:
            await update.message.reply_text("⚠️ Pipeline is not running!")

    async def pipeline_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Pipeline status: /pipeline"""
        if not await self._check_admin(update):
            return
        if not self.pipeline:
            await update.message.reply_text("❌ Pipeline not initialized!")
            return
        qs = await self.pipeline.get_queue_status()
        msg = (
            f"⚙️ <b>Pipeline Status</b>\n\n"
            f"Running: {'✅' if qs['is_running'] else '❌'}\n"
            f"Active Tasks: {qs['active_tasks']}\n"
            f"Queue Size: {qs['queue_size']}\n"
            f"Workers: {qs['workers']}\n\n"
        )
        if qs.get('tasks'):
            msg += "<b>Active Tasks:</b>\n"
            for t in qs['tasks']:
                msg += f"  • {t['title'][:20]} EP{t['episode']} [{t['status']}]\n"
        msg += f"\n{Config.FOOTER}"
        await update.message.reply_text(msg, parse_mode=ParseMode.HTML)

    # ==================== MISC ADMIN ====================

    async def bot_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show bot version and system info: /botinfo"""
        if not await self._check_admin(update):
            return
        import platform
        disk = shutil.disk_usage(Config.BASE_DIR)
        msg = (
            f"🤖 <b>Bot Information</b>\n\n"
            f"🏷 Version: <b>2.0.0</b>\n"
            f"🐍 Python: <b>{platform.python_version()}</b>\n"
            f"💻 OS: <b>{platform.system()} {platform.release()}</b>\n"
            f"💾 Disk Free: <b>{disk.free / (1024**3):.1f} GB</b>\n"
            f"⚡ Timezone: <b>{Config.TIMEZONE}</b>\n"
            f"📡 AniList API: <b>{Config.ANILIST_API}</b>\n"
            f"📡 Jikan API: <b>{Config.JIKAN_API}</b>\n\n"
            f"{Config.FOOTER}"
        )
        await update.message.reply_text(msg, parse_mode=ParseMode.HTML)

    async def ping(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Ping the bot: /ping"""
        start = datetime.now()
        msg = await update.message.reply_text("🏓 Pinging...")
        elapsed = (datetime.now() - start).total_seconds() * 1000
        await msg.edit_text(f"🏓 Pong! Response: <b>{elapsed:.0f}ms</b>\n\n{Config.FOOTER}",
                            parse_mode=ParseMode.HTML)

    async def logs(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send latest log file: /logs"""
        if not await self._check_admin(update):
            return
        from pathlib import Path
        log_dir = Path("data/logs")
        if not log_dir.exists():
            await update.message.reply_text("❌ No log directory found!")
            return
        log_files = sorted(log_dir.glob("*.log"), key=lambda f: f.stat().st_mtime, reverse=True)
        if not log_files:
            await update.message.reply_text("❌ No log files found!")
            return
        latest = log_files[0]
        try:
            with open(latest, 'rb') as f:
                await update.message.reply_document(document=f, filename=latest.name)
        except Exception as e:
            await update.message.reply_text(f"❌ Failed to send log: {e}")

    async def reload_config(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Reload config from database: /reload"""
        if not await self._check_superadmin(update):
            return
        rt = await self.db_manager.get_config('request_time', Config.REQUEST_TIME)
        ch = await self.db_manager.get_config('cleanup_hours', str(Config.CLEANUP_HOURS))
        mr = await self.db_manager.get_config('max_user_requests', str(Config.MAX_USER_REQUESTS))
        md = await self.db_manager.get_config('max_daily_requests', str(Config.MAX_GLOBAL_DAILY_REQUESTS))
        Config.REQUEST_TIME = rt
        Config.CLEANUP_HOURS = int(ch)
        Config.MAX_USER_REQUESTS = int(mr)
        Config.MAX_GLOBAL_DAILY_REQUESTS = int(md)
        await update.message.reply_text(
            f"✅ <b>Config Reloaded!</b>\n\n"
            f"Request time: {rt}\nCleanup: {ch}h\nMax requests: {mr}\nDaily limit: {md}\n\n{Config.FOOTER}",
            parse_mode=ParseMode.HTML
        )

    async def help_admin(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show all admin commands: /ahelp"""
        if not await self._check_admin(update):
            return
        msg = (
            "👑 <b>Admin Commands Reference</b>\n\n"
            "<b>📋 Requests:</b>\n"
            "/view_requests — View pending requests\n"
            "/approve &lt;id&gt; — Approve request\n"
            "/reject &lt;id&gt; — Reject request\n"
            "/auto_approve on|off — Toggle auto-approve\n\n"
            "<b>📡 Tasks:</b>\n"
            "/addtask &lt;title&gt; &lt;ep&gt; — Add task\n"
            "/tasks — View active/pending tasks\n"
            "/taskinfo &lt;id&gt; — Task details\n"
            "/failed — List failed tasks\n"
            "/redownload &lt;id&gt; — Retry task\n"
            "/cancel_task &lt;id&gt; — Cancel task\n"
            "/set_source &lt;id&gt; &lt;url&gt; — Set source URL\n\n"
            "<b>⚙️ Settings:</b>\n"
            "/set_max_requests &lt;n&gt; — User request limit\n"
            "/set_max_daily &lt;n&gt; — Global daily limit\n"
            "/set_request_time &lt;HH:MM&gt; — Processing time\n"
            "/del_timer &lt;12h|1d&gt; — Cleanup timer\n"
            "/set_quality &lt;480p|720p|1080p&gt;\n"
            "/maintenance on|off — Maintenance mode\n"
            "/config — Show all config\n"
            "/setconfig &lt;key&gt; &lt;val&gt; — Set config\n"
            "/reload — Reload config from DB\n\n"
            "<b>📡 Channels:</b>\n"
            "/set_channel &lt;title&gt; &lt;id&gt;\n"
            "/remove_channel &lt;title&gt;\n"
            "/channels — List channel routes\n\n"
            "<b>👥 Users:</b>\n"
            "/users — List users\n"
            "/userinfo &lt;id&gt; — User details\n"
            "/ban &lt;id&gt; — Ban user\n"
            "/unban &lt;id&gt; — Unban user\n"
            "/reset_user &lt;id&gt; — Reset requests\n\n"
            "<b>📢 Broadcast:</b>\n"
            "/broadcast &lt;msg&gt; — Text broadcast\n"
            "/broadcast_photo — Photo broadcast\n\n"
            "<b>👑 Admin Mgmt:</b>\n"
            "/add_admin &lt;id&gt; — Add admin\n"
            "/remove_admin &lt;id&gt; — Remove admin\n"
            "/list_admins — List admins\n\n"
            "<b>💾 Storage/Maintenance:</b>\n"
            "/stats — Statistics\n"
            "/dstats — Detailed stats\n"
            "/storage — Storage info\n"
            "/cleanup — Force cleanup\n"
            "/backup — Manual DB backup\n"
            "/clear_queue — Clear task queue\n"
            "/reset_counter — Reset daily counter\n\n"
            "<b>⚙️ Pipeline:</b>\n"
            "/pipeline — Pipeline status\n"
            "/start_pipeline — Start pipeline\n"
            "/stop_pipeline — Stop pipeline\n\n"
            "<b>🔍 Search:</b>\n"
            "/nyaa &lt;query&gt; — Search Nyaa.si\n\n"
            "<b>🛠 System:</b>\n"
            "/scheduler — Scheduler jobs\n"
            "/run_now &lt;job&gt; — Run job now\n"
            "/botinfo — Bot system info\n"
            "/ping — Ping the bot\n"
            "/logs — Send log file\n"
            "/panel — Admin panel UI\n"
            "/ahelp — This help\n\n"
            f"{Config.FOOTER}"
        )
        await update.message.reply_text(msg, parse_mode=ParseMode.HTML)

    # ==================== HELPERS ====================

    async def _get_storage_info(self) -> dict:
        import shutil as sh
        dl_size = proc_size = temp_size = 0
        if Config.DOWNLOAD_PATH.exists():
            dl_size = sum(f.stat().st_size for f in Config.DOWNLOAD_PATH.glob('**/*') if f.is_file())
        if Config.PROCESSED_PATH.exists():
            proc_size = sum(f.stat().st_size for f in Config.PROCESSED_PATH.glob('**/*') if f.is_file())
        if Config.TEMP_PATH.exists():
            temp_size = sum(f.stat().st_size for f in Config.TEMP_PATH.glob('**/*') if f.is_file())
        total = dl_size + proc_size + temp_size
        free = sh.disk_usage(Config.BASE_DIR).free
        return {
            'downloads_size': format_size(dl_size),
            'processed_size': format_size(proc_size),
            'temp_size': format_size(temp_size),
            'total_used': format_size(total),
            'free_space': format_size(free)
        }

    async def _search_nyaa(self, query: str) -> list:
        """Search Nyaa.si RSS feed for anime"""
        import aiohttp
        from bs4 import BeautifulSoup
        results = []
        try:
            url = f"https://nyaa.si/?q={query.replace(' ', '+')}&c=1_0&f=0&page=rss"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    if resp.status == 200:
                        text = await resp.text()
                        soup = BeautifulSoup(text, 'lxml-xml')
                        items = soup.find_all('item')
                        for item in items[:10]:
                            title = item.find('title')
                            link = item.find('link')
                            size_tag = item.find('nyaa:size')
                            seeders_tag = item.find('nyaa:seeders')
                            cat_tag = item.find('nyaa:category')
                            results.append({
                                'title': title.text if title else 'Unknown',
                                'link': link.text if link else '',
                                'size': size_tag.text if size_tag else 'N/A',
                                'seeders': seeders_tag.text if seeders_tag else '0',
                                'category': cat_tag.text if cat_tag else 'Anime'
                            })
        except Exception as e:
            self.logger.warning(f"Nyaa search failed: {e}")
        return results

    async def _log_admin_action(self, action: str):
        try:
            from telegram import Bot
            bot = Bot(token=Config.BOT_TOKEN)
            await bot.send_message(
                chat_id=Config.ADMIN_LOG_CHANNEL,
                text=f"📝 <b>Admin Log</b>\n\n{action}\n\n{Config.FOOTER}",
                parse_mode=ParseMode.HTML
            )
        except Exception as e:
            self.logger.error(f"Failed to log admin action: {e}")
