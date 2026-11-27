---
name: protocol-runner
description: Use before performing any scientific data analysis whose method may need citing (for example filtering, normalising, diversity, similarity, clustering, enrichment or meta-analysis, especially for a paper or Methods section), even when the user does not mention protocols. Checks the federated protocol registry for a citable, versioned protocol for the task, and if one matches, executes it with Level 1 and Level 2 citations.
version: 2.2.0
category: protocols
author: waldronlab
tags: [workflow, protocol, pipeline, method_origin_citation, provenance]
---

# protocol-runner

**Skill version: 2.2.0.** Keep this line equal to `version` in the frontmatter. It is repeated here because some agent software strips the frontmatter when it loads a skill, and the Skill Execution Record below must name the version.

Finds and executes citable, versioned analysis protocols from federated repositories, ensuring reproducible agent behavior and correct attribution of methods and underlying literature.

## Usage

- "Run the 16S quality control protocol"
- "Search for a metagenomics taxonomy protocol and run it"
- "Can you follow the waldronlab/agent-protocols version of the 16S pipeline?"
- "Remove taxa present in fewer than 10% of samples" — an ordinary analysis request. Check the registry for a matching protocol before writing your own implementation. If none matches, say so and proceed without one; do not present your own implementation as a protocol.

## Prerequisites

- Network access to fetch `registry.yaml` and `PROTOCOLS.yaml` indices over HTTPS from the protocol registry and protocol repositories (e.g., from a git hosting service such as GitHub).

## Process

### 1. Discover Available Protocols

1. Read `registry.yaml` from the `waldronlab/agent-protocol-standard` repository (or whatever repository the user specified, defaulting to `https://raw.githubusercontent.com/waldronlab/agent-protocol-standard/main/registry.yaml`).
2. For each registered entry in that file, fetch its `PROTOCOLS.yaml` index using its `index_url`. Each protocol entry carries the fields this skill relies on: `name`, `description`, `version`, `date`, `status`, `type` (`atomic` | `composite`), `method_origin_citation`, `protocol_citation`, `artifact_doi`, `collection_doi`, `license`, `protocol_url`, `upstream_repositories`, `database_urls`, `protocols_used`.
3. Merge all protocol entries from all fetched indices into a single available protocol list. **Carry the parent metadata onto each entry as you merge it**: `trust_tier` comes from the repository's entry in `registry.yaml`, and the repository name from the index's top-level `repository` field. Neither is a property of an individual protocol, and without them the ranking and display below have nothing to work with.
4. **If the registry or an index cannot be fetched** — no network, a blocked host, a malformed file — and the user did not ask for a protocol by name, say which fetch failed, then carry out the request without a protocol, under the rules of step 2.4. This skill now loads for ordinary analysis requests, and an unreachable registry must not stop the user's analysis. If the user did name a protocol, report the failure and stop.

### 2. Match Protocol to Request

1. If the user named a specific repository or version — "the `waldronlab/agent-protocols` version", "v1.2.1 of independent-filtering-variance" — treat those as **hard filters**, applied before any ranking. If nothing matches exactly, say so and stop rather than falling back to a same-named protocol from another repository or a different release; silently substituting either breaks the provenance this skill exists to preserve.
2. Match the user's stated task to the remaining protocols using `name`, `description`, `category`, and `tags`.
3. If there are multiple matches, rank them by `trust_tier` (descending), and then by `status` (preferring `stable`).
4. **If no protocol matches** and the user did not name one, say so in one sentence, naming the registry checked, and carry out the request without a protocol. In that case:
   - Emit no Method Provenance block and no AI Agent Protocol attribution sentence: no protocol was followed, and your own implementation is not one.
   - Do not present a near match as the protocol for the task, and do not apply one the user did not ask for.
   - Give no DOI or PMID from memory, including for the method itself. Name the method and tell the user its citation is theirs to look up. No frontmatter stands behind such an identifier, so nothing can check it.

### 3. Present Selection to User

1. Show the top 1-3 matches to the user.
2. For each match, provide the `name`, repository name, `version`, `status`, `trust_tier`, and `description`.
3. Ask the user to confirm which protocol to run.

Once a protocol is selected, resolve its dependencies (step 4) and then apply these status rules to
**every protocol in the resolved execution chain**, not only the one the user chose. A `stable`
composite may depend on a protocol that is not, and executing it unannounced would be exactly the
silent substitution this skill is meant to prevent:

   - *Warning*: status `draft` — warn the user that it may be unstable, naming which protocol in the chain it is.
   - *Warning*: status `superseded` — warn the user and suggest checking for a newer version or successor protocol.
   - *Error*: status `deprecated` — refuse to run **any part of the chain** unless explicitly overridden.

