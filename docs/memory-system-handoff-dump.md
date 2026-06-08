# Memory System Handoff Dump

Status: working-session handoff dump  
Purpose: preserve the full discussion state so a local agent such as Codex, Claude Code, or Hermes can continue writing and maintaining Agent Foundry documentation without losing the reasoning context.  
Generated from: ChatGPT session discussion about persistent memory, ChatGPT history export/import, Agent Foundry integration, research-to-knowledge transformation, harvest policy, and anti-drift requirements.  
Important intent: this file is a dump of discussion content, not a final design document and not merely an action plan.

## 0. How to Use This Dump

This document should be read before creating or modifying long-term docs in the `agent-foundry` repository. It is intended to be placed under `docs/` or used as input to create a formal document such as:

- `docs/memory-system-design.md`
- `docs/memory-harvest-lifecycle.md`
- `docs/memory-taxonomy.md`
- `docs/memory-triage-skill.md`
- `docs/memory-runtime-adapters.md`
- `docs/memory-sync-and-governance.md`

The local agent should not treat this dump as a final polished architecture. It should treat it as preserved discussion state, research notes, requirements, principles, provisional taxonomy, and unresolved design questions.

Current capability boundary:

- `current`: Agent Foundry currently has `practices/`, `assets/`, `workflows/`, `schemas/`, `indexes/`, `adapters/`, `runtime/`, `usage/`, `imports/`, and `docs/` as implemented repository structures.
- `current`: this file is evidence and handoff context under `docs/`; it is not a canonical memory schema or runtime adapter.
- `proposed`: future memory-system concepts such as `memory/projects/`, `knowledge/`, `research_memos/`, `project_memory`, memory record schemas, Memory Triage Skill, semantic/vector indexes, and MCP memory access remain design concepts until implemented through reviewed repository changes.
- `future`: agents should not create those proposed directories, write to them, or route artifacts into them unless a later task explicitly implements that architecture.

When using this dump, the local agent should first read existing Agent Foundry docs, especially:

- `README.md`
- `docs/system-design.md`
- `docs/offline-sync.md`
- `docs/lifecycle-compatibility.md`
- `docs/usage.md`
- `docs/commands.md`

The local agent should preserve existing Agent Foundry principles:

- The repository is the canonical source of truth.
- Runtime files under `~/.codex`, `~/.claude`, `~/.hermes`, ChatGPT project knowledge, and similar locations are downstream adapters.
- Agent memory, session summaries, chat exports, and external skills are evidence sources, not authorities.
- Human review gates durable practices, project memory, knowledge assets, and runtime adapter updates.
- Local-first and offline-capable operation are required.
- Sync should be safe, staged, reviewable, and non-destructive.
- Raw evidence may be sensitive and should not be treated the same as sanitized canonical records or generated adapters.

## 1. Core Motivation

The user has accumulated substantial long-term knowledge in ChatGPT conversations, including project-specific content such as W10 robot architecture, Hermes, Agent Foundry, and other engineering topics, as well as broader domain knowledge such as embodied intelligence, control theory, factory logistics, health, education, tooling, and personal/professional working preferences.

The motivating problem is not simply “export chat history.” The real problem is that valuable reasoning, research, conclusions, corrections, and project memory are trapped in a chat interface and are vulnerable to loss, drift, account migration, tool separation, and context-window limitations.

The user wants a system that can:

1. Preserve hard-won knowledge and insight collected through ChatGPT and agent sessions.
2. Support future account migration by dumping enough structured information that a new ChatGPT account or new agent runtime can recover useful context.
3. Distinguish raw chats from curated knowledge.
4. Support ongoing session-end or project-scoped harvest rather than one-time full dump.
5. Integrate ChatGPT memory with development-agent memory, especially Codex, Claude Code, Hermes, and Agent Foundry.
6. Allow offline, local-first operation with online and multi-machine sync.
7. Support project-specific memory, domain knowledge, professional profile, practices, and skills without collapsing them into one category.
8. Eventually support visualization, mind maps, Obsidian, and graph navigation, but not at the cost of the core memory system.
9. Avoid drift and loss during complex long-running design discussions.
10. Produce maintainable Markdown/Git-backed documentation and memory assets that can be edited by local agents.

A recurring theme is that this very discussion demonstrates the problem: as the conversation becomes complex, summaries can drift toward action planning and lose earlier research/knowledge-preservation goals. Therefore the memory system must explicitly preserve static research outputs, not just plans and skills.

## 2. Important Boundary: ChatGPT Internal Memory Is Not the Source of Truth

A major early conclusion was that ChatGPT’s internal memory should not be treated as the canonical memory store.

Reasons discussed:

1. ChatGPT chat history export and ChatGPT internal memory are different things.
2. ChatGPT internal memory is a product-managed personalization layer, not a structured, versioned, auditable knowledge database.
3. Saved memories and reference chat history may be useful, but should be treated as evidence or input signals.
4. Complete, structured, reliable export/import of internal ChatGPT memory cannot be assumed.
5. ChatGPT and Codex conversations are separate product contexts; using the same account does not mean Codex inherits this ChatGPT thread.
6. Therefore a user-controlled memory vault must be the source of truth.

The durable system should therefore treat the following as evidence sources:

- ChatGPT conversation exports
- ChatGPT saved memory copied manually
- ChatGPT “what do you know about me / this project” summaries
- Session-end summaries
- Codex sessions
- Claude Code sessions
- Hermes logs
- Pull requests
- commits
- design docs
- scripts
- terminal logs
- user-created notes
- external research sources

But canonical knowledge must live in a controlled repository or vault.

## 3. Relationship to Agent Foundry

Agent Foundry already has the right philosophical basis:

- It is local-first.
- It treats durable knowledge and runtime delivery as separate.
- It uses practices, assets, adapters, usage evidence, workflows, schemas, and scripts.
- It treats agent memory and session summaries as evidence sources.
- It requires human approval before durable rules become active.
- It publishes downstream adapters for different environments.
- It supports offline snapshot/sync design.

The memory system should extend Agent Foundry rather than replace it.

However, the current discussion expands Agent Foundry from “practice/skill foundry” toward a broader “memory and knowledge foundry.” This includes:

