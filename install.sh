#!/usr/bin/env bash
set -euo pipefail

# ── Auto-detect project directory ──
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"

# ── Activate venv if present ──
if [[ -f "$PROJECT_DIR/venv/bin/activate" ]]; then
    source "$PROJECT_DIR/venv/bin/activate"
fi
SERVICE_NAME="caption-gen-bot"
SERVICE_DIR="$HOME/.config/systemd/user"
SERVICE_FILE="$SERVICE_DIR/$SERVICE_NAME.service"
CRON_MARKER="# caption-gen-autopost"

# ── Parse flags ──
ACTION="install"
DRY_RUN=false
for arg in "$@"; do
    case "$arg" in
        --uninstall) ACTION="uninstall" ;;
        --dry-run)   DRY_RUN=true ;;
        --help|-h)
            echo "Usage: install.sh [--uninstall] [--dry-run] [--help]"
            echo ""
            echo "  --uninstall  Remove cron jobs, systemd service, and pause file"
            echo "  --dry-run    Show what would be done without making changes"
            echo "  --help       Show this help message"
            exit 0
            ;;
    esac
done

# ── Helpers ──

info()  { echo "[INFO]  $*"; }
warn()  { echo "[WARN]  $*"; }
error() { echo "[ERROR] $*"; exit 1; }

source_env() {
    if [[ -f "$PROJECT_DIR/.env" ]]; then
        set -a
        source "$PROJECT_DIR/.env"
        set +a
    else
        error ".env not found at $PROJECT_DIR/.env"
    fi
}

# ── Validate Prerequisites ──

validate_prerequisites() {
    local errors=0

    info "Checking prerequisites..."

    # Python 3
    if command -v python3 >/dev/null 2>&1; then
        info "  python3: $(python3 --version 2>&1)"
    else
        echo "[FAIL]  python3 not found"; errors=$((errors+1))
    fi

    # Claude CLI
    if command -v claude >/dev/null 2>&1; then
        info "  claude CLI: found"
    else
        # Check common locations
        for p in "$HOME/.local/bin/claude" "$HOME/bin/claude" /usr/local/bin/claude; do
            if [[ -x "$p" ]]; then
                info "  claude CLI: found at $p"
                break
            fi
        done
        if ! command -v claude >/dev/null 2>&1; then
            echo "[FAIL]  claude CLI not found in PATH"; errors=$((errors+1))
        fi
    fi

    # .env keys
    source_env
    [[ -n "${ELEVENLABS_API_KEY:-}" ]]   || { echo "[FAIL]  ELEVENLABS_API_KEY not set in .env"; errors=$((errors+1)); }
    [[ -n "${UPLOAD_POST_API_KEY:-}" ]]   || { echo "[FAIL]  UPLOAD_POST_API_KEY not set in .env"; errors=$((errors+1)); }
    [[ -n "${TELEGRAM_BOT_TOKEN:-}" ]]    || { echo "[FAIL]  TELEGRAM_BOT_TOKEN not set in .env"; errors=$((errors+1)); }
    [[ -n "${TELEGRAM_CHAT_ID:-}" ]]      || { echo "[FAIL]  TELEGRAM_CHAT_ID not set in .env"; errors=$((errors+1)); }
    info "  .env keys: checked"

    # python-telegram-bot
    if python3 -c "import telegram" 2>/dev/null; then
        info "  python-telegram-bot: installed"
    else
        warn "python-telegram-bot not installed. Installing..."
        pip3 install 'python-telegram-bot>=20.0' || { echo "[FAIL]  pip install failed"; errors=$((errors+1)); }
    fi

    # python-dotenv
    if python3 -c "from dotenv import load_dotenv" 2>/dev/null; then
        info "  python-dotenv: installed"
    else
        warn "python-dotenv not installed. Installing..."
        pip3 install python-dotenv || { echo "[FAIL]  pip install failed"; errors=$((errors+1)); }
    fi

    if (( errors > 0 )); then
        error "Fix the above $errors error(s) and re-run."
    fi

    info "All prerequisites satisfied."
}

# ── Install Cron Jobs ──

install_cron() {
    info "Installing cron jobs (21 entries, TZ=Europe/London)..."

    local auto_post="$PROJECT_DIR/auto-post.sh"

    # Remove existing entries first (idempotent)
    (crontab -l 2>/dev/null | grep -v "$CRON_MARKER") | crontab - 2>/dev/null || true

    local log="$PROJECT_DIR/posting.log"

    # Build cron block
    local CRON_BLOCK
    CRON_BLOCK="$CRON_MARKER
TZ=Europe/London
50 6 * * 1  $auto_post >> $log 2>&1  $CRON_MARKER
50 16 * * 1 $auto_post >> $log 2>&1  $CRON_MARKER
50 18 * * 1 $auto_post >> $log 2>&1  $CRON_MARKER
50 6 * * 2  $auto_post >> $log 2>&1  $CRON_MARKER
50 16 * * 2 $auto_post >> $log 2>&1  $CRON_MARKER
50 19 * * 2 $auto_post >> $log 2>&1  $CRON_MARKER
50 6 * * 3  $auto_post >> $log 2>&1  $CRON_MARKER
50 14 * * 3 $auto_post >> $log 2>&1  $CRON_MARKER
50 16 * * 3 $auto_post >> $log 2>&1  $CRON_MARKER
50 8 * * 4  $auto_post >> $log 2>&1  $CRON_MARKER
50 16 * * 4 $auto_post >> $log 2>&1  $CRON_MARKER
50 18 * * 4 $auto_post >> $log 2>&1  $CRON_MARKER
50 6 * * 5  $auto_post >> $log 2>&1  $CRON_MARKER
50 12 * * 5 $auto_post >> $log 2>&1  $CRON_MARKER
50 18 * * 5 $auto_post >> $log 2>&1  $CRON_MARKER
50 10 * * 6 $auto_post >> $log 2>&1  $CRON_MARKER
50 14 * * 6 $auto_post >> $log 2>&1  $CRON_MARKER
50 18 * * 6 $auto_post >> $log 2>&1  $CRON_MARKER
50 8 * * 0  $auto_post >> $log 2>&1  $CRON_MARKER
50 10 * * 0 $auto_post >> $log 2>&1  $CRON_MARKER
50 18 * * 0 $auto_post >> $log 2>&1  $CRON_MARKER"

    # Append to existing crontab
    (crontab -l 2>/dev/null; echo "$CRON_BLOCK") | crontab -

    local count
    count=$(crontab -l 2>/dev/null | grep -c "$CRON_MARKER" || true)
    info "  Installed $count cron entries."
}

