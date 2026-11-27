# Expected impact

**KEYUR SHAILESHKUMAR PATEL** · ORCID https://orcid.org/0009-0008-5261-043X
(1) MSc Artificial Intelligence student, Department of Computer Science, Brunel University London, UK
(2) Independent researcher
*Conducted independently; not an official Brunel University London project.*

Written before any real data were collected. It describes what each possible outcome would mean,
so the study's value does not depend on getting a positive result.

## The problem this addresses
Science keeps losing useful knowledge. Ke et al. (2015) found that "sleeping beauties", papers ignored
for years and then suddenly important, are at least 100 times more common than earlier estimates. Famous
cases took decades to wake up: Rous's 1911 cancer-virus work earned a Nobel Prize 55 years later, and
Freundlich's 1907 adsorption work became widely cited only in the 2000s, for water purification. Until now,
every study has found these papers *after* they woke up. This study tests whether they can be woken
*on purpose*.

## What each outcome would mean

| Outcome | What it means | Who it helps |
|---|---|---|
| **Back-test positive** (H1 supported) | First preregistered evidence that an AI that reads text can match forgotten papers to the needs that later woke them, using only information from before the awakening | Science-of-science researchers, research funders, librarians, AI-for-science tool builders |
| **Forward test positive** (H2 supported) | The engine's forgotten pre-1990 candidates are judged more useful for open antibiotic-resistance problems than random old papers | Microbiology and infectious-disease researchers looking for new leads |
| **A strong individual lead** | A specific old paper whose idea might help with a resistance problem. Needs expert reading and lab testing before it counts as a rediscovery | Labs working on that problem; patients in the long run |
| **Negative results** | Because the test is preregistered and open, a null result is a reliable map of where AI literature reading does not yet work, and stops others from overclaiming | Anyone building or funding AI literature-mining tools |

## Why antibiotic resistance
Bacterial antimicrobial resistance was directly responsible for an estimated 1.27 million deaths in 2019
(Murray et al., 2022, *The Lancet*), and few new antibiotic classes have appeared in decades. Much
pre-antibiotic-era and early-antibiotic-era work (phage therapy, bacterial interference, antiseptics,
dormancy studies) was set aside once antibiotics worked. That makes the field a natural place to look for
forgotten answers.

## Lasting outputs, whatever the result
1. A free, open-source engine (MIT) that anyone can point at a new field by editing one problems file.
2. An open benchmark of computationally identified sleeping beauties with their pre-awakening need statements,
   so other methods can be compared on the same task.
3. A fully hashed, reproducible record: data snapshot, every AI prompt and reply, and every run.

## Honest limits on the claim
- Today's AI models have read text written after these awakenings, so the back-test is an upper bound.
- AI judges are not human experts. A forward-test hit is a lead, not a discovery.
- "First" should be stated as "to our knowledge, the first preregistered test of …" (see `related_work.md`).

## References
- Ke, Q., Ferrara, E., Radicchi, F., & Flammini, A. (2015). Defining and identifying Sleeping Beauties in
  science. *PNAS*, 112(24), 7426-7431.
- Murray, C. J. L., et al. (2022). Global burden of bacterial antimicrobial resistance in 2019: a systematic
  analysis. *The Lancet*, 399(10325), 629-655.
