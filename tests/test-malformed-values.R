# Property tests for malformed frontmatter values, sourced by tests/run-tests.R.
#
# YAML gives a field whatever shape the author wrote. Every check in the validator needs the same
# question answered — is this one string? — and the one-fixture-per-rule suite only ever asked it
# with well-shaped input. That is how `name: ~`, `name: [a, b]` and `type: [atomic, composite]`
# each reached an `if` of the wrong length in turn and aborted the whole run: one field at a time,
# three review passes apart.
#
# So this asserts a property rather than a message. For every frontmatter field, against every
# shape YAML can produce, the validator must:
#
#   1. exit non-zero — the value is not a conforming one;
#   2. report through the accumulated `[ERROR]` path; and
#   3. not crash. An uncaught R error aborts `sapply()` over every protocol, so one malformed file
#      takes down the report for all the others.
#
# Condition 3 is the one that keeps being violated, and it is invisible to a test that only greps
# for an expected message.

malformed_dir <- file.path(tempdir(), "malformed-values")

# The shapes a YAML scalar field can arrive as, other than the string it should be. Numeric and
# logical are here because `name: 123` is a case the validator has already mishandled once: it
# parses to a number, matches a numerically-named directory, and skipped the pattern check.
bad_values <- list(
  "null"    = "~",
  "list"    = "[alpha, beta]",
  "mapping" = "{value: alpha}",
  "empty"   = '""',
  "numeric" = "123",
  "logical" = "true"
)

# Every scalar frontmatter field the validator reads, and the line in the fixture it replaces.
scalar_fields <- list(
  name            = "name: example-protocol",
  description     = NULL,   # filled in below from the fixture
  version         = NULL,
  date            = NULL,
  status          = "status: draft",
  protocol_citation = 'protocol_citation: "10.1000/example-procedure"',
  type            = "type: atomic",
  method_origin_citation = 'method_origin_citation: "10.1000/example"'
)

template_path <- file.path(fixtures_dir, "valid", "basic", "protocols", "example-protocol", "protocol.md")
template <- readLines(template_path, warn = FALSE)
for (field in names(scalar_fields)) {
  if (is.null(scalar_fields[[field]])) {
    hit <- grep(sprintf("^%s:", field), template, value = TRUE)
    scalar_fields[[field]] <- if (length(hit) > 0) hit[1] else NA_character_
  }
}

for (field in names(scalar_fields)) {
  original <- scalar_fields[[field]]
  if (is.na(original) || !any(template == original)) {
    check(sprintf("malformed %s: fixture line found", field), FALSE,
          sprintf("no line '%s' in the basic fixture; the matrix cannot substitute it", original))
    next
  }
  for (shape in names(bad_values)) {
    dir <- file.path(malformed_dir, paste0(field, "-", shape), "protocols", "example-protocol")
    dir.create(dir, recursive = TRUE, showWarnings = FALSE)
    lines <- template
    lines[lines == original] <- sprintf("%s: %s", field, bad_values[[shape]])
    writeLines(lines, file.path(dir, "protocol.md"))

    result <- run_validator(dirname(dir))
    crashed <- grepl("(^|\n)Error|Execution halted", result$output)
    reported <- grepl("[ERROR]", result$output, fixed = TRUE)

    check(sprintf("malformed %s: %s does not crash the validator", field, shape),
          !crashed, sprintf("uncaught R error:\n%s", result$output))
    check(sprintf("malformed %s: %s is reported and fails", field, shape),
          result$status != 0 && reported,
          sprintf("status %d, output:\n%s", result$status, result$output))
  }
}

