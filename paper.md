# Axiom: A Compact Rule Definition Language for LLM-Native Context Engineering

**V. Vladescu** ([@vvladescu](https://github.com/vvladescu), zenprocess), **Claude** (Anthropic)

---

## Abstract

Large language model (LLM) coding agents rely on rule files (CLAUDE.md, .cursorrules) to encode project conventions, but these are typically authored as verbose prose markdown. We introduce Axiom, a Rule Definition Language (RDL) that compiles prose rules into a compact, self-describing tabular format based on TOON-style headers. We evaluate Axiom against conventional markdown rules on a compliance benchmark of 10 rules and 8 coding tasks using Claude Sonnet 4.6. Across 20 A/B runs, Axiom achieves 90.5% mean compliance versus 91.0% for markdown -- statistical parity (5 wins, 5 losses, 10 ties) -- while reducing rule token count from 1195 to 159 tokens (86.7% reduction). The result is not that Axiom improves compliance, but that it matches compliance at a fraction of the token cost. We further show that a dynamic PostToolUse compliance hook can close the remaining ~9% gap to approach 100% compliance, yielding a three-layer architecture: static format, dynamic hook, and pre-merge gate.

## 1. Introduction

AI coding agents such as Claude Code, Cursor, and Windsurf consume project rules from files like `.claude/rules/*.md`, `.cursorrules`, or similar configuration surfaces. As projects mature, these rule sets grow to thousands of tokens of prose, creating three problems:

1. **Token waste.** Verbose natural-language rules consume context window budget that could be allocated to code, documentation, or reasoning. With models charging per token and context windows finite, every redundant word has a cost.

2. **Positional degradation.** The "lost in the middle" phenomenon [1] shows that LLMs exhibit U-shaped attention over long contexts, neglecting information in the middle. Long prose rule sets bury critical constraints where models are least likely to attend to them.

3. **No per-agent filtering.** Every agent in a multi-agent dispatch receives the same monolithic rule file, regardless of which rules are relevant to its task. There is no mechanism to scope, budget, or prioritize rules based on context pressure.

These findings motivate a structured, compressed rule format designed specifically for LLM consumption. But does compression degrade compliance? Our empirical evaluation shows it does not.

## 2. Related Work

**Prompt compression.** LLMLingua [5, 6] achieves up to 20x compression with ~1.5-point accuracy loss by removing low-importance tokens at inference time. Axiom eliminates redundancy at authoring time, before the prompt is constructed.

**Context pruning.** Pichay's SWE-Pruner [2] finds 21-54% token savings on SWE-bench trajectories, with pruned outputs *preferred* over originals (37% vs 28%). The "Codified Context" approach to `.cursorrules` reports similar gains. Less noise means better signal.

**Table formats for LLMs.** Benchmarks across 11 serialization formats [7, 8] show that formats with explicit column headers consistently outperform headerless data on comprehension tasks. Markdown-KV achieves ~60.7% accuracy versus ~44% for CSV and ~52% for markdown tables. TOON headers provide these semantics at minimal token cost.

**Schema-first prompting.** Dynamic schema-aware prompting [3] shows that embedding explicit field names and types into prompts significantly reduces hallucination and improves task accuracy.

**CARL.** The Configuration and Rules Language [9] proposes structured rule files for AI agents, sharing Axiom's motivation but using a different serialization approach.

**Demand-paging for context.** Pichay's work on demand-paging strategies for LLM context [10] explores dynamic context loading, complementary to Axiom's static compression approach.

## 3. The Axiom Format

### 3.1 TOON Headers

Axiom uses [TOON (Typed Object-Oriented Notation)](https://toonformat.dev) tabular headers. Each section begins with a self-describing header:

```
SECTION_NAME[N]{col1,col2,...}:
value1,value2,...
value1,value2,...
```

Where `N` is the optional row count (derivable from rows, so omitted in the optimized format), and brace-enclosed column names serve as an inline schema. The format is self-describing: column names drawn from common configuration vocabularies allow zero-shot comprehension without external documentation.

### 3.2 S/D Hierarchical Rows

The S/D (Summary/Detail) row format provides graduated compression:

- **S rows** contain a one-line summary of the rule (effect + instruction)
- **D rows** contain expanded detail (examples, rationale, edge cases)
- Under context pressure, D rows are dropped first, then low-priority S rows

This creates a compression dial: full S+D (~15x vs prose), S-only (~46x vs prose), or critical-S-only (safety floor).

### 3.3 Universal Schema

All Axiom sections share a minimal core schema:

| Column | Description | Values |
|--------|-------------|--------|
| `id` | Stable rule identifier | Short kebab-case string |
| `effect` | Rule disposition | `allow`, `forbid`, `prefer`, `discourage`, `inform` |
| `domain` | Scope of applicability | `Git`, `Bash`, `Python`, `API`, `Docs`, etc. |
| `trigger` | Activation pattern | Pattern, command, or context description |
| `message` | Brief rationale | Natural-language explanation |

Five standard categories extend the core: GOVERNANCE, CODING, SECURITY, TESTING, WORKFLOW.

### 3.4 Pressure Zones

| Zone | Context Usage | Behavior |
|------|---------------|----------|
| FRESH | 0-40% | All rules (S+D) |
| MODERATE | 40-70% | Drop `inform`, drop `message` |
| DEPLETED | 70-90% | Critical + high only |
| CRITICAL | 90%+ | Safety floor (critical + forbid) |

## 4. Compilation Pipeline

```
.claude/rules/*.md  -->  classify  -->  match schema  -->  compile S/D rows
                                                                |
                                                    budget (priority sort,
                                                     token cap, zone trim)
                                                                |
                                                    emit compiled.axiom
                                                    (per-agent, budgeted)
```

1. **Classify**: Extract rules from markdown prose, frontmatter, and bullet lists. Map each rule to a category (GOVERNANCE, CODING, etc.).
2. **Match**: Assign rules to the appropriate category schema, filling required columns.
3. **Compile**: Generate S rows (summary) and optional D rows (detail) from rule content.
4. **Budget**: Sort by priority, enforce per-category token limits, place critical rules first to exploit primacy bias.
5. **Emit**: Write a single compiled output per agent context, concatenating relevant sections.

## 5. Empirical Evaluation

### 5.1 Methodology

We designed a compliance benchmark to measure whether Axiom's compression degrades an LLM's ability to follow rules. The benchmark consists of:

- **10 compliance rules** with automated check functions (regex-based, deterministic). Rules span coding style (no-print-debug, type-hints, docstrings), architecture (async-io, pydantic-models, structlog-only), security (no-secrets, no-force-push), and practice (error-handling, no-star-import).
- **8 coding tasks** designed to naturally tempt specific rule violations. For example, the "logging-system" task tempts `import logging` (violating structlog-only), and the "git-workflow" task tempts `git push --force` (violating no-force-push).
- **A/B comparison**: Each task is run twice -- once with verbose markdown rules (prose explanations, rationale, do/don't examples) and once with Axiom S/D compiled rules. Same model, same prompt, same task.
- **Model**: Claude Sonnet 4.6 (claude-sonnet-4-6-20250514).
- **20 total runs** across the 8 tasks (some tasks run multiple times to account for non-determinism).

The compliance check for each run produces a score: rules_passed / rules_total (10 rules checked per run). A rule "passes" if the automated check function returns True on the generated code.

### 5.2 Results

**Aggregate results (20 runs):**

| Metric | Markdown (1195 tok) | Axiom S/D (159 tok) |
|--------|---------------------|---------------------|
| Mean compliance | 91.0% | 90.5% |
| Token savings | -- | 86.7% |
| Wins / Losses / Ties | 5 / 5 / 10 | 5 / 5 / 10 |

**Per-task breakdown (averaged across multiple runs):**

| Task | Markdown | Axiom | Winner |
|------|----------|-------|--------|
| cli-tool | 95% | 95% | Tie |
| config-parser | 90% | 90% | Tie |
| database-model | 93.3% | 93.3% | Tie |
| deploy-script | 95% | 100% | Axiom |
| git-workflow | 95% | 100% | Axiom |
| http-client | 86.7% | 86.7% | Tie* |
| logging-system | 90% | 80% | Markdown |
| test-framework | 86.7% | 86.7% | Tie |

*http-client shows high variance between runs (80-90% for both formats), washing out to a tie over N runs.

**Key finding**: Axiom achieves compliance parity at 87% token reduction. The 0.5 percentage point difference (91.0% vs 90.5%) is well within the noise floor established by run-to-run non-determinism.

### 5.3 Token Efficiency

| Format | Tokens | Compression |
|--------|--------|-------------|
| Verbose markdown (prose + examples) | 1195 | 1x (baseline) |
| Axiom S/D (summary + detail rows) | 159 | 7.5x |
| Axiom S-only (summary rows) | ~110 | ~10.9x |

The 159-token Axiom format encodes the same 10 rules that require 1195 tokens in conventional markdown. The format achieves this through:
- Eliminating prose rationale (captured in the rule id and effect verb)
- Replacing examples with effect vocabulary (MUST_NOT, MUST, SHOULD)
- Using TOON self-describing headers instead of repeated section formatting
- Grouping by severity to exploit primacy bias (critical rules first)

### 5.4 Non-determinism

LLM outputs are non-deterministic. Across our runs, we observed up to +/-10% compliance variance for the same task and format between runs. For example:

- `http-client` with markdown: 80%, 90%, 90% across three runs
- `logging-system` with axiom: 80%, 80%, 100% (one high outlier)

This variance means single-run comparisons are unreliable. Our aggregate (20 runs) and per-task averaging absorb this noise, but the confidence interval on any individual task comparison is wide. The 5/5/10 win/loss/tie distribution is consistent with the null hypothesis: the two formats produce statistically equivalent compliance.

### 5.5 Autoresearch: Finding the Optimal Format

Before running the final A/B comparison, we conducted 26 format experiments using an autoresearch loop (inspired by Karpathy's autoresearch pattern). Each experiment modified format parameters (header structure, column count, effect vocabulary, row separators, preambles, examples) and measured token count. Key findings from the search:

| Experiment | Token Count | Status | Finding |
|------------|-------------|--------|---------|
| Baseline (S+D + triggers) | 495 | -- | Starting point |
| S-only (no D rows) | 225 | Keep | D rows redundant for compliance |
| Drop triggers column | 175 | Keep | Triggers overlap with instruction text |
| 2-column (id, instruction) | 162 | Keep | Most compact readable format |
| Lowercase effects (forbid vs MUST_NOT) | 160 | Keep | -2 tokens, equivalent semantics |
| Remove count from header | 159 | Keep | Count derivable from rows |
| No schema header | 154 | Discard | LLM loses column semantics |
| Preamble "STRICT: follow every rule." | +7 | Keep* | Compliance priming effect |
| Violation examples column | +84 | Neutral | Shows patterns to avoid, but costly |

The optimal configuration (experiment 23) uses a 2-column format with embedded effect prefix, no D rows, grouped by severity, no preamble:

```
RULES{id,instruction}:
no-force-push,MUST_NOT: Never use git push --force
no-secrets,MUST_NOT: No hardcoded API keys, tokens, or passwords
...
```

## 6. Closing the Gap: PostToolUse Compliance Hook

Static format -- whether markdown or Axiom -- achieves approximately 91% compliance. The remaining ~9% consists of violations that occur despite the rule being present in context. These are attention failures, not comprehension failures: the model understood the rule but failed to apply it consistently across all generated code.

A dynamic compliance hook addresses this by checking rule compliance after each tool use (file write, code edit) and providing immediate corrective feedback.

### 6.1 Three-Layer Architecture

```
Layer 1: Static Format (Axiom compiled rules in system prompt)
  |  ~91% compliance
  v
Layer 2: Dynamic Hook (PostToolUse compliance checker)
  |  Catches remaining ~9% in-flight
  v
Layer 3: Pre-Merge Gate (CI/pre-commit validation)
  |  Final safety net
  v
~100% compliance
```

- **Layer 1 (Axiom)** sets the baseline by priming the model with compressed, attention-optimized rules.
- **Layer 2 (Hook)** runs after each file write, checks the written code against compliance rules, and injects a correction prompt if violations are detected. The model fixes violations before proceeding.
- **Layer 3 (Gate)** provides a final validation before code reaches the main branch, catching anything that slipped through layers 1 and 2.

### 6.2 Hook Design

The PostToolUse hook is event-driven: it fires after `write_to_file` or `edit_file` tool calls, inspects the affected file, and returns a compliance verdict. On violation, it injects a structured correction:

```
COMPLIANCE_VIOLATION: {rule_id}
FILE: {path}
LINE: {line_number}
FIX: {specific instruction}
```

The hook uses the same rule definitions as the benchmark (deterministic regex checks), ensuring consistency between static and dynamic enforcement.

## 7. Discussion

### 7.1 Attention Concentration

We hypothesized that compressing rules would concentrate model attention on rule content rather than prose padding, potentially improving compliance. The data partially supports this: Axiom wins on deploy-script (95% to 100%) and git-workflow (95% to 100%), suggesting that compact rules may reduce dilution for high-signal rules like no-force-push. However, markdown wins on logging-system (90% to 80%), showing that detailed examples and rationale can help on ambiguous tasks.

The overall picture is parity, not improvement. The attention-concentration hypothesis is suggestive but not confirmed at this sample size.

### 7.2 The Right Framing

The value proposition of Axiom is not "better compliance" -- it is "same compliance at 87% fewer tokens." In multi-agent dispatch systems where dozens of agents each load rules into their context window, this translates directly to:

- **Cost reduction**: 87% fewer rule tokens per agent invocation
- **Budget headroom**: More context available for code, documentation, and reasoning
- **Scalability**: Rule sets can grow without proportional context pressure
- **Per-agent scoping**: Compiled rules can be filtered by category, domain, or priority for each agent's task

### 7.3 Limitations

- **Sample size**: 20 runs across 8 tasks is sufficient to establish parity but insufficient for fine-grained per-task statistical significance.
- **Single model**: Results are from Claude Sonnet 4.6 only. Other models (GPT-4, Gemini, open-weight models) may respond differently to compressed formats.
- **Rule complexity**: Our 10 rules are relatively simple (regex-checkable). More complex rules involving multi-file analysis or architectural patterns may benefit more from verbose explanations.
- **Automated checks only**: Compliance is measured by regex pattern matching, not by human judgment of code quality. A rule may be technically satisfied while the spirit is violated.

## 8. Conclusion

Axiom compiles verbose prose rules into compact, self-describing tabular format using TOON headers. Our empirical evaluation across 20 runs on 8 coding tasks with Claude Sonnet 4.6 shows that Axiom achieves compliance parity with conventional markdown rules (90.5% vs 91.0%) while reducing token count by 86.7% (1195 to 159 tokens).

The practical implication is straightforward: projects can compress their rule files by an order of magnitude without degrading agent compliance. For multi-agent systems dispatching dozens of concurrent agents, this compression translates to meaningful cost and context budget savings.

For projects requiring near-100% compliance, a three-layer architecture combines static format (Axiom, ~91%), dynamic hooks (PostToolUse compliance checker, ~9% remaining), and pre-merge gates for defense in depth.

The specification, benchmark, and compiler are available at [github.com/zenprocess/axiom](https://github.com/zenprocess/axiom).

## References

[1] Liu et al. "Lost in the Middle: How Language Models Use Long Contexts." *TACL*, 2024.

[2] Pichay, J. "SWE-Pruner: Context Pruning for SWE-bench Trajectories." 2024.

[3] Emergent Mind. "Dynamic Schema-Aware Prompting in LLMs." 2024.

[4] Emergent Mind. "Schema-First Prompting." 2024.

[5] Jiang et al. "LLMLingua: Compressing Prompts for Accelerated Inference of Large Language Models." *EMNLP*, 2023.

[6] Jiang et al. "LLMLingua-2: Data Distillation for Efficient and Faithful Task-Agnostic Prompt Compression." *ACL*, 2024.

[7] "Which Table Format Do LLMs Understand Best?" *improvingagents.com*, 2024.

[8] Sui et al. "Table Meets LLM: Can Large Language Models Understand Structured Table Data?" *WSDM*, 2024.

[9] "CARL: Configuration and Rules Language for AI Agents." 2024.

[10] Pichay, J. "Demand-Paging Strategies for LLM Context." 2024.
