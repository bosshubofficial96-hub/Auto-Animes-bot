# ✦ ＡＵＴＯ ＡＮＩＭＥ ✦ Bot

## Project Overview

An enterprise-grade automated anime media management bot for Telegram. It automates the full pipeline: fetching anime metadata from AniList/Jikan, downloading, encoding to HEVC at multiple resolutions (480p/720p/1080p), uploading, and posting to Telegram channels.

## Tech Stack

- **Language**: Python 3.12
- **Framework**: python-telegram-bot v20.7
- **Database**: SQLite (via aiosqlite)
- **Scheduling**: APScheduler
- **Media**: FFmpeg (HEVC/H.265 encoding)
- **APIs**: AniList GraphQL, Jikan (MAL)

## Project Structure

- `bot/` — Main application package
  - `main.py` — Entry point
  - `config.py` — Configuration (reads from `.env`)
  - `core/` — Pipeline stages (fetch, download, process, upload, post)
  - `database/` — SQLite database management
  - `handlers/` — Telegram command handlers
  - `services/` — External API integrations and scheduler
  - `utils/` — Logging, helpers, validators
- `scripts/` — Setup/start/stop shell scripts
- `data/` — Runtime data (downloads, processed files, logs)

## Required Environment Variables

Set these before starting the bot:

| Variable | Description | Required |
|---|---|---|
| `BOT_TOKEN` | Telegram Bot API token (from @BotFather) | Yes |
| `DEFAULT_CHANNEL` | Telegram channel ID (e.g. `-1001234567890`) | Yes |
| `ADMIN_LOG_CHANNEL` | Admin log channel ID | Yes |
| `ADMIN_IDS` | Comma-separated Telegram user IDs for admins | Yes |
| `BOT_USERNAME` | Bot username without @ | No |
| `DATABASE_PATH` | Path to SQLite DB file | No |
| `REQUEST_TIME` | Daily processing time (HH:MM, IST) | No |

## Running the Bot

1. Set required environment variables (see above)
2. The workflow `Start application` runs `python3 -m bot.main`

## User Preferences

- Use Python async patterns throughout
- Keep the modular pipeline structure
