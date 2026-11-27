# Wake-up Engine: finding forgotten science that already solves today's problems
# Author: KEYUR SHAILESHKUMAR PATEL
# ORCID: https://orcid.org/0009-0008-5261-043X
# Affiliations: (1) MSc Artificial Intelligence student, Department of Computer Science,
#               Brunel University London, UK; (2) Independent researcher
# Note: Conducted independently; not an official Brunel University London project.
# License: MIT (see LICENSE)
"""OpenAlex client (free, open scholarly data) with disk cache and polite rate limiting.

Every HTTP response is cached under data/cache/openalex/<sha256(url)>.json together with
the URL and retrieval time, so a run can be repeated exactly from the cache and the
cache itself can be archived on OSF as the data snapshot.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlencode

import requests

from .runlog import ROOT, sha256_text, utcnow

WORK_FIELDS = ("id,doi,title,publication_year,type,cited_by_count,abstract_inverted_index,"
               "authorships,primary_topic,referenced_works,counts_by_year")


def build_filter(filters: dict[str, Any]) -> str:
    return ",".join(f"{k}:{v}" for k, v in filters.items())


def reconstruct_abstract(inv: dict | None) -> str:
    if not inv:
        return ""
    pos: dict[int, str] = {}
    for word, idxs in inv.items():
        for i in idxs:
            pos[i] = word
    return " ".join(pos[i] for i in sorted(pos))


def slim_work(w: dict) -> dict:
    """Keep only what the study needs, with a plain-text abstract."""
    pt = w.get("primary_topic") or {}
    return {
        "id": (w.get("id") or "").replace("https://openalex.org/", ""),
        "doi": w.get("doi"),
        "title": w.get("title") or "",
        "year": w.get("publication_year"),
        "type": w.get("type"),
        "cited_by_count": w.get("cited_by_count", 0),
        "abstract": reconstruct_abstract(w.get("abstract_inverted_index")),
        "authors": [((a.get("author") or {}).get("display_name") or "")
                    for a in (w.get("authorships") or [])],
        "topic_id": ((pt.get("id") or "").replace("https://openalex.org/", "")) or None,
        "topic": pt.get("display_name"),
        # full URL kept on purpose: OpenAlex filters accept it as-is
        "field_id": (pt.get("field") or {}).get("id"),
        "field": (pt.get("field") or {}).get("display_name"),
        "domain": (pt.get("domain") or {}).get("display_name"),
        "referenced_works": [r.replace("https://openalex.org/", "") for r in (w.get("referenced_works") or [])],
        "counts_by_year": w.get("counts_by_year") or [],
    }


class OpenAlex:
    def __init__(self, cfg: dict, run=None, cache_dir: Path | None = None):
        self.base = cfg["openalex"]["base_url"].rstrip("/")
        self.min_interval = 1.0 / float(cfg["openalex"].get("requests_per_second", 8))
        self.timeout = cfg["openalex"].get("timeout_s", 60)
        self.max_retries = cfg["openalex"].get("max_retries", 6)
        self.cache_dir = cache_dir or (ROOT / "data" / "cache" / "openalex")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.api_key = os.environ.get("OPENALEX_API_KEY") or None
        self.mailto = os.environ.get("OPENALEX_MAILTO") or None
        self.run = run
        self._last = 0.0
        self.session = requests.Session()
        self.session.headers["User-Agent"] = "WakeUpEngine/0.1 (open research software)"

    # ---------------------------------------------------------------- HTTP
    def _get(self, path: str, params: dict[str, Any]) -> dict:
        params = {k: v for k, v in params.items() if v is not None}
        url = f"{self.base}/{path}?{urlencode(sorted(params.items()))}"
        key = sha256_text(url)
        cp = self.cache_dir / f"{key}.json"
        if cp.exists():
            if self.run:
                self.run.count("openalex_cache_hits")
            return json.loads(cp.read_text())["response"]
        auth = {}
        if self.api_key:
            auth["api_key"] = self.api_key
        if self.mailto:
            auth["mailto"] = self.mailto
        for attempt in range(self.max_retries):
            wait = self._last + self.min_interval - time.time()
            if wait > 0:
                time.sleep(wait)
            self._last = time.time()
            try:
                r = self.session.get(url, params=auth, timeout=self.timeout)
            except requests.RequestException as e:
                self._backoff(attempt, f"network error {e}")
                continue
            if r.status_code == 200:
                data = r.json()
                cp.write_text(json.dumps({"url": url, "retrieved_utc": utcnow(), "response": data}))
                if self.run:
                    self.run.count("openalex_requests")
                return data
            if r.status_code in (429, 500, 502, 503, 504):
                self._backoff(attempt, f"HTTP {r.status_code}")
                continue
            raise RuntimeError(f"OpenAlex HTTP {r.status_code} for {url}: {r.text[:300]}")
        raise RuntimeError(f"OpenAlex failed after {self.max_retries} retries: {url}")

    def _backoff(self, attempt: int, why: str) -> None:
        delay = min(60, 2 ** (attempt + 1))
        if self.run:
            self.run.log.warning("OpenAlex %s; retry in %ss", why, delay)
        time.sleep(delay)

    # ---------------------------------------------------------------- API
    def list_works(self, filters: dict[str, Any], n: int, search: str | None = None,
                   sample_seed: int | None = None, sort: str | None = None,
                   select: str = WORK_FIELDS) -> list[dict]:
        """Return up to n works. With sample_seed, a reproducible random sample."""
        out: list[dict] = []
        per_page = 200
        if sample_seed is not None:
            n_sample = min(n, 10000)
            page = 1
            while len(out) < n_sample:
                data = self._get("works", {"filter": build_filter(filters), "sample": n_sample,
                                           "seed": sample_seed, "per-page": per_page,
                                           "page": page, "select": select})
                res = data.get("results", [])
                if not res:
                    break
                out.extend(res)
                page += 1
        else:
            cursor = "*"
            while len(out) < n and cursor:
                data = self._get("works", {"filter": build_filter(filters), "search": search,
                                           "sort": sort, "per-page": min(per_page, max(1, n - len(out))),
                                           "cursor": cursor, "select": select})
                res = data.get("results", [])
                if not res:
                    break
                out.extend(res)
                cursor = (data.get("meta") or {}).get("next_cursor")
        return [slim_work(w) for w in out[:n]]

    def citations_by_year(self, work_id: str) -> dict[int, int]:
        """Full citation history: number of citing works per publication year."""
        data = self._get("works", {"filter": f"cites:{work_id}", "group_by": "publication_year"})
        hist: dict[int, int] = {}
        for g in data.get("group_by", []):
            try:
                hist[int(g["key"])] = int(g["count"])
            except (ValueError, KeyError, TypeError):
                continue
        return hist

    def get_work(self, work_id: str) -> dict:
        return slim_work(self._get(f"works/{work_id}", {"select": WORK_FIELDS}))


def iter_chunks(seq: list, n: int) -> Iterable[list]:
    for i in range(0, len(seq), n):
        yield seq[i:i + n]
