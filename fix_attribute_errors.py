"""
Attribute Error Fixer for 500 Server Errors

This script automatically fixes common 'object has no attribute' errors 
by synchronizing form fields with database models.

Specifically, it checks the models and forms to ensure that any fields 
defined in models are also present in the corresponding forms.
"""

import inspect
import logging
import re
import sys
from types import ModuleType
from typing import Dict, List, Set, Tuple, Type

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import the necessary modules
try:
    import models
    import forms
    from app import app, db
except ImportError as e:
    logger.error(f"Failed to import required modules: {e}")
    sys.exit(1)

def get_model_fields(model_class) -> Set[str]:
    """Extract column names from an SQLAlchemy model class"""
    fields = set()
    
    # Look for Column definitions in the class attributes
    for attr_name, attr_value in model_class.__dict__.items():
        # Skip private attributes, methods, and SQLAlchemy internals
        if (attr_name.startswith('_') or 
            callable(attr_value) or 
            isinstance(attr_value, property)):
            continue
        
        # If it's a Column, it's a field
        if hasattr(attr_value, 'type') and hasattr(attr_value, 'key'):
            fields.add(attr_name)
            
    # Check for declared columns in table definition
    if hasattr(model_class, '__table__') and hasattr(model_class.__table__, 'columns'):
        for column in model_class.__table__.columns:
            if column.name not in fields:
                fields.add(column.name)
                
    return fields

def get_form_fields(form_class) -> Set[str]:
    """Extract field names from a FlaskForm class"""
    fields = set()
    
    for attr_name, attr_value in form_class.__dict__.items():
        # Skip private attributes, methods, and FlaskForm internals
        if attr_name.startswith('_') or callable(attr_value):
            continue
        
        # Check if it's a form field (has a 'data' attribute)
        if hasattr(attr_value, 'data'):
            fields.add(attr_name)
            
    return fields

def find_missing_fields() -> Dict[str, Dict[str, List[str]]]:
    """Find fields that are missing from forms but present in models"""
    model_classes = {}
    form_classes = {}
    missing_fields = {}
    
    # Get all model classes from the models module
    for name, obj in inspect.getmembers(models):
        if inspect.isclass(obj) and hasattr(obj, '__tablename__'):
            model_classes[name] = obj
            
    # Get all form classes from the forms module
    for name, obj in inspect.getmembers(forms):
        if inspect.isclass(obj) and name.endswith('Form'):
            form_classes[name] = obj
    
    # Find corresponding model-form pairs
    for form_name, form_class in form_classes.items():
        # Remove "Form" suffix to get potential model name
        potential_model_name = form_name[:-4] if form_name.endswith('Form') else form_name
        
        # Check if there's a matching model
        if potential_model_name in model_classes:
            model_class = model_classes[potential_model_name]
            
            # Get fields for both
            model_fields = get_model_fields(model_class)
            form_fields = get_form_fields(form_class)
            
            # Find fields in the model but not in the form
            missing = [field for field in model_fields if field not in form_fields]
            
            if missing:
                missing_fields[form_name] = {
                    'model': potential_model_name,
                    'missing_fields': missing
                }
    
    return missing_fields

def fix_settings_form():
    """Fix the specific 'SettingsForm has no attribute search_pages_limit' error"""
    try:
        with open('forms.py', 'r') as file:
            content = file.read()
            
        # Check if search_pages_limit is already in the SettingsForm
        if 'search_pages_limit' in content and 'class SettingsForm' in content:
            pattern = r'class\s+SettingsForm.*?search_pages_limit'
            if re.search(pattern, content, re.DOTALL):
                logger.info("search_pages_limit already exists in SettingsForm, no fix needed")
                return True
        
        # Add the missing field to the SettingsForm
        pattern = r'(class\s+SettingsForm.*?"""Form for user settings""".*?# General settings\s*\n)'
        replacement = r'\1    search_pages_limit = IntegerField(\'Google Search Pages Limit\', validators=[\n        DataRequired(),\n        NumberRange(min=1, max=10, message=\'Please select a value between 1 and 10 pages.\')\n    ], description=\'Number of Google search results pages to fetch per search (1-10)\')\n\n'
        
        new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)
        
        if new_content != content:
            with open('forms.py', 'w') as file:
                file.write(new_content)
            logger.info("Added search_pages_limit to SettingsForm")
            return True
        else:
            logger.warning("Failed to locate insertion point for search_pages_limit in SettingsForm")
            return False
            
    except Exception as e:
        logger.error(f"Error fixing SettingsForm: {e}")
        return False

