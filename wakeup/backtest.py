# Wake-up Engine: finding forgotten science that already solves today's problems
# Author: KEYUR SHAILESHKUMAR PATEL
# ORCID: https://orcid.org/0009-0008-5261-043X
# Affiliations: (1) MSc Artificial Intelligence student, Department of Computer Science,
#               Brunel University London, UK; (2) Independent researcher
# Note: Conducted independently; not an official Brunel University London project.
# License: MIT (see LICENSE)
"""Study 1, the back-test.

For each known sleeping beauty (SB) found computationally in OpenAlex:
  1. compute its beauty coefficient B and awakening year Y (Ke et al. 2015)
  2. find the field that woke it (papers citing it in [Y, Y+3]) and describe that field's
     open needs using ONLY papers from year Y-1 that do not cite the SB
  3. hide the SB among 999 decoys from the same field and era (author names, years removed)
  4. rank all 1000 with random, BM25, dense, hybrid and the full engine (hybrid + LLM re-rank)
  5. hit = SB in the top 10 (preregistered primary outcome)

v0.2 adds: a fixed SHA-256 development/confirmatory split (exploratory runs touch the
development part only), per-item random seeds, saved per-candidate scores for independent
re-checking, a prompt leak scan, a disguised-text memorization check, and inputs for the
known-answer gate.
"""
from __future__ import annotations

import datetime as _dt
import json
from collections import Counter

import numpy as np
import pandas as pd

from . import prompts as P
from .beauty import beauty_coefficient, citation_series
from .leakscan import scan
from .llm import parse_json
from .retrieval import bm25_scores, dense_scores, ranks_from_scores, rrf
from .split import assign, item_seed
from .stats import (bootstrap_ci, expected_random_mrr, holm, mcnemar_exact, mcnemar_one_sided, mde_binomial, mrr,
                    poisson_binomial_greater, wilson_ci)
from .textutil import anonymize, paper_text, title_similarity, surnames

METHODS = ["random", "bm25", "dense", "hybrid", "engine"]




# ------------------------------------------------------------------ step 1: sample
def find_sleeping_beauties(oa, cfg: dict, run) -> tuple[pd.DataFrame, list[dict]]:
    b = cfg["backtest"]
    seed = cfg["seed"]
    last_year = b.get("last_complete_year") or (_dt.date.today().year - 1)
    y0, y1 = b["candidate_pub_years"]
    filters = {"publication_year": f"{y0}-{y1}",
               "cited_by_count": f">{b['candidate_min_citations'] - 1}",
               "has_abstract": "true", "type": "article"}
    run.log.info("Sampling up to %d candidate old papers: %s", b["candidate_pool_size"], filters)
    pool = oa.list_works(filters, b["candidate_pool_size"], sample_seed=seed)
    run.log.info("Candidate pool: %d papers", len(pool))
    rows, works = [], {}
    for i, w in enumerate(pool):
        if i and i % 250 == 0:
            run.log.info("  citation histories: %d/%d", i, len(pool))
        hist = oa.citations_by_year(w["id"])
        bc = beauty_coefficient(citation_series(hist, w["year"], last_year), w["year"])
        reasons = []
        if bc.sleep_years < b["min_sleep_years"]:
            reasons.append("short_sleep")
        if not (b["min_awakening_year"] <= bc.awakening_year <= b["max_awakening_year"]):
            reasons.append("awakening_year_out_of_range")
        if bc.c_m < b["min_peak_citations"]:
            reasons.append("low_peak")
        if bc.B < b["min_beauty_B"]:
            reasons.append("low_B")
        rows.append({"id": w["id"], "year": w["year"], "title": w["title"], "field": w["field"],
                     "cited_by_count": w["cited_by_count"], "B": round(bc.B, 3), "t_m": bc.t_m,
                     "c_m": bc.c_m, "awakening_year": bc.awakening_year, "sleep_years": bc.sleep_years,
                     "eligible": not reasons, "exclusion_reasons": ";".join(reasons),
                     "series": json.dumps(bc.series)})
        works[w["id"]] = w
    df = pd.DataFrame(rows)
    elig = df[df.eligible].sort_values(["B", "id"], ascending=[False, True])
    chosen = elig.head(b["n_sleeping_beauties"])
    df["selected"] = df.id.isin(chosen.id)
    sbs = []
    for _, r in chosen.iterrows():
        w = dict(works[r.id])
        w.update({"B": r.B, "awakening_year": int(r.awakening_year), "sleep_years": int(r.sleep_years),
                  "c_m": int(r.c_m)})
        sbs.append(w)
    run.log.info("Eligible sleeping beauties: %d, selected: %d", len(elig), len(sbs))
    return df, sbs


