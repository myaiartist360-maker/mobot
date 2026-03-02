#!/data/data/com.termux/files/usr/bin/bash
# =========================================================
# MOBOT - Android AI Assistant
# Termux Bootstrap Installer
# =========================================================
# Run this script inside Termux to install MOBOT:
#   curl -sSL https://raw.githubusercontent.com/your-fork/mobot/main/install-termux.sh | bash
# =========================================================

set -e

echo ""
echo "🤖 MOBOT Termux Installer"
echo "========================="
echo ""

# ── Step 1: Update packages ──────────────────────────────
echo "[1/6] Updating Termux packages..."
pkg update -y && pkg upgrade -y

# ── Step 2: Install Python and Git ───────────────────────
echo "[2/6] Installing Python, Git, and build tools..."
pkg install python python-pip git binutils -y

# ── Step 3: Install MOBOT ────────────────────────────────
echo "[3/6] Installing MOBOT..."
pip install --upgrade pip
pip install mobot-ai

# ── Step 4: Optional Termux:API (Android control) ────────
echo "[4/6] Installing Termux:API for enhanced Android control..."
pkg install termux-api -y

echo ""
echo "  ⚠  IMPORTANT: Also install the 'Termux:API' companion app"
echo "     from F-Droid (NOT the Play Store version):"
echo "     https://f-droid.org/packages/com.termux.api/"
echo ""
read -p "     Press Enter when done (or Ctrl+C to skip)..." ignored

# ── Step 5: Grant storage access ─────────────────────────
echo "[5/6] Setting up storage access..."
termux-setup-storage || true

# ── Step 6: Onboard MOBOT ────────────────────────────────
echo "[6/6] Initializing MOBOT configuration..."
mobot onboard

echo ""
echo "✅ MOBOT is installed and ready!"
echo ""
echo "Quick start:"
echo "  mobot agent                         # Interactive chat"
echo "  mobot agent -m 'list my apps'       # One-shot command"
echo "  mobot agent -m 'take a screenshot'  # Android screenshot"
echo ""
echo "Config file: ~/.mobot/config.json"
echo "  → Add your LLM API key (get one free at https://openrouter.ai/keys)"
echo ""
echo "🤖 Happy MOBOTting!"
