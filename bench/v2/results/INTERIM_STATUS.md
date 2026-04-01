
=== AXIOM COMPLIANCE DATA — INTERIM RESULTS ===
51 total runs across 2 experiments (v2 bench)

SONNET (40 runs):
  markdown   n=24  avg=89.2%  (range: 70-100%)
  toon       n= 9  avg=92.2%  (range: 70-100%)
  cacp       n= 7  avg=92.9%  (range: 80-100%)

OPUS (11 runs, markdown only so far):
  markdown   n=11  avg=86.4%  (range: 80-90%)

KEY FINDINGS (interim):
1. TOON beats markdown: 92.2% vs 89.2% (+3.0%)
2. CACP beats markdown: 92.9% vs 89.2% (+3.7%)
3. Both compressed formats OUTPERFORM verbose markdown
4. Opus is LESS compliant than Sonnet on same rules (86.4% vs 89.2%)
5. Token savings: markdown ~1195 tok, TOON ~239 tok, CACP ~281 tok

REMAINING: Need TOON+CACP data for Opus to complete the comparison.
Run: python3 bench/v2/runner.py --phase final --model opus --runs 5

