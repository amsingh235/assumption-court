"""Evidence retrieval: DuckDuckGo (`ddgs`) + Wikipedia REST API. Free, no keys.

Every pool item carries a VERBATIM quote (1-3 sentences copied from the snippet/extract).
RETRIEVAL_PROVIDER=fake returns clearly-labelled placeholder items for offline development.
"""
from __future__ import annotations

import hashlib
import logging
import re
from typing import Optional
from urllib.parse import quote as urlquote

import httpx
from pydantic import BaseModel

from app.config import get_settings
from app.models import utcnow

log = logging.getLogger(__name__)

WIKI_UA = "AssumptionCourt/0.1 (https://github.com/amsingh235/assumption-court)"
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(])")


class PoolItem(BaseModel):
    id: str = ""
    query: str
    source_url: str
    source_title: str
    retrieved_quote: str
    retrieved_at: str


def verbatim_quote(text: str, max_sentences: int = 3, max_chars: int = 450) -> str:
    """First 1-3 sentences of `text`, copied verbatim (never paraphrased)."""
    text = " ".join(text.split())
    if not text:
        return ""
    sentences = _SENTENCE_END.split(text)
    out = ""
    for sentence in sentences[:max_sentences]:
        candidate = f"{out} {sentence}".strip()
        if out and len(candidate) > max_chars:
            break
        out = candidate
    if len(out) > max_chars:  # a single very long sentence: cut on a word boundary
        out = out[:max_chars].rsplit(" ", 1)[0]
    assert out in text  # verbatim guarantee
    return out


# ---------------------------------------------------------------- live sources

def search_ddg(query: str, max_results: int) -> list[PoolItem]:
    from ddgs import DDGS

    items: list[PoolItem] = []
    for hit in DDGS().text(query, max_results=max_results) or []:
        quote = verbatim_quote(hit.get("body", ""))
        if quote and hit.get("href"):
            items.append(PoolItem(query=query, source_url=hit["href"], source_title=hit.get("title", ""),
                                  retrieved_quote=quote, retrieved_at=utcnow()))
    return items


def search_wikipedia(query: str, max_results: int = 1) -> list[PoolItem]:
    headers = {"User-Agent": WIKI_UA}
    items: list[PoolItem] = []
    with httpx.Client(headers=headers, timeout=15, follow_redirects=True) as client:
        found = client.get("https://en.wikipedia.org/w/rest.php/v1/search/page",
                           params={"q": query, "limit": max_results})
        found.raise_for_status()
        for page in found.json().get("pages", []):
            summary = client.get(f"https://en.wikipedia.org/api/rest_v1/page/summary/{urlquote(page['key'], safe='')}")
            if summary.status_code != 200:
                continue
            data = summary.json()
            quote = verbatim_quote(data.get("extract", ""))
            url = data.get("content_urls", {}).get("desktop", {}).get("page") or \
                f"https://en.wikipedia.org/wiki/{urlquote(page['key'])}"
            if quote:
                items.append(PoolItem(query=query, source_url=url, source_title=f"Wikipedia: {data.get('title', page['title'])}",
                                      retrieved_quote=quote, retrieved_at=utcnow()))
    return items


# ---------------------------------------------------------------- fake source (offline dev only)

# (source kind, quote). Kind drives the fake Judge's source tier; wording drives the fake debaters' lean.
_FAKE_TEMPLATES = [
    ("gov", "A 2025 official statistics release on {q} reports figures consistent with the claim."),
    ("news", "A 2024 industry report on {q} finds the claim does not hold in most markets."),
    ("blog", "A 2019 company blog post on {q} argues the opposite of the common assumption."),
    ("unknown", "An undated forum summary on {q} repeats the claim without data."),
    ("gov", "A 2025 academic study of {q} finds evidence against the claim."),
    ("news", "A 2024 news analysis of {q} finds support for the claim."),
]


def search_fake(query: str, max_results: int) -> list[PoolItem]:
    """Deterministic placeholder evidence. Titles and URLs are marked FAKE and use the reserved .invalid TLD."""
    digest = int(hashlib.md5(query.encode()).hexdigest(), 16)
    slug = re.sub(r"[^a-z0-9]+", "-", query.lower()).strip("-")[:40]
    items = []
    for i in range(max_results):
        kind, template = _FAKE_TEMPLATES[(digest >> (4 * i)) % len(_FAKE_TEMPLATES)]
        items.append(PoolItem(
            query=query,
            source_url=f"https://offline.invalid/{kind}/{slug}-{i}",
            source_title=f"[FAKE OFFLINE SOURCE] {query[:60]}",
            retrieved_quote=template.format(q=query.rstrip(".?!")),
            retrieved_at=utcnow(),
        ))
    return items


# ---------------------------------------------------------------- public API

def retrieve(queries: list[str], results_per_query: Optional[int] = None) -> tuple[list[PoolItem], list[str]]:
    """Run each query against the sources. Returns (deduplicated items, error messages). Never raises."""
    settings = get_settings()
    n = results_per_query or settings.results_per_query
    items: list[PoolItem] = []
    errors: list[str] = []
    for query in queries:
        sources = [("fake", lambda q: search_fake(q, n))] if settings.retrieval_provider == "fake" else [
            ("ddgs", lambda q: search_ddg(q, n)),
            ("wikipedia", lambda q: search_wikipedia(q, 1)),
        ]
        for name, fn in sources:
            try:
                items.extend(fn(query))
            except Exception as exc:  # network errors, rate limits, "No results found"
                errors.append(f"{name}: {query!r}: {type(exc).__name__}: {str(exc)[:160]}")
                log.warning("retrieval failed: %s", errors[-1])
    seen: set[str] = set()
    unique = []
    for item in items:
        if item.source_url not in seen:
            seen.add(item.source_url)
            unique.append(item)
    return unique, errors
