"""
Helper utility functions for ✦ ＡＵＴＯ ＡＮＩＭＥ ✦
"""

import re
import uuid
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from typing import Tuple, Optional, Dict, Any, List
import html


def format_size(size_bytes: int) -> str:
    """Format file size to human readable format"""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.2f} {size_names[i]}"


def format_duration(seconds: int) -> str:
    """Format duration to HH:MM:SS or MM:SS"""
    if seconds < 0:
        seconds = 0
    
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes:02d}:{secs:02d}"


def format_eta(seconds: int) -> str:
    """Format ETA to human readable string"""
    if seconds <= 0:
        return "Calculating..."
    
    if seconds < 60:
        return f"{seconds} seconds"
    elif seconds < 3600:
        minutes = seconds // 60
        return f"{minutes} minute{'s' if minutes > 1 else ''}"
    elif seconds < 86400:
        hours = seconds // 3600
        return f"{hours} hour{'s' if hours > 1 else ''}"
    else:
        days = seconds // 86400
        return f"{days} day{'s' if days > 1 else ''}"


def format_timestamp(timestamp: datetime, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """Format datetime object to string"""
    if not timestamp:
        return "N/A"
    return timestamp.strftime(format_str)


def generate_task_id() -> str:
    """Generate unique task ID"""
    return f"task_{uuid.uuid4().hex[:12]}"


def generate_request_id() -> str:
    """Generate unique request ID"""
    return f"req_{uuid.uuid4().hex[:8]}"


def sanitize_filename(filename: str) -> str:
    """Sanitize filename by removing invalid characters"""
    # Remove invalid characters for filenames
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Remove control characters
    filename = re.sub(r'[\x00-\x1f\x7f]', '', filename)
    # Trim whitespace and limit length
    filename = filename.strip()[:200]
    return filename or "untitled"


def create_progress_bar(progress: float, width: int = 20) -> str:
    """Create a text-based progress bar
    
    Args:
        progress: Progress percentage (0-100)
        width: Width of the progress bar in characters
    
    Returns:
        Progress bar string
    """
    if progress < 0:
        progress = 0
    if progress > 100:
        progress = 100
    
    filled = int(width * progress / 100)
    empty = width - filled
    
    bar = "█" * filled + "░" * empty
    return f"[{bar}] {progress:.1f}%"


def calculate_speed(downloaded_bytes: int, elapsed_seconds: float) -> float:
    """Calculate download speed in KB/s"""
    if elapsed_seconds <= 0:
        return 0.0
    return downloaded_bytes / elapsed_seconds / 1024


def calculate_eta(file_size: int, downloaded: int, speed: float) -> int:
    """Calculate ETA in seconds"""
    if speed <= 0:
        return 0
    remaining = file_size - downloaded
    return int(remaining / speed / 1024)


def extract_anime_info(text: str) -> Optional[Dict[str, Any]]:
    """Extract anime information from text
    
    Supports formats:
    - "One Piece Episode 1080"
    - "Naruto 220"
    - "Demon Slayer: S02E12"
    """
    patterns = [
        # Pattern: "Title Episode 123"
        r'^(.*?)\s+(?:episode|ep|e)?\s*(\d+)$',
        # Pattern: "Title S02E12"
        r'^(.*?)\s+(?:s|season)?\s*(\d+)\s*[ex-]\s*(\d+)$',
        # Pattern: "Title - 123"
        r'^(.*?)[\s\-]+(\d+)$'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            groups = match.groups()
            title = groups[0].strip()
            episode = int(groups[1]) if len(groups) >= 2 else None
            
            if len(groups) >= 3:
                # Season and episode format
                episode = int(groups[2])
            
            return {
                'title': title,
                'episode': episode
            }
    
    # If no pattern matches, treat entire text as title with episode 1
    return {
        'title': text.strip(),
        'episode': 1
    }


def is_valid_url(url: str) -> bool:
    """Check if string is a valid URL"""
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE
    )
    return bool(url_pattern.match(url))


def validate_url(url: str) -> Tuple[bool, Optional[str]]:
    """Validate URL and return result with error message"""
    if not url:
        return False, "URL is empty"
    if not is_valid_url(url):
        return False, "Invalid URL format"
    return True, None


def calculate_etag(content: bytes) -> str:
    """Calculate ETag for content"""
    return hashlib.md5(content).hexdigest()


def clean_html(text: str) -> str:
    """Clean HTML tags from text"""
    if not text:
        return ""
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    # Unescape HTML entities
    text = html.unescape(text)
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """Truncate text to maximum length"""
    if not text:
        return ""
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def get_file_extension(filename: str) -> str:
    """Get file extension from filename"""
    path = Path(filename)
    return path.suffix.lower()


def format_speed(speed_kbps: float) -> str:
    """Format speed to human readable string"""
    if speed_kbps < 1024:
        return f"{speed_kbps:.0f} KB/s"
    else:
        return f"{speed_kbps / 1024:.1f} MB/s"


def get_size_from_gb(gb: int) -> int:
    """Convert GB to bytes"""
    return gb * 1024 * 1024 * 1024


def merge_dicts(dict1: Dict, dict2: Dict) -> Dict:
    """Recursively merge two dictionaries"""
    result = dict1.copy()
    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_dicts(result[key], value)
        else:
            result[key] = value
    return result


def chunk_list(lst: List, chunk_size: int) -> List[List]:
    """Split a list into chunks"""
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]


def retry_async(func, max_retries: int = 3, delay: int = 1):
    """Decorator for async retry logic"""
    import asyncio
    from functools import wraps
    
    @wraps(func)
    async def wrapper(*args, **kwargs):
        last_error = None
        for attempt in range(max_retries):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    await asyncio.sleep(delay * (attempt + 1))
        raise last_error
    return wrapper


def parse_quality_from_size(size_mb: int) -> str:
    """Estimate quality based on file size in MB"""
    if size_mb < 100:
        return "480p"
    elif size_mb < 300:
        return "720p"
    else:
        return "1080p"
