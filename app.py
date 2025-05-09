import os
import secrets
from datetime import timedelta
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
# Set remember cookie duration to 1 year (365 days)
app.config['REMEMBER_COOKIE_DURATION'] = timedelta(days=365)
app.config['REMEMBER_COOKIE_SECURE'] = True
app.config['REMEMBER_COOKIE_HTTPONLY'] = True
app.config['REMEMBER_COOKIE_REFRESH_EACH_REQUEST'] = True

# Configure database connection and setup function for dynamic configuration
def configure_database(app_instance, force_refresh=False):
    """Configure database connection dynamically
    
    Args:
        app_instance: The Flask application instance
        force_refresh: Whether to refresh the connection even if already configured
    """
    database_url = os.environ.get("DATABASE_URL")  # Check for database URL
    app_instance.logger.info(f"Database URL detected: {'Yes' if database_url else 'No'}")
    
    # Set up SQLAlchemy configuration
    if database_url:
        app_instance.config["SQLALCHEMY_DATABASE_URI"] = database_url
            
        app_instance.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
            "pool_recycle": 300,
            "pool_pre_ping": True,
        }
        app_instance.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
        
        # Initialize the app with the extension
        db.init_app(app_instance)
        
        # Initialize database tables in app context
        try:
            with app_instance.app_context():
                from models import SearchQuery, SearchResult, SummaryFeedback, User, AnonymousSearchLimit
                db.create_all()
                app_instance.logger.info("Database tables initialized successfully")
        except Exception as e:
            app_instance.logger.error(f"Error initializing database tables: {str(e)}")
        
        return True
    else:
        app_instance.logger.error("DATABASE_URL is not set. Using SQLite for development only.")
        # Use SQLite as a fallback for development
        instance_path = os.path.join(app_instance.root_path, 'instance')
        if not os.path.exists(instance_path):
            os.makedirs(instance_path)
        app_instance.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(instance_path, "dev.db")
        app_instance.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
        db.init_app(app_instance)
        
        # Initialize database tables in app context
        try:
            with app_instance.app_context():
                from models import SearchQuery, SearchResult, SummaryFeedback, User, AnonymousSearchLimit
                db.create_all()
                app_instance.logger.info("SQLite database tables initialized successfully")
        except Exception as e:
            app_instance.logger.error(f"Error initializing SQLite database tables: {str(e)}")
        
        app_instance.logger.warning("No DATABASE_URL set. Database functionality will be limited.")
        app_instance.logger.warning("Please set DATABASE_URL to enable full functionality.")
        return False

# Initialize the database with the current configuration
configure_database(app)
