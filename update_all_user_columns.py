"""
Complete User Schema Update Script
This script updates the users table with all required columns from the model
"""
from app import app, db
from datetime import datetime
from sqlalchemy import Column, Integer, DateTime, text, Boolean, String

def update_all_user_columns():
    """Update the users table schema to include all required columns"""
    with app.app_context():
        print("Starting complete User schema update...")
        
        # Define all the columns that should exist in the User model
        columns_to_check = [
            {"name": "search_count_today", "type": "INTEGER", "default": "0"},
            {"name": "search_count_reset_date", "type": "TIMESTAMP", "default": "CURRENT_TIMESTAMP"},
            {"name": "search_pages_limit", "type": "INTEGER", "default": "1"},
            {"name": "hide_wikipedia", "type": "BOOLEAN", "default": "FALSE"},
            {"name": "show_feedback_features", "type": "BOOLEAN", "default": "FALSE"},
            {"name": "enable_suggestions", "type": "BOOLEAN", "default": "TRUE"},
            {"name": "generate_summaries", "type": "BOOLEAN", "default": "TRUE"},
            {"name": "summary_depth", "type": "INTEGER", "default": "3"},
            {"name": "summary_complexity", "type": "INTEGER", "default": "3"}
        ]
        
        # Check and add each column
        for column in columns_to_check:
            try:
                # Check if the column exists
                query = f"SELECT {column['name']} FROM users LIMIT 1"
                db.session.execute(text(query))
                print(f"Column {column['name']} already exists in users table.")
            except Exception as e:
                # Column doesn't exist, add it
                print(f"Adding missing column {column['name']} to users table...")
                add_column_query = f"ALTER TABLE users ADD COLUMN {column['name']} {column['type']} DEFAULT {column['default']}"
                db.session.execute(text(add_column_query))
                db.session.commit()
                print(f"Successfully added {column['name']} column to users table.")
        
        print("User schema update completed.")

if __name__ == '__main__':
    update_all_user_columns()