- project memory
- domain knowledge
- research memos
- source digests
- professional profile
- working preferences
- decision records
- not-adopted records
- open questions
- runtime adapter updates
- practices
- skills

A key distinction emerged:

- `practices/` are durable cross-project rules, heuristics, patterns, playbooks, checklists, anti-patterns, and examples.
- `assets/` are reusable skills, subagents, automations, and packages.
- `memory/projects/<project>/` should hold project-specific facts, decisions, rationales, interfaces, constraints, deprecated assumptions, and state.
- `knowledge/domains/<domain>/` should hold reusable domain knowledge and research notes.
- `profile/` or similar should hold professional profile and working preferences.
- `imports/` or `evidence/` should hold staged/raw external or session-derived material.

The system should not force every valuable conversation artifact into “practice” or “skill.” Many important outputs are static reference knowledge.

## 4. Phase 1 Priority Correction: Preserve Knowledge and Research Outputs First

A later correction was important: the initial version of the design drifted too quickly toward action plans, skills, practices, and runtime behavior. The user explicitly corrected this.

Current priority for the initial phase:

- Preserve painstakingly collected and synthesized knowledge.
- Preserve research outputs such as the memory-to-knowledge framework comparison.
- Make such outputs available for future learning, reference, and reuse.
- Use Obsidian/Markdown/Git-compatible storage.
- Do not prematurely force every insight into skill, practice, or behavior plan.
- Do not build an automatic agent self-improvement pipeline before a stable knowledge asset layer exists.

Phase 1 should therefore emphasize:

- research memo capture
- structured static knowledge notes
- source digests
- concept notes
- decision context
- project/domain cross-linking
- session indexes
- low-cost triage
- human review
- Markdown/Obsidian readability
- Git-backed maintainability

Phase 1 should not primarily emphasize:

- automatic agent behavior modification
- automatic skill creation
- automatic adapter publishing
- full temporal knowledge graph implementation
- full autonomous memory CRUD
- all-chat auto-harvest

The static knowledge layer remains active and maintainable, not dead text. Each note should have metadata, links, status, source, and review hooks.

## 5. Memory-to-Knowledge Research Findings

The session included a research pass over agent memory frameworks, knowledge management theory, and related projects. The following findings should be preserved as knowledge, not reduced to implementation tasks.

### 5.1 Agent Memory Taxonomy: Episodic, Semantic, Procedural, Profile, Runtime Adapter

A recurring framework is to distinguish memory types:

- Episodic memory: records of events, conversations, actions, sessions, traces, logs.
- Semantic memory: facts, concepts, definitions, project facts, domain knowledge.
- Procedural memory: rules, workflows, practices, playbooks, skills, scripts.
- Profile/preference memory: user preferences, professional profile, stable working style, project profile.
- Runtime adapter: derived instruction/context forms for specific agent tools, not canonical memory.

Applied to this system:

- Raw ChatGPT conversation = episodic evidence.
- “W10 VLA outputs 10–30Hz joint references, not trajectories” = semantic project fact.
- “When reviewing W10 motion architecture, check planning path vs learned servo path distinction” = procedural/practice candidate.
- “User prefers deep technical reasoning and dislikes oversimplified action plans” = working preference/profile memory.
- `AGENTS.md`, `CLAUDE.md`, `SKILL.md`, ChatGPT Project Knowledge = runtime adapters.

The system must not collapse these categories.

### 5.2 LangChain / LangGraph Memory Lessons

LangChain-like memory frameworks support a useful distinction:

- short-term memory is thread/session-scoped;
- long-term memory persists across threads/sessions;
- long-term memory can be semantic, episodic, or procedural;
- semantic memory may be represented as profile or as a collection.

Design implications:

- User/project profile should be compact and stable.
- Project facts and research notes should be stored as collection records, not one giant profile.
- Profile update is risky as it grows; collection-style memory is easier to add to but harder to search and consolidate.
- Memory writing can happen on the hot path or in the background.
- For this system, background/session-end harvest is preferred for most durable memory.
- Hot-path memory writes should be rare and reserved for explicit, stable, high-confidence updates.

### 5.3 MemGPT / Letta Lessons

MemGPT/Letta-style virtual context management suggests that memory should be layered like an operating system memory hierarchy:

- current context
- working memory
- retrieved memory
- archival memory
- external storage

Design implications:

- Do not load all memory into prompt/context.
- Use a memory manager to decide what to retrieve, keep, summarize, archive, or page in.
- Canonical memory can live in Markdown/Git while runtime retrieval uses indexes or MCP.
- The system should separate archival source-of-truth from runtime context packing.

### 5.4 Mem0 Lessons

Mem0-like systems emphasize that production memory needs more than embeddings:

- add/search/update/delete operations
- metadata
- workspace governance
- audit logs
- evaluations
- optional graph memory

Design implications:

- Even if Agent Foundry remains Markdown-first, it should define memory CRUD semantics.
- Every memory change should be auditable.
- Memory entries need metadata and lifecycle states.
- Evaluation and usage evidence matter.

### 5.5 Zep / Graphiti Lessons

Graphiti was discussed as a temporal knowledge graph approach:

- it stores evolving context as a temporal graph;
- it handles changing relationships;
- it preserves provenance;
- it supports hybrid search combining semantic, full-text, and graph traversal;
- it processes discrete episodes.

Design implications:

- Time and change must be first-class.
- Decisions can be superseded.
- “Not adopted” and “deprecated” are important record types.
- Project memory must preserve why old ideas were rejected or replaced.
- A graph index is useful, but should initially be a derived index, not the source of truth.

### 5.6 A-MEM Lessons

A-MEM is important because it combines agentic memory with Zettelkasten-like organization:

- new memories are stored as structured notes with attributes such as context, keywords, and tags;
- the system links new memories to historical memories;
- new memories can update old memories’ contextual representation;
- memory evolves, rather than merely accumulating.

Design implications:

- New records should not just append; they may update links, status, tags, and context of older records.
- Adding a new W10 design decision may supersede old decisions.
- Memory consolidation is not just summarization; it is graph/link/status evolution.
- Link and Consolidate stages are essential.

