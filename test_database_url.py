import os
import logging
from get_database_url import ensure_database_url

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_database_url_configuration():
    """Test the DATABASE_URL configuration mechanism"""
    # Test if DATABASE_URL gets set automatically
    logger.info("Testing DATABASE_URL configuration...")
    
    # Get the current value (may be None)
    current_url = os.environ.get("DATABASE_URL")
    logger.info(f"Initial DATABASE_URL: {'Set' if current_url else 'Not set'}")
    
    # Try to ensure it's set
    result_url = ensure_database_url()
    logger.info(f"After ensure_database_url(): {'Set' if result_url else 'Not set'}")
    
    if result_url:
        # Don't print the actual URL for security, just show that it's set
        masked_url = result_url.split('@')[0].split(':')[0] + ":*****@*****"
        logger.info(f"DATABASE_URL is now set to: {masked_url}")
        return True
    else:
        logger.warning("Could not set DATABASE_URL")
        return False

if __name__ == "__main__":
    success = test_database_url_configuration()
    print(f"Test {'passed' if success else 'failed'}: {'DATABASE_URL is set' if success else 'Could not set DATABASE_URL'}")