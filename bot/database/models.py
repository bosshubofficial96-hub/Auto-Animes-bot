"""
Data Models for ✦ ＡＵＴＯ ＡＮＩＭＥ ✦ Database
"""

import json
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field


class TaskStatus(Enum):
    """Status of a processing task"""
    PENDING = "pending"
    FETCHING = "fetching"
    DOWNLOADING = "downloading"
    PROCESSING = "processing"
    UPLOADING = "uploading"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REDOWNLOAD_REQUESTED = "redownload_requested"


class RequestStatus(Enum):
    """Status of user request"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMPLETED = "completed"
    PROCESSING = "processing"


class AnimeStatus(Enum):
    """Anime release status"""
    RELEASING = "releasing"
    FINISHED = "finished"
    NOT_YET_RELEASED = "not_yet_released"
    CANCELLED = "cancelled"
    HIATUS = "hiatus"


class Quality(Enum):
    """Video quality options"""
    P480 = "480p"
    P720 = "720p"
    P1080 = "1080p"
    
    @classmethod
    def values(cls) -> List[str]:
        return [q.value for q in cls]


@dataclass
class AnimeTask:
    """Anime processing task model"""
    task_id: str
    title: str
    episode: int
    quality: str
    status: TaskStatus
    source_url: Optional[str] = None
    file_path: Optional[Path] = None
    processed_paths: Dict[str, Path] = field(default_factory=dict)
    telegram_message_ids: Dict[str, int] = field(default_factory=dict)
    error_log: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    requested_by: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    retry_count: int = 0
    progress: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage"""
        return {
            'task_id': self.task_id,
            'title': self.title,
            'episode': self.episode,
            'quality': self.quality,
            'status': self.status.value,
            'source_url': self.source_url,
            'file_path': str(self.file_path) if self.file_path else None,
            'processed_paths': json.dumps({k: str(v) for k, v in self.processed_paths.items()}),
            'telegram_message_ids': json.dumps(self.telegram_message_ids),
            'error_log': self.error_log,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'requested_by': self.requested_by,
            'metadata': json.dumps(self.metadata),
            'retry_count': self.retry_count,
            'progress': self.progress
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AnimeTask':
        """Create from dictionary from database"""
        return cls(
            task_id=data['task_id'],
            title=data['title'],
            episode=data['episode'],
            quality=data['quality'],
            status=TaskStatus(data['status']),
            source_url=data.get('source_url'),
            file_path=Path(data['file_path']) if data.get('file_path') else None,
            processed_paths={
                k: Path(v) for k, v in json.loads(data.get('processed_paths', '{}')).items()
            },
            telegram_message_ids=json.loads(data.get('telegram_message_ids', '{}')),
            error_log=data.get('error_log'),
            created_at=datetime.fromisoformat(data['created_at']),
            updated_at=datetime.fromisoformat(data['updated_at']),
            started_at=datetime.fromisoformat(data['started_at']) if data.get('started_at') else None,
            completed_at=datetime.fromisoformat(data['completed_at']) if data.get('completed_at') else None,
            requested_by=data.get('requested_by'),
            metadata=json.loads(data.get('metadata', '{}')),
            retry_count=data.get('retry_count', 0),
            progress=data.get('progress', 0.0)
        )
    
    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), default=str)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'AnimeTask':
        """Create from JSON string"""
        return cls.from_dict(json.loads(json_str))


@dataclass
class UserRequest:
    """User request model"""
    request_id: int
    user_id: int
    anime_title: str
    episode: Optional[int] = None
    quality: Optional[str] = None
    status: RequestStatus = RequestStatus.PENDING
    requested_at: datetime = field(default_factory=datetime.now)
    processed_at: Optional[datetime] = None
    task_id: Optional[str] = None
    admin_notes: Optional[str] = None
    user_name: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'request_id': self.request_id,
            'user_id': self.user_id,
            'anime_title': self.anime_title,
            'episode': self.episode,
            'quality': self.quality,
            'status': self.status.value,
            'requested_at': self.requested_at.isoformat(),
            'processed_at': self.processed_at.isoformat() if self.processed_at else None,
            'task_id': self.task_id,
            'admin_notes': self.admin_notes,
            'user_name': self.user_name
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserRequest':
        """Create from dictionary"""
        return cls(
            request_id=data['request_id'],
            user_id=data['user_id'],
            anime_title=data['anime_title'],
            episode=data.get('episode'),
            quality=data.get('quality'),
            status=RequestStatus(data['status']),
            requested_at=datetime.fromisoformat(data['requested_at']),
            processed_at=datetime.fromisoformat(data['processed_at']) if data.get('processed_at') else None,
            task_id=data.get('task_id'),
            admin_notes=data.get('admin_notes'),
            user_name=data.get('user_name')
        )


