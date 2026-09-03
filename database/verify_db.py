# verify_db.py
import sqlite3
from datetime import datetime

def check_vault_access(rfid_uid, pin):
    """
    Queries vault.db to validate the user credentials and check time constraints.
    Returns a dictionary with the action, risk_score, and reasoning.
    """
    conn = sqlite3.connect("vault.db")
    cursor = conn.cursor()
    
    # 1. Look up the user by their RFID UID
    cursor.execute("SELECT name, pin, role, allowed_days, allowed_start, allowed_end FROM users WHERE rfid_uid = ?", (rfid_uid,))
    user = cursor.fetchone()
    
    # If user doesn't exist at all
    if not user:
        conn.close()
        return {
            "action": "DENY_ACCESS_LOCK",
            "risk_score": "High",
            "reason": "Unrecognized or spoofed RFID credentials."
        }
        
    name, correct_pin, role, allowed_days, allowed_start, allowed_end = user
    
    # 2. Check if the PIN is correct
    if pin != correct_pin:
        conn.close()
        return {
            "action": "DENY_ACCESS_LOCK",
            "risk_score": "Medium",
            "reason": f"Invalid PIN entered for user: {name}."
        }
        
    # 3. Check time and day constraints
    now = datetime.now()
    current_day = now.strftime("%a") # e.g., 'Mon', 'Tue', 'Wed'
    current_hour = now.hour          # e.g., 14 (for 2 PM)
    
    # Check if today is an allowed day
    if current_day not in allowed_days:
        conn.close()
        return {
            "action": "DENY_ACCESS_LOCK",
            "risk_score": "Medium",
            "reason": f"Access denied. {name} is not permitted on {current_day}."
        }
        
    # Check if current time is within allowed hours
    if not (allowed_start <= current_hour <= allowed_end):
        conn.close()
        return {
            "action": "DENY_ACCESS_LOCK",
            "risk_score": "Medium",
            "reason": f"Access denied. {name} is outside allowed hours ({allowed_start}:00-{allowed_end}:00)."
        }
        
    # If all checks pass, grant access!
    conn.close()
    return {
        "action": "GRANT_ACCESS_UNLOCK",
        "risk_score": "Low",
        "reason": f"Valid credentials. {name} authorized during standard hours."
    }

# This part only runs if you run verify_db.py directly (helps for debugging)
if __name__ == "__main__":
    print("--- TESTING DATABASE CONNECTION ---")
    conn = sqlite3.connect("vault.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, role FROM users")
    print("Current Users in DB:", cursor.fetchall())
    conn.close()