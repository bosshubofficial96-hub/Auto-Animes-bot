"""
Callback Query Handlers for Inline Buttons
"""

import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from bot.config import Config
from bot.database.database import DatabaseManager
from bot.database.models import RequestStatus, AnimeTask, TaskStatus
from bot.utils.logger import setup_logger
from bot.utils.helpers import generate_task_id, format_size


class CallbackHandlers:
    """Handler for all callback queries"""

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.logger = setup_logger("callback_handlers")
        self.pipeline = None

    def set_pipeline(self, pipeline):
        self.pipeline = pipeline

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle all callback queries"""
        query = update.callback_query
        await query.answer()

        data = query.data
        user_id = query.from_user.id
        is_admin = await self.db_manager.is_admin(user_id) or user_id in Config.ADMIN_IDS

        # ── Request management ──
        if data.startswith('view_req_'):
            if not is_admin:
                await query.edit_message_text("❌ Admin access required!")
                return
            request_id = int(data.split('_')[2])
            await self._view_request_details(query, request_id)

        elif data.startswith('approve_req_'):
            if not is_admin:
                await query.edit_message_text("❌ Admin access required!")
                return
            request_id = int(data.split('_')[2])
            await self._approve_request(query, context, request_id)

        elif data.startswith('reject_req_'):
            if not is_admin:
                await query.edit_message_text("❌ Admin access required!")
                return
            request_id = int(data.split('_')[2])
            await self._reject_request(query, request_id)

        elif data == 'approve_all':
            if not is_admin:
                await query.edit_message_text("❌ Admin access required!")
                return
            await self._approve_all_requests(query, context)

        elif data == 'reject_all':
            if not is_admin:
                await query.edit_message_text("❌ Admin access required!")
                return
            await self._reject_all_requests(query)

        # ── Anime selection ──
        elif data.startswith('select_anime_') or data.startswith('sa_'):
            prefix = 'select_anime_' if data.startswith('select_anime_') else 'sa_'
            anime_title = data[len(prefix):]
            request_id = await self.db_manager.add_user_request(
                user_id, anime_title,
                user_name=query.from_user.username or query.from_user.first_name
            )
            await query.edit_message_text(
                f"✅ <b>Request Added!</b>\n\n"
                f"🎬 Anime: <b>{anime_title}</b>\n"
                f"📋 Request ID: <code>#{request_id}</code>\n\n"
                f"Use <code>/status</code> to track it.\n\n{Config.FOOTER}",
                parse_mode=ParseMode.HTML
            )

        # ── Task retry / cancel ──
        elif data.startswith('retry_task_'):
            if not is_admin:
                await query.edit_message_text("❌ Admin access required!")
                return
            task_id = data.replace('retry_task_', '')
            await self._retry_task(query, context, task_id)

        elif data.startswith('cancel_task_'):
            if not is_admin:
                await query.edit_message_text("❌ Admin access required!")
                return
            task_id = data.replace('cancel_task_', '')
            await self.db_manager.update_task_status(task_id, TaskStatus.CANCELLED)
            await query.edit_message_text(
                f"🚫 Task <code>{task_id}</code> cancelled.\n\n{Config.FOOTER}",
                parse_mode=ParseMode.HTML
            )

        # ── Admin panel sections ──
        elif data == 'panel_stats':
            if not is_admin:
                await query.edit_message_text("❌ Admin access required!")
                return
            await self._panel_stats(query)

        elif data == 'panel_storage':
            if not is_admin:
                await query.edit_message_text("❌ Admin access required!")
                return
            await self._panel_storage(query)

        elif data == 'panel_tasks':
            if not is_admin:
                await query.edit_message_text("❌ Admin access required!")
                return
            await self._panel_tasks(query)

        elif data == 'panel_requests':
            if not is_admin:
                await query.edit_message_text("❌ Admin access required!")
                return
            await self._panel_requests(query)

        elif data == 'panel_maintenance':
            if not is_admin:
                await query.edit_message_text("❌ Admin access required!")
                return
            await self._panel_maintenance(query)

        elif data == 'panel_info':
            if not is_admin:
                await query.edit_message_text("❌ Admin access required!")
                return
            await self._panel_info(query)

        elif data == 'panel_users':
            if not is_admin:
                await query.edit_message_text("❌ Admin access required!")
                return
            await self._panel_users(query)

        elif data == 'panel_settings':
            if not is_admin:
                await query.edit_message_text("❌ Admin access required!")
                return
            await self._panel_settings(query)

        elif data == 'panel_broadcast':
            if not is_admin:
                await query.edit_message_text("❌ Admin access required!")
                return
            await query.edit_message_text(
                f"📢 <b>Broadcast</b>\n\nUse <code>/broadcast &lt;message&gt;</code> to send a message to all users.\n\n"
                f"For photos: <code>/broadcast_photo</code> (reply to a photo).\n\n{Config.FOOTER}",
                parse_mode=ParseMode.HTML
            )

        elif data == 'panel_cleanup':
            if not is_admin:
                await query.edit_message_text("❌ Admin access required!")
                return
            await self._panel_do_cleanup(query)

        # ── Queue clear confirm ──
        elif data == 'confirm_clear_queue':
            if not is_admin:
                await query.edit_message_text("❌ Admin access required!")
                return
            async with self.db_manager.get_connection() as conn:
                await conn.execute(
                    "UPDATE tasks SET status='cancelled' WHERE status IN ('pending','fetching')"
                )
                await conn.commit()
            await query.edit_message_text(
                f"✅ <b>Queue Cleared!</b>\n\nAll pending tasks cancelled.\n\n{Config.FOOTER}",
                parse_mode=ParseMode.HTML
            )
            await self._log_admin_action(f"🗑 Queue cleared by {query.from_user.id}")

        elif data == 'cancel_action':
            await query.edit_message_text("❌ Action cancelled.")

        # ── User actions ──
        elif data.startswith('user_requests_'):
            if not is_admin:
                await query.edit_message_text("❌ Admin access required!")
                return
            uid = int(data.replace('user_requests_', ''))
            requests = await self.db_manager.get_user_requests(uid, limit=10)
            msg = f"📋 <b>Requests by user {uid}</b>\n\n"
            for r in requests:
                msg += f"#{r['request_id']} — {r['anime_title'][:30]} [{r['status']}]\n"
            await query.edit_message_text(msg + f"\n{Config.FOOTER}", parse_mode=ParseMode.HTML)

        elif data.startswith('ban_user_'):
            if not is_admin:
                await query.edit_message_text("❌ Admin access required!")
                return
            uid = int(data.replace('ban_user_', ''))
            await self.db_manager.set_config(f'banned_{uid}', 'true|Admin action')
            await query.edit_message_text(
                f"🚫 User <code>{uid}</code> has been banned.\n\n{Config.FOOTER}",
                parse_mode=ParseMode.HTML
            )
            await self._log_admin_action(f"🚫 User {uid} banned via panel by {query.from_user.id}")

        # ── Pagination ──
        elif data.startswith('req_page_'):
            if not is_admin:
                await query.edit_message_text("❌ Admin access required!")
                return
            page = int(data.replace('req_page_', ''))
            limit = 15
            pending = await self.db_manager.get_pending_requests(limit=limit * (page + 2))
            pending = pending[page * limit:(page + 1) * limit]
            if not pending:
                await query.edit_message_text("📭 No more pending requests.", parse_mode=ParseMode.HTML)
                return
            keyboard = []
            for req in pending:
                txt = f"#{req['request_id']} — {req['anime_title'][:25]}"
                keyboard.append([InlineKeyboardButton(txt, callback_data=f"view_req_{req['request_id']}")])
            nav = []
            if page > 0:
                nav.append(InlineKeyboardButton("◀️ Prev", callback_data=f"req_page_{page - 1}"))
            nav.append(InlineKeyboardButton("▶️ Next", callback_data=f"req_page_{page + 1}"))
            keyboard.append(nav)
            await query.edit_message_reply_markup(InlineKeyboardMarkup(keyboard))

    # ──────────────────────────────────────────────
    # Request detail handlers
    # ──────────────────────────────────────────────

    async def _view_request_details(self, query, request_id: int):
        """View full request details with action buttons"""
        req = await self.db_manager.get_request_by_id(request_id)
        if not req:
            await query.edit_message_text(f"❌ Request #{request_id} not found!")
            return
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Approve", callback_data=f"approve_req_{request_id}"),
                InlineKeyboardButton("❌ Reject", callback_data=f"reject_req_{request_id}")
            ],
            [InlineKeyboardButton("◀️ Back to List", callback_data="panel_requests")]
        ])
        requested_at = str(req.get('requested_at', 'N/A'))[:16]
        await query.edit_message_text(
            f"📋 <b>Request #{request_id}</b>\n\n"
            f"🎬 Anime: <b>{req['anime_title']}</b>\n"
            f"👤 User ID: <code>{req['user_id']}</code>\n"
            f"📺 Episode: {req.get('episode', 'N/A')}\n"
            f"🎯 Quality: {req.get('quality', 'Default')}\n"
            f"📊 Status: <b>{req['status'].upper()}</b>\n"
            f"📅 Requested: {requested_at}\n\n"
            f"Select an action:",
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard
        )

    async def _approve_request(self, query, context, request_id: int):
        """Approve request and create pipeline task"""
        req = await self.db_manager.get_request_by_id(request_id)
        if not req:
            await query.edit_message_text(f"❌ Request #{request_id} not found!")
            return
        task_id = generate_task_id()
        episode = req.get('episode') or 1
        quality = req.get('quality') or "720p"
        task = AnimeTask(
            task_id=task_id,
            title=req['anime_title'],
            episode=episode,
            quality=quality,
            status=TaskStatus.PENDING,
            requested_by=req['user_id'],
            metadata={'approved_by': query.from_user.id, 'request_id': request_id}
        )
        await self.db_manager.add_task(task)
        await self.db_manager.update_request_status(request_id, RequestStatus.APPROVED, task_id)
        if self.pipeline:
            await self.pipeline.add_task(task)
        await query.edit_message_text(
            f"✅ <b>Request Approved!</b>\n\n"
            f"🎬 Anime: <b>{req['anime_title']}</b>\n"
            f"📺 Episode: {episode} | 🎯 {quality}\n"
            f"🔗 Task: <code>{task_id}</code>\n\n{Config.FOOTER}",
            parse_mode=ParseMode.HTML
        )
        await self._log_admin_action(f"✅ Request #{request_id} approved → {task_id} by {query.from_user.id}")

    async def _reject_request(self, query, request_id: int):
        """Reject a user request"""
        req = await self.db_manager.get_request_by_id(request_id)
        if not req:
            await query.edit_message_text(f"❌ Request #{request_id} not found!")
            return
        await self.db_manager.update_request_status(request_id, RequestStatus.REJECTED)
        # Notify user
        try:
            from telegram import Bot
            bot = Bot(token=Config.BOT_TOKEN)
            await bot.send_message(
                chat_id=req['user_id'],
                text=f"❌ <b>Request Rejected</b>\n\n"
                     f"Your request for <b>{req['anime_title']}</b> was rejected by an admin.\n\n{Config.FOOTER}",
                parse_mode=ParseMode.HTML
            )
        except Exception:
            pass
        await query.edit_message_text(
            f"❌ <b>Request Rejected</b>\n\nRequest #{request_id} has been rejected.\n\n{Config.FOOTER}",
            parse_mode=ParseMode.HTML
        )
        await self._log_admin_action(f"❌ Request #{request_id} rejected by {query.from_user.id}")

    async def _approve_all_requests(self, query, context):
        """Approve all pending requests"""
        pending = await self.db_manager.get_pending_requests(limit=200)
        approved = 0
        for req in pending:
            task_id = generate_task_id()
            task = AnimeTask(
                task_id=task_id,
                title=req['anime_title'],
                episode=req.get('episode') or 1,
                quality=req.get('quality') or "720p",
                status=TaskStatus.PENDING,
                requested_by=req['user_id'],
                metadata={'bulk_approved': True}
            )
            await self.db_manager.add_task(task)
            await self.db_manager.update_request_status(req['request_id'], RequestStatus.APPROVED, task_id)
            if self.pipeline:
                await self.pipeline.add_task(task)
            approved += 1
        await query.edit_message_text(
            f"✅ <b>Bulk Approval Complete!</b>\n\n"
            f"Approved <b>{approved}</b> requests and added them to pipeline.\n\n{Config.FOOTER}",
            parse_mode=ParseMode.HTML
        )
        await self._log_admin_action(f"✅ Bulk approved {approved} requests by {query.from_user.id}")

    async def _reject_all_requests(self, query):
        """Reject all pending requests"""
        pending = await self.db_manager.get_pending_requests(limit=200)
        rejected = 0
        for req in pending:
            await self.db_manager.update_request_status(req['request_id'], RequestStatus.REJECTED)
            rejected += 1
        await query.edit_message_text(
            f"❌ <b>Bulk Rejection Complete</b>\n\nRejected <b>{rejected}</b> requests.\n\n{Config.FOOTER}",
            parse_mode=ParseMode.HTML
        )
        await self._log_admin_action(f"❌ Bulk rejected {rejected} requests by {query.from_user.id}")

    async def _retry_task(self, query, context, task_id: str):
        """Retry a failed task"""
        task = await self.db_manager.get_task(task_id)
        if not task:
            await query.edit_message_text(f"❌ Task {task_id} not found!")
            return
        task.status = TaskStatus.PENDING
        task.error_log = None
        task.retry_count += 1
        await self.db_manager.add_task(task)
        if self.pipeline:
            await self.pipeline.add_task(task)
        await query.edit_message_text(
            f"🔄 <b>Task Queued for Retry</b>\n\n"
            f"Task: <code>{task_id}</code>\n"
            f"{task.title} EP{task.episode}\n"
            f"Retry count: {task.retry_count}\n\n{Config.FOOTER}",
            parse_mode=ParseMode.HTML
        )
        await self._log_admin_action(f"🔄 Task {task_id} retried by {query.from_user.id}")

    # ──────────────────────────────────────────────
    # Panel section handlers
    # ──────────────────────────────────────────────

    async def _panel_stats(self, query):
        task_stats = await self.db_manager.get_task_stats()
        user_count = await self.db_manager.get_user_count()
        pending_reqs = await self.db_manager.get_pending_requests(limit=1)
        msg = (
            f"📊 <b>Quick Stats</b>\n\n"
            f"✅ Completed: {task_stats.get('completed', 0)}\n"
            f"❌ Failed: {task_stats.get('failed', 0)}\n"
            f"⏳ Pending tasks: {task_stats.get('pending', 0)}\n"
            f"📨 Pending requests: {await self.db_manager.get_daily_request_count()}\n"
            f"👥 Users: {user_count}\n\n"
            f"Use /stats for full details.\n\n{Config.FOOTER}"
        )
        keyboard = [[InlineKeyboardButton("◀️ Back", callback_data="back_panel")]]
        await query.edit_message_text(msg, parse_mode=ParseMode.HTML)

    async def _panel_storage(self, query):
        import shutil
        from bot.utils.helpers import format_size
        dl = proc = 0
        if Config.DOWNLOAD_PATH.exists():
            dl = sum(f.stat().st_size for f in Config.DOWNLOAD_PATH.glob('**/*') if f.is_file())
        if Config.PROCESSED_PATH.exists():
            proc = sum(f.stat().st_size for f in Config.PROCESSED_PATH.glob('**/*') if f.is_file())
        disk = shutil.disk_usage(Config.BASE_DIR)
        free_gb = disk.free / (1024 ** 3)
        msg = (
            f"💾 <b>Storage</b>\n\n"
            f"📥 Downloads: {format_size(dl)}\n"
            f"⚙️ Processed: {format_size(proc)}\n"
            f"🆓 Free: {free_gb:.1f} GB\n\n"
            f"Use /cleanup to free space.\n\n{Config.FOOTER}"
        )
        await query.edit_message_text(msg, parse_mode=ParseMode.HTML)

    async def _panel_tasks(self, query):
        active = await self.db_manager.get_active_tasks()
        pending = await self.db_manager.get_pending_tasks(limit=5)
        msg = f"📡 <b>Tasks</b>\n\n🔄 Active: {len(active)}\n⏳ Pending: {len(pending)}\n\n"
        for t in active[:5]:
            msg += f"• {t.title[:20]} EP{t.episode} [{t.status.value}]\n"
        msg += f"\nUse /tasks for full view.\n\n{Config.FOOTER}"
        await query.edit_message_text(msg, parse_mode=ParseMode.HTML)

    async def _panel_requests(self, query):
        pending = await self.db_manager.get_pending_requests(limit=10)
        if not pending:
            await query.edit_message_text(f"📭 No pending requests.\n\n{Config.FOOTER}", parse_mode=ParseMode.HTML)
            return
        keyboard = []
        for req in pending[:8]:
            txt = f"#{req['request_id']} — {req['anime_title'][:22]}"
            keyboard.append([InlineKeyboardButton(txt, callback_data=f"view_req_{req['request_id']}")])
        keyboard.append([
            InlineKeyboardButton("✅ Approve All", callback_data="approve_all"),
            InlineKeyboardButton("❌ Reject All", callback_data="reject_all")
        ])
        await query.edit_message_text(
            f"📋 <b>Pending Requests ({len(pending)})</b>\n\n{Config.FOOTER}",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def _panel_maintenance(self, query):
        current = await self.db_manager.get_config('maintenance_mode', 'false')
        state = '🔧 ON' if current == 'true' else '✅ OFF'
        new_val = 'false' if current == 'true' else 'true'
        new_label = '✅ Turn OFF' if current == 'true' else '🔧 Turn ON'
        keyboard = [[InlineKeyboardButton(new_label, callback_data=f"toggle_maintenance_{new_val}")]]
        await query.edit_message_text(
            f"🔧 <b>Maintenance Mode: {state}</b>\n\n"
            f"When ON, regular users cannot use the bot.\n\n{Config.FOOTER}",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def _panel_info(self, query):
        import platform
        version = await self.db_manager.get_config('bot_version', '2.0.0')
        msg = (
            f"💡 <b>Bot Info</b>\n\n"
            f"🏷 Version: {version}\n"
            f"🐍 Python: {platform.python_version()}\n"
            f"⚡ Timezone: {Config.TIMEZONE}\n"
            f"📅 Request time: {Config.REQUEST_TIME}\n"
            f"🗑 Cleanup: every {Config.CLEANUP_HOURS}h\n\n"
            f"Use /botinfo for full details.\n\n{Config.FOOTER}"
        )
        await query.edit_message_text(msg, parse_mode=ParseMode.HTML)

    async def _panel_users(self, query):
        count = await self.db_manager.get_user_count()
        admins = await self.db_manager.get_admins()
        msg = (
            f"👥 <b>Users</b>\n\n"
            f"Total users: {count}\n"
            f"DB admins: {len(admins)}\n"
            f"Superadmins: {len(Config.ADMIN_IDS)}\n\n"
            f"Use /users, /userinfo, /ban, /unban for management.\n\n{Config.FOOTER}"
        )
        await query.edit_message_text(msg, parse_mode=ParseMode.HTML)

    async def _panel_settings(self, query):
        msg = (
            f"⚙️ <b>Settings</b>\n\n"
            f"Max user requests: {Config.MAX_USER_REQUESTS}\n"
            f"Daily limit: {Config.MAX_GLOBAL_DAILY_REQUESTS}\n"
            f"Processing time: {Config.REQUEST_TIME} IST\n"
            f"Cleanup timer: {Config.CLEANUP_HOURS}h\n"
            f"Qualities: {', '.join(Config.QUALITY_OPTIONS)}\n\n"
            f"Use /config for all settings.\n\n{Config.FOOTER}"
        )
        await query.edit_message_text(msg, parse_mode=ParseMode.HTML)

    async def _panel_do_cleanup(self, query):
        from datetime import timedelta
        cutoff = __import__('datetime').datetime.now() - timedelta(hours=Config.CLEANUP_HOURS)
        dl_del = proc_del = temp_del = 0
        for path, counter in [
            (Config.DOWNLOAD_PATH, 'dl'),
            (Config.PROCESSED_PATH, 'proc'),
            (Config.TEMP_PATH, 'temp')
        ]:
            if path.exists():
                for f in path.glob("*"):
                    if f.is_file() and __import__('datetime').datetime.fromtimestamp(f.stat().st_mtime) < cutoff:
                        f.unlink()
                        if counter == 'dl':
                            dl_del += 1
                        elif counter == 'proc':
                            proc_del += 1
                        else:
                            temp_del += 1
        tasks_del = await self.db_manager.delete_old_tasks(days=30)
        await query.edit_message_text(
            f"✅ <b>Cleanup Done!</b>\n\n"
            f"🗑 Downloads: {dl_del}\n"
            f"🗑 Processed: {proc_del}\n"
            f"🗑 Temp: {temp_del}\n"
            f"🗑 Old tasks: {tasks_del}\n\n{Config.FOOTER}",
            parse_mode=ParseMode.HTML
        )

    async def _log_admin_action(self, action: str):
        try:
            from telegram import Bot
            bot = Bot(token=Config.BOT_TOKEN)
            await bot.send_message(
                chat_id=Config.ADMIN_LOG_CHANNEL,
                text=f"📝 <b>Admin Action</b>\n\n{action}\n\n{Config.FOOTER}",
                parse_mode=ParseMode.HTML
            )
        except Exception as e:
            self.logger.error(f"Failed to log admin action: {e}")
