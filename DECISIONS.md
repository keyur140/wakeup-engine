# Design decisions

**KEYUR SHAILESHKUMAR PATEL** (ORCID https://orcid.org/0009-0008-5261-043X).
*Conducted independently; not an official Brunel University London project.*

Every judgment call in this study was put to the author as a multiple-choice question with a recommended
option. This file records the author's answer to each one. It is hashed at the freeze.

| # | Date | Question | Author's choice |
|---|---|---|---|
| D1 | 2026-10-26 | Field for the 20 forward-test problems | Antibiotic resistance |
| D2 | 2026-10-26 | Which AI reads and judges | Free open-weights models; judges from different model families than the engine |
| D3 | 2026-10-26 | Source of known sleeping beauties | Computed from OpenAlex citation histories with the Ke et al. (2015) beauty coefficient |
| D4 | 2026-10-26 | What counts as a back-test hit | True sleeping beauty in the top 10 of 1,000 candidates |
| D5 | 2026-10-26 | Replacement for human expert raters | Blind panel of 3 AI judges; agreement reported as Krippendorff's alpha |
| D6 | 2026-10-26 | Budget | $0: free API tiers and local models only |
| D7 | 2026-10-26 | Where the models run | Everything on the Groq free tier (Ollama or OpenRouter as alternatives) |
| D8 | 2026-10-26 | The 20 problems | Delegated to the AI assistant: AR14 changed from antifungals to drug-resistant UTIs, AR18 from environmental residues to untreatable gonorrhoea; the other 18 kept |
| D9 | 2026-10-26 | What the AI sees of each paper | Anonymized title + abstract |
| D10 | 2026-10-26 | "Forgotten" cut-off | At most 25 total citations |
| D11 | 2026-11-03 | How the exploratory run happens | Cloud environment with network access to OpenAlex and Groq; key stored as an environment variable |
| D12 | 2026-11-03 | Lock part of the data (as in MEWS) | Yes: SHA-256 split, 20% development (exploratory), 80% locked confirmatory; 4 separate practice problems for exploration |
| D13 | 2026-11-03 | Known-answer gate for every AI | Yes: AUC > 0.5 with one-sided p < 0.05 on the development sleeping beauties; failing models excluded |
| D14 | 2026-11-03 | Disguised-text check | Yes, as a secondary check (paraphrase by a different model family; every re-ranked text paraphrased) |
| D15 | 2026-11-03 | Make "beats plain search" a main test | Yes: H1a (beats chance) and H1b (beats hybrid search) are co-primary, Holm-corrected |
| D16 | 2026-11-04 | Models after Groq retired Llama 3.3 70B, Qwen3-32B and Kimi K2 | Option A (recommended): engine + memorization qwen/qwen3.8-27b; paraphraser openai/gpt-oss-120b; judges openai/gpt-oss-120b, openai/gpt-oss-20b, allam-2-7b (two judges share the gpt-oss family; reported) |
| D17 | 2026-11-05 | Groq free tier caps the engine at 200,000 tokens/day; how to finish the exploratory run | Stay free ($0 rule kept): run resumes from cache each day until done (about 3 days) |
| D18 | 2026-11-20 | After the exploratory run: how the confirmatory test handles papers the engine model recognizes (14/21 dev items; all engine hits among them, hybrid search same split) | Option A (recommended): add a preregistered secondary test S1, engine hit@10 > chance on unrecognized items only (exact binomial, alpha 0.05, outside the H1a/H1b Holm family), with its power stated; main tests unchanged |
| D19 | 2026-11-20 | After the exploratory run: how many hybrid-search results the engine re-reads (top 50 caps the engine at 52% on dev data; top 100 would give 57%) | Option A (recommended): keep top 50; top 100 would roughly double engine calls and run time on the free tier |
| D20 | 2026-11-27 | After the freeze and before OSF registration, an accidental `confirm` start (ISSUES I21) partly processed confirmatory item W1993374508 (1 need summary, re-rank scores for 29 decoys; the sleeping beauty itself was not scored and no result was computed or seen). Keep or drop the item? | Option A (recommended): exclude it from the confirmatory back-test and disclose it; 78 confirmatory items remain (minimum 50). Set in `config/study.yaml` (`excluded_before_registration`), then the study was re-frozen |

Author credit and the AI-use statement were approved by the author on 2026-10-26.
