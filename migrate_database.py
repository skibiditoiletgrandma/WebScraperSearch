
import os
from app import app, db
from models import User, SearchQuery, SearchResult, SummaryFeedback, AnonymousSearchLimit, Citation

def migrate_database():
    """Migrate data from primary to secondary database"""
    with app.app_context():
        # Get all data from models
        users = User.query.all()
        queries = SearchQuery.query.all()
        results = SearchResult.query.all()
        feedbacks = SummaryFeedback.query.all()
        anon_limits = AnonymousSearchLimit.query.all()
        citations = Citation.query.all()
        
        # Switch to secondary database
        app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL_2")
        db.create_all()  # Create tables in new database
        
        # Insert all data
        for user in users:
            db.session.add(user)
        for query in queries:
            db.session.add(query)
        for result in results:
            db.session.add(result)
        for feedback in feedbacks:
            db.session.add(feedback)
        for limit in anon_limits:
            db.session.add(limit)
        for citation in citations:
            db.session.add(citation)
            
        db.session.commit()
        print("Database migration completed successfully!")

if __name__ == "__main__":
    migrate_database()
