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

# valid/bare-step-heading
local({
  files <- list()
  lines <- baseline
  lines <- c(
    if (41 > 0) lines[1:41] else character(0),
    c("### Step"),
    if (42 < length(lines)) lines[(42+1):length(lines)] else character(0)
  )
  files[["example-protocol"]] <- lines
  run_case("bare-step-heading", files)
})

# valid/composite
local({
  files <- list()
  lines <- baseline
  lines <- c(
    if (65 > 0) lines[1:65] else character(0),
    c("*No reviews yet.*"),
    if (75 < length(lines)) lines[(75+1):length(lines)] else character(0)
  )
  lines <- c(
    if (50 > 0) lines[1:50] else character(0),
    character(0),
    if (58 < length(lines)) lines[(58+1):length(lines)] else character(0)
  )
  lines <- c(
    if (42 > 0) lines[1:42] else character(0),
    c("Run `example-tool --input reads.fastq`."),
    if (47 < length(lines)) lines[(47+1):length(lines)] else character(0)
  )
  lines <- c(
    if (31 > 0) lines[1:31] else character(0),
    c("The dependency target for `example-composite`."),
    if (33 < length(lines)) lines[(33+1):length(lines)] else character(0)
  )
  lines <- c(
    if (29 > 0) lines[1:29] else character(0),
    c("# Example Atomic Protocol"),
    if (30 < length(lines)) lines[(30+1):length(lines)] else character(0)
  )
  lines <- c(
    if (6 > 0) lines[1:6] else character(0),
    c("date: 2026-01-15"),
    if (18 < length(lines)) lines[(18+1):length(lines)] else character(0)
  )
  lines <- c(
    if (1 > 0) lines[1:1] else character(0),
    c("name: example-atomic", "description: An atomic protocol that a composite protocol in the same repository depends on.", "version: 1.0.0"),
    if (4 < length(lines)) lines[(4+1):length(lines)] else character(0)
  )
  files[["example-atomic"]] <- lines
  lines <- baseline
  lines <- c(
    if (65 > 0) lines[1:65] else character(0),
    c("*No reviews yet.*"),
    if (75 < length(lines)) lines[(75+1):length(lines)] else character(0)
  )
  lines <- c(
    if (50 > 0) lines[1:50] else character(0),
    character(0),
    if (58 < length(lines)) lines[(58+1):length(lines)] else character(0)
  )
  lines <- c(
    if (41 > 0) lines[1:41] else character(0),
    c("### Step 1: Run the atomic protocol", "Execute `example-atomic`."),
    if (47 < length(lines)) lines[(47+1):length(lines)] else character(0)
  )
  lines <- c(
    if (31 > 0) lines[1:31] else character(0),
    c("Exercises the local-dependency check, which resolves `repository:` against the repository the", "validator is running in."),
    if (33 < length(lines)) lines[(33+1):length(lines)] else character(0)
  )
  lines <- c(
    if (29 > 0) lines[1:29] else character(0),
    c("# Example Composite Protocol"),
    if (30 < length(lines)) lines[(30+1):length(lines)] else character(0)
  )
  lines <- c(
    if (20 > 0) lines[1:20] else character(0),
    c("type: composite", "protocols_used:", "  - name: example-atomic", "    repository: example-org/example-protocols", "    version: 1.0.0"),
    if (24 < length(lines)) lines[(24+1):length(lines)] else character(0)
  )
  lines <- c(
    if (19 > 0) lines[1:19] else character(0),
    c("protocol_citation: \"10.1000/example-procedure\""),
    if (19 < length(lines)) lines[(19+1):length(lines)] else character(0)
  )
  lines <- c(
    if (6 > 0) lines[1:6] else character(0),
    c("date: 2026-01-15"),
    if (18 < length(lines)) lines[(18+1):length(lines)] else character(0)
  )
  lines <- c(
    if (1 > 0) lines[1:1] else character(0),
    c("name: example-composite", "description: A composite protocol whose dependency lives in this same repository.", "version: 1.0.0"),
    if (4 < length(lines)) lines[(4+1):length(lines)] else character(0)
  )
  files[["example-composite"]] <- lines
  run_case("composite", files)
})