# ------------------------------------------------------------------ step 2: need
def build_need(oa, llm, sb: dict, cfg: dict, run) -> dict:
    b = cfg["backtest"]
    Y = sb["awakening_year"]
    awakeners = oa.list_works({"cites": sb["id"], "publication_year": f"{Y}-{Y + b['awakener_window_years']}"}, 200)
    topics = Counter(w["topic_id"] for w in awakeners if w.get("topic_id"))
    if not topics:
        return {"ok": False, "reason": "no_awakener_topic", "n_awakeners": len(awakeners)}
    topic_id, _ = sorted(topics.items(), key=lambda kv: (-kv[1], kv[0]))[0]
    topic_name = next((w["topic"] for w in awakeners if w.get("topic_id") == topic_id), None)
    year = Y - b["need_context_year_offset"]
    ctx = oa.list_works({"primary_topic.id": topic_id, "publication_year": year, "has_abstract": "true"},
                        200, sample_seed=cfg["seed"])
    ctx = [w for w in ctx if w["id"] != sb["id"] and sb["id"] not in w.get("referenced_works", [])]
    ctx = ctx[:b["need_context_n_abstracts"]]
    if len(ctx) < 5:
        return {"ok": False, "reason": "insufficient_need_context", "n_context": len(ctx),
                "topic_id": topic_id}
    # Blind the context to the SB: drop its authors' surnames too
    sb_names = sb.get("authors", [])
    abstracts = [anonymize(f"- {w['title']}: {w['abstract'][:700]}", w.get("authors", []) + sb_names)
                 for w in ctx]
    raw_need = "\n".join(abstracts)
    reply = llm.chat(P.NEED_SYSTEM, P.NEED_USER.format(n=len(ctx), abstracts=raw_need),
                     task="need_summary", meta={"sb": sb["id"]}, max_tokens=600)
    parsed = parse_json(reply) or {}
    need = anonymize(str(parsed.get("need") or reply)[:2500], sb_names)
    return {"ok": True, "topic_id": topic_id, "topic": topic_name, "context_year": year,
            "n_awakeners": len(awakeners), "context_ids": [w["id"] for w in ctx],
            "need": need, "raw_need": raw_need}


# ------------------------------------------------------------------ step 3: decoys
def build_candidates(oa, sb: dict, cfg: dict, run) -> tuple[list[dict], str]:
    b = cfg["backtest"]
    n_dec = b["n_candidates"] - 1
    y = sb["year"]
    seed = cfg["seed"] + int(sb["id"].lstrip("W")[-6:] or 0)
    tiers = [("same_field_pm%d" % b["decoy_pub_year_window"],
              {"primary_topic.field.id": sb["field_id"],
               "publication_year": f"{y - b['decoy_pub_year_window']}-{y + b['decoy_pub_year_window']}"}),
             ("same_field_pm%d" % (2 * b["decoy_pub_year_window"]),
              {"primary_topic.field.id": sb["field_id"],
               "publication_year": f"{y - 2 * b['decoy_pub_year_window']}-{y + 2 * b['decoy_pub_year_window']}"}),
             ("any_field_pm%d" % b["decoy_pub_year_window"],
              {"publication_year": f"{y - b['decoy_pub_year_window']}-{y + b['decoy_pub_year_window']}"})]
    if b.get("decoy_match") != "same_field" or not sb.get("field_id"):
        tiers = tiers[2:]
    decoys, seen, used = [], {sb["id"]}, []
    for name, f in tiers:
        f = dict(f, has_abstract="true", type="article")
        for w in oa.list_works(f, int(n_dec * 1.3), sample_seed=seed):
            if w["id"] in seen or not w["abstract"]:
                continue
            seen.add(w["id"])
            decoys.append(w)
            if len(decoys) >= n_dec:
                break
        used.append(name)
        if len(decoys) >= n_dec:
            break
    return decoys[:n_dec], "+".join(used)


