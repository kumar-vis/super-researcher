"""Cross-section duplication detection (2026-10-29 harness fix).

Ghost Ships v1 told the Finnie-crates story and the MS Trader boarding
twice, in near-identical detail, in consecutive sections. The continuity
summary existed but carried no enforceable "already told" record. This
module provides the post-compile detector whose report lands in QA:

- exact repeated shingles (8-word runs) shared by two different sections;
- near-duplicate sentences (token-set Jaccard >= 0.7) across sections,
  citations stripped — these are the re-told facts.

Used together with the facts-used ledger that ``publish`` now asks the
continuity summariser to maintain (see ``update_continuity_summary``).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

CITATION_RE = re.compile(r"\[S\d{4}:C[^\]]+\]|\[\^\d+\^\]\(#ref-\d+\)")
SHINGLE_SIZE = 8


def strip_citations(text: str) -> str:
    return CITATION_RE.sub("", text)


def _words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9'’]+", strip_citations(text).lower())


def shingles(text: str, size: int = SHINGLE_SIZE) -> set[tuple[str, ...]]:
    words = _words(text)
    return {tuple(words[i : i + size]) for i in range(len(words) - size + 1)}


def sentences(text: str) -> list[str]:
    cleaned = strip_citations(text)
    cleaned = re.sub(r"^#{1,6}\s+.*$", "", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", cleaned)
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", cleaned) if len(s.split()) >= 8]


def _token_set(sentence: str) -> frozenset[str]:
    return frozenset(_words(sentence))


def duplication_report(section_texts: dict[str, str]) -> dict[str, Any]:
    """Compare every pair of sections; report shared shingles + sentences."""
    names = sorted(section_texts)
    shingle_sets = {name: shingles(section_texts[name]) for name in names}
    sentence_sets = {name: [(s, _token_set(s)) for s in sentences(section_texts[name])] for name in names}
    pairs = []
    total_shared_shingles = 0
    total_dup_sentences = 0
    for i, a in enumerate(names):
        for b in names[i + 1 :]:
            shared = shingle_sets[a] & shingle_sets[b]
            dup_sentences = []
            for sent_a, toks_a in sentence_sets[a]:
                for sent_b, toks_b in sentence_sets[b]:
                    union = toks_a | toks_b
                    if union and len(toks_a & toks_b) / len(union) >= 0.7:
                        dup_sentences.append({"a": sent_a[:160], "b": sent_b[:160]})
                        break
            if shared or dup_sentences:
                pairs.append(
                    {
                        "sections": [a, b],
                        "shared_shingles": len(shared),
                        "sample_shingle": " ".join(next(iter(shared))) if shared else "",
                        "duplicate_sentences": dup_sentences[:6],
                        "duplicate_sentence_count": len(dup_sentences),
                    }
                )
                total_shared_shingles += len(shared)
                total_dup_sentences += len(dup_sentences)
    return {
        "section_count": len(names),
        "pair_count": len(pairs),
        "total_shared_shingles": total_shared_shingles,
        "total_duplicate_sentences": total_dup_sentences,
        "pairs": pairs,
    }


def duplication_report_for_sections_dir(sections_dir: Path) -> dict[str, Any]:
    texts = {}
    for path in sorted(Path(sections_dir).glob("*.md")):
        texts[path.stem] = path.read_text(encoding="utf-8", errors="replace")
    return duplication_report(texts)
