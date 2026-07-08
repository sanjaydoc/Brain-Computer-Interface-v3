"""Tests for the retrieval layer — pure parsers + graceful orchestration (no network in CI)."""

from __future__ import annotations

import bciv3
from bciv3.search import retrieve, build_context
from bciv3.search import sources as S


def test_pubmed_parser():
    payload = {"result": {"uids": ["111", "222"],
                          "111": {"title": "Gas vesicles as acoustic reporters", "source": "Nature", "pubdate": "2018"},
                          "222": {"title": "MAPseq barcoding", "source": "Cell", "pubdate": "2016"}}}
    out = S.parse_pubmed(payload, 5)
    assert len(out) == 2 and out[0]["source"] == "pubmed"
    assert "acoustic reporters" in out[0]["title"] and out[0]["url"].endswith("/111/")


def test_arxiv_parser():
    xml = """<feed xmlns="http://www.w3.org/2005/Atom">
      <entry><title>Expansion microscopy at scale</title>
        <id>http://arxiv.org/abs/2401.00001</id><summary>A method.</summary></entry></feed>"""
    out = S.parse_arxiv(xml, 5)
    assert len(out) == 1 and out[0]["source"] == "arxiv"
    assert out[0]["title"] == "Expansion microscopy at scale" and "2401.00001" in out[0]["url"]


def test_wikipedia_parser():
    payload = {"query": {"search": [{"title": "Connectome", "snippet": "a <span class=\"searchmatch\">map</span>"}]}}
    out = S.parse_wikipedia(payload, 5)
    assert out[0]["source"] == "wikipedia" and out[0]["title"] == "Connectome"
    assert "map" in out[0]["snippet"] and "Connectome" in out[0]["url"]


def test_build_context_format():
    cites = [{"source": "pubmed", "title": "T1", "url": "u1", "snippet": "s1"}]
    ctx = build_context(cites)
    assert ctx.startswith("PRIOR KNOWLEDGE") and "[pubmed] T1" in ctx and "u1" in ctx
    assert build_context([]) == ""


def test_retrieve_is_graceful_offline():
    # empty query / no sources → empty, never raises
    r = retrieve("", sources=[])
    assert r["context"] == "" and r["citations"] == [] and r["sources_used"] == []
    r2 = retrieve("anything", sources=["not_a_real_source"])
    assert r2["citations"] == [] and r2["sources_used"] == []


def test_retrieve_reports_per_source_status():
    # unknown sources are ignored; known-but-empty report a status (offline → 'error'/'no results')
    r = retrieve("connectome", sources=["arxiv", "not_real"])
    assert "not_real" not in r["per_source"]
    assert "arxiv" in r["per_source"]        # a human-readable status string either way


def test_record_carries_citation_fields():
    # ground=False → no network; the record still has the citation fields (empty)
    rec = bciv3.record("multiplexed_reporters", backend="fallback", ground=False, save=False)
    assert "citations" in rec and "sources_used" in rec and rec["grounded"] is False
    assert rec["score"]["passed"] is True        # simulator still ran as the last step
