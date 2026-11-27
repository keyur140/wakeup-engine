# Wake-up Engine: finding forgotten science that already solves today's problems
# Author: KEYUR SHAILESHKUMAR PATEL
# ORCID: https://orcid.org/0009-0008-5261-043X
# Affiliations: (1) MSc Artificial Intelligence student, Department of Computer Science,
#               Brunel University London, UK; (2) Independent researcher
# Note: Conducted independently; not an official Brunel University London project.
# License: MIT (see LICENSE)
"""Tests for the v0.2 safeguards: split, gate, collapse, leak scan, one-sided McNemar, MDE."""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from wakeup.gate import auc_and_p, collapse_share  # noqa: E402
from wakeup.leakscan import scan  # noqa: E402
from wakeup.split import assign, item_seed  # noqa: E402
from wakeup.stats import mcnemar_one_sided, mde_binomial  # noqa: E402


def test_split_is_stable_and_near_target():
    ids = [f"W{i}" for i in range(20000)]
    a = [assign(i, 20261026, 0.2) for i in ids]
    assert a == [assign(i, 20261026, 0.2) for i in ids]
    share = a.count("dev") / len(a)
    assert 0.19 < share < 0.21
    assert a != [assign(i, 1, 0.2) for i in ids]


def test_item_seed_independent_of_order():
    assert item_seed(1, "rank", "W5") == item_seed(1, "rank", "W5")
    assert item_seed(1, "rank", "W5") != item_seed(1, "rank", "W6")


def test_gate_auc_perfect_and_random():
    good = [[9, 1, 2, 3, 1, 2] for _ in range(15)]
    auc, p, n = auc_and_p(good, 2000, 1)
    assert auc == 1.0 and p < 0.01 and n == 15
    rng = np.random.default_rng(0)
    rnd = [list(rng.random(6)) for _ in range(15)]
    auc2, p2, _ = auc_and_p(rnd, 2000, 1)
    assert p2 > 0.01


def test_gate_ties_count_half_and_nan_dropped():
    auc, _, n = auc_and_p([[3, 3, 3], [float("nan"), 1, 2]], 100, 1)
    assert auc == 0.5 and n == 1


def test_collapse_share():
    assert collapse_share([3, 3, 3, 3, 4]) == 0.8
    assert collapse_share([3] * 20) == 1.0


def test_leak_scan_finds_clues():
    found = scan("Smith et al. (1954) doi:10.1000/xyz https://x.org W2741809807 a sleeping beauty", ["John Smith"])
    for k in ("year", "doi", "url", "openalex_id", "et_al", "study_words", "author_name"):
        assert k in found, (k, found)
    assert scan("Adsorption of dyes on charcoal surfaces was measured.") == []


def test_mcnemar_one_sided():
    a = np.array([1] * 8 + [0] * 2 + [1] * 10, bool)
    b = np.array([0] * 8 + [1] * 2 + [1] * 10, bool)
    r = mcnemar_one_sided(a, b)
    assert r["a_only"] == 8 and r["b_only"] == 2
    assert abs(r["p_one_sided"] - 0.0546875) < 1e-9


def test_mde_matches_prereg_numbers():
    assert abs(mde_binomial(50, 0.01, 0.05, 0.8) - 0.0836) < 0.002
    assert abs(mde_binomial(80, 0.01, 0.05, 0.8) - 0.0527) < 0.002


def test_excluded_before_registration_is_skipped_before_any_call(tmp_path):
    """D20 / ISSUES I21: an author-excluded item gets no OpenAlex or model call and is reported as excluded."""
    import copy
    import json
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from run import mock_config
    from wakeup.backtest import run_backtest
    from wakeup.llm import make_llm
    from wakeup.mock import MockOpenAlex
    from wakeup.report import Report
    from wakeup.runlog import Run, load_config
    cfg = mock_config(load_config())
    cfg["backtest"].update(n_sleeping_beauties=12)
    oa = MockOpenAlex(seed=cfg["seed"], n_beauties=12, signal=True)
    first = Run("excl_a", copy.deepcopy(cfg), mock=True, runs_dir=tmp_path)
    run_backtest(oa, make_llm(cfg, "engine", first, True), cfg, first, Report(first, "a"), split="dev")
    sample = json.loads((first.dir / "data" / "sample_for_freeze.json").read_text())
    target = [s["id"] for s in sample if s["split"] == "confirm"][0]
    cfg["backtest"]["excluded_before_registration"] = [target]
    second = Run("excl_b", cfg, mock=True, runs_dir=tmp_path)
    run_backtest(oa, make_llm(cfg, "engine", second, True), cfg, second, Report(second, "b"),
                 split="confirm", frozen_sample=sample)
    calls = (second.dir / "llm_calls.jsonl").read_text() if (second.dir / "llm_calls.jsonl").exists() else ""
    assert target not in calls
    assert "excluded_before_registration" in (second.dir / "run.log").read_text()
