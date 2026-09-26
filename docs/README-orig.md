# Super Researcher 🦸

Local UI and corpus builder for Phase 1 and Phase 2.

## Run

```bash
python3 run_app.py
```

If you use the Atlas tab, run the app from the project virtualenv:

```bash
.venv/bin/python run_app.py
```

Open:

```text
http://127.0.0.1:8765
```

## What It Does

Phase 1 creates `research_protocol.json` from the topic, context, controls, archetype classification, rubric assessment, and default assumptions.

Phase 2 creates search heuristics, a parallel search plan, candidate discovery, source downloads, dedupe, Markdown sidecars, a corpus index, and a quality report.

Outputs are written under:

```text
research_runs/<timestamp-topic>_Corpus/
```

## Providers

LLM planning uses Codex built-in OAuth through the local Codex binary first. Gemini is a fallback when configured in `api_keys.txt`. Search/fetch adapters use Exa, Serper, SerpAPI, and Firecrawl when keys are present.

## Post-Process A Corpus

```bash
python3 run_postprocess.py --root research_runs
```

This repairs corpus outputs after acquisition without changing the downloader. It fixes filename/type mismatches, regenerates Markdown sidecars, attempts targeted re-fetch only for confident wrong-payload cases, deletes unrecoverable corrupted files, updates the corpus index/JSONL records, and appends a compact repair summary to `research_runs/corpus_validation_report.md`.

For best PDF table/image extraction, install optional libraries in the Python environment used to run the command:

```bash
python3 -m pip install PyMuPDF pymupdf4llm docling beautifulsoup4 lxml
```

## Corpus Atlas

The UI includes an `Atlas` tab for Markdown sidecar chunking, local embedding, 2D projection, point inspection, Keep/Reject/Key Evidence curation, and corpus post-processing for damaged PDF-derived Markdown. Atlas artifacts are stored inside each corpus under `atlas/`.

Install Atlas dependencies before building a map:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-atlas.txt
npm install
npm run build:atlas
```

The default local embedding model is `BAAI/bge-base-en-v1.5`; it is cached under `.models/` on first build. The `Post-process` button repairs PDF Markdown sidecars with excessive newline fragmentation using PyMuPDF4LLM first, then a conservative reflow fallback. If Markdown changes, rebuild the Atlas.

## Topic Discovery Experiment

```bash
.venv/bin/python run_topic_discovery.py --corpus latest --max-chunks 300
```

Mines table-of-contents entries and Atlas heading paths, dedupes them, then asks the LLM for a Markdown topic/subtopic outline. Outputs are written to `atlas/topics/` inside the corpus. This is an experiment path only; it does not change the UI.
