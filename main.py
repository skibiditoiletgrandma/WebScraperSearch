import logging
from app import app, db
from routes import *

# Initialize database tables
with app.app_context():
    # Import the models to ensure they're registered with SQLAlchemy
    import models
    
    # Create all tables
    db.create_all()
    app.logger.info("Database tables created")

if __name__ == "__main__":
    # Set up logging for debugging
    logging.basicConfig(level=logging.DEBUG)
    # Run the Flask app on port 5000 and bind to all interfaces
    app.run(host="0.0.0.0", port=5000, debug=True)
