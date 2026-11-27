# Wake-up Engine: finding forgotten science that already solves today's problems
# Author: KEYUR SHAILESHKUMAR PATEL
# ORCID: https://orcid.org/0009-0008-5261-043X
# Affiliations: (1) MSc Artificial Intelligence student, Department of Computer Science,
#               Brunel University London, UK; (2) Independent researcher
# Note: Conducted independently; not an official Brunel University London project.
# License: MIT (see LICENSE)
"""Study 2, the forward test, and Study 3, the blind AI judge panel.

For each of 20 open problems (antibiotic resistance):
  1. search pre-1990 literature in OpenAlex (author's seed queries + AI-proposed queries
     in older vocabulary)
  2. keep only "forgotten" papers (few citations)
  3. rank with hybrid retrieval + LLM re-rank; the top 5 are the engine's candidates
  4. mix them with 5 random papers from the same retrieved pool and 5 random pre-1990 papers
  5. three different AI judges rate every item blind (pointwise, shuffled, anonymized)
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import yaml

from . import prompts as P
from .llm import parse_json
from .retrieval import bm25_scores, dense_scores, ranks_from_scores, rrf
from .runlog import ROOT, sha256_text
from .stats import holm, krippendorff_alpha, stratified_permutation_test, wilson_ci
from .leakscan import scan
from .textutil import paper_text

GROUPS = ["engine", "pool_random", "global_random"]


def load_problems(cfg, problems_file: str | None = None) -> list[dict]:
    p = ROOT / (problems_file or cfg["forward"]["problems_file"])
    probs = yaml.safe_load(p.read_text())["problems"]
    lim = cfg["forward"].get("limit_problems")
    return probs[:lim] if lim else probs


def expand_queries(llm, prob: dict, cfg) -> list[str]:
    rep = llm.chat(P.QUERY_SYSTEM, P.QUERY_USER.format(problem=prob["statement"],
                                                       n=cfg["forward"]["query_expansion_n"]),
                   task="query_expansion", meta={"problem": prob["id"]})
    pj = parse_json(rep) or {}
    qs = [str(q).strip() for q in (pj.get("queries") or []) if str(q).strip()]
    return qs[:cfg["forward"]["query_expansion_n"]]


def gather_pool(oa, queries: list[str], cfg) -> list[dict]:
    f = cfg["forward"]
    pool, seen = [], set()
    for q in queries:
        for w in oa.list_works({"publication_year": f"<{f['max_pub_year'] + 1}", "has_abstract": "true"},
                               f["results_per_query"], search=q):
            if w["id"] in seen or not w["abstract"]:
                continue
            seen.add(w["id"])
            w["matched_query"] = q
            pool.append(w)
    return pool


def run_forward(oa, engine_llm, judges, cfg: dict, run, report, problems_file: str | None = None,
                gate: list[dict] | None = None, label: str = "confirmatory") -> dict:
    f, rcfg = cfg["forward"], cfg["rating"]
    rng = np.random.default_rng(cfg["seed"] + 1)
    problems = load_problems(cfg, problems_file)
    run.log.info("Forward test on %d problems", len(problems))
    # one shared reproducible sample of pre-1990 papers for the global random control
    global_pool = [w for w in oa.list_works({"publication_year": f"<{f['max_pub_year'] + 1}",
                                             "has_abstract": "true"}, 2000, sample_seed=cfg["seed"] + 2)
                   if w["cited_by_count"] <= f["forgotten_max_citations"]]
    items, prob_rows = [], []
    used_global = set()
    for pi, prob in enumerate(problems, 1):
        qs = list(prob.get("seed_queries", [])) + expand_queries(engine_llm, prob, cfg)
        pool = gather_pool(oa, qs, cfg)
        forgotten = [w for w in pool if w["cited_by_count"] <= f["forgotten_max_citations"]]
        run.log.info("[%d/%d] %s: %d retrieved, %d forgotten, queries=%s", pi, len(problems), prob["id"],
                     len(pool), len(forgotten), qs)
        prob_rows.append({"problem": prob["id"], "title": prob["title"], "queries": " | ".join(qs),
                          "n_retrieved": len(pool), "n_forgotten": len(forgotten)})
        if len(forgotten) < f["n_engine_candidates"] + f["n_pool_random_controls"]:
            run.log.warning("   too few forgotten candidates; problem skipped")
            prob_rows[-1]["skipped"] = True
            continue
        texts = [paper_text(w, True, True) for w in forgotten]
        r_bm = ranks_from_scores(bm25_scores(prob["statement"], texts), rng)
        r_de = ranks_from_scores(dense_scores(prob["statement"], texts, cfg["embeddings"]["model"],
                                              cfg["embeddings"]["batch_size"],
                                              force_tfidf=cfg["embeddings"].get("force_tfidf", False))[0], rng)
        r_hy = ranks_from_scores(rrf([r_bm, r_de]), rng)
        K = min(f["rerank_top_k"], len(forgotten))
        top = list(np.argsort(r_hy)[:K])
        sc = {}
        for j in top:
            pj = parse_json(engine_llm.chat(P.RERANK_SYSTEM, P.RERANK_USER.format(
                need=prob["statement"], candidate=texts[j]), task="rerank",
                meta={"problem": prob["id"], "cand": forgotten[j]["id"]})) or {}
            try:
                sc[j] = float(pj.get("score"))
            except (TypeError, ValueError):
                sc[j] = -1.0
                run.count("rerank_parse_failures")
        ordered = sorted(top, key=lambda j: (-sc[j], r_hy[j]))
        eng = ordered[:f["n_engine_candidates"]]
        rest = [j for j in range(len(forgotten)) if j not in set(eng)]
        ctrl = list(rng.choice(rest, size=f["n_pool_random_controls"], replace=False))
        avail = [w for w in global_pool if w["id"] not in used_global and w["id"] not in {x["id"] for x in forgotten}]
        gidx = list(rng.choice(len(avail), size=min(f["n_global_random_controls"], len(avail)), replace=False))
        chosen = ([("engine", forgotten[j], sc.get(j)) for j in eng] +
                  [("pool_random", forgotten[j], sc.get(j)) for j in ctrl] +
                  [("global_random", avail[j], None) for j in gidx])
        for g, w, s in chosen:
            if g == "global_random":
                used_global.add(w["id"])
            items.append({"item_id": sha256_text(f"{cfg['seed']}|{prob['id']}|{w['id']}|{g}")[:12],
                          "problem": prob["id"], "group": g, "work_id": w["id"], "doi": w.get("doi"),
                          "title": w["title"], "year": w["year"], "cited_by_count": w["cited_by_count"],
                          "engine_llm_score": s, "text": paper_text(w, True, True),
                          "statement": prob["statement"]})
    items_df = pd.DataFrame(items)
    pd.DataFrame(prob_rows).to_csv(run.path("results", "forward_problems_retrieval.csv"), index=False)
    if items_df.empty:
        report.h2("Forward test")
        report.p("No problem had enough forgotten candidates; nothing to rate.")
        return {"n_items": 0}
    # blinded key: what judges see vs what the analyst sees later
    items_df.drop(columns=["text", "statement"]).to_csv(run.path("results", "forward_items_UNBLINDING_KEY.csv"),
                                                         index=False)
    leaks = []
    for _, it in items_df.iterrows():
        for lk in scan(it.text):
            leaks.append({"item_id": it.item_id, "leak": lk})
    pd.DataFrame(leaks, columns=["item_id", "leak"]).to_csv(run.path("results", "forward_leak_scan.csv"), index=False)
    ratings = rate_items(items_df, judges, cfg, run)
    ratings.to_csv(run.path("results", "forward_ratings_long.csv"), index=False)
    return analyse_forward(items_df, ratings, cfg, run, report, pd.DataFrame(prob_rows), gate, label,
                           len(problems), len(leaks))


def rate_items(items: pd.DataFrame, judges: list, cfg, run) -> pd.DataFrame:
    rows = []
    for ji, judge in enumerate(judges):
        order = np.random.default_rng(cfg["seed"] + 100 + ji).permutation(len(items))
        run.log.info("Judge %s rating %d items (blind, shuffled)", judge.name, len(items))
        for idx in order:
            it = items.iloc[idx]
            rep = judge.chat(P.JUDGE_SYSTEM, P.JUDGE_USER.format(problem=it.statement, candidate=it.text),
                             task="judge", meta={"item": it.item_id}, max_tokens=1500)
            pj = parse_json(rep) or {}

            def clip(v):
                try:
                    v = int(round(float(v)))
                    return v if 1 <= v <= 5 else np.nan
                except (TypeError, ValueError):
                    return np.nan
            a, nov = clip(pj.get("applicability")), clip(pj.get("novelty"))
            if np.isnan(a):
                run.count("judge_parse_failures")
            rows.append({"item_id": it.item_id, "judge": judge.name, "model": judge.model,
                         "applicability": a, "novelty": nov, "reason": str(pj.get("reason", ""))[:500]})
    return pd.DataFrame(rows)


def analyse_forward(items, ratings, cfg, run, report, probs, gate=None, label="confirmatory",
                    n_problems=0, n_leaks=0) -> dict:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from .gate import collapse_share
    rc, alpha = cfg["rating"], cfg["stats"]["alpha"]
    report.h2(f"Forward test ({label}): forgotten pre-1990 candidates for {n_problems} "
              f"antibiotic-resistance problems")
    report.table(probs)
    all_judges = sorted(ratings.judge.unique())
    dropped = {}
    passed_gate = None if gate is None else {g["model_name"] for g in gate if g["passed"]}
    for j in all_judges:
        share = collapse_share(ratings[ratings.judge == j].applicability.to_numpy(float))
        if share > cfg["gate"]["collapse_threshold"]:
            dropped[j] = f"answer collapse ({share:.0%} identical)"
        elif passed_gate is not None and j not in passed_gate:
            dropped[j] = "failed the known-answer gate"
    judges = [j for j in all_judges if j not in dropped]
    report.p("Judges used: " + (", ".join(judges) or "none") + ". Dropped: " +
             (", ".join(f"{j} ({why})" for j, why in dropped.items()) or "none") + ".")
    report.p(f"Prompt leak scan of the {len(items)} texts shown to judges: {n_leaks} leaks found.")
    if len(judges) < 2:
        report.p("Fewer than 2 usable judges, so the forward test is NOT TESTABLE in this run.")
        return {"n_items": len(items), "judges_used": judges, "judges_dropped": dropped,
                "testable": False, "n_leaks": n_leaks}
    need_k = min(rc["hit_min_judges_at_threshold"], len(judges))
    wide_a = ratings.pivot(index="item_id", columns="judge", values="applicability")
    wide_n = ratings.pivot(index="item_id", columns="judge", values="novelty")
    alpha_a = krippendorff_alpha(wide_a[judges].T.to_numpy(float), "ordinal")
    alpha_n = krippendorff_alpha(wide_n[judges].T.to_numpy(float), "ordinal")
    reliable = bool(alpha_a >= rc["min_alpha_reliable"])
    agg = pd.DataFrame({"item_id": wide_a.index,
                        "median_applicability": wide_a[judges].median(axis=1).to_numpy(),
                        "mean_applicability": wide_a[judges].mean(axis=1).to_numpy(),
                        "n_judges_ge4": (wide_a[judges] >= rc["hit_min_median_applicability"]).sum(axis=1).to_numpy(),
                        "median_novelty": wide_n[judges].median(axis=1).to_numpy()})
    df = items.drop(columns=["text", "statement"]).merge(agg, on="item_id")
    df["hit"] = ((df.median_applicability >= rc["hit_min_median_applicability"]) &
                 (df.n_judges_ge4 >= need_k) &
                 (df.median_novelty >= rc["hit_min_median_novelty"]) &
                 (df.cited_by_count <= cfg["forward"]["forgotten_max_citations"]))
    df.to_csv(run.path("results", "forward_items_scored.csv"), index=False)
    iters = cfg["stats"]["permutation_iterations"]
    tests = {
        "H2_engine_vs_pool_random": stratified_permutation_test(df.mean_applicability, df.group, df.problem,
                                                                "engine", "pool_random", iters, cfg["seed"]),
        "H3_engine_vs_global_random": stratified_permutation_test(df.mean_applicability, df.group, df.problem,
                                                                  "engine", "global_random", iters, cfg["seed"]),
    }
    from scipy.stats import fisher_exact
    hits = {g: (int(df[df.group == g].hit.sum()), int((df.group == g).sum())) for g in GROUPS}
    e, c = hits["engine"], hits["pool_random"]
    _, p_f = fisher_exact([[e[0], e[1] - e[0]], [c[0], c[1] - c[0]]], alternative="greater")
    tests["hit_rate_engine_vs_pool_random_fisher"] = {"p_one_sided": float(p_f)}
    adj = holm({"H2": tests["H2_engine_vs_pool_random"]["p_one_sided"],
                "H3": tests["H3_engine_vs_global_random"]["p_one_sided"]})
    tests["H2_engine_vs_pool_random"]["p_holm"] = adj["H2"]
    tests["H3_engine_vs_global_random"]["p_holm"] = adj["H3"]
    report.h2("Blind AI judge panel")
    report.p(f"Judges: {', '.join(f'{j} ({ratings[ratings.judge == j].model.iloc[0]})' for j in judges)}. "
             f"Each judge saw every item alone, in its own random order, with author names and years removed "
             f"and without knowing which items the engine picked.")
    report.p(f"Agreement (Krippendorff's alpha, ordinal): applicability {alpha_a:.3f}, novelty {alpha_n:.3f}. "
             + ("Applicability ratings meet the preregistered reliability bar."
                if reliable else f"Applicability alpha is below the preregistered bar of {rc['min_alpha_reliable']}, "
                "so forward-test results are EXPLORATORY only."))
    gt = []
    for g in GROUPS:
        s = df[df.group == g]
        k, n = hits[g]
        lo, hi = wilson_ci(k, n, alpha)
        gt.append({"group": g, "n_items": n, "mean_applicability": s.mean_applicability.mean(),
                   "mean_novelty": s.median_novelty.mean(), "hits": k, "hit_rate": k / n if n else np.nan,
                   "hit_rate_95CI": f"[{lo:.2f}, {hi:.2f}]"})
    report.table(pd.DataFrame(gt))
    report.h2("Forward-test hypotheses")
    for name, t in tests.items():
        if "difference" in t:
            report.p(f"{name}: engine mean {t['mean_treat']:.2f} vs control {t['mean_control']:.2f} "
                     f"(difference {t['difference']:+.2f}), stratified permutation p = {t['p_one_sided']:.4f}, "
                     f"Holm-adjusted p = {t['p_holm']:.4f}.")
        else:
            report.p(f"{name}: one-sided Fisher exact p = {t['p_one_sided']:.4f}.")
    pj = ratings.groupby(["judge", "model"]).agg(mean_applicability=("applicability", "mean"),
                                                 mean_novelty=("novelty", "mean"),
                                                 parse_failures=("applicability", lambda s: int(s.isna().sum()))).reset_index()
    report.h2("Per-judge calibration")
    report.table(pj)
    fig, ax = plt.subplots(figsize=(6, 3.6))
    data = [df[df.group == g].mean_applicability.dropna() for g in GROUPS]
    ax.boxplot(data, tick_labels=GROUPS, showmeans=True)
    ax.set_ylabel("mean applicability (1-5)")
    ax.spines[["top", "right"]].set_visible(False)
    report.figure(fig, "forward_applicability_by_group", "Blind judge applicability ratings by group.")
    plt.close(fig)
    short = df[(df.group == "engine")].sort_values(["hit", "mean_applicability"], ascending=False).head(20)
    report.h2("Rediscovery shortlist (unblinded after rating)")
    report.p("Engine candidates ranked by blind judge rating. A 'hit' here is a lead to check, "
             "not a confirmed rediscovery: each needs reading in full and, ideally, a lab or literature follow-up.")
    report.table(short[["problem", "work_id", "doi", "title", "year", "cited_by_count",
                        "mean_applicability", "median_novelty", "hit"]])
    summary = {"n_items": len(df), "judges": judges, "judges_used": judges, "judges_dropped": dropped,
               "testable": True, "n_leaks": n_leaks, "krippendorff_alpha_applicability": alpha_a,
               "krippendorff_alpha_novelty": alpha_n, "ratings_reliable": reliable,
               "hits_by_group": hits, "tests": tests}
    return summary
