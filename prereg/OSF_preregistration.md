# Wake-up Engine: A Preregistered Computational Test of Deliberately Waking Science's Sleeping Beauties

**KEYUR SHAILESHKUMAR PATEL**

ORCID: https://orcid.org/0009-0008-5261-043X

(1) MSc Artificial Intelligence student, Department of Computer Science, Brunel University London, UK

(2) Independent researcher

*Conducted independently; not an official Brunel University London project.*

Template: OSF Preregistration (standard). Version 0.2.0, drafted 2026-11-03.
Status: DRAFT until the author freezes it (`python run.py freeze --from-run runs/<exploratory run>`) and
registers it on OSF. The SHA-256 bundle hash from `prereg/FREEZE_MANIFEST.json` must be pasted into the OSF
form (section 7).

> AI assistance: Code and draft text were prepared with help from an AI assistant (Claude, Anthropic)
> under the author's direction. All design decisions, hypotheses and hit criteria were chosen by the
> author (see `DECISIONS.md`). The author takes full responsibility for the work.

### What changed from version 0.1.0 (before any confirmatory data)
Version 0.2.0 adds safeguards learned from the author's earlier projects (MEWS, Replication Oracle, the
AI-music preprint) and from synthetic validation. Each change is listed in `DEVIATIONS.md` and was made
before any confirmatory item was processed.
1. A fixed SHA-256 **development / confirmatory split** of the sleeping beauties (20% / 80%).
2. An **exploratory run** on the development part only, with 4 practice forward problems.
3. A **known-answer gate** and an **answer-collapse rule** for every AI model.
4. A **disguised-text check** (paraphrase by a different model family) and an automatic **prompt leak scan**.
5. **H1b** (engine beats plain search) added as a co-primary test, after synthetic world W4 showed that
   word overlap alone can beat chance.
6. Eleven automatic **self-checks** that recompute key numbers a second way.
7. The sleeping-beauty sample and gate decisions are **frozen as files** and hashed into the registration.

---

## 1. Study information

### 1.1 Research questions
- **RQ1 (back-test).** Given only the literature of the year before a known "sleeping beauty" paper woke up,
  can an AI engine pick that paper out of about 1,000 old papers as the one that answers the
  waking field's need, better than chance and better than plain search?
- **RQ2 (forward test).** For 20 open problems in antibiotic resistance, does the engine surface forgotten
  pre-1990 papers that blind AI judges rate as more applicable than random old papers?
- **RQ3 (reliability).** Do AI judges from different model families pass a known-answer test and agree
  enough for their ratings to be used?

### 1.2 Background and gap
Sleeping beauties (SBs) are papers ignored for years and then suddenly heavily cited. Ke et al. (2015,
PNAS) defined the beauty coefficient *B* and found SBs across 22 million papers. Later work identifies
them retrospectively from citation curves (e.g. Chaleplioglou et al., 2026, *Scientometrics*, mRNA
vaccines) or predicts them from citation and metadata features (Li, Ma & Feng, 2024, *Journal of
Informetrics*). Literature-based discovery (Swanson and successors) uses time-sliced evaluation but
mostly links concepts, not whole forgotten papers to a stated need. To the author's knowledge (search of
2026-10-26, see `docs/related_work.md`) no study has preregistered a test of whether an AI that reads the
text can match a known SB to the need that later woke it, using only information available before the
awakening.

### 1.3 Hypotheses (all directional)
- **H1a (co-primary, back-test).** The engine ranks the true SB in its top 10 more often than chance
  (chance = 10/N per item, 1% when N = 1,000).
- **H1b (co-primary, back-test).** On the same items, the engine has more top-10 hits than hybrid search
  without the AI re-reading (exact one-sided McNemar test on items where exactly one of the two hits).
- **H2 (primary, forward test).** Engine-selected candidates receive a higher mean judge applicability
  rating than random candidates from the same retrieved pool.
- **H3 (secondary).** Engine candidates are rated higher than random pre-1990 papers.
- **H4 (secondary).** The engine has more top-10 hits than BM25 alone and than dense retrieval alone.

## 2. Design plan

### 2.1 Study type
Observational, fully computational, using public bibliographic data and open-weights language
models. No human participants and no human raters.

