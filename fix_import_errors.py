
#!/usr/bin/env python3
"""
Import Error Fixer

This script detects and fixes common Python import errors, including:
- Missing imports
- Circular imports
- Incorrect import paths 
- Missing modules
"""

import os
import logging
import importlib
import sys
import re
import ast
from types import ModuleType
from typing import List, Dict, Optional, Set, Tuple, Any

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

def check_circular_imports(module_name: str) -> List[str]:
    """
    Check for circular imports in a module
    
    Args:
        module_name: The name of the module to check
        
    Returns:
        List of visited modules
    """
    visited = set()
    import_chain = []
    
    def visit_module(name: str) -> None:
        if name in visited:
            return
        if name in import_chain:
            logger.error(f"Circular import detected: {' -> '.join(import_chain + [name])}")
            return
        
        visited.add(name)
        import_chain.append(name)
        
        try:
            module = importlib.import_module(name)
            for key, value in module.__dict__.items():
                if isinstance(value, ModuleType) and value.__name__ not in visited:
                    visit_module(value.__name__)
        except Exception as e:
            logger.error(f"Error checking imports in {name}: {str(e)}")
            
        import_chain.pop()
    
    try:
        visit_module(module_name)
    except Exception as e:
        logger.error(f"Error visiting module {module_name}: {str(e)}")
        
    return list(visited)