### 4. Resolve Dependencies

1. Once the user selects a protocol, check its `protocols_used` field. The entries follow this object structure:
   ```yaml
   protocols_used:
     - name: humann4-sgb-aggregation
       repository: waldronlab/agent-protocols
       version: 1.0.0
   ```
2. Resolve each dependency in the merged federation index by **`name`, `repository`, and exact `version`**. `protocols_used.version` is an exact requirement, not a minimum: running a different release of a declared dependency changes what was executed while the provenance block still claims the declared version. If no entry matches all three, report which dependency could not be resolved and abort.
3. Order execution: Dependencies must be executed *before* the main protocol, in the order they are declared.
4. Apply the status rules from step 3 to every protocol resolved here before executing anything.
5. *Constraint*: Composite protocols define single-level execution dependencies across constituent atomic protocols. If a dependency itself has dependencies, inform the user and abort.

### 5. Fetch Content and Compile Citations

1. For each protocol in the execution chain (dependencies first, then the main protocol):
   - Fetch the markdown content using the `protocol_url` specified in the index.
   - Parse `protocol_citation`, which every protocol carries (ADR 0014). Compare it against this protocol's own DOIs — `artifact_doi` first, then `collection_doi`. Where it matches neither, it names a publication describing this procedure. Where it matches either, the protocol is a first definition published there, and the same DOI must not be cited twice in the block below.
   - Parse `method_origin_citation` where present, to extract the DOI or PMID of the method's origin (Level 2 Citation). It is optional: a protocol that originates no method — operating a tool, building a reference database — omits it, and that absence is not a defect to report.
   - For a composite protocol (`type: composite`), aggregate the `method_origin_citation` of each constituent atomic protocol listed in `protocols_used`. Where the composite carries one of its own — the composition was itself published as a method — cite it alongside the aggregated constituents.
2. **Important**: Before executing any code, emit the full Method Provenance block using the following format, adapted for each protocol in the chain. "Before" is about order, not only about where it appears in the final reply:
   - Write the block as a message, **before the first tool call that reads, transforms, or writes the user's data**. Fetching the registry, indices, and protocol files may come first; anything that touches the data may not.
   - Where nothing you write reaches the user until a single final report, as when you run as a sub-agent, also write the block to `method_provenance.md` beside the outputs before that first data step, and put it first in the final report.
   - Reproduce the template's headings and field labels exactly (`## Method Provenance`, `### Protocol Citation (Level 1)`, and each `Label:` line, plus `### Primary Literature to Cite (Level 2)` only where the next point says it applies), so a reader or a script can find each field. Citations listed in another format do not satisfy this step.
   - Where no protocol in the chain carries a `method_origin_citation`, leave the Level 2 heading out altogether. A `### Primary Literature to Cite (Level 2)` heading with "None" or "omitted" under it is still a Level 2 section; say in a sentence outside the block that none applies.
   - Take every value from the protocol's frontmatter and the index. Do not add author names, years, or other bibliographic detail from memory; give the DOI, which is what the reader resolves.

   ```markdown
   ## Method Provenance

   ### Protocol Citation (Level 1)
   Following: [Author] "[Protocol Title/Name]"
   Repository: [Repository Name], protocol: [Protocol Name] v[Version] ([date])
   Repository DOI: [collection_doi if present]
   Protocol DOI: [artifact_doi if present]
   Publication DOI: [protocol_citation — omit this line when it equals the Repository DOI or the Protocol DOI above, which means this protocol is a first definition published there, and the same DOI must not appear twice]
   Trust tier: [trust_tier]
   License: [license]

   [Include the Level 2 heading and the list below it only when a protocol in the chain carries a `method_origin_citation`. Otherwise leave out both: do not write the heading with "None" under it.]
   ### Primary Literature to Cite (Level 2)
   This protocol implements methods from:
   - [The method's origin (DOI/PMID) from `method_origin_citation`, where the protocol carries one. Omit this section entirely when no protocol in the chain does: a protocol that originates no method has no primary literature to attribute, and inventing one is the failure this block exists to prevent]
   - [Composite protocols: the aggregated `method_origin_citation` values of all constituent atomic protocols that carry one]
   - [Composite protocols that carry their own `method_origin_citation`: that DOI/PMID as well, labelled as the method the composition itself proposes]
   ```

   *Note: If `artifact_doi` is present, cite it. If only `collection_doi` is present, ensure it is clearly displayed alongside the specific protocol name and version so the user knows which part of the repository was used.*

