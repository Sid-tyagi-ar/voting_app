import re
import requests

# URL to fetch disposable domains list
DISPOSABLE_DOMAINS_URL = "https://gist.githubusercontent.com/your-username/your-gist-id/raw/disposable_domains.txt"

def load_disposable_domains():
    """Load the list of disposable email domains."""
    try:
        response = requests.get(DISPOSABLE_DOMAINS_URL)
        response.raise_for_status()
        return set(response.text.splitlines())
    except Exception as e:
        print(f"Failed to load disposable domains: {e}")
        return set()

def is_valid_email(email):
    """Check if an email is valid and not from a disposable domain."""
    try:
        # Regex validation
        if not re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", email):
            print(f"Regex validation failed for {email}")
            return False
            
        # Extract domain
        domain = email.split('@')[-1].lower()
        
        # Check disposable domains
        disposable_domains = load_disposable_domains()
        if domain in disposable_domains:
            print(f"Disposable domain detected: {domain}")
            return False
            
        return True
    except Exception as e:
        print(f"Unexpected error during email validation: {e}")
        return False
