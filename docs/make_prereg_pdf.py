# Wake-up Engine: finding forgotten science that already solves today's problems
# Author: KEYUR SHAILESHKUMAR PATEL
# ORCID: https://orcid.org/0009-0008-5261-043X
# Affiliations: (1) MSc Artificial Intelligence student, Department of Computer Science,
#               Brunel University London, UK; (2) Independent researcher
# Note: Conducted independently; not an official Brunel University London project.
# License: MIT (see LICENSE)
"""Render a preregistration Markdown file to PDF.

  python docs/make_prereg_pdf.py prereg/OSF_form_answers.md prereg/WakeUpEngine_OSF_Preregistration.pdf
"""
from __future__ import annotations

import html
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from reportlab.lib.pagesizes import A4  # noqa: E402
from reportlab.lib.units import mm  # noqa: E402
from reportlab.platypus import SimpleDocTemplate  # noqa: E402

from wakeup.meta import AUTHOR, VERSION  # noqa: E402
from wakeup.pdfreport import QUIET, P  # noqa: E402


def inline(t: str) -> str:
    t = html.escape(t, quote=False)
    t = re.sub(r"`([^`]+)`", r'<font face="Courier">\1</font>', t)
    t = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<i>\1</i>", t)
    t = re.sub(r"(https?://[^\s)<]+)", r'<link href="\1" color="#1a5fb4">\1</link>', t)
    return t


def render(md: str):
    st, para, item = [], [], []   # item = [prefix, text] of an open list item

    def flush():
        if para:
            st.append(P(inline(" ".join(para))))
            para.clear()
        if item:
            st.append(P(f"{item[0]}&nbsp; {inline(item[1])}"))
            item.clear()
    first_title = True
    for line in md.splitlines():
        s = line.rstrip()
        if not s.strip() or s.strip() == "---":
            flush()
            continue
        m = re.match(r"^(\s*)(- |(\d+)\. )(.*)", s)
        if s.startswith("# "):
            flush()
            st.append(P(inline(s[2:]), "title" if first_title else "h1"))
            first_title = False
        elif s.startswith("## "):
            flush()
            st.append(P(inline(s[3:]), "h2"))
        elif s.startswith("### "):
            flush()
            st.append(P(f"<b>{inline(s[4:])}</b>"))
        elif m:
            flush()
            mark = "&bull;" if m.group(2) == "- " else f"{m.group(3)}."
            item.extend(["&nbsp;" * (5 if m.group(1) else 0) + mark, m.group(4)])
        elif item and line.startswith(" "):
            item[1] += " " + s.strip()
        elif s.startswith("> "):
            flush()
            st.append(P(inline(s[2:]), "small"))
        else:
            if item:
                flush()
            para.append(s.strip())
    flush()
    return st


def main(src: str, out: str) -> None:
    a = AUTHOR
    footer = f"Wake-up Engine OSF preregistration v{VERSION} - {a['name']} - ORCID {a['orcid'].split('/')[-1]} - page "

    def on_page(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(QUIET)
        canvas.drawString(18 * mm, 10 * mm, footer + str(doc.page))
        canvas.restoreState()
    doc = SimpleDocTemplate(out, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm,
                            bottomMargin=18 * mm, title="Wake-up Engine: OSF Preregistration", author=a["name"],
                            creator=f"Wake-up Engine v{VERSION}")
    doc.build(render(Path(src).read_text(encoding="utf-8")), onFirstPage=on_page, onLaterPages=on_page)
    print(out)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
