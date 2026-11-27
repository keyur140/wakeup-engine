# Wake-up Engine: finding forgotten science that already solves today's problems
# Author: KEYUR SHAILESHKUMAR PATEL
# ORCID: https://orcid.org/0009-0008-5261-043X
# Affiliations: (1) MSc Artificial Intelligence student, Department of Computer Science,
#               Brunel University London, UK; (2) Independent researcher
# Note: Conducted independently; not an official Brunel University London project.
# License: MIT (see LICENSE)
"""Synthetic OpenAlex world for offline self-tests (`python run.py selftest`).

It plants a few artificial "sleeping beauties" whose method words match a later need, so
the test can check that every pipeline step runs and that the statistics behave sensibly.
Nothing produced in mock mode is a scientific result.
"""
from __future__ import annotations

import numpy as np

from .textutil import tokenize

FIELDS = {
    "https://openalex.org/fields/A": ["adsorption", "isotherm", "charcoal", "solute", "surface",
                                      "porous", "colloid", "filtration", "equilibrium", "dye"],
    "https://openalex.org/fields/B": ["bacteria", "phage", "lysis", "culture", "strain", "mould",
                                      "antagonism", "serum", "infection", "colony"],
    "https://openalex.org/fields/C": ["electrode", "lithium", "anode", "electrolyte", "cell",
                                      "voltage", "oxide", "capacity", "corrosion", "salt"],
}
FILLER = ["study", "results", "observed", "experiments", "measurements", "sample", "effect",
          "conditions", "analysis", "found", "method", "value", "series", "obtained"]


class MockOpenAlex:
    def __init__(self, seed: int = 1, n_old: int = 1500, n_beauties: int = 12, signal: bool = True,
                 bridge: bool | None = None):
        """signal=False: the need never mentions what the beauty offers.
        bridge: the beauty also uses two everyday words of the field that later woke it, so plain
        word search can find it without any reasoning. Default: same as signal.
        signal=False, bridge=False is the pure null world."""
        if bridge is None:
            bridge = signal
        rng = np.random.default_rng(seed)
        self.works: dict[str, dict] = {}
        self.hist: dict[str, dict[int, int]] = {}
        self.cites: dict[str, list[str]] = {}
        fields = list(FIELDS)
        wid = 0

        def new_id():
            nonlocal wid
            wid += 1
            return f"W{900000 + wid}"

        def text(vocab, k, extra=()):
            words = list(rng.choice(vocab, size=k)) + list(rng.choice(FILLER, size=k)) + list(extra)
            rng.shuffle(words)
            return " ".join(words)

        # ordinary old papers with normal (early-peak) citation histories
        for _ in range(n_old):
            f = fields[rng.integers(len(fields))]
            y = int(rng.integers(1900, 1986))
            i = new_id()
            peak = int(rng.integers(2, 15))
            scale = 1.0 if rng.random() < 0.5 else 0.01  # half are little-cited ("forgotten")
            h = {}
            for t in range(0, 2025 - y):
                lam = scale * (3 + 15 * np.exp(-((t - peak) ** 2) / 30.0))
                h[y + t] = int(rng.poisson(lam))
            self._add(i, f, y, text(FIELDS[f], 12), text(FIELDS[f], 3), h)

        # planted sleeping beauties: method words from field A, awakened by a need in field B/C
        self.planted = []
        for b in range(n_beauties):
            f_old = fields[b % 3]
            f_new = fields[(b + 1) % 3]
            y = int(rng.integers(1905, 1960))
            sleep = int(rng.integers(20, 50))
            Y = y + sleep
            key = [f"keyword{b}a", f"keyword{b}b", f"keyword{b}c"]
            h = {}
            for t in range(0, 2025 - y):
                yr = y + t
                h[yr] = int(rng.poisson(0.5)) if yr < Y else int(rng.poisson(min(60, 10 + 6 * (yr - Y))))
            i = new_id()
            self._add(i, f_old, y, text(FIELDS[f_old], 10, key + (FIELDS[f_new][:2] if bridge else [])),
                      "on a curious " + " ".join(key[:2]), h)
            self.planted.append(i)
            # awakeners: field f_new papers citing it in [Y, Y+3]
            topic_new = f"{f_new}/topic{b}"
            for k in range(8):
                a = new_id()
                self._add(a, f_new, Y + int(rng.integers(0, 4)), text(FIELDS[f_new], 10, key[:1]),
                          "applying " + key[0], {}, topic=topic_new)
                self.works[a]["referenced_works"] = [i]
                self.cites.setdefault(i, []).append(a)
            # need context: field f_new papers describing the need (not citing it). Spread over
            # the years around waking, because the estimated awakening year can differ from Y.
            for yr in range(Y - 12, Y + 12):
                for k in range(6):
                    c = new_id()
                    need_words = (key[1:2] + key[2:3]) if signal else []
                    self._add(c, f_new, yr, text(FIELDS[f_new], 10, need_words),
                              text(FIELDS[f_new], 3), {}, topic=topic_new)

    def _add(self, i, field, year, abstract, title, hist, topic=None):
        self.works[i] = {"id": i, "doi": None, "title": title, "year": year, "type": "article",
                         "cited_by_count": int(sum(hist.values())), "abstract": abstract,
                         "authors": [f"Author{i} Mocksen"], "topic_id": topic or (field + "/topic"),
                         "topic": "mock topic", "field_id": field, "field": field.split("/")[-1],
                         "domain": "mock", "referenced_works": [], "counts_by_year": []}
        self.hist[i] = hist

    # ------------------------------------------------------------- client API
    def _match(self, w, filters):
        for k, v in filters.items():
            v = str(v)
            if k == "publication_year":
                y = w["year"]
                if v.startswith("<"):
                    if not y < int(v[1:]):
                        return False
                elif "-" in v:
                    a, b = v.split("-")
                    if not int(a) <= y <= int(b):
                        return False
                elif y != int(v):
                    return False
            elif k == "cited_by_count":
                c = w["cited_by_count"]
                if v.startswith(">") and not c > int(v[1:]):
                    return False
                if v.startswith("<") and not c < int(v[1:]):
                    return False
            elif k == "has_abstract":
                if (v == "true") != bool(w["abstract"]):
                    return False
            elif k == "type":
                if w["type"] != v:
                    return False
            elif k == "primary_topic.id":
                if w["topic_id"] != v:
                    return False
            elif k == "primary_topic.field.id":
                if w["field_id"] != v:
                    return False
            elif k == "cites":
                if w["id"] not in self.cites.get(v, []):
                    return False
            else:
                raise ValueError(f"mock does not support filter {k}")
        return True

    def list_works(self, filters, n, search=None, sample_seed=None, sort=None, select=None):
        res = [w for w in self.works.values() if self._match(w, filters)]
        if search:
            q = set(tokenize(search))
            scored = [(len(q & set(tokenize(w["title"] + " " + w["abstract"]))), w["id"], w) for w in res]
            res = [w for s, _, w in sorted(scored, key=lambda t: (-t[0], t[1])) if s > 0]
        elif sample_seed is not None:
            rng = np.random.default_rng(sample_seed)
            res = sorted(res, key=lambda w: w["id"])
            res = [res[i] for i in rng.permutation(len(res))]
        return [dict(w) for w in res[:n]]

    def citations_by_year(self, work_id):
        return dict(self.hist.get(work_id, {}))

    def get_work(self, work_id):
        return dict(self.works[work_id])
