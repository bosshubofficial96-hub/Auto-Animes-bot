"""
Configuration Management for ✦ ＡＵＴＯ ＡＮＩＭＥ ✦
"""

import os
from pathlib import Path
from typing import Dict, Optional, List
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Config:
    """Main configuration class for the bot"""
    
    # ==================== BOT CONFIGURATION ====================
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "8673455526:AAEP7wAgfHvBWKAG0-Ui-jSzqpD5yXxtGhQ")
    BOT_USERNAME: str = os.getenv("BOT_USERNAME", "auto_anime_bot")
    
    # ==================== CHANNEL CONFIGURATION ====================
    DEFAULT_CHANNEL: int = int(os.getenv("DEFAULT_CHANNEL", -1003907294981))
    ADMIN_LOG_CHANNEL: int = int(os.getenv("ADMIN_LOG_CHANNEL", -1003907294981))
    
    # Dynamic channel routing
    CHANNEL_ROUTING: Dict[str, int] = {}
    
    # ==================== DATABASE ====================
    DATABASE_PATH: Path = Path(os.getenv("DATABASE_PATH", "data/anime_bot.db"))
    
    # ==================== STORAGE PATHS ====================
    BASE_DIR: Path = Path(__file__).parent.parent
    DOWNLOAD_PATH: Path = BASE_DIR / "data" / "downloads"
    PROCESSED_PATH: Path = BASE_DIR / "data" / "processed"
    TEMP_PATH: Path = BASE_DIR / "data" / "temp"
    LOGS_PATH: Path = BASE_DIR / "data" / "logs"
    
    # Create directories if not exist
    for path in [DOWNLOAD_PATH, PROCESSED_PATH, TEMP_PATH, LOGS_PATH]:
        path.mkdir(parents=True, exist_ok=True)
    
    # ==================== API ENDPOINTS ====================
    ANILIST_API: str = "https://graphql.anilist.co"
    JIKAN_API: str = "https://api.jikan.moe/v4"
    SIMKL_API: str = "https://api.simkl.com"
    
    # ==================== PERFORMANCE SETTINGS ====================
    TARGET_SPEED_KBPS: int = int(os.getenv("TARGET_SPEED", "700"))
    MIN_SPEED_KBPS: int = 600
    MAX_SPEED_KBPS: int = 700
    
    MAX_CONCURRENT_DOWNLOADS: int = int(os.getenv("MAX_CONCURRENT_DOWNLOADS", "3"))
    MAX_CONCURRENT_UPLOADS: int = int(os.getenv("MAX_CONCURRENT_UPLOADS", "2"))
    DOWNLOAD_TIMEOUT: int = int(os.getenv("DOWNLOAD_TIMEOUT", "3600"))
    UPLOAD_TIMEOUT: int = int(os.getenv("UPLOAD_TIMEOUT", "1800"))
    
    # ==================== QUALITY SETTINGS ====================
    QUALITY_OPTIONS: List[str] = ["480p", "720p", "1080p"]
    VIDEO_CODEC: str = "libx265"  # HEVC for better compression
    AUDIO_CODEC: str = "aac"
    AUDIO_BITRATE: str = "128k"
    
    # FFmpeg settings per quality
    FFMPEG_SETTINGS: Dict[str, Dict] = {
        "480p": {
            "video_size": "854x480",
            "video_bitrate": "800k",
            "crf": 28
        },
        "720p": {
            "video_size": "1280x720",
            "video_bitrate": "1500k",
            "crf": 26
        },
        "1080p": {
            "video_size": "1920x1080",
            "video_bitrate": "2500k",
            "crf": 24
        }
    }
    
    # ==================== SCHEDULING ====================
    TIMEZONE: str = "Asia/Kolkata"  # IST
    REQUEST_TIME: str = os.getenv("REQUEST_TIME", "18:00")  # Daily processing time
    CLEANUP_HOURS: int = int(os.getenv("CLEANUP_HOURS", "12"))
    
    # ==================== REQUEST LIMITS ====================
    MAX_USER_REQUESTS: int = int(os.getenv("MAX_USER_REQUESTS", "5"))
    MAX_GLOBAL_DAILY_REQUESTS: int = int(os.getenv("MAX_GLOBAL_DAILY_REQUESTS", "100"))
    
    # ==================== REDIS (for task queue) ====================
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))
    
    # ==================== STORAGE LIMITS ====================
    MAX_STORAGE_GB: int = int(os.getenv("MAX_STORAGE_GB", "50"))
    CLEANUP_THRESHOLD_GB: int = int(os.getenv("CLEANUP_THRESHOLD_GB", "45"))
    
    # ==================== FFMPEG ====================
    FFMPEG_PATH: str = os.getenv("FFMPEG_PATH", "ffmpeg")
    FFPROBE_PATH: str = os.getenv("FFPROBE_PATH", "ffprobe")
    
    # ==================== RETRY SETTINGS ====================
    MAX_RETRIES: int = 3
    RETRY_DELAY: int = 5
    RETRY_BACKOFF: float = 2.0
    
    # ==================== ADMIN LIST ====================
    ADMIN_IDS: List[int] = [int(id.strip()) for id in os.getenv("ADMIN_IDS", "").split(",") if id.strip()]
    
    # ==================== BRANDING ====================
    FOOTER: str = "🤩 POWERED BY: BOSSHUB— BOTZ & 𝐁𝐨𝐬𝐬𝐡𝐮𝐛😁"
    
    @classmethod
    def validate(cls) -> bool:
        """Validate required configuration"""
        if not cls.BOT_TOKEN:
            raise ValueError("BOT_TOKEN is required")
        if cls.DEFAULT_CHANNEL == -100:
            raise ValueError("DEFAULT_CHANNEL is required")
        return True
    
    @classmethod
    def get_channel_for_anime(cls, anime_title: str) -> int:
        """Get channel ID for specific anime"""
        return cls.CHANNEL_ROUTING.get(anime_title, cls.DEFAULT_CHANNEL)
    
    @classmethod
    def get_ffmpeg_command(cls, quality: str, input_path: Path, output_path: Path) -> list:
        """Generate FFmpeg command for video processing"""
        settings = cls.FFMPEG_SETTINGS.get(quality, cls.FFMPEG_SETTINGS["720p"])
        
        return [
            cls.FFMPEG_PATH,
            "-i", str(input_path),
            "-c:v", cls.VIDEO_CODEC,
            "-c:a", cls.AUDIO_CODEC,
            "-b:a", cls.AUDIO_BITRATE,
            "-vf", f"scale={settings['video_size']}",
            "-b:v", settings["video_bitrate"],
            "-crf", str(settings["crf"]),
            "-preset", "medium",
            "-movflags", "+faststart",
            str(output_path)
  ]
