"""
Database Migration Manager for ✦ ＡＵＴＯ ＡＮＩＭＥ ✦
Handles schema migrations and version updates
"""

import sqlite3
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

from bot.utils.logger import setup_logger


class MigrationManager:
    """Manages database schema migrations"""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.logger = setup_logger("migrations")
        self._ensure_migrations_table()
    
    def _ensure_migrations_table(self):
        """Create migrations tracking table if not exists"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version INTEGER PRIMARY KEY,
                    applied_at TIMESTAMP,
                    description TEXT
                )
            """)
            conn.commit()
    
    def get_current_version(self) -> int:
        """Get current schema version"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT MAX(version) FROM schema_migrations")
            result = cursor.fetchone()[0]
            return result or 0
    
    def get_applied_migrations(self) -> List[Dict]:
        """Get list of applied migrations"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM schema_migrations ORDER BY version")
            rows = cursor.fetchall()
            return [
                {'version': row[0], 'applied_at': row[1], 'description': row[2]}
                for row in rows
            ]
    
    def apply_migration(self, version: int, description: str, up_sql: str):
        """Apply a migration"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            try:
                # Execute migration
                cursor.executescript(up_sql)
                
                # Record migration
                cursor.execute("""
                    INSERT INTO schema_migrations (version, applied_at, description)
                    VALUES (?, ?, ?)
                """, (version, datetime.now().isoformat(), description))
                
                conn.commit()
                self.logger.info(f"Applied migration v{version}: {description}")
                return True
                
            except Exception as e:
                conn.rollback()
                self.logger.error(f"Migration v{version} failed: {e}")
                raise
    
    def migrate_to_latest(self):
        """Migrate database to latest version"""
        current = self.get_current_version()
        
        migrations = self._get_migrations()
        pending = [m for m in migrations if m['version'] > current]
        
        if not pending:
            self.logger.info("Database is up to date")
            return
        
        self.logger.info(f"Applying {len(pending)} migrations...")
        
        for migration in pending:
            self.apply_migration(
                migration['version'],
                migration['description'],
                migration['up_sql']
            )
        
        self.logger.info("Migrations completed successfully")
    
    def _get_migrations(self) -> List[Dict]:
        """Get all available migrations"""
        return [
            {
                'version': 1,
                'description': 'Initial schema',
                'up_sql': """
                    -- Initial schema is created by DatabaseManager.initialize()
                    -- This is a placeholder for future migrations
                """
            },
            {
                'version': 2,
                'description': 'Add indexes for performance',
                'up_sql': """
                    CREATE INDEX IF NOT EXISTS idx_tasks_status_created ON tasks(status, created_at);
                    CREATE INDEX IF NOT EXISTS idx_requests_user_status ON user_requests(user_id, status);
                    CREATE INDEX IF NOT EXISTS idx_tasks_requested_by ON tasks(requested_by);
                """
            },
            {
                'version': 3,
                'description': 'Add file_size column to tasks',
                'up_sql': """
                    ALTER TABLE tasks ADD COLUMN file_size INTEGER DEFAULT 0;
                    ALTER TABLE tasks ADD COLUMN download_speed REAL DEFAULT 0;
                    ALTER TABLE user_requests ADD COLUMN notified INTEGER DEFAULT 0;
                """
            },
            {
                'version': 4,
                'description': 'Add failed attempts tracking',
                'up_sql': """
                    ALTER TABLE tasks ADD COLUMN failed_attempts INTEGER DEFAULT 0;
                    ALTER TABLE tasks ADD COLUMN last_error_time TIMESTAMP;
                    CREATE INDEX IF NOT EXISTS idx_tasks_failed ON tasks(failed_attempts);
                """
            },
            {
                'version': 5,
                'description': 'Add channel routing table',
                'up_sql': """
                    CREATE TABLE IF NOT EXISTS channel_routing (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        anime_title TEXT NOT NULL,
                        channel_id INTEGER NOT NULL,
                        created_at TIMESTAMP,
                        updated_at TIMESTAMP,
                        UNIQUE(anime_title, channel_id)
                    );
                    CREATE INDEX IF NOT EXISTS idx_routing_anime ON channel_routing(anime_title);
                """
            }
        ]
    
    def rollback(self, target_version: int = 0):
        """Rollback migrations to target version"""
        current = self.get_current_version()
        
        if target_version >= current:
            self.logger.info("Nothing to rollback")
            return
        
        migrations = self._get_migrations()
        to_rollback = [m for m in migrations if m['version'] > target_version]
        to_rollback.reverse()
        
        self.logger.info(f"Rolling back {len(to_rollback)} migrations...")
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            for migration in to_rollback:
                try:
                    if 'down_sql' in migration:
                        cursor.executescript(migration['down_sql'])
                    
                    cursor.execute("DELETE FROM schema_migrations WHERE version = ?", 
                                 (migration['version'],))
                    conn.commit()
                    self.logger.info(f"Rolled back v{migration['version']}")
                    
                except Exception as e:
                    conn.rollback()
                    self.logger.error(f"Rollback failed for v{migration['version']}: {e}")
                    raise
        
        self.logger.info("Rollback completed")
    
    def repair(self):
        """Repair migration state"""
        self.logger.info("Repairing migration state...")
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Get actual applied migrations from schema
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            # Check if core tables exist
            required_tables = ['tasks', 'user_requests', 'admins', 'config']
            missing_tables = [t for t in required_tables if t not in tables]
            
            if missing_tables:
                self.logger.warning(f"Missing tables: {missing_tables}")
                # Reinitialize database
                from bot.database.database import DatabaseManager
                db_manager = DatabaseManager(self.db_path)
                # This would need to be called with await in async context
                self.logger.info("Please reinitialize the database")
    
    def get_migration_status(self) -> Dict:
        """Get migration status"""
        current = self.get_current_version()
        migrations = self._get_migrations()
        latest = migrations[-1]['version'] if migrations else 0
        
        return {
            'current_version': current,
            'latest_version': latest,
            'is_latest': current >= latest,
            'pending_count': latest - current,
            'applied_migrations': self.get_applied_migrations(),
            'available_migrations': len(migrations)
        }
    
    def export_schema(self, output_path: Path) -> bool:
        """Export current database schema"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT sql FROM sqlite_master WHERE type='table'")
                schemas = cursor.fetchall()
                
                with open(output_path, 'w') as f:
                    f.write("-- Database Schema Export\n")
                    f.write(f"-- Generated: {datetime.now().isoformat()}\n\n")
                    
                    for schema in schemas:
                        if schema[0]:
                            f.write(f"{schema[0]};\n\n")
                
                self.logger.info(f"Schema exported to {output_path}")
                return True
                
        except Exception as e:
            self.logger.error(f"Schema export failed: {e}")
            return False"""
Database Migration Manager for ✦ ＡＵＴＯ ＡＮＩＭＥ ✦
Handles schema migrations and version updates
"""

