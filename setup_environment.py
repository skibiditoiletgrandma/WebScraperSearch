#!/usr/bin/env python3
"""
Environment Setup Script for Web Search Application

This script automatically sets up all required environment variables for the application:
- Creates a PostgreSQL database if one doesn't exist
- Sets up DATABASE_URL and all PostgreSQL-related environment variables
- Generates a secure SESSION_SECRET
- Verifies that all environment variables are properly set

Usage:
    python setup_environment.py

The script can be run multiple times safely as it checks for existing configurations
before creating new ones.
"""

import os
import sys
import time
import secrets
import logging
import psycopg2
import subprocess
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Constants
MAX_WAIT_TIME = 30  # Maximum time to wait for database creation (seconds)
SECRETS_FILE = '.env'  # File to store secrets locally


def check_postgres_env_vars():
    """
    Check if all required PostgreSQL environment variables are set.
    
    Returns:
        bool: True if all variables are set, False otherwise
        list: List of missing variables
    """
    required_vars = ["PGHOST", "PGPORT", "PGUSER", "PGPASSWORD", "PGDATABASE"]
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    
    return len(missing_vars) == 0, missing_vars


def check_database_url():
    """
    Check if DATABASE_URL is set and valid.
    
    Returns:
        bool: True if DATABASE_URL is set and valid, False otherwise
    """
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        return False
    
    # Try to connect to the database to verify the URL is valid
    try:
        conn = psycopg2.connect(database_url)
        conn.close()
        return True
    except Exception as e:
        logger.warning(f"DATABASE_URL is set but invalid: {str(e)}")
        return False


def construct_database_url():
    """
    Construct DATABASE_URL from individual PostgreSQL environment variables.
    
    Returns:
        bool: True if DATABASE_URL was successfully constructed and set, False otherwise
    """
    all_vars_set, missing_vars = check_postgres_env_vars()
    if not all_vars_set:
        logger.warning(f"Cannot construct DATABASE_URL. Missing variables: {', '.join(missing_vars)}")
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
        
        # Save to .env file
        save_env_var("DATABASE_URL", database_url)
        
        return True
    
    except Exception as e:
        logger.error(f"Failed to connect to PostgreSQL: {str(e)}")
        return False


