import os
from datetime import datetime
from sqlalchemy import text
from app import app, db
from models import SearchResult
from ensure_db_url import ensure_db_url

def update_database_schema():
    """Update the database schema to include new sharing columns"""
    try:
        # Ensure DATABASE_URL is set before proceeding
        if not os.environ.get("DATABASE_URL"):
            print("DATABASE_URL not set. Attempting to configure it automatically...")
            if not ensure_db_url():
                print("ERROR: Could not set DATABASE_URL automatically.")
                return False
            else:
                database_url = os.environ.get("DATABASE_URL")
                if database_url and '@' in database_url:
                    masked_url = f"{database_url.split('@')[0].split(':')[0]}:*****@*****"
                    print(f"Successfully set DATABASE_URL: {masked_url}")
                else:
                    print("Successfully set DATABASE_URL")
            
        with app.app_context():
            print("Starting database schema update...")
            
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
                result = db.session.execute(text("SELECT to_regclass('search_result')")).scalar()
                if not result:
                    print("The search_result table doesn't exist. Creating all tables...")
                    db.create_all()
                    print("Tables created successfully.")
                    return True
            except Exception as e:
                print(f"Error checking tables: {str(e)}")
                db.create_all()
                print("Created all tables.")
                return True
            
            # Check if columns already exist to avoid errors
            try:
                # Try to query one of the new columns
                db.session.query(SearchResult.share_count).first()
                print("Share columns already exist. No update needed.")
                return True
            except Exception:
                # If an error occurs, the column doesn't exist, so we need to add it
                pass
            
            # Add the new columns
            column_definitions = [
                "share_count INTEGER DEFAULT 0",
                "last_shared TIMESTAMP WITHOUT TIME ZONE",
                "shared_by VARCHAR(64)"
            ]
            
            # Execute the ALTER TABLE statements
            for column_def in column_definitions:
                column_name = column_def.split()[0]
                try:
                    # Check if column exists first
                    col_check = db.session.execute(
                        f"SELECT column_name FROM information_schema.columns "
                        f"WHERE table_name='search_result' AND column_name='{column_name}'"
                    ).scalar()
                    
                    if not col_check:
                        # For new columns, preserve existing data
                        if column_name in ['search_count_today', 'search_count_reset_date']:
                            # First get existing values
                            current_values = db.session.execute(
                                "SELECT id, search_count_today, search_count_reset_date FROM users"
                            ).fetchall()
                            
                            # Add column with defaults
                            db.session.execute(f"ALTER TABLE search_result ADD COLUMN {column_def}")
                            
                            # Restore values if they existed
                            for user_id, count, reset_date in current_values:
                                if count is not None and reset_date is not None:
                                    db.session.execute(
                                        f"UPDATE users SET search_count_today = {count}, "
                                        f"search_count_reset_date = '{reset_date}' WHERE id = {user_id}"
                                    )
                        else:
                            db.session.execute(f"ALTER TABLE search_result ADD COLUMN {column_def}")
                        print(f"Added column '{column_name}' to search_result table.")
                    else:
                        print(f"Column '{column_name}' already exists.")
                except Exception as e:
                    print(f"Error adding column '{column_name}': {str(e)}")
            
            # Commit the changes
            db.session.commit()
            print("Database schema update completed successfully!")
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