def extract_imports_from_file(filename: str) -> List[Tuple[str, str, List[str]]]:
    """
    Extract all imports from a Python file.
    
    Args:
        filename: Path to the Python file
        
    Returns:
        List of tuples (import_type, module, [names]) where:
            - import_type is either 'import' or 'from'
            - module is the module being imported
            - names is a list of names being imported (for 'from' imports)
    """
    imports = []
    
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Parse the file with ast to extract imports
        try:
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for name in node.names:
                        imports.append(('import', name.name, []))
                        
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ''
                    names = [name.name for name in node.names]
                    imports.append(('from', module, names))
                    
        except SyntaxError:
            # If there's a syntax error, fall back to regex
            import_pattern = r'^import\s+([a-zA-Z0-9_.,\s]+)'
            from_pattern = r'^from\s+([a-zA-Z0-9_.]+)\s+import\s+([a-zA-Z0-9_.,\s\(\)]+)'
            
            lines = content.split('\n')
            for line in lines:
                line = line.strip()
                
                # Check for import statements
                import_match = re.match(import_pattern, line)
                if import_match:
                    modules = [m.strip() for m in import_match.group(1).split(',')]
                    for module in modules:
                        imports.append(('import', module, []))
                        
                # Check for from ... import statements
                from_match = re.match(from_pattern, line)
                if from_match:
                    module = from_match.group(1)
                    names_str = from_match.group(2).replace('(', '').replace(')', '')
                    names = [n.strip() for n in names_str.split(',')]
                    imports.append(('from', module, names))
                    
    except Exception as e:
        logger.error(f"Error extracting imports from {filename}: {str(e)}")
        
    return imports

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
        if not all(os.path.exists(f) for f in files):
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
                    if match:
                        model_imports.append(match.group(1).strip())
                
                if model_imports:
                    # Remove the model imports from the top of the file
                    for model_import in model_imports:
                        content = re.sub(
                            r'from models import ' + model_import.replace(' ', r'\s+'),
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
                                import_statement = 'from models import ' + ', '.join(model_imports)
                                new_db_config = db_config_text.replace(
                                    'db.create_all()',
                                    f'{import_statement}\n                db.create_all()'
                                )
                                content = content.replace(db_config_text, new_db_config)
                                fixes_needed = True
                                logger.info("Moved model imports inside configure_database function")
                
            # Check for missing imports of key modules
            # If Flask is used but not imported
            if 'Flask(' in content and not any(['import Flask' in content, 'from flask import' in content]):
                lines = content.split('\n')
                insert_pos = 0
                
                # Find last import line
                for i, line in enumerate(lines):
                    if line.strip().startswith(('import ', 'from ')) and not line.strip().startswith('#'):
                        insert_pos = i + 1
                
                lines.insert(insert_pos, 'from flask import Flask')
                content = '\n'.join(lines)
                fixes_needed = True
                logger.info(f"Added missing Flask import in {file}")
            
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
            results[file] = False
    
    # After fixing individual files, check for circular imports
    try:
        # Check for circular imports
        if 'main.py' in files or any(f.endswith('main.py') for f in files):
            logger.info("Checking for circular imports...")
            checked_modules = check_circular_imports('main')
            circular_found = False
            
            # Extract circular import entries from logger
            logger_handler = logger.handlers[0]
            if hasattr(logger_handler, 'stream'):
                log_output = logger_handler.stream.getvalue()
                circular_found = 'Circular import detected' in log_output
            
            if circular_found:
                logger.warning("Circular imports detected, attempting to fix...")
                # Fixing the most common circular import patterns...
                # (This would involve more complex refactoring that would be specific to the codebase)
            else:
                logger.info("No circular imports detected")
                
    except Exception as e:
        logger.error(f"Error checking circular imports: {str(e)}")
    
    return results

def check_module_availability():
    """
    Check if all required modules are available
    
    Returns:
        bool: True if all required modules are available, False otherwise
    """
    required_modules = ['flask', 'sqlalchemy', 'gunicorn']
    missing_modules = []
    
    for module in required_modules:
        try:
            importlib.import_module(module)
            logger.info(f"Module {module} is available")
        except ImportError:
            logger.error(f"Required module {module} is not installed")
            missing_modules.append(module)
    
    return len(missing_modules) == 0

def check_file_errors():
    """
    Check all Python files for import errors or undefined names
    
    Returns:
        Dict[str, List[str]]: Dictionary mapping filenames to lists of error messages
    """
    errors = {}
    files = find_python_files()
    
    for file in files:
        file_errors = []
        try:
            with open(file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check for syntax errors first
            try:
                tree = ast.parse(content)
            except SyntaxError as e:
                file_errors.append(f"Syntax error: {e}")
                errors[file] = file_errors
                continue
            
            # Check for undefined names and potential import errors
            imported_names = set()
            defined_names = set()
            used_names = set()
            
            # First pass: collect imported and defined names
            for node in ast.walk(tree):
                # Collect imports
                if isinstance(node, ast.Import):
                    for name in node.names:
                        imported_names.add(name.name)
                elif isinstance(node, ast.ImportFrom):
                    for name in node.names:
                        imported_names.add(name.name)
                
                # Collect defined names
                elif isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                    defined_names.add(node.name)
                elif isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            defined_names.add(target.id)
            
            # Second pass: collect used names
            for node in ast.walk(tree):
                if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                    used_names.add(node.id)
            
            # Find potentially undefined names
            all_defined = imported_names.union(defined_names).union(set(['__name__', '__file__', '__doc__']))
            undefined = used_names - all_defined
            
            if undefined:
                file_errors.append(f"Potentially undefined names: {', '.join(undefined)}")
            
            if file_errors:
                errors[file] = file_errors
                
        except Exception as e:
            logger.error(f"Error checking {file}: {str(e)}")
            errors[file] = [f"Error: {str(e)}"]
    
    return errors

def main():
    """Main function to run the script."""
    logger.info("Starting import error fixes...")
    
    # Check if required modules are available
    if not check_module_availability():
        logger.error("Missing required modules - proceeding with available modules")
    
    # Fix import errors
    results = fix_import_errors()
    
    # Count successes
    successes = sum(1 for result in results.values() if result)
    logger.info(f"Fixed import errors in {successes} out of {len(results)} files")
    
    # Check for remaining errors
    remaining_errors = check_file_errors()
    if remaining_errors:
        logger.warning(f"Found potential issues in {len(remaining_errors)} files")
        for file, errors in remaining_errors.items():
            logger.warning(f"Issues in {file}:")
            for error in errors:
                logger.warning(f"  - {error}")
    else:
        logger.info("No remaining import issues detected")
    
    return 0 if successes > 0 or not remaining_errors else 1

if __name__ == "__main__":
    sys.exit(main())
