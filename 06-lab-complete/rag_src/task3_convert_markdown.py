"""Task 3 - Convert landing files to Markdown."""

import json
import re
import zipfile
from html import escape
from pathlib import Path
from xml.etree import ElementTree

try:
    from markitdown import MarkItDown
except Exception:  # pragma: no cover
    MarkItDown = None

LANDING_DIR = Path(__file__).parent.parent / "data" / "landing"
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "standardized"


def _docx_to_text(filepath: Path) -> str:
    namespaces = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    with zipfile.ZipFile(filepath) as archive:
        xml = archive.read("word/document.xml")
    root = ElementTree.fromstring(xml)
    paragraphs = []
    for paragraph in root.findall(".//w:p", namespaces):
        text = "".join(node.text or "" for node in paragraph.findall(".//w:t", namespaces))
        text = text.strip()
        if text:
            paragraphs.append(text)
    return "\n\n".join(paragraphs)


def _convert_with_best_effort(filepath: Path) -> str:
    if MarkItDown is not None:
        try:
            result = MarkItDown().convert(str(filepath))
            text = getattr(result, "text_content", "") or ""
            if text.strip():
                return text
        except Exception as exc:
            print(f"  MarkItDown failed for {filepath.name}: {exc}")

    if filepath.suffix.lower() == ".docx":
        return _docx_to_text(filepath)
    return filepath.read_text(encoding="utf-8", errors="ignore")


def _json_article_to_markdown(data: dict) -> str:
    title = data.get("title") or data.get("headline") or "Untitled article"
    url = data.get("url", "N/A")
    crawled = data.get("crawl_date") or data.get("date_crawled") or "N/A"
    content = (
        data.get("content_markdown")
        or data.get("markdown")
        or data.get("content")
        or data.get("text")
        or ""
    )
    if not str(content).strip():
        content = escape(json.dumps(data, ensure_ascii=False, indent=2))
    content = re.sub(r"\n{3,}", "\n\n", str(content)).strip()
    return (
        f"# {title}\n\n"
        f"**Source:** {url}\n\n"
        f"**Crawled:** {crawled}\n\n"
        "---\n\n"
        f"{content}\n"
    )


def convert_legal_docs() -> list[Path]:
    """Convert PDF/DOC/DOCX files in data/landing/legal to Markdown."""
    legal_dir = LANDING_DIR / "legal"
    output_dir = OUTPUT_DIR / "legal"
    output_dir.mkdir(parents=True, exist_ok=True)
    if not legal_dir.exists():
        return []

    outputs = []
    for filepath in sorted(legal_dir.iterdir()):
        if filepath.suffix.lower() in {".pdf", ".docx", ".doc"}:
            print(f"Converting: {filepath.name}")
            text = _convert_with_best_effort(filepath)
            output_path = output_dir / f"{filepath.stem}.md"
            output_path.write_text(text, encoding="utf-8")
            outputs.append(output_path)
            print(f"  Saved: {output_path}")
    return outputs


def convert_news_articles() -> list[Path]:
    """Convert crawled news files in data/landing/news to Markdown."""
    news_dir = LANDING_DIR / "news"
    output_dir = OUTPUT_DIR / "news"
    output_dir.mkdir(parents=True, exist_ok=True)
    if not news_dir.exists():
        return []

    outputs = []
    for filepath in sorted(news_dir.iterdir()):
        if filepath.suffix.lower() == ".json":
            print(f"Converting: {filepath.name}")
            data = json.loads(filepath.read_text(encoding="utf-8"))
            output_path = output_dir / f"{filepath.stem}.md"
            output_path.write_text(_json_article_to_markdown(data), encoding="utf-8")
            outputs.append(output_path)
            print(f"  Saved: {output_path}")
        elif filepath.suffix.lower() in {".html", ".md", ".txt"}:
            output_path = output_dir / f"{filepath.stem}.md"
            output_path.write_text(_convert_with_best_effort(filepath), encoding="utf-8")
            outputs.append(output_path)
    return outputs


def convert_all() -> list[Path]:
    """Convert all landing files while preserving legal/news subdirectories."""
    print("Task 3: Convert to Markdown")
    outputs = []
    outputs.extend(convert_legal_docs())
    outputs.extend(convert_news_articles())
    print(f"Done. Wrote {len(outputs)} markdown files to {OUTPUT_DIR}")
    return outputs


if __name__ == "__main__":
    convert_all()
