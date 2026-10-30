"""Fresh Opening Summary stage (2026-10-29 harness fix).

Ghost Ships v1's Opening Summary was stitched mechanically from section
openings (``extract_section_summary``), so it repeated section text
verbatim — including the lifted line "Sections 1 and 2 used three words
as if they were one", which is meaningless out of context.

This stage generates the summary fresh, after compile, from per-section
abstracts (title + opening lines), via the normal LLM client. A verbatim
overlap guard rejects any draft sharing a >= ``OVERLAP_WORDS``-word run
with the compiled section text and regenerates with the offending
passage flagged (up to ``MAX_ATTEMPTS``). The accepted summary is written
to ``atlas/publish/opening_summary.md``; ``reporting`` uses it for the
summary box when present.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

OVERLAP_WORDS = 12
MAX_ATTEMPTS = 3
SELF_REFERENCE_RE = re.compile(r"\bSection\s+\d+\b|§\s*\d+|as (?:was )?recorded in\b", re.IGNORECASE)


def summary_override_path(corpus: Path) -> Path:
    return corpus / "atlas" / "publish" / "opening_summary.md"


def _normalise(text: str) -> list[str]:
    return re.findall(r"[a-z0-9'’]+", text.lower())


def longest_verbatim_overlap(summary: str, corpus_text: str, size: int = OVERLAP_WORDS) -> str:
    """Return the first >=size-word verbatim run shared with corpus_text."""
    summary_words = _normalise(summary)
    corpus_words = set()
    words = _normalise(corpus_text)
    corpus_shingles = {" ".join(words[i : i + size]) for i in range(len(words) - size + 1)}
    for i in range(len(summary_words) - size + 1):
        run = " ".join(summary_words[i : i + size])
        if run in corpus_shingles:
            return run
    return ""


def section_abstracts(corpus: Path, plan: dict[str, Any], state: dict[str, Any]) -> list[dict[str, str]]:
    completed = {item.get("section_id"): item for item in state.get("completed_sections", [])}
    abstracts = []
    for section in plan.get("sections", []):
        item = completed.get(section.get("section_id"))
        opening = ""
        if item and Path(item.get("path", "")).exists():
            raw = Path(item["path"]).read_text(encoding="utf-8", errors="replace")
            body = re.sub(r"^#{1,6}\s+.*$", "", raw, flags=re.MULTILINE)
            body = re.sub(r"\[S\d{4}:C[^\]]+\]", "", body)
            opening = " ".join(body.split())[:500]
        abstracts.append({"title": section.get("title", ""), "opening": opening})
    return abstracts


def build_summary_prompt(title: str, abstracts: list[dict[str, str]], flagged: str = "") -> str:
    listing = "\n".join(f"- {a['title']}: {a['opening']}" for a in abstracts)
    guard = ""
    if flagged:
        guard = (
            "\nIMPORTANT: a previous draft copied this passage verbatim from a section — "
            f"do not reuse it or any near-verbatim phrasing: \"{flagged}\"\n"
        )
    return f"""Write the Opening Summary for a research report titled "{title}".

Rules:
- 280-380 words, two or three paragraphs, fresh prose written for a reader who has not seen the report.
- Summarise what the report covers and its main findings; do not copy sentences or phrases from the section openings below — synthesise.
- Do not refer to sections by number, do not use phrases like "Section 3 shows", and do not mention the writing process.
- No citations, no markdown headings, no bullet lists.
{guard}
Section titles and openings (for content only — do not copy phrasing):
{listing}
"""


def generate_opening_summary(corpus: Path, llm: Any, title: str = "") -> dict[str, Any]:
    from . import publish

    plan = publish.read_json_object(publish.publish_plan_path(corpus))
    state = publish.read_json_object(publish.publish_state_path(corpus))
    abstracts = section_abstracts(corpus, plan, state)
    full_text = ""
    for item in state.get("completed_sections", []):
        path = Path(item.get("path", ""))
        if path.exists():
            full_text += "\n" + path.read_text(encoding="utf-8", errors="replace")
    flagged = ""
    last_overlap = ""
    for attempt in range(1, MAX_ATTEMPTS + 1):
        draft = llm.text_call(build_summary_prompt(title or corpus.name, abstracts, flagged)).strip()
        overlap = longest_verbatim_overlap(draft, full_text)
        self_ref = SELF_REFERENCE_RE.search(draft)
        if not overlap and not self_ref:
            path = summary_override_path(corpus)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(draft + "\n", encoding="utf-8")
            return {"ok": True, "attempts": attempt, "words": len(draft.split()), "path": str(path)}
        last_overlap = overlap or (self_ref.group(0) if self_ref else "")
        flagged = last_overlap
    return {"ok": False, "attempts": MAX_ATTEMPTS, "last_overlap": last_overlap}
