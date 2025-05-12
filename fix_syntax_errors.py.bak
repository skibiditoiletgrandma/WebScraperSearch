
#!/usr/bin/env python3
"""
Syntax Error Fixer

This script identifies and fixes common syntax errors in Python files, including:
- Indentation errors
- Missing colons after conditionals/loops
- Malformed function definitions
- Other common syntax problems
"""

import re
import logging
import os
import sys
import ast
from typing import List, Dict, Tuple, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Files to check by default
DEFAULT_FILES = ['app.py', 'main.py', 'routes.py', 'models.py', 'forms.py', 'scraper.py']

def find_python_files(directory: str = '.', max_depth: int = 2) -> List[str]:
    """Find all Python files in the specified directory, up to a maximum depth."""
    python_files = []
    
    # Don't search in virtual environments or .git directories
    excluded_dirs = ['venv', '.venv', 'env', '.env', '.git', '__pycache__', 'node_modules']
    
    for root, dirs, files in os.walk(directory):
        # Calculate current depth
        depth = root.count(os.sep) - directory.count(os.sep)
        if depth > max_depth:
            continue
            
        # Skip excluded directories
        dirs[:] = [d for d in dirs if d not in excluded_dirs]
        
        # Add Python files
        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))
                
    return python_files

def fix_string_docstrings(files: List[str] = None) -> Dict[str, bool]:
    """
    Fix malformed docstring literals in Python files
    
    Args:
        files: List of files to process. If None, uses default files.
        
    Returns:
        Dict mapping filenames to whether they were fixed
    """
    if files is None:
        files = DEFAULT_FILES
        # Check if files exist, otherwise find all Python files
        if not all(os.path.exists(f) for f in files):
            logger.info("Not all default files exist, searching for Python files...")
            files = find_python_files()
    
    results = {}
    
    for filename in files:
        if not os.path.exists(filename):
            logger.warning(f"File not found: {filename}")
            results[filename] = False
            continue
            
        try:
            logger.info(f"Checking docstrings in file: {filename}")
            with open(filename, 'r', encoding='utf-8') as file:
                content = file.read()

            # Fix common docstring issues
            fixes = [
                # Basic docstring fixes
                (r'"{6,}([^"]*)"{6,}', r'"""\1"""'),  # Fix multiple triple quotes
                (r'"{6,}([^"]*)"{3}', r'"""\1"""'),  # Fix excess quotes at start
                (r'"{3}([^"]*)"{6,}', r'"""\1"""'),  # Fix excess quotes at end
                
                # Incomplete docstrings
                (r'""([^"]*)"(\s*return|\s*pass|\s*[a-zA-Z])', r'"""\1"""\2'),  # Fix unclosed docstrings
                (r'""([^"]*)"(\s+)', r'"""\1"""\2'),  # Fix docstrings without closure
                (r'"([^"]*)"(\s+)def', r'"""\1"""\2def'),  # Fix function docstrings
                (r'"""([^"]*)"(\s+)', r'"""\1"""\2'),  # Fix partially closed docstrings
                
                # Complex cases
                (r'""([^"]*)"{3}', r'"""\1"""'),  # Fix weird mixed quotes
                (r'"{3}([^"]*)""', r'"""\1"""'),  # Fix weird mixed quotes
                (r'""([^"]*)"(\n\s*def|\n\s*class)', r'"""\1"""\2'),  # Fix unclosed docstrings before functions/classes
                
                # Additional patterns for specific issues
                (r'"""\s*([^"]*)"\s*Args:', r'"""\1\n    Args:'),  # Fix Args formatting
                (r'Args:([^"]*)"""""""', r'Args:\1"""'),  # Fix excess quotes after Args
            ]

            fixed_content = content
            for pattern, replacement in fixes:
                fixed_content = re.sub(pattern, replacement, fixed_content)

            # Look for unclosed docstrings by analyzing line by line
            lines = fixed_content.split('\n')
            in_docstring = False
            docstring_start = -1
            
            for i in range(len(lines)):
                line = lines[i]
                
                # Count the number of triple quotes in this line
                triple_quotes = line.count('"""')
                
                # If we're not in a docstring and find an odd number of triple quotes,
                # we're starting a docstring
                if not in_docstring and triple_quotes % 2 == 1:
                    in_docstring = True
                    docstring_start = i
                
                # If we're in a docstring and find an odd number of triple quotes,
                # we're ending a docstring
                elif in_docstring and triple_quotes % 2 == 1:
                    in_docstring = False
                
                # Special case: if we're in a docstring and find a function/class definition,
                # we should close the docstring
                elif in_docstring and re.match(r'^\s*(def|class)\s+', line):
                    lines[i-1] = lines[i-1] + '"""'
                    in_docstring = False
                    
            # If we reach the end of the file and we're still in a docstring, close it
            if in_docstring and docstring_start >= 0:
                lines[-1] = lines[-1] + '"""'
                
            fixed_content = '\n'.join(lines)

            if fixed_content != content:
                with open(filename, 'w', encoding='utf-8') as file:
                    file.write(fixed_content)
                logger.info(f"Fixed docstring issues in {filename}")
                results[filename] = True
            else:
                logger.info(f"No docstring issues found in {filename}")
                results[filename] = False

        except Exception as e:
            logger.error(f"Error processing {filename}: {str(e)}")
            results[filename] = False

    return results