### 2.2 The lock (development / confirmatory split)
Every selected SB is assigned to the **development** part if
`int(SHA-256("wakeup-split|20261026|<OpenAlex ID>")[:12], 16) / 16^12 < 0.20`, otherwise to the
**confirmatory** part. The rule depends on nothing but the ID and the seed.
- The exploratory run (`python run.py explore`) processes development items only. Titles of confirmatory
  items are written as `[LOCKED]` in every saved table, and self-check C6 confirms that no confirmatory item
  was processed.
- The exploratory forward test uses 4 practice problems (`config/forward_problems_dev.yaml`), never the 20
  preregistered problems.
- At freeze, the selected SB sample (with its split) and the gate decisions are copied into
  `prereg/frozen_sample.json` and `prereg/gate_frozen.json` and hashed. The confirmatory run
  (`python run.py confirm`) uses exactly these files and refuses to run unless every preregistered file
  matches the freeze.

### 2.3 Blinding
- Candidate papers are shown with author names, author-derived eponyms, four-digit years, DOIs, URLs,
  OpenAlex IDs and "et al." removed. Venue is never shown.
- An automatic **prompt leak scan** checks every text shown to a model for years, DOIs, URLs, OpenAlex IDs,
  "et al.", author surnames and study words (for example "sleeping beauty"). Leaks are counted and reported.
- In the back-test, the SB is shuffled among decoys with a per-item seeded permutation. Prompts never say
  that a sleeping beauty is present.
- In the forward test, each judge rates each item alone, in its own seeded random order, under a generic
  "blind reviewer" prompt, and is not told how the item was chosen. The un-blinding key is a separate file
  used only after all ratings are collected. Self-check C2 confirms no judge prompt contains a group label.

### 2.4 Study design
**Back-test.**
1. Draw a seeded random sample of up to 6,000 OpenAlex works (articles, published 1900-1985,
   at least 100 citations, abstract available).
2. For each, retrieve its yearly citation history (OpenAlex `group_by=publication_year` on citing works)
   up to the last complete year and compute *B*, peak year *t_m* and awakening time *t_a* exactly as in
   Ke et al. (2015).
3. Eligible SBs: sleep length *t_a* >= 10 years, awakening year *Y* between 1950 and 2018, peak yearly
   citations >= 20, *B* >= 50. Select the top 100 by *B* (ties broken by OpenAlex ID). Apply the split (2.2).
4. **Need statement.** The waking field is the most common OpenAlex primary topic among works citing
   the SB in years *Y* to *Y*+3. From that topic, take a seeded sample of up to 20 works published in
   year *Y*-1 that do not cite the SB. The engine model summarizes their open problems, instructed to
   use only these abstracts and to name no solutions. SB author surnames are removed from this text.
5. **Candidate set.** 999 decoys: articles with abstracts from the SB's OpenAlex field published within
   +/-3 years of it (fallback tiers, recorded per item: same field +/-6 years, then any field +/-3 years).
   At least 99 decoys are required.
6. **Ranking methods.** random; BM25; dense embeddings (BAAI/bge-small-en-v1.5); hybrid (reciprocal-rank
   fusion of BM25 and dense, k = 60); **engine** = hybrid, then the top 50 re-scored 0-10 by the engine
   LLM and re-ordered by that score (ties broken by hybrid rank). Ties are broken at random with a per-item seed.
   Every candidate's scores are saved per item so ranks can be recomputed (self-check C3).

**Known-answer gate (on development items only, in the exploratory run).**
For each usable development SB, each model (engine and each judge) scores the SB and 5 seeded decoys against
the need. AUC = share of (SB, decoy) pairs within an item where the SB scores higher (ties = 0.5).
One-sided permutation p (10,000 permutations; the SB position is shuffled within each item).
A model **passes** if AUC > 0.5, p < 0.05, at least 10 usable items, and it is not collapsed.
**Answer collapse:** more than 95% of a model's usable scores are identical. A judge that fails the gate
or collapses is excluded from the forward test. If fewer than 2 judges remain, the forward test is reported
as not testable. The engine's gate result is reported; it does not stop the back-test.
The gate decisions are frozen (`prereg/gate_frozen.json`) and used unchanged in the confirmatory run.

