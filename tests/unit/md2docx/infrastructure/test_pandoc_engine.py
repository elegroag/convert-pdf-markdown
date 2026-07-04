"""Tests for pandoc engine."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from md2docx.domain.exceptions import PandocNotFoundError
from md2docx.infrastructure.engines.pandoc_engine import PandocEngine


class TestPandocEngine:
    def test_raises_when_pandoc_missing(self, tmp_path: Path) -> None:
        engine = PandocEngine()
        with patch(
            "md2docx.infrastructure.engines.pandoc_engine.require_pandoc",
            side_effect=PandocNotFoundError("missing"),
        ), pytest.raises(PandocNotFoundError):
            engine.convert(
                tmp_path / "in.md",
                tmp_path / "ref.docx",
                tmp_path / "out.docx",
            )

    def test_runs_subprocess(self, tmp_path: Path) -> None:
        md = tmp_path / "in.md"
        ref = tmp_path / "ref.docx"
        out = tmp_path / "out.docx"
        md.write_text("# Test", encoding="utf-8")
        ref.write_bytes(b"PK")
        out.write_bytes(b"PK")

        engine = PandocEngine()
        with patch(
            "md2docx.infrastructure.engines.pandoc_engine.require_pandoc",
            return_value="/usr/bin/pandoc",
        ), patch("md2docx.infrastructure.engines.pandoc_engine.subprocess.run") as run:
            run.return_value = MagicMock(returncode=0)
            result = engine.convert(md, ref, out)
        assert result == out
        run.assert_called_once()
