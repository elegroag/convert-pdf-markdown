"""FrontmatterBuilder — produces YAML frontmatter from DocxMetadata."""

from __future__ import annotations

from docx2md.domain.entities.entities import DocxMetadata


class FrontmatterBuilder:
    """Build YAML frontmatter from document metadata."""

    @staticmethod
    def build(metadata: DocxMetadata) -> str:
        """Return a YAML frontmatter block or empty string when no data."""
        fields: dict[str, str] = {}
        if metadata.title:
            fields["title"] = metadata.title
        if metadata.author:
            fields["author"] = metadata.author
        if metadata.subject:
            fields["subject"] = metadata.subject
        if metadata.creator:
            fields["creator"] = metadata.creator
        if not fields:
            return ""
        lines = ["---"]
        for key, value in fields.items():
            safe = value.replace('"', '\\"')
            lines.append(f'{key}: "{safe}"')
        lines.append("---")
        return "\n".join(lines)


__all__ = ["FrontmatterBuilder"]
