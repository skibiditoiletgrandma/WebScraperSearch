"""
Database migration utility for handling schema changes
"""
import logging
from sqlalchemy.exc import OperationalError
from app import db
from models import User, SearchQuery, SearchResult, SummaryFeedback, AnonymousSearchLimit, Citation

def fix_missing_columns():
    """
    Check and fix missing columns in database tables
    This function will be called when a schema error is detected
    """
    try:
        logging.info("Checking and fixing database schema...")
        
        # Create missing tables if they don't exist
        with db.engine.connect() as conn:
            # Get existing tables
            inspector = db.inspect(db.engine)
            existing_tables = inspector.get_table_names()
            
            # Create missing tables using SQLAlchemy's create_all
            missing_tables = [table for table in ['users', 'search_query', 'search_result', 'summary_feedback', 'anonymous_search_limit', 'citations'] 
                             if table not in existing_tables]
            
            if missing_tables:
                logging.info(f"Creating missing tables: {', '.join(missing_tables)}")
                db.create_all()  # This will create all missing tables based on models
            
            # Check columns in users table
            if 'users' in existing_tables:
                existing_columns = [col['name'] for col in inspector.get_columns('users')]
                
                # Add missing columns to the users table
                if 'search_pages_limit' not in existing_columns:
                    logging.info("Adding 'search_pages_limit' column to users table...")
                    conn.execute(db.text("ALTER TABLE users ADD COLUMN search_pages_limit INTEGER DEFAULT 1"))
                    
                if 'hide_wikipedia' not in existing_columns:
                    logging.info("Adding 'hide_wikipedia' column to users table...")
                    conn.execute(db.text("ALTER TABLE users ADD COLUMN hide_wikipedia BOOLEAN DEFAULT FALSE"))
                    
                if 'show_feedback_features' not in existing_columns:
                    logging.info("Adding 'show_feedback_features' column to users table...")
                    conn.execute(db.text("ALTER TABLE users ADD COLUMN show_feedback_features BOOLEAN DEFAULT TRUE"))
                    
                if 'generate_summaries' not in existing_columns:
                    logging.info("Adding 'generate_summaries' column to users table...")
                    conn.execute(db.text("ALTER TABLE users ADD COLUMN generate_summaries BOOLEAN DEFAULT TRUE"))
                    
                if 'summary_depth' not in existing_columns:
                    logging.info("Adding 'summary_depth' column to users table...")
                    conn.execute(db.text("ALTER TABLE users ADD COLUMN summary_depth INTEGER DEFAULT 3"))
                    
                if 'summary_complexity' not in existing_columns:
                    logging.info("Adding 'summary_complexity' column to users table...")
                    conn.execute(db.text("ALTER TABLE users ADD COLUMN summary_complexity INTEGER DEFAULT 3"))
                
            conn.commit()
        
        logging.info("Database schema check and fix completed successfully")
        return True
        
    except Exception as e:
        logging.error(f"Error fixing database schema: {str(e)}")
        return False

def handle_db_error(error):
    """
    Handle database errors by checking for schema issues and fixing them
    
    Args:
        error: The exception that was raised
        
    Returns:
        bool: True if the error was handled, False otherwise
    """
    # Check if it's a missing column error
    error_str = str(error).lower()
    is_column_error = ('no such column' in error_str or 
                       'column does not exist' in error_str or
                       'undefined column' in error_str)
    
    if is_column_error:
        logging.warning(f"Schema error detected: {str(error)}")
        success = fix_missing_columns()
        if success:
            logging.info("Schema error was successfully fixed")
            return True
    
    # If we get here, the error wasn't handled
    return False