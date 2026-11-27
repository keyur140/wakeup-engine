# Deviations log

**KEYUR SHAILESHKUMAR PATEL** (ORCID https://orcid.org/0009-0008-5261-043X).

A deviation is any change to the plan after it was written down. Changes made **before the freeze** are
listed here so readers can see how the plan evolved. Changes **after the freeze** are also detected
automatically by SHA-256 (`DEVIATION_FROM_FREEZE` in every run) and must be added here with a reason.

## Before the freeze (version 0.1.0 -> 0.2.0, 2026-11-03)

No real data had been collected for any confirmatory item when these were made.

| # | Change | Why | Source |
|---|---|---|---|
| P1 | Development / confirmatory split of the sleeping beauties (20/80, SHA-256) | Lets us explore on real data without touching the test data | Author's MEWS project; D12 |
| P2 | Exploratory run with 4 practice forward problems | Keeps the 20 preregistered problems unseen | D12 |
| P3 | Known-answer gate and answer-collapse rule | An AI judge can look fine and carry no information (AUC 0.495, 1,152 identical scores in the author's AI-music preprint) | D13 |
| P4 | Disguised-text check | Tests recognition of wording vs reasoning | D14 |
| P5 | H1b, engine vs plain search, co-primary | Synthetic world W4 beat chance with no reasoning, by word overlap alone | D15 |
| P6 | Prompt leak scan; anonymizer also strips DOIs, URLs, IDs and "et al." | Automatic proof that no clue reached the model | Replication Oracle lessons |
| P7 | Eleven self-checks; per-item seeds; per-candidate score files | Every headline number can be rebuilt a second way | Author's earlier projects |
| P8 | Judge prompt made generic ("blind reviewer"), not antibiotic-specific | The same prompt serves practice and real problems | Consistency |
| P9 | Frozen sample and gate files hashed into the registration | The confirmatory sample cannot change after registration | MEWS lock file |
| P10 | `confirm` replaces the separate `backtest` / `forward` commands and refuses to run unless frozen | Prevents accidental confirmatory runs | Safety |
| P11 | Forward-test hit needs at least min(2, judges used) judges at >= 4 | Applies the rule when a judge is excluded by the gate | Follows from P3 |
| P12 | Preregistered secondary test S1: H1a on unrecognized items only (was a sensitivity analysis) | Exploratory run: all engine hits among recognized items (ISSUES I17) | D18 |

## After the freeze

| # | Change | Why | Decision |
|---|---|---|---|
| A1 | 2026-11-27, after the first freeze and before OSF registration: confirmatory item W1993374508 excluded (`excluded_before_registration` in `config/study.yaml`); study re-frozen | An accidental `confirm` start by a faulty test partly processed it (1 need summary, 29 decoy re-rank scores; sleeping beauty not scored; no result computed or seen). ISSUES I21 | D20 |
