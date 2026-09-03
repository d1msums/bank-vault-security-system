from bot import send_alert

send_alert("STAFF001", "HIGH", "Environmental emergency: MQ-2 Gas Leak alarm triggered")
send_alert("CLEANER001", "MEDIUM", "Out-of-bounds schedule violation for Cleaner (18:00-22:00)")
send_alert("UNKNOWN_XYZ", "HIGH", "Unknown RFID card identification scanned")