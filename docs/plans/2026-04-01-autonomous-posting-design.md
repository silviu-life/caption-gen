# Autonomous TikTok Posting System — Design Document

**Date:** 2026-04-01
**Project:** Carl Jung Caption Gen (@heal.with.jung)
**Goal:** Autonomously post 3 TikTok videos per day at research-optimized times for UK engagement, with Telegram bot monitoring and control.

---

## System Overview

Four components:

1. **`auto-post.sh`** — Cron-triggered wrapper script. Handles git sync, Claude invocation, success detection, logging, Telegram notification, and failure handling.
2. **`telegram_bot.py`** — Systemd-managed Python service. Listens for `/status`, `/resume`, `/scripts`, `/pause` commands. Restricted to a single authorized chat ID.
3. **`install.sh`** — One-command installer for both VPS and local. Sets up cron jobs, systemd service, validates prerequisites.
4. **`CLAUDE.md`** — Project instructions so Claude can help install prerequisites on a fresh server.

**Deployment targets:** Hostinger VPS (primary), local Linux machine (fallback). Both use system cron + systemd.

---

## Posting Schedule

All times in **Europe/London** timezone (auto-handles GMT/BST transitions). Each time is shifted 10 minutes before peak engagement to allow algorithm pickup.

| Day       | Slot 1 | Slot 2 | Slot 3 | Rationale                                                    |
|-----------|--------|--------|--------|--------------------------------------------------------------|
| Monday    | 06:50  | 16:50  | 18:50  | Commuter + post-work + "fresh start" evening                 |
| Tuesday   | 06:50  | 16:50  | 19:50  | Commuter + afternoon + peak evening (top engagement day)     |
| Wednesday | 06:50  | 14:50  | 16:50  | Commuter + midweek cognitive peak + work transition          |
| Thursday  | 08:50  | 16:50  | 18:50  | Coffee break + afternoon + highest engagement evening        |
| Friday    | 06:50  | 12:50  | 18:50  | Commuter + lunch wind-down + best evening of the week        |
| Saturday  | 10:50  | 14:50  | 18:50  | Late morning leisure + afternoon + evening (less competition)|
| Sunday    | 08:50  | 10:50  | 18:50  | Early reflective + late morning (high completion) + "reset"  |

**Research sources:** Buffer (7.1M posts), Sprout Social (2B engagements), SocialPilot (700K posts), Hopper HQ, iQfluence, RecurPost (2M+ posts). Educational/motivational content performs best Tue-Thu 3-9 PM; reflective content peaks Sun morning.

**Content runway:** 93 total scripts, 4 posted. At 3/day = ~30 days of content remaining.

---

## Component 1: auto-post.sh

Called by each of the 21 weekly cron entries. Single-purpose: execute one posting cycle.

```
Usage: auto-post.sh [--dry-run]
```

### Execution Flow

1. **Pause check** — If `~/.caption-gen-paused` exists, exit silently.

2. **Missed post recovery** — Compare today's already-completed posts (from posting_log.json) against today's schedule. If a slot was missed (e.g., VPS reboot), proceed with posting to catch up.

3. **Git pull** — `git pull --rebase` to sync latest state (posting_log.json from other runs).

4. **Invoke Claude** — `claude -p post-next` with output captured. Timeout: 10 minutes.

5. **Success detection** — Count entries in posting_log.json before and after. If new entry added with `"status": "success"`, the post succeeded.

6. **On success:**
   - Parse new log entry: script name, characters_used, cost_usd
   - Extract full caption from Claude's output
   - Calculate cumulative cost from all log entries
   - Send Telegram notification:
     ```
     Posted: 005 - becoming-who-you-are
     
     Caption:
     <full caption text + hashtags>
     
     Cost: $0.17 | Total: $0.85
     Remaining: 88/93 scripts
     ```
   - Append to `posting.log` (text): `[2026-04-02 18:50] SUCCESS 005-becoming-who-you-are $0.17`
   - Git commit + push: `post: 005-becoming-who-you-are`

7. **On failure:**
   - Create `~/.caption-gen-paused`
   - Send Telegram alert: "POSTING FAILED: [error]. System paused. Send /resume to retry."
   - Log failure to `posting.log`

8. **All-done detection:** If posting_log.json has 93 entries, send Telegram: "All 93 scripts posted! Schedule complete." Create pause file.

9. **Dry-run mode** (`--dry-run`): Skips `claude -p post-next`. Logs what would happen, sends Telegram preview.

### Environment

- Loads `.env` from project directory (TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)
- Uses `curl` for Telegram API calls (no Python dependency in the wrapper)
- Working directory: project root (auto-detected or configured in install)

---

## Component 2: telegram_bot.py

Lightweight Python service using `python-telegram-bot` library.

### Commands

| Command    | Description                                              |
|------------|----------------------------------------------------------|
| `/status`  | Today's remaining post times, next script, scripts remaining, last post time, cumulative cost |
| `/resume`  | Remove pause file, immediately run `auto-post.sh` to retry failed post, report result |
| `/scripts` | Show next 2 unposted script names with numbers           |
| `/pause`   | Create pause file, confirm system is paused               |

### Features

- **Command menu registration:** On startup, calls `bot.set_my_commands()` so commands appear in Telegram's `/` menu with descriptions.
- **Security:** Only responds to configured chat ID (`-5110202206`). Silently ignores all other senders.
- **State reading:** Reads `posting_log.json` for posting history and costs. Reads `~/.caption-gen-paused` for pause state. Has hardcoded schedule dict matching cron times.
- **Resume action:** Deletes pause file, runs `auto-post.sh` via subprocess, captures output, sends result back to Telegram.

### Systemd Service

