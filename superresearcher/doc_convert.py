from __future__ import annotations

import html
import mimetypes
import re
import shutil
import subprocess
import urllib.parse
import urllib.request
import zlib
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from .config import atomic_write_text, slugify


DATA_EXTS = {".csv", ".tsv", ".xlsx", ".xls", ".json", ".zip", ".parquet", ".sav", ".dta"}


def detect_magic(path: Path) -> str:
    data = path.read_bytes()[:8192]
    stripped = data.lstrip().lower()
    if data.startswith(b"%PDF-"):
        return "pdf"
    if data.startswith(b"PK\x03\x04"):
        return "zip"
    if data.startswith(b"\xff\xd8\xff"):
        return "jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if stripped.startswith((b"<!doctype html", b"<html")) or b"<html" in stripped[:4096]:
        return "html"
    if path.suffix.lower() in {".json", ".jsonl", ".csv", ".tsv", ".txt", ".md"}:
        return "text"
    return "unknown"


def preferred_suffix(path: Path) -> str:
    kind = detect_magic(path)
    if kind == "pdf":
        return ".pdf"
    if kind == "html":
        return ".html"
    if kind == "jpeg":
        return ".jpg"
    if kind == "png":
        return ".png"
    if kind == "zip" and path.suffix.lower() in {".xlsx", ".docx", ".pptx", ".zip"}:
        return path.suffix.lower()
    return path.suffix.lower() or ".dat"


def convert_file_to_markdown(path: Path, source: dict[str, Any], markdown_path: Path, assets_root: Path) -> dict[str, Any]:
    source_id = source_identifier(path, source)
    asset_dir = assets_root / source_id
    asset_dir.mkdir(parents=True, exist_ok=True)
    title = source.get("title") or path.stem
    kind = detect_magic(path)
    header = [
        f"# {title}",
        "",
        f"- URL: {source.get('url', '')}",
        f"- Publisher: {source.get('publisher', '')}",
        f"- Source type: {source.get('source_type', kind)}",
        f"- Original file: {path}",
        "",
        "---",
        "",
    ]
    notes: list[str] = []
    if kind == "pdf":
        body, pdf_notes = pdf_to_markdown(path, asset_dir)
        notes.extend(pdf_notes)
    elif kind == "html":
        body, html_notes = html_file_to_markdown(path, source.get("url", ""), asset_dir)
        notes.extend(html_notes)
    elif path.suffix.lower() in DATA_EXTS:
        body = data_to_markdown(path)
    else:
        body = text_to_markdown(path)
    atomic_write_text(markdown_path, "\n".join(header) + body.strip() + "\n")
    return {"markdown_path": str(markdown_path), "conversion_notes": notes, "asset_dir": str(asset_dir)}


def pdf_to_markdown(path: Path, asset_dir: Path) -> tuple[str, list[str]]:
    notes: list[str] = []
    for converter in (pdf_via_pymupdf4llm, pdf_via_docling, pdf_via_pymupdf):
        try:
            body = converter(path, asset_dir)
            if body and len(body.strip()) > 100:
                return body, notes
        except Exception as exc:
            notes.append(f"{converter.__name__}_failed:{str(exc)[:120]}")
    body = pdf_via_system_or_rough(path)
    notes.append("pdf_fallback_text_only")
    return body, notes


def pdf_via_pymupdf4llm(path: Path, asset_dir: Path) -> str:
    import pymupdf4llm  # type: ignore

    kwargs = {
        "write_images": True,
        "image_path": str(asset_dir),
        "image_format": "png",
    }
    try:
        return pymupdf4llm.to_markdown(str(path), **kwargs)
    except TypeError:
        return pymupdf4llm.to_markdown(str(path))


def pdf_via_docling(path: Path, asset_dir: Path) -> str:
    from docling.document_converter import DocumentConverter  # type: ignore

    result = DocumentConverter().convert(str(path))
    document = result.document
    try:
        return document.export_to_markdown(image_placeholder=f"{asset_dir}/")
    except TypeError:
        return document.export_to_markdown()


