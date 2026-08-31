import sqlite3
import sys
from pathlib import Path

DATABASE = Path(__file__).resolve().parent.parent / "database.db"

if len(sys.argv) > 1:
    roll_number = sys.argv[1].strip().upper()
else:
    roll_number = input("Enter the registration number to make admin: ").strip().upper()

if not roll_number or roll_number == "YOUR_REGISTRATION_NUMBER":
    print("Usage: python database\\create_admin.py YOUR_ACTUAL_REGISTRATION_NUMBER")
    print("Replace the placeholder with the registration number used during sign up.")
    sys.exit(1)

with sqlite3.connect(DATABASE) as connection:
    cursor = connection.execute("UPDATE users SET role='admin' WHERE roll_number=?", (roll_number,))
    if cursor.rowcount:
        print(f"Admin access granted to {roll_number}. Log out and log in again to refresh your session.")
    else:
        print(f"No user found with registration number: {roll_number}")
        print("Register the user first, then run this script with the exact registration number.")
        sys.exit(1)
