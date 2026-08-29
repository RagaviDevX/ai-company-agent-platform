from pathlib import Path


def test_planner_prompt_exists():
    root = Path(__file__).resolve().parents[1]
    text = (root / "backend" / "prompts" / "planner_prompt.txt").read_text(encoding="utf-8")
    assert "CEO Planner" in text
