#!/usr/bin/env bash
set -euo pipefail

# ── Project directory (auto-detect from script location) ──
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"

# ── PATH augmentation for cron environment ──
export PATH="$HOME/.local/bin:$HOME/bin:/usr/local/bin:/usr/bin:/bin:$PATH"
# Expand nvm node paths if they exist
for d in "$HOME"/.nvm/versions/node/*/bin; do
    [ -d "$d" ] && export PATH="$d:$PATH"
done

# ── Constants ──
PAUSE_FILE="$HOME/.caption-gen-paused"
LOG_JSON="$PROJECT_DIR/posting_log.json"
LOG_TEXT="$PROJECT_DIR/posting.log"
TOTAL_SCRIPTS=93
LOCK_FILE="/tmp/caption-gen.lock"
CLAUDE_OUTPUT=$(mktemp /tmp/caption-gen-claude-XXXXXX.txt)
trap 'rm -f "$CLAUDE_OUTPUT"' EXIT

# ── Parse flags ──
DRY_RUN=false
[[ "${1:-}" == "--dry-run" ]] && DRY_RUN=true

# ── Load .env ──
if [[ -f "$PROJECT_DIR/.env" ]]; then
    set -a
    source "$PROJECT_DIR/.env"
    set +a
else
    echo "ERROR: .env not found at $PROJECT_DIR/.env"
    exit 1
fi

# ── Concurrency lock ──
exec 200>"$LOCK_FILE"
flock -n 200 || { echo "Another instance is running, skipping."; exit 0; }

# ── Functions ──

html_escape() {
    local text="$1"
    text="${text//&/&amp;}"
    text="${text//</&lt;}"
    text="${text//>/&gt;}"
    echo "$text"
}

send_telegram() {
    local message="$1"
    if [[ -z "${TELEGRAM_BOT_TOKEN:-}" || -z "${TELEGRAM_CHAT_ID:-}" ]]; then
        echo "WARN: Telegram not configured, skipping notification."
        return 0
    fi
    curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
        -d chat_id="$TELEGRAM_CHAT_ID" \
        -d text="$message" \
        -d parse_mode="HTML" > /dev/null 2>&1 || true
}

count_log_entries() {
    python3 -c "
import json, sys
try:
    entries = json.load(open('$LOG_JSON'))
    print(len(entries))
except Exception:
    print(0)
"
}

get_cumulative_cost() {
    python3 -c "
import json
try:
    entries = json.load(open('$LOG_JSON'))
    total = sum(e.get('cost_usd', 0) for e in entries)
    print(f'{total:.2f}')
except Exception:
    print('0.00')
"
}

get_remaining() {
    local count
    count=$(count_log_entries)
    echo $(( TOTAL_SCRIPTS - count ))
}

get_last_entry() {
    python3 -c "
import json
try:
    entries = json.load(open('$LOG_JSON'))
    if entries:
        e = entries[-1]
        print(f\"{e.get('filename', 'unknown')}|{e.get('cost_usd', 0):.4f}|{e.get('characters_used', 0)}\")
    else:
        print('none|0|0')
except Exception:
    print('error|0|0')
"
}

extract_caption() {
    local output_file="$1"
    # Try to extract caption from Claude's "--- Post Complete ---" summary
    # Look for "Caption:" line and grab everything until the next known field
    local caption
    caption=$(sed -n '/^Caption:/,/^\(ElevenLabs cost:\|Status:\|Remaining:\|---\)/{ /^Caption:/{ s/^Caption: *//; p; }; /^\(ElevenLabs cost:\|Status:\|Remaining:\|---\)/!{ /^Caption:/!p; }; }' "$output_file" 2>/dev/null | head -10)
    if [[ -z "$caption" ]]; then
        # Fallback: try to find hashtag lines as caption indicator
        caption=$(grep -E '#CarlJung|#Psychology|#ShadowWork' "$output_file" 2>/dev/null | head -3)
    fi
    if [[ -z "$caption" ]]; then
        caption="[caption not extracted]"
    fi
    echo "$caption"
}

append_text_log() {
    local status="$1"
    local details="$2"
    local timestamp
    timestamp=$(TZ=Europe/London date '+%Y-%m-%d %H:%M')
    echo "[$timestamp] $status $details" >> "$LOG_TEXT"
}

# ── Main flow ──

cd "$PROJECT_DIR"

# 1. Check pause file
if [[ -f "$PAUSE_FILE" ]]; then
    exit 0
fi

# 2. Check if all scripts already posted
count_before=$(count_log_entries)
if (( count_before >= TOTAL_SCRIPTS )); then
    send_telegram "🎉🎉🎉 <b>All $TOTAL_SCRIPTS scripts posted!</b>

