import re

def clean_text(text: str) -> str:
    if not text:
        return ""
    
    # Remove null bytes and non-printable characters
    cleaned = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', text)
    
    # Normalize whitespace
    cleaned = re.sub(r'\s+', ' ', cleaned)
    
    # Remove duplicate lines roughly (preserve some structure)
    lines = cleaned.split('. ')
    seen = set()
    unique_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped not in seen:
            seen.add(stripped)
            unique_lines.append(stripped)
            
    return '. '.join(unique_lines).strip()