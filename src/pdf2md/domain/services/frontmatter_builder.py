"""FrontmatterBuilder — produces the YAML frontmatter block.

Pure-domain: takes a :class:`PdfMetadata` and a page count, returns
the YAML string. The renderer wraps the result between ``---\\n``
fences only when the result is non-empty.

v0.2.0 hardening:

- Values that contain YAML-unsafe characters (``:``, ``#``, ``&``,
  ``*``, ``?``, ``|``, ``>``, ``!``, ``%``, ``@``, leading ``-``,
  leading digit, embedded ``'`` or control chars) are emitted as
  literal block scalars (``|``) instead of double-quoted strings.
- PDF creation dates in the ``D:YYYYMMDDHHMMSS±HH'MM'`` format are
  normalised to ISO 8601 (``YYYY-MM-DDTHH:MM:SS±HH:MM``).
- Unparseable dates are preserved verbatim in a block scalar.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone

from pdf2md.domain.entities.entities import PdfMetadata

# Characters that, when present unescaped inside a double-quoted YAML
# scalar, either change its semantics (colons, hashes, indicators) or
# are hard to escape safely (control chars). Embedded double quotes
# are fine when escaped with a backslash. The list is conservative —
# when in doubt, emit a block scalar.
_UNSAFE_CHARS_RE = re.compile(r"[:#&*?|>%@!`'’”]|[\]\[}{]")
_LEADING_DASH_OR_DIGIT_RE = re.compile(r"^[\s]*[-\d]")
_CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")

# PDF date format: D:YYYYMMDDHHMMSS±HH'MM'
_PDF_DATE_RE = re.compile(
    r"^D:(\d{4})(\d{2})(\d{2})"
    r"(\d{2})?(\d{2})?(\d{2})?"
    r"([+\-]\d{2})'?(\d{2})?'?$"
)


def _normalise_pdf_date(value: str) -> str | None:
    """Convert a PDF date to ISO 8601, or return ``None`` if unparseable."""
    m = _PDF_DATE_RE.match(value.strip())
    if not m:
        return None
    year, month, day, hour, minute, second, tz_h, tz_m = m.groups()
    hour = hour or "00"
    minute = minute or "00"
    second = second or "00"
    try:
        dt = datetime(
            int(year),
            int(month),
            int(day),
            int(hour),
            int(minute),
            int(second),
            tzinfo=timezone.utc,
        )
    except ValueError:
        return None
    iso = dt.strftime("%Y-%m-%dT%H:%M:%S")
    sign = tz_h[0]
    tz_h_abs = tz_h[1:].lstrip("0") or "0"
    return f"{iso}{sign}{int(tz_h_abs):02d}:{tz_m}"


def _needs_block_scalar(value: str) -> bool:
    """Return True if ``value`` is unsafe for a quoted YAML scalar."""
    if not value.strip():
        return False
    if _LEADING_DASH_OR_DIGIT_RE.match(value):
        return True
    if _UNSAFE_CHARS_RE.search(value):
        return True
    if _CONTROL_CHARS_RE.search(value):
        return True
    return False


class FrontmatterBuilder:
    """Stateless namespace for building YAML frontmatter."""

    @staticmethod
    def _escape_double_quoted(value: str) -> str:
        """Escape for a double-quoted YAML scalar (safe for plain text)."""
        return (
            value.replace("\\", "\\\\")
            .replace('"', '\\"')
            .replace("\n", "\\n")
            .replace("\t", "\\t")
        )

    @classmethod
    def _emit_value(cls, value: str) -> str:
        """Format ``value`` as a YAML scalar."""
        if _needs_block_scalar(value):
            # Literal block scalar. Indent each line by 2 spaces.
            escaped = value.replace("\r\n", "\n").replace("\r", "\n")
            lines = escaped.split("\n")
            body = "\n".join(f"  {line}" for line in lines)
            return f"|\n{body}"
        return f'"{cls._escape_double_quoted(value)}"'

    @classmethod
    def build(cls, metadata: PdfMetadata, *, page_count: int) -> str:
        """Return the YAML frontmatter for ``metadata`` + ``page_count``.

        Returns an empty string when ``metadata`` carries no meaningful
        data, signalling the caller that no frontmatter should be emitted.
        """
        if metadata.is_empty():
            return ""

        lines: list[str] = ["---"]
        if metadata.title:
            lines.append(f"title: {cls._emit_value(metadata.title)}")
        if metadata.author:
            lines.append(f"author: {cls._emit_value(metadata.author)}")
        if metadata.subject:
            lines.append(f"subject: {cls._emit_value(metadata.subject)}")
        if metadata.creator:
            lines.append(f"creator: {cls._emit_value(metadata.creator)}")
        if metadata.producer:
            lines.append(f"producer: {cls._emit_value(metadata.producer)}")
        if metadata.creation_date:
            iso = _normalise_pdf_date(metadata.creation_date)
            final = iso if iso is not None else metadata.creation_date
            lines.append(f"created: {cls._emit_value(final)}")
        lines.append(f"pages: {int(page_count)}")
        lines.append("---")
        return "\n".join(lines)


__all__ = ["FrontmatterBuilder"]
