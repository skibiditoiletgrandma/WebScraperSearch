
#!/usr/bin/env python3
import logging
import re

def fix_string_literals():
    """Fix any malformed string literals in routes.py"""
    try:
        with open('routes.py', 'r') as file:
            content = file.read()
        
        # Fix common string literal issues
        fixes = [
            (r'""([^"]*)"', r'"\1"'),  # Fix doubled quotes at start
            (r'"([^"]*)""\s', r'"\1" '),  # Fix doubled quotes at end
            (r'""time out"', r'"time out"'),  # Specific fix for time out string
        ]
        
        fixed_content = content
        for pattern, replacement in fixes:
            fixed_content = re.sub(pattern, replacement, fixed_content)
        
        if fixed_content != content:
            with open('routes.py', 'w') as file:
                file.write(fixed_content)
            print("Fixed malformed string literals in routes.py")
            return True
        
        print("No string literal issues found")
        return False
        
    except Exception as e:
        print(f"Error fixing string literals: {str(e)}")
        return False

if __name__ == "__main__":
    fix_string_literals()
