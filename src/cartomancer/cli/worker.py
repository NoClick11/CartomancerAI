import typer

from cartomancer.config import get_settings
from cartomancer.db import jobs_repo
from cartomancer.db.connection import connect_and_migrate
from cartomancer.utils.logging import setup_logging
from cartomancer.worker.runner import run_worker

worker_app = typer.Typer(help="Run and manage the generation worker.")


@worker_app.command("start")
def start(
    poll_interval: float | None = typer.Option(
        None, "--poll-interval", help="Seconds between queue polls (default: from config)."
    ),
    once: bool = typer.Option(False, "--once", help="Process a single pending job and exit."),
    max_jobs: int | None = typer.Option(
        None, "--max-jobs", help="Stop after processing this many jobs."
    ),
) -> None:
    """Start the worker loop (this is the default command run inside the container)."""
    setup_logging()
    settings = get_settings()
    run_worker(settings, poll_interval=poll_interval, once=once, max_jobs=max_jobs)


@worker_app.command("recover")
def recover() -> None:
    """Reset jobs stuck in 'running' (e.g. after a crash) back to 'pending'."""
    settings = get_settings()
    conn = connect_and_migrate(settings.db_path)
    count = jobs_repo.recover_stuck(conn)
    typer.echo(f"recovered {count} job(s)")