# valid/composite-with-method-citation
local({
  files <- list()
  lines <- baseline
  lines <- c(
    if (65 > 0) lines[1:65] else character(0),
    c("*No reviews yet.*"),
    if (75 < length(lines)) lines[(75+1):length(lines)] else character(0)
  )
  lines <- c(
    if (50 > 0) lines[1:50] else character(0),
    character(0),
    if (58 < length(lines)) lines[(58+1):length(lines)] else character(0)
  )
  lines <- c(
    if (42 > 0) lines[1:42] else character(0),
    c("Run `example-tool --input reads.fastq`."),
    if (47 < length(lines)) lines[(47+1):length(lines)] else character(0)
  )
  lines <- c(
    if (31 > 0) lines[1:31] else character(0),
    c("The dependency target for `example-composite`."),
    if (33 < length(lines)) lines[(33+1):length(lines)] else character(0)
  )
  lines <- c(
    if (29 > 0) lines[1:29] else character(0),
    c("# Example Atomic Protocol"),
    if (30 < length(lines)) lines[(30+1):length(lines)] else character(0)
  )
  lines <- c(
    if (6 > 0) lines[1:6] else character(0),
    c("date: 2026-01-15"),
    if (18 < length(lines)) lines[(18+1):length(lines)] else character(0)
  )
  lines <- c(
    if (1 > 0) lines[1:1] else character(0),
    c("name: example-atomic", "description: An atomic protocol that a composite protocol in the same repository depends on.", "version: 1.0.0"),
    if (4 < length(lines)) lines[(4+1):length(lines)] else character(0)
  )
  files[["example-atomic"]] <- lines
  lines <- baseline
  lines <- c(
    if (65 > 0) lines[1:65] else character(0),
    c("*No reviews yet.*"),
    if (75 < length(lines)) lines[(75+1):length(lines)] else character(0)
  )
  lines <- c(
    if (50 > 0) lines[1:50] else character(0),
    character(0),
    if (58 < length(lines)) lines[(58+1):length(lines)] else character(0)
  )
  lines <- c(
    if (41 > 0) lines[1:41] else character(0),
    c("### Step 1: Run the atomic protocol", "Execute `example-atomic`."),
    if (47 < length(lines)) lines[(47+1):length(lines)] else character(0)
  )
  lines <- c(
    if (31 > 0) lines[1:31] else character(0),
    c("Exercises the local-dependency check, which resolves `repository:` against the repository the", "validator is running in."),
    if (33 < length(lines)) lines[(33+1):length(lines)] else character(0)
  )
  lines <- c(
    if (29 > 0) lines[1:29] else character(0),
    c("# Example Composite Protocol"),
    if (30 < length(lines)) lines[(30+1):length(lines)] else character(0)
  )
  lines <- c(
    if (23 > 0) lines[1:23] else character(0),
    c("protocols_used:", "  - name: example-atomic", "    repository: example-org/example-protocols", "    version: 1.0.0"),
    if (24 < length(lines)) lines[(24+1):length(lines)] else character(0)
  )
  lines <- c(
    if (20 > 0) lines[1:20] else character(0),
    c("type: composite", "# A sequence of methods can itself be published as a method; this is permitted.", "method_origin_citation: \"10.1000/example-pipeline\""),
    if (22 < length(lines)) lines[(22+1):length(lines)] else character(0)
  )
  lines <- c(
    if (6 > 0) lines[1:6] else character(0),
    c("date: 2026-01-15"),
    if (18 < length(lines)) lines[(18+1):length(lines)] else character(0)
  )
  lines <- c(
    if (1 > 0) lines[1:1] else character(0),
    c("name: example-composite", "description: A composite protocol whose dependency lives in this same repository.", "version: 1.0.0"),
    if (4 < length(lines)) lines[(4+1):length(lines)] else character(0)
  )
  files[["example-composite"]] <- lines
  run_case("composite-with-method-citation", files)
})

