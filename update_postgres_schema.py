"""
Update PostgreSQL Database Schema
This script adds the new summary and settings-related columns to the PostgreSQL database
"""

import logging
import os
import sys

from sqlalchemy import Column, Boolean, Integer, text
from sqlalchemy.sql import select

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Add the current directory to the path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import our database models
from app import app, db  # Import app as well
from models import User

def update_database_schema():
    """
    Update the database schema to include new settings and summary columns
    """
    logging.info("Starting database schema update for PostgreSQL...")
    
    # Start a connection to the database within the app context
    with app.app_context():
        connection = db.engine.connect()
        transaction = connection.begin()
    
        try:
            # Check if the columns exist first to avoid errors
            logging.info("Checking if hide_wikipedia column exists...")
            column_check = connection.execute(text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'users' AND column_name = 'hide_wikipedia'"
            )).fetchall()
            
            # Only add columns if they don't exist
            if not column_check:
                logging.info("Adding hide_wikipedia column to users table...")
                connection.execute(text(
                    "ALTER TABLE users ADD COLUMN hide_wikipedia BOOLEAN DEFAULT FALSE"
                ))
            else:
                logging.info("hide_wikipedia column already exists.")
                
            # Check if show_feedback_features exists
            column_check = connection.execute(text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'users' AND column_name = 'show_feedback_features'"
            )).fetchall()
            
            if not column_check:
                logging.info("Adding show_feedback_features column to users table...")
                connection.execute(text(
                    "ALTER TABLE users ADD COLUMN show_feedback_features BOOLEAN DEFAULT TRUE"
                ))
            else:
                logging.info("show_feedback_features column already exists.")
                
            # Check if generate_summaries exists
            column_check = connection.execute(text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'users' AND column_name = 'generate_summaries'"
            )).fetchall()
            
            if not column_check:
                logging.info("Adding generate_summaries column to users table...")
                connection.execute(text(
                    "ALTER TABLE users ADD COLUMN generate_summaries BOOLEAN DEFAULT TRUE"
                ))
            else:
                logging.info("generate_summaries column already exists.")
                
            # Check if summary_depth exists
            column_check = connection.execute(text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'users' AND column_name = 'summary_depth'"
            )).fetchall()
            
            if not column_check:
                logging.info("Adding summary_depth column to users table...")
                connection.execute(text(
                    "ALTER TABLE users ADD COLUMN summary_depth INTEGER DEFAULT 3"
                ))
            else:
                logging.info("summary_depth column already exists.")
                
            # Check if summary_complexity exists
            column_check = connection.execute(text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'users' AND column_name = 'summary_complexity'"
            )).fetchall()
            
            if not column_check:
                logging.info("Adding summary_complexity column to users table...")
                connection.execute(text(
                    "ALTER TABLE users ADD COLUMN summary_complexity INTEGER DEFAULT 3"
                ))
            else:
                logging.info("summary_complexity column already exists.")
                
            # Check if enable_suggestions exists
            column_check = connection.execute(text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'users' AND column_name = 'enable_suggestions'"
            )).fetchall()
            
            if not column_check:
                logging.info("Adding enable_suggestions column to users table...")
                connection.execute(text(
                    "ALTER TABLE users ADD COLUMN enable_suggestions BOOLEAN DEFAULT TRUE"
                ))
            else:
                logging.info("enable_suggestions column already exists.")
                
            # Commit the transaction
            transaction.commit()
            logging.info("Database schema update completed successfully!")
            
        except Exception as e:
            # Roll back the transaction in case of error
            transaction.rollback()
            logging.error(f"Error updating database schema: {str(e)}")
            raise
            
        finally:
            # Close the connection
            connection.close()
        
if __name__ == "__main__":
    # Run the update function
    update_database_schema()