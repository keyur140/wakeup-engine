# Data card: results

Project: Wake-up Engine: finding forgotten science that already solves today's problems

Creator: KEYUR SHAILESHKUMAR PATEL  
ORCID: https://orcid.org/0009-0008-5261-043X  
Affiliations: (1) MSc Artificial Intelligence student, Department of Computer Science, Brunel University London, UK; (2) Independent researcher  
*Conducted independently; not an official Brunel University London project.*

Run: `20261103T185013Z_selftest_MOCK_7207d4` (MOCK, synthetic)  
Licence: CC BY 4.0

## Description
Outputs of a Wake-up Engine exploratory run (dev part of the sleeping beauties).

## Sources
- Synthetic mock world

## Files
- `data/`: sleeping-beauty screening, selection and split (locked titles blanked)
- `results/`: ranks, per-candidate scores, gate, ratings, tests, leak scans (CSV/JSON)
- `checks.json`: self-verification results
- `llm_calls.jsonl`: every model call with prompt and response hashes
- `*.pdf / report.md / report.html`: human-readable reports

## Provenance and integrity
All API responses are cached under `data/cache/` with the request URL and retrieval time. SHA-256 hashes of every file in this run are in `manifest.json` and `SHA256SUMS`.

AI assistance: Code and draft text were prepared with help from an AI assistant (Claude, Anthropic) under the author's direction. All design decisions, hypotheses and hit criteria were chosen by the author. The author takes full responsibility for the work.
