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

def configure_secrets():
    """Configure all necessary secret values and environment variables"""
    # Create instance directory if it doesn't exist
    instance_path = 'instance'
    os.makedirs(instance_path, exist_ok=True)

    # Create and print the database URL
    sqlite_path = os.path.join(instance_path, 'dev.db')
    database_url = f'sqlite:///{sqlite_path}'
    print("\nDatabase URL:", database_url)

if __name__ == "__main__":
    create_database()