"""
AniList API Service for ✦ ＡＵＴＯ ＡＮＩＭＥ ✦
Handles all AniList GraphQL queries and mutations
"""

import aiohttp
import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime

from bot.config import Config
from bot.utils.logger import setup_logger


class AniListService:
    """Service for interacting with AniList API"""
    
    def __init__(self):
        self.api_url = Config.ANILIST_API
        self.logger = setup_logger("anilist_service")
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def close(self):
        """Close the aiohttp session"""
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def _make_request(self, query: str, variables: Dict = None) -> Optional[Dict]:
        """Make GraphQL request to AniList"""
        try:
            session = await self._get_session()
            async with session.post(
                self.api_url,
                json={'query': query, 'variables': variables or {}},
                headers={'Content-Type': 'application/json', 'Accept': 'application/json'}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    if 'errors' in data:
                        self.logger.error(f"GraphQL errors: {data['errors']}")
                        return None
                    return data.get('data')
                else:
                    self.logger.error(f"HTTP {response.status}: {await response.text()}")
                    return None
        except Exception as e:
            self.logger.error(f"Request failed: {e}")
            return None
    
    async def search_anime(self, search: str, limit: int = 10) -> List[Dict]:
        """Search for anime by title"""
        query = """
        query ($search: String, $limit: Int) {
            Page(page: 1, perPage: $limit) {
                media(search: $search, type: ANIME, sort: POPULARITY_DESC) {
                    id
                    title {
                        romaji
                        english
                        native
                    }
                    format
                    episodes
                    status
                    startDate {
                        year
                        month
                        day
                    }
                    endDate {
                        year
                        month
                        day
                    }
                    season
                    seasonYear
                    description
                    coverImage {
                        large
                        medium
                    }
                    bannerImage
                    genres
                    averageScore
                    meanScore
                    popularity
                    favourites
                    trending
                    nextAiringEpisode {
                        episode
                        airingAt
                        timeUntilAiring
                    }
                    studios {
                        nodes {
                            name
                        }
                    }
                    source
                    duration
                    countryOfOrigin
                }
            }
        }
        """
        
        variables = {'search': search, 'limit': limit}
        data = await self._make_request(query, variables)
        
        if data and 'Page' in data:
            results = []
            for media in data['Page']['media']:
                results.append({
                    'id': media['id'],
                    'title': {
                        'romaji': media['title'].get('romaji'),
                        'english': media['title'].get('english'),
                        'native': media['title'].get('native')
                    },
                    'format': media.get('format'),
                    'episodes': media.get('episodes'),
                    'status': media.get('status'),
                    'description': media.get('description'),
                    'cover_image': media.get('coverImage', {}).get('large'),
                    'banner_image': media.get('bannerImage'),
                    'genres': media.get('genres', []),
                    'score': media.get('averageScore') or media.get('meanScore'),
                    'popularity': media.get('popularity'),
                    'studios': [s['name'] for s in media.get('studios', {}).get('nodes', [])],
                    'next_episode': media.get('nextAiringEpisode')
                })
            return results
        return []
    
    async def get_anime_details(self, anime_id: int) -> Optional[Dict]:
        """Get detailed information about a specific anime"""
        query = """
        query ($id: Int) {
            Media(id: $id, type: ANIME) {
                id
                title {
                    romaji
                    english
                    native
                }
                format
                episodes
                duration
                status
                startDate {
                    year
                    month
                    day
                }
                endDate {
                    year
                    month
                    day
                }
                season
                seasonYear
                description
                coverImage {
                    large
                    medium
                    color
                }
                bannerImage
                genres
                synonyms
                averageScore
                meanScore
                popularity
                favourites
                trending
                tags {
                    name
                    description
                }
                relations {
                    edges {
                        relationType
                        node {
                            id
                            title {
                                romaji
                            }
                            format
                        }
                    }
                }
                characters {
                    edges {
                        role
                        node {
                            name {
                                full
                            }
                            image {
                                large
                            }
                        }
                    }
                }
                studios {
                    nodes {
                        name
                        isAnimationStudio
                    }
                }
                source
                countryOfOrigin
                isLicensed
                hasChapters
                hasVolumes
                recommendations {
                    nodes {
                        mediaRecommendation {
                            id
                            title {
                                romaji
                            }
                            coverImage {
                                medium
                            }
                        }
                    }
                }
                nextAiringEpisode {
                    episode
                    airingAt
                    timeUntilAiring
                }
                airingSchedule {
                    nodes {
                        episode
                        airingAt
                    }
                }
            }
        }
        """
        
        variables = {'id': anime_id}
        data = await self._make_request(query, variables)
        
        if data and 'Media' in data:
            media = data['Media']
            return {
                'id': media['id'],
                'title': media['title'],
                'format': media.get('format'),
                'episodes': media.get('episodes'),
                'duration': media.get('duration'),
                'status': media.get('status'),
                'start_date': media.get('startDate'),
                'end_date': media.get('endDate'),
                'description': media.get('description'),
                'cover_image': media.get('coverImage', {}).get('large'),
                'cover_color': media.get('coverImage', {}).get('color'),
                'banner_image': media.get('bannerImage'),
                'genres': media.get('genres', []),
                'synonyms': media.get('synonyms', []),
                'score': media.get('averageScore') or media.get('meanScore'),
                'popularity': media.get('popularity'),
                'favourites': media.get('favourites'),
                'trending': media.get('trending'),
                'studios': [s['name'] for s in media.get('studios', {}).get('nodes', []) if s.get('isAnimationStudio')],
                'source': media.get('source'),
                'country': media.get('countryOfOrigin'),
                'next_episode': media.get('nextAiringEpisode'),
                'airing_schedule': media.get('airingSchedule', {}).get('nodes', [])
            }
        return None
    
    async def get_trending_anime(self, page: int = 1, per_page: int = 10) -> List[Dict]:
        """Get trending anime"""
        query = """
        query ($page: Int, $perPage: Int) {
            Page(page: $page, perPage: $perPage) {
                media(type: ANIME, sort: TRENDING_DESC) {
                    id
                    title {
                        romaji
                        english
                    }
                    coverImage {
                        large
                    }
                    averageScore
                    episodes
                    format
                    nextAiringEpisode {
                        episode
                        airingAt
                    }
                    status
                }
            }
        }
        """
        
        variables = {'page': page, 'perPage': per_page}
        data = await self._make_request(query, variables)
        
        if data and 'Page' in data:
            return data['Page']['media']
        return []
    
    async def get_popular_anime(self, page: int = 1, per_page: int = 10) -> List[Dict]:
        """Get popular anime"""
        query = """
        query ($page: Int, $perPage: Int) {
            Page(page: $page, perPage: $perPage) {
                media(type: ANIME, sort: POPULARITY_DESC) {
                    id
                    title {
                        romaji
                        english
                    }
                    coverImage {
                        large
                    }
                    averageScore
                    episodes
                    format
                    status
                    popularity
                }
            }
        }
        """
        
        variables = {'page': page, 'perPage': per_page}
        data = await self._make_request(query, variables)
        
        if data and 'Page' in data:
            return data['Page']['media']
        return []
    
    async def get_seasonal_anime(self, season: str = None, year: int = None) -> List[Dict]:
        """Get seasonal anime"""
        from datetime import datetime
        
        if not year:
            year = datetime.now().year
        if not season:
            month = datetime.now().month
            if month in [1, 2, 3]:
                season = "WINTER"
            elif month in [4, 5, 6]:
                season = "SPRING"
            elif month in [7, 8, 9]:
                season = "SUMMER"
            else:
                season = "FALL"
        
        query = """
        query ($season: MediaSeason, $year: Int) {
            Page(page: 1, perPage: 50) {
                media(type: ANIME, season: $season, seasonYear: $year, sort: POPULARITY_DESC) {
                    id
                    title {
                        romaji
                        english
                    }
                    coverImage {
                        large
                    }
                    averageScore
                    episodes
                    format
                    status
                    nextAiringEpisode {
                        episode
                        airingAt
                    }
                }
            }
        }
        """
        
        variables = {'season': season.upper(), 'year': year}
        data = await self._make_request(query, variables)
        
        if data and 'Page' in data:
            return data['Page']['media']
        return []
    
    async def get_airing_schedule(self, page: int = 1, per_page: int = 20) -> List[Dict]:
        """Get currently airing anime schedule"""
        query = """
        query ($page: Int, $perPage: Int) {
            Page(page: $page, perPage: $perPage) {
                media(type: ANIME, status: RELEASING, sort: POPULARITY_DESC) {
                    id
                    title {
                        romaji
                        english
                    }
                    coverImage {
                        medium
                    }
                    episodes
                    nextAiringEpisode {
                        episode
                        airingAt
                        timeUntilAiring
                    }
                    averageScore
                    genres
                    studios {
                        nodes {
                            name
                        }
                    }
                }
            }
        }
        """
        
        variables = {'page': page, 'perPage': per_page}
        data = await self._make_request(query, variables)
        
        if data and 'Page' in data:
            results = []
            for media in data['Page']['media']:
                next_ep = media.get('nextAiringEpisode')
                if next_ep:
                    results.append({
                        'id': media['id'],
                        'title': media['title'].get('english') or media['title'].get('romaji'),
                        'cover': media.get('coverImage', {}).get('medium'),
                        'episode': next_ep.get('episode'),
                        'airing_at': next_ep.get('airingAt'),
                        'time_until': next_ep.get('timeUntilAiring'),
                        'score': media.get('averageScore'),
                        'genres': media.get('genres', [])[:3],
                        'studio': media.get('studios', {}).get('nodes', [{}])[0].get('name')
                    })
            return results
        return []
    
    async def get_anime_by_id(self, anime_id: int) -> Optional[Dict]:
        """Get anime by ID (alias for get_anime_details)"""
        return await self.get_anime_details(anime_id)
    
    async def get_character_details(self, character_id: int) -> Optional[Dict]:
        """Get character details"""
        query = """
        query ($id: Int) {
            Character(id: $id) {
                id
                name {
                    full
                    native
                    alternative
                }
                image {
                    large
                    medium
                }
                description
                favourites
                media {
                    nodes {
                        id
                        title {
                            romaji
                        }
                        format
                    }
                }
            }
        }
        """
        
        variables = {'id': character_id}
        data = await self._make_request(query, variables)
        
        if data and 'Character' in data:
            return data['Character']
        return None
    
    async def get_studio_details(self, studio_id: int) -> Optional[Dict]:
        """Get studio details"""
        query = """
        query ($id: Int) {
            Studio(id: $id) {
                id
                name
                isAnimationStudio
                media {
                    nodes {
                        id
                        title {
                            romaji
                        }
                        format
                        episodes
                    }
                }
                favourites
            }
        }
        """
        
        variables = {'id': studio_id}
        data = await self._make_request(query, variables)
        
        if data and 'Studio' in data:
            return data['Studio']
        return None