@dataclass
class Admin:
    """Admin user model"""
    user_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    added_by: Optional[int] = None
    added_at: datetime = field(default_factory=datetime.now)
    permissions: List[str] = field(default_factory=lambda: ['all'])
    is_active: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'user_id': self.user_id,
            'username': self.username,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'added_by': self.added_by,
            'added_at': self.added_at.isoformat(),
            'permissions': json.dumps(self.permissions),
            'is_active': self.is_active
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Admin':
        """Create from dictionary"""
        return cls(
            user_id=data['user_id'],
            username=data.get('username'),
            first_name=data.get('first_name'),
            last_name=data.get('last_name'),
            added_by=data.get('added_by'),
            added_at=datetime.fromisoformat(data['added_at']) if data.get('added_at') else datetime.now(),
            permissions=json.loads(data.get('permissions', '["all"]')),
            is_active=data.get('is_active', True)
        )
    
    def has_permission(self, permission: str) -> bool:
        """Check if admin has specific permission"""
        return 'all' in self.permissions or permission in self.permissions


@dataclass
class AiringAnime:
    """Currently airing anime model"""
    anime_id: int
    title: str
    title_english: Optional[str] = None
    title_romaji: Optional[str] = None
    episode_count: int = 0
    next_episode: int = 1
    airing_date: Optional[datetime] = None
    airing_time_until: Optional[int] = None
    studio: Optional[str] = None
    genres: List[str] = field(default_factory=list)
    rating: Optional[float] = None
    image_url: Optional[str] = None
    banner_url: Optional[str] = None
    synopsis: Optional[str] = None
    status: AnimeStatus = AnimeStatus.RELEASING
    total_episodes: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'anime_id': self.anime_id,
            'title': self.title,
            'title_english': self.title_english,
            'title_romaji': self.title_romaji,
            'episode_count': self.episode_count,
            'next_episode': self.next_episode,
            'airing_date': self.airing_date.isoformat() if self.airing_date else None,
            'airing_time_until': self.airing_time_until,
            'studio': self.studio,
            'genres': json.dumps(self.genres),
            'rating': self.rating,
            'image_url': self.image_url,
            'banner_url': self.banner_url,
            'synopsis': self.synopsis,
            'status': self.status.value,
            'total_episodes': self.total_episodes
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AiringAnime':
        """Create from dictionary"""
        return cls(
            anime_id=data['anime_id'],
            title=data['title'],
            title_english=data.get('title_english'),
            title_romaji=data.get('title_romaji'),
            episode_count=data.get('episode_count', 0),
            next_episode=data.get('next_episode', 1),
            airing_date=datetime.fromisoformat(data['airing_date']) if data.get('airing_date') else None,
            airing_time_until=data.get('airing_time_until'),
            studio=data.get('studio'),
            genres=json.loads(data.get('genres', '[]')),
            rating=data.get('rating'),
            image_url=data.get('image_url'),
            banner_url=data.get('banner_url'),
            synopsis=data.get('synopsis'),
            status=AnimeStatus(data.get('status', 'releasing')),
            total_episodes=data.get('total_episodes')
        )


@dataclass
 class DownloadQueue:
    """Download queue item model"""
    queue_id: int
    task_id: str
    priority: int = 0
    added_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'queue_id': self.queue_id,
            'task_id': self.task_id,
            'priority': self.priority,
            'added_at': self.added_at.isoformat(),
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }


@dataclass
class BotStats:
    """Bot statistics model"""
    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    total_requests: int = 0
    pending_requests: int = 0
    total_users: int = 0
    total_downloads_gb: float = 0.0
    uptime_seconds: int = 0
    last_updated: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'total_tasks': self.total_tasks,
            'completed_tasks': self.completed_tasks,
            'failed_tasks': self.failed_tasks,
            'total_requests': self.total_requests,
            'pending_requests': self.pending_requests,
            'total_users': self.total_users,
            'total_downloads_gb': self.total_downloads_gb,
            'uptime_seconds': self.uptime_seconds,
            'last_updated': self.last_updated.isoformat()
        }
