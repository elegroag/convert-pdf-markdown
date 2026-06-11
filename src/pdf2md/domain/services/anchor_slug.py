"""AnchorSlug — GitHub-style slug generator for headings and filenames.

The slug is used in two places:
- as the Markdown anchor for a heading (``#introduccion``)
- as the filesystem name for a document / image asset

Both consumers want the same rule set so that a heading's anchor
matches the filename slug derived from its text.
"""

from __future__ import annotations

import re
import unicodedata

_SLUG_RE = re.compile(r"[^a-z0-9._-]+")
_SEP_RE = re.compile(r"-+")


class AnchorSlug:
    """Stateless namespace for slug utilities."""

    @staticmethod
    def slugify(text: str) -> str:
        """Convert ``text`` into a lowercase, ASCII-only, hyphen-separated slug.

        Rules:
            - Strip combining diacritics (``Capítulo`` → ``Capitulo``).
            - Replace runs of non-alphanumeric chars with a single hyphen.
            - Strip leading and trailing hyphens.
            - Fall back to ``"document"`` for empty / punctuation-only inputs.
        """
        normalized = unicodedata.normalize("NFKD", text)
        ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
        lowered = ascii_only.lower().strip()
        slug = _SLUG_RE.sub("-", lowered)
        slug = _SEP_RE.sub("-", slug).strip("-")
        return slug or "document"

    @staticmethod
    def unique_slug(text: str, used: set[str]) -> str:
        """Return a slug derived from ``text`` that is not yet in ``used``.

        Duplicates are suffixed with ``-1``, ``-2``, … until a free
        name is found. The ``used`` set is not mutated.
        """
        base = AnchorSlug.slugify(text)
        if base not in used:
            return base
        index = 1
        while f"{base}-{index}" in used:
            index += 1
        return f"{base}-{index}"


__all__ = ["AnchorSlug"]
