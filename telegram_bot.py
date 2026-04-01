#!/usr/bin/env python3
"""Telegram bot for monitoring and controlling the Carl Jung TikTok posting system."""

import json
import logging
import os
import re
import subprocess
from datetime import datetime
from functools import wraps
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from telegram import BotCommand, Update
from telegram.ext import Application, CommandHandler, ContextTypes

# ── Configuration ──

PROJECT_DIR = Path(__file__).parent.resolve()
PAUSE_FILE = Path.home() / ".caption-gen-paused"
LOG_JSON = PROJECT_DIR / "posting_log.json"
SCRIPTS_DIR = PROJECT_DIR / "scripts"
TOTAL_SCRIPTS = 93
LONDON_TZ = ZoneInfo("Europe/London")

load_dotenv(PROJECT_DIR / ".env")
AUTHORIZED_CHAT_ID = int(os.environ["TELEGRAM_CHAT_ID"])

# Python weekday(): 0=Monday ... 6=Sunday
SCHEDULE = {
    0: ["06:50", "16:50", "18:50"],  # Monday
    1: ["06:50", "16:50", "19:50"],  # Tuesday
    2: ["06:50", "14:50", "16:50"],  # Wednesday
    3: ["08:50", "16:50", "18:50"],  # Thursday
    4: ["06:50", "12:50", "18:50"],  # Friday
    5: ["10:50", "14:50", "18:50"],  # Saturday
    6: ["08:50", "10:50", "18:50"],  # Sunday
}

DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ── Helpers ──


def authorized_only(func):
    """Only allow commands from the authorized chat."""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_chat.id != AUTHORIZED_CHAT_ID:
            return
        return await func(update, context)
    return wrapper


def load_posting_log() -> list[dict]:
    if not LOG_JSON.exists():
        return []
    try:
        return json.loads(LOG_JSON.read_text())
    except (json.JSONDecodeError, OSError):
        return []


def get_posted_numbers() -> set[int]:
    return {e["script_number"] for e in load_posting_log() if "script_number" in e}


def get_next_unposted(count: int = 1) -> list[tuple[int, str]]:
    """Return the next `count` unposted scripts as (number, slug) tuples."""
    posted = get_posted_numbers()
    scripts = []
    for f in sorted(SCRIPTS_DIR.glob("*.txt")):
        match = re.match(r"^(\d{3})-(.+)\.txt$", f.name)
        if not match:
            continue
        num = int(match.group(1))
        if num not in posted:
            slug = f.stem  # e.g. "005-becoming-who-you-are"
            scripts.append((num, slug))
            if len(scripts) >= count:
                break
    return scripts


def get_cumulative_cost() -> float:
    return sum(e.get("cost_usd", 0) for e in load_posting_log())


def london_now() -> datetime:
    return datetime.now(LONDON_TZ)


# ── Command Handlers ──


@authorized_only
async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        log = load_posting_log()
        posted = len(log)
        remaining = TOTAL_SCRIPTS - posted
        cost = get_cumulative_cost()
        paused = PAUSE_FILE.exists()
        now = london_now()

        # Last post info
        last_post = "None"
        if log:
            last = log[-1]
            last_post = f"{last['filename']} ({last.get('date_posted', '?')})"

        # Next script
        upcoming = get_next_unposted(1)
        next_script = upcoming[0][1] if upcoming else "All posted!"

        # Today's remaining schedule times
        today_slots = SCHEDULE.get(now.weekday(), [])
        current_time = now.strftime("%H:%M")
        remaining_slots = [t for t in today_slots if t > current_time]

        status_icon = "🔴 PAUSED" if paused else "🟢 ACTIVE"
        remaining_str = ", ".join(f"<b>{t}</b>" for t in remaining_slots) if remaining_slots else "all done for today ✨"

        # Progress bar
        pct = int(posted / TOTAL_SCRIPTS * 20)
        bar = "▓" * pct + "░" * (20 - pct)

        msg = (
            f"{status_icon}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📌 Last: <i>{last_post}</i>\n"
            f"🎬 Next: <b>{next_script}</b>\n\n"
            f"🕐 Today: {remaining_str}\n\n"
            f"📊 Progress: {posted}/{TOTAL_SCRIPTS}\n"
            f"<code>{bar}</code> {posted * 100 // TOTAL_SCRIPTS}%\n\n"
            f"💰 Total cost: ${cost:.2f}"
        )
        await update.message.reply_text(msg, parse_mode="HTML")
    except Exception as e:
        logger.exception("Error in /status")
        await update.message.reply_text(f"Error: {e}")


