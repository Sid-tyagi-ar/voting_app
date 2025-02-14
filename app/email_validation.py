import re

# Allowed institutional domains
ALLOWED_DOMAINS = {"students.iitmandi.ac.in"}

def is_valid_email(email):
    """Check if an email is from an allowed institutional domain."""
    try:
        # Regex validation
        if not re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", email):
            print(f"Regex validation failed for {email}")
            return False
            
        # Extract domain
        domain = email.split('@')[-1].lower()
        
        # Allow only institutional emails
        if domain in ALLOWED_DOMAINS:
            return True
            
        return False
    except Exception as e:
        print(f"Unexpected error during email validation: {e}")
        return False
