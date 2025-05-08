import os
import secrets
from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase

# Create base class for SQLAlchemy models
class Base(DeclarativeBase):
    pass

# Initialize SQLAlchemy with the base class
db = SQLAlchemy(model_class=Base)

# Create the Flask application
app = Flask(__name__)

# Set a secure secret key (generate a random one if not provided)
app.secret_key = os.environ.get("SESSION_SECRET") or secrets.token_hex(16)
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)  # needed for url_for to generate with https

# Configure app settings
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB max file size
app.config["SEARCH_RESULTS_LIMIT"] = 10  # Limit number of search results

# Configure database
database_url = os.environ.get("DATABASE_URL")
if database_url:
    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }
    # Initialize the app with the extension
    db.init_app(app)
    
    # Initialize database tables in app context
    with app.app_context():
        from models import SearchQuery, SearchResult, SummaryFeedback
        db.create_all()
        app.logger.info("Database tables initialized")
else:
    app.logger.warning("DATABASE_URL not set - database features will not be available")
