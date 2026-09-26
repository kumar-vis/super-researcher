from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from superresearcher import atlas


def words(prefix: str, count: int) -> str:
    return " ".join(f"{prefix}{index:04d}." for index in range(count))


def source() -> dict[str, object]:
    return {
        "source_id": "0001",
        "title": "Example",
        "publisher": "publisher",
        "url": "https://example.com",
        "source_type": "pdf",
        "warning_flags": [],
    }


class AtlasChunkingTests(unittest.TestCase):
    def test_heading_and_table_chunking(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            md = Path(tmp) / "0001-source.md"
            md.write_text(
                "\n".join(
                    [
                        "# Source Header",
                        "Title: Example",
                        "---",
                        "# Market",
                        "First paragraph with useful context.",
                        "",
                        "Second paragraph continues the same section.",
                        "",
                        "## Metrics",
                        "| Metric | Value |",
                        "| --- | --- |",
                        "| Cost | 10 |",
                        "",
                        "Text after table.",
                    ]
                ),
                encoding="utf-8",
            )

            chunks = atlas.chunk_markdown_file(md, source())

        self.assertGreaterEqual(len(chunks), 3)
        self.assertEqual(chunks[0]["metadata"]["section_path"], "Market")
        self.assertEqual(chunks[1]["metadata"]["chunk_type"], "table")
        self.assertIn("| Metric | Value |", chunks[1]["text"])
        self.assertEqual(chunks[2]["metadata"]["section_path"], "Market > Metrics")

    def test_small_text_chunk_merges_backward(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            md = Path(tmp) / "0001-source.md"
            md.write_text(f"# Header\n---\n# Large\n{words('large', 220)}\n\n# Small\n{words('small', 40)}", encoding="utf-8")

            chunks = atlas.chunk_markdown_file(md, source())

        self.assertEqual(len(chunks), 1)
        self.assertIn("small0000", chunks[0]["text"])
        self.assertEqual(chunks[0]["metadata"]["section_path"], "Large")
        self.assertEqual(chunks[0]["metadata"]["section_paths"], ["Large", "Small"])

    def test_first_small_text_chunk_merges_forward(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            md = Path(tmp) / "0001-source.md"
            md.write_text(f"# Header\n---\n# Small\n{words('small', 40)}\n\n# Large\n{words('large', 220)}", encoding="utf-8")

            chunks = atlas.chunk_markdown_file(md, source())

        self.assertEqual(len(chunks), 1)
        self.assertIn("large0000", chunks[0]["text"])
        self.assertEqual(chunks[0]["metadata"]["section_path"], "Small")
        self.assertEqual(chunks[0]["metadata"]["section_paths"], ["Small", "Large"])

    def test_oversized_text_chunk_splits(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            md = Path(tmp) / "0001-source.md"
            md.write_text(f"# Header\n---\n# Long\n{words('long', 1201)}", encoding="utf-8")

            chunks = atlas.chunk_markdown_file(md, source())

        self.assertGreater(len(chunks), 1)
        for chunk in chunks:
            self.assertLessEqual(chunk["metadata"]["word_count"], 1000)
            self.assertLessEqual(len(chunk["text"]), 8000)

    def test_oversized_split_uses_regex_word_counter(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            md = Path(tmp) / "0001-source.md"
            slash_words = " ".join("alpha/beta." for _ in range(700))
            md.write_text(f"# Header\n---\n# Long\n{slash_words}", encoding="utf-8")

            chunks = atlas.chunk_markdown_file(md, source())

        self.assertGreater(len(chunks), 1)
        for chunk in chunks:
            self.assertLessEqual(chunk["metadata"]["word_count"], 1000)

    def test_oversized_split_runs_after_merge(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            md = Path(tmp) / "0001-source.md"
            md.write_text(f"# Header\n---\n# Almost Full\n{words('full', 950)}\n\n# Tiny\n{words('tiny', 60)}", encoding="utf-8")

            chunks = atlas.chunk_markdown_file(md, source())

        self.assertGreater(len(chunks), 1)
        for chunk in chunks:
            self.assertLessEqual(chunk["metadata"]["word_count"], 1000)
            self.assertLessEqual(len(chunk["text"]), 8000)

    def test_tables_remain_standalone_boundaries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            md = Path(tmp) / "0001-source.md"
            md.write_text(
                "\n".join(
                    [
                        "# Header",
                        "---",
                        "# Before",
                        words("before", 20),
                        "",
                        "| Metric | Value |",
                        "| --- | --- |",
                        "| Cost | 10 |",
                        "",
                        "# After",
                        words("after", 20),
                    ]
                ),
                encoding="utf-8",
            )

            chunks = atlas.chunk_markdown_file(md, source())

        self.assertEqual([chunk["metadata"]["chunk_type"] for chunk in chunks], ["text", "table", "text"])
        self.assertEqual(chunks[0]["metadata"]["section_path"], "Before")
        self.assertEqual(chunks[2]["metadata"]["section_path"], "After")

    def test_raw_pdf_chunks_get_warning_flag(self) -> None:
        body = "%PDF-1.7\n" + "\n".join(
            f"{index} 0 obj\n<</Filter/FlateDecode/Length 20>>stream\nabc\nendstream\nendobj"
            for index in range(1, 14)
        )
        chunk = atlas.make_chunk(source(), Path("0001-source.md"), 1, body, ["Extracted PDF Text"], "text")

        self.assertIn("raw_pdf_markdown", chunk["metadata"]["warning_flags"])

    def test_empty_markdown_produces_no_chunks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            md = Path(tmp) / "0001-empty.md"
            md.write_text("# Empty\n---\n\n", encoding="utf-8")
            chunks = atlas.chunk_markdown_file(md, {"source_id": "0001", "title": "Empty"})

        self.assertEqual(chunks, [])


class CorpusDiscoveryTests(unittest.TestCase):
    def test_latest_completed_corpus_is_preferred(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            old = root / "20260101-old_Corpus"
            new = root / "20260102-new_Corpus"
            for corpus, state in ((old, "failed"), (new, "completed")):
                (corpus / "markdown").mkdir(parents=True)
                (corpus / "markdown" / "0001.md").write_text("body", encoding="utf-8")
                (corpus / "run.json").write_text(json.dumps({"state": state, "topic": corpus.name}), encoding="utf-8")
                (corpus / "ingested_sources.jsonl").write_text("{}", encoding="utf-8")

            self.assertEqual(atlas.latest_corpus_id(root), new.name)


if __name__ == "__main__":
    unittest.main()
