# Development Guide

This repository contains the `agent-protocol-standard` schema definitions, the Python-based validator, and the GitHub Actions used by content repositories.

## Technical Stack
- **Language**: Python 3.10+
- **Validation**: [Pydantic](https://docs.pydantic.dev/) for declarative schema definitions.
- **Testing**: [Pytest](https://docs.pytest.org/) for model, fixture, and CLI validation.

## Local Setup
To run tests locally, install Python and the required dependencies:
```bash
pip install pytest "pydantic>=2.0.0" pyyaml
```

## Running Tests
Run the entire test suite from the root of the repository:
```bash
pytest tests/
```

## Modifying the Schema

The protocol frontmatter schema is defined in `scripts/models.py` using Pydantic. Document-level checks (like Materials/Steps and History & Reviews) are implemented in `scripts/validate_protocol.py`. 

### Adding a New Field
To add a new field to the protocol frontmatter, add it as a class attribute to the `ProtocolFrontmatter` class in `scripts/models.py`. Pydantic handles type coercion and basic validation automatically.

```python
class ProtocolFrontmatter(BaseModel):
    # ... existing fields ...
    funding_source: Optional[str] = None  # Example of a new optional field
```

### Adding a Complex Validation Rule
If a field requires complex validation (e.g., cross-field dependencies, custom formatting, or complex error messages), use a Pydantic `@model_validator` or `@field_validator`.

For example, to enforce that composite protocols declare dependencies:
```python
from pydantic import BaseModel, model_validator
from typing import Literal

class ProtocolFrontmatter(BaseModel):
    type: Literal['atomic', 'composite']
    protocols_used: list = []

    @model_validator(mode='after')
    def check_composite_dependencies(self) -> 'ProtocolFrontmatter':
        if self.type == 'composite' and not self.protocols_used:
            raise ValueError("Composite protocols must declare 'protocols_used'")
        return self
```

## Testing Validation Changes

Because we use Pydantic, testing frontmatter model rules does not require writing markdown files to disk or dealing with fragile string manipulation. You test those model rules in-memory by passing dictionaries to the models.
End-to-end validator behavior is still tested with Markdown fixtures and CLI/filesystem execution paths in `tests/test_validate_protocol.py`.

Add your tests to `tests/test_models.py`:

```python
import pytest
from pydantic import ValidationError
from scripts.models import ProtocolFrontmatter

def test_composite_requires_dependencies():
    # 1. Start with a valid baseline dictionary
    bad_dict = {**valid_dict()}
    
    # 2. Mutate it to trigger the failure state
    bad_dict["type"] = "composite"
    bad_dict["protocols_used"] = []
    
    # 3. Assert that Pydantic rejects it with the expected error message
    with pytest.raises(ValidationError, match="'type: composite' requires a non-empty 'protocols_used'"):
        ProtocolFrontmatter(**bad_dict)
```

## Updating the Template and Fixtures
If your schema change adds a new required field, ensure you also update `template/protocols/example-protocol/protocol.md` so that future protocols scaffolded from the template do not immediately fail validation.

Additionally, update the valid fixtures in `tests/fixtures/valid/` and any affected content-repository protocols, otherwise CI will fail when validating existing protocols against the new schema.
