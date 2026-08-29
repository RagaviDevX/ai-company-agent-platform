from backend.tools.python_exec import safe_calculate


def test_safe_calculate():
    assert safe_calculate("2 + 3 * 4") == "14"


def test_rejects_names():
    try:
        safe_calculate("__import__('os').system('echo hi')")
        assert False, "should have raised"
    except (ValueError, SyntaxError, TypeError):
        pass
