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
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username}>'

class SearchQuery(db.Model):
    """Model for storing search queries"""
    __tablename__ = 'search_query'
    
    id = Column(Integer, primary_key=True)
    query_text = Column(String(255), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    ip_address = Column(String(45))  # IPv6 addresses can be up to 45 chars
    
    # Relationship to search results
    results = relationship('SearchResult', backref='search_query', lazy=True, cascade="all, delete-orphan")
    
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
    
    # Relationship to feedback
    feedback = relationship('SummaryFeedback', backref='search_result', lazy=True, cascade="all, delete-orphan")
    
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
    
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