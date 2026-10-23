---
name: update-protocol
description: Bump a protocol's version, record the change in History & Reviews, and update the pin in every composite in the same repository that depends on it
version: 0.1.0
category: protocols
author: waldronlab
tags: [protocol, version, history, changelog, composite, dependencies]
---

# update-protocol

Bumps the `version` and `date` of a protocol, inserts the matching entry at the top of
`## History & Reviews`, and brings every same-repository dependent's `protocols_used` pin up to the
new version. The bookkeeping is the whole job. The content of the change, and the words that
describe it, are the author's.

## Usage

- "Bump prevalence-filtering to 1.1.0; I changed the default threshold to 10%"
- "Patch release of humann4-sgb-aggregation: fixed the Mash sketch size in Step 3"
- "Major version of independent-filtering-variance, the output columns were renamed"

## Prerequisites

- A local checkout of the content repository, with its `protocols/` directory visible.
- A local checkout of `waldronlab/agent-protocol-standard` for `scripts/validate_protocol.py`,
  with Python 3.10+, `pydantic`, and `pyyaml`.
- The content repository's `owner/name`, from `GITHUB_REPOSITORY` or the checkout's `origin`
  remote, for the validator runs in steps 2.7 and 5.

## Process

### 1. Collect the three inputs

From the user, take:

1. The **protocol name**, which is the directory under `protocols/`.
2. The **bump**: `major`, `minor`, `patch`, or an explicit version such as `2.0.0`.
3. The **change description**: what is different in this release.

If the change description is missing, ask for it and stop. The `#### Changes` bullets are the
author's statement of what changed. Do not infer them from a diff, from the conversation, or from
the bump kind. The new `date` is today unless the user gives another.

### 2. Check everything before editing anything

Every check below runs before any file is edited, so that a failed check leaves the repository
exactly as it was. In order:

1. Confirm the `protocols/` directory exists and contains `protocols/<name>/protocol.md`. If not,
   say so and stop.
2. Read the frontmatter `version`. It must match `^[0-9]+\.[0-9]+\.[0-9]+$`; if it does not, say
   so and stop. Compute the **target version** from it and the bump kind. If the user gave an
   explicit version, it is the target as given, but if it is not `X.Y.Z`, or is not greater than
   the current `version`, say so and stop.
3. Check the new `date` is `YYYY-MM-DD`; if not, say so and stop. If it is earlier than the date
   in the previous top `### Version` heading, say so and ask before proceeding.
4. Read the top `### Version X.Y.Z (YYYY-MM-DD)` heading under `## History & Reviews`. If its
   version already equals the target, stop and say the entry exists; inserting another would be
   a duplicate, and the validator rejects it.
5. Find the **direct dependents**: every `protocol.md` under the same `protocols/` directory
   whose `protocols_used` has an entry with `name` equal to this protocol. A dependency is
   same-repository when its file exists here, at `protocols/<name>/protocol.md` (ADR 0018); the
   entry's `repository` should name this repository, and a mismatch is reported, not fixed.
   Read the `protocols_used` list itself; a search for the name also hits the protocol's own
   `name:` line and prose in Steps that mention it, and neither is a pin. If the protocol being
   bumped is itself a composite, its own `protocols_used` is left alone; only pins at it change.
6. Walk the graph to closure. For each dependent found, search `protocols_used` lists again for
   that dependent's name, and repeat until no new protocol is found. ADR 0001 says Phase 1
   supports single-level dependencies only, and the standard defines a composite as composing
   atomic protocols, so a second level should not occur; if it does, it joins the list. If the
   walk reaches a protocol already on the list, or the protocol being bumped, stop and report
   the chain; that is a question about the repository, not bookkeeping. Record the **ordered
   list** of protocols to touch, each with its current pinned version and its own current
   `version`. Step 4 iterates this list and nothing else.
7. Run the validator over the whole directory, from the standard checkout, exactly as in step 5.
   If the bumped protocol or any protocol on the list already has an `[ERROR]`, stop and report
   it; after editing there is no way to tell which errors this run caused. This also catches,
   before any edit, a pin that does not equal the protocol's current version, a top History
   entry that disagrees with the frontmatter, and a missing `## History & Reviews` section.
   An error in a protocol not on the list does not block; it is reported, not fixed.

Nothing in this step edits a file. If any check fails, nothing is changed. If an edit in step 3
or 4 fails partway, restore every file touched in this run to its content before the run, and
report which step failed.

### 3. Bump the protocol

1. Set frontmatter `version` to the target and `date` to the new date. These are the top-level
   keys at column zero. Entries in `reviews` carry an indented `date:` and `protocol_version:` of
   their own, which stay as they are.