def pdf_via_pymupdf(path: Path, asset_dir: Path) -> str:
    import fitz  # type: ignore

    doc = fitz.open(str(path))
    parts: list[str] = ["## Extracted PDF Content", ""]
    for page_index, page in enumerate(doc, start=1):
        parts.extend([f"## Page {page_index}", ""])
        try:
            tables = page.find_tables()
            for table_index, table in enumerate(tables, start=1):
                rows = table.extract()
                table_md = rows_to_markdown(rows)
                if table_md:
                    parts.extend([f"### Table {page_index}.{table_index}", "", table_md, ""])
        except Exception:
            pass
        try:
            text = page.get_text("markdown")
        except Exception:
            text = page.get_text("text")
        if text.strip():
            parts.extend([text.strip(), ""])
        for image_index, img in enumerate(page.get_images(full=True), start=1):
            xref = img[0]
            try:
                image = doc.extract_image(xref)
                ext = image.get("ext", "png")
                img_path = asset_dir / f"page-{page_index:03d}-image-{image_index:03d}.{ext}"
                img_path.write_bytes(image["image"])
                parts.extend([f"![Page {page_index} image {image_index}]({markdown_asset_link(img_path, asset_dir)})", ""])
            except Exception:
                continue
    doc.close()
    return "\n".join(parts)


def pdf_via_system_or_rough(path: Path) -> str:
    pdftotext = shutil.which("pdftotext")
    if pdftotext:
        try:
            result = subprocess.run([pdftotext, "-layout", str(path), "-"], capture_output=True, text=True, timeout=90)
            if result.returncode == 0 and result.stdout.strip():
                return "## Extracted PDF Text\n\n" + result.stdout
        except Exception:
            pass
    content = path.read_bytes()
    extracted = extract_pdf_text_rough(content)
    if extracted.strip():
        return "## Extracted PDF Text\n\n" + extracted
    return "PDF preserved locally. Full text extraction was not available for this file.\n"


def html_file_to_markdown(path: Path, base_url: str, asset_dir: Path) -> tuple[str, list[str]]:
    text = path.read_text(encoding="utf-8", errors="replace")
    try:
        return html_via_lxml(text, base_url, asset_dir)
    except Exception:
        parser = MarkdownHTMLParser(base_url, asset_dir)
        parser.feed(text)
        return parser.to_markdown(), parser.notes


def html_via_lxml(text: str, base_url: str, asset_dir: Path) -> tuple[str, list[str]]:
    from lxml import html as lxml_html  # type: ignore

    doc = lxml_html.fromstring(text)
    notes: list[str] = []
    title = clean_inline(" ".join(doc.xpath("//title/text()")[:1]))
    parts: list[str] = []
    if title:
        parts.extend([f"## {title}", ""])
    for bad in doc.xpath("//script|//style|//noscript"):
        bad.drop_tree()
    for element in doc.xpath("//body//*[self::h1 or self::h2 or self::h3 or self::p or self::li or self::table or self::img]"):
        tag = element.tag.lower()
        if tag in {"h1", "h2", "h3"}:
            level = int(tag[1])
            value = clean_inline(element.text_content())
            if value:
                parts.extend(["", "#" * level + f" {value}", ""])
        elif tag == "p":
            value = linkify_lxml_children(element, base_url)
            if value:
                parts.extend([value, ""])
        elif tag == "li":
            value = linkify_lxml_children(element, base_url)
            if value:
                parts.append(f"- {value}")
        elif tag == "table":
            table = lxml_table_to_markdown(element)
            if table:
                parts.extend(["", table, ""])
            else:
                parts.extend(["", lxml_html.tostring(element, encoding="unicode"), ""])
                notes.append("html_table_preserved_raw")
        elif tag == "img":
            src = element.get("src") or ""
            alt = element.get("alt") or "image"
            link, note = save_or_link_image(src, base_url, asset_dir, alt)
            if note:
                notes.append(note)
            if link:
                parts.extend([f"![{clean_inline(alt)}]({link})", ""])
    return "\n".join(parts), notes


