"""Retrieval sources — small stdlib HTTP clients for the knowledge bases the invention engine
grounds on (same set as inventor-studio-v3). Each `search_*` returns a list of Citation dicts;
every call is wrapped so a network error / timeout yields [] (v3 still runs offline).

Keyless & default: pubmed, arxiv, wikipedia. Optional/config: pubchem, uspto, github (GITHUB_TOKEN
for rate), searxng (SEARXNG_URL), jina (page reader). Parsers are pure so they unit-test offline.
"""

from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

UA = {"User-Agent": "bciv3-invention-engine/0.1 (research)"}


def _get(url: str, timeout: float = 8.0, headers: dict | None = None) -> str:
    req = urllib.request.Request(url, headers={**UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def _cite(source, title, url, snippet=""):
    return {"source": source, "title": str(title).strip()[:240],
            "url": url, "snippet": str(snippet).strip()[:300]}


# ---------- pure parsers (offline-testable) ----------
def parse_pubmed(esummary_json: dict, n: int) -> list[dict]:
    res = esummary_json.get("result", {})
    out = []
    for uid in res.get("uids", [])[:n]:
        d = res.get(uid, {})
        out.append(_cite("pubmed", d.get("title", uid),
                         f"https://pubmed.ncbi.nlm.nih.gov/{uid}/",
                         f"{d.get('source','')} {d.get('pubdate','')}"))
    return out


def parse_arxiv(atom_xml: str, n: int) -> list[dict]:
    ns = {"a": "http://www.w3.org/2005/Atom"}
    root = ET.fromstring(atom_xml)
    out = []
    for e in root.findall("a:entry", ns)[:n]:
        title = (e.findtext("a:title", default="", namespaces=ns) or "").strip()
        url = (e.findtext("a:id", default="", namespaces=ns) or "").strip()
        summ = (e.findtext("a:summary", default="", namespaces=ns) or "").strip()
        out.append(_cite("arxiv", title, url, summ))
    return out


def parse_wikipedia(search_json: dict, n: int) -> list[dict]:
    out = []
    for it in search_json.get("query", {}).get("search", [])[:n]:
        t = it.get("title", "")
        snip = it.get("snippet", "").replace("<span class=\"searchmatch\">", "").replace("</span>", "")
        out.append(_cite("wikipedia", t,
                         "https://en.wikipedia.org/wiki/" + urllib.parse.quote(t.replace(" ", "_")), snip))
    return out


# ---------- live searches (each returns [] on any failure) ----------
def search_pubmed(q: str, n: int = 3) -> list[dict]:
    try:
        key = os.environ.get("NCBI_API_KEY")
        p = urllib.parse.urlencode({"db": "pubmed", "term": q, "retmax": n, "retmode": "json",
                                    "sort": "relevance", **({"api_key": key} if key else {})})
        ids = json.loads(_get(f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?{p}")) \
            .get("esearchresult", {}).get("idlist", [])
        if not ids:
            return []
        sp = urllib.parse.urlencode({"db": "pubmed", "id": ",".join(ids), "retmode": "json",
                                     **({"api_key": key} if key else {})})
        return parse_pubmed(json.loads(_get(f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?{sp}")), n)
    except Exception:
        return []


def search_arxiv(q: str, n: int = 3) -> list[dict]:
    try:
        p = urllib.parse.urlencode({"search_query": f"all:{q}", "start": 0, "max_results": n})
        return parse_arxiv(_get(f"http://export.arxiv.org/api/query?{p}"), n)
    except Exception:
        return []


def search_wikipedia(q: str, n: int = 3) -> list[dict]:
    try:
        p = urllib.parse.urlencode({"action": "query", "list": "search", "srsearch": q,
                                    "srlimit": n, "format": "json"})
        return parse_wikipedia(json.loads(_get(f"https://en.wikipedia.org/w/api.php?{p}")), n)
    except Exception:
        return []


def search_pubchem(q: str, n: int = 3) -> list[dict]:
    try:
        url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{urllib.parse.quote(q)}/cids/JSON"
        cids = json.loads(_get(url)).get("IdentifierList", {}).get("CID", [])[:n]
        return [_cite("pubchem", f"PubChem CID {c}", f"https://pubchem.ncbi.nlm.nih.gov/compound/{c}") for c in cids]
    except Exception:
        return []


def search_uspto(q: str, n: int = 3) -> list[dict]:
    try:
        qy = urllib.parse.quote(json.dumps({"_text_any": {"patent_title": q}}))
        fl = urllib.parse.quote(json.dumps(["patent_number", "patent_title"]))
        opt = urllib.parse.quote(json.dumps({"per_page": n}))
        data = json.loads(_get(f"https://api.patentsview.org/patents/query?q={qy}&f={fl}&o={opt}"))
        return [_cite("uspto", p.get("patent_title", p.get("patent_number")),
                      f"https://patents.google.com/patent/US{p.get('patent_number')}") for p in (data.get("patents") or [])[:n]]
    except Exception:
        return []


def search_github(q: str, n: int = 3) -> list[dict]:
    try:
        tok = os.environ.get("GITHUB_TOKEN")
        h = {"Authorization": f"Bearer {tok}"} if tok else {}
        p = urllib.parse.urlencode({"q": q, "per_page": n, "sort": "stars"})
        data = json.loads(_get(f"https://api.github.com/search/repositories?{p}", headers=h))
        return [_cite("github", r.get("full_name"), r.get("html_url"), r.get("description") or "")
                for r in (data.get("items") or [])[:n]]
    except Exception:
        return []


def search_searxng(q: str, n: int = 3) -> list[dict]:
    base = os.environ.get("SEARXNG_URL")
    if not base:
        return []
    try:
        p = urllib.parse.urlencode({"q": q, "format": "json"})
        data = json.loads(_get(f"{base.rstrip('/')}/search?{p}"))
        return [_cite("searxng", r.get("title"), r.get("url"), r.get("content") or "")
                for r in (data.get("results") or [])[:n]]
    except Exception:
        return []


def read_page(url: str, timeout: float = 12.0) -> str:
    """Jina reader — fetch a URL as clean text (needs no key for r.jina.ai)."""
    try:
        return _get(f"https://r.jina.ai/{url}", timeout=timeout)[:8000]
    except Exception:
        return ""


SOURCES = {
    "pubmed": search_pubmed, "arxiv": search_arxiv, "wikipedia": search_wikipedia,
    "pubchem": search_pubchem, "uspto": search_uspto, "github": search_github, "searxng": search_searxng,
}
# All sources on by default; unconfigured ones (searxng without SEARXNG_URL) just return []. Override
# with BCIV3_SEARCH_SOURCES="pubmed,arxiv" to narrow.
DEFAULT_SOURCES = ["pubmed", "arxiv", "wikipedia", "pubchem", "uspto", "github", "searxng"]