# valid/first-release
local({
  files <- list()
  lines <- baseline
  lines <- c(
    if (65 > 0) lines[1:65] else character(0),
    c("*No reviews yet.*"),
    if (75 < length(lines)) lines[(75+1):length(lines)] else character(0)
  )
  lines <- c(
    if (50 > 0) lines[1:50] else character(0),
    character(0),
    if (58 < length(lines)) lines[(58+1):length(lines)] else character(0)
  )
  lines <- c(
    if (42 > 0) lines[1:42] else character(0),
    c("Run `example-tool --input reads.fastq`."),
    if (47 < length(lines)) lines[(47+1):length(lines)] else character(0)
  )
  lines <- c(
    if (31 > 0) lines[1:31] else character(0),
    c("The pre-review case: the section is still required, only its `#### Reviews` body is a placeholder,", "and the optional `reviews:` frontmatter field is omitted entirely."),
    if (33 < length(lines)) lines[(33+1):length(lines)] else character(0)
  )
  lines <- c(
    if (29 > 0) lines[1:29] else character(0),
    c("# Example First Release"),
    if (30 < length(lines)) lines[(30+1):length(lines)] else character(0)
  )
  lines <- c(
    if (6 > 0) lines[1:6] else character(0),
    c("date: 2026-01-15"),
    if (18 < length(lines)) lines[(18+1):length(lines)] else character(0)
  )
  lines <- c(
    if (1 > 0) lines[1:1] else character(0),
    c("name: example-first-release", "description: A first release that nobody has reviewed yet, with no 'reviews' frontmatter field.", "version: 1.0.0"),
    if (4 < length(lines)) lines[(4+1):length(lines)] else character(0)
  )
  files[["example-first-release"]] <- lines
  run_case("first-release", files)
})

# valid/pmid-citation
local({
  files <- list()
  lines <- baseline
  lines <- c(
    if (21 > 0) lines[1:21] else character(0),
    c("method_origin_citation: \"PMID:12345678\""),
    if (22 < length(lines)) lines[(22+1):length(lines)] else character(0)
  )
  files[["example-protocol"]] <- lines
  run_case("pmid-citation", files)
})

# valid/self-cited-first-definition
local({
  files <- list()
  lines <- baseline
  lines <- c(
    if (31 > 0) lines[1:31] else character(0),
    c("A first definition: protocol_citation repeats collection_doi, and no method origin is claimed, exercising two releases, a reviewed older version, an unreviewed"),
    if (32 < length(lines)) lines[(32+1):length(lines)] else character(0)
  )
  lines <- c(
    if (21 > 0) lines[1:21] else character(0),
    c("protocol_citation: \"10.5281/zenodo.9999999\""),
    if (23 < length(lines)) lines[(23+1):length(lines)] else character(0)
  )
  lines <- c(
    if (20 > 0) lines[1:20] else character(0),
    c("collection_doi: \"10.5281/zenodo.9999999\""),
    if (20 < length(lines)) lines[(20+1):length(lines)] else character(0)
  )
  lines <- c(
    if (2 > 0) lines[1:2] else character(0),
    c("description: A first definition — protocol_citation repeats collection_doi, and no method origin is claimed."),
    if (3 < length(lines)) lines[(3+1):length(lines)] else character(0)
  )
  files[["example-protocol"]] <- lines
  run_case("self-cited-first-definition", files)
})

# valid/stable-status
local({
  files <- list()
  lines <- baseline
  lines <- c(
    if (31 > 0) lines[1:31] else character(0),
    c("A minimal conforming protocol at status `stable`, exercising two releases, a reviewed older version, an unreviewed"),
    if (32 < length(lines)) lines[(32+1):length(lines)] else character(0)
  )
  lines <- c(
    if (18 > 0) lines[1:18] else character(0),
    c("status: stable"),
    if (19 < length(lines)) lines[(19+1):length(lines)] else character(0)
  )
  files[["example-protocol"]] <- lines
  run_case("stable-status", files)
})

# invalid/ascending-order
local({
  files <- list()
  lines <- baseline
  lines <- c(
    if (75 > 0) lines[1:75] else character(0),
    c("", "### Version 1.1.0 (2026-03-01)", "", "#### Changes", "- Made the output path of Step 1 explicit.", "", "#### Reviews", "*No reviews yet.*"),
    if (75 < length(lines)) lines[(75+1):length(lines)] else character(0)
  )
  lines <- c(
    if (51 > 0) lines[1:51] else character(0),
    character(0),
    if (59 < length(lines)) lines[(59+1):length(lines)] else character(0)
  )
  lines <- c(
    if (17 > 0) lines[1:17] else character(0),
    c("date: 2026-01-15"),
    if (18 < length(lines)) lines[(18+1):length(lines)] else character(0)
  )
  lines <- c(
    if (3 > 0) lines[1:3] else character(0),
    c("version: 1.0.0"),
    if (4 < length(lines)) lines[(4+1):length(lines)] else character(0)
  )
  files[["example-protocol"]] <- lines
  run_case("ascending-order", files, "Version entries must be in descending order (newest at the top), but '1.0.0' appears above '1.1.0'")
})

