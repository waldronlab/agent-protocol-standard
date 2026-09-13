#!/usr/bin/env python3
import sys
import os
import re
import yaml
from pathlib import Path
from datetime import datetime

# Make sure scripts directory is in path
sys.path.insert(0, str(Path(__file__).parent))
from models import ProtocolFrontmatter, check_renamed_fields, SEMVER_PATTERN, ORCID_PATTERN
from repo_utils import detect_repository

def strip_frontmatter_and_code(lines):
    keep = [True] * len(lines)
    in_fence = False
    fence = None
    fence_length = 0
    in_frontmatter = False
    
    for i, line in enumerate(lines):
        if not in_fence and i == 0 and re.match(r'^---[ \t]*$', line):
            in_frontmatter = True
            keep[i] = False
            continue
            
        if in_frontmatter:
            keep[i] = False
            if re.match(r'^(---|\.\.\.)[ \t]*$', line):
                in_frontmatter = False
            continue
            
        marker_match = re.match(r'^[ \t]{0,3}(`{3,}|~{3,})', line)
        if marker_match:
            run = marker_match.group(1).strip()
            token = run[0]
            run_length = len(run)
            suffix = line[marker_match.end():]
            
            if not in_fence:
                if token != '`' or '`' not in suffix:
                    in_fence = True
                    fence = token
                    fence_length = run_length
                    keep[i] = False
                    continue
            elif token == fence and run_length >= fence_length and re.match(r'^[ \t]*$', suffix):
                in_fence = False
                fence = None
                fence_length = 0
                keep[i] = False
                continue
                
        if in_fence:
            keep[i] = False
            
    return [line for k, line in zip(keep, lines) if k]

def strip_orcid_suffix(x):
    return re.sub(r'[ \t]*\(\[.*\]\(.*\)\)$', '', x).strip()

def is_valid_date(x):
    if not re.match(r'^[0-9]{4}-[0-9]{2}-[0-9]{2}$', x):
        return False
    try:
        datetime.strptime(x, "%Y-%m-%d")
        return True
    except ValueError:
        return False

def extract_frontmatter(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    match = re.match(r'^---[\r\n]+(.*?[\r\n]+)(?:---|\.\.\.)[\r\n]+', content, re.DOTALL)
    if not match:
        return None
        
    try:
        # Load yaml safely
        # We need to manually parse the date as string if PyYAML parses it as date directly
        # but PyYAML parsing to date is fine since pydantic handles it. However pydantic models need dicts.
        parsed = yaml.safe_load(match.group(1))
        return parsed
    except Exception as e:
        raise Exception(f"Failed to parse YAML frontmatter: {str(e)}")

def validate_history(file_path, frontmatter, frontmatter_reviews):
    errors = []
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = [line.rstrip('\n') for line in f]
        
    heading_idx = [i for i, line in enumerate(lines) if re.match(r'^##[ \t]+History & Reviews[ \t]*$', line)]
    if not heading_idx:
        print("  [ERROR] Missing required '## History & Reviews' section (see PROTOCOL_STANDARD.md).")
        return False
    if len(heading_idx) > 1:
        print("  [ERROR] Found multiple '## History & Reviews' headings; there must be exactly one.")
        return False
        
    section = lines[heading_idx[0]+1:]
    
    later_section = [i for i, line in enumerate(section) if re.match(r'^##[ \t]', line)]
    if later_section:
        errors.append(f"'## History & Reviews' must be the last section, but '{section[later_section[0]].strip()}' appears after it")
        
    version_idx = [i for i, line in enumerate(section) if re.match(r'^###[ \t]', line)]
    if not version_idx:
        print("  [ERROR] '## History & Reviews' has no '### Version X.Y.Z (YYYY-MM-DD)' entries.")
        return False
        
    versions = []
    heading_dates = []
    parseable = []
    
    version_heading_pattern = r'^###[ \t]+Version[ \t]+([^ \t]+)[ \t]+\(([0-9]{4}-[0-9]{2}-[0-9]{2})\)[ \t]*$'
    
    for idx in version_idx:
        heading = section[idx]
        match = re.match(version_heading_pattern, heading)
        if not match:
            errors.append(f"Malformed version heading '{heading.strip()}'; expected '### Version X.Y.Z (YYYY-MM-DD)'")
            versions.append(None)
            heading_dates.append(None)
            parseable.append(False)
            continue
            
        v = match.group(1)
        d = match.group(2)
        versions.append(v)
        heading_dates.append(d)
        
        if not re.match(SEMVER_PATTERN, v):
            errors.append(f"Version '{v}' in '## History & Reviews' is not semantic versioning (X.Y.Z)")
            parseable.append(False)
        else:
            parseable.append(True)
            
        if not is_valid_date(d):
            errors.append(f"Invalid date '{d}' in heading '{heading.strip()}'")

    if len(versions) > 1:
        for i in range(len(versions) - 1):
            if not parseable[i] or not parseable[i+1]:
                continue
            v1 = list(map(int, versions[i].split('.')))
            v2 = list(map(int, versions[i+1].split('.')))
            if v1 == v2:
                errors.append(f"Duplicate version entry '{versions[i]}' in '## History & Reviews'")
            elif v1 < v2:
                errors.append(f"Version entries must be in descending order (newest at the top), but '{versions[i]}' appears above '{versions[i+1]}'")
                
    fm_version = str(frontmatter.get('version', ''))
    if parseable[0] and versions[0] != fm_version:
        errors.append(f"Top entry in '## History & Reviews' is version '{versions[0]}', but frontmatter declares version '{fm_version}'")
        
    fm_date = str(frontmatter.get('date', ''))
    if heading_dates[0] is not None and heading_dates[0] != fm_date:
        errors.append(f"Top entry in '## History & Reviews' is dated '{heading_dates[0]}', but frontmatter declares date '{fm_date}'. The heading date is the version's release date.")

    bounds = version_idx + [len(section)]
    md_reviews = []

    for k in range(len(version_idx)):
        label = versions[k] if versions[k] is not None else section[version_idx[k]].strip()
        body = section[version_idx[k]+1:bounds[k+1]]
        
        changes_idx = [i for i, line in enumerate(body) if re.match(r'^####[ \t]+Changes[ \t]*$', line)]
        if not changes_idx:
            errors.append(f"Version {label} is missing a '#### Changes' subsection")
        else:
            subsequent = [i for i, line in enumerate(body) if re.match(r'^####[ \t]', line)]
            next_heading = [i for i in subsequent if i > changes_idx[0]]
            changes_end = next_heading[0] if next_heading else len(body)
            changes_body = body[changes_idx[0]+1:changes_end]
            if not any(re.match(r'^-[ \t]+[^ \t]', line) for line in changes_body):
                errors.append(f"Version {label} has an empty '#### Changes' subsection; list what changed as bullet points")
                
        reviews_idx = [i for i, line in enumerate(body) if re.match(r'^####[ \t]+Reviews[ \t]*$', line)]
        if not reviews_idx:
            errors.append(f"Version {label} is missing a '#### Reviews' subsection")
            continue
            
        reviews_body = body[reviews_idx[0]+1:]
        block_starts = [i for i, line in enumerate(reviews_body) if re.match(r'^\*\*Review by', line)]
        block_bounds = block_starts + [len(reviews_body)]
        reviewer_names = []
        
        for b in range(len(block_starts)):
            heading = reviews_body[block_starts[b]]
            block = reviews_body[block_starts[b]+1:block_bounds[b+1]]
            
            match = re.match(r'^\*\*Review by[ \t]+(.+)\*\*[ \t]*$', heading)
            if not match:
                errors.append(f"Malformed review heading '{heading.strip()}' under version {label}; expected '**Review by <Name>**'")
                continue
                
            who = match.group(1)
            block_orcid = None
            linked_orcid_match = re.search(r'\(\[([^]]*)\]\([^)]*\)\)[ \t]*$', who)
            if linked_orcid_match:
                block_orcid = linked_orcid_match.group(1)
                if not re.match(ORCID_PATTERN, block_orcid):
                    errors.append(f"Invalid ORCID '{block_orcid}' in review block under version {label}")
                    
            reviewer = strip_orcid_suffix(who)
            reviewer_names.append(reviewer)
            
            date_line = [line for line in block if re.match(r'^-[ \t]+\*\*Date:\*\*', line)]
            block_date = None
            if not date_line:
                errors.append(f"Review by '{reviewer}' under version {label} is missing a '- **Date:**' line")
            else:
                block_date = re.sub(r'^-[ \t]+\*\*Date:\*\*', '', date_line[0]).strip()
                if not is_valid_date(block_date):
                    errors.append(f"Review by '{reviewer}' under version {label} has an invalid date '{block_date}' (expected YYYY-MM-DD)")
                    
            status_line = [line for line in block if re.match(r'^-[ \t]+\*\*Status:\*\*', line)]
            block_status = None
            if not status_line:
                errors.append(f"Review by '{reviewer}' under version {label} is missing a '- **Status:**' line")
            else:
                quoted = re.search(r'`([^`]*)`', status_line[0])
                if not quoted:
                    errors.append(f"Review by '{reviewer}' under version {label} must give a backtick-quoted status")
                else:
                    block_status = quoted.group(1)
                    if block_status not in ['approved', 'verified-with-benchmark', 'changes-requested', 'deprecated']:
                        errors.append(f"Invalid review status '{block_status}' under version {label}. Must be one of: approved, verified-with-benchmark, changes-requested, deprecated")

            if not any(re.match(r'^-[ \t]+\*\*Notes:\*\*', line) for line in block):
                errors.append(f"Review by '{reviewer}' under version {label} is missing a '- **Notes:**' line")
                
            if versions[k] is not None:
                md_reviews.append({
                    'version': versions[k],
                    'name': reviewer,
                    'date': block_date,
                    'status': block_status,
                    'orcid': block_orcid
                })

        placeholder = any(re.match(r'^\*No reviews yet\.\*[ \t]*$', line) for line in reviews_body)
        if not reviewer_names and not placeholder:
            errors.append(f"Version {label} has no review blocks; its '#### Reviews' subsection must contain '*No reviews yet.*'")
        if reviewer_names and placeholder:
            errors.append(f"Version {label} has review blocks but is also marked '*No reviews yet.*'")

    # Convert frontmatter_reviews to similar dict format to compare
    fm_reviews_list = []
    if isinstance(frontmatter_reviews, list):
        for r in frontmatter_reviews:
            r_dict = r.model_dump() if hasattr(r, 'model_dump') else r
            if not isinstance(r_dict, dict):
                continue
                
            # Check version
            if r_dict.get('protocol_version') not in [v for i, v in enumerate(versions) if parseable[i]]:
                errors.append(f"Review by '{r_dict.get('name', 'Unknown')}' declares protocol_version '{r_dict.get('protocol_version')}', which has no matching entry in '## History & Reviews'")
                
            fm_reviews_list.append({
                'version': r_dict.get('protocol_version'),
                'name': r_dict.get('name'),
                'date': str(r_dict.get('date')) if r_dict.get('date') else None,
                'status': r_dict.get('status'),
                'orcid': r_dict.get('orcid')
            })

    def review_key(r):
        return f"version {r['version']}, reviewer '{r['name']}'"
        
    md_keys = {review_key(r): r for r in md_reviews}
    fm_keys = {review_key(r): r for r in fm_reviews_list}
    
    for key in set(md_keys.keys()) - set(fm_keys.keys()):
        errors.append(f"Review block for {key} has no matching entry in the frontmatter 'reviews' array")
    for key in set(fm_keys.keys()) - set(md_keys.keys()):
        errors.append(f"Frontmatter review for {key} has no matching '**Review by ...**' block under that version")
        
    for key in set(md_keys.keys()) & set(fm_keys.keys()):
        from_md = md_keys[key]
        from_fm = fm_keys[key]
        for field in ['date', 'status', 'orcid']:
            md_value = from_md.get(field)
            fm_value = from_fm.get(field)
            if md_value is None:
                continue
            if md_value != fm_value:
                errors.append(f"Review for {key} disagrees between the markdown block and the frontmatter: {field} is '{md_value}' in the section but '{fm_value}' in 'reviews'")

    if errors:
        for message in errors:
            print(f"  [ERROR] {message}")
        return False
    return True

def validate_protocol(file_path, protocols_dir):
    print(f"Validating {file_path}...")
    try:
        raw_frontmatter = extract_frontmatter(file_path)
    except Exception as e:
        print(f"  [ERROR] {e}")
        return False
        
    if raw_frontmatter is None:
        print("  [ERROR] Failed to parse YAML frontmatter: missing or invalid")
        return False
        
    if not isinstance(raw_frontmatter, dict):
        print("  [ERROR] Failed to parse YAML frontmatter: document is not a mapping")
        return False

    errors = check_renamed_fields(raw_frontmatter)
    
    try:
        fm_model = ProtocolFrontmatter(**raw_frontmatter)
    except Exception as e:
        import json
        try:
            # Pydantic ValidationError
            for err in e.errors():
                loc = ".".join(str(l) for l in err["loc"])
                msg = err["msg"]
                # We need to mimic the old R error messages slightly or just output pydantic errors
                if err["type"] == "missing":
                    errors.append(f"Missing required fields: {loc}")
                else:
                    errors.append(f"'{loc}' {msg}")
        except:
            errors.append(f"Frontmatter validation error: {str(e)}")
            
        fm_model = None
        
    dir_name = os.path.basename(os.path.dirname(file_path))
    display_name = raw_frontmatter.get('name', dir_name) if isinstance(raw_frontmatter.get('name'), str) else dir_name

    if isinstance(raw_frontmatter.get('name'), str) and dir_name != raw_frontmatter.get('name'):
        errors.append(f"Directory name '{dir_name}' does not match protocol name '{raw_frontmatter['name']}'")

    # Body sections validation
    with open(file_path, 'r', encoding='utf-8') as f:
        body = [line.rstrip('\n') for line in f]
        
    prose = strip_frontmatter_and_code(body)
    if not any(re.match(r'^##[ \t]+Materials[ \t]*$', line) for line in prose):
        errors.append("Missing required '## Materials' section (see PROTOCOL_STANDARD.md)")
        
    step_heading_idx = [i for i, line in enumerate(prose) if re.match(r'^##[ \t]+Steps[ \t]*$', line)]
    if not step_heading_idx:
        errors.append("Missing required '## Steps' section (see PROTOCOL_STANDARD.md)")
    else:
        after = prose[step_heading_idx[0]+1:]
        next_section = [i for i, line in enumerate(after) if re.match(r'^##[ \t]', line)]
        section = after[:next_section[0]] if next_section else after
        if not any(re.match(r'^###[ \t]+Step([ \t]|:|$)', line) for line in section):
            errors.append("'## Steps' contains no '### Step' heading; a protocol must have at least one step")
            
    if fm_model and fm_model.protocols_used:
        this_repository = detect_repository()
        for dep in fm_model.protocols_used:
            if this_repository is None:
                print(f"  [WARN] Cannot determine this repository, so the local availability of dependency '{dep.name}' was not checked. Set GITHUB_REPOSITORY to 'owner/name' to enable this check.")
            elif dep.repository == this_repository:
                dep_path = os.path.join(protocols_dir, dep.name, "protocol.md")
                if not os.path.exists(dep_path):
                    errors.append(f"Dependent protocol '{dep.name}' not found at '{dep_path}'")

    for msg in errors:
        print(f"  [ERROR] {msg} in '{display_name}'")
        
    fm_reviews = fm_model.reviews if fm_model else []
        
    history_ok = validate_history(file_path, raw_frontmatter, fm_reviews)

    if errors or not history_ok:
        return False

    print("  [OK] Valid.")
    return True

if __name__ == '__main__':
    args = sys.argv[1:]
    protocols_dir = args[0] if len(args) >= 1 and args[0] else "protocols"
    
    if not os.path.isdir(protocols_dir):
        print(f"  [ERROR] No '{protocols_dir}' directory found. Pass the protocols directory as the first argument.")
        sys.exit(1)
        
    protocol_files = list(Path(protocols_dir).rglob("protocol.md"))
    if not protocol_files:
        print(f"  [ERROR] No 'protocol.md' files found under '{protocols_dir}'.")
        sys.exit(1)
        
    results = [validate_protocol(str(f), protocols_dir) for f in protocol_files]
    
    if not all(results):
        print("\nValidation failed for some protocols.")
        sys.exit(1)
    else:
        print("\nAll protocols passed validation!")
