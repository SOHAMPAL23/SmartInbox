import sqlite3
try:
    conn = sqlite3.connect("smartinbox.db")
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(predictions)")
    columns = [row[1] for row in cursor.fetchall()]
    print(f"Columns: {columns}")
    conn.close()
except Exception as e:
    print(f"ERROR: {e}")
