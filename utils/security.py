import re

def scrub_sensitive_data(text):
    """
    Removes sensitive information like API keys from text.
    Targeting standard URL parameters: key=..., api_key=..., apiKey=...
    """
    if not isinstance(text, str):
        text = str(text)
        
    # Regex to catch key=VALUE pairs in URLs or strings
    # Matches key/api_key/apiKey followed by optional whitespace, =, and non-whitespace characters
    pattern = r'(key|api_?key|apiKey)\s*=\s*([^\s&]+)'
    
    # Replace with key=REDACTED
    scrubbed = re.sub(pattern, r'\1=REDACTED', text, flags=re.IGNORECASE)
    return scrubbed
