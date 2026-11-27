# Wake-up Engine: finding forgotten science that already solves today's problems
# Author: KEYUR SHAILESHKUMAR PATEL
# ORCID: https://orcid.org/0009-0008-5261-043X
# Affiliations: (1) MSc Artificial Intelligence student, Department of Computer Science,
#               Brunel University London, UK; (2) Independent researcher
# Note: Conducted independently; not an official Brunel University London project.
# License: MIT (see LICENSE)
"""Fixed development / confirmatory split (the "lock").

Each sleeping beauty is assigned by SHA-256 of a fixed salt and its OpenAlex ID, so the split
never depends on run order, on the data or on anyone's choice. Exploratory runs may only touch
the development part. Confirmatory commands refuse to run until the study is frozen.
"""
from __future__ import annotations

import hashlib


def assign(work_id: str, seed: int, dev_fraction: float) -> str:
    h = hashlib.sha256(f"wakeup-split|{seed}|{work_id}".encode()).hexdigest()
    u = int(h[:12], 16) / float(16 ** 12)
    return "dev" if u < dev_fraction else "confirm"


def item_seed(seed: int, *parts: str) -> int:
    """Per-item random seed, so one item's randomness never depends on another item."""
    h = hashlib.sha256("|".join([str(seed), *parts]).encode()).hexdigest()
    return int(h[:15], 16)
