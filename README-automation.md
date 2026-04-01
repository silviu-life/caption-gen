# Autonomous Posting System

Automated TikTok posting for **@heal.with.jung** — posts 3 Carl Jung psychology videos daily at optimal UK engagement times.

## Quick Start

```bash
# Install everything (cron + Telegram bot service)
bash install.sh

# Verify it works
bash auto-post.sh --dry-run

# Uninstall
bash install.sh --uninstall
```

## How It Works

1. **Cron** triggers `auto-post.sh` at 21 scheduled times per week
2. The script runs `claude -p "/post-next"` which:
   - Finds the next unposted script
   - Generates the video (ElevenLabs TTS + caption compositing)
   - Researches SEO hashtags
   - Crafts a TikTok caption
   - Posts via upload-post.com
   - Updates `posting_log.json`
3. On success: Telegram notification with caption, costs, remaining count, then git commit + push
4. On failure: System pauses, Telegram alert sent. Send `/resume` to retry.

## Schedule (Europe/London)

Times are 10 minutes before peak engagement windows, based on research across 8+ social media analytics platforms.

| Day | Times | Peak Windows |
|-----|-------|-------------|
| Mon | 06:50, 16:50, 18:50 | Commuter, post-work, evening motivation |
| Tue | 06:50, 16:50, 19:50 | Top engagement day for educational content |
| Wed | 06:50, 14:50, 16:50 | Midweek cognitive peak |
| Thu | 08:50, 16:50, 18:50 | Highest evening engagement across niches |
| Fri | 06:50, 12:50, 18:50 | Best evening of the week |
| Sat | 10:50, 14:50, 18:50 | Less competition, leisure scrolling |
| Sun | 08:50, 10:50, 18:50 | Reflective content, "Sunday reset" |

## Telegram Bot

Runs as a systemd service. Commands:

| Command | Description |
|---------|-------------|
| `/status` | Current state, next post, remaining scripts, costs |
| `/resume` | Clear pause and retry immediately |
| `/scripts` | Show next 2 upcoming scripts |
| `/pause` | Pause all scheduled posting |

## Files

| File | Purpose |
|------|---------|
| `auto-post.sh` | Cron wrapper — git sync, claude invocation, notifications |
| `telegram_bot.py` | Telegram bot service for monitoring and control |
| `install.sh` | One-command installer for cron + systemd |
| `posting_log.json` | Structured log (git-tracked, source of truth) |
| `posting.log` | Human-readable text log (local only) |

## Troubleshooting

**System paused unexpectedly?**
```bash
cat posting.log                          # Check what happened
rm ~/.caption-gen-paused                 # Clear pause
bash auto-post.sh                        # Retry manually
```

**Bot not responding?**
```bash
systemctl --user status caption-gen-bot  # Check service
systemctl --user restart caption-gen-bot # Restart it
journalctl --user -u caption-gen-bot -f  # Watch logs
```

**Cron not firing?**
```bash
crontab -l | grep caption-gen            # Verify entries exist
TZ=Europe/London date +"%A %H:%M"       # Check current London time
```
