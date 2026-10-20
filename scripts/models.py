from pydantic import BaseModel, Field, field_validator, model_validator
from typing import List, Optional, Literal, Any, Dict, Iterator, Tuple
from datetime import date, datetime
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

    @field_validator('date', mode='before')
    def validate_date_format(cls, v):
        if isinstance(v, str):
            try:
                return date.fromisoformat(v)
            except ValueError as exc:
                raise ValueError("Must be YYYY-MM-DD date") from exc
        if isinstance(v, datetime):
            raise ValueError("Must be a YYYY-MM-DD date")
        if not isinstance(v, date):
            raise ValueError("Must be a YYYY-MM-DD date")
        return v

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

    @field_validator('date', mode='before')
    def validate_date_format(cls, v):
        if isinstance(v, str):
            try:
                return date.fromisoformat(v)
            except ValueError as exc:
                raise ValueError("Must be YYYY-MM-DD date") from exc
        if isinstance(v, datetime):
            raise ValueError("Must be a YYYY-MM-DD date")
        if not isinstance(v, date):
            raise ValueError("Must be a YYYY-MM-DD date")
        return v

    @field_validator('type', mode='before')
    def reject_null_type(cls, v):
        if v is None:
            raise ValueError("must be either 'atomic' or 'composite'")
        return v

    @field_validator('method_origin_citation', mode='before')
    def reject_null_method_origin_citation(cls, v):
        if v is None:
            raise ValueError("must be omitted when unknown; do not set it to null")
        return v

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

# ---------------------------------------------------------------------------
# Protocol tests: protocols/<name>/tests/<test-name>/test.yaml (PROTOCOL_STANDARD.md, "Tests")
# ---------------------------------------------------------------------------

TEST_NAME_PATTERN = r"^[a-z0-9]+([-_][a-z0-9]+)*$"
SHA256_PATTERN = r"^[0-9a-f]{64}$"
# Keys the executor's own report uses in diagnostic mode; a test may not expect them.
RESERVED_RESULT_KEYS = ("outcome", "observation")
# Keys the checker writes into run.yaml itself; executor.yaml may not supply them.
RESERVED_RUN_RECORD_KEYS = (
    "run_record", "protocol", "version", "repository", "protocol_commit",
    "uncommitted", "source_digest", "checker", "tests",
)


class FileRef(BaseModel):
    """A file slot: exactly one of {path} or {url, sha256}; `header` only on an expected table."""
    model_config = {'extra': 'forbid'}
    path: Optional[str] = None
    url: Optional[str] = None
    sha256: Optional[str] = None
    header: Optional[Literal['shown', 'withheld']] = None

    @model_validator(mode='after')
    def one_shape(self):
        if self.path is not None and (self.url is not None or self.sha256 is not None):
            raise ValueError("a file is either {path} or {url, sha256}, not both")
        if self.path is None and self.url is None:
            raise ValueError("a file needs 'path' or 'url'")
        if self.path is not None:
            p = self.path
            if p.startswith('/') or p.startswith('\\') or re.match(r'^[A-Za-z]:', p):
                raise ValueError(f"'path' must be relative to the test directory, found '{p}'")
            if '..' in p.replace('\\', '/').split('/'):
                raise ValueError(f"'path' may not leave the test directory, found '{p}'")
        if self.url is not None:
            if not self.url.startswith('https://'):
                raise ValueError(f"'url' must be https, found '{self.url}'")
            if self.sha256 is None:
                raise ValueError("a remote file needs 'sha256'")
            if not re.match(SHA256_PATTERN, self.sha256):
                raise ValueError("'sha256' must be 64 lowercase hex characters")
        return self

    @property
    def name(self) -> str:
        return self.path if self.path is not None else self.url.rsplit('/', 1)[-1].split('?')[0]

    @property
    def is_table(self) -> bool:
        return self.name.lower().endswith('.csv')


def is_file_mapping(value: Any) -> bool:
    """A mapping is a file slot when it carries 'path' or 'url'; any other mapping is data."""
    return isinstance(value, dict) and ('path' in value or 'url' in value)


