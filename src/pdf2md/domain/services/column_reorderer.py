"""Reorder blocks for multi-column PDF layouts."""

from __future__ import annotations

from pdf2md.domain.value_objects.value_objects import ContentBlock


class ColumnReorderer:
    """Detect two-column layouts and reorder blocks for reading order."""

    @staticmethod
    def reorder(
        blocks: list[ContentBlock],
        *,
        page_width: float,
    ) -> list[ContentBlock]:
        """Return blocks sorted for natural reading in single- or two-column pages."""
        if page_width <= 0 or len(blocks) < 4:
            return blocks

        positioned = [b for b in blocks if b.bbox and b.bbox[0] != b.bbox[2]]
        if len(positioned) < 4:
            return blocks

        centers = sorted((b.bbox[0] + b.bbox[2]) / 2.0 for b in positioned)  # type: ignore[union-attr]
        mid = len(centers) // 2
        split = (centers[mid - 1] + centers[mid]) / 2.0

        left = [b for b in positioned if ((b.bbox[0] + b.bbox[2]) / 2.0) < split]  # type: ignore[union-attr]
        right = [b for b in positioned if ((b.bbox[0] + b.bbox[2]) / 2.0) >= split]  # type: ignore[union-attr]

        min_cluster = max(2, len(positioned) // 5)
        if len(left) < min_cluster or len(right) < min_cluster:
            return ColumnReorderer._sort_by_position(blocks)

        gap = abs(
            min((b.bbox[0] + b.bbox[2]) / 2.0 for b in right)  # type: ignore[union-attr]
            - max((b.bbox[0] + b.bbox[2]) / 2.0 for b in left)  # type: ignore[union-attr]
        )
        if gap < page_width * 0.08:
            return ColumnReorderer._sort_by_position(blocks)

        ordered = (
            ColumnReorderer._sort_by_position(left)
            + ColumnReorderer._sort_by_position(right)
        )
        without_bbox = [b for b in blocks if not b.bbox or b.bbox[0] == b.bbox[2]]
        return ordered + without_bbox

    @staticmethod
    def _sort_by_position(blocks: list[ContentBlock]) -> list[ContentBlock]:
        def _key(block: ContentBlock) -> tuple[float, float]:
            if block.bbox:
                return (block.bbox[1], block.bbox[0])
            return (0.0, 0.0)

        return sorted(blocks, key=_key)


__all__ = ["ColumnReorderer"]
