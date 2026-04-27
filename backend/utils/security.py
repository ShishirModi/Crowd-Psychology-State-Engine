import re

def scrub_sensitive_data(text):
    """
    Removes sensitive information like API keys from text.
    Targeting standard URL parameters: key=..., api_key=..., apiKey=...
    """
    if not isinstance(text, str):
        text = str(text)
        
    # Regex to catch key=VALUE pairs in URLs or strings (e.g. key=12345)
    url_pattern = r'(key|api_?key|apiKey|appid)\s*=\s*([^\s&]+)'
    text = re.sub(url_pattern, r'\1=REDACTED', text, flags=re.IGNORECASE)
    
    # Regex for JSON style "key": "value"
    json_pattern = r'("key"|"api_?key"|"apiKey"|"appid")\s*:\s*"([^"]+)"'
    text = re.sub(json_pattern, r'\1: "REDACTED"', text, flags=re.IGNORECASE)
    
    return text
