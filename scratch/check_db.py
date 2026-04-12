import sqlite3

def check_db():
    conn = sqlite3.connect("catalog_reference.db")
    cursor = conn.cursor()
    
    query = "Laproff"
    print(f"Checking for '{query}' in titular...")
    
    # Check with LIKE
    cursor.execute("SELECT id, titular, nombre_comercial, registro_invima FROM reference_products WHERE titular LIKE ? LIMIT 10", (f"%{query}%",))
    rows = cursor.fetchall()
    print(f"LIKE results ({len(rows)}):")
    for r in rows:
        print(r)
        
    # Check FTS5
    try:
        print("\nChecking FTS5...")
        cursor.execute("SELECT rowid, titular, nombre_comercial FROM reference_fts WHERE reference_fts MATCH ? LIMIT 10", (f"{query}*",))
        rows = cursor.fetchall()
        print(f"FTS5 results ({len(rows)}):")
        for r in rows:
            print(r)
    except Exception as e:
        print(f"FTS5 Error: {e}")

    conn.close()

if __name__ == "__main__":
    check_db()
