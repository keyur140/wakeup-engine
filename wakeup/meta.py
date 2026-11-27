# Wake-up Engine: finding forgotten science that already solves today's problems
# Author: KEYUR SHAILESHKUMAR PATEL
# ORCID: https://orcid.org/0009-0008-5261-043X
# Affiliations: (1) MSc Artificial Intelligence student, Department of Computer Science,
#               Brunel University London, UK; (2) Independent researcher
# Note: Conducted independently; not an official Brunel University London project.
# License: MIT (see LICENSE)
"""Author and project metadata, written into every manifest, report and data card."""
from . import __version__

PROJECT_TITLE = "Wake-up Engine: finding forgotten science that already solves today's problems"
STUDY_TITLE = ("Wake-up Engine: A Preregistered Computational Test of Deliberately "
               "Waking Science's Sleeping Beauties")
VERSION = __version__

AUTHOR = {
    "name": "KEYUR SHAILESHKUMAR PATEL",
    "given_names": "KEYUR SHAILESHKUMAR",
    "family_names": "PATEL",
    "orcid": "https://orcid.org/0009-0008-5261-043X",
    "affiliations": [
        "MSc Artificial Intelligence student, Department of Computer Science, "
        "Brunel University London, UK",
        "Independent researcher",
    ],
    "note": "Conducted independently; not an official Brunel University London project.",
}

AI_USE_STATEMENT = (
    "AI assistance: Code and draft text were prepared with help from an AI assistant "
    "(Claude, Anthropic) under the author's direction. All design decisions, hypotheses "
    "and hit criteria were chosen by the author. The author takes full responsibility "
    "for the work."
)

DATA_LICENSE = "CC BY 4.0"
CODE_LICENSE = "MIT"


def author_block_markdown() -> str:
    a = AUTHOR
    return (
        f"**{a['name']}**  \n"
        f"ORCID: {a['orcid']}  \n"
        f"(1) {a['affiliations'][0]}  \n"
        f"(2) {a['affiliations'][1]}  \n"
        f"*{a['note']}*"
    )
