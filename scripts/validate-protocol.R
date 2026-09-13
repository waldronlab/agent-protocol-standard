#!/usr/bin/env Rscript

# Usage: Rscript validate-protocol.R [protocols-dir]
#
# Defaults to 'protocols'. Run from the root of the repository holding the protocols.

if (!requireNamespace("rmarkdown", quietly = TRUE)) {
  install.packages("rmarkdown", repos = "https://cloud.r-project.org")
}

local({
  args <- commandArgs(trailingOnly = FALSE)
  file_arg <- grep("^--file=", args, value = TRUE)
  script_dir <- if (length(file_arg) > 0) dirname(sub("^--file=", "", file_arg[1])) else "."
  source(file.path(script_dir, "repo-utils.R"))
})

args <- commandArgs(trailingOnly = TRUE)
protocols_dir <- if (length(args) >= 1 && nzchar(args[1])) args[1] else "protocols"

# A validation run that validated nothing must not report success: as a published action, the most
# likely cause is a mistyped protocols path, and a green check would say the protocols are fine when
# none were read.
if (!dir.exists(protocols_dir)) {
  cat(sprintf("  [ERROR] No '%s' directory found. Pass the protocols directory as the first argument.\n",
              protocols_dir))
  quit(status = 1)
}

# Used only to recognise a 'protocols_used' dependency that lives in this same repository, whose
# file we can therefore check for. NA outside a git checkout (a bare tarball, say), in which case
# the local existence check is skipped rather than failing.
this_repository <- detect_repository()

protocol_files <- list.files(protocols_dir, pattern = "protocol\\.md$", recursive = TRUE, full.names = TRUE)
if (length(protocol_files) == 0) {
  cat(sprintf("  [ERROR] No 'protocol.md' files found under '%s'.\n", protocols_dir))
  quit(status = 1)
}

required_fields <- c("name", "description", "version", "authors", "date", "status")

# Controlled vocabulary for review statuses (see PROTOCOL_STANDARD.md). There is deliberately no
# "unreviewed" value: a version nobody has reviewed simply has no entry.
review_statuses <- c("approved", "verified-with-benchmark", "changes-requested", "deprecated")

# The protocol's own lifecycle, distinct from the review vocabulary above (PROTOCOL_STANDARD.md).
# The runner ranks on these and refuses to execute a 'deprecated' protocol, so an unchecked typo
# here disarms the standard's only hard safety rule.
protocol_statuses <- c("draft", "stable", "deprecated", "superseded")

orcid_pattern <- "^[0-9]{4}-[0-9]{4}-[0-9]{4}-[0-9]{3}[0-9X]$"

# 'name' is the protocol's identifier in the directory layout, the index, and every dependency
# reference, so one capital or underscore splits a protocol into two spellings that never resolve
# to each other.
kebab_case_pattern <- "^[a-z0-9]+(-[a-z0-9]+)*$"

# A DOI or a PubMed ID. The point is to reject free-text placeholders ("see the HUMAnN paper"),
# which cannot be resolved by a reader or an agent.
citation_pattern <- "^(10\\.[0-9]{4,9}/[^[:space:]]+|PMID:[0-9]+)$"

# The starter protocol in template/ carries this, and it is DOI-shaped, so the pattern above passes
# it. A copied template is the likeliest wrong citation there is, so name it outright.
template_placeholder_citation <- "10.0000/replace-with-a-real-doi"
semver_pattern <- "^[0-9]+\\.[0-9]+\\.[0-9]+$"
date_pattern <- "^[0-9]{4}-[0-9]{2}-[0-9]{2}$"
version_heading_pattern <- "^###[[:space:]]+Version[[:space:]]+([^[:space:]]+)[[:space:]]+\\(([0-9]{4}-[0-9]{2}-[0-9]{2})\\)[[:space:]]*$"

# YAML gives a field whatever shape the author wrote: a string, a number, a list, a mapping, or
# NULL for `field: ~`. Nearly every check here needs the same question answered — is this one
# string? — and answering it inline per field is what let `name: ~`, `name: [a, b]` and
# `type: [atomic, composite]` each abort the run in turn, one field at a time.
scalar_string <- function(x) is.character(x) && length(x) == 1L && !is.na(x)

# A value's description for an error message. Never coerces: as.character() on a mapping deparses
# it into something that reads like a value the author wrote ("found: 'atomic'" for
# `type: {value: atomic}`), and on other shapes it can fail outright — inside the very message
# meant to report the bad shape.
describe_value <- function(x) {
  if (is.null(x)) return("nothing (the field is empty or `~`)")
  if (scalar_string(x)) return(sprintf("'%s'", x))
  if (is.list(x)) return(sprintf("a %s of %d element(s)",
                                 if (!is.null(names(x))) "mapping" else "list", length(x)))
  if (length(x) != 1L) return(sprintf("%d values", length(x)))
  cls <- class(x)[1]
  article <- if (grepl("^[aeiou]", cls)) "an" else "a"
  sprintf("%s %s ('%s')", article, cls, tryCatch(format(x), error = function(e) "?"))
}

