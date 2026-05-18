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

    async def _is_banned(self, user_id: int) -> bool:
        val = await self.db_manager.get_config(f'banned_{user_id}')
        return val is not None and val.startswith('true')

    async def _is_maintenance(self) -> bool:
        val = await self.db_manager.get_config('maintenance_mode', 'false')
        return val == 'true'

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user = update.effective_user
        await self.db_manager.register_user(
            user.id, user.username, user.first_name, user.last_name
        )
        if await self._is_banned(user.id):
            await update.message.reply_text("🚫 You have been banned from using this bot.")
            return
        welcome_message = (
            f"🎬 <b>Welcome to ✦ ＡＵＴＯ ＡＮＩＭＥ ✦</b>\n\n"
            f"Hello <b>{user.first_name}</b>! I'm your automated anime media management bot.\n\n"
            f"<b>✨ Features:</b>\n"
            f"• 📺 Automatically fetch latest anime episodes\n"
            f"• 🎯 Multiple quality options (480p, 720p, 1080p)\n"
            f"• 📝 Request any anime you want\n"
            f"• ⚡ High-speed downloads (600-700 KB/s)\n"
            f"• 🔄 24/7 automated processing\n\n"
            f"<b>📋 Available Commands:</b>\n"
            f"• <code>/request &lt;anime&gt;</code> — Request an anime\n"
            f"• <code>/latest</code> — View latest uploads\n"
            f"• <code>/airing</code> — See today's airing schedule\n"
            f"• <code>/search &lt;anime&gt;</code> — Search for anime\n"
            f"• <code>/status</code> — Check your request status\n"
            f"• <code>/myreqs</code> — All your requests\n"
            f"• <code>/trending</code> — Trending anime\n"
            f"• <code>/seasonal</code> — Current season anime\n"
            f"• <code>/help</code> — Show detailed help\n\n"
            f"<b>💡 Quick Tip:</b>\n"
            f"Use <code>#request Anime Name</code> anywhere in chat to quickly request!\n\n"
            f"{Config.FOOTER}"
        )
        await update.message.reply_text(welcome_message, parse_mode=ParseMode.HTML)

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_text = (
            f"📚 <b>✦ ＡＵＴＯ ＡＮＩＭＥ ✦ — Help Guide</b>\n\n"
            f"<b>🎯 Request System:</b>\n"
            f"• <code>/request &lt;anime name&gt;</code> — Submit a request\n"
            f"• <code>#request &lt;anime name&gt;</code> — Quick request via hashtag\n"
            f"• Each user can request up to {Config.MAX_USER_REQUESTS} anime\n"
            f"• Requests are processed daily at {Config.REQUEST_TIME} IST\n\n"
            f"<b>📺 Information Commands:</b>\n"
            f"• <code>/latest</code> — Shows 10 most recent uploads\n"
            f"• <code>/airing</code> — Shows anime airing today\n"
            f"• <code>/search &lt;name&gt;</code> — Search anime database\n"
            f"• <code>/status</code> — Check your request status\n"
            f"• <code>/myreqs</code> — Full request history\n"
            f"• <code>/trending</code> — Trending anime now\n"
            f"• <code>/seasonal</code> — Current season anime\n\n"
            f"<b>🎬 Quality Options:</b>\n"
            f"• <b>480p</b> — Small file size, good for mobile\n"
            f"• <b>720p</b> — Balanced quality & size\n"
            f"• <b>1080p</b> — Best quality, larger files\n\n"
            f"<b>⚡ Performance:</b>\n"
            f"• Download Speed: {Config.TARGET_SPEED_KBPS} KB/s average\n"
            f"• Processing Time: 5-10 minutes per episode\n"
            f"• Upload Speed: Optimized for Telegram\n\n"
            f"<b>❓ Need Help?</b>\n"
            f"Contact an admin for assistance or report issues.\n\n"
            f"{Config.FOOTER}"
        )
        await update.message.reply_text(help_text, parse_mode=ParseMode.HTML)

    async def request_anime(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /request command"""
        user_id = update.effective_user.id
        user_name = update.effective_user.first_name

        await self.db_manager.register_user(
            user_id, update.effective_user.username,
            update.effective_user.first_name, update.effective_user.last_name
        )

        if await self._is_banned(user_id):
            await update.message.reply_text("🚫 You have been banned from using this bot.")
            return

        if await self._is_maintenance() and user_id not in Config.ADMIN_IDS:
            await update.message.reply_text(
                "🔧 <b>Bot is under maintenance</b>\n\nPlease try again later.\n\n"
                f"{Config.FOOTER}", parse_mode=ParseMode.HTML
            )
            return

        if not context.args:
            await update.message.reply_text(
                "❌ <b>Usage:</b> <code>/request &lt;anime name&gt;</code>\n\n"
                "Example: <code>/request One Piece</code>\n"
                "Or: <code>/request Demon Slayer Season 2</code>\n\n"
                f"You can also use <code>#request Anime Name</code>!\n\n{Config.FOOTER}",
                parse_mode=ParseMode.HTML
            )
            return

        anime_title = ' '.join(context.args).strip()

        can_request, message = await self._check_request_limits(user_id)
        if not can_request:
            await update.message.reply_text(
                f"❌ <b>Request Limit Reached!</b>\n\n{message}\n\n{Config.FOOTER}",
                parse_mode=ParseMode.HTML
            )
            return

        search_results = await self._search_anime(anime_title)

        if not search_results:
            request_id = await self.db_manager.add_user_request(
                user_id, anime_title, user_name=user_name
            )
            await update.message.reply_text(
                f"⚠️ <b>Request Added (Pending Validation)</b>\n\n"
                f"🎬 Anime: <b>{anime_title}</b>\n"
                f"📋 Request ID: <code>#{request_id}</code>\n\n"
                f"⚠️ Could not find exact match. Admins will review.\n"
                f"Status: ⏳ Pending Approval\n\n{Config.FOOTER}",
                parse_mode=ParseMode.HTML
            )
        elif len(search_results) == 1:
            request_id = await self.db_manager.add_user_request(
                user_id, search_results[0]['title'], user_name=user_name
            )
            await update.message.reply_text(
                f"✅ <b>Request Added Successfully!</b>\n\n"
                f"🎬 Anime: <b>{search_results[0]['title']}</b>\n"
                f"📺 Episodes: {search_results[0].get('episodes', '?')}\n"
                f"⭐ Rating: {search_results[0].get('score', 'N/A')}\n"
                f"📋 Request ID: <code>#{request_id}</code>\n\n"
                f"Your request will be processed soon!\n"
                f"Use <code>/status</code> to track.\n\n{Config.FOOTER}",
                parse_mode=ParseMode.HTML
            )
        else:
            keyboard = []
            for anime in search_results[:5]:
                safe_title = anime['title'][:40]
                keyboard.append([InlineKeyboardButton(
                    f"{safe_title} ({anime.get('score', '?')}⭐)",
                    callback_data=f"sa_{safe_title[:35]}"
                )])
            await update.message.reply_text(
                f"🔍 <b>Multiple matches for '{anime_title}'</b>\n\n"
                f"Select the correct anime:\n\n{Config.FOOTER}",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

        await self.db_manager.increment_daily_request()

    async def request_hashtag(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle #request <anime> format"""
        message_text = update.message.text
        match = re.search(r'#request\s+(.+)', message_text, re.IGNORECASE)
        if match:
            anime_title = match.group(1).strip()
            context.args = anime_title.split()
            await self.request_anime(update, context)

    async def latest_uploads(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /latest command"""
        completed_tasks = await self.db_manager.get_completed_tasks(limit=10)
        if not completed_tasks:
            await update.message.reply_text(
                f"📭 <b>No Uploads Yet</b>\n\nNo anime uploaded yet. Be the first to request!\n\n"
                f"Use <code>/request &lt;anime&gt;</code>\n\n{Config.FOOTER}",
                parse_mode=ParseMode.HTML
            )
            return
        message = self.poster.format_latest_message(completed_tasks)
        await update.message.reply_text(message, parse_mode=ParseMode.HTML)

    async def airing_today(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /airing command"""
        msg = await update.message.reply_text(
            "🔄 <b>Fetching today's airing schedule...</b>", parse_mode=ParseMode.HTML
        )
        try:
            cached = await self.db_manager.get_cached_airing()
            if cached:
                airing_list = cached[:20]
            else:
                airing_list = await self.fetcher.get_airing_schedule()
        except Exception as e:
            self.logger.error(f"Failed to fetch airing: {e}")
            airing_list = []
        message = self.poster.format_airing_message(airing_list)
        await msg.edit_text(message, parse_mode=ParseMode.HTML)

    async def search_anime(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /search command"""
        if not context.args:
            await update.message.reply_text(
                "❌ <b>Usage:</b> <code>/search &lt;anime name&gt;</code>\n\n"
                f"Example: <code>/search Naruto</code>\n\n{Config.FOOTER}",
                parse_mode=ParseMode.HTML
            )
            return
        query = ' '.join(context.args)
        msg = await update.message.reply_text(
            f"🔍 <b>Searching for '{query}'...</b>", parse_mode=ParseMode.HTML
        )
        results = await self._search_anime(query)
        if not results:
            await msg.edit_text(
                f"❌ <b>No Results Found</b>\n\nNo anime matching '{query}'.\n\n"
                f"Try different keywords or use <code>/request</code>!\n\n{Config.FOOTER}",
                parse_mode=ParseMode.HTML
            )
            return
        message = "🔍 <b>Search Results:</b>\n\n"
        for i, anime in enumerate(results[:8], 1):
            message += (
                f"{i}. <b>{anime['title']}</b>\n"
                f"   ├─ Episodes: {anime.get('episodes', '?')}\n"
                f"   ├─ Score: {anime.get('score', 'N/A')}\n"
                f"   └─ Status: {anime.get('status', 'Unknown')}\n\n"
            )
        message += Config.FOOTER
        keyboard = []
        for anime in results[:5]:
            keyboard.append([InlineKeyboardButton(
                f"📌 Request: {anime['title'][:35]}",
                callback_data=f"select_anime_{anime['title'][:50]}"
            )])
        await msg.edit_text(
            message, parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None
        )

    async def check_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command"""
        user_id = update.effective_user.id
        user_requests = await self.db_manager.get_user_requests(user_id, limit=10)
        if not user_requests:
            await update.message.reply_text(
                f"📭 <b>No Requests Found</b>\n\n"
                f"Use <code>/request &lt;anime&gt;</code> to get started!\n\n{Config.FOOTER}",
                parse_mode=ParseMode.HTML
            )
            return
        message = "📋 <b>Your Requests:</b>\n\n"
        for req in user_requests:
            status_emoji = {
                'pending': '⏳', 'approved': '✅', 'processing': '🔄',
                'completed': '🎉', 'rejected': '❌'
            }.get(req['status'], '❓')
            message += f"{status_emoji} <b>#{req['request_id']}</b> — {req['anime_title'][:40]}\n"
            message += f"   └─ Status: <b>{req['status'].upper()}</b>\n"
            if req.get('processed_at'):
                message += f"   └─ Updated: {str(req['processed_at'])[:10]}\n"
            message += "\n"
        message += f"💡 Use <code>/latest</code> to see completed uploads!\n\n{Config.FOOTER}"
        await update.message.reply_text(message, parse_mode=ParseMode.HTML)

    async def my_requests(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /myreqs command — full request history"""
        user_id = update.effective_user.id
        all_reqs = await self.db_manager.get_user_requests(user_id, limit=20)
        if not all_reqs:
            await update.message.reply_text(
                f"📭 No request history found.\n\n{Config.FOOTER}", parse_mode=ParseMode.HTML
            )
            return
        total = len(all_reqs)
        completed = len([r for r in all_reqs if r['status'] == 'completed'])
        pending = len([r for r in all_reqs if r['status'] == 'pending'])
        rejected = len([r for r in all_reqs if r['status'] == 'rejected'])
        message = (
            f"📋 <b>Your Request History</b>\n\n"
            f"Total: {total} | ✅ {completed} | ⏳ {pending} | ❌ {rejected}\n\n"
        )
        for req in all_reqs[:15]:
            emoji = {'pending': '⏳', 'approved': '✅', 'processing': '🔄',
                     'completed': '🎉', 'rejected': '❌'}.get(req['status'], '❓')
            message += f"{emoji} #{req['request_id']} — {req['anime_title'][:30]}\n"
        if total > 15:
            message += f"\n...and {total - 15} more\n"
        message += f"\n{Config.FOOTER}"
        await update.message.reply_text(message, parse_mode=ParseMode.HTML)

    async def trending_anime(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /trending command"""
        msg = await update.message.reply_text(
            "🔥 <b>Fetching trending anime...</b>", parse_mode=ParseMode.HTML
        )
        try:
            from bot.services.anilist_service import AniListService
            anilist = AniListService()
            trending = await anilist.get_trending(limit=10)
            if not trending:
                await msg.edit_text(f"❌ Could not fetch trending anime.\n\n{Config.FOOTER}",
                                    parse_mode=ParseMode.HTML)
                return
            message = "🔥 <b>Trending Anime Now</b>\n\n"
            for i, anime in enumerate(trending, 1):
                title = anime.get('title', {}).get('english') or anime.get('title', {}).get('romaji', 'Unknown')
                score = anime.get('averageScore', 'N/A')
                episodes = anime.get('episodes', '?')
                message += f"{i}. <b>{title}</b>\n"
                message += f"   ⭐ {score}/100 | 📺 {episodes} eps\n\n"
            message += Config.FOOTER
            keyboard = []
            for anime in trending[:5]:
                title = anime.get('title', {}).get('english') or anime.get('title', {}).get('romaji', 'Unknown')
                keyboard.append([InlineKeyboardButton(
                    f"📌 Request: {title[:35]}",
                    callback_data=f"select_anime_{title[:50]}"
                )])
            await msg.edit_text(message, parse_mode=ParseMode.HTML,
                                reply_markup=InlineKeyboardMarkup(keyboard))
        except Exception as e:
            self.logger.error(f"Trending fetch error: {e}")
            await msg.edit_text(
                f"❌ Failed to fetch trending anime.\n\n{Config.FOOTER}", parse_mode=ParseMode.HTML
            )

    async def seasonal_anime(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /seasonal command"""
        msg = await update.message.reply_text(
            "🌸 <b>Fetching current season anime...</b>", parse_mode=ParseMode.HTML
        )
        try:
            from bot.services.anilist_service import AniListService
            anilist = AniListService()
            seasonal = await anilist.get_seasonal(limit=10)
            if not seasonal:
                await msg.edit_text(
                    f"❌ Could not fetch seasonal anime.\n\n{Config.FOOTER}", parse_mode=ParseMode.HTML
                )
                return
            now = datetime.now()
            season_name = {1: 'Winter', 2: 'Winter', 3: 'Spring', 4: 'Spring', 5: 'Spring',
                           6: 'Summer', 7: 'Summer', 8: 'Summer', 9: 'Fall', 10: 'Fall',
                           11: 'Fall', 12: 'Winter'}.get(now.month, 'Current')
            message = f"🌸 <b>{season_name} {now.year} Anime</b>\n\n"
            for i, anime in enumerate(seasonal, 1):
                title = anime.get('title', {}).get('english') or anime.get('title', {}).get('romaji', 'Unknown')
                score = anime.get('averageScore', 'N/A')
                episodes = anime.get('episodes', '?')
                studio = anime.get('studios', {}).get('nodes', [{}])[0].get('name', 'Unknown') \
                    if anime.get('studios', {}).get('nodes') else 'N/A'
                message += f"{i}. <b>{title}</b>\n"
                message += f"   🎭 {studio} | ⭐ {score}/100 | 📺 {episodes} eps\n\n"
            message += Config.FOOTER
            keyboard = []
            for anime in seasonal[:5]:
                title = anime.get('title', {}).get('english') or anime.get('title', {}).get('romaji', 'Unknown')
                keyboard.append([InlineKeyboardButton(
                    f"📌 Request: {title[:35]}",
                    callback_data=f"select_anime_{title[:50]}"
                )])
            await msg.edit_text(message, parse_mode=ParseMode.HTML,
                                reply_markup=InlineKeyboardMarkup(keyboard))
        except Exception as e:
            self.logger.error(f"Seasonal fetch error: {e}")
            await msg.edit_text(
                f"❌ Failed to fetch seasonal anime.\n\n{Config.FOOTER}", parse_mode=ParseMode.HTML
            )

    async def _check_request_limits(self, user_id: int) -> tuple:
        """Check if user can make more requests"""
        daily_count = await self.db_manager.get_daily_request_count()
        if daily_count >= Config.MAX_GLOBAL_DAILY_REQUESTS:
            return False, "Global daily request limit reached. Try again tomorrow."
        user_requests = await self.db_manager.get_user_requests(user_id)
        pending_count = len([
            r for r in user_requests
            if r['status'] in ('pending', 'approved', 'processing')
        ])
        if pending_count >= Config.MAX_USER_REQUESTS:
            return False, (
                f"You already have {pending_count} pending requests. "
                f"Maximum is {Config.MAX_USER_REQUESTS}."
            )
        return True, "OK"

    async def _search_anime(self, query: str) -> List[dict]:
        """Search for anime using AniList"""
        try:
            from bot.services.anilist_service import AniListService
            anilist = AniListService()
            return await anilist.search_anime(query)
        except Exception as e:
            self.logger.error(f"Anime search failed: {e}")
            return []
