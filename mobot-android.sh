#!/data/data/com.termux/files/usr/bin/bash
# =========================================================
# MOBOT Android Launcher
# Run this inside Termux to start MOBOT with Android env vars
# =========================================================

export MOBOT_HOME="${HOME}/.mobot"
export MOBOT_ANDROID=1

# Add Termux bin to PATH so android tools are found
export PATH="${PATH}:/data/data/com.termux/files/usr/bin"

# Pass all CLI arguments through
exec python -m mobot "$@"
