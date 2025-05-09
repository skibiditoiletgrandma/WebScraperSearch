
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

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
    # Use SQLite as the database
    db_path = os.path.join('instance', 'simple.db')
    
    # Create instance directory if it doesn't exist
    os.makedirs('instance', exist_ok=True)
    
    # Create database engine
    engine = create_engine(f'sqlite:///{db_path}')
    
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
            content="This is our first note in the database!"
        )
        session.add(note)
        session.commit()
        print("Database created successfully!")
        print(f"Database location: {db_path}")
        
    except Exception as e:
        print(f"Error: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    create_database()
