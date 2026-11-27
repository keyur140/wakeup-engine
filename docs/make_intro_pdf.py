# Wake-up Engine: finding forgotten science that already solves today's problems
# Author: KEYUR SHAILESHKUMAR PATEL
# ORCID: https://orcid.org/0009-0008-5261-043X
# Affiliations: (1) MSc Artificial Intelligence student, Department of Computer Science,
#               Brunel University London, UK; (2) Independent researcher
# Note: Conducted independently; not an official Brunel University London project.
# License: MIT (see LICENSE)
"""Builds docs/WakeUpEngine_Project_Introduction.pdf: the whole project in plain words, one section.

Run:  python docs/make_intro_pdf.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from reportlab.lib.pagesizes import A4  # noqa: E402
from reportlab.lib.units import mm  # noqa: E402
from reportlab.platypus import SimpleDocTemplate, Spacer  # noqa: E402

from wakeup.meta import AI_USE_STATEMENT, AUTHOR, VERSION  # noqa: E402
from wakeup.pdfreport import QUIET, P, bullets, table  # noqa: E402

OUT = ROOT / "docs" / "WakeUpEngine_Project_Introduction.pdf"


def build() -> Path:
    a = AUTHOR
    st = [P("Wake-up Engine: an introduction in plain words", "title"),
          P("Can AI find forgotten science that already solves today's problems?", "sub"), Spacer(1, 8),
          P(f"<b>{a['name']}</b>"), P(f"ORCID: {a['orcid']}"), P(a["affiliations"][0]), P(a["affiliations"][1]),
          P(f"<i>{a['note']}</i>"), Spacer(1, 4),
          P(f"Software version {VERSION} &middot; Written 3 November 2026, before any real data were collected.", "small"),
          Spacer(1, 6),
          P("The project in one section", "h1")]

    def h(t):
        st.append(P(t, "h2"))

    def p(t):
        st.append(P(t))

    h("The problem: science forgets")
    p("Every year, millions of research papers are published. Most are read for a while and then forgotten. "
      "A few of them hold ideas that turn out to be important much later, when someone finally needs them. "
      "Researchers call these papers <b>sleeping beauties</b>: a paper sleeps for years with almost no "
      "citations, then suddenly wakes up and is cited a lot.")
    p("Famous examples exist. Peyton Rous showed in 1911 that a virus could cause cancer in chickens; the work "
      "was largely set aside and he received the Nobel Prize 55 years later, in 1966. Ke and colleagues (2015, "
      "<i>PNAS</i>) measured how often this happens across 22 million papers and found that sleeping beauties are "
      "far more common than people thought.")
    p("The sad part is that every study so far has found these papers only <b>after</b> they woke up. While a "
      "paper sleeps, the problem it could help with stays unsolved, sometimes for decades. Nobody has tested "
      "whether we can wake them <b>on purpose</b>.")

    h("The idea")
    p("Today's AI language models can read a paper's summary and judge whether it fits a problem. So the question "
      "of this project is simple: <b>if we describe a problem to an AI, can it pick out the forgotten old paper "
      "that holds the answer?</b> I call the system that does this the <b>Wake-up Engine</b>.")
    p("An idea like this is easy to claim and hard to prove. A demo that finds one nice old paper proves "
      "nothing, because we cannot tell luck from skill. So the project is built as a careful scientific test, "
      "written down in advance (preregistered) on the Open Science Framework (OSF), with every number checkable.")

    h("How the engine works")
    p("The engine gets a short description of a problem. It searches a free, open database of scientific papers "
      "(OpenAlex) in two ways: by matching words (BM25 search) and by matching meaning (an embedding model). It "
      "combines both lists. Then an AI model reads the top 50 papers one by one and scores how well each fits "
      "the problem, from 0 to 10. The papers with the best scores are the engine's picks.")

    h("Study 1, the back-test: can it find papers we already know about?")
    p("To test whether the engine works, we need cases where we know the right answer. Sleeping beauties give "
      "us exactly that. The code finds about 100 real sleeping beauties in OpenAlex using the Ke et al. formula "
      "(the beauty coefficient). For each one, it goes back in time to the year <b>before</b> the paper woke up "
      "and asks: what was the field that later woke it struggling with at that moment? It reads up to 20 "
      "summaries from that year, written by people who had <b>not</b> cited the sleeping beauty, and turns them "
      "into a short description of the need.")
    p("Then the sleeping beauty is hidden among 999 other real papers from the same field and the same years "
      "(decoys). Names, years and links are removed, so the AI cannot simply look them up. If the engine puts the "
      "real sleeping beauty in its <b>top 10 out of 1,000</b>, that counts as a hit. By luck alone, a hit happens "
      "1% of the time.")
    p("There are two main tests, and both must pass before we say the engine reads for meaning:")
    st.extend(bullets(["<b>H1a:</b> the engine gets more hits than luck would give.",
                       "<b>H1b:</b> the engine gets more hits than plain search without the AI reading. This "
                       "matters because our synthetic tests showed that simple word matching can sometimes beat "
                       "luck with no understanding at all."]))

    h("Study 2, the forward test: can it find new leads for a real problem?")
    p("The back-test looks at the past. The forward test looks at today. I chose <b>antibiotic resistance</b>, "
      "because it kills more than a million people a year (an estimated 1.27 million deaths directly caused in "
      "2019, Murray et al., 2022, <i>The Lancet</i>) and because a lot of early work, such as phage therapy, "
      "was set aside once antibiotics worked. That makes it a good place to look for forgotten answers.")
    p("The study has 20 open problems, for example killing dormant 'persister' bacteria, breaking up biofilms, "
      "and treating drug-resistant gonorrhoea. For each one, the engine searches papers published <b>before "
      "1990</b> that have <b>25 citations or fewer</b> (forgotten papers), and picks its top 5.")

    h("Study 3, the blind AI panel: are the engine's picks really better?")
    p("This study uses no human experts, so three AI judges (none from the engine's model family) rate each paper's "
      "usefulness and novelty from 1 to 5. They also rate 10 random forgotten papers per problem, mixed in with "
      "the engine's picks. The judges never learn which papers the engine chose. If the engine's picks score "
      "higher than the random ones, that is evidence the engine finds useful leads. We also measure how much "
      "the judges agree with each other (Krippendorff's alpha).")

    h("How the project stays honest")
    p("I designed this project using lessons from my earlier work, where I saw that an AI can pass every "
      "software check and still be useless: one scoring model was no better than a coin flip, and one AI judge "
      "gave the same score to 1,152 different items. So the Wake-up Engine has these safeguards:")
    st.append(table([["Safeguard", "What it does, simply"],
                     ["Preregistration", "The plan, the rules for a hit and the tests are fixed and published "
                      "before the real test is run."],
                     ["The lock", "20% of sleeping beauties are for trying out the method; 80% are locked away "
                      "for the real test. A fixed SHA-256 rule decides which is which, and the code refuses to "
                      "open the locked part before the plan is frozen."],
                     ["Known-answer gate", "Before any AI's scores count, it must show it can tell a real "
                      "sleeping beauty from decoys. AIs that fail are dropped."],
                     ["Same-answer rule", "An AI that gives almost every paper the same score is dropped."],
                     ["Memory check", "We ask the AI whether it recognizes each hidden paper, and repeat the test "
                      "without the ones it knows."],
                     ["Disguised text", "A different AI rewrites the papers in new words. If the engine only "
                      "finds the paper with its original wording, it was recognizing, not reasoning."],
                     ["Leak scan", "Every text the AI sees is checked for years, names, links and IDs."],
                     ["Self-checks", "Eleven automatic checks recompute the key numbers a second way."],
                     ["Fingerprints", "Every file, prompt and AI reply is fingerprinted with SHA-256, so any "
                      "change is visible."]],
                    widths=[38 * mm, 136 * mm]))

    h("What we know so far (synthetic tests only)")
    p("Before using real data, I tested the whole system on <b>synthetic worlds</b>, which are made-up worlds "
      "where we know the right answer. This tests the machinery, not science:")
    st.extend(bullets([
        "When the answer was really there, the engine found it: 12 of 17 in its top 10, where luck would give "
        "about 10% in these smaller test sets.",
        "When there was nothing to find, it stayed quiet: only 1 false alarm in 40 empty worlds, within the "
        "expected 5%.",
        "When the AI cheated by remembering papers, the checks caught it: the memory check flagged all 17, and "
        "disguising the text pushed the cheater's average position from 1.3 to 5.3.",
        "Bad judges, one random and one that always gave the same score, were removed automatically.",
        "In the synthetic world the AI re-reading did <b>not</b> beat plain search (71% vs 94% hits). This is "
        "useful: test H1b caught it, which is exactly why H1b is now a main test."]))
    p("There are <b>no real results yet</b>. Next comes the exploratory run on real data, using only the 20% "
      "practice part and 4 practice problems. Then the plan is frozen and registered on OSF, and only then does "
      "the real (confirmatory) test run.")

    h("What the possible results would mean")
    st.append(table([["If...", "It means"],
                     ["Both main back-tests pass", "To our knowledge, the first preregistered evidence that AI can "
                      "match forgotten papers to the needs that later woke them, using only what was known at the time."],
                     ["The forward test passes", "A shortlist of forgotten pre-1990 ideas against antibiotic "
                      "resistance, rated more useful than random old papers. Each one is a lead for experts to check, "
                      "not a discovery."],
                     ["Nothing passes", "A trustworthy, open 'no', which shows where AI literature reading falls "
                      "short and stops others from overclaiming."]],
                    widths=[48 * mm, 126 * mm]))
    p("Whatever the outcome, three things last: free open-source software anyone can point at a new field, an "
      "open benchmark of sleeping beauties with their 'before' need statements, and a fully checkable record.")

    h("Honest limits")
    st.extend(bullets([
        "Today's AI models were trained on text written after these papers woke up. The checks reduce this "
        "problem but cannot remove it, so a positive back-test is the best case.",
        "AI judges are not human experts. A forward-test hit is a lead, not proof.",
        "The free database has fewer summaries for very old papers, so some sleeping beauties cannot be used."]))

    h("Cost, tools and who did what")
    p("The whole project costs $0. It uses OpenAlex (free, open data), free open-weights AI models on the Groq "
      "free tier (or on your own computer with Ollama), and open-source Python code (MIT licence). Anyone can "
      "download it, run it and get the same numbers.")
    p(f"<b>Use of AI tools.</b> {AI_USE_STATEMENT}")

    h("Words used")
    st.append(table([["Word", "Meaning"],
                     ["Sleeping beauty", "A paper ignored for years, then suddenly cited a lot."],
                     ["Back-test", "Testing a method on the past, where the answer is already known."],
                     ["Decoy", "A real old paper used to hide the sleeping beauty."],
                     ["Preregistration", "Publishing the plan before running the test, so nobody can change it after."],
                     ["p-value", "How surprising a result would be if the engine were only lucky. Small = unlikely luck."],
                     ["SHA-256", "A file fingerprint. Change one letter and the fingerprint changes."]],
                    widths=[38 * mm, 136 * mm]))

    footer = f"Wake-up Engine introduction - {a['name']} - ORCID {a['orcid'].split('/')[-1]} - page "

    def on_page(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(QUIET)
        canvas.drawString(18 * mm, 10 * mm, footer + str(doc.page))
        canvas.restoreState()

    doc = SimpleDocTemplate(str(OUT), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm,
                            bottomMargin=18 * mm, title="Wake-up Engine: an introduction in plain words",
                            author=a["name"], creator=f"Wake-up Engine v{VERSION}")
    doc.build(st, onFirstPage=on_page, onLaterPages=on_page)
    return OUT


if __name__ == "__main__":
    print(build())