def walk_file_refs(obj: Any, prefix: str = "") -> Iterator[Tuple[str, Dict]]:
    """Yield (dotted key path, raw mapping) for every file slot inside obj."""
    if is_file_mapping(obj):
        yield prefix or "<root>", obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            yield from walk_file_refs(v, f"{prefix}.{k}" if prefix else str(k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from walk_file_refs(v, f"{prefix}[{i}]")


def _check_file_refs(obj: Any, where: str, expected: bool):
    for key, raw in walk_file_refs(obj):
        try:
            ref = FileRef(**raw)
        except Exception as exc:
            raise ValueError(f"{where}.{key}: {_first_error(exc)}")
        if ref.header is not None and not (expected and ref.is_table):
            raise ValueError(f"{where}.{key}: 'header' is only allowed on a table in expected_outputs")
        if expected and not ref.is_table:
            raise ValueError(
                f"{where}.{key}: an expected file must be a CSV table (name ending in .csv); "
                f"no other file format is defined"
            )


def _first_error(exc: Exception) -> str:
    errors = getattr(exc, 'errors', None)
    if callable(errors):
        try:
            errs = errors()
            if errs:
                loc = ".".join(str(l) for l in errs[0].get('loc', ()))
                msg = errs[0]['msg'].replace('Value error, ', '')
                return f"{loc}: {msg}" if loc else msg
        except Exception:
            pass
    return str(exc)


def _check_no_reserved(mapping: Dict, where: str):
    for k in RESERVED_RESULT_KEYS:
        if k in mapping:
            raise ValueError(f"{where} may not use the reserved key '{k}'")


class AcceptedOutcome(BaseModel):
    model_config = {'extra': 'forbid'}
    outcome: str
    expected_outputs: Optional[Dict[str, Any]] = None
    expected_absent: Optional[List[str]] = None

    @model_validator(mode='after')
    def has_evidence(self):
        if not re.match(TEST_NAME_PATTERN, self.outcome):
            raise ValueError(f"outcome label must be lower-case words joined by - or _, found '{self.outcome}'")
        has_outputs = bool(self.expected_outputs)
        has_absent = bool(self.expected_absent)
        if not has_outputs and not has_absent:
            raise ValueError(
                f"outcome '{self.outcome}' needs evidence: a non-empty 'expected_outputs' or 'expected_absent'"
            )
        if has_outputs:
            _check_no_reserved(self.expected_outputs, f"outcome '{self.outcome}' expected_outputs")
            _check_file_refs(self.expected_outputs, f"outcome '{self.outcome}' expected_outputs", expected=True)
        if has_absent:
            for k in self.expected_absent:
                if k in RESERVED_RESULT_KEYS:
                    raise ValueError(f"outcome '{self.outcome}' expected_absent may not name the reserved key '{k}'")
        return self


class Evaluation(BaseModel):
    model_config = {'extra': 'forbid'}
    mode: Literal['exact', 'diagnostic']
    numeric_tolerance: float = 0.0
    accepted_outcomes: Optional[List[AcceptedOutcome]] = None

    @field_validator('numeric_tolerance')
    def non_negative(cls, v):
        if v < 0:
            raise ValueError("'numeric_tolerance' must be >= 0")
        return v


class ProtocolTest(BaseModel):
    """The schema of one test.yaml."""
    model_config = {'extra': 'forbid'}
    name: str
    description: str
    inputs: Dict[str, Any]
    expected_outputs: Optional[Dict[str, Any]] = None
    evaluation: Evaluation

    @field_validator('name')
    def validate_name(cls, v):
        if not re.match(TEST_NAME_PATTERN, v):
            raise ValueError(f"'name' must be lower-case words joined by - or _, found '{v}'")
        return v

    @field_validator('description')
    def validate_description(cls, v):
        if not v.strip():
            raise ValueError("'description' must not be blank")
        return v

    @model_validator(mode='after')
    def mode_consistency(self):
        _check_file_refs(self.inputs, "inputs", expected=False)
        if self.evaluation.mode == 'exact':
            if not self.expected_outputs:
                raise ValueError("mode 'exact' requires a non-empty 'expected_outputs'; a test that checks nothing is invalid")
            if self.evaluation.accepted_outcomes:
                raise ValueError("mode 'exact' does not use 'accepted_outcomes'")
            _check_no_reserved(self.expected_outputs, "expected_outputs")
            _check_file_refs(self.expected_outputs, "expected_outputs", expected=True)
        else:
            if self.expected_outputs is not None:
                raise ValueError("mode 'diagnostic' puts expectations under each accepted outcome, not at the top level")
            if not self.evaluation.accepted_outcomes:
                raise ValueError("mode 'diagnostic' requires a non-empty 'accepted_outcomes'")
            labels = [o.outcome for o in self.evaluation.accepted_outcomes]
            if len(set(labels)) != len(labels):
                raise ValueError("accepted outcome labels must be unique")
        return self

    def outcome(self, label: str) -> Optional[AcceptedOutcome]:
        for o in self.evaluation.accepted_outcomes or []:
            if o.outcome == label:
                return o
        return None


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
