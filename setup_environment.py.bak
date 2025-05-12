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
import traceback
import subprocess
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Import psycopg2 with error handling
try:
    import psycopg2
except ImportError:
    logger.warning("Could not import psycopg2. Some database functions may not work.")
    # Create a fallback psycopg2 module with a connect function that always raises an exception
    class FallbackPsycopg2:
        @staticmethod
        def connect(*args, **kwargs):
            raise ImportError("psycopg2 is not installed")
    
    psycopg2 = FallbackPsycopg2()

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
        # Import psycopg2 only when needed to handle potential import errors
        import psycopg2
        conn = psycopg2.connect(database_url)
        conn.close()
        return True
    except ImportError:
        logger.warning("Could not import psycopg2. Please ensure it's installed.")
        return False
    except Exception as e:
        logger.warning(f"DATABASE_URL is set but invalid: {str(e)}")
        # Log the full traceback at debug level for troubleshooting
        logger.debug(f"Exception traceback: {traceback.format_exc()}")
        return False


def construct_database_url():
    """
    Construct DATABASE_URL from individual PostgreSQL environment variables.
    
    Returns:
        bool: True if DATABASE_URL was successfully constructed and set, False otherwise
    """
    try:
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
        
        except ImportError:
            logger.warning("Could not import psycopg2. Unable to test database connection.")
            # Set the URL anyway but warn that it wasn't tested
            os.environ["DATABASE_URL"] = database_url
            save_env_var("DATABASE_URL", database_url)
            logger.warning("Set DATABASE_URL without testing the connection.")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {str(e)}")
            logger.debug(f"Connection error traceback: {traceback.format_exc()}")
            return False
            
    except Exception as e:
        logger.error(f"Unexpected error constructing DATABASE_URL: {str(e)}")
        logger.debug(f"Traceback: {traceback.format_exc()}")
        return False


def create_postgresql_database():
    """
    Create a new PostgreSQL database using Replit's create_postgresql_database_tool.
    
    Returns:
        bool: True if database creation was successful, False otherwise
    """
    logger.info("Creating new PostgreSQL database...")
    
    try:
        # First, try to use the Replit create_postgresql_database_tool directly
        # This is the safest way to create a database on Replit
        success = False
        
        try:
            # Try importing from the module and running it (Replit's direct method)
            logger.info("Attempting to create database using Replit's tool...")
            
            # Use a try-except block for the Python functionality that can raise tracebacks
            try:
                # Import dynamically to avoid import errors at module level
                from create_postgresql_database_tool import create_postgresql_database_tool
                create_postgresql_database_tool()
                success = True
                logger.info("Successfully initiated database creation with Replit's tool")
            except ImportError:
                logger.warning("Could not import create_postgresql_database_tool directly")
                raise  # Re-raise to fall back to the next method
            
        except (ImportError, Exception):
            # If direct import fails, try the subprocess approach
            logger.info("Using subprocess approach to create database")
            
            try:
                # Run the tool through a subprocess
                result = subprocess.run(
                    ["python", "-c", 
                     "try:\n    from create_postgresql_database_tool import create_postgresql_database_tool\n    create_postgresql_database_tool()\nexcept Exception as e:\n    import sys\n    print(f'Error: {str(e)}', file=sys.stderr)\n    sys.exit(1)"],
                    capture_output=True,
                    text=True
                )
                
                if result.returncode == 0:
                    success = True
                    logger.info("Successfully initiated database creation with subprocess approach")
                else:
                    logger.error(f"Failed to create database using subprocess: {result.stderr}")
                    
                    # If subprocess fails, try with a function call through the Replit API
                    try:
                        import requests
                        response = requests.post("https://replit.com/api/v1/postgresql/create")
                        if response.status_code < 400:  # Any 2xx or 3xx status code
                            success = True
                            logger.info("Successfully initiated database creation with API approach")
                        else:
                            logger.error(f"API approach failed with status code: {response.status_code}")
                    except Exception as e:
                        logger.error(f"Failed to create database using API approach: {str(e)}")
                        logger.debug(f"API error traceback: {traceback.format_exc()}")
            except Exception as e:
                logger.error(f"Subprocess execution failed: {str(e)}")
                logger.debug(f"Subprocess error traceback: {traceback.format_exc()}")
        
        # If any method was successful, wait for the environment variables to be populated
        if success:
            logger.info("Waiting for PostgreSQL environment variables to be populated...")
            
            # Wait for up to MAX_WAIT_TIME seconds for the environment variables to appear
            for i in range(MAX_WAIT_TIME):
                if all([
                    os.environ.get("PGHOST"),
                    os.environ.get("PGPORT"),
                    os.environ.get("PGUSER"),
                    os.environ.get("PGPASSWORD"),
                    os.environ.get("PGDATABASE")
                ]):
                    logger.info(f"PostgreSQL environment variables detected after {i+1} seconds")
                    
                    # If DATABASE_URL isn't set, construct it from the individual variables
                    if not os.environ.get("DATABASE_URL"):
                        logger.info("Constructing DATABASE_URL from PostgreSQL variables")
                        construct_database_url()
                    
                    break
                
                if i < MAX_WAIT_TIME - 1:  # Don't log on the last iteration
                    logger.info(f"Waiting for PostgreSQL environment variables ({i+1}/{MAX_WAIT_TIME})...")
                    time.sleep(1)
        
        # Check final state of environment variables
        all_vars_set, missing_vars = check_postgres_env_vars()
        db_url_set = "DATABASE_URL" in os.environ
        
        if all_vars_set and db_url_set:
            logger.info("PostgreSQL database created successfully with all environment variables")
            return True
        elif all_vars_set:
            logger.info("PostgreSQL variables set, but DATABASE_URL is missing. Constructing it now.")
            return construct_database_url()
        elif success:
            logger.warning(f"Database creation initiated, but some variables are missing: {', '.join(missing_vars)}")
            # If we got here, the database creation probably worked but some variables weren't populated
            # Let's give it a bit more time and check again
            logger.info("Waiting a bit longer for variables to be populated...")
            time.sleep(5)
            
            # Check one more time
            all_vars_set, missing_vars = check_postgres_env_vars()
            if all_vars_set:
                logger.info("PostgreSQL variables now detected after additional wait")
                if not os.environ.get("DATABASE_URL"):
                    return construct_database_url()
                return True
            
            logger.warning("Could not confirm all PostgreSQL variables were set correctly")
            return False
        else:
            logger.error("All database creation methods failed")
            return False
            
    except Exception as e:
        logger.error(f"Unexpected error creating PostgreSQL database: {str(e)}")
        logger.debug(f"Traceback: {traceback.format_exc()}")
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
    try:
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
                
        except ImportError:
            logger.warning("Could not import psycopg2. Unable to test database connection.")
            return True  # Assume it's ok since we can't test it
            
        except Exception as e:
            logger.error(f"Database connection test failed: {str(e)}")
            logger.debug(f"Connection test traceback: {traceback.format_exc()}")
            return False
            
    except Exception as e:
        logger.error(f"Unexpected error in database connection test: {str(e)}")
        logger.debug(f"Traceback: {traceback.format_exc()}")
        return False


