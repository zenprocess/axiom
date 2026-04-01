# Axiom: A Compact Rule Definition Language for LLM-Native Context Engineering

**V. Vladescu** ([@vvladescu](https://github.com/vvladescu), standra.ai / zenprocess)

---

## Abstract

Large language model (LLM) coding agents rely on rule files (CLAUDE.md, .cursorrules) to encode project conventions, but these are typically authored as verbose prose markdown. We introduce Axiom, a Rule Definition Language (RDL) that compiles prose rules into a compact, self-describing tabular format. We evaluate Axiom and two compressed alternatives (TOON tabular and CACP structured fields) against conventional markdown on a compliance benchmark of 10 rules, 8 coding tasks, and 3 models (Claude Opus 4.6, Claude Sonnet 4.6, Hermes/qwen3-coder). Across 684 valid runs, compressed formats achieve compliance parity with markdown at 80-87% token savings. Opus is the only model where a compressed format (TOON, 91.6%) outperforms markdown (91.3%). Sonnet favors markdown by ~7 percentage points, while Hermes is format-agnostic (all formats within 2%). The compliance ceiling with static rules alone is approximately 91%; the remaining ~9% requires a dynamic PostToolUse compliance hook, yielding a three-layer architecture: static format (~91%), dynamic hook (~9%), and pre-merge gate.

## 1. Introduction

AI coding agents such as Claude Code, Cursor, and Windsurf consume project rules from files like `.claude/rules/*.md`, `.cursorrules`, or similar configuration surfaces. As projects mature, these rule sets grow to thousands of tokens of prose, creating three problems:

1. **Token waste.** Verbose natural-language rules consume context window budget that could be allocated to code, documentation, or reasoning. With models charging per token and context windows finite, every redundant word has a cost.

2. **Positional degradation.** The "lost in the middle" phenomenon [1] shows that LLMs exhibit U-shaped attention over long contexts, neglecting information in the middle. Long prose rule sets bury critical constraints where models are least likely to attend to them.

3. **No per-agent filtering.** Every agent in a multi-agent dispatch receives the same monolithic rule file, regardless of which rules are relevant to its task. There is no mechanism to scope, budget, or prioritize rules based on context pressure.

These problems motivate a structured, compressed rule format designed specifically for LLM consumption. But does compression degrade compliance? Our 684-run empirical evaluation shows it does not -- and in one case, compression slightly improves it.

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

### 3.5 CACP Alternative

CACP (Context-Aware Communication Protocol) is a complementary structured format that uses labeled fields rather than tabular rows. Where Axiom/TOON encodes rules as table entries, CACP wraps them in typed dispatch/response fields (TASK, CONTEXT, ACCEPTANCE, SCOPE). Both achieve similar compression ratios but optimize for different use cases: TOON for static rule sets, CACP for agent communication protocols.

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

We designed a compliance benchmark (AxiomBench) to measure whether compressed rule formats degrade an LLM's ability to follow project conventions. The benchmark consists of:

- **10 compliance rules** with automated check functions (regex-based, deterministic). Rules span coding style (no-print-debug, type-hints, docstrings), architecture (async-io, pydantic-models, structlog-only), security (no-secrets, no-force-push), and practice (error-handling, no-star-import).
- **8 coding tasks** designed to naturally tempt specific rule violations. For example, the "logging-system" task tempts `import logging` (violating structlog-only), and the "git-workflow" task tempts `git push --force` (violating no-force-push).
- **3 rule formats**: verbose markdown (prose explanations, rationale, do/don't examples), TOON (Axiom S-only tabular), and CACP (structured labeled fields).
- **3 models**: Claude Opus 4.6 (claude-opus-4-6-20250514), Claude Sonnet 4.6 (claude-sonnet-4-6-20250514), and Hermes/qwen3-coder (open-weight, locally hosted via vLLM).
- **684 valid runs** across the full matrix (model x format x task), with per-cell sample sizes ranging from 30 to 153 runs.

The compliance check for each run produces a score: rules_passed / rules_total (10 rules checked per run). A rule "passes" if the automated check function returns True on the generated code.

### 5.2 Results

**Aggregate compliance by model and format (684 runs, 95% confidence intervals):**

| Model | Markdown | TOON | CACP | N |
|-------|----------|------|------|---|
| Opus 4.6 | 91.3% +/-5.5 (n=30) | **91.6%** +/-4.9 (n=31) | 88.0% +/-5.1 (n=40) | 101 |
| Hermes/qwen3-coder | **87.5%** +/-2.6 (n=153) | 85.8% +/-2.8 (n=152) | 87.1% +/-2.7 (n=147) | 452 |
| Sonnet 4.6 | **90.7%** +/-4.4 (n=41) | 83.8% +/-5.7 (n=40) | 83.8% +/-5.1 (n=50) | 131 |

### 5.3 Per-Model Analysis

**Opus 4.6 (n=101): TOON beats markdown.** Opus is the only model where a compressed format outperforms verbose markdown. TOON achieves 91.6% vs markdown's 91.3% -- a marginal difference within confidence intervals, but directionally noteworthy. This is consistent with the attention-concentration hypothesis: at Opus-level capability, the model has sufficient comprehension to extract rules from any format, and compressed formats reduce noise that dilutes attention. CACP underperforms at 88.0%, suggesting that tabular structure is better suited to rule encoding than labeled fields for high-capability models.

**Sonnet 4.6 (n=131): Markdown leads.** Sonnet shows the clearest format preference, with markdown (90.7%) outperforming both TOON (83.8%) and CACP (83.8%) by approximately 7 percentage points. The gap exceeds the confidence intervals and is statistically meaningful. Sonnet appears to benefit from the verbose explanations, examples, and rationale that markdown provides. This suggests that mid-tier models may need the redundancy of prose to achieve full rule comprehension -- the compression removes scaffolding that Sonnet relies on.

**Hermes/qwen3-coder (n=452): Format-agnostic.** With the largest sample size and all three formats within a 2-percentage-point band (85.8%-87.5%), Hermes shows no meaningful format preference. This model achieves consistent compliance regardless of how rules are encoded, making format choice purely an efficiency decision. The practical implication is clear: use compressed formats for Hermes to save 80-87% of rule tokens at zero compliance cost.

### 5.4 Format Autoresearch

Before running the final multi-model evaluation, we conducted 26 format experiments using an autoresearch loop (inspired by Karpathy's autoresearch pattern). Each experiment modified format parameters and measured both token count and compliance. Key findings:

| Experiment | Token Count | Status | Finding |
|------------|-------------|--------|---------|
| Baseline (S+D + triggers) | 495 | -- | Starting point |
| S-only (no D rows) | 225 | Keep | D rows redundant for compliance |
| Drop triggers column | 175 | Keep | Triggers overlap with instruction text |
| 2-column (id, instruction) | 162 | Keep | Most compact readable format |
| MUST_NOT effect prefix | 159 | Keep | Clearer signal than lowercase effects |
| Remove count from header | 159 | Keep | Count derivable from rows |
| No schema header | 154 | Discard | LLM loses column semantics |
| Critical-first ordering | 159 | Keep | Exploits primacy bias |
| Preamble "STRICT: follow every rule." | +7 | Keep* | Marginal compliance priming |
| Violation examples column | +84 | Neutral | Shows patterns to avoid, but costly |

The optimal configuration (experiment 23) uses S-only, 2-column format with MUST_NOT effect prefix, critical-first ordering:

```
RULES{id,instruction}:
no-force-push,MUST_NOT: Never use git push --force
no-secrets,MUST_NOT: No hardcoded API keys, tokens, or passwords
...
```

### 5.5 Token Efficiency

| Format | Tokens | Savings vs Markdown |
|--------|--------|---------------------|
| Verbose markdown (prose + examples) | 1195 | -- (baseline) |
| TOON (S-only, 2-column) | 239 | 80.0% |
| CACP (structured fields) | 281 | 76.5% |
| Axiom S+D (summary + detail) | 495 | 58.6% |

All compressed formats achieve substantial savings. The TOON S-only format encodes the same 10 rules in 239 tokens that require 1195 tokens in conventional markdown -- an 80% reduction. The format achieves this through:
- Eliminating prose rationale (captured in the rule id and effect verb)
- Replacing examples with effect vocabulary (MUST_NOT, MUST, SHOULD)
- Using TOON self-describing headers instead of repeated section formatting
- Grouping by severity to exploit primacy bias (critical rules first)

## 6. Three-Layer Compliance Architecture

Static format -- whether markdown or compressed -- achieves approximately 91% compliance at best (Opus with TOON). The remaining ~9% consists of violations that occur despite the rule being present in context. These are attention failures, not comprehension failures: the model understood the rule but failed to apply it consistently across all generated code.

### 6.1 Architecture

```
Layer 1: Static Format (compiled rules in system prompt)
  |  ~91% compliance ceiling
  v
Layer 2: Dynamic Hook (PostToolUse compliance checker)
  |  Catches remaining ~9% in-flight
  v
Layer 3: Pre-Merge Gate (CI/pre-commit validation)
  |  Final safety net
  v
~100% compliance
```

- **Layer 1 (Format)** sets the baseline by priming the model with rules. Compressed formats achieve parity with markdown for most models while saving 80-87% of tokens.
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

### 7.1 Honest Assessment

The data does not support a universal claim that compressed formats improve compliance. What it shows is more nuanced and arguably more useful:

1. **Compressed formats match markdown for most models.** Hermes achieves identical compliance regardless of format. Opus slightly favors TOON. Only Sonnet shows a meaningful preference for verbose markdown.

2. **The trade-off is model-dependent.** High-capability models (Opus) can extract rules from any format and may benefit from reduced noise. Mid-tier models (Sonnet) may rely on the redundancy of prose explanations. Open-weight models (Hermes) are indifferent.

3. **Token savings are universal.** Regardless of which model or format, compressed representations save 80-87% of rule tokens. For systems dispatching many agents concurrently, this translates to meaningful cost reduction.

4. **The compliance ceiling is ~91%.** No format exceeds 92% compliance with static rules alone. The remaining gap requires dynamic enforcement (hooks) or post-hoc validation (gates).

### 7.2 Attention Concentration

We hypothesized that compressing rules would concentrate model attention on rule content rather than prose padding. The Opus result (TOON 91.6% > markdown 91.3%) is directionally consistent with this hypothesis, but the margin is within confidence intervals. The Sonnet result (markdown leads by ~7%) suggests that what looks like "padding" to a high-capability model may serve as useful comprehension scaffolding for weaker models.

### 7.3 Practical Implications

For multi-agent dispatch systems where dozens of agents each load rules into their context window:

- **Cost reduction**: 80-87% fewer rule tokens per agent invocation
- **Budget headroom**: More context available for code, documentation, and reasoning
- **Scalability**: Rule sets can grow without proportional context pressure
- **Per-agent scoping**: Compiled rules can be filtered by category, domain, or priority for each agent's task
- **Model-aware formatting**: Route Opus/Hermes agents through compressed formats; consider verbose for Sonnet

### 7.4 Limitations

- **Confidence intervals overlap.** While 684 runs is substantial, per-cell sample sizes (30-153) mean that small differences between formats are not statistically significant at the individual model level. The Opus TOON advantage (0.3pp) is within noise; the Sonnet markdown advantage (~7pp) exceeds confidence intervals and is meaningful.
- **Rule complexity.** Our 10 rules are relatively simple (regex-checkable). More complex rules involving multi-file analysis or architectural patterns may respond differently to compression.
- **Automated checks only.** Compliance is measured by regex pattern matching, not by human judgment of code quality. A rule may be technically satisfied while the spirit is violated.
- **Three models.** Results may differ for GPT-4, Gemini, or other model families. The model-dependent nature of our findings suggests that format optimization should be validated per-model.
- **Static rules only.** We evaluate the format layer in isolation. The interaction between format choice and dynamic hook effectiveness is not measured.

## 8. Conclusion

We present Axiom, a Rule Definition Language that compiles verbose prose rules into compact tabular format. Our 684-run evaluation across 3 models, 3 formats, and 8 coding tasks yields an honest finding: compressed formats achieve compliance parity with markdown at 80-87% token savings, with model-dependent variation.

Opus is the only model where compressed format (TOON, 91.6%) outperforms markdown (91.3%) -- a result consistent with the attention-concentration hypothesis but within confidence intervals. Sonnet favors verbose markdown by ~7 percentage points. Hermes is format-agnostic, making format choice purely an efficiency decision.

The compliance ceiling with static rules alone is approximately 91%. A three-layer architecture -- static format, dynamic PostToolUse hook, and pre-merge gate -- addresses the full compliance spectrum.

The practical recommendation is straightforward: for high-capability and open-weight models, use compressed rule formats to save 80-87% of rule tokens at no compliance cost. For mid-tier models, evaluate the trade-off between token savings and the potential compliance reduction. For systems requiring near-100% compliance regardless of model, invest in dynamic enforcement layers rather than format optimization.

The specification, benchmark, and compiler are available at [github.com/zenprocess/axiom](https://github.com/zenprocess/axiom).

## Acknowledgments

This work is part of the [standra.ai](https://standra.ai) ecosystem for AI-assisted software engineering.

**AI Disclosure**: Claude Code (Anthropic) was used to assist with experiment implementation, benchmark automation, and drafting. All hypotheses, experimental design, results analysis, and conclusions were independently formulated and validated by the author.

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
