# Wake-up Engine: finding forgotten science that already solves today's problems
# Author: KEYUR SHAILESHKUMAR PATEL
# ORCID: https://orcid.org/0009-0008-5261-043X
# Affiliations: (1) MSc Artificial Intelligence student, Department of Computer Science,
#               Brunel University London, UK; (2) Independent researcher
# Note: Conducted independently; not an official Brunel University London project.
# License: MIT (see LICENSE)
"""Report writer: Markdown + self-contained HTML, plus a data card for every run."""
from __future__ import annotations

import base64
import html
import io
from pathlib import Path

import pandas as pd

from .meta import AI_USE_STATEMENT, AUTHOR, DATA_LICENSE, PROJECT_TITLE, STUDY_TITLE, VERSION, author_block_markdown


class Report:
    def __init__(self, run, title: str):
        self.run = run
        self.title = title
        self.md: list[str] = []
        self.html: list[str] = []
        self._header()

    def _header(self):
        r = self.run
        mock = "\n\n> **MOCK MODE: synthetic data. These numbers are NOT scientific results.**" if r.mock else ""
        self.md.append(f"# {self.title}\n\n*{STUDY_TITLE}*\n\n{author_block_markdown()}\n\n"
                       f"Run `{r.run_id}` · software v{VERSION} · started {r.started}  \n"
                       f"Preregistration check: **{r.prereg['status']}**{mock}\n")
        a = AUTHOR
        self.html.append(
            f"<h1>{html.escape(self.title)}</h1><p><em>{html.escape(STUDY_TITLE)}</em></p>"
            f"<p><strong>{html.escape(a['name'])}</strong><br>ORCID: <a href='{a['orcid']}'>{a['orcid']}</a><br>"
            f"(1) {html.escape(a['affiliations'][0])}<br>(2) {html.escape(a['affiliations'][1])}<br>"
            f"<em>{html.escape(a['note'])}</em></p>"
            f"<p>Run <code>{r.run_id}</code> · software v{VERSION} · started {r.started}<br>"
            f"Preregistration check: <strong>{r.prereg['status']}</strong></p>"
            + ("<p class='mock'><strong>MOCK MODE: synthetic data. These numbers are NOT scientific "
               "results.</strong></p>" if r.mock else ""))

    def h2(self, text):
        self.md.append(f"\n## {text}\n")
        self.html.append(f"<h2>{html.escape(text)}</h2>")

    def p(self, text):
        self.md.append(text + "\n")
        self.html.append(f"<p>{html.escape(text)}</p>")

    def bullets(self, items):
        self.md.append("\n".join(f"- {i}" for i in items) + "\n")
        self.html.append("<ul>" + "".join(f"<li>{html.escape(str(i))}</li>" for i in items) + "</ul>")

    def table(self, df: pd.DataFrame, floatfmt: str = "{:.4g}"):
        d = df.copy()
        for c in d.columns:
            if pd.api.types.is_float_dtype(d[c]):
                d[c] = d[c].map(lambda x: "" if pd.isna(x) else floatfmt.format(x))
        self.md.append(d.to_markdown(index=False) + "\n" if _has_tabulate() else "```\n" + d.to_string(index=False) + "\n```\n")
        self.html.append(d.to_html(index=False, escape=True, border=0, classes="t"))

    def figure(self, fig, name: str, caption: str):
        png = self.run.path("figures", f"{name}.png")
        fig.savefig(png, dpi=150, bbox_inches="tight")
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=110, bbox_inches="tight")
        b64 = base64.b64encode(buf.getvalue()).decode()
        self.md.append(f"![{caption}](figures/{name}.png)\n\n*{caption}*\n")
        self.html.append(f"<figure><img src='data:image/png;base64,{b64}' alt='{html.escape(caption)}'>"
                         f"<figcaption>{html.escape(caption)}</figcaption></figure>")

    def save(self, stem: str = "report"):
        self.h2("Credit, licence and AI use")
        self.p(f"Author: {AUTHOR['name']} ({AUTHOR['orcid']}). {AUTHOR['note']}")
        self.p(f"Data and reports licensed {DATA_LICENSE}. Code licensed MIT.")
        self.p(AI_USE_STATEMENT)
        self.p("Integrity: every file in this run folder is listed with its SHA-256 hash in "
               "manifest.json and SHA256SUMS. Check with `python run.py verify <run folder>`.")
        (self.run.dir / f"{stem}.md").write_text("\n".join(self.md), encoding="utf-8")
        css = ("body{font-family:system-ui,sans-serif;max-width:960px;margin:2rem auto;padding:0 16px;"
               "line-height:1.5;color:#1d1d1f;background:#fff}table.t{border-collapse:collapse;margin:1rem 0;"
               "font-size:.9rem}table.t td,table.t th{border-bottom:1px solid #ddd;padding:4px 8px;text-align:left}"
               "img{max-width:100%}.mock{background:#fff3cd;padding:8px}code{background:#f3f3f3;padding:1px 4px}")
        doc = (f"<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' "
               f"content='width=device-width,initial-scale=1'><title>{html.escape(self.title)}</title>"
               f"<style>{css}</style></head><body>{''.join(self.html)}</body></html>")
        (self.run.dir / f"{stem}.html").write_text(doc, encoding="utf-8")


def _has_tabulate() -> bool:
    try:
        import tabulate  # noqa: F401
        return True
    except Exception:
        return False


def write_data_card(run, name: str, description: str, files: dict[str, str], sources: list[str]):
    a = AUTHOR
    lines = [f"# Data card: {name}", "", f"Project: {PROJECT_TITLE}", "",
             f"Creator: {a['name']}  ", f"ORCID: {a['orcid']}  ",
             f"Affiliations: (1) {a['affiliations'][0]}; (2) {a['affiliations'][1]}  ",
             f"*{a['note']}*", "", f"Run: `{run.run_id}`{' (MOCK, synthetic)' if run.mock else ''}  ",
             f"Licence: {DATA_LICENSE}", "", "## Description", description, "", "## Sources"]
    lines += [f"- {s}" for s in sources]
    lines += ["", "## Files"] + [f"- `{k}`: {v}" for k, v in files.items()]
    lines += ["", "## Provenance and integrity",
              "All API responses are cached under `data/cache/` with the request URL and retrieval "
              "time. SHA-256 hashes of every file in this run are in `manifest.json` and `SHA256SUMS`.",
              "", AI_USE_STATEMENT, ""]
    run.path(f"DATA_CARD_{name}.md").write_text("\n".join(lines), encoding="utf-8")