### 5.7 MemMachine / Ground-Truth Preservation Lessons

MemMachine-like ideas emphasize preserving raw episodes because early lossy summarization can drop important details.

Design implications:

- Raw evidence should remain available.
- Canonical memory should be a derived layer.
- Retrieval should sometimes return to raw episode context.
- Source/provenance is mandatory.
- Summaries should not erase design constraints, rejected options, or evidential context.

### 5.8 gstack Lessons

gstack was discussed as a workflow/skill compounding framework, not primarily a memory framework.

Key observed ideas:

- It packages Claude Code workflows into specialists, slash commands, and Markdown skills.
- It proceduralizes repeated engineering workflows.
- It shows how experience can become commands and skills.
- It is closer to the runtime/procedural adapter layer than to canonical memory.

Design implications:

- gstack is relevant for the later skill/practice layer.
- It should not drive Phase 1 knowledge preservation.
- Agent Foundry can use similar adapter patterns when a knowledge item matures into a practice or skill.
- Proceduralization should happen after evidence and knowledge have stabilized.

### 5.9 Multica Lessons

Multica was discussed as a managed agents platform.

Observed relevance:

- It positions agents as team members handling tasks.
- It tracks progress and reusable skills.
- It uses a web/backend/daemon architecture and can connect to coding agents.
- It suggests that memory and skills can be part of a task execution platform.

Design implications:

- Managed agent runtime and memory foundry are related but different.
- Agent Foundry should remain the knowledge/practice/adapter source of truth.
- A future runtime manager can use memory outputs, but should not be conflated with the memory repository.

### 5.10 Reflexion, Voyager, Generative Agents

Three research patterns were discussed:

Reflexion:
- turns task feedback into verbal reflections;
- stores them to improve future decisions;
- useful for session-end reflection and practice candidates.

Voyager:
- turns successful behaviors into executable skill libraries;
- useful for eventual skill packaging.

Generative Agents:
- stores observations, produces reflections, and uses them in planning;
- useful for raw episode + reflection + planning context architecture.

Design implication:

- Research memo, reflection, practice, and skill are different outputs.
- The system should not turn every insight into a skill immediately.

### 5.11 SECI Model

SECI was used as a theoretical lens:

- Socialization: tacit-to-tacit sharing.
- Externalization: tacit-to-explicit articulation.
- Combination: explicit-to-explicit synthesis.
- Internalization: explicit-to-tacit behavior/practice.

Applied to this system:

- User intuition and project experience become explicit through ChatGPT conversation.
- Session harvest externalizes and structures that knowledge.
- Canonical notes combine and reconcile knowledge.
- Runtime adapters and skills help agents internalize the knowledge into future behavior.

This maps well to the desired loop:

```text
Tacit intuition / project experience
  -> conversation externalization
  -> structured memory extraction
  -> canonical combination
  -> adapter publication
  -> agent/runtime internalization
  -> usage evidence
  -> review and revision
```

### 5.12 PKM / PIM / Zettelkasten

PKM/PIM and Zettelkasten were used to justify why knowledge should not be forced into one folder or one project.

Key lessons:

- Personal knowledge management is cyclical: acquire, classify, store, maintain, retrieve, use.
- Zettelkasten emphasizes small linked notes with metadata, tags, IDs, and cross-references.
- Classification exists to support future use, not aesthetic taxonomy.
- A note may belong to multiple contexts.
- Directory path is only one view; metadata and links are more important.

Design implication:

- Markdown/Obsidian can be a human-facing layer.
- Frontmatter should carry machine-readable metadata.
- Cross-links should connect project decisions to domain knowledge.
- The vault should support multiple views: project, domain, source, practice, profile, runtime.

### 5.13 Records Continuum

Records continuum theory was invoked to support provenance and evidence from the moment of capture.

Design implications:

- Capture should preserve source metadata immediately.
- A raw conversation is both record and evidence.
- Memory entries need provenance, not just content.
- Evidence should remain traceable even after summaries are generated.
- Raw evidence, canonical records, and public/shared adapters need different privacy/sync treatment.

### 5.14 Cognitive Architecture / CoALA / Soar

Cognitive architecture ideas were discussed to show that agent memory is not merely a storage layer.

Relevant distinctions:

- working memory
- semantic memory
- episodic memory
- procedural memory
- decision/action mechanisms

Design implications:

- The system should eventually integrate memory with agent action and retrieval.
- However, Phase 1 should not prematurely build the full cognitive runtime.
- The architecture should keep room for future memory manager and retrieval policies.

## 6. Full Memory-to-Knowledge Lifecycle

The original discussion produced a 12-stage lifecycle, later corrected because stages `0` and `2.5` were awkward. The cleaned lifecycle below uses continuous numbering and incorporates activation and triage as first-class stages.

### Stage 1: Intent and Scope Activation

Decide whether the session should enter the memory pipeline at all.

This includes:

- whether harvest is enabled;
- which project/domain/profile scope applies;
- whether the user explicitly requested saving;
- whether default privacy should be local-only;
- whether the session is likely ephemeral;
- which work context is active.

This stage prevents global indiscriminate harvesting.

### Stage 2: Capture

Preserve raw evidence when appropriate.

Inputs may include:

- ChatGPT thread
- copied ChatGPT memory
- session-end summary
- Codex/Claude/Hermes transcript
- source URLs
- files
- diffs
- terminal logs
- screenshots
- design artifacts
- manually written notes

Capture should be low-loss but privacy-aware.

### Stage 3: Segment

Split long material into coherent units.

Segmentation should be based on meaning, not token length only. Useful segment types include:

- topic episode
- decision episode
- research episode
- implementation episode
- troubleshooting episode
- reflection episode
- source assimilation episode
- design correction episode

### Stage 4: Triage

Determine which segments deserve deeper extraction, what artifact lanes they should produce, and what saving level is appropriate.

Triage is a distinct skill and should not be confused with summarization.

It should output:

- recommended save level
- primary work context
- secondary work contexts
- artifact lanes
- evidence of high-value signals
- review cost estimate
- future value estimate
- suppression reasons
- privacy/safety flags