# Drops YAML frontmatter and fenced code blocks, so that a heading shown inside a worked example
# is not mistaken for the document's own. A protocol whose '## Steps' exists only inside a ```markdown
# illustration has no steps.
strip_frontmatter_and_code <- function(lines) {
  keep <- rep(TRUE, length(lines))
  in_fence <- FALSE
  fence <- NULL
  fence_length <- 0L
  in_frontmatter <- FALSE
  for (i in seq_along(lines)) {
    line <- lines[i]
    # Frontmatter only when the file opens with it.
    if (!in_fence && i == 1 && grepl("^---[[:space:]]*$", line)) {
      in_frontmatter <- TRUE
      keep[i] <- FALSE
      next
    }
    if (in_frontmatter) {
      keep[i] <- FALSE
      if (grepl("^(---|\\.\\.\\.)[[:space:]]*$", line)) in_frontmatter <- FALSE
      next
    }
    # CommonMark's rule, not an approximation of it: a closing fence uses the same character as
    # the opener, is at least as long, and carries nothing but whitespace after it. Recording only
    # the character let a lone ``` close a ```` block, and ignoring the suffix let ```not-a-close
    # close one — either way the rest of the example leaked out as prose and satisfied the
    # structural checks it was supposed to fail.
    marker <- regmatches(line, regexpr("^[[:space:]]{0,3}(`{3,}|~{3,})", line))
    if (length(marker) == 1) {
      run <- trimws(marker)
      token <- substr(run, 1, 1)
      run_length <- nchar(run)
      suffix <- sub("^[[:space:]]{0,3}(`{3,}|~{3,})", "", line)
      if (!in_fence) {
        # An opening backtick fence's info string may not contain a backtick; otherwise anything.
        if (!identical(token, "`") || !grepl("`", suffix, fixed = TRUE)) {
          in_fence <- TRUE
          fence <- token
          fence_length <- run_length
          keep[i] <- FALSE
          next
        }
      } else if (identical(token, fence) && run_length >= fence_length &&
                 grepl("^[[:space:]]*$", suffix)) {
        in_fence <- FALSE
        fence <- NULL
        fence_length <- 0L
        keep[i] <- FALSE
        next
      }
    }
    if (in_fence) keep[i] <- FALSE
  }
  lines[keep]
}

# "Jane Doe ([0000-...](https://orcid.org/0000-...))" -> "Jane Doe"
strip_orcid_suffix <- function(x) trimws(sub("[[:space:]]*\\(\\[.*\\]\\(.*\\)\\)$", "", x))

is_valid_date <- function(x) {
  if (!grepl(date_pattern, x)) return(FALSE)
  parsed <- tryCatch(as.Date(x), error = function(e) NA)
  !is.na(parsed)
}

