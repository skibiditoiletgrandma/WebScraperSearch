import os
import sys
from app import app, db
from models import User
from getpass import getpass
from datetime import datetime

def create_admin_user():
    """Create an admin user for the application"""
    print("Create Admin User")
    print("================")
    
    try:
        # Check if any admin users already exist
        with app.app_context():
            existing_admin = User.query.filter_by(is_admin=True).first()
            if existing_admin:
                print(f"Admin user already exists: {existing_admin.username} ({existing_admin.email})")
                answer = input("Do you want to create another admin user? (y/n): ")
                if answer.lower() != 'y':
                    print("Operation cancelled.")
                    return
            
            # Collect user information
            username = input("Enter username: ")
            if not username:
                print("Username cannot be empty.")
                return
            
            # Check if username already exists
            existing_user = User.query.filter_by(username=username).first()
            if existing_user:
                print(f"Username '{username}' is already taken.")
                return
            
            email = input("Enter email address: ")
            if not email or '@' not in email:
                print("Please enter a valid email address.")
                return
            
            # Check if email already exists
            existing_email = User.query.filter_by(email=email).first()
            if existing_email:
                print(f"Email '{email}' is already registered.")
                return
            
            # Get password with confirmation
            password = getpass("Enter password (input will be hidden): ")
            if not password or len(password) < 8:
                print("Password must be at least 8 characters long.")
                return
            
            confirm_password = getpass("Confirm password (input will be hidden): ")
            if password != confirm_password:
                print("Passwords do not match.")
                return
            
            # Create the admin user
            user = User(
                username=username,
                email=email,
                is_admin=True,
                created_at=datetime.utcnow()
            )
            user.set_password(password)
            
            # Save to database
            db.session.add(user)
            db.session.commit()
            
            print(f"\nAdmin user '{username}' created successfully!")
            print("You can now log in to the application with these credentials.")
    
    except Exception as e:
        print(f"Error creating admin user: {str(e)}")
        return

if __name__ == "__main__":
    create_admin_user()