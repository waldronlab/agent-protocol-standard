import os
import re
import subprocess

def parse_repository_url(url: str) -> str:
    url = url.strip()
    if not url:
        return None
    
    url = re.sub(r'/+$', '', url)
    url = re.sub(r'\.git$', '', url)
    url = re.sub(r'/+$', '', url)

    if re.match(r'^[^/]+@[^/:]+:', url):
        url = re.sub(r'^[^/]+@[^/:]+:', '', url)
    elif re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*://', url):
        url = re.sub(r'^[a-zA-Z][a-zA-Z0-9+.-]*://', '', url)
        url = re.sub(r'^[^/]*@', '', url)
        if not re.match(r'^[^/]+/', url):
            return None
        url = re.sub(r'^[^/]+/', '', url)
    else:
        return None
        
    url = re.sub(r'^/+', '', url)
    
    if re.match(r'^[^/]+/[^/]+$', url):
        return url
    return None

def detect_repository() -> str:
    from_env = os.environ.get("GITHUB_REPOSITORY")
    if from_env:
        return from_env
    
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"], 
            capture_output=True, text=True, check=True
        )
        url = result.stdout.strip()
        if url:
            return parse_repository_url(url)
    except Exception:
        pass
        
    return None

def detect_ref() -> str:
    if os.environ.get("GITHUB_EVENT_NAME") == "pull_request":
        base_ref = os.environ.get("GITHUB_BASE_REF")
        return base_ref if base_ref else "main"
    
    from_env = os.environ.get("GITHUB_REF_NAME")
    return from_env if from_env else "main"
