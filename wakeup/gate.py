# Wake-up Engine: finding forgotten science that already solves today's problems
# Author: KEYUR SHAILESHKUMAR PATEL
# ORCID: https://orcid.org/0009-0008-5261-043X
# Affiliations: (1) MSc Artificial Intelligence student, Department of Computer Science,
#               Brunel University London, UK; (2) Independent researcher
# Note: Conducted independently; not an official Brunel University London project.
# License: MIT (see LICENSE)
"""Known-answer gate and answer-collapse rule.

Lesson from the author's AI-music preprint: a scoring model can pass every software check and
still carry no information (CLAP, AUC 0.495), and an AI judge can give every item the same
score (1,152 identical scores). So before any model's scores count, it must show it can tell a
known answer from a decoy.

Gate (run on DEVELOPMENT sleeping beauties only): for each one, the model scores the true
sleeping beauty and 5 decoys against the need that later woke it. AUC = share of
(sleeping beauty, decoy) pairs, within the same item, where the sleeping beauty scores higher
(ties count half). One-sided permutation p-value: which of the 6 items is "true" is shuffled
within each item. Pass = AUC > 0.5, p < alpha, and at least `min_items` usable items.

Collapse: a model whose usable scores are more than 95% identical is dropped whatever its AUC.
"""
from __future__ import annotations

import numpy as np

from . import prompts as P
from .llm import parse_json
from .split import item_seed
from .textutil import paper_text


def _score(model, kind: str, need: str, text: str, meta: dict) -> float:
    if kind == "judge":
        rep = model.chat(P.JUDGE_SYSTEM, P.JUDGE_USER.format(problem=need, candidate=text),
                         task="gate_judge", meta=meta, max_tokens=1500)
        v = (parse_json(rep) or {}).get("applicability")
    else:
        rep = model.chat(P.RERANK_SYSTEM, P.RERANK_USER.format(need=need, candidate=text),
                         task="gate_engine", meta=meta)
        v = (parse_json(rep) or {}).get("score")
    try:
        return float(v)
    except (TypeError, ValueError):
        return float("nan")


def gate_items(dev_items: list[dict], cfg: dict) -> list[dict]:
    """dev_items: [{sb, need, candidates (list of works), target_idx}] -> gate sets."""
    g = cfg["gate"]
    sets = []
    for it in dev_items:
        rng = np.random.default_rng(item_seed(cfg["seed"], "gate", it["sb"]["id"]))
        others = [j for j in range(len(it["candidates"])) if j != it["target_idx"]]
        pick = list(rng.choice(others, size=min(g["n_decoys"], len(others)), replace=False))
        works = [it["sb"]] + [it["candidates"][j] for j in pick]
        b = cfg["backtest"]
        sets.append({"sb": it["sb"]["id"], "need": it["need"],
                     "texts": [paper_text(w, b["anonymize"], b["include_title"]) for w in works],
                     "ids": [w["id"] for w in works]})
    return sets


def auc_and_p(rows: list[list[float]], iters: int, seed: int) -> tuple[float, float, int]:
    """rows: per item, [score_true, score_decoy1, ...]. NaN entries dropped."""
    clean = [np.array(r, float) for r in rows if not np.isnan(r[0]) and np.sum(~np.isnan(r[1:])) > 0]
    if not clean:
        return float("nan"), float("nan"), 0

    def auc(rs, true_idx):
        num = den = 0.0
        for r, t in zip(rs, true_idx):
            tv = r[t]
            for j, v in enumerate(r):
                if j == t or np.isnan(v) or np.isnan(tv):
                    continue
                num += 1.0 if tv > v else 0.5 if tv == v else 0.0
                den += 1
        return num / den if den else float("nan")

    obs = auc(clean, [0] * len(clean))
    rng = np.random.default_rng(seed)
    ge = 0
    for _ in range(iters):
        idx = [int(rng.integers(0, len(r))) for r in clean]
        if auc(clean, idx) >= obs - 1e-12:
            ge += 1
    return float(obs), (ge + 1) / (iters + 1), len(clean)


def collapse_share(values) -> float:
    v = np.asarray([x for x in values if not np.isnan(x)], float)
    if len(v) == 0:
        return float("nan")
    _, counts = np.unique(v, return_counts=True)
    return float(counts.max() / len(v))


def run_gate(models: list[tuple[str, object, str]], sets: list[dict], cfg: dict, run) -> list[dict]:
    """models: [(name, model, kind)], kind = 'judge' or 'engine'."""
    g = cfg["gate"]
    out = []
    for name, model, kind in models:
        rows, flat = [], []
        for s in sets:
            r = [_score(model, kind, s["need"], t, {"sb": s["sb"], "work": wid, "gate": True})
                 for t, wid in zip(s["texts"], s["ids"])]
            rows.append(r)
            flat.extend(r)
        auc, p, n = auc_and_p(rows, g["permutation_iterations"], item_seed(cfg["seed"], "gate-perm", name))
        coll = collapse_share(flat)
        collapsed = bool(not np.isnan(coll) and coll > g["collapse_threshold"])
        parse_fail = float(np.mean(np.isnan(np.asarray(flat, float)))) if flat else float("nan")
        passed = (not collapsed) and n >= g["min_items"] and auc > 0.5 and p < g["alpha"]
        reason = ("answer collapse" if collapsed else
                  f"too few usable items ({n} < {g['min_items']})" if n < g["min_items"] else
                  "AUC not above chance" if not (auc > 0.5 and p < g["alpha"]) else "passed")
        out.append({"model_name": name, "role": kind, "provider": getattr(model, "provider", "?"),
                    "model": getattr(model, "model", "?"), "n_items": n, "auc": auc, "p_one_sided": p,
                    "largest_identical_share": coll, "parse_failure_rate": parse_fail,
                    "collapsed": collapsed, "passed": bool(passed), "reason": reason})
        run.log.info("Gate %s (%s): AUC %.3f, p %.4f, n %d, identical share %.2f -> %s",
                     name, kind, auc, p, n, coll, reason)
    return out
