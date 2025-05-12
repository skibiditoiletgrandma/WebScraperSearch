import os

def check_env_vars():
    """Check environment variables related to the database connection"""
    print("Current environment variables:")
    
    variables = [
        'DATABASE_URL', 
        'PGHOST', 
        'PGPORT', 
        'PGUSER', 
        'PGPASSWORD', 
        'PGDATABASE'
    ]
    
    for var in variables:
        value = os.environ.get(var)
        if var == 'DATABASE_URL' and value:
            # Mask sensitive parts of the URL
            masked_url = value.split('@')[0].split(':')[0] + ":*****@*****"
            print(f"{var}: {masked_url}")
        elif var == 'PGPASSWORD' and value:
            print(f"{var}: *****")
        else:
            print(f"{var}: {value if value else 'Not set'}")

if __name__ == '__main__':
    check_env_vars()