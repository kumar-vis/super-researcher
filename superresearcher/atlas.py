from __future__ import annotations

import hashlib
import json
import re
import threading
import time
import traceback
import urllib.parse
from datetime import datetime
from pathlib import Path
from typing import Any

from .config import DEFAULT_STORAGE_ROOT, ROOT, atomic_write_json
from .postprocess import raw_pdf_corruption_metrics


MODEL_NAME = "BAAI/bge-base-en-v1.5"
MODEL_CACHE = ROOT / ".models"
CHUNKING_VERSION = "heading-paragraph-table-v2"
MIN_TEXT_CHUNK_WORDS = 200
MIN_TEXT_CHUNK_CHARS = 1200
MAX_TEXT_CHUNK_WORDS = 1000
MAX_TEXT_CHUNK_CHARS = 8000
ATLAS_JOBS: dict[str, "AtlasJob"] = {}


class AtlasDependencyError(RuntimeError):
    pass


def dependency_status() -> dict[str, Any]:
    python = {}
    for module in ("sentence_transformers", "numpy", "umap"):
        try:
            __import__(module)
            python[module] = True
        except Exception:
            python[module] = False
    node_package = (ROOT / "node_modules" / "embedding-atlas").exists()
    return {
        "model": MODEL_NAME,
        "model_cache": str(MODEL_CACHE),
        "python": python,
        "node": {"embedding-atlas": node_package},
        "ready_for_build": python["sentence_transformers"] and python["numpy"],
        "install_commands": [
            "python3 -m venv .venv && .venv/bin/python -m pip install -r requirements-atlas.txt",
            "npm install",
            f"Model will download into {MODEL_CACHE} on first build.",
        ],
    }


def list_corpora(root: Path = DEFAULT_STORAGE_ROOT) -> list[dict[str, Any]]:
    root = root.resolve()
    if not root.exists():
        return []
    rows = []
    for corpus in sorted(root.glob("*_Corpus"), key=lambda p: p.stat().st_mtime, reverse=True):
        run = read_json(corpus / "run.json")
        ingested = read_jsonl(corpus / "ingested_sources.jsonl")
        markdown_count = len(list((corpus / "markdown").glob("*.md"))) if (corpus / "markdown").exists() else 0
        manifest = read_json(corpus / "atlas" / "manifest.json")
        rows.append(
            {
                "id": corpus.name,
                "name": corpus.name,
                "path": str(corpus),
                "topic": run.get("topic") or corpus.name,
                "state": run.get("state"),
                "completed_at": run.get("completed_at"),
                "mtime": corpus.stat().st_mtime,
                "source_count": len(ingested),
                "markdown_count": markdown_count,
                "atlas_ready": bool(manifest),
                "chunk_count": manifest.get("chunk_count", 0),
                "model": manifest.get("model"),
            }
        )
    return rows


def latest_corpus_id(root: Path = DEFAULT_STORAGE_ROOT) -> str | None:
    corpora = list_corpora(root)
    if not corpora:
        return None
    completed = [row for row in corpora if row.get("state") == "completed"]
    return (completed or corpora)[0]["id"]


def resolve_corpus(corpus_id_or_path: str, root: Path = DEFAULT_STORAGE_ROOT) -> Path:
    root = root.resolve()
    raw = urllib.parse.unquote(corpus_id_or_path)
    candidate = Path(raw).expanduser()
    if not candidate.is_absolute():
        candidate = root / raw
    candidate = candidate.resolve()
    if candidate != root and root not in candidate.parents:
        raise ValueError("Corpus path must be inside research_runs.")
    if not candidate.exists() or not candidate.is_dir() or not candidate.name.endswith("_Corpus"):
        raise ValueError("Corpus folder not found.")
    return candidate


