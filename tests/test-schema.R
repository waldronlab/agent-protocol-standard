# Generated dynamically
baseline <- c(

  "---",
  "name: example-protocol",
  "description: A minimal conforming protocol used as a fixture for the validator test suite.",
  "version: 1.1.0",
  "authors:",
  "  - name: Ada Lovelace",
  "    orcid: 0000-0002-1825-0097",
  "reviews:",
  "  - name: Grace Hopper",
  "    orcid: 0000-0001-5109-3700",
  "    date: 2026-02-01",
  "    protocol_version: 1.0.0",
  "    status: verified-with-benchmark",
  "  - name: Alan Turing",
  "    date: 2026-01-20",
  "    protocol_version: 1.0.0",
  "    status: approved",
  "date: 2026-03-01",
  "status: draft",
  "license: CC-BY-4.0",
  "type: atomic",
  "method_origin_citation: \"10.1000/example\"",
  "protocol_citation: \"10.1000/example-procedure\"",
  "protocols_used: []",
  "key_packages: []",
  "category: example",
  "tags: [example, fixture]",
  "---",
  "",
  "# Example Protocol",
  "",
  "A minimal conforming protocol, exercising two releases, a reviewed older version, an unreviewed",
  "current version, and a reviewer with and without an ORCID.",
  "",
  "## Materials",
  "",
  "- **Software & Repositories:**",
  "  - `example-tool` (https://example.org/example-tool) — version 1.0.",
  "",
  "## Steps",
  "",
  "### Step 1: Run the example tool",
  "Run `example-tool --input reads.fastq --output counts.tsv`.",
  "",
  "## Notes",
  "",
  "This protocol exists only to exercise `scripts/validate-protocol.R`. It is not a real method.",
  "",
  "## History & Reviews",
  "<!-- Newest versions at the top -->",
  "",
  "### Version 1.1.0 (2026-03-01)",
  "",
  "#### Changes",
  "- Made the output path of Step 1 explicit.",
  "",
  "#### Reviews",
  "*No reviews yet.*",
  "",
  "### Version 1.0.0 (2026-01-15)",
  "",
  "#### Changes",
  "- Initial protocol creation.",
  "",
  "#### Reviews",
  "",
  "**Review by Grace Hopper ([0000-0001-5109-3700](https://orcid.org/0000-0001-5109-3700))**",
  "- **Date:** 2026-02-01",
  "- **Status:** `verified-with-benchmark`",
  "- **Notes:** Executed against the example dataset; the output counts matched the expected values.",
  "",
  "**Review by Alan Turing**",
  "- **Date:** 2026-01-20",
  "- **Status:** `approved`",
  "- **Notes:** Read for scientific soundness. The parameters in Step 1 are appropriate."
)


replace_line <- function(lines, pattern, replacement) {
  idx <- which(lines == pattern)
  if (length(idx) == 0) stop(paste("Pattern not found:", pattern))
  lines[idx[1]] <- replacement
  lines
}

remove_line <- function(lines, pattern) {
  idx <- which(lines == pattern)
  if (length(idx) == 0) stop(paste("Pattern not found:", pattern))
  lines[-idx[1]]
}

remove_block <- function(lines, start_pattern, end_pattern) {
  start_idx <- which(lines == start_pattern)
  if (length(start_idx) == 0) stop(paste("Start pattern not found:", start_pattern))
  end_idx <- which(lines == end_pattern)
  if (length(end_idx) == 0) stop(paste("End pattern not found:", end_pattern))
  end_idx <- end_idx[end_idx > start_idx[1]][1]
  lines[-(start_idx[1]:end_idx)]
}

insert_after <- function(lines, pattern, insert) {
  idx <- which(lines == pattern)
  if (length(idx) == 0) stop(paste("Pattern not found:", pattern))
  c(lines[1:idx[1]], insert, if (idx[1] < length(lines)) lines[(idx[1]+1):length(lines)] else character(0))
}