# Validates the '## History & Reviews' section and the frontmatter 'reviews' array, including their
# consistency with each other. Collects every problem rather than stopping at the first.
validate_history <- function(file_path, frontmatter) {
  errors <- character(0)
  lines <- readLines(file_path, warn = FALSE)

  heading_idx <- grep("^##[[:space:]]+History & Reviews[[:space:]]*$", lines)
  if (length(heading_idx) == 0) {
    cat("  [ERROR] Missing required '## History & Reviews' section (see PROTOCOL_STANDARD.md).\n")
    return(FALSE)
  }
  if (length(heading_idx) > 1) {
    cat("  [ERROR] Found multiple '## History & Reviews' headings; there must be exactly one.\n")
    return(FALSE)
  }

  section <- if (heading_idx < length(lines)) lines[(heading_idx + 1):length(lines)] else character(0)

  later_section <- grep("^##[[:space:]]", section)
  if (length(later_section) > 0) {
    errors <- c(errors, sprintf(
      "'## History & Reviews' must be the last section, but '%s' appears after it",
      trimws(section[later_section[1]])))
  }

  # Every level-3 heading in this section must be a version entry. Selecting only the well-formed
  # ones would silently skip a typo'd heading ('### Verson 1.1.0 (...)') and everything under it.
  version_idx <- grep("^###[[:space:]]", section)
  if (length(version_idx) == 0) {
    cat("  [ERROR] '## History & Reviews' has no '### Version X.Y.Z (YYYY-MM-DD)' entries.\n")
    return(FALSE)
  }

  # Parse the version headings
  versions <- character(length(version_idx))
  heading_dates <- character(length(version_idx))
  for (k in seq_along(version_idx)) {
    heading <- section[version_idx[k]]
    if (!grepl(version_heading_pattern, heading)) {
      errors <- c(errors, sprintf(
        "Malformed version heading '%s'; expected '### Version X.Y.Z (YYYY-MM-DD)'", trimws(heading)))
      versions[k] <- NA_character_
      heading_dates[k] <- NA_character_
      next
    }
    versions[k] <- sub(version_heading_pattern, "\\1", heading)
    heading_dates[k] <- sub(version_heading_pattern, "\\2", heading)
    if (!grepl(semver_pattern, versions[k])) {
      errors <- c(errors, sprintf(
        "Version '%s' in '## History & Reviews' is not semantic versioning (X.Y.Z)", versions[k]))
    }
    if (!is_valid_date(heading_dates[k])) {
      errors <- c(errors, sprintf(
        "Invalid date '%s' in heading '%s'", heading_dates[k], trimws(heading)))
    }
  }

  # Entries must be strictly descending (newest first)
  parseable <- !is.na(versions) & grepl(semver_pattern, versions)
  if (length(versions) > 1) {
    for (k in seq_len(length(versions) - 1)) {
      if (!parseable[k] || !parseable[k + 1]) next
      above <- numeric_version(versions[k])
      below <- numeric_version(versions[k + 1])
      if (above == below) {
        errors <- c(errors, sprintf("Duplicate version entry '%s' in '## History & Reviews'", versions[k]))
      } else if (above < below) {
        errors <- c(errors, sprintf(
          "Version entries must be in descending order (newest at the top), but '%s' appears above '%s'",
          versions[k], versions[k + 1]))
      }
    }
  }

  # The top entry describes the current release, so it must agree with the frontmatter on both the
  # version and the release date.
  fm_version <- as.character(frontmatter$version)
  if (parseable[1] && !identical(versions[1], fm_version)) {
    errors <- c(errors, sprintf(
      "Top entry in '## History & Reviews' is version '%s', but frontmatter declares version '%s'",
      versions[1], fm_version))
  }
  fm_date <- as.character(frontmatter$date)
  if (!is.na(heading_dates[1]) && !identical(heading_dates[1], fm_date)) {
    errors <- c(errors, sprintf(
      "Top entry in '## History & Reviews' is dated '%s', but frontmatter declares date '%s'. The heading date is the version's release date.",
      heading_dates[1], fm_date))
  }

  # Parse the review blocks under each version
  bounds <- c(version_idx, length(section) + 1)
  md_reviews <- data.frame(
    version = character(0), name = character(0), date = character(0),
    status = character(0), orcid = character(0), stringsAsFactors = FALSE)

  for (k in seq_along(version_idx)) {
    label <- if (is.na(versions[k])) trimws(section[version_idx[k]]) else versions[k]
    body <- if (bounds[k + 1] - 1 >= version_idx[k] + 1) {
      section[(version_idx[k] + 1):(bounds[k + 1] - 1)]
    } else {
      character(0)
    }

    changes_idx <- grep("^####[[:space:]]+Changes[[:space:]]*$", body)
    if (length(changes_idx) == 0) {
      errors <- c(errors, sprintf("Version %s is missing a '#### Changes' subsection", label))
    } else {
      subsequent <- grep("^####[[:space:]]", body)
      next_heading <- subsequent[subsequent > changes_idx[1]]
      changes_end <- if (length(next_heading) > 0) next_heading[1] - 1 else length(body)
      changes_body <- if (changes_end >= changes_idx[1] + 1) {
        body[(changes_idx[1] + 1):changes_end]
      } else {
        character(0)
      }
      if (!any(grepl("^-[[:space:]]+[^[:space:]]", changes_body))) {
        errors <- c(errors, sprintf(
          "Version %s has an empty '#### Changes' subsection; list what changed as bullet points", label))
      }
    }

    reviews_idx <- grep("^####[[:space:]]+Reviews[[:space:]]*$", body)
    if (length(reviews_idx) == 0) {
      errors <- c(errors, sprintf("Version %s is missing a '#### Reviews' subsection", label))
      next
    }
    reviews_body <- if (reviews_idx[1] < length(body)) body[(reviews_idx[1] + 1):length(body)] else character(0)

    # Each review block runs from its '**Review by ...**' heading to the next one, so that the
    # Date/Status/Notes lines are attributed to the reviewer they belong to.
    block_starts <- grep("^\\*\\*Review by", reviews_body)
    block_bounds <- c(block_starts, length(reviews_body) + 1)
    reviewer_names <- character(0)

    for (b in seq_along(block_starts)) {
      heading <- reviews_body[block_starts[b]]
      block <- if (block_bounds[b + 1] - 1 >= block_starts[b] + 1) {
        reviews_body[(block_starts[b] + 1):(block_bounds[b + 1] - 1)]
      } else {
        character(0)
      }

      matched <- regmatches(heading, regexec("^\\*\\*Review by[[:space:]]+(.+)\\*\\*[[:space:]]*$", heading))[[1]]
      if (length(matched) < 2) {
        errors <- c(errors, sprintf(
          "Malformed review heading '%s' under version %s; expected '**Review by <Name>**'",
          trimws(heading), label))
        next
      }
      who <- matched[2]
      block_orcid <- NA_character_
      linked_orcid <- regmatches(who, regexec("\\(\\[([^]]*)\\]\\([^)]*\\)\\)[[:space:]]*$", who))[[1]]
      if (length(linked_orcid) >= 2) {
        block_orcid <- linked_orcid[2]
        if (!grepl(orcid_pattern, block_orcid)) {
          errors <- c(errors, sprintf(
            "Invalid ORCID '%s' in review block under version %s", block_orcid, label))
        }
      }
      reviewer <- strip_orcid_suffix(who)
      reviewer_names <- c(reviewer_names, reviewer)

      block_date <- NA_character_
      date_line <- grep("^-[[:space:]]+\\*\\*Date:\\*\\*", block, value = TRUE)
      if (length(date_line) == 0) {
        errors <- c(errors, sprintf(
          "Review by '%s' under version %s is missing a '- **Date:**' line", reviewer, label))
      } else {
        block_date <- trimws(sub("^-[[:space:]]+\\*\\*Date:\\*\\*", "", date_line[1]))
        if (!is_valid_date(block_date)) {
          errors <- c(errors, sprintf(
            "Review by '%s' under version %s has an invalid date '%s' (expected YYYY-MM-DD)",
            reviewer, label, block_date))
        }
      }

      block_status <- NA_character_
      status_line <- grep("^-[[:space:]]+\\*\\*Status:\\*\\*", block, value = TRUE)
      if (length(status_line) == 0) {
        errors <- c(errors, sprintf(
          "Review by '%s' under version %s is missing a '- **Status:**' line", reviewer, label))
      } else {
        quoted <- regmatches(status_line[1], regexec("`([^`]*)`", status_line[1]))[[1]]
        if (length(quoted) < 2) {
          errors <- c(errors, sprintf(
            "Review by '%s' under version %s must give a backtick-quoted status", reviewer, label))
        } else {
          block_status <- quoted[2]
          if (!block_status %in% review_statuses) {
            errors <- c(errors, sprintf(
              "Invalid review status '%s' under version %s. Must be one of: %s",
              block_status, label, paste(review_statuses, collapse = ", ")))
          }
        }
      }

      if (!any(grepl("^-[[:space:]]+\\*\\*Notes:\\*\\*", block))) {
        errors <- c(errors, sprintf(
          "Review by '%s' under version %s is missing a '- **Notes:**' line", reviewer, label))
      }

      if (!is.na(versions[k])) {
        md_reviews <- rbind(md_reviews, data.frame(
          version = versions[k], name = reviewer, date = block_date,
          status = block_status, orcid = block_orcid, stringsAsFactors = FALSE))
      }
    }

    placeholder <- any(grepl("^\\*No reviews yet\\.\\*[[:space:]]*$", reviews_body))
    if (length(reviewer_names) == 0 && !placeholder) {
      errors <- c(errors, sprintf(
        "Version %s has no review blocks; its '#### Reviews' subsection must contain '*No reviews yet.*'",
        label))
    }
    if (length(reviewer_names) > 0 && placeholder) {
      errors <- c(errors, sprintf(
        "Version %s has review blocks but is also marked '*No reviews yet.*'", label))
    }
  }

  # Validate the frontmatter 'reviews' array. Absent or empty is valid: an unreviewed protocol
  # simply has no entries.
  fm_reviews <- data.frame(
    version = character(0), name = character(0), date = character(0),
    status = character(0), orcid = character(0), stringsAsFactors = FALSE)
  if (!is.null(frontmatter$reviews)) {
    # A YAML mapping is also a list in R, and a named one passes an is.list() test while being the
    # wrong shape entirely: the schema calls this an array of objects.
    if (!is.list(frontmatter$reviews) || !is.null(names(frontmatter$reviews))) {
      errors <- c(errors, sprintf("'reviews' must be a list of objects, found %s",
                                  describe_value(frontmatter$reviews)))
    } else {
      for (review in frontmatter$reviews) {
        if (!is.list(review)) {
          errors <- c(errors, "Each 'reviews' entry must be an object, not a bare value")
          next
        }
        who <- if (scalar_string(review$name)) review$name else "<unnamed>"
        missing_keys <- setdiff(c("name", "date", "protocol_version", "status"), names(review))
        if (length(missing_keys) > 0) {
          errors <- c(errors, sprintf(
            "Review entry for '%s' is missing required field(s): %s",
            who, paste(missing_keys, collapse = ", ")))
          next
        }
        # Shape before use, as in validate_protocol(). Coercing first and testing after is what let
        # `status: [approved, deprecated]` reach a length-2 `if` and abort the run, and a two-element
        # review date reach is_valid_date() the same way — one malformed review taking down the
        # report for every protocol.
        malformed <- character(0)
        for (field in c("name", "date", "protocol_version", "status")) {
          if (!scalar_string(review[[field]])) {
            malformed <- c(malformed, sprintf("'%s' (%s)", field, describe_value(review[[field]])))
          }
        }
        if (!is.null(review$orcid) && !scalar_string(review$orcid)) {
          malformed <- c(malformed, sprintf("'orcid' (%s)", describe_value(review$orcid)))
        }
        if (length(malformed) > 0) {
          errors <- c(errors, sprintf(
            "Review entry for '%s' has field(s) that must each be a single string: %s",
            who, paste(malformed, collapse = ", ")))
          next
        }
        status <- review$status
        if (!status %in% review_statuses) {
          errors <- c(errors, sprintf(
            "Review by '%s' has invalid status '%s'. Must be one of: %s",
            who, status, paste(review_statuses, collapse = ", ")))
        }
        if (!is.null(review$orcid) && !grepl(orcid_pattern, review$orcid)) {
          errors <- c(errors, sprintf("Review by '%s' has a malformed 'orcid': %s", who, review$orcid))
        }
        if (!is_valid_date(review$date)) {
          errors <- c(errors, sprintf(
            "Review by '%s' has an invalid 'date': %s (expected YYYY-MM-DD)", who, review$date))
        }
        reviewed_version <- review$protocol_version
        if (!reviewed_version %in% versions[parseable]) {
          errors <- c(errors, sprintf(
            "Review by '%s' declares protocol_version '%s', which has no matching entry in '## History & Reviews'",
            who, reviewed_version))
        }
        fm_reviews <- rbind(fm_reviews, data.frame(
          version = reviewed_version, name = who, date = review$date,
          status = status,
          orcid = if (is.null(review$orcid)) NA_character_ else review$orcid,
          stringsAsFactors = FALSE))
      }
    }
  }

  # The markdown blocks and the frontmatter array must describe the same reviews. Membership alone
  # is not enough: the duplicated date, status, and ORCID must agree too, or a machine reader and a
  # human reader of the same protocol would draw different conclusions.
  review_key <- function(df) {
    if (nrow(df) == 0) character(0) else paste0("version ", df$version, ", reviewer '", df$name, "'")
  }
  md_keys <- review_key(md_reviews)
  fm_keys <- review_key(fm_reviews)
  for (key in setdiff(md_keys, fm_keys)) {
    errors <- c(errors, sprintf("Review block for %s has no matching entry in the frontmatter 'reviews' array", key))
  }
  for (key in setdiff(fm_keys, md_keys)) {
    errors <- c(errors, sprintf("Frontmatter review for %s has no matching '**Review by ...**' block under that version", key))
  }
  for (key in intersect(md_keys, fm_keys)) {
    from_md <- md_reviews[md_keys == key, ][1, ]
    from_fm <- fm_reviews[fm_keys == key, ][1, ]
    for (field in c("date", "status", "orcid")) {
      md_value <- from_md[[field]]
      fm_value <- from_fm[[field]]
      # A missing markdown value has already been reported on its own terms, and an ORCID may
      # legitimately be recorded in the frontmatter only.
      if (is.na(md_value)) next
      if (!identical(md_value, fm_value)) {
        errors <- c(errors, sprintf(
          "Review for %s disagrees between the markdown block and the frontmatter: %s is '%s' in the section but '%s' in 'reviews'",
          key, field, md_value, fm_value))
      }
    }
  }

  if (length(errors) > 0) {
    for (message in errors) cat(sprintf("  [ERROR] %s\n", message))
    return(FALSE)
  }
  return(TRUE)
}

