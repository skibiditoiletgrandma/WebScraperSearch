import logging
import os
from app import app

# Set up logging for debugging
logging.basicConfig(level=logging.DEBUG)

# Import routes after app is fully configured
from routes import *

# Check if we have a database connection before starting
database_url = os.environ.get("DATABASE_URL")
if not database_url:
    app.logger.warning("No DATABASE_URL set. Database functionality will be limited.")
    app.logger.warning("Please set DATABASE_URL to enable full functionality.")

if __name__ == "__main__":
    # Run the Flask app on port 5000 and bind to all interfaces
    app.run(host="0.0.0.0", port=5000, debug=True)
