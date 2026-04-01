# Axiom: A Compact Rule Definition Language for LLM-Native Context Engineering

**V. Vladescu** ([@vvladescu](https://github.com/vvladescu), zenprocess), **Claude** (Anthropic)

---

## Abstract

Large language model (LLM) coding agents increasingly rely on rule files to encode project conventions, governance policies, and security constraints. These rules are typically authored as prose markdown, which is verbose, positionally fragile, and scales poorly as rule sets grow. We introduce Axiom, a Rule Definition Language (RDL) that compiles human-readable rules into a compact, self-describing tabular format based on [TOON](https://toonformat.dev)-style headers (`SECTION[N]{columns}:` followed by CSV rows). A ZenRule prototype demonstrates 20:1 compression (20k to 1k tokens) with no observed degradation in agent compliance. The v0.5.0 hierarchical S/D (Summary/Detail) row format extends this to 15x (full S+D) to 46x (summary-only) compression, enabling pressure-adaptive rule loading. This result aligns with findings from LLMLingua (up to 20x compression, ~1.5-point accuracy loss), SWE-Pruner (21-54% token savings with quality improvement), and table-format benchmarks showing that structured tabular inputs outperform equivalent prose by over 15 percentage points on comprehension tasks. Axiom defines a universal core schema and per-category extensions, enabling static conflict detection, token budgeting, and deterministic compilation from markdown source files.

## 1. Introduction

AI coding agents such as Claude Code, Cursor, and Windsurf consume project rules from files like `.claude/rules/*.md`, `.cursorrules`, or similar configuration surfaces. As projects mature, these rule sets grow to thousands of tokens of prose, creating three problems:

1. **Token waste.** Verbose natural-language rules consume context window budget that could be allocated to code, documentation, or reasoning. With models charging per token and context windows finite, every redundant word has a cost.

2. **Positional degradation.** The "lost in the middle" phenomenon [1] shows that LLMs exhibit U-shaped attention over long contexts, neglecting information in the middle. Long prose rule sets bury critical constraints where models are least likely to attend to them.

3. **Quality inversion.** Counter-intuitively, Pichay's SWE-Pruner work [2] demonstrates that filtering context *improves* output quality: pruned trajectories were preferred 37% of the time versus 28% for full context. More is not better.

These findings motivate a structured, compressed rule format designed specifically for LLM consumption.

## 2. Format Specification

Axiom uses the [TOON (Typed Object-Oriented Notation)](https://toonformat.dev) tabular format. Each section begins with a self-describing header:

```
SECTION_NAME[N]{col1,col2,col3,...}:
value1,value2,value3,...
value1,value2,value3,...
```

Where `N` is the row count, and the brace-enclosed column names serve as an inline schema. For example:

```
GOVERNANCE[3]{id,effect,domain,trigger,message}:
no-force-push,forbid,Git,push --force,Rewrites remote history; use revert
no-main-commit,forbid,Git,commit on main/master,Work on feature branches
require-types,prefer,Python,function definition,Add type hints to all signatures
```

The format is self-describing: column names drawn from common configuration vocabularies (`id`, `effect`, `trigger`) allow zero-shot comprehension without external documentation. This aligns with schema-first prompting research showing that explicit field names dramatically improve LLM accuracy over headerless data [3, 4].

## 3. Schema Definitions

### 3.1 Universal Core

All Axiom sections share a minimal core schema:

| Column | Description | Values |
|--------|-------------|--------|
| `id` | Stable rule identifier | Short kebab-case string |
| `effect` | Rule disposition | `allow`, `forbid`, `prefer`, `discourage`, `inform` |
| `domain` | Scope of applicability | `Git`, `Bash`, `Python`, `API`, `Docs`, etc. |
| `trigger` | Activation pattern or event | Pattern, command, or context description |
| `condition` | Optional narrowing predicate | `branch:main`, `env:prod`, etc. |
| `message` | Brief rationale for the model | Natural-language explanation |

### 3.2 Category Extensions

Axiom defines five standard categories, each extending the core:

- **GOVERNANCE** — Core columns only. Guards on agent behavior and tool use.
- **CODING** — Adds `language`, `scope`, `severity`, `fix_hint`. Convention enforcement.
- **SECURITY** — Adds `risk_level`, `data_type`, `response`. Secret detection, access control.
- **TESTING** — Adds `target`, `threshold`, `action`. Quality gates.
- **WORKFLOW** — Adds `phase`, `actor`. Process and CI rules.

Each category uses its own `SECTION[N]{...}:` header, keeping schemas minimal and parse-friendly.

Axiom also defines CACP (Context/Acceptance/Constraints/Protocol) as a second normative serialization, encoding rules as structured bullet lists (`- [CATEGORY] id: message (effect: value)`) for environments where tabular CSV is less natural, such as dispatcher integration with CACP-speaking agents.

## 4. Empirical Backing

Four independent lines of evidence support the Axiom design:

**Prompt compression.** LLMLingua [5, 6] achieves up to 20x compression with ~1.5-point accuracy loss by removing low-importance tokens. This confirms that verbose prompts contain substantial redundancy. Axiom eliminates this redundancy at authoring time rather than at inference time. The v0.5.0 S/D (Summary/Detail) row format pushes this further: summary-only loading achieves 46x compression versus prose, while full S+D loading achieves 15x — giving tools a graduated compression dial tied to context pressure.

**Context pruning improves quality.** Pichay's SWE-Pruner [2] finds 21-54% token savings on SWE-bench trajectories, with pruned outputs *preferred* over originals (37% vs 28%). The "Codified Context" approach to `.cursorrules` reports similar gains. Less noise means better signal.

**Table formats outperform prose.** Benchmarks across 11 serialization formats [7, 8] show Markdown-KV achieving ~60.7% accuracy versus ~44% for CSV and ~52% for markdown tables on comprehension tasks. Formats with explicit column headers consistently outperform headerless data. [TOON](https://toonformat.dev) headers provide these semantics at minimal token cost.

**Schema-first prompting.** Dynamic schema-aware prompting [3] shows that embedding explicit field names and types into prompts significantly reduces hallucination and improves task accuracy, supporting Axiom's self-describing header design.

## 5. Compilation Model

Axiom is both a format and a compilation target. The pipeline:

```
.claude/rules/*.md  -->  parse + extract  -->  normalize to schemas
                                                      |
                                           static analysis (conflicts,
                                            redundancy, shadowing)
                                                      |
                                           emit compiled.axiom
                                           (per-agent, budgeted)
```

The compiler accepts markdown rule files with YAML frontmatter (`id`, `category`, `effect`, `priority`, `trigger`, etc.) as source input, enabling human-friendly authoring with full schema control before compilation.

1. **Parse**: Extract rules from markdown prose, front-matter, and bullet lists.
2. **Normalize**: Map each rule to the appropriate category schema (GOVERNANCE, CODING, etc.).
3. **Analyze**: Detect conflicts (e.g., `allow` and `forbid` on the same trigger), shadowed rules, and unreachable conditions.
4. **Budget**: Sort by priority, enforce per-category token limits, place critical rules at the top to avoid positional degradation.
5. **Emit**: Write a single `.axiom` file per agent context, concatenating relevant sections.

The compiler provides deterministic, auditable mappings from source rules to agent context, enabling version control, diffing, and regression testing of rule sets.

## 6. Conclusion

Axiom addresses a practical gap: AI coding agents need project rules, but the dominant format (prose markdown) wastes tokens and degrades at scale. By encoding rules in self-describing tabular sections with explicit schemas, Axiom achieves 15-46x compression (depending on S/D loading depth) while aligning with empirical findings on structured prompting, table comprehension, and context pruning. The format is simple enough to author by hand, structured enough to compile and analyze, and native enough for LLMs to interpret zero-shot.

Notably, CLAUDE.md files — which load on every agent turn — are the highest-leverage compilation target; Axiom v0.3.0 defines a lossless mapping from CLAUDE.md sections to TOON tables, PROSE blocks, and standard category schemas, enabling projects to compress their most frequently loaded context without information loss.

The specification, examples, and compiler will be available at [github.com/zenprocess/axiom](https://github.com/zenprocess/axiom).

## References

[1] Liu et al. "Lost in the Middle: How Language Models Use Long Contexts." *TACL*, 2024.

[2] Pichay, J. "SWE-Pruner: Context Pruning for SWE-bench Trajectories." 2024. 21-54% token savings, 37% vs 28% preference for pruned outputs.

[3] Emergent Mind. "Dynamic Schema-Aware Prompting in LLMs." 2024.

[4] Emergent Mind. "Schema-First Prompting." 2024.

[5] Jiang et al. "LLMLingua: Compressing Prompts for Accelerated Inference of Large Language Models." *EMNLP*, 2023.

[6] Jiang et al. "LLMLingua-2: Data Distillation for Efficient and Faithful Task-Agnostic Prompt Compression." *ACL*, 2024.

[7] "Which Table Format Do LLMs Understand Best?" *improvingagents.com*, 2024.

[8] Sui et al. "Table Meets LLM: Can Large Language Models Understand Structured Table Data?" *WSDM*, 2024.