class AtlasJob:
    def __init__(self, corpus: Path, force: bool = False) -> None:
        self.corpus = corpus.resolve()
        self.force = force
        self.job_id = f"{self.corpus.name}-{int(time.time())}"
        self.status: dict[str, Any] = {
            "job_id": self.job_id,
            "corpus_id": self.corpus.name,
            "corpus_path": str(self.corpus),
            "state": "queued",
            "stage": "Queued",
            "progress": 0,
            "counts": {},
            "error": None,
            "started_at": None,
            "completed_at": None,
        }
        self._lock = threading.Lock()
        self.thread = threading.Thread(target=self._run, daemon=True)

    def start(self) -> None:
        ATLAS_JOBS[self.job_id] = self
        self.thread.start()

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return json.loads(json.dumps(self.status))

    def event(self, stage: str, progress: int, **counts: Any) -> None:
        with self._lock:
            self.status["stage"] = stage
            self.status["progress"] = progress
            self.status["counts"].update(counts)

    def _run(self) -> None:
        try:
            with self._lock:
                self.status["state"] = "running"
                self.status["started_at"] = datetime.now().isoformat(timespec="seconds")
            self.event("Reading sidecars", 5)
            result = build_atlas(self.corpus, force=self.force, progress=self.event)
            with self._lock:
                self.status["state"] = "completed"
                self.status["completed_at"] = datetime.now().isoformat(timespec="seconds")
                self.status["progress"] = 100
                self.status["stage"] = "Ready"
                self.status["counts"].update(result)
        except Exception as exc:
            error_path = self.corpus / "atlas" / "build-error.log"
            error_path.parent.mkdir(parents=True, exist_ok=True)
            error_path.write_text(traceback.format_exc(), encoding="utf-8")
            with self._lock:
                self.status["state"] = "failed"
                self.status["error"] = str(exc)
                self.status["completed_at"] = datetime.now().isoformat(timespec="seconds")


def start_atlas_job(corpus_id_or_path: str, force: bool = False) -> AtlasJob:
    corpus = resolve_corpus(corpus_id_or_path)
    for job in ATLAS_JOBS.values():
        snap = job.snapshot()
        if snap["corpus_path"] == str(corpus) and snap["state"] in {"queued", "running"}:
            return job
    job = AtlasJob(corpus, force=force)
    job.start()
    return job


def get_job(job_id: str) -> AtlasJob | None:
    return ATLAS_JOBS.get(job_id)


def build_atlas(corpus: Path, force: bool = False, progress=None) -> dict[str, int]:
    atlas_dir = corpus / "atlas"
    atlas_dir.mkdir(exist_ok=True)
    signature = corpus_signature(corpus)
    manifest_path = atlas_dir / "manifest.json"
    manifest = read_json(manifest_path)
    if not force and manifest.get("signature") == signature and (atlas_dir / "points.jsonl").exists() and (atlas_dir / "chunks.jsonl").exists():
        return {"chunk_count": manifest.get("chunk_count", 0), "source_count": manifest.get("source_count", 0), "cached": 1}

    if progress:
        progress("Chunking Markdown sidecars", 15)
    chunks = chunk_corpus(corpus)
    if not chunks:
        raise RuntimeError("No Markdown chunks found for this corpus.")
    write_jsonl(atlas_dir / "chunks.jsonl", chunks)

    if progress:
        progress("Embedding chunks", 35, chunk_count=len(chunks))
    embeddings = embed_texts([chunk["embedding_text"] for chunk in chunks])

    if progress:
        progress("Projecting map", 70, chunk_count=len(chunks))
    coords = project_embeddings(embeddings)

    points = []
    for chunk, (x, y) in zip(chunks, coords):
        point = {
            "id": chunk["id"],
            "x": float(x),
            "y": float(y),
            "text_preview": chunk["text"][:500],
            "metadata": chunk["metadata"],
        }
        points.append(point)
    write_jsonl(atlas_dir / "points.jsonl", points)

    manifest = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "model": MODEL_NAME,
        "signature": signature,
        "chunk_count": len(chunks),
        "source_count": len({chunk["metadata"]["source_id"] for chunk in chunks}),
        "points_path": str(atlas_dir / "points.jsonl"),
        "chunks_path": str(atlas_dir / "chunks.jsonl"),
        "selections_path": str(atlas_dir / "selections.jsonl"),
    }
    atomic_write_json(manifest_path, manifest)
    if not (atlas_dir / "selections.jsonl").exists():
        (atlas_dir / "selections.jsonl").write_text("", encoding="utf-8")
    if progress:
        progress("Saving atlas", 92, chunk_count=len(chunks), source_count=manifest["source_count"])
    return {"chunk_count": len(chunks), "source_count": manifest["source_count"], "cached": 0}


