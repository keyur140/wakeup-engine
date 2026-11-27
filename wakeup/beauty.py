# Wake-up Engine: finding forgotten science that already solves today's problems
# Author: KEYUR SHAILESHKUMAR PATEL
# ORCID: https://orcid.org/0009-0008-5261-043X
# Affiliations: (1) MSc Artificial Intelligence student, Department of Computer Science,
#               Brunel University London, UK; (2) Independent researcher
# Note: Conducted independently; not an official Brunel University London project.
# License: MIT (see LICENSE)
"""Beauty coefficient B and awakening time t_a (Ke, Ferrara, Radicchi & Flammini, 2015, PNAS).

Given yearly citations c_t, t = 0 .. T years after publication, with peak c_m at t_m:

    l_t  = (c_m - c_0) / t_m * t + c_0           (line from (0, c_0) to (t_m, c_m))
    B    = sum_{t=0}^{t_m} (l_t - c_t) / max(1, c_t)
    t_a  = argmax_{t <= t_m} d_t,
    d_t  = |(c_m - c_0) t - t_m c_t + t_m c_0| / sqrt((c_m - c_0)^2 + t_m^2)
"""
from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass
class Beauty:
    B: float
    t_m: int
    c_m: int
    t_a: int
    awakening_year: int
    sleep_years: int
    series: list[int]


def citation_series(hist: dict[int, int], pub_year: int, last_year: int) -> list[int]:
    return [int(hist.get(y, 0)) for y in range(pub_year, last_year + 1)]


def beauty_coefficient(series: list[int], pub_year: int) -> Beauty:
    if not series:
        return Beauty(0.0, 0, 0, 0, pub_year, 0, [])
    c0 = series[0]
    c_m = max(series)
    t_m = series.index(c_m)  # first year reaching the peak
    if t_m == 0:
        return Beauty(0.0, 0, c_m, 0, pub_year, 0, series)
    slope = (c_m - c0) / t_m
    B = 0.0
    for t in range(t_m + 1):
        l_t = slope * t + c0
        B += (l_t - series[t]) / max(1, series[t])
    denom = math.sqrt((c_m - c0) ** 2 + t_m ** 2)
    best_t, best_d = 0, -1.0
    for t in range(t_m + 1):
        d = abs((c_m - c0) * t - t_m * series[t] + t_m * c0) / denom
        if d > best_d:
            best_t, best_d = t, d
    return Beauty(B=B, t_m=t_m, c_m=c_m, t_a=best_t, awakening_year=pub_year + best_t,
                  sleep_years=best_t, series=series)