# invalid/atomic-with-dependencies
local({
  files <- list()
  lines <- baseline
  lines <- c(
    if (23 > 0) lines[1:23] else character(0),
    c("protocols_used:", "  - name: other-protocol", "    repository: example/other", "    version: 1.0.0"),
    if (24 < length(lines)) lines[(24+1):length(lines)] else character(0)
  )
  files[["example-protocol"]] <- lines
  run_case("atomic-with-dependencies", files, "'type: atomic' cannot declare 'protocols_used'")
})

# invalid/composite-without-dependencies
local({
  files <- list()
  lines <- baseline
  lines <- c(
    if (20 > 0) lines[1:20] else character(0),
    c("type: composite"),
    if (21 < length(lines)) lines[(21+1):length(lines)] else character(0)
  )
  files[["example-protocol"]] <- lines
  run_case("composite-without-dependencies", files, "'type: composite' requires a non-empty 'protocols_used'")
})

# invalid/date-mismatch
local({
  files <- list()
  lines <- baseline
  lines <- c(
    if (17 > 0) lines[1:17] else character(0),
    c("date: 2026-03-02"),
    if (18 < length(lines)) lines[(18+1):length(lines)] else character(0)
  )
  files[["example-protocol"]] <- lines
  run_case("date-mismatch", files, "Top entry in '## History & Reviews' is dated '2026-03-01', but frontmatter declares date '2026-03-02'")
})

# invalid/deprecated-citations-field
local({
  files <- list()
  lines <- baseline
  lines <- c(
    if (23 > 0) lines[1:23] else character(0),
    c("citations: ~"),
    if (23 < length(lines)) lines[(23+1):length(lines)] else character(0)
  )
  files[["example-protocol"]] <- lines
  run_case("deprecated-citations-field", files, "Deprecated 'citations' field found")
})

# invalid/draft-unreviewed-status
local({
  files <- list()
  lines <- baseline
  lines <- c(
    if (73 > 0) lines[1:73] else character(0),
    c("- **Status:** `draft-unreviewed`"),
    if (74 < length(lines)) lines[(74+1):length(lines)] else character(0)
  )
  lines <- c(
    if (16 > 0) lines[1:16] else character(0),
    c("    status: draft-unreviewed"),
    if (17 < length(lines)) lines[(17+1):length(lines)] else character(0)
  )
  files[["example-protocol"]] <- lines
  run_case("draft-unreviewed-status", files, "Review by 'Alan Turing' has invalid status 'draft-unreviewed'")
})

# invalid/empty-changes
local({
  files <- list()
  lines <- baseline
  lines <- c(
    if (54 > 0) lines[1:54] else character(0),
    character(0),
    if (55 < length(lines)) lines[(55+1):length(lines)] else character(0)
  )
  files[["example-protocol"]] <- lines
  run_case("empty-changes", files, "Version 1.1.0 has an empty '#### Changes' subsection")
})

# invalid/fence-close-with-suffix
local({
  files <- list()
  lines <- baseline
  lines <- c(
    if (43 > 0) lines[1:43] else character(0),
    c("```"),
    if (43 < length(lines)) lines[(43+1):length(lines)] else character(0)
  )
  lines <- c(
    if (39 > 0) lines[1:39] else character(0),
    c("```not-a-close", ""),
    if (39 < length(lines)) lines[(39+1):length(lines)] else character(0)
  )
  lines <- c(
    if (34 > 0) lines[1:34] else character(0),
    c("Example layout:", "", "```markdown"),
    if (34 < length(lines)) lines[(34+1):length(lines)] else character(0)
  )
  files[["example-protocol"]] <- lines
  run_case("fence-close-with-suffix", files, "Missing required '## Steps' section")
})

# invalid/free-text-method-citation
local({
  files <- list()
  lines <- baseline
  lines <- c(
    if (21 > 0) lines[1:21] else character(0),
    c("method_origin_citation: \"see the HUMAnN 4 paper\""),
    if (22 < length(lines)) lines[(22+1):length(lines)] else character(0)
  )
  files[["example-protocol"]] <- lines
  run_case("free-text-method-citation", files, "must be a DOI ('10.1000/xyz') or a PubMed ID")
})

