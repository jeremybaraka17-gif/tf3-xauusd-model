"""
telegram_notify.py -- sends a plain-text (HTML-formatted) message to a
Telegram chat via the Bot API's `sendMessage` endpoint. Standard HTTPS
POST, stdlib only (no extra dependency) -- portable to any machine with
outbound internet access.

NOT tested end-to-end in this project: there is no real bot token or
chat ID available in this research sandbox to send an actual message
with. What IS tested (see tf3_daemon.py --dry-run) is that this function
constructs a well-formed request and handles failure paths without
crashing the caller.

To set this up for real:
  1. Message @BotFather on Telegram, /newbot, follow the prompts -- you
     get a bot token back (looks like 123456789:ABCdefGhIJKlmnOPQRstuVWXyz).
  2. Message your new bot at least once (anything), or add it to a group.
  3. Get your chat ID: message @userinfobot for a private chat, or call
     https://api.telegram.org/bot<TOKEN>/getUpdates after step 2 and read
     the chat.id field from the JSON it returns.
  4. Put both values in daemon_config.json.
"""
import json
import time
import urllib.request
import urllib.error


def send_message(bot_token, chat_id, text, max_retries=3, timeout=15):
    """Returns (success: bool, detail: str). Retries on transient
    failures with a short backoff. Does not raise -- the caller (the
    daemon) decides how loudly to fail when this returns False, since a
    failed alert is exactly the situation where an unhandled exception
    could also swallow the local log entry that's the only remaining
    record something went wrong."""
    if not bot_token or "PASTE_YOUR" in str(bot_token):
        return False, "telegram_bot_token is not configured (still the placeholder in daemon_config.json)"
    if not chat_id or "PASTE_YOUR" in str(chat_id):
        return False, "telegram_chat_id is not configured (still the placeholder in daemon_config.json)"

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = json.dumps({"chat_id": chat_id, "text": text, "parse_mode": "HTML"}).encode("utf-8")
    last_err = None
    for attempt in range(1, max_retries + 1):
        try:
            req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body = json.loads(resp.read().decode("utf-8"))
                if body.get("ok"):
                    return True, "sent"
                last_err = f"Telegram API returned ok=false: {body}"
        except urllib.error.HTTPError as e:
            try:
                detail = e.read().decode("utf-8", errors="replace")
            except Exception:
                detail = str(e)
            last_err = f"HTTP {e.code}: {detail}"
        except Exception as e:
            last_err = f"{type(e).__name__}: {e}"
        if attempt < max_retries:
            time.sleep(2 * attempt)
    return False, last_err or "unknown failure"
