"""
Update User Schema Script
This script adds the search_count_today and search_count_reset_date columns to the users table
"""
from app import app, db
from datetime import datetime
from sqlalchemy import Column, Integer, DateTime, text

def update_user_schema():
    """Update the users table schema to include search count fields"""
    with app.app_context():
        # Check if we need to add the columns
        try:
            # Try a simple query to see if the columns exist
            db.session.execute(text("SELECT search_count_today FROM users LIMIT 1"))
            print("The search_count_today column already exists.")
        except Exception as e:
            # Columns don't exist, so add them
            print("Adding missing columns to users table...")
            
            # First check if we have existing data to preserve
            try:
                current_values = db.session.execute(text(
                    "SELECT id, search_count_today, search_count_reset_date FROM users"
                )).fetchall()
            except:
                current_values = []

            # Execute SQL to add the missing columns - one statement at a time
            db.session.execute(text("ALTER TABLE users ADD COLUMN search_count_today INTEGER DEFAULT 0"))
            db.session.execute(text("ALTER TABLE users ADD COLUMN search_count_reset_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP"))
            
            # Restore previous values if they existed
            for user_id, count, reset_date in current_values:
                if count is not None and reset_date is not None:
                    db.session.execute(text(
                        f"UPDATE users SET search_count_today = :count, "
                        f"search_count_reset_date = :reset_date WHERE id = :user_id"
                    ), {"count": count, "reset_date": reset_date, "user_id": user_id})
            
            db.session.commit()
            print("Successfully added search_count_today and search_count_reset_date columns to users table.")
        
        print("Database schema update completed.")

if __name__ == '__main__':
    update_user_schema()