run_case <- function(name, files, expected = NULL) {
  dir <- file.path(tempdir(), "schema-tests", name)
  for (f in names(files)) {
    d <- file.path(dir, "protocols", f)
    dir.create(d, recursive = TRUE, showWarnings = FALSE)
    writeLines(files[[f]], file.path(d, "protocol.md"))
  }
  res <- run_validator(file.path(dir, "protocols"))
  if (is.null(expected)) {
    check(sprintf("valid/%s", name), res$status == 0, sprintf("expected success, got %d\n%s", res$status, res$output))
  } else {
    pass <- res$status != 0 && grepl(expected, res$output, fixed = TRUE)
    check(sprintf("invalid/%s", name), pass, sprintf("expected fail with '%s', got status %d\n%s", expected, res$status, res$output))
  }
}

# valid/basic
local({
  files <- list()
  files[["example-protocol"]] <- baseline
  run_case("basic", files)
})

# valid/bare-step-heading
local({
  files <- list()
  lines <- baseline
  lines <- replace_line(lines, "### Step 1: Run the example tool", c("### Step"))
  files[["example-protocol"]] <- lines
  run_case("bare-step-heading", files)
})

# valid/composite
local({
  files <- list()
  lines <- baseline
  lines <- remove_block(lines, "", "- **Notes:** Read for scientific soundness. The parameters in Step 1 are appropriate.")
  lines <- insert_after(lines, "", c("*No reviews yet.*"))
  lines <- remove_block(lines, "", "*No reviews yet.*")
  lines <- remove_block(lines, "Run `example-tool --input reads.fastq --output counts.tsv`.", "This protocol exists only to exercise `scripts/validate-protocol.R`. It is not a real method.")
  lines <- insert_after(lines, "Run `example-tool --input reads.fastq --output counts.tsv`.", c("Run `example-tool --input reads.fastq`."))
  lines <- remove_block(lines, "A minimal conforming protocol, exercising two releases, a reviewed older version, an unreviewed", "current version, and a reviewer with and without an ORCID.")
  lines <- insert_after(lines, "A minimal conforming protocol, exercising two releases, a reviewed older version, an unreviewed", c("The dependency target for `example-composite`."))
  lines <- replace_line(lines, "# Example Protocol", c("# Example Atomic Protocol"))
  lines <- remove_block(lines, "    orcid: 0000-0002-1825-0097", "date: 2026-03-01")
  lines <- insert_after(lines, "    orcid: 0000-0002-1825-0097", c("date: 2026-01-15"))
  lines <- remove_block(lines, "name: example-protocol", "version: 1.1.0")
  lines <- insert_after(lines, "name: example-protocol", c("name: example-atomic", "description: An atomic protocol that a composite protocol in the same repository depends on.", "version: 1.0.0"))
  files[["example-atomic"]] <- lines
  lines <- baseline
  lines <- remove_block(lines, "", "- **Notes:** Read for scientific soundness. The parameters in Step 1 are appropriate.")
  lines <- insert_after(lines, "", c("*No reviews yet.*"))
  lines <- remove_block(lines, "", "*No reviews yet.*")
  lines <- remove_block(lines, "### Step 1: Run the example tool", "This protocol exists only to exercise `scripts/validate-protocol.R`. It is not a real method.")
  lines <- insert_after(lines, "### Step 1: Run the example tool", c("### Step 1: Run the atomic protocol", "Execute `example-atomic`."))
  lines <- remove_block(lines, "A minimal conforming protocol, exercising two releases, a reviewed older version, an unreviewed", "current version, and a reviewer with and without an ORCID.")
  lines <- insert_after(lines, "A minimal conforming protocol, exercising two releases, a reviewed older version, an unreviewed", c("Exercises the local-dependency check, which resolves `repository:` against the repository the", "validator is running in."))
  lines <- replace_line(lines, "# Example Protocol", c("# Example Composite Protocol"))
  lines <- remove_block(lines, "type: atomic", "protocols_used: []")
  lines <- insert_after(lines, "type: atomic", c("type: composite", "protocols_used:", "  - name: example-atomic", "    repository: example-org/example-protocols", "    version: 1.0.0"))
  lines <- insert_after(lines, "status: draft", c("protocol_citation: \"10.1000/example-procedure\""))
  lines <- remove_block(lines, "    orcid: 0000-0002-1825-0097", "date: 2026-03-01")
  lines <- insert_after(lines, "    orcid: 0000-0002-1825-0097", c("date: 2026-01-15"))
  lines <- remove_block(lines, "name: example-protocol", "version: 1.1.0")
  lines <- insert_after(lines, "name: example-protocol", c("name: example-composite", "description: A composite protocol whose dependency lives in this same repository.", "version: 1.0.0"))
  files[["example-composite"]] <- lines
  run_case("composite", files)
})