def linkify_lxml_children(element: Any, base_url: str) -> str:
    text = clean_inline(element.text_content())
    links = []
    for link in element.xpath(".//a[@href]"):
        label = clean_inline(link.text_content())
        href = urllib.parse.urljoin(base_url, link.get("href"))
        if label and href:
            links.append((label, href))
    for label, href in links[:8]:
        if label in text:
            text = text.replace(label, f"[{label}]({href})", 1)
    return text


def lxml_table_to_markdown(table: Any) -> str:
    rows: list[list[str]] = []
    for tr in table.xpath(".//tr"):
        cells = [clean_inline(cell.text_content()) for cell in tr.xpath("./th|./td")]
        if cells:
            rows.append(cells)
    return rows_to_markdown(rows)


class MarkdownHTMLParser(HTMLParser):
    def __init__(self, base_url: str, asset_dir: Path) -> None:
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.asset_dir = asset_dir
        self.lines: list[str] = []
        self.notes: list[str] = []
        self.stack: list[str] = []
        self.href: str | None = None
        self.table_rows: list[list[str]] = []
        self.current_row: list[str] | None = None
        self.current_cell: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = {k.lower(): v or "" for k, v in attrs}
        self.stack.append(tag)
        if tag in {"h1", "h2", "h3"}:
            self.lines.extend(["", "#" * int(tag[1]) + " "])
        elif tag in {"p", "div", "section", "article"}:
            self.lines.append("")
        elif tag == "li":
            self.lines.append("- ")
        elif tag == "a":
            self.href = urllib.parse.urljoin(self.base_url, attrs_dict.get("href", ""))
        elif tag == "img":
            src = attrs_dict.get("src", "")
            alt = attrs_dict.get("alt", "image")
            link, note = save_or_link_image(src, self.base_url, self.asset_dir, alt)
            if note:
                self.notes.append(note)
            if link:
                self.lines.extend(["", f"![{clean_inline(alt)}]({link})", ""])
        elif tag == "table":
            self.table_rows = []
        elif tag == "tr":
            self.current_row = []
        elif tag in {"th", "td"}:
            self.current_cell = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "a":
            self.href = None
        elif tag in {"h1", "h2", "h3", "p", "li", "div", "section", "article"}:
            self.lines.append("")
        elif tag in {"th", "td"} and self.current_cell is not None and self.current_row is not None:
            self.current_row.append(clean_inline(" ".join(self.current_cell)))
            self.current_cell = None
        elif tag == "tr" and self.current_row:
            self.table_rows.append(self.current_row)
            self.current_row = None
        elif tag == "table":
            table = rows_to_markdown(self.table_rows)
            if table:
                self.lines.extend(["", table, ""])
            self.table_rows = []
        if self.stack:
            self.stack.pop()

    def handle_data(self, data: str) -> None:
        value = clean_inline(data)
        if not value:
            return
        if self.stack and self.stack[-1] in {"script", "style", "noscript"}:
            return
        if self.current_cell is not None:
            self.current_cell.append(value)
        elif self.href and self.href.startswith(("http://", "https://")):
            self.lines.append(f"[{value}]({self.href})")
        else:
            self.lines.append(value)

    def to_markdown(self) -> str:
        return "\n".join(self.lines)


def save_or_link_image(src: str, base_url: str, asset_dir: Path, alt: str) -> tuple[str, str | None]:
    if not src:
        return "", None
    full = urllib.parse.urljoin(base_url, src)
    parsed = urllib.parse.urlsplit(full)
    if parsed.scheme not in {"http", "https", "file"}:
        return full, "image_link_preserved_non_http"
    suffix = Path(parsed.path).suffix.lower()
    if suffix not in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"}:
        suffix = mimetypes.guess_extension("image/png") or ".png"
    filename = slugify(alt or Path(parsed.path).stem or "image")[:50] + suffix
    target = unique_path(asset_dir / filename)
    try:
        if parsed.scheme == "file":
            target.write_bytes(Path(urllib.parse.unquote(parsed.path)).read_bytes())
        else:
            req = urllib.request.Request(full, headers={"User-Agent": "SuperResearcher/0.2"})
            with urllib.request.urlopen(req, timeout=20) as resp:
                target.write_bytes(resp.read())
        return markdown_asset_link(target, asset_dir), None
    except Exception as exc:
        return full, f"image_download_failed:{str(exc)[:80]}"


