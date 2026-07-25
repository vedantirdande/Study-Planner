import sqlite3

conn = sqlite3.connect("database.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    roll_number TEXT UNIQUE NOT NULL,
    branch TEXT NOT NULL,
    semester INTEGER NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT DEFAULT 'student',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS resources (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    title TEXT NOT NULL,

    subject TEXT NOT NULL,

    branch TEXT NOT NULL,

    semester INTEGER NOT NULL,

    resource_type TEXT NOT NULL,

    filename TEXT NOT NULL,

    uploaded_by INTEGER,

    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY(uploaded_by) REFERENCES users(id)

)
""")

conn.commit()
conn.close()

print("Database Created Successfully ✅")