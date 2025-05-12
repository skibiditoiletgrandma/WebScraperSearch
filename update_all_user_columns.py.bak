"""
Update All User Columns

This script ensures that all users in the database have the expected columns with valid default values.
It's useful after schema changes to make sure old users have new fields properly initialized.
"""

import logging
from datetime import datetime
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Try to import the necessary modules
try:
    from app import app, db
    from models import User
    from sqlalchemy import inspect, text
except ImportError as e:
    logger.error(f"Failed to import required modules: {e}")
    sys.exit(1)

def ensure_database_url():
    """Ensure DATABASE_URL is set"""
    try:
        from ensure_db_url import ensure_db_url
        if not ensure_db_url():
            logger.error("Failed to configure DATABASE_URL")
            return False
        return True
    except ImportError:
        logger.error("ensure_db_url module not found")
        return False

def get_user_columns():
    """Get a list of all columns in the User model"""
    inspector = inspect(User)
    return [column.key for column in inspector.columns]

def update_user_columns():
    """Update all users to ensure they have all columns with valid defaults"""
    try:
        with app.app_context():
            # First check connection
            try:
                db.session.execute(text("SELECT 1"))
                logger.info("Database connection successful")
            except Exception as e:
                logger.error(f"Database connection failed: {e}")
                return False
                
            # Get all users
            users = User.query.all()
            logger.info(f"Found {len(users)} users in the database")
            
            # Default values for columns
            defaults = {
                'search_pages_limit': 1,
                'hide_wikipedia': False,
                'show_feedback_features': False,
                'enable_suggestions': True,
                'generate_summaries': True,
                'summary_depth': 3,
                'summary_complexity': 3,
                'search_count_today': 0,
                'search_count_reset_date': datetime.utcnow(),
                'is_admin': False
            }
            
            # Check columns and add defaults if missing
            columns = get_user_columns()
            updated_count = 0
            
            for user in users:
                user_updated = False
                
                for column, default_value in defaults.items():
                    # Check if user has this attribute set properly
                    if column in columns:
                        try:
                            current_value = getattr(user, column)
                            if current_value is None:
                                setattr(user, column, default_value)
                                logger.info(f"Set default value for user {user.username}, column {column}")
                                user_updated = True
                        except AttributeError:
                            setattr(user, column, default_value)
                            logger.info(f"Set default value for user {user.username}, column {column}")
                            user_updated = True
                
                if user_updated:
                    updated_count += 1
            
            # Commit changes
            if updated_count > 0:
                db.session.commit()
                logger.info(f"Updated {updated_count} users with default column values")
            else:
                logger.info("No user updates were needed")
                
            return True
                
    except Exception as e:
        logger.error(f"Error updating user columns: {e}")
        return False

if __name__ == "__main__":
    logger.info("Starting user column update")
    
    if ensure_database_url():
        if update_user_columns():
            logger.info("Successfully updated all user columns")
        else:
            logger.error("Failed to update user columns")
    else:
        logger.error("Failed to ensure DATABASE_URL, aborting")