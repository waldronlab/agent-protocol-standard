#!/usr/bin/env python3
import sys
import os
import yaml
from pathlib import Path
from datetime import UTC, datetime

# Make sure scripts directory is in path
sys.path.insert(0, str(Path(__file__).parent))
from repo_utils import detect_repository, detect_ref
from validate_protocol import extract_frontmatter

def main():
    args = sys.argv[1:]
    protocols_dir = args[0] if len(args) >= 1 and args[0] else "protocols"
    output_file = args[1] if len(args) >= 2 and args[1] else "PROTOCOLS.yaml"
    
    if not os.path.isdir(protocols_dir):
        sys.exit(f"No '{protocols_dir}' directory found. Pass the protocols directory as the first argument.")
        
    protocol_files = sorted(list(Path(protocols_dir).rglob("protocol.md")))
    if not protocol_files:
        sys.exit(f"No 'protocol.md' files found under '{protocols_dir}'.")
        
    repository_name = detect_repository()
    if not repository_name:
        sys.exit("Could not determine which repository these protocols belong to. Set GITHUB_REPOSITORY to 'owner/name', or run this script inside a git checkout whose 'origin' remote points at the repository hosting them.")
        
    repository_ref = detect_ref()
    
    protocols_list = []
    unreadable = []
    
    for file_path in protocol_files:
        try:
            frontmatter = extract_frontmatter(str(file_path))
        except Exception as e:
            print(f"  [ERROR] Failed to parse YAML frontmatter in {file_path}: {str(e)}")
            frontmatter = None
            
        if not isinstance(frontmatter, dict) or not frontmatter:
            unreadable.append(str(file_path))
            continue
            
        # Add protocol URL to the metadata
        frontmatter['protocol_url'] = f"https://raw.githubusercontent.com/{repository_name}/{repository_ref}/{file_path.as_posix()}"
        
        # Convert date to string if it's parsed as datetime.date
        if 'date' in frontmatter and hasattr(frontmatter['date'], 'isoformat'):
            frontmatter['date'] = frontmatter['date'].isoformat()
            
        if 'reviews' in frontmatter and isinstance(frontmatter['reviews'], list):
            for r in frontmatter['reviews']:
                if isinstance(r, dict) and 'date' in r and hasattr(r['date'], 'isoformat'):
                    r['date'] = r['date'].isoformat()
                    
        protocols_list.append(frontmatter)
        
    if unreadable:
        unreadable_str = ", ".join(unreadable)
        sys.exit(f"Could not read {len(unreadable)} protocol(s): {unreadable_str}. Refusing to write an index that omits them.")
        
    index = {
        'spec_version': '0.1.0',
        'repository': repository_name,
        'generated_at': datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        'protocols': protocols_list
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        yaml.dump(index, f, sort_keys=False, default_flow_style=False)
        
    print(f"Successfully generated {output_file} with {len(protocols_list)} protocols.")

if __name__ == '__main__':
    main()
