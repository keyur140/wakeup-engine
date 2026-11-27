# Wake-up Engine: finding forgotten science that already solves today's problems
# Author: KEYUR SHAILESHKUMAR PATEL
# ORCID: https://orcid.org/0009-0008-5261-043X
# Affiliations: (1) MSc Artificial Intelligence student, Department of Computer Science,
#               Brunel University London, UK; (2) Independent researcher
# Note: Conducted independently; not an official Brunel University London project.
# License: MIT (see LICENSE)
"""OpenAlex client tests with a fake HTTP session (no network)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from wakeup.openalex import OpenAlex, reconstruct_abstract
from wakeup.runlog import load_config


class FakeResp:
    def __init__(self, data):
        self.status_code, self._d, self.text = 200, data, ""

    def json(self):
        return self._d


class FakeSession:
    def __init__(self):
        self.calls = []
        self.headers = {}

    def get(self, url, params=None, timeout=None):
        self.calls.append(url)
        if "group_by" in url:
            return FakeResp({"group_by": [{"key": "1950", "count": 3}, {"key": "1990", "count": 40},
                                          {"key": "unknown", "count": 1}]})
        if "cursor=%2A" in url:
            return FakeResp({"meta": {"next_cursor": "abc"}, "results": [work("W1"), work("W2")]})
        return FakeResp({"meta": {"next_cursor": None}, "results": [work("W3")]})


def work(i):
    return {"id": f"https://openalex.org/{i}", "title": "T", "publication_year": 1950,
            "abstract_inverted_index": {"hello": [0], "world": [1]}, "authorships": [],
            "primary_topic": {"id": "https://openalex.org/T1", "field": {"id": "https://openalex.org/fields/13"}}}


def test_paging_group_by_and_cache(tmp_path):
    oa = OpenAlex(load_config(), cache_dir=tmp_path)
    oa.min_interval = 0
    oa.session = FakeSession()
    ws = oa.list_works({"publication_year": "<1990"}, 3, search="phage")
    assert [w["id"] for w in ws] == ["W1", "W2", "W3"]
    assert ws[0]["abstract"] == "hello world" and ws[0]["field_id"] == "https://openalex.org/fields/13"
    h = oa.citations_by_year("W1")
    assert h == {1950: 3, 1990: 40}
    n = len(oa.session.calls)
    oa.citations_by_year("W1")           # served from cache
    assert len(oa.session.calls) == n


def test_reconstruct_abstract_order():
    assert reconstruct_abstract({"b": [1], "a": [0, 2]}) == "a b a"
