import os
import logging
import psycopg2

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
        
        # Test the connection before setting the environment variable
        try:
            # Setup connection string
            conn = psycopg2.connect(
                host=pghost,
                port=pgport,
                user=pguser,
                password=pgpassword,
                dbname=pgdatabase
            )
            conn.close()
            logger.info("Successfully tested PostgreSQL connection")
            
            # Set the constructed DATABASE_URL in the environment
            os.environ["DATABASE_URL"] = database_url
            logger.info("Set DATABASE_URL from individual PostgreSQL variables")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {str(e)}")
            return False
    
    # If we get here, we couldn't set DATABASE_URL
    logger.warning("Could not set DATABASE_URL. Missing PostgreSQL environment variables.")
    return False

def get_database_url():
    """
    Get the DATABASE_URL from environment variables or construct it 
    from individual PostgreSQL environment variables.
    Returns:
        str: The database URL or None if it cannot be determined
    """
    # Check if DATABASE_URL is already set
    if db_url := os.environ.get("DATABASE_URL"):
        return db_url
    
    # Check if we have the individual PostgreSQL variables
    pghost = os.environ.get("PGHOST")
    pgport = os.environ.get("PGPORT")
    pguser = os.environ.get("PGUSER")
    pgpassword = os.environ.get("PGPASSWORD")
    pgdatabase = os.environ.get("PGDATABASE")
    
    # Verify all required variables are present
    if all([pghost, pgport, pguser, pgpassword, pgdatabase]):
        # Construct DATABASE_URL from individual components
        return f"postgresql://{pguser}:{pgpassword}@{pghost}:{pgport}/{pgdatabase}"
    
    return None

if __name__ == "__main__":
    configure_database_url()