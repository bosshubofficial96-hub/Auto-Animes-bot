# ✦ ＡＵＴＯ ＡＮＩＭＥ ✦

<p align="center">
  <strong>Enterprise-Grade Automated Anime Media Management Bot for Telegram</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.8+-blue.svg">
  <img src="https://img.shields.io/badge/Telegram-Bot-blue.svg">
  <img src="https://img.shields.io/badge/License-MIT-green.svg">
  <img src="https://img.shields.io/badge/Version-2.0.0-orange.svg">
</p>

## 🎬 Features

- **Automated Pipeline**: FETCH → DOWNLOAD → PROCESS → UPLOAD → POST
- **Triple Quality Output**: 480p, 720p, 1080p HEVC encoding
- **Smart Request System**: User requests with admin approval workflow
- **Scheduled Processing**: Daily cron jobs in IST timezone
- **Multi-Channel Routing**: Route different anime to different channels
- **High Performance**: 600-700 KB/s download speeds
- **Auto Cleanup**: Configurable file retention policies
- **24/7 Operation**: Robust error handling and auto-retry

## 📋 Commands

### User Commands
| Command | Description |
|---------|-------------|
| `/start` | Start the bot |
| `/help` | Show help message |
| `/request <anime>` | Request an anime |
| `#request <anime>` | Quick request using hashtag |
| `/latest` | View latest uploads |
| `/airing` | Today's airing schedule |
| `/search <anime>` | Search anime database |
| `/status` | Check your requests |

### Admin Commands
| Command | Description |
|---------|-------------|
| `/add_admin <id>` | Add new admin |
| `/view_requests` | View pending requests |
| `/set_max_requests <n>` | Set max requests per user |
| `/set_request_time <HH:MM>` | Set daily processing time |
| `/del_timer <duration>` | Set cleanup timer |
| `/addtask <title> <ep>` | Force add task |
| `/redownload <task_id>` | Retry failed task |
| `/stats` | View bot statistics |
| `/broadcast <msg>` | Broadcast message |

## 🚀 Installation

### Prerequisites
- Python 3.8+
- FFmpeg
- Telegram Bot Token

### Quick Start

```bash
# Clone repository
git clone https://github.com/BOSSHUB/auto-anime-bot.git
cd auto-anime-bot

# Run setup script
chmod +x scripts/setup.sh
./scripts/setup.sh

# Edit .env file with your bot token
nano .env

# Start the bot
./scripts/start.sh
