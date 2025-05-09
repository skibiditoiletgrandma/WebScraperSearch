
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime
import os

# Create the base class for declarative models
Base = declarative_base()

# Define a sample model
class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    username = Column(String(64), unique=True, nullable=False)
    email = Column(String(120), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

def create_database():
    # Create instance directory if it doesn't exist
    instance_path = 'instance'
    os.makedirs(instance_path, exist_ok=True)
    
    # Database URL
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        # Use SQLite as fallback
        sqlite_path = os.path.join(instance_path, 'dev.db')
        database_url = f'sqlite:///{sqlite_path}'
        print(f"Using SQLite database at: {sqlite_path}")
    
    # Create engine
    engine = create_engine(database_url)
    
    try:
        # Create all tables
        Base.metadata.create_all(engine)
        
        # Create a session factory
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Add a sample user
        sample_user = User(
            username='sample_user',
            email='sample@example.com'
        )
        
        # Add and commit the sample user
        session.add(sample_user)
        session.commit()
        
        print("Database created successfully!")
        print(f"Created sample user: {sample_user.username}")
        
    except Exception as e:
        print(f"Error creating database: {e}")
        if session:
            session.rollback()
    finally:
        if session:
            session.close()

if __name__ == "__main__":
    create_database()
