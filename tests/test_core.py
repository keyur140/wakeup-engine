# Wake-up Engine: finding forgotten science that already solves today's problems
# Author: KEYUR SHAILESHKUMAR PATEL
# ORCID: https://orcid.org/0009-0008-5261-043X
# Affiliations: (1) MSc Artificial Intelligence student, Department of Computer Science,
#               Brunel University London, UK; (2) Independent researcher
# Note: Conducted independently; not an official Brunel University London project.
# License: MIT (see LICENSE)
"""Unit tests for the statistical and integrity core. Run: python -m pytest -q"""
import json
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from wakeup.beauty import beauty_coefficient
from wakeup.llm import parse_json
from wakeup.stats import (binom_greater, krippendorff_alpha, mcnemar_exact,
                          poisson_binomial_greater, stratified_permutation_test, wilson_ci)
from wakeup.textutil import anonymize


def test_beauty_flat_then_spike_is_high():
    series = [0] * 40 + [5, 20, 50, 80]
    b = beauty_coefficient(series, 1920)
    assert b.B > 100
    assert b.t_m == 43
    assert 38 <= b.t_a <= 42          # wakes at the end of the flat period
    assert b.awakening_year == 1920 + b.t_a


def test_beauty_early_peak_is_low():
    series = [10, 40, 30, 20, 10, 5, 2, 1]
    b = beauty_coefficient(series, 1950)
    assert b.B <= 0 + 1e-9 or b.t_m == 1


def test_beauty_linear_growth_is_zero():
    series = list(range(0, 21))
    assert abs(beauty_coefficient(series, 1900).B) < 1e-9


def test_krippendorff_matches_reference_package():
    kd = pytest.importorskip("krippendorff")
    rng = np.random.default_rng(0)
    truth = rng.integers(1, 6, size=60)
    data = np.vstack([np.clip(truth + rng.integers(-1, 2, size=60), 1, 5) for _ in range(3)]).astype(float)
    data[0, 5] = np.nan
    for level in ["ordinal", "interval", "nominal"]:
        ours = krippendorff_alpha(data, level)
        ref = kd.alpha(reliability_data=data, level_of_measurement=level)
        assert abs(ours - ref) < 1e-9, (level, ours, ref)


def test_poisson_binomial_equals_binomial_when_equal_p():
    for k in [0, 1, 3, 7]:
        assert abs(poisson_binomial_greater(k, [0.01] * 100) - binom_greater(k, 100, 0.01)) < 1e-9 or k == 0


def test_wilson_bounds():
    lo, hi = wilson_ci(5, 100)
    assert 0 < lo < 0.05 < hi < 0.12


def test_mcnemar_counts():
    a = np.array([1, 1, 0, 0, 1], bool)
    b = np.array([0, 1, 0, 1, 0], bool)
    r = mcnemar_exact(a, b)
    assert r["a_only"] == 2 and r["b_only"] == 1


def test_permutation_detects_clear_difference():
    vals = np.r_[np.full(20, 4.0), np.full(20, 2.0)]
    groups = np.array(["engine"] * 20 + ["ctrl"] * 20)
    strata = np.tile(np.arange(10), 4)
    r = stratified_permutation_test(vals, groups, strata, "engine", "ctrl", iters=2000, seed=1)
    assert r["p_one_sided"] < 0.01


def test_anonymize_removes_years_and_eponyms():
    t = anonymize("The Freundlich adsorption isotherm (1907) applied in 1909.", ["H. Freundlich"])
    assert "1907" not in t and "Freundlich" not in t and "[NAME]" in t


def test_parse_json_handles_thinking_and_fences():
    assert parse_json('<think>hmm {"x":1}</think>```json\n{"score": 7}\n```')["score"] == 7
    assert parse_json('Sure! {"applicability": 4, "novelty": 2} done')["applicability"] == 4
    assert parse_json("no json") is None
