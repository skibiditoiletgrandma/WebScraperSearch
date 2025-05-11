#!/usr/bin/env python3
"""
Comprehensive Fix Script

This script handles multiple types of syntax and import errors:
1. String literal errors (misquoted strings, unclosed quotes)
2. Docstring errors (malformed triple quotes)
3. Import errors (circular imports, missing imports)
4. General syntax errors

Run this script to automatically detect and fix common issues.
"""

import os
import sys
import logging
import re
import importlib
import traceback
from typing import List, Dict, Optional, Tuple

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

def fix_string_literals(files: Optional[List[str]] = None) -> Dict[str, bool]:
    """
    Fix any malformed string literals in specified Python files.
    
    Args:
        files: List of files to process. If None, checks all Python files in current directory.
        
    Returns:
        Dict mapping filenames to whether they were fixed
    """
    if files is None:
        files = DEFAULT_FILES
        # Check if files exist, otherwise find all Python files
        if not all(os.path.exists(f) for f in DEFAULT_FILES):
            logger.info("Not all default files exist, searching for Python files...")
            files = find_python_files()
    
    results = {}
    
    for filename in files:
        if not os.path.exists(filename):
            logger.warning(f"File not found: {filename}")
            results[filename] = False
            continue
            
        try:
            logger.info(f"Checking string literals in file: {filename}")
            with open(filename, 'r', encoding='utf-8') as file:
                content = file.read()
            
            # Fix common string literal issues
            fixes = [
                # Regular string fixes
                (r'""([^"]*)"', r'"\1"'),  # Fix doubled quotes at start
                (r'"([^"]*)""\s', r'"\1" '),  # Fix doubled quotes at end
                (r'"([^"]*)["\']([^"\']*)["\']([^"]*)"', r'"\1\2\3"'),  # Fix mixed quotes
                (r'f""{5,}([^"]*)(\{[^}]*\})([^"]*)"', r'f"\1\2\3"'),  # Fix f-strings with multiple quotes
                
                # Triple-quoted string fixes - most common docstring issues
                (r'"{6,}([^"]*)"{6,}', r'"""\1"""'),  # Fix multiple consecutive triple quotes
                (r'"{6,}([^"]*)"{3}', r'"""\1"""'),  # Fix malformed opening/closing
                (r'"{3}([^"]*)"{6,}', r'"""\1"""'),  # Fix malformed opening/closing
                (r'"{3}([^"]*)""{1,2}([^"]*)""{0,2}', r'"""\1\2"""'),  # Fix broken triple quotes
                (r'"{3}([^"]*)"([^"]*)"{3}', r'"""\1\2"""'),  # Fix quotes inside triple quotes
                (r'"{3}([^"]*)"([^"]*)"{2}', r'"""\1\2"""'),  # Fix incomplete closing triple quotes
                (r'"{2}([^"]*)"([^"]*)"{3}', r'"""\1\2"""'),  # Fix incomplete opening triple quotes
                (r'"{2}([^"]*)"{4}', r'"""\1"""'),  # Another pattern of malformed triple quotes
                
                # Special case for docstrings with double quotes at beginning
                (r'""""""([^"]*)"""', r'"""\1"""'),  # Fix doubled triple quotes at start
                (r'"""([^"]*)""""""', r'"""\1"""'),  # Fix doubled triple quotes at end
                
                # Fix unclosed docstrings that should end before certain patterns
                (r'""([^"]*)"(\s*def|\s*class|\s*@|\s*#|\s*if|\s*else|\s*elif|\s*try|\s*except|\s*finally|\s*with|\s*return|\s*pass|\s*[a-zA-Z_][a-zA-Z0-9_]*\s*=)', 
                 r'"""\1"""\2'),
                
                # Fix malformed triple quotes in multiline docstrings
                (r'"{3}([^"]*)\n([^"]*)"([^"]*)""{0,2}', r'"""\1\n\2\3"""'),
                
                # Fix specific malformed patterns seen in the error
                (r'""([^"]*)"\s*Args:', r'"""\1\n    Args:'),
                (r'Args:([^"]*)"""""""', r'Args:\1"""'),
                
                # Fix missing double quotes in f-strings
                (r'f"""""([^"]*)(\{[^}]*\})([^"]*)"', r'f"\1\2\3"'),
                (r'f"""([^"]*)(\{[^}]*\})([^"]*)"', r'f"""\1\2\3"""'),
                
                # Handle unterminated f-strings
                (r'f"([^"]*)', r'f"\1"'),  # Close unterminated f-string
                (r'f"""([^"]*)$', r'f"""\1"""'),  # Close unterminated triple-quoted f-string
            ]
            
            fixed_content = content
            for pattern, replacement in fixes:
                fixed_content = re.sub(pattern, replacement, fixed_content)
            
            # Look for incomplete triple quotes at end of docstrings
            # This is a common issue with docstrings followed by function/class code
            def fix_incomplete_docstrings(text):
                lines = text.split('\n')
                in_triple_quote = False
                quote_start_line = -1
                
                for i, line in enumerate(lines):
                    # Count the number of triple quotes in this line
                    triple_quotes = line.count('"""')
                    
                    # If we're not in a docstring and find an odd number of triple quotes,
                    # we're starting a docstring
                    if not in_triple_quote and triple_quotes % 2 == 1:
                        in_triple_quote = True
                        quote_start_line = i
                    
                    # If we're in a docstring and find an odd number of triple quotes,
                    # we're ending a docstring
                    elif in_triple_quote and triple_quotes % 2 == 1:
                        in_triple_quote = False
                    
                    # If we're in a docstring and at a line that looks like it should end the docstring
                    elif in_triple_quote and i > quote_start_line and re.match(r'^\s*(def|class|@|if|else|elif|try|except|finally|with|return|pass|[a-zA-Z_][a-zA-Z0-9_]*\s*=)', line):
                        # Insert closing triple quotes at the end of previous line
                        lines[i-1] = lines[i-1] + '"""'
                        in_triple_quote = False
                
                # If we reach the end of file with an unclosed triple quote, close it
                if in_triple_quote and quote_start_line >= 0:
                    lines[-1] = lines[-1] + '"""'
                    
                return '\n'.join(lines)
            
            # Apply the docstring fixes
            fixed_content = fix_incomplete_docstrings(fixed_content)
            
            # Additional fix for f-strings with excessive quotes
            fixed_content = re.sub(r'f""{2,}([^"]*)(\{[^}]*\})([^"]*)"', r'f"\1\2\3"', fixed_content)
            
            if fixed_content != content:
                with open(filename, 'w', encoding='utf-8') as file:
                    file.write(fixed_content)
                logger.info(f"Fixed malformed string literals in {filename}")
                results[filename] = True
            else:
                logger.info(f"No string literal issues found in {filename}")
                results[filename] = False
                
        except Exception as e:
            logger.error(f"Error fixing string literals in {filename}: {str(e)}")
            logger.debug(traceback.format_exc())
            results[filename] = False
    
    return results

