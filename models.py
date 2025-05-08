from datetime import datetime
from app import db, login_manager
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Float, Boolean
from sqlalchemy.orm import relationship
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(UserMixin, db.Model):
    """Model for user accounts"""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    username = Column(String(64), unique=True, nullable=False, index=True)
    email = Column(String(120), unique=True, nullable=False, index=True)
    password_hash = Column(String(256), nullable=False)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime)
    search_count_today = Column(Integer, default=0)  # Number of searches used today
    search_count_reset_date = Column(DateTime, default=datetime.utcnow)  # When the daily search count was last reset
    
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(str(self.password_hash), password)
    
    def __repr__(self):
        return f'<User {self.username}>'
        
    def check_search_limit(self):
        """Check if user has reached their daily search limit"""
        # Check if we need to reset the daily counter (new day)
        if self.search_count_reset_date is None or (datetime.utcnow().date() > self.search_count_reset_date.date()):
            # It's a new day, reset the counter
            self.search_count_today = 0
            self.search_count_reset_date = datetime.utcnow()
            return True  # User can search
        
        # Return True if user has searches remaining, False if limit reached
        return self.search_count_today < 15  # Daily limit is 15 searches
    
    def increment_search_count(self):
        """Increment the user's search count for today"""
        # First make sure the daily counter is current
        self.check_search_limit()
        # Increment counter
        self.search_count_today += 1
        return self.search_count_today
        
    def remaining_searches(self):
        """Return the number of searches remaining for the user today"""
        self.check_search_limit()  # Make sure the counter is current
        
        # Get the current search count as a Python int
        current_count = 0
        if self.search_count_today is not None:
            current_count = int(self.search_count_today)
            
        # Calculate remaining searches
        remaining = 15 - current_count
        if remaining < 0:
            return 0
        return remaining

class SearchQuery(db.Model):
    """Model for storing search queries"""
    __tablename__ = 'search_query'
    
    id = Column(Integer, primary_key=True)
    query_text = Column(String(255), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    ip_address = Column(String(45))  # IPv6 addresses can be up to 45 chars
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True)  # Can be null for anonymous searches
    is_public = Column(Boolean, default=True)  # Whether this search is visible to other users
    
    # Relationships
    results = relationship('SearchResult', backref='search_query', lazy=True, cascade="all, delete-orphan")
    user = relationship('User', backref='searches', lazy=True)
    
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
    
    def __repr__(self):
        return f"<SearchQuery {self.query_text}>"

class SearchResult(db.Model):
    """Model for storing search results"""
    __tablename__ = 'search_result'
    
    id = Column(Integer, primary_key=True)
    search_query_id = Column(Integer, ForeignKey('search_query.id'), nullable=False)
    title = Column(String(255), nullable=False)
    link = Column(String(2048), nullable=False)  # URLs can be long
    description = Column(Text)
    summary = Column(Text)
    rank = Column(Integer)  # Position in search results
    timestamp = Column(DateTime, default=datetime.utcnow)
    share_count = Column(Integer, default=0)  # Track number of times shared
    last_shared = Column(DateTime)  # Last time this summary was shared
    shared_by = Column(String(64))  # Username of user who shared it (if applicable)
    
    # Relationship to feedback
    feedback = relationship('SummaryFeedback', backref='search_result', lazy=True, cascade="all, delete-orphan")
    
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
    
    def increment_share_count(self, username=None):
        """Increment the share count and update last_shared timestamp"""
        current_count = 0
        if self.share_count is not None:
            current_count = self.share_count
        self.share_count = current_count + 1
        self.last_shared = datetime.utcnow()
        if username:
            self.shared_by = username
    
    def __repr__(self):
        title_value = self.title
        if isinstance(title_value, str):
            return f"<SearchResult {title_value[:30]}...>"
        return f"<SearchResult [No Title]>"

class SummaryFeedback(db.Model):
    """Model for storing user feedback on summaries"""
    __tablename__ = 'summary_feedback'
    
    id = Column(Integer, primary_key=True)
    search_result_id = Column(Integer, ForeignKey('search_result.id'), nullable=False)
    rating = Column(Integer)  # Rating from 1 to 5 stars
    comment = Column(Text)  # Optional comment from user
    helpful = Column(Boolean, default=False)  # Was the summary helpful?
    accurate = Column(Boolean, default=False)  # Was the summary accurate?
    complete = Column(Boolean, default=False)  # Was the summary complete?
    ip_address = Column(String(45))  # To prevent duplicate ratings
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
    
    def __repr__(self):
        return f"<SummaryFeedback id={self.id} rating={self.rating}>"

class AnonymousSearchLimit(db.Model):
    """Model for tracking anonymous user search limits via session IDs"""
    __tablename__ = 'anonymous_search_limit'
    
    id = Column(Integer, primary_key=True)
    session_id = Column(String(64), unique=True, nullable=False, index=True)
    search_count = Column(Integer, default=0)  # Number of searches used by this anonymous session
    first_search_date = Column(DateTime, default=datetime.utcnow)
    last_search_date = Column(DateTime, default=datetime.utcnow)
    ip_address = Column(String(45))  # To help identify patterns or abuse
    
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
    
    def __repr__(self):
        return f"<AnonymousSearchLimit session_id={self.session_id} count={self.search_count}>"
        
    def increment_search_count(self):
        """Increment the search count for this anonymous session"""
        self.search_count += 1
        self.last_search_date = datetime.utcnow()
        return self.search_count
        
    def check_search_limit(self):
        """Check if anonymous user has reached their total search limit (3)"""
        # Get the current count as a Python int
        current_count = 0
        if self.search_count is not None:
            current_count = int(self.search_count)
        
        # Anonymous users have a lifetime limit of 3 searches
        return current_count < 3
        
    def remaining_searches(self):
        """Return the number of searches remaining for anonymous users"""
        # Get the current count as a Python int
        current_count = 0
        if self.search_count is not None:
            current_count = int(self.search_count)
            
        # Calculate remaining searches
        remaining = 3 - current_count
        if remaining < 0:
            return 0
        return remaining