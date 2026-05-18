"""
Fetcher Module — Anime metadata and source URL fetching
Integrates Nyaa.si RSS for download sources
"""

import re
import aiohttp
from typing import Optional, Dict, Any, List
from datetime import datetime

from bot.config import Config
from bot.database.database import DatabaseManager
from bot.database.models import AnimeTask
from bot.utils.logger import setup_logger


class Fetcher:
    """Fetches anime metadata and source URLs"""

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.logger = setup_logger("fetcher")
        self.providers = [
            self._fetch_from_anilist,
            self._fetch_from_jikan,
        ]

    async def fetch(self, task: AnimeTask) -> Optional[Dict[str, Any]]:
        """Fetch source URL and metadata for the task"""
        self.logger.info(f"Fetching: {task.title} EP{task.episode}")

        # If a source URL is already set manually (e.g., admin set it), skip fetch
        if task.source_url:
            self.logger.info(f"Source URL already set for {task.task_id}")
            return {'url': task.source_url, 'metadata': task.metadata}

        # Try API providers for metadata, then search Nyaa for download URL
        metadata = {}
        for provider in self.providers:
            try:
                result = await provider(task)
                if result:
                    metadata = result.get('metadata', {})
                    break
            except Exception as e:
                self.logger.warning(f"Provider {provider.__name__} failed: {e}")
                continue

        # Search Nyaa.si for the actual download URL
        nyaa_url = await self._get_download_url_nyaa(task.title, task.episode)
        if nyaa_url:
            self.logger.info(f"✅ Found Nyaa source for {task.title} EP{task.episode}")
            return {'url': nyaa_url, 'metadata': metadata}

        # Fallback: search AnimeTosho
        tosho_url = await self._get_download_url_tosho(task.title, task.episode)
        if tosho_url:
            self.logger.info(f"✅ Found AnimeTosho source for {task.title} EP{task.episode}")
            return {'url': tosho_url, 'metadata': metadata}

        self.logger.error(f"❌ No source found for: {task.title} EP{task.episode}")
        return None

    async def _fetch_from_anilist(self, task: AnimeTask) -> Optional[Dict[str, Any]]:
        """Fetch metadata from AniList API"""
        query = """
        query ($search: String) {
            Media (search: $search, type: ANIME) {
                id
                title { romaji english native }
                episodes
                status
                nextAiringEpisode { episode airingAt }
                siteUrl
                coverImage { large }
                description
                genres
                averageScore
            }
        }
        """
        variables = {'search': task.title}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    Config.ANILIST_API,
                    json={'query': query, 'variables': variables},
                    headers={'Content-Type': 'application/json'},
                    timeout=aiohttp.ClientTimeout(total=15)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        media = data.get('data', {}).get('Media')
                        if media:
                            return {
                                'url': None,
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
        except Exception as e:
            self.logger.warning(f"AniList fetch failed: {e}")
        return None

    async def _fetch_from_jikan(self, task: AnimeTask) -> Optional[Dict[str, Any]]:
        """Fetch metadata from Jikan API (MyAnimeList)"""
        search_url = f"{Config.JIKAN_API}/anime?q={task.title}&limit=1"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(search_url, timeout=aiohttp.ClientTimeout(total=15)) as response:
                    if response.status == 200:
                        data = await response.json()
                        results = data.get('data', [])
                        if results:
                            anime = results[0]
                            return {
                                'url': None,
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
        except Exception as e:
            self.logger.warning(f"Jikan fetch failed: {e}")
        return None

    async def _get_download_url_nyaa(self, title: str, episode: int) -> Optional[str]:
        """
        Search Nyaa.si RSS for anime download link.
        Finds the best match (SubsPlease/Erai-raws groups preferred).
        """
        if episode <= 0:
            return None

        ep_padded = str(episode).zfill(2)
        queries = [
            f"{title} - {ep_padded}",
            f"{title} {ep_padded}",
            f"{title} episode {episode}",
        ]
        preferred_groups = ['subsplease', 'erai-raws', 'horriblesubs', 'ember', 'judas']

        for query in queries:
            result = await self._nyaa_rss_search(query, preferred_groups)
            if result:
                return result

        return None

    async def _nyaa_rss_search(self, query: str, preferred_groups: List[str]) -> Optional[str]:
        """Search Nyaa.si RSS and return best torrent link"""
        try:
            encoded_query = query.replace(' ', '+')
            rss_url = f"https://nyaa.si/?q={encoded_query}&c=1_2&f=0&page=rss"
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    rss_url,
                    timeout=aiohttp.ClientTimeout(total=20),
                    headers={'User-Agent': 'Mozilla/5.0 (AnimeBot/2.0)'}
                ) as resp:
                    if resp.status != 200:
                        return None
                    text = await resp.text()
            return self._parse_nyaa_rss(text, preferred_groups)
        except Exception as e:
            self.logger.debug(f"Nyaa RSS search failed for '{query}': {e}")
            return None

    def _parse_nyaa_rss(self, xml_text: str, preferred_groups: List[str]) -> Optional[str]:
        """Parse Nyaa RSS XML and return best magnet/torrent link"""
        try:
            items = re.findall(r'<item>(.*?)</item>', xml_text, re.DOTALL)
            if not items:
                return None

            best_link = None
            best_score = -1

            for item in items[:15]:
                title_match = re.search(r'<title><!\[CDATA\[(.*?)\]\]></title>', item)
                link_match = re.search(r'<link>(.*?)</link>', item)
                guid_match = re.search(r'<guid>(https://nyaa\.si/view/\d+)</guid>', item)
                seeders_match = re.search(r'<nyaa:seeders>(.*?)</nyaa:seeders>', item)

                if not title_match or not (link_match or guid_match):
                    continue

                item_title = title_match.group(1).lower()
                link = link_match.group(1) if link_match else guid_match.group(1)
                seeders = int(seeders_match.group(1)) if seeders_match else 0

                score = seeders
                for group in preferred_groups:
                    if group in item_title:
                        score += 1000
                        break
                if '1080p' in item_title:
                    score += 5
                elif '720p' in item_title:
                    score += 3
                elif '480p' in item_title:
                    score += 1

                if score > best_score:
                    best_score = score
                    best_link = link

            return best_link
        except Exception as e:
            self.logger.debug(f"RSS parse error: {e}")
            return None

    async def _get_download_url_tosho(self, title: str, episode: int) -> Optional[str]:
        """Search AnimeTosho as fallback source"""
        if episode <= 0:
            return None
        ep_padded = str(episode).zfill(2)
        query = f"{title} - {ep_padded}"
        try:
            encoded = query.replace(' ', '+')
            url = f"https://animetosho.org/search?q={encoded}&t=2"
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    timeout=aiohttp.ClientTimeout(total=20),
                    headers={'User-Agent': 'Mozilla/5.0 (AnimeBot/2.0)'}
                ) as resp:
                    if resp.status == 200:
                        text = await resp.text()
                        # Extract first torrent link from HTML
                        match = re.search(r'href="(https://animetosho\.org/storage/torrent/[^"]+\.torrent)"', text)
                        if match:
                            return match.group(1)
        except Exception as e:
            self.logger.debug(f"AnimeTosho search failed: {e}")
        return None

    async def get_airing_schedule(self) -> list:
        """Get today's airing anime from AniList"""
        query = """
        query {
            Page(page: 1, perPage: 50) {
                media(status: RELEASING, sort: POPULARITY_DESC) {
                    id
                    title { romaji english }
                    nextAiringEpisode { episode airingAt timeUntilAiring }
                    episodes
                    coverImage { medium }
                    averageScore
                    genres
                    studios { nodes { name } }
                }
            }
        }
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    Config.ANILIST_API,
                    json={'query': query},
                    timeout=aiohttp.ClientTimeout(total=20)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        media_list = data.get('data', {}).get('Page', {}).get('media', [])
                        today_airing = []
                        for media in media_list:
                            next_ep = media.get('nextAiringEpisode')
                            if next_ep:
                                airing_time = datetime.fromtimestamp(next_ep['airingAt'])
                                if airing_time.date() == datetime.now().date():
                                    title = media['title'].get('english') or media['title'].get('romaji')
                                    studio = ''
                                    nodes = media.get('studios', {}).get('nodes', [])
                                    if nodes:
                                        studio = nodes[0].get('name', '')
                                    today_airing.append({
                                        'id': media['id'],
                                        'title': title,
                                        'episode': next_ep['episode'],
                                        'airing_time': airing_time,
                                        'airing_at': next_ep['airingAt'],
                                        'cover': media.get('coverImage', {}).get('medium'),
                                        'score': media.get('averageScore'),
                                        'genres': media.get('genres', [])[:3],
                                        'studio': studio
                                    })
                        return today_airing
        except Exception as e:
            self.logger.error(f"Failed to fetch airing schedule: {e}")
        return []
