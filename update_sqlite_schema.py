"""
Update SQLite Schema Script
This script adds missing columns to the SQLite database tables
"""
import os
import sys
import sqlite3

def update_sqlite_schema():
    """Update the SQLite database schema to include missing columns"""
    
    # Get the path to the SQLite database file
    root_path = os.path.dirname(os.path.abspath(__file__))
    instance_path = os.path.join(root_path, 'instance')
    db_path = os.path.join(instance_path, "dev.db")
    
    if not os.path.exists(db_path):
        print(f"SQLite database file not found at {db_path}")
        return
    
    print(f"Updating SQLite database at {db_path}")
    
    # Connect to the SQLite database
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if the users table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        if not cursor.fetchone():
            print("Users table does not exist in the SQLite database")
            conn.close()
            return
        
        # Check if the search_count_today column exists
        cursor.execute("PRAGMA table_info(users)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'search_count_today' not in columns:
            print("Adding search_count_today column to users table")
            cursor.execute("ALTER TABLE users ADD COLUMN search_count_today INTEGER DEFAULT 0")
        else:
            print("search_count_today column already exists")
        
        if 'search_count_reset_date' not in columns:
            print("Adding search_count_reset_date column to users table")
            cursor.execute("ALTER TABLE users ADD COLUMN search_count_reset_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
        else:
            print("search_count_reset_date column already exists")
        
        # Commit the changes
        conn.commit()
        conn.close()
        print("SQLite database schema update completed successfully")
        
    except Exception as e:
        print(f"Error updating SQLite database: {str(e)}")
        if 'conn' in locals() and conn:
            conn.close()

if __name__ == '__main__':
    update_sqlite_schema()