# ------------------------------------------------------------------ step 4: rank
def _llm_score(llm, need, text, meta, run, task="rerank"):
    rep = llm.chat(P.RERANK_SYSTEM, P.RERANK_USER.format(need=need, candidate=text), task=task, meta=meta)
    try:
        return float((parse_json(rep) or {}).get("score"))
    except (TypeError, ValueError):
        run.count(f"{task}_parse_failures")
        return -1.0


def rank_all(need: str, raw_need: str, cands: list[dict], target_idx: int, llm, cfg, run, rng,
             sb_id: str, leaks: list) -> tuple[dict, pd.DataFrame, list[int], list[str]]:
    b = cfg["backtest"]
    texts = [paper_text(w, b["anonymize"], b["include_title"]) for w in cands]
    emb = dict(model_name=cfg["embeddings"]["model"], batch_size=cfg["embeddings"]["batch_size"],
               force_tfidf=cfg["embeddings"].get("force_tfidf", False))
    out = {}
    r_rand = ranks_from_scores(np.zeros(len(texts)), rng)
    s_bm = bm25_scores(need, texts)
    s_de, emb_kind = dense_scores(need, texts, **emb)
    r_bm, r_de = ranks_from_scores(s_bm, rng), ranks_from_scores(s_de, rng)
    s_hy = rrf([r_bm, r_de])
    r_hy = ranks_from_scores(s_hy, rng)
    K = min(b["rerank_top_k"], len(texts))
    top = [int(j) for j in np.argsort(r_hy)[:K]]
    llm_scores = {}
    for j in top:
        for f in scan(texts[j], cands[j].get("authors")):
            leaks.append({"sb": sb_id, "where": "candidate", "work": cands[j]["id"], "leak": f})
        llm_scores[j] = _llm_score(llm, need, texts[j], {"sb": sb_id, "cand": cands[j]["id"]}, run)
    ordered = sorted(top, key=lambda j: (-llm_scores[j], r_hy[j]))
    eng = r_hy.copy()
    for pos, j in enumerate(ordered):
        eng[j] = pos + 1
    out.update(random=int(r_rand[target_idx]), bm25=int(r_bm[target_idx]), dense=int(r_de[target_idx]),
               hybrid=int(r_hy[target_idx]), engine=int(eng[target_idx]),
               engine_llm_score_target=llm_scores.get(target_idx), embedding_backend=emb_kind)
    if b.get("sensitivity_raw_need"):
        rb = ranks_from_scores(bm25_scores(raw_need, texts), rng)
        rd = ranks_from_scores(dense_scores(raw_need, texts, **emb)[0], rng)
        rh = ranks_from_scores(rrf([rb, rd]), rng)
        out.update(raw_bm25=int(rb[target_idx]), raw_dense=int(rd[target_idx]), raw_hybrid=int(rh[target_idx]))
    scores = pd.DataFrame({"cand_id": [w["id"] for w in cands], "is_target": [j == target_idx for j in range(len(cands))],
                           "bm25": s_bm, "dense": s_de, "rank_random": r_rand, "rank_bm25": r_bm,
                           "rank_dense": r_de, "rrf": s_hy, "rank_hybrid": r_hy,
                           "llm_score": [llm_scores.get(j, np.nan) for j in range(len(cands))],
                           "rank_engine": eng})
    return out, scores, top, texts


