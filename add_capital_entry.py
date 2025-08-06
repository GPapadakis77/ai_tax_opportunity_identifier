import sqlite3

db_path = r"data\tax_opportunities.db"

conn = sqlite3.connect(db_path)
cur = conn.cursor()

cur.execute("""
INSERT INTO opportunities (
    id, title, url, date, source, full_text, keywords, entities, main_topic, sentiment, opportunity_score, opportunity_type
) VALUES (
    'capital-2025-07-31-01',
    'Παράδειγμα είδησης από το Capital',
    'https://www.capital.gr/news/123456',
    '2025-07-31',
    'Capital',
    'Πλήρες κείμενο είδησης από το Capital...',
    'οικονομία, επενδύσεις',
    '[("Capital", "ORG")]',
    'General Economic Topic',
    NULL,
    NULL,
    NULL
)
""")

conn.commit()
conn.close()

print("Η εγγραφή προστέθηκε με επιτυχία!")