### Stage 5: Extract

Extract candidate knowledge from selected segments.

Candidate types include:

- facts
- concepts
- decisions
- rationales
- assumptions
- not-adopted options
- deprecated assumptions
- open questions
- procedures
- preferences
- profile updates
- skills
- research conclusions
- source summaries
- adapter update suggestions

### Stage 6: Type and Scope

Assign memory type and scope.

Typing answers “what kind of thing is this?”

Scoping answers “where can it be useful?”

Both must support multiple labels.

### Stage 7: Normalize

Convert extracted candidates into structured record format.

Normalization should include:

- stable ID
- title
- kind
- scope
- status
- claim
- rationale
- evidence/source
- confidence
- privacy
- validity/review timing
- related records
- supersedes/superseded-by
- publish flags
- body content

### Stage 8: Link

Connect new records to existing knowledge.

Links may include:

- related concepts
- project decisions
- source digests
- raw episodes
- earlier assumptions
- superseded records
- open questions
- generated adapters
- practices/skills

This stage is central to preventing isolated notes.

### Stage 9: Consolidate

Merge, revise, supersede, or split records.

New knowledge may:

- create a new record;
- add evidence to an old record;
- revise an active record;
- supersede a deprecated record;
- close an open question;
- split a broad note into smaller notes;
- merge duplicate notes;
- downgrade a claim to reference-only.

This is where memory evolution happens.

### Stage 10: Validate and Govern

Apply review gates.

This includes:

- human approval;
- confidence checks;
- source reliability;
- safety/risk classification;
- stale information check;
- privacy review;
- dedupe validation;
- schema validation.

Agents may propose changes but should not silently promote candidates to active durable knowledge.

### Stage 11: Publish

Generate downstream artifacts.

Possible outputs:

- Obsidian-compatible Markdown
- ChatGPT project knowledge pack
- Codex context
- AGENTS.md
- CLAUDE.md
- Hermes SKILL.md
- skills
- scripts
- MCP resources
- semantic index
- graph index

Publishing is derived from canonical memory and should be reproducible.

### Stage 12: Recall and Use

Use memory in future sessions and agents.

Recall can be:

- manual via Obsidian/Git search
- semantic/vector search
- full-text search
- graph traversal
- MCP resource retrieval
- context pack loading
- adapter instructions

Recall should be task- and scope-aware, not all-memory injection.

### Stage 13: Review, Forget, and Revise

Maintain the memory system over time.

This includes:

- stale memory detection;
- conflicting record review;
- low-value record archiving;
- usage evidence review;
- adapter drift checks;
- revising old records when new evidence arrives;
- forgetting or isolating sensitive/obsolete items.

This stage is necessary because long-term memory can become harmful if outdated or invalid memories continue to guide behavior.

## 7. Work Context, Artifact Lane, and Lifecycle Intent

A major refinement was that simple harvest modes are insufficient. Instead of six mutually exclusive modes, the system should use a multidimensional model:

```text
Work Context × Artifact Lane × Lifecycle Intent
```

Harvest is not a category picker. It is a scoped, evidence-aware triage and artifact-routing policy embedded in the full memory lifecycle.

### 7.1 Work Context

Work Context describes the situation or activity type of the session.

Important contexts discussed:

1. Deep Research Session  
   Long-form research, framework comparison, external source synthesis, theory exploration.

2. Project-Embedded Micro Research  
   Research performed inside a project to answer project-specific questions. Example: discussing control theory or factory turnover boxes inside W10 project context.

3. Architecture / System Design Session  
   Architecture, interfaces, module boundaries, tradeoffs, lifecycle, system evolution.

4. Artifact Review / Consistency Check  
   Reviewing docs, diagrams, tables, versions, contradictions, or design consistency.

5. Implementation / Vibe Coding Session  
   Coding, debugging, scripts, environment repair, quick iteration.

6. Toolchain / Environment Setup  
   macOS, zsh, proxy, Docker, VM, VPS, CI, local setup.

7. Agent Workflow Design  
   Discussion of agent frameworks, memory, skills, runtime adapters, harvest process.

8. Project State Update  
   Current state, progress, blockers, next actions, milestone snapshots.

9. External Source Assimilation  
   Reading and digesting papers, repos, product docs, web pages, standards.

10. Decision / Tradeoff Closure  
   Comparing alternatives and reaching a decision or non-decision.

11. Professional Profile / Working Preference Update  
   Stable professional interests, working style, collaboration preferences, anti-preferences.

12. Ephemeral Q&A / Disposable Assistance  
   One-off questions with little long-term value.

These are not mutually exclusive.

### 7.2 Artifact Lane

Artifact Lane describes what should be produced.

Important lanes discussed:

1. Session Index  
   Minimal record: title, date, scope, short summary, possible follow-up.

2. Research Memo  
   Long-form research output for future learning and reference.

3. Source Digest  
   Summary and evaluation of external sources, repos, documents, or papers.

4. Concept Note  
   Explanation of a concept, theory, term, taxonomy, or framework.

5. Project Fact  
   Current project fact, constraint, interface, environment, version, or state.

6. Decision Record  
   Decision, alternatives, adopted option, rejected options, rationale.

7. Design Rationale  
   Why a design was chosen, what background influenced it.

8. Open Question  
   Unresolved questions, hypotheses, validation tasks.

9. Deprecated / Not-Adopted Record  
   Old assumptions, rejected options, reasons for non-adoption.

10. Practice Candidate  
    Reusable rule, heuristic, checklist, anti-pattern, working principle.

11. Skill / Automation Candidate  
    Reusable workflow, script, command, agent skill, automation.

12. Profile / Preference Update  
    Long-term professional profile or working preference update.

13. Runtime Adapter Update  
    AGENTS.md / CLAUDE.md / SKILL.md / ChatGPT project knowledge update suggestion.

14. Evidence Attachment  
    Raw transcript, diff, log, source link, screenshot, file reference.

### 7.3 Lifecycle Intent

Lifecycle Intent describes how strongly the artifact should affect future use.

Important intents:

1. Archive Only  
   Save only; no active use.

2. Reference  
   Searchable and readable, but not authoritative.

