# Wake-up Engine: finding forgotten science that already solves today's problems
# Author: KEYUR SHAILESHKUMAR PATEL
# ORCID: https://orcid.org/0009-0008-5261-043X
# Affiliations: (1) MSc Artificial Intelligence student, Department of Computer Science,
#               Brunel University London, UK; (2) Independent researcher
# Note: Conducted independently; not an official Brunel University London project.
# License: MIT (see LICENSE)
"""LLM access through any OpenAI-compatible endpoint (Groq, OpenRouter, local Ollama).

* temperature 0 by default, fixed prompts (see prompts.py)
* every call is logged to <run>/llm_calls.jsonl with SHA-256 of prompt and response
* identical calls are served from data/cache/llm so reruns are exact and free
* a deterministic MockLLM lets the whole pipeline be tested offline
"""
from __future__ import annotations

import json
import os
import re
import threading
import time
from pathlib import Path
from typing import Any

import requests

from .runlog import ROOT, sha256_json, sha256_text, utcnow
from .textutil import tokenize

THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)


def parse_json(text: str) -> dict | None:
    """Pull the first JSON object out of a model reply."""
    if not text:
        return None
    t = THINK_RE.sub("", text).strip()
    t = re.sub(r"^```(?:json)?|```$", "", t, flags=re.MULTILINE).strip()
    try:
        return json.loads(t)
    except Exception:
        pass
    depth, start = 0, None
    for i, ch in enumerate(t):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}" and depth:
            depth -= 1
            if depth == 0 and start is not None:
                try:
                    return json.loads(t[start:i + 1])
                except Exception:
                    start = None
    return None


class RateLimiter:
    def __init__(self, per_minute: float):
        self.interval = 60.0 / max(per_minute, 1e-9)
        self.last = 0.0
        self.lock = threading.Lock()

    def wait(self):
        with self.lock:
            d = self.last + self.interval - time.time()
            if d > 0:
                time.sleep(d)
            self.last = time.time()