# invalid/invalid-protocol-status
local({
  files <- list()
  lines <- baseline
  lines <- c(
    if (18 > 0) lines[1:18] else character(0),
    c("status: banana"),
    if (19 < length(lines)) lines[(19+1):length(lines)] else character(0)
  )
  files[["example-protocol"]] <- lines
  run_case("invalid-protocol-status", files, "'status' must be one of 'draft', 'stable', 'deprecated', 'superseded'")
})

# invalid/invalid-status
local({
  files <- list()
  lines <- baseline
  lines <- c(
    if (73 > 0) lines[1:73] else character(0),
    c("- **Status:** `looks-good`"),
    if (74 < length(lines)) lines[(74+1):length(lines)] else character(0)
  )
  lines <- c(
    if (16 > 0) lines[1:16] else character(0),
    c("    status: looks-good"),
    if (17 < length(lines)) lines[(17+1):length(lines)] else character(0)
  )
  files[["example-protocol"]] <- lines
  run_case("invalid-status", files, "Review by 'Alan Turing' has invalid status 'looks-good'")
})

# invalid/legacy-field-name
local({
  files <- list()
  lines <- baseline
  lines <- c(
    if (21 > 0) lines[1:21] else character(0),
    c("citation: \"10.1000/example\""),
    if (23 < length(lines)) lines[(23+1):length(lines)] else character(0)
  )
  lines <- c(
    if (19 > 0) lines[1:19] else character(0),
    c("protocol_citation: \"10.1000/example-procedure\""),
    if (19 < length(lines)) lines[(19+1):length(lines)] else character(0)
  )
  files[["example-protocol"]] <- lines
  run_case("legacy-field-name", files, "Field 'citation' was renamed to 'method_origin_citation' (see PROTOCOL_STANDARD.md) in 'example-protocol'")
})

# invalid/legacy-field-null-placeholder
local({
  files <- list()
  lines <- baseline
  lines <- c(
    if (23 > 0) lines[1:23] else character(0),
    c("repository_doi: ~"),
    if (23 < length(lines)) lines[(23+1):length(lines)] else character(0)
  )
  files[["example-protocol"]] <- lines
  run_case("legacy-field-null-placeholder", files, "Field 'repository_doi' was renamed to 'collection_doi' (see PROTOCOL_STANDARD.md) in 'example-protocol'")
})

# invalid/list-valued-type
local({
  files <- list()
  lines <- baseline
  lines <- c(
    if (20 > 0) lines[1:20] else character(0),
    c("type: [atomic, composite]"),
    if (21 < length(lines)) lines[(21+1):length(lines)] else character(0)
  )
  files[["example-protocol"]] <- lines
  run_case("list-valued-type", files, "'type' must be either 'atomic' or 'composite'")
})

# invalid/malformed-author-orcid
local({
  files <- list()
  lines <- baseline
  lines <- c(
    if (6 > 0) lines[1:6] else character(0),
    c("    orcid: 0000-0002-1825"),
    if (7 < length(lines)) lines[(7+1):length(lines)] else character(0)
  )
  files[["example-protocol"]] <- lines
  run_case("malformed-author-orcid", files, "has a malformed ORCID")
})

# invalid/malformed-orcid
local({
  files <- list()
  lines <- baseline
  lines <- c(
    if (66 > 0) lines[1:66] else character(0),
    c("**Review by Grace Hopper ([0000-0001-5109-370](https://orcid.org/0000-0001-5109-370))**"),
    if (67 < length(lines)) lines[(67+1):length(lines)] else character(0)
  )
  lines <- c(
    if (9 > 0) lines[1:9] else character(0),
    c("    orcid: 0000-0001-5109-370"),
    if (10 < length(lines)) lines[(10+1):length(lines)] else character(0)
  )
  files[["example-protocol"]] <- lines
  run_case("malformed-orcid", files, "Review by 'Grace Hopper' has a malformed 'orcid': 0000-0001-5109-370")
})

