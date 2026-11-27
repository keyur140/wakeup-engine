#!/usr/bin/env python3
# Wake-up Engine: finding forgotten science that already solves today's problems
# Author: KEYUR SHAILESHKUMAR PATEL
# ORCID: https://orcid.org/0009-0008-5261-043X
# Affiliations: (1) MSc Artificial Intelligence student, Department of Computer Science,
#               Brunel University London, UK; (2) Independent researcher
# Note: Conducted independently; not an official Brunel University London project.
# License: MIT (see LICENSE)
"""Wake-up Engine command line (v0.2).

Order of use:
  1. python run.py selftest              offline test of the whole pipeline on synthetic data (no keys)
  2. python run.py validate              synthetic worlds with known answers -> validation PDF (no keys)
  3. python run.py explore               EXPLORATORY run on real data: development sleeping beauties (20%),
                                         known-answer gate, 4 practice problems, checks, exploratory PDF
  4. python run.py freeze --from-run runs/<explore run>
                                         copy the sleeping-beauty sample and gate decisions into prereg/
                                         and hash every preregistered file. Upload to OSF after this.
  5. python run.py confirm               CONFIRMATORY run: locked 80% + the 20 preregistered problems.
                                         Refuses to run unless the files match the freeze.

Other:
  python run.py verify runs/<id>         re-check every SHA-256 and re-run the self-checks
  python run.py drift-check runs/<id>    re-ask a sample of recorded AI calls and compare answers

Options: --config path/to/study.yaml   --limit N (pilot: only N items / problems, logged as a deviation)
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import shutil
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from wakeup.meta import AI_USE_STATEMENT, AUTHOR  # noqa: E402
from wakeup.runlog import (Run, check_against_freeze, compute_prereg_hashes, load_config,  # noqa: E402
                           sha256_file, sha256_json, sha256_text, utcnow)

FROZEN_SAMPLE = ROOT / "prereg" / "frozen_sample.json"
FROZEN_GATE = ROOT / "prereg" / "gate_frozen.json"


def load_env(path: Path) -> None:
    """Minimal .env reader (KEY=VALUE lines). Values are never written to logs."""
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def mock_config(cfg: dict) -> dict:
    """Smaller sizes for the synthetic world. Mock runs are labelled and never count as results."""
    c = copy.deepcopy(cfg)
    c["backtest"].update(candidate_pool_size=2500, n_sleeping_beauties=40, min_usable=5, min_usable_dev=5,
                         n_candidates=100, min_decoys=60, rerank_top_k=20, disguise_top_k=10,
                         min_awakening_year=1920, dev_fraction=0.5)
    c["forward"].update(results_per_query=60, rerank_top_k=15)
    c["stats"].update(bootstrap_iterations=500, permutation_iterations=1000)
    c["gate"].update(permutation_iterations=1000, min_items=5)
    c["embeddings"]["force_tfidf"] = True
    return c


def apply_limit(cfg: dict, limit: int | None, run=None) -> dict:
    if not limit:
        return cfg
    c = copy.deepcopy(cfg)
    c["backtest"]["n_sleeping_beauties"] = limit
    c["forward"]["limit_problems"] = limit
    return c


# ----------------------------------------------------------------------------- pipeline
def pipeline(cfg: dict, run, mode: str, mock: bool, oa=None, frozen_sample=None, frozen_gate=None,
             title_extra: str = "") -> dict:
    """mode 'explore' = development part + practice problems; 'confirm' = locked part + 20 problems."""
    from wakeup.backtest import run_backtest
    from wakeup.checks import run_checks
    from wakeup.forward import run_forward
    from wakeup.gate import gate_items, run_gate
    from wakeup.llm import make_judges, make_llm
    from wakeup.report import Report

    split = "dev" if mode == "explore" else "confirm"
    label = "exploratory" if mode == "explore" else "confirmatory"
    if oa is None:
        if mock:
            from wakeup.mock import MockOpenAlex
            oa = MockOpenAlex(seed=cfg["seed"], n_beauties=cfg["backtest"]["n_sleeping_beauties"])
        else:
            from wakeup.openalex import OpenAlex
            oa = OpenAlex(cfg, run)
    engine = make_llm(cfg, "engine", run, mock)
    para = make_llm(cfg, "paraphraser", run, mock) if cfg["backtest"].get("disguise_check") else None
    judges = make_judges(cfg, run, mock)
    report = Report(run, f"Wake-up Engine {label} results" + (" (SYNTHETIC DATA)" if mock else "") + title_extra)
    summary: dict = {"mode": mode, "split": split, "mock": mock}

    bt = run_backtest(oa, engine, cfg, run, report, split=split, paraphraser=para, frozen_sample=frozen_sample)
    summary["backtest"] = bt["summary"]

    if mode == "explore":
        sets = gate_items(bt["gate_inputs"], cfg)
        models = [("engine", engine, "engine")] + [(j.name, j, "judge") for j in judges]
        gate = run_gate(models, sets, cfg, run)
        run.write_json("results/gate.json", gate)
        report.h2("Known-answer gate (development items)")
        import pandas as pd
        report.table(pd.DataFrame(gate))
    else:
        gate = frozen_gate
        run.write_json("results/gate.json", gate)
        report.h2("Known-answer gate (frozen from the exploratory run)")
        import pandas as pd
        report.table(pd.DataFrame(gate))

    pf = cfg["forward"]["dev_problems_file"] if mode == "explore" else cfg["forward"]["problems_file"]
    summary["forward"] = run_forward(oa, engine, judges, cfg, run, report, problems_file=pf, gate=gate, label=label)
    run.write_json("results/summary.json", summary)

    checks = run_checks(run.dir, cfg, split)
    run.write_json("checks.json", checks)
    report.h2("Self-checks")
    import pandas as pd
    report.table(pd.DataFrame(checks))
    report.h2("Run notes and deviations")
    report.bullets(run.notes or ["none"])
    report.save()
    from wakeup.report import write_data_card
    write_data_card(run, "results",
                    f"Outputs of a Wake-up Engine {label} run ({split} part of the sleeping beauties).",
                    {"data/": "sleeping-beauty screening, selection and split (locked titles blanked)",
                     "results/": "ranks, per-candidate scores, gate, ratings, tests, leak scans (CSV/JSON)",
                     "checks.json": "self-verification results",
                     "llm_calls.jsonl": "every model call with prompt and response hashes",
                     "*.pdf / report.md / report.html": "human-readable reports"},
                    ["Synthetic mock world" if mock else "OpenAlex (CC0), https://openalex.org"])
    summary["checks"] = {"passed": sum(c["status"] == "pass" for c in checks),
                         "failed": sum(c["status"] == "FAIL" for c in checks),
                         "n_a": sum(c["status"] == "n/a" for c in checks)}
    return summary


def _finish(run, status, summary, pdf_kind=None, extra_sections=None):
    pdf = None
    if pdf_kind and status == "completed":
        try:
            from wakeup.pdfreport import build_pdf
            pdf = build_pdf(run, pdf_kind, extra_sections)
            run.log.info("PDF report: %s", pdf.name)
        except Exception as e:
            run.log.error("PDF build failed: %s\n%s", e, traceback.format_exc())
            run.notes.append(f"PDF build failed: {e}")
    mp = run.finish(status, {"summary": summary})
    print(f"\nRun folder: {run.dir}\nManifest: {mp}" + (f"\nPDF: {pdf}" if pdf else ""))
    return pdf


def cmd_explore(args, mock: bool) -> int:
    cfg = load_config(args.config)
    if mock:
        cfg = mock_config(cfg)
    cfg = apply_limit(cfg, args.limit)
    name = "selftest" if mock else "explore"
    run = Run(name + (f"_pilot{args.limit}" if args.limit else ""), cfg, mock=mock)
    run.notes.append("EXPLORATORY run: development sleeping beauties and practice problems only. "
                     "Not the preregistered test.")
    if args.limit:
        run.notes.append(f"PILOT: limited to {args.limit} items/problems.")
    status, summary = "completed", {}
    try:
        summary = pipeline(cfg, run, "explore", mock)
    except Exception as e:
        status = "failed"
        run.log.error("Run failed: %s\n%s", e, traceback.format_exc())
        run.notes.append(f"FAILED: {e}")
    _finish(run, status, summary, "exploratory")
    return 0 if status == "completed" else 1


def cmd_confirm(args) -> int:
    cfg = load_config(args.config)
    pre = check_against_freeze()
    missing = [p.name for p in (FROZEN_SAMPLE, FROZEN_GATE) if not p.exists()]
    if missing or pre["status"] != "MATCHES_FREEZE":
        print("REFUSED: the confirmatory run needs a frozen study.\n"
              f"  preregistration status: {pre['status']}\n"
              f"  missing frozen files: {missing or 'none'}\n"
              f"  changed files: {pre.get('changed_files') or 'none'}; added: {pre.get('added_files') or 'none'}\n"
              "Run `python run.py explore`, then `python run.py freeze --from-run runs/<explore run>`.")
        return 3
    if args.limit:
        print("REFUSED: --limit is not allowed for the confirmatory run.")
        return 3
    run = Run("confirm", cfg, mock=False)
    status, summary = "completed", {}
    try:
        summary = pipeline(cfg, run, "confirm", False, frozen_sample=json.loads(FROZEN_SAMPLE.read_text()),
                           frozen_gate=json.loads(FROZEN_GATE.read_text()))
    except Exception as e:
        status = "failed"
        run.log.error("Run failed: %s\n%s", e, traceback.format_exc())
        run.notes.append(f"FAILED: {e}")
    _finish(run, status, summary, "confirmatory")
    return 0 if status == "completed" else 1


# ----------------------------------------------------------------------------- validation
WORLDS = [
    {"id": "W1", "name": "Signal world",
     "story": "The need really points to the planted sleeping beauty; the engine reads honestly. Judges: two useful, one random.",
     "signal": True, "engine": "signal", "judges": ["signal", "signal", "null"],
     "expect": {"H1a beats chance": True, "engine passes gate": True, "judges passing gate": "2 (the random one fails)",
                "forward testable": True, "engine beats random picks (H2)": "either", "big drop when disguised": False,
                "recognition probe flags items": False, "engine adds value over search": "either"}},
    {"id": "W2", "name": "Null world",
     "story": "The need carries no clue about the sleeping beauty and the engine scores at random. One judge gives "
              "every item the same score.",
     "signal": False, "bridge": False, "engine": "null", "judges": ["null", "null", "collapse"],
     "expect": {"H1a beats chance": False, "engine passes gate": False, "judges passing gate": "0",
                "forward testable": False, "engine beats random picks (H2)": False, "big drop when disguised": False,
                "engine adds value over search": False}},
    {"id": "W4", "name": "Word-overlap world",
     "story": "The need carries no real clue, but the sleeping beauty happens to share a few everyday words with the "
              "field that later woke it. The engine scores at random. Plain word search can then beat chance with "
              "no reasoning at all. This world shows why 'beats chance' alone is not enough.",
     "signal": False, "bridge": True, "engine": "null", "judges": ["signal", "signal", "signal"],
     "expect": {"H1a beats chance": "either", "engine adds value over search": False, "engine passes gate": "either"}},
    {"id": "W3", "name": "Memorizer world",
     "story": "The engine does not read for meaning; it recognizes planted papers by a hidden identity word, like a "
              "model that has memorized famous papers.",
     "signal": True, "engine": "memorizer", "judges": ["signal", "signal", "signal"],
     "expect": {"H1a beats chance": True, "engine passes gate": True, "judges passing gate": "3",
                "forward testable": True, "engine beats random picks (H2)": "either",
                "big drop when disguised": True, "recognition probe flags items": True}},
]


def _observed(s: dict, gate: list) -> dict:
    bt, fw = s.get("backtest", {}), s.get("forward", {})
    pr = bt.get("primary") or {}
    eng = next((g for g in gate if g["model_name"] == "engine"), {})
    jpass = sum(g["passed"] for g in gate if g["role"] == "judge")
    h2 = (fw.get("tests") or {}).get("H2_engine_vs_pool_random", {})
    dg = bt.get("disguise") or {}
    sm = bt.get("sensitivity_memorization") or {}
    eh = (bt.get("secondary") or {}).get("engine_vs_hybrid")
    return {"H1a beats chance": bool(pr.get("supported")), "engine passes gate": bool(eng.get("passed")),
            "judges passing gate": str(jpass), "forward testable": bool(fw.get("testable")),
            "engine beats random picks (H2)": bool(h2.get("p_holm", 1) < 0.05) if h2 else False,
            "big drop when disguised": bool(dg and dg.get("wilcoxon_p_worse", 1) < 0.05
                                            and dg.get("mean_rank_disguised", 0) > 2 * dg.get("mean_rank_original", 1)),
            "recognition probe flags items": bool(sm.get("n_memorized", 0) > 0),
            "engine adds value over search": bool((bt.get("primary_b") or {}).get("supported")),
            "_hits": f"{pr.get('hits', 'n/a')}/{pr.get('n', 'n/a')}", "_p": pr.get("p_one_sided"),
            "_engine_auc": eng.get("auc"), "_disguise": (dg.get("mean_rank_original"), dg.get("mean_rank_disguised")),
            "_memorized": sm.get("n_memorized"),
            "_vs_search": (f"engine-only hits {eh['a_only']}, search-only hits {eh['b_only']}, Holm p "
                           f"{eh['p_holm']:.3g}" if eh else "n/a")}


def _match(exp, obs):
    if exp == "either":
        return True
    if isinstance(exp, str):
        return exp.split(" ")[0] == str(obs)
    return bool(exp) == bool(obs)


def cmd_validate(args) -> int:
    from wakeup.mock import MockOpenAlex
    from wakeup.split import item_seed
    base = mock_config(load_config(args.config))
    parent = Run("validate", base, mock=True)
    parent.notes.append("SYNTHETIC VALIDATION: no real data. Tests the machinery, not science.")
    status, rows, subs, obs_all = "completed", [], [], {}
    try:
        for w in WORLDS:
            cfg = copy.deepcopy(base)
            cfg["mock"] = {"engine_behaviour": w["engine"], "memorization_behaviour": w["engine"],
                           "paraphraser_behaviour": "signal", "judge_behaviours": w["judges"]}
            sub = Run(f"world_{w['id']}", cfg, mock=True, runs_dir=parent.dir / "worlds")
            oa = MockOpenAlex(seed=cfg["seed"], n_beauties=cfg["backtest"]["n_sleeping_beauties"], signal=w["signal"],
                              bridge=w.get("bridge"))
            s = pipeline(cfg, sub, "explore", True, oa=oa, title_extra=f" - {w['id']} {w['name']}")
            gate = json.loads((sub.dir / "results" / "gate.json").read_text())
            o = _observed(s, gate)
            obs_all[w["id"]] = {"summary_checks": s.get("checks"), **o}
            for k, e in w["expect"].items():
                rows.append({"world": w["id"], "property": k, "expected": str(e), "observed": str(o.get(k)),
                             "as_expected": _match(e, o.get(k))})
            subs.append((w, sub, s, o))
        # lock test: confirmatory pipeline on W1's frozen sample must touch only locked items
        w1 = subs[0][1]
        cfg = copy.deepcopy(subs[0][1].config)
        lock = Run("world_W1_confirm_locktest", cfg, mock=True, runs_dir=parent.dir / "worlds")
        sample = json.loads((w1.dir / "data" / "sample_for_freeze.json").read_text())
        gate = json.loads((w1.dir / "results" / "gate.json").read_text())
        oa = MockOpenAlex(seed=cfg["seed"], n_beauties=cfg["backtest"]["n_sleeping_beauties"], signal=True)
        s = pipeline(cfg, lock, "confirm", True, oa=oa, frozen_sample=sample, frozen_gate=gate,
                     title_extra=" - lock test")
        ck = {c["id"]: c for c in json.loads((lock.dir / "checks.json").read_text())}
        rows.append({"world": "W1-lock", "property": "confirm run touches only locked items",
                     "expected": "True", "observed": str(ck.get("C6", {}).get("status") == "pass"),
                     "as_expected": ck.get("C6", {}).get("status") == "pass"})
        subs.append(({"id": "W1-lock"}, lock, s, None))
        # false-positive rate: the null world over many seeds
        n_seeds = args.null_seeds
        fp = 0
        fp_rows = []
        for i in range(n_seeds):
            cfg = copy.deepcopy(base)
            cfg["seed"] = item_seed(base["seed"], "null-seed", str(i)) % 10 ** 8
            cfg["mock"] = {"engine_behaviour": "null", "memorization_behaviour": "null",
                           "paraphraser_behaviour": "signal", "judge_behaviours": ["null", "null", "null"]}
            cfg["backtest"]["disguise_check"] = False
            cfg["backtest"]["memorization_check"] = False
            r = _quiet_backtest(cfg, parent, i)
            fp_rows.append(r)
            fp += bool(r["supported"])
        parent.write_json("results/null_world_false_positives.json", fp_rows)
        rows.append({"world": "W2 x seeds", "property": f"H1a false-positive rate (unadjusted p < 0.05) over {n_seeds} null worlds",
                     "expected": "<= about 5%", "observed": f"{fp}/{n_seeds}",
                     "as_expected": fp / max(n_seeds, 1) <= 0.10})
        import pandas as pd
        pd.DataFrame(rows).to_csv(parent.path("results", "validation_expected_vs_observed.csv"), index=False)
        parent.write_json("results/validation_observed.json", obs_all)
        # summary.json and checks of W1 are the detailed example in the PDF
        for f in ("results/summary.json", "results/gate.json", "checks.json"):
            shutil.copy(w1.dir / f, parent.path(f))
        for fig in (w1.dir / "figures").glob("*.png"):
            shutil.copy(fig, parent.path("figures", fig.name))
        for f in ("results/forward_items_scored.csv",):
            if (w1.dir / f).exists():
                shutil.copy(w1.dir / f, parent.path(f))
        extra = _validation_sections(rows, subs, fp_rows)
    except Exception as e:
        status = "failed"
        parent.log.error("Validation failed: %s\n%s", e, traceback.format_exc())
        parent.notes.append(f"FAILED: {e}")
        extra = None
    for _, sub, _, _ in subs:
        sub.finish("completed")
    _finish(parent, status, {"rows": rows}, "validation", extra)
    ok = status == "completed" and all(r["as_expected"] for r in rows)
    print("All validation expectations met." if ok else "Some validation expectations were NOT met (see the PDF).")
    return 0 if status == "completed" else 1


def _quiet_backtest(cfg, parent, i):
    """Back-test only, in a throwaway sub-run, for the false-positive estimate."""
    from wakeup.backtest import run_backtest
    from wakeup.llm import make_llm
    from wakeup.mock import MockOpenAlex
    from wakeup.report import Report
    import logging
    sub = Run(f"null_seed{i:02d}", cfg, mock=True, runs_dir=parent.dir / "null_seeds")
    for h in sub.log.handlers:
        if isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler):
            h.setLevel(logging.WARNING)
    oa = MockOpenAlex(seed=cfg["seed"], n_beauties=cfg["backtest"]["n_sleeping_beauties"], signal=False, bridge=False)
    bt = run_backtest(oa, make_llm(cfg, "engine", sub, True), cfg, sub, Report(sub, "null seed"), split="dev")
    pr = bt["summary"].get("primary") or {}
    sub.finish("completed")
    return {"seed": cfg["seed"], "hits": pr.get("hits"), "n": pr.get("n"), "p": pr.get("p_one_sided"),
            "supported": bool(pr.get("p_one_sided", 1) < 0.05)}


def _validation_sections(rows, subs, fp_rows):
    from reportlab.platypus import Spacer
    from wakeup.pdfreport import P, bullets, fmt, table
    from reportlab.lib.units import mm
    sec = [P("Validation worlds: expected vs observed", "h1"),
           P("Each world has a known truth. The test passes when the pipeline reports what that truth implies: "
             "signal when it is there, nothing when it is not, and a warning when the engine is cheating by memory.")]
    for w, sub, s, o in subs:
        if o is None:
            continue
        sec += [P(f"{w['id']}: {w['name']}", "h2"), P(w["story"]),
                P(f"Hits {o['_hits']} (p = {fmt(o['_p'])}); engine gate AUC {fmt(o['_engine_auc'])}; "
                  f"disguise mean rank original vs disguised {fmt(o['_disguise'][0])} vs {fmt(o['_disguise'][1])}; "
                  f"recognized by the probe: {fmt(o['_memorized'])}; engine vs search alone: {o['_vs_search']}. Self-checks: "
                  f"{s['checks']['passed']} pass, {s['checks']['failed']} fail, {s['checks']['n_a']} n/a.", "small")]
    sec.append(Spacer(1, 4))
    sec.append(table([["World", "Property", "Expected", "Observed", "OK?"]] +
                     [[r["world"], r["property"], r["expected"], r["observed"], "yes" if r["as_expected"] else "NO"]
                      for r in rows], widths=[18 * mm, 62 * mm, 34 * mm, 34 * mm, 14 * mm]))
    n_ok = sum(r["as_expected"] for r in rows)
    sec.append(P(f"<b>{n_ok} of {len(rows)} expectations met.</b> Sections 4 to 6 below show world W1 in full detail, "
                 "exactly as a real exploratory report would show real data.", "box"))
    sec += bullets([f"False-positive estimate: {sum(r['supported'] for r in fp_rows)} of {len(fp_rows)} null worlds gave "
                    "p below 0.05 for H1 (the expected rate is at most 5%)."])
    return [sec]


# ----------------------------------------------------------------------------- freeze / verify / drift
def cmd_freeze(args) -> int:
    if args.from_run:
        src = Path(args.from_run)
        need = {src / "data" / "sample_for_freeze.json": FROZEN_SAMPLE, src / "results" / "gate.json": FROZEN_GATE}
        miss = [str(p) for p in need if not p.exists()]
        if miss:
            print("Cannot freeze from that run; missing:", miss)
            return 2
        m = json.loads((src / "manifest.json").read_text()) if (src / "manifest.json").exists() else {}
        if m.get("mock_mode"):
            print("REFUSED: that run used synthetic (mock) data. Freeze from a real `explore` run.")
            return 2
        for a, b in need.items():
            shutil.copy(a, b)
        print(f"Copied the sleeping-beauty sample and gate decisions from {src.name} into prereg/.")
    hashes = compute_prereg_hashes()
    bundle = sha256_json(hashes)
    out = {"frozen_at": utcnow(), "author": AUTHOR, "ai_use_statement": AI_USE_STATEMENT,
           "instructions": "Upload this file, prereg/OSF_preregistration.md, prereg/frozen_sample.json and "
                           "prereg/gate_frozen.json to OSF. The bundle hash fingerprints every preregistered file "
                           "and all analysis code.",
           "from_exploratory_run": (Path(args.from_run).name if args.from_run else None),
           "from_run_manifest_sha256": (sha256_file(Path(args.from_run) / "manifest.json")
                                        if args.from_run and (Path(args.from_run) / "manifest.json").exists() else None),
           "bundle_sha256": bundle, "files": hashes}
    p = ROOT / "prereg" / "FREEZE_MANIFEST.json"
    p.write_text(json.dumps(out, indent=2))
    print(f"Frozen {len(hashes)} files. Bundle SHA-256: {bundle}\nWritten: {p}")
    if not FROZEN_SAMPLE.exists():
        print("NOTE: no frozen sample yet. `confirm` will refuse until you freeze --from-run an explore run.")
    return 0


def cmd_verify(args) -> int:
    d = Path(args.target)
    sums = d / "SHA256SUMS"
    if not sums.exists():
        print("No SHA256SUMS in", d)
        return 2
    bad = 0
    for line in sums.read_text().splitlines():
        h, name = line.split("  ", 1)
        f = d / name
        ok = f.exists() and sha256_file(f) == h
        bad += not ok
        if not ok:
            print("MISMATCH", name)
    print("All files verified." if not bad else f"{bad} file(s) failed verification.")
    cfgp, summ = d / "config_snapshot.yaml", d / "results" / "summary.json"
    if cfgp.exists() and summ.exists():
        import yaml
        from wakeup.checks import run_checks
        cfg = yaml.safe_load(cfgp.read_text())
        split = json.loads(summ.read_text()).get("split", "dev")
        checks = run_checks(d, cfg, split)
        for c in checks:
            print(f"  {c['id']:4s} {c['status']:5s} {c['check']}: {c['detail']}")
        bad += sum(c["status"] == "FAIL" for c in checks)
    return 0 if not bad else 1


def cmd_drift(args) -> int:
    """Re-ask up to N recorded calls with the cache bypassed; report how many answers changed."""
    from wakeup.llm import LLM
    d = Path(args.target)
    cfg = load_config(args.config)
    calls = [json.loads(x) for x in (d / "llm_calls.jsonl").read_text().splitlines()]
    calls = [c for c in calls if c.get("provider") != "mock" and c.get("response") is not None]
    if not calls:
        print("No real AI calls recorded in that run.")
        return 2
    import random
    random.Random(cfg["seed"]).shuffle(calls)
    calls = calls[:args.n]
    run = Run("drift_check", cfg)
    rows, models = [], {}
    for c in calls:
        key = (c["provider"], c["model"])
        if key not in models:
            models[key] = LLM(cfg, c["provider"], c["model"], run, name=c.get("role_name", "drift"))
        new = models[key].chat(c["system"], c["user"], task=c["task"] + "_drift", meta=c.get("meta"),
                               bypass_cache=True)
        rows.append({"task": c["task"], "model": c["model"], "same": sha256_text(new) == c["response_sha256"]})
    same = sum(r["same"] for r in rows)
    run.write_json("results/drift_check.json", {"source_run": d.name, "n": len(rows), "identical": same, "rows": rows})
    run.log.info("Drift check: %d of %d answers identical to the recorded ones", same, len(rows))
    run.finish("completed", {"identical": same, "n": len(rows)})
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["selftest", "validate", "explore", "freeze", "confirm", "verify",
                                        "verify-run", "drift-check", "backtest", "forward", "all"])
    ap.add_argument("target", nargs="?", help="run folder for verify / drift-check")
    ap.add_argument("--config", default=None)
    ap.add_argument("--limit", type=int, default=None, help="pilot: only first N items")
    ap.add_argument("--from-run", default=None, help="freeze: exploratory run folder to take the sample from")
    ap.add_argument("--n", type=int, default=20, help="drift-check: number of calls to re-ask")
    ap.add_argument("--null-seeds", type=int, default=20, help="validate: number of null worlds")
    args = ap.parse_args()
    load_env(ROOT / ".env")
    if args.command in ("backtest", "forward", "all"):
        print("In v0.2 the preregistered analysis is one command: `python run.py confirm` "
              "(back-test on the locked part + forward test). Use `explore` for the exploratory run.")
        return 2
    if args.command == "freeze":
        return cmd_freeze(args)
    if args.command in ("verify", "verify-run", "drift-check"):
        if not args.target:
            ap.error(f"{args.command} needs a run folder")
        return cmd_drift(args) if args.command == "drift-check" else cmd_verify(args)
    if args.command == "validate":
        return cmd_validate(args)
    if args.command == "confirm":
        return cmd_confirm(args)
    return cmd_explore(args, mock=args.command == "selftest")


if __name__ == "__main__":
    sys.exit(main())
