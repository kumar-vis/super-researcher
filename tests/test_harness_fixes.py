"""Tests for the 2026-10-29 harness fixes: bibliography, lint gate,
duplication detection, brief coverage, and the summary overlap guard."""

import re

from superresearcher import bibliography, coverage, duplication, lint_gate
from superresearcher.summary_stage import longest_verbatim_overlap


# --- bibliography -----------------------------------------------------------

def test_looks_like_filename_detects_slugs():
    assert bibliography.looks_like_filename("0010-rediscovering-lost-relationships-canadian")
    assert bibliography.looks_like_filename("some-source.markdown")
    assert not bibliography.looks_like_filename("Plastic Pollution in the World's Oceans")
    assert not bibliography.looks_like_filename("Message in a Bottle")


def test_format_reference_never_contains_filename():
    entry = {
        "source_id": "0010",
        "title": "Rediscovering Lost Relationships: Canadian Inuit and Inupiat",
        "publisher": "Arctic Anthropology",
        "url": "https://example.org/paper",
        "authors": ["Jane Doe", "John Roe"],
        "venue": "Arctic Anthropology",
        "year": 2016,
        "doi": "",
    }
    item = bibliography.format_reference(entry, 3, "ref-3", "0010")
    assert ".markdown" not in item
    assert "Jane Doe" in item and "(2016)" in item
    assert bibliography.validate_reference_item(item) == []


def test_validate_reference_item_flags_raw_filenames():
    bad = "1. []{#ref-1} 0010-rediscovering-lost-relationships-canadian-inuit. markdown. Source S0010."
    assert bibliography.validate_reference_item(bad)


# --- lint gate --------------------------------------------------------------

def test_lint_detects_internal_leak():
    report = lint_gate.lint_report("# T\n\n_Challenger Deep | 2026 | Prepared from Challenger Deep compile artifacts._\n")
    assert not report["ok"]
    assert report["counts"].get("leak", 0) >= 1


def test_lint_merges_adjacent_duplicate_markers():
    md = "Claim one [^1^](#ref-1)[^1^](#ref-1) and more text."
    assert lint_gate.find_adjacent_duplicate_markers(md)
    fixed, report = lint_gate.fix_report(md)
    assert "[^1^](#ref-1)[^1^](#ref-1)" not in fixed
    assert report["counts"].get("duplicate_marker", 0) == 0


def test_section_reference_resolution_uses_chapters():
    plan = {
        "sections": [
            {"title": "A1", "source_path": ["Chapter One", "A1"]},
            {"title": "A2", "source_path": ["Chapter One", "A2"]},
            {"title": "B1", "source_path": ["Chapter Two", "B1"]},
        ]
    }
    fixed, problems = lint_gate.resolve_section_references("See §3 and Section 2 for details.", plan)
    assert problems == []
    assert "Chapter 2" in fixed and "Chapter 1" in fixed
    assert "§" not in fixed


def test_statutory_section_references_are_left_alone():
    plan = {
        "sections": [
            {"title": f"S{i}", "source_path": ["Chapter One", f"S{i}"]} for i in range(1, 60)
        ]
    }
    fixed, problems = lint_gate.resolve_section_references(
        "Liability under CERCLA § 104 and 33 U.S.C. § 414, as foreshadowed in §44.", plan
    )
    assert problems == []
    assert "§ 104" in fixed and "§ 414" in fixed  # statutory: untouched
    assert "Chapter 1" in fixed  # §44 is within range: resolved


def test_caption_problems_flags_truncation_and_fragment():
    assert lint_gate.caption_problems("Fig. 1. The steamer Baychimo; photo taken by Captain George E")
    assert lint_gate.caption_problems("Simply put, similar floating vessels should be treated the.")
    assert lint_gate.caption_problems("Distribution of debris")  # no terminal punctuation
    assert lint_gate.caption_problems("Map of drift tracks in the North Pacific. Source: S0013.") == []


# --- duplication ------------------------------------------------------------

def test_duplication_report_finds_retold_story():
    story = (
        "In early December 1931 Inupiat hunters spotted her near Skull Cliff south of Barrow "
        "and salvaged several bales of furs from the vessel's hold during the long winter."
    )
    report = duplication.duplication_report(
        {
            "section-001": f"The ship vanished. {story} Then silence followed for many years afterwards.",
            "section-002": f"A different opening paragraph entirely. {story} The record then stops.",
            "section-003": "Whales migrate through cold northern waters each spring without incident.",
        }
    )
    assert report["total_shared_shingles"] > 0
    assert report["total_duplicate_sentences"] >= 1


def test_duplication_report_clean_for_distinct_sections():
    report = duplication.duplication_report(
        {
            "section-001": "Salvage law gives a finder rights when a vessel is abandoned at sea by its owner.",
            "section-002": "Drift bottles released in 1906 mapped the surface currents of the North Sea.",
        }
    )
    assert report["total_shared_shingles"] == 0


# --- coverage ---------------------------------------------------------------

ANGLES = [
    {"name": "ghost ships", "keywords": ["ghost ship", "derelict", "baychimo"], "spine": True},
    {"name": "drift science", "keywords": ["drift", "floatees", "currents"], "spine": True},
    {"name": "fishing gear", "keywords": ["fishing gear", "aldfg"], "spine": False},
]


def test_coverage_flags_oversized_cluster_chapter():
    sections = [
        {"title": f"Gear topic {i}", "source_path": ["Ghost Gear", f"Gear topic {i}"]} for i in range(8)
    ] + [
        {"title": "Baychimo the ghost ship", "source_path": ["Phenomenon", "Baychimo the ghost ship"]},
        {"title": "Drift and currents", "source_path": ["Drift", "Drift and currents"]},
    ]
    report = coverage.coverage_report(sections, ANGLES)
    assert not report["ok"]
    assert any("15%" in p for p in report["problems"])


def test_coverage_ok_when_spine_dominates():
    sections = [
        {"title": "Baychimo ghost ship derelict", "source_path": ["Phenomenon", "Baychimo ghost ship derelict"]},
        {"title": "More derelict ghost ship cases", "source_path": ["Phenomenon", "More derelict ghost ship cases"]},
        {"title": "Drift currents floatees", "source_path": ["Drift", "Drift currents floatees"]},
        {"title": "Fishing gear aldfg", "source_path": ["Gear", "Fishing gear aldfg"]},
    ]
    report = coverage.coverage_report(sections, ANGLES)
    assert report["spine_share"] >= 0.5


# --- summary overlap guard --------------------------------------------------

def test_overlap_guard_catches_verbatim_run():
    section_text = "the quick brown fox jumps over the lazy dog near the river bank today"
    summary = "An intro. The quick brown fox jumps over the lazy dog near the river bank today indeed."
    assert longest_verbatim_overlap(summary, section_text)
    fresh = "A wholly fresh synthesis written in new words about maritime subjects and ocean themes."
    assert longest_verbatim_overlap(fresh, section_text) == ""
