import pytest

from cartomancer.ingest.yaml_parser import parse_yaml

YAML_CONTENT = """
defaults:
  width: 1536
  height: 1024
  tags: [example]

maps:
  - id: map-1
    name: "Test Map"
    prompt: "a test prompt"
    tags: [custom]
  - prompt: "a prompt without id or name"
"""


def test_parse_yaml_merges_defaults(tmp_path, settings):
    path = tmp_path / "maps.yaml"
    path.write_text(YAML_CONTENT)

    entries = parse_yaml(path, settings)

    assert len(entries) == 2
    assert entries[0].source_key == "map-1"
    assert entries[0].width == 1536
    assert entries[0].height == 1024
    assert entries[0].tags == ["custom"]
    assert entries[0].guidance == settings.default_guidance

    # entry without id/name gets an auto-generated slug and inherits file-level tags
    assert entries[1].source_key
    assert entries[1].tags == ["example"]


def test_parse_yaml_missing_prompt_raises(tmp_path, settings):
    path = tmp_path / "bad.yaml"
    path.write_text("maps:\n  - name: no prompt here\n")
    with pytest.raises(ValueError):
        parse_yaml(path, settings)


def test_parse_yaml_empty_file(tmp_path, settings):
    path = tmp_path / "empty.yaml"
    path.write_text("")
    assert parse_yaml(path, settings) == []
