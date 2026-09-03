from flask import Flask, request, jsonify, render_template
import sqlite3
import os

app = Flask(__name__)
DB = r"C:\Users\sofea\bank_guard\vault.db"

@app.route("/log", methods=["POST"])
def log_entry():
    data = request.get_json()
    print("Received log:", data)
    conn = sqlite3.connect(DB)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO logs
        (user_name, role, access_time, motion_detected,
         gas_detected, alert_triggered, risk_score)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        data.get("user_name"),
        data.get("role"),
        data.get("access_time"),
        data.get("motion_detected"),
        data.get("gas_detected"),
        data.get("alert_triggered"),
        data.get("risk_score")
    ))
    conn.commit()
    conn.close()
    return jsonify({"status": "logged"}), 200

@app.route("/")
def dashboard():
    conn = sqlite3.connect(DB)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM logs ORDER BY id DESC")
    logs = cursor.fetchall()
    conn.close()

    low    = sum(1 for log in logs if log[10] == 'LOW')
    medium = sum(1 for log in logs if log[10] == 'MEDIUM')
    high   = sum(1 for log in logs if log[10] == 'HIGH')
    total  = len(logs)

    print(f"Dashboard: {total} total | {low} LOW | {medium} MEDIUM | {high} HIGH")

    return render_template("dashboard.html",
                           logs=logs,
                           total=total,
                           low=low,
                           medium=medium,
                           high=high)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)