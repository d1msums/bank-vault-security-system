import sqlite3
import csv
import random
from datetime import datetime, timedelta

DB_NAME = "vault.db"
CSV_NAME = "vault_logs.csv"

def generate_security_dataset(total_records=150):
    """Programmatically generates a realistic, sequential security dataset."""
    
    # 1. Initialize and clean the database tables
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
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
    
    # Seed defined personnel profiles
    cursor.execute("INSERT INTO users VALUES (NULL,'Ahmad Staff','STAFF001','Staff',9,18)")
    cursor.execute("INSERT INTO users VALUES (NULL,'Siti Manager','MANAGER001','Manager',0,23)")
    cursor.execute("INSERT INTO users VALUES (NULL,'Ali Cleaner','CLEANER001','Cleaner',18,22)")
    conn.commit()

    # Define generation rules
    user_profiles = [
        ("STAFF001", "Ahmad Staff", "Staff", 9, 18),
        ("MANAGER001", "Siti Manager", "Manager", 0, 23),
        ("CLEANER001", "Ali Cleaner", "Cleaner", 18, 22)
    ]
    
    # Timeline starts on July 1st, 2026
    current_timestamp = datetime(2026, 7, 1, 8, 0, 0)
    
    print(self_reply := f"Generating {total_records} sequential rows...")

    for _ in range(total_records):
        # Progress time forward randomly by 1 to 5 hours per event
        current_timestamp += timedelta(hours=random.randint(1, 5), minutes=random.randint(0, 59))
        event_hour = current_timestamp.hour
        
        # Decide transaction nature: 85% Authorized Personnel, 11% Intruder, 4% Environment Hazard
        scenario = random.choices(["authorized", "intruder", "hazard"], weights=[85, 11, 4], k=1)[0]
        
        if scenario == "authorized":
            u_id, name, role, start_shift, end_shift = random.choice(user_profiles)
            
            # Evaluate flag if logging entry outside assigned shift window
            if event_hour < start_shift or event_hour >= end_shift:
                alert = "UNUSUAL_HOUR"
                risk = "MEDIUM"
            else:
                alert = "NONE"
                risk = "LOW"
                
            # Program session time (10 to 240 minutes)
            stay_duration = random.randint(10, 240)
            exit_timestamp = current_timestamp + timedelta(minutes=stay_duration)
            
            access_str = current_timestamp.strftime("%Y-%m-%d %H:%M:%S")
            exit_str = exit_timestamp.strftime("%Y-%m-%d %H:%M:%S")
            duration_str = f"{stay_duration} mins"
            motion, gas = 0, 0
            
        elif scenario == "intruder":
            u_id, name, role = "UNKNOWN", "Unknown Person", "None"
            access_str = current_timestamp.strftime("%Y-%m-%d %H:%M:%S")
            exit_str, duration_str = "NULL", "NULL"
            motion, gas = 1, 0
            alert = "LOCKOUT_ALERT"
            risk = "HIGH"
            
        else:  # Hazard event
            u_id, name, role = "SYSTEM", "Environmental_Sensor", "Hardware"
            access_str = current_timestamp.strftime("%Y-%m-%d %H:%M:%S")
            exit_str, duration_str = "NULL", "NULL"
            motion = random.choice([0, 1])
            gas = 1
            alert = "GAS_LEAK_DETECTION"
            risk = "HIGH"

        # Commit generated transaction to SQLite 
        cursor.execute("""
            INSERT INTO logs (user_id, user_name, role, access_time, exit_time, session_duration, motion_detected, gas_detected, alert_triggered, risk_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (u_id, name, role, access_str, exit_str, duration_str, motion, gas, alert, risk))

    conn.commit()
    print("Database generation complete.")

    # 2. Extract database dataset and generate the CSV file structure
    cursor.execute("SELECT id, user_id, user_name, role, access_time, exit_time, session_duration, motion_detected, gas_detected, alert_triggered, risk_score FROM logs")
    dataset_rows = cursor.fetchall()
    
    with open(CSV_NAME, "w", newline="", encoding="utf-8") as csv_file:
        csv_writer = csv.writer(csv_file)
        
        # Structure headers matching the database schema properties
        csv_writer.writerow([
            "Log_ID", "User_ID", "User_Name", "Role", "Access_Time", 
            "Exit_Time", "Session_Duration", "Motion_Detected", 
            "Gas_Detected", "Alert_Triggered", "Risk_Score"
        ])
        csv_writer.writerows(dataset_rows)
        
    conn.close()
    print(f"File '{CSV_NAME}' generated successfully containing {len(dataset_rows)} custom records.")

if __name__ == "__main__":
    generate_security_dataset(150)