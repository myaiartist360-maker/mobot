#!/data/data/com.termux/files/usr/bin/bash
# =========================================================
# MOBOT - Android AI Assistant
# Termux Bootstrap Installer
# =========================================================
# Run this script inside Termux to install MOBOT:
#   pkg install curl git -y && curl -sSL https://raw.githubusercontent.com/myaiartist360-maker/mobot/master/install-termux.sh | bash
# =========================================================

set -e

MOBOT_REPO="https://github.com/myaiartist360-maker/mobot.git"
MOBOT_DIR="$HOME/mobot"

echo ""
echo "🤖 MOBOT Termux Installer"
echo "========================="
echo ""

# ── Step 1: Update packages ──────────────────────────────
echo "[1/6] Updating Termux packages..."
pkg update -y && pkg upgrade -y

# ── Step 2: Install Python and Git ───────────────────────
echo "[2/6] Installing Python and Git..."
# NOTE: Never run 'pip install --upgrade pip' in Termux — pip is managed by pkg
pkg install python python-pip git -y

# ── Step 3: Clone MOBOT from GitHub ──────────────────────
echo "[3/6] Cloning MOBOT from GitHub..."
if [ -d "$MOBOT_DIR" ]; then
    echo "     Found existing install at $MOBOT_DIR — updating to latest..."
    git -C "$MOBOT_DIR" fetch origin
    git -C "$MOBOT_DIR" reset --hard origin/master
else
    git clone "$MOBOT_REPO" "$MOBOT_DIR"
fi

# ── Step 4: Install MOBOT Python package ─────────────────
echo "[4/6] Installing MOBOT..."
# litellm is pinned <1.76.1 in pyproject.toml — this avoids the fastuuid dependency
# which has no pre-built ARM64 wheel and fails to compile on Termux.
# Setting ANDROID_API_LEVEL as a safety net for any other Rust-based packages.
cd "$MOBOT_DIR"
export ANDROID_API_LEVEL=24
pip install -e .

# Ensure mobot is on PATH
export PATH="$PATH:$HOME/.local/bin"
if ! grep -q '.local/bin' "$HOME/.bashrc" 2>/dev/null; then
    echo 'export PATH="$PATH:$HOME/.local/bin"' >> "$HOME/.bashrc"
fi

# ── Step 5: Termux:API for Android control ───────────────
echo "[5/6] Installing Termux:API for Android control..."
pkg install termux-api -y

echo ""
echo "  ⚠  IMPORTANT: Also install the 'Termux:API' companion app"
echo "     from F-Droid (NOT the Play Store version):"
echo "     https://f-droid.org/packages/com.termux.api/"
echo ""

# ── Step 6: Grant storage + onboard ──────────────────────
echo "[6/6] Setting up storage access and initializing MOBOT..."
termux-setup-storage || true

mobot onboard

echo ""
echo "✅ MOBOT is installed and ready!"
echo ""
echo "Quick start:"
echo "  mobot agent                          # Interactive chat"
echo "  mobot agent -m 'list my apps'        # One-shot command"
echo "  mobot agent -m 'take a screenshot'   # Android screenshot"
echo "  mobot agent -m 'open WhatsApp'       # Launch an app"
echo ""
echo "Config: ~/.mobot/config.json"
echo "  → Add your free LLM API key: https://openrouter.ai/keys"
echo ""
echo "🤖 Happy MOBOTting!"
