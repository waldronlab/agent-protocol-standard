---
name: example-composite
description: A composite protocol whose dependency lives in this same repository.
version: 1.0.0
authors:
  - name: Ada Lovelace
date: 2026-01-15
status: draft
license: CC-BY-4.0
type: composite
# A sequence of methods can itself be published as a method; this is permitted.
method_origin_citation: "10.1000/example-pipeline"
protocol_citation: "10.1000/example-procedure"
protocols_used:
  - name: example-atomic
    repository: example-org/example-protocols
    version: 1.0.0
key_packages: []
category: example
tags: [example, fixture]
---

# Example Composite Protocol

Exercises the local-dependency check, which resolves `repository:` against the repository the
validator is running in.

## Materials

- **Software & Repositories:**
  - `example-tool` (https://example.org/example-tool) — version 1.0.

## Steps

### Step 1: Run the atomic protocol
Execute `example-atomic`.

## History & Reviews
<!-- Newest versions at the top -->

### Version 1.0.0 (2026-01-15)

#### Changes
- Initial protocol creation.

#### Reviews
*No reviews yet.*