3. Project Context  
   Usable as background for a project.

4. Decision Authority  
   Active project fact or decision that should affect agent behavior.

5. Practice Candidate  
   Possible future practice after review.

6. Skill Candidate  
   Possible future skill/automation after review.

7. Runtime Instruction  
   Should be published into agent context/adapters.

8. Profile Memory  
   Should influence cross-project personalization, used cautiously.

This model allows combinations such as:

```text
W10 project micro research about factory logistics
  Work Context:
    Project-Embedded Micro Research
  Artifact Lanes:
    Source Digest
    Concept Note
    Design Rationale
    Not-Adopted Record
  Lifecycle Intent:
    Reference
    Project Context
    maybe Decision Authority
  Runtime Publication:
    ChatGPT project maybe
    Codex maybe not
    global profile no
```

## 8. Harvest Activation and Saving Levels

The system should avoid automatically harvesting all chats. It should use explicit activation, project-level enablement, and session-level confirmation.

### 8.1 Activation Sources

A session can enter harvest when:

- user explicitly asks to save, harvest, record, or dump;
- the current project has harvest enabled;
- the session contains high-value signals;
- the user triggers a command such as `/harvest research`;
- the session is part of a known workstream such as W10, Agent Foundry, Hermes, or professional profile;
- the session ends and a lightweight triage suggests value.

However, high-value signal detection should not silently write active memory. It should propose.

### 8.2 Save Levels

A tiered save-level model was proposed:

- L0: No harvest  
  Do not save beyond normal chat history/export.

- L1: Session index only  
  Save a light index for future discovery.

- L2: Structured knowledge note  
  Save research memo, source digest, concept note, or project note.

- L3: Canonical memory patch / practice / skill candidate  
  Requires stronger review and may update active records.

Most ad hoc chats should be L0/L1.

Research sessions like the current memory-system discussion should be L2.

Vibe coding that reveals reusable procedures may produce L3 practice or skill candidates.

## 9. Memory Triage Skill

The user emphasized that “high-value signal” detection is good but must be implemented with quality. This led to the idea of an explicit Memory Triage Skill.

### 9.1 Role

Memory Triage Skill is responsible for deciding whether a session or segment deserves memory processing and how it should be routed.

It is not the summarizer.

It should answer:

- Is this worth saving?
- What kind of work context is this?
- What artifact lanes are appropriate?
- What saving level?
- Which segments should be ignored?
- What review is needed?
- Is this sensitive, stale, risky, or low-confidence?
- Does this indicate a profile/working preference update?
- Does this suggest a practice or skill candidate?

### 9.2 Components

The skill should include:

1. Signal detector  
   Detects valuable signals.

2. Artifact recommender  
   Recommends output artifacts.

3. Scope resolver  
   Assigns project/domain/profile/toolchain/runtime scopes.

4. Quality and cost controller  
   Estimates future value and review burden.

5. Suppression filter  
   Avoids harvesting repeated, low-value, ephemeral, sensitive, or already-known content.

6. Feedback loop  
   Learns from user accept/reject and later usage.

### 9.3 High-Value Signals

High-value signals discussed include:

Knowledge value signals:

- long-form research synthesis
- external source comparison
- conceptual framework creation
- terminology/taxonomy creation
- non-obvious insight
- correction of prior misconception
- cross-domain mapping
- explicit unresolved issue

Project value signals:

- architecture decision
- interface agreement
- module boundary
- system lifecycle change
- project state update
- risk identification
- version inconsistency
- deprecated assumption
- not-adopted option

Practice value signals:

- repeated error
- reusable workflow
- review checklist
- anti-pattern
- debugging pattern
- toolchain setup
- automatable script

Profile value signals:

- stable professional direction
- long-term working preference
- recurring dissatisfaction with assistant behavior
- preferred reasoning/format style
- cross-project collaboration preference

Negative/suppression signals:

- one-off Q&A
- pure phrasing edits
- duplicate material
- low confidence
- no source
- easily outdated facts
- sensitive/private raw material
- unsupported medical/legal/financial claims
- content unlikely to be reused

### 9.4 Example Triage Output

```yaml
harvest_triage:
  primary_context: project_embedded_micro_research
  secondary_context:
    - architecture_design
  recommended_level: L2
  recommended_lanes:
    - source_digest
    - design_rationale
    - open_question
  high_value_signals:
    - type: external_source_comparison
      strength: 0.8
      evidence: "Compared multiple agent memory frameworks."
    - type: conceptual_framework_created
      strength: 0.9
      evidence: "Created a lifecycle for memory-to-knowledge."
    - type: project_design_implication
      strength: 0.85
      evidence: "Impacts Agent Foundry memory subsystem design."
  do_not_harvest:
    - "repeated confirmations"
    - "temporary wording"
  review_required: true
  estimated_review_cost: medium
  expected_future_value: high
```

### 9.5 Skill Introduction Strategy

The triage skill should be introduced gradually:

Stage A: rule + LLM rubric  
Use explicit scoring and structured output.

Stage B: evidence calibration  
Record triage decisions, user accept/reject, later usefulness.

Stage C: personalized learned policy  
Use accumulated feedback to adapt the triage rubric.

## 10. Project-Embedded Micro Research

This was identified as a critical missing mode.

Problem:

Within project work, the user often researches general domain material. Example: W10 discussions may include embodied intelligence, control theory, or factory turnover boxes. These are not pure project decisions, but they are not unrelated research either.

The system should not force them into either “project memory” or “domain knowledge” exclusively.

Correct handling:

1. Save general knowledge in domain/reference layer.
2. Save project impact in project rationale/decision/open question layer.
3. Link the two.

Example:

```text
Domain artifact:
  knowledge/domains/factory-logistics/source-digest/container-types.md

Project artifact:
  memory/projects/W10/rationale/turnover-box-relevance.md

Link:
  W10 rationale depends_on domain source digest.
```

Project-side artifact should answer:

- Why was this research done?
- What did it imply for the project?
- Was anything adopted?
- Was anything explicitly not adopted?
- What open questions remain?
- Should the project agent use this knowledge?

Domain-side artifact should preserve the broader research output for future reuse.

