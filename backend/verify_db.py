# /backend/verify_db.py

import sqlite3
import os
from pathlib import Path

# --- ABSOLUTE PATH FIX ---
# This ensures the script finds the DB file regardless of where it's executed from.
# 1. Get the path of the script's parent folder (backend/).
# 2. Get the parent of that (project root).
PROJECT_ROOT = Path(__file__).resolve().parent.parent
# Define the absolute path for the DB file in the project root
DB_FILE_PATH = PROJECT_ROOT / "hazard_log.db"
DB_PATH = str(DB_FILE_PATH) # Final path string

# Check for file existence using the reliable absolute path
if not os.path.exists(DB_PATH):
    print("="*60)
    print(f"❌ Error: The 'hazard_log.db' file was not found at the expected location.")
    print(f"Expected Location: {DB_PATH}")
    print("ACTION: Ensure the server (Terminal 1) is run FIRST to create the file.")
    print("="*60)
    exit()

try:
    # Connect to the database file using the absolute path
    conn = sqlite3.connect(DB_PATH) 
    cursor = conn.cursor()

    # Query all records
    cursor.execute("SELECT * FROM hazards")
    records = cursor.fetchall()

    # Print results
    print("\n--- DATABASE VERIFICATION RESULTS ---")
    print(f"Total Hazards Successfully Logged: {len(records)}")

    if len(records) > 0:
        # Note: Index 0 is ID, 1 is hazard_type, 4 is severity.
        print(f"First Record Saved: ID={records[0][0]}, Type={records[0][1]}, Severity={records[0][4]}")
        print("\n🎉 The First 60% Milestone is VERIFIED and COMPLETE! 🎉")
    else:
        print("\n⚠️ Verification Failed: Zero records found. Run detection_logic.py again. ⚠️")

    conn.close()

except sqlite3.OperationalError as e:
    print(f"\n❌ Database Error: {e}")