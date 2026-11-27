# Wake-up Engine: finding forgotten science that already solves today's problems
# Author: KEYUR SHAILESHKUMAR PATEL
# ORCID: https://orcid.org/0009-0008-5261-043X
# Affiliations: (1) MSc Artificial Intelligence student, Department of Computer Science,
#               Brunel University London, UK; (2) Independent researcher
# Note: Conducted independently; not an official Brunel University London project.
# License: MIT (see LICENSE)
"""Run folders, logging, SHA-256 integrity manifests and provenance.

Every command creates runs/<run_id>/ containing:
  run.log            human-readable log
  config_snapshot.yaml  exact config used
  environment.json   python, platform, package versions
  manifest.json      author, run info, prereg check, SHA-256 of every output
  SHA256SUMS         `sha256sum -c` compatible list of every file in the run
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import logging
import os
import platform
import secrets
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

from .meta import AI_USE_STATEMENT, AUTHOR, CODE_LICENSE, DATA_LICENSE, PROJECT_TITLE, VERSION

ROOT = Path(__file__).resolve().parent.parent


def sha256_file(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_json(obj: Any) -> str:
    return sha256_text(json.dumps(obj, sort_keys=True, ensure_ascii=False, default=str))


def utcnow() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# Files that together define the preregistered study. Their hashes are frozen
# before data collection (`python run.py freeze`) and re-checked on every run.
PREREG_FILES = [
    "prereg/OSF_preregistration.md",
    "config/study.yaml",
    "config/forward_problems_antibiotic_resistance.yaml",
    "config/forward_problems_dev.yaml",
    "prereg/frozen_sample.json",       # sleeping-beauty sample + split, copied from the exploratory run
    "prereg/gate_frozen.json",         # known-answer gate decisions from the exploratory run
    "DECISIONS.md",
    "requirements.lock",
]
PREREG_CODE_GLOBS = ["wakeup/*.py", "run.py"]


def prereg_file_list() -> list[Path]:
    files = [ROOT / p for p in PREREG_FILES]
    for g in PREREG_CODE_GLOBS:
        files.extend(sorted(ROOT.glob(g)))
    return [f for f in files if f.exists()]


def compute_prereg_hashes() -> dict[str, str]:
    return {str(f.relative_to(ROOT)): sha256_file(f) for f in prereg_file_list()}


def check_against_freeze() -> dict[str, Any]:
    """Compare current study files with prereg/FREEZE_MANIFEST.json."""
    freeze_path = ROOT / "prereg" / "FREEZE_MANIFEST.json"
    if not freeze_path.exists():
        return {"frozen": False, "status": "NOT_FROZEN",
                "message": "Study not frozen yet. Run `python run.py freeze` before real data collection."}
    frozen = json.loads(freeze_path.read_text())
    now = compute_prereg_hashes()
    changed = sorted(k for k in frozen["files"] if now.get(k) != frozen["files"][k])
    added = sorted(k for k in now if k not in frozen["files"])
    status = "MATCHES_FREEZE" if not changed and not added else "DEVIATION_FROM_FREEZE"
    return {"frozen": True, "status": status, "frozen_at": frozen.get("frozen_at"),
            "freeze_bundle_sha256": frozen.get("bundle_sha256"),
            "changed_files": changed, "added_files": added}


def environment_info() -> dict[str, Any]:
    pkgs = {}
    for name in ["numpy", "pandas", "scipy", "scikit-learn", "rank-bm25", "requests",
                 "PyYAML", "matplotlib", "sentence-transformers", "torch"]:
        try:
            from importlib.metadata import version
            pkgs[name] = version(name)
        except Exception:
            pkgs[name] = None
    try:
        freeze = subprocess.run([sys.executable, "-m", "pip", "freeze"], capture_output=True,
                                text=True, timeout=60).stdout.splitlines()
    except Exception:
        freeze = []
    return {"python": sys.version, "platform": platform.platform(),
            "machine": platform.machine(), "packages": pkgs, "pip_freeze": freeze}


class Run:
    """A single reproducible run with its own folder, log and manifest."""

    def __init__(self, command: str, config: dict, mock: bool = False, runs_dir: Path | None = None):
        self.command = command
        self.config = config
        self.mock = mock
        stamp = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        self.run_id = f"{stamp}_{command}{'_MOCK' if mock else ''}_{secrets.token_hex(3)}"
        base = runs_dir or (ROOT / "runs")
        self.dir = base / self.run_id
        self.dir.mkdir(parents=True, exist_ok=True)
        self.started = utcnow()
        self.log = logging.getLogger(f"wakeup.{self.run_id}")
        self.log.setLevel(logging.INFO)
        self.log.handlers.clear()
        fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s", "%Y-%m-%dT%H:%M:%S")
        fh = logging.FileHandler(self.dir / "run.log", encoding="utf-8")
        fh.setFormatter(fmt)
        sh = logging.StreamHandler(sys.stdout)
        sh.setFormatter(fmt)
        self.log.addHandler(fh)
        self.log.addHandler(sh)
        self.notes: list[str] = []
        self.counters: dict[str, int] = {}
        (self.dir / "config_snapshot.yaml").write_text(yaml.safe_dump(config, sort_keys=False))
        (self.dir / "environment.json").write_text(json.dumps(environment_info(), indent=2))
        self.prereg = check_against_freeze()
        self.log.info("Run %s started (command=%s, mock=%s)", self.run_id, command, mock)
        self.log.info("Author: %s (%s)", AUTHOR["name"], AUTHOR["orcid"])
        self.log.info("Preregistration check: %s", self.prereg["status"])
        if mock:
            self.log.warning("MOCK MODE: synthetic data, results are NOT scientific findings.")

    def path(self, *parts: str) -> Path:
        p = self.dir.joinpath(*parts)
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    def count(self, key: str, n: int = 1) -> None:
        self.counters[key] = self.counters.get(key, 0) + n

    def write_json(self, name: str, obj: Any) -> Path:
        p = self.path(name)
        p.write_text(json.dumps(obj, indent=2, ensure_ascii=False, default=str))
        return p

    def finish(self, status: str = "completed", extra: dict | None = None) -> Path:
        self.log.info("Run finished: %s. Writing manifest and SHA-256 sums.", status)
        for h in list(self.log.handlers):
            h.close()
            self.log.removeHandler(h)
        files = sorted(p for p in self.dir.rglob("*") if p.is_file()
                       and p.name not in ("manifest.json", "SHA256SUMS"))
        hashes = {str(p.relative_to(self.dir)): sha256_file(p) for p in files}
        manifest = {
            "project": PROJECT_TITLE,
            "software_version": VERSION,
            "author": AUTHOR,
            "ai_use_statement": AI_USE_STATEMENT,
            "licenses": {"code": CODE_LICENSE, "data_and_reports": DATA_LICENSE},
            "run_id": self.run_id,
            "command": self.command,
            "mock_mode": self.mock,
            "started_utc": self.started,
            "finished_utc": utcnow(),
            "status": status,
            "argv": sys.argv,
            "config_sha256": sha256_json(self.config),
            "preregistration_check": self.prereg,
            "counters": self.counters,
            "notes": self.notes,
            "extra": extra or {},
            "files_sha256": hashes,
        }
        mp = self.dir / "manifest.json"
        mp.write_text(json.dumps(manifest, indent=2, ensure_ascii=False, default=str))
        lines = [f"{h}  {name}" for name, h in hashes.items()]
        lines.append(f"{sha256_file(mp)}  manifest.json")
        (self.dir / "SHA256SUMS").write_text("\n".join(lines) + "\n")
        print(f"Manifest SHA-256: {sha256_file(mp)}")
        return mp


def load_config(path: str | os.PathLike | None = None) -> dict:
    p = Path(path) if path else ROOT / "config" / "study.yaml"
    return yaml.safe_load(p.read_text())
