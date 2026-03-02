# Installing MOBOT on Android

MOBOT is an Android-friendly AI assistant forked from [NanoBot](https://github.com/HKUDS/nanobot). It runs directly on your Android device via **Termux** and can control your phone: launch apps, take screenshots, send email, navigate UI, and more.

---

## Prerequisites

| Requirement | Why |
|---|---|
| Android 7.0+ | Required by Termux |
| [Termux](https://f-droid.org/packages/com.termux/) from **F-Droid** | Terminal emulator (NOT Play Store version — it's outdated) |
| [Termux:API](https://f-droid.org/packages/com.termux.api/) from **F-Droid** | Enables screenshot, share, and other Android APIs |
| LLM API key | Get a free one at [openrouter.ai/keys](https://openrouter.ai/keys) |

> ⚠️ **Important**: Always install Termux from **F-Droid**, not the Google Play Store. The Play Store version is unmaintained.

---

## Quick Install (Recommended)

1. Open **Termux** on your Android device
2. Run the one-line installer:

```bash
curl -sSL https://raw.githubusercontent.com/your-fork/mobot/main/install-termux.sh | bash
```

This automatically:
- Updates Termux packages
- Installs Python, git, pip
- Installs `mobot-ai` package
- Installs `termux-api`
- Runs `mobot onboard`

---

## Manual Install

If you prefer step-by-step:

```bash
# 1. Update packages
pkg update && pkg upgrade -y

# 2. Install dependencies
pkg install python python-pip git -y

# 3. Install mobot-ai
pip install mobot-ai

# 4. Install Termux:API support
pkg install termux-api -y

# 5. Grant storage access (needed for screenshots)
termux-setup-storage

# 6. Initialize MOBOT
mobot onboard
```

---

## Configuration

After installing, add your LLM API key:

```bash
nano ~/.mobot/config.json
```

Add your key under `providers`:
```json
{
  "providers": {
    "openrouter": {
      "apiKey": "sk-or-your-key-here"
    }
  },
  "agents": {
    "defaults": {
      "model": "openrouter/google/gemini-2.0-flash-001"
    }
  }
}
```

Free models available at [openrouter.ai](https://openrouter.ai) — no credit card required for many.

---

## Using MOBOT

### Interactive Chat Mode
```bash
mobot agent
```

### One-shot Commands
```bash
mobot agent -m "What apps do I have installed?"
mobot agent -m "Take a screenshot and save it"
mobot agent -m "Open Gmail"
mobot agent -m "Send an email to john@example.com saying I'll be late"
```

### Android Control Examples
```
You: list all my installed apps
MOBOT: [uses android_control to list packages] Here are your installed apps: ...

You: open WhatsApp
MOBOT: [uses android_control to launch com.whatsapp] Opened WhatsApp!

You: take a screenshot and share it
MOBOT: [screenshot saved to /sdcard/DCIM/MOBOT/] Screenshot taken! Opening share sheet...

You: navigate to Settings > Wi-Fi
MOBOT: [opens settings, taps through menus] Opened Wi-Fi settings.
```

---

## Android Control Configuration

MOBOT auto-detects whether to use **ADB mode** (from a PC) or **Termux mode** (on-device). You can override in `~/.mobot/config.json`:

```json
{
  "android": {
    "mode": "termux",
    "termuxApi": true,
    "screenshotsDir": "/sdcard/DCIM/MOBOT"
  }
}
```

| Setting | Values | Default |
|---|---|---|
| `mode` | `"auto"`, `"adb"`, `"termux"` | `"auto"` |
| `termuxApi` | `true/false` | `true` |
| `screenshotsDir` | any path | `/sdcard/DCIM/MOBOT` |

---

## Using from a PC via ADB

If you want to control your phone from a PC/Mac instead:

1. Enable **USB Debugging** on your phone (Settings → Developer Options)
2. Connect via USB and run `adb devices` to verify
3. Install mobot on your PC:
   ```bash
   pip install mobot-ai
   mobot onboard
   ```
4. No extra config needed — MOBOT auto-detects ADB

```bash
# From PC terminal:
mobot agent -m "take a screenshot of my phone"
# → runs: adb shell screencap -p /sdcard/DCIM/MOBOT/mobot_screenshot.png
# → retrieves and confirms saved path
```

---

## Creating a Termux Shortcut (Widget)

To launch MOBOT from your Android home screen:

1. Install **Termux:Widget** from F-Droid
2. Create a script in `~/.shortcuts/`:
   ```bash
   mkdir -p ~/.shortcuts
   cat > ~/.shortcuts/MOBOT.sh << 'EOF'
   #!/data/data/com.termux/files/usr/bin/bash
   mobot agent
   EOF
   chmod +x ~/.shortcuts/MOBOT.sh
   ```
3. Add the **Termux:Widget** widget to your home screen
4. Tap the MOBOT shortcut to launch

---

## Troubleshooting

| Issue | Solution |
|---|---|
| `mobot: command not found` | Run `pip install mobot-ai` or check PATH: `export PATH="$PATH:~/.local/bin"` |
| Screenshots fail | Run `termux-setup-storage` and install Termux:API from F-Droid |
| `adb: not found` | Install ADB: `pkg install android-tools` (or connect via USB from PC) |
| API key error | Edit `~/.mobot/config.json` and add your key |
| App won't launch via `am start` | Some apps block intents — try tapping manually after MOBOT opens the screen |

---

## Channels (Optional)

MOBOT supports all NanoBot channels for receiving commands from:
- **Telegram** — add bot token to config, message from anywhere
- **WhatsApp** — via bridge (requires Node.js)
- **Email** — IMAP polling
- **Discord, Slack, Matrix**, etc.

See `mobot channels status` for configuration help.