validate_protocol <- function(file_path) {
  cat(sprintf("Validating %s...\n", file_path))
  
  # Parse YAML frontmatter
  frontmatter <- tryCatch({
    rmarkdown::yaml_front_matter(file_path)
  }, error = function(e) {
    cat(sprintf("  [ERROR] Failed to parse YAML frontmatter: %s\n", e$message))
    return(NULL)
  })
  
  if (is.null(frontmatter)) return(FALSE)
  
  # Check required fields
  missing_fields <- setdiff(required_fields, names(frontmatter))
  if (length(missing_fields) > 0) {
    cat(sprintf("  [ERROR] Missing required fields: %s\n", paste(missing_fields, collapse = ", ")))
    return(FALSE)
  }
  
  # Everything from here accumulates into 'errors' rather than returning on the first problem, so a
  # contributor sees every violation in one CI round-trip instead of one per push. The two checks
  # above stay fatal: without parseable frontmatter, or with a required field missing, the checks
  # below would report confusing consequences of a problem already named.
  errors <- character(0)
  body <- readLines(file_path, warn = FALSE)

  # Shape before comparison. `name: ~` parses to NULL and `name: [a, b]` to a vector, and either
  # one reaching the `if` below aborts the whole run with an R error rather than reporting the
  # problem through the accumulated path — taking every other protocol's report down with it.
  dir_name <- basename(dirname(file_path))
  name_is_scalar_string <- scalar_string(frontmatter$name)

  # Check directory structure matches name
  if (name_is_scalar_string && dir_name != frontmatter$name) {
    errors <- c(errors, sprintf("Directory name '%s' does not match protocol name '%s'",
                                dir_name, frontmatter$name))
  }

  # A guard that only *skips* on the wrong type lets the wrong type through: an unquoted `name: 123`
  # parses to a number, matches a '123/' directory, and never reaches the pattern below.
  if (!name_is_scalar_string) {
    errors <- c(errors, sprintf("'name' must be a single string, found %s",
                                describe_value(frontmatter$name)))
  } else if (!grepl(kebab_case_pattern, frontmatter$name)) {
    errors <- c(errors, sprintf(
      "'name' must be kebab-case: lowercase letters and digits separated by single hyphens. Found '%s'",
      frontmatter$name))
  }

  # Check authors format
  # A mapping (`authors: {Ada: {name: ...}}`) is a named list, which passes is.list() while being
  # the wrong shape: the schema calls for an array of objects.
  if (!is.list(frontmatter$authors) || !is.null(names(frontmatter$authors)) ||
      length(frontmatter$authors) == 0) {
    errors <- c(errors, sprintf("'authors' must be a non-empty list of objects, found %s",
                                describe_value(frontmatter$authors)))
  } else {
    for (author in frontmatter$authors) {
      # The entry itself, before anything is read out of it. `$` on an atomic vector is an error,
      # not NULL, so a bare `- Ada Lovelace` entry aborts the run rather than being reported.
      if (!is.list(author)) {
        errors <- c(errors, sprintf("Each 'authors' entry must be an object with a 'name', found %s",
                                    describe_value(author)))
        next
      }
      if (is.null(author$name)) {
        errors <- c(errors, "All authors must have a 'name' field")
      } else if (!scalar_string(author$name)) {
        errors <- c(errors, sprintf("An author 'name' must be a single string, found %s",
                                    describe_value(author$name)))
      }
      # An author ORCID is recommended, not required, so its absence is fine. A malformed one is
      # not: it is a claim about a specific named person that resolves to nobody. Reviewer ORCIDs
      # were already checked this way; this is the same field in the other place it appears.
      author_label <- if (scalar_string(author$name)) author$name else "?"
      if (!is.null(author$orcid)) {
        # Type and length first: `&&` reads only the first element, so a list of ORCIDs would be
        # judged on its first entry and a malformed second one never reported.
        if (!scalar_string(author$orcid)) {
          errors <- c(errors, sprintf("Author '%s' must have a single 'orcid' string, found %s",
                                      author_label, describe_value(author$orcid)))
        } else if (!grepl(orcid_pattern, author$orcid)) {
          errors <- c(errors, sprintf("Author '%s' has a malformed ORCID: '%s'",
                                      author_label, author$orcid))
        }
      }
    }
  }

  # `date` is required and was never shape-checked: `date: ~` reached validate_history(), where the
  # comparison against a zero-length value produced no error at all, and the protocol validated
  # clean. A list-valued date produced one confusing error per element instead.
  if (!scalar_string(frontmatter$date) || !is_valid_date(frontmatter$date)) {
    errors <- c(errors, sprintf("'date' must be a single YYYY-MM-DD date, found %s",
                                describe_value(frontmatter$date)))
  }

  for (field in c("description", "version")) {
    if (!scalar_string(frontmatter[[field]])) {
      errors <- c(errors, sprintf("'%s' must be a single string, found %s",
                                  field, describe_value(frontmatter[[field]])))
    } else if (!nzchar(trimws(frontmatter[[field]]))) {
      errors <- c(errors, sprintf("'%s' is required and must not be blank", field))
    }
  }

  if (!scalar_string(frontmatter$status) || !frontmatter$status %in% protocol_statuses) {
    errors <- c(errors, sprintf("'status' must be one of %s, found %s",
                                paste(sprintf("'%s'", protocol_statuses), collapse = ", "),
                                describe_value(frontmatter$status)))
  }

  # Check type field if present
  type_is_valid <- scalar_string(frontmatter$type) && frontmatter$type %in% c("atomic", "composite")
  if ("type" %in% names(frontmatter) && !type_is_valid) {
    errors <- c(errors, sprintf("'type' must be either 'atomic' or 'composite', found %s",
                                describe_value(frontmatter$type)))
  }

  # 'type' is optional, so infer it the way a reader would when it is absent: a protocol that
  # composes others is composite, and one that composes nothing is atomic. Inferred rather than
  # trusted whenever `type` is not one valid scalar, so that `type: [atomic, composite]` reports a
  # type error instead of reaching a length-2 `if` condition and aborting the run.
  n_deps <- if (is.null(frontmatter$protocols_used)) 0L else length(frontmatter$protocols_used)
  effective_type <- if (type_is_valid) frontmatter$type else {
    if (n_deps > 0) "composite" else "atomic"
  }

  # The two halves of ADR 0004's definition, each stated in PROTOCOL_STANDARD.md and neither
  # previously enforced.
  if (identical(frontmatter$type, "atomic") && n_deps > 0) {
    errors <- c(errors, sprintf(
      "'type: atomic' cannot declare 'protocols_used' (%d listed); an atomic protocol composes no others",
      n_deps))
  }
  if (identical(frontmatter$type, "composite") && n_deps == 0) {
    errors <- c(errors, "'type: composite' requires a non-empty 'protocols_used'; a composite composes other protocols")
  }

  # Check method_origin_citation field
  # Presence, not value: `citations: ~` parses to NULL, so a value check would let the deprecated
  # key through. Same reasoning as the renamed-field loop below.
  if ("citations" %in% names(frontmatter)) {
    errors <- c(errors, "Deprecated 'citations' field found. Use 'method_origin_citation' (singular string)")
  }

  # Fields renamed so that each name says what it identifies (ADR 0009).
  # Rejected rather than accepted-with-warning: the spec is pre-1.0 and no protocol predates the rename.
  renamed_fields <- list(
    citation               = "method_origin_citation",
    method_citation        = "method_origin_citation",
    publication_doi        = "protocol_citation",
    protocol_doi           = "artifact_doi",
    repository_doi         = "collection_doi"
  )
  for (old_name in names(renamed_fields)) {
    # Presence, not value: a YAML null placeholder such as `protocol_doi: ~` parses to NULL, and the
    # pre-rename template used exactly that spelling, so a value check would let old names through.
    if (old_name %in% names(frontmatter)) {
      errors <- c(errors, sprintf("Field '%s' was renamed to '%s' (see PROTOCOL_STANDARD.md)",
                                  old_name, renamed_fields[[old_name]]))
    }
  }

  # Shared shape check for both citation fields. Neither may be the starter protocol's placeholder,
  # which is DOI-shaped and so passes the pattern on its own (ADR 0012).
  check_citation <- function(field) {
    value <- frontmatter[[field]]
    if (!scalar_string(value)) {
      return(sprintf("'%s' must be a single string (DOI or PMID), found %s", field, describe_value(value)))
    }
    if (identical(value, template_placeholder_citation)) {
      return(sprintf("'%s' is still the template placeholder '%s'; replace it with the real citation",
                     field, template_placeholder_citation))
    }
    if (!grepl(citation_pattern, value)) {
      return(sprintf("'%s' must be a DOI ('10.1000/xyz') or a PubMed ID ('PMID:12345678'), found: '%s'",
                     field, value))
    }
    NULL
  }

  # `protocol_citation` is required of every protocol (ADR 0014). Where a publication describes this
  # procedure it names that publication; where none does, it names the protocol's own DOI, and the
  # equality with `collection_doi` is what makes "first definition, published here" a claim the
  # metadata states rather than an absence a reader has to interpret.
  if (!("protocol_citation" %in% names(frontmatter))) {
    errors <- c(errors, "'protocol_citation' is required: the DOI or PMID of a publication describing this procedure, or this protocol's own 'artifact_doi' or 'collection_doi' where none does")
  } else {
    problem <- check_citation("protocol_citation")
    if (!is.null(problem)) errors <- c(errors, problem)
  }

  # `method_origin_citation` is optional: it names where the method was first proposed, which is a
  # question about the literature that not every protocol has an answer to — a protocol documenting
  # how to operate a tool did not originate a method (ADR 0014). A composite may carry one, since a
  # sequence of methods can itself be published as a method (ADR 0010).
  if ("method_origin_citation" %in% names(frontmatter)) {
    problem <- check_citation("method_origin_citation")
    if (!is.null(problem)) errors <- c(errors, problem)
  }

  # The body sections. PROTOCOL_STANDARD.md requires '## Materials' and '## Steps' with at least one
  # '### Step': a document with neither is not a protocol, however complete its metadata is.
  # Checked against the prose only — a protocol whose sections appear solely inside a fenced
  # example has none.
  prose <- strip_frontmatter_and_code(body)
  if (length(grep("^##[[:space:]]+Materials[[:space:]]*$", prose)) == 0) {
    errors <- c(errors, "Missing required '## Materials' section (see PROTOCOL_STANDARD.md)")
  }
  step_heading <- grep("^##[[:space:]]+Steps[[:space:]]*$", prose)
  if (length(step_heading) == 0) {
    errors <- c(errors, "Missing required '## Steps' section (see PROTOCOL_STANDARD.md)")
  } else {
    # Only this section's own headings count. Searching the whole document would let a '### Step'
    # under '## Notes' satisfy an empty '## Steps'. The trailing boundary keeps '### Steps' — a
    # plausible typo for the section heading itself — from passing as a step, while still
    # admitting a bare '### Step', which the standard does not forbid.
    after <- prose[(step_heading[1] + 1):length(prose)]
    next_section <- grep("^##[[:space:]]", after)
    section <- if (length(next_section) > 0) after[seq_len(next_section[1] - 1)] else after
    if (length(grep("^###[[:space:]]+Step([[:space:]]|:|$)", section)) == 0) {
      errors <- c(errors, "'## Steps' contains no '### Step' heading; a protocol must have at least one step")
    }
  }

  # Check protocols_used structure for composite/dependent protocols
  if (!is.null(frontmatter$protocols_used) &&
      (!is.list(frontmatter$protocols_used) || !is.null(names(frontmatter$protocols_used)))) {
    errors <- c(errors, sprintf("'protocols_used' must be a list of objects, found %s",
                                describe_value(frontmatter$protocols_used)))
  } else if (n_deps > 0) {
    for (dep in frontmatter$protocols_used) {
      # As with authors: validate the entry before dereferencing it. `protocols_used: [foo]`
      # reached `dep$name` on a character and aborted the run.
      if (!is.list(dep)) {
        errors <- c(errors, sprintf("Each entry in 'protocols_used' must be an object with 'name', 'repository' and 'version', found %s",
                                    describe_value(dep)))
        next
      }
      if (!scalar_string(dep$name) || !scalar_string(dep$repository) || !scalar_string(dep$version)) {
        errors <- c(errors, "Each entry in 'protocols_used' must have 'name', 'repository', and 'version'")
        next
      }
      # Check local repository dependencies
      if (is.na(this_repository)) {
        cat(sprintf("  [WARN] Cannot determine this repository, so the local availability of dependency '%s' was not checked. Set GITHUB_REPOSITORY to 'owner/name' to enable this check.\n", dep$name))
      } else if (dep$repository == this_repository) {
        dep_path <- file.path(protocols_dir, dep$name, "protocol.md")
        if (!file.exists(dep_path)) {
          errors <- c(errors, sprintf("Dependent protocol '%s' not found at '%s'", dep$name, dep_path))
        }
      }
    }
  }

  # sprintf() with a zero-length argument returns character(0), so a `name: ~` would have printed
  # no errors at all — every message silently dropped by the line meant to report them. The
  # directory is always available and is what the reader needs to find the file anyway.
  display_name <- if (name_is_scalar_string) frontmatter$name else dir_name
  for (msg in errors) {
    cat(sprintf("  [ERROR] %s in '%s'\n", msg, display_name))
  }

  # Check the '## History & Reviews' feed and the frontmatter 'reviews' array. It reports its own
  # errors, and collects them the same way, so a history problem and a frontmatter problem surface
  # together rather than one release apart.
  history_ok <- validate_history(file_path, frontmatter)

  if (length(errors) > 0 || !history_ok) return(FALSE)

  cat("  [OK] Valid.\n")
  return(TRUE)
}

results <- sapply(protocol_files, validate_protocol)

if (any(!results)) {
  cat("\nValidation failed for some protocols.\n")
  quit(status = 1)
} else {
  cat("\nAll protocols passed validation!\n")
}