# invalid/missing-local-dependency
local({
  files <- list()
  lines <- baseline
  lines <- c(
    if (65 > 0) lines[1:65] else character(0),
    c("*No reviews yet.*"),
    if (75 < length(lines)) lines[(75+1):length(lines)] else character(0)
  )
  lines <- c(
    if (50 > 0) lines[1:50] else character(0),
    character(0),
    if (58 < length(lines)) lines[(58+1):length(lines)] else character(0)
  )
  lines <- c(
    if (41 > 0) lines[1:41] else character(0),
    c("### Step 1: Run the atomic protocol", "Execute `example-atomic`."),
    if (47 < length(lines)) lines[(47+1):length(lines)] else character(0)
  )
  lines <- c(
    if (31 > 0) lines[1:31] else character(0),
    c("Exercises the local-dependency check, which resolves `repository:` against the repository the", "validator is running in."),
    if (33 < length(lines)) lines[(33+1):length(lines)] else character(0)
  )
  lines <- c(
    if (29 > 0) lines[1:29] else character(0),
    c("# Example Composite Protocol"),
    if (30 < length(lines)) lines[(30+1):length(lines)] else character(0)
  )
  lines <- c(
    if (20 > 0) lines[1:20] else character(0),
    c("type: composite", "protocols_used:", "  - name: example-atomic", "    repository: example-org/example-protocols", "    version: 1.0.0"),
    if (24 < length(lines)) lines[(24+1):length(lines)] else character(0)
  )
  lines <- c(
    if (19 > 0) lines[1:19] else character(0),
    c("protocol_citation: \"10.1000/example-procedure\""),
    if (19 < length(lines)) lines[(19+1):length(lines)] else character(0)
  )
  lines <- c(
    if (6 > 0) lines[1:6] else character(0),
    c("date: 2026-01-15"),
    if (18 < length(lines)) lines[(18+1):length(lines)] else character(0)
  )
  lines <- c(
    if (1 > 0) lines[1:1] else character(0),
    c("name: example-composite", "description: A composite protocol whose dependency lives in this same repository.", "version: 1.0.0"),
    if (4 < length(lines)) lines[(4+1):length(lines)] else character(0)
  )
  files[["example-composite"]] <- lines
  run_case("missing-local-dependency", files, "Dependent protocol 'example-atomic' not found at")
})

# invalid/missing-materials
local({
  files <- list()
  lines <- baseline
  lines <- c(
    if (33 > 0) lines[1:33] else character(0),
    character(0),
    if (38 < length(lines)) lines[(38+1):length(lines)] else character(0)
  )
  files[["example-protocol"]] <- lines
  run_case("missing-materials", files, "Missing required '## Materials' section")
})

# invalid/missing-protocol-citation
local({
  files <- list()
  lines <- baseline
  lines <- c(
    if (31 > 0) lines[1:31] else character(0),
    c("A protocol naming its method's origin but no publication describing the procedure, exercising two releases, a reviewed older version, an unreviewed"),
    if (32 < length(lines)) lines[(32+1):length(lines)] else character(0)
  )
  lines <- c(
    if (22 > 0) lines[1:22] else character(0),
    character(0),
    if (23 < length(lines)) lines[(23+1):length(lines)] else character(0)
  )
  lines <- c(
    if (2 > 0) lines[1:2] else character(0),
    c("description: A protocol naming its method's origin but no publication describing the procedure used as a fixture for the validator test suite."),
    if (3 < length(lines)) lines[(3+1):length(lines)] else character(0)
  )
  files[["example-protocol"]] <- lines
  run_case("missing-protocol-citation", files, "'protocol_citation' is required")
})

# invalid/missing-section
local({
  files <- list()
  lines <- baseline
  lines <- c(
    if (47 > 0) lines[1:47] else character(0),
    character(0),
    if (75 < length(lines)) lines[(75+1):length(lines)] else character(0)
  )
  lines <- c(
    if (7 > 0) lines[1:7] else character(0),
    character(0),
    if (17 < length(lines)) lines[(17+1):length(lines)] else character(0)
  )
  files[["example-protocol"]] <- lines
  run_case("missing-section", files, "Missing required '## History & Reviews' section")
})

# invalid/missing-status-line
local({
  files <- list()
  lines <- baseline
  lines <- c(
    if (73 > 0) lines[1:73] else character(0),
    character(0),
    if (74 < length(lines)) lines[(74+1):length(lines)] else character(0)
  )
  files[["example-protocol"]] <- lines
  run_case("missing-status-line", files, "Review by 'Alan Turing' under version 1.0.0 is missing a '- **Status:**' line")
})

