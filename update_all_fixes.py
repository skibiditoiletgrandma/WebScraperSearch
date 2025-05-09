"""
Update All Fixes

This script automatically runs all available fix scripts to resolve common issues:
1. Ensures DATABASE_URL is configured correctly
2. Fixes attribute errors in forms
3. Updates user records with proper default values
4. Updates database schema as needed

Run this script whenever you encounter a 500 server error or after updating the application.
"""

import importlib
import logging
import sys
import os
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def run_module_if_exists(module_name, function_name=None):
    """Run a module if it exists, optionally calling a specific function"""
    try:
        if os.path.exists(f"{module_name}.py"):
            logger.info(f"Running {module_name}...")
            try:
                if function_name:
                    # Import the module and run a specific function
                    module = importlib.import_module(module_name)
                    func = getattr(module, function_name)
                    result = func()
                    if result is False:
                        logger.warning(f"{module_name}.{function_name} returned False")
                    return result
                else:
                    # Just import the module (will run __main__ code)
                    importlib.import_module(module_name)
                    return True
            except Exception as e:
                logger.error(f"Error running {module_name}: {e}")
                return False
        else:
            logger.info(f"Module {module_name} not found, skipping")
            return None
    except Exception as e:
        logger.error(f"Unexpected error with {module_name}: {e}")
        return False

def main():
    """Run all fix scripts in the correct order"""
    logger.info("Starting comprehensive fix process")
    
    # Step 1: Ensure database connection
    logger.info("Step 1: Ensuring database connection is configured")
    run_module_if_exists("ensure_db_url", "ensure_db_url")
    
    time.sleep(1)  # Short pause between steps
    
    # Step 2: Fix attribute errors in forms
    logger.info("Step 2: Fixing attribute errors in forms")
    run_module_if_exists("fix_attribute_errors")
    
    time.sleep(1)  # Short pause between steps
    
    # Step 3: Update user columns with proper defaults
    logger.info("Step 3: Updating user columns with proper defaults")
    run_module_if_exists("update_all_user_columns")
    
    time.sleep(1)  # Short pause between steps
    
    # Step 4: Update database schema if needed
    logger.info("Step 4: Updating database schema if needed")
    run_module_if_exists("update_schema", "update_database_schema")
    
    logger.info("All fix processes completed!")
    logger.info("Please restart the application for changes to take effect:")
    logger.info("   gunicorn --bind 0.0.0.0:5000 --reuse-port --reload main:app")

if __name__ == "__main__":
    main()