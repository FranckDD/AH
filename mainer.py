import sqlite3

db_path = "offline.db"  # chemin vers ta base locale

def rename_userid_to_doctorid():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Vérifier la structure
    cursor.execute("PRAGMA table_info(appointments)")
    columns = [row[1] for row in cursor.fetchall()]

    if "doctor_id" in columns:
        print("✅ La colonne doctor_id existe déjà, rien à faire.")
    elif "user_id" in columns:
        print("🔄 Renommage de user_id → doctor_id ...")
        cursor.execute("ALTER TABLE appointments RENAME COLUMN user_id TO doctor_id;")
        conn.commit()
        print("✅ Renommage terminé avec succès.")
    else:
        print("⚠️ Ni user_id ni doctor_id trouvés dans la table appointments.")

    conn.close()

if __name__ == "__main__":
    rename_userid_to_doctorid()
