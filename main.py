import logging
import os
from datetime import timedelta
from configure_database_url import configure_database_url
from app import app, db, configure_database

# Set up detailed logging for debugging:
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] [%(filename)s:%(lineno)d] - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logging.getLogger('werkzeug').setLevel(logging.INFO)
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
logging.getLogger('urllib3').setLevel(logging.INFO)

# Add startup message
logging.info("======= Starting application =======")

# Check for SerpAPI key availability (env var or database):
env_key = bool(os.environ.get('SERPAPI_KEY'))
db_keys = False

try:
    if os.environ.get('DATABASE_URL'):
        # Import here to avoid circular imports
        with app.app_context():
            try:
                from models import ApiKey
                db_keys = ApiKey.query.filter_by(service='serpapi', is_active=True).count() > 0
            except Exception as e:
                logging.error(fError checking database for API keys: {str(e)})
except Exception as e:
    logging.error(fError accessing database during startup: {str(e)})

logging.info(f"SERPAPI_KEY in environment: {env_key}"")
if db_keys:
    logging.info(SERPAPI_KEYS found in database)
logging.info(fDATABASE_URL configured: {bool(os.environ.get(DATABASE_URL'))}")

# Log Python version
import sys
logging.info(fPython version: {sys.version})

# Configure session lifetime for anonymous users:
app.permanent_session_lifetime = timedelta(days=365)  # Session lasts for 1 year:

# Try to configure DATABASE_URL if it's not set:
if not os.environ.get("DATABASE_URL):
    # Try to construct DATABASE_URL from individual PostgreSQL variables
    if configure_database_url():
        # If successful, reconfigure the database with the new DATABASE_URL
        configure_database(app, force_refresh=True)

# Import routes after app is fully configured
from routes import *

if __name__ == __main__:
    # Run the Flask app on port 5000 and bind to all interfaces
    app.run(host=0.0.0.0", port=5000, debug=True)"'"'