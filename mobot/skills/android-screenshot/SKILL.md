---
name: android-screenshot
description: Take, retrieve, and share screenshots on an Android device using ADB or Termux:API.
metadata: {"mobot":{"emoji":"📸","os":["android","linux"],"requires":{"bins":["adb OR termux-screenshot"]}}}
---

# Android Screenshot Skill

Use the `android_control` tool with `action="screenshot"` to capture the device screen.

## Take a Screenshot

```
android_control(action="screenshot")
# Saves to /sdcard/DCIM/MOBOT/mobot_screenshot.png

android_control(action="screenshot", filename="my_capture")
# Saves to /sdcard/DCIM/MOBOT/my_capture.png
```

## Retrieve & Share the Screenshot

### From a PC via ADB
```bash
# Pull screenshot to your PC:
adb pull /sdcard/DCIM/MOBOT/mobot_screenshot.png .

# Or pull with custom name:
adb pull /sdcard/DCIM/MOBOT/my_capture.png ./capture.png
```

### On-device via Termux (share via Android share sheet)
```
android_control(action="share_file", file_path="/sdcard/DCIM/MOBOT/mobot_screenshot.png")
```
This opens the Android share sheet — you can then send via WhatsApp, Gmail, etc.

### On-device via Termux (save to gallery)
Screenshots are saved to `/sdcard/DCIM/MOBOT/` which is visible in your Photos app.

## Full Workflow Examples

### Capture & Share via WhatsApp
```
1. android_control(action="screenshot", filename="share_now")
2. android_control(action="share_file", file_path="/sdcard/DCIM/MOBOT/share_now.png")
3. In the share sheet, choose WhatsApp and select a contact
```

### Capture & Email via Gmail
```
1. android_control(action="screenshot", filename="email_attach")
2. android_control(action="launch_app", package="com.google.android.gm")
3. android_control(action="send_email_intent", to="friend@example.com", subject="Screenshot", body="See attached screenshot")
# Note: attach the file manually from the Gmail compose screen
```

## Requirements

| Mode | Requirement |
|------|------------|
| Termux (preferred) | `pkg install termux-api && apt install termux-api` + Termux:API app from F-Droid |
| ADB from PC | `adb` in PATH, USB debugging enabled on phone |
| Fallback | `screencap` (may need root on some devices) |

## Troubleshooting

- **Permission denied**: Run `termux-setup-storage` in Termux to grant storage access
- **screencap blank/error**: Try via ADB (`adb exec-out screencap -p > screenshot.png`) from your PC
- **Termux:API not found**: Install both the Termux:API package (`pkg install termux-api`) AND the Termux:API Android app from F-Droid
