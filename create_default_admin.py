import os
from app import app, db
from models import User
from datetime import datetime

def create_default_admin():
    """Create a default admin user for the application"""
    
    # Default admin credentials
    username = "admin"
    email = "admin@example.com"
    password = "admin123456"
    
    try:
        with app.app_context():
            # Check if the admin already exists
            existing_admin = User.query.filter_by(username=username).first()
            
            if existing_admin:
                print(f"Admin user '{username}' already exists.")
                return
            
            # Create new admin user
            admin = User(
                username=username,
                email=email,
                is_admin=True,
                created_at=datetime.utcnow()
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

if __name__ == "__main__":
    create_default_admin()