
#!/usr/bin/env python3
"""
Automatic Code Fixer

This script automatically scans Python files for common issues and fixes them:
- Syntax errors
- String literal errors
- Import errors
- Docstring issues
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

def fix_syntax_errors(content: str) -> Tuple[str, bool]:
    """Fix common syntax errors in Python code."""
    fixes = [
        # Missing colons
        (r'(if\s+[^:\n]+)(\s*\n)', r'\1:\2'),
        (r'(elif\s+[^:\n]+)(\s*\n)', r'\1:\2'),
        (r'(else\s*)(\n)', r'\1:\2'),
        (r'(for\s+[^:\n]+)(\s*\n)', r'\1:\2'),
        (r'(while\s+[^:\n]+)(\s*\n)', r'\1:\2'),
        (r'(def\s+[^:\n]+\))(\s*\n)', r'\1:\2'),
        (r'(class\s+[^:\n(]+)(\s*\n)', r'\1:\2'),
        
        # Fix list comprehensions
        (r'\[([^]\n]+)for', r'[ \1 for'),
        (r'for([^]\n]+)in', r'for \1 in'),
        (r'if([^]\n]+)\]', r'if \1 ]'),
        
        # Fix parentheses
        (r'(\w+)\s*\(\s*([^()]*?)\s*$', r'\1(\2)'),
    ]
    
    fixed = content
    for pattern, replacement in fixes:
        fixed = re.sub(pattern, replacement, fixed)
    
    return fixed, fixed != content

def fix_string_literals(content: str) -> Tuple[str, bool]:
    """Fix string literal issues."""
    fixes = [
        # Fix quotes
        (r'""([^"]*)"', r'"\1"'),
        (r'"([^"]*)""\s', r'"\1" '),
        (r'"([^"]*)["\']([^"\']*)["\']([^"]*)"', r'"\1\2\3"'),
        
        # Fix f-strings
        (r'f"([^"]*){([^}]*)}([^"]*)"', r'f"\1{\2}\3"'),
        (r'f"([^"]*){\s*([^}]*?)\s*}([^"]*)"', r'f"\1{\2}\3"'),
        
        # Fix docstrings
        (r'"{6,}([^"]*)"{6,}', r'"""\1"""'),
        (r'"{3}([^"]*)"([^"]*)"{3}', r'"""\1\2"""'),
    ]
    
    fixed = content
    for pattern, replacement in fixes:
        fixed = re.sub(pattern, replacement, fixed)
    
    return fixed, fixed != content

def fix_imports(content: str, filename: str) -> Tuple[str, bool]:
    """Fix common import issues."""
    imports = set()
    import_section = []
    code_section = []
    in_imports = True
    
    # Split imports from code
    for line in content.split('\n'):
        if line.strip().startswith(('import ', 'from ')):
            import_section.append(line)
            imports.add(line.strip())
        elif line.strip() and in_imports:
            in_imports = False
            code_section.append(line)
        else:
            code_section.append(line)
    
    # Sort and deduplicate imports
    sorted_imports = sorted(list(imports))
    
    # Recombine with proper spacing
    new_content = '\n'.join(sorted_imports)
    if sorted_imports and code_section:
        new_content += '\n\n'
    new_content += '\n'.join(code_section)
    
    return new_content, new_content != content

def validate_fixes(content: str, filename: str) -> bool:
    """Validate that the fixes didn't break the code."""
    try:
        ast.parse(content)
        return True
    except SyntaxError as e:
        logger.error(f"Validation failed for {filename}: {str(e)}")
        return False

def fix_file(filename: str) -> bool:
    """Fix all issues in a single file."""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        fixed = content
        
        # Apply fixes in sequence
        fixed, syntax_changed = fix_syntax_errors(fixed)
        fixed, literal_changed = fix_string_literals(fixed)
        fixed, import_changed = fix_imports(fixed, filename)
        
        # Validate the changes
        if fixed != original_content:
            if validate_fixes(fixed, filename):
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(fixed)
                logger.info(f"Fixed {filename}")
                if syntax_changed:
                    logger.info(f"  - Fixed syntax errors")
                if literal_changed:
                    logger.info(f"  - Fixed string literals")
                if import_changed:
                    logger.info(f"  - Fixed imports")
                return True
            else:
                logger.warning(f"Fixes for {filename} failed validation, skipping")
                return False
        else:
            logger.info(f"No issues found in {filename}")
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
    
    # Fix each file
    fixed_count = 0
    for file in files:
        if fix_file(file):
            fixed_count += 1
            
    logger.info(f"Fixed {fixed_count} out of {len(files)} files")
    return 0 if fixed_count > 0 or len(files) > 0 else 1

if __name__ == "__main__":
    sys.exit(main())