# valid/composite-with-method-citation
local({
  files <- list()
  lines <- baseline
  lines <- remove_block(lines, "", "- **Notes:** Read for scientific soundness. The parameters in Step 1 are appropriate.")
  lines <- insert_after(lines, "", c("*No reviews yet.*"))
  lines <- remove_block(lines, "", "*No reviews yet.*")
  lines <- remove_block(lines, "Run `example-tool --input reads.fastq --output counts.tsv`.", "This protocol exists only to exercise `scripts/validate-protocol.R`. It is not a real method.")
  lines <- insert_after(lines, "Run `example-tool --input reads.fastq --output counts.tsv`.", c("Run `example-tool --input reads.fastq`."))
  lines <- remove_block(lines, "A minimal conforming protocol, exercising two releases, a reviewed older version, an unreviewed", "current version, and a reviewer with and without an ORCID.")
  lines <- insert_after(lines, "A minimal conforming protocol, exercising two releases, a reviewed older version, an unreviewed", c("The dependency target for `example-composite`."))
  lines <- replace_line(lines, "# Example Protocol", c("# Example Atomic Protocol"))
  lines <- remove_block(lines, "    orcid: 0000-0002-1825-0097", "date: 2026-03-01")
  lines <- insert_after(lines, "    orcid: 0000-0002-1825-0097", c("date: 2026-01-15"))
  lines <- remove_block(lines, "name: example-protocol", "version: 1.1.0")
  lines <- insert_after(lines, "name: example-protocol", c("name: example-atomic", "description: An atomic protocol that a composite protocol in the same repository depends on.", "version: 1.0.0"))
  files[["example-atomic"]] <- lines
  lines <- baseline
  lines <- remove_block(lines, "", "- **Notes:** Read for scientific soundness. The parameters in Step 1 are appropriate.")
  lines <- insert_after(lines, "", c("*No reviews yet.*"))
  lines <- remove_block(lines, "", "*No reviews yet.*")
  lines <- remove_block(lines, "### Step 1: Run the example tool", "This protocol exists only to exercise `scripts/validate-protocol.R`. It is not a real method.")
  lines <- insert_after(lines, "### Step 1: Run the example tool", c("### Step 1: Run the atomic protocol", "Execute `example-atomic`."))
  lines <- remove_block(lines, "A minimal conforming protocol, exercising two releases, a reviewed older version, an unreviewed", "current version, and a reviewer with and without an ORCID.")
  lines <- insert_after(lines, "A minimal conforming protocol, exercising two releases, a reviewed older version, an unreviewed", c("Exercises the local-dependency check, which resolves `repository:` against the repository the", "validator is running in."))
  lines <- replace_line(lines, "# Example Protocol", c("# Example Composite Protocol"))
  lines <- replace_line(lines, "protocols_used: []", c("protocols_used:", "  - name: example-atomic", "    repository: example-org/example-protocols", "    version: 1.0.0"))
  lines <- remove_block(lines, "type: atomic", "method_origin_citation: \"10.1000/example\"")
  lines <- insert_after(lines, "type: atomic", c("type: composite", "# A sequence of methods can itself be published as a method; this is permitted.", "method_origin_citation: \"10.1000/example-pipeline\""))
  lines <- remove_block(lines, "    orcid: 0000-0002-1825-0097", "date: 2026-03-01")
  lines <- insert_after(lines, "    orcid: 0000-0002-1825-0097", c("date: 2026-01-15"))
  lines <- remove_block(lines, "name: example-protocol", "version: 1.1.0")
  lines <- insert_after(lines, "name: example-protocol", c("name: example-composite", "description: A composite protocol whose dependency lives in this same repository.", "version: 1.0.0"))
  files[["example-composite"]] <- lines
  run_case("composite-with-method-citation", files)
})

