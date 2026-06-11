"""
Generic multi-format document text extractor.
=============================================

Turns a heterogeneous claim folder (txt / csv / xlsx / docx / images) into a
single plain-text block suitable for pasting into an LLM agent prompt.

Used by the insurance-claims test runner (Option 1: "realistic packet,
text-extracted") and intentionally written to be FORMAT-GENERIC and dependency-
light so the future Option-2 true-file-ingestion path can reuse the same
dispatcher.

Public API:
    extract_text(path) -> str
    extract_folder(folder, recursive=True) -> str

No new third-party dependencies: openpyxl and python-docx are already used by
the workflow test-data tooling; Pillow ships with the backend image stack.
"""

from __future__ import annotations

from pathlib import Path

# Suffixes handled natively. Anything else falls back to a best-effort raw read.
_PLAIN = {".txt", ".csv", ".json", ".md", ".log"}
_IMAGE = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp"}


def extract_text(path: str | Path) -> str:
    """Extract a readable text representation of a single file.

    Dispatches by file extension. Never raises on a single bad file — returns a
    short ``[UNREADABLE ...]`` marker instead so one corrupt document cannot
    sink a whole claim packet.
    """
    p = Path(path)
    suffix = p.suffix.lower()
    try:
        if suffix in _PLAIN:
            return p.read_text(encoding="utf-8").strip()
        if suffix == ".xlsx":
            return _extract_xlsx(p)
        if suffix == ".docx":
            return _extract_docx(p)
        if suffix in _IMAGE:
            return _extract_image(p)
        # Unknown type — best-effort raw read, otherwise just note it exists.
        try:
            return p.read_text(encoding="utf-8").strip()
        except Exception:
            return f"[BINARY FILE — {p.name}, {p.stat().st_size} bytes, not text-extractable]"
    except Exception as exc:  # pragma: no cover - defensive
        return f"[UNREADABLE {p.name}: {type(exc).__name__}: {exc}]"


def extract_folder(folder: str | Path, recursive: bool = True) -> str:
    """Concatenate the extracted text of every file in ``folder``.

    Each file is prefixed with a ``--- <stem> (<suffix>) ---`` banner so the
    agent can tell the documents apart. Files are visited in sorted path order
    for deterministic output.
    """
    root = Path(folder)
    if not root.exists():
        return f"[ERROR] Folder not found: {root}"

    paths = sorted(root.rglob("*") if recursive else root.iterdir())
    parts: list[str] = []
    for fpath in paths:
        if fpath.is_file():
            rel = fpath.relative_to(root)
            label = str(rel).replace("\\", "/")
            parts.append(f"\n--- {label} ({fpath.suffix.lstrip('.') or 'file'}) ---\n{extract_text(fpath)}")
    return "\n".join(parts)


# ── Format handlers ──────────────────────────────────────────────────────────


def _extract_xlsx(p: Path) -> str:
    """Render every sheet of a workbook as pipe-delimited text rows."""
    from openpyxl import load_workbook

    wb = load_workbook(p, read_only=True, data_only=True)
    blocks: list[str] = []
    for ws in wb.worksheets:
        lines = [f"[Sheet: {ws.title}]"]
        for row in ws.iter_rows(values_only=True):
            if row is None:
                continue
            cells = ["" if c is None else str(c) for c in row]
            if any(cell.strip() for cell in cells):
                lines.append(" | ".join(cells))
        blocks.append("\n".join(lines))
    wb.close()
    return "\n\n".join(blocks).strip()


def _extract_docx(p: Path) -> str:
    """Pull paragraphs and table rows from a .docx in document order."""
    import docx  # python-docx

    document = docx.Document(str(p))
    lines: list[str] = []
    for para in document.paragraphs:
        text = para.text.strip()
        if text:
            lines.append(text)
    for table in document.tables:
        for row in table.rows:
            cells = [c.text.strip() for c in row.cells]
            if any(cells):
                lines.append(" | ".join(cells))
    return "\n".join(lines).strip()


def _extract_image(p: Path) -> str:
    """Images aren't OCR'd this phase — surface their EXIF metadata instead.

    Date/GPS/device EXIF is the evidentiary payload an adjuster or fraud
    investigator actually reasons about (does the capture date match the loss?
    does GPS match the insured address?).
    """
    summary = f"[IMAGE EVIDENCE — {p.name}]"
    try:
        from PIL import Image
        from PIL.ExifTags import GPSTAGS, IFD, TAGS

        with Image.open(p) as img:
            exif = img.getexif()
            meta: list[str] = [f"dimensions={img.width}x{img.height}"]

            for tag_id, value in exif.items():
                name = TAGS.get(tag_id, str(tag_id))
                if name in ("Make", "Model", "DateTime", "ImageDescription"):
                    meta.append(f"{name}={value}")

            # Exif sub-IFD (DateTimeOriginal lives here).
            try:
                exif_ifd = exif.get_ifd(IFD.Exif)
                dto = exif_ifd.get(0x9003)  # DateTimeOriginal
                if dto:
                    meta.append(f"DateTimeOriginal={dto}")
            except Exception:
                pass

            # GPS sub-IFD → human-readable lat/lon.
            try:
                gps_ifd = exif.get_ifd(IFD.GPSInfo)
                if gps_ifd:
                    gps = {GPSTAGS.get(k, k): v for k, v in gps_ifd.items()}
                    lat = _dms_to_deg(gps.get("GPSLatitude"), gps.get("GPSLatitudeRef"))
                    lon = _dms_to_deg(gps.get("GPSLongitude"), gps.get("GPSLongitudeRef"))
                    if lat is not None and lon is not None:
                        meta.append(f"GPS={lat:.5f},{lon:.5f}")
            except Exception:
                pass

            if meta:
                summary += " " + ", ".join(meta)
    except Exception:
        pass
    return summary


def _dms_to_deg(dms, ref) -> float | None:
    """Convert EXIF (deg, min, sec) rationals + N/S/E/W ref to signed degrees."""
    if not dms or ref is None:
        return None
    try:
        d, m, s = (float(x) for x in dms)
        deg = d + m / 60.0 + s / 3600.0
        if str(ref).upper() in ("S", "W"):
            deg = -deg
        return deg
    except Exception:
        return None


if __name__ == "__main__":
    import sys

    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    if target.is_dir():
        print(extract_folder(target))
    else:
        print(extract_text(target))
