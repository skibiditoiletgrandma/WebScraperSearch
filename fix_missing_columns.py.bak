
import os
import logging
from sqlalchemy import text, inspect
from app import app, db
from models import User

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def fix_missing_columns():
    """Fix missing columns in the database tables"""
    try:
        with app.app_context():
            # Check database connection
            try:
                db.session.execute(text("SELECT 1"))
                logger.info("Database connection successful")
            except Exception as e:
                logger.error(f"Database connection failed: {e}")
                return False

            # Get expected columns from the User model
            inspector = inspect(User)
            expected_columns = {column.key: column for column in inspector.columns}
            
            # Get existing columns from the database
            existing_columns = {}
            for column in db.session.execute(text(
                "SELECT column_name, data_type FROM information_schema.columns "
                "WHERE table_name = 'users'"
            )).fetchall():
                existing_columns[column[0]] = column[1]

            # Compare and add missing columns
            for column_name, column_obj in expected_columns.items():
                if column_name not in existing_columns:
                    logger.info(f"Adding missing column: {column_name}")
                    
                    # Determine column type and constraints
                    col_type = str(column_obj.type)
                    nullable = "" if column_obj.nullable else "NOT NULL"
                    default = f"DEFAULT {column_obj.default.arg}" if column_obj.default else ""
                    
                    # Create the column
                    try:
                        db.session.execute(text(
                            f"ALTER TABLE users ADD COLUMN {column_name} {col_type} {nullable} {default}"
                        ))
                        logger.info(f"Successfully added column {column_name}")
                    except Exception as e:
                        logger.error(f"Error adding column {column_name}: {e}")
                        db.session.rollback()
                        continue

            # Commit changes
            db.session.commit()
            logger.info("Database column fixes completed successfully")
            return True

    except Exception as e:
        logger.error(f"Error fixing missing columns: {e}")
        return False

if __name__ == "__main__":
    if fix_missing_columns():
        print("Successfully fixed missing database columns")
    else:
        print("Failed to fix missing database columns")
