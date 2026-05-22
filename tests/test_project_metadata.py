from pathlib import Path

from neobank_product_analytics import __version__


def test_project_version_is_defined() -> None:
    assert __version__ == "0.1.0"


def test_informal_summary_label_is_not_present() -> None:
    root = Path(__file__).resolve().parents[1]
    checked_paths = [
        *root.glob("docs/**/*.md"),
        *root.glob("src/**/*.py"),
        *root.glob("app/**/*.py"),
    ]

    matches = []
    informal_labels = ["tl" + ";dr", "td" + "lr"]
    for path in checked_paths:
        text = path.read_text(encoding="utf-8").lower()
        if any(label in text for label in informal_labels):
            matches.append(str(path.relative_to(root)))

    assert matches == []
