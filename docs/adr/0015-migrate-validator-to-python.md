# ADR 1: Migrate Protocol Validator to Python and Pydantic

**Date:** 2026-09-13
**Status:** Accepted

## Context
The `agent-protocol-standard` repository defines the schema for AI agent protocols. Initially, the validator and its test suite were written in R. This aligned perfectly with the lab's primary domain expertise in R and the Bioconductor ecosystem, ensuring that existing contributors could easily read and maintain the repository's infrastructure.

However, R lacks a mainstream, declarative data-validation library equivalent to Python's Pydantic. Because of this, the R implementation suffered from two critical flaws:
1. **Procedural Complexity:** The validation logic grew into a monolithic ~800-line script consisting of manual `if` statements, loops, and custom error formatting for every individual field and edge case.
2. **Fragile Testing:** To test the CLI script, the test suite relied on error-prone string manipulation (custom regex to find and remove markdown headers or YAML blocks) to generate malformed protocols. A simple addition to the schema often broke the regex logic of dozens of unrelated tests, creating a massive maintenance burden.

## Decision
We will transition the `agent-protocol-standard` validator and its test suite from R to Python. We will use **Pydantic** to define the schema declaratively, and **Pytest** to run the test suite.

## Consequences

### Positive
*   **Declarative Simplicity:** Complex validation logic (e.g., cross-field dependencies, type checking) is now handled natively by Pydantic. The core logic was reduced from ~800 lines of procedural R to ~160 lines of declarative Python.
*   **Robust Testing:** Testing is now performed in-memory on Python dictionaries (e.g., `Protocol(**bad_dict)`), completely eliminating the need for fragile string manipulation and disk I/O.
*   **Speed:** The test suite executes in a fraction of the time.

### Negative / Trade-offs
*   **Ecosystem Divergence:** The repository's tooling stack now diverges from the lab's standard R/Bioconductor ecosystem. 
*   **Maintenance Barrier:** Contributors who are fluent in R but unfamiliar with Python will face a higher barrier to entry when attempting to modify the validator's logic or GitHub Actions CI pipelines. To mitigate this, clear developer documentation on modifying Pydantic models will be maintained.
