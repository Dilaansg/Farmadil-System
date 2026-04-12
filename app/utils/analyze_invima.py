import sqlite3
conn = sqlite3.connect('catalog_reference.db')
c = conn.cursor()

# Test 1: FTS search for lab name
print("=== Test: FTS 'laproff' ===")
try:
    c.execute("SELECT id, nombre_comercial, titular FROM reference_fts JOIN reference_products rp ON rp.id = reference_fts.rowid WHERE reference_fts MATCH ? LIMIT 3", ('"laproff"*',))
    for r in c.fetchall(): print(r)
except Exception as e:
    print(f"FTS ERROR: {e}")

# Test 2: LIKE search for lab name  
print("\n=== Test: LIKE titular '%laproff%' ===")
c.execute("SELECT id, nombre_comercial, titular FROM reference_products WHERE LOWER(titular) LIKE '%laproff%' LIMIT 3")
for r in c.fetchall(): print(r)

# Test 3: LIKE search for INVIMA number
print("\n=== Test: LIKE registro_invima '2021M%' ===")
c.execute("SELECT id, nombre_comercial, registro_invima FROM reference_products WHERE registro_invima LIKE '2021M%' LIMIT 3")
for r in c.fetchall(): print(r)

# Test 4: LIKE on registro for INVIMA prefix
print("\n=== Test: registro starts with 'INVIMA' ===")
c.execute("SELECT id, nombre_comercial, registro_invima FROM reference_products WHERE registro_invima LIKE 'INVIMA%' LIMIT 3")
for r in c.fetchall(): print(r)

# Test 5: Sample data
print("\n=== Sample first 3 rows ===")
c.execute("SELECT id, nombre_comercial, titular, registro_invima FROM reference_products LIMIT 3")
for r in c.fetchall(): print(r)

# Test 6: FTS for 'electrolit'
print("\n=== Test: FTS 'electrolit' ===")
try:
    c.execute("SELECT id, nombre_comercial, titular FROM reference_fts JOIN reference_products rp ON rp.id = reference_fts.rowid WHERE reference_fts MATCH ? ORDER BY rank LIMIT 5", ('"electrolit"*',))
    for r in c.fetchall(): print(r)
except Exception as e:
    print(f"FTS ERROR: {e}")

conn.close()
