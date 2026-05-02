import sqlite3
conn = sqlite3.connect('jobs.db')
cursor = conn.cursor()
cursor.execute("""
    SELECT title, company, score, url, notes
    FROM jobs 
    WHERE status = 'applied'
    ORDER BY score DESC
    LIMIT 20
""")
jobs = cursor.fetchall()
conn.close()

for title, company, score, url, notes in jobs:
    print(f"{score} | {title} @ {company}")
    print(f"      {url}\n")