# valid/first-release
local({
  files <- list()
  lines <- baseline
  lines <- remove_block(lines, "", "- **Notes:** Read for scientific soundness. The parameters in Step 1 are appropriate.")
  lines <- insert_after(lines, "", c("*No reviews yet.*"))
  lines <- remove_block(lines, "", "*No reviews yet.*")
  lines <- remove_block(lines, "Run `example-tool --input reads.fastq --output counts.tsv`.", "This protocol exists only to exercise `scripts/validate-protocol.R`. It is not a real method.")
  lines <- insert_after(lines, "Run `example-tool --input reads.fastq --output counts.tsv`.", c("Run `example-tool --input reads.fastq`."))
  lines <- remove_block(lines, "A minimal conforming protocol, exercising two releases, a reviewed older version, an unreviewed", "current version, and a reviewer with and without an ORCID.")
  lines <- insert_after(lines, "A minimal conforming protocol, exercising two releases, a reviewed older version, an unreviewed", c("The pre-review case: the section is still required, only its `#### Reviews` body is a placeholder,", "and the optional `reviews:` frontmatter field is omitted entirely."))
  lines <- replace_line(lines, "# Example Protocol", c("# Example First Release"))
  lines <- remove_block(lines, "    orcid: 0000-0002-1825-0097", "date: 2026-03-01")
  lines <- insert_after(lines, "    orcid: 0000-0002-1825-0097", c("date: 2026-01-15"))
  lines <- remove_block(lines, "name: example-protocol", "version: 1.1.0")
  lines <- insert_after(lines, "name: example-protocol", c("name: example-first-release", "description: A first release that nobody has reviewed yet, with no 'reviews' frontmatter field.", "version: 1.0.0"))
  files[["example-first-release"]] <- lines
  run_case("first-release", files)
})

# valid/pmid-citation
local({
  files <- list()
  lines <- baseline
  lines <- replace_line(lines, "method_origin_citation: \"10.1000/example\"", c("method_origin_citation: \"PMID:12345678\""))
  files[["example-protocol"]] <- lines
  run_case("pmid-citation", files)
})

# valid/self-cited-first-definition
local({
  files <- list()
  lines <- baseline
  lines <- replace_line(lines, "A minimal conforming protocol, exercising two releases, a reviewed older version, an unreviewed", c("A first definition: protocol_citation repeats collection_doi, and no method origin is claimed, exercising two releases, a reviewed older version, an unreviewed"))
  lines <- remove_block(lines, "method_origin_citation: \"10.1000/example\"", "protocol_citation: \"10.1000/example-procedure\"")
  lines <- insert_after(lines, "method_origin_citation: \"10.1000/example\"", c("protocol_citation: \"10.5281/zenodo.9999999\""))
  lines <- insert_after(lines, "license: CC-BY-4.0", c("collection_doi: \"10.5281/zenodo.9999999\""))
  lines <- replace_line(lines, "description: A minimal conforming protocol used as a fixture for the validator test suite.", c("description: A first definition — protocol_citation repeats collection_doi, and no method origin is claimed."))
  files[["example-protocol"]] <- lines
  run_case("self-cited-first-definition", files)
})

# valid/stable-status
local({
  files <- list()
  lines <- baseline
  lines <- replace_line(lines, "A minimal conforming protocol, exercising two releases, a reviewed older version, an unreviewed", c("A minimal conforming protocol at status `stable`, exercising two releases, a reviewed older version, an unreviewed"))
  lines <- replace_line(lines, "status: draft", c("status: stable"))
  files[["example-protocol"]] <- lines
  run_case("stable-status", files)
})

# invalid/ascending-order
local({
  files <- list()
  lines <- baseline
  lines <- insert_after(lines, "- **Notes:** Read for scientific soundness. The parameters in Step 1 are appropriate.", c("", "### Version 1.1.0 (2026-03-01)", "", "#### Changes", "- Made the output path of Step 1 explicit.", "", "#### Reviews", "*No reviews yet.*"))
  lines <- remove_block(lines, "### Version 1.1.0 (2026-03-01)", "")
  lines <- replace_line(lines, "date: 2026-03-01", c("date: 2026-01-15"))
  lines <- replace_line(lines, "version: 1.1.0", c("version: 1.0.0"))
  files[["example-protocol"]] <- lines
  run_case("ascending-order", files, "Version entries must be in descending order (newest at the top), but '1.0.0' appears above '1.1.0'")
})