def disguised_check(llm, paraphraser, need, texts, top, target_idx, cfg, run, sb_id, cands) -> dict | None:
    """Re-rank the hybrid top-k with every text paraphrased by a different model family."""
    k = cfg["backtest"]["disguise_top_k"]
    sub = top[:k]
    if target_idx not in sub:
        return None
    orig, disg = {}, {}
    for j in sub:
        orig[j] = _llm_score(llm, need, texts[j], {"sb": sb_id, "cand": cands[j]["id"]}, run)
        rep = paraphraser.chat(P.PARA_SYSTEM, P.PARA_USER.format(candidate=texts[j]), task="paraphrase",
                               meta={"sb": sb_id, "cand": cands[j]["id"]}, max_tokens=600)
        para = str((parse_json(rep) or {}).get("text") or "")
        para = anonymize(para, cands[j].get("authors")) if para else texts[j]
        disg[j] = _llm_score(llm, need, "Abstract: " + para, {"sb": sb_id, "cand": cands[j]["id"],
                                                              "disguised": True}, run)

    def pos(sc):
        order = sorted(sub, key=lambda j: (-sc[j], j))
        return order.index(target_idx) + 1
    return {"sb": sb_id, "k": len(sub), "rank_original": pos(orig), "rank_disguised": pos(disg),
            "score_original": orig[target_idx], "score_disguised": disg[target_idx]}


# ------------------------------------------------------------------ memorization
def memorization(llm, work: dict, cfg, sb_id: str, kind: str) -> dict:
    b = cfg["backtest"]
    text = paper_text(work, b["anonymize"], b["include_title"])
    rep = llm.chat(P.MEMO_SYSTEM, P.MEMO_USER.format(candidate=text), task="memorization",
                   meta={"sb": sb_id, "work": work["id"], "kind": kind})
    pj = parse_json(rep) or {}
    sim = title_similarity(str(pj.get("title") or ""), work.get("title") or "")
    names = [s.lower() for s in surnames(work.get("authors", [])[:1])]
    fa = str(pj.get("first_author") or "").lower()
    author_ok = bool(names) and any(n in fa for n in names)
    try:
        year_ok = pj.get("year") is not None and abs(int(pj["year"]) - int(work["year"])) <= 2
    except (TypeError, ValueError):
        year_ok = False
    memorized = sim >= b["memorization_title_similarity"] or (author_ok and year_ok)
    return {"work": work["id"], "kind": kind, "claimed_recognized": bool(pj.get("recognized")),
            "title_similarity": round(sim, 3), "author_match": author_ok, "year_match": year_ok,
            "memorized": bool(memorized)}


# ------------------------------------------------------------------ main


# ------------------------------------------------------------------ main
def select_sample(oa, cfg, run, frozen_sample: list[dict] | None):
    """Use the frozen sample when one exists (confirmatory), else screen OpenAlex now."""
    if frozen_sample is not None:
        run.log.info("Using the FROZEN sleeping-beauty sample (%d items)", len(frozen_sample))
        return pd.DataFrame(), frozen_sample
    table, sbs = find_sleeping_beauties(oa, cfg, run)
    for sb in sbs:
        sb["split"] = assign(sb["id"], cfg["seed"], cfg["backtest"]["dev_fraction"])
    if len(table):
        table["split"] = [assign(i, cfg["seed"], cfg["backtest"]["dev_fraction"]) for i in table.id]
    return table, sbs


