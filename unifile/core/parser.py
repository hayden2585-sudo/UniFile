"""
Unifile by Soniscorett - Universal Read-Only File Parser
Safely inspects and extracts text from any file type (PDF, DOCX, XLSX, PPTX,
CSV, HTML, JSON, Archives, Code, Images, Raw Binaries) in strictly read-only mode.
"""

from __future__ import annotations
import csv
import io
import os
import re
import tarfile
import zipfile
from pathlib import Path
from typing import Tuple, List, Dict, Any, Optional

import pypdf
import docx
import openpyxl
import pptx
from bs4 import BeautifulSoup
from PIL import Image, ExifTags


class UniversalParser:
    """Safe, read-only multi-format text extractor."""

    MAX_FILE_BYTES = 50 * 1024 * 1024  # 50 MB safety ceiling

    @classmethod
    def read_file(cls, path_or_bytes: str | Path | bytes | io.BytesIO, filename: Optional[str] = None) -> Tuple[str, Dict[str, Any]]:
        """
        Extracts human-readable text and structural metadata from any file.
        Strictly READ-ONLY. Guaranteed non-destructive.
        """
        metadata: Dict[str, Any] = {
            "source_type": "unknown",
            "filename": filename or "unknown_file",
            "size_bytes": 0,
            "read_only": True,
            "extracted_pages_or_records": 0,
        }

        # Resolve input stream
        raw_bytes: bytes
        if isinstance(path_or_bytes, (str, Path)):
            path = Path(path_or_bytes)
            if not path.exists():
                raise FileNotFoundError(f"File not found: {path}")
            metadata["filename"] = filename or path.name
            metadata["size_bytes"] = path.stat().st_size
            if metadata["size_bytes"] > cls.MAX_FILE_BYTES:
                raise ValueError(f"File size {metadata['size_bytes']} exceeds safe read limit ({cls.MAX_FILE_BYTES} bytes).")
            with open(path, "rb") as f:
                raw_bytes = f.read()
        elif isinstance(path_or_bytes, io.BytesIO):
            raw_bytes = path_or_bytes.getvalue()
            metadata["size_bytes"] = len(raw_bytes)
        elif isinstance(path_or_bytes, bytes):
            raw_bytes = path_or_bytes
            metadata["size_bytes"] = len(raw_bytes)
        else:
            raise TypeError("Unsupported file input format.")

        ext = Path(metadata["filename"]).suffix.lower()

        # Route by file extension / format
        try:
            if ext == ".pdf":
                text, count = cls._parse_pdf(raw_bytes)
                metadata["source_type"] = "pdf_document"
                metadata["extracted_pages_or_records"] = count
                return text, metadata

            elif ext in (".docx", ".doc"):
                text, count = cls._parse_docx(raw_bytes)
                metadata["source_type"] = "word_document"
                metadata["extracted_pages_or_records"] = count
                return text, metadata

            elif ext in (".xlsx", ".xls"):
                text, count = cls._parse_xlsx(raw_bytes)
                metadata["source_type"] = "excel_spreadsheet"
                metadata["extracted_pages_or_records"] = count
                return text, metadata

            elif ext in (".pptx", ".ppt"):
                text, count = cls._parse_pptx(raw_bytes)
                metadata["source_type"] = "presentation_document"
                metadata["extracted_pages_or_records"] = count
                return text, metadata

            elif ext in (".csv", ".tsv"):
                text, count = cls._parse_delimited(raw_bytes, delimiter="\t" if ext == ".tsv" else ",")
                metadata["source_type"] = "tabular_data"
                metadata["extracted_pages_or_records"] = count
                return text, metadata

            elif ext in (".html", ".htm", ".xhtml"):
                text = cls._parse_html(raw_bytes)
                metadata["source_type"] = "html_markup"
                return text, metadata

            elif ext == ".json":
                text = cls._parse_text_multi_encoding(raw_bytes)
                metadata["source_type"] = "json_data"
                return text, metadata

            elif ext in (".zip", ".tar", ".gz", ".tgz"):
                text, count = cls._parse_archive(raw_bytes, ext)
                metadata["source_type"] = "compressed_archive"
                metadata["extracted_pages_or_records"] = count
                return text, metadata

            elif ext in (".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".svg"):
                text = cls._parse_image_metadata(raw_bytes, ext)
                metadata["source_type"] = "image_media"
                return text, metadata

            elif ext in (
                ".txt", ".md", ".markdown", ".rst", ".log", ".py", ".js", ".ts",
                ".jsx", ".tsx", ".css", ".scss", ".xml", ".yaml", ".yml", ".toml",
                ".ini", ".conf", ".sh", ".bash", ".sql", ".c", ".cpp", ".h", ".rs",
                ".go", ".java", ".php", ".rb", ".dart", ".lua"
            ):
                text = cls._parse_text_multi_encoding(raw_bytes)
                metadata["source_type"] = "text_or_code"
                return text, metadata

            else:
                # Universal fallback: try text decoding first, then binary string extractor
                text, is_binary = cls._parse_universal_fallback(raw_bytes)
                metadata["source_type"] = "binary_stream" if is_binary else "untyped_text"
                return text, metadata

        except Exception as e:
            # Resilient fallback: never crash, fall back to universal binary string extraction
            fallback_text, _ = cls._parse_universal_fallback(raw_bytes)
            metadata["source_type"] = f"salvaged_stream ({type(e).__name__})"
            return fallback_text, metadata

    @classmethod
    def _parse_pdf(cls, data: bytes) -> Tuple[str, int]:
        reader = pypdf.PdfReader(io.BytesIO(data))
        num_pages = len(reader.pages)
        parts = []
        for i, page in enumerate(reader.pages):
            txt = page.extract_text() or ""
            parts.append(f"--- Page {i+1} / {num_pages} ---\n{txt}")
        return "\n\n".join(parts), num_pages

    @classmethod
    def _parse_docx(cls, data: bytes) -> Tuple[str, int]:
        doc = docx.Document(io.BytesIO(data))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        # Extract tables
        for table in doc.tables:
            for row in table.rows:
                row_cells = [cell.text.strip().replace("\n", " ") for cell in row.cells]
                paragraphs.append(" | ".join(row_cells))
        return "\n\n".join(paragraphs), len(paragraphs)

    @classmethod
    def _parse_xlsx(cls, data: bytes) -> Tuple[str, int]:
        wb = openpyxl.load_workbook(io.BytesIO(data), data_only=True, read_only=True)
        sections = []
        total_rows = 0
        for sheet in wb.sheetnames:
            ws = wb[sheet]
            sections.append(f"### Sheet: {sheet}")
            for row in ws.iter_rows(values_only=True):
                # Filter out completely empty rows
                if any(v is not None for v in row):
                    row_str = " | ".join(str(c if c is not None else "") for c in row)
                    sections.append(row_str)
                    total_rows += 1
        return "\n".join(sections), total_rows

    @classmethod
    def _parse_pptx(cls, data: bytes) -> Tuple[str, int]:
        prs = pptx.Presentation(io.BytesIO(data))
        slides_text = []
        for i, slide in enumerate(prs.slides):
            slide_parts = [f"--- Slide {i+1} ---"]
            for shape in slide.shapes:
                if shape.has_text_frame:
                    for paragraph in shape.text_frame.paragraphs:
                        text = paragraph.text.strip()
                        if text:
                            slide_parts.append(text)
            slides_text.append("\n".join(slide_parts))
        return "\n\n".join(slides_text), len(prs.slides)

    @classmethod
    def _parse_delimited(cls, data: bytes, delimiter: str = ",") -> Tuple[str, int]:
        text = cls._parse_text_multi_encoding(data)
        reader = csv.reader(io.StringIO(text), delimiter=delimiter)
        lines = []
        count = 0
        for row in reader:
            if row:
                lines.append(" | ".join(row))
                count += 1
        return "\n".join(lines), count

    @classmethod
    def _parse_html(cls, data: bytes) -> str:
        raw_text = cls._parse_text_multi_encoding(data)
        soup = BeautifulSoup(raw_text, "html.parser")
        # Remove scripts, styles
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        return soup.get_text(separator="\n", strip=True)

    @classmethod
    def _parse_archive(cls, data: bytes, ext: str) -> Tuple[str, int]:
        parts = []
        file_count = 0
        if ext == ".zip":
            with zipfile.ZipFile(io.BytesIO(data), "r") as z:
                for info in z.infolist()[:50]:  # Cap at 50 internal files
                    if not info.is_dir() and info.file_size < 5 * 1024 * 1024:
                        try:
                            content = z.read(info.filename)
                            inner_text, _ = cls._parse_universal_fallback(content)
                            parts.append(f"=== File: {info.filename} ({info.file_size} bytes) ===\n{inner_text[:10000]}")
                            file_count += 1
                        except Exception:
                            pass
        else:
            with tarfile.open(fileobj=io.BytesIO(data), mode="r:*") as tar:
                for member in tar.getmembers()[:50]:
                    if member.isfile() and member.size < 5 * 1024 * 1024:
                        try:
                            f = tar.extractfile(member)
                            if f:
                                content = f.read()
                                inner_text, _ = cls._parse_universal_fallback(content)
                                parts.append(f"=== File: {member.name} ({member.size} bytes) ===\n{inner_text[:10000]}")
                                file_count += 1
                        except Exception:
                            pass
        return "\n\n".join(parts), file_count

    @classmethod
    def _parse_image_metadata(cls, data: bytes, ext: str) -> str:
        if ext == ".svg":
            return cls._parse_html(data)

        parts = [f"Image Format: {ext.upper()}"]
        try:
            im = Image.open(io.BytesIO(data))
            parts.append(f"Resolution: {im.width}x{im.height} pixels, Mode: {im.mode}")
            exif = im.getexif()
            if exif:
                parts.append("EXIF Metadata:")
                for k, v in exif.items():
                    tag_name = ExifTags.TAGS.get(k, str(k))
                    parts.append(f"  {tag_name}: {v}")
        except Exception as e:
            parts.append(f"Image inspection: {str(e)}")
        return "\n".join(parts)

    @classmethod
    def _parse_text_multi_encoding(cls, data: bytes) -> str:
        """Tries common encodings sequentially."""
        for enc in ("utf-8", "utf-8-sig", "cp1252", "latin-1", "iso-8859-1", "shift_jis", "gb18030"):
            try:
                return data.decode(enc)
            except Exception:
                pass
        return data.decode("utf-8", errors="replace")

    @classmethod
    def _parse_universal_fallback(cls, data: bytes) -> Tuple[str, bool]:
        """
        Attempts to read as text; if binary, extracts printable ASCII/UTF-8 strings.
        """
        # Check null byte ratio
        null_count = data.count(b"\x00")
        is_binary = null_count > (len(data) * 0.05) or (b"\x7f\x45\x4c\x46" in data[:4])

        if not is_binary:
            try:
                text = cls._parse_text_multi_encoding(data)
                return text, False
            except Exception:
                pass

        # Binary string extractor (runs of 4+ printable characters)
        printable_pattern = re.compile(rb"[\x20-\x7e\t\n\r]{4,}")
        matches = printable_pattern.findall(data)
        lines = [m.decode("ascii", errors="replace") for m in matches]
        summary = f"--- Binary Stream Recovered ({len(lines)} readable string blocks extracted) ---\n"
        return summary + "\n".join(lines), True