class LLM:
    """One model on one provider."""

    def __init__(self, cfg: dict, provider: str, model: str, run=None, name: str | None = None):
        self.cfg = cfg
        self.provider = provider
        self.model = model
        self.name = name or model
        p = cfg["llm"]["providers"][provider]
        self.base_url = p["base_url"].rstrip("/")
        env = p.get("api_key_env")
        self.api_key = os.environ.get(env) if env else None
        if env and not self.api_key:
            raise RuntimeError(f"Missing API key: set {env} in your .env file (provider {provider}).")
        self.limiter = _limiter(provider, p.get("requests_per_minute", 20))
        self.temperature = cfg["llm"].get("temperature", 0.0)
        self.max_tokens = cfg["llm"].get("max_tokens", 400)
        self.use_cache = cfg["llm"].get("cache", True)
        self.cache_dir = ROOT / "data" / "cache" / "llm"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.run = run

    def chat(self, system: str, user: str, task: str, meta: dict | None = None,
             max_tokens: int | None = None, bypass_cache: bool = False) -> str:
        payload = {"model": self.model, "temperature": self.temperature,
                   "max_tokens": max_tokens or self.max_tokens,
                   "messages": [{"role": "system", "content": system},
                                {"role": "user", "content": user}]}
        key = sha256_json({"provider": self.provider, **payload})
        cp = self.cache_dir / f"{key}.json"
        cached = False
        if self.use_cache and cp.exists() and not bypass_cache:
            text = json.loads(cp.read_text())["response"]
            cached = True
        else:
            text = self._call(payload)
            if bypass_cache:  # drift check: never overwrite the stored answer
                self._log(task, key, system, user, text, False, meta)
                return text
            cp.write_text(json.dumps({"request_sha256": key, "provider": self.provider,
                                      "model": self.model, "retrieved_utc": utcnow(),
                                      "response": text}))
        self._log(task, key, system, user, text, cached, meta)
        return text

    def _call(self, payload: dict) -> str:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        last_err = None
        # Retries default to 8; WAKEUP_LLM_MAX_RETRIES lets a free-tier run wait out daily limits (ISSUES I14).
        for attempt in range(int(os.environ.get("WAKEUP_LLM_MAX_RETRIES", "8"))):
            self.limiter.wait()
            try:
                r = requests.post(f"{self.base_url}/chat/completions", json=payload,
                                  headers=headers, timeout=180)
            except requests.RequestException as e:
                last_err = str(e)
                time.sleep(min(120, 2 ** (attempt + 1)))
                continue
            if r.status_code == 200:
                data = r.json()
                msg = data["choices"][0]["message"]
                return msg.get("content") or ""
            last_err = f"HTTP {r.status_code}: {r.text[:300]}"
            if r.status_code in (408, 409, 429, 500, 502, 503, 504):
                retry_after = r.headers.get("retry-after")
                delay = float(retry_after) if retry_after and retry_after.replace(".", "").isdigit() \
                    else min(120, 2 ** (attempt + 1))
                if self.run:
                    self.run.log.warning("%s %s; retry in %.0fs", self.name, last_err[:80], delay)
                time.sleep(delay)
                continue
            raise RuntimeError(f"LLM call failed ({self.provider}/{self.model}): {last_err}")
        raise RuntimeError(f"LLM call failed after retries ({self.provider}/{self.model}): {last_err}")

    def _log(self, task, key, system, user, text, cached, meta):
        if not self.run:
            return
        self.run.count(f"llm_calls_{task}")
        if cached:
            self.run.count("llm_cache_hits")
        rec = {"utc": utcnow(), "task": task, "role_name": self.name, "provider": self.provider,
               "model": self.model, "temperature": self.temperature, "request_sha256": key,
               "prompt_sha256": sha256_text(system + "\n" + user),
               "response_sha256": sha256_text(text), "cached": cached, "meta": meta or {},
               "system": system, "user": user, "response": text}
        with open(self.run.path("llm_calls.jsonl"), "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


_LIMITERS: dict[str, RateLimiter] = {}


def _limiter(provider: str, rpm: float) -> RateLimiter:
    if provider not in _LIMITERS:
        _LIMITERS[provider] = RateLimiter(rpm)
    return _LIMITERS[provider]


class MockLLM:
    """Deterministic offline stand-in used only for self-tests and synthetic validation.

    behaviour:
      signal     scores by word overlap with the need (an honest, useful model)
      null       scores at random (a useless model)
      memorizer  recognizes planted sleeping beauties by their identity token ("keywordNa")
                 and scores them 10, otherwise random: good on original text, lost when disguised
      collapse   gives every item the same score
    It is NOT a model and its outputs are not findings. Runs that use it are flagged MOCK.
    """

    def __init__(self, name: str = "mock", run=None, bias: float = 0.0, behaviour: str = "signal"):
        self.name = name
        self.provider = "mock"
        self.model = f"mock-{name}-{behaviour}"
        self.run = run
        self.bias = bias
        self.behaviour = behaviour

    def _rand(self, user: str) -> float:
        return int(sha256_text(self.name + "|" + user)[:6], 16) / float(16 ** 6)

    def chat(self, system: str, user: str, task: str, meta: dict | None = None,
             max_tokens: int | None = None, bypass_cache: bool = False) -> str:
        import re as _re
        h = self._rand(user)
        if task == "need_summary":
            words = tokenize(user)
            uniq = sorted(set(words), key=lambda w: (-words.count(w), w))
            out = json.dumps({"need": "Open problems involve " + ", ".join(uniq[:25])})
        elif task == "query_expansion":
            prob = user.split("OPEN PROBLEM (today):")[-1].split("Propose")[0]
            uniq = sorted(set(tokenize(prob)))
            out = json.dumps({"queries": [" ".join(uniq[i:i + 2]) for i in range(0, 10, 2)]})
        elif task == "paraphrase":
            body = user.split("\n\n")[1] if "\n\n" in user else user
            body = _re.sub(r"keyword(\d+)a", "", body)           # identity token removed
            body = _re.sub(r"Title:[^\n]*\n", "", body)
            out = json.dumps({"text": "Rewritten: " + body})
        elif task == "memorization":
            m = _re.search(r"keyword(\d+)a", user)
            if self.behaviour == "memorizer" and m:
                out = json.dumps({"recognized": True, "title": f"on a curious keyword{m.group(1)}a "
                                  f"keyword{m.group(1)}b", "first_author": "Mocksen", "year": None})
            else:
                out = json.dumps({"recognized": False, "title": "", "first_author": "", "year": None})
        elif task in ("rerank", "judge", "gate_judge", "gate_engine"):
            head, _, cand = user.partition("CANDIDATE")
            need, ctoks = set(tokenize(head)), set(tokenize(cand))
            ov = len(need & ctoks) / (len(ctoks) ** 0.5 + 1)
            if self.behaviour == "signal":
                x = ov * 4 + h + self.bias
            elif self.behaviour == "memorizer":
                x = 10.0 if _re.search(r"keyword\d+a", cand) else h * 6
            elif self.behaviour == "collapse":
                x = 3.0
            else:
                x = h * 10
            if task in ("rerank", "gate_engine"):
                out = json.dumps({"score": round(min(10.0, max(0.0, x)), 2), "reason": "mock"})
            else:
                a = 3 if self.behaviour == "collapse" else int(max(1, min(5, round(1 + x / 2.5))))
                nov = int(max(1, min(5, round(2 + 2 * h))))
                out = json.dumps({"applicability": a, "novelty": nov, "reason": "mock"})
        else:
            out = "{}"
        if self.run:
            self.run.count(f"llm_calls_{task}")
            rec = {"utc": utcnow(), "task": task, "role_name": self.name, "provider": "mock",
                   "model": self.model, "prompt_sha256": sha256_text(system + "\n" + user),
                   "response_sha256": sha256_text(out), "cached": False, "meta": meta or {},
                   "system": system, "user": user, "response": out}
            with open(self.run.path("llm_calls.jsonl"), "a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        return out


def make_llm(cfg: dict, role: str, run=None, mock: bool = False) -> Any:
    r = cfg["llm"]["roles"][role]
    if mock:
        return MockLLM(role, run, behaviour=cfg.get("mock", {}).get(f"{role}_behaviour", "signal"))
    return LLM(cfg, r["provider"], r["model"], run, name=role)


def make_judges(cfg: dict, run=None, mock: bool = False) -> list:
    js = []
    behaviours = cfg.get("mock", {}).get("judge_behaviours", [])
    for i, j in enumerate(cfg["llm"]["roles"]["judges"]):
        if mock:
            beh = behaviours[i] if i < len(behaviours) else "signal"
            js.append(MockLLM(j["name"], run, bias=0.2 * (i - 1), behaviour=beh))
        else:
            js.append(LLM(cfg, j["provider"], j["model"], run, name=j["name"]))
    return js
