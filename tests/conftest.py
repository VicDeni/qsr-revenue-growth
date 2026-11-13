import shutil
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
LANDING = REPO / "data" / "landing"


@pytest.fixture
def landing(tmp_path: Path) -> Path:
    """A tiny landing zone: two order files (5 rows each) plus the reference files."""
    root = tmp_path / "landing"
    (root / "orders").mkdir(parents=True)
    for month in ("2024-01", "2024-02"):
        lines = (LANDING / "orders" / f"orders_{month}.csv").read_text().splitlines()[:6]
        (root / "orders" / f"orders_{month}.csv").write_text("\n".join(lines) + "\n")
    shutil.copytree(LANDING / "reference", root / "reference")
    return root
