
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

def fix_import_statements(content: str, filename: str) -> Tuple[str, bool]:
    """Fix common import statement issues."""
    fixes = [
        # Fix from imports missing 'import' keyword
        (r'from\s+([^\s]+)\s+([^\s]+)', r'from \1 import \2'),
        
        # Fix multiple imports on same line
        (r'import\s+([^,\s]+),\s*([^\s]+)', r'import \1\nimport \2'),
        
        # Fix relative imports
        (r'from\s+\.+([^\s]+)\s+import', r'from \1 import'),
        
        # Fix common typos in import statements
        (r'impotr\s+', 'import '),
        (r'from\s+([^\s]+)\s+improt\s+', r'from \1 import '),
    ]
    
    fixed = content
    for pattern, replacement in fixes:
        fixed = re.sub(pattern, replacement, fixed)
    
    # Special handling for routes.py
    if filename.endswith('routes.py'):
        if 'from app import app' in fixed and 'from app import db' not in fixed:
            fixed = fixed.replace('from app import app', 'from app import app, db')
    
    return fixed, fixed != content

def fix_syntax_errors(content: str) -> Tuple[str, bool]:
    """Fix common syntax errors in Python code."""
    fixes = [
        # Fix list comprehension syntax
        (r'\[\s*for\s+', '[ item for '),
        (r'\[\s*([^\]]+?)\s+for\s+([^\]]+?)\s+in\s+([^\]]+?)\s*\]', r'[\1 for \2 in \3]'),
        
        # Fix dictionary comprehension syntax
        (r'\{\s*([^}]+?):\s*([^}]+?)\s+for\s+([^}]+?)\s+in\s+([^}]+?)\s*\}', r'{\1: \2 for \3 in \4}'),
        
        # Fix missing colons
        (r'(if|elif|else|for|while|def|class|try|except|finally)\s+([^:\n]+)(\s*\n)', r'\1 \2:\3'),
        
        # Fix missing parentheses
        (r'print\s+([^(].+)', r'print(\1)'),
        
        # Fix trailing commas in lists/dicts
        (r',\s*([}\]])', r'\1'),
        
        # Fix missing quotes in strings
        (r'=\s*([^"\'{\[\d][^,}\]\n]+)\s*[,}\]]', r'="\1",'),
    ]
    
    fixed = content
    for pattern, replacement in fixes:
        fixed = re.sub(pattern, replacement, fixed)
    
    return fixed, fixed != content

def fix_file(filename: str) -> bool:
    """Fix all issues in a single file."""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        fixed = content
        
        # Apply fixes in sequence
        fixed, import_changed = fix_import_statements(fixed, filename)
        fixed, syntax_changed = fix_syntax_errors(fixed)
        
        # Validate the changes
        if fixed != original_content:
            try:
                ast.parse(fixed)  # Validate syntax
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(fixed)
                logger.info(f"Fixed {filename}")
                if import_changed:
                    logger.info(f"  - Fixed import statements")
                if syntax_changed:
                    logger.info(f"  - Fixed syntax errors")
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

def main():
    """Main entry point."""
    logger.info("Starting automatic code fixes...")
    
    # Find all Python files
    files = find_python_files()
    if not files:
        logger.error("No Python files found")
        return 1
        
    logger.info(f"Found {len(files)} Python files")
    
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
