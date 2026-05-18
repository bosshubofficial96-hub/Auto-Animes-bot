"""
User Command Handlers for ✦ ＡＵＴＯ ＡＮＩＭＥ ✦
"""

import re
from datetime import datetime
from typing import Optional, List
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from bot.config import Config
from bot.database.database import DatabaseManager
from bot.database.models import TaskStatus, RequestStatus
from bot.core.fetcher import Fetcher
from bot.core.poster import Poster
from bot.utils.logger import setup_logger
from bot.utils.helpers import generate_task_id


class UserHandlers:
    """Handler for all user commands"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.logger = setup_logger("user_handlers")
        self.fetcher = Fetcher(db_manager)
        self.poster = Poster(db_manager)
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user = update.effective_user
        
        welcome_message = f"""
🎬 <b>Welcome to ✦ ＡＵＴＯ ＡＮＩＭＥ ✦</b>

Hello <b>{user.first_name}</b>! I'm your automated anime media management bot.

<b>✨ Features:</b>
• 📺 Automatically fetch latest anime episodes
• 🎯 Multiple quality options (480p, 720p, 1080p)
• 📝 Request any anime you want
• ⚡ High-speed downloads (600-700 KB/s)
• 🔄 24/7 automated processing

<b>📋 Available Commands:</b>
• <code>/request &lt;anime&gt;</code> - Request an anime
• <code>/latest</code> - View latest uploads
• <code>/airing</code> - See today's airing schedule
• <code>/search &lt;anime&gt;</code> - Search for anime
• <code>/status</code> - Check your request status
• <code>/help</code> - Show detailed help

<b>💡 Quick Tip:</b>
Use <code>#request Anime Name</code> anywhere in chat to quickly request!

{Config.FOOTER}
        """
        
        await update.message.reply_text(welcome_message.strip(), parse_mode=ParseMode.HTML)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_text = f"""
📚 <b>✦ ＡＵＴＯ ＡＮＩＭＥ ✦ - Help Guide</b>

<b>🎯 Request System:</b>
• <code>/request &lt;anime name&gt;</code> - Submit a request
• <code>#request &lt;anime name&gt;</code> - Quick request using hashtag
• Each user can request up to {Config.MAX_USER_REQUESTS} anime
• Requests are processed daily at {Config.REQUEST_TIME} IST

<b>📺 Information Commands:</b>
• <code>/latest</code> - Shows 10 most recent uploads
• <code>/airing</code> - Shows anime airing today
• <code>/search &lt;name&gt;</code> - Search anime database
• <code>/status</code> - Check your request status

<b>🎬 Quality Options:</b>
• <b>480p</b> - Small file size, good for mobile
• <b>720p</b> - Balanced quality & size
• <b>1080p</b> - Best quality, larger files

<b>⚡ Performance:</b>
• Download Speed: {Config.TARGET_SPEED_KBPS} KB/s average
• Processing Time: 5-10 minutes per episode
• Upload Speed: Optimized for Telegram

<b>❓ Need Help?</b>
Contact an admin for assistance or report issues in the support channel.

