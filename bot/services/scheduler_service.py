"""
Scheduler Service for ✦ ＡＵＴＯ ＡＮＩＭＥ ✦
Manages cron jobs and scheduled tasks
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional, Callable, Any
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.jobstores.base import JobLookupError

from bot.config import Config
from bot.database.database import DatabaseManager
from bot.database.models import RequestStatus, TaskStatus, AnimeTask
from bot.utils.logger import setup_logger
from bot.utils.helpers import generate_task_id


class SchedulerService:
    """Service for managing scheduled tasks"""

    def __init__(self, application, db_manager: DatabaseManager):
        self.application = application
        self.db_manager = db_manager
        self.logger = setup_logger("scheduler")
        self.scheduler = AsyncIOScheduler(timezone=Config.TIMEZONE)
        self.is_running = False

    async def initialize(self):
        """Initialize and start the scheduler"""
        self.logger.info("Initializing scheduler service...")
        await self._load_jobs()
        self.scheduler.start()
        self.is_running = True
        self.logger.info("✅ Scheduler service initialized")

    async def _load_jobs(self):
        """Load all scheduled jobs"""
        request_time = await self.db_manager.get_config('request_time', Config.REQUEST_TIME)
        hour, minute = map(int, request_time.split(':'))

        self.scheduler.add_job(
            self.process_daily_requests,
            trigger=CronTrigger(hour=hour, minute=minute),
            id='daily_request_processing',
            name='Process daily user requests',
            replace_existing=True
        )
        self.logger.info(f"📅 Daily request processing scheduled at {request_time} IST")

        cleanup_hours = int(await self.db_manager.get_config('cleanup_hours', str(Config.CLEANUP_HOURS)))
        self.scheduler.add_job(
            self.cleanup_storage,
            trigger=IntervalTrigger(hours=cleanup_hours),
            id='storage_cleanup',
            name='Clean up old files',
            replace_existing=True
        )
        self.logger.info(f"🗑️ Storage cleanup scheduled every {cleanup_hours} hours")

        self.scheduler.add_job(
            self.backup_database,
            trigger=CronTrigger(hour=3, minute=0),
            id='database_backup',
            name='Backup database',
            replace_existing=True
        )
        self.logger.info("💾 Database backup scheduled daily at 3:00 AM")

        self.scheduler.add_job(
            self.fetch_airing_schedule,
            trigger=IntervalTrigger(hours=6),
            id='airing_fetch',
            name='Fetch airing schedule',
            replace_existing=True
        )
        self.logger.info("📺 Airing schedule fetch scheduled every 6 hours")

        self.scheduler.add_job(
            self.health_check,
            trigger=IntervalTrigger(minutes=30),
            id='health_check',
            name='Bot health check',
            replace_existing=True
        )
        self.logger.info("❤️ Health check scheduled every 30 minutes")

        self.scheduler.add_job(
            self.update_stats,
            trigger=IntervalTrigger(hours=1),
            id='stats_update',
            name='Update bot statistics',
            replace_existing=True
        )
        self.logger.info("📊 Stats update scheduled every hour")

    async def process_daily_requests(self):
        """Process all pending user requests"""
        self.logger.info("📋 Processing daily requests...")
        try:
            pending_requests = await self.db_manager.get_pending_requests()
            if not pending_requests:
                self.logger.info("No pending requests to process")
                return
            self.logger.info(f"Found {len(pending_requests)} pending requests")

            auto_approve = await self.db_manager.get_config('auto_approve_requests', 'false')

            if auto_approve == 'true':
                for req in pending_requests:
                    task = AnimeTask(
                        task_id=generate_task_id(),
                        title=req['anime_title'],
                        episode=req.get('episode') or 1,
                        quality=req.get('quality') or "720p",
                        status=TaskStatus.PENDING,
                        requested_by=req['user_id']
                    )
                    await self.db_manager.add_task(task)
                    await self.db_manager.update_request_status(
                        req['request_id'],
                        RequestStatus.PROCESSING,
                        task.task_id
                    )
                self.logger.info(f"Auto-approved {len(pending_requests)} requests")
            else:
                await self._notify_admins_pending_requests(pending_requests)

        except Exception as e:
            self.logger.error(f"Daily request processing failed: {e}")

    async def cleanup_storage(self):
        """Clean up old files and free disk space"""
        self.logger.info("🧹 Running storage cleanup...")
        try:
            cleanup_hours = int(await self.db_manager.get_config('cleanup_hours', str(Config.CLEANUP_HOURS)))
            cutoff_time = datetime.now() - timedelta(hours=cleanup_hours)

            dl_deleted = proc_deleted = temp_deleted = 0
            for path, name in [
                (Config.DOWNLOAD_PATH, 'download'),
                (Config.PROCESSED_PATH, 'processed'),
                (Config.TEMP_PATH, 'temp')
            ]:
                if path.exists():
                    for file_path in path.glob("*"):
                        if file_path.is_file():
                            mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                            if mtime < cutoff_time:
                                file_path.unlink()
                                if name == 'download':
                                    dl_deleted += 1
                                elif name == 'processed':
                                    proc_deleted += 1
                                else:
                                    temp_deleted += 1

            tasks_deleted = await self.db_manager.delete_old_tasks(days=30)
            self.logger.info(
                f"✅ Cleanup: dl={dl_deleted}, proc={proc_deleted}, temp={temp_deleted}, tasks={tasks_deleted}"
            )
            await self.db_manager.set_config('last_cleanup', datetime.now().isoformat())

        except Exception as e:
            self.logger.error(f"Storage cleanup failed: {e}")

    async def backup_database(self):
        """Create database backup"""
        self.logger.info("💾 Creating database backup...")
        try:
            backup_dir = Config.BASE_DIR / "data" / "backups"
            backup_dir.mkdir(parents=True, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = backup_dir / f"auto_backup_{ts}.db"
            success = await self.db_manager.backup(backup_path)
            if success:
                for backup in backup_dir.glob("auto_backup_*.db"):
                    if backup != backup_path:
                        age = datetime.now() - datetime.fromtimestamp(backup.stat().st_mtime)
                        if age.days > 7:
                            backup.unlink()
                self.logger.info(f"✅ Database backed up: {backup_path}")
            else:
                self.logger.error("Database backup failed")
        except Exception as e:
            self.logger.error(f"Backup failed: {e}")

    async def fetch_airing_schedule(self):
        """Fetch and cache airing schedule"""
        self.logger.info("📺 Fetching airing schedule...")
        try:
            from bot.services.anilist_service import AniListService
            anilist = AniListService()
            airing = await anilist.get_airing_schedule()
            for anime in airing:
                await self.db_manager.cache_airing_anime(anime['id'], anime)
            self.logger.info(f"✅ Cached {len(airing)} airing anime")
            if airing:
                await self._notify_new_episodes(airing)
        except Exception as e:
            self.logger.error(f"Failed to fetch airing schedule: {e}")

    async def health_check(self):
        """Perform health check on the bot"""
        self.logger.info("❤️ Running health check...")
        try:
            await self.db_manager.get_config('bot_version')
            active_tasks = await self.db_manager.get_active_tasks()
            stuck_threshold = datetime.now() - timedelta(hours=2)
            stuck_tasks = [
                t.task_id for t in active_tasks
                if t.started_at and t.started_at < stuck_threshold
            ]
            if stuck_tasks:
                self.logger.warning(f"Found {len(stuck_tasks)} stuck tasks: {stuck_tasks}")
                await self._notify_stuck_tasks(stuck_tasks)

            import shutil
            disk_usage = shutil.disk_usage(Config.BASE_DIR)
            free_gb = disk_usage.free / (1024 ** 3)
            if free_gb < Config.CLEANUP_THRESHOLD_GB:
                self.logger.warning(f"Low disk space: {free_gb:.1f} GB free")
                await self._notify_low_disk_space(free_gb)

            self.logger.info("✅ Health check passed")
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")

    async def update_stats(self):
        """Update bot statistics"""
        self.logger.info("📊 Updating bot statistics...")
        try:
            stats = await self.db_manager.get_detailed_stats()
            self.logger.info(f"Stats updated: {stats.total_tasks} tasks, {stats.total_users} users")
        except Exception as e:
            self.logger.error(f"Stats update failed: {e}")

    async def _notify_admins_pending_requests(self, requests: list):
        from bot.core.uploader import Uploader
        uploader = Uploader(self.db_manager)
        message = (
            f"📋 <b>Pending Requests Notification</b>\n\n"
            f"There are <b>{len(requests)}</b> pending requests waiting for approval.\n\n"
            f"<b>Recent:</b>\n"
        )
        for req in requests[:5]:
            message += f"• #{req['request_id']} — {req['anime_title']} (User: {req['user_id']})\n"
        if len(requests) > 5:
            message += f"\n... and {len(requests) - 5} more"
        message += f"\n\nUse <code>/view_requests</code> to manage.\n\n{Config.FOOTER}"
        await uploader.send_admin_log(message)

    async def _notify_new_episodes(self, airing_list: list):
        from bot.core.uploader import Uploader
        uploader = Uploader(self.db_manager)
        today_episodes = [
            a for a in airing_list
            if datetime.fromtimestamp(a.get('airing_at', 0)).date() == datetime.now().date()
        ]
        if today_episodes:
            message = "🎬 <b>New Episodes Airing Today!</b>\n\n"
            for a in today_episodes:
                message += f"• <b>{a.get('title', 'Unknown')}</b> — Episode {a.get('episode', '?')}\n"
            message += f"\n{Config.FOOTER}"
            await uploader.send_admin_log(message)

    async def _notify_stuck_tasks(self, task_ids: list):
        from bot.core.uploader import Uploader
        uploader = Uploader(self.db_manager)
        message = (
            f"⚠️ <b>Stuck Tasks Detected</b>\n\n"
            f"These tasks have been stuck for over 2 hours:\n\n"
        )
        for task_id in task_ids:
            message += f"• <code>{task_id}</code>\n"
        message += f"\nUse <code>/redownload &lt;task_id&gt;</code> to retry.\n\n{Config.FOOTER}"
        await uploader.send_admin_log(message)

    async def _notify_low_disk_space(self, free_gb: float):
        from bot.core.uploader import Uploader
        uploader = Uploader(self.db_manager)
        message = (
            f"⚠️ <b>Low Disk Space Warning</b>\n\n"
            f"Free space: <b>{free_gb:.1f} GB</b>\n"
            f"Threshold: <b>{Config.CLEANUP_THRESHOLD_GB} GB</b>\n\n"
            f"Use <code>/cleanup</code> to free space.\n\n{Config.FOOTER}"
        )
        await uploader.send_admin_log(message)

    async def shutdown(self):
        self.logger.info("Shutting down scheduler...")
        self.scheduler.shutdown(wait=False)
        self.is_running = False
        self.logger.info("✅ Scheduler shutdown complete")

    def get_jobs(self) -> list:
        return self.scheduler.get_jobs()

    def pause_job(self, job_id: str) -> bool:
        try:
            self.scheduler.pause_job(job_id)
            return True
        except JobLookupError:
            return False

    def resume_job(self, job_id: str) -> bool:
        try:
            self.scheduler.resume_job(job_id)
            return True
        except JobLookupError:
            return False

    def add_custom_job(self, func: Callable, trigger: Any, job_id: str, **kwargs):
        self.scheduler.add_job(func, trigger, id=job_id, **kwargs)
        self.logger.info(f"Added custom job: {job_id}")
