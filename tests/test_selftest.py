# Wake-up Engine: finding forgotten science that already solves today's problems
# Author: KEYUR SHAILESHKUMAR PATEL
# ORCID: https://orcid.org/0009-0008-5261-043X
# Affiliations: (1) MSc Artificial Intelligence student, Department of Computer Science,
#               Brunel University London, UK; (2) Independent researcher
# Note: Conducted independently; not an official Brunel University London project.
# License: MIT (see LICENSE)
"""End-to-end offline test: the whole pipeline on synthetic data, then hash verification."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


def test_selftest_runs_and_verifies(tmp_path):
    out = subprocess.run([sys.executable, str(ROOT / "run.py"), "selftest"], capture_output=True, text=True,
                         timeout=900)
    assert out.returncode == 0, out.stdout[-3000:] + out.stderr[-3000:]
    run_dir = Path([l for l in out.stdout.splitlines() if l.startswith("Run folder:")][-1].split(": ", 1)[1])
    m = json.loads((run_dir / "manifest.json").read_text())
    assert m["status"] == "completed" and m["mock_mode"] is True
    assert m["author"]["orcid"] == "https://orcid.org/0009-0008-5261-043X"
    for f in ["report.md", "report.html", "results/backtest_ranks.csv", "results/forward_ratings_long.csv",
              "llm_calls.jsonl", "SHA256SUMS", "DATA_CARD_results.md", "checks.json", "results/gate.json",
              "results/leak_scan.csv", "data/sample_for_freeze.json"]:
        assert (run_dir / f).exists(), f
    assert list(run_dir.glob("WakeUpEngine_Exploratory_Report_*.pdf"))
    checks = json.loads((run_dir / "checks.json").read_text())
    assert not [c for c in checks if c["status"] == "FAIL"], checks
    sel = json.loads((run_dir / "data" / "sleeping_beauties_selected.json").read_text())
    import pandas as pd
    ranks = pd.read_csv(run_dir / "results" / "backtest_ranks.csv")
    split = {x["id"]: x["split"] for x in sel}
    assert set(split[i] for i in ranks.sb) == {"dev"}          # the lock held
    pool = pd.read_csv(run_dir / "data" / "candidate_pool_beauty.csv")
    locked = pool[(pool.selected) & (pool.split == "confirm")]
    assert len(locked) and (locked.title == "[LOCKED]").all()  # locked titles never shown
    v = subprocess.run([sys.executable, str(ROOT / "run.py"), "verify", str(run_dir)], capture_output=True, text=True)
    assert v.returncode == 0, v.stdout
    # tampering must be detected
    (run_dir / "report.md").write_text("tampered")
    v2 = subprocess.run([sys.executable, str(ROOT / "run.py"), "verify", str(run_dir)], capture_output=True, text=True)
    assert v2.returncode == 1


def test_confirm_refuses_without_freeze():
    # Check the freeze FIRST. In a frozen study `confirm` really runs and would process locked
    # confirmatory items (issue I21, 2026-11-27), so the test must never start it then.
    if (ROOT / "prereg" / "FREEZE_MANIFEST.json").exists() and (ROOT / "prereg" / "frozen_sample.json").exists():
        pytest.skip("study is frozen; running `confirm` here would touch locked confirmatory data")
    out = subprocess.run([sys.executable, str(ROOT / "run.py"), "confirm"], capture_output=True, text=True, timeout=120)
    assert out.returncode == 3 and "REFUSED" in out.stdout
