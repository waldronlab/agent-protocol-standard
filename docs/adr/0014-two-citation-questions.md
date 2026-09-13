# 0014. Ask Two Citation Questions, and Require the Answerable One

- **Status:** Accepted
- **Date:** 2026-09-13
- **Deciders:** Levi Waldron (User), AI Agent
- **Amends:** [ADR-0009](0009-name-metadata-fields-by-what-they-identify.md) — renames one field it named and
  inverts which of the two citation fields is required; [ADR-0012](0012-require-materials-steps-and-a-resolvable-citation.md) —
  replaces its atomic-must-carry-a-method-citation rule

## Context and Problem Statement

ADR 0009 named the citation fields `method_citation` and `protocol_citation` and required the first on
every atomic protocol. The distinction proved hard to explain. `PROTOCOL_STANDARD.md` needed a
counterfactual to express it — *if the protocol's steps were rewritten, would the DOI still be right?* —
and `AUTHORING.md` spent twenty lines on it. A rule a contributor cannot apply is a rule that gets
applied wrongly.

**The required field is not always answerable.** The six HUMAnN 4 protocols carry a `method_citation`
because the schema demands one, not because a method was proposed there: building a tool's reference
database performs no method that anybody invented. The schema was forcing a citation into existence.

**The backlog is paper-first, and the schema is method-first.** The 31 protocol issues are
protocolizations of published analyses — bugSigSimple, the BugSigDB paper, curatedMetagenomicDataAnalyses.
For those, "what paper describes this procedure?" has an obvious answer, while "where was the method first
proposed?" takes archaeology: tracing leave-one-dataset-out past its first microbiome use to Riester et al.
2014 was deliberate effort. The schema required the hard question and made the easy one optional.

## Decision

**`protocol_citation` is required. `method_origin_citation` is optional.** `method_citation` is renamed;
the old name is rejected, as under ADR 0009.

Each field answers one question, stated on its own rather than against the other:

| Field | Question |
|---|---|
| `protocol_citation` | Who published **these instructions**? |
| `method_origin_citation` | Who **invented the method**? |

**Where no publication describes the procedure, `protocol_citation` names the protocol's own DOI** —
`artifact_doi` where one exists, otherwise `collection_doi`. This is expected to be **rare** — a protocol
usually encodes a published procedure, and that publication is the answer — but where it applies it makes
first definition a claim rather than an absence:

- `protocol_citation` matches neither of the protocol's own DOIs — an external publication describes this
  procedure.
- `protocol_citation` equals the protocol's own DOI — `artifact_doi` where it has one, otherwise `collection_doi` — a first definition, published here.

A collection with no DOI cannot host a first definition: there is nothing to cite. Deposit it first. That
is a deliberate consequence rather than an oversight — a repository claiming to hold citable protocols
should be citable itself.

An absent field conflates "first definition" with "nobody filled it in". A required field separates them,
and CI can check the answer is one of the two legal shapes.

**The concept DOI, not a version DOI.** A version DOI names exact bytes, which sounds more precise, but a
protocol cannot carry the DOI of the release that has not been minted yet — the value would have to be
known before the act that creates it. Name, version, and concept DOI together identify the exact protocol
without that circularity, and a concept DOI does not need rewriting on every release.

**`method_origin_citation` is omitted where no method was originated.** ADR 0012's rule that an atomic
protocol must carry a method citation is withdrawn: it was the rule forcing the HUMAnN protocols to name a
method nobody proposed. A composite may still carry one where the composition was itself published as a
method (ADR 0010, unchanged).

## Alternatives Considered

- **Keep the current scheme and rewrite only the guidance.** The rule was defensible and the explanation
  was the problem, so better prose might have sufficed. Rejected because it would not have fixed the
  unanswerable-required-field problem, which is a schema fault rather than a documentation one.
- **Rename only, leaving `method_origin_citation` required on atomic protocols.** `method_origin_citation`
  carries the rule in the name, which is most of what made the old name confusing. Rejected for the same
  reason: naming the field better does not make every protocol have an origin to name.
- **Require at least one of the two fields.** Simpler to implement, but it restores the choice this ADR
  removes, and an author supplies whichever they happen to have.
- **Allow `protocol_citation` to stay empty for a first definition.** Rejected: an absence cannot be
  distinguished from an omission, so the metadata could not state what is true.
- **Drop `protocol_citation` entirely**, on the grounds that `artifact_doi` and `collection_doi` already
  identify the document. Rejected: those say where this document lives, not who published the procedure,
  and the two differ exactly when a protocol transcribes someone else's published analysis — which is most
  of the backlog.

## Consequences

Requiring the answerable question also removes the pressure to misfile the other one. The standing citation
policy exists because authors cite the paper they read where the method's origin belongs; giving that paper
a correct home of its own should do more than a rule forbidding the substitution did.

Every protocol must now name a `protocol_citation`, and the seven existing ones are migrated in the content
repository: the eLife HUMAnN paper describes the database-build procedure, so it serves as both fields'
value on those six.

`method_origin_citation` becomes optional, so it can be omitted honestly rather than filled in to pass CI.
The risk accepted is that an author skips it where an origin does exist — the standing citation policy and
`AUTHORING.md` carry that obligation, and no validator can check whether a paper is really the first.

This is the second rename of these fields in two days, following ADR 0009. The spec is `0.y.z` precisely so
that this is allowed, and no protocol outside this organisation consumes it yet, but the churn is real and
is the main argument the alternatives above had going for them.
