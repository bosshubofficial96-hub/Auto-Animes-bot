"""
Downloader Module - Handles high-speed media downloading
"""

import aiohttp
import aiofiles
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any
from tenacity import retry, stop_after_attempt, wait_exponential

from bot.config import Config
from bot.database.database import DatabaseManager
from bot.database.models import AnimeTask
from bot.utils.logger import setup_logger
from bot.utils.helpers import format_size


class Downloader:
    """High-speed downloader with retry logic and progress tracking"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.logger = setup_logger("downloader")
        self.active_downloads: Dict[str, Dict] = {}
        self.semaphore = asyncio.Semaphore(Config.MAX_CONCURRENT_DOWNLOADS)
    
    @retry(
        stop=stop_after_attempt(Config.MAX_RETRIES),
        wait=wait_exponential(multiplier=Config.RETRY_BACKOFF, min=2, max=30)
    )
    async def download(self, task: AnimeTask) -> Optional[Dict[str, Any]]:
        """Download media from source URL"""
        if not task.source_url:
            self.logger.error(f"No source URL for task: {task.task_id}")
            return None
        
        self.logger.info(f"⬇️ Downloading: {task.title} EP{task.episode}")
        
        # Create download path
        download_path = Config.DOWNLOAD_PATH / f"{task.task_id}.mp4"
        
        async with self.semaphore:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        task.source_url,
                        timeout=aiohttp.ClientTimeout(total=Config.DOWNLOAD_TIMEOUT)
                    ) as response:
                        
                        if response.status != 200:
                            raise Exception(f"HTTP {response.status}: {response.reason}")
                        
                        # Get file size
                        total_size = int(response.headers.get('content-length', 0))
                        self.logger.info(f"File size: {format_size(total_size)}")
                        
                        # Track download progress
                        downloaded = 0
                        start_time = asyncio.get_event_loop().time()
                        
                        # Store progress info
                        self.active_downloads[task.task_id] = {
                            'total': total_size,
                            'downloaded': 0,
                            'speed': 0
                        }
                        
                        async with aiofiles.open(download_path, 'wb') as f:
                            async for chunk in response.content.iter_chunked(1024 * 1024):  # 1MB chunks
                                await f.write(chunk)
                                downloaded += len(chunk)
                                
                                # Update progress
                                self.active_downloads[task.task_id]['downloaded'] = downloaded
                                
                                # Calculate speed
                                elapsed = asyncio.get_event_loop().time() - start_time
                                if elapsed > 0:
                                    speed = downloaded / elapsed / 1024  # KB/s
                                    self.active_downloads[task.task_id]['speed'] = speed
                                    
                                    # Log progress every 10 seconds
                                    if int(elapsed) % 10 == 0:
                                        progress = (downloaded / total_size * 100) if total_size > 0 else 0
                                        self.logger.info(
                                            f"Download progress: {progress:.1f}% | "
                                            f"Speed: {speed:.0f} KB/s | "
                                            f"Elapsed: {elapsed:.0f}s"
                                        )
                        
                        elapsed = asyncio.get_event_loop().time() - start_time
                        avg_speed = downloaded / elapsed / 1024 if elapsed > 0 else 0
                        
                        self.logger.info(
                            f"✅ Download complete: {task.task_id} | "
                            f"Time: {elapsed:.1f}s | "
                            f"Avg Speed: {avg_speed:.0f} KB/s"
                        )
                        
                        # Clean up tracking
                        self.active_downloads.pop(task.task_id, None)
                        
                        return {
                            'file_path': download_path,
                            'size': downloaded,
                            'download_time': elapsed,
                            'avg_speed': avg_speed
                        }
                        
            except asyncio.TimeoutError:
                self.logger.error(f"Download timeout for {task.task_id}")
                raise
            except Exception as e:
                self.logger.error(f"Download failed for {task.task_id}: {e}")
                # Clean up partial download
                if download_path.exists():
                    download_path.unlink()
                raise
    
    async def download_from_torrent(self, task: AnimeTask, magnet_link: str) -> Optional[Path]:
        """
        Download using torrent/magnet link
        Requires: libtorrent or qbittorrent API
        """
        # Placeholder for torrent download implementation
        # You can integrate with:
        # - qBittorrent Web API
        # - libtorrent-python
        # - aria2
        pass
    
    async def get_download_progress(self, task_id: str) -> Optional[Dict]:
        """Get download progress for a task"""
        return self.active_downloads.get(task_id)
    
    async def cancel_download(self, task_id: str) -> bool:
        """Cancel an ongoing download"""
        # Implementation depends on download method
        # For aiohttp downloads, we'd need to close the session
        if task_id in self.active_downloads:
            # Mark for cancellation
            self.active_downloads[task_id]['cancel'] = True
            return True
        return False
