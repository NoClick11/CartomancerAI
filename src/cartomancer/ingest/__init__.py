from pathlib import Path

from cartomancer.config import Settings
from cartomancer.models import PromptEntry

from .txt_parser import parse_txt
from .yaml_parser import parse_yaml

__all__ = ["parse_file", "parse_txt", "parse_yaml"]


def parse_file(path: Path, settings: Settings) -> list[PromptEntry]:
    suffix = path.suffix.lower()
    if suffix in (".yaml", ".yml"):
        return parse_yaml(path, settings)
    if suffix == ".txt":
        return parse_txt(path, settings)
    raise ValueError(f"unsupported prompt file extension: {suffix!r} (expected .yaml/.yml/.txt)")
