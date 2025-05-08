import os
import secrets
from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from flask_login import LoginManager

# Create base class for SQLAlchemy models
class Base(DeclarativeBase):
    pass

# Initialize SQLAlchemy with the base class
db = SQLAlchemy(model_class=Base)

# Initialize Flask-Login
login_manager = LoginManager()

# Create the Flask application
app = Flask(__name__)

# Set a secure secret key (generate a random one if not provided)
app.secret_key = os.environ.get("SESSION_SECRET") or secrets.token_hex(16)
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)  # needed for url_for to generate with https

# Configure app settings
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB max file size
app.config["SEARCH_RESULTS_LIMIT"] = 10  # Limit number of search results

# Configure login settings
login_manager.init_app(app)
login_manager.login_view = 'login'  # type: ignore
login_manager.login_message = 'Please log in to access this page'
login_manager.login_message_category = 'info'

# Configure database
database_url = os.environ.get("DATABASE_URL")
app.logger.info(f"Database URL detected: {'Yes' if database_url else 'No'}")

# Set up SQLAlchemy configuration
if database_url:
    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    
    # Initialize the app with the extension
    db.init_app(app)
else:
    app.logger.error("DATABASE_URL is not set. Using SQLite for development only.")
    # Use SQLite as a fallback for development
    import os
    instance_path = os.path.join(app.root_path, 'instance')
    if not os.path.exists(instance_path):
        os.makedirs(instance_path)
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(instance_path, "dev.db")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db.init_app(app)

# Initialize database tables in app context if database URL is set
if database_url:
    try:
        with app.app_context():
            from models import SearchQuery, SearchResult, SummaryFeedback, User
            db.create_all()
            app.logger.info("Database tables initialized successfully")
    except Exception as e:
        app.logger.error(f"Error initializing database tables: {str(e)}")
else:
    app.logger.warning("DATABASE_URL not set - database features will not be available")