# invalid/atomic-with-dependencies
local({
  files <- list()
  lines <- baseline
  lines <- replace_line(lines, "protocols_used: []", c("protocols_used:", "  - name: other-protocol", "    repository: example/other", "    version: 1.0.0"))
  files[["example-protocol"]] <- lines
  run_case("atomic-with-dependencies", files, "'type: atomic' cannot declare 'protocols_used'")
})

# invalid/composite-without-dependencies
local({
  files <- list()
  lines <- baseline
  lines <- replace_line(lines, "type: atomic", c("type: composite"))
  files[["example-protocol"]] <- lines
  run_case("composite-without-dependencies", files, "'type: composite' requires a non-empty 'protocols_used'")
})

# invalid/date-mismatch
local({
  files <- list()
  lines <- baseline
  lines <- replace_line(lines, "date: 2026-03-01", c("date: 2026-03-02"))
  files[["example-protocol"]] <- lines
  run_case("date-mismatch", files, "Top entry in '## History & Reviews' is dated '2026-03-01', but frontmatter declares date '2026-03-02'")
})

# invalid/deprecated-citations-field
local({
  files <- list()
  lines <- baseline
  lines <- insert_after(lines, "protocol_citation: \"10.1000/example-procedure\"", c("citations: ~"))
  files[["example-protocol"]] <- lines
  run_case("deprecated-citations-field", files, "Deprecated 'citations' field found")
})

# invalid/draft-unreviewed-status
local({
  files <- list()
  lines <- baseline
  lines <- replace_line(lines, "- **Status:** `approved`", c("- **Status:** `draft-unreviewed`"))
  lines <- replace_line(lines, "    status: approved", c("    status: draft-unreviewed"))
  files[["example-protocol"]] <- lines
  run_case("draft-unreviewed-status", files, "Review by 'Alan Turing' has invalid status 'draft-unreviewed'")
})

# invalid/empty-changes
local({
  files <- list()
  lines <- baseline
  lines <- remove_line(lines, "- Made the output path of Step 1 explicit.")
  files[["example-protocol"]] <- lines
  run_case("empty-changes", files, "Version 1.1.0 has an empty '#### Changes' subsection")
})

# invalid/fence-close-with-suffix
local({
  files <- list()
  lines <- baseline
  lines <- insert_after(lines, "Run `example-tool --input reads.fastq --output counts.tsv`.", c("```"))
  lines <- insert_after(lines, "", c("```not-a-close", ""))
  lines <- insert_after(lines, "", c("Example layout:", "", "```markdown"))
  files[["example-protocol"]] <- lines
  run_case("fence-close-with-suffix", files, "Missing required '## Steps' section")
})

# invalid/free-text-method-citation
local({
  files <- list()
  lines <- baseline
  lines <- replace_line(lines, "method_origin_citation: \"10.1000/example\"", c("method_origin_citation: \"see the HUMAnN 4 paper\""))
  files[["example-protocol"]] <- lines
  run_case("free-text-method-citation", files, "must be a DOI ('10.1000/xyz') or a PubMed ID")
})

# invalid/invalid-protocol-status
local({
  files <- list()
  lines <- baseline
  lines <- replace_line(lines, "status: draft", c("status: banana"))
  files[["example-protocol"]] <- lines
  run_case("invalid-protocol-status", files, "'status' must be one of 'draft', 'stable', 'deprecated', 'superseded'")
})

# invalid/invalid-status
local({
  files <- list()
  lines <- baseline
  lines <- replace_line(lines, "- **Status:** `approved`", c("- **Status:** `looks-good`"))
  lines <- replace_line(lines, "    status: approved", c("    status: looks-good"))
  files[["example-protocol"]] <- lines
  run_case("invalid-status", files, "Review by 'Alan Turing' has invalid status 'looks-good'")
})

