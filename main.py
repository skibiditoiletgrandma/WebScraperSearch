import logging
import os
from datetime import timedelta
from configure_database_url import configure_database_url
from app import app, db, configure_database

# Set up logging for debugging
logging.basicConfig(level=logging.DEBUG)

# Configure session lifetime for anonymous users
app.permanent_session_lifetime = timedelta(days=365)  # Session lasts for 1 year

# Try to configure DATABASE_URL if it's not set
if not os.environ.get("DATABASE_URL"):
    # Try to construct DATABASE_URL from individual PostgreSQL variables
    if configure_database_url():
        # If successful, reconfigure the database with the new DATABASE_URL
        configure_database(app, force_refresh=True)

# Import routes after app is fully configured
from routes import *

if __name__ == "__main__":
    # Run the Flask app on port 5000 and bind to all interfaces
    app.run(host="0.0.0.0", port=5000, debug=True)
