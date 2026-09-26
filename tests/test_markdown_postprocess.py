from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from superresearcher import postprocess


class MarkdownReadabilityPostprocessTests(unittest.TestCase):
    def test_detects_fragmented_pdf_markdown(self) -> None:
        body = "\n".join(["U", "A", "M", "Vis", "io", "n", "C", "o", "n", "c", "e", "p", "t"] * 20)
        metrics = postprocess.readability_metrics(body)

        self.assertTrue(metrics["damaged"])
        self.assertTrue(metrics["newline_damaged"])

    def test_detects_binary_fallback_gibberish(self) -> None:
        body = ("mó\n\x10 öò\x01z\x02\x01^>\x00 \x04 \x86C\x01\x10o\n" * 100) + "AAM Market Assessment Report"
        metrics = postprocess.readability_metrics(body)

        self.assertTrue(metrics["damaged"])
        self.assertTrue(metrics["binary_corrupt"])

    def test_detects_printable_raw_pdf_markdown_without_controls(self) -> None:
        body = "%PDF-1.7\n" + "\n".join(
            f"{index} 0 obj\n<</Filter/FlateDecode/Length 20>>stream\nabc\nendstream\nendobj"
            for index in range(1, 14)
        )
        metrics = postprocess.readability_metrics(body)

        self.assertEqual(metrics["nul_count"], 0)
        self.assertEqual(metrics["control_count"], 0)
        self.assertFalse(metrics["binary_corrupt"])
        self.assertTrue(metrics["damaged"])
        self.assertTrue(metrics["raw_pdf_corrupt"])

    def test_shorter_clean_candidate_can_replace_raw_pdf_markdown(self) -> None:
        old_body = "%PDF-1.7\n" + "\n".join(
            f"{index} 0 obj\n<</Filter/FlateDecode/Length 20>>stream\n{'ABCDEF' * 80}\nendstream\nendobj"
            for index in range(1, 18)
        )
        candidate = ("Clean extracted report text with readable sentences and normal Markdown structure. " * 80).strip()

        self.assertTrue(postprocess.candidate_is_better(old_body, candidate))

    def test_reflows_fragmented_text_without_touching_tables(self) -> None:
        body = "\n".join(
            ["U", "A", "M", "Vis", "io", "n", "", "| Metric | Value |", "| --- | --- |", "| Cost | 10 |"]
        )

        cleaned = postprocess.cleanup_newline_damage(body)

        self.assertIn("UAM Vision", cleaned)
        self.assertIn("| Metric | Value |", cleaned)

    def test_row_reflow_overwrites_sidecar_and_marks_note(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            corpus = Path(tmp)
            md = corpus / "markdown" / "0001-example.md"
            md.parent.mkdir()
            md.write_text(
                "# Example\n\n- Source type: pdf\n\n---\n\n" + "\n".join(["A", "d", "v", "a", "n", "c", "e", "d"] * 30),
                encoding="utf-8",
            )
            row = {
                "source_type": "pdf",
                "local_path": str(corpus / "originals" / "0001-example.pdf"),
                "markdown_path": str(md),
                "conversion_notes": ["pdf_fallback_text_only"],
            }

            result = postprocess.postprocess_markdown_row(corpus, row)

        self.assertEqual(result["reflowed"], 1)
        self.assertIn("postprocess_newline_reflowed", result["row"]["conversion_notes"])


if __name__ == "__main__":
    unittest.main()