### 6. Execute Protocol

1. **Check the materials before Step 1.** Every condition in `## Materials` is written with *must* or *should* (PROTOCOL_STANDARD.md, "Markdown Content Structure"). Check each against the inputs the user supplied:
   - A *must* condition that fails: stop, report which condition failed and on which input, and produce none of the protocol's outputs.
   - A *should* condition that fails: warn the user, naming the condition and the consequence the protocol gives for it, then continue. Record the warning for step 7.
2. Follow the steps in the fetched protocol content in order.
3. **Resource Discovery**: Agents can discover and download pre-computed reference data and upstream tools using the `database_urls` and `upstream_repositories` YAML fields provided in the index.
4. Adapt the provided code to the user's specific environment, file paths, parameters, and organisms as necessary.
5. If a step cannot be followed exactly as written, or requires a different package version than specified, note this departure inline.

### 7. Record Departures

1. After execution completes, emit a final "Departures from protocol" section.
2. List any deviations made during execution (e.g., using a different parameter value, skipping a step, or substituting a package). This is a normal part of adapting a protocol; recording it is what matters for provenance.
3. List every warning given in step 6.1, with the condition that was not met.

### 8. Generate Draft Methods Section

1. **Narrative Synthesis:** Synthesize a publication-ready narrative Methods section describing the exact analysis steps performed.
   - If the protocol contains a `## Methods Template` section, use its text as the baseline phrasing structure and fill in actual runtime parameters and sample identifiers. Otherwise, construct clear academic prose.
2. **Inline Method Attribution (Level 2):** Embed the `method_origin_citation` of each protocol in the chain directly into the narrative prose at the step that uses it, by DOI or PMID (e.g., *"...using the Jaccard coefficient (DOI: `[method_origin_citation]`)"*). **Cite only DOIs and PMIDs that appear in the frontmatter of a protocol in the chain** — `method_origin_citation`, `protocol_citation`, `artifact_doi`, `collection_doi`. Do not add others, including for software or for a method no protocol covers, from memory or elsewhere: nothing can check them. Name software and versions in prose without a DOI.
3. **Departures & Parameters:** Seamlessly incorporate any runtime parameter adaptations or deviations recorded in Step 7 into the text.
4. **AI Agent Protocols Attribution Subsection (Level 1):** Include a dedicated separate paragraph/subsection naming and citing the executed protocol artifact, repository, version, and protocol/repository DOI:
   > *"Computational analysis was automated using the AI Agent Protocol `[Protocol Name]` (v`[Version]`, DOI: `[artifact_doi or collection_doi]`) from `[repository]`, executed via the `protocol-runner` agent skill (`waldronlab/agent-protocol-standard`)."*

   Both DOI fields are optional in the standard and are frequently absent. **Omit the DOI clause entirely when neither `artifact_doi` nor `collection_doi` is present** — a sentence reading "DOI:" with nothing after it is worse than no DOI at all — and name the repository and version instead, which always exist.
5. **No Style-Specific Bibliography Formatting:** Do not generate formatted bibliographies in arbitrary styles (APA, MLA, BibTeX, etc.); propagate exact DOIs and PMIDs so users can seamlessly import them into their reference manager of choice.

## Output Format

1. The "Method Provenance" block (Level 1 and Level 2 citations emitted pre-execution).
2. Code and execution logs from running the steps.
3. The "Departures from protocol" summary.
4. The **"Draft Methods Section"** (publication-ready prose with inline DOI citations, runtime parameters, and dedicated AI Agent Protocol attribution subsection).
5. A **Skill Execution Record**: a single closing line naming this skill and its version, as stated at the top of this file, so a reader of the transcript can tell which runner, at which version, produced everything above.

   > 🛠️ Skill executed: `protocol-runner` v`[the Skill version stated at the top of this file]` (`waldronlab/agent-protocol-standard`)

## Examples

**User**: "Search for a metagenomics taxonomy protocol and run it"

**Skill produces**:
- A short list of matching protocols with version, status, trust tier, and description
- A request for the user to confirm which protocol to run
- A method provenance block before any execution begins
- The executed steps and logs
- A departures summary after the protocol finishes
- A drafted narrative Methods section with inline citations for the user's manuscript

## Notes

- Trust scores and popularity metrics are reserved for a future release, but `trust_tier` from the registry should be displayed if available.
- This skill is language- and ecosystem-agnostic. Protocols are written as English-language procedures and may be implemented in any language or pipeline framework; nothing here assumes R, Bioconductor, or any particular runtime.
