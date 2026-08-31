import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE = BASE_DIR / "database.db"

connection = sqlite3.connect(DATABASE)
cursor = connection.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL COLLATE NOCASE,
    roll_number TEXT UNIQUE NOT NULL COLLATE NOCASE,
    branch TEXT NOT NULL,
    semester INTEGER NOT NULL CHECK (semester BETWEEN 1 AND 8),
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'student' CHECK (role IN ('student', 'admin')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS resources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    subject TEXT NOT NULL,
    branch TEXT NOT NULL,
    semester INTEGER NOT NULL CHECK (semester BETWEEN 1 AND 8),
    resource_type TEXT NOT NULL,
    filename TEXT NOT NULL,
    uploaded_by INTEGER,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(uploaded_by) REFERENCES users(id) ON DELETE SET NULL
)
""")

cursor.execute("CREATE INDEX IF NOT EXISTS idx_resources_type ON resources(resource_type)")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_resources_branch_semester ON resources(branch, semester)")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_resources_uploader ON resources(uploaded_by)")

connection.commit()
connection.close()
print(f"Database ready: {DATABASE}")
