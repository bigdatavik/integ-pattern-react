"""Process uploaded requirements documents."""

import os
from typing import Tuple


def extract_text(file_bytes: bytes, file_name: str) -> Tuple[str, bool]:
    """Extract text from an uploaded file.

    Returns:
        Tuple of (extracted_text, success_flag)
    """
    ext = os.path.splitext(file_name)[1].lower()

    if ext in (".txt", ".md"):
        try:
            return file_bytes.decode("utf-8"), True
        except UnicodeDecodeError:
            return file_bytes.decode("latin-1"), True

    if ext == ".pdf":
        try:
            import io
            import PyPDF2
            reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
            if text.strip():
                return text, True
        except Exception:
            pass
        return "", False

    if ext == ".docx":
        try:
            import io
            import docx
            doc = docx.Document(io.BytesIO(file_bytes))
            text = "\n".join(p.text for p in doc.paragraphs)
            if text.strip():
                return text, True
        except Exception:
            pass
        return "", False

    return "", False


def combine_requirements(extracted_text: str, manual_text: str) -> str:
    """Combine extracted and manually entered requirements."""
    parts = []
    if extracted_text.strip():
        parts.append("## Extracted from uploaded document\n")
        parts.append(extracted_text.strip())
    if manual_text.strip():
        if parts:
            parts.append("\n\n")
        parts.append("## Additional requirements\n")
        parts.append(manual_text.strip())
    return "\n".join(parts) if parts else "No requirements provided."