def fix_attribute_errors_in_templates():
    """Find and fix common attribute errors in template files"""
    try:
        import os
        template_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
        
        if not os.path.exists(template_dir):
            logger.warning(f"Template directory not found: {template_dir}")
            return False
            
        fixes_applied = False
        
        # Check each template file
        for filename in os.listdir(template_dir):
            if not filename.endswith('.html'):
                continue
                
            filepath = os.path.join(template_dir, filename)
            try:
                with open(filepath, 'r') as file:
                    content = file.read()
                
                # Look for common error patterns like accessing non-existent attributes
                # Example: form.search_pages_limit when it doesn't exist in the form
                potential_errors = re.findall(r'form\.([\w_]+)', content)
                
                for form_class_name in ['SettingsForm', 'LoginForm', 'RegistrationForm', 'CitationForm']:
                    if form_class_name.lower() in filename.lower():
                        form_class = getattr(forms, form_class_name)
                        form_fields = get_form_fields(form_class)
                        
                        for attr in potential_errors:
                            if attr not in form_fields and not attr.startswith('_') and attr != 'csrf_token' and attr != 'submit':
                                logger.warning(f"Potential error in {filename}: form.{attr} is referenced but does not exist in {form_class_name}")
            
            except Exception as e:
                logger.error(f"Error checking template {filename}: {e}")
                
        return fixes_applied
    
    except Exception as e:
        logger.error(f"Error fixing attribute errors in templates: {e}")
        return False
        
def auto_repair_routes_file():
    """Check and repair common attribute errors in routes.py"""
    try:
        import os
        routes_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'routes.py')
        
        if not os.path.exists(routes_file):
            logger.warning(f"Routes file not found: {routes_file}")
            return False
            
        with open(routes_file, 'r') as file:
            content = file.read()
            
        # Example: Look for form.search_pages_limit.data but search_pages_limit doesn't exist
        for form_class_name in ['SettingsForm', 'LoginForm', 'RegistrationForm', 'CitationForm']:
            form_class = getattr(forms, form_class_name)
            form_fields = get_form_fields(form_class)
            
            # Pattern for form.attribute.data patterns
            pattern = fr'{form_class_name.lower()}\.([\w_]+)\.data'
            matches = re.findall(pattern, content, re.IGNORECASE)
            
            for attr in matches:
                if attr not in form_fields and not attr.startswith('_') and attr != 'csrf_token' and attr != 'submit':
                    logger.warning(f"Potential error in routes.py: {form_class_name.lower()}.{attr}.data is referenced but does not exist in {form_class_name}")
        
        return False  # We're only checking, not fixing yet
        
    except Exception as e:
        logger.error(f"Error repairing routes file: {e}")
        return False

def main():
    """Main function to find and fix attribute errors"""
    logger.info("Starting attribute error fixer")
    
    # Try to fix the specific SettingsForm issue
    settings_form_fixed = fix_settings_form()
    
    # Try to find any other missing fields
    fixed_additional = False
    try:
        with app.app_context():
            missing_fields = find_missing_fields()
            
            if missing_fields:
                logger.info(f"Found {len(missing_fields)} forms with missing fields:")
                for form_name, info in missing_fields.items():
                    logger.info(f"- {form_name} is missing fields from {info['model']}: {', '.join(info['missing_fields'])}")
                    # We could auto-fix these too if needed
            else:
                logger.info("No missing fields found in any form classes.")
                
            # Check templates and routes for potential errors
            fix_attribute_errors_in_templates()
            auto_repair_routes_file()
            
    except Exception as e:
        logger.error(f"Error finding missing fields: {e}")
    
    if settings_form_fixed or fixed_additional:
        logger.info("Attribute error fixes applied successfully.")
        logger.info("Please restart the application for changes to take effect.")
    else:
        logger.info("No fixes were applied or needed.")
        
    # Print command for restarting the application
    logger.info("To restart the application, run: gunicorn --bind 0.0.0.0:5000 --reuse-port --reload main:app")

if __name__ == "__main__":
    main()