# Wake-up Engine: finding forgotten science that already solves today's problems
# Author: KEYUR SHAILESHKUMAR PATEL
# ORCID: https://orcid.org/0009-0008-5261-043X
# Affiliations: (1) MSc Artificial Intelligence student, Department of Computer Science,
#               Brunel University London, UK; (2) Independent researcher
# Note: Conducted independently; not an official Brunel University London project.
# License: MIT (see LICENSE)
"""Easy-language PDF report for a run (exploratory, confirmatory or synthetic validation).

Layout follows the author's earlier MEWS exploratory report: the short answer first, what the
report is and is not, "can we trust the run?" checks, results, leakage checks, problems
found, what we can and cannot say, words used, fingerprints, and common questions.
Every page footer carries the author's name and ORCID.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer,
                                Table, TableStyle)

from .meta import AI_USE_STATEMENT, AUTHOR, STUDY_TITLE, VERSION
from .runlog import ROOT, sha256_file, sha256_json

INK = colors.HexColor("#1d1d1f")
QUIET = colors.HexColor("#5f6368")
RULE = colors.HexColor("#d0d4da")
ACCENT = colors.HexColor("#1a5fb4")
TINT = colors.HexColor("#eef3fb")

ss = getSampleStyleSheet()
S = {
    "title": ParagraphStyle("t", parent=ss["Title"], fontName="Helvetica-Bold", fontSize=19, leading=23,
                            textColor=INK, alignment=TA_LEFT, spaceAfter=4),
    "sub": ParagraphStyle("s", parent=ss["Normal"], fontName="Helvetica", fontSize=11, leading=14, textColor=QUIET),
    "h1": ParagraphStyle("h1", parent=ss["Heading2"], fontName="Helvetica-Bold", fontSize=13.5, leading=17,
                         textColor=INK, spaceBefore=10, spaceAfter=4),
    "h2": ParagraphStyle("h2", parent=ss["Heading3"], fontName="Helvetica-Bold", fontSize=11, leading=14,
                         textColor=INK, spaceBefore=6, spaceAfter=2),
    "body": ParagraphStyle("b", parent=ss["Normal"], fontName="Helvetica", fontSize=9.6, leading=13.2, textColor=INK,
                           spaceAfter=4),
    "small": ParagraphStyle("sm", parent=ss["Normal"], fontName="Helvetica", fontSize=8.2, leading=10.5,
                            textColor=QUIET, spaceAfter=3),
    "cell": ParagraphStyle("c", parent=ss["Normal"], fontName="Helvetica", fontSize=8.2, leading=10.2, textColor=INK),
    "cellb": ParagraphStyle("cb", parent=ss["Normal"], fontName="Helvetica-Bold", fontSize=8.2, leading=10.2,
                            textColor=INK),
    "box": ParagraphStyle("bx", parent=ss["Normal"], fontName="Helvetica", fontSize=9.6, leading=13.2,
                          textColor=INK, backColor=TINT, borderPadding=6, spaceBefore=4, spaceAfter=8),
}


def P(text, style="body"):
    return Paragraph(text, S[style])


def bullets(items):
    return [P(f"&bull;&nbsp; {t}") for t in items]


def table(rows, widths=None, header=True):
    data = [[P(str(c), "cellb" if (header and i == 0) else "cell") for c in r] for i, r in enumerate(rows)]
    t = Table(data, colWidths=widths, repeatRows=1 if header else 0)
    st = [("VALIGN", (0, 0), (-1, -1), "TOP"), ("LINEBELOW", (0, 0), (-1, -1), 0.3, RULE),
          ("LEFTPADDING", (0, 0), (-1, -1), 3), ("RIGHTPADDING", (0, 0), (-1, -1), 3),
          ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2)]
    if header:
        st += [("BACKGROUND", (0, 0), (-1, 0), TINT), ("LINEBELOW", (0, 0), (-1, 0), 0.8, ACCENT)]
    t.setStyle(TableStyle(st))
    return t


def fmt(x, pct=False, nd=3):
    if x is None:
        return "n/a"
    try:
        if x != x:
            return "n/a"
    except Exception:
        pass
    if pct:
        return f"{x:.0%}" if x >= 0.1 or x == 0 else f"{x:.1%}"
    if isinstance(x, float):
        return f"{x:.{nd}g}"
    return str(x)


def code_sha256() -> str:
    files = sorted(ROOT.glob("wakeup/*.py")) + [ROOT / "run.py"]
    return sha256_json({str(f.relative_to(ROOT)): sha256_file(f) for f in files})


def _read_json(p: Path, default):
    try:
        return json.loads(p.read_text())
    except Exception:
        return default


def build_pdf(run, kind: str, extra_sections: list | None = None) -> Path:
    """kind: 'exploratory', 'confirmatory' or 'validation'."""
    d = run.dir
    summ = _read_json(d / "results" / "summary.json", {})
    checks = _read_json(d / "checks.json", [])
    gate = _read_json(d / "results" / "gate.json", [])
    bt = summ.get("backtest", {}) or {}
    fw = summ.get("forward", {}) or {}
    a = AUTHOR
    title = {"exploratory": "Wake-up Engine: what the exploratory run shows",
             "confirmatory": "Wake-up Engine: preregistered (confirmatory) results",
             "validation": "Wake-up Engine: design, safeguards and synthetic validation"}[kind]
    subtitle = {"exploratory": "Development sleeping beauties and practice problems only. An easy-language report.",
                "confirmatory": "Locked confirmatory sleeping beauties and the 20 preregistered problems.",
                "validation": "The full pipeline run on synthetic worlds with known answers. No real data."}[kind]
    if run.mock and kind != "validation":
        subtitle += " MOCK DATA: NOT SCIENTIFIC RESULTS."
    footer = f"Wake-up Engine {kind} report - {a['name']} - ORCID {a['orcid'].split('/')[-1]} - page "
    out = d / f"WakeUpEngine_{kind.capitalize()}_Report_{run.run_id}.pdf"

    def on_page(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(QUIET)
        canvas.drawString(18 * mm, 10 * mm, footer + str(doc.page))
        canvas.restoreState()

    st = []
    st += [P(title, "title"), P(subtitle, "sub"), Spacer(1, 8),
           P(f"<b>{a['name']}</b>"), P(f"ORCID: {a['orcid']}"), P(a["affiliations"][0]), P(a["affiliations"][1]),
           P(f"<i>{a['note']}</i>"), Spacer(1, 6),
           P(f"Run: {run.run_id} &nbsp;&middot;&nbsp; Software v{VERSION} &nbsp;&middot;&nbsp; Started {run.started}"),
           P(f"Preregistration status: <b>{run.prereg['status']}</b>"), Spacer(1, 6),
           P(f"<b>Use of AI tools.</b> {AI_USE_STATEMENT} Separately, the system tests open-weights AI models "
             "as its engine and as blind judges; those models are the object of study.", "small"),
           P("Licence: text and figures CC BY 4.0; code MIT.", "small")]

    # 1. short answer
    st.append(P("1. The short answer", "h1"))
    short = []
    pr = bt.get("primary")
    if pr:
        short.append(f"Back-test: the engine put the real sleeping beauty in its top {cfg_k(run)} for "
                     f"<b>{pr['hits']} of {pr['n']}</b> items ({fmt(pr['rate'], True)}; luck would give "
                     f"{fmt(pr['chance_rate'], True)}). One-sided p = {fmt(pr['p_one_sided'])}.")
        pb = bt.get("primary_b")
        if pb:
            short.append(f"Engine vs plain search (H1b): engine-only finds {pb['engine_only_hits']}, search-only finds "
                         f"{pb['search_only_hits']}; one-sided p = {fmt(pb['p_one_sided'])} (Holm {fmt(pb['p_holm'])}). "
                         "This is the test that rules out 'it is just keyword matching'.")
        mt = {r["method"]: r for r in bt.get("method_table", [])}
        if "hybrid" in mt and "engine" in mt:
            short.append(f"Search alone (hybrid) found {fmt(mt['hybrid'][f'hit@{cfg_k(run)}'], True)} in its top "
                         f"{cfg_k(run)}; the AI re-reading moved this to {fmt(mt['engine'][f'hit@{cfg_k(run)}'], True)}.")
        sm = bt.get("sensitivity_memorization")
        if sm:
            short.append(f"Memorization: the engine model recognized {sm['n_memorized']} of {pr['n']} sleeping "
                         f"beauties from their anonymized text.")
        dg = bt.get("disguise")
        if dg:
            short.append(f"Disguised text: mean position {fmt(dg['mean_rank_original'])} with original wording vs "
                         f"{fmt(dg['mean_rank_disguised'])} when rewritten (p = {fmt(dg['wilcoxon_p_worse'])} for 'worse').")
    elif bt:
        short.append(f"Back-test: no usable items ({bt.get('n_usable', 0)}).")
    if gate:
        passed = [g["model_name"] for g in gate if g["passed"]]
        short.append(f"Known-answer gate: {len(passed)} of {len(gate)} AI models passed "
                     f"({', '.join(passed) or 'none'}).")
    if fw:
        if fw.get("testable"):
            t2 = fw.get("tests", {}).get("H2_engine_vs_pool_random", {})
            short.append(f"Forward test: engine picks rated {fmt(t2.get('mean_treat'))} vs "
                         f"{fmt(t2.get('mean_control'))} for random picks from the same search (1-5 scale), "
                         f"p = {fmt(t2.get('p_one_sided'))}. Judge agreement alpha = "
                         f"{fmt(fw.get('krippendorff_alpha_applicability'))}.")
        else:
            short.append("Forward test: not testable in this run (fewer than 2 usable judges).")
    nchk = [c for c in checks if c["status"] != "n/a"]
    if checks:
        short.append(f"Self-checks: {sum(c['status'] == 'pass' for c in nchk)} of {len(nchk)} passed"
                     f"{' (' + str(len(checks) - len(nchk)) + ' not applicable)' if len(checks) > len(nchk) else ''}.")
    st += bullets(short or ["No results were produced in this run."])
    meaning = {"exploratory": "This is a first look on development data, used to find problems and check the method. "
                              "It is a health check, not proof. The real test is the preregistered one on the locked part.",
               "confirmatory": "These are the preregistered tests on data locked before the freeze.",
               "validation": "Synthetic worlds have known answers, so they test whether the machinery finds signal "
                             "when it is there and stays quiet when it is not. They say nothing about real science."}[kind]
    st.append(P(f"<b>What this means in plain words.</b> {meaning}", "box"))

    # 2. what it is / is not
    st.append(P("2. What this report is, and what it is not", "h1"))
    if kind == "exploratory":
        st += [P("Every sleeping beauty is assigned to a development part (20%) or a locked confirmatory part (80%) by a "
                 "fixed SHA-256 rule. This run touched only the development part and four practice problems that are "
                 "not among the 20 preregistered ones. The code refuses to process locked items until the study is "
                 "frozen. Titles of locked items are blanked in every saved table."),
               P("So the numbers here are exploratory. p-values are a preview of the method and must not be quoted "
                 "as findings.")]
    elif kind == "validation":
        st += [P("Four synthetic worlds were built: <b>W1 signal</b> (the need really points to the planted sleeping "
                 "beauty and the engine reads honestly), <b>W2 null</b> (the need carries no clue and the engine "
                 "scores at random), <b>W3 memorizer</b> (the engine recognizes planted papers by a hidden "
                 "identity word, not by meaning) and <b>W4 word overlap</b> (no real clue, but the sleeping beauty "
                 "shares a few everyday words with the waking field). Judges include useful ones, random ones and "
                 "one that always gives the same score. A <b>lock test</b> runs the confirmatory path and checks it "
                 "touches only locked items, and 40 extra null worlds estimate how often the main test gives a "
                 "false alarm."),
               P("Synthetic worlds have no planted answers for the forward test, so the forward numbers here only show "
                 "that the forward machinery runs and that bad judges are removed.")]
    else:
        st += [P("Confirmatory results on the locked part, run after the freeze. Deviations, if any, are listed below.")]

    # 3. checks
    st.append(P("3. Can we trust the run? (checks)", "h1"))
    if checks:
        st.append(table([["#", "Check", "Result", "Detail"]] +
                        [[c["id"], c["check"], c["status"], c["detail"]] for c in checks],
                        widths=[12 * mm, 62 * mm, 16 * mm, 84 * mm]))
    else:
        st.append(P("No checks file found."))

    # extra sections (validation worlds)
    for sec in extra_sections or []:
        st += sec

    # 4. back-test
    if bt:
        st.append(P("4. Back-test: can the engine find sleeping beauties before they woke up?", "h1"))
        st.append(P(f"Screened {fmt(bt.get('n_screened'))} old papers; {fmt(bt.get('n_eligible'))} met the "
                    f"sleeping-beauty rules; {fmt(bt.get('n_selected_all'))} selected; {fmt(bt.get('n_in_split'))} in "
                    f"this part; {fmt(bt.get('n_usable'))} usable. Exclusions: "
                    f"{', '.join(f'{k}: {v}' for k, v in (bt.get('exclusions') or {}).items()) or 'none'}."))
        mt = bt.get("method_table", [])
        if mt:
            k = cfg_k(run)
            st.append(table([["Method", "n", "hit@1", "hit@5", f"hit@{k}", "hit@50", "MRR", "MRR 95% CI", "median rank"]] +
                            [[r["method"], r["n"], fmt(r.get("hit@1"), True), fmt(r.get("hit@5"), True),
                              fmt(r.get(f"hit@{k}"), True), fmt(r.get("hit@50"), True), fmt(r["MRR"]),
                              r["MRR_95CI"], fmt(r["median_rank"])] for r in mt]))
            st.append(P("hit@k = share of items where the real sleeping beauty is in the top k. MRR = average of "
                        "1 / rank (1.0 = always first). Random = the floor.", "small"))
        if pr:
            st.append(P(f"Minimum detectable effect: with {pr['n']} items, a true hit rate of "
                        f"{fmt(pr.get('minimum_detectable_rate_80pct_power'), True)} would be detected 80% of the time. "
                        "A non-significant result below that is inconclusive, not evidence of no effect."))
        fig = d / "figures" / "backtest_hit_at_k.png"
        if fig.exists():
            st += [Image(str(fig), width=150 * mm, height=86 * mm),
                   P("Share of sleeping beauties found within the top k, for each method. Dashed line: preregistered k.", "small")]
        sec = bt.get("secondary") or {}
        if sec:
            st.append(P("Does the AI reading add value over search alone?", "h2"))
            st.append(table([["Comparison", "only engine hit", "only other hit", "p (exact)", "p (Holm)"]] +
                            [[k2, v["a_only"], v["b_only"], fmt(v["p_two_sided"]), fmt(v["p_holm"])] for k2, v in sec.items()]))
        st.append(P("Leakage checks", "h2"))
        lk = []
        sm = bt.get("sensitivity_memorization")
        if sm:
            lk.append(f"Recognition probe: {sm['n_memorized']} sleeping beauties named; decoy false-recognition rate "
                      f"{fmt(sm.get('decoy_false_recognition_rate'), True)}. Without recognized items: "
                      f"{sm.get('clean_hits', 'n/a')} of {sm.get('n_clean', 'n/a')} hits (p = {fmt(sm.get('clean_p'))}).")
        dg = bt.get("disguise")
        if dg:
            lk.append(f"Disguised text ({dg['n']} items): mean position {fmt(dg['mean_rank_original'])} original vs "
                      f"{fmt(dg['mean_rank_disguised'])} disguised; worse in {fmt(dg['share_worse_when_disguised'], True)} "
                      f"of items; p = {fmt(dg['wilcoxon_p_worse'])}.")
        lk.append(f"Prompt leak scan: {bt.get('n_leaks', 0)} leaks in texts shown to the engine.")
        st += bullets(lk)

    # 5. gate
    if gate:
        st.append(P("5. Known-answer gate: which AI models can tell a known answer from a decoy?", "h1"))
        st.append(P("Each model scored the real sleeping beauty and 5 decoys against the need that later woke it. "
                    "AUC 0.5 = no better than chance; 1.0 = always right. A model counts only if AUC is above 0.5 with "
                    "p below the preregistered alpha, on enough items, and its answers are not collapsed."))
        st.append(table([["Model", "Role", "Items", "AUC", "p", "Same-answer share", "Decision"]] +
                        [[f"{g['model_name']} ({g['model']})", g["role"], g["n_items"], fmt(g["auc"]),
                          fmt(g["p_one_sided"]), fmt(g["largest_identical_share"], True),
                          ("PASS" if g["passed"] else "FAIL") + f": {g['reason']}"] for g in gate],
                        widths=[48 * mm, 16 * mm, 12 * mm, 14 * mm, 14 * mm, 22 * mm, 48 * mm]))

    # 6. forward
    if fw:
        st.append(P("6. Forward test: forgotten old papers for open problems", "h1"))
        st.append(P(f"Judges used: {', '.join(fw.get('judges_used', [])) or 'none'}. Dropped: "
                    f"{', '.join(f'{k} ({v})' for k, v in (fw.get('judges_dropped') or {}).items()) or 'none'}."))
        if fw.get("testable"):
            hb = fw.get("hits_by_group", {})
            st.append(table([["Group", "Items", "Hits (preregistered rule)"]] +
                            [[g, v[1], f"{v[0]}"] for g, v in hb.items()]))
            tt = fw.get("tests", {})
            rows = [["Test", "Engine", "Control", "Difference", "p", "p (Holm)"]]
            for name, t in tt.items():
                if "difference" in t:
                    rows.append([name, fmt(t["mean_treat"]), fmt(t["mean_control"]), fmt(t["difference"]),
                                 fmt(t["p_one_sided"]), fmt(t.get("p_holm"))])
            st.append(table(rows))
            st.append(P(f"Judge agreement (Krippendorff's alpha, ordinal): applicability "
                        f"{fmt(fw.get('krippendorff_alpha_applicability'))}, novelty "
                        f"{fmt(fw.get('krippendorff_alpha_novelty'))}. Below 0.40 the forward test counts as exploratory only."))
            fig = d / "figures" / "forward_applicability_by_group.png"
            if fig.exists():
                st += [Image(str(fig), width=120 * mm, height=72 * mm),
                       P("Blind judge ratings by group (1-5).", "small")]
            sl = d / "results" / "forward_items_scored.csv"
            if sl.exists():
                df = pd.read_csv(sl)
                top = df[df.group == "engine"].sort_values(["hit", "mean_applicability"], ascending=False).head(10)
                if len(top):
                    st.append(P("Top engine leads (a lead to check, not a discovery)", "h2"))
                    st.append(table([["Problem", "Paper", "Year", "Cited", "Rating", "Hit"]] +
                                    [[r.problem, str(r.title)[:90], r.year, r.cited_by_count,
                                      fmt(r.mean_applicability), "yes" if r.hit else "no"] for r in top.itertuples()],
                                    widths=[16 * mm, 96 * mm, 12 * mm, 12 * mm, 14 * mm, 10 * mm]))

    # 7. problems found
    st.append(P("7. Problems found, and what was done", "h1"))
    notes = list(run.notes)
    fails = [c for c in checks if c["status"] == "FAIL"]
    items = [f"Check {c['id']} failed: {c['check']} ({c['detail']})." for c in fails] + notes
    issues = ROOT / "ISSUES.md"
    st += bullets(items or ["No new problems were found in this run."])
    if issues.exists():
        st.append(P("The full running list of problems, with status, is in ISSUES.md in the project.", "small"))

    # 8. can / cannot say
    st.append(P("8. What we can and cannot say", "h1"))
    st += bullets([
        "We can say how the engine behaves on these items, and every number can be rebuilt from the saved files.",
        "We cannot say yet whether it works on the locked items: exploratory items were used to check the method."
        if kind == "exploratory" else "Results apply to the items and models tested here.",
        "Today's AI models were trained on text written after these papers woke up. The recognition probe and the "
        "disguised-text check reduce this problem but cannot remove it, so a positive back-test is an upper bound.",
        "AI judges are not human experts. A forward-test hit is a lead for experts to check, not a rediscovery."])

    # 9. words
    st.append(P("9. Words used", "h1"))
    st.append(table([["Word", "Meaning"],
                     ["Sleeping beauty", "A paper ignored for years, then suddenly cited a lot (Ke et al., 2015)."],
                     ["Beauty coefficient B", "How long and how deeply a paper slept before its citation peak."],
                     ["Awakening year", "The year the citation curve turned upward."],
                     ["Need statement", "What the waking field was struggling with, built only from the year before waking."],
                     ["Decoy", "A real old paper from the same field and era, used to hide the sleeping beauty."],
                     ["hit@10", "The sleeping beauty is in the engine's top 10."],
                     ["Known-answer gate", "A model must show it can pick known answers before its scores count."],
                     ["Disguised text", "The same paper rewritten by another AI so its wording cannot be recognized."],
                     ["Development / locked", "20% of items for checking the method; 80% kept for the preregistered test."],
                     ["SHA-256", "A file fingerprint. If one byte changes, the fingerprint changes."]],
                    widths=[40 * mm, 134 * mm]))

    # 10. fingerprints
    st.append(P("10. How to check this report", "h1"))
    st.append(table([["Item", "Value"], ["Run", run.run_id], ["Code SHA-256", code_sha256()],
                     ["Config SHA-256", sha256_json(run.config)], ["Seed", str(run.config.get("seed"))],
                     ["Preregistration check", run.prereg.get("status")],
                     ["Freeze bundle", str(run.prereg.get("freeze_bundle_sha256") or "not frozen yet")]],
                    widths=[40 * mm, 134 * mm]))
    st.append(P("The SHA-256 of this PDF is in manifest.json and SHA256SUMS next to it. "
                "Run `python run.py verify <run folder>` to check every file.", "small"))

    # 11. FAQ
    st.append(P("11. Common questions", "h1"))
    st.append(table([["Question", "Short answer"],
                     ["Has anyone looked at the locked items?", "No analysis has. The code refuses to process them before "
                      "the freeze, and their titles are blanked in saved tables."],
                     ["Could the AI just remember famous papers?", "Possibly; that is why there is a recognition probe, a "
                      "disguised-text check and a sensitivity analysis without recognized items."],
                     ["Why trust the AI judges?", "Only judges that pass the known-answer gate and do not collapse to one "
                      "answer are used; their agreement is measured."],
                     ["Did an AI do the research?", "No. The questions, hypotheses and design choices are the author's. "
                      "An AI assistant helped write code and documents under the author's direction."]],
                    widths=[55 * mm, 119 * mm]))

    doc = SimpleDocTemplate(str(out), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm,
                            bottomMargin=18 * mm, title=title, author=a["name"],
                            subject=STUDY_TITLE, creator=f"Wake-up Engine v{VERSION}")
    doc.build(st, onFirstPage=on_page, onLaterPages=on_page)
    return out


def cfg_k(run) -> int:
    return int(run.config["backtest"]["hit_k"])
