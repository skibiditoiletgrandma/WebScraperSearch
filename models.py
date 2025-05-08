from datetime import datetime
from app import db

class SearchQuery(db.Model):
    """Model for storing search queries"""
    id = db.Column(db.Integer, primary_key=True)
    query_text = db.Column(db.String(255), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    ip_address = db.Column(db.String(45))  # IPv6 addresses can be up to 45 chars
    
    # Relationship to search results
    results = db.relationship('SearchResult', backref='search_query', lazy=True, cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<SearchQuery {self.query_text}>"

class SearchResult(db.Model):
    """Model for storing search results"""
    id = db.Column(db.Integer, primary_key=True)
    search_query_id = db.Column(db.Integer, db.ForeignKey('search_query.id'), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    link = db.Column(db.String(2048), nullable=False)  # URLs can be long
    description = db.Column(db.Text)
    summary = db.Column(db.Text)
    rank = db.Column(db.Integer)  # Position in search results
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<SearchResult {self.title[:30]}...>"