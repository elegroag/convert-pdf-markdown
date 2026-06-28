"""AnchorSlug — GitHub-style slug generator for filenames."""

from __future__ import annotations

import re
import unicodedata

_SLUG_RE = re.compile(r"[^a-z0-9._-]+")
_SEP_RE = re.compile(r"-+")


class AnchorSlug:
    """Stateless namespace for slug utilities."""

    @staticmethod
    def slugify(text: str) -> str:
        """Convert text into a lowercase, ASCII-only, hyphen-separated slug."""
        normalized = unicodedata.normalize("NFKD", text)
        ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
        lowered = ascii_only.lower().strip()
        slug = _SLUG_RE.sub("-", lowered)
        slug = _SEP_RE.sub("-", slug).strip("-")
        return slug or "document"


__all__ = ["AnchorSlug"]
