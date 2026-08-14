from typer.testing import CliRunner

from cartomancer.cli import app

runner = CliRunner()


def _set_env(monkeypatch, tmp_path):
    monkeypatch.setenv("CARTOMANCER_DB_PATH", str(tmp_path / "db.sqlite3"))
    monkeypatch.setenv("CARTOMANCER_OUTPUT_DIR", str(tmp_path / "output"))


def test_enqueue_dry_run_does_not_touch_db(tmp_path, monkeypatch):
    _set_env(monkeypatch, tmp_path)
    prompts_file = tmp_path / "prompts.txt"
    prompts_file.write_text("a cozy tavern\nan ancient ruin\n")

    result = runner.invoke(app, ["enqueue", str(prompts_file), "--dry-run"])

    assert result.exit_code == 0
    assert "2 entry(ies)" in result.stdout
    assert not (tmp_path / "db.sqlite3").exists()


def test_enqueue_then_status_shows_job(tmp_path, monkeypatch):
    _set_env(monkeypatch, tmp_path)
    prompts_file = tmp_path / "prompts.txt"
    prompts_file.write_text("a cozy tavern\n")

    enqueue_result = runner.invoke(app, ["enqueue", str(prompts_file)])
    assert enqueue_result.exit_code == 0
    assert "1 queued, 0 skipped" in enqueue_result.stdout

    status_result = runner.invoke(app, ["status"])
    assert status_result.exit_code == 0
    assert "cozy tavern" in status_result.stdout


def test_enqueue_twice_skips_duplicates(tmp_path, monkeypatch):
    _set_env(monkeypatch, tmp_path)
    prompts_file = tmp_path / "prompts.txt"
    prompts_file.write_text("a cozy tavern\n")

    runner.invoke(app, ["enqueue", str(prompts_file)])
    second = runner.invoke(app, ["enqueue", str(prompts_file)])

    assert "0 queued, 1 skipped" in second.stdout
