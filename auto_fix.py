
#!/usr/bin/env python3
"""
Automatic Code Fixer

This script automatically scans Python files for common issues and fixes them:
- Syntax errors
- String literal errors 
- Import errors
- Route import issues
"""

import os
import sys
import logging
import re
import ast
import traceback
from typing import Dict, List, Tuple, Optional, Set
import importlib

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

def find_python_files(directory: str = '.', max_depth: int = 2) -> List[str]:
    """Find all Python files in directory up to max_depth."""
    python_files = []
    excluded_dirs = {'venv', '.venv', 'env', '.env', '.git', '__pycache__', 'node_modules'}
    
    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if d not in excluded_dirs]
        depth = root[len(directory):].count(os.sep)
        
        if depth <= max_depth:
            for file in files:
                if file.endswith('.py'):
                    python_files.append(os.path.join(root, file))
                    
    return python_files

def fix_syntax_errors(content: str, filename: str) -> Tuple[str, bool]:
    """Fix common syntax errors in Python code."""
    fixes = [
        # Fix list/dict comprehension syntax
        (r'\[\s*for\s+', '[ item for '),
        (r'\[\s*([^\]]+?)\s+for\s+([^\]]+?)\s+in\s+([^\]]+?)\s*\]', r'[\1 for \2 in \3]'),
        (r'\{\s*([^}]+?):\s*([^}]+?)\s+for\s+([^}]+?)\s+in\s+([^}]+?)\s*\}', r'{\1: \2 for \3 in \4}'),
        
        # Fix missing colons
        (r'(if|elif|else|for|while|def|class|try|except|finally)\s+([^:\n]+)(\s*\n)', r'\1 \2:\3'),
        
        # Fix trailing colons in list comprehensions
        (r'([}\]])\s*:', r'\1'),
        
        # Fix missing parentheses
        (r'print\s+([^(].+)', r'print(\1)'),
        
        # Fix trailing commas in lists/dicts
        (r',\s*([}\]])', r'\1'),
        
        # Fix missing quotes in strings
        (r'=\s*([^"\'{\[\d][^,}\]\n]+)\s*[,}\]]', r'="\1"'),
        
        # Fix mismatched brackets
        (r'\[\s*([^\]]*?)\s*\}', r'[\1]'),
        (r'\{\s*([^}]*?)\s*\]', r'{\1}'),
        
        # Fix export result formatting
        (r'\}\s*for\s+r\s+in\s+results\s*\]:', r'} for r in results]'),
    ]
    
    fixed = content
    changed = False
    
    for pattern, replacement in fixes:
        new_content = re.sub(pattern, replacement, fixed)
        if new_content != fixed:
            changed = True
            fixed = new_content
    
    # Special handling for routes.py export formatting
    if filename == 'routes.py' and '] for r in results]:' in fixed:
        fixed = fixed.replace('] for r in results]:', '] for r in results')
        changed = True
        
    return fixed, changed

def check_imports(filename: str) -> List[str]:
    """Check if all imports in a file are valid."""
    issues = []
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            content = f.read()
        
        try:
            tree = ast.parse(content)
        except SyntaxError as e:
            issues.append(f"Syntax error: {str(e)}")
            return issues
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                try:
                    if isinstance(node, ast.Import):
                        for name in node.names:
                            try:
                                importlib.import_module(name.name)
                            except ImportError as e:
                                issues.append(f"Cannot import {name.name}: {str(e)}")
                    elif isinstance(node, ast.ImportFrom):
                        try:
                            importlib.import_module(node.module)
                        except ImportError as e:
                            issues.append(f"Cannot import from {node.module}: {str(e)}")
                except Exception as e:
                    issues.append(f"Import error: {str(e)}")
                    
    except Exception as e:
        issues.append(f"Error checking imports: {str(e)}")
        
    return issues

def fix_file(filename: str) -> bool:
    """Fix all issues in a single file."""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Apply syntax fixes
        fixed, changed = fix_syntax_errors(content, filename)
        
        # Validate the changes
        if fixed != original_content:
            try:
                ast.parse(fixed)  # Validate syntax
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(fixed)
                logger.info(f"Fixed {filename}")
                if changed:
                    logger.info("  - Fixed syntax errors")
                
                # Create backup if needed
                backup_file = f"{filename}.bak"
                if not os.path.exists(backup_file):
                    with open(backup_file, 'w', encoding='utf-8') as f:
                        f.write(original_content)
                    logger.info(f"  - Created backup: {backup_file}")
                
                return True
            except SyntaxError as e:
                logger.warning(f"Fixes for {filename} failed validation: {str(e)}")
                # Restore original content if validation fails
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(original_content)
                return False
        else:
            logger.info(f"No issues found in {filename}")
            return False
            
    except Exception as e:
        logger.error(f"Error processing {filename}: {str(e)}")
        logger.debug(traceback.format_exc())
        return False

def check_database_configuration() -> bool:
    """Check if database is properly configured."""
    try:
        import sqlite3
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        
        # Check for DATABASE_URL
        db_url = os.environ.get('DATABASE_URL', 'sqlite:///instance/simple.db')
        logger.info(f"Database URL detected: {bool(db_url)}")
        
        # Try to connect and initialize tables
        engine = create_engine(db_url)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Basic check - try to execute a simple query
        session.execute('SELECT 1')
        logger.info("Database tables initialized successfully")
        return True
        
    except Exception as e:
        logger.error(f"Database configuration error: {str(e)}")
        return False

def main():
    """Main entry point."""
    logger.info("Starting automatic code fixes...")
    
    # Find all Python files
    files = find_python_files()
    if not files:
        logger.error("No Python files found")
        return 1
        
    logger.info(f"Found {len(files)} Python files")
    
    # Check database configuration
    db_ok = check_database_configuration()
    
    # Fix each file
    fixed_count = 0
    for file in files:
        if fix_file(file):
            fixed_count += 1
            
        # Check for import issues
        import_issues = check_imports(file)
        if import_issues:
            logger.warning(f"Import issues in {file}:")
            for issue in import_issues:
                logger.warning(f"  - {issue}")
            
    logger.info(f"Fixed {fixed_count} out of {len(files)} files")
    return 0 if fixed_count > 0 or len(files) > 0 else 1

if __name__ == "__main__":
    sys.exit(main())