def run_backtest(oa, llm, cfg: dict, run, report, split: str = "dev", paraphraser=None,
                 frozen_sample: list[dict] | None = None) -> dict:
    b = cfg["backtest"]
    table, sbs = select_sample(oa, cfg, run, frozen_sample)
    if len(table):
        # the locked part is never shown: titles of confirmatory items are blanked in this table
        shown = table.copy()
        shown.loc[(shown.selected) & (shown.split != split), ["title"]] = "[LOCKED]"
        shown.to_csv(run.path("data", "candidate_pool_beauty.csv"), index=False)
    run.write_json("data/sleeping_beauties_selected.json",
                   [{"id": s["id"], "split": s["split"], "year": s["year"], "B": s["B"],
                     "awakening_year": s["awakening_year"], "sleep_years": s["sleep_years"]} for s in sbs])
    run.write_json("data/sample_for_freeze.json", sbs)
    todo = [s for s in sbs if s["split"] == split]
    run.log.info("Split: %d development, %d confirmatory. This run processes the %s part only (%d items).",
                 sum(s["split"] == "dev" for s in sbs), sum(s["split"] == "confirm" for s in sbs), split, len(todo))
    results, needs, memo, leaks, disg, gate_inputs = [], [], [], [], [], []
    # Items excluded by the author before registration (D20, ISSUES I21). Skipped before any call.
    pre_excluded = set(b.get("excluded_before_registration") or [])
    for i, sb in enumerate(todo, 1):
        rng = np.random.default_rng(item_seed(cfg["seed"], "rank", sb["id"]))
        run.log.info("[%d/%d] SB %s (%s, woke %s, B=%.1f)", i, len(todo), sb["id"], sb["year"],
                     sb["awakening_year"], sb["B"])
        if sb["id"] in pre_excluded:
            results.append({"sb": sb["id"], "usable": False, "exclusion": "excluded_before_registration"})
            run.log.info("   excluded: excluded_before_registration (D20, ISSUES I21)")
            continue
        nd = build_need(oa, llm, sb, cfg, run)
        needs.append({"sb": sb["id"], **{k: v for k, v in nd.items() if k != "raw_need"}})
        if not nd["ok"]:
            results.append({"sb": sb["id"], "usable": False, "exclusion": nd["reason"]})
            run.log.info("   excluded: %s", nd["reason"])
            continue
        for f in scan(nd["need"], sb.get("authors")):
            leaks.append({"sb": sb["id"], "where": "need", "work": sb["id"], "leak": f})
        decoys, tier = build_candidates(oa, sb, cfg, run)
        if len(decoys) < b.get("min_decoys", 99):
            results.append({"sb": sb["id"], "usable": False, "exclusion": "too_few_decoys"})
            continue
        cands = decoys + [sb]
        perm = rng.permutation(len(cands))
        cands = [cands[j] for j in perm]
        target_idx = int(np.where(perm == len(decoys))[0][0])
        r, scores, top, texts = rank_all(nd["need"], nd["raw_need"], cands, target_idx, llm, cfg, run, rng,
                                         sb["id"], leaks)
        scores.to_csv(run.path("results", "scores", f"{sb['id']}.csv"), index=False)
        row = {"sb": sb["id"], "usable": True, "exclusion": "", "sb_year": sb["year"],
               "awakening_year": sb["awakening_year"], "B": sb["B"], "field": sb.get("field"),
               "waking_topic": nd.get("topic"), "n_candidates": len(cands), "decoy_tier": tier,
               **{f"rank_{m}": r[m] for m in METHODS},
               **{f"rank_{k}": r[k] for k in ("raw_bm25", "raw_dense", "raw_hybrid") if k in r},
               "engine_llm_score_target": r["engine_llm_score_target"],
               "embedding_backend": r["embedding_backend"]}
        if b.get("memorization_check"):
            m = memorization(llm, sb, cfg, sb["id"], "sleeping_beauty")
            memo.append({"sb": sb["id"], **m})
            row["memorized"] = m["memorized"]
            others = [k for k in range(len(cands)) if k != target_idx]
            for d in [cands[j] for j in rng.choice(others, size=min(3, len(others)), replace=False)]:
                memo.append({"sb": sb["id"], **memorization(llm, d, cfg, sb["id"], "decoy")})
        if b.get("disguise_check") and paraphraser is not None:
            dc = disguised_check(llm, paraphraser, nd["need"], texts, top, target_idx, cfg, run, sb["id"], cands)
            if dc:
                disg.append(dc)
        gate_inputs.append({"sb": sb, "need": nd["need"], "candidates": cands, "target_idx": target_idx})
        results.append(row)
        run.log.info("   ranks: %s", {m: r[m] for m in METHODS})
    res = pd.DataFrame(results)
    res.to_csv(run.path("results", "backtest_ranks.csv"), index=False)
    pd.DataFrame(needs).to_json(run.path("results", "need_statements.jsonl"), orient="records", lines=True)
    memo_df = pd.DataFrame(memo)
    if memo:
        memo_df.to_csv(run.path("results", "memorization_checks.csv"), index=False)
    pd.DataFrame(leaks, columns=["sb", "where", "work", "leak"]).to_csv(run.path("results", "leak_scan.csv"), index=False)
    disg_df = pd.DataFrame(disg)
    if disg:
        disg_df.to_csv(run.path("results", "disguised_check.csv"), index=False)
    summary = analyse_backtest(res, memo_df, disg_df, pd.DataFrame(leaks), cfg, run, report, table, split, len(sbs))
    run.write_json("results/backtest_summary.json", summary)
    return {"summary": summary, "gate_inputs": gate_inputs, "results": res}


