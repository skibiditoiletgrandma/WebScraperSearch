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
            
            # Execute SQL to add the missing columns - one statement at a time
            db.session.execute(text("ALTER TABLE users ADD COLUMN search_count_today INTEGER DEFAULT 0"))
            db.session.execute(text("ALTER TABLE users ADD COLUMN search_count_reset_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP"))
            
            db.session.commit()
            print("Successfully added search_count_today and search_count_reset_date columns to users table.")
        
        print("Database schema update completed.")

if __name__ == '__main__':
    update_user_schema()