def fix_import_errors(files: Optional[List[str]] = None) -> Dict[str, bool]:
    """
    Fix common import errors in the application
    
    Args:
        files: List of files to check. If None, use default files.
        
    Returns:
        Dict mapping filenames to whether they were fixed
    """
    if files is None:
        files = DEFAULT_FILES
        # Check if files exist, otherwise find all Python files
        if not all(os.path.exists(f) for f in DEFAULT_FILES):
            logger.info("Not all default files exist, searching for Python files...")
            files = find_python_files()
    
    results = {}
    
    for file in files:
        if not os.path.exists(file):
            logger.warning(f"File not found: {file}")
            results[file] = False
            continue
                
        try:
            logger.info(f"Checking imports in {file}")
            with open(file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Fix common import issues
            fixes_needed = False
            
            # Check for app imports in main.py
            if file == 'main.py':
                # If importing from app but missing important imports
                if 'from app import app' in content and not any([
                    'from app import app, db' in content,
                    'from app import app, db, configure_database' in content
                ]):
                    new_content = content.replace(
                        'from app import app', 
                        'from app import app, db, configure_database'
                    )
                    if new_content != content:
                        content = new_content
                        fixes_needed = True
                        logger.info("Fixed missing imports from app in main.py")
                
                # If app.py exists but isn't imported at all
                elif os.path.exists('app.py') and not any([
                    'from app import' in content,
                    'import app' in content
                ]):
                    # Add import at the beginning of the file, after any module docstring
                    lines = content.split('\n')
                    import_line = 'from app import app, db, configure_database'
                    
                    # Find the right position to add the import
                    # (after module docstring or at the top)
                    insert_pos = 0
                    in_docstring = False
                    triple_quotes = 0
                    
                    for i, line in enumerate(lines):
                        if '"""' in line or "'''" in line:
                            triple_quotes += line.count('"""') + line.count("'''")
                            if triple_quotes % 2 == 1:  # Opening quote
                                in_docstring = True
                            else:  # Closing quote
                                in_docstring = False
                                insert_pos = i + 1
                        
                        # If we've left the docstring and found the first import or code line,
                        # insert before that
                        if not in_docstring and i > insert_pos and line.strip() and not line.startswith('#'):
                            insert_pos = i
                            break
                    
                    # Insert the import
                    lines.insert(insert_pos, import_line)
                    content = '\n'.join(lines)
                    fixes_needed = True
                    logger.info("Added app import to main.py")
            
            # Fix circular imports between app.py and models.py by moving model imports inside functions
            if file == 'app.py' and 'from models import' in content:
                # Look for imports of models at the module level that should be moved inside functions
                model_import_pattern = r'^from models import ([a-zA-Z0-9_, ]+)'
                
                # Find model imports
                model_imports = []
                for line in content.split('\n'):
                    match = re.match(model_import_pattern, line.strip())
                    if match and not line.strip().startswith('#'):
                        imports = match.group(1).strip()
                        # Don't include db and login_manager in model_imports
                        parts = [p.strip() for p in imports.split(',')]
                        model_parts = [p for p in parts if p not in ('db', 'login_manager')]
                        if model_parts:
                            model_imports.append(', '.join(model_parts))
                
                if model_imports:
                    # Remove the model imports from the top of the file
                    for model_import in model_imports:
                        content = re.sub(
                            r'from models import .*' + model_import.replace(' ', r'\s+') + '.*',
                            '',
                            content
                        )
                    
                    # Make sure db and login_manager are still imported
                    if not any([
                        'from models import db, login_manager' in content,
                        'from models import login_manager, db' in content
                    ]):
                        # Add the db and login_manager imports
                        if 'from models import' in content:
                            content = content.replace(
                                'from models import',
                                'from models import db, login_manager,'
                            )
                        else:
                            # Find where to insert the import
                            lines = content.split('\n')
                            last_import_line = 0
                            
                            for i, line in enumerate(lines):
                                if line.strip().startswith(('import ', 'from ')) and not line.strip().startswith('#'):
                                    last_import_line = i
                            
                            lines.insert(last_import_line + 1, 'from models import db, login_manager')
                            content = '\n'.join(lines)
                    
                    # Update the function where model imports are needed
                    if 'configure_database' in content:
                        # Find the configure_database function
                        db_config_pattern = r'def configure_database\([^)]*\):.*?db\.create_all\(\)'
                        db_config_match = re.search(db_config_pattern, content, re.DOTALL)
                        
                        if db_config_match:
                            db_config_text = db_config_match.group(0)
                            
                            # If the create_all() call is already there but without the model imports
                            if 'create_all' in db_config_text and not any(['from models import ' + m for m in model_imports]):
                                import_statement = 'from models import ' + ', '.join(m for m in model_imports if m.strip())
                                if import_statement != 'from models import ':  # Only add if there are actual imports
                                    new_db_config = db_config_text.replace(
                                        'db.create_all()',
                                        f'{import_statement}\n                db.create_all()'
                                    )
                                    content = content.replace(db_config_text, new_db_config)
                                    fixes_needed = True
                                    logger.info("Moved model imports inside configure_database function")
            
            # Save changes if needed
            if fixes_needed:
                with open(file, 'w', encoding='utf-8') as f:
                    f.write(content)
                logger.info(f"Fixed imports in {file}")
                results[file] = True
            else:
                logger.info(f"No import issues found in {file}")
                results[file] = False
                
        except Exception as e:
            logger.error(f"Error fixing imports in {file}: {str(e)}")
            logger.debug(traceback.format_exc())
            results[file] = False
    
    return results

def fix_syntax_errors(files: Optional[List[str]] = None) -> Dict[str, bool]:
    """
    Fix common syntax errors in Python files
    
    Args:
        files: List of files to process. If None, uses default files.
        
    Returns:
        Dict mapping filenames to whether they were fixed
    """
    if files is None:
        files = DEFAULT_FILES
        # Check if files exist, otherwise find all Python files
        if not all(os.path.exists(f) for f in DEFAULT_FILES):
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

            # Try to check for syntax errors
            try:
                compile(content, filename, 'exec')
                logger.info(f"File {filename} has valid syntax")
                results[filename] = False  # No fixes needed
                continue
            except SyntaxError as e:
                logger.warning(f"Syntax error in {filename}: {str(e)}")
                # Continue with fixes
            
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
                
                # Fix unterminated string literals
                (r'("[^"]*$)', r'\1"'),  # Close unterminated string
                (r"('[^']*$)", r"\1'"),  # Close unterminated string
                
                # Fix f-string issues
                (r'(f"[^"]*$)', r'\1"'),  # Close unterminated f-string
                
                # Fix triple quotes
                (r'("{3}[^"]*$)', r'\1"""'),  # Close unterminated triple quotes
                (r"('{3}[^']*$)", r"\1'''"),  # Close unterminated triple quotes
            ]

            fixed_content = content
            for pattern, replacement in fixes:
                fixed_content = re.sub(pattern, replacement, fixed_content)
            
            # Check if the fixes fixed the syntax error
            syntax_fixed = False
            try:
                compile(fixed_content, filename, 'exec')
                syntax_fixed = True
                logger.info(f"Successfully fixed syntax in {filename}")
            except SyntaxError as e:
                logger.warning(f"Could not fully fix syntax error in {filename}: {str(e)}")
                # We'll save it anyway in case we made partial progress
            
            if fixed_content != content:
                with open(filename, 'w', encoding='utf-8') as file:
                    file.write(fixed_content)
                logger.info(f"Applied syntax fixes to {filename}")
                results[filename] = True
            else:
                results[filename] = False  # No changes made
                
        except Exception as e:
            logger.error(f"Error fixing syntax in {filename}: {str(e)}")
            logger.debug(traceback.format_exc())
            results[filename] = False

    return results

