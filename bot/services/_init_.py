"""
Services module for ✦ ＡＵＴＯ ＡＮＩＭＥ ✦
"""

from bot.services.anilist_service import AniListService
from bot.services.jikan_service import JikanService
from bot.services.scheduler_service import SchedulerService

__all__ = ['AniListService', 'JikanService', 'SchedulerService']
