# Axiom Specification v0.1.0

## 1. Overview

Axiom is a Rule Definition Language (RDL) for encoding AI agent rules in a compact, self-describing tabular format. Files use the `.axiom` extension.

## 2. TOON Header Syntax

Each section begins with a header line:

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

## 9. File Extension

Axiom files use the `.axiom` extension. Compiled per-agent rule sets are conventionally named `compiled.axiom`.

## 10. MIME Type

`text/x-axiom` (provisional).

## 11. Versioning

This specification is versioned using semantic versioning. The current version is `0.1.0`. The version is not embedded in the file format; it is tracked by the specification document.