# invalid/legacy-field-name
local({
  files <- list()
  lines <- baseline
  lines <- remove_block(lines, "method_origin_citation: \"10.1000/example\"", "protocol_citation: \"10.1000/example-procedure\"")
  lines <- insert_after(lines, "method_origin_citation: \"10.1000/example\"", c("citation: \"10.1000/example\""))
  lines <- insert_after(lines, "status: draft", c("protocol_citation: \"10.1000/example-procedure\""))
  files[["example-protocol"]] <- lines
  run_case("legacy-field-name", files, "Field 'citation' was renamed to 'method_origin_citation' (see PROTOCOL_STANDARD.md) in 'example-protocol'")
})

# invalid/legacy-field-null-placeholder
local({
  files <- list()
  lines <- baseline
  lines <- insert_after(lines, "protocol_citation: \"10.1000/example-procedure\"", c("repository_doi: ~"))
  files[["example-protocol"]] <- lines
  run_case("legacy-field-null-placeholder", files, "Field 'repository_doi' was renamed to 'collection_doi' (see PROTOCOL_STANDARD.md) in 'example-protocol'")
})

# invalid/list-valued-type
local({
  files <- list()
  lines <- baseline
  lines <- replace_line(lines, "type: atomic", c("type: [atomic, composite]"))
  files[["example-protocol"]] <- lines
  run_case("list-valued-type", files, "'type' must be either 'atomic' or 'composite'")
})

# invalid/malformed-author-orcid
local({
  files <- list()
  lines <- baseline
  lines <- replace_line(lines, "    orcid: 0000-0002-1825-0097", c("    orcid: 0000-0002-1825"))
  files[["example-protocol"]] <- lines
  run_case("malformed-author-orcid", files, "has a malformed ORCID")
})

# invalid/malformed-orcid
local({
  files <- list()
  lines <- baseline
  lines <- replace_line(lines, "**Review by Grace Hopper ([0000-0001-5109-3700](https://orcid.org/0000-0001-5109-3700))**", c("**Review by Grace Hopper ([0000-0001-5109-370](https://orcid.org/0000-0001-5109-370))**"))
  lines <- replace_line(lines, "    orcid: 0000-0001-5109-3700", c("    orcid: 0000-0001-5109-370"))
  files[["example-protocol"]] <- lines
  run_case("malformed-orcid", files, "Review by 'Grace Hopper' has a malformed 'orcid': 0000-0001-5109-370")
})

# invalid/missing-local-dependency
local({
  files <- list()
  lines <- baseline
  lines <- remove_block(lines, "", "- **Notes:** Read for scientific soundness. The parameters in Step 1 are appropriate.")
  lines <- insert_after(lines, "", c("*No reviews yet.*"))
  lines <- remove_block(lines, "", "*No reviews yet.*")
  lines <- remove_block(lines, "### Step 1: Run the example tool", "This protocol exists only to exercise `scripts/validate-protocol.R`. It is not a real method.")
  lines <- insert_after(lines, "### Step 1: Run the example tool", c("### Step 1: Run the atomic protocol", "Execute `example-atomic`."))
  lines <- remove_block(lines, "A minimal conforming protocol, exercising two releases, a reviewed older version, an unreviewed", "current version, and a reviewer with and without an ORCID.")
  lines <- insert_after(lines, "A minimal conforming protocol, exercising two releases, a reviewed older version, an unreviewed", c("Exercises the local-dependency check, which resolves `repository:` against the repository the", "validator is running in."))
  lines <- replace_line(lines, "# Example Protocol", c("# Example Composite Protocol"))
  lines <- remove_block(lines, "type: atomic", "protocols_used: []")
  lines <- insert_after(lines, "type: atomic", c("type: composite", "protocols_used:", "  - name: example-atomic", "    repository: example-org/example-protocols", "    version: 1.0.0"))
  lines <- insert_after(lines, "status: draft", c("protocol_citation: \"10.1000/example-procedure\""))
  lines <- remove_block(lines, "    orcid: 0000-0002-1825-0097", "date: 2026-03-01")
  lines <- insert_after(lines, "    orcid: 0000-0002-1825-0097", c("date: 2026-01-15"))
  lines <- remove_block(lines, "name: example-protocol", "version: 1.1.0")
  lines <- insert_after(lines, "name: example-protocol", c("name: example-composite", "description: A composite protocol whose dependency lives in this same repository.", "version: 1.0.0"))
  files[["example-composite"]] <- lines
  run_case("missing-local-dependency", files, "Dependent protocol 'example-atomic' not found at")
})

