"""Pre-export lint gate (2026-10-29 harness fix).

Hard-fail checks over the final report markdown (and, pre-export, over the
visual plan's captions). A report that fails the gate must be fixed or the
export stopped — never shipped with known defects. Defects targeted are the
ones found in the 2026-10-27 Ghost Ships v1 export:

(a) internal/process leakage ("Challenger Deep", "compile artifacts",
    "Evidence note" meta-text, template plumbing),
(b) unresolved internal cross-references ("§44", "Section 51") left over
    from compile-time numbering — resolvable ones are rewritten to the
    printed chapter number,
(c) adjacent duplicate citation markers ([^1^][^1^] for the same source),
(d) figure captions that are truncated mid-word / mid-sentence or are
    body-text fragments,
(e) bibliography entries containing raw filenames (see bibliography.py).
"""

from __future__ import annotations

import re
from typing import Any

LEAK_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("internal codename 'Challenger Deep'", re.compile(r"Challenger Deep")),
    ("process language 'compile artifacts'", re.compile(r"compile artifacts", re.IGNORECASE)),
    ("internal 'Evidence note' meta-text", re.compile(r"Evidence note\s*:", re.IGNORECASE)),
    ("process language 'Prepared from'", re.compile(r"Prepared from .*?artifacts", re.IGNORECASE)),
    ("raw chunk citation left unrendered", re.compile(r"\[S\d{4}:C[^\]]+\]")),
]

SECTION_REF_RE = re.compile(r"§\s*(\d+)|(?<![\w.])Section\s+(\d+)\b")
ADJACENT_DUP_MARKER_RE = re.compile(r"(\[\^\d+\^\]\(#ref-\d+\))\s*\1")
CAPTION_LINE_RE = re.compile(r"^\*Figure:?\s*(?P<body>.+)\*$", re.MULTILINE)
STOPWORD_ENDINGS = {
    "the", "a", "an", "of", "to", "in", "on", "by", "for", "with", "and",
    "or", "from", "at", "as", "is", "was", "were", "are", "be", "its",
}


def find_leaks(markdown: str) -> list[dict[str, str]]:
    findings = []
    for label, pattern in LEAK_PATTERNS:
        for match in pattern.finditer(markdown):
            findings.append({"kind": "leak", "label": label, "match": match.group(0)[:80]})
    return findings


def find_adjacent_duplicate_markers(markdown: str) -> list[str]:
    return [m.group(0)[:60] for m in ADJACENT_DUP_MARKER_RE.finditer(markdown)]


def merge_adjacent_duplicate_markers(markdown: str) -> str:
    previous = None
    while previous != markdown:
        previous = markdown
        markdown = ADJACENT_DUP_MARKER_RE.sub(r"\1", markdown)
    return markdown


def chapter_map_from_plan(plan: dict[str, Any]) -> dict[int, int]:
    """Map compile-time section index (1-based, plan order) -> printed chapter.

    Chapters follow the plan sections' ``source_path`` first element, in
    order of first appearance — the same grouping the exporter uses.
    """
    mapping: dict[int, int] = {}
    chapters: list[str] = []
    for index, section in enumerate(plan.get("sections") or [], start=1):
        path = [str(p).strip() for p in section.get("source_path", []) if str(p).strip()]
        group = path[0] if len(path) > 1 else "Report"
        if group not in chapters:
            chapters.append(group)
        mapping[index] = chapters.index(group) + 1
    return mapping


def resolve_section_references(markdown: str, plan: dict[str, Any]) -> tuple[str, list[dict[str, str]]]:
    """Rewrite §N / Section N compile refs to 'Chapter M'.

    Only numbers within the plan's section range can be internal
    cross-references. Larger § numbers are external citations (statutes
    and regulations — "33 U.S.C. § 414", "CERCLA § 104") and are left
    untouched: a § number beyond the section count cannot refer to a
    section of this report.
    """
    chapter_of = chapter_map_from_plan(plan)
    total = len(plan.get("sections") or [])
    problems: list[dict[str, str]] = []

    def repl(match: re.Match[str]) -> str:
        number = int(match.group(1) or match.group(2))
        if 1 <= number <= total:
            return f"Chapter {chapter_of[number]}"
        return match.group(0)  # external/statutory reference, not internal

    return SECTION_REF_RE.sub(repl, markdown), problems


def caption_problems(caption: str) -> list[str]:
    """Heuristics for truncated / fragment captions."""
    text = (caption or "").strip()
    problems = []
    if not text:
        return ["empty caption"]
    # Split off the trailing source attribution the exporter appends.
    body = re.sub(r"Source:\s*\[?S\d{4}\]?\.?\s*$", "", text).strip()
    body = re.sub(r"\[?S\d{4}\]?\.?\s*$", "", body).strip()
    if not body:
        return problems
    if not re.search(r"[.!?…)\]\"']$", body):
        problems.append("caption does not end with terminal punctuation (likely truncated)")
    last_word = re.findall(r"[A-Za-zÀ-ÿ]+", body)
    if last_word and last_word[-1].lower() in STOPWORD_ENDINGS:
        problems.append(f"caption ends with a function word ('{last_word[-1]}') — likely a fragment")
    if last_word and len(last_word[-1]) == 1 and last_word[-1].isupper():
        problems.append("caption ends with a single capital letter (truncated mid-name)")
    return problems


def find_caption_problems(markdown: str) -> list[dict[str, str]]:
    findings = []
    for match in CAPTION_LINE_RE.finditer(markdown):
        for problem in caption_problems(match.group("body")):
            findings.append({"kind": "caption", "label": problem, "match": match.group("body")[:100]})
    return findings


def find_bibliography_problems(markdown: str) -> list[dict[str, str]]:
    from .bibliography import validate_reference_item

    findings = []
    ref_split = re.split(r"\n##\s+References\s*\n", markdown)
    if len(ref_split) < 2:
        return findings
    for line in ref_split[1].splitlines():
        line = line.strip()
        if re.match(r"^\d+\.\s", line):
            for problem in validate_reference_item(line):
                findings.append({"kind": "bibliography", "label": problem, "match": line[:100]})
    return findings


def lint_report(markdown: str, plan: dict[str, Any] | None = None) -> dict[str, Any]:
    """Full gate over final report markdown. ``ok`` is True only when clean."""
    findings: list[dict[str, str]] = []
    findings.extend(find_leaks(markdown))
    findings.extend(
        {"kind": "duplicate_marker", "label": "adjacent duplicate citation marker", "match": m}
        for m in find_adjacent_duplicate_markers(markdown)
    )
    findings.extend(find_caption_problems(markdown))
    findings.extend(find_bibliography_problems(markdown))
    if plan is not None:
        _, unresolved = resolve_section_references(markdown, plan)
        findings.extend(unresolved)
    return {"ok": not findings, "findings": findings, "counts": _counts(findings)}


def fix_report(markdown: str, plan: dict[str, Any] | None = None) -> tuple[str, dict[str, Any]]:
    """Apply the gate's safe automatic fixes, then re-lint.

    Auto-fixes: merge adjacent duplicate markers; resolve §N/Section N
    references against the plan. Leaks, caption and bibliography problems
    are NOT auto-fixed — they fail the gate for a human/pipeline decision.
    """
    fixed = merge_adjacent_duplicate_markers(markdown)
    if plan is not None:
        fixed, _ = resolve_section_references(fixed, plan)
    return fixed, lint_report(fixed, plan)


def _counts(findings: list[dict[str, str]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for finding in findings:
        counts[finding["kind"]] = counts.get(finding["kind"], 0) + 1
    return counts
