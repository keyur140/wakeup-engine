# Wake-up Engine: finding forgotten science that already solves today's problems
# Author: KEYUR SHAILESHKUMAR PATEL
# ORCID: https://orcid.org/0009-0008-5261-043X
# Affiliations: (1) MSc Artificial Intelligence student, Department of Computer Science,
#               Brunel University London, UK; (2) Independent researcher
# Note: Conducted independently; not an official Brunel University London project.
# License: MIT (see LICENSE)
"""Text helpers: blinding (anonymization), tokenizing, fuzzy matching."""
from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher

YEAR_RE = re.compile(r"\b(1[5-9]\d\d|20\d\d)s?\b")
WS_RE = re.compile(r"\s+")
TOKEN_RE = re.compile(r"[a-z0-9]+")

STOPWORDS = set("""a an the of and or in on for to with by from at as is are was were be been being
this that these those it its into than then there their our we they he she his her which who whom
not no can could may might will would shall should do does did has have had also such using used use
""".split())


def normalize(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    return WS_RE.sub(" ", s).strip()


def surnames(authors: list[str]) -> list[str]:
    out = []
    for a in authors or []:
        parts = [p for p in re.split(r"[\s,.]+", normalize(a)) if len(p) > 2]
        if parts:
            out.append(parts[-1])
    return out


def anonymize(text: str, authors: list[str] | None = None) -> str:
    """Remove years and author surnames (incl. eponyms such as 'Freundlich isotherm')."""
    t = normalize(text)
    t = re.sub(r"\b10\.\d{4,9}/\S+", "[DOI]", t)
    t = re.sub(r"https?://\S+|www\.\S+", "[URL]", t)
    t = re.sub(r"\bW\d{6,}\b", "[ID]", t)
    t = re.sub(r"\bet al\.?", "and colleagues", t, flags=re.IGNORECASE)
    t = YEAR_RE.sub("[YEAR]", t)
    for s in sorted(set(surnames(authors or [])), key=len, reverse=True):
        t = re.sub(rf"\b{re.escape(s)}(?:'s|s')?\b", "[NAME]", t, flags=re.IGNORECASE)
    return t


def paper_text(work: dict, anonymize_on: bool = True, include_title: bool = True,
               max_chars: int = 2500) -> str:
    title = work.get("title") or ""
    abstract = work.get("abstract") or ""
    body = f"Title: {title}\nAbstract: {abstract}" if include_title else f"Abstract: {abstract}"
    if anonymize_on:
        body = anonymize(body, work.get("authors"))
    return body[:max_chars]


def tokenize(text: str) -> list[str]:
    return [t for t in TOKEN_RE.findall(normalize(text).lower()) if t not in STOPWORDS and len(t) > 1]


def title_similarity(a: str, b: str) -> float:
    a, b = " ".join(tokenize(a)), " ".join(tokenize(b))
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()