def create_postgresql_database():
    """
    Create a new PostgreSQL database using Replit's create_postgresql_database_tool.
    
    Returns:
        bool: True if database creation was successful, False otherwise
    """
    logger.info("Creating new PostgreSQL database...")
    
    try:
        # Import and use the Replit database creation tool
        # This approach avoids directly using subprocess to call the tool
        # First try the specialized approach (Replit specific)
        try:
            from create_postgresql_database_tool import create_postgresql_database_tool
            create_postgresql_database_tool()
            
            # Wait for environment variables to be populated
            for i in range(MAX_WAIT_TIME):
                if all([
                    os.environ.get("PGHOST"),
                    os.environ.get("PGPORT"),
                    os.environ.get("PGUSER"),
                    os.environ.get("PGPASSWORD"),
                    os.environ.get("PGDATABASE"),
                    os.environ.get("DATABASE_URL")
                ]):
                    logger.info(f"PostgreSQL environment variables detected after {i+1} seconds")
                    break
                
                logger.info(f"Waiting for PostgreSQL environment variables ({i+1}/{MAX_WAIT_TIME})...")
                time.sleep(1)
        except ImportError:
            # Fall back to using the subprocess approach
            logger.info("Using subprocess approach to create database")
            result = subprocess.run(
                ["python", "-c", "from create_postgresql_database_tool import create_postgresql_database_tool; create_postgresql_database_tool()"],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                logger.error(f"Failed to create database: {result.stderr}")
                # Try the direct API approach
                try:
                    import requests
                    requests.post("https://replit.com/api/v1/postgresql/create")
                    logger.info("Attempted to create database using API approach")
                    time.sleep(5)  # Wait for the database to be created
                except Exception as e:
                    logger.error(f"Failed to create database using API approach: {str(e)}")
                    return False
        
        # Check final state of environment variables
        all_vars_set, missing_vars = check_postgres_env_vars()
        db_url_set = "DATABASE_URL" in os.environ
        
        if all_vars_set and db_url_set:
            logger.info("PostgreSQL database created successfully with all environment variables")
            return True
        elif all_vars_set:
            logger.info("PostgreSQL variables set, but DATABASE_URL is missing. Constructing it now.")
            return construct_database_url()
        else:
            logger.warning(f"Database creation completed, but some variables are missing: {', '.join(missing_vars)}")
            return False
            
    except Exception as e:
        logger.error(f"Error creating PostgreSQL database: {str(e)}")
        return False


def generate_session_secret():
    """
    Generate and set a secure SESSION_SECRET if one doesn't exist.
    
    Returns:
        bool: True if SESSION_SECRET was successfully set, False otherwise
    """
    if os.environ.get("SESSION_SECRET"):
        logger.info("SESSION_SECRET is already set")
        return True
    
    try:
        # Generate a secure random session secret
        session_secret = secrets.token_hex(32)  # 32 bytes = 64 hex characters
        
        # Set the environment variable
        os.environ["SESSION_SECRET"] = session_secret
        
        # Save to .env file
        save_env_var("SESSION_SECRET", session_secret)
        
        logger.info("Generated and set new SESSION_SECRET")
        return True
        
    except Exception as e:
        logger.error(f"Failed to generate SESSION_SECRET: {str(e)}")
        return False


def save_env_var(key, value):
    """
    Save an environment variable to the .env file.
    
    Args:
        key (str): The environment variable name
        value (str): The environment variable value
        
    Returns:
        bool: True if the variable was saved successfully, False otherwise
    """
    try:
        # Read existing .env file if it exists
        env_lines = []
        env_path = Path(SECRETS_FILE)
        
        if env_path.exists():
            with open(env_path, 'r') as f:
                env_lines = f.readlines()
        
        # Remove any existing definition of this key
        env_lines = [line for line in env_lines if not line.startswith(f"{key}=")]
        
        # Add the new definition
        env_lines.append(f"{key}={value}\n")
        
        # Write back to the file
        with open(env_path, 'w') as f:
            f.writelines(env_lines)
            
        return True
        
    except Exception as e:
        logger.error(f"Failed to save {key} to {SECRETS_FILE}: {str(e)}")
        return False


def load_env_vars_from_file():
    """
    Load environment variables from the .env file.
    
    Returns:
        bool: True if variables were loaded successfully, False otherwise
    """
    env_path = Path(SECRETS_FILE)
    if not env_path.exists():
        logger.info(f"{SECRETS_FILE} file not found. No variables to load.")
        return False
    
    try:
        with open(env_path, 'r') as f:
            env_lines = f.readlines()
        
        # Process each line
        for line in env_lines:
            line = line.strip()
            if line and not line.startswith('#'):
                # Split at the first equals sign
                if '=' in line:
                    key, value = line.split('=', 1)
                    # Only set if not already in environment
                    if key not in os.environ:
                        os.environ[key] = value
                        logger.debug(f"Loaded {key} from {SECRETS_FILE}")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to load variables from {SECRETS_FILE}: {str(e)}")
        return False


def test_database_connection():
    """
    Test the database connection using the DATABASE_URL.
    
    Returns:
        bool: True if the connection test was successful, False otherwise
    """
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        logger.error("Cannot test database connection: DATABASE_URL is not set")
        return False
    
    try:
        # Connect to the database
        conn = psycopg2.connect(database_url)
        
        # Create a cursor
        cur = conn.cursor()
        
        # Execute a simple query
        cur.execute("SELECT 1")
        result = cur.fetchone()
        
        # Close the cursor and connection
        cur.close()
        conn.close()
        
        if result and result[0] == 1:
            logger.info("Database connection test successful")
            return True
        else:
            logger.warning("Database connection test returned unexpected result")
            return False
            
    except Exception as e:
        logger.error(f"Database connection test failed: {str(e)}")
        return False


def main():
    """
    Main function to set up all environment variables.
    """
    logger.info("Starting environment setup for Web Search Application")
    
    # First, try to load any existing variables from .env file
    load_env_vars_from_file()
    
    # Check if we already have a working database configuration
    if check_database_url():
        logger.info("Existing DATABASE_URL is valid")
    else:
        # Check if we have the individual PostgreSQL variables
        all_vars_set, _ = check_postgres_env_vars()
        
        if all_vars_set:
            # Try to construct DATABASE_URL from individual variables
            if construct_database_url():
                logger.info("Successfully constructed DATABASE_URL from PostgreSQL variables")
            else:
                logger.warning("Failed to construct DATABASE_URL from existing PostgreSQL variables")
                # Try to create a new database
                create_postgresql_database()
        else:
            # Create a new PostgreSQL database
            if create_postgresql_database():
                logger.info("Successfully created new PostgreSQL database")
            else:
                logger.error("Failed to set up PostgreSQL database")
                return 1
    
    # Generate SESSION_SECRET if needed
    if generate_session_secret():
        logger.info("SESSION_SECRET is set")
    else:
        logger.error("Failed to set up SESSION_SECRET")
        return 1
    
    # Final verification
    all_vars_set, missing_vars = check_postgres_env_vars()
    db_url_valid = check_database_url()
    session_secret_set = "SESSION_SECRET" in os.environ
    
    if all_vars_set and db_url_valid and session_secret_set:
        logger.info("All environment variables are set correctly")
        
        # Print a summary of the environment variables (with masked sensitive values)
        logger.info("Environment variables summary:")
        masked_db_url = os.environ.get("DATABASE_URL", "").split('@')[0].split(':')[0] + ":*****@*****"
        logger.info(f"DATABASE_URL: {masked_db_url}")
        logger.info(f"PGHOST: {os.environ.get('PGHOST')}")
        logger.info(f"PGPORT: {os.environ.get('PGPORT')}")
        logger.info(f"PGUSER: {os.environ.get('PGUSER')}")
        logger.info(f"PGPASSWORD: {'*' * 8}")
        logger.info(f"PGDATABASE: {os.environ.get('PGDATABASE')}")
        logger.info(f"SESSION_SECRET: {'*' * 8}")
        
        # Test database connection
        if test_database_connection():
            logger.info("Database connection verified")
        else:
            logger.warning("Environment variables are set, but database connection test failed")
            
        return 0
    else:
        # Log which variables are missing
        if not all_vars_set:
            logger.error(f"Missing PostgreSQL variables: {', '.join(missing_vars)}")
        if not db_url_valid:
            logger.error("DATABASE_URL is not valid")
        if not session_secret_set:
            logger.error("SESSION_SECRET is not set")
        
        logger.error("Environment setup failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())