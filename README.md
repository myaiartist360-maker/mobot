<div align="center">
  <h1>🤖 MOBOT: Android-Friendly AI Assistant</h1>
  <p>
    <a href="https://github.com/myaiartist360-maker/mobot"><img src="https://img.shields.io/badge/GitHub-mobot-181717?style=flat&logo=github" alt="GitHub"></a>
    <img src="https://img.shields.io/badge/python-≥3.11-blue" alt="Python">
    <img src="https://img.shields.io/badge/license-MIT-green" alt="License">
    <img src="https://img.shields.io/badge/Android-Termux-A4C639?style=flat&logo=android&logoColor=white" alt="Android">
    <img src="https://img.shields.io/badge/ADB-Supported-00B0FF?style=flat" alt="ADB">
  </p>
</div>

🤖 **MOBOT** is an **Android-friendly personal AI assistant** forked from [NanoBot](https://github.com/HKUDS/nanobot). It runs directly on your Android device via **Termux** and can control your phone — launch apps, take screenshots, send email, navigate UI, and more.

⚡️ Ultra-lightweight: ~4,000 lines of core agent code, full LLM tool loop, persistent memory, and multi-channel support.

📱 **New in MOBOT**: Direct Android device control via ADB or Termux — no root required.

---

## ✨ Key Features

🤖 **Android Control**: Launch apps, tap/swipe, screenshot, send email, share files — all via natural language.

🪶 **Ultra-Lightweight**: ~4,000 lines of core code. Easy to read, modify, and extend.

⚡️ **Fast**: Minimal footprint means faster startup, lower memory, quicker responses.

📱 **Termux Native**: Runs directly on your Android phone via Termux — no PC needed.

🔌 **Multi-Channel**: Telegram, WhatsApp, Discord, Slack, Email, DingTalk, QQ, Feishu, Matrix.

🛠️ **MCP Support**: Plug in any Model Context Protocol server as native agent tools.

---

## 🏗️ Architecture

```
Your Phone / PC
     │
     ▼
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│  Chat Apps  │────▶│  Agent Loop  │────▶│   LLM Provider  │
│  Telegram   │     │  (mobot/)    │◀────│  OpenRouter/    │
│  WhatsApp   │     └──────┬───────┘     │  Gemini/Claude  │
│  CLI/Termux │            │             └─────────────────┘
└─────────────┘     ┌──────▼───────┐
                    │    Tools     │
                    │ • android_control  ← NEW
                    │ • exec / shell
                    │ • web search
                    │ • file system
                    │ • cron / schedule
                    └──────────────┘
```

---

## 📱 Android Control Capabilities

MOBOT adds a new `android_control` tool with **13 actions**:

| Action | What it does |
|---|---|
| `list_apps` | List all installed user apps |
| `launch_app` | Open an app by package name |
| `tap` | Tap screen at (x, y) |
| `swipe` | Swipe gesture between two points |
| `screenshot` | Capture screen → `/sdcard/DCIM/MOBOT/` |
| `get_screen_text` | Read current UI text via uiautomator |
| `send_key` | Send keyevent (HOME, BACK, POWER, etc.) |
| `send_email_intent` | Open email compose via Android Intent |
| `type_text` | Type text into focused field |
| `press_back` | Press Back button |
| `press_home` | Go to Home screen |
| `open_settings` | Open Android Settings |
| `share_file` | Open Android share sheet for a file |

**Works in two modes:**
- **Termux mode** — running directly on the device (auto-detected via `$PREFIX`)
- **ADB mode** — controlling phone from a PC (`adb` on PATH)

---

## 📦 Install

### 📱 On Android (Termux) — Recommended

> Install [Termux](https://f-droid.org/packages/com.termux/) and [Termux:API](https://f-droid.org/packages/com.termux.api/) from **F-Droid** first (NOT Play Store).

**One-liner:**
```bash
pkg install curl git -y && curl -sSL https://raw.githubusercontent.com/myaiartist360-maker/mobot/master/install-termux.sh | bash
```

**Or step-by-step:**
```bash
pkg update && pkg upgrade -y
pkg install git python python-pip termux-api -y

# Grant storage access (for screenshots)
termux-setup-storage

# Clone and install from source (not on PyPI yet)
git clone https://github.com/myaiartist360-maker/mobot.git
cd mobot
export ANDROID_API_LEVEL=24   # safety net for any Rust-based build tools
pip install -e .

# Add mobot to PATH
export PATH="$PATH:$HOME/.local/bin"
echo 'export PATH="$PATH:$HOME/.local/bin"' >> ~/.bashrc

mobot onboard
```

> ⚠️ **Never run `pip install --upgrade pip` in Termux** — pip is managed by `pkg`.

### 💻 On PC (control phone via ADB)

```bash
# mobot-ai is not on PyPI yet — install from source
git clone https://github.com/myaiartist360-maker/mobot.git
cd mobot
pip install -e .
mobot onboard
# Connect phone via USB with USB Debugging enabled
mobot agent -m "take a screenshot of my phone"
```

---


## 🚀 Quick Start

> [!TIP]
> Set your API key in `~/.mobot/config.json`.
> Get a free API key at [openrouter.ai/keys](https://openrouter.ai/keys) — many models need no credit card.

**1. Initialize**

```bash
mobot onboard
```

**2. Configure** (`~/.mobot/config.json`)

```json
{
  "providers": {
    "openrouter": {
      "apiKey": "sk-or-v1-xxx"
    }
  },
  "agents": {
    "defaults": {
      "model": "openrouter/google/gemini-2.0-flash-001"
    }
  }
}
```

**3. Chat**

```bash
mobot agent
```

**4. Try Android control**

```bash
mobot agent -m "list all my installed apps"
mobot agent -m "open WhatsApp"
mobot agent -m "take a screenshot and save it"
mobot agent -m "send an email to john@example.com saying I'll be late"
```

---

## 💬 Chat Apps

Connect MOBOT to your favorite messaging platform.

| Channel | What you need |
|---------|---------------|
| **Telegram** | Bot token from @BotFather |
| **Discord** | Bot token + Message Content intent |
| **WhatsApp** | QR code scan (Node.js ≥18 required) |
| **Feishu** | App ID + App Secret |
| **DingTalk** | App Key + App Secret |
| **Slack** | Bot token + App-Level token |
| **Email** | IMAP/SMTP credentials |
| **QQ** | App ID + App Secret |
| **Matrix** | Access token + homeserver |

<details>
<summary><b>Telegram</b> (Recommended)</summary>

**1. Create a bot**
- Open Telegram, search `@BotFather`
- Send `/newbot`, follow prompts, copy the token

**2. Configure** (`~/.mobot/config.json`)

```json
{
  "channels": {
    "telegram": {
      "enabled": true,
      "token": "YOUR_BOT_TOKEN",
      "allowFrom": ["YOUR_USER_ID"]
    }
  }
}
```

**3. Run**

```bash
mobot gateway
```

</details>

<details>
<summary><b>WhatsApp</b></summary>

Requires **Node.js ≥18**.

```bash
mobot channels login   # Scan QR code
mobot gateway          # Start gateway
```

```json
{
  "channels": {
    "whatsapp": {
      "enabled": true,
      "allowFrom": ["+1234567890"]
    }
  }
}
```

</details>

<details>
<summary><b>Discord</b></summary>

**1.** Go to [discord.com/developers](https://discord.com/developers/applications) → Create app → Bot → Copy token

**2.** Enable **MESSAGE CONTENT INTENT** in Bot settings

**3. Configure:**
```json
{
  "channels": {
    "discord": {
      "enabled": true,
      "token": "YOUR_BOT_TOKEN",
      "allowFrom": ["YOUR_USER_ID"]
    }
  }
}
```

**4. Run:** `mobot gateway`

</details>

<details>
<summary><b>Email</b></summary>

```json
{
  "channels": {
    "email": {
      "enabled": true,
      "consentGranted": true,
      "imapHost": "imap.gmail.com",
      "imapPort": 993,
      "imapUsername": "my-mobot@gmail.com",
      "imapPassword": "your-app-password",
      "smtpHost": "smtp.gmail.com",
      "smtpPort": 587,
      "smtpUsername": "my-mobot@gmail.com",
      "smtpPassword": "your-app-password",
      "fromAddress": "my-mobot@gmail.com",
      "allowFrom": ["your-email@gmail.com"]
    }
  }
}
```

Run: `mobot gateway`

</details>

<details>
<summary><b>Slack, Feishu, DingTalk, QQ, Matrix</b></summary>

These work the same as NanoBot — replace all `nanobot gateway` commands with `mobot gateway` and config paths from `~/.nanobot/` to `~/.mobot/`.

Full channel documentation: see original [NanoBot README](https://github.com/HKUDS/nanobot#-chat-apps).

</details>

---

## ⚙️ Configuration

Config file: `~/.mobot/config.json`

### Providers

| Provider | Get API Key |
|----------|-------------|
| `openrouter` | [openrouter.ai](https://openrouter.ai) (recommended) |
| `anthropic` | [console.anthropic.com](https://console.anthropic.com) |
| `openai` | [platform.openai.com](https://platform.openai.com) |
| `gemini` | [aistudio.google.com](https://aistudio.google.com) |
| `deepseek` | [platform.deepseek.com](https://platform.deepseek.com) |
| `groq` | [console.groq.com](https://console.groq.com) |
| `custom` | Any OpenAI-compatible endpoint |
| `vllm` | Local self-hosted model |

### Android Config

```json
{
  "android": {
    "mode": "auto",
    "adbHost": "localhost",
    "adbPort": 5037,
    "adbSerial": "",
    "termuxApi": true,
    "screenshotsDir": "/sdcard/DCIM/MOBOT"
  }
}
```

| Option | Values | Default |
|--------|--------|---------|
| `mode` | `"auto"`, `"adb"`, `"termux"` | `"auto"` |
| `termuxApi` | `true/false` | `true` |
| `screenshotsDir` | Any device path | `/sdcard/DCIM/MOBOT` |

### MCP (Model Context Protocol)

```json
{
  "tools": {
    "mcpServers": {
      "filesystem": {
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/dir"]
      }
    }
  }
}
```

---

## 🖥️ CLI Reference

| Command | Description |
|---------|-------------|
| `mobot onboard` | Initialize config & workspace |
| `mobot agent` | Interactive chat |
| `mobot agent -m "..."` | One-shot message |
| `mobot agent --no-markdown` | Plain text output |
| `mobot agent --logs` | Show runtime logs |
| `mobot gateway` | Start gateway (all channels) |
| `mobot channels status` | Show channel status |
| `mobot channels login` | Link WhatsApp (QR scan) |
| `mobot cron list` | List scheduled tasks |
| `mobot cron add ...` | Add a cron job |
| `mobot --version` | Show version |

---

## 🐳 Docker

```bash
# First-time setup
docker compose run --rm mobot-cli onboard
vim ~/.mobot/config.json   # add API keys

# Start gateway
docker compose up -d mobot-gateway

# CLI usage
docker compose run --rm mobot-cli agent -m "Hello!"
docker compose logs -f mobot-gateway
```

---

## 🐧 Linux / Android Service

Run MOBOT as a background service:

**systemd (Linux):**
```ini
# ~/.config/systemd/user/mobot-gateway.service
[Unit]
Description=MOBOT Gateway
After=network.target

[Service]
Type=simple
ExecStart=%h/.local/bin/mobot gateway
Restart=always
RestartSec=10

[Install]
WantedBy=default.target
```

```bash
systemctl --user enable --now mobot-gateway
```

**Termux background (Android):**
```bash
# Run in background with nohup
nohup mobot gateway > ~/mobot.log 2>&1 &

# Or use Termux:Boot to auto-start
mkdir -p ~/.termux/boot
echo "mobot gateway >> ~/mobot.log 2>&1" > ~/.termux/boot/start-mobot.sh
chmod +x ~/.termux/boot/start-mobot.sh
```

---

## 🔧 Troubleshooting on Android

| Problem | Fix |
|---------|-----|
| **`pip install --upgrade pip` is forbidden** | Termux manages pip via `pkg`. Never run `pip install --upgrade pip`. Use `pkg install python-pip` instead |
| **`fastuuid` build error** during `pip install` | Run `pkg install rust -y` first, then retry `MATHLIB="" pip install -e .` |
| `mobot: command not found` | Add to PATH: `echo 'export PATH="$PATH:$HOME/.local/bin"' >> ~/.bashrc && source ~/.bashrc` |
| `pkg install` fails | Run `pkg update && pkg upgrade -y` first |
| Screenshot is blank/fails | Install Termux:API from F-Droid AND run `pkg install termux-api` |
| Storage permission denied | Run `termux-setup-storage` and tap Allow |
| `git clone` slow/fails | Check Wi-Fi; try `pkg install git` to reinstall |
| `pip install` very slow | Add `--no-cache-dir` flag; if Rust is compiling, it can take 10–20 min |
| App won't launch via `launch_app` | Try `get_screen_text` first to confirm the package name |
| ADB not found | Run `pkg install android-tools` (on Termux) or install ADB on PC |

---

## 📁 Project Structure

```
mobot/                     ← Main package (renamed from nanobot/)
├── agent/
│   ├── loop.py            ← Core agent loop
│   ├── context.py         ← Prompt builder
│   ├── memory.py          ← Persistent memory
│   └── tools/
│       ├── android.py     ← NEW: Android device control
│       ├── shell.py       ← Shell execution
│       ├── web.py         ← Web search/fetch
│       └── filesystem.py  ← File operations
├── skills/
│   ├── android-navigate/  ← NEW: App navigation skill
│   ├── android-screenshot/← NEW: Screenshot skill
│   ├── android-email/     ← NEW: Email skill
│   └── ...                ← github, weather, tmux, memory...
├── channels/              ← Telegram, Discord, WhatsApp, etc.
├── config/                ← Schema with AndroidConfig
└── cli/                   ← CLI commands

install-termux.sh          ← Android one-liner installer
mobot-android.sh           ← Android launcher script
INSTALL_ANDROID.md         ← Full Android install guide
```

---

## 🤝 Contribute

PRs welcome! The codebase is intentionally small and readable.

**Roadmap:**
- [ ] Screenshot sharing via Telegram/WhatsApp channels
- [ ] Voice command support (Whisper → Android control)
- [ ] On-device vision (screenshot + describe screen)
- [ ] Multi-modal: see and respond to images
- [ ] Long-term memory improvements

---

<p align="center">
  <em>🤖 MOBOT — Your Android AI Assistant</em><br><br>
  Forked from <a href="https://github.com/HKUDS/nanobot">NanoBot</a> · MIT License
</p>