def chunk_corpus(corpus: Path) -> list[dict[str, Any]]:
    metadata = source_metadata_by_markdown(corpus)
    chunks: list[dict[str, Any]] = []
    for md_path in sorted((corpus / "markdown").glob("*.md")):
        source = metadata.get(str(md_path.resolve())) or metadata.get(md_path.name) or fallback_source_metadata(md_path)
        source_chunks = chunk_markdown_file(md_path, source)
        chunks.extend(source_chunks)
    return chunks


def source_metadata_by_markdown(corpus: Path) -> dict[str, dict[str, Any]]:
    rows = read_jsonl(corpus / "ingested_sources.jsonl")
    by_path: dict[str, dict[str, Any]] = {}
    for idx, row in enumerate(rows, start=1):
        md = row.get("markdown_path")
        source_id = source_id_from_path(Path(md or row.get("local_path", f"{idx:04d}")))
        metadata = {
            "source_id": source_id,
            "title": row.get("title") or Path(md or "").stem,
            "publisher": row.get("publisher", "unknown"),
            "url": row.get("url", ""),
            "source_type": row.get("source_type", "unknown"),
            "local_path": row.get("local_path", ""),
            "markdown_path": md or "",
            "warning_flags": row.get("warning_flags", []),
        }
        if md:
            path = Path(md)
            by_path[str(path.resolve())] = metadata
            by_path[path.name] = metadata
    return by_path


def fallback_source_metadata(md_path: Path) -> dict[str, Any]:
    return {
        "source_id": source_id_from_path(md_path),
        "title": md_path.stem,
        "publisher": "unknown",
        "url": "",
        "source_type": "markdown",
        "local_path": "",
        "markdown_path": str(md_path),
        "warning_flags": [],
    }


def chunk_markdown_file(path: Path, source: dict[str, Any]) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8", errors="replace")
    text = strip_sidecar_header(text)
    blocks = markdown_blocks(text)
    raw_chunks: list[dict[str, Any]] = []
    pending: list[str] = []
    pending_path: list[str] = []

    def append_raw(text: str, section_path: list[str], chunk_type: str) -> None:
        body = text.strip()
        if not body:
            return
        raw_chunks.append(
            {
                "text": body,
                "section_path": list(section_path),
                "section_paths": [list(section_path)],
                "chunk_type": chunk_type,
            }
        )

    def flush() -> None:
        nonlocal pending, pending_path
        body = "\n\n".join(pending).strip()
        if not body:
            pending = []
            return
        append_raw(body, pending_path, "text")
        pending = []

    for block in blocks:
        if block["type"] == "heading":
            flush()
            pending_path = block["section_path"]
            continue
        if block["type"] == "table":
            flush()
            append_raw(block["text"], block["section_path"], "table")
            continue
        words = word_count(block["text"])
        if not pending:
            pending_path = block["section_path"]
        if word_count("\n\n".join(pending)) + words > 1100 and word_count("\n\n".join(pending)) >= 500:
            flush()
            pending_path = block["section_path"]
        pending.append(block["text"])
    flush()
    chunks = normalize_text_chunks(raw_chunks)
    return [
        make_chunk(
            source,
            path,
            index,
            chunk["text"],
            chunk["section_path"],
            chunk["chunk_type"],
            chunk.get("section_paths"),
        )
        for index, chunk in enumerate(chunks, start=1)
    ]