# invalid/missing-materials
local({
  files <- list()
  lines <- baseline
  lines <- remove_block(lines, "", "  - `example-tool` (https://example.org/example-tool) — version 1.0.")
  files[["example-protocol"]] <- lines
  run_case("missing-materials", files, "Missing required '## Materials' section")
})

# invalid/missing-protocol-citation
local({
  files <- list()
  lines <- baseline
  lines <- replace_line(lines, "A minimal conforming protocol, exercising two releases, a reviewed older version, an unreviewed", c("A protocol naming its method's origin but no publication describing the procedure, exercising two releases, a reviewed older version, an unreviewed"))
  lines <- remove_line(lines, "protocol_citation: \"10.1000/example-procedure\"")
  lines <- replace_line(lines, "description: A minimal conforming protocol used as a fixture for the validator test suite.", c("description: A protocol naming its method's origin but no publication describing the procedure used as a fixture for the validator test suite."))
  files[["example-protocol"]] <- lines
  run_case("missing-protocol-citation", files, "'protocol_citation' is required")
})

# invalid/missing-section
local({
  files <- list()
  lines <- baseline
  lines <- remove_block(lines, "", "- **Notes:** Read for scientific soundness. The parameters in Step 1 are appropriate.")
  lines <- remove_block(lines, "reviews:", "    status: approved")
  files[["example-protocol"]] <- lines
  run_case("missing-section", files, "Missing required '## History & Reviews' section")
})

# invalid/missing-status-line
local({
  files <- list()
  lines <- baseline
  lines <- remove_line(lines, "- **Status:** `approved`")
  files[["example-protocol"]] <- lines
  run_case("missing-status-line", files, "Review by 'Alan Turing' under version 1.0.0 is missing a '- **Status:**' line")
})

# invalid/missing-steps
local({
  files <- list()
  lines <- baseline
  lines <- remove_block(lines, "## Steps", "")
  files[["example-protocol"]] <- lines
  run_case("missing-steps", files, "Missing required '## Steps' section")
})

# invalid/nested-fence-escape
local({
  files <- list()
  lines <- baseline
  lines <- insert_after(lines, "Run `example-tool --input reads.fastq --output counts.tsv`.", c("````"))
  lines <- insert_after(lines, "", c("```", ""))
  lines <- insert_after(lines, "", c("Example layout:", "", "````markdown"))
  files[["example-protocol"]] <- lines
  run_case("nested-fence-escape", files, "Missing required '## Materials' section")
})

# invalid/non-kebab-name
local({
  files <- list()
  lines <- baseline
  lines <- replace_line(lines, "name: example-protocol", c("name: Example_Protocol"))
  files[["Example_Protocol"]] <- lines
  run_case("non-kebab-name", files, "'name' must be kebab-case")
})

# invalid/non-string-name
local({
  files <- list()
  lines <- baseline
  lines <- replace_line(lines, "name: example-protocol", c("name: 123"))
  files[["123"]] <- lines
  run_case("non-string-name", files, "'name' must be a single string")
})

# invalid/null-name
local({
  files <- list()
  lines <- baseline
  lines <- replace_line(lines, "name: example-protocol", c("name: ~"))
  files[["example-protocol"]] <- lines
  run_case("null-name", files, "'name' must be a single string")
})

# invalid/review-drift
local({
  files <- list()
  lines <- baseline
  lines <- replace_line(lines, "    status: approved", c("    status: changes-requested"))
  lines <- replace_line(lines, "    date: 2026-01-20", c("    date: 2026-01-21"))
  files[["example-protocol"]] <- lines
  run_case("review-drift", files, "disagrees between the markdown block and the frontmatter: status is 'approved' in the section but 'changes-requested' in 'reviews'")
})

