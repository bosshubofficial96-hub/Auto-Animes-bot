"""
Poster Module - Handles final posting and markdown formatting
"""

from typing import Optional, Dict, Any

from bot.config import Config
from bot.database.database import DatabaseManager
from bot.database.models import AnimeTask
from bot.utils.logger import setup_logger


class Poster:
    """Handles final posting with styled markdown formatting"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.logger = setup_logger("poster")
    
    async def post(self, task: AnimeTask) -> bool:
        """Post completion notification and final formatting"""
        self.logger.info(f"📝 Posting completion: {task.title} EP{task.episode}")
        
        # Send admin notification
        await self._notify_admins(task)
        
        # Update request status if applicable
        if task.requested_by:
            await self._notify_user(task)
        
        # Log completion
        self.logger.info(f"✅ Successfully posted: {task.task_id}")
        
        return True
    
    async def _notify_admins(self, task: AnimeTask):
        """Send completion notification to admins"""
        from bot.core.uploader import Uploader
        uploader = Uploader(self.db_manager)
        
        total_size = 0
        for path in task.processed_paths.values():
            if path.exists():
                total_size += path.stat().st_size
        
        size_mb = total_size / (1024 * 1024)
        
        message = f"""
✅ <b>Task Completed Successfully</b>

📋 <b>Task ID:</b> <code>{task.task_id}</code>
🎬 <b>Title:</b> {task.title}
📺 <b>Episode:</b> {task.episode}
🎯 <b>Qualities:</b> {', '.join(task.processed_paths.keys())}
📦 <b>Total Size:</b> {size_mb:.1f} MB
⏱️ <b>Processing Time:</b> {(task.completed_at - task.created_at).total_seconds():.0f}s

{Config.FOOTER}
        """
        
        await uploader.send_admin_log(message)
    
    async def _notify_user(self, task: AnimeTask):
        """Notify user who requested the anime"""
        from bot.core.uploader import Uploader
        uploader = Uploader(self.db_manager)
        
        message = f"""
🎉 <b>Your requested anime is now available!</b>

🎬 <b>Title:</b> {task.title}
📺 <b>Episode:</b> {task.episode}
🎯 <b>Qualities Available:</b> {', '.join(task.processed_paths.keys())}

Check the channel for the download links!

{Config.FOOTER}
        """
        
        try:
            from telegram import Bot
            bot = Bot(token=Config.BOT_TOKEN)
            await bot.send_message(
                chat_id=task.requested_by,
                text=message,
                parse_mode='HTML'
            )
        except Exception as e:
            self.logger.warning(f"Failed to notify user {task.requested_by}: {e}")
    
    def format_airing_message(self, airing_list: list) -> str:
        """Format airing schedule message"""
        if not airing_list:
            return "📺 No anime airing today!"
        
        message = "📺 <b>Today's Airing Schedule</b>\n\n"
        
        for anime in airing_list:
            airing_time = anime.get('airing_time')
            time_str = airing_time.strftime("%I:%M %p") if airing_time else "Unknown"
            
            message += f"🎬 <b>{anime['title']}</b>\n"
            message += f"   └─ Episode {anime['episode']} at {time_str}\n\n"
        
        message += f"\n{Config.FOOTER}"
        
        return message
    
    def format_latest_message(self, tasks: list) -> str:
        """Format latest uploads message"""
        if not tasks:
            return "📭 No recent uploads found!"
        
        message = "📺 <b>Latest Uploads</b>\n\n"
        
        for task in tasks[:10]:
            message += f"🎬 <b>{task.title}</b>\n"
            message += f"   ├─ Episode: {task.episode}\n"
            message += f"   ├─ Qualities: {', '.join(task.processed_paths.keys())}\n"
            message += f"   └─ Completed: {task.completed_at.strftime('%Y-%m-%d %H:%M')}\n\n"
        
        message += f"\n{Config.FOOTER}"
        
        return message