# The container fields. A scalar matrix misses these entirely, and they are where the same bug
# reappeared one level up: the entry is dereferenced with `$`, which is an error rather than NULL
# on an atomic value, so `protocols_used: [foo]` aborted the run after the scalar fields were
# hardened. Each case replaces a whole block rather than one line.
container_cases <- list(
  list(name = "authors scalar entry",
       from = "^authors:$", to = "^reviews:$",
       lines = "authors: [Ada Lovelace]"),
  list(name = "authors non-scalar name",
       from = "^authors:$", to = "^reviews:$",
       lines = c("authors:", "  - name: [Ada, Lovelace]")),
  list(name = "authors null",
       from = "^authors:$", to = "^reviews:$",
       lines = "authors: ~"),
  list(name = "authors mapping",
       from = "^authors:$", to = "^reviews:$",
       lines = "authors: {name: Ada Lovelace}"),
  list(name = "protocols_used scalar entry",
       from = "^protocols_used: \\[\\]$", to = NULL,
       lines = "protocols_used: [some-protocol]"),
  list(name = "protocols_used scalar",
       from = "^protocols_used: \\[\\]$", to = NULL,
       lines = "protocols_used: some-protocol"),
  list(name = "protocols_used entry missing fields",
       from = "^protocols_used: \\[\\]$", to = NULL,
       lines = c("protocols_used:", "  - name: other-protocol")),
  list(name = "reviews scalar entry",
       from = "^reviews:$", to = "^date:$|^date: ",
       lines = "reviews: [looks fine]"),
  list(name = "reviews mapping",
       from = "^reviews:$", to = "^date:$|^date: ",
       lines = "reviews: {grace: {name: Grace Hopper}}"),
  list(name = "authors mapping instead of sequence",
       from = "^authors:$", to = "^reviews:$",
       lines = "authors: {ada: {name: Ada Lovelace}}"),
  list(name = "protocols_used mapping instead of sequence",
       from = "^protocols_used: \\[\\]$", to = NULL,
       lines = "protocols_used: {other: {name: other-protocol}}")
)

# A review entry is an object whose own fields are then coerced and tested. Guarding the entry but
# not its fields is the same bug one level deeper: a two-element `status` or `date` reached a
# length-sensitive `if` inside validate_history() and aborted the run, after the entry-level guard
# was already in place.
review_field_shapes <- list(
  name             = "[Grace, Hopper]",
  date             = "[2026-02-01, 2026-02-02]",
  protocol_version = "[1.0.0, 1.1.0]",
  status           = "[approved, deprecated]",
  orcid            = "[0000-0001-5109-3700, 0000-0002-1825-0097]"
)
for (field in names(review_field_shapes)) {
  container_cases <- c(container_cases, list(list(
    name = paste("review", field, "non-scalar"),
    from = "^reviews:$", to = "^date:$|^date: ",
    lines = c("reviews:",
              "  - name: Grace Hopper",
              "    date: 2026-02-01",
              "    protocol_version: 1.0.0",
              "    status: approved",
              sprintf("    %s: %s", field, review_field_shapes[[field]]))
  )))
}

for (case in container_cases) {
  start <- grep(case$from, template)
  if (length(start) != 1) {
    check(sprintf("malformed %s: fixture block found", case$name), FALSE,
          sprintf("pattern '%s' matched %d lines", case$from, length(start)))
    next
  }
  stop_at <- if (is.null(case$to)) start else {
    after <- grep(case$to, template)
    after <- after[after > start]
    if (length(after) == 0) length(template) else after[1] - 1
  }
  dir <- file.path(malformed_dir, gsub("[^a-z0-9]+", "-", tolower(case$name)),
                   "protocols", "example-protocol")
  dir.create(dir, recursive = TRUE, showWarnings = FALSE)
  lines <- c(template[seq_len(start - 1)], case$lines,
             if (stop_at < length(template)) template[(stop_at + 1):length(template)])
  writeLines(lines, file.path(dir, "protocol.md"))

  result <- run_validator(dirname(dir))
  check(sprintf("malformed %s: does not crash the validator", case$name),
        !grepl("(^|\n)Error|Execution halted", result$output),
        sprintf("uncaught R error:\n%s", result$output))
  check(sprintf("malformed %s: is reported and fails", case$name),
        result$status != 0 && grepl("[ERROR]", result$output, fixed = TRUE),
        sprintf("status %d, output:\n%s", result$status, result$output))
}

# An author ORCID is optional, so it is not in the scalar matrix, but a malformed one must behave
# the same way rather than reaching grepl() as a list.
for (shape in c("list", "mapping")) {
  dir <- file.path(malformed_dir, paste0("author-orcid-", shape), "protocols", "example-protocol")
  dir.create(dir, recursive = TRUE, showWarnings = FALSE)
  lines <- template
  lines[grepl("^    orcid: 0000-0002-1825-0097$", lines)] <-
    sprintf("    orcid: %s", bad_values[[shape]])
  writeLines(lines, file.path(dir, "protocol.md"))

  result <- run_validator(dirname(dir))
  check(sprintf("malformed author orcid: %s does not crash the validator", shape),
        !grepl("(^|\n)Error|Execution halted", result$output),
        sprintf("uncaught R error:\n%s", result$output))
  check(sprintf("malformed author orcid: %s is reported and fails", shape),
        result$status != 0 && grepl("[ERROR]", result$output, fixed = TRUE),
        sprintf("status %d, output:\n%s", result$status, result$output))
}
