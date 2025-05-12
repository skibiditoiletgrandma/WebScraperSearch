#!/usr/bin/env python3

def fix_scraper_file():
    with open('scraper.py', 'r') as file:
        content = file.read()
    
    # Replace the import section with improved error handling
    new_import_section = """import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs
import re
import logging
import trafilatura
import random
import time
import os
from serpapi import GoogleSearch
from flask import flash

# Import ApiKey model and db from app
# Handle the case where we're importing this module outside of Flask context
try:
    from app import db
    from models import ApiKey
    HAS_DB = True
except ImportError:
    # Mock ApiKey for when models is not available (e.g., during imports)
    class ApiKey:
        @classmethod
        def get_next_active_key(cls, service, current_key_id=None):
            return None
        
        def mark_used(self):
            pass
        
        def record_error(self, error_message):
            pass
    
    HAS_DB = False
    db = None
"""

    old_import_section = content.split("# List of user agents to rotate for requests")[0]
    content = content.replace(old_import_section, new_import_section)
    
    # Replace all db.session.commit() with proper checks
    content = content.replace("if has_db and db is not None:", "if HAS_DB and db is not None:")
    
    # Fix specific db.session.commit() calls
    content = content.replace("db.session.commit()", 
                             "if HAS_DB and db is not None:\n            db.session.commit()")
    
    # Clean up any double conditionals that might have been created
    content = content.replace("if HAS_DB and db is not None:\n        if HAS_DB and db is not None:", 
                            "if HAS_DB and db is not None:")
    
    with open('scraper.py', 'w') as file:
        file.write(content)
    
    print("Fixed scraper.py file")

if __name__ == "__main__":
    fix_scraper_file()
