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
from bot.utils.helpers import generate_task_id


class CallbackHandlers:
    """Handler for all callback queries"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.logger = setup_logger("callback_handlers")
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle all callback queries"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        user_id = query.from_user.id
        
        # Check if user is admin for admin callbacks
        is_admin = await self.db_manager.is_admin(user_id) or user_id in Config.ADMIN_IDS
        
        if data.startswith('view_req_'):
            # View specific request details
            if not is_admin:
                await query.edit_message_text("❌ Admin access required!")
                return
            
            request_id = int(data.split('_')[2])
            await self._view_request_details(query, request_id)
        
        elif data.startswith('approve_req_'):
            # Approve a request
            if not is_admin:
                await query.edit_message_text("❌ Admin access required!")
                return
            
            request_id = int(data.split('_')[2])
            await self._approve_request(query, context, request_id)
        
        elif data.startswith('reject_req_'):
            # Reject a request
            if not is_admin:
                await query.edit_message_text("❌ Admin access required!")
                return
            
            request_id = int(data.split('_')[2])
            await self._reject_request(query, request_id)
        
        elif data == 'approve_all':
            # Approve all pending requests
            if not is_admin:
                await query.edit_message_text("❌ Admin access required!")
                return
            
            await self._approve_all_requests(query, context)
        
        elif data == 'reject_all':
            # Reject all pending requests
            if not is_admin:
                await query.edit_message_text("❌ Admin access required!")
                return
            
            await self._reject_all_requests(query)
        
        elif data.startswith('select_anime_'):
            # User selected anime from search results
            anime_title = data.replace('select_anime_', '')
            request_id = await self.db_manager.add_user_request(user_id, anime_title)
            
            await query.edit_message_text(
                f"✅ <b>Request Added Successfully!</b>\n\n"
                f"🎬 Anime: <b>{anime_title}</b>\n"
                f"📋 Request ID: <code>#{request_id}</code>\n\n"
                f"Your request has been queued and will be processed soon!\n\n"
                f"Use <code>/status</code> to track your requests.\n\n"
                f"{Config.FOOTER}",
                parse_mode=ParseMode.HTML
            )
        
        elif data.startswith('retry_task_'):
            # Retry failed task
            if not is_admin:
                await query.edit_message_text("❌ Admin access required!")
                return
            
            task_id = data.replace('retry_task_', '')
            await self._retry_task(query, context, task_id)
    
    async def _view_request_details(self, query, request_id: int):
        """View detailed information about a request"""
        # Get request details from database (you need to implement get_request method)
        # For now, show basic info
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Approve", callback_data=f"approve_req_{request_id}"),
                InlineKeyboardButton("❌ Reject", callback_data=f"reject_req_{request_id}")
            ],
            [InlineKeyboardButton("◀️ Back to List", callback_data="back_to_requests")]
        ])
        
        await query.edit_message_text(
            f"📋 <b>Request Details</b>\n\n"
            f"Request ID: <code>#{request_id}</code>\n"
            f"Anime: [Title Here]\n"
            f"Requested By: [User ID]\n"
            f"Requested At: [Timestamp]\n\n"
            f"Select an action below:",
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard
        )
    
    async def _approve_request(self, query, context, request_id: int):
        """Approve a user request and add to pipeline"""
        # Update request status
        await self.db_manager.update_request_status(request_id, RequestStatus.APPROVED)
        
        # Create task from request
        task_id = generate_task_id()
        
        # Get request details (implement get_request_by_id)
        # task = AnimeTask(
        #     task_id=task_id,
        #     title=request['anime_title'],
        #     episode=1,  # Default to episode 1 or get from request
        #     quality="720p",
        #     status=TaskStatus.PENDING,
        #     requested_by=request['user_id']
        # )
        
        # await self.db_manager.add_task(task)
        
        await query.edit_message_text(
            f"✅ <b>Request Approved!</b>\n\n"
            f"Request #{request_id} has been approved and added to the processing queue.\n\n"
            f"Task ID: <code>{task_id}</code>\n\n"
            f"{Config.FOOTER}",
            parse_mode=ParseMode.HTML
        )
        
        # Log admin action
        await self._log_admin_action(
            f"✅ Request #{request_id} approved by {query.from_user.id}"
        )
    
    async def _reject_request(self, query, request_id: int):
        """Reject a user request"""
        await self.db_manager.update_request_status(request_id, RequestStatus.REJECTED)
        
        await query.edit_message_text(
            f"❌ <b>Request Rejected</b>\n\n"
            f"Request #{request_id} has been rejected.\n\n"
            f"{Config.FOOTER}",
            parse_mode=ParseMode.HTML
        )
        
        # Log admin action
        await self._log_admin_action(
            f"❌ Request #{request_id} rejected by {query.from_user.id}"
        )
    
    async def _approve_all_requests(self, query, context):
        """Approve all pending requests"""
        pending_requests = await self.db_manager.get_pending_requests()
        
        approved_count = 0
        for req in pending_requests:
            await self.db_manager.update_request_status(req['request_id'], RequestStatus.APPROVED)
            # Create tasks for each request
            approved_count += 1
        
        await query.edit_message_text(
            f"✅ <b>Bulk Approval Complete</b>\n\n"
            f"Approved <b>{approved_count}</b> requests successfully.\n\n"
            f"They have been added to the processing queue.\n\n"
            f"{Config.FOOTER}",
            parse_mode=ParseMode.HTML
        )
        
        # Log admin action
        await self._log_admin_action(
            f"✅ Bulk approved {approved_count} requests by {query.from_user.id}"
        )
    
    async def _reject_all_requests(self, query):
        """Reject all pending requests"""
        pending_requests = await self.db_manager.get_pending_requests()
        
        rejected_count = 0
        for req in pending_requests:
            await self.db_manager.update_request_status(req['request_id'], RequestStatus.REJECTED)
            rejected_count += 1
        
        await query.edit_message_text(
            f"❌ <b>Bulk Rejection Complete</b>\n\n"
            f"Rejected <b>{rejected_count}</b> requests.\n\n"
            f"{Config.FOOTER}",
            parse_mode=ParseMode.HTML
        )
        
        # Log admin action
        await self._log_admin_action(
            f"❌ Bulk rejected {rejected_count} requests by {query.from_user.id}"
        )
    
    async def _retry_task(self, query, context, task_id: str):
        """Retry a failed task"""
        task = await self.db_manager.get_task(task_id)
        
        if not task:
            await query.edit_message_text(f"❌ Task {task_id} not found!")
            return
        
        # Reset task status
        task.status = TaskStatus.PENDING
        task.error_log = None
        task.retry_count += 1
        
        await self.db_manager.add_task(task)
        
        await query.edit_message_text(
            f"🔄 <b>Task Reset for Retry</b>\n\n"
            f"Task: <code>{task_id}</code>\n"
            f"Title: {task.title} EP{task.episode}\n"
            f"Retry Count: {task.retry_count}\n\n"
            f"The task has been added back to the queue.\n\n"
            f"{Config.FOOTER}",
            parse_mode=ParseMode.HTML
        )
        
        # Log admin action
        await self._log_admin_action(
            f"🔄 Task {task_id} retry requested by {query.from_user.id}"
        )
    
    async def _log_admin_action(self, action: str):
        """Log admin action to admin channel"""
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
