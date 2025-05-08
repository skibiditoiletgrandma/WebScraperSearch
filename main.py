import logging
from app import app, db
from routes import *

# Set up logging for debugging
logging.basicConfig(level=logging.DEBUG)

# Initialize database tables
with app.app_context():
    # Import the models to ensure they're registered with SQLAlchemy
    import models
    
    try:
        # Create all tables if they don't exist
        db.create_all()
        app.logger.info("Database tables created or already exist")
    except Exception as e:
        app.logger.error(f"Error creating database tables: {str(e)}")

if __name__ == "__main__":
    # Run the Flask app on port 5000 and bind to all interfaces
    app.run(host="0.0.0.0", port=5000, debug=True)