def validate_files(files: Optional[List[str]] = None) -> Dict[str, Tuple[bool, str]]:
    """
    Validate that all files have correct syntax
    
    Args:
        files: List of files to validate. If None, uses default files.
        
    Returns:
        Dict mapping filenames to tuples of (is_valid, error_message)
    """
    if files is None:
        files = DEFAULT_FILES
        # Check if files exist, otherwise find all Python files
        if not all(os.path.exists(f) for f in DEFAULT_FILES):
            logger.info("Not all default files exist, searching for Python files...")
            files = find_python_files()
    
    results = {}
    
    for filename in files:
        if not os.path.exists(filename):
            logger.warning(f"File not found: {filename}")
            results[filename] = (False, "File not found")
            continue
            
        try:
            with open(filename, 'r', encoding='utf-8') as file:
                content = file.read()
            
            # Check syntax
            try:
                compile(content, filename, 'exec')
                results[filename] = (True, "Valid syntax")
            except SyntaxError as e:
                results[filename] = (False, f"Syntax error: {str(e)}")
                
        except Exception as e:
            results[filename] = (False, f"Error: {str(e)}")
    
    return results

def check_imports(files: Optional[List[str]] = None) -> Dict[str, Dict[str, List[str]]]:
    """
    Check imports in files to detect potential issues
    
    Args:
        files: List of files to check. If None, uses default files.
        
    Returns:
        Dict mapping filenames to import information
    """
    if files is None:
        files = DEFAULT_FILES
        # Check if files exist, otherwise find all Python files
        if not all(os.path.exists(f) for f in DEFAULT_FILES):
            logger.info("Not all default files exist, searching for Python files...")
            files = find_python_files()
    
    results = {}
    
    for filename in files:
        if not os.path.exists(filename):
            logger.warning(f"File not found: {filename}")
            continue
            
        try:
            logger.info(f"Checking imports in {filename}")
            with open(filename, 'r', encoding='utf-8') as file:
                content = file.read()
            
            # Extract imports using regex
            imports = []
            from_imports = []
            
            # Simple import statements
            import_pattern = r'^import\s+([a-zA-Z0-9_.,\s]+)'
            for line in content.split('\n'):
                line = line.strip()
                import_match = re.match(import_pattern, line)
                if import_match and not line.startswith('#'):
                    imports.extend([m.strip() for m in import_match.group(1).split(',')])
            
            # From import statements
            from_pattern = r'^from\s+([a-zA-Z0-9_.]+)\s+import\s+([a-zA-Z0-9_.,\s\(\)]+)'
            for line in content.split('\n'):
                line = line.strip()
                from_match = re.match(from_pattern, line)
                if from_match and not line.startswith('#'):
                    module = from_match.group(1)
                    names = [n.strip() for n in from_match.group(2).replace('(', '').replace(')', '').split(',')]
                    from_imports.append((module, names))
            
            results[filename] = {
                'imports': imports,
                'from_imports': from_imports
            }
                
        except Exception as e:
            logger.error(f"Error checking imports in {filename}: {str(e)}")
            logger.debug(traceback.format_exc())
    
    return results

