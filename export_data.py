import sqlite3
import pandas as pd

# Connect to your SQLite database
conn = sqlite3.connect("vault.db")

# Try changing 'logs' to your exact table name if it differs (e.g., 'log', 'access_logs', etc.)
table_name = "logs"

try:
  # Load the entire table into a pandas DataFrame
  df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)

  # Export all rows to a CSV file ready for Kaggle
  df.to_csv("full_vault_data.csv", index=False)

  print(
      f"Successfully exported {len(df)} rows from '{table_name}' to"
      " full_vault_data.csv!"
  )

except Exception as e:
  print(f"Error querying table '{table_name}': {e}")
  print(
      "Tip: Open check_db.py and run it to verify your exact database table"
      " name."
  )

finally:
  conn.close()