This prevents the project memory from being flooded with background detail, while also preserving hard-won research.

## 11. Professional Profile and Working Preferences

The user corrected that “personal reflection” is not the important profile area. The user’s priority is professional profile, working style, and project/agent collaboration preferences.

Therefore profile should be split into:

1. Professional Profile  
   Long-term technical direction, engineering role, domains of interest, project focus.

2. Working Preferences  
   Preferred reasoning style, output format, review style, dislike of premature simplification, desire for careful comparison and convergence, desire for documentable conclusions.

3. Personal Reflection  
   Life reflections, lower priority for this system and not default input to coding agents.

Professional profile and working preferences can be high-value memory, but should be handled cautiously. They may affect ChatGPT global instructions, Codex behavior, Claude Code instructions, or Agent Foundry adapter rules.

Current important working-preference facts from this session:

- The user wants complex systems discussions to avoid drift and loss.
- The user distrusts oversimplified local designs that forget the whole-system complexity.
- The user values research outputs as durable knowledge, not merely action plans.
- The user notices that the assistant tends to drift toward action planning.
- The user wants memory systems precisely to preserve complex evolving context.
- The user wants architecture-clear, maintainable documents.
- The user wants staged discussion before final docs.
- The user prefers local-first, Markdown/Git-backed, editable knowledge.

These are candidates for working preference memory, but they should not be blindly promoted without review.

## 12. Static Research Output as First-Class Knowledge Asset

A major design correction:

The system should preserve static research outputs such as the memory-framework research summary. These are not just evidence for later practices. They are useful future learning/reference materials.

Research memo should be first-class.

Potential record types:

- `research_memo`
- `source_digest`
- `concept_note`
- `framework_comparison`
- `theory_note`
- `literature_note`

A research memo may later contribute to:

- project rationale
- practice
- skill
- adapter
- decision record

But it should not be forced into those forms prematurely.

For example, the memory-to-knowledge framework research should be preserved as a research memo with:

- problem framing
- source frameworks
- theory frameworks
- engineering implications
- mapping to Agent Foundry
- unresolved questions
- citations
- future design inputs

## 13. Raw Evidence vs Canonical Knowledge vs Adapter

A persistent design principle:

```text
Raw evidence != canonical knowledge != runtime adapter
```

Raw evidence includes:

- chat transcripts
- logs
- file diffs
- raw exports
- copied memories
- screenshots
- source files
- external links

Canonical knowledge includes:

- research memos
- concept notes
- project facts
- decision records
- domain notes
- practices
- skills
- profile records

Runtime adapters include:

- ChatGPT project knowledge pack
- AGENTS.md
- CLAUDE.md
- SKILL.md
- MCP resources
- local instruction files
- generated context packs

Adapters are downstream and regenerable. Canonical memory should preserve durable content, rationale, lifecycle, and relationships. Raw evidence should remain available for audit but may be local-only or privacy-limited.

## 14. Proposed Repository / Vault Shape

Several possible directory structures were discussed. A future formal doc should refine this.

Potential structure:

```text
agent-foundry/
  memory/
    projects/
      W10/
        project-profile.md
        current-state.md
        facts/
        decisions/
        rationale/
        interfaces/
        open-questions/
        deprecated/
        session-summaries/
    profile/
      professional-profile.md
      working-preferences.md
      personal-reflections.md
    indexes/
      memory-index.yaml
      source-index.yaml
      project-index.yaml

  knowledge/
    domains/
      embodied-intelligence/
      control-theory/
      factory-logistics/
      agent-memory/
      health/
    research-memos/
    source-digests/
    concept-notes/

  imports/
    chatgpt/
      raw/
      saved-memory/
      staged/
      extracted/
    codex/
    claude-code/
    hermes/

  evidence/
    local/
    shared/

  workflows/
    harvest-session.md
    memory-triage.md
    review-memory-patch.md
    publish-memory-adapters.md

  schemas/
    memory-record.schema.yaml
    research-memo.schema.yaml
    memory-patch.schema.yaml
    triage-report.schema.yaml

  scripts/
    import_chatgpt_export.py
    harvest_session_memory.py
    propose_memory_patch.py
    check_memory_consistency.py
    publish_project_adapters.py

  adapters/
    chatgpt/
    codex/
    claude-code/
    hermes/
```

This is not final. It should be reconciled with existing Agent Foundry structure.

Important question: Should `knowledge/` be top-level or under `memory/`? The discussion has not resolved this.

A likely distinction:

- `memory/` = project/profile/current durable memory
- `knowledge/` = research/domain/reference knowledge
- `practices/` and `assets/` remain as currently defined in Agent Foundry

But this may create too many top-level areas. A formal design should compare alternatives.

## 15. Record Types and Metadata

Provisional record types discussed:

- `research_memo`
- `source_digest`
- `concept_note`
- `project_fact`
- `architecture_decision`
- `decision_record`
- `design_rationale`
- `interface_contract`
- `terminology`
- `constraint`
- `assumption`
- `not_adopted`
- `deprecated_assumption`
- `open_question`
- `procedure`
- `practice_candidate`
- `skill_candidate`
- `profile_update`
- `working_preference`
- `runtime_adapter_update`
- `session_index`
- `source_summary`

Provisional metadata fields:

```yaml
id:
title:
kind:
scope:
  - project:
  - domain:
  - profile:
  - toolchain:
status:
claim:
summary:
rationale:
source:
evidence:
confidence:
privacy:
validity:
review:
related:
supersedes:
superseded_by:
publish:
  chatgpt_global:
  chatgpt_project:
  codex:
  claude_code:
  hermes:
  obsidian_only:
created:
updated:
owner:
```

Status values discussed:

- candidate
- proposed
- active
- background
- reference_only
- not_adopted_now
- revised
- superseded
- archived
- needs_verification

The schema should support multi-scope records and links.

## 16. ChatGPT Export / Import and Account Migration

The account migration goal was discussed.

Important conclusions:

- Do not rely on ChatGPT internal memory as canonical.
- ChatGPT data export is raw evidence.
- Saved memory copied from ChatGPT is also evidence/candidate profile input.
- A new account should be bootstrapped from a generated migration pack, not from raw chat dumps alone.
- Only stable global user preferences should go into ChatGPT global memory.
- Project knowledge should go into ChatGPT Project files/knowledge, not global memory.

Suggested migration pack shape:

```text
chatgpt-migration-pack/
  00_README_IMPORT_ORDER.md
  01_user_profile.md
  02_global_working_preferences.md
  03_project_index.md
  projects/
    W10/
      00_W10_current_state.md
      01_W10_architecture_decisions.md
      02_W10_runtime_terms.md
      03_W10_interfaces.md
      04_W10_open_questions.md
      05_W10_deprecated_assumptions.md
  agent_foundry/
    active_practices_summary.md
    adapter_usage.md
```

The import order matters:

1. User/global profile, very compact.
2. Working preferences, carefully curated.
3. Project index.
4. Project-specific packs.
5. Agent Foundry practices/adapters.
6. Raw history only if needed for search/reference, not for active memory.

## 17. Codex Handoff and Role Split

The user considered switching to Codex because Codex can directly write local docs.

Discussion conclusion:

- It is not safe to assume no quality degradation or no context loss when moving from ChatGPT app to Codex.
- ChatGPT and Codex conversations are separate contexts.
- Codex is strong as a local repo execution and editing agent.
- ChatGPT is better suited to high-level long-form architecture discussion and reflective reasoning in this session.
- Best workflow: ChatGPT creates high-quality handoff dump/spec; Codex reads it and writes/edits docs in the local repo.

Recommended role split:

ChatGPT:
- architecture reasoning
- deep research
- synthesis
- drift correction
- handoff dumps
- design review

Codex:
- read local files
- write docs
- edit Markdown
- generate scripts
- run checks
- show diffs
- commit changes if approved

Suggested Codex prompt:

```text
Read docs/memory-system-handoff-dump.md, README.md, docs/system-design.md, docs/offline-sync.md, docs/lifecycle-compatibility.md.

Create an initial maintainable design document under docs/memory-system-design.md.

Do not change repository structure yet.

Preserve unresolved questions explicitly.

Do not reduce the system to action plans or skills. Preserve research outputs as first-class knowledge assets.

Show me the diff before committing.
```

## 18. Anti-Drift Requirement

The user explicitly emphasized that complex system discussions must avoid drift and loss.

This became a meta-requirement:

- The assistant must not gradually forget earlier high-level complexity.
- The system itself exists to prevent this kind of drift.
- Summaries must not collapse research outputs into action plans.
- Docs must preserve both “what we plan to do” and “what we learned.”
- The memory system must track unresolved concerns and corrections.
- Periodic reflection should be built into the discussion process.

Potential anti-drift mechanisms:

1. Maintain handoff dumps at major discussion checkpoints.
2. Preserve “design principles” separately from implementation plans.
3. Maintain “unresolved questions” explicitly.
4. Track “corrections to prior assistant drift.”
5. Use session indexes even for discussions not fully harvested.
6. Require local docs to distinguish research, requirements, architecture, and action items.
7. Use memory triage to identify when the assistant/user corrected drift.

## 19. Requirements and Design Principles Accumulated So Far

### 19.1 Core Requirements

1. Local-first canonical memory.
2. Markdown/Git-compatible.
3. Obsidian-readable.
4. ChatGPT account migration support.
5. Cross-agent runtime support.
6. Project memory and domain knowledge both supported.
7. Static research outputs preserved.
8. Practices and skills supported later but not over-prioritized in Phase 1.
9. Harvest is scoped and economical, not global automatic ingestion.
10. Triage skill detects value and routes artifacts.
11. Multi-dimensional context/lane/intent model.
12. Raw evidence and canonical memory separated.
13. Human review for durable memory.
14. Offline/online/multi-machine support.
15. Runtime adapters are generated downstream.
16. Memory evolves: link, consolidate, supersede, revise.
17. Stale/invalid memory must be reviewable and forgettable.
18. Professional profile and working preferences are first-class.
19. Personal reflection is lower priority for this use case.
20. Anti-drift and checkpointing are explicit goals.

### 19.2 Design Principles

1. Memory is typed progressively, not classified once.
2. Harvest is not a category picker.
3. Directory path is a view; metadata and links carry semantics.
4. Raw evidence is ground truth but not active knowledge.
5. Canonical memory is reviewed and structured.
6. Adapters are downstream and regenerable.
7. Static research notes are first-class knowledge assets.
8. Not-adopted and deprecated records are important.
9. Project-embedded micro research must produce both domain-side and project-side artifacts.
10. Review burden is a product requirement.
11. Cost discipline is part of the system.
12. Avoid premature skillification.
13. Avoid all-chat auto-harvest.
14. Use session-level confirmation even when project-level harvest is enabled.
15. Use compact runtime context plus retrieval rather than full memory injection.
16. Preserve source and provenance at capture time.
17. Treat professional profile separately from life reflection.
18. Keep Phase 1 narrow in implementation but broad in conceptual architecture.

## 20. Unresolved Questions

The following questions remain open and should be carried into future design docs.

### 20.1 Scope and Directory Structure

Should domain knowledge live under `knowledge/`, under `memory/knowledge/`, or inside Agent Foundry’s existing `docs/`/`imports/` structure?

How should this relate to existing `practices/`, `assets/`, `indexes/`, and `workflows/`?

Should Obsidian vault layout exactly mirror repo layout, or should Obsidian be a view over repo files?

### 20.2 Raw Evidence Storage

Should full ChatGPT exports be stored in Git?

If not, where should they live?

Should raw evidence be encrypted?

Should raw evidence be local-only with hash/index in Git?

How to handle expired uploaded files and inaccessible artifacts?

### 20.3 Research Memo Granularity

Should a long research memo be one file, or should it be split into source digests + concept notes + synthesis memo?

When should an L2 research memo be promoted to multiple atomic concept notes?

How to avoid losing readability by over-atomizing?

### 20.4 Memory Triage Implementation

What is the initial rubric?

What scoring thresholds should map to L0/L1/L2/L3?

How should user accept/reject feedback be recorded?

How should triage skill improve?