def main():
    """Main function to run the script."""
    logger.info("Starting comprehensive fix script...")
    
    # Get files from command line args or use default
    files = sys.argv[1:] if len(sys.argv) > 1 else None
    
    # Run all the fix functions in sequence
    logger.info("Step 1: Fixing string literals...")
    string_results = fix_string_literals(files)
    
    logger.info("Step 2: Fixing syntax errors...")
    syntax_results = fix_syntax_errors(files)
    
    logger.info("Step 3: Fixing import errors...")
    import_results = fix_import_errors(files)
    
    # Combine results
    all_files = set(string_results.keys()) | set(syntax_results.keys()) | set(import_results.keys())
    fixed_files = []
    
    for filename in all_files:
        if string_results.get(filename, False) or syntax_results.get(filename, False) or import_results.get(filename, False):
            fixed_files.append(filename)
    
    # Validate all files
    logger.info("Final validation...")
    validation_results = validate_files(files)
    
    valid_files = [f for f, (valid, _) in validation_results.items() if valid]
    invalid_files = [(f, msg) for f, (valid, msg) in validation_results.items() if not valid]
    
    # Print summary
    logger.info("=== Summary ===")
    logger.info(f"Fixed {len(fixed_files)} files:")
    for f in fixed_files:
        logger.info(f"  - {f}")
    
    logger.info(f"\nValid syntax in {len(valid_files)} files")
    
    if invalid_files:
        logger.warning(f"\nStill have syntax issues in {len(invalid_files)} files:")
        for f, msg in invalid_files:
            logger.warning(f"  - {f}: {msg}")
    else:
        logger.info("\nAll files have valid syntax!")
    
    return 0 if not invalid_files else 1

if __name__ == "__main__":
    sys.exit(main())