```ini
[Unit]
Description=Caption Gen Telegram Bot
After=network.target

[Service]
Type=simple
WorkingDirectory=/path/to/caption-gen
ExecStart=/usr/bin/python3 /path/to/caption-gen/telegram_bot.py
Restart=always
RestartSec=10
EnvironmentFile=/path/to/caption-gen/.env

[Install]
WantedBy=default.target
```

Installed to `~/.config/systemd/user/`. Starts on boot, auto-restarts on crash.

### Dependencies

- `python-telegram-bot>=20.0` (added to requirements.txt)

---

## Component 3: install.sh

One-command setup for VPS or local machine.

```
Usage: install.sh [--local | --vps] [--dry-run] [--uninstall]
```

### Steps

1. **Validate prerequisites:**
   - Python 3 present
   - `claude` CLI installed and authenticated
   - `.env` has: ELEVENLABS_API_KEY, UPLOAD_POST_API_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
   - `python-telegram-bot` installed (auto-installs if missing via pip)
   - Git repo clean and on master

2. **Install cron jobs:**
   - Detect project path
   - Write 21 cron entries with `TZ=Europe/London` prefix
   - Append to user crontab (preserving existing entries)

3. **Install systemd service:**
   - Generate unit file with correct paths
   - Copy to `~/.config/systemd/user/`
   - `systemctl --user daemon-reload && systemctl --user enable --now caption-gen-bot`

4. **Dry-run test:**
   - Run `auto-post.sh --dry-run`
   - Send test Telegram message: "Caption-gen bot installed and ready!"

5. **Print summary:**
   - Next 3 scheduled post times
   - Systemd service status
   - Crontab listing

**Uninstall** (`--uninstall`): Removes cron entries (grep + filter), stops and disables systemd service, removes unit file.

---

## Component 4: CLAUDE.md Updates

Add a section to the project's CLAUDE.md with:

- Server setup prerequisites (Python, pip, Claude CLI, authentication)
- Required .env keys with descriptions
- How to run install.sh
- How to verify with --dry-run
- The full posting schedule for reference
- Telegram bot commands reference
- Troubleshooting common issues

This enables running `claude` on the VPS and saying "set up the posting system" — Claude reads CLAUDE.md and knows exactly what to do.

---

## Cron Configuration

```cron
# Caption-gen autonomous posting schedule (Europe/London)
TZ=Europe/London

# Monday
50 6 * * 1  /path/to/auto-post.sh >> /path/to/posting.log 2>&1
50 16 * * 1 /path/to/auto-post.sh >> /path/to/posting.log 2>&1
50 18 * * 1 /path/to/auto-post.sh >> /path/to/posting.log 2>&1

# Tuesday
50 6 * * 2  /path/to/auto-post.sh >> /path/to/posting.log 2>&1
50 16 * * 2 /path/to/auto-post.sh >> /path/to/posting.log 2>&1
50 19 * * 2 /path/to/auto-post.sh >> /path/to/posting.log 2>&1

# Wednesday
50 6 * * 3  /path/to/auto-post.sh >> /path/to/posting.log 2>&1
50 14 * * 3 /path/to/auto-post.sh >> /path/to/posting.log 2>&1
50 16 * * 3 /path/to/auto-post.sh >> /path/to/posting.log 2>&1

# Thursday
50 8 * * 4  /path/to/auto-post.sh >> /path/to/posting.log 2>&1
50 16 * * 4 /path/to/auto-post.sh >> /path/to/posting.log 2>&1
50 18 * * 4 /path/to/auto-post.sh >> /path/to/posting.log 2>&1

# Friday
50 6 * * 5  /path/to/auto-post.sh >> /path/to/posting.log 2>&1
50 12 * * 5 /path/to/auto-post.sh >> /path/to/posting.log 2>&1
50 18 * * 5 /path/to/auto-post.sh >> /path/to/posting.log 2>&1

# Saturday
50 10 * * 6 /path/to/auto-post.sh >> /path/to/posting.log 2>&1
50 14 * * 6 /path/to/auto-post.sh >> /path/to/posting.log 2>&1
50 18 * * 6 /path/to/auto-post.sh >> /path/to/posting.log 2>&1

# Sunday
50 8 * * 0  /path/to/auto-post.sh >> /path/to/posting.log 2>&1
50 10 * * 0 /path/to/auto-post.sh >> /path/to/posting.log 2>&1
50 18 * * 0 /path/to/auto-post.sh >> /path/to/posting.log 2>&1
```

---

## .env Updates

New keys to add:

```env
TELEGRAM_BOT_TOKEN=8212639952:AAHcp3-KKr8odqGedGgxLK_BNpDsfBdEnTY
TELEGRAM_CHAT_ID=-5110202206
```

---

## Error Handling

| Scenario | Action |
|----------|--------|
| Claude CLI fails | Pause + Telegram alert |
| Git pull conflict | Pause + Telegram alert |
| Network down | Pause + Telegram alert |
| posting_log.json corrupt | Pause + Telegram alert |
| VPS reboots mid-day | On next cron trigger, detect missed posts, post immediately |
| All 93 scripts posted | Telegram "complete" message + pause |
| Telegram API down | Log locally, continue posting (notifications degraded) |

---

## Text Log Format (posting.log)

```
[2026-04-02 06:50] SUCCESS 005-becoming-who-you-are chars=847 cost=$0.17 total=$0.85 remaining=88
[2026-04-02 16:50] SUCCESS 006-the-wound-that-heals chars=912 cost=$0.18 total=$1.03 remaining=87
[2026-04-02 18:50] FAILED  007-the-forgotten-dream error="claude timeout after 600s"
[2026-04-02 18:50] PAUSED  System paused after failure. Awaiting /resume.
```
