import serial
import sqlite3
import time
from bot import send_alert
from datetime import datetime

# Set your serial port ('COM3', 'COM4' for Windows, or '/dev/ttyUSB0' for Linux/Mac)
ser = serial.Serial("COM3", 9600, timeout=1) 

def ai_risk(uid, hour, wrong_count):
    """Predicts risk assessment based on user profile and system rules."""
    conn = sqlite3.connect("vault.db")
    c = conn.cursor()
    # Matches exact columns from setup_db.py: role, allowed_start, allowed_end
    c.execute("SELECT role, allowed_start, allowed_end FROM users WHERE rfid_uid=?", (uid,))
    row = c.fetchone()
    conn.close()
    
    if not row:
        return "HIGH", "Unknown RFID card identification scanned"
        
    role, start, end = row
    
    # Rule 1: Brute force detection
    if wrong_count >= 3:
        return "HIGH", f"Suspicious activity: 3 failed PIN attempts by {role}"
        
    # Rule 2: Access window timeframe enforcement
    if not (start <= hour < end):
        return "MEDIUM", f"Out-of-bounds schedule violation for {role} ({start}:00-{end}:00)"
        
    return "LOW", "Normal authorized access entry verified"

def log_access(uid, risk, reason, motion, gas):
    """Logs the entry data using your exact database schema parameters."""
    conn = sqlite3.connect("vault.db")
    c = conn.cursor()
    
    # Fetch user details to populate name and role in logs table
    c.execute("SELECT name, role FROM users WHERE rfid_uid=?", (uid,))
    user_row = c.fetchone()
    
    if user_row:
        user_name, role = user_row
    else:
        user_name, role = "UNKNOWN", "Unknown Role"
        
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Matches your exact columns: id, user_id, user_name, role, access_time, exit_time, 
    # session_duration, motion_detected, gas_detected, alert_triggered, risk_score
    c.execute(
        """
        INSERT INTO logs 
        (user_id, user_name, role, access_time, motion_detected, gas_detected, alert_triggered, risk_score)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (uid, user_name, role, now, motion, gas, reason, risk)
    )
    conn.commit()
    conn.close()

print("🛰️ Serial listener to ESP32 started. Awaiting sensor logs...")

while True:
    try:
        if ser.in_waiting > 0:
            line = ser.readline().decode("utf-8").strip()
            print(f"📥 Received from hardware: {line}") # Helps debug incoming ESP32 data strings
            
            # Expected ESP32 payload structure example: ACCESS:STAFF001,0,1,0
            if line.startswith("ACCESS:"):
                parts = line.split(",")
                uid   = parts[1]
                wrong = int(parts[2])
                
                # Capture optional live sensor logs sent via serial (0 = clear, 1 = triggered)
                motion = int(parts[3]) if len(parts) > 3 else 0
                gas    = int(parts[4]) if len(parts) > 4 else 0
                
                # If sensor goes off automatically elevate context status
                hour = datetime.now().hour
                risk, reason = ai_risk(uid, hour, wrong)
                
                # Override rule check if hardware safety sensors detect threats
                if gas == 1:
                    risk, reason = "HIGH", "Environmental emergency: MQ-2 Gas Leak alarm triggered"
                elif motion == 1 and risk == "HIGH":
                    reason += " + unexpected motion movement inside vault room"
                
                # Save into SQLite database
                log_access(uid, risk, reason, motion, gas)
                
                # Instant Telegram alert push notification dispatch
                if risk in ("MEDIUM", "HIGH"):
                    send_alert(uid, risk, reason)
                    
    except Exception as e:
        print(f"⚠️ Error parsing data loop: {e}")
        
    time.sleep(0.1)