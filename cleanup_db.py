import sqlite3

conn = sqlite3.connect('jobs.db')
cursor = conn.cursor()

# Delete irrelevant jobs
cursor.execute("""
    DELETE FROM jobs WHERE status = 'new' AND (
        title LIKE '%programmer%' OR
        title LIKE '%.net%' OR
        title LIKE '%developer%' OR
        title LIKE '%engineer%' OR
        title LIKE '%volunteer%' OR
        title LIKE '%therapist%' OR
        title LIKE '%clinical%' OR
        title LIKE '%nurse%' OR
        title LIKE '%sales%' OR
        title LIKE '%driver%' OR
        title LIKE '%military%' OR
        title LIKE '%attorney%' OR
        title LIKE '%accountant%' OR
        title LIKE '%designer%' OR
        title LIKE '%recruiter%' OR
        score < 70
    )
""")

deleted = cursor.rowcount
conn.commit()

# Show what remains
cursor.execute("""
    SELECT title, company, score 
    FROM jobs 
    WHERE status = 'new'
    ORDER BY score DESC
""")
remaining = cursor.fetchall()
conn.close()

print(f"Deleted {deleted} irrelevant jobs")
print(f"\n{len(remaining)} quality jobs remaining:\n")
for title, company, score in remaining:
    print(f"{score} - {title} @ {company}")
