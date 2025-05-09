import os
import logging

def configure_database_url():
    """
    Check if DATABASE_URL environment variable is set.
    If not, construct it from individual PostgreSQL environment variables.
    Returns:
        bool: True if DATABASE_URL was configured, False otherwise
    """
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    # Check if DATABASE_URL is already set
    if os.environ.get("DATABASE_URL"):
        logger.info("DATABASE_URL is already set")
        return True
    
    # Check if we have the individual PostgreSQL variables
    pghost = os.environ.get("PGHOST")
    pgport = os.environ.get("PGPORT")
    pguser = os.environ.get("PGUSER")
    pgpassword = os.environ.get("PGPASSWORD")
    pgdatabase = os.environ.get("PGDATABASE")
    
    # Verify all required variables are present
    if all([pghost, pgport, pguser, pgpassword, pgdatabase]):
        # Construct DATABASE_URL from individual components
        database_url = f"postgresql://{pguser}:{pgpassword}@{pghost}:{pgport}/{pgdatabase}"
        
        # Set the constructed DATABASE_URL in the environment
        os.environ["DATABASE_URL"] = database_url
        logger.info("Set DATABASE_URL from individual PostgreSQL variables")
        return True
    
    # If we get here, we couldn't set DATABASE_URL
    logger.warning("Could not set DATABASE_URL. Missing PostgreSQL environment variables.")
    return False

if __name__ == "__main__":
    configure_database_url()