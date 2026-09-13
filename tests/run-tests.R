#!/usr/bin/env Rscript

# Usage: Rscript tests/run-tests.R
#
# The whole test suite. Three parts:
#
#   1. scripts/validate-protocol.R against every fixture under tests/fixtures/, and against the
#      starter protocol in template/, which new content repositories copy:
#
#        tests/fixtures/valid/<case>/protocols/<name>/protocol.md    must pass (exit 0)
#        tests/fixtures/invalid/<case>/protocols/<name>/protocol.md  must fail (exit 1) AND print
#                                                                    the message in expected.txt
#
#      To add a case, create the directory and (for an invalid case) its expected.txt; nothing here
#      needs editing.
#
#   2. tests/test-repo-utils.R  — unit tests for the repository and ref detection helpers.
#   3. tests/test-generator.R   — the index generator's output and its refusals.
#   4. tests/test-malformed-values.R — every frontmatter field against every shape YAML can
#      produce, asserting the validator reports rather than crashes.

tests_dir <- local({
  args <- commandArgs(trailingOnly = FALSE)
  file_arg <- grep("^--file=", args, value = TRUE)
  if (length(file_arg) > 0) dirname(sub("^--file=", "", file_arg[1])) else "tests"
})
validator <- normalizePath(file.path(tests_dir, "..", "scripts", "validate-protocol.R"),
                           mustWork = TRUE)
fixtures_dir <- file.path(tests_dir, "fixtures")

# Fixtures declare this as their repository, so the local 'protocols_used' dependency check
# resolves identically here and in CI, where GITHUB_REPOSITORY names the real repository.
fixture_repository <- "example-org/example-protocols"

run_validator <- function(protocols_path) {
  output <- suppressWarnings(system2(
    "Rscript", c(shQuote(validator), shQuote(protocols_path)),
    stdout = TRUE, stderr = TRUE,
    env = paste0("GITHUB_REPOSITORY=", fixture_repository)
  ))
  status <- attr(output, "status")
  list(status = if (is.null(status)) 0L else as.integer(status),
       output = paste(output, collapse = "\n"))
}

cases <- function(kind) {
  dir <- file.path(fixtures_dir, kind)
  sort(list.dirs(dir, recursive = FALSE, full.names = FALSE))
}

failures <- character(0)
passed <- 0L

# Assertion helper for the unit tests sourced at the end, which report into the same tally.
check <- function(label, ok, detail = NULL) {
  if (isTRUE(ok)) {
    cat(sprintf("  [PASS] %s\n", label))
    passed <<- passed + 1L
  } else {
    cat(sprintf("  [FAIL] %s%s\n", label,
                if (is.null(detail)) "" else paste0("\n           ", detail)))
    failures <<- c(failures, label)
  }
}

source(file.path(tests_dir, "test-schema.R"))

# The starter protocol a new content repository copies must conform in every respect but one: its
# 'method_origin_citation' is a placeholder, and the validator now rejects that exact string. So the
# template is asserted to fail with precisely that error and no other. A new repository's first CI
# run is therefore red until the adopter writes a real citation, which is the one thing the template
# cannot do for them — and pinning the message still catches a template that has otherwise drifted
# from the standard, which is what this check was always for.
template_protocols <- file.path(tests_dir, "..", "template", "protocols")
# Names the field, not just the placeholder text: filtering on the placeholder alone would silently
# accept a second field carrying the same value, which is how the starter briefly failed twice.
template_expected <- "'protocol_citation' is still the template placeholder"
if (!dir.exists(template_protocols)) {
  cat("  [FAIL] template: no template/protocols directory\n")
  failures <- c(failures, "template")
} else {
  result <- run_validator(template_protocols)
  output_lines <- strsplit(result$output, "\n")[[1]]
  other_errors <- grep("\\[ERROR\\]", output_lines, value = TRUE)
  other_errors <- other_errors[!grepl(template_expected, other_errors, fixed = TRUE)]
  # An uncaught R error carries no [ERROR] prefix, so counting prefixed lines alone would report a
  # pass for a validator that emitted the placeholder message and then crashed.
  crashes <- grep("^Error|Execution halted", output_lines, value = TRUE)
  if (result$status == 0) {
    cat("  [FAIL] template/protocols: expected the placeholder citation to be rejected, but it passed\n")
    failures <- c(failures, "template")
  } else if (!grepl(template_expected, result$output, fixed = TRUE)) {
    # Absence of other errors is not evidence of the right one: a crash before any [ERROR] line
    # also exits nonzero and leaves 'other_errors' empty.
    cat(sprintf("  [FAIL] template/protocols: failed, but not on its placeholder citation\n%s\n",
                result$output))
    failures <- c(failures, "template")
  } else if (length(other_errors) > 0 || length(crashes) > 0) {
    cat(sprintf("  [FAIL] template/protocols: the starter protocol does not conform, beyond its placeholder citation\n%s\n",
                paste(c(other_errors, crashes), collapse = "\n")))
    failures <- c(failures, "template")
  } else {
    cat("  [PASS] template/protocols fails only on its placeholder citation\n")
    passed <- passed + 1L
  }
}

# A run that validated nothing must not report success. As a published action the likeliest cause is
# a mistyped protocols path, and a green check would claim the protocols are fine when none were
# read.
empty_dir <- file.path(tempdir(), "empty-protocols")
dir.create(empty_dir, showWarnings = FALSE, recursive = TRUE)
empty_runs <- list(
  list(label = "missing protocols directory", path = file.path(tempdir(), "no-such-directory")),
  list(label = "protocols directory holding no protocol.md", path = empty_dir)
)
for (run in empty_runs) {
  result <- run_validator(run$path)
  if (result$status == 0) {
    cat(sprintf("  [FAIL] empty/%s: the validator passed without validating anything\n", run$label))
    failures <- c(failures, sprintf("empty/%s", run$label))
  } else {
    cat(sprintf("  [PASS] empty/%s\n", run$label))
    passed <- passed + 1L
  }
}

source(file.path(tests_dir, "test-malformed-values.R"))
source(file.path(tests_dir, "test-repo-utils.R"))
source(file.path(tests_dir, "test-generator.R"))

cat("\n")
if (length(failures) > 0) {
  cat(sprintf("%d passed, %d FAILED: %s\n", passed, length(failures),
              paste(failures, collapse = ", ")))
  quit(status = 1)
}
cat(sprintf("All %d tests passed.\n", passed))
