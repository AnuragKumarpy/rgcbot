# 🤖 RGCBot — Production-Grade Telegram Supergroup Management & Fun Bot

[![Python Version](https://img.shields.io/badge/python-3.11%20%7C%203.12-blue.svg)](https://www.python.org/)
[![Aiogram Version](https://img.shields.io/badge/aiogram-3.15+-brightgreen.svg)](https://docs.aiogram.dev/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Docker](https://img.shields.io/badge/docker-ready-2496ED.svg)](Dockerfile)
[![AWS Ready](https://img.shields.io/badge/AWS-EC2%20%7C%20ECS-orange.svg)](deploy/)

**RGCBot** is an asynchronous Telegram bot for supergroups and active communities. It combines moderation, anti-spam controls, inline settings, fun commands, a TTL-based message cleanup worker, and optional MTProto-backed username resolution/member sync.

---

## 🌟 Key Highlights & Architectural Features

### 1. ⏱️ Ephemeral Auto-Deletion Engine ("Clean Chat")
- **Zero Chat Clutter**: Every bot reply, warning, error notice, or game roll is tagged with a Time-To-Live (TTL) and queued in a **Redis Sorted Set (`ZSET`)**.
- **Decoupled Background Sweeper**: An asynchronous sweeper worker continuously deletes expired messages in batches using Telegram's high-speed `deleteMessages` API without blocking user commands.
- **Trigger Command Cleaner**: Automatically deletes the user's triggering `/command` message as well when the bot's response expires.
- **Configurable Per-Group TTLs**: Admins can customize or disable TTLs per category via inline settings (`/settings`).

### 2. 📊 Activity History & Analytics
- **Group History**: `/stats` renders a group activity card with daily, weekly, monthly, or all-time message history, active members, and top contributors.
- **User History**: `/ustats` shows a member's message history across chats, plus their top groups, bans, karma, coins, and game stats.
- **Global History**: `/topstats` aggregates the most active users, groups, and game scorers across the bot.

### 3. 🛡️ Moderation Suite
- **Granular Restraints**: `/ban`, `/sban`, `/tban <time>`, `/mute`, `/smute`, `/tmute <time>`, `/kick`, `/unban`, `/unmute`.
- **Warn Escalation Matrix**: `/warn <reason>`, `/warns`, `/resetwarns`. Automatically triggers a temporary mute, kick, or ban when a member reaches the group's warning limit.
- **Bulk Cleanup**: `/purge` (batch delete up to 100 recent messages) and `/del`.
- **Pinned Message Controls**: `/pin` and `/unpin`.

### 4. 🚪 Gatekeeper Verification & Anti-Spam
- **Join Captcha Gate**: Restricts new members immediately upon joining until they pass a challenge (Button click or Math problem `12 + 5 = ?`).
- **Auto-Kick on Timeout**: Automatically kicks unverified accounts if they don't solve the captcha within the timeout window (default 90s).
- **Anti-Flood Shield**: Detects rapid message bursts and mutes flooders automatically for 10 minutes.
- **Anti-Link & Anti-Forward Guard**: Deletes non-whitelisted URLs, Telegram invite links (`t.me/+...`), and channel forwards.
- **Audit Log Channel**: Broadcasts all moderation actions, kicks, bans, and security triggers in real time to a dedicated private Telegram channel.

### 5. 🎮 Interactive Gamification & Fun Engine
- **Reputation & Karma**: Users award karma by replying with natural triggers (`+rep`, `thanks`, `+1`, `helpful`). Features pair cooldowns and anti-self-rep protection.
- **Daily Streak Rewards**: `/daily` claims daily bonus coins with consecutive-day streak multipliers.
- **Russian Roulette (`/roulette`)**: Spin the cylinder with a 1-in-6 chance of getting **temporarily muted for 60 seconds**! Safe spins earn survival coins and streaks.
- **Animated Mini-Games & Dice Duels**:
  - Native Telegram dice animations (`🎲`, `🎯`, `🎳`, `🎰`, `⚽`, `🏀`).
  - `/duel [bet_amount]`: Challenge another user to a live dice duel with interactive "Accept" / "Decline" inline buttons.
- **Social Utilities & Flairs**:
  - `/profile` / `/me`: Sleek profile card showing karma, coins, streak, rank tier, and badges.
   - `/ustats`: Personal messaging, ban, and game stats with appeal actions when available.
   - `/topstats`: Global top messaging users, top chats, and top game scorers.
   - `/appeal`: Request admin review for active bans through the bot.
  - `/settitle <flair>`: Set custom flair titles.
  - `/afk <reason>`: Sets AFK status; automatically announces AFK when mentioned and clears upon return.
  - `/filter <word> <reply>` & `/filters`: Dynamic auto-responder keywords.

### 6. ⚙️ Interactive Settings Dashboard
- Run `/settings` in any group to open the inline keyboard menu for toggling modules, adjusting TTL timers, and configuring warn thresholds.

### 7. 🔌 Runtime Modes
- `BOT_MODE=webhook` starts the embedded `aiohttp` server and registers the Telegram webhook.
- `BOT_MODE=polling` runs long polling and disables the webhook before polling starts.
- The bot always starts the TTL sweeper, database layer, Redis client, and command metadata setup during startup.

---

## 🏗️ System Architecture

```
Telegram Cloud API
       │
       ▼
[ Gateway / Webhook / Polling Ingress ]
       │
       ├── Rate Limiting Middleware (Redis Token Bucket)
       ├── Auth & Permissions Middleware (Admin Cache)
       └── Database Session Middleware (Asyncpg)
       │
       ▼
[ Aiogram 3 Dispatcher & Routers ]
       ├── Admin Router (Mute, Ban, Warn, Purge, Settings)
       ├── Fun Router (Karma, Games, Russian Roulette, AFK)
       ├── Events Router (Captcha Gate, Anti-Flood, Filters)
       └── Common Router (Start, Help, Rules)
       │
       ▼
[ Ephemeral Auto-Delete Engine ]
       │──> ZADD delete_timestamp chat_id:msg_id (Redis ZSET)
       └──> Async Sweeper Worker ──> Batch deleteMessages API
       │
[ Storage Tier ]
       ├── PostgreSQL 16 (Users, Groups, Warns, Logs, Filters)
       └── Redis 7 (TTL Queues, Sliding Window Counters, Captchas)
```

---

## 🚀 Quick Start (Local Setup)

### Option 1: Running with Docker Compose (Recommended)

1. **Clone and configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env and insert your BOT_TOKEN from @BotFather
   ```

2. **Start the complete stack**:
   ```bash
   docker compose up -d --build
   ```

3. **Check logs**:
   ```bash
   docker compose logs -f bot
   ```

---

### Option 2: Running in Python Virtualenv

1. **Create virtualenv & install dependencies**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Set up PostgreSQL and Redis**:
   The default runtime expects PostgreSQL and Redis. Make sure both are running locally or via Docker:
   ```bash
   docker run -d --name pg -p 5432:5432 -e POSTGRES_PASSWORD=postgres postgres:16-alpine
   docker run -d --name redis -p 6379:6379 redis:7-alpine
   ```

3. **Run the Bot**:
   ```bash
   python -m src.main
   ```

4. **Optional local testing shortcut**:
   If you want to avoid loading the repo `.env` during test collection, run pytest from outside the repository root and point `PYTHONPATH` at the project.
   ```bash
   cd /tmp
   PYTHONPATH=/home/Gaurav/Desktop/tg/rgcbot uv run --project /home/Gaurav/Desktop/tg/rgcbot pytest -q /home/Gaurav/Desktop/tg/rgcbot/tests
   ```

---

## ☁️ AWS Production Deployment Guide

### Deployment Model A: AWS EC2 with Docker Compose & Systemd

1. **Launch an AWS EC2 Instance**:
   - Instance Type: `t4g.small` (ARM Graviton) or `t3.small` (Ubuntu 24.04 LTS).
   - Security Group: Allow outbound HTTPS (Port 443). If using Webhook mode, open Port 80/443 for inbound traffic. If using Polling mode, **no inbound open ports are required!**

2. **Install Docker & Docker Compose on EC2**:
   ```bash
   sudo apt-get update && sudo apt-get install -y docker.io docker-compose-v2
   sudo usermod -aG docker ubuntu
   ```

3. **Deploy Codebase**:
   ```bash
   git clone <your-repo-url> /home/ubuntu/rgcbot
   cd /home/ubuntu/rgcbot
   cp .env.example .env
   # Populate BOT_TOKEN, DATABASE_URL, REDIS_URL
   ```

4. **Install Systemd Service for Auto-Restart on Boot**:
   ```bash
   sudo cp deploy/systemd/rgcbot.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable rgcbot
   sudo systemctl start rgcbot
   ```

5. **Monitor Service**:
   ```bash
   sudo systemctl status rgcbot
   journalctl -u rgcbot -f
   ```

---

### Deployment Model B: AWS ECS Fargate + RDS PostgreSQL + ElastiCache

For a fully serverless, zero-maintenance AWS architecture:
1. Build and push the Docker image to **AWS ECR**:
   ```bash
   aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <AWS_ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com
   docker build -t rgcbot:latest .
   docker tag rgcbot:latest <AWS_ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/rgcbot:latest
   docker push <AWS_ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/rgcbot:latest
   ```
2. Provision **AWS RDS PostgreSQL 16** and **AWS ElastiCache Redis**.
3. Register the task definition from `deploy/aws-ecs-task-def.json` in ECS.
4. Attach an **Application Load Balancer (ALB)** with an HTTPS listener pointing to the target group on port 8000 (`/health`).

### Current Environment Variables

The canonical template lives in [.env.example](.env.example). The main runtime keys are:

- `BOT_TOKEN`, `BOT_MODE`, `WEBHOOK_HOST`, `WEBHOOK_PATH`, `WEBHOOK_SECRET`, `SERVER_HOST`, `SERVER_PORT`
- `BOT_SUPER_ADMINS`
- `DATABASE_URL`, `DB_ECHO`, `DB_POOL_SIZE`, `DB_MAX_OVERFLOW`
- `REDIS_URL`, `REDIS_TTL_QUEUE_KEY`, `REDIS_RATE_LIMIT_PREFIX`
- `DEFAULT_MOD_TTL`, `DEFAULT_FUN_TTL`, `DEFAULT_RULES_TTL`, `DEFAULT_WARN_TTL`, `DEFAULT_GENERAL_TTL`
- `SWEEPER_INTERVAL_SECONDS`, `SWEEPER_BATCH_SIZE`
- `DEFAULT_FLOOD_LIMIT`, `DEFAULT_FLOOD_WINDOW`, `DEFAULT_CAPTCHA_TIMEOUT`, `DEFAULT_LOG_CHANNEL_ID`
- `TELEGRAM_API_ID`, `TELEGRAM_API_HASH`, `USER_SESSION_STRING`
- `LOG_LEVEL`

---

## 📜 Full Command Reference

### 🛡️ Moderation & Administration Commands
| Command | Arguments | Description | Default TTL |
|---|---|---|---|
| `/ban` | `[reason]` | Permanently ban replied user | 15s |
| `/tban` | `<time> [reason]` | Temporary ban (e.g. `1d`, `12h`, `30m`) | 15s |
| `/mute` | `[reason]` | Restrict sending messages | 15s |
| `/tmute` | `<time> [reason]` | Temporary mute (e.g. `30m`, `2h`) | 15s |
| `/unban` | - | Lift ban on replied user | 15s |
| `/unmute` | - | Restore speaking permissions | 15s |
| `/kick` | `[reason]` | Remove user from group (can rejoin) | 15s |
| `/warn` | `[reason]` | Issue warning (auto-escalates on limit) | 20s |
| `/warns` | - | View active warnings count | 20s |
| `/resetwarns` | - | Reset user warnings to 0 | 20s |
| `/purge` | - | Bulk delete messages up to replied message | 4s |
| `/del` | - | Delete replied message | Instant |
| `/pin` | - | Pin replied message | 15s |
| `/unpin` | - | Unpin replied message | 15s |
| `/settings` | - | Open interactive security & TTL dashboard | None |
| `/filter` | `<keyword> <text>` | Add keyword auto-reply | 15s |
| `/stop` | `<keyword>` | Remove keyword auto-reply | 15s |
| `/setrules` | `<rules text>` | Set group rules | 15s |

### 🌟 Fun, Reputation & Gamification Commands
| Command | Arguments | Description | Default TTL |
|---|---|---|---|
| `+rep` / `thanks` | - | Award +1 reputation to replied member | 30s |
| `/karma` / `/rep` | - | View reputation score, coins, and tier | 30s |
| `/topkarma` | - | Top 10 group reputation leaderboard | 45s |
| `/ustats` | `[reply]` | View personal messaging, ban, and game stats | 30s |
| `/topstats` | - | Global top messaging users, groups, and game scorers | 45s |
| `/stats` | - | Group activity history, top contributors, and timeframe cards | 45s |
| `/appeal` | - | Request review for active ban(s) through the bot | 45s |
| `/daily` | - | Claim daily bonus coins & streak | 30s |
| `/roulette` | - | Russian Roulette (1/6 chance of 60s mute!) | 25s / 60s |
| `/duel` | `[amount]` | Challenge replied user to dice duel | 60s |
| `/dice` | - | Roll animated dice | 30s |
| `/slots` | - | Spin animated slot machine (Payout on 777) | 30s |
| `/darts` | - | Throw animated darts | 30s |
| `/bowling` | - | Roll animated bowling ball | 30s |
| `/basketball` | - | Shoot animated basketball | 30s |
| `/football` | - | Kick animated football | 30s |
| `/profile` / `/me` | - | View member profile card | 30s |
| `/settitle` | `<title>` | Set custom flair title | 30s |
| `/afk` | `[reason]` | Mark self as AFK | 30s |
| `/rules` | - | View group rules | 45s |
| `/help` | - | View bot command guide | 45s |

---

## ⚙️ Environment Variables Reference

| Variable | Default | Description |
|---|---|---|
| `BOT_TOKEN` | *Required* | Telegram Bot token from @BotFather |
| `BOT_MODE` | `webhook` | `webhook` (recommended for production) or `polling` |
| `WEBHOOK_HOST` | `https://yourdomain.com` | Public HTTPS base URL that Telegram can reach |
| `WEBHOOK_PATH` | `/webhook` | Webhook route path registered with Telegram |
| `WEBHOOK_SECRET` | `None` | Optional secret token validated on incoming webhook calls |
| `SERVER_HOST` | `0.0.0.0` | Local bind address for the webhook HTTP server |
| `SERVER_PORT` | `8000` | Local bind port for the webhook HTTP server |
| `DATABASE_URL` | `postgresql+asyncpg://...` | PostgreSQL async connection string |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection URL |
| `BOT_SUPER_ADMINS` | `""` | Comma-separated list of Super Admin user IDs |
| `DEFAULT_MOD_TTL` | `15` | Default TTL for moderation notices (seconds) |
| `DEFAULT_FUN_TTL` | `30` | Default TTL for game results & karma notices |
| `DEFAULT_RULES_TTL` | `45` | Default TTL for rules and help menus |
| `DEFAULT_WARN_TTL` | `20` | Default TTL for warning alerts |
| `SWEEPER_INTERVAL_SECONDS` | `1.5` | Interval between background deletion sweeps |
| `DEFAULT_LOG_CHANNEL_ID` | `None` | Telegram channel ID for global audit logs |
| `LOG_LEVEL` | `INFO` | Logging verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |

---

## 🧪 Testing

Run the automated test suite with pytest:
```bash
make test
# Or directly:
pytest tests/ -v
```

If local `.env` values interfere with collection, use the same isolated invocation the CI/docs expect:
```bash
cd /tmp
PYTHONPATH=/home/Gaurav/Desktop/tg/rgcbot BOT_SUPER_ADMINS=[] uv run --project /home/Gaurav/Desktop/tg/rgcbot pytest -q /home/Gaurav/Desktop/tg/rgcbot/tests
```

For linting:
```bash
make lint
```

---

## 📄 License
Released under the [MIT License](LICENSE).
