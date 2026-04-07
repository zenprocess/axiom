# Axiom Specification v0.6.0

## 1. Overview

Axiom is a Rule Definition Language (RDL) for encoding AI agent rules in a compact, self-describing tabular format. Files use the `.axiom` extension.

## 2. [TOON](https://toonformat.dev) Header Syntax

Each section begins with a [TOON (Typed Object-Oriented Notation)](https://toonformat.dev) header line:

```
SECTION_NAME[N]{col1,col2,...}:
```

- **SECTION_NAME** — uppercase identifier for the rule category (e.g., `GOVERNANCE`, `CODING`).
- **N** — integer count of data rows that follow.
- **{col1,col2,...}** — comma-separated column names enclosed in braces. These serve as the inline schema.
- **:** — the header line MUST end with a colon.

The header is immediately followed by `N` data rows.

## 3. Row Format

Each data row is a comma-separated list of values, one rule per line. All rule sections use a **universal column schema** with a hierarchical **S/D (Summary/Detail)** row format.

### 3.1 Universal Column Schema

Every rule section uses the same five columns:

| Column | Type | Description |
|--------|------|-------------|
| `id` | string | Rule identifier (stable, short, kebab-case) |
| `level` | enum | `S` (summary — always loaded) or `D` (detail — loaded on demand) |
| `effect` | enum | `forbid`, `require`, `prefer`, `inform` |
| `instruction` | string | Imperative command, max 20 words |
| `trigger` | string | When this applies (tool name, file pattern, condition) |

The header for any rule section is:

```
SECTION_NAME[N]{id,level,effect,instruction,trigger}:
```

### 3.2 S/D Hierarchical Rows

Each rule has two rows — **S** (summary) and **D** (detail):

- **S row** (~15 tokens): Always loaded. Captures the essential constraint in one imperative sentence.
- **D row** (~30 tokens): Loaded on demand. Provides specifics, exceptions, safe alternatives, or detection patterns.

```
RULES[4]{id,level,effect,instruction,trigger}:
no-gold-plating,S,forbid,Build ONLY acceptance criteria items,Write/Edit
no-gold-plating,D,forbid,No extra helpers or error handling for unchanged code,FILES_CREATED not in AC
bash-safety,S,forbid,No git stash -u | git clean | rm -rf | git reset --hard,Bash
bash-safety,D,forbid,Safe: git stash (tracked) | git checkout -- file | rm by name,Bash blocked command
```

The section name (GOVERNANCE, CODING, SECURITY, etc.) provides grouping; the level provides loading priority.

### 3.3 CSV Rules

**Rules:**
- Fields are separated by commas with no spaces after the delimiter (unless the space is part of the value).
- Values MUST NOT contain unescaped commas. To include a comma in a value, wrap the entire value in double quotes: `"value with, comma"`.
- To include a double quote inside a quoted value, escape it as `""`.
- Empty values are represented as empty strings between delimiters: `id,,effect,instruction,trigger`.
- Rows MUST have exactly as many fields as columns declared in the header.
- Blank lines between rows are ignored.
- Lines beginning with `#` are comments and are ignored.

## 4. Sections

Multiple sections can appear in a single `.axiom` file. Sections are separated by blank lines (optional but recommended for readability). All sections use the same universal column schema (`{id,level,effect,instruction,trigger}`).

```
GOVERNANCE[4]{id,level,effect,instruction,trigger}:
no-force-push,S,forbid,Never git push --force,Bash
no-force-push,D,forbid,Safe: git push --force-with-lease for history correction,push --force
no-main-commit,S,forbid,Never commit directly on main/master,Git commit
no-main-commit,D,forbid,Create feature branch from main before committing,branch:main

CODING[2]{id,level,effect,instruction,trigger}:
no-print-debug,S,forbid,No print() for debugging,Python
no-print-debug,D,forbid,Use structlog for all logging output,print() in *.py
```

## 5. Universal Column Schema

All sections use the same five columns (see Section 3.1). This replaces the per-category column schemas from earlier versions. The section name provides semantic grouping; the schema is universal.

| Column | Type | Required | Description |
|--------|------|----------|-------------|
| `id` | string | Yes | Rule identifier (stable, short, kebab-case) |
| `level` | enum | Yes | `S` (summary) or `D` (detail) |
| `effect` | enum | Yes | `forbid`, `require`, `prefer`, `inform` |
| `instruction` | string | Yes | Imperative command, max 20 words |
| `trigger` | string | Yes | When this applies (tool name, file pattern, condition) |

## 6. Reserved Effects

| Effect | Semantics |
|--------|-----------|
| `forbid` | MUST NOT do this. Hard constraint. |
| `require` | MUST do this. Hard constraint. |
| `prefer` | SHOULD do this when applicable. Soft recommendation. |
| `inform` | No behavioral constraint; informational context for the agent. |

## 7. Priority Levels

When categories include a `priority` or `severity` column, the following levels are defined:

| Level | Semantics |
|-------|-----------|
| `critical` | Must never be violated. Abort on breach. |
| `high` | Strong constraint. Violations are errors. |
| `medium` | Default. Violations are warnings. |
| `low` | Advisory. Best-effort compliance. |

## 8. Standard Categories

All categories use the universal column schema `{id,level,effect,instruction,trigger}`. The category name provides semantic grouping only.

| Category | Purpose |
|----------|---------|
| `GOVERNANCE` | Guards on agent behavior, tool use, and process adherence |
| `CODING` | Language conventions, patterns, and style enforcement |
| `SECURITY` | Secret detection, access control, data handling |
| `TESTING` | Quality gates, coverage thresholds, test requirements |
| `WORKFLOW` | Process, CI, and phase-gating rules |

Category-specific semantics (language, risk level, threshold, etc.) are encoded in the `instruction` and `trigger` fields rather than as separate columns. This keeps the schema universal and parsing trivial.

## 9. Alternative Serializations

[TOON](https://toonformat.dev) is the default and most compact Axiom serialization. CACP (Context/Acceptance/Constraints/Protocol) is defined as a second normative serialization for environments where structured bullet-list format is preferred over tabular CSV.

### 9.1 CACP Encoding

A CACP-encoded rule set uses four sections:

```
CONTEXT:Project rules compiled by <tool>
SCOPE:<comma-separated category list>

RULES:
- [CATEGORY] id: message (effect: effect_value)
- [CATEGORY] id: message (effect: effect_value)

VERIFY:Apply all rules marked 'forbid'. Log rules marked 'prefer'.
```

**Rules:**
- The `CONTEXT` line provides provenance (compiler name, agent role).
- The `SCOPE` line lists all categories included.
- Each rule is a bullet under `RULES:`, formatted as `- [CATEGORY] id: message (effect: effect_value)`.
- Rules are grouped by category, with categories in alphabetical order.
- The `VERIFY` line instructs the consuming agent on enforcement semantics.
- CACP is approximately 2-3x more verbose than TOON for the same rule set but requires no CSV parsing.

### 9.2 Choosing a Serialization

| | TOON | CACP |
|---|---|---|
| Token cost | Minimal | 2-3x TOON |
| Parse complexity | CSV-aware | Bullet-list |
| Agent familiarity | Novel format | Familiar to CACP-speaking agents |
| Use case | Token-constrained, compiled output | Dispatcher integration, debugging |

Tools SHOULD default to TOON. Tools MAY offer a `--format cacp` flag.

Reference implementation: [zenprocess/cacp](https://github.com/zenprocess/cacp).

## 10. Pressure Zones

Context window pressure determines which S/D rows are loaded. Tools SHOULD implement pressure-aware loading using the following graduated zones:

| Zone | Context Usage | Behavior |
|------|--------------|----------|
| FRESH | 0-40% | S + D rows for all matched rules |
| MODERATE | 40-70% | S rows for all, D rows for high-relevance only |
| DEPLETED | 70-90% | S rows only |
| CRITICAL | 90%+ | S rows for `critical` + `forbid` only |

**Rules:**
- Zone boundaries are computed as `estimated_task_tokens / model_context_window`.
- The safety floor (S rows with `forbid` effect on critical rules) MUST never be dropped regardless of pressure.
- Within each zone, the drop order for effects is: `inform` first, then `prefer`, `require`, `forbid` last.
- D rows are always dropped before S rows of the same rule.
- Tools SHOULD report dropped rules and their reasons in a budget report.

## 11. Conflict Resolution

When multiple rules match the same trigger or context, conflicts are resolved using the following normative order:

### 11.1 Resolution Cascade

1. **Priority wins.** `critical` > `high` > `medium` > `low`. A `critical` rule always overrides a `low` rule on the same trigger.
2. **Within same priority: more specific trigger wins.** Specificity ranking: `regex` > `keyword` > `wildcard` > `none` (no trigger).
3. **Within same specificity: first-defined wins.** The rule appearing earlier in the source file takes precedence.

### 11.2 Tool Behavior

- Tools SHOULD warn on detected conflicts during compilation (e.g., `allow` and `forbid` on the same trigger at the same priority).
- Tools MAY auto-resolve using this cascade, annotating the resolution in compiler output.
- Tools MUST NOT silently discard conflicting rules without reporting.

### 11.3 Example

```
GOVERNANCE[4]{id,level,effect,instruction,trigger}:
no-force-push,S,forbid,Never git push --force,Bash
no-force-push,D,forbid,Safe: git push --force-with-lease for history correction,push --force
allow-force-lease,S,prefer,Use --force-with-lease when rewriting remote history,Git push
allow-force-lease,D,inform,Only after confirming no shared commits will be lost,push --force-with-lease
```

Resolution: `no-force-push` wins on `push --force` (forbid > prefer). `allow-force-lease` applies only to the more specific `push --force-with-lease` trigger.

## 12. Source Format

Axiom rules can be authored as markdown files with YAML frontmatter. This is the recommended source format for human authoring; compilation to Axiom (TOON or CACP) is performed by a compiler.

### 12.1 Frontmatter Schema

```yaml
---
id: no-force-push
description: Prevent force-push to protected branches
category: governance
domain: Git
effect: forbid
priority: critical
activation: always
roles: [agent, reviewer]
globs: ["*.sh", "Makefile"]
paths: ["*.sh", "Makefile"]
trigger: push --force
condition: branch:main
when_to_use: When reviewing or executing git push commands
---
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | No (derived from filename if absent) | Stable kebab-case identifier |
| `description` | string | No | One-line summary of the rule. Used for rule selectors and summaries. |
| `category` | string | No (defaults to `governance`) | Target Axiom section |
| `domain` | string | No | Scope: `Git`, `Python`, `Bash`, etc. |
| `effect` | enum | No (defaults to `inform`) | `allow`, `forbid`, `prefer`, `discourage`, `inform` |
| `priority` | enum | No (defaults to `medium`) | `critical`, `high`, `medium`, `low` |
| `activation` | string | No | `always`, `on-demand`, or cron expression |
| `roles` | list[string] | No | Agent roles this rule applies to |
| `globs` | list[string] | No | File patterns that scope the rule |
| `paths` | list[string] | No | Alias for `globs`. File glob patterns that scope the rule. |
| `trigger` | string | No | Pattern or command that activates the rule |
| `condition` | string | No | Narrowing predicate |
| `when_to_use` | string | No | Hint for model-driven invocation. Signals task-match activation. |

All fields are optional. The body text (after the frontmatter) becomes the `message` field.

**`paths` / `globs` aliasing:** Both fields accept the same glob pattern syntax. When both are present, compilers MUST merge them (union, deduplicated). Compilers SHOULD normalize to `globs` in compiled output.

### 12.2 Complete Example

```markdown
---
id: no-force-push
description: Prevent force-push to protected branches
category: governance
domain: Git
effect: forbid
priority: critical
trigger: push --force
condition: branch:main
roles: [agent]
globs: ["*.sh"]
when_to_use: When reviewing or executing git push commands
---
Never use `git push --force`. It rewrites remote history and can destroy
other contributors' work. Use `--force-with-lease` instead.
```

### 12.3 Claude Code Compatibility

Any `.claude/rules/*.md` file with Claude Code frontmatter is valid Axiom source. Claude Code uses three frontmatter fields:

| CC Field | Axiom Equivalent | Notes |
|----------|-----------------|-------|
| `description` | `description` | Direct match. One-line rule summary. |
| `paths` | `globs` (alias: `paths`) | Axiom accepts `paths` as an alias for `globs`. |
| `when_to_use` | `when_to_use` | Direct match. Model-driven invocation hint. |

A CC rule file like:

```markdown
---
description: Coding standards for Python files
paths: ["**/*.py"]
when_to_use: When writing or modifying Python code
---
Use type hints on all function signatures.
```

compiles without modification. The compiler treats `description` as metadata, maps `paths` to `globs`, carries `when_to_use` as an activation signal, infers `effect: inform` and `priority: medium` from defaults, and uses the body as `message`.

### 12.4 Compilation Relationship

```
.claude/rules/*.md  →  Axiom compiler  →  compiled.axiom (TOON)
                                        →  compiled.cacp  (CACP)
```

The compiler parses frontmatter, maps fields to the appropriate category schema, and emits the compiled format. Rules without frontmatter are treated as `inform` effect with `medium` priority.

## 13. CLAUDE.md Compilation

CLAUDE.md files are valid Axiom source documents. Because CLAUDE.md loads on every agent turn, it is the highest-leverage compression target in any project. The compiler maps each section of a CLAUDE.md to the appropriate Axiom representation using the following strategy.

### 13.1 Section Mapping

| CLAUDE.md Section Type | Axiom Representation |
|------------------------|---------------------|
| Status tables, endpoint lists, dispatch statuses | Standard TOON tables (e.g., `ENDPOINTS[N]{method,path,description}:`) |
| Conventions, constraints, safety rules | `GOVERNANCE[N]{...}:`, `CODING[N]{...}:`, `SECURITY[N]{...}:` |
| Command blocks (dev commands, CLI usage) | `COMMANDS[N]{cmd,description}:` |
| File structure blocks (directory trees) | `STRUCTURE[N]{path,description}:` |
| Narrative prose (architecture descriptions, explanations) | `PROSE[N]{}:` — literal text, no tabulation |

### 13.2 PROSE Block

The `PROSE` section type carries literal text that cannot be meaningfully tabulated without information loss. Its header uses an empty column set:

```
PROSE[N]{}:
```

Where `N` is the number of lines that follow. The block is terminated by the next section header or EOF. Lines are reproduced verbatim — no column parsing, no comma splitting. This preserves architecture narratives, design rationale, and other free-form content that loses meaning when forced into columns.

### 13.3 Zero Information Loss

CLAUDE.md compilation is **lossless structural compression**. Every piece of information in the source CLAUDE.md MUST appear in the compiled output. The compiler:

1. Preserves all rules, commands, paths, descriptions, and prose.
2. Eliminates only syntactic redundancy (markdown formatting, repeated headers, filler words).
3. Reports any content that could not be mapped to a section type.

### 13.4 Coexistence

Compilation is optional. A project MAY have both `CLAUDE.md` and `CLAUDE.axiom` in the same directory. When both exist, tools SHOULD prefer the compiled `.axiom` version for context injection, falling back to the markdown original if the compiled version is stale or absent.

### 13.5 Example

**Before** (CLAUDE.md excerpt, 140 tokens):

```markdown
## Key Commands

​```bash
# Dev environment
pip install -e ".[dev]"

# Run tests
PYTHONPATH=src pytest tests/

# Dispatch a task
zd dispatch --issue 1234
​```

## Development Conventions

- Python 3.12+ with type hints on all function signatures
- Pydantic v2 BaseModel for all data structures — never raw dicts
- async def for all I/O
- structlog for logging — never print()
```

**After** (CLAUDE.axiom excerpt, 55 tokens):

```
COMMANDS[3]{cmd,description}:
pip install -e ".[dev]",Dev environment setup
PYTHONPATH=src pytest tests/,Run tests
zd dispatch --issue 1234,Dispatch a task

CODING[8]{id,level,effect,instruction,trigger}:
type-hints,S,require,Add type hints to all function signatures,Python function def
type-hints,D,require,Return types and parameter types on every def,*.py
pydantic-models,S,require,Use Pydantic v2 BaseModel for all data structures,Python
pydantic-models,D,forbid,No raw dicts for structured data,dict literal
async-io,S,require,Use async def for all I/O operations,Python I/O
async-io,D,require,subprocess + file + network calls must be async,sync I/O call
structlog-only,S,forbid,No print() — use structlog for all logging,Python
structlog-only,D,forbid,Replace print/logging.info with structlog bound logger,print() in *.py
```

## 14. File Extension

Axiom files use the `.axiom` extension. Compiled per-agent rule sets are conventionally named `compiled.axiom`.

## 15. MIME Type

`text/x-axiom` (provisional).

## 16. MCP Resource URIs

Axiom content is accessible over the [Model Context Protocol](https://modelcontextprotocol.io) (MCP) via a standard URI scheme. Any Axiom-compatible MCP server MAY serve these resources; a reference implementation is available separately.

The URI scheme is part of this standard. Server implementations are not.

### 16.1 URI Scheme

| URI | Description |
|-----|-------------|
| `axiom://rules` | All compiled rules (concatenated across categories) |
| `axiom://rules/{category}` | Rules for a specific category (`governance`, `coding`, `security`, `testing`, `workflow`) |
| `axiom://claude-md` | Compiled CLAUDE.md |
| `axiom://claude-md/{agent_role}` | Compiled CLAUDE.md filtered for agent role |
| `axiom://policy/{action}/{resource}` | Policy evaluation result for action on resource |
| `axiom://meta/coverage` | Coverage report (which agents see which rules) |
| `axiom://meta/conflicts` | Conflict report (opposing effects on same trigger) |
| `axiom://meta/freshness` | Rule freshness report (last triggered timestamps) |

### 16.2 Content Types

| URI pattern | Content-Type |
|-------------|-------------|
| `axiom://rules`, `axiom://rules/{category}`, `axiom://claude-md`, `axiom://claude-md/{agent_role}` | `text/x-axiom` |
| `axiom://policy/**`, `axiom://meta/**` | `text/plain` |

### 16.3 Example MCP Tool Definition

An MCP server exposing Axiom resources declares them as standard MCP resources:

```json
{
  "resources": [
    {
      "uri": "axiom://rules",
      "name": "All Axiom rules",
      "description": "Compiled rules across all categories in TOON format",
      "mimeType": "text/x-axiom"
    },
    {
      "uri": "axiom://rules/{category}",
      "name": "Axiom rules by category",
      "description": "Compiled rules for a single category (governance, coding, security, testing, workflow)",
      "mimeType": "text/x-axiom"
    },
    {
      "uri": "axiom://claude-md",
      "name": "Compiled CLAUDE.md",
      "description": "Project CLAUDE.md compiled to Axiom TOON format",
      "mimeType": "text/x-axiom"
    },
    {
      "uri": "axiom://policy/{action}/{resource}",
      "name": "Policy evaluation",
      "description": "Evaluate whether an action is allowed on a resource",
      "mimeType": "text/plain"
    },
    {
      "uri": "axiom://meta/coverage",
      "name": "Rule coverage report",
      "description": "Which agents see which rules",
      "mimeType": "text/plain"
    }
  ]
}
```

## 17. Orchestration & Complexity Stratification

> **Inspirations.** The orchestration axis and complexity-tier stratification
> in this section are motivated by Fabian Wesner's [One-Shot Shop Challenge](https://agentic-engineers.dev)
> ([announcement](https://www.linkedin.com/posts/fabian-wesner_oneshotshop-share-7442096217976897536-SRI9/)),
> which empirically showed that orchestration architecture beats model choice
> (Team Mode 85% vs Sub-Agents 57% on the same model, 143 E2E tests).
> The reference implementation is [zenprocess/pawbench](https://github.com/zenprocess/pawbench);
> see Switchyard spec 009 for the operational mapping.

A dispatcher or benchmark is **Axiom-stratification-compliant** if it either
implements the schemas in this section or documents in its conformance
statement why it omits them. These schemas are normative for runners that
report multi-dimensional dispatch results.

### 17.1 Orchestration Shape Vocabulary

Every dispatch result MUST be tagged with exactly one orchestration shape from
the canonical vocabulary below. New shapes MAY be added as extensions but MUST
NOT collide with these identifiers.

| Shape            | Definition                                                                                  |
|------------------|---------------------------------------------------------------------------------------------|
| `flat`           | Single dispatch, single agent, no decomposition. The reference baseline.                    |
| `waves`          | Graph-coloring of non-conflicting tasks into sequential waves of parallel dispatches.       |
| `scatter-gather` | Decompose → N parallel workers → merge step. Workers do not coordinate during execution.   |
| `team-mode`      | Coordinated multi-agent execution with a shared spec and an integration checkpoint.        |
| `subagents`      | Localized sub-dispatches without coordination or merge step.                                |

Tools MUST report shape via the `orchestration` field on every result row.

### 17.2 Complexity Tier Vocabulary

Every dispatched task MUST carry exactly one complexity tier. Tier is
author-tagged at scenario-authoring time; tools MAY infer when missing, and
agent self-assessment MAY be present but is overridden by the verifier.

| Tier            | Definition                                                                                       |
|-----------------|--------------------------------------------------------------------------------------------------|
| `display`       | Read-only render of existing data; no state mutation.                                            |
| `crud`          | Single-entity create / read / update / delete with validation.                                   |
| `transactional` | Multi-entity flow with invariants (checkout, transfer, booking). Failure must roll back fully.   |
| `cross_cutting` | Spans multiple subsystems (e.g., auth + payments + email).                                       |

Stratified reporting (`pass_rate_by_tier`, `dqs_by_tier`) is REQUIRED for any
runner claiming Axiom stratification compliance.

### 17.3 `fixture_gap` Status

`fixture_gap` is a terminal dispatch status meaning *acceptance criteria are
un-evaluable due to missing setup* (seed data, fixtures, environment, external
services) — and the gap is **not the agent's fault**. Runners MUST:

- Exclude `fixture_gap` rows from agent rankings.
- Surface `fixture_gap_rate` as a scenario-health metric.
- Where possible, detect fixture gaps pre-dispatch (faster signal, zero cost).

`fixture_gap` joins the existing terminal status set
(`ok`, `fail`, `partial`, `rejected`, `no_changes`, `decomposed`, `retry`).

### 17.4 Verifier Reliability — `verification_runs[]`

To measure verifier flake, the AC verifier MAY be invoked N times on the same
commit. Each invocation produces one `VerifierRun` record:

```
VERIFIER_RUNS[N]{run_id,verdict,prompt_hash,elapsed_ms,notes}:
1,pass,a3f...,120,
2,pass,a3f...,118,
3,fail,a3f...,131,disagreement on AC#3
```

| Field         | Type   | Required | Notes                                          |
|---------------|--------|----------|------------------------------------------------|
| `run_id`      | int    | Yes      | Sequential 1..N                                |
| `verdict`     | enum   | Yes      | `pass` \| `fail` \| `unrunnable`               |
| `prompt_hash` | string | Yes      | SHA-256 of the verifier prompt                 |
| `elapsed_ms`  | int    | Yes      | Wall-clock duration                            |
| `notes`       | string | No       | Disagreement reason or model-output excerpt    |

The derived SLI `verifier_agreement_rate = unanimous_runs / total_runs` is
RECOMMENDED for any runner reporting multi-run verification.

### 17.5 Artifact Quality — `artifact_quality`

A static-analysis score over the *changed files only*, orthogonal to AC pass.

```
ARTIFACT_QUALITY[1]{language,lint_errors,type_errors,cyclomatic_max,score,analyzer}:
python,3,0,12,0.82,ruff+mypy+radon
```

| Field            | Type   | Required | Notes                                        |
|------------------|--------|----------|----------------------------------------------|
| `language`       | string | Yes      | Primary language analyzed                    |
| `lint_errors`    | int    | Yes      | Count of lint errors (≥ 0)                   |
| `type_errors`    | int    | Yes      | Count of type errors (≥ 0)                   |
| `cyclomatic_max` | int    | Yes      | Max cyclomatic complexity across changes     |
| `score`          | float  | Yes      | Normalized 0..1                              |
| `analyzer`       | string | Yes      | Tool that produced the score                 |

Artifact quality is intentionally **independent** of any composite dispatch
score. Runners MUST NOT silently fold it into existing aggregate scores;
inclusion in aggregates requires an explicit, versioned schema change.

### 17.6 Conformance Statement

A runner declaring Axiom stratification compliance MUST publish a conformance
statement listing, for each of §17.1–§17.5, one of: `implemented`,
`extension`, or `omitted (reason)`. The statement is part of the runner's
release artifact.

## 18. Versioning

This specification is versioned using semantic versioning. The current version is `0.6.0`. The version is not embedded in the file format; it is tracked by the specification document.

### Changelog

- **0.6.0** — §17 Orchestration & Complexity Stratification added (orchestration shape vocabulary, complexity tier vocabulary, `fixture_gap` status, `verification_runs[]`, `artifact_quality`). Inspired by Fabian Wesner's One-Shot Shop Challenge. Reference implementation: [zenprocess/pawbench](https://github.com/zenprocess/pawbench).
- **0.5.0** — Universal column schema, S/D hierarchical rows, MCP resource URIs.