What a journey! Every Carl Jung script has found its audience. The posting system is now paused.

✨ Schedule complete — thank you, Jung!"
    touch "$PAUSE_FILE"
    append_text_log "COMPLETE" "All $TOTAL_SCRIPTS scripts posted. System paused."
    exit 0
fi

# 3. Git pull (stash local changes first if needed)
git_pull_output=""
if ! git_pull_output=$(git pull --rebase 2>&1); then
    # Try stashing uncommitted changes and retrying
    git stash 2>/dev/null || true
    if ! git_pull_output=$(git pull --rebase 2>&1); then
        git stash pop 2>/dev/null || true
        error_msg=$(html_escape "Git pull failed: $git_pull_output")
        send_telegram "🚨 <b>Posting Failed</b>

$error_msg

⏸️ System paused — send /resume to retry"
        touch "$PAUSE_FILE"
        append_text_log "FAILED" "Git pull failed: $git_pull_output"
        exit 1
    fi
    git stash pop 2>/dev/null || true
fi

# 4. Dry-run mode
if [[ "$DRY_RUN" == "true" ]]; then
    remaining=$(get_remaining)
    cumulative=$(get_cumulative_cost)
    send_telegram "🧪 <b>Dry Run Complete</b>

📝 Would post the next script
📦 Remaining: $remaining / $TOTAL_SCRIPTS
💰 Total cost so far: \$$cumulative

Everything looks good! ✨"
    append_text_log "DRY-RUN" "remaining=$remaining cost=\$$cumulative"
    echo "Dry run complete. Telegram notification sent."
    exit 0
fi

# 5. Run claude -p "/post-next"
echo "Invoking claude -p /post-next ..."
set +e
timeout 600 claude -p "/post-next" > "$CLAUDE_OUTPUT" 2>&1
claude_exit=$?
set -e

# 6. Check success by comparing log entry count
count_after=$(count_log_entries)

if (( count_after > count_before )); then
    # ── SUCCESS ──
    IFS='|' read -r script_slug cost_usd chars_used <<< "$(get_last_entry)"
    remaining=$(get_remaining)
    cumulative=$(get_cumulative_cost)
    caption=$(extract_caption "$CLAUDE_OUTPUT")
    caption_escaped=$(html_escape "$caption")

    # Send Telegram notification
    tg_message="✅ <b>New Post Live!</b>

🎬 <b>$script_slug</b>

💬 <i>$caption_escaped</i>

💰 Cost: \$$cost_usd · Total: \$$cumulative
📦 Remaining: $remaining / $TOTAL_SCRIPTS"

    send_telegram "$tg_message"

    # Append to text log
    append_text_log "SUCCESS" "$script_slug chars=$chars_used cost=\$$cost_usd total=\$$cumulative remaining=$remaining"

    # Git commit and push
    git add posting_log.json 2>/dev/null || true
    git commit -m "post: $script_slug" 2>/dev/null || true
    if ! git push 2>/dev/null; then
        send_telegram "⚠️ Git push failed for <b>$script_slug</b> — post is live but log not synced to remote"
        append_text_log "WARN" "Git push failed for $script_slug"
    fi

    # Check if that was the last one
    if (( remaining == 0 )); then
        send_telegram "🎉🎉🎉 <b>All $TOTAL_SCRIPTS scripts posted!</b>

What a journey! Every Carl Jung script has found its audience. The posting system is now paused.

✨ Schedule complete — thank you, Jung!"
        touch "$PAUSE_FILE"
        append_text_log "COMPLETE" "All $TOTAL_SCRIPTS scripts posted. System paused."
    fi

    echo "Post successful: $script_slug"
else
    # ── FAILURE ──
    touch "$PAUSE_FILE"

    # Extract error snippet from claude output
    error_snippet=$(tail -20 "$CLAUDE_OUTPUT" 2>/dev/null | head -10)
    if [[ -z "$error_snippet" ]]; then
        if (( claude_exit == 124 )); then
            error_snippet="Claude timed out after 600 seconds."
        else
            error_snippet="Claude exited with code $claude_exit. No output captured."
        fi
    fi

    error_escaped=$(html_escape "$(echo "$error_snippet" | head -5)")
    send_telegram "🚨 <b>Posting Failed</b>

Something went wrong:
<pre>$error_escaped</pre>

⏸️ System paused — send /resume to retry"

    append_text_log "FAILED" "claude_exit=$claude_exit error=$(echo "$error_snippet" | head -1)"
    append_text_log "PAUSED" "System paused after failure. Awaiting /resume."

    echo "Post failed. System paused. Check Telegram for details."
    exit 1
fi
