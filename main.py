import logging
import os
from datetime import timedelta
from configure_database_url import configure_database_url
from app import app, db

# Set up logging for debugging
logging.basicConfig(level=logging.DEBUG)

# Configure session lifetime for anonymous users
app.permanent_session_lifetime = timedelta(days=365)  # Session lasts for 1 year

# Try to configure DATABASE_URL if it's not set
if not os.environ.get("DATABASE_URL"):
    configure_database_url()
    
# Import routes after app is fully configured
from routes import *

# Check if we have a database connection before starting
database_url = os.environ.get("DATABASE_URL")
if not database_url:
    app.logger.warning("No DATABASE_URL set. Database functionality will be limited.")
    app.logger.warning("Please set DATABASE_URL to enable full functionality.")
    # Initialize database tables for SQLite anyway
    try:
        with app.app_context():
            from models import SearchQuery, SearchResult, SummaryFeedback, User, AnonymousSearchLimit
            db.create_all()
            app.logger.info("SQLite database tables initialized successfully")
    except Exception as e:
        app.logger.error(f"Error initializing SQLite database tables: {str(e)}")

if __name__ == "__main__":
    # Run the Flask app on port 5000 and bind to all interfaces
    app.run(host="0.0.0.0", port=5000, debug=True)
