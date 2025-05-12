with open('scraper.py', 'r') as file:
    content = file.read()

# Fix strange indentation in the code
content = content.replace('if has_db and db is not None:\n\n            db.session.commit()', 
                         'if has_db and db is not None:\n            db.session.commit()')
content = content.replace('if has_db and db is not None:\n\n                db.session.commit()', 
                         'if has_db and db is not None:\n                db.session.commit()')
content = content.replace('if has_db and db is not None:\n\n                    db.session.commit()', 
                         'if has_db and db is not None:\n                    db.session.commit()')

with open('scraper.py', 'w') as file:
    file.write(content)

print("Fixed for matting issues  in scraper.py")
