"""
Database Manager for ✦ ＡＵＴＯ ＡＮＩＭＥ ✦
Handles all database operations with SQLite
"""

import sqlite3
import json
import aiosqlite
from pathlib import Path
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any, Tuple
from contextlib import asynccontextmanager

from bot.database.models import (
    AnimeTask, UserRequest, TaskStatus, RequestStatus, 
    Admin, AiringAnime, BotStats
)
from bot.utils.logger import setup_logger


class DatabaseManager:
    """Async database manager for the bot"""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.logger = setup_logger("database")
        self._ensure_directory()
    
    def _ensure_directory(self):
        """Ensure database directory exists"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
    
    @asynccontextmanager
    async def get_connection(self):
        """Get database connection context manager"""
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            yield conn
    
    async def initialize(self):
        """Initialize database tables and indexes"""
        async with self.get_connection() as conn:
            # Tasks table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    task_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    episode INTEGER,
                    quality TEXT,
                    status TEXT,
                    source_url TEXT,
                    file_path TEXT,
                    processed_paths TEXT,
                    telegram_message_ids TEXT,
                    error_log TEXT,
                    created_at TIMESTAMP,
                    updated_at TIMESTAMP,
                    started_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    requested_by INTEGER,
                    metadata TEXT,
                    retry_count INTEGER DEFAULT 0,
                    progress REAL DEFAULT 0
                )
            """)
            
            # User requests table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS user_requests (
                    request_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    user_name TEXT,
                    anime_title TEXT NOT NULL,
                    episode INTEGER,
                    quality TEXT,
                    status TEXT DEFAULT 'pending',
                    requested_at TIMESTAMP,
                    processed_at TIMESTAMP,
                    task_id TEXT,
                    admin_notes TEXT,
                    FOREIGN KEY (task_id) REFERENCES tasks(task_id)
                )
            """)
            
            # Admins table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS admins (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    added_by INTEGER,
                    added_at TIMESTAMP,
                    permissions TEXT,
                    is_active INTEGER DEFAULT 1
                )
            """)
            
            # Daily request counter
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS daily_requests (
                    date TEXT PRIMARY KEY,
                    count INTEGER DEFAULT 0
                )
            """)
            
            # Config table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS config (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TIMESTAMP
                )
            """)
            
            # Airing cache table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS airing_cache (
                    anime_id INTEGER PRIMARY KEY,
                    data TEXT,
                    last_updated TIMESTAMP
                )
            """)
            
            # Users table (for tracking)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    first_seen TIMESTAMP,
                    last_seen TIMESTAMP,
                    request_count INTEGER DEFAULT 0
                )
            """)
            
            # Download queue table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS download_queue (
                    queue_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT,
                    priority INTEGER DEFAULT 0,
                    added_at TIMESTAMP,
                    started_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES tasks(task_id)
                )
            """)
            
            # Bot statistics table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS bot_stats (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    total_tasks INTEGER DEFAULT 0,
                    completed_tasks INTEGER DEFAULT 0,
                    failed_tasks INTEGER DEFAULT 0,
                    total_requests INTEGER DEFAULT 0,
                    pending_requests INTEGER DEFAULT 0,
                    total_users INTEGER DEFAULT 0,
                    total_downloads_gb REAL DEFAULT 0,
                    uptime_seconds INTEGER DEFAULT 0,
                    last_updated TIMESTAMP
                )
            """)
            
            # Create indexes for performance
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_title ON tasks(title)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_created ON tasks(created_at)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_requests_user ON user_requests(user_id)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_requests_status ON user_requests(status)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_requests_requested ON user_requests(requested_at)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_queue_priority ON download_queue(priority, added_at)")
            
            # Initialize default config if not exists
            default_configs = [
                ('request_time', '18:00'),
                ('cleanup_hours', '12'),
                ('max_user_requests', '5'),
                ('max_daily_requests', '100'),
                ('maintenance_mode', 'false'),
                ('last_cleanup', datetime.now().isoformat()),
                ('bot_version', '2.0.0'),
                ('auto_approve_requests', 'false')
            ]
            
            for key, value in default_configs:
                await conn.execute("""
                    INSERT OR IGNORE INTO config (key, value, updated_at)
                    VALUES (?, ?, ?)
                """, (key, value, datetime.now()))
            
            # Initialize bot stats
            await conn.execute("""
                INSERT OR IGNORE INTO bot_stats (id, last_updated)
                VALUES (1, ?)
            """, (datetime.now().isoformat(),))
            
            await conn.commit()
            
            self.logger.info("✅ Database initialized successfully")
    
    # ==================== TASK OPERATIONS ====================
    
    async def add_task(self, task: AnimeTask) -> bool:
        """Add a new task to database"""
        async with self.get_connection() as conn:
            try:
                await conn.execute("""
                    INSERT OR REPLACE INTO tasks 
                    (task_id, title, episode, quality, status, source_url, file_path,
                     processed_paths, telegram_message_ids, error_log, created_at,
                     updated_at, started_at, completed_at, requested_by, metadata, 
                     retry_count, progress)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    task.task_id, task.title, task.episode, task.quality,
                    task.status.value, task.source_url, 
                    str(task.file_path) if task.file_path else None,
                    json.dumps({k: str(v) for k, v in task.processed_paths.items()}),
                    json.dumps(task.telegram_message_ids),
                    task.error_log, task.created_at.isoformat(), 
                    task.updated_at.isoformat(),
                    task.started_at.isoformat() if task.started_at else None,
                    task.completed_at.isoformat() if task.completed_at else None,
                    task.requested_by, json.dumps(task.metadata), 
                    task.retry_count, task.progress
                ))
                await conn.commit()
                return True
            except Exception as e:
                self.logger.error(f"Error adding task: {e}")
                return False
    
    async def update_task_status(self, task_id: str, status: TaskStatus, error_log: str = None):
        """Update task status"""
        async with self.get_connection() as conn:
            await conn.execute("""
                UPDATE tasks 
                SET status = ?, error_log = ?, updated_at = ?
                WHERE task_id = ?
            """, (status.value, error_log, datetime.now().isoformat(), task_id))
            
            # Update started_at if status is processing
            if status in [TaskStatus.DOWNLOADING, TaskStatus.PROCESSING, TaskStatus.UPLOADING]:
                await conn.execute("""
                    UPDATE tasks SET started_at = ? 
                    WHERE task_id = ? AND started_at IS NULL
                """, (datetime.now().isoformat(), task_id))
            
            await conn.commit()
    
    async def update_task_progress(self, task_id: str, progress: float):
        """Update task progress percentage"""
        async with self.get_connection() as conn:
            await conn.execute("""
                UPDATE tasks SET progress = ?, updated_at = ?
                WHERE task_id = ?
            """, (progress, datetime.now().isoformat(), task_id))
            await conn.commit()
    
    async def get_task(self, task_id: str) -> Optional[AnimeTask]:
        """Get task by ID"""
        async with self.get_connection() as conn:
            async with conn.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    return self._row_to_task(row)
        return None
    
    async def get_pending_tasks(self, limit: int = 10) -> List[AnimeTask]:
        """Get pending tasks"""
        async with self.get_connection() as conn:
            async with conn.execute("""
                SELECT * FROM tasks 
                WHERE status IN ('pending', 'failed', 'redownload_requested')
                ORDER BY 
                    CASE status 
                        WHEN 'redownload_requested' THEN 0
                        WHEN 'pending' THEN 1
                        ELSE 2
                    END,
                    created_at ASC
                LIMIT ?
            """, (limit,)) as cursor:
                rows = await cursor.fetchall()
                return [self._row_to_task(row) for row in rows]
    
    async def get_active_tasks(self) -> List[AnimeTask]:
        """Get active (processing) tasks"""
        async with self.get_connection() as conn:
            async with conn.execute("""
                SELECT * FROM tasks 
                WHERE status IN ('fetching', 'downloading', 'processing', 'uploading')
                ORDER BY started_at ASC
            """) as cursor:
                rows = await cursor.fetchall()
                return [self._row_to_task(row) for row in rows]
    
    async def get_completed_tasks(self, limit: int = 50, offset: int = 0) -> List[AnimeTask]:
        """Get completed tasks"""
        async with self.get_connection() as conn:
            async with conn.execute("""
                SELECT * FROM tasks 
                WHERE status = 'completed'
                ORDER BY completed_at DESC
                LIMIT ? OFFSET ?
            """, (limit, offset)) as cursor:
                rows = await cursor.fetchall()
                return [self._row_to_task(row) for row in rows]
    
    async def get_tasks_by_title(self, title: str, limit: int = 20) -> List[AnimeTask]:
        """Get tasks by anime title"""
        async with self.get_connection() as conn:
            async with conn.execute("""
                SELECT * FROM tasks 
                WHERE title LIKE ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (f'%{title}%', limit)) as cursor:
                rows = await cursor.fetchall()
                return [self._row_to_task(row) for row in rows]
    
    async def delete_old_tasks(self, days: int = 30) -> int:
        """Delete tasks older than specified days"""
        cutoff_date = datetime.now() - timedelta(days=days)
        async with self.get_connection() as conn:
            cursor = await conn.execute("""
                DELETE FROM tasks 
                WHERE status IN ('completed', 'failed') 
                AND completed_at < ?
                RETURNING task_id
            """, (cutoff_date.isoformat(),))
            deleted = await cursor.fetchall()
            await conn.commit()
            return len(deleted)
    
    def _row_to_task(self, row) -> AnimeTask:
        """Convert database row to AnimeTask object"""
        return AnimeTask(
            task_id=row['task_id'],
            title=row['title'],
            episode=row['episode'],
            quality=row['quality'],
            status=TaskStatus(row['status']),
            source_url=row['source_url'],
            file_path=Path(row['file_path']) if row['file_path'] else None,
            processed_paths={
                k: Path(v) for k, v in json.loads(row['processed_paths'] or '{}').items()
            },
            telegram_message_ids=json.loads(row['telegram_message_ids'] or '{}'),
            error_log=row['error_log'],
            created_at=datetime.fromisoformat(row['created_at']),
            updated_at=datetime.fromisoformat(row['updated_at']),
            started_at=datetime.fromisoformat(row['started_at']) if row['started_at'] else None,
            completed_at=datetime.fromisoformat(row['completed_at']) if row['completed_at'] else None,
            requested_by=row['requested_by'],
            metadata=json.loads(row['metadata'] or '{}'),
            retry_count=row['retry_count'] or 0,
            progress=row['progress'] or 0.0
        )
    
    # ==================== USER REQUEST OPERATIONS ====================
    
    async def add_user_request(self, user_id: int, anime_title: str, episode: int = None, 
                                quality: str = None, user_name: str = None) -> int:
        """Add a user request"""
        async with self.get_connection() as conn:
            cursor = await conn.execute("""
                INSERT INTO user_requests 
                (user_id, user_name, anime_title, episode, quality, requested_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (user_id, user_name, anime_title, episode, quality, datetime.now().isoformat()))
            await conn.commit()
            
            # Update user's request count
            await self._increment_user_request_count(user_id)
            
            return cursor.lastrowid
    
    async def get_pending_requests(self, limit: int = 50) -> List[Dict]:
        """Get all pending requests"""
        async with self.get_connection() as conn:
            async with conn.execute("""
                SELECT * FROM user_requests 
                WHERE status = 'pending'
                ORDER BY requested_at ASC
                LIMIT ?
            """, (limit,)) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
    
    async def get_request_by_id(self, request_id: int) -> Optional[Dict]:
        """Get request by ID"""
        async with self.get_connection() as conn:
            async with conn.execute(
                "SELECT * FROM user_requests WHERE request_id = ?", (request_id,)
            ) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None
    
    async def update_request_status(self, request_id: int, status: RequestStatus, 
                                     task_id: str = None, admin_notes: str = None):
        """Update request status"""
        async with self.get_connection() as conn:
            await conn.execute("""
                UPDATE user_requests 
                SET status = ?, processed_at = ?, task_id = ?, admin_notes = ?
                WHERE request_id = ?
            """, (status.value, datetime.now().isoformat(), task_id, admin_notes, request_id))
            await conn.commit()
    
    async def get_user_requests(self, user_id: int, limit: int = 20) -> List[Dict]:
        """Get user's requests"""
        async with self.get_connection() as conn:
            async with conn.execute("""
                SELECT * FROM user_requests 
                WHERE user_id = ?
                ORDER BY requested_at DESC
                LIMIT ?
            """, (user_id, limit)) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
    
    async def get_requests_by_status(self, status: RequestStatus, limit: int = 100) -> List[Dict]:
        """Get requests by status"""
        async with self.get_connection() as conn:
            async with conn.execute("""
                SELECT * FROM user_requests 
                WHERE status = ?
                ORDER BY requested_at ASC
                LIMIT ?
            """, (status.value, limit)) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
    
    # ==================== ADMIN OPERATIONS ====================
    
    async def add_admin(self, user_id: int, username: str = None, first_name: str = None,
                        last_name: str = None, added_by: int = None) -> bool:
        """Add admin user"""
        async with self.get_connection() as conn:
            try:
                await conn.execute("""
                    INSERT OR REPLACE INTO admins 
                    (user_id, username, first_name, last_name, added_by, added_at, permissions)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (user_id, username, first_name, last_name, added_by, 
                      datetime.now().isoformat(), json.dumps(['all'])))
                await conn.commit()
                return True
            except Exception as e:
                self.logger.error(f"Error adding admin: {e}")
                return False
    
    async def is_admin(self, user_id: int) -> bool:
        """Check if user is admin"""
        async with self.get_connection() as conn:
            async with conn.execute(
                "SELECT 1 FROM admins WHERE user_id = ? AND is_active = 1", (user_id,)
            ) as cursor:
                row = await cursor.fetchone()
                return row is not None
    
    async def get_admins(self, include_inactive: bool = False) -> List[Admin]:
        """Get all admins"""
        query = "SELECT * FROM admins"
        if not include_inactive:
            query += " WHERE is_active = 1"
        
        async with self.get_connection() as conn:
            async with conn.execute(query) as cursor:
                rows = await cursor.fetchall()
                return [Admin.from_dict(dict(row)) for row in rows]
    
    async def remove_admin(self, user_id: int) -> bool:
        """Remove admin (soft delete)"""
        async with self.get_connection() as conn:
            await conn.execute(
                "UPDATE admins SET is_active = 0 WHERE user_id = ?", (user_id,)
            )
            await conn.commit()
            return True
    
    async def update_admin_permissions(self, user_id: int, permissions: List[str]) -> bool:
        """Update admin permissions"""
        async with self.get_connection() as conn:
            await conn.execute("""
                UPDATE admins SET permissions = ? WHERE user_id = ?
            """, (json.dumps(permissions), user_id))
            await conn.commit()
            return True
    
    # ==================== USER OPERATIONS ====================
    
    async def register_user(self, user_id: int, username: str = None, 
                            first_name: str = None, last_name: str = None):
        """Register or update user"""
        async with self.get_connection() as conn:
            await conn.execute("""
                INSERT INTO users (user_id, username, first_name, last_name, first_seen, last_seen)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    username = COALESCE(?, username),
                    first_name = COALESCE(?, first_name),
                    last_name = COALESCE(?, last_name),
                    last_seen = ?
            """, (user_id, username, first_name, last_name, 
                  datetime.now().isoformat(), datetime.now().isoformat(),
                  username, first_name, last_name, datetime.now().isoformat()))
            await conn.commit()
    
    async def get_user(self, user_id: int) -> Optional[Dict]:
        """Get user by ID"""
        async with self.get_connection() as conn:
            async with conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None
    
    async def get_all_users(self, limit: int = 1000) -> List[Dict]:
        """Get all users"""
        async with self.get_connection() as conn:
            async with conn.execute("SELECT * FROM users ORDER BY last_seen DESC LIMIT ?", (limit,)) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
    
    async def get_user_count(self) -> int:
        """Get total number of users"""
        async with self.get_connection() as conn:
            async with conn.execute("SELECT COUNT(*) as count FROM users") as cursor:
                row = await cursor.fetchone()
                return row['count'] if row else 0
    
    async def _increment_user_request_count(self, user_id: int):
        """Increment user's request count"""
        async with self.get_connection() as conn:
            await conn.execute("""
                UPDATE users SET request_count = request_count + 1
                WHERE user_id = ?
            """, (user_id,))
            await conn.commit()
    
    # ==================== CONFIG OPERATIONS ====================
    
    async def get_config(self, key: str, default: str = None) -> str:
        """Get config value"""
        async with self.get_connection() as conn:
            async with conn.execute("SELECT value FROM config WHERE key = ?", (key,)) as cursor:
                row = await cursor.fetchone()
                return row['value'] if row else default
    
    async def set_config(self, key: str, value: str):
        """Set config value"""
        async with self.get_connection() as conn:
            await conn.execute("""
                INSERT OR REPLACE INTO config (key, value, updated_at)
                VALUES (?, ?, ?)
            """, (key, value, datetime.now().isoformat()))
            await conn.commit()
    
    async def get_all_config(self) -> Dict[str, str]:
        """Get all config values"""
        async with self.get_connection() as conn:
            async with conn.execute("SELECT key, value FROM config") as cursor:
                rows = await cursor.fetchall()
                return {row['key']: row['value'] for row in rows}
    
    # ==================== STATISTICS ====================
    
    async def get_daily_request_count(self, target_date: date = None) -> int:
        """Get request count for a date"""
        if target_date is None:
            target_date = date.today()
        
        date_str = target_date.isoformat()
        async with self.get_connection() as conn:
            async with conn.execute(
                "SELECT count FROM daily_requests WHERE date = ?", (date_str,)
            ) as cursor:
                row = await cursor.fetchone()
                return row['count'] if row else 0
    
    async def increment_daily_request(self):
        """Increment today's request count"""
        today = date.today().isoformat()
        async with self.get_connection() as conn:
            await conn.execute("""
                INSERT INTO daily_requests (date, count)
                VALUES (?, 1)
                ON CONFLICT(date) DO UPDATE SET count = count + 1
            """, (today,))
            await conn.commit()
    
    async def get_task_stats(self) -> Dict:
        """Get task statistics"""
        async with self.get_connection() as conn:
            stats = {}
            for status in ['pending', 'fetching', 'downloading', 'processing', 
                          'uploading', 'completed', 'failed', 'cancelled']:
                async with conn.execute(
                    "SELECT COUNT(*) as count FROM tasks WHERE status = ?", (status,)
                ) as cursor:
                    row = await cursor.fetchone()
                    stats[status] = row['count']
            return stats
    
    async def get_detailed_stats(self) -> BotStats:
        """Get detailed bot statistics"""
        async with self.get_connection() as conn:
            # Task counts
            async with conn.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed
                FROM tasks
            """) as cursor:
                row = await cursor.fetchone()
                total_tasks = row['total'] or 0
                completed_tasks = row['completed'] or 0
                failed_tasks = row['failed'] or 0
            
            # Request counts
            async with conn.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending
                FROM user_requests
            """) as cursor:
                row = await cursor.fetchone()
                total_requests = row['total'] or 0
                pending_requests = row['pending'] or 0
            
            # User count
            total_users = await self.get_user_count()
            
            # Update bot stats
            await conn.execute("""
                UPDATE bot_stats 
                SET total_tasks = ?, completed_tasks = ?, failed_tasks = ?,
                    total_requests = ?, pending_requests = ?, total_users = ?,
                    last_updated = ?
                WHERE id = 1
            """, (total_tasks, completed_tasks, failed_tasks, 
                  total_requests, pending_requests, total_users,
                  datetime.now().isoformat()))
            await conn.commit()
            
            return BotStats(
                total_tasks=total_tasks,
                completed_tasks=completed_tasks,
                failed_tasks=failed_tasks,
                total_requests=total_requests,
                pending_requests=pending_requests,
                total_users=total_users
            )
    
    # ==================== AIRING CACHE ====================
    
    async def cache_airing_anime(self, anime_id: int, data: Dict):
        """Cache airing anime data"""
        async with self.get_connection() as conn:
            await conn.execute("""
                INSERT OR REPLACE INTO airing_cache (anime_id, data, last_updated)
                VALUES (?, ?, ?)
            """, (anime_id, json.dumps(data), datetime.now().isoformat()))
            await conn.commit()
    
    async def get_cached_airing(self, anime_id: int, max_age_hours: int = 24) -> Optional[Dict]:
        """Get cached airing anime data"""
        cutoff = datetime.now() - timedelta(hours=max_age_hours)
        async with self.get_connection() as conn:
            async with conn.execute("""
                SELECT data FROM airing_cache 
                WHERE anime_id = ? AND last_updated > ?
            """, (anime_id, cutoff.isoformat())) as cursor:
                row = await cursor.fetchone()
                return json.loads(row['data']) if row else None
    
    # ==================== DOWNLOAD QUEUE ====================
    
    async def add_to_queue(self, task_id: str, priority: int = 0):
        """Add task to download queue"""
        async with self.get_connection() as conn:
            await conn.execute("""
                INSERT INTO download_queue (task_id, priority, added_at)
                VALUES (?, ?, ?)
            """, (task_id, priority, datetime.now().isoformat()))
            await conn.commit()
    
    async def get_next_queue_item(self) -> Optional[str]:
        """Get next item from queue"""
        async with self.get_connection() as conn:
            async with conn.execute("""
                SELECT task_id FROM download_queue
                WHERE started_at IS NULL
                ORDER BY priority DESC, added_at ASC
                LIMIT 1
            """) as cursor:
                row = await cursor.fetchone()
                if row:
                    # Mark as started
                    await conn.execute("""
                        UPDATE download_queue SET started_at = ?
                        WHERE task_id = ?
                    """, (datetime.now().isoformat(), row['task_id']))
                    await conn.commit()
                    return row['task_id']
        return None
    
    async def complete_queue_item(self, task_id: str):
        """Mark queue item as completed"""
        async with self.get_connection() as conn:
            await conn.execute("""
                UPDATE download_queue SET completed_at = ?
                WHERE task_id = ?
            """, (datetime.now().isoformat(), task_id))
            await conn.commit()
    
    # ==================== MAINTENANCE ====================
    
    async def vacuum(self):
        """Optimize database"""
        async with self.get_connection() as conn:
            await conn.execute("VACUUM")
    
    async def backup(self, backup_path: Path) -> bool:
        """Create database backup"""
        try:
            import shutil
            shutil.copy2(self.db_path, backup_path)
            self.logger.info(f"Database backed up to {backup_path}")
            return True
        except Exception as e:
            self.logger.error(f"Backup failed: {e}")
            return False
