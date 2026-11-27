# Wake-up Engine: finding forgotten science that already solves today's problems
# Author: KEYUR SHAILESHKUMAR PATEL
# ORCID: https://orcid.org/0009-0008-5261-043X
# Affiliations: (1) MSc Artificial Intelligence student, Department of Computer Science,
#               Brunel University London, UK; (2) Independent researcher
# Note: Conducted independently; not an official Brunel University London project.
# License: MIT (see LICENSE)
"""All prompts used in the study, fixed before data collection (part of the preregistration).

Prompts never reveal which candidate is the true sleeping beauty, its year, or its authors.
"""

NEED_SYSTEM = (
    "You are a careful historian of science. You only use the texts you are given. "
    "You never use knowledge of anything published after them."
)
NEED_USER = """Below are {n} research abstracts from one research field, all published in the same year.
Using ONLY these abstracts, describe the main unsolved problems, open questions and unmet
methodological needs of this field at that time. Do not propose solutions, do not name
specific later methods, people or papers. Write 120-200 words.

{abstracts}

Answer as JSON: {{"need": "<text>"}}"""

RERANK_SYSTEM = (
    "You evaluate whether an older research paper could help solve a research need. "
    "Judge only from the texts shown. Answer with JSON only."
)
RERANK_USER = """RESEARCH NEED:
{need}

CANDIDATE OLDER PAPER (author names and years removed):
{candidate}

On a 0-10 scale, how likely is it that the method, finding, model or material in the
candidate paper directly addresses the research need (0 = unrelated, 10 = it is a ready
solution or key enabling idea)? Answer as JSON: {{"score": <number 0-10>, "reason": "<one sentence>"}}"""

QUERY_SYSTEM = (
    "You are an expert librarian for historical scientific literature (before 1990). "
    "Answer with JSON only."
)
QUERY_USER = """OPEN PROBLEM (today):
{problem}

Propose {n} short search queries (2-6 words each) that would find OLDER papers (before 1990)
whose methods or findings might help with this problem. Use the vocabulary older papers
would have used (older names for organisms, chemicals, techniques), and include
cross-field ideas, not only the obvious modern terms.
Answer as JSON: {{"queries": ["...", "..."]}}"""

MEMO_SYSTEM = "You are a bibliographic expert. Answer with JSON only."
MEMO_USER = """Here is an anonymized paper (author names and years removed):

{candidate}

Do you recognize this specific paper? If yes, give its exact title, first author surname and
publication year. If you do not specifically recognize it, say so; do not guess.
Answer as JSON: {{"recognized": true/false, "title": "...", "first_author": "...", "year": <int or null>}}"""

JUDGE_SYSTEM = (
    "You are a senior scientist acting as a blind reviewer. You judge whether an older paper "
    "could help with a stated research problem. Judge only from the texts shown. "
    "Answer with JSON only."
)
JUDGE_USER = """OPEN PROBLEM:
{problem}

CANDIDATE OLDER PAPER (anonymized; you do not know why it was selected):
{candidate}

Rate two things on 1-5 scales.
applicability: 1 = irrelevant; 2 = loosely related; 3 = plausibly useful background;
4 = the method/finding could concretely help address the problem; 5 = strong, specific,
testable route to a solution.
novelty: 1 = this idea is already standard in current work on the problem;
3 = known but under-used; 5 = this idea seems absent from current approaches.
Answer as JSON: {{"applicability": <1-5>, "novelty": <1-5>, "reason": "<one or two sentences>"}}"""

PARA_SYSTEM = (
    "You rewrite scientific abstracts in plain, different words. Keep every scientific idea, "
    "method and finding. Answer with JSON only."
)
PARA_USER = """Rewrite the paper below so that its exact wording could not be recognized:
use different sentence structure and ordinary words, drop the title, and drop any distinctive
names of people, places, compounds or techniques that would identify the specific paper
(describe them instead). Keep the meaning complete. 80-200 words.

{candidate}

Answer as JSON: {{"text": "<rewritten text>"}}"""
