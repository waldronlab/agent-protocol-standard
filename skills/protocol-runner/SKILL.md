---
name: protocol-runner
description: Search, retrieve, evaluate trust, and execute citable workflows from federated protocol repositories
version: 2.0.0
category: protocols
author: waldronlab
tags: [workflow, protocol, pipeline, method_origin_citation, provenance]
---

# protocol-runner

Finds and executes citable, versioned analysis protocols from federated repositories, ensuring reproducible agent behavior and correct attribution of methods and underlying literature.

## Usage

- "Run the 16S quality control protocol"
- "Search for a metagenomics taxonomy protocol and run it"
- "Can you follow the waldronlab/agent-protocols version of the 16S pipeline?"

## Prerequisites

- Network access to fetch `registry.yaml` and `PROTOCOLS.yaml` indices over HTTPS from the protocol registry and protocol repositories (e.g., from a git hosting service such as GitHub).

## Process

### 1. Discover Available Protocols

1. Read `registry.yaml` from the `waldronlab/agent-protocol-standard` repository (or whatever repository the user specified, defaulting to `https://raw.githubusercontent.com/waldronlab/agent-protocol-standard/main/registry.yaml`).
2. For each registered entry in that file, fetch its `PROTOCOLS.yaml` index using its `index_url`. Each protocol entry carries the fields this skill relies on: `name`, `description`, `version`, `date`, `status`, `type` (`atomic` | `composite`), `method_origin_citation`, `protocol_citation`, `artifact_doi`, `collection_doi`, `license`, `protocol_url`, `upstream_repositories`, `database_urls`, `protocols_used`.
3. Merge all protocol entries from all fetched indices into a single available protocol list. **Carry the parent metadata onto each entry as you merge it**: `trust_tier` comes from the repository's entry in `registry.yaml`, and the repository name from the index's top-level `repository` field. Neither is a property of an individual protocol, and without them the ranking and display below have nothing to work with.

### 2. Match Protocol to Request

1. If the user named a specific repository or version — "the `waldronlab/agent-protocols` version", "v1.2.1 of independent-filtering-variance" — treat those as **hard filters**, applied before any ranking. If nothing matches exactly, say so and stop rather than falling back to a same-named protocol from another repository or a different release; silently substituting either breaks the provenance this skill exists to preserve.
2. Match the user's stated task to the remaining protocols using `name`, `description`, `category`, and `tags`.
3. If there are multiple matches, rank them by `trust_tier` (descending), and then by `status` (preferring `stable`).

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
   - Parse `protocol_citation`, which every protocol carries (ADR 0014). Where it differs from `collection_doi` it names a publication describing this procedure; where it equals `collection_doi` the protocol is a first definition published in that collection, and the two should not be cited twice.
   - Parse `method_origin_citation` where present, to extract the DOI or PMID of the method's origin (Level 2 Citation). It is optional: a protocol that originates no method — operating a tool, building a reference database — omits it, and that absence is not a defect to report.
   - For a composite protocol (`type: composite`), aggregate the `method_origin_citation` of each constituent atomic protocol listed in `protocols_used`. Where the composite carries one of its own — the composition was itself published as a method — cite it alongside the aggregated constituents.
2. **Important**: Before executing any code, emit the full Method Provenance block to the user using the following format, adapted for each protocol in the chain:

   ```markdown
   ## Method Provenance

   ### Protocol Citation (Level 1)
   Following: [Author] "[Protocol Title/Name]"
   Repository: [Repository Name], protocol: [Protocol Name] v[Version] ([date])
   Repository DOI: [collection_doi if present]
   Protocol DOI: [artifact_doi if present]
   Publication DOI: [protocol_citation — omit this line when it equals the Repository DOI above, which means this protocol is a first definition published there]
   Trust tier: [trust_tier]
   License: [license]

   ### Primary Literature to Cite (Level 2)
   This protocol implements methods from:
   - [The method's origin (DOI/PMID) from `method_origin_citation`, where the protocol carries one. Omit this section entirely when no protocol in the chain does: a protocol that originates no method has no primary literature to attribute, and inventing one is the failure this block exists to prevent]
   - [Composite protocols: the aggregated `method_origin_citation` values of all constituent atomic protocols that carry one]
   - [Composite protocols that carry their own `method_origin_citation`: that DOI/PMID as well, labelled as the method the composition itself proposes]
   ```

   *Note: If `artifact_doi` is present, cite it. If only `collection_doi` is present, ensure it is clearly displayed alongside the specific protocol name and version so the user knows which part of the repository was used.*

### 6. Execute Protocol

1. Follow the steps in the fetched protocol content in order.
2. **Resource Discovery**: Agents can discover and download pre-computed reference data and upstream tools using the `database_urls` and `upstream_repositories` YAML fields provided in the index.
3. Adapt the provided code to the user's specific environment, file paths, parameters, and organisms as necessary.
4. If a step cannot be followed exactly as written, or requires a different package version than specified, note this departure inline.

### 7. Record Departures

1. After execution completes, emit a final "Departures from protocol" section.
2. List any deviations made during execution (e.g., using a different parameter value, skipping a step, or substituting a package). This is a normal part of adapting a protocol; recording it is what matters for provenance.

### 8. Generate Draft Methods Section

1. **Narrative Synthesis:** Synthesize a publication-ready narrative Methods section describing the exact analysis steps performed.
   - If the protocol contains a `## Methods Template` section, use its text as the baseline phrasing structure and fill in actual runtime parameters and sample identifiers. Otherwise, construct clear academic prose.
2. **Inline Method & Tool Attribution (Level 2):** Embed underlying methodology and software citations directly into the narrative prose at the relevant steps using their DOIs/PMIDs (e.g., *"...using MetaPhlAn 4.2 (DOI: 10.1038/s41587-023-01688-w)"*).
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
5. A **Skill Execution Record**: a single closing line naming this skill and the `version` from its own frontmatter, so a reader of the transcript can tell which runner, at which version, produced everything above.

   > 🛠️ Skill executed: `protocol-runner` v`[version from this skill's frontmatter]` (`waldronlab/agent-protocol-standard`)

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
