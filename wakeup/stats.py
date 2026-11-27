# Wake-up Engine: finding forgotten science that already solves today's problems
# Author: KEYUR SHAILESHKUMAR PATEL
# ORCID: https://orcid.org/0009-0008-5261-043X
# Affiliations: (1) MSc Artificial Intelligence student, Department of Computer Science,
#               Brunel University London, UK; (2) Independent researcher
# Note: Conducted independently; not an official Brunel University London project.
# License: MIT (see LICENSE)
"""Preregistered statistics. Plain numpy/scipy so every number can be checked by hand."""
from __future__ import annotations

import math

import numpy as np
from scipy import stats as st


def wilson_ci(k: int, n: int, alpha: float = 0.05) -> tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    z = st.norm.ppf(1 - alpha / 2)
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (max(0.0, c - h), min(1.0, c + h))


def binom_greater(k: int, n: int, p0: float) -> float:
    """One-sided exact binomial test, H1: rate > p0."""
    if n == 0:
        return float("nan")
    return float(st.binomtest(k, n, p0, alternative="greater").pvalue)


def mcnemar_exact(a_hit: np.ndarray, b_hit: np.ndarray) -> dict:
    """Exact McNemar test (two-sided) on paired binary outcomes."""
    a_hit, b_hit = np.asarray(a_hit, bool), np.asarray(b_hit, bool)
    b = int(np.sum(a_hit & ~b_hit))   # A hit, B miss
    c = int(np.sum(~a_hit & b_hit))   # A miss, B hit
    n = b + c
    p = 1.0 if n == 0 else float(st.binomtest(b, n, 0.5, alternative="two-sided").pvalue)
    return {"a_only": b, "b_only": c, "p_two_sided": p}


def mcnemar_one_sided(a_hit, b_hit) -> dict:
    """Exact one-sided McNemar: is A a hit more often than B on the same items?"""
    r = mcnemar_exact(a_hit, b_hit)
    n = r["a_only"] + r["b_only"]
    r["p_one_sided"] = 1.0 if n == 0 else float(st.binomtest(r["a_only"], n, 0.5, alternative="greater").pvalue)
    return r


def bootstrap_ci(values: np.ndarray, fn=np.mean, iters: int = 10000, seed: int = 0,
                 alpha: float = 0.05) -> tuple[float, float]:
    values = np.asarray(values, float)
    if len(values) == 0:
        return (float("nan"), float("nan"))
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(values), size=(iters, len(values)))
    boots = np.apply_along_axis(fn, 1, values[idx])
    return (float(np.quantile(boots, alpha / 2)), float(np.quantile(boots, 1 - alpha / 2)))


def mrr(ranks: np.ndarray) -> float:
    ranks = np.asarray(ranks, float)
    return float(np.mean(1.0 / ranks)) if len(ranks) else float("nan")


def expected_random_mrr(n_candidates: int) -> float:
    return float(np.mean(1.0 / np.arange(1, n_candidates + 1)))


def stratified_permutation_test(values: np.ndarray, groups: np.ndarray, strata: np.ndarray,
                                g_treat: str, g_ctrl: str, iters: int = 10000,
                                seed: int = 0) -> dict:
    """One-sided test that mean(treat) > mean(control), shuffling labels within each stratum."""
    values, groups, strata = np.asarray(values, float), np.asarray(groups), np.asarray(strata)
    mask = np.isin(groups, [g_treat, g_ctrl])
    v, g, s = values[mask], groups[mask], strata[mask]
    obs = v[g == g_treat].mean() - v[g == g_ctrl].mean()
    rng = np.random.default_rng(seed)
    strata_idx = [np.where(s == u)[0] for u in np.unique(s)]
    count = 0
    gp = g.copy()
    for _ in range(iters):
        for idx in strata_idx:
            gp[idx] = rng.permutation(g[idx])
        diff = v[gp == g_treat].mean() - v[gp == g_ctrl].mean()
        if diff >= obs - 1e-12:
            count += 1
    return {"mean_treat": float(v[g == g_treat].mean()), "mean_control": float(v[g == g_ctrl].mean()),
            "difference": float(obs), "p_one_sided": (count + 1) / (iters + 1),
            "n_treat": int(np.sum(g == g_treat)), "n_control": int(np.sum(g == g_ctrl))}


def krippendorff_alpha(data: np.ndarray, level: str = "ordinal") -> float:
    """Krippendorff's alpha. data: raters x units, np.nan for missing."""
    data = np.asarray(data, float)
    vals = np.unique(data[~np.isnan(data)])
    if len(vals) < 2:
        return float("nan")
    idx = {v: i for i, v in enumerate(vals)}
    V = len(vals)
    o = np.zeros((V, V))
    for u in range(data.shape[1]):
        col = data[:, u]
        col = col[~np.isnan(col)]
        m = len(col)
        if m < 2:
            continue
        for i in range(m):
            for j in range(m):
                if i != j:
                    o[idx[col[i]], idx[col[j]]] += 1.0 / (m - 1)
    n_c = o.sum(axis=1)
    n = n_c.sum()
    if n <= 1:
        return float("nan")
    d2 = np.zeros((V, V))
    for c in range(V):
        for k in range(V):
            if level == "nominal":
                d2[c, k] = 0.0 if c == k else 1.0
            elif level == "interval":
                d2[c, k] = (vals[c] - vals[k]) ** 2
            else:  # ordinal
                lo, hi = min(c, k), max(c, k)
                d2[c, k] = (n_c[lo:hi + 1].sum() - (n_c[c] + n_c[k]) / 2.0) ** 2
    D_o = (o * d2).sum() / n
    D_e = (np.outer(n_c, n_c) * d2).sum() / (n * (n - 1))
    return float("nan") if D_e == 0 else float(1 - D_o / D_e)


def holm(pvals: dict[str, float]) -> dict[str, float]:
    items = sorted(pvals.items(), key=lambda kv: kv[1])
    m = len(items)
    out, running = {}, 0.0
    for i, (k, p) in enumerate(items):
        adj = min(1.0, (m - i) * p)
        running = max(running, adj)
        out[k] = running
    return out


def poisson_binomial_greater(k: int, ps: list[float]) -> float:
    """P(X >= k) where X is a sum of independent Bernoulli(p_i). Exact (dynamic programming).

    Used for the primary test when candidate-set sizes differ between sleeping beauties,
    so the chance hit rate k/N differs per item. Equals the binomial test when all p_i match.
    """
    dist = np.zeros(len(ps) + 1)
    dist[0] = 1.0
    for p in ps:
        dist[1:] = dist[1:] * (1 - p) + dist[:-1] * p
        dist[0] *= (1 - p)
    return float(min(1.0, dist[k:].sum()))


def binom_critical(n: int, p0: float, alpha: float) -> int:
    """Smallest number of hits k with P(X >= k | p0) < alpha."""
    for k in range(n + 2):
        if k > n or float(st.binom.sf(k - 1, n, p0)) < alpha:
            return k
    return n + 1


def mde_binomial(n: int, p0: float, alpha: float = 0.05, power: float = 0.8) -> float:
    """Minimum detectable true hit rate: the smallest rate found with the given power."""
    if n <= 0:
        return float("nan")
    kc = binom_critical(n, p0, alpha)
    if kc > n:
        return float("nan")
    lo, hi = p0, 1.0
    for _ in range(60):
        mid = (lo + hi) / 2
        if float(st.binom.sf(kc - 1, n, mid)) >= power:
            hi = mid
        else:
            lo = mid
    return hi
