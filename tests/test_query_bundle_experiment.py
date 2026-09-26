from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import run_query_bundle_experiment as qbe


def write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def chunk(
    chunk_id: str,
    text: str,
    source_id: str,
    title: str,
    section: str,
    status: str | None = None,
) -> dict[str, object]:
    return {
        "id": chunk_id,
        "text": text,
        "metadata": {
            "source_id": source_id,
            "title": title,
            "publisher": f"{source_id}.example",
            "url": f"https://example.com/{source_id}",
            "section_path": section,
            "chunk_type": "text",
            "word_count": len(text.split()),
            "warning_flags": [],
        },
        "_status": status,
    }


def make_corpus(tmp: str) -> Path:
    corpus = Path(tmp) / "query_Corpus"
    atlas = corpus / "atlas"
    rows = [
        chunk(
            "c1",
            "Urban Air Mobility (UAM) smart charging coordination reduces peak load. Table 1 Charging Demand Forecast. power grid flow smart charging smart charging",
            "s1",
            "Grid Integration Report",
            "Infrastructure > Charging coordination, UAM charging demand, and power grid flow",
            "keep",
        ),
        chunk(
            "c2",
            "Power grid flow constraints and smart charging coordination affect aircraft fleet dispatch and charging demand.",
            "s2",
            "Airport Electrification Study",
            "Infrastructure > Power system welfare and smart charging",
            "key_evidence",
        ),
        chunk(
            "c3",
            "Vertiport siting and access requirements are related but separate.",
            "s3",
            "Vertiport Study",
            "Infrastructure > Vertiport and TOLA availability",
        ),
        chunk(
            "c4",
            "Safety certification requirements do not focus on charging demand.",
            "s4",
            "Safety Report",
            "Regulation > Certification",
        ),
    ]
    write_jsonl(atlas / "chunks.jsonl", [{k: v for k, v in row.items() if k != "_status"} for row in rows])
    write_jsonl(atlas / "selections.jsonl", [{"chunk_id": row["id"], "status": row["_status"]} for row in rows if row.get("_status")])
    (atlas / "topics").mkdir(parents=True)
    (atlas / "topics" / "topic_tree.md").write_text(
        """
- Infrastructure and Electrification
  - Existing facilities and planned upgrades
  - Charging coordination, UAM charging demand, and power grid flow
  - Power system welfare and smart charging
""",
        encoding="utf-8",
    )
    write_json(
        atlas / "topics" / "deduped_subtopics.json",
        [
            {
                "label": "Charging coordination",
                "aliases": ["UAM charging demand", "Power grid flow"],
                "chunk_ids": ["c1", "c2"],
                "section_paths": ["Infrastructure > Charging coordination, UAM charging demand, and power grid flow"],
                "source_count": 2,
                "occurrence_count": 2,
            }
        ],
    )
    write_json(
        atlas / "topics" / "toc_entries.json",
        [
            {
                "label": "Power system welfare and smart charging",
                "aliases": ["Smart charging"],
                "chunk_ids": ["c2"],
                "section_paths": ["Infrastructure > Power system welfare and smart charging"],
                "source_count": 1,
                "occurrence_count": 1,
            }
        ],
    )
    return corpus


class QueryBundleExperimentTests(unittest.TestCase):
    def test_exact_and_fuzzy_topic_anchoring(self) -> None:
        nodes = qbe.flatten_topics(
            [
                {
                    "id": "topic-1",
                    "label": "Infrastructure and Electrification",
                    "selected": True,
                    "children": [
                        {"id": "topic-1-1", "label": "Charging coordination, UAM charging demand, and power grid flow", "selected": True, "children": []}
                    ],
                }
            ]
        )

        exact = qbe.find_topic_node("Charging coordination, UAM charging demand, and power grid flow", nodes)
        fuzzy = qbe.find_topic_node("charging demand grid flow", nodes)

        self.assertEqual(exact["id"], "topic-1-1")
        self.assertEqual(fuzzy["id"], "topic-1-1")

    def test_bigram_trigram_and_acronym_extraction(self) -> None:
        text = "Urban Air Mobility (UAM) smart charging coordination improves power grid flow. smart charging coordination. FAA (May 2018. Time 1:28:20)."

        ngrams = qbe.extract_ngrams(text, sizes=(2, 3), limit=60)
        acronyms = qbe.extract_acronym_pairs([{"id": "c1", "text": text, "metadata": {}, "selection_status": "unmarked"}])

        self.assertIn("Smart Charging", ngrams)
        self.assertIn("Power Grid Flow", ngrams)
        self.assertNotIn("Of On Demand", qbe.extract_ngrams("analysis of on demand mobility", sizes=(3,), limit=20))
        self.assertEqual(acronyms[0]["acronym"], "UAM")
        self.assertEqual(acronyms[0]["expansion"], "Urban Air Mobility")
        self.assertNotIn("FAA", [item["acronym"] for item in acronyms])

    def test_term_dedupe_merges_near_duplicates(self) -> None:
        rows = [
            {"term": "Power Grid Flow", "normalized": "power grid flow", "score": 10, "frequency": 1, "categories": {"tfidf": 1}, "chunk_ids": [], "source_ids": [], "source_count": 0, "source_titles": [], "curation_mix": {}},
            {"term": "Power Grid Flows", "normalized": "power grid flows", "score": 8, "frequency": 1, "categories": {"heading": 1}, "chunk_ids": [], "source_ids": [], "source_count": 0, "source_titles": [], "curation_mix": {}},
        ]

        deduped = qbe.dedupe_scored_terms(rows)

        self.assertEqual(len(deduped), 1)
        self.assertIn("heading", deduped[0]["categories"])
        self.assertIn("tfidf", deduped[0]["categories"])

    def test_run_experiment_writes_outputs_and_scores_curation_source_diversity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            corpus = make_corpus(tmp)

            result = qbe.run_query_bundle_experiment(corpus=str(corpus), subtopic=qbe.DEFAULT_SUBTOPIC)

            out = corpus / "atlas" / "query_bundles"
            self.assertTrue((out / "query_bundle.json").exists())
            self.assertTrue((out / "query_bundle.md").exists())
            self.assertTrue((out / "candidate_terms.json").exists())
            self.assertTrue((out / "candidate_terms.md").exists())
            self.assertTrue((out / "anchor_chunks.json").exists())
            self.assertTrue((out / "coverage_report.md").exists())
            self.assertGreaterEqual(result["summary"]["anchor_chunk_count"], 2)
            self.assertIn("Power system welfare and smart charging", result["query_bundle"]["sibling_terms"])
            self.assertIn("UAM", [item["acronym"] for item in result["query_bundle"]["acronyms"]])
            self.assertTrue(any("Smart Charging" in term for term in result["query_bundle"]["bigrams_trigrams"]))
            self.assertTrue(any("power grid flow" in query.lower() for query in result["query_bundle"]["retrieval_queries"]))
            top_terms = result["candidate_terms"][:20]
            self.assertTrue(any(item["source_count"] >= 2 for item in top_terms))
            self.assertTrue(any(item["curation_mix"]["keep"] or item["curation_mix"]["key_evidence"] for item in top_terms))


if __name__ == "__main__":
    unittest.main()
