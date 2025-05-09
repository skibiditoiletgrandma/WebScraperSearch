
import os
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import psycopg2
from urllib.parse import urlparse

# Create base class for SQLAlchemy models
Base = declarative_base()

# Define a simple model
class Note(Base):
    __tablename__ = 'notes'

    id = Column(Integer, primary_key=True)
    title = Column(String(100), nullable=False)
    content = Column(String(500))
    created_at = Column(DateTime, default=datetime.utcnow)

def create_database():
    # Get database URL from environment
    database_url = os.environ.get('DATABASE_URL')
    
    if not database_url:
        print("Error: DATABASE_URL environment variable not set")
        return

    # Parse the URL to get database name
    url = urlparse(database_url)
    db_name = url.path[1:]  # Remove leading slash
    
    try:
        # Create database engine
        engine = create_engine(database_url)
        
        # Create all tables
        Base.metadata.create_all(engine)
        
        # Create a session factory
        Session = sessionmaker(bind=engine)
        
        # Create a session
        session = Session()
        
        try:
            # Add a sample note
            note = Note(
                title="First Note",
                content="This is our first note in the PostgreSQL database!"
            )
            session.add(note)
            session.commit()
            print("Database created successfully!")
            print(f"Database URL: {database_url}")
            
        except Exception as e:
            print(f"Error: {e}")
            session.rollback()
        finally:
            session.close()
            
    except Exception as e:
        print(f"Error creating database: {e}")

if __name__ == "__main__":
    create_database()