# invalid/missing-steps
local({
  files <- list()
  lines <- baseline
  lines <- c(
    if (39 > 0) lines[1:39] else character(0),
    character(0),
    if (44 < length(lines)) lines[(44+1):length(lines)] else character(0)
  )
  files[["example-protocol"]] <- lines
  run_case("missing-steps", files, "Missing required '## Steps' section")
})

# invalid/nested-fence-escape
local({
  files <- list()
  lines <- baseline
  lines <- c(
    if (43 > 0) lines[1:43] else character(0),
    c("````"),
    if (43 < length(lines)) lines[(43+1):length(lines)] else character(0)
  )
  lines <- c(
    if (39 > 0) lines[1:39] else character(0),
    c("```", ""),
    if (39 < length(lines)) lines[(39+1):length(lines)] else character(0)
  )
  lines <- c(
    if (34 > 0) lines[1:34] else character(0),
    c("Example layout:", "", "````markdown"),
    if (34 < length(lines)) lines[(34+1):length(lines)] else character(0)
  )
  files[["example-protocol"]] <- lines
  run_case("nested-fence-escape", files, "Missing required '## Materials' section")
})

# invalid/non-kebab-name
local({
  files <- list()
  lines <- baseline
  lines <- c(
    if (1 > 0) lines[1:1] else character(0),
    c("name: Example_Protocol"),
    if (2 < length(lines)) lines[(2+1):length(lines)] else character(0)
  )
  files[["Example_Protocol"]] <- lines
  run_case("non-kebab-name", files, "'name' must be kebab-case")
})

# invalid/non-string-name
local({
  files <- list()
  lines <- baseline
  lines <- c(
    if (1 > 0) lines[1:1] else character(0),
    c("name: 123"),
    if (2 < length(lines)) lines[(2+1):length(lines)] else character(0)
  )
  files[["123"]] <- lines
  run_case("non-string-name", files, "'name' must be a single string")
})

# invalid/null-name
local({
  files <- list()
  lines <- baseline
  lines <- c(
    if (1 > 0) lines[1:1] else character(0),
    c("name: ~"),
    if (2 < length(lines)) lines[(2+1):length(lines)] else character(0)
  )
  files[["example-protocol"]] <- lines
  run_case("null-name", files, "'name' must be a single string")
})

# invalid/review-drift
local({
  files <- list()
  lines <- baseline
  lines <- c(
    if (16 > 0) lines[1:16] else character(0),
    c("    status: changes-requested"),
    if (17 < length(lines)) lines[(17+1):length(lines)] else character(0)
  )
  lines <- c(
    if (14 > 0) lines[1:14] else character(0),
    c("    date: 2026-01-21"),
    if (15 < length(lines)) lines[(15+1):length(lines)] else character(0)
  )
  files[["example-protocol"]] <- lines
  run_case("review-drift", files, "disagrees between the markdown block and the frontmatter: status is 'approved' in the section but 'changes-requested' in 'reviews'")
})

# invalid/review-not-in-frontmatter
local({
  files <- list()
  lines <- baseline
  lines <- c(
    if (57 > 0) lines[1:57] else character(0),
    c("", "**Review by Marie Curie**", "- **Date:** 2026-03-05", "- **Status:** `approved`", "- **Notes:** Read for scientific soundness."),
    if (58 < length(lines)) lines[(58+1):length(lines)] else character(0)
  )
  files[["example-protocol"]] <- lines
  run_case("review-not-in-frontmatter", files, "Review block for version 1.1.0, reviewer 'Marie Curie' has no matching entry in the frontmatter 'reviews' array")
})

# invalid/review-not-in-markdown
local({
  files <- list()
  lines <- baseline
  lines <- c(
    if (8 > 0) lines[1:8] else character(0),
    c("  - name: Marie Curie", "    date: 2026-03-05", "    protocol_version: 1.1.0", "    status: approved"),
    if (8 < length(lines)) lines[(8+1):length(lines)] else character(0)
  )
  files[["example-protocol"]] <- lines
  run_case("review-not-in-markdown", files, "Frontmatter review for version 1.1.0, reviewer 'Marie Curie' has no matching '**Review by ...**' block under that version")
})

