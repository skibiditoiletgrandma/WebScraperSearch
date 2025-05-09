from app import app, db

def update_citation_schema():
    """Update the database schema to include the citation table"""
    with app.app_context():
        db.create_all()
        print("Database schema updated to include the citations table.")

if __name__ == '__main__':
    update_citation_schema()