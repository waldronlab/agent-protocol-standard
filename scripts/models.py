from pydantic import BaseModel, Field, field_validator, model_validator
from typing import List, Optional, Literal
from datetime import date
import re

ORCID_PATTERN = r"^[0-9]{4}-[0-9]{4}-[0-9]{4}-[0-9]{3}[0-9X]$"
KEBAB_CASE_PATTERN = r"^[a-z0-9]+(-[a-z0-9]+)*$"
CITATION_PATTERN = r"^(10\.[0-9]{4,9}/[^\s]+|PMID:[0-9]+)$"
TEMPLATE_PLACEHOLDER_CITATION = "10.0000/replace-with-a-real-doi"
SEMVER_PATTERN = r"^[0-9]+\.[0-9]+\.[0-9]+$"

class Author(BaseModel):
    name: str
    orcid: Optional[str] = None

    @field_validator('orcid')
    def validate_orcid(cls, v):
        if v is not None and not re.match(ORCID_PATTERN, v):
            raise ValueError(f"Malformed ORCID: '{v}'")
        return v

class Review(BaseModel):
    name: str
    date: date
    protocol_version: str
    status: Literal['approved', 'verified-with-benchmark', 'changes-requested', 'deprecated']
    orcid: Optional[str] = None

    @field_validator('orcid')
    def validate_orcid(cls, v):
        if v is not None and not re.match(ORCID_PATTERN, v):
            raise ValueError(f"Malformed ORCID: '{v}'")
        return v

class ProtocolUsed(BaseModel):
    name: str
    repository: str
    version: str

class ProtocolFrontmatter(BaseModel):
    name: str
    description: str
    version: str
    authors: List[Author]
    date: date
    status: Literal['draft', 'stable', 'deprecated', 'superseded']
    protocol_citation: str
    
    type: Optional[Literal['atomic', 'composite']] = None
    license: Optional[str] = None
    method_origin_citation: Optional[str] = None
    artifact_doi: Optional[str] = None
    collection_doi: Optional[str] = None
    upstream_repositories: Optional[List[str]] = None
    database_urls: Optional[List[str]] = None
    protocols_used: Optional[List[ProtocolUsed]] = None
    key_packages: Optional[List[str]] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    reviews: Optional[List[Review]] = None

    # We must allow extra fields only for pydantic internals or things not specified? No, Extra.forbid is usually better, but spec doesn't say forbid. Let's not forbid.
    model_config = {'extra': 'allow'}

    @field_validator('name')
    def validate_name(cls, v):
        if not re.match(KEBAB_CASE_PATTERN, v):
            raise ValueError(f"'name' must be kebab-case, found '{v}'")
        return v

    @field_validator('authors')
    def validate_authors(cls, v):
        if not v:
            raise ValueError("must be a non-empty list of objects")
        return v

    @field_validator('description', 'version')
    def validate_non_blank_string(cls, v):
        if not v.strip():
            raise ValueError("must not be blank")
        return v
        
    @field_validator('protocol_citation', 'method_origin_citation')
    def validate_citation(cls, v, info):
        if v is not None:
            if v == TEMPLATE_PLACEHOLDER_CITATION:
                raise ValueError(f"is still the template placeholder '{TEMPLATE_PLACEHOLDER_CITATION}'; replace it with the real citation")
            if not re.match(CITATION_PATTERN, v):
                raise ValueError(f"must be a DOI ('10.1000/xyz') or a PubMed ID ('PMID:12345678'), found: '{v}'")
        return v

    @model_validator(mode='before')
    @classmethod
    def reject_explicit_nulls(cls, data: dict):
        for field in ['type', 'method_origin_citation']:
            if field in data and data[field] is None:
                raise ValueError(f"Explicit null for '{field}' is not allowed; omit the field entirely instead")
        return data

    @model_validator(mode='after')
    def validate_type_and_deps(self):
        n_deps = len(self.protocols_used) if self.protocols_used else 0
        effective_type = self.type if self.type else ('composite' if n_deps > 0 else 'atomic')
        
        if effective_type == 'atomic' and n_deps > 0:
            raise ValueError(f"'type: atomic' cannot declare 'protocols_used' ({n_deps} listed); an atomic protocol composes no others")
        if effective_type == 'composite' and n_deps == 0:
            raise ValueError("'type: composite' requires a non-empty 'protocols_used'; a composite composes other protocols")
            
        return self

def check_renamed_fields(data: dict):
    # This must run before Pydantic parsing if we want to catch renamed fields
    renamed_fields = {
        'citation': 'method_origin_citation',
        'method_citation': 'method_origin_citation',
        'publication_doi': 'protocol_citation',
        'protocol_doi': 'artifact_doi',
        'repository_doi': 'collection_doi'
    }
    errors = []
    if 'citations' in data:
        errors.append("Deprecated 'citations' field found. Use 'method_origin_citation' (singular string)")
        
    for old_name, new_name in renamed_fields.items():
        if old_name in data:
            errors.append(f"Field '{old_name}' was renamed to '{new_name}' (see PROTOCOL_STANDARD.md)")
            
    return errors
