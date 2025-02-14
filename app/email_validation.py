import re
import requests
import dns.resolver

def load_disposable_domains():
    url = "https://gist.githubusercontent.com/your-username/your-gist-id/raw/disposable_domains.txt"
    try:
        response = requests.get(url)
        response.raise_for_status()
        return set(response.text.splitlines())
    except Exception as e:
        return set()

def is_valid_email(email):
    try:
        if not re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", email):
            return False
        domain = email.split('@')[-1]
        disposable_domains = load_disposable_domains()
        if domain in disposable_domains:
            return False
        return is_valid_domain(domain)
    except Exception as e:
        return False
