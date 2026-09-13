# Tests for scripts/generate-protocols-yaml.R, sourced by tests/run-tests.R.
#
# The generator's output is the federation index: what it writes is what every agent fetches, and
# the index-generation action commits it automatically. A wrong or empty index is therefore
# published without anyone looking at it.

generator <- normalizePath(file.path(tests_dir, "..", "scripts", "generate-protocols-yaml.R"),
                           mustWork = TRUE)

# Run the generator with the given working directory, so that relative paths in protocol_url values
# come out as they would in a real repository checkout.
run_generator <- function(wd, args = c("protocols", "PROTOCOLS.yaml"), env = character(0)) {
  old <- setwd(wd)
  on.exit(setwd(old), add = TRUE)
  output <- suppressWarnings(system2(
    "Rscript", c(shQuote(generator), shQuote(args)),
    stdout = TRUE, stderr = TRUE, env = env
  ))
  status <- attr(output, "status")
  list(status = if (is.null(status)) 0L else as.integer(status),
       output = paste(output, collapse = "\n"))
}

# A throwaway repository holding one conforming protocol, copied from the fixtures.
work <- file.path(tempdir(), "generator-roundtrip")
unlink(work, recursive = TRUE)
dir.create(file.path(work, "protocols"), recursive = TRUE, showWarnings = FALSE)
dir.create(file.path(work, "protocols", "example-protocol"), recursive = TRUE)
writeLines(baseline, file.path(work, "protocols", "example-protocol", "protocol.md"))

result <- run_generator(work, env = c("GITHUB_REPOSITORY=some-org/some-repo",
                                      "GITHUB_EVENT_NAME=push",
                                      "GITHUB_REF_NAME=trunk"))
index_file <- file.path(work, "PROTOCOLS.yaml")

if (result$status != 0 || !file.exists(index_file)) {
  check("generator writes an index", FALSE, result$output)
} else {
  index <- yaml::yaml.load_file(index_file)

  check("generated index names the detected repository",
        identical(index$repository, "some-org/some-repo"),
        sprintf("got %s", index$repository))

  check("generated index carries the spec version",
        identical(index$spec_version, "0.1.0"))

  urls <- vapply(index$protocols,
                 function(p) if (is.null(p$protocol_url)) NA_character_ else p$protocol_url,
                 character(1))
  check("protocol_url is built from the detected repository and ref",
        identical(urls, "https://raw.githubusercontent.com/some-org/some-repo/trunk/protocols/example-protocol/protocol.md"),
        paste(urls, collapse = ", "))

  # The whole frontmatter is copied through, which is how reviews reach the index without the
  # generator knowing anything about them — the mechanism ADR 0005 relies on. Compare the complete
  # objects: checking only the reviewer names would still pass if orcid, date, protocol_version or
  # status were dropped, which is the failure that would actually matter.
  expected_reviews <- list(
    list(name = "Grace Hopper", orcid = "0000-0001-5109-3700", date = "2026-02-01",
         protocol_version = "1.0.0", status = "verified-with-benchmark"),
    list(name = "Alan Turing", date = "2026-01-20",
         protocol_version = "1.0.0", status = "approved")
  )
  actual_reviews <- lapply(index$protocols[[1]]$reviews, function(r) lapply(r, as.character))
  check("every frontmatter field reaches the index, including ones the generator knows nothing about",
        identical(actual_reviews, expected_reviews),
        paste(utils::capture.output(str(actual_reviews)), collapse = " | "))
}

# An empty index is never the right answer: the action commits the output, so a mistyped path would
# replace a populated federation index with nothing.
empty <- file.path(tempdir(), "generator-empty")
unlink(empty, recursive = TRUE)
dir.create(file.path(empty, "protocols"), recursive = TRUE, showWarnings = FALSE)
result <- run_generator(empty, env = "GITHUB_REPOSITORY=some-org/some-repo")
check("generator refuses to write an index when it finds no protocols",
      result$status != 0 && !file.exists(file.path(empty, "PROTOCOLS.yaml")),
      result$output)

result <- run_generator(empty, args = c("no-such-directory", "PROTOCOLS.yaml"),
                        env = "GITHUB_REPOSITORY=some-org/some-repo")
check("generator refuses to write an index when the protocols directory is missing",
      result$status != 0 && !file.exists(file.path(empty, "PROTOCOLS.yaml")),
      result$output)

# A protocol whose frontmatter cannot be parsed must not simply be dropped. It exists in the
# repository but would be missing from the index, so no agent could discover it — and the run would
# report success and commit that index.
malformed <- file.path(tempdir(), "generator-malformed")
unlink(malformed, recursive = TRUE)
dir.create(file.path(malformed, "protocols", "broken"), recursive = TRUE, showWarnings = FALSE)
dir.create(file.path(malformed, "protocols", "example-protocol"), recursive = TRUE)
writeLines(baseline, file.path(malformed, "protocols", "example-protocol", "protocol.md"))
writeLines(c("---", "name: broken", "  bad: [unclosed", "---", "", "# Broken"),
           file.path(malformed, "protocols", "broken", "protocol.md"))
result <- run_generator(malformed, env = "GITHUB_REPOSITORY=some-org/some-repo")
check("generator refuses to write an index that silently omits an unreadable protocol",
      result$status != 0 && !file.exists(file.path(malformed, "PROTOCOLS.yaml")),
      result$output)

# Better to fail than to publish an index whose URLs point at the wrong repository. A fresh working
# directory, so that "no index was written" is actually being asserted rather than inherited from
# the successful run above; and outside any git checkout, so there is no origin remote to fall back
# to.
undetectable <- file.path(tempdir(), "generator-undetectable")
unlink(undetectable, recursive = TRUE)
dir.create(file.path(undetectable, "protocols"), recursive = TRUE, showWarnings = FALSE)
dir.create(file.path(undetectable, "protocols", "example-protocol"), recursive = TRUE)
writeLines(baseline, file.path(undetectable, "protocols", "example-protocol", "protocol.md"))
result <- run_generator(undetectable, env = "GITHUB_REPOSITORY=")
check("generator stops, writing nothing, when the repository cannot be determined",
      result$status != 0 &&
        !file.exists(file.path(undetectable, "PROTOCOLS.yaml")) &&
        grepl("Could not determine which repository", result$output, fixed = TRUE),
      result$output)