def method_table(u: pd.DataFrame, cols: list[str], k_list: list[int], cfg) -> pd.DataFrame:
    rows = []
    for c in cols:
        ranks = u[f"rank_{c}"].to_numpy()
        row = {"method": c, "n": len(ranks)}
        for k in k_list:
            row[f"hit@{k}"] = float(np.mean(ranks <= k))
        row["MRR"] = mrr(ranks)
        lo, hi = bootstrap_ci(1.0 / ranks, iters=cfg["stats"]["bootstrap_iterations"], seed=cfg["seed"])
        row["MRR_95CI"] = f"[{lo:.3f}, {hi:.3f}]"
        row["median_rank"] = float(np.median(ranks))
        rows.append(row)
    return pd.DataFrame(rows)




def analyse_backtest(res, memo, disg, leaks, cfg, run, report, pool, split, n_selected_all) -> dict:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    b, alpha = cfg["backtest"], cfg["stats"]["alpha"]
    k = b["hit_k"]
    label = "development (exploratory)" if split == "dev" else "confirmatory"
    report.h2(f"Back-test on the {label} sleeping beauties")
    n_pool = len(pool)
    n_elig = int(pool.eligible.sum()) if len(pool) else None
    usable = res[res["usable"] == True] if len(res) else res  # noqa: E712
    n = len(usable)
    excl = res[res["usable"] == False].exclusion.value_counts().to_dict() if len(res) else {}  # noqa: E712
    report.bullets([f"Candidate old papers screened: {n_pool if n_pool else 'frozen sample used'}",
                    f"Passed sleeping-beauty criteria: {n_elig if n_elig is not None else 'n/a'}",
                    f"Selected (top by B): {n_selected_all}, of which {len(res)} are in the {label} part",
                    f"Usable after need/decoy checks: {n}",
                    "Exclusions: " + (", ".join(f"{a}: {c}" for a, c in excl.items()) or "none")])
    summary = {"split": split, "n_screened": n_pool, "n_eligible": n_elig, "n_selected_all": n_selected_all,
               "n_in_split": len(res), "n_usable": n, "exclusions": excl,
               "n_leaks": int(len(leaks)), "leaks_by_type": leaks.leak.value_counts().to_dict() if len(leaks) else {}}
    if n == 0:
        report.p("No usable sleeping beauties, so no test was run.")
        return summary
    min_usable = b["min_usable"] if split == "confirm" else b.get("min_usable_dev", 5)
    if n < min_usable:
        report.p(f"WARNING: only {n} usable items, below the minimum of {min_usable}. Results are underpowered.")
        summary["underpowered"] = True
    hits = (usable.rank_engine <= k).to_numpy()
    ps = (np.minimum(k, usable.n_candidates) / usable.n_candidates).to_numpy()
    p_primary = poisson_binomial_greater(int(hits.sum()), list(ps))
    lo, hi = wilson_ci(int(hits.sum()), n, alpha)
    mde = mde_binomial(n, float(ps.mean()), alpha, 0.8)
    # H1b (co-primary, added after synthetic world W4 showed word overlap alone can beat chance):
    # engine beats plain hybrid search on the same items. Holm across H1a and H1b.
    h1b = mcnemar_one_sided(hits, (usable.rank_hybrid <= k).to_numpy())
    adj1 = holm({"H1a": p_primary, "H1b": h1b["p_one_sided"]})
    summary["primary"] = {"hypothesis": f"H1a: engine hit@{k} rate > chance", "hits": int(hits.sum()), "n": n,
                          "rate": float(hits.mean()), "rate_95CI_wilson": [lo, hi], "chance_rate": float(ps.mean()),
                          "p_one_sided": p_primary, "p_holm": adj1["H1a"], "supported": bool(adj1["H1a"] < alpha),
                          "minimum_detectable_rate_80pct_power": mde}
    summary["primary_b"] = {"hypothesis": f"H1b: engine hit@{k} > hybrid search hit@{k} (same items)",
                            "engine_only_hits": h1b["a_only"], "search_only_hits": h1b["b_only"],
                            "search_hits": int((usable.rank_hybrid <= k).sum()),
                            "p_one_sided": h1b["p_one_sided"], "p_holm": adj1["H1b"],
                            "supported": bool(adj1["H1b"] < alpha)}
    report.h2("Main result (H1)" + (" - preview only" if split == "dev" else ""))
    report.p(f"The engine put the true sleeping beauty in its top {k} for {int(hits.sum())} of {n} items "
             f"({hits.mean():.1%}, 95% CI {lo:.1%} to {hi:.1%}). Chance would give {ps.mean():.1%}. "
             f"Exact one-sided p = {p_primary:.3g} (Holm-adjusted {adj1['H1a']:.3g}). With {n} items, a true hit rate of {mde:.1%} or more "
             f"would be detected 80% of the time (minimum detectable effect).")
    pb = summary["primary_b"]
    report.p(f"H1b, engine vs plain search on the same items: the engine alone found {pb['engine_only_hits']}, "
             f"search alone found {pb['search_only_hits']} (search total {pb['search_hits']} of {n}). "
             f"Exact one-sided McNemar p = {pb['p_one_sided']:.3g}, Holm-adjusted {pb['p_holm']:.3g}.")
    if split == "dev":
        report.p("These items were used to check and tune the method, so this is a preview, not a finding. "
                 "The preregistered test uses only the locked confirmatory part.")
    sec = {}
    for other in ["hybrid", "bm25", "dense"]:
        sec[f"engine_vs_{other}"] = mcnemar_exact(usable.rank_engine.to_numpy() <= k,
                                                  usable[f"rank_{other}"].to_numpy() <= k)
    adj = holm({kk: v["p_two_sided"] for kk, v in sec.items()})
    for kk in sec:
        sec[kk]["p_holm"] = adj[kk]
    summary["secondary"] = sec
    report.h2("All methods")
    mt = method_table(usable, METHODS, b["report_k"], cfg)
    report.table(mt)
    mt.to_csv(run.path("results", "backtest_method_table.csv"), index=False)
    summary["method_table"] = mt.to_dict(orient="records")
    med_n = int(usable.n_candidates.median())
    report.p(f"Pure chance with {med_n} candidates gives MRR {expected_random_mrr(med_n):.4f} "
             f"and hit@{k} {min(k, med_n) / med_n:.1%}.")
    report.h2("Does the AI reading add value? (engine vs search alone)")
    report.table(pd.DataFrame([{"comparison": kk, "engine_only_hits": v["a_only"], "other_only_hits": v["b_only"],
                                "p_exact": v["p_two_sided"], "p_holm": v["p_holm"]} for kk, v in sec.items()]))
    if "memorized" in usable.columns:
        mem = usable[usable.memorized == True]  # noqa: E712
        clean = usable[usable.memorized != True]  # noqa: E712
        dec = memo[memo.kind == "decoy"] if len(memo) else memo
        sens = {"n_memorized": int(len(mem)),
                "decoy_false_recognition_rate": float(dec.memorized.mean()) if len(dec) else None}
        if len(clean):
            hc = (clean.rank_engine <= k).to_numpy()
            pc = (np.minimum(k, clean.n_candidates) / clean.n_candidates).to_numpy()
            sens.update(n_clean=int(len(clean)), clean_hits=int(hc.sum()), clean_rate=float(hc.mean()),
                        clean_p=poisson_binomial_greater(int(hc.sum()), list(pc)))
        summary["sensitivity_memorization"] = sens
        report.h2("Leakage check 1: did the AI simply remember the paper?")
        report.p(f"The engine model named {len(mem)} of {n} sleeping beauties from their anonymized text "
                 f"(it named {sens['decoy_false_recognition_rate'] if sens['decoy_false_recognition_rate'] is not None else 'n/a'} "
                 f"of decoys, as a comparison).")
        if len(clean):
            report.p(f"Without the remembered ones: {sens['clean_hits']} of {sens['n_clean']} hits "
                     f"({sens['clean_rate']:.1%}), p = {sens['clean_p']:.3g}.")
    if len(disg):
        from scipy.stats import wilcoxon
        diff = (disg.rank_disguised - disg.rank_original).to_numpy()
        try:
            pw = float(wilcoxon(diff, alternative="greater").pvalue) if np.any(diff != 0) else 1.0
        except ValueError:
            pw = float("nan")
        summary["disguise"] = {"n": int(len(disg)), "mean_rank_original": float(disg.rank_original.mean()),
                               "mean_rank_disguised": float(disg.rank_disguised.mean()),
                               "share_worse_when_disguised": float(np.mean(diff > 0)),
                               "wilcoxon_p_worse": pw}
        report.h2("Leakage check 2: does it still find the paper when the text is disguised?")
        report.p(f"For the {len(disg)} items where the sleeping beauty reached the search top "
                 f"{b['disguise_top_k']}, every one of those {b['disguise_top_k']} texts was rewritten by a "
                 f"different AI model and re-ranked. Mean position of the sleeping beauty: "
                 f"{disg.rank_original.mean():.1f} with original text, {disg.rank_disguised.mean():.1f} disguised "
                 f"(one-sided Wilcoxon p = {pw:.3g} for 'worse when disguised'). A large drop would suggest "
                 f"the AI recognizes wording rather than ideas.")
    report.h2("Leakage check 3: prompt leak scan")
    report.p(f"Every text shown to a model was scanned for years, DOIs, links, IDs, author names and study words. "
             f"Leaks found: {len(leaks)}" + (f" ({summary['leaks_by_type']})." if len(leaks) else "."))
    if "rank_raw_hybrid" in usable.columns:
        report.h2("Sensitivity: raw abstracts instead of the AI-written need")
        report.table(method_table(usable, ["raw_bm25", "raw_dense", "raw_hybrid"], b["report_k"], cfg))
    fig, ax = plt.subplots(figsize=(7, 4))
    ks = np.arange(1, int(usable.n_candidates.max()) + 1)
    for m in METHODS:
        rr = usable[f"rank_{m}"].to_numpy()
        ax.plot(ks, [(rr <= kk).mean() for kk in ks], label=m)
    ax.axvline(k, ls="--", c="grey", lw=1)
    ax.set_xscale("log")
    ax.set_xlabel("k (top-k cutoff, log scale)")
    ax.set_ylabel("share of sleeping beauties found")
    ax.legend(frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
    report.figure(fig, "backtest_hit_at_k", f"Hit@k for each method; dashed line = preregistered k = {k}.")
    plt.close(fig)
    report.h2("Item-level results")
    show = ["sb", "sb_year", "awakening_year", "B", "field", "waking_topic", "n_candidates",
            "rank_random", "rank_bm25", "rank_dense", "rank_hybrid", "rank_engine", "memorized"]
    report.table(usable[[c for c in show if c in usable.columns]])
    backends = usable.embedding_backend.unique().tolist()
    summary["embedding_backends"] = backends
    if any("tfidf" in x for x in backends):
        run.notes.append("Embedding fallback to TF-IDF was used (sentence-transformers unavailable).")
    return summary