**Forward test.**
1. The 20 problems in `config/forward_problems_antibiotic_resistance.yaml` were chosen at the author's
   direction before any data were collected (seed queries drafted with AI assistance).
2. Queries = the seed queries + 5 queries proposed by the engine LLM in older vocabulary.
   Each query retrieves up to 100 OpenAlex works published before 1990 with abstracts.
3. "Forgotten" = total citations <= 25. Only forgotten papers are kept.
4. Rank with hybrid retrieval + LLM re-rank of the top 50; the top 5 are the engine candidates.
5. Controls per problem: 5 random forgotten papers from the same retrieved pool (excluding the engine's 5)
   and 5 random forgotten pre-1990 papers from a seeded global OpenAlex sample.
6. Three judges, none from the engine's family (gpt-oss-120b, gpt-oss-20b, ALLaM-2-7B; D16) rate each item for
   *applicability* (1-5) and *novelty* (1-5), using the fixed rubric in `wakeup/prompts.py`.

### 2.5 Randomization
Global seed 20261026. Per-item seeds are derived as SHA-256 of the seed and the item ID, so one item's
randomness never depends on another. numpy PCG64 generators throughout.

## 3. Sampling plan

### 3.1 Existing data
Before registration, the following will exist and will be reported as exploratory:
- offline self-tests and synthetic validation (`selftest`, `validate`, no real data);
- one exploratory run on the development SBs and the 4 practice problems (`explore`).
The exploratory run was completed on 2026-11-20 (run `20261120T194454Z_explore_23274f`, manifest SHA-256 `11a60c777e92cd0f4a1cfb6d4ffb88fb52fa99f784602394de76cf6366270775`); its full report is uploaded with this registration.
Apart from the one item disclosed below, no confirmatory SB and none of the 20 preregistered problems has been
processed. The frozen sample file contains the confirmatory IDs and metadata (needed to run them later) but no
analysis of them.

**Disclosure: one confirmatory item touched before registration (ISSUES I21, decision D20).** On 2026-11-27, after the first freeze and before this registration, running the test suite started `confirm` twice by accident (a test ran the command before checking for a freeze). Both starts were stopped by the test's 120-second timeout while still on confirmatory item 1 of 79, OpenAlex W1993374508. In total 1 need summary and re-rank scores for 29 decoy candidates were requested from the engine model. The sleeping beauty itself was not scored, no rank, hit or summary statistic was computed, and nobody looked at any reply. No other confirmatory item and none of the 20 preregistered problems was touched. The author excluded W1993374508 from the confirmatory back-test (`config/study.yaml`: `excluded_before_registration`); it is reported as an exclusion with reason `excluded_before_registration`. The test was fixed, both partial runs are kept unchanged in `runs/_INCIDENT_2026-11-27_accidental_confirm/`, and the study was then re-frozen.

### 3.2 Data collection
OpenAlex REST API (CC0 data). Every response is cached with its URL and retrieval time and can be shared as
the data snapshot. Language models are open-weights models called through free OpenAI-compatible
endpoints (Groq by default) or run locally (Ollama), at temperature 0, with every prompt and reply logged and
hashed. A **drift check** (`python run.py drift-check`) re-asks a sample of 20 recorded calls with the
cache bypassed and reports how many answers are identical; it never overwrites the stored answers.

### 3.3 Sample size and rationale
- Back-test: of the 100 selected SBs, 79 are confirmatory and 78 remain after the D20 exclusion. The confirmatory analysis requires at
  least 50 usable items. With *n* = 50 and chance = 1%, the exact one-sided test at alpha = 0.05 needs
  3 hits; the minimum detectable hit rate at 80% power is 8.4% (n = 50) or 5.3% (n = 80). These are
  computed by `wakeup/stats.py: mde_binomial` and printed in every report. Below 50 usable items the result
  is labelled underpowered.
- H1b power depends on the number of items where the engine and search disagree, which cannot be known in
  advance. A non-significant H1b is reported as inconclusive, not as "no added value".
- Forward test: 20 problems x 15 items = 300 items, 900 ratings (fewer if a judge is excluded).

### 3.4 Stopping rule
All confirmatory items are processed once. No optional stopping. Failed API calls are retried. Items that
cannot be built (no waking topic, fewer than 5 context abstracts, fewer than 99 decoys) are excluded for the
recorded reason, automatically and before any ranking. One item, W1993374508, is excluded by the author
before registration (D20, see 3.1).

## 4. Variables
- **Primary back-test outcome:** rank of the true SB under the engine (1 = best); hit = rank <= 10.
- **Secondary back-test outcomes:** hit@{1, 5, 50, 100}, MRR, median rank, for every method.
- **Gate outcomes:** AUC, permutation p, usable items, largest identical-score share, parse-failure rate.
- **Forward-test outcomes per item:** each judge's applicability and novelty; item mean and median
  across judges; count of judges rating applicability >= 4.
- **Forward-test hit:** median applicability >= 4 AND at least min(2, number of judges used) judges rate
  applicability >= 4 AND median novelty >= 3 AND total citations <= 25.
- **Memorization flag:** the engine model, shown the anonymized SB text, names a title with similarity
  >= 0.6 to the real title, or the right first-author surname with the year within +/-2.
- **Disguise outcome:** the SB's rank among the hybrid top 20 with original texts vs with all 20 texts
  rewritten by the paraphraser model (a different family from the engine).

## 5. Analysis plan

### 5.1 Statistical models
- **H1a:** exact one-sided Poisson-binomial test on the number of engine hits (chance per item = 10/N_i;
  identical to the binomial test when all N = 1,000). Wilson 95% CI on the hit rate.
- **H1b:** exact one-sided McNemar (binomial on discordant items), engine vs hybrid.
- **H2, H3:** one-sided stratified permutation test (10,000 permutations, group labels shuffled within each
  problem) on the difference in mean item applicability, engine vs control. Fisher's exact test on hit rates
  is reported as secondary.
- **H4:** exact McNemar tests, engine vs BM25 and engine vs dense.
- MRR with 10,000-sample bootstrap 95% CIs.

### 5.2 Inference criteria
alpha = 0.05. H1a and H1b are Holm-corrected as a family of two. H2 is tested at 0.05 (different data and
question); H2 and H3 are Holm-corrected together. Secondary tests are Holm-corrected within each study.
A supportive claim that the engine "reads for meaning" requires **both** H1a and H1b.

### 5.3 Data exclusion
Only the automatic exclusions in 3.4, the gate rule in 2.4, and the author's pre-registration exclusion of W1993374508 (D20, see 3.1). Unparseable model replies are not re-asked:
in re-ranking a parse failure scores -1 (it ranks last among the re-ranked); in judging it counts as a
missing rating. Parse-failure counts are reported.

### 5.3b Secondary test S1
**Preregistered secondary test S1 (D18): recognized papers.** Among confirmatory sleeping beauties NOT flagged as memorized by the recognition probe, is the engine's hit@10 rate above chance (1%)? Exact one-sided binomial test, alpha 0.05, not part of the Holm family of H1a/H1b. The number of unrecognized items, the minimum detectable rate at 80% power, and hybrid search's hit@10 on the same items (descriptive) are reported next to it; the test is already computed by the code (summary field sensitivity_memorization), and the extra numbers come from the saved ranks file (results/backtest_ranks.csv). Reason: in the exploratory run all 8 engine hits were among recognized items, and hybrid search showed the same split, so recognition may mark easier papers rather than memory.

### 5.4 Reliability of the judges
Krippendorff's alpha (ordinal) over the judges used. If applicability alpha < 0.40, the forward test is
reported as exploratory only.

### 5.5 Sensitivity and robustness analyses (planned)
1. H1a repeated without SBs flagged as memorized (now the preregistered secondary test S1, see below); decoy false-recognition rate reported for comparison.
2. Disguised-text check: one-sided Wilcoxon signed-rank test that the SB ranks worse when disguised. A large
   drop is read as a sign of recognition rather than reasoning.
3. Retrieval methods repeated with the raw context abstracts instead of the LLM-written need.
4. Decoy fallback tier and embedding backend reported per item. A TF-IDF fallback is a deviation.

### 5.6 Self-verification (reported on every run)
C1 every AI reply matches its stored SHA-256; C2 no group label in judge prompts; C3 ranks recomputed
from saved per-candidate scores; C4 headline numbers recomputed from the ranks file; C5 the H1a p-value
recomputed by simulation; C6 the lock held; C7 need built from year *Y*-1; C8 one target and no duplicate
candidates per set; C9 leak scan; C10 Krippendorff's alpha recomputed with a second implementation; C11 gate
decisions follow the rule. A failed check is reported prominently and investigated before interpretation.

### 5.7 Validation of the machinery (before registration)
`python run.py validate` runs the full pipeline on synthetic worlds with known answers: W1 signal, W2 null,
W3 memorizer, W4 word-overlap-only, a lock test, and 40 null worlds to estimate the H1a false-positive rate.
Its report is attached to the registration. It tests the code, not any scientific claim.

## 6. Other

### 6.1 Known limitations (stated in advance)
- **Hindsight leakage.** Today's models were trained on text written after the awakenings. Anonymization,
  the recognition probe, the disguised-text check and the leak scan reduce this but cannot remove it. A
  positive back-test is an upper bound on what a model with a true cut-off would achieve.
- OpenAlex citation and abstract coverage is weaker for older papers. Requiring abstracts biases the
  sample towards papers whose abstracts were later digitized.
- AI judges are not domain experts. The forward test measures AI-judged plausibility. Any shortlisted
  candidate needs expert and experimental follow-up before it is called a rediscovery.
- Free model endpoints can change or retire models. The cache, the logged model names and the drift check
  make this visible; a replaced model is a deviation.
- Patent and scanned-archive sources are out of scope for version 0.2.0.

### 6.2 Deviations
Any change to a frozen file is detected by SHA-256 comparison on every run and printed in the run's report
and manifest as `DEVIATION_FROM_FREEZE`. `confirm` refuses to run in that state. All deviations are listed in
`DEVIATIONS.md` and will be reported in the paper.

### 6.3 Open materials
Code (MIT), configuration, prompts, frozen sample, cached data snapshot, all run folders with logs, PDFs and
hashes (CC BY 4.0).

## 7. Integrity record
This file is itself one of the fingerprinted (frozen) files, so it cannot hold its own freeze hash. The freeze
date and bundle SHA-256 are recorded in `prereg/FREEZE_MANIFEST.json` and in the OSF form ("Other",
Integrity record).
- Freeze date (UTC) and bundle SHA-256: see `prereg/FREEZE_MANIFEST.json`
- Exploratory run ID and its manifest SHA-256: 20261120T194454Z_explore_23274f,
  11a60c777e92cd0f4a1cfb6d4ffb88fb52fa99f784602394de76cf6366270775
- Models and providers used (from `config/study.yaml`): all on Groq (free tier), temperature 0. Engine and
  recognition probe: qwen/qwen3.8-27b. Paraphraser: openai/gpt-oss-120b. Judges: openai/gpt-oss-120b,
  openai/gpt-oss-20b, allam-2-7b. Embeddings: BAAI/bge-small-en-v1.5 (local).

## References
- Ke, Q., Ferrara, E., Radicchi, F., & Flammini, A. (2015). Defining and identifying Sleeping Beauties in
  science. *PNAS*, 112(24), 7426-7431. https://doi.org/10.1073/pnas.1424329112
- Li, X., Ma, X., & Feng, Y. (2024). Early identification of breakthrough research from sleeping beauties
  using machine learning. *Journal of Informetrics*, 18(2).
- Chaleplioglou, A., Selinopoulou, E., Kyprianos, K., Koulouris, A., et al. (2026). Awakening Sleeping Beauties
  from articles on mRNA vaccines against COVID-19. *Scientometrics*, 131, 1707-1730.
  https://doi.org/10.1007/s11192-026-05598-x
- Krippendorff, K. (2011). Computing Krippendorff's alpha-reliability. University of Pennsylvania.
- Priem, J., Piwowar, H., & Orr, R. (2022). OpenAlex: A fully-open index of scholarly works, authors,
  venues, institutions, and concepts. arXiv:2205.01833.
