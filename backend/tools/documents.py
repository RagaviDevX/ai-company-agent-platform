from pathlib import Path

import fitz
from docx import Document


def read_pdf(file_path: str) -> str:
    doc = fitz.open(file_path)
    text = "".join(page.get_text() for page in doc)
    doc.close()
    return text


def read_docx(file_path: str) -> str:
    document = Document(file_path)
    return "\n".join(p.text for p in document.paragraphs)


def extract_text(file_path: str) -> str:
    suffix = Path(file_path).suffix.lower()
    if suffix == ".pdf":
        return read_pdf(file_path)
    if suffix in {".docx", ".doc"}:
        return read_docx(file_path)
    if suffix in {".txt", ".md", ".csv", ".py", ".json"}:
        return Path(file_path).read_text(encoding="utf-8", errors="ignore")
    raise ValueError(f"Unsupported document type: {suffix}")


def chunk_text(text: str, size: int = 800, overlap: int = 120) -> list[str]:
    cleaned = " ".join(text.split())
    if not cleaned:
        return []
    chunks = []
    start = 0
    while start < len(cleaned):
        end = min(len(cleaned), start + size)
        chunks.append(cleaned[start:end])
        if end == len(cleaned):
            break
        start = max(0, end - overlap)
    return chunks