import sqlite3
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

from bot.utils.logger import setup_logger


class MigrationManager:
    """Manages database schema migrations"""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.logger = setup_logger("migrations")
        self._ensure_migrations_table()
    
    def _ensure_migrations_table(self):
        """Create migrations tracking table if not exists"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version INTEGER PRIMARY KEY,
                    applied_at TIMESTAMP,
                    description TEXT
                )
            """)
            conn.commit()
    
    def get_current_version(self) -> int:
        """Get current schema version"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT MAX(version) FROM schema_migrations")
            result = cursor.fetchone()[0]
            return result or 0
    
    def get_applied_migrations(self) -> List[Dict]:
        """Get list of applied migrations"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM schema_migrations ORDER BY version")
            rows = cursor.fetchall()
            return [
                {'version': row[0], 'applied_at': row[1], 'description': row[2]}
                for row in rows
            ]
    
    def apply_migration(self, version: int, description: str, up_sql: str):
        """Apply a migration"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            try:
                # Execute migration
                cursor.executescript(up_sql)
                
                # Record migration
                cursor.execute("""
                    INSERT INTO schema_migrations (version, applied_at, description)
                    VALUES (?, ?, ?)
                """, (version, datetime.now().isoformat(), description))
                
                conn.commit()
                self.logger.info(f"Applied migration v{version}: {description}")
                return True
                
            except Exception as e:
                conn.rollback()
                self.logger.error(f"Migration v{version} failed: {e}")
                raise
    
    def migrate_to_latest(self):
        """Migrate database to latest version"""
        current = self.get_current_version()
        
        migrations = self._get_migrations()
        pending = [m for m in migrations if m['version'] > current]
        
        if not pending:
            self.logger.info("Database is up to date")
            return
        
        self.logger.info(f"Applying {len(pending)} migrations...")
        
        for migration in pending:
            self.apply_migration(
                migration['version'],
                migration['description'],
                migration['up_sql']
            )
        
        self.logger.info("Migrations completed successfully")
    
    def _get_migrations(self) -> List[Dict]:
        """Get all available migrations"""
        return [
            {
                'version': 1,
                'description': 'Initial schema',
                'up_sql': """
                    -- Initial schema is created by DatabaseManager.initialize()
                    -- This is a placeholder for future migrations
                """
            },
            {
                'version': 2,
                'description': 'Add indexes for performance',
                'up_sql': """
                    CREATE INDEX IF NOT EXISTS idx_tasks_status_created ON tasks(status, created_at);
                    CREATE INDEX IF NOT EXISTS idx_requests_user_status ON user_requests(user_id, status);
                    CREATE INDEX IF NOT EXISTS idx_tasks_requested_by ON tasks(requested_by);
                """
            },
            {
                'version': 3,
                'description': 'Add file_size column to tasks',
                'up_sql': """
                    ALTER TABLE tasks ADD COLUMN file_size INTEGER DEFAULT 0;
                    ALTER TABLE tasks ADD COLUMN download_speed REAL DEFAULT 0;
                    ALTER TABLE user_requests ADD COLUMN notified INTEGER DEFAULT 0;
                """
            },
            {
                'version': 4,
                'description': 'Add failed attempts tracking',
                'up_sql': """
                    ALTER TABLE tasks ADD COLUMN failed_attempts INTEGER DEFAULT 0;
                    ALTER TABLE tasks ADD COLUMN last_error_time TIMESTAMP;
                    CREATE INDEX IF NOT EXISTS idx_tasks_failed ON tasks(failed_attempts);
                """
            },
            {
                'version': 5,
                'description': 'Add channel routing table',
                'up_sql': """
                    CREATE TABLE IF NOT EXISTS channel_routing (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        anime_title TEXT NOT NULL,
                        channel_id INTEGER NOT NULL,
                        created_at TIMESTAMP,
                        updated_at TIMESTAMP,
                        UNIQUE(anime_title, channel_id)
                    );
                    CREATE INDEX IF NOT EXISTS idx_routing_anime ON channel_routing(anime_title);
                """
            }
        ]
    
    def rollback(self, target_version: int = 0):
        """Rollback migrations to target version"""
        current = self.get_current_version()
        
        if target_version >= current:
            self.logger.info("Nothing to rollback")
            return
        
        migrations = self._get_migrations()
        to_rollback = [m for m in migrations if m['version'] > target_version]
        to_rollback.reverse()
        
        self.logger.info(f"Rolling back {len(to_rollback)} migrations...")
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            for migration in to_rollback:
                try:
                    if 'down_sql' in migration:
                        cursor.executescript(migration['down_sql'])
                    
                    cursor.execute("DELETE FROM schema_migrations WHERE version = ?", 
                                 (migration['version'],))
                    conn.commit()
                    self.logger.info(f"Rolled back v{migration['version']}")
                    
                except Exception as e:
                    conn.rollback()
                    self.logger.error(f"Rollback failed for v{migration['version']}: {e}")
                    raise
        
        self.logger.info("Rollback completed")
    
    def repair(self):
        """Repair migration state"""
        self.logger.info("Repairing migration state...")
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Get actual applied migrations from schema
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            # Check if core tables exist
            required_tables = ['tasks', 'user_requests', 'admins', 'config']
            missing_tables = [t for t in required_tables if t not in tables]
            
            if missing_tables:
                self.logger.warning(f"Missing tables: {missing_tables}")
                # Reinitialize database
                from bot.database.database import DatabaseManager
                db_manager = DatabaseManager(self.db_path)
                # This would need to be called with await in async context
                self.logger.info("Please reinitialize the database")
    
    def get_migration_status(self) -> Dict:
        """Get migration status"""
        current = self.get_current_version()
        migrations = self._get_migrations()
        latest = migrations[-1]['version'] if migrations else 0
        
        return {
            'current_version': current,
            'latest_version': latest,
            'is_latest': current >= latest,
            'pending_count': latest - current,
            'applied_migrations': self.get_applied_migrations(),
            'available_migrations': len(migrations)
        }
    
    def export_schema(self, output_path: Path) -> bool:
        """Export current database schema"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT sql FROM sqlite_master WHERE type='table'")
                schemas = cursor.fetchall()
                
                with open(output_path, 'w') as f:
                    f.write("-- Database Schema Export\n")
                    f.write(f"-- Generated: {datetime.now().isoformat()}\n\n")
                    
                    for schema in schemas:
                        if schema[0]:
                            f.write(f"{schema[0]};\n\n")
                
                self.logger.info(f"Schema exported to {output_path}")
                return True
                
        except Exception as e:
            self.logger.error(f"Schema export failed: {e}")
            return False