Should it be a practice, skill, script, prompt, or full workflow?

### 20.5 Review Burden

How many candidate records per session is acceptable?

How should the system batch and prioritize review?

Should low-confidence candidates expire automatically?

Should there be a “save as raw only” mode?

### 20.6 Professional Profile

What profile fields are safe and useful across agents?

How should profile changes be approved?

Should profile memory be versioned?

How to prevent project-specific facts from leaking into global profile?

### 20.7 Runtime Adapter Boundary

What belongs in ChatGPT Project Knowledge vs global ChatGPT memory?

What belongs in AGENTS.md vs CLAUDE.md vs SKILL.md?

How much W10 context should be loaded by default?

Should Codex get only project instructions, or also memory search tools?

### 20.8 Graph / Index Layer

When should Graphiti/LightRAG-style graph/vector indexes be introduced?

Should derived graph index be generated from Markdown frontmatter and links?

What database/index should be used first: SQLite, ripgrep, embeddings, pgvector, local vector DB, or graph DB?

### 20.9 Medical / Health / High-Stakes Domains

How should health-related memory be marked?

Should health notes be default `needs_verification`?

How should the system distinguish personal notes from advice?

How to prevent runtime agents from acting on stale or unverified health information?

### 20.10 Codex Transition

What exact prompt should Codex receive?

Should Codex create one large design doc or split docs immediately?

How to prevent Codex from over-simplifying the design?

Should ChatGPT review Codex-generated docs after creation?

### 20.11 Memory Access and MCP Boundary

How should MCP expose memory access without making unsafe writes easy?

Should MCP resources be read-only by default, with separate reviewed write tools?

How should an agent prove that a write target is current repository capability rather than proposed memory architecture?

What validation should exist before MCP-mediated memory updates can affect adapters or runtime instructions?

## 21. Suggested Immediate Next Step

The user asked for this dump specifically so they can move into Codex or another local agent without losing context.

The next step should not be to implement the full system immediately. The next step should be:

1. Place this dump in `docs/memory-system-handoff-dump.md`.
2. Ask Codex to read it plus existing Agent Foundry docs.
3. Ask Codex to create a first maintainable document, likely `docs/memory-system-design.md`.
4. The first formal doc should distinguish:
   - goals and non-goals
   - research findings
   - conceptual architecture
   - lifecycle
   - harvest model
   - triage skill
   - knowledge/research asset model
   - project/domain/profile/practice/skill separation
   - unresolved questions
5. Codex should show a diff before commit.
6. ChatGPT should review the generated doc for drift, missing research outputs, and over-action-plan bias.

## 22. Caution to Future Agents

Do not reduce this design to:

- “just export ChatGPT history”
- “just make Obsidian notes”
- “just generate skills”
- “just summarize sessions”
- “just use a vector database”
- “just write AGENTS.md”
- “just build a mind map”

The target system is broader:

```text
A local-first, Markdown/Git-backed, evidence-preserving, progressively typed, review-governed memory and knowledge foundry that can preserve research outputs, project memory, professional profile, practices, and skills, then publish compact runtime adapters for ChatGPT, Codex, Claude Code, Hermes, and related agents.
```

Phase 1 may intentionally implement only a narrow part of that system, but the design must not forget the larger architecture.

## 23. Selected External Research References to Re-check Later

The prior discussion referenced several sources and frameworks. These should be rechecked and cited properly in formal docs.

- LangChain memory concepts: semantic / episodic / procedural memory, thread-scoped vs long-term memory, profile vs collection, hot-path vs background memory writing.
- MemGPT / Letta: virtual context management and memory hierarchy.
- Mem0: production memory service, memory CRUD, managed memory, graph memory.
- Zep / Graphiti: temporal knowledge graph, episode ingestion, hybrid retrieval, provenance.
- A-MEM: agentic memory, Zettelkasten-style dynamic links, memory evolution.
- MemMachine: ground-truth-preserving memory architecture.
- Reflexion: verbal reflection from task feedback.
- Voyager: executable skill library from experience.
- Generative Agents: observations, reflections, planning.
- Zettelkasten: atomic linked notes.
- PKM/PIM: personal information/knowledge lifecycle.
- Records continuum: evidence/provenance from capture onward.
- SECI: tacit/explicit knowledge conversion.
- gstack: proceduralized Claude Code workflows and skills.
- Multica: managed agent execution and reusable skills.

## 24. Specific Corrections Made During Discussion

These corrections are especially important because they capture drift and refinement.

1. The system should not rely on ChatGPT internal memory as canonical.
2. The system should not assume Codex can continue the ChatGPT thread without context loss.
3. The system should not start by building a skill factory.
4. Static research output is a first-class asset.
5. Six harvest modes are too simplistic.
6. Harvest must support project-embedded micro research.
7. Professional profile and working preferences are more important than generic personal reflection.
8. Harvest mode is not a memory type; it is a processing strategy.
9. The lifecycle should include activation and triage as first-class stages.
10. Stage numbering should be clean and maintainable.
11. High-value signal detection should be a skill with feedback loop.
12. Future docs should preserve complexity and not collapse into local simple tools.

## 25. Candidate Formal Document Outline

A later formal `docs/memory-system-design.md` could use this outline:

```text
# Memory System Design

## Purpose
## Background and Problem Statement
## Goals and Non-Goals
## Relationship to Agent Foundry
## Source-of-Truth Model
## Evidence, Knowledge, Practice, Skill, and Adapter Layers
## Memory-to-Knowledge Lifecycle
## Work Context, Artifact Lane, and Lifecycle Intent
## Knowledge Asset Types
## Research Memo and Source Digest Model
## Project Memory Model
## Domain Knowledge Model
## Professional Profile and Working Preferences
## Harvest Activation and Save Levels
## Memory Triage Skill
## Link, Consolidation, and Supersession
## Validation, Governance, and Review
## Runtime Adapters
## ChatGPT Migration Pack
## Offline/Online/Multi-Machine Sync
## Security, Privacy, and High-Stakes Domains
## Phase Plan
## Open Questions
```

The formal doc should not be just an implementation plan. It should include research findings and conceptual architecture.