# invalid/review-not-in-frontmatter
local({
  files <- list()
  lines <- baseline
  lines <- replace_line(lines, "*No reviews yet.*", c("", "**Review by Marie Curie**", "- **Date:** 2026-03-05", "- **Status:** `approved`", "- **Notes:** Read for scientific soundness."))
  files[["example-protocol"]] <- lines
  run_case("review-not-in-frontmatter", files, "Review block for version 1.1.0, reviewer 'Marie Curie' has no matching entry in the frontmatter 'reviews' array")
})

# invalid/review-not-in-markdown
local({
  files <- list()
  lines <- baseline
  lines <- insert_after(lines, "reviews:", c("  - name: Marie Curie", "    date: 2026-03-05", "    protocol_version: 1.1.0", "    status: approved"))
  files[["example-protocol"]] <- lines
  run_case("review-not-in-markdown", files, "Frontmatter review for version 1.1.0, reviewer 'Marie Curie' has no matching '**Review by ...**' block under that version")
})

# invalid/sections-only-in-code-fence
local({
  files <- list()
  lines <- baseline
  lines <- replace_line(lines, "Run `example-tool --input reads.fastq --output counts.tsv`.", c("```"))
  lines <- insert_after(lines, "", c("A protocol is laid out like this:", "", "```markdown"))
  files[["example-protocol"]] <- lines
  run_case("sections-only-in-code-fence", files, "Missing required '## Materials' section")
})

# invalid/step-heading-outside-steps
local({
  files <- list()
  lines <- baseline
  lines <- remove_block(lines, "", "## Notes")
  lines <- insert_after(lines, "", c("The steps are described below.", "", "## Notes", ""))
  files[["example-protocol"]] <- lines
  run_case("step-heading-outside-steps", files, "'## Steps' contains no '### Step' heading")
})

# invalid/steps-only-in-code-fence
local({
  files <- list()
  lines <- baseline
  lines <- insert_after(lines, "Run `example-tool --input reads.fastq --output counts.tsv`.", c("```"))
  lines <- insert_after(lines, "", c("Example layout:", "", "```markdown"))
  files[["example-protocol"]] <- lines
  run_case("steps-only-in-code-fence", files, "Missing required '## Steps' section")
})

# invalid/steps-without-step-headings
local({
  files <- list()
  lines <- baseline
  lines <- remove_line(lines, "### Step 1: Run the example tool")
  files[["example-protocol"]] <- lines
  run_case("steps-without-step-headings", files, "contains no '### Step' heading")
})

# invalid/template-placeholder-citation
local({
  files <- list()
  lines <- baseline
  lines <- replace_line(lines, "method_origin_citation: \"10.1000/example\"", c("method_origin_citation: \"10.0000/replace-with-a-real-doi\""))
  files[["example-protocol"]] <- lines
  run_case("template-placeholder-citation", files, "is still the template placeholder")
})

# invalid/typo-version-heading
local({
  files <- list()
  lines <- baseline
  lines <- replace_line(lines, "### Version 1.0.0 (2026-01-15)", c("### Verson 1.0.0 (2026-01-15)"))
  files[["example-protocol"]] <- lines
  run_case("typo-version-heading", files, "Malformed version heading '### Verson 1.0.0 (2026-01-15)'; expected '### Version X.Y.Z (YYYY-MM-DD)'")
})

# invalid/unknown-protocol-version
local({
  files <- list()
  lines <- baseline
  lines <- replace_line(lines, "    protocol_version: 1.0.0", c("    protocol_version: 0.9.0"))
  files[["example-protocol"]] <- lines
  run_case("unknown-protocol-version", files, "Review by 'Alan Turing' declares protocol_version '0.9.0', which has no matching entry in '## History & Reviews'")
})

# invalid/version-mismatch
local({
  files <- list()
  lines <- baseline
  lines <- replace_line(lines, "version: 1.1.0", c("version: 1.2.0"))
  files[["example-protocol"]] <- lines
  run_case("version-mismatch", files, "Top entry in '## History & Reviews' is version '1.1.0', but frontmatter declares version '1.2.0'")
})

