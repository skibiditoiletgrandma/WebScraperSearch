import os
import logging
from configure_database_url import configure_database_url, get_database_url

def ensure_database_url():
    """
    Ensure the DATABASE_URL environment variable is set.
    If it's not set, try to construct it from individual PostgreSQL variables.
    Returns:
        str: The database URL or None if it cannot be determined
    """
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    # Check if DATABASE_URL is already set
    if database_url := os.environ.get("DATABASE_URL"):
        logger.info("DATABASE_URL is already set")
        return database_url
    
    # Try to configure it from individual PostgreSQL environment variables
    if configure_database_url():
        database_url = os.environ.get("DATABASE_URL")
        logger.info(f"Set DATABASE_URL: {database_url.split('@')[0].split(':')[0]}:*****@*****")
        return database_url
    
    # Couldn't set DATABASE_URL
    logger.warning("Could not set DATABASE_URL. Missing PostgreSQL environment variables.")
    return None

if __name__ == "__main__":
    # This is useful to run as a standalone script to set DATABASE_URL
    if url := ensure_database_url():
        print(f"DATABASE_URL is set: {url.split('@')[0].split(':')[0]}:*****@*****")
    else:
        print("Could not set DATABASE_URL. Missing PostgreSQL environment variables.")