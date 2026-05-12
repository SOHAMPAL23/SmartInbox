import sqlite3

def migrate():
    conn = sqlite3.connect("smartinbox.db")
    cursor = conn.cursor()
    
    # Check current columns
    cursor.execute("PRAGMA table_info(predictions)")
    existing_columns = [row[1] for row in cursor.fetchall()]
    
    new_columns = [
        ("spam_type", "TEXT"),
        ("spam_type_confidence", "REAL"),
        ("spam_type_explanation", "TEXT"),
        ("ai_spam_score", "REAL"),
        ("traditional_spam_score", "REAL"),
        ("ham_score", "REAL"),
        ("threat_level", "TEXT"),
        ("ai_generated_probability", "REAL"),
        ("phishing_probability", "REAL"),
        ("ml_model_score", "REAL"),
        ("groq_semantic_score", "REAL"),
        ("heuristic_score", "REAL"),
        ("detected_categories", "JSON"),
        ("reasoning", "TEXT"),
        ("recommended_action", "TEXT"),
        ("groq_available", "BOOLEAN")
    ]
    
    for col_name, col_type in new_columns:
        if col_name not in existing_columns:
            print(f"Adding column {col_name}...")
            try:
                cursor.execute(f"ALTER TABLE predictions ADD COLUMN {col_name} {col_type}")
            except Exception as e:
                print(f"Failed to add {col_name}: {e}")
        else:
            print(f"Column {col_name} already exists.")
            
    conn.commit()
    conn.close()
    print("Migration complete.")

if __name__ == "__main__":
    migrate()