2. Insert a new entry at the top of `## History & Reviews`, directly below the
   `<!-- Newest versions at the top -->` comment (or the `## History & Reviews` heading, if the
   comment is absent), with a blank line between the end of the new entry and the previous top
   entry's heading:

   ```markdown
   ### Version X.Y.Z (YYYY-MM-DD)

   #### Changes
   - <the user's description, one bullet per change>

   #### Reviews
   *No reviews yet.*
   ```

   Older entries, their `#### Changes`, and their review blocks stay exactly as they are. The
   frontmatter `reviews` array is not touched either: a review is of a version (ADR 0005), and
   the new version has none.
3. Leave `status` alone. A bump does not change status. If it is `stable`, whether the new
   version is still stable is the authors' assertion (ADR 0013), not a consequence of the bump;
   say so in the report rather than changing it.
4. Leave `## Materials`, `## Steps`, and `## Notes` alone. If the user's change is not yet in the
   document, that is their edit, made before or after this skill runs; mention it in the report.

### 4. Update each protocol on the list

For every protocol on the list recorded in step 2.6, in order:

1. Set the pin's `version` to the new version of the protocol it points at. `protocols_used.version`
   is exact, so a dependent left pinning the old version fails in the runner at resolution time,
   and the validator rejects it with `'protocols_used' pins '<name>' at version '<old>' but
   '<path>' declares version '<new>'; the pin is exact, so update the pin in '<dependent>'`.
2. Bump the dependent's own **patch** version, set its `date` to the same date, and insert a
   History entry exactly as in step 3, whose `#### Changes` is:

   ```markdown
   - Pin `<name>` at <new version> (was <old>).
   ```

   `## History & Reviews` is the changelog. A dependent whose pin changed without an entry
   carries a change no reader can see. The runner cites every protocol in a chain at its own
   version, so provenance does not need this bump; the record does.
3. Leave the dependent's `status` alone too. If it is `stable`, the ADR 0013 note in step 3.3
   applies to it as well; report it, do not change it.

No new search happens here. A protocol that is not on the list is not touched.

### 5. Validate the whole directory

From the standard checkout:

```sh
GITHUB_REPOSITORY=<owner/name> python3 scripts/validate_protocol.py <path to protocols dir>
```

Every `protocol.md` under the directory is checked, which is what makes a missed dependent
visible. Read every `[ERROR]`. Fix the ones this skill caused, such as a heading it inserted
in the wrong place or a pin it missed, and run again. An error in a protocol this skill did not
touch is reported, not fixed; that is `validate-protocol`. Never report done while an error that
this skill introduced remains.

## Output Format

1. **Bumped**: the protocol, its old and new version, and the new date.
2. The History entry inserted, verbatim.
3. **Dependents updated**: one line per protocol on the list, giving its own old and new version
   and the same `- Pin <name> at <new> (was <old>).` text that went into its History entry, plus
   its `status` when that is `stable`. "None in this repository" when there were none.
4. Whether `status` is `stable` on the bumped protocol, and that it was left unchanged.
5. The validator's final run, verbatim.
6. A closing line naming this skill and its version:

   > 🛠️ Skill executed: `update-protocol` v`0.1.0` (`waldronlab/agent-protocol-standard`)

## Notes

- The patch bump of a dependent whose pin changed (step 4) applies within a repository only.
  ADR 0018 (`docs/adr/0018-resolve-dependencies-without-the-index.md`) requires a repository's
  head to be self-consistent, so a sibling's pin moves in the same change as the bump, and the
  History entry is what makes that move visible. The argument for and against the bump is in
  `waldronlab/agent-protocol-standard#36`.
- A composite in another repository that pins this protocol is unaffected by the bump. It
  resolves its pin from its own `source` (ADR 0018), and its authors move the pin when they
  choose. This skill does nothing for it, and does not search for it.
- This skill records a change; it does not make one. Editing Materials or Steps is the author's
  work, and fixing what the validator reports in a protocol this skill did not touch is
  `validate-protocol`. Running a protocol's tests after the bump is `test-protocol`.
- `GITHUB_REPOSITORY` is required on every validator run here. The validator falls back to the
  `origin` remote of the directory it is run from, and steps 2.7 and 5 run it from the standard
  checkout, so without the variable it would take the standard as the repository and skip every
  same-repository pin check. The same applies when the content checkout's remote is a fork or a
  mirror. This holds until `waldronlab/agent-protocol-standard#54` lands; the skill itself no
  longer needs the repository name to find dependents.
