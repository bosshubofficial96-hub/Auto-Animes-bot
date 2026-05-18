"""
Jikan API Service (MyAnimeList) for ✦ ＡＵＴＯ ＡＮＩＭＥ ✦
"""

import aiohttp
import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime

from bot.config import Config
from bot.utils.logger import setup_logger


class JikanService:
    """Service for interacting with Jikan API (MyAnimeList)"""
    
    def __init__(self):
        self.api_url = Config.JIKAN_API
        self.logger = setup_logger("jikan_service")
        self.session: Optional[aiohttp.ClientSession] = None
        self.rate_limit_delay = 1.0  # Jikan API rate limit: 1 request per second
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def close(self):
        """Close the aiohttp session"""
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def _make_request(self, endpoint: str) -> Optional[Dict]:
        """Make GET request to Jikan API with rate limiting"""
        await asyncio.sleep(self.rate_limit_delay)  # Respect rate limit
        
        try:
            session = await self._get_session()
            url = f"{self.api_url}/{endpoint}"
            
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('data')
                elif response.status == 429:
                    self.logger.warning("Rate limit hit, waiting longer...")
                    await asyncio.sleep(2)
                    return await self._make_request(endpoint)
                else:
                    self.logger.error(f"HTTP {response.status}: {await response.text()}")
                    return None
        except Exception as e:
            self.logger.error(f"Request failed: {e}")
            return None
    
    async def search_anime(self, query: str, limit: int = 10, page: int = 1) -> List[Dict]:
        """Search for anime by title"""
        endpoint = f"anime?q={query}&limit={limit}&page={page}"
        data = await self._make_request(endpoint)
        
        if data:
            results = []
            for anime in data:
                results.append({
                    'mal_id': anime.get('mal_id'),
                    'title': anime.get('title'),
                    'title_english': anime.get('title_english'),
                    'title_japanese': anime.get('title_japanese'),
                    'type': anime.get('type'),
                    'episodes': anime.get('episodes'),
                    'status': anime.get('status'),
                    'score': anime.get('score'),
                    'scored_by': anime.get('scored_by'),
                    'rank': anime.get('rank'),
                    'popularity': anime.get('popularity'),
                    'synopsis': anime.get('synopsis'),
                    'genres': [g['name'] for g in anime.get('genres', [])],
                    'image_url': anime.get('images', {}).get('jpg', {}).get('image_url'),
                    'airing': anime.get('airing'),
                    'year': anime.get('year'),
                    'season': anime.get('season')
                })
            return results
        return []
    
    async def get_anime_details(self, mal_id: int) -> Optional[Dict]:
        """Get detailed anime information by MAL ID"""
        endpoint = f"anime/{mal_id}/full"
        data = await self._make_request(endpoint)
        
        if data:
            return {
                'mal_id': data.get('mal_id'),
                'title': data.get('title'),
                'title_english': data.get('title_english'),
                'title_japanese': data.get('title_japanese'),
                'type': data.get('type'),
                'episodes': data.get('episodes'),
                'status': data.get('status'),
                'airing': data.get('airing'),
                'start_date': data.get('aired', {}).get('from'),
                'end_date': data.get('aired', {}).get('to'),
                'season': data.get('season'),
                'year': data.get('year'),
                'duration': data.get('duration'),
                'rating': data.get('rating'),
                'score': data.get('score'),
                'scored_by': data.get('scored_by'),
                'rank': data.get('rank'),
                'popularity': data.get('popularity'),
                'synopsis': data.get('synopsis'),
                'background': data.get('background'),
                'genres': [g['name'] for g in data.get('genres', [])],
                'studios': [s['name'] for s in data.get('studios', [])],
                'producers': [p['name'] for p in data.get('producers', [])],
                'image_url': data.get('images', {}).get('jpg', {}).get('image_url'),
                'trailer_url': data.get('trailer', {}).get('url')
            }
        return None
    
    async def get_seasonal_anime(self, year: int = None, season: str = None) -> List[Dict]:
        """Get seasonal anime schedule"""
        from datetime import datetime
        
        if not year:
            year = datetime.now().year
        if not season:
            month = datetime.now().month
            if month in [1, 2, 3]:
                season = 'winter'
            elif month in [4, 5, 6]:
                season = 'spring'
            elif month in [7, 8, 9]:
                season = 'summer'
            else:
                season = 'fall'
        
        endpoint = f"seasons/{year}/{season}"
        data = await self._make_request(endpoint)
        
        if data:
            results = []
            for anime in data:
                results.append({
                    'mal_id': anime.get('mal_id'),
                    'title': anime.get('title'),
                    'episodes': anime.get('episodes'),
                    'score': anime.get('score'),
                    'image_url': anime.get('images', {}).get('jpg', {}).get('image_url'),
                    'synopsis': anime.get('synopsis')
                })
            return results
        return []
    
    async def get_top_anime(self, type: str = 'tv', page: int = 1) -> List[Dict]:
        """Get top anime rankings"""
        endpoint = f"top/anime?type={type}&page={page}"
        data = await self._make_request(endpoint)
        
        if data:
            results = []
            for anime in data:
                results.append({
                    'mal_id': anime.get('mal_id'),
                    'rank': anime.get('rank'),
                    'title': anime.get('title'),
                    'score': anime.get('score'),
                    'episodes': anime.get('episodes'),
                    'image_url': anime.get('images', {}).get('jpg', {}).get('image_url')
                })
            return results
        return []
    
    async def get_upcoming_anime(self, page: int = 1) -> List[Dict]:
        """Get upcoming anime"""
        endpoint = f"seasons/upcoming?page={page}"
        data = await self._make_request(endpoint)
        
        if data:
            results = []
            for anime in data:
                results.append({
                    'mal_id': anime.get('mal_id'),
                    'title': anime.get('title'),
                    'episodes': anime.get('episodes'),
                    'airing_start': anime.get('aired', {}).get('from'),
                    'image_url': anime.get('images', {}).get('jpg', {}).get('image_url')
                })
            return results
        return []
    
    async def get_random_anime(self) -> Optional[Dict]:
        """Get random anime"""
        endpoint = "random/anime"
        data = await self._make_request(endpoint)
        
        if data:
            return {
                'mal_id': data.get('mal_id'),
                'title': data.get('title'),
                'synopsis': data.get('synopsis'),
                'episodes': data.get('episodes'),
                'score': data.get('score'),
                'image_url': data.get('images', {}).get('jpg', {}).get('image_url')
            }
        return None
    
    async def get_anime_recommendations(self, mal_id: int) -> List[Dict]:
        """Get anime recommendations"""
        endpoint = f"anime/{mal_id}/recommendations"
        data = await self._make_request(endpoint)
        
        if data:
            results = []
            for rec in data:
                results.append({
                    'mal_id': rec.get('entry', {}).get('mal_id'),
                    'title': rec.get('entry', {}).get('title'),
                    'recommendation_count': rec.get('votes')
                })
            return results
        return []
    
    async def get_anime_characters(self, mal_id: int) -> List[Dict]:
        """Get anime characters"""
        endpoint = f"anime/{mal_id}/characters"
        data = await self._make_request(endpoint)
        
        if data:
            results = []
            for char in data:
                results.append({
                    'character_id': char.get('character', {}).get('mal_id'),
                    'name': char.get('character', {}).get('name'),
                    'role': char.get('role'),
                    'image_url': char.get('character', {}).get('images', {}).get('jpg', {}).get('image_url')
                })
            return results
        return []
