import logging
from app import app
from routes import *

if __name__ == "__main__":
    # Set up logging for debugging
    logging.basicConfig(level=logging.DEBUG)
    # Run the Flask app on port 5000 and bind to all interfaces
    app.run(host="0.0.0.0", port=5000, debug=True)
