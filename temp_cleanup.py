import sqlite3
conn = sqlite3.connect('jobs.db')
cursor = conn.cursor()

# 1. Delete clearly irrelevant jobs (User SQL)
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
        title LIKE '%military%'
    )
""")
deleted_roles = cursor.rowcount

# 2. Manual Skips from Top 10 Review
cursor.execute("""
    DELETE FROM jobs WHERE status = 'new' AND (
        company LIKE '%Humana%' OR
        company LIKE '%CitizenGO%' OR
        company LIKE '%ECMC Group%' OR
        title LIKE '%Administrative Assistant%'
    )
""")
deleted_manual = cursor.rowcount

conn.commit()
conn.close()

print(f"Deleted {deleted_roles} broadly irrelevant jobs.")
print(f"Deleted {deleted_manual} user-flagged companies/roles.")
