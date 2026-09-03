import sqlite3
import random
from datetime import datetime, timedelta

DB = r"C:\Users\sofea\bank_guard\vault.db"

conn = sqlite3.connect(DB)
cursor = conn.cursor()

# Drop and recreate
cursor.execute("DROP TABLE IF EXISTS logs")
cursor.execute("DROP TABLE IF EXISTS users")

cursor.execute("""
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    rfid_uid TEXT UNIQUE NOT NULL,
    role TEXT NOT NULL,
    allowed_start INTEGER NOT NULL,
    allowed_end INTEGER NOT NULL
)
""")

cursor.execute("""
CREATE TABLE logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT,
    user_name TEXT,
    role TEXT,
    access_time TEXT,
    exit_time TEXT,
    session_duration TEXT,
    motion_detected INTEGER DEFAULT 0,
    gas_detected INTEGER DEFAULT 0,
    alert_triggered TEXT,
    risk_score TEXT
)
""")

# Insert users
cursor.execute("INSERT INTO users VALUES (NULL,'Ahmad Staff','STAFF001','Staff',9,18)")
cursor.execute("INSERT INTO users VALUES (NULL,'Siti Manager','MANAGER001','Manager',0,23)")
cursor.execute("INSERT INTO users VALUES (NULL,'Ali Cleaner','CLEANER001','Cleaner',18,22)")

# Generate 150 realistic records
user_profiles = [
    ("STAFF001",   "Ahmad Staff",  "Staff",   9,  18),
    ("MANAGER001", "Siti Manager", "Manager", 0,  23),
    ("CLEANER001", "Ali Cleaner",  "Cleaner", 18, 22)
]

current_timestamp = datetime(2026, 7, 1, 8, 0, 0)

for _ in range(150):
    current_timestamp += timedelta(
        hours=random.randint(1, 5),
        minutes=random.randint(0, 59)
    )
    event_hour = current_timestamp.hour
    scenario = random.choices(
        ["authorized", "intruder", "hazard"],
        weights=[85, 11, 4], k=1
    )[0]

    if scenario == "authorized":
        u_id, name, role, start_shift, end_shift = random.choice(user_profiles)
        if event_hour < start_shift or event_hour >= end_shift:
            alert = "UNUSUAL_HOUR"
            risk  = "MEDIUM"
        else:
            alert = "NONE"
            risk  = "LOW"
        stay  = random.randint(10, 240)
        exit_ts = current_timestamp + timedelta(minutes=stay)
        access_str   = current_timestamp.strftime("%Y-%m-%d %H:%M:%S")
        exit_str     = exit_ts.strftime("%Y-%m-%d %H:%M:%S")
        duration_str = f"{stay} mins"
        motion, gas  = 0, 0

    elif scenario == "intruder":
        u_id, name, role   = "UNKNOWN", "Unknown Person", "None"
        access_str         = current_timestamp.strftime("%Y-%m-%d %H:%M:%S")
        exit_str, duration_str = "NULL", "NULL"
        motion, gas        = 1, 0
        alert              = "LOCKOUT_ALERT"
        risk               = "HIGH"

    else:
        u_id, name, role   = "SYSTEM", "Environmental Sensor", "Hardware"
        access_str         = current_timestamp.strftime("%Y-%m-%d %H:%M:%S")
        exit_str, duration_str = "NULL", "NULL"
        motion             = random.choice([0, 1])
        gas                = 1
        alert              = "GAS_LEAK_DETECTION"
        risk               = "HIGH"

    cursor.execute("""
        INSERT INTO logs
        (user_id, user_name, role, access_time, exit_time,
         session_duration, motion_detected, gas_detected,
         alert_triggered, risk_score)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (u_id, name, role, access_str, exit_str,
          duration_str, motion, gas, alert, risk))

conn.commit()

# Verify
cursor.execute("SELECT COUNT(*) FROM logs")
print("Total rows:", cursor.fetchone()[0])
cursor.execute("SELECT risk_score, COUNT(*) FROM logs GROUP BY risk_score")
for row in cursor.fetchall():
    print(row)

conn.close()
print("Database ready.")