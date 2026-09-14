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
    # Checked first, and deliberately not a GITHUB_* name. A caller that pins its checkout to a
    # branch has to be able to tell the generator which ref the index describes, or protocol_url
    # values name a revision the index was not built from. GITHUB_REF_NAME is runner-provided and
    # overriding it from a workflow is unsupported, so the override gets its own variable.
    explicit = os.environ.get("PROTOCOL_INDEX_REF")
    if explicit:
        return explicit

    if os.environ.get("GITHUB_EVENT_NAME") == "pull_request":
        base_ref = os.environ.get("GITHUB_BASE_REF")
        return base_ref if base_ref else "main"
    
    from_env = os.environ.get("GITHUB_REF_NAME")
    return from_env if from_env else "main"
