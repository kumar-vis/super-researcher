"""Bibliography enrichment for publish source indexes.

Fix (2026-10-29, authorized by the repo owner): compiled reports rendered
their References list from chunk metadata, whose "title" is the markdown
filename slug (e.g. "0010-rediscovering-lost-relationships-...markdown").
This module builds real bibliographic entries for every corpus source:

- base record from ``data/ingested.jsonl`` (real title / publisher / URL
  captured at seed time),
- PDF embedded metadata (title / author) from ``originals/*.pdf``,
- DOI detection in the converted markdown head, resolved against the
  Crossref API for authors / venue / year when reachable,
- year + "et al." author hints parsed from the seeded title string.

Enriched fields are merged into ``atlas/publish/source_index.json`` (under
each source's ``bib`` key plus flattened convenience fields) and written to
``atlas/publish/bibliography.json``. ``reporting.render_reference_list_item``
prefers these fields and never renders a raw filename.
"""

from __future__ import annotations

import json
import re
import urllib.request
from pathlib import Path
from typing import Any

from .config import atomic_write_json

DOI_RE = re.compile(r"10\.\d{4,9}/[-._;()/:A-Za-z0-9]+")
YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")
ET_AL_RE = re.compile(r"\(([A-Z][A-Za-zÀ-ÿ'’.-]+) et al\.?,?\s*((?:19|20)\d{2})\)")
SLUG_TITLE_RE = re.compile(r"^\d{4}-[a-z0-9][a-z0-9\-]*$")
FILENAME_LEAK_RE = re.compile(r"\.markdown\b|\.md\b|\.pdf\b", re.IGNORECASE)


def bibliography_path(corpus: Path) -> Path:
    return corpus / "atlas" / "publish" / "bibliography.json"


def looks_like_filename(title: str) -> bool:
    """True when a 'title' is really a filename slug, not a publication title."""
    text = (title or "").strip()
    if not text:
        return True
    if FILENAME_LEAK_RE.search(text):
        return True
    if SLUG_TITLE_RE.match(text):
        return True
    # Long hyphenated token with no spaces is a slug, not a title.
    if " " not in text and "-" in text and len(text) > 24:
        return True
    return False


def humanize_slug(title: str) -> str:
    """Last-resort readable title from a filename slug."""
    text = re.sub(r"^\d{4}-", "", (title or "").strip())
    text = text.replace("-", " ").strip()
    return text[:1].upper() + text[1:] if text else "Untitled source"


def _ingested_records(corpus: Path) -> dict[str, dict[str, Any]]:
    path = corpus / "data" / "ingested.jsonl"
    records: dict[str, dict[str, Any]] = {}
    if not path.exists():
        return records
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        sid = str(row.get("source_id", "")).zfill(4)
        if sid:
            records[sid] = row
    return records


def _pdf_metadata(pdf_path: Path) -> dict[str, str]:
    try:
        import pymupdf  # PyMuPDF >= 1.24 name; falls back below
    except ImportError:  # pragma: no cover
        try:
            import fitz as pymupdf  # type: ignore
        except ImportError:
            return {}
    try:
        with pymupdf.open(pdf_path) as doc:
            meta = doc.metadata or {}
        return {
            "title": str(meta.get("title") or "").strip(),
            "author": str(meta.get("author") or "").strip(),
        }
    except Exception:
        return {}


def _markdown_head(corpus: Path, source_id: str) -> str:
    md_dir = corpus / "markdown"
    if not md_dir.exists():
        return ""
    matches = sorted(md_dir.glob(f"{source_id}-*.md"))
    if not matches:
        return ""
    return matches[0].read_text(encoding="utf-8", errors="replace")[:6000]


def _crossref(doi: str, timeout: float = 8.0) -> dict[str, Any] | None:
    url = f"https://api.crossref.org/works/{urllib.request.quote(doi, safe='')}"
    req = urllib.request.Request(url, headers={"User-Agent": "SuperResearcher/bibliography (mailto:research@localhost)"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8", errors="replace"))
    except Exception:
        return None
    msg = payload.get("message") or {}
    authors = []
    for author in msg.get("author") or []:
        name = " ".join(part for part in [author.get("given", ""), author.get("family", "")] if part).strip()
        if name:
            authors.append(name)
    year = None
    for key in ("published-print", "published-online", "issued", "created"):
        parts = ((msg.get(key) or {}).get("date-parts") or [[]])[0]
        if parts:
            year = parts[0]
            break
    titles = msg.get("title") or []
    return {
        "authors": authors,
        "title": titles[0] if titles else "",
        "venue": (msg.get("container-title") or [""])[0],
        "year": year,
        "doi": msg.get("DOI") or doi,
    }


def extract_bibliography(corpus: Path, use_crossref: bool = True) -> dict[str, dict[str, Any]]:
    """Build a bibliographic entry per source_id for the corpus."""
    ingested = _ingested_records(corpus)
    entries: dict[str, dict[str, Any]] = {}
    originals = corpus / "originals"
    pdfs = {p.name[:4]: p for p in originals.glob("*.pdf")} if originals.exists() else {}
    for source_id, record in sorted(ingested.items()):
        entry: dict[str, Any] = {
            "source_id": source_id,
            "title": (record.get("title") or "").strip(),
            "publisher": (record.get("publisher") or "").strip(),
            "url": (record.get("url") or "").strip(),
            "authors": [],
            "venue": "",
            "year": None,
            "doi": "",
        }
        # Year / et-al. hints embedded in seeded titles, e.g. "(Eriksen et al., 2014)".
        m = ET_AL_RE.search(entry["title"])
        if m:
            entry["authors"] = [f"{m.group(1)} et al."]
            entry["year"] = int(m.group(2))
            entry["title"] = ET_AL_RE.sub("", entry["title"]).rstrip(" (").strip()
        if entry["year"] is None:
            ym = YEAR_RE.search(entry["title"]) or YEAR_RE.search(entry["publisher"])
            if ym:
                entry["year"] = int(ym.group(0))
        # PDF metadata can supply authors when the seed record cannot.
        pdf_path = pdfs.get(source_id)
        if pdf_path is not None:
            meta = _pdf_metadata(pdf_path)
            if meta.get("author") and not entry["authors"]:
                # Drop scanner/uploader artifacts (e.g. "Catherine_Kuziel").
                candidates = [a.strip() for a in re.split(r";|, and ", meta["author"]) if a.strip()]
                entry["authors"] = [a for a in candidates if "_" not in a]
            if meta.get("title") and looks_like_filename(entry["title"]):
                entry["title"] = meta["title"]
        # DOI from the converted markdown head -> Crossref enrichment.
        head = _markdown_head(corpus, source_id)
        doi_match = DOI_RE.search(head) or DOI_RE.search(entry["url"])
        if doi_match:
            doi = doi_match.group(0).rstrip(").,")
            doi = re.sub(r"(_|/pdf|\.pdf)$", "", doi)
            entry["doi"] = doi
            if use_crossref:
                cross = _crossref(doi)
                if cross:
                    if cross["authors"]:
                        entry["authors"] = cross["authors"]
                    if cross["title"] and not looks_like_filename(cross["title"]):
                        entry["title"] = cross["title"]
                    entry["venue"] = cross["venue"] or entry["venue"]
                    entry["year"] = cross["year"] or entry["year"]
        if not entry["venue"]:
            entry["venue"] = entry["publisher"]
        if looks_like_filename(entry["title"]):
            entry["title"] = humanize_slug(entry["title"])
        entries[source_id] = entry
    return entries


def format_reference(entry: dict[str, Any], number: int, anchor_id: str, source_id: str) -> str:
    """Render one References-list markdown item from an enriched entry."""
    authors = ", ".join(a for a in entry.get("authors") or [] if a)
    year = entry.get("year")
    title = (entry.get("title") or "Untitled source").strip()
    venue = (entry.get("venue") or entry.get("publisher") or "").strip()
    doi = (entry.get("doi") or "").strip()
    url = (entry.get("url") or "").strip()
    head = ""
    if authors:
        head = authors
        if year:
            head += f" ({year})"
    elif year:
        head = f"({year})"
    parts = [p for p in [head, title] if p]
    text = ". ".join(parts).rstrip(".") + "."
    if venue and venue.lower() not in title.lower():
        text += f" {venue}."
    if doi:
        text += f" https://doi.org/{doi}"
    elif url:
        text += f" {url}"
    text += f" Source S{source_id}."
    return f"{number}. []{{#{anchor_id}}} " + text


def validate_reference_item(text: str) -> list[str]:
    """Hard-rule violations for a rendered reference item."""
    problems = []
    if ".markdown" in text or ".md)" in text:
        problems.append("reference contains a markdown filename")
    if re.search(r"\b\d{4}-[a-z0-9]+(?:-[a-z0-9]+){3,}", text):
        problems.append("reference contains a raw filename slug")
    return problems


def enrich_source_index(corpus: Path, use_crossref: bool = True) -> dict[str, Any]:
    """Merge bibliography entries into the publish source index on disk."""
    from . import publish  # local import to avoid a cycle

    entries = extract_bibliography(corpus, use_crossref=use_crossref)
    index_path = publish.publish_source_index_path(corpus)
    index = publish.read_json_object(index_path)
    sources = index.get("sources") or {}
    for source_id, entry in entries.items():
        source = sources.get(source_id)
        if source is None:
            continue
        source["bib"] = entry
        # Flattened fields the renderer prefers over chunk metadata.
        if entry.get("title") and not looks_like_filename(entry["title"]):
            source["bib_title"] = entry["title"]
        if entry.get("publisher"):
            source["bib_publisher"] = entry["publisher"]
        if entry.get("url"):
            source["bib_url"] = entry["url"]
    if sources:
        index["sources"] = sources
        atomic_write_json(index_path, index)
    atomic_write_json(bibliography_path(corpus), {"sources": entries})
    return {"sources_enriched": len(entries), "bibliography": entries}
