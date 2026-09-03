from verify_db import check_vault_access
import time

print("🧪 STARTING MOCK HARDWARE ACCREDITATION TEST...")
time.sleep(1)

# Helper function to simulate how the SG90 motor would react based on the system action
def simulate_sg90_motor(action):
    if "UNLOCK" in action.upper() or "GRANT" in action.upper():
        return "🔄 SG90 Motor rotating to 90° (Vault Unlocked)"
    else:
        return "🔒 SG90 Motor staying at 0° (Vault Locked)"

# Test Case A: Ahmad Staff trying to access during his allowed time window
print("\n[Scenario 1: Ahmad scans his card during the day]")
result = check_vault_access("STAFF001", "1234")
print(f"📡 System Action -> {simulate_sg90_motor(result['action'])}")
print(f"🧠 AI Risk Engine assessment: {result['risk_score']} Risk ({result['reason']})")

# Test Case B: Someone types the wrong PIN
print("\n[Scenario 2: Intruder gets the PIN wrong]")
result = check_vault_access("STAFF001", "9999")
print(f"📡 System Action -> {simulate_sg90_motor(result['action'])}")
print(f"🧠 AI Risk Engine assessment: {result['risk_score']} Risk ({result['reason']})")

# Test Case C: Scanning an unrecognized card
print("\n[Scenario 3: Someone found/cloned an unknown RFID tag]")
result = check_vault_access("UNKNOWN_TAG_XYZ", "0000")
print(f"📡 System Action -> {simulate_sg90_motor(result['action'])}")
print(f"🧠 AI Risk Engine assessment: {result['risk_score']} Risk ({result['reason']})")