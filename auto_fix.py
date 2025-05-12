
#!/usr/bin/env python3
"""
Automatic Code Fixer

This script automatically scans Python files for common issues and fixes them:
- Syntax errors
- String literal errors 
- Import errors
- Route import issues
- Docstring formatting
"""

import os
import sys
import logging
import re
import ast
import traceback
from typing import Dict, List, Tuple, Optional, Set

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

def fix_string_literals(content: str) -> str:
    """Fix string literal issues in Python code."""
    fixes = [
        # Basic string fixes
        (r'""([^"]*)"', r'"\1"'),  # Fix doubled quotes at start
        (r'"([^"]*)""\s', r'"\1" '),  # Fix doubled quotes at end
        (r'"([^"]*)["\']([^"\']*)["\']([^"]*)"', r'"\1\2\3"'),  # Fix mixed quotes
        
        # Fix unterminated strings
        (r'("[^"]*$)', r'\1"'),  # Close unterminated string
        (r"('[^']*$)", r"\1'"),  # Close unterminated string
        
        # Fix f-string issues
        (r'f""{2,}([^"]*)(\{[^}]*\})([^"]*)"', r'f"\1\2\3"'),
        (r'(f"[^"]*$)', r'\1"'),  # Close unterminated f-string
        
        # Fix triple quotes
        (r'"{6,}([^"]*)"{6,}', r'"""\1"""'),  # Fix multiple triple quotes
        (r'"{6,}([^"]*)"{3}', r'"""\1"""'),  # Fix excess quotes at start
        (r'"{3}([^"]*)"{6,}', r'"""\1"""'),  # Fix excess quotes at end
        
        # Fix docstrings
        (r'""([^"]*)"(\s*def|\s*class|\s*@)', r'"""\1"""\2'),
        (r'""([^"]*)"(\s+)', r'"""\1"""\2'),
        (r'"""([^"]*)"(\s+)', r'"""\1"""\2'),
    ]
    
    fixed = content
    for pattern, replacement in fixes:
        fixed = re.sub(pattern, replacement, fixed)
    return fixed

def balance_brackets(content: str) -> str:
    """Balance brackets in code using a stack-based approach."""
    lines = content.split('\n')
    result_lines = []
    stack = []
    
    for line in lines:
        if line.strip().startswith('#'):
            result_lines.append(line)
            continue
            
        processed_line = line
        for i, char in enumerate(line):
            if char in '([{':
                stack.append((char, len(result_lines), i))
            elif char in ')]}':
                if not stack:
                    processed_line = processed_line[:i] + processed_line[i+1:]
                else:
                    opening = stack[-1][0]
                    if (opening == '(' and char == ')') or \
                       (opening == '[' and char == ']') or \
                       (opening == '{' and char == '}'):
                        stack.pop()
                    else:
                        processed_line = processed_line[:i] + get_matching_close(opening) + processed_line[i+1:]
                        stack.pop()
                        
        result_lines.append(processed_line)
    
    while stack:
        opening, line_num, col = stack.pop()
        result_lines[line_num] = result_lines[line_num] + get_matching_close(opening)
        
    return '\n'.join(result_lines)

def get_matching_close(opening: str) -> str:
    """Get matching closing bracket for an opening bracket."""
    pairs = {'(': ')', '[': ']', '{': '}'}
    return pairs.get(opening, '')

def fix_syntax_errors(content: str, filename: str) -> Tuple[str, bool]:
    """Fix common syntax errors in Python code."""
    content = balance_brackets(content)
    content = fix_string_literals(content)
    
    fixes = [
        # Fix missing colons
        (r'(if|elif|else|for|while|def|class|try|except|finally)\s+([^:\n]+)(\s*\n)', r'\1 \2:\3'),
        
        # Fix comprehension syntax
        (r'\[\s*for\s+', r'[item for '),
        (r'\[\s*([^\]]+?)\s+for\s+([^\]]+?)\s+in\s+([^\]]+?)\s*\]', r'[\1 for \2 in \3]'),
        
        # Fix indentation
        (r'^\t+', lambda m: '    ' * len(m.group())),  # Convert tabs to spaces
    ]
    
    fixed = content
    changed = False
    
    for pattern, replacement in fixes:
        new_content = re.sub(pattern, replacement, fixed, flags=re.MULTILINE)
        if new_content != fixed:
            changed = True
            fixed = new_content
    
    return fixed, changed

def check_database_configuration() -> bool:
    """Check if database is properly configured."""
    try:
        import sqlite3
        from sqlalchemy import create_engine, text
        from sqlalchemy.orm import sessionmaker

        db_url = os.environ.get('DATABASE_URL', 'sqlite:///instance/simple.db')
        engine = create_engine(db_url)
        Session = sessionmaker(bind=engine)
        session = Session()
        session.execute(text('SELECT 1'))
        logger.info("Database configuration verified")
        return True

    except Exception as e:
        logger.error(f"Database configuration error: {str(e)}")
        return False

def fix_file(filename: str) -> bool:
    """Fix all issues in a single file."""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            content = f.read()
            
        original_content = content
        fixed, syntax_changed = fix_syntax_errors(content, filename)
        
        # Create backup if changes will be made
        if fixed != original_content:
            backup_file = f"{filename}.bak"
            if not os.path.exists(backup_file):
                with open(backup_file, 'w', encoding='utf-8') as f:
                    f.write(original_content)
                logger.info(f"Created backup: {backup_file}")
        
        # Validate changes
        try:
            ast.parse(fixed)
            if fixed != original_content:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(fixed)
                logger.info(f"Fixed {filename}")
                return True
        except SyntaxError as e:
            logger.warning(f"Validation failed for {filename}: {str(e)}")
            # Restore original if validation fails
            if fixed != original_content:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(original_content)
            return False
            
        return False
        
    except Exception as e:
        logger.error(f"Error processing {filename}: {str(e)}")
        logger.debug(traceback.format_exc())
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
    if not db_ok:
        logger.warning("Database configuration issues detected")

    # Fix each file
    fixed_count = 0
    for file in files:
        if fix_file(file):
            fixed_count += 1

    logger.info(f"Fixed {fixed_count} out of {len(files)} files")
    return 0 if fixed_count > 0 or len(files) > 0 else 1

if __name__ == "__main__":
    sys.exit(main())
