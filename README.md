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

Axiom uses TOON-style self-describing tabular headers:

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

## Reserved Effects

`allow` | `forbid` | `prefer` | `discourage` | `inform`

## Documentation

- [Specification](spec.md) — normative format definition
- [Paper](paper.md) — research backing and design rationale
- [Examples](examples/) — sample `.axiom` files

## License

[MIT](LICENSE)