# ── Install Systemd Service ──

install_systemd() {
    info "Installing systemd user service..."

    mkdir -p "$SERVICE_DIR"

    local python_path
    python_path=$(which python3)

    cat > "$SERVICE_FILE" << EOF
[Unit]
Description=Caption Gen Telegram Bot
After=network.target

[Service]
Type=simple
WorkingDirectory=$PROJECT_DIR
ExecStart=$python_path $PROJECT_DIR/telegram_bot.py
Restart=always
RestartSec=10
EnvironmentFile=$PROJECT_DIR/.env

[Install]
WantedBy=default.target
EOF

    # Enable linger so user services run without active login (critical for VPS)
    if command -v loginctl >/dev/null 2>&1; then
        loginctl enable-linger "$USER" 2>/dev/null || warn "Could not enable linger. User services may not run without login."
    fi

    systemctl --user daemon-reload
    systemctl --user enable --now "$SERVICE_NAME"

    info "  Service installed and started."
}

# ── Uninstall ──

uninstall() {
    info "Uninstalling caption-gen automation..."

    # Remove cron entries
    (crontab -l 2>/dev/null | grep -v "$CRON_MARKER") | crontab - 2>/dev/null || true
    info "  Cron entries removed."

    # Stop and remove systemd service
    systemctl --user stop "$SERVICE_NAME" 2>/dev/null || true
    systemctl --user disable "$SERVICE_NAME" 2>/dev/null || true
    rm -f "$SERVICE_FILE"
    systemctl --user daemon-reload 2>/dev/null || true
    info "  Systemd service removed."

    # Remove pause file
    rm -f "$HOME/.caption-gen-paused"
    info "  Pause file removed."

    info "Uninstall complete. Posting logs preserved."
}

# ── Print Summary ──

print_summary() {
    echo ""
    echo "═══════════════════════════════════════════"
    echo "  Caption-Gen Automation — Installed"
    echo "═══════════════════════════════════════════"
    echo ""

    # Schedule
    echo "Schedule (Europe/London):"
    echo "  Mon: 06:50, 16:50, 18:50"
    echo "  Tue: 06:50, 16:50, 19:50"
    echo "  Wed: 06:50, 14:50, 16:50"
    echo "  Thu: 08:50, 16:50, 18:50"
    echo "  Fri: 06:50, 12:50, 18:50"
    echo "  Sat: 10:50, 14:50, 18:50"
    echo "  Sun: 08:50, 10:50, 18:50"
    echo ""

    # Cron count
    local cron_count
    cron_count=$(crontab -l 2>/dev/null | grep -c "$CRON_MARKER" || true)
    echo "Cron entries: $cron_count"

    # Service status
    echo "Bot service: $(systemctl --user is-active "$SERVICE_NAME" 2>/dev/null || echo "unknown")"

    # Remaining scripts
    local remaining
    remaining=$(python3 -c "
import json
try:
    print(93 - len(json.load(open('$PROJECT_DIR/posting_log.json'))))
except Exception:
    print(93)
")
    echo "Scripts remaining: $remaining/93"
    echo ""

    echo "Commands:"
    echo "  Manual post:    bash auto-post.sh"
    echo "  Dry run:        bash auto-post.sh --dry-run"
    echo "  Uninstall:      bash install.sh --uninstall"
    echo "  Bot logs:       journalctl --user -u $SERVICE_NAME -f"
    echo ""

    echo "Telegram commands: /status /resume /scripts /pause"
    echo ""
}

# ── Main ──

case "$ACTION" in
    uninstall)
        uninstall
        ;;
    install)
        if [[ "$DRY_RUN" == "true" ]]; then
            info "DRY RUN — would perform the following:"
            info "  1. Validate prerequisites (python3, claude, .env keys)"
            info "  2. Install 21 cron entries with TZ=Europe/London"
            info "  3. Install systemd user service for telegram_bot.py"
            info "  4. Enable loginctl linger for $USER"
            info "  5. Run auto-post.sh --dry-run"
            info "  6. Send test Telegram message"
            exit 0
        fi

        validate_prerequisites

        # Make scripts executable
        chmod +x "$PROJECT_DIR/auto-post.sh"

        install_cron
        install_systemd

        # Run dry-run test
        info "Running dry-run test..."
        bash "$PROJECT_DIR/auto-post.sh" --dry-run || warn "Dry-run had issues. Check above output."

        # Send test Telegram message
        source_env
        curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
            -d chat_id="$TELEGRAM_CHAT_ID" \
            -d text="Caption-gen bot installed and ready on $(hostname)!" > /dev/null 2>&1 || warn "Could not send test Telegram message."

        print_summary
        ;;
esac
