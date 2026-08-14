from cartomancer.ingest.txt_parser import parse_txt


def test_parse_txt_skips_blank_and_comment_lines(tmp_path, settings):
    path = tmp_path / "prompts.txt"
    path.write_text("a cozy tavern\n\n# a comment\nan ancient ruin\n")

    entries = parse_txt(path, settings)

    assert [e.prompt for e in entries] == ["a cozy tavern", "an ancient ruin"]
    assert entries[0].tags == []
    assert entries[0].width == settings.default_width
    assert entries[0].name is None
