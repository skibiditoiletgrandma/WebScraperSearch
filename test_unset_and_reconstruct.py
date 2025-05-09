import os
import logging
from get_database_url import ensure_database_url

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_unset_and_reconstruct():
    """
    Test unsetting DATABASE_URL and then reconstructing it
    from individual PostgreSQL environment variables
    """
    # Save the current DATABASE_URL value
    original_url = os.environ.get("DATABASE_URL")
    
    if original_url:
        logger.info("Original DATABASE_URL is set")
        # Temporarily unset DATABASE_URL
        try:
            os.environ.pop("DATABASE_URL")
            logger.info("Temporarily unset DATABASE_URL")
            
            # Now try to reconstruct it
            logger.info("Attempting to reconstruct DATABASE_URL...")
            new_url = ensure_database_url()
            
            if new_url:
                # Make a masked version for logging
                masked_url = new_url.split('@')[0].split(':')[0] + ":*****@*****"
                logger.info(f"Successfully reconstructed DATABASE_URL: {masked_url}")
                
                # Check if it matches the original (except for credentials part which might be ordered differently)
                host_port_db_original = original_url.split('@')[1] if '@' in original_url else ""
                host_port_db_new = new_url.split('@')[1] if '@' in new_url else ""
                
                if host_port_db_original == host_port_db_new:
                    logger.info("Reconstructed URL matches original (host/port/database)")
                else:
                    logger.warning("Reconstructed URL differs from original!")
                
                return True
            else:
                logger.error("Failed to reconstruct DATABASE_URL")
                return False
        finally:
            # Always restore the original DATABASE_URL
            if original_url:
                os.environ["DATABASE_URL"] = original_url
                logger.info("Restored original DATABASE_URL")
    else:
        logger.warning("No DATABASE_URL set to begin with")
        
        # Try to create one from scratch
        new_url = ensure_database_url()
        if new_url:
            masked_url = new_url.split('@')[0].split(':')[0] + ":*****@*****"
            logger.info(f"Created new DATABASE_URL: {masked_url}")
            return True
        else:
            logger.error("Couldn't create DATABASE_URL")
            return False

if __name__ == "__main__":
    success = test_unset_and_reconstruct()
    print(f"Test {'passed' if success else 'failed'}")
    
    # Check if DATABASE_URL is still set to make sure we restored it
    if os.environ.get("DATABASE_URL"):
        print("DATABASE_URL is currently set")
    else:
        print("Warning: DATABASE_URL is NOT set")