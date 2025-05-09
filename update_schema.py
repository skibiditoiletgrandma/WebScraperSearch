import os
from datetime import datetime
from app import app, db
from models import SearchResult

def update_database_schema():
    """Update the database schema to include new sharing columns"""
    try:
        with app.app_context():
            print("Starting database schema update...")
            
            # Check if database is accessible
            if not os.environ.get("DATABASE_URL"):
                print("ERROR: DATABASE_URL environment variable not set.")
                return False
            
            # Check connection
            try:
                # Try to execute a simple query to test connection
                db.session.execute("SELECT 1")
                print("Database connection successful.")
            except Exception as e:
                print(f"Database connection failed: {str(e)}")
                return False
            
            # Check if table exists
            try:
                result = db.session.execute("SELECT to_regclass('search_result')").scalar()
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