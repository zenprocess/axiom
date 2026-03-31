# Axiom Specification v0.2.0

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
category: governance
domain: Git
effect: forbid
priority: critical
activation: always
roles: [agent, reviewer]
globs: ["*.sh", "Makefile"]
trigger: push --force
condition: branch:main
---
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | No (derived from filename if absent) | Stable kebab-case identifier |
| `category` | string | No (defaults to `governance`) | Target Axiom section |
| `domain` | string | No | Scope: `Git`, `Python`, `Bash`, etc. |
| `effect` | enum | No (defaults to `inform`) | `allow`, `forbid`, `prefer`, `discourage`, `inform` |
| `priority` | enum | No (defaults to `medium`) | `critical`, `high`, `medium`, `low` |
| `activation` | string | No | `always`, `on-demand`, or cron expression |
| `roles` | list[string] | No | Agent roles this rule applies to |
| `globs` | list[string] | No | File patterns that scope the rule |
| `trigger` | string | No | Pattern or command that activates the rule |
| `condition` | string | No | Narrowing predicate |

All fields are optional. The body text (after the frontmatter) becomes the `message` field.

### 12.2 Complete Example

```markdown
---
id: no-force-push
category: governance
domain: Git
effect: forbid
priority: critical
trigger: push --force
condition: branch:main
roles: [agent]
---
Never use `git push --force`. It rewrites remote history and can destroy
other contributors' work. Use `--force-with-lease` instead.
```

### 12.3 Compilation Relationship

```
.claude/rules/*.md  →  Axiom compiler  →  compiled.axiom (TOON)
                                        →  compiled.cacp  (CACP)
```

The compiler parses frontmatter, maps fields to the appropriate category schema, and emits the compiled format. Rules without frontmatter are treated as `inform` effect with `medium` priority.

## 13. File Extension

Axiom files use the `.axiom` extension. Compiled per-agent rule sets are conventionally named `compiled.axiom`.

## 14. MIME Type

`text/x-axiom` (provisional).

## 15. Versioning

This specification is versioned using semantic versioning. The current version is `0.2.0`. The version is not embedded in the file format; it is tracked by the specification document.
