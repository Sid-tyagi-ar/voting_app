import re
import requests
import dns.resolver

DISPOSABLE_DOMAINS_URL = "https://gist.githubusercontent.com/your-username/your-gist-id/raw/disposable_domains.txt"

def load_disposable_domains():
    try:
        response = requests.get(DISPOSABLE_DOMAINS_URL)
        response.raise_for_status()
        return set(response.text.splitlines())
    except Exception as e:
        print(f"Failed to load disposable domains: {e}")
        return set()

def is_valid_domain(domain):
    try:
        # Check MX records for the domain
        mx_records = dns.resolver.resolve(domain, 'MX')
        return bool(mx_records)  # True if MX records exist
    except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, 
            dns.resolver.NoNameservers, dns.resolver.Timeout) as e:
        print(f"Domain validation failed for {domain}: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error during domain validation: {e}")
        return False

def is_valid_email(email):
    try:
        # Regex validation
        if not re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", email):
            print(f"Regex validation failed for {email}")
            return False
            
        # Extract domain
        domain = email.split('@')[-1]
        
        # Check disposable domains
        disposable_domains = load_disposable_domains()
        if domain in disposable_domains:
            print(f"Disposable domain detected: {domain}")
            return False
            
        # Check MX records
        if not is_valid_domain(domain):
            print(f"MX record validation failed for {domain}")
            return False
            
        return True
    except Exception as e:
        print(f"Unexpected error during email validation: {e}")
        return False
