"""
✦ ＡＵＴＯ ＡＮＩＭＥ ✦ - Enterprise Media Management Engine
Advanced Automated Anime Media Fetching & Distribution Bot
"""

__version__ = "2.0.0"
__author__ = "BOSSHUB"
__description__ = "Advanced Automated Anime Media Fetching & Distribution Bot"

from bot.config import Config
from bot.core.pipeline import Pipeline
from bot.database.database import DatabaseManager

__all__ = ['Config', 'Pipeline', 'DatabaseManager']
