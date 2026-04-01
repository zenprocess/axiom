# Axiom

A compact Rule Definition Language (RDL) for AI coding agents. Compiles verbose markdown rules into self-describing tabular format with 20:1 token compression and no compliance degradation.

## Before & After

**Markdown rule (87 tokens):**

```markdown
## Git Safety
- Never use `git push --force` on any branch. Force pushing rewrites
  remote history and can destroy other contributors' work. If you need
  to update a remote branch, use `git push --force-with-lease` instead,
  which will fail if the remote has commits you haven't seen.
```

**Axiom compiled (18 tokens):**

```
GOVERNANCE[1]{id,effect,domain,trigger,message}:
no-force-push,forbid,Git,push --force,Use --force-with-lease instead
```

## Format

Axiom uses [TOON](https://toonformat.dev)-style self-describing tabular headers:

```
SECTION_NAME[N]{col1,col2,...}:
value1,value2,value3,...
value1,value2,value3,...
```

- `SECTION_NAME` — uppercase category (GOVERNANCE, CODING, SECURITY, etc.)
- `[N]` — row count
- `{col1,col2,...}` — inline column schema
- Rows are CSV-like, one rule per line

## Core Schemas

| Category | Columns |
|----------|---------|
| GOVERNANCE | `id, effect, domain, trigger, condition, message` |
| CODING | `id, language, scope, pattern, effect, fix_hint, severity` |
| SECURITY | `id, risk_level, data_type, trigger, effect, response` |
| TESTING | `id, effect, target, threshold, action, message` |
| WORKFLOW | `id, effect, phase, actor, condition, message` |

## Serializations

| Format | Use case | Token cost |
|--------|----------|------------|
| **TOON** (default) | Compiled output, token-constrained | Minimal |
| **CACP** | Dispatcher integration, debugging | 2-3x TOON |

## Source Format

Rules are authored as markdown with YAML frontmatter. Axiom's frontmatter is a superset of Claude Code's `description`/`paths`/`when_to_use` fields, so `.claude/rules/*.md` files work with both CC and Axiom without modification.

```markdown
---
id: no-force-push
description: Prevent force-push to protected branches
category: governance
effect: forbid
priority: critical
trigger: push --force
globs: ["*.sh"]
when_to_use: When reviewing or executing git push commands
---
Never use `git push --force`. Use `--force-with-lease` instead.
```

`paths` is accepted as an alias for `globs` (CC compatibility).

## Pressure Zones

| Zone | Context | Behavior |
|------|---------|----------|
| FRESH | 0-40% | All rules |
| MODERATE | 40-70% | Drop `inform`, drop `message` |
| DEPLETED | 70-90% | Critical + high only |
| CRITICAL | 90%+ | Safety floor (critical + forbid) |

## Reserved Effects

`allow` | `forbid` | `prefer` | `discourage` | `inform`

## MCP Integration

Axiom content is accessible via [Model Context Protocol](https://modelcontextprotocol.io) resource URIs. Any Axiom-compatible MCP server can serve compiled rules, CLAUDE.md, and policy evaluations using the `axiom://` URI scheme:

```
axiom://rules                        — all compiled rules
axiom://rules/{category}             — rules for a specific category
axiom://claude-md                    — compiled CLAUDE.md
axiom://policy/{action}/{resource}   — policy evaluation result
axiom://meta/coverage                — rule coverage report
```

See [spec.md, section 16](spec.md#16-mcp-resource-uris) for the full URI scheme and MCP tool definition examples.

## Documentation

- [Specification](spec.md) — normative format definition
- [Paper](paper.md) — research backing and design rationale
- [Examples](examples/) — sample `.axiom` files

## License

[MIT](LICENSE)
