"""
Main Pipeline Controller for ✦ ＡＵＴＯ ＡＮＩＭＥ ✦
Manages the complete media lifecycle: FETCH → DOWNLOAD → PROCESS → UPLOAD → POST
"""

import asyncio
import uuid
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum

from bot.config import Config
from bot.database.database import DatabaseManager
from bot.database.models import AnimeTask, TaskStatus
from bot.core.fetcher import Fetcher
from bot.core.downloader import Downloader
from bot.core.processor import Processor
from bot.core.uploader import Uploader
from bot.core.poster import Poster
from bot.utils.logger import setup_logger
from bot.utils.helpers import generate_task_id


class PipelineStage(Enum):
    """Pipeline execution stages"""
    FETCH = "fetch"
    DOWNLOAD = "download"
    PROCESS = "process"
    UPLOAD = "upload"
    POST = "post"
    COMPLETE = "complete"


class Pipeline:
    """Main pipeline controller for media processing"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.logger = setup_logger("pipeline")
        
        # Initialize pipeline components
        self.fetcher = Fetcher(db_manager)
        self.downloader = Downloader(db_manager)
        self.processor = Processor(db_manager)
        self.uploader = Uploader(db_manager)
        self.poster = Poster(db_manager)
        
        # Active tasks tracking
        self.active_tasks: Dict[str, AnimeTask] = {}
        self.task_queue: asyncio.Queue = asyncio.Queue()
        
        # Worker tasks
        self.workers: List[asyncio.Task] = []
        self.is_running = False
    
    async def start(self):
        """Start the pipeline workers"""
        self.is_running = True
        self.logger.info("🚀 Starting pipeline workers...")
        
        # Start queue processor workers
        for i in range(Config.MAX_CONCURRENT_DOWNLOADS):
            worker = asyncio.create_task(self._process_queue_worker(i))
            self.workers.append(worker)
        
        # Start scheduler for pending tasks
        self.workers.append(asyncio.create_task(self._pending_task_monitor()))
        
        self.logger.info(f"✅ Started {len(self.workers)} pipeline workers")
    
    async def stop(self):
        """Stop all pipeline workers"""
        self.is_running = False
        self.logger.info("🛑 Stopping pipeline workers...")
        
        for worker in self.workers:
            worker.cancel()
        
        await asyncio.gather(*self.workers, return_exceptions=True)
        self.workers.clear()
        self.logger.info("✅ Pipeline workers stopped")
    
    async def add_task(self, task: AnimeTask) -> bool:
        """Add a task to the processing queue"""
        await self.db_manager.add_task(task)
        await self.task_queue.put(task)
        self.logger.info(f"📋 Task added to queue: {task.task_id} - {task.title} EP{task.episode}")
        return True
    
    async def _process_queue_worker(self, worker_id: int):
        """Worker to process tasks from queue"""
        self.logger.info(f"🔧 Worker {worker_id} started")
        
        while self.is_running:
            try:
                # Get task from queue with timeout
                task = await asyncio.wait_for(self.task_queue.get(), timeout=5.0)
                
                if task is None:
                    continue
                
                self.logger.info(f"👷 Worker {worker_id} processing: {task.task_id}")
                self.active_tasks[task.task_id] = task
                
                # Execute pipeline
                result = await self._execute_pipeline(task)
                
                # Remove from active tasks
                self.active_tasks.pop(task.task_id, None)
                self.task_queue.task_done()
                
                if result:
                    self.logger.info(f"✅ Worker {worker_id} completed: {task.task_id}")
                else:
                    self.logger.error(f"❌ Worker {worker_id} failed: {task.task_id}")
                    
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Worker {worker_id} error: {e}")
                await asyncio.sleep(1)
    
    async def _execute_pipeline(self, task: AnimeTask) -> bool:
        """Execute full pipeline for a task"""
        try:
            # Stage 1: FETCH
            self.logger.info(f"📡 Stage 1 - FETCH: {task.task_id}")
            await self.db_manager.update_task_status(task.task_id, TaskStatus.FETCHING)
            
            fetch_result = await self.fetcher.fetch(task)
            if not fetch_result:
                raise Exception("Failed to fetch source")
            task.source_url = fetch_result.get('url')
            task.metadata = fetch_result.get('metadata', {})
            
            # Stage 2: DOWNLOAD
            self.logger.info(f"⬇️ Stage 2 - DOWNLOAD: {task.task_id}")
            await self.db_manager.update_task_status(task.task_id, TaskStatus.DOWNLOADING)
            
            download_result = await self.downloader.download(task)
            if not download_result:
                raise Exception("Failed to download")
            task.file_path = download_result.get('file_path')
            
            # Stage 3: PROCESS
            self.logger.info(f"⚙️ Stage 3 - PROCESS: {task.task_id}")
            await self.db_manager.update_task_status(task.task_id, TaskStatus.PROCESSING)
            
            process_result = await self.processor.process(task)
            if not process_result:
                raise Exception("Failed to process")
            task.processed_paths = process_result.get('processed_paths', {})
            
            # Stage 4: UPLOAD
            self.logger.info(f"📤 Stage 4 - UPLOAD: {task.task_id}")
            await self.db_manager.update_task_status(task.task_id, TaskStatus.UPLOADING)
            
            upload_result = await self.uploader.upload(task)
            if not upload_result:
                raise Exception("Failed to upload")
            task.telegram_message_ids = upload_result.get('message_ids', {})
            
            # Stage 5: POST
            self.logger.info(f"📝 Stage 5 - POST: {task.task_id}")
            post_result = await self.poster.post(task)
            if not post_result:
                raise Exception("Failed to post")
            
            # Mark as completed
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now()
            await self.db_manager.add_task(task)
            
            # Cleanup
            await self._cleanup_task_files(task)
            
            self.logger.info(f"🎉 Pipeline complete: {task.task_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Pipeline error for {task.task_id}: {e}")
            task.status = TaskStatus.FAILED
            task.error_log = str(e)
            await self.db_manager.add_task(task)
            return False
    
    async def _pending_task_monitor(self):
        """Monitor and add pending tasks from database"""
        self.logger.info("📊 Pending task monitor started")
        
        while self.is_running:
            try:
                # Get pending tasks from database
                pending_tasks = await self.db_manager.get_pending_tasks(limit=10)
                
                for task in pending_tasks:
                    # Check if already in queue or active
                    if task.task_id in self.active_tasks:
                        continue
                    
                    # Check if already in queue
                    in_queue = False
                    for q_item in list(self.task_queue._queue):
                        if hasattr(q_item, 'task_id') and q_item.task_id == task.task_id:
                            in_queue = True
                            break
                    
                    if not in_queue:
                        await self.task_queue.put(task)
                        self.logger.info(f"📋 Added pending task to queue: {task.task_id}")
                
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Pending task monitor error: {e}")
                await asyncio.sleep(60)
    
    async def _cleanup_task_files(self, task: AnimeTask):
        """Cleanup temporary files after successful processing"""
        try:
            # Remove source file
            if task.file_path and task.file_path.exists():
                task.file_path.unlink()
                self.logger.debug(f"Removed source file: {task.file_path}")
            
            # Schedule cleanup for processed files after upload delay
            async def delayed_cleanup():
                await asyncio.sleep(3600)  # 1 hour delay
                for quality, path in task.processed_paths.items():
                    if path and path.exists():
                        path.unlink()
                        self.logger.debug(f"Removed processed file: {path}")
            
            asyncio.create_task(delayed_cleanup())
            
        except Exception as e:
            self.logger.warning(f"Cleanup error for {task.task_id}: {e}")
    
    async def get_queue_status(self) -> Dict[str, Any]:
        """Get current queue status"""
        return {
            'active_tasks': len(self.active_tasks),
            'queue_size': self.task_queue.qsize(),
            'workers': len(self.workers),
            'is_running': self.is_running,
            'tasks': [
                {
                    'task_id': t.task_id,
                    'title': t.title,
                    'episode': t.episode,
                    'status': t.status.value,
                    'progress': getattr(t, 'progress', 0)
                }
                for t in self.active_tasks.values()
            ]
          }
