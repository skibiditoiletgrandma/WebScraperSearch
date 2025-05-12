import os
from datetime import datetime
from sqlalchemy import text
from app import app, db
from models import User

def update_database_schema():
    """Update the database schema to include new summary settings columns"""
    try:
        with app.app_context():
            print("Starting database schema update for summary settings...")
            
            # Check if database is accessible
            if not os.environ.get("DATABASE_URL"):
                print("ERROR: DATABASE_URL environment variable not set.")
                return False
            
            # Check connection
            try:
                # Try to execute a simple query to test connection
                db.session.execute(text("SELECT 1"))
                print("Database connection successful.")
            except Exception as e:
                print(f"Database connection failed: {str(e)}")
                return False
            
            # Check if table exists
            try:
                result = db.session.execute(text("SELECT to_regclass('users')")).scalar()
                if not result:
                    print("The users table doesn't exist. Creating all tables...")
                    db.create_all()
                    print("Tables created successfully.")
                    return True
            except Exception as e:
                print(f"Error checking tables: {str(e)}")
                db.create_all()
                print("Created all tables.")
                return True
            
            # New columns to add
            column_definitions = [
                "generate_summaries BOOLEAN DEFAULT TRUE",
                "summary_depth INTEGER DEFAULT 3",
                "summary_complexity INTEGER DEFAULT 3"
            ]
            
            # Execute the ALTER TABLE statements
            for column_def in column_definitions:
                column_name = column_def.split()[0]
                try:
                    # Check if column exists first
                    col_check = db.session.execute(
                        text(f"SELECT column_name FROM information_schema.columns "
                             f"WHERE table_name='users' AND column_name='{column_name}'")
                    ).scalar()
                    
                    if not col_check:
                        db.session.execute(text(f"ALTER TABLE users ADD COLUMN {column_def}"))
                        print(f"Added column '{column_name}' to users table.")
                    else:
                        print(f"Column '{column_name}' already exists.")
                except Exception as e:
                    print(f"Error adding column '{column_name}': {str(e)}")
            
            # Commit the changes
            db.session.commit()
            print("Database schema update for summary settings completed successfully!")
            return True
            
    except Exception as e:
        print(f"Error updating database schema: {str(e)}")
        return False

if __name__ == "__main__":
    # Run the update
    if update_database_schema():
        print("Database update completed successfully!")
    else:
        print("Database update failed.")