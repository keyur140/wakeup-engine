# Wake-up Engine: finding forgotten science that already solves today's problems
# Author: KEYUR SHAILESHKUMAR PATEL
# ORCID: https://orcid.org/0009-0008-5261-043X
# Affiliations: (1) MSc Artificial Intelligence student, Department of Computer Science,
#               Brunel University London, UK; (2) Independent researcher
# Note: Conducted independently; not an official Brunel University London project.
# License: MIT (see LICENSE)
"""Prompt leak scan: checks every text a model is shown for clues that break blinding."""
from __future__ import annotations

import re

from .textutil import surnames

PATTERNS = {
    "year": re.compile(r"\b(1[5-9]\d\d|20\d\d)s?\b"),
    "doi": re.compile(r"\b10\.\d{4,9}/\S+", re.IGNORECASE),
    "url": re.compile(r"https?://|www\.", re.IGNORECASE),
    "openalex_id": re.compile(r"\bW\d{6,}\b"),
    "et_al": re.compile(r"\bet al\b", re.IGNORECASE),
    "study_words": re.compile(r"sleeping beaut|delayed recognition|beauty coefficient|"
                              r"engine pick|control item|random control", re.IGNORECASE),
}


def scan(text: str, authors: list[str] | None = None) -> list[str]:
    hits = [name for name, rx in PATTERNS.items() if rx.search(text or "")]
    for s in surnames(authors or []):
        if re.search(rf"\b{re.escape(s)}\b", text or "", flags=re.IGNORECASE):
            hits.append("author_name")
            break
    return hits
