#!/usr/bin/env python3
"""
PostgreSQL Database Setup Script

This script ensures that all necessary PostgreSQL environment variables are set up
and creates a new PostgreSQL database if needed. It's designed to be run once
during project setup or whenever the database configuration needs to be reset.

Environment variables that will be set up:
- DATABASE_URL: The complete database connection URL
- PGHOST: The PostgreSQL server host
- PGPORT: The PostgreSQL server port
- PGUSER: The PostgreSQL username
- PGPASSWORD: The PostgreSQL password
- PGDATABASE: The PostgreSQL database name

Usage:
    python setup_database.py

"""

import os
import sys
import time
import logging
import subprocess
import psycopg2

# Set up logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_postgres_env_vars():
    """
    Check if all required PostgreSQL environment variables are set.
    
    Returns:
        bool: True if all variables are set, False otherwise
    """
    required_vars = ["PGHOST", "PGPORT", "PGUSER", "PGPASSWORD", "PGDATABASE"]
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    
    if missing_vars:
        logger.warning(f"Missing PostgreSQL environment variables: {', '.join(missing_vars)}")
        return False
    
    return True

def create_postgresql_database():
    """
    Create a new PostgreSQL database using Replit's create_postgresql_database_tool.
    
    Returns:
        bool: True if database creation was successful, False otherwise
    """
    logger.info("Creating a new PostgreSQL database...")
    
    try:
        # Use Replit's function to create a new PostgreSQL database
        result = subprocess.run(
            [
                "python3", "-c", 
                """
from antml.function_calls import create_postgresql_database_tool
create_postgresql_database_tool()
                """
            ], 
            capture_output=True, 
            text=True
        )
        
        if result.returncode != 0:
            logger.error(f"Failed to create database: {result.stderr}")
            return False
        
        logger.info("Database creation initiated. Waiting for environment variables...")
        
        # Wait for the environment variables to be set (there's sometimes a delay)
        max_wait = 10  # seconds
        for i in range(max_wait):
            if check_postgres_env_vars():
                logger.info(f"PostgreSQL environment variables detected after {i+1} seconds")
                return True
            
            if i < max_wait - 1:
                time.sleep(1)
        
        # If we got here, we timed out waiting for the variables
        logger.warning("Timed out waiting for PostgreSQL environment variables")
        return False
        
    except Exception as e:
        logger.error(f"Error creating PostgreSQL database: {str(e)}")
        return False

def construct_database_url():
    """
    Construct DATABASE_URL from individual PostgreSQL environment variables.
    
    Returns:
        bool: True if DATABASE_URL was successfully set, False otherwise
    """
    if not check_postgres_env_vars():
        return False
    
    # Get the PostgreSQL variables
    pghost = os.environ.get("PGHOST")
    pgport = os.environ.get("PGPORT")
    pguser = os.environ.get("PGUSER")
    pgpassword = os.environ.get("PGPASSWORD")
    pgdatabase = os.environ.get("PGDATABASE")
    
    # Construct the DATABASE_URL
    database_url = f"postgresql://{pguser}:{pgpassword}@{pghost}:{pgport}/{pgdatabase}"
    
    # Test the connection before setting the environment variable
    try:
        # Try to connect to the database
        conn = psycopg2.connect(
            host=pghost,
            port=pgport,
            user=pguser,
            password=pgpassword,
            dbname=pgdatabase
        )
        conn.close()
        
        # Set the DATABASE_URL environment variable
        os.environ["DATABASE_URL"] = database_url
        
        # Log a masked version for security
        masked_url = f"postgresql://{pguser}:******@{pghost}:{pgport}/{pgdatabase}"
        logger.info(f"Successfully set DATABASE_URL: {masked_url}")
        
        return True
    
    except Exception as e:
        logger.error(f"Failed to connect to PostgreSQL: {str(e)}")
        return False

def ensure_database_url():
    """
    Ensure DATABASE_URL is set in environment variables.
    If it's not set, try to construct it or create a new database.
    
    Returns:
        bool: True if DATABASE_URL is set, False otherwise
    """
    # Check if DATABASE_URL is already set
    if os.environ.get("DATABASE_URL"):
        logger.info("DATABASE_URL is already set")
        return True
    
    # Try to construct DATABASE_URL from existing PostgreSQL variables
    if construct_database_url():
        return True
    
    # If we get here, we need to create a new database
    logger.warning("DATABASE_URL is not set and could not be constructed from PostgreSQL variables")
    logger.info("Attempting to create a new PostgreSQL database...")
    
    # Create a new PostgreSQL database
    if create_postgresql_database():
        # Try again to construct DATABASE_URL
        return construct_database_url()
    
    # If we get here, we failed to create a database
    logger.error("Failed to create a PostgreSQL database. Database functionality will be limited.")
    return False

def test_database_connection():
    """
    Test the database connection by executing a simple query.
    
    Returns:
        bool: True if the connection test was successful, False otherwise
    """
    if not os.environ.get("DATABASE_URL"):
        logger.error("DATABASE_URL is not set. Cannot test connection.")
        return False
    
    try:
        # Connect using the DATABASE_URL
        conn = psycopg2.connect(os.environ.get("DATABASE_URL"))
        cursor = conn.cursor()
        
        # Try a simple query
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        
        # Close cursor and connection
        cursor.close()
        conn.close()
        
        if result and result[0] == 1:
            logger.info("Database connection test successful")
            return True
        else:
            logger.warning("Unexpected result from database connection test")
            return False
            
    except Exception as e:
        logger.error(f"Database connection test failed: {str(e)}")
        return False

def main():
    """
    Main function to set up the PostgreSQL database.
    """
    logger.info("Starting PostgreSQL database setup")
    
    if ensure_database_url():
        logger.info("PostgreSQL database setup completed successfully")
        
        # Test the database connection
        if test_database_connection():
            logger.info("Database connection verified")
        else:
            logger.warning("Database setup succeeded, but connection test failed")
            
        return 0
    else:
        logger.error("PostgreSQL database setup failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())