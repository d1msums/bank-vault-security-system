import sqlite3

conn = sqlite3.connect(r"C:\Users\sofea\bank_guard\vault.db")
cursor = conn.cursor()

low    = 0
medium = 0
high   = 0

cursor.execute("SELECT risk_score FROM logs")
rows = cursor.fetchall()

for row in rows:
    val = row[0]
    print(repr(val))  # shows exact value including spaces or hidden chars
    if val == 'LOW':    low += 1
    elif val == 'MEDIUM': medium += 1
    elif val == 'HIGH':   high += 1

print(f"\nLOW: {low} | MEDIUM: {medium} | HIGH: {high}")
conn.close()