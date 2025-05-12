"""
Utility module to ensure DATABASE_URL is set correctly.
This can be imported by any script in the project that needs DATABASE_URL.

Usage example:

```python
import os
from ensure_db_url import ensure_db_url

# Make sure DATABASE_URL is set
ensure_db_url()

# Now use DATABASE_URL
database_url = os.environ.get("DATABASE_URL")
# ... rest of your script that needs DATABASE_URL
```
"""

import os
import sys
import logging
import subprocess
import time
from configure_database_url import configure_database_url

def create_postgresql_database():
    """
    Create a new PostgreSQL database using Replit's create_postgresql_database_tool.
    This requires the script to be run in the Replit environment.
    
    Returns:
        bool: True if database creation was initiated, False otherwise
    """
    logger = logging.getLogger(__name__)
    logger.info("No DATABASE_URL found. Creating a new PostgreSQL database...")
    
    try:
        # Execute create_postgresql_database_tool directly using bash
        result = subprocess.run(
            [
                "bash", "-c", 
                """
                python3 -c "
                from antml.function_calls import create_postgresql_database_tool
                create_postgresql_database_tool()
                "
                """
            ], 
            capture_output=True, 
            text=True
        )
        
        if result.returncode != 0:
            logger.error(f"Failed to execute database creation tool: {result.stderr}")
            return False
            
        logger.info("Initiated database creation, waiting for environment variables...")
        
        # Wait for the environment variables to be set
        # Sometimes there's a delay before they're available
        max_wait = 10  # seconds
        for i in range(max_wait):
            if all([
                os.environ.get("PGHOST"),
                os.environ.get("PGPORT"),
                os.environ.get("PGUSER"),
                os.environ.get("PGPASSWORD"),
                os.environ.get("PGDATABASE")
            ]):
                logger.info(f"PostgreSQL environment variables detected after {i+1} seconds")
                break
                
            if i < max_wait - 1:  # Don't sleep on the last iteration
                time.sleep(1)
        
        # Check final state of environment variables
        if all([
            os.environ.get("PGHOST"),
            os.environ.get("PGPORT"),
            os.environ.get("PGUSER"),
            os.environ.get("PGPASSWORD"),
            os.environ.get("PGDATABASE")
        ]):
            logger.info("PostgreSQL database created successfully")
            return True
        else:
            logger.warning("Database creation completed, but some environment variables are missing")
            # Return True anyway and let configure_database_url handle any issues
            return True
            
    except Exception as e:
        logger.error(f"Error creating PostgreSQL database: {str(e)}")
        return False

def ensure_db_url():
    """
    Ensure DATABASE_URL is set in environment variables.
    If it's not set, try the following steps:
    1. Try to construct it from individual PostgreSQL variables
    2. If that fails, create a new PostgreSQL database
    
    Returns:
        bool: True if DATABASE_URL is set (or was successfully set), False otherwise
    """
    logger = logging.getLogger(__name__)
    
    # Check if DATABASE_URL is already set
    if os.environ.get("DATABASE_URL"):
        return True
    
    # Configure it from individual PostgreSQL environment variables
    success = configure_database_url()
    
    if success:
        return True
    
    # If we get here, we need to create a new PostgreSQL database
    logger.warning(
        "DATABASE_URL is not set and could not be constructed from PostgreSQL variables. "
        "Attempting to create a new PostgreSQL database."
    )
    
    # Try to create a new database
    if create_postgresql_database():
        # Now try again to set DATABASE_URL from the newly created PostgreSQL database
        return configure_database_url()
    
    logger.error(
        "Could not create a PostgreSQL database. Database functionality will be limited. "
        "Please set up a database manually."
    )
    return False

if __name__ == "__main__":
    # Set up logging when run as script
    logging.basicConfig(level=logging.INFO)
    
    # Attempt to ensure DATABASE_URL is set
    if ensure_db_url():
        # Get a masked version for security
        db_url = os.environ.get("DATABASE_URL", "")
        masked_url = db_url.split('@')[0].split(':')[0] + ":*****@*****" if '@' in db_url else "UNKNOWN FORMAT"
        print(f"DATABASE_URL is set: {masked_url}")
        sys.exit(0)
    else:
        print("ERROR: Could not set DATABASE_URL. Database functionality will be limited.")
        print("Make sure the following environment variables are set: PGHOST, PGPORT, PGUSER, PGPASSWORD, PGDATABASE")
        sys.exit(1)