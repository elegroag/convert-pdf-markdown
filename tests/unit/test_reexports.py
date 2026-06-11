"""Smoke tests covering the re-exports in package ``__init__`` modules.

These exist purely so that the lines `from .x import y` count as
covered by the coverage report.
"""

from __future__ import annotations


def test_domain_root_reexports() -> None:
    from pdf2md import domain

    assert hasattr(domain, "entities")
    assert hasattr(domain, "value_objects")
    assert hasattr(domain, "ports")
    assert hasattr(domain, "use_cases")
    assert hasattr(domain, "exceptions")
    assert hasattr(domain, "services")


def test_application_root_reexports() -> None:
    from pdf2md import application

    assert hasattr(application, "dto")
    assert hasattr(application, "services")


def test_infrastructure_root_reexports() -> None:
    from pdf2md import infrastructure

    assert hasattr(infrastructure, "extractors")
    assert hasattr(infrastructure, "renderers")
    assert hasattr(infrastructure, "storage")


def test_interface_api_reexports() -> None:
    import pytest

    try:
        from pdf2md.interface import api
    except ImportError:
        pytest.skip("fastapi is not installed")
    assert hasattr(api, "app")


def test_interface_root_exports_version() -> None:
    import pdf2md

    assert hasattr(pdf2md, "__version__")
    assert isinstance(pdf2md.__version__, str)
