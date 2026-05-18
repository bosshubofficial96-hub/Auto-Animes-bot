"""
Processor Module - Handles video encoding and quality conversion
"""

import asyncio
import subprocess
import json
from pathlib import Path
from typing import Optional, Dict, Any
from concurrent.futures import ThreadPoolExecutor

from bot.config import Config
from bot.database.database import DatabaseManager
from bot.database.models import AnimeTask
from bot.utils.logger import setup_logger
from bot.utils.helpers import format_size


class Processor:
    """Video processor for quality conversion using FFmpeg"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.logger = setup_logger("processor")
        self.executor = ThreadPoolExecutor(max_workers=2)
        self.processing_tasks: Dict[str, Dict] = {}
    
    async def process(self, task: AnimeTask) -> Optional[Dict[str, Any]]:
        """Process video into multiple qualities"""
        if not task.file_path or not task.file_path.exists():
            self.logger.error(f"Source file not found: {task.file_path}")
            return None
        
        self.logger.info(f"⚙️ Processing: {task.title} EP{task.episode}")
        
        # Get video info first
        video_info = await self._get_video_info(task.file_path)
        if not video_info:
            self.logger.error("Failed to get video info")
            return None
        
        self.logger.info(f"Source: {video_info['width']}x{video_info['height']}, "
                        f"Duration: {video_info['duration']:.1f}s, "
                        f"Size: {format_size(video_info['size'])}")
        
        # Process each quality
        processed_paths = {}
        
        for quality in Config.QUALITY_OPTIONS:
            # Skip if source is lower quality
            if self._should_skip_quality(video_info['height'], quality):
                self.logger.info(f"Skipping {quality} (source too low)")
                continue
            
            output_path = Config.PROCESSED_PATH / f"{task.task_id}_{quality}.mp4"
            
            # Skip if already exists
            if output_path.exists():
                self.logger.info(f"{quality} already exists, skipping")
                processed_paths[quality] = output_path
                continue
            
            self.logger.info(f"Converting to {quality}...")
            
            # Start tracking
            self.processing_tasks[task.task_id] = {
                'quality': quality,
                'progress': 0
            }
            
            # Process with FFmpeg
            success = await self._convert_video(
                task.file_path,
                output_path,
                quality,
                task.task_id
            )
            
            if success and output_path.exists():
                processed_paths[quality] = output_path
                size_mb = output_path.stat().st_size / (1024 * 1024)
                self.logger.info(f"✅ {quality} complete: {size_mb:.1f} MB")
            else:
                self.logger.error(f"❌ Failed to convert to {quality}")
        
        # Clean up tracking
        self.processing_tasks.pop(task.task_id, None)
        
        if not processed_paths:
            self.logger.error("No qualities were processed successfully")
            return None
        
        return {'processed_paths': processed_paths}
    
    async def _get_video_info(self, video_path: Path) -> Optional[Dict]:
        """Get video information using ffprobe"""
        cmd = [
            Config.FFPROBE_PATH,
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_streams',
            '-show_format',
            str(video_path)
        ]
        
        try:
            result = await asyncio.get_event_loop().run_in_executor(
                self.executor,
                lambda: subprocess.run(cmd, capture_output=True, text=True, check=True)
            )
            
            data = json.loads(result.stdout)
            
            # Find video stream
            video_stream = None
            for stream in data.get('streams', []):
                if stream.get('codec_type') == 'video':
                    video_stream = stream
                    break
            
            if video_stream:
                return {
                    'width': int(video_stream.get('width', 0)),
                    'height': int(video_stream.get('height', 0)),
                    'codec': video_stream.get('codec_name'),
                    'duration': float(data.get('format', {}).get('duration', 0)),
                    'size': int(data.get('format', {}).get('size', 0)),
                    'bitrate': int(video_stream.get('bit_rate', 0))
                }
        except Exception as e:
            self.logger.error(f"Failed to get video info: {e}")
        
        return None
    
    async def _convert_video(
        self,
        input_path: Path,
        output_path: Path,
        quality: str,
        task_id: str
    ) -> bool:
        """Convert video using FFmpeg with progress tracking"""
        
        ffmpeg_cmd = Config.get_ffmpeg_command(quality, input_path, output_path)
        
        # Add progress reporting
        ffmpeg_cmd.extend([
            '-progress', 'pipe:1',
            '-stats_period', '1.0'
        ])
        
        self.logger.debug(f"FFmpeg command: {' '.join(ffmpeg_cmd)}")
        
        try:
            process = await asyncio.create_subprocess_exec(
                *ffmpeg_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Monitor progress
            while True:
                line = await process.stdout.readline()
                if not line:
                    break
                
                line = line.decode().strip()
                
                # Parse progress
                if line.startswith('out_time_ms='):
                    time_ms = int(line.split('=')[1])
                    if task_id in self.processing_tasks:
                        # Calculate progress based on duration (simplified)
                        # You'd need total duration for accurate progress
                        pass
                
                elif line == 'progress=end':
                    break
            
            await process.wait()
            
            if process.returncode == 0:
                return True
            else:
                stderr = await process.stderr.read()
                self.logger.error(f"FFmpeg error: {stderr.decode()}")
                return False
                
        except Exception as e:
            self.logger.error(f"Conversion error: {e}")
            return False
    
    def _should_skip_quality(self, source_height: int, target_quality: str) -> bool:
        """Check if target quality should be skipped based on source"""
        quality_map = {
            '480p': 480,
            '720p': 720,
            '1080p': 1080
        }
        
        target_height = quality_map.get(target_quality, 0)
        return source_height < target_height
    
    async def get_processing_progress(self, task_id: str) -> Optional[Dict]:
        """Get processing progress for a task"""
        return self.processing_tasks.get(task_id)
