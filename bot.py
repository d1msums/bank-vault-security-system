import requests
import sqlite3
import time
from datetime import datetime

BOT_TOKEN = "8912130376:AAG-teKuQoBxDHgiAe2FpvOMn0VOx5s_hos"
CHAT_ID   = "5738671708"
DB_PATH   = "vault.db"

def send_alert(user_id, risk, reason, timestamp=None):
    if timestamp is None:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Escape special Markdown characters
    def escape(text):
        return str(text).replace("_", "\\_").replace("*", "\\*").replace("`", "\\`").replace("[", "\\[")
    
    msg = (
        f"🚨 *Bank Guard Alert* 🚨\n\n"
        f"👤 *User ID:* {escape(user_id)}\n"
        f"📅 *Time:* {timestamp}\n"
        f"⚠️ *Risk:* {risk}\n"
        f"📝 *Reason:* {escape(reason)}"
    )
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": msg,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, data=payload)
        print(f"Sent to {user_id}: {response.json()}")
    except Exception as e:
        print(f"Error sending alert: {e}")

def get_last_logs(n=5):
    """Fetches the latest n logs matching your exact logs table structure."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Matches columns from your table: id, user_id, user_name, role, access_time, exit_time, session_duration, motion_detected, gas_detected, alert_triggered, risk_score
    c.execute(
        "SELECT user_name, role, access_time, alert_triggered, risk_score FROM logs "
        "ORDER BY id DESC LIMIT ?", (n,)
    )
    rows = c.fetchall()
    conn.close()
    return rows

def handle_commands():
    offset = None
    print("🤖 Bot started. Press Ctrl+C to stop.")

    while True:
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
            params = {"timeout": 10, "allowed_updates": ["message"]}
            if offset:
                params["offset"] = offset

            resp = requests.get(url, params=params, timeout=15).json()

            for update in resp.get("result", []):
                offset = update.get("update_id") + 1
                message = update.get("message", {})
                text = message.get("text", "").strip()

                if text == "/start" or text == "/help":
                    msg = "👋 *Bank Guard Bot Controller*\n\nAvailable Commands:\n`/status` - Check hardware status\n`/log` - Review latest 5 vault entries"
                    
                elif text == "/status":
                    msg = "🟢 *Vault Security System: ONLINE*\n\n🔹 PIR Motion Sensor: Active\n🔹 MQ-2 Gas Sensor: Active\n🔹 Solenoid Lock: Armed"
                    
                elif text == "/log":
                    rows = get_last_logs()
                    if not rows:
                        msg = "🗄️ Database is empty. No logs found yet."
                    else:
                        msg = "📑 *Last 5 Vault Logs:*\n\n"
                        for r in rows:
                            name = r[0] or "UNKNOWN"
                            role = r[1] or "Unknown Role"
                            time_stamp = r[2] or "N/A"
                            alert = r[3] or "None"
                            risk = r[4] or "LOW"
                            msg += f"🕒 {time_stamp}\n👤 *{name}* ({role})\n⚠️ Risk: *{risk}*\n📝 Triggered: {alert}\n\n"
                else:
                    continue  # ignore unknown commands

                requests.post(
                    f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                    data={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}
                )

        except Exception as e:
            print(f"Error: {e}")

        time.sleep(1)  # reduce to 1 second for faster response


if __name__ == '__main__':
    handle_commands()