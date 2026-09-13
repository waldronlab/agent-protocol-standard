---
name: example-protocol
description: A minimal conforming protocol used as a fixture for the validator test suite.
version: 1.1.0
authors:
  - name: Ada Lovelace
    orcid: 0000-0002-1825-0097
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
