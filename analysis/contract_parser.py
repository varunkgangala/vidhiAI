import os
import io


def extract_text_from_pdf(file_stream) -> str:
    try:
        from pypdf import PdfReader
        reader = PdfReader(file_stream)
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
        return text.strip()
    except Exception as e:
        raise ValueError(f"PDF extraction failed: {e}")


def extract_text_from_docx(file_stream) -> str:
    try:
        from docx import Document
        doc = Document(file_stream)
        text = "\n".join(para.text for para in doc.paragraphs)
        return text.strip()
    except Exception as e:
        raise ValueError(f"DOCX extraction failed: {e}")


def extract_text_from_txt(file_stream) -> str:
    try:
        raw = file_stream.read()
        return raw.decode("utf-8", errors="replace").strip()
    except Exception as e:
        raise ValueError(f"TXT extraction failed: {e}")


def parse_contract(file, filename: str) -> str:
    ext = os.path.splitext(filename)[1].lower()
    if ext == ".pdf":
        return extract_text_from_pdf(file)
    elif ext in (".docx", ".doc"):
        return extract_text_from_docx(file)
    elif ext == ".txt":
        return extract_text_from_txt(file)
    else:
        raise ValueError(f"Unsupported file type: {ext}")


ALLOWED_EXTENSIONS = {".pdf", ".docx", ".doc", ".txt"}


def is_allowed_file(filename: str) -> bool:
    return os.path.splitext(filename)[1].lower() in ALLOWED_EXTENSIONS
