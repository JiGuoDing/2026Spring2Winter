import sqlite3, os, tempfile, hashlib
d = tempfile.mkdtemp()
p = os.path.join(d, "t.db")
c = sqlite3.connect(p)
c.executescript("""
CREATE TABLE dim_region(id INTEGER PRIMARY KEY, name TEXT);
CREATE TABLE fact_order(id INTEGER PRIMARY KEY, region_id INT, amt REAL, paid_at TEXT);
INSERT INTO dim_region VALUES (1,'EAST'),(2,'WEST');
INSERT INTO fact_order VALUES (1,1,120.5,'2024-05-01'),(2,2,80.0,'2024-05-02');
""")
c.commit(); c.close()
ro = sqlite3.connect(f"file:{p}?mode=ro&immutable=1", uri=True)
cur = ro.execute("SELECT r.name, SUM(f.amt) FROM fact_order f JOIN dim_region r ON r.id=f.region_id GROUP BY 1")
print("query ok:", cur.fetchall())
try:
    ro.execute("DELETE FROM fact_order")
except Exception as e:
    print("readonly enforced:", type(e).__name__)
print("snapshot hash:", hashlib.sha256(open(p,'rb').read()).hexdigest()[:16])
