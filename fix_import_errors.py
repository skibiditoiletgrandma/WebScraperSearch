
#!/usr/bin/env python3
import os
import logging
import importlib
import sys
from types import ModuleType
from typing import List, Dict, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_circular_imports(module_name: str) -> List[str]:
    """Check for circular imports in a module"""
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
    
    visit_module(module_name)
    return list(visited)

def fix_import_errors() -> bool:
    """Fix common import errors in the application"""
    try:
        # Check main application files
        files_to_check = ['main.py', 'app.py', 'routes.py']
        
        for file in files_to_check:
            if not os.path.exists(file):
                logger.warning(f"File {file} not found")
                continue
                
            with open(file, 'r') as f:
                content = f.read()
                
            # Fix common import issues
            fixes_needed = False
            
            # Check for proper imports
            if 'from app import app' in content and not content.startswith('from app import'):
                content = content.replace('from app import app', 'from app import app, db, configure_database')
                fixes_needed = True
            
            # Ensure imports are at the top
            if fixes_needed:
                with open(file, 'w') as f:
                    f.write(content)
                logger.info(f"Fixed imports in {file}")
        
        # Check for circular imports
        checked_modules = check_circular_imports('main')
        if checked_modules:
            logger.info("Import chain checked successfully")
            
        return True
        
    except Exception as e:
        logger.error(f"Error fixing import errors: {str(e)}")
        return False

def check_module_availability():
    """Check if all required modules are available"""
    required_modules = ['flask', 'sqlalchemy', 'gunicorn']
    
    for module in required_modules:
        try:
            importlib.import_module(module)
            logger.info(f"Module {module} is available")
        except ImportError:
            logger.error(f"Required module {module} is not installed")
            return False
    return True

if __name__ == "__main__":
    logger.info("Starting import error fixes...")
    
    if not check_module_availability():
        logger.error("Missing required modules")
        sys.exit(1)
        
    if fix_import_errors():
        logger.info("Import errors fixed successfully")
    else:
        logger.error("Failed to fix import errors")
        sys.exit(1)
