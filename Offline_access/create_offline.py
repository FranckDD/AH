# create_offline_db.py
import sqlite3
import sys

SQL_FILE = "C:/Users/DD/Desktop/Project Stage/ah2_v2/AH2/Offline_access/offline_schema.sql"
DB_FILE = "offline.db"

def main():
    print(f"Création de {DB_FILE} à partir de {SQL_FILE}...")
    with open(SQL_FILE, "r", encoding="utf-8") as f:
        sql = f.read()

    conn = sqlite3.connect(DB_FILE)
    # activer foreign keys
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        conn.executescript(sql)
        conn.commit()
        print("✅ Base SQLite créée avec succès.")
    except Exception as e:
        print("❌ Erreur:", e)
    finally:
        conn.close()

if __name__ == "__main__":
    main()