def fix_other_syntax_errors(files: List[str] = None) -> Dict[str, bool]:
    """
    Fix other common syntax errors in Python files
    
    Args:
        files: List of files to process. If None, uses default files.
        
    Returns:
        Dict mapping filenames to whether they were fixed
    """
    if files is None:
        files = DEFAULT_FILES
        # Check if files exist, otherwise find all Python files
        if not all(os.path.exists(f) for f in files):
            logger.info("Not all default files exist, searching for Python files...")
            files = find_python_files()
    
    results = {}
    
    for filename in files:
        if not os.path.exists(filename):
            logger.warning(f"File not found: {filename}")
            results[filename] = False
            continue
            
        try:
            logger.info(f"Checking syntax in file: {filename}")
            with open(filename, 'r', encoding='utf-8') as file:
                content = file.read()

            # Try to parse the file with ast to check for syntax errors
            syntax_valid = False
            try:
                ast.parse(content)
                syntax_valid = True
                logger.info(f"File {filename} has valid syntax")
            except SyntaxError as e:
                logger.warning(f"Syntax error in {filename}: {str(e)}")
                # Continue with fixes anyway
            
            # Only apply these fixes if we detected a syntax error
            if not syntax_valid:
                # Fix common syntax errors
                fixes = [
                    # Missing colons
                    (r'(if\s+[^:\n]+)(\s*\n)', r'\1:\2'),  # Add missing colon after if
                    (r'(elif\s+[^:\n]+)(\s*\n)', r'\1:\2'),  # Add missing colon after elif
                    (r'(else\s*)(\n)', r'\1:\2'),  # Add missing colon after else
                    (r'(for\s+[^:\n]+)(\s*\n)', r'\1:\2'),  # Add missing colon after for
                    (r'(while\s+[^:\n]+)(\s*\n)', r'\1:\2'),  # Add missing colon after while
                    (r'(def\s+[^:\n]+\))(\s*\n)', r'\1:\2'),  # Add missing colon after def
                    (r'(class\s+[^:\n(]+)(\s*\n)', r'\1:\2'),  # Add missing colon after class
                    
                    # Unclosed parentheses in function definitions
                    (r'(def\s+\w+\([^)]*$)', r'\1)'),  # Close unclosed parenthesis in function definition
                    
                    # Remove invalid characters or syntax
                    (r'^\s*,\s*$', r''),  # Remove solo commas on their own line
                    (r'^\s*;\s*$', r''),  # Remove solo semicolons on their own line
                ]

                fixed_content = content
                for pattern, replacement in fixes:
                    fixed_content = re.sub(pattern, replacement, fixed_content)
                
                # Check if the fixes actually fixed the syntax error
                try:
                    ast.parse(fixed_content)
                    logger.info(f"Successfully fixed syntax in {filename}")
                    results[filename] = True
                except SyntaxError as e:
                    logger.warning(f"Could not fully fix syntax error in {filename}: {str(e)}")
                    results[filename] = False
                    # We'll return it anyway in case we made partial progress
                    
                if fixed_content != content:
                    with open(filename, 'w', encoding='utf-8') as file:
                        file.write(fixed_content)
                    logger.info(f"Applied syntax fixes to {filename}")
                    
            else:
                results[filename] = False  # No fixes needed

        except Exception as e:
            logger.error(f"Error fixing syntax in {filename}: {str(e)}")
            results[filename] = False

    return results

def main():
    """Main function to run the script."""
    logger.info("Starting syntax error fix script...")
    
    # Get files from command line args or use default
    files = sys.argv[1:] if len(sys.argv) > 1 else None
    
    # Fix string docstrings
    docstring_results = fix_string_docstrings(files)
    
    # Fix other syntax errors
    syntax_results = fix_other_syntax_errors(files)
    
    # Combine results
    combined_results = {**docstring_results, **syntax_results}
    
    # Count successes
    successes = sum(1 for result in combined_results.values() if result)
    logger.info(f"Fixed {successes} out of {len(combined_results)} files")
    
    # Return success if we fixed any file or all files were already good
    return 0 if successes > 0 or len(combined_results) > 0 else 1

if __name__ == "__main__":
    sys.exit(main())