@authorized_only
async def cmd_resume(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not PAUSE_FILE.exists():
            await update.message.reply_text("💡 System isn't paused — all good!")
            return

        PAUSE_FILE.unlink()
        await update.message.reply_text("▶️ Pause cleared! Running auto-post now...\n\nThis may take a few minutes 🍵")

        result = subprocess.run(
            ["bash", str(PROJECT_DIR / "auto-post.sh")],
            cwd=str(PROJECT_DIR),
            capture_output=True,
            text=True,
            timeout=660,
        )

        if result.returncode == 0:
            await update.message.reply_text("✅ Post completed successfully!")
        else:
            stderr_snippet = (result.stderr or result.stdout or "No output")[-500:]
            await update.message.reply_text(f"❌ Post failed (exit {result.returncode}):\n{stderr_snippet}")
    except subprocess.TimeoutExpired:
        await update.message.reply_text("⏰ auto-post.sh timed out after 11 minutes")
    except Exception as e:
        logger.exception("Error in /resume")
        await update.message.reply_text(f"Error: {e}")


@authorized_only
async def cmd_scripts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        upcoming = get_next_unposted(2)
        if not upcoming:
            await update.message.reply_text("🎉 All 93 scripts have been posted!")
            return

        lines = ["📜 <b>Coming up next:</b>\n"]
        for i, (num, slug) in enumerate(upcoming):
            prefix = "▸" if i == 0 else "▹"
            readable = slug[4:].replace("-", " ").title()
            lines.append(f"{prefix} <b>{num:03d}</b> — {readable}")

        await update.message.reply_text("\n".join(lines), parse_mode="HTML")
    except Exception as e:
        logger.exception("Error in /scripts")
        await update.message.reply_text(f"Error: {e}")


@authorized_only
async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "🧠 <b>Carl Jung Bot — Commands</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "📊  /status — How's everything going?\n"
        "📜  /scripts — Peek at what's coming next\n"
        "▶️  /resume — Unpause and post now\n"
        "⏸️  /pause — Take a break from posting\n"
        "❓  /help — You're looking at it!\n"
    )
    await update.message.reply_text(msg, parse_mode="HTML")


@authorized_only
async def cmd_pause(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        PAUSE_FILE.touch()
        await update.message.reply_text("⏸️ System paused\n\nCron jobs will skip until you send /resume")
    except Exception as e:
        logger.exception("Error in /pause")
        await update.message.reply_text(f"Error: {e}")


# ── Application Setup ──


async def post_init(application: Application):
    """Register command menu so commands appear in Telegram UI."""
    await application.bot.set_my_commands([
        BotCommand("status", "📊 How's everything going?"),
        BotCommand("resume", "▶️ Unpause and post now"),
        BotCommand("scripts", "📜 Peek at what's coming next"),
        BotCommand("pause", "⏸️ Take a break from posting"),
        BotCommand("help", "❓ Show all commands"),
    ])
    logger.info("Bot commands registered with Telegram.")


def main():
    token = os.environ["TELEGRAM_BOT_TOKEN"]

    app = Application.builder().token(token).post_init(post_init).build()

    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("resume", cmd_resume))
    app.add_handler(CommandHandler("scripts", cmd_scripts))
    app.add_handler(CommandHandler("pause", cmd_pause))
    app.add_handler(CommandHandler("help", cmd_help))

    logger.info("Starting Caption-Gen Telegram bot (polling)...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
