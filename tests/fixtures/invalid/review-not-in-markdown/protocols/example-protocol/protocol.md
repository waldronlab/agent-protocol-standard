---
name: example-protocol
description: A minimal conforming protocol used as a fixture for the validator test suite.
version: 1.1.0
authors:
  - name: Ada Lovelace
    orcid: 0000-0002-1825-0097
reviews:
  - name: Marie Curie
    date: 2026-03-05
    protocol_version: 1.1.0
    status: approved
  - name: Grace Hopper
    orcid: 0000-0001-5109-3700
    date: 2026-02-01
    protocol_version: 1.0.0
    status: verified-with-benchmark
  - name: Alan Turing
    date: 2026-01-20
    protocol_version: 1.0.0
    status: approved
date: 2026-03-01
status: draft
license: CC-BY-4.0
type: atomic
method_origin_citation: "10.1000/example"
protocol_citation: "10.1000/example-procedure"
protocols_used: []
key_packages: []
category: example
tags: [example, fixture]
---

# Example Protocol

A minimal conforming protocol, exercising two releases, a reviewed older version, an unreviewed
current version, and a reviewer with and without an ORCID.

## Materials

- **Software & Repositories:**
  - `example-tool` (https://example.org/example-tool) — version 1.0.

## Steps

### Step 1: Run the example tool
Run `example-tool --input reads.fastq --output counts.tsv`.

## Notes

This protocol exists only to exercise `scripts/validate-protocol.R`. It is not a real method.

## History & Reviews
<!-- Newest versions at the top -->

### Version 1.1.0 (2026-03-01)

#### Changes
- Made the output path of Step 1 explicit.

#### Reviews
*No reviews yet.*

### Version 1.0.0 (2026-01-15)

#### Changes
- Initial protocol creation.

#### Reviews

**Review by Grace Hopper ([0000-0001-5109-3700](https://orcid.org/0000-0001-5109-3700))**
- **Date:** 2026-02-01
- **Status:** `verified-with-benchmark`
- **Notes:** Executed against the example dataset; the output counts matched the expected values.

**Review by Alan Turing**
- **Date:** 2026-01-20
- **Status:** `approved`
- **Notes:** Read for scientific soundness. The parameters in Step 1 are appropriate.
