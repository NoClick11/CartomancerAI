from pathlib import Path

import pytest

from cartomancer.config import Settings


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        db_path=tmp_path / "db" / "cartomancer.sqlite3",
        output_dir=tmp_path / "output",
    )
