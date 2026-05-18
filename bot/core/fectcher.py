"""
Fetcher Module - Handles anime metadata and source URL fetching
"""

import aiohttp
from typing import Optional, Dict, Any
from datetime import datetime

from bot.config import Config
from bot.database.database import DatabaseManager
from bot.database.models import AnimeTask
from bot.utils.logger import setup_logger


class Fetcher:
    """Fetches anime metadata and source URLs from various APIs"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.logger = setup_logger("fetcher")
        
        # Source providers (can be extended)
        self.providers = [
            self._fetch_from_anilist,
            self._fetch_from_jikan,
        ]
    
    async def fetch(self, task: AnimeTask) -> Optional[Dict[str, Any]]:
        """Fetch source URL and metadata for the task"""
        self.logger.info(f"Fetching: {task.title} EP{task.episode}")
        
        for provider in self.providers:
            try:
                result = await provider(task)
                if result and result.get('url'):
                    self.logger.info(f"✅ Found source from {provider.__name__}")
                    return result
            except Exception as e:
                self.logger.warning(f"Provider {provider.__name__} failed: {e}")
                continue
        
        self.logger.error(f"❌ No source found for: {task.title}")
        return None
    
    async def _fetch_from_anilist(self, task: AnimeTask) -> Optional[Dict[str, Any]]:
        """Fetch from AniList API"""
        query = """
        query ($search: String) {
            Media (search: $search, type: ANIME) {
                id
                title {
                    romaji
                    english
                    native
                }
                episodes
                status
                nextAiringEpisode {
                    episode
                    airingAt
                }
                siteUrl
                coverImage {
                    large
                }
                description
                genres
                averageScore
            }
        }
        """
        
        variables = {'search': task.title}
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                Config.ANILIST_API,
                json={'query': query, 'variables': variables},
                headers={'Content-Type': 'application/json'}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    media = data.get('data', {}).get('Media')
                    
                    if media:
                        # Build source URL (you can integrate with torrent/RSS providers)
                        source_url = await self._get_download_url(media, task.episode)
                        
                        return {
                            'url': source_url,
                            'metadata': {
                                'anilist_id': media['id'],
                                'title_english': media['title'].get('english'),
                                'title_romaji': media['title'].get('romaji'),
                                'genres': media.get('genres', []),
                                'score': media.get('averageScore'),
                                'description': media.get('description'),
                                'cover_url': media.get('coverImage', {}).get('large'),
                                'total_episodes': media.get('episodes')
                            }
                        }
        
        return None
    
    async def _fetch_from_jikan(self, task: AnimeTask) -> Optional[Dict[str, Any]]:
        """Fetch from Jikan API (MyAnimeList)"""
        # Search for anime
        search_url = f"{Config.JIKAN_API}/anime?q={task.title}&limit=1"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(search_url) as response:
                if response.status == 200:
                    data = await response.json()
                    results = data.get('data', [])
                    
                    if results:
                        anime = results[0]
                        source_url = await self._get_download_url(anime, task.episode)
                        
                        return {
                            'url': source_url,
                            'metadata': {
                                'mal_id': anime['mal_id'],
                                'title': anime['title'],
                                'synopsis': anime.get('synopsis'),
                                'genres': [g['name'] for g in anime.get('genres', [])],
                                'score': anime.get('score'),
                                'episodes': anime.get('episodes'),
                                'image_url': anime.get('images', {}).get('jpg', {}).get('image_url')
                            }
                        }
        
        return None
    
    async def _get_download_url(self, media: Dict, episode: int) -> Optional[str]:
        """
        Get download URL from various sources.
        This is a placeholder - integrate with your preferred sources:
        - Torrent sites (Nyaa.si, AnimeTosho)
        - Direct download sites
        - RSS feeds
        """
        # Example: Search Nyaa.si (you'll need to implement actual scraping)
        # For production, integrate with:
        # - Nyaa.si API/RSS
        # - AnimeTosho
        # - Your own CDN/database
        
        # Placeholder - return None to try next provider
        # Implement your source fetching logic here
        
        # Example structure for torrent source:
        if episode <= 0:
            return None
        
        # This is a mock - replace with actual source fetching
        # You can integrate with:
        # - nyaa.si RSS: https://nyaa.si/?q={title}+{episode}&page=rss
        # - animetosho.org API
        # - Your private trackers
        
        return None
    
    async def get_airing_schedule(self) -> list:
        """Get today's airing anime schedule"""
        query = """
        query {
            Page(page: 1, perPage: 50) {
                media(status: RELEASING, sort: POPULARITY_DESC) {
                    id
                    title {
                        romaji
                        english
                    }
                    nextAiringEpisode {
                        episode
                        airingAt
                        timeUntilAiring
                    }
                    episodes
                    coverImage {
                        medium
                    }
                }
            }
        }
        """
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                Config.ANILIST_API,
                json={'query': query}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    media_list = data.get('data', {}).get('Page', {}).get('media', [])
                    
                    # Filter today's airing
                    today_airing = []
                    for media in media_list:
                        next_ep = media.get('nextAiringEpisode')
                        if next_ep:
                            airing_time = datetime.fromtimestamp(next_ep['airingAt'])
                            if airing_time.date() == datetime.now().date():
                                today_airing.append({
                                    'title': media['title'].get('english') or media['title'].get('romaji'),
                                    'episode': next_ep['episode'],
                                    'airing_time': airing_time,
                                    'cover': media.get('coverImage', {}).get('medium')
                                })
                    
                    return today_airing
        
        return []
