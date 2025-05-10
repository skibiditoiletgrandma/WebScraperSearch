#!/usr/bin/env python3

def fix_scraper_file():
    with open('scraper.py', 'r') as file:
        lines = file.readlines()
    
    # Create a new file with fixed content
    with open('scraper.py.new', 'w') as file:
        for i, line in enumerate(lines):
            # Skip the problematic section
            if i >= 147 and i <= 151:
                continue
            
            # Replace duplicate HAS_DB checks
            if "if has_db and db is not None:" in line:
                file.write(line.replace("has_db", "HAS_DB"))
            else:
                file.write(line)
        
    # Rewrite the file with correct content
    with open('scraper.py.new', 'r') as f_new:
        content = f_new.read()
        
    # Fix all db.session.commit() calls with proper indentation and single check
    content = content.replace("db.session.commit()", """if HAS_DB and db is not None:
                db.session.commit()""")
    
    # Remove any nested/duplicated conditionals
    content = content.replace("if HAS_DB and db is not None:\n            if HAS_DB and db is not None:", 
                            "if HAS_DB and db is not None:")
    content = content.replace("if HAS_DB and db is not None:\n                if HAS_DB and db is not None:", 
                            "if HAS_DB and db is not None:")
    
    with open('scraper.py', 'w') as file:
        file.write(content)
    
    print("Fixed scraper.py file")

if __name__ == "__main__":
    fix_scraper_file()
