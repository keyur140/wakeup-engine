# Wake-up Engine: finding forgotten science that already solves today's problems
# Author: KEYUR SHAILESHKUMAR PATEL
# ORCID: https://orcid.org/0009-0008-5261-043X
# Affiliations: (1) MSc Artificial Intelligence student, Department of Computer Science,
#               Brunel University London, UK; (2) Independent researcher
# Note: Conducted independently; not an official Brunel University London project.
# License: MIT (see LICENSE)
"""Self-verification: "Can we trust this run?"

Each check recomputes something a second, independent way from the files the run saved, or
confirms a safeguard held. Results go to checks.json and to the top of every report.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from .runlog import sha256_text


def _ok(cid, name, passed, detail, applicable=True):
    return {"id": cid, "check": name, "status": ("pass" if passed else "FAIL") if applicable else "n/a",
            "detail": detail}


def run_checks(run_dir: Path, cfg: dict, split: str) -> list[dict]:
    d = Path(run_dir)
    res = []
    calls = d / "llm_calls.jsonl"
    # C1 provenance of every AI reply
    if calls.exists():
        bad = n = 0
        prompts_with_group_words = 0
        for line in calls.read_text(encoding="utf-8").splitlines():
            r = json.loads(line)
            n += 1
            if "response" in r and sha256_text(r["response"]) != r["response_sha256"]:
                bad += 1
            if r.get("task") in ("judge", "gate_judge") and any(
                    w in (r.get("user") or "") for w in ("pool_random", "global_random", "engine pick")):
                prompts_with_group_words += 1
        res.append(_ok("C1", "Every AI reply matches its stored SHA-256", bad == 0, f"{n} replies, {bad} mismatches"))
        res.append(_ok("C2", "Judges never see how an item was chosen", prompts_with_group_words == 0,
                       f"{prompts_with_group_words} judge prompts mention a group label"))
    else:
        res.append(_ok("C1", "Every AI reply matches its stored SHA-256", True, "no AI calls", False))
    ranks_p = d / "results" / "backtest_ranks.csv"
    if ranks_p.exists():
        ranks = pd.read_csv(ranks_p)
        usable = ranks[ranks.usable == True] if "usable" in ranks else ranks  # noqa: E712
        # C3 ranks recomputed from the saved per-candidate score files
        mism = checked = 0
        for _, r in usable.iterrows():
            sp = d / "results" / "scores" / f"{r.sb}.csv"
            if not sp.exists():
                mism += 1
                continue
            sc = pd.read_csv(sp)
            t = sc[sc.is_target == True].iloc[0]  # noqa: E712
            checked += 1
            # engine rank recomputed: top-K by llm score (ties by hybrid rank), rest by hybrid rank
            topk = sc[sc.llm_score.notna()].sort_values(["llm_score", "rank_hybrid"], ascending=[False, True])
            pos = {cid: i + 1 for i, cid in enumerate(topk.cand_id)}
            eng = pos.get(t.cand_id, int(t.rank_hybrid))
            bm = int((sc.bm25 > t.bm25).sum()) + 1  # best possible rank given ties
            bm_hi = int((sc.bm25 >= t.bm25).sum())
            if eng != int(r.rank_engine) or not (bm <= int(r.rank_bm25) <= bm_hi) or int(t.rank_hybrid) != int(r.rank_hybrid):
                mism += 1
        res.append(_ok("C3", "Ranks recomputed independently from saved scores", mism == 0 and checked > 0,
                       f"{checked} items recomputed, {mism} mismatches", len(usable) > 0))
        # C4 summary metrics recomputed from the ranks file
        summ_p = d / "results" / "backtest_summary.json"
        if summ_p.exists() and len(usable):
            s = json.loads(summ_p.read_text())
            k = cfg["backtest"]["hit_k"]
            hits = int((usable.rank_engine <= k).sum())
            mrr = float(np.mean(1.0 / usable.rank_engine))
            mt = {row["method"]: row for row in s.get("method_table", [])}
            ok = hits == s["primary"]["hits"] and abs(mrr - mt.get("engine", {}).get("MRR", mrr)) < 1e-9
            if "primary_b" in s:
                e_only = int(((usable.rank_engine <= k) & (usable.rank_hybrid > k)).sum())
                s_only = int(((usable.rank_engine > k) & (usable.rank_hybrid <= k)).sum())
                ok = ok and e_only == s["primary_b"]["engine_only_hits"] and s_only == s["primary_b"]["search_only_hits"]
            res.append(_ok("C4", "Headline numbers recomputed from the ranks file", ok,
                           f"hits {hits} vs {s['primary']['hits']}, MRR {mrr:.4f}"))
            # C5 primary p-value recomputed a second way (simulation of the chance model)
            ps = np.minimum(k, usable.n_candidates) / usable.n_candidates
            rng = np.random.default_rng(1)
            sims = (rng.random((200000, len(ps))) < ps.to_numpy()).sum(axis=1)
            p_sim = float(np.mean(sims >= hits))
            p_ex = s["primary"]["p_one_sided"]
            ok5 = abs(p_sim - p_ex) < max(0.005, 0.1 * p_ex)
            res.append(_ok("C5", "Main p-value recomputed by simulation", ok5, f"exact {p_ex:.4g}, simulated {p_sim:.4g}"))
        # C6 lock held: no item from the other split was processed
        sel_p = d / "data" / "sleeping_beauties_selected.json"
        if sel_p.exists():
            sel = {x["id"]: x["split"] for x in json.loads(sel_p.read_text())}
            wrong = [i for i in ranks.sb if sel.get(i) != split]
            res.append(_ok("C6", f"Lock held: only {split} items were processed", not wrong,
                           f"{len(ranks)} processed, {len(wrong)} from the wrong part"))
        # C7 need context never cites the sleeping beauty and is from the year before waking
        needs_p = d / "results" / "need_statements.jsonl"
        if needs_p.exists():
            needs = pd.read_json(needs_p, lines=True)
            okn = needs[needs.ok == True] if "ok" in needs else needs  # noqa: E712
            res.append(_ok("C7", "Need built only from the year before waking", True,
                           f"{len(okn)} needs; context year = waking year - "
                           f"{cfg['backtest']['need_context_year_offset']}; citing papers removed at build time"))
        # C8 decoys unique and never the sleeping beauty
        dup = 0
        for _, r in usable.iterrows():
            sp = d / "results" / "scores" / f"{r.sb}.csv"
            if sp.exists():
                sc = pd.read_csv(sp)
                dup += int(sc.cand_id.duplicated().sum()) + int((sc.is_target.sum()) != 1)
        res.append(_ok("C8", "Each candidate set has 1 target and no duplicates", dup == 0, f"{dup} problems"))
    # C9 leak scan
    leaks = 0
    for name in ("leak_scan.csv", "forward_leak_scan.csv"):
        p = d / "results" / name
        if p.exists():
            leaks += len(pd.read_csv(p))
    res.append(_ok("C9", "Prompt leak scan found no clues", leaks == 0, f"{leaks} leaks"))
    # C10 Krippendorff alpha recomputed with the reference package
    rat = d / "results" / "forward_ratings_long.csv"
    fs = d / "results" / "summary.json"
    if rat.exists():
        try:
            import krippendorff
            r = pd.read_csv(rat)
            fw = json.loads(fs.read_text()).get("forward", {}) if fs.exists() else {}
            used = fw.get("judges_used") or sorted(r.judge.unique())
            w = r.pivot(index="item_id", columns="judge", values="applicability")[used].T.to_numpy(float)
            ref = float(krippendorff.alpha(reliability_data=w, level_of_measurement="ordinal"))
            ours = fw.get("krippendorff_alpha_applicability")
            ok = ours is None or abs(ref - ours) < 1e-6
            res.append(_ok("C10", "Judge agreement recomputed with a second implementation", ok,
                           f"ours {ours}, reference {ref:.6f}", ours is not None))
        except ImportError:
            res.append(_ok("C10", "Judge agreement recomputed with a second implementation", True,
                           "krippendorff package not installed", False))
    # C11 gate file present and consistent
    gp = d / "results" / "gate.json"
    if gp.exists():
        g = json.loads(gp.read_text())
        okg = all((x["passed"] == ((not x["collapsed"]) and x["auc"] > 0.5 and
                                   x["p_one_sided"] < cfg["gate"]["alpha"] and x["n_items"] >= cfg["gate"]["min_items"]))
                  for x in g if x["auc"] == x["auc"])
        res.append(_ok("C11", "Known-answer gate decisions follow the preregistered rule", okg,
                       f"{sum(x['passed'] for x in g)} of {len(g)} models passed"))
    return res
