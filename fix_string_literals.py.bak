
#!/usr/bin/env python3
"""
String Literal Fixer

This script fixes malformed string literals in Python files, including:
- Unclosed quotes
- Mismatched quotes
- Extra quotes
- Triple-quoted strings with improper termination
"""

import logging
import re
import os
import sys
from typing import List, Dict, Tuple

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

def fix_string_literals(files: List[str] = None) -> Dict[str, bool]:
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
            logger.info(f"Checking file: {filename}")
            with open(filename, 'r', encoding='utf-8') as file:
                content = file.read()
            
            # Fix common string literal issues
            fixes = [
                # Regular string fixes
                (r'""([^"]*)"', r'"\1"'),  # Fix doubled quotes at start
                (r'"([^"]*)""\s', r'"\1" '),  # Fix doubled quotes at end
                (r'"([^"]*)["\']([^"\']*)["\']([^"]*)"', r'"\1\2\3"'),  # Fix mixed quotes
                
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
                    # Check for opening triple quotes
                    if '"""' in line and not in_triple_quote:
                        # Count quotes to ensure we're dealing with triple quotes
                        quote_count = line.count('"""')
                        if quote_count % 2 == 1:  # Odd number means unclosed
                            in_triple_quote = True
                            quote_start_line = i
                    
                    # Check for closing
                    elif '"""' in line and in_triple_quote:
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
            results[filename] = False
    
    return results

def count_quotes(content: str) -> Dict[str, int]:
    """Count different types of quotes in the content."""
    return {
        'single': content.count("'"),
        'double': content.count('"'),
        'triple_double': content.count('"""'),
        'triple_single': content.count("'''"),
    }

def main():
    """Main function to run the script."""
    logger.info("Starting string literal fix script...")
    
    # Get files from command line args or use default
    files = sys.argv[1:] if len(sys.argv) > 1 else None
    
    # Fix string literals
    results = fix_string_literals(files)
    
    # Count successes
    successes = sum(1 for result in results.values() if result)
    logger.info(f"Fixed {successes} out of {len(results)} files")
    
    # Return success if we fixed any file or all files were already good
    return 0 if successes > 0 or len(results) > 0 else 1

if __name__ == "__main__":
    sys.exit(main())