def normalize_text_chunks(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    chunks = split_oversized_text_chunks(chunks)
    chunks = merge_small_text_chunks(chunks, allow_oversized=True)
    chunks = split_oversized_text_chunks(chunks)
    return merge_small_text_chunks(chunks, allow_oversized=False)


def split_oversized_text_chunks(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for chunk in chunks:
        if chunk.get("chunk_type") != "text" or not text_is_oversized(chunk["text"]):
            result.append(chunk)
            continue
        for piece in split_oversized_text(chunk["text"]):
            result.append(
                {
                    **chunk,
                    "text": piece,
                    "section_path": list(chunk.get("section_path") or []),
                    "section_paths": [list(path) for path in chunk.get("section_paths") or [chunk.get("section_path") or []]],
                }
            )
    return result


def merge_small_text_chunks(chunks: list[dict[str, Any]], allow_oversized: bool) -> list[dict[str, Any]]:
    chunks = [copy_raw_chunk(chunk) for chunk in chunks]
    while True:
        changed = False
        for index, chunk in enumerate(chunks):
            if chunk.get("chunk_type") != "text" or not text_is_small(chunk["text"]):
                continue
            previous_index = index - 1 if index > 0 and chunks[index - 1].get("chunk_type") == "text" else None
            next_index = index + 1 if index + 1 < len(chunks) and chunks[index + 1].get("chunk_type") == "text" else None
            target_index = choose_merge_target(chunks, index, previous_index, next_index, allow_oversized)
            if target_index is None:
                continue
            if target_index < index:
                chunks[target_index] = merge_text_chunk_pair(chunks[target_index], chunk)
                del chunks[index]
            else:
                chunks[index] = merge_text_chunk_pair(chunk, chunks[target_index])
                del chunks[target_index]
            changed = True
            break
        if not changed:
            return chunks


def choose_merge_target(
    chunks: list[dict[str, Any]],
    index: int,
    previous_index: int | None,
    next_index: int | None,
    allow_oversized: bool,
) -> int | None:
    if previous_index is None and next_index is None:
        return None
    preferred_index = previous_index if previous_index is not None else next_index
    alternate_index = next_index if preferred_index == previous_index else previous_index

    def would_fit(target_index: int | None) -> bool:
        if target_index is None:
            return False
        left, right = (target_index, index) if target_index < index else (index, target_index)
        return not text_is_oversized(merge_text_values(chunks[left]["text"], chunks[right]["text"]))

    if would_fit(preferred_index):
        return preferred_index
    if would_fit(alternate_index):
        return alternate_index
    return preferred_index if allow_oversized else None


def merge_text_chunk_pair(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    return {
        "text": merge_text_values(left["text"], right["text"]),
        "section_path": list(left.get("section_path") or []),
        "section_paths": unique_section_paths(
            [list(path) for path in left.get("section_paths") or [left.get("section_path") or []]]
            + [list(path) for path in right.get("section_paths") or [right.get("section_path") or []]]
        ),
        "chunk_type": "text",
    }


def copy_raw_chunk(chunk: dict[str, Any]) -> dict[str, Any]:
    return {
        "text": chunk["text"],
        "section_path": list(chunk.get("section_path") or []),
        "section_paths": [list(path) for path in chunk.get("section_paths") or [chunk.get("section_path") or []]],
        "chunk_type": chunk.get("chunk_type", "text"),
    }


def merge_text_values(left: str, right: str) -> str:
    return f"{left.rstrip()}\n\n{right.lstrip()}".strip()


def text_is_small(text: str) -> bool:
    return word_count(text) < MIN_TEXT_CHUNK_WORDS or len(text) < MIN_TEXT_CHUNK_CHARS


def text_is_oversized(text: str) -> bool:
    return word_count(text) > MAX_TEXT_CHUNK_WORDS or len(text) > MAX_TEXT_CHUNK_CHARS


def unique_section_paths(paths: list[list[str]]) -> list[list[str]]:
    result: list[list[str]] = []
    seen: set[tuple[str, ...]] = set()
    for path in paths:
        key = tuple(path)
        if key not in seen:
            result.append(path)
            seen.add(key)
    return result


def make_chunk(
    source: dict[str, Any],
    path: Path,
    index: int,
    text: str,
    section_path: list[str],
    chunk_type: str,
    section_paths: list[list[str]] | None = None,
) -> dict[str, Any]:
    source_id = source["source_id"]
    chunk_id = f"source_{source_id}__chunk_{index:04d}"
    flags = set(source.get("warning_flags") or [])
    lowered = text[:200000].lower()
    if "before you continue" in lowered or "captcha" in lowered or "verify you are human" in lowered:
        flags.add("bot_or_consent_wall")
    if "\x00" in text:
        flags.add("contains_nul_bytes")
    clean_text = re.sub(r"\x00", "", text).strip()
    if raw_pdf_corruption_metrics(clean_text)["raw_pdf_corrupt"]:
        flags.add("raw_pdf_markdown")
    section_path_label = format_section_path(section_path)
    section_path_labels = unique_labels(format_section_path(item) for item in (section_paths or [section_path]))
    metadata = {
        **source,
        "section_path": section_path_label,
        "chunk_type": chunk_type,
        "word_count": word_count(clean_text),
        "markdown_path": str(path),
        "warning_flags": sorted(flags),
    }
    if len(section_path_labels) > 1:
        metadata["section_paths"] = section_path_labels
    return {
        "id": chunk_id,
        "text": clean_text,
        "embedding_text": f"{source.get('title', '')}\n{metadata['section_path']}\n{clean_text}",
        "metadata": metadata,
    }


def format_section_path(section_path: list[str]) -> str:
    return " > ".join(section_path) if section_path else ""


def unique_labels(labels: Any) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for label in labels:
        if label and label not in seen:
            result.append(label)
            seen.add(label)
    return result


def strip_sidecar_header(text: str) -> str:
    lines = text.splitlines()
    if lines and lines[0].startswith("#"):
        for idx, line in enumerate(lines[:40]):
            if line.strip() == "---":
                return "\n".join(lines[idx + 1 :]).strip()
    return text.strip()


def markdown_blocks(text: str) -> list[dict[str, Any]]:
    blocks = []
    section_path: list[str] = []
    paragraph: list[str] = []
    table: list[str] = []

    def flush_paragraph() -> None:
        nonlocal paragraph
        body = "\n".join(paragraph).strip()
        if body:
            blocks.append({"type": "text", "text": body, "section_path": list(section_path)})
        paragraph = []

    def flush_table() -> None:
        nonlocal table
        body = "\n".join(table).strip()
        if body:
            blocks.append({"type": "table", "text": body, "section_path": list(section_path)})
        table = []

    for raw in text.splitlines():
        line = raw.rstrip()
        heading = re.match(r"^(#{1,6})\s+(.+)$", line)
        if heading:
            flush_paragraph()
            flush_table()
            level = len(heading.group(1))
            title = heading.group(2).strip()
            section_path = section_path[: max(0, level - 1)] + [title]
            blocks.append({"type": "heading", "text": title, "section_path": list(section_path)})
            continue
        if line.strip().startswith("|") and line.strip().endswith("|"):
            flush_paragraph()
            table.append(line)
            continue
        if table:
            flush_table()
        if not line.strip():
            flush_paragraph()
        else:
            paragraph.append(line)
    flush_paragraph()
    flush_table()
    return blocks


def split_oversized_text(text: str) -> list[str]:
    text = text.strip()
    if not text or not text_is_oversized(text):
        return [text] if text else []
    units: list[str] = []
    for paragraph in [part.strip() for part in re.split(r"\n{2,}", text) if part.strip()]:
        if text_is_oversized(paragraph):
            units.extend(split_oversized_paragraph(paragraph))
        else:
            units.append(paragraph)
    return pack_text_units(units)


def split_oversized_paragraph(text: str) -> list[str]:
    sentences = [sentence.strip() for sentence in re.split(r"(?<=[.!?])\s+", text) if sentence.strip()]
    if len(sentences) <= 1:
        return split_by_word_windows(text)
    parts: list[str] = []
    for sentence in sentences:
        if text_is_oversized(sentence):
            parts.extend(split_by_word_windows(sentence))
        else:
            parts.append(sentence)
    return parts


def pack_text_units(units: list[str]) -> list[str]:
    pieces: list[str] = []
    current = ""
    for unit in units:
        if not unit:
            continue
        if text_is_oversized(unit):
            if current:
                pieces.append(current)
                current = ""
            pieces.extend(split_by_word_windows(unit))
            continue
        candidate = merge_text_values(current, unit) if current else unit
        if current and text_is_oversized(candidate):
            pieces.append(current)
            current = unit
        else:
            current = candidate
    if current:
        pieces.append(current)
    return [piece.strip() for piece in pieces if piece.strip()]


def split_by_word_windows(text: str) -> list[str]:
    words = text.split()
    if not words:
        return []
    pieces: list[str] = []
    current: list[str] = []
    for word in words:
        if len(word) > MAX_TEXT_CHUNK_CHARS:
            if current:
                pieces.append(" ".join(current))
                current = []
            pieces.extend(word[index : index + MAX_TEXT_CHUNK_CHARS] for index in range(0, len(word), MAX_TEXT_CHUNK_CHARS))
            continue
        candidate = " ".join(current + [word])
        if current and text_is_oversized(candidate):
            pieces.append(" ".join(current))
            current = [word]
        else:
            current.append(word)
    if current:
        pieces.append(" ".join(current))
    return [piece for piece in pieces if piece]


def embed_texts(texts: list[str]) -> Any:
    status = dependency_status()
    if not status["ready_for_build"]:
        missing = [name for name, ok in status["python"].items() if name in {"sentence_transformers", "numpy"} and not ok]
        raise AtlasDependencyError(f"Missing Atlas embedding dependencies: {', '.join(missing)}. Install with: python3 -m pip install sentence-transformers umap-learn scikit-learn numpy")
    from sentence_transformers import SentenceTransformer  # type: ignore

    model = SentenceTransformer(MODEL_NAME, cache_folder=str(MODEL_CACHE))
    return model.encode(texts, batch_size=16, show_progress_bar=False, normalize_embeddings=True)


def project_embeddings(embeddings: Any) -> list[tuple[float, float]]:
    import numpy as np  # type: ignore

    matrix = np.asarray(embeddings, dtype=np.float32)
    n = len(matrix)
    if n == 1:
        return [(0.0, 0.0)]
    if n == 2:
        return [(-1.0, 0.0), (1.0, 0.0)]
    try:
        import umap  # type: ignore

        reducer = umap.UMAP(n_components=2, n_neighbors=min(15, n - 1), min_dist=0.08, metric="cosine", random_state=42)
        coords = reducer.fit_transform(matrix)
    except Exception:
        centered = matrix - matrix.mean(axis=0, keepdims=True)
        u, s, _ = np.linalg.svd(centered, full_matrices=False)
        coords = u[:, :2] * s[:2]
        if coords.shape[1] == 1:
            coords = np.column_stack([coords[:, 0], np.zeros(n)])
    coords = normalize_coords(coords)
    return [(float(x), float(y)) for x, y in coords]


def normalize_coords(coords: Any) -> Any:
    import numpy as np  # type: ignore

    coords = np.asarray(coords, dtype=np.float32)
    mins = coords.min(axis=0)
    maxs = coords.max(axis=0)
    span = np.where(maxs - mins == 0, 1, maxs - mins)
    return ((coords - mins) / span) * 2 - 1


def corpus_signature(corpus: Path) -> str:
    files = []
    for path in sorted((corpus / "markdown").glob("*.md")):
        stat = path.stat()
        files.append({"path": path.name, "mtime": stat.st_mtime_ns, "size": stat.st_size})
    payload = {"model": MODEL_NAME, "files": files, "chunking": CHUNKING_VERSION}
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()


def get_points(corpus_id: str) -> list[dict[str, Any]]:
    corpus = resolve_corpus(corpus_id)
    return read_jsonl(corpus / "atlas" / "points.jsonl")


def get_chunk(corpus_id: str, chunk_id: str) -> dict[str, Any]:
    corpus = resolve_corpus(corpus_id)
    for chunk in read_jsonl(corpus / "atlas" / "chunks.jsonl"):
        if chunk.get("id") == chunk_id:
            return chunk
    raise ValueError("Chunk not found.")


def get_selections(corpus_id: str) -> dict[str, Any]:
    corpus = resolve_corpus(corpus_id)
    selections = {}
    for row in read_jsonl(corpus / "atlas" / "selections.jsonl"):
        if row.get("chunk_id"):
            selections[row["chunk_id"]] = row
    return selections


def update_selections(corpus_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    corpus = resolve_corpus(corpus_id)
    atlas_dir = corpus / "atlas"
    atlas_dir.mkdir(exist_ok=True)
    path = atlas_dir / "selections.jsonl"
    current = get_selections(corpus_id)
    updates = payload.get("updates") or [payload]
    allowed = {"none", "keep", "reject", "key_evidence", "maybe"}
    now = datetime.now().isoformat(timespec="seconds")
    for update in updates:
        chunk_id = update.get("chunk_id")
        if not chunk_id:
            continue
        status = update.get("status", "none")
        if status not in allowed:
            raise ValueError(f"Invalid selection status: {status}")
        if status == "none":
            current.pop(chunk_id, None)
            continue
        current[chunk_id] = {
            "chunk_id": chunk_id,
            "status": status,
            "notes": update.get("notes", ""),
            "selected_at": now,
        }
    write_jsonl(path, list(current.values()))
    return current


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.strip():
            try:
                rows.append(json.loads(line))
            except Exception:
                continue
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + ("\n" if rows else ""), encoding="utf-8")
    tmp.replace(path)


def source_id_from_path(path: Path) -> str:
    match = re.match(r"^(\d{4})", path.stem)
    return match.group(1) if match else hashlib.sha1(path.name.encode("utf-8")).hexdigest()[:8]


def word_count(text: str) -> int:
    return len(re.findall(r"\b[\w'-]+\b", text))
