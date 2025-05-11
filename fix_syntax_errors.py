
#!/usr/bin/env python3
import re
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_string_docstrings():
    """Fix malformed docstring literals in Python files"""
    try:
        files_to_check = ['routes.py', 'main.py', 'app.py']
        
        for filename in files_to_check:
            try:
                with open(filename, 'r') as file:
                    content = file.read()

                # Fix common docstring issues
                fixes = [
                    (r'"{6,}([^"]*)"{6,}', r'"""\1"""'),  # Fix multiple triple quotes
                    (r'""([^"]*)"(\s*return|\s*pass|\s*[a-zA-Z])', r'"""\1"""\2'),  # Fix unclosed docstrings
                    (r'""([^"]*)"(\s+)', r'"""\1"""\2'),  # Fix docstrings without closure
                    (r'"([^"]*)"(\s+)def', r'"""\1"""\2def'),  # Fix function docstrings
                    (r'"""([^"]*)"(\s+)', r'"""\1"""\2'),  # Fix partially closed docstrings
                ]

                fixed_content = content
                for pattern, replacement in fixes:
                    fixed_content = re.sub(pattern, replacement, fixed_content)

                if fixed_content != content:
                    with open(filename, 'w') as file:
                        file.write(fixed_content)
                    logger.info(f"Fixed docstring issues in {filename}")

            except Exception as e:
                logger.error(f"Error processing {filename}: {str(e)}")

        return True

    except Exception as e:
        logger.error(f"Error fixing string literals: {str(e)}")
        return False

if __name__ == "__main__":
    fix_string_docstrings()
