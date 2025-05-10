import os
import sys
from app import app, db
from models import User
from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError

def create_default_admin():
    """Create a default admin user for the application"""
    
    print("Creating default admin user...")
    
    # Default admin credentials
    username = "admin"
    email = "admin@example.com"
    password = "admin123456"
    
    try:
        with app.app_context():
            # Make sure all tables exist
            db.create_all()
            
            # Check if the admin already exists
            try:
                existing_admin = User.query.filter_by(username=username).first()
                
                if existing_admin:
                    print(f"Admin user '{username}' already exists.")
                    return
            except SQLAlchemyError as e:
                print(f"Error checking for existing admin: {str(e)}")
                print("Attempting to create admin anyway...")
            
            # Create new admin user
            admin = User(
                username=username,
                email=email,
                is_admin=True,
                created_at=datetime.utcnow(),
                search_count_today=0,
                search_pages_limit=1,
                hide_wikipedia=False,
                show_feedback_features=True,
                enable_suggestions=True,
                generate_summaries=True,
                summary_depth=3,
                summary_complexity=3
            )
            admin.set_password(password)
            
            # Save to database
            db.session.add(admin)
            db.session.commit()
            
            print(f"Admin user created successfully!")
            print(f"Username: {username}")
            print(f"Password: {password}")
            print(f"Email: {email}")
            print("\nIMPORTANT: Change these default credentials in production!")
    
    except Exception as e:
        print(f"Error creating admin user: {str(e)}")
        print(f"Exception type: {type(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    create_default_admin()