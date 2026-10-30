"""Brief-coverage check for publish plans (2026-10-29 harness fix).

Ghost Ships v1's structure mirrored its corpus clusters: the longest
chapter was ghost fishing gear (a corpus cluster) while the title topic —
ghost ships themselves — was ~7% of the words. This module scores a plan
(or curated topic tree) against the run brief's angles BEFORE compose /
compile spend happens, and emits the coverage report the runbook requires.

Angles are supplied by the driver as ``{name, keywords, spine}`` dicts —
typically one per numbered angle in the run brief. A section is assigned
to the angle whose keywords best match its title + topic path.
"""

from __future__ import annotations

import re
from typing import Any

MAX_CLUSTER_SHARE = 0.15


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", (text or "").lower()))


def classify_section(section: dict[str, Any], angles: list[dict[str, Any]]) -> str | None:
    haystack = " ".join(
        [
            str(section.get("title", "")),
            " ".join(str(p) for p in section.get("source_path", []) or []),
            str(section.get("source_topic_id", "")),
        ]
    ).lower()
    best, best_score = None, 0
    for angle in angles:
        score = 0
        for keyword in angle.get("keywords", []):
            if keyword.lower() in haystack:
                score += 2 if " " in keyword else 1
        if score > best_score:
            best, best_score = angle["name"], score
    return best


def coverage_report(sections: list[dict[str, Any]], angles: list[dict[str, Any]]) -> dict[str, Any]:
    total = max(len(sections), 1)
    by_angle: dict[str, int] = {angle["name"]: 0 for angle in angles}
    by_chapter: dict[str, int] = {}
    unclassified = 0
    for section in sections:
        name = classify_section(section, angles)
        if name is None:
            unclassified += 1
        else:
            by_angle[name] += 1
        path = [str(p).strip() for p in section.get("source_path", []) if str(p).strip()]
        chapter = path[0] if len(path) > 1 else (section.get("title") or "?")
        by_chapter[chapter] = by_chapter.get(chapter, 0) + 1
    spine_names = {a["name"] for a in angles if a.get("spine")}
    spine_sections = sum(by_angle[n] for n in spine_names)
    problems = []
    for chapter, count in by_chapter.items():
        share = count / total
        if share > MAX_CLUSTER_SHARE and count > 3:
            problems.append(
                f"chapter '{chapter}' holds {count}/{total} sections ({share:.0%}) — above the ~15% cluster cap"
            )
    if spine_names and spine_sections / total < 0.34:
        problems.append(
            f"spine angles hold only {spine_sections}/{total} sections ({spine_sections / total:.0%}) — below plurality"
        )
    for angle in angles:
        if by_angle[angle["name"]] == 0:
            problems.append(f"brief angle '{angle['name']}' has no sections")
    return {
        "section_count": len(sections),
        "by_angle": {name: {"sections": n, "share": round(n / total, 3)} for name, n in by_angle.items()},
        "by_chapter": {name: {"sections": n, "share": round(n / total, 3)} for name, n in by_chapter.items()},
        "spine_share": round(spine_sections / total, 3),
        "unclassified": unclassified,
        "problems": problems,
        "ok": not problems,
    }
