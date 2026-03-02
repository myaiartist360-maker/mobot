---
name: android-navigate
description: Navigate and launch apps on an Android device using ADB (from PC) or Termux shell (on-device).
metadata: {"mobot":{"emoji":"📱","os":["android","linux"],"requires":{"bins":["adb OR termux"]}}}
---

# Android App Navigation Skill

Use the `android_control` tool to interact with apps and the Android UI.

## Quick Start

```
Action: list_apps        → See all installed user apps
Action: launch_app       → Open a specific app by package name
Action: tap              → Tap a screen coordinate
Action: swipe            → Swipe gesture
Action: press_back       → Press the Back button
Action: press_home       → Go to the Home screen
Action: get_screen_text  → Read all visible UI text on screen
Action: open_settings    → Open Android Settings
```

## Common Package Names

| App | Package Name |
|-----|-------------|
| Gmail | com.google.android.gm |
| Chrome | com.android.chrome |
| WhatsApp | com.whatsapp |
| YouTube | com.google.android.youtube |
| Camera | com.android.camera2 |
| Files | com.google.android.documentsui |
| Maps | com.google.android.apps.maps |
| Settings | com.android.settings |
| Calculator | com.android.calculator2 |
| Contacts | com.android.contacts |

## Workflow: Open and Interact with an App

```
1. List apps: android_control(action="list_apps")
2. Launch: android_control(action="launch_app", package="com.whatsapp")
3. Read screen: android_control(action="get_screen_text")
4. Tap a button at (540, 800): android_control(action="tap", x=540, y=800)
5. Type text: android_control(action="type_text", text="Hello!")
6. Press back: android_control(action="press_back")
```

## UI Navigation

- Use `get_screen_text` to understand what's on screen before tapping
- Coordinates are in pixels; most phones are 1080×2400 or 1440×3200
- Common coordinates for swipe down (notification shade): x1=540, y1=100, x2=540, y2=800
- Swipe up (scroll): x1=540, y1=1500, x2=540, y2=500

## Mode Detection

MOBOT auto-detects whether you are using:
- **ADB mode**: `adb` is on PATH → commands prefixed with `adb shell`
- **Termux mode**: Running inside Termux on the device → commands run directly

To force a mode, set `android.mode` in `~/.mobot/config.json`.
