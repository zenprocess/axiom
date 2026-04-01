# Axiom Specification v0.4.0

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

Each data row is a comma-separated list of values, one rule per line:

```
value1,value2,value3,...
```

**Rules:**
- Fields are separated by commas with no spaces after the delimiter (unless the space is part of the value).
- Values MUST NOT contain unescaped commas. To include a comma in a value, wrap the entire value in double quotes: `"value with, comma"`.
- To include a double quote inside a quoted value, escape it as `""`.
- Empty values are represented as empty strings between delimiters: `id,,domain,trigger,,message`.
- Rows MUST have exactly as many fields as columns declared in the header.
- Blank lines between rows are ignored.
- Lines beginning with `#` are comments and are ignored.

## 4. Sections

Multiple sections can appear in a single `.axiom` file. Sections are separated by blank lines (optional but recommended for readability). Each section has its own header and column schema.

```
GOVERNANCE[2]{id,effect,domain,trigger,message}:
no-force-push,forbid,Git,push --force,Rewrites remote history
no-main-commit,forbid,Git,commit on main,Use feature branches

CODING[1]{id,language,effect,pattern,fix_hint,severity}:
no-print-debug,Python,forbid,print() for debugging,Use structlog,warning
```

## 5. Universal Core Columns

All categories SHOULD include these columns (though only `id` and `effect` are REQUIRED):

| Column | Type | Description |
|--------|------|-------------|
| `id` | string | Unique, stable, kebab-case identifier |
| `effect` | enum | One of: `allow`, `forbid`, `prefer`, `discourage`, `inform` |
| `domain` | string | Scope: `Git`, `Bash`, `Python`, `TypeScript`, `API`, `Docs`, etc. |
| `trigger` | string | Pattern, command, event, or context that activates the rule |
| `condition` | string | Optional predicate narrowing when the rule applies |
| `message` | string | Brief natural-language rationale for the agent |

## 6. Reserved Effects

| Effect | Semantics |
|--------|-----------|
| `allow` | Explicitly permitted (overrides a broader `discourage`) |
| `forbid` | MUST NOT do this. Hard constraint. |
| `prefer` | SHOULD do this when applicable. Soft recommendation. |
| `discourage` | SHOULD NOT do this. Soft constraint. |
| `inform` | No behavioral constraint; informational context for the agent. |

## 7. Priority Levels

When categories include a `priority` or `severity` column, the following levels are defined:

| Level | Semantics |
|-------|-----------|
| `critical` | Must never be violated. Abort on breach. |
| `high` | Strong constraint. Violations are errors. |
| `medium` | Default. Violations are warnings. |
| `low` | Advisory. Best-effort compliance. |

## 8. Standard Category Schemas

### 8.1 GOVERNANCE

```
GOVERNANCE[N]{id,effect,domain,trigger,condition,message}:
```

Guards on agent behavior, tool use, and process adherence.

### 8.2 CODING

```
CODING[N]{id,language,scope,pattern,effect,fix_hint,severity}:
```

Additional columns:
- `language` — programming language (`Python`, `TypeScript`, `Go`, etc.)
- `scope` — `project`, `module`, `file`, `function`
- `pattern` — code pattern or description to match
- `fix_hint` — what to do instead
- `severity` — `info`, `warning`, `error`

### 8.3 SECURITY

```
SECURITY[N]{id,risk_level,data_type,trigger,effect,response}:
```

Additional columns:
- `risk_level` — `low`, `medium`, `high`, `critical`
- `data_type` — `secret`, `pii`, `key`, `token`, `credential`
- `response` — `abort`, `redact`, `warn`, `notify`

### 8.4 TESTING

```
TESTING[N]{id,effect,target,threshold,action,message}:
```

Additional columns:
- `target` — `unit`, `integration`, `e2e`, `coverage`
- `threshold` — quantitative gate (e.g., `>=80%`)
- `action` — `enforce`, `recommend`

### 8.5 WORKFLOW

```
WORKFLOW[N]{id,effect,phase,actor,condition,message}:
```

Additional columns:
- `phase` — `planning`, `coding`, `review`, `deploy`
- `actor` — `orchestrator`, `agent`, `reviewer`, `ci`

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

Context window pressure determines how aggressively rules are compressed. Tools SHOULD implement pressure-aware compilation using the following graduated zones:

| Zone | Context Usage | Behavior |
|------|--------------|----------|
| FRESH | 0-40% | All sections, all columns, full messages |
| MODERATE | 40-70% | Drop `message` column, drop rules with `inform` effect |
| DEPLETED | 70-90% | Only `critical` and `high` priority rules retained |
| CRITICAL | 90%+ | Safety floor only: `critical` priority + `forbid` effect |

**Rules:**
- Zone boundaries are computed as `estimated_task_tokens / model_context_window`.
- The safety floor (critical + forbid) MUST never be dropped regardless of pressure.
- Within each zone, the drop order for effects is: `inform` first, then `discourage`, `prefer`, `allow`, `forbid` last.
- Within each zone, the drop order for priorities is: `low` first, then `medium`, `high`, `critical` last.
- Tools SHOULD report dropped rules and their reasons in a budget report.
- Tools MAY truncate `message` fields before dropping entire rules.

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
GOVERNANCE[2]{id,effect,priority,domain,trigger,message}:
no-force-push,forbid,critical,Git,push --force,Rewrites remote history
allow-force-lease,allow,high,Git,push --force-with-lease,Safe alternative
```

Resolution: `no-force-push` wins on `push --force` (critical > high). `allow-force-lease` applies only to the more specific `push --force-with-lease` trigger.

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

CODING[4]{id,language,effect,pattern,fix_hint,severity}:
type-hints,Python,prefer,function definition,Add type hints to all signatures,warning
pydantic-models,Python,prefer,data structures,Use Pydantic v2 BaseModel not raw dicts,warning
async-io,Python,prefer,I/O operations,Use async def for all I/O,warning
structlog-only,Python,forbid,print(),Use structlog for logging,error
```

## 14. File Extension

Axiom files use the `.axiom` extension. Compiled per-agent rule sets are conventionally named `compiled.axiom`.

## 15. MIME Type

`text/x-axiom` (provisional).

## 16. MCP Resource URIs

Axiom content is accessible over the [Model Context Protocol](https://modelcontextprotocol.io) (MCP) via a standard URI scheme. Any Axiom-compatible MCP server MAY serve these resources; [Sieeve](https://github.com/zenprocess/sieeve) is the reference implementation.

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

## 17. Versioning

This specification is versioned using semantic versioning. The current version is `0.4.0`. The version is not embedded in the file format; it is tracked by the specification document.