# invalid/sections-only-in-code-fence
local({
  files <- list()
  lines <- baseline
  lines <- c(
    if (42 > 0) lines[1:42] else character(0),
    c("```"),
    if (43 < length(lines)) lines[(43+1):length(lines)] else character(0)
  )
  lines <- c(
    if (34 > 0) lines[1:34] else character(0),
    c("A protocol is laid out like this:", "", "```markdown"),
    if (34 < length(lines)) lines[(34+1):length(lines)] else character(0)
  )
  files[["example-protocol"]] <- lines
  run_case("sections-only-in-code-fence", files, "Missing required '## Materials' section")
})

# invalid/step-heading-outside-steps
local({
  files <- list()
  lines <- baseline
  lines <- c(
    if (43 > 0) lines[1:43] else character(0),
    character(0),
    if (45 < length(lines)) lines[(45+1):length(lines)] else character(0)
  )
  lines <- c(
    if (41 > 0) lines[1:41] else character(0),
    c("The steps are described below.", "", "## Notes", ""),
    if (41 < length(lines)) lines[(41+1):length(lines)] else character(0)
  )
  files[["example-protocol"]] <- lines
  run_case("step-heading-outside-steps", files, "'## Steps' contains no '### Step' heading")
})

# invalid/steps-only-in-code-fence
local({
  files <- list()
  lines <- baseline
  lines <- c(
    if (43 > 0) lines[1:43] else character(0),
    c("```"),
    if (43 < length(lines)) lines[(43+1):length(lines)] else character(0)
  )
  lines <- c(
    if (39 > 0) lines[1:39] else character(0),
    c("Example layout:", "", "```markdown"),
    if (39 < length(lines)) lines[(39+1):length(lines)] else character(0)
  )
  files[["example-protocol"]] <- lines
  run_case("steps-only-in-code-fence", files, "Missing required '## Steps' section")
})

# invalid/steps-without-step-headings
local({
  files <- list()
  lines <- baseline
  lines <- c(
    if (41 > 0) lines[1:41] else character(0),
    character(0),
    if (42 < length(lines)) lines[(42+1):length(lines)] else character(0)
  )
  files[["example-protocol"]] <- lines
  run_case("steps-without-step-headings", files, "contains no '### Step' heading")
})

# invalid/template-placeholder-citation
local({
  files <- list()
  lines <- baseline
  lines <- c(
    if (21 > 0) lines[1:21] else character(0),
    c("method_origin_citation: \"10.0000/replace-with-a-real-doi\""),
    if (22 < length(lines)) lines[(22+1):length(lines)] else character(0)
  )
  files[["example-protocol"]] <- lines
  run_case("template-placeholder-citation", files, "is still the template placeholder")
})

# invalid/typo-version-heading
local({
  files <- list()
  lines <- baseline
  lines <- c(
    if (59 > 0) lines[1:59] else character(0),
    c("### Verson 1.0.0 (2026-01-15)"),
    if (60 < length(lines)) lines[(60+1):length(lines)] else character(0)
  )
  files[["example-protocol"]] <- lines
  run_case("typo-version-heading", files, "Malformed version heading '### Verson 1.0.0 (2026-01-15)'; expected '### Version X.Y.Z (YYYY-MM-DD)'")
})

# invalid/unknown-protocol-version
local({
  files <- list()
  lines <- baseline
  lines <- c(
    if (15 > 0) lines[1:15] else character(0),
    c("    protocol_version: 0.9.0"),
    if (16 < length(lines)) lines[(16+1):length(lines)] else character(0)
  )
  files[["example-protocol"]] <- lines
  run_case("unknown-protocol-version", files, "Review by 'Alan Turing' declares protocol_version '0.9.0', which has no matching entry in '## History & Reviews'")
})

# invalid/version-mismatch
local({
  files <- list()
  lines <- baseline
  lines <- c(
    if (3 > 0) lines[1:3] else character(0),
    c("version: 1.2.0"),
    if (4 < length(lines)) lines[(4+1):length(lines)] else character(0)
  )
  files[["example-protocol"]] <- lines
  run_case("version-mismatch", files, "Top entry in '## History & Reviews' is version '1.1.0', but frontmatter declares version '1.2.0'")
})

