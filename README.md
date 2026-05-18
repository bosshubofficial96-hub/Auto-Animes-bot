# ✦ ＡＵＴＯ ＡＮＩＭＥ ✦

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.8+-blue.svg">
  <img src="https://img.shields.io/badge/Telegram-Bot-blue.svg">
  <img src="https://img.shields.io/badge/License-MIT-green.svg">
  <img src="https://img.shields.io/badge/Version-2.0.0-orange.svg">
  <img src="https://img.shields.io/badge/Docker-Ready-brightgreen.svg">
  <img src="https://img.shields.io/badge/FFmpeg-Required-red.svg">
</p>

<p align="center">
  <strong>🚀 Enterprise-Grade Automated Anime Media Management Bot for Telegram</strong><br>
  <strong>Fetch → Download → Process → Upload → Post | Fully Automated | 24/7 Operation</strong>
</p>

<p align="center">
  <img src="https://raw.githubusercontent.com/BOSSHUB/auto-anime-bot/main/assets/demo.gif" alt="Demo" width="600">
</p>

<p align="center">
  🤩 POWERED BY: BOSSHUB— BOTZ & 𝐁𝐨𝐬𝐬𝐡𝐮𝐛 😁
</p>

---

## 📋 Table of Contents

- [✨ Features](#-features)
- [📊 System Architecture](#-system-architecture)
- [🚀 Quick Deployment](#-quick-deployment)
- [📦 Deployment Methods](#-deployment-methods)
- [⚙️ Configuration](#️-configuration)
- [📋 Commands](#-commands)
- [🎯 Pipeline Stages](#-pipeline-stages)
- [🔧 Performance Tuning](#-performance-tuning)
- [📈 Monitoring & Logging](#-monitoring--logging)
- [🐛 Troubleshooting](#-troubleshooting)
- [🔒 Security](#-security)
- [🔄 Backup & Recovery](#-backup--recovery)
- [📊 Database Schema](#-database-schema)
- [🤝 Contributing](#-contributing)
- [📝 License](#-license)
- [🙏 Acknowledgments](#-acknowledgments)

---

## ✨ Features

### 🎯 Core Features
| Feature | Description |
|---------|-------------|
| **🔄 Automated Pipeline** | Complete media lifecycle: FETCH → DOWNLOAD → PROCESS → UPLOAD → POST |
| **🎯 Triple Quality Output** | 480p, 720p, 1080p using HEVC/H.265 encoding for optimal compression |
| **📝 Smart Request System** | User requests with admin approval workflow and priority queue |
| **⏰ Scheduled Processing** | Daily cron jobs in IST timezone with configurable execution time |
| **📡 Multi-Channel Routing** | Route different anime titles to different Telegram channels |
| **⚡ High Performance** | 600-700 KB/s sustained download speeds with parallel processing |
| **🧹 Auto Cleanup** | Configurable file retention policies with automatic disk space management |
| **🛡️ 24/7 Operation** | Robust error handling, auto-retry, and health monitoring |

### 🔧 Advanced Features
| Feature | Description |
|---------|-------------|
| **🔐 Multi-Level Admin** | Role-based access control with granular permissions |
| **💾 Automatic Backups** | Daily database backups with 7-day retention policy |
| **📊 Real-time Stats** | Prometheus metrics + Grafana dashboards |
| **🐳 Docker Support** | Easy deployment with Docker Compose and multiple profiles |
| **🔄 Auto-Retry** | Failed tasks automatically retry with exponential backoff |
| **📱 Mobile Optimized** | Streamable videos with Telegram's native streaming support |
| **🎨 Rich Formatting** | HTML/Markdown captions with anime metadata, ratings, and genres |
| **🌐 Multi-API Support** | AniList, MyAnimeList (Jikan), and extensible API architecture |
| **🗄️ Database Options** | SQLite (default), PostgreSQL (production), Redis caching |
| **📡 Webhook Support** | Production-ready webhook mode with SSL/TLS |

### 📊 Performance Metrics
| Metric | Value |
|--------|-------|
| Download Speed | 600-700 KB/s average |
| Processing Time | 5-10 minutes per episode |
| Concurrent Downloads | 3 (configurable) |
| Concurrent Uploads | 2 (configurable) |
| Uptime | 99.9% with auto-restart |
| Response Time | < 1 second for commands |
| Database Size | ~10MB per 1000 tasks |

---

## 📊 System Architecture

```

┌─────────────────────────────────────────────────────────────────────────────┐
│                              TELEGRAM USERS                                  │
│                    /request, /latest, /airing, /search                      │
└─────────────────────────────────────────────────────────────────────────────┘
│
▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         ✦ ＡＵＴＯ ＡＮＩＭＥ ✦ BOT                             │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐   │
│  │  FETCH   │ → │ DOWNLOAD │ → │ PROCESS  │ → │ UPLOAD   │ → │  POST    │   │
│  │  ──────  │   │ ──────── │   │ ──────── │   │ ──────── │   │ ──────── │   │
│  │ AniList  │   │ 600KB/s  │   │ HEVC/H.265│   │ Telegram │   │ Channel  │   │
│  │ Jikan    │   │ Multi-   │   │ 480p     │   │ Streaming│   │ HTML     │   │
│  │ Simkl    │   │ Thread   │   │ 720p     │   │ Upload   │   │ Markdown │   │
│  │ RSS      │   │ Queue    │   │ 1080p    │   │ Retry    │   │ Metadata │   │
│  └──────────┘   └──────────┘   └──────────┘   └──────────┘   └──────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
│
┌──────────────────┼──────────────────┐
▼                  ▼                  ▼
┌───────────────┐  ┌───────────────┐  ┌───────────────┐
│    SQLite     │  │     Redis     │  │  PostgreSQL   │
│   Database    │  │  Task Queue   │  │ (Production)  │
├───────────────┤  ├───────────────┤  ├───────────────┤
│ • Tasks       │  │ • Job Queue   │  │ • Tasks       │
│ • Requests    │  │ • Cache       │  │ • Requests    │
│ • Users       │  │ • Sessions    │  │ • Analytics   │
│ • Config      │  │ • Rate Limits │  │ • Audit Logs  │
└───────────────┘  └───────────────┘  └───────────────┘
│                  │                  │
└──────────────────┼──────────────────┘
▼
┌───────────────────┐
│    Prometheus     │
│   + Grafana       │
│   Monitoring      │
└───────────────────┘

```

---

## 🚀 Quick Deployment

### Prerequisites
- ✅ Python 3.8 or higher
- ✅ FFmpeg installed on system
- ✅ Telegram Bot Token (from [@BotFather](https://t.me/BotFather))
- ✅ Telegram Channel (for posting content, must add bot as admin)
- ✅ Minimum 2GB RAM (4GB recommended for 1080p processing)

### One-Click Deploy (Linux/Mac)

```bash
# Clone repository
git clone https://github.com/BOSSHUB/auto-anime-bot.git
cd auto-anime-bot

# Run automated setup
chmod +x scripts/setup.sh
./scripts/setup.sh

# Edit configuration
nano .env

# Start bot
./scripts/start.sh
```

Windows Deployment

```powershell
# Clone repository
git clone https://github.com/BOSSHUB/auto-anime-bot.git
cd auto-anime-bot

# Create virtual environment
python -m venv venv
.\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy and edit .env file
copy .env.example .env
notepad .env

# Run bot
python -m bot.main
```

---

📦 Deployment Methods

Method 1: Local Deployment (Ubuntu/Debian)

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y python3 python3-pip python3-venv ffmpeg git

# Clone repository
git clone https://github.com/BOSSHUB/auto-anime-bot.git
cd auto-anime-bot

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Configure environment
cp .env.example .env
nano .env  # Add your BOT_TOKEN, DEFAULT_CHANNEL, ADMIN_IDS

# Create required directories
mkdir -p data/{downloads,processed,temp,logs,backups,config}

# Initialize database
python -c "from bot.database.database import DatabaseManager; from bot.config import Config; import asyncio; asyncio.run(DatabaseManager(Config.DATABASE_PATH).initialize())"

# Run bot
python -m bot.main

# To run in background:
nohup python -m bot.main > bot.log 2>&1 &
```

Method 2: Docker Deployment (Recommended)

```bash
# Clone repository
git clone https://github.com/BOSSHUB/auto-anime-bot.git
cd auto-anime-bot

# Configure environment
cp .env.example .env
nano .env  # Add your BOT_TOKEN, DEFAULT_CHANNEL, ADMIN_IDS

# Build and start with Docker Compose
docker-compose up -d --build

# View logs
docker-compose logs -f auto-anime-bot

# Check status
docker-compose ps

# Stop bot
docker-compose down

# Stop and remove volumes (clean start)
docker-compose down -v
```

Method 3: Docker with Full Monitoring Stack

```bash
# Start with all services (Redis + Prometheus + Grafana)
docker-compose --profile monitoring up -d

# Access services:
# - Bot: Telegram
# - Redis: localhost:6379
# - Prometheus: http://localhost:9090
# - Grafana: http://localhost:3000 (admin/admin)

# View all logs
docker-compose logs -f
```

Method 4: Production Deployment (PostgreSQL + Redis)

```bash
# Start with production database
docker-compose --profile with-postgres up -d

# Run database migrations
docker-compose exec auto-anime-bot python scripts/migrate.py

# Create admin user
docker-compose exec auto-anime-bot python scripts/create_admin.py --user-id 123456789

# Backup database
docker-compose exec postgres pg_dump -U auto_anime auto_anime > backup.sql
```

Method 5: Systemd Service (Linux Production)

```bash
# Create systemd service file
sudo nano /etc/systemd/system/auto-anime-bot.service
```

```ini
[Unit]
Description=Auto Anime Bot Service
After=network.target network-online.target
Wants=network-online.target

[Service]
Type=simple
User=ubuntu
Group=ubuntu
WorkingDirectory=/home/ubuntu/auto-anime-bot
Environment="PATH=/home/ubuntu/auto-anime-bot/venv/bin"
Environment="PYTHONPATH=/home/ubuntu/auto-anime-bot"
ExecStart=/home/ubuntu/auto-anime-bot/venv/bin/python -m bot.main
ExecReload=/bin/kill -HUP $MAINPID
Restart=always
RestartSec=10
StartLimitInterval=300
StartLimitBurst=5

# Security hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/home/ubuntu/auto-anime-bot/data

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable auto-anime-bot
sudo systemctl start auto-anime-bot
sudo systemctl status auto-anime-bot

# View logs
sudo journalctl -u auto-anime-bot -f
```

Method 6: Heroku Deployment

```bash
# Install Heroku CLI
curl https://cli-assets.heroku.com/install.sh | sh

# Login to Heroku
heroku login

# Create Heroku app
heroku create auto-anime-bot-$(openssl rand -hex 4)

# Add buildpacks
heroku buildpacks:add heroku/python
heroku buildpacks:add https://github.com/jonathanong/heroku-buildpack-ffmpeg-latest.git

# Set environment variables
heroku config:set BOT_TOKEN=your_bot_token
heroku config:set DEFAULT_CHANNEL=-1001234567890
heroku config:set ADMIN_LOG_CHANNEL=-1001234567890
heroku config:set ADMIN_IDS=123456789

# Deploy
git push heroku main

# Scale dyno
heroku ps:scale worker=1

# View logs
heroku logs --tail
```

Method 7: Kubernetes Deployment

```yaml
# k8s-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: auto-anime-bot
  namespace: anime-bot
spec:
  replicas: 2
  selector:
    matchLabels:
      app: auto-anime-bot
  template:
    metadata:
      labels:
        app: auto-anime-bot
    spec:
      containers:
      - name: bot
        image: bosshub/auto-anime-bot:latest
        env:
        - name: BOT_TOKEN
          valueFrom:
            secretKeyRef:
              name: bot-secrets
              key: bot-token
        - name: DEFAULT_CHANNEL
          value: "-1001234567890"
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "2000m"
        volumeMounts:
        - name: data
          mountPath: /app/data
      volumes:
      - name: data
        persistentVolumeClaim:
          claimName: anime-bot-pvc
```

```bash
# Apply deployment
kubectl apply -f k8s-deployment.yaml
```

---

⚙️ Configuration

Environment Variables (.env)

```env
# ==================== REQUIRED ====================
BOT_TOKEN=your_bot_token_here                    # Telegram bot token from @BotFather
DEFAULT_CHANNEL=-1001234567890                   # Default channel for uploads
ADMIN_LOG_CHANNEL=-1001234567890                 # Channel for admin logs
ADMIN_IDS=123456789,987654321                    # Comma-separated admin user IDs

# ==================== OPTIONAL ====================
# Bot Settings
BOT_USERNAME=auto_anime_bot                      # Bot username (without @)
WEBHOOK_MODE=false                               # Use webhook instead of polling
WEBHOOK_URL=https://your-domain.com/webhook      # Webhook URL
WEBHOOK_PORT=8443                                # Webhook port

# API Configuration
ANILIST_CLIENT_ID=                               # Optional: AniList client ID
ANILIST_CLIENT_SECRET=                           # Optional: AniList client secret
JIKAN_API=https://api.jikan.moe/v4              # Jikan API endpoint

# Database
DATABASE_PATH=data/anime_bot.db                  # SQLite database path
DATABASE_URL=sqlite:///data/anime_bot.db        # Full database URL

# PostgreSQL (if using)
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=auto_anime
POSTGRES_USER=auto_anime
POSTGRES_PASSWORD=your_password

# Redis (for caching and queues)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=

# Performance Settings
MAX_CONCURRENT_DOWNLOADS=3                       # Max parallel downloads
MAX_CONCURRENT_UPLOADS=2                         # Max parallel uploads
DOWNLOAD_TIMEOUT=3600                            # Download timeout (seconds)
UPLOAD_TIMEOUT=1800                              # Upload timeout (seconds)
TARGET_SPEED=700                                 # Target download speed (KB/s)
BUFFER_SIZE=1048576                              # Buffer size (1MB)

# Quality Settings
QUALITIES=480p,720p,1080p                        # Comma-separated qualities
VIDEO_CODEC=libx265                              # Video codec (libx264/libx265)
AUDIO_CODEC=aac                                  # Audio codec
AUDIO_BITRATE=128k                               # Audio bitrate
PRESET=medium                                    # FFmpeg preset

# Storage Limits
MAX_STORAGE_GB=50                                # Max storage in GB
CLEANUP_THRESHOLD_GB=45                          # Cleanup when above this
MAX_FILE_SIZE_GB=2                              # Max file size for Telegram

# Schedule Settings
REQUEST_TIME=18:00                               # Daily processing time (IST)
CLEANUP_HOURS=12                                 # Cleanup interval (hours)
TIMEZONE=Asia/Kolkata                            # Bot timezone

# Request Limits
MAX_USER_REQUESTS=5                              # Max requests per user
MAX_GLOBAL_DAILY_REQUESTS=100                    # Global daily request limit
AUTO_APPROVE_REQUESTS=false                      # Auto-approve user requests

# Channel Routing (Format: "Anime:ChannelID,Another:ChannelID")
CHANNEL_ROUTING="One Piece:-100123, Naruto:-100456"

# FFmpeg Paths
FFMPEG_PATH=/usr/bin/ffmpeg
FFPROBE_PATH=/usr/bin/ffprobe

# Logging
LOG_LEVEL=INFO                                   # DEBUG, INFO, WARNING, ERROR
LOG_FILE=data/logs/bot.log
LOG_MAX_SIZE=10MB                                # Max log file size
LOG_BACKUP_COUNT=5                               # Number of backup logs

# Monitoring
ENABLE_METRICS=true                              # Enable Prometheus metrics
METRICS_PORT=9090                                # Metrics endpoint port

# Security
ALLOWED_USERS=                                   # Comma-separated allowed user IDs (empty = all)
BLOCKED_USERS=                                   # Comma-separated blocked user IDs
RATE_LIMIT_REQUESTS=30                           # Requests per minute per user
RATE_LIMIT_BURST=50                              # Rate limit burst

# Advanced
MAINTENANCE_MODE=false                           # Put bot in maintenance mode
SKIP_EXISTING_FILES=true                         # Skip existing downloads
VERIFY_SSL=true                                  # Verify SSL certificates
```

Channel Routing Configuration

Configure different channels for different anime:

```python
# In bot/config.py or via environment variable
CHANNEL_ROUTING = {
    "One Piece": -1001234567890,
    "Naruto": -1001234567891,
    "Demon Slayer": -1001234567892,
    "Jujutsu Kaisen": -1001234567893,
    "Attack on Titan": -1001234567894,
}
```

Or via .env:

```env
CHANNEL_ROUTING="One Piece:-1001234567890,Naruto:-1001234567891,Demon Slayer:-1001234567892"
```

---

📋 Commands

👤 User Commands

Command Description Example
/start Start the bot and get welcome message /start
/help Show detailed help menu /help
/request <anime> Request an anime /request One Piece
#request <anime> Quick request using hashtag #request Naruto
/latest View 10 most recent uploads /latest
/airing Show today's airing schedule /airing
/search <query> Search for anime in database /search Demon Slayer
/status Check your request status /status
/cancel <id> Cancel a pending request /cancel 123

👑 Admin Commands

Command Description Example
/add_admin <id> Add new admin /add_admin 123456789
/remove_admin <id> Remove admin /remove_admin 123456789
/view_requests View pending user requests /view_requests
/approve <id> Approve a request /approve 123
/reject <id> Reject a request /reject 123
/set_max_requests <n> Set max requests per user /set_max_requests 10
/set_request_time <HH:MM> Set daily processing time /set_request_time 18:00
/del_timer <duration> Set cleanup timer /del_timer 12h
/addtask <title> <ep> Force add task /addtask "One Piece" 1080
/redownload <task_id> Retry failed task /redownload task_abc123
/cancel_task <task_id> Cancel running task /cancel_task task_abc123
/broadcast <msg> Broadcast message to users /broadcast Maintenance soon
/stats View bot statistics /stats
/debug Show debug information /debug
/reload_config Reload configuration /reload_config
/backup Manual database backup /backup
/restore <file> Restore database from backup /restore backup.db
/cleanup Force manual cleanup /cleanup
/set_channel <anime> <channel> Set channel routing /set_channel "One Piece" -100123
/view_queue View download queue /view_queue
/priority <task_id> <priority> Set task priority /priority task_abc123 5

---

🎯 Pipeline Stages

Stage 1: FETCH 📡

· Queries AniList/MyAnimeList APIs
· Fetches anime metadata (title, episode, genres, rating)
· Identifies source URLs from configured providers
· Caches results for 24 hours

Stage 2: DOWNLOAD ⬇️

· High-speed multi-threaded downloading
· 600-700 KB/s sustained speed
· Checks file integrity with MD5
· Resume support for interrupted downloads
· Automatic retry on failure (3 attempts)

Stage 3: PROCESS ⚙️

· FFmpeg-based video processing
· Encodes to HEVC/H.265 for smaller size
· Generates 480p, 720p, 1080p versions
· Preserves original audio quality
· Adds metadata tags (title, episode, anime info)

Stage 4: UPLOAD 📤

· Parallel uploading to Telegram
· Streamable video format
· Automatic thumbnail generation
· Retry with exponential backoff
· Fallback channel support

Stage 5: POST 📝

· Rich HTML/Markdown formatting
· Includes: Title, Episode, Quality, Genres, Rating
· Channel-specific routing
· User notification on completion
· Admin log entry

---

🔧 Performance Tuning

Optimize Download Speed

```python
# In config.py
MAX_CONCURRENT_DOWNLOADS = 4      # Increase parallel downloads
BUFFER_SIZE = 2097152             # 2MB buffer (increase from 1MB)
TARGET_SPEED = 1000               # Target 1MB/s
```

Optimize Processing Speed

```python
# FFmpeg preset optimization
PRESET = "ultrafast"              # Faster but larger files
# PRESET = "veryfast"             # Good balance
# PRESET = "medium"               # Default (recommended)
```

Memory Management

```python
# Limit memory usage
MAX_CACHE_SIZE = 100              # Max cached items
CLEANUP_INTERVAL = 300            # Cleanup every 5 minutes
```

Database Optimization

```sql
-- Enable WAL mode for better concurrency
PRAGMA journal_mode=WAL;

-- Optimize cache size
PRAGMA cache_size=-20000;  -- 20MB cache

-- Optimize query performance
CREATE INDEX IF NOT EXISTS idx_tasks_status_created ON tasks(status, created_at);
```

---

📈 Monitoring & Logging

Prometheus Metrics

```python
# Available metrics
- bot_tasks_total{status}          # Total tasks by status
- bot_download_duration_seconds    # Download duration histogram
- bot_upload_duration_seconds      # Upload duration histogram
- bot_active_tasks                 # Currently active tasks
- bot_queue_size                   # Current queue size
- bot_errors_total{type}           # Error count by type
- bot_requests_total               # Total user requests
- bot_storage_used_bytes           # Storage usage in bytes
```

Grafana Dashboard

Import dashboard ID: 1860 (Telegram Bot Analytics)

```json
{
  "dashboard": {
    "title": "Auto Anime Bot Dashboard",
    "panels": [
      {
        "title": "Tasks per Day",
        "type": "graph",
        "targets": [{ "expr": "sum(bot_tasks_total)" }]
      },
      {
        "title": "Download Speed",
        "type": "gauge",
        "targets": [{ "expr": "avg(bot_download_speed_kbps)" }]
      },
      {
        "title": "Queue Size",
        "type": "stat",
        "targets": [{ "expr": "bot_queue_size" }]
      }
    ]
  }
}
```

Log Levels

```python
LOG_LEVEL = "DEBUG"    # Most verbose, all messages
LOG_LEVEL = "INFO"     # Informational messages
LOG_LEVEL = "WARNING"  # Warning and errors only
LOG_LEVEL = "ERROR"    # Errors only
```

Log Rotation

```python
# Automatic log rotation
- Daily log files: auto_anime_YYYYMMDD.log
- Max size: 10MB per file
- Retention: 30 days
- Compression: gzip after 7 days
```

---

🐛 Troubleshooting

Common Issues and Solutions

Issue 1: Bot Not Responding

```bash
# Check if bot is running
ps aux | grep python

# Check logs
tail -f data/logs/auto_anime_*.log

# Restart bot
./scripts/stop.sh
./scripts/start.sh
```

Issue 2: Download Fails with Timeout

```python
# Increase timeout in config.py
DOWNLOAD_TIMEOUT = 7200  # 2 hours

# Or check network connectivity
ping google.com
```

Issue 3: FFmpeg Not Found

```bash
# Install FFmpeg
sudo apt update
sudo apt install ffmpeg

# Verify installation
ffmpeg -version
```

Issue 4: Database Locked

```sql
-- Enable WAL mode
PRAGMA journal_mode=WAL;

-- Or vacuum database
VACUUM;
```

Issue 5: Upload Failed (File Too Large)

```python
# Compress more
VIDEO_BITRATE = "800k"  # Reduce from 1500k
CRF = 28                # Increase from 24
```

Debug Mode

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
python -m bot.main --debug

# Check database
sqlite3 data/anime_bot.db "SELECT * FROM tasks WHERE status='failed';"
```

---

🔒 Security

Best Practices

1. Never commit .env file - Already in .gitignore
2. Use environment variables for all secrets
3. Limit admin access - Only trusted users
4. Regular backups - Automatic daily backups
5. Monitor logs - Check for suspicious activity
6. Update regularly - Keep dependencies updated
7. Use HTTPS - For webhook mode
8. Rate limiting - Prevents abuse

Security Checklist

```bash
✅ BOT_TOKEN stored in environment (not in code)
✅ ADMIN_IDS configured with specific user IDs
✅ ADMIN_LOG_CHANNEL set to private channel
✅ Regular security updates via `pip list --outdated`
✅ Database permissions restricted (600)
✅ SSL/TLS enabled for webhook mode
✅ Rate limiting enabled (30 req/min)
✅ Input sanitization enabled
```

---

🔄 Backup & Recovery

Automatic Backups

```bash
# Backup location
data/backups/

# Backup schedule
Daily at 3:00 AM

# Retention
7 days (configurable)
```

Manual Backup

```bash
# Via command
python scripts/backup.py

# Via SQLite
sqlite3 data/anime_bot.db ".backup data/backups/manual_backup.db"

# Via Docker
docker-compose exec auto-anime-bot python scripts/backup.py
```

Restore from Backup

```bash
# Stop bot
./scripts/stop.sh

# Restore database
cp data/backups/anime_bot_backup_20240101_030000.db data/anime_bot.db

# Start bot
./scripts/start.sh
```

---

📊 Database Schema

Tables Structure

```sql
-- tasks: Store all processing tasks
CREATE TABLE tasks (
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
);

-- user_requests: Store user anime requests
CREATE TABLE user_requests (
    request_id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    user_name TEXT,
    anime_title TEXT NOT NULL,
    episode INTEGER,
    quality TEXT,
    status TEXT DEFAULT 'pending',
    requested_at TIMESTAMP,
    processed_at TIMESTAMP,
    task_id TEXT,
    admin_notes TEXT
);

-- admins: Store admin users
CREATE TABLE admins (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    last_name TEXT,
    added_by INTEGER,
    added_at TIMESTAMP,
    permissions TEXT,
    is_active INTEGER DEFAULT 1
);
```

---

🤝 Contributing

Development Setup

```bash
# Fork and clone repository
git clone https://github.com/YOUR_USERNAME/auto-anime-bot.git
cd auto-anime-bot

# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
pytest tests/

# Run linting
flake8 bot/
black bot/

# Run type checking
mypy bot/
```

Pull Request Process

1. Fork the repository
2. Create feature branch (git checkout -b feature/amazing)
3. Commit changes (git commit -m 'Add amazing feature')
4. Push to branch (git push origin feature/amazing)
5. Open Pull Request

Code Style

· Follow PEP 8 guidelines
· Use type hints
· Write docstrings for functions
· Add tests for new features
· Keep functions small and focused

---

📝 License

MIT License - Created with ❤️ by BOSSHUB

Copyright (c) 2026 BOSSHUB

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

---

🙏 Acknowledgments

· python-telegram-bot - Telegram Bot API wrapper
· AniList - Anime database and GraphQL API
· MyAnimeList (Jikan) - Anime API service
· FFmpeg - Video processing engine
· Contributors - All open source contributors

---

📞 Support & Community

· GitHub Issues: Report bugs
· Telegram Support: Join group
· Documentation: Read docs

---

<p align="center">
  <strong>✦ ＡＵＴＯ ＡＮＩＭＥ ✦ - The Ultimate Anime Automation Bot</strong>
</p>

<p align="center">
  Made with 🎬 by BOSSHUB
</p>

<p align="center">
  🤩 POWERED BY: BOSSHUB— BOTZ & 𝐁𝐨𝐬𝐬𝐡𝐮𝐛 😁
</p>

<p align="center">
  <img src="https://visitor-badge.laobi.icu/badge?page_id=bosshub.auto-anime-bot" alt="Visitors">
  <img src="https://img.shields.io/github/stars/BOSSHUB/auto-anime-bot?style=social" alt="Stars">
  <img src="https://img.shields.io/github/forks/BOSSHUB/auto-anime-bot?style=social" alt="Forks">
</p>


---

