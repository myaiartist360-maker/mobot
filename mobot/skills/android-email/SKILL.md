---
name: android-email
description: Send emails via Android email apps (Gmail, Outlook) or Termux using ADB intents or direct API.
metadata: {"mobot":{"emoji":"📧","os":["android","linux"],"requires":{"bins":["adb OR termux"]}}}
---

# Android Email Sending Skill

MOBOT can send emails on Android via three methods:
1. **Android Intent** (opens Gmail/Outlook compose screen — recommended, most reliable)
2. **Termux mail** (sends directly without opening an app — requires SMTP config)
3. **MOBOT email channel** (IMAP/SMTP configured in `~/.mobot/config.json`)

---

## Method 1: Android Intent (opens email app)

Use `send_email_intent` to open the device's default email app with pre-filled fields:

```
android_control(
  action="send_email_intent",
  to="recipient@example.com",
  subject="Hello from MOBOT",
  body="This email was sent via MOBOT's Android control."
)
```

The email app will open on screen. The user taps **Send** to complete.

### Pre-fill multiple recipients
Use comma-separated addresses in `to`:
```
android_control(action="send_email_intent", to="alice@example.com,bob@example.com", subject="Meeting Notes")
```

### Gmail-specific launch (if intent doesn't pick Gmail)
```
1. android_control(action="launch_app", package="com.google.android.gm")
2. android_control(action="tap", x=1000, y=1800)   # Tap compose FAB (bottom-right)
3. android_control(action="tap", x=540, y=400)      # Tap To: field
4. android_control(action="type_text", text="recipient@example.com")
5. android_control(action="send_key", keycode="KEYCODE_TAB")
6. android_control(action="type_text", text="Subject line here")
```

---

## Method 2: Send via Termux (direct SMTP, no UI)

If Termux has `msmtp` or `sendmail` configured:

```bash
# Install and configure msmtp first (one-time):
pkg install msmtp
# Edit ~/.msmtprc with your SMTP server details

# Then send via exec tool:
exec(command="echo 'Body text' | msmtp -a default recipient@example.com")
```

Or use Python for SMTP via exec:
```python
exec(command="""python3 -c "
import smtplib
from email.mime.text import MIMEText
msg = MIMEText('Hello from MOBOT!')
msg['Subject'] = 'Test Email'
msg['From'] = 'you@gmail.com'
msg['To'] = 'recipient@example.com'
with smtplib.SMTP_SSL('smtp.gmail.com', 465) as s:
    s.login('you@gmail.com', 'your-app-password')
    s.send_message(msg)
print('Sent!')
" """)
```

---

## Method 3: MOBOT Email Channel (IMAP/SMTP)

Configure the email channel in `~/.mobot/config.json`:
```json
{
  "channels": {
    "email": {
      "enabled": true,
      "smtp_host": "smtp.gmail.com",
      "smtp_port": 587,
      "smtp_username": "you@gmail.com",
      "smtp_password": "your-app-password",
      "from_address": "you@gmail.com"
    }
  }
}
```

Then ask MOBOT directly:
```
"Send an email to friend@example.com with subject 'Hello' and body 'Hope you are well'"
```

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Email app doesn't open | Check if `am` is available: `android_control(action="open_settings")` first |
| Intent opens wrong app | Set Gmail as default email app in Android Settings |
| Gmail compose is blank | Use `type_text` steps to fill fields manually after launch |
| SMTP auth fails | Use Gmail App Passwords (requires 2FA) or enable Less Secure Apps |
