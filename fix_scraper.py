import re

def add_db_check_before_commit(file_path):
    with open(file_path, 'r') as file:
        content = file.read()
    
    # Use regex to find db.session.commit() and replace with conditional check
    pattern = r'(\s+)db\.session\.commit\(\)'
    replacement = r'\1if has_db and db is not None:\n\1    db.session.commit()'
    
    updated_content = re.sub(pattern, replacement, content)
    
    with open(file_path, 'w') as file:
        file.write(updated_content)
    
    print(f"Fixed db.session.commit() calls in {file_path}")

add_db_check_before_commit('scraper.py')
