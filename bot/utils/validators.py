"""
Validation utilities for ✦ ＡＵＴＯ ＡＮＩＭＥ ✦
"""

import re
from typing import Tuple, Optional, List


def validate_anime_title(title: str) -> Tuple[bool, Optional[str]]:
    """Validate anime title format"""
    if not title or not title.strip():
        return False, "Anime title cannot be empty"
    
    if len(title) < 2:
        return False, "Anime title must be at least 2 characters long"
    
    if len(title) > 200:
        return False, "Anime title cannot exceed 200 characters"
    
    invalid_chars = ['<', '>', ':', '"', '|', '?', '*', '\\', '/']
    for char in invalid_chars:
        if char in title:
            return False, f"Anime title cannot contain '{char}'"
    
    sql_patterns = [r'\bDROP\b', r'\bDELETE\b', r'\bINSERT\b', r'\bUPDATE\b', r'\bSELECT\b', r'--', r';--']
    for pattern in sql_patterns:
        if re.search(pattern, title, re.IGNORECASE):
            return False, "Invalid characters in title"
    
    return True, None


def validate_quality(quality: str) -> Tuple[bool, Optional[str]]:
    """Validate video quality"""
    valid_qualities = ['480p', '720p', '1080p']
    
    if not quality:
        return False, "Quality cannot be empty"
    
    if quality not in valid_qualities:
        return False, f"Invalid quality. Choose from: {', '.join(valid_qualities)}"
    
    return True, None


def validate_episode_number(episode: int) -> Tuple[bool, Optional[str]]:
    """Validate episode number"""
    if episode is None:
        return False, "Episode number cannot be empty"
    
    if not isinstance(episode, int):
        try:
            episode = int(episode)
        except (ValueError, TypeError):
            return False, "Episode number must be a number"
    
    if episode < 0:
        return False, "Episode number cannot be negative"
    
    if episode > 10000:
        return False, "Episode number is too large (max 10000)"
    
    return True, None


def validate_user_id(user_id: int) -> Tuple[bool, Optional[str]]:
    """Validate user ID"""
    if not user_id:
        return False, "User ID cannot be empty"
    
    if not isinstance(user_id, int):
        try:
            user_id = int(user_id)
        except (ValueError, TypeError):
            return False, "User ID must be a number"
    
    if user_id <= 0:
        return False, "Invalid user ID"
    
    return True, None


def validate_channel_id(channel_id: int) -> Tuple[bool, Optional[str]]:
    """Validate Telegram channel ID"""
    if not channel_id:
        return False, "Channel ID cannot be empty"
    
    if not isinstance(channel_id, int):
        try:
            channel_id = int(channel_id)
        except (ValueError, TypeError):
            return False, "Channel ID must be a number"
    
    if channel_id >= 0:
        return False, "Invalid channel ID. Channel IDs are negative numbers"
    
    return True, None


def validate_url(url: str) -> Tuple[bool, Optional[str]]:
    """Validate URL format"""
    if not url:
        return False, "URL cannot be empty"
    
    url_pattern = re.compile(
        r'^https?://'
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'
        r'localhost|'
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
        r'(?::\d+)?'
        r'(?:/?|[/?]\S+)$', re.IGNORECASE
    )
    
    if not url_pattern.match(url):
        return False, "Invalid URL format"
    
    return True, None


def validate_time_format(time_str: str) -> Tuple[bool, Optional[str]]:
    """Validate time format (HH:MM)"""
    if not time_str:
        return False, "Time cannot be empty"
    
    time_pattern = re.compile(r'^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$')
    
    if not time_pattern.match(time_str):
        return False, "Invalid time format. Use HH:MM (24-hour format)"
    
    return True, None


def validate_duration(duration_str: str) -> Tuple[bool, Optional[int]]:
    """Validate duration string (e.g., '12h', '1d', '30m')"""
    if not duration_str:
        return False, None
    
    duration_str = duration_str.lower().strip()
    
    try:
        if duration_str.endswith('h'):
            hours = int(duration_str[:-1])
        elif duration_str.endswith('d'):
            hours = int(duration_str[:-1]) * 24
        elif duration_str.endswith('m'):
            hours = int(duration_str[:-1]) / 60
        else:
            hours = int(duration_str)
        
        if hours < 0.5:
            return False, None
        
        return True, int(hours) if hours >= 1 else 1
        
    except ValueError:
        return False, None


def sanitize_input(text: str, max_length: int = 500) -> str:
    """Sanitize user input"""
    if not text:
        return ""
    
    text = text.strip()
    
    if len(text) > max_length:
        text = text[:max_length]
    
    text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
    
    text = text.replace('&', '&amp;')
    text = text.replace('<', '&lt;')
    text = text.replace('>', '&gt;')
    text = text.replace('"', '&quot;')
    
    return text


def validate_file_size(file_size: int, max_gb: int = 2) -> Tuple[bool, Optional[str]]:
    """Validate file size for Telegram upload"""
    max_bytes = max_gb * 1024 * 1024 * 1024
    
    if file_size <= 0:
        return False, "Invalid file size"
    
    if file_size > max_bytes:
        return False, f"File size exceeds Telegram limit of {max_gb}GB"
    
    return True, None


def validate_bot_token(token: str) -> Tuple[bool, Optional[str]]:
    """Validate Telegram bot token format"""
    if not token:
        return False, "Bot token cannot be empty"
    
    token_pattern = re.compile(r'^\d+:[A-Za-z0-9_-]+$')
    
    if not token_pattern.match(token):
        return False, "Invalid bot token format"
    
    return True, None


def validate_request_limit(current_count: int, max_limit: int) -> Tuple[bool, Optional[str]]:
    """Validate if request limit has been reached"""
    if current_count >= max_limit:
        return False, f"Request limit reached. Maximum {max_limit} requests allowed."
    return True, None


def validate_search_query(query: str) -> Tuple[bool, Optional[str]]:
    """Validate search query"""
    if not query or not query.strip():
        return False, "Search query cannot be empty"
    
    if len(query) < 2:
        return False, "Search query must be at least 2 characters"
    
    if len(query) > 100:
        return False, "Search query too long (max 100 characters)"
    
    return True, None