{Config.FOOTER}
        """
        
        await update.message.reply_text(help_text.strip(), parse_mode=ParseMode.HTML)
    
    async def request_anime(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /request command"""
        user_id = update.effective_user.id
        user_name = update.effective_user.first_name
        
        if not context.args:
            await update.message.reply_text(
                "❌ <b>Usage:</b> <code>/request &lt;anime name&gt;</code>\n\n"
                "Example: <code>/request One Piece</code>\n"
                "Or: <code>/request Demon Slayer Season 2</code>\n\n"
                f"You can also use <code>#request Anime Name</code> format!",
                parse_mode=ParseMode.HTML
            )
            return
        
        anime_title = ' '.join(context.args).strip()
        
        # Check request limits
        can_request, message = await self._check_request_limits(user_id)
        
        if not can_request:
            await update.message.reply_text(
                f"❌ <b>Request Limit Reached!</b>\n\n{message}\n\n{Config.FOOTER}",
                parse_mode=ParseMode.HTML
            )
            return
        
        # Search for anime to validate
        search_results = await self._search_anime(anime_title)
        
        if not search_results:
            # Still add request but mark as pending validation
            request_id = await self.db_manager.add_user_request(user_id, anime_title)
            
            await update.message.reply_text(
                f"⚠️ <b>Request Added (Pending Validation)</b>\n\n"
                f"🎬 Anime: <b>{anime_title}</b>\n"
                f"📋 Request ID: <code>#{request_id}</code>\n\n"
                f"⚠️ Could not find exact match in database.\n"
                f"Admins will review your request.\n\n"
                f"Status: ⏳ Pending Approval\n\n"
                f"{Config.FOOTER}",
                parse_mode=ParseMode.HTML
            )
        else:
            # Exact match or suggestions found
            if len(search_results) == 1:
                # Exact match
                request_id = await self.db_manager.add_user_request(user_id, search_results[0]['title'])
                
                await update.message.reply_text(
                    f"✅ <b>Request Added Successfully!</b>\n\n"
                    f"🎬 Anime: <b>{search_results[0]['title']}</b>\n"
                    f"📺 Episodes: {search_results[0].get('episodes', '?')}\n"
                    f"⭐ Rating: {search_results[0].get('score', 'N/A')}/100\n"
                    f"📋 Request ID: <code>#{request_id}</code>\n\n"
                    f"Your request has been queued and will be processed soon!\n\n"
                    f"Use <code>/status</code> to track your requests.\n\n"
                    f"{Config.FOOTER}",
                    parse_mode=ParseMode.HTML
                )
            else:
                # Multiple matches - show selection keyboard
                keyboard = []
                for anime in search_results[:5]:
                    keyboard.append([InlineKeyboardButton(
                        f"{anime['title']} ({anime.get('score', '?')}⭐)",
                        callback_data=f"select_anime_{anime['title']}"
                    )])
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(
                    f"🔍 <b>Multiple matches found for '{anime_title}'</b>\n\n"
                    f"Please select the correct anime from below:\n\n"
                    f"{Config.FOOTER}",
                    parse_mode=ParseMode.HTML,
                    reply_markup=reply_markup
                )
        
        # Increment daily request counter
        await self.db_manager.increment_daily_request()
    
    async def request_hashtag(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle #request <anime> format"""
        message_text = update.message.text
        match = re.search(r'#request\s+(.+)', message_text, re.IGNORECASE)
        
        if match:
            anime_title = match.group(1).strip()
            # Simulate /request command
            context.args = anime_title.split()
            await self.request_anime(update, context)
    
    async def latest_uploads(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /latest command - Show latest uploads"""
        completed_tasks = await self.db_manager.get_completed_tasks(limit=10)
        
        if not completed_tasks:
            await update.message.reply_text(
                f"📭 <b>No Uploads Yet</b>\n\n"
                f"No anime have been uploaded yet. Be the first to make a request!\n\n"
                f"Use <code>/request &lt;anime&gt;</code> to request.\n\n"
                f"{Config.FOOTER}",
                parse_mode=ParseMode.HTML
            )
            return
        
        message = self.poster.format_latest_message(completed_tasks)
        await update.message.reply_text(message, parse_mode=ParseMode.HTML)
    
    async def airing_today(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /airing command - Show today's airing schedule"""
        await update.message.reply_text(
            "🔄 <b>Fetching today's schedule...</b>",
            parse_mode=ParseMode.HTML
        )
        
        airing_list = await self.fetcher.get_airing_schedule()
        message = self.poster.format_airing_message(airing_list)
        
        await update.message.reply_text(message, parse_mode=ParseMode.HTML)
    
    async def search_anime(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /search command"""
        if not context.args:
            await update.message.reply_text(
                "❌ <b>Usage:</b> <code>/search &lt;anime name&gt;</code>\n\n"
                "Example: <code>/search Naruto</code>",
                parse_mode=ParseMode.HTML
            )
            return
        
        query = ' '.join(context.args)
        
        await update.message.reply_text(
            f"🔍 <b>Searching for '{query}'...</b>",
            parse_mode=ParseMode.HTML
        )
        
        results = await self._search_anime(query)
        
        if not results:
            await update.message.reply_text(
                f"❌ <b>No Results Found</b>\n\n"
                f"No anime matching '{query}' was found.\n\n"
                f"Try different keywords or use <code>/request</code> to request it!\n\n"
                f"{Config.FOOTER}",
                parse_mode=ParseMode.HTML
            )
            return
        
        message = "🔍 <b>Search Results:</b>\n\n"
        
        for i, anime in enumerate(results[:10], 1):
            message += f"{i}. <b>{anime['title']}</b>\n"
            message += f"   ├─ Episodes: {anime.get('episodes', '?')}\n"
            message += f"   ├─ Score: {anime.get('score', 'N/A')}/100\n"
            message += f"   └─ Status: {anime.get('status', 'Unknown')}\n\n"
        
        message += f"\n{Config.FOOTER}"
        
        await update.message.reply_text(message, parse_mode=ParseMode.HTML)
    
    async def check_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command - Check user's requests"""
        user_id = update.effective_user.id
        
        user_requests = await self.db_manager.get_user_requests(user_id)
        
        if not user_requests:
            await update.message.reply_text(
                f"📭 <b>No Requests Found</b>\n\n"
                f"You haven't made any requests yet.\n\n"
                f"Use <code>/request &lt;anime&gt;</code> to get started!\n\n"
                f"{Config.FOOTER}",
                parse_mode=ParseMode.HTML
            )
            return
        
        message = "📋 <b>Your Requests:</b>\n\n"
        
        for req in user_requests[:10]:
            status_emoji = {
                'pending': '⏳',
                'approved': '✅',
                'processing': '🔄',
                'completed': '🎉',
                'rejected': '❌'
            }.get(req['status'], '❓')
            
            message += f"{status_emoji} <b>#{req['request_id']}</b> - {req['anime_title'][:40]}\n"
            message += f"   └─ Status: <b>{req['status'].upper()}</b>\n"
            
            if req['processed_at']:
                message += f"   └─ Processed: {req['processed_at'][:10]}\n"
            
            message += "\n"
        
        message += f"\n💡 <b>Tip:</b> Use <code>/latest</code> to see completed uploads!\n\n"
        message += Config.FOOTER
        
        await update.message.reply_text(message, parse_mode=ParseMode.HTML)
    
    async def _check_request_limits(self, user_id: int) -> tuple:
        """Check if user can make more requests"""
        # Check global daily limit
        daily_count = await self.db_manager.get_daily_request_count()
        
        if daily_count >= Config.MAX_GLOBAL_DAILY_REQUESTS:
            return False, "Global daily request limit reached. Please try again tomorrow."
        
        # Check user's pending requests
        user_requests = await self.db_manager.get_user_requests(user_id)
        pending_count = len([r for r in user_requests if r['status'] in ['pending', 'approved', 'processing']])
        
        if pending_count >= Config.MAX_USER_REQUESTS:
            return False, f"You already have {pending_count} pending requests. Maximum allowed is {Config.MAX_USER_REQUESTS}."
        
        return True, "OK"
    
    async def _search_anime(self, query: str) -> List[dict]:
        """Search for anime using AniList"""
        from bot.services.anilist_service import AniListService
        anilist = AniListService()
        return await anilist.search_anime(query)
