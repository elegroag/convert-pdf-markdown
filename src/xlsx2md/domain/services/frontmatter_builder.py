"""FrontmatterBuilder — produces YAML frontmatter from XlsxMetadata."""

from __future__ import annotations

from xlsx2md.domain.entities.entities import XlsxMetadata


class FrontmatterBuilder:
    """Build YAML frontmatter from workbook metadata."""

    @staticmethod
    def build(metadata: XlsxMetadata, *, sheet_name: str = "", sheet_index: int | None = None) -> str:
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
        if sheet_name:
            fields["sheet"] = sheet_name
        if sheet_index is not None:
            fields["sheet_index"] = str(sheet_index + 1)
            fields["sheet_total"] = str(len(metadata.sheet_names))
        if not fields:
            return ""
        lines = ["---"]
        for key, value in fields.items():
            safe = value.replace('"', '\\"')
            lines.append(f'{key}: "{safe}"')
        lines.append("---")
        return "\n".join(lines)


__all__ = ["FrontmatterBuilder"]
