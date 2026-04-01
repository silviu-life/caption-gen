# Caption-Gen — Carl Jung TikTok Posting Pipeline

TikTok channel: **@heal.with.jung** — Carl Jung psychology quotes as short-form videos.

## Project Structure

- `caption_gen.py` — CLI to generate videos from script files (TTS + captions + compositing)
- `tts.py` / `compositor.py` / `renderer.py` — Supporting modules
- `scripts/` — 93 numbered scripts (`NNN-slug.txt`)
- `output/` — Generated MP4 videos
- `posting_log.json` — JSON array tracking all posted videos
- `.claude/skills/post-next/SKILL.md` — Skill for the full posting pipeline

## Autonomous Posting System

### How It Works

- `auto-post.sh` is called by cron 3x daily at research-optimized UK times
- It runs `claude -p "/post-next"` which generates the video, researches hashtags, crafts a caption, posts to TikTok, and updates `posting_log.json`
- `telegram_bot.py` runs as a systemd service for monitoring and control
- On failure, the system pauses and alerts via Telegram. Send `/resume` to retry.

### Server Setup Prerequisites

When setting up on a new server:

1. **Python 3.10+** with pip
2. **Install dependencies:** `pip install -r requirements.txt`
3. **Claude CLI:** Install and authenticate (`claude auth login`)
4. **Git:** Configure with push access to the repo
5. **`.env` file** with these keys:
   - `ELEVENLABS_API_KEY` — ElevenLabs API key for TTS
   - `UPLOAD_POST_API_KEY` — JWT token for upload-post.com
   - `UPLOAD_POST_PROFILE` — Profile name (carl_jung)
   - `TELEGRAM_BOT_TOKEN` — Telegram bot token from @BotFather
   - `TELEGRAM_CHAT_ID` — Telegram chat ID for notifications
6. **Install automation:** `bash install.sh`
7. **Verify:** `bash auto-post.sh --dry-run`

### Posting Schedule (Europe/London)

| Day | Slot 1 | Slot 2 | Slot 3 |
|-----|--------|--------|--------|
| Mon | 06:50  | 16:50  | 18:50  |
| Tue | 06:50  | 16:50  | 19:50  |
| Wed | 06:50  | 14:50  | 16:50  |
| Thu | 08:50  | 16:50  | 18:50  |
| Fri | 06:50  | 12:50  | 18:50  |
| Sat | 10:50  | 14:50  | 18:50  |
| Sun | 08:50  | 10:50  | 18:50  |

### Telegram Bot Commands

- `/status` — Schedule, stats, costs, pause state
- `/resume` — Clear pause and retry the failed post immediately
- `/scripts` — Show next 2 unposted scripts
- `/pause` — Pause all scheduled posting

### Troubleshooting

- **Check text log:** `cat posting.log`
- **Check bot logs:** `journalctl --user -u caption-gen-bot -f`
- **Manually resume:** `rm ~/.caption-gen-paused && bash auto-post.sh`
- **Manual post:** `bash auto-post.sh`
- **Reinstall:** `bash install.sh --uninstall && bash install.sh`
