"""
Extracts plain text from knowledge-base sources: uploaded documents
(.txt, .md, .html, .docx, .pdf) or a fetched web page.

Same principle as app/routers/admin_uploads.py's image handling: the
content type is determined by sniffing actual bytes, never trusted
from the client-supplied filename extension or Content-Type header —
both are attacker-controlled, and a mismatch (e.g. a renamed binary
file claiming to be .txt) is rejected outright rather than silently
misparsed.
"""
from __future__ import annotations

import io
import zipfile

import httpx
from bs4 import BeautifulSoup
from docx import Document
from pypdf import PdfReader

from app.net_safety import UnsafeUrlError, assert_public_http_url

ALLOWED_TEXT_EXTENSIONS = {".txt", ".md"}
ALLOWED_HTML_EXTENSIONS = {".html", ".htm"}

MAX_URL_RESPONSE_BYTES = 5 * 1024 * 1024  # 5 MB
URL_FETCH_TIMEOUT_SECONDS = 15.0


class ExtractionError(Exception):
    """Raised for any file/URL that can't be turned into usable text —
    unsupported type, corrupt content, sniff mismatch, or (for URLs) a
    disallowed/unreachable address. Always a clear, user-facing message,
    never a raw parser traceback."""


# ── Byte sniffing ────────────────────────────────────────────────────

def _sniff_pdf(raw: bytes) -> bool:
    return raw[:5] == b"%PDF-"


def _sniff_docx(raw: bytes) -> bool:
    # docx is a zip container with a specific internal layout — plain
    # "starts with the zip magic number" isn't enough to trust it's
    # really a Word document, so open it and check for the expected
    # part rather than just matching the first 4 bytes.
    if raw[:4] != b"PK\x03\x04":
        return False
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as zf:
            return "word/document.xml" in zf.namelist()
    except zipfile.BadZipFile:
        return False


def _looks_binary(raw: bytes) -> bool:
    """Rejects "text" uploads that are actually some other binary
    format (renamed .exe, image, etc.) — a genuine text/markdown/HTML
    file won't contain NUL bytes or a high proportion of non-printable
    control characters in its first chunk."""
    sample = raw[:2048]
    if b"\x00" in sample:
        return True
    printable = sum(1 for b in sample if 9 <= b <= 13 or 32 <= b <= 126 or b >= 128)
    return sample and (printable / len(sample)) < 0.85


# ── Per-format extraction ──────────────────────────────────────────────

def _extract_pdf(raw: bytes) -> str:
    try:
        reader = PdfReader(io.BytesIO(raw))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception as e:
        raise ExtractionError(f"Could not read PDF: {e}") from e


def _extract_docx(raw: bytes) -> str:
    try:
        doc = Document(io.BytesIO(raw))
        return "\n".join(p.text for p in doc.paragraphs)
    except Exception as e:
        raise ExtractionError(f"Could not read Word document: {e}") from e


def _extract_html(raw_html: str) -> str:
    soup = BeautifulSoup(raw_html, "lxml")
    for tag in soup(["script", "style", "noscript", "template"]):
        tag.decompose()
    text = soup.get_text(separator="\n")
    # Collapse the run of blank lines BeautifulSoup's block-level
    # separators tend to produce into something readable.
    lines = [line.strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def _decode_text(raw: bytes) -> str:
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("utf-8", errors="replace")


# ── Public entry points ─────────────────────────────────────────────

def extract_from_upload(raw: bytes, filename: str, *, max_chars: int) -> tuple[str, bool, str]:
    """Returns (text, truncated, content_type). Raises ExtractionError
    for anything that isn't a genuinely-recognized, safe document type."""
    lower = filename.lower()
    is_pdf = _sniff_pdf(raw)
    is_docx = _sniff_docx(raw)

    if lower.endswith(".pdf") or is_pdf:
        if not is_pdf:
            raise ExtractionError("File content does not match a PDF.")
        text, content_type = _extract_pdf(raw), "pdf"
    elif lower.endswith(".docx") or is_docx:
        if not is_docx:
            raise ExtractionError("File content does not match a Word (.docx) document.")
        text, content_type = _extract_docx(raw), "docx"
    elif any(lower.endswith(ext) for ext in ALLOWED_HTML_EXTENSIONS):
        if is_pdf or is_docx or _looks_binary(raw):
            raise ExtractionError("File content does not match an HTML file.")
        text, content_type = _extract_html(_decode_text(raw)), "html"
    elif any(lower.endswith(ext) for ext in ALLOWED_TEXT_EXTENSIONS):
        if is_pdf or is_docx or _looks_binary(raw):
            raise ExtractionError("File content does not match a plain text file.")
        text, content_type = _decode_text(raw), "markdown" if lower.endswith(".md") else "text"
    else:
        raise ExtractionError("Unsupported file type. Please upload .txt, .md, .html, .docx, or .pdf.")

    return _cap(text, max_chars) + (content_type,)


# ── URL fetching, with SSRF guards ──────────────────────────────────
#
# The actual check lives in app/net_safety.py, shared with
# webhook_service.py's outbound delivery path — see that module's
# docstring for what it does and doesn't defend against.


def _validate_public_url(url: str) -> None:
    try:
        assert_public_http_url(url)
    except UnsafeUrlError as e:
        raise ExtractionError(str(e)) from e


def extract_from_url(url: str, *, max_chars: int) -> tuple[str, bool, str, str]:
    """Returns (text, truncated, content_type, page_title)."""
    _validate_public_url(url)

    try:
        with httpx.stream("GET", url, follow_redirects=True, timeout=URL_FETCH_TIMEOUT_SECONDS,
                           headers={"User-Agent": "PerenniaKnowledgeBaseBot/1.0"}) as resp:
            resp.raise_for_status()
            # Re-validate the final URL after redirects — a redirect
            # could otherwise be used to reach a blocked address.
            _validate_public_url(str(resp.url))

            content_type_header = resp.headers.get("content-type", "")
            chunks = []
            total = 0
            for chunk in resp.iter_bytes():
                total += len(chunk)
                if total > MAX_URL_RESPONSE_BYTES:
                    raise ExtractionError(
                        f"Page is too large (over {MAX_URL_RESPONSE_BYTES // (1024 * 1024)}MB)."
                    )
                chunks.append(chunk)
            raw = b"".join(chunks)
    except httpx.HTTPStatusError as e:
        raise ExtractionError(f"The page returned an error: HTTP {e.response.status_code}") from e
    except httpx.HTTPError as e:
        raise ExtractionError(f"Could not fetch that page: {e}") from e

    if "html" in content_type_header:
        html = _decode_text(raw)
        soup = BeautifulSoup(html, "lxml")
        title = soup.title.get_text(strip=True) if soup.title else url
        text = _extract_html(html)
        content_type = "html"
    elif "text/plain" in content_type_header or not content_type_header:
        text = _decode_text(raw)
        title = url
        content_type = "text"
    else:
        raise ExtractionError(f"Unsupported page content type: {content_type_header or 'unknown'}")

    capped_text, truncated = _cap(text, max_chars)
    return capped_text, truncated, content_type, title


def _cap(text: str, max_chars: int) -> tuple[str, bool]:
    text = text.strip()
    if len(text) > max_chars:
        return text[:max_chars], True
    return text, False
