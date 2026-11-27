# Wake-up Engine: finding forgotten science that already solves today's problems
# Author: KEYUR SHAILESHKUMAR PATEL
# ORCID: https://orcid.org/0009-0008-5261-043X
# Affiliations: (1) MSc Artificial Intelligence student, Department of Computer Science,
#               Brunel University London, UK; (2) Independent researcher
# Note: Conducted independently; not an official Brunel University London project.
# License: MIT (see LICENSE)
"""Retrieval baselines and first stage of the engine: random, BM25, dense, hybrid (RRF)."""
from __future__ import annotations

import numpy as np

from .textutil import tokenize

_EMBEDDER = {"obj": None, "kind": None, "name": None}


def bm25_scores(query: str, docs: list[str]) -> np.ndarray:
    from rank_bm25 import BM25Okapi
    toks = [tokenize(d) or ["_empty_"] for d in docs]
    bm = BM25Okapi(toks)
    return np.asarray(bm.get_scores(tokenize(query)), dtype=float)


def _get_embedder(model_name: str, force_tfidf: bool = False):
    if _EMBEDDER["obj"] is not None and _EMBEDDER["name"] == (model_name, force_tfidf):
        return _EMBEDDER["obj"], _EMBEDDER["kind"]
    obj, kind = None, "tfidf"
    if not force_tfidf:
        try:
            from sentence_transformers import SentenceTransformer
            obj, kind = SentenceTransformer(model_name), "sentence-transformers"
        except Exception as e:
            print(f"WARNING: sentence-transformers model '{model_name}' unavailable ({e}); "
                  "using TF-IDF fallback. This is recorded as a deviation.")
            obj, kind = None, "tfidf"
    _EMBEDDER.update(obj=obj, kind=kind, name=(model_name, force_tfidf))
    return obj, kind


def _encode(model, model_name: str, texts: list[str], batch_size: int) -> np.ndarray:
    """Embed texts. With WAKEUP_EMBED_CACHE=1 the exact arrays are stored on disk and reused, so an
    interrupted run resumes quickly (ISSUES I15). The numbers are identical with or without it."""
    import os
    if os.environ.get("WAKEUP_EMBED_CACHE") != "1":
        return model.encode(texts, normalize_embeddings=True, batch_size=batch_size)
    import hashlib
    from pathlib import Path
    h = hashlib.sha256(("\x1f".join([model_name, str(batch_size)] + texts)).encode("utf-8")).hexdigest()
    cdir = Path(__file__).resolve().parent.parent / "data" / "cache" / "embeddings"
    cdir.mkdir(parents=True, exist_ok=True)
    cp = cdir / f"{h}.npy"
    if cp.exists():
        return np.load(cp)
    arr = np.asarray(model.encode(texts, normalize_embeddings=True, batch_size=batch_size))
    tmp = cdir / f"{h}.tmp.npy"
    np.save(tmp, arr)
    tmp.replace(cp)
    return arr


def dense_scores(query: str, docs: list[str], model_name: str, batch_size: int = 64,
                 force_tfidf: bool = False) -> tuple[np.ndarray, str]:
    model, kind = _get_embedder(model_name, force_tfidf)
    if kind == "sentence-transformers":
        q = _encode(model, model_name, [query], batch_size)
        d = _encode(model, model_name, docs, batch_size)
        return (d @ q[0]).astype(float), f"sentence-transformers:{model_name}"
    from sklearn.feature_extraction.text import TfidfVectorizer
    vec = TfidfVectorizer(tokenizer=tokenize, lowercase=False, token_pattern=None, sublinear_tf=True)
    m = vec.fit_transform(docs + [query])
    d, q = m[:-1], m[-1]
    return np.asarray((d @ q.T).toarray()).ravel().astype(float), "tfidf-fallback"


def ranks_from_scores(scores: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Rank 1 = best. Ties broken at random (seeded), never in favour of the target."""
    tiebreak = rng.random(len(scores))
    order = np.lexsort((tiebreak, -scores))
    ranks = np.empty(len(scores), dtype=int)
    ranks[order] = np.arange(1, len(scores) + 1)
    return ranks


def rrf(rank_lists: list[np.ndarray], k: int = 60) -> np.ndarray:
    """Reciprocal rank fusion score (higher = better)."""
    return sum(1.0 / (k + r) for r in rank_lists)
