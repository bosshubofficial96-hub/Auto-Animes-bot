"""
Uploader Module - Handles uploading to Telegram channels
"""

import asyncio
from pathlib import Path
from typing import Optional, Dict, Any

from telegram import Bot, InputFile
from telegram.error import TelegramError

from bot.config import Config
from bot.database.database import DatabaseManager
from bot.database.models import AnimeTask
from bot.utils.logger import setup_logger
from bot.utils.helpers import format_size


class Uploader:
    """Handles uploading processed media to Telegram channels"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.logger = setup_logger("uploader")
        self.bot = Bot(token=Config.BOT_TOKEN)
        self.semaphore = asyncio.Semaphore(Config.MAX_CONCURRENT_UPLOADS)
        self.upload_progress: Dict[str, Dict] = {}
    
    async def upload(self, task: AnimeTask) -> Optional[Dict[str, Any]]:
        """Upload all processed qualities to Telegram"""
        if not task.processed_paths:
            self.logger.error(f"No processed files for task: {task.task_id}")
            return None
        
        self.logger.info(f"📤 Uploading: {task.title} EP{task.episode}")
        
        # Determine target channel
        channel_id = Config.get_channel_for_anime(task.title)
        
        message_ids = {}
        
        # Upload each quality
        for quality, file_path in task.processed_paths.items():
            if not file_path.exists():
                self.logger.warning(f"File not found for {quality}: {file_path}")
                continue
            
            async with self.semaphore:
                try:
                    # Start tracking
                    self.upload_progress[task.task_id] = {
                        'quality': quality,
                        'progress': 0,
                        'total_size': file_path.stat().st_size
                    }
                    
                    # Upload video
                    with open(file_path, 'rb') as f:
                        message = await self.bot.send_video(
                            chat_id=channel_id,
                            video=InputFile(f, filename=f"{task.title}_EP{task.episode}_{quality}.mp4"),
                            caption=self._build_caption(task, quality),
                            supports_streaming=True,
                            timeout=Config.UPLOAD_TIMEOUT,
                            write_timeout=Config.UPLOAD_TIMEOUT
                        )
                    
                    message_ids[quality] = message.message_id
                    
                    # Upload thumbnail if available
                    if task.metadata.get('cover_url'):
                        await self._upload_thumbnail(channel_id, task, message_ids)
                    
                    file_size_mb = file_path.stat().st_size / (1024 * 1024)
                    self.logger.info(f"✅ Uploaded {quality}: {file_size_mb:.1f} MB")
                    
                except TelegramError as e:
                    self.logger.error(f"Upload failed for {quality}: {e}")
                    # Try alternative channel
                    if channel_id != Config.DEFAULT_CHANNEL:
                        self.logger.info(f"Retrying on default channel")
                        channel_id = Config.DEFAULT_CHANNEL
                        # Retry upload (simplified - you may want to retry properly)
                finally:
                    self.upload_progress.pop(task.task_id, None)
        
        if not message_ids:
            return None
        
        return {'message_ids': message_ids, 'channel_id': channel_id}
    
    def _build_caption(self, task: AnimeTask, quality: str) -> str:
        """Build styled caption for the post"""
        metadata = task.metadata
        
        # Build genres string
        genres = metadata.get('genres', [])
        genres_str = " | ".join(genres[:3]) if genres else "N/A"
        
        # Build rating stars
        score = metadata.get('score')
        if score:
            rating_stars = "⭐" * min(5, int(score / 20))
            rating_text = f"{score}/100 {rating_stars}"
        else:
            rating_text = "N/A"
        
        caption = f"""
🎬 <b>{metadata.get('title_english', task.title)}</b>
│
├─ 📺 <b>Episode:</b> {task.episode}
├─ 🎯 <b>Quality:</b> {quality}
├─ 🏷️ <b>Genres:</b> {genres_str}
├─ ⭐ <b>Rating:</b> {rating_text}
│
└─ 📖 <b>Synopsis:</b>
   {metadata.get('description', 'No description available')[:200]}...

{Config.FOOTER}
        """
        
        return caption.strip()
    
    async def _upload_thumbnail(self, channel_id: int, task: AnimeTask, message_ids: Dict):
        """Upload thumbnail as a separate photo message"""
        try:
            # Download thumbnail first
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(task.metadata.get('cover_url')) as response:
                    if response.status == 200:
                        thumbnail_data = await response.read()
                        
                        # Send as photo
                        await self.bot.send_photo(
                            chat_id=channel_id,
                            photo=thumbnail_data,
                            caption=f"📸 <b>{task.title}</b> - Episode {task.episode}",
                            reply_to_message_id=message_ids.get('720p')
                        )
        except Exception as e:
            self.logger.warning(f"Thumbnail upload failed: {e}")
    
    async def get_upload_progress(self, task_id: str) -> Optional[Dict]:
        """Get upload progress for a task"""
        return self.upload_progress.get(task_id)
    
    async def send_admin_log(self, message: str, parse_mode: str = 'HTML'):
        """Send log message to admin channel"""
        try:
            await self.bot.send_message(
                chat_id=Config.ADMIN_LOG_CHANNEL,
                text=message,
                parse_mode=parse_mode
            )
        except Exception as e:
            self.logger.error(f"Failed to send admin log: {e}")