def rows_to_markdown(rows: list[list[Any]]) -> str:
    cleaned = [[clean_inline(str(cell)) for cell in row] for row in rows if any(clean_inline(str(cell)) for cell in row)]
    if not cleaned:
        return ""
    width = max(len(row) for row in cleaned)
    padded = [row + [""] * (width - len(row)) for row in cleaned]
    header = padded[0]
    body = padded[1:]
    lines = [
        "| " + " | ".join(escape_cell(cell) for cell in header) + " |",
        "| " + " | ".join("---" for _ in header) + " |",
    ]
    for row in body:
        lines.append("| " + " | ".join(escape_cell(cell) for cell in row) + " |")
    return "\n".join(lines)


def data_to_markdown(path: Path) -> str:
    content = path.read_bytes()
    if path.suffix.lower() in {".csv", ".tsv", ".json"} or len(content) < 200000:
        sample = content[:20000].decode("utf-8", errors="replace")
        return f"## Data File Preview\n\nOriginal data file is preserved at `{path}`.\n\n```text\n{sample}\n```\n"
    return f"Data file preserved locally at `{path}`. Preview skipped because the file is large or binary.\n"


def text_to_markdown(path: Path) -> str:
    return "## Extracted Text\n\n" + path.read_text(encoding="utf-8", errors="replace")


def source_identifier(path: Path, source: dict[str, Any]) -> str:
    stem = path.stem
    match = re.match(r"^(\d{4})", stem)
    if match:
        return match.group(1)
    return slugify(source.get("title") or stem)[:48]


def unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    for i in range(2, 10000):
        candidate = path.with_name(f"{path.stem}-{i}{path.suffix}")
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"Could not allocate unique path for {path}")


def markdown_asset_link(path: Path, asset_dir: Path) -> str:
    return f"../assets/{asset_dir.name}/{path.name}".replace(" ", "%20")


def clean_inline(value: str) -> str:
    return html.unescape(re.sub(r"\s+", " ", value or "")).strip()


def escape_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def extract_pdf_text_rough(content: bytes) -> str:
    streams = re.findall(rb"stream\r?\n(.*?)\r?\nendstream", content, flags=re.S)
    chunks: list[str] = []
    for stream in streams[:200]:
        data = stream.strip()
        for candidate in (data, try_flate(data)):
            if not candidate:
                continue
            text = extract_pdf_text_operators(candidate)
            if text:
                chunks.append(text)
                break
    if chunks:
        return "\n\n".join(chunks)
    ascii_text = re.sub(rb"[^\x09\x0A\x0D\x20-\x7E]+", b" ", content)
    return ascii_text[:200000].decode("utf-8", errors="replace")


def try_flate(data: bytes) -> bytes:
    try:
        return zlib.decompress(data)
    except Exception:
        return b""


def extract_pdf_text_operators(data: bytes) -> str:
    text = data.decode("latin-1", errors="ignore")
    parts: list[str] = []
    for block in re.findall(r"BT(.*?)ET", text, flags=re.S):
        for item in re.findall(r"\((?:\\.|[^\\)])*\)\s*Tj", block, flags=re.S):
            parts.append(unescape_pdf_string(item[:-2].strip()))
        for array in re.findall(r"\[(.*?)\]\s*TJ", block, flags=re.S):
            for raw in re.findall(r"\((?:\\.|[^\\)])*\)", array):
                parts.append(unescape_pdf_string(raw))
    return "\n".join(clean_inline(p) for p in parts if clean_inline(p))


def unescape_pdf_string(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith("(") and raw.endswith(")"):
        raw = raw[1:-1]
    return raw.replace(r"\(", "(").replace(r"\)", ")").replace(r"\\", "\\").replace(r"\n", "\n").replace(r"\r", "\n").replace(r"\t", "\t")
