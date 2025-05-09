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
from configure_database_url import configure_database_url

def ensure_db_url():
    """
    Ensure DATABASE_URL is set in environment variables.
    If it's not set, construct it from individual PostgreSQL variables.
    
    Returns:
        bool: True if DATABASE_URL is set (or was successfully set), False otherwise
    """
    # Check if DATABASE_URL is already set
    if os.environ.get("DATABASE_URL"):
        return True
    
    # Configure it from individual PostgreSQL environment variables
    success = configure_database_url()
    
    if not success:
        logging.error(
            "DATABASE_URL is not set and could not be constructed from PostgreSQL variables. "
            "Make sure PGHOST, PGPORT, PGUSER, PGPASSWORD, and PGDATABASE are properly set."
        )
    
    return success

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