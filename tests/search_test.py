from backend.tools.search import format_search


def test_format_search_empty():
    assert "No search" in format_search([])