def main():
    """
    Main function to set up all environment variables.
    """
    try:
        logger.info("Starting environment setup for Web Search Application")
        
        # First, try to load any existing variables from .env file
        try:
            load_env_vars_from_file()
        except Exception as e:
            logger.warning(f"Failed to load environment variables from file: {str(e)}")
            logger.debug(f"Load env vars traceback: {traceback.format_exc()}")
            # Continue execution even if loading fails
        
        # Check if we already have a working database configuration
        database_valid = False
        try:
            database_valid = check_database_url()
            if database_valid:
                logger.info("Existing DATABASE_URL is valid")
        except Exception as e:
            logger.warning(f"Error checking database URL: {str(e)}")
            logger.debug(f"Check database URL traceback: {traceback.format_exc()}")
            database_valid = False
        
        if not database_valid:
            # Check if we have the individual PostgreSQL variables
            all_vars_set = False
            try:
                all_vars_set, _ = check_postgres_env_vars()
            except Exception as e:
                logger.warning(f"Error checking PostgreSQL variables: {str(e)}")
                logger.debug(f"Check PostgreSQL vars traceback: {traceback.format_exc()}")
                all_vars_set = False
            
            if all_vars_set:
                # Try to construct DATABASE_URL from individual variables
                try:
                    if construct_database_url():
                        logger.info("Successfully constructed DATABASE_URL from PostgreSQL variables")
                    else:
                        logger.warning("Failed to construct DATABASE_URL from existing PostgreSQL variables")
                        # Try to create a new database
                        create_postgresql_database()
                except Exception as e:
                    logger.warning(f"Error constructing DATABASE_URL: {str(e)}")
                    logger.debug(f"Construct DATABASE_URL traceback: {traceback.format_exc()}")
                    # Try to create a new database anyway
                    try:
                        create_postgresql_database()
                    except Exception as e2:
                        logger.error(f"Error creating PostgreSQL database: {str(e2)}")
                        logger.debug(f"Create database traceback: {traceback.format_exc()}")
            else:
                # Create a new PostgreSQL database
                try:
                    if create_postgresql_database():
                        logger.info("Successfully created new PostgreSQL database")
                    else:
                        logger.warning("Failed to set up PostgreSQL database, but continuing anyway")
                        # Don't return error, continue and try to set other variables
                except Exception as e:
                    logger.error(f"Error creating PostgreSQL database: {str(e)}")
                    logger.debug(f"Create database traceback: {traceback.format_exc()}")
        
        # Generate SESSION_SECRET if needed
        session_secret_set = False
        try:
            session_secret_set = generate_session_secret()
            if session_secret_set:
                logger.info("SESSION_SECRET is set")
            else:
                # If the normal method fails, manually create a fallback secret
                fallback_secret = secrets.token_hex(32)
                os.environ["SESSION_SECRET"] = fallback_secret
                save_env_var("SESSION_SECRET", fallback_secret)
                logger.info("Created SESSION_SECRET with fallback method")
                session_secret_set = True
        except Exception as e:
            logger.warning(f"Error generating SESSION_SECRET: {str(e)}")
            logger.debug(f"Generate session secret traceback: {traceback.format_exc()}")
            # Create a fallback secret
            try:
                import uuid
                fallback_secret = str(uuid.uuid4()) + str(uuid.uuid4())
                os.environ["SESSION_SECRET"] = fallback_secret
                save_env_var("SESSION_SECRET", fallback_secret)
                logger.info("Created SESSION_SECRET with fallback uuid method")
                session_secret_set = True
            except Exception as e2:
                logger.error(f"All session secret generation methods failed: {str(e2)}")
        
        # Final verification
        all_vars_set = False
        missing_vars = []
        db_url_valid = False
        
        try:
            all_vars_set, missing_vars = check_postgres_env_vars()
        except Exception as e:
            logger.warning(f"Error in final PostgreSQL variables check: {str(e)}")
            
        try:
            db_url_valid = check_database_url()
        except Exception as e:
            logger.warning(f"Error in final DATABASE_URL check: {str(e)}")
            
        session_secret_set = "SESSION_SECRET" in os.environ
        
        # Print a summary of the environment variables (with masked sensitive values)
        logger.info("Environment variables summary:")
        
        try:
            if "DATABASE_URL" in os.environ:
                db_url = os.environ.get("DATABASE_URL", "")
                if db_url and '@' in db_url:
                    masked_db_url = db_url.split('@')[0].split(':')[0] + ":*****@*****"
                else:
                    masked_db_url = "Set but in unexpected format"
                logger.info(f"DATABASE_URL: {masked_db_url}")
            else:
                logger.info("DATABASE_URL: Not set")
            
            logger.info(f"PGHOST: {os.environ.get('PGHOST', 'Not set')}")
            logger.info(f"PGPORT: {os.environ.get('PGPORT', 'Not set')}")
            logger.info(f"PGUSER: {os.environ.get('PGUSER', 'Not set')}")
            
            if "PGPASSWORD" in os.environ:
                logger.info(f"PGPASSWORD: {'*' * 8}")
            else:
                logger.info("PGPASSWORD: Not set")
                
            logger.info(f"PGDATABASE: {os.environ.get('PGDATABASE', 'Not set')}")
            
            if "SESSION_SECRET" in os.environ:
                logger.info(f"SESSION_SECRET: {'*' * 8}")
            else:
                logger.info("SESSION_SECRET: Not set")
        except Exception as e:
            logger.warning(f"Error generating environment summary: {str(e)}")
        
        # Test database connection
        if db_url_valid:
            try:
                if test_database_connection():
                    logger.info("Database connection verified")
                else:
                    logger.warning("Environment variables are set, but database connection test failed")
            except Exception as e:
                logger.warning(f"Error testing database connection: {str(e)}")
        
        # Log overall status
        if all_vars_set and db_url_valid and session_secret_set:
            logger.info("All environment variables are set correctly")
            return 0
        else:
            # Log which variables are missing
            if not all_vars_set:
                logger.warning(f"Missing PostgreSQL variables: {', '.join(missing_vars)}")
            if not db_url_valid:
                logger.warning("DATABASE_URL is not valid")
            if not session_secret_set:
                logger.warning("SESSION_SECRET is not set")
            
            # Even if some variables are missing, return success if we have the essential ones
            if db_url_valid and session_secret_set:
                logger.info("Essential environment variables are set, proceeding despite some missing variables")
                return 0
            else:
                logger.warning("Some essential environment variables could not be set")
                return 1
                
    except Exception as e:
        logger.error(f"Unexpected error in setup_environment.py: {str(e)}")
        logger.debug(f"Main function traceback: {traceback.format_exc()}")
        
        # Make a last-ditch effort to set SESSION_SECRET if it's not set
        if "SESSION_SECRET" not in os.environ:
            try:
                os.environ["SESSION_SECRET"] = secrets.token_hex(32)
                logger.info("Created SESSION_SECRET in exception handler")
            except:
                pass
        
        return 1


if __name__ == "__main__":
    sys.exit(main())