import time

import typer
from rich.console import Console
from rich.table import Table
from rich.text import Text

from cartomancer.config import get_settings
from cartomancer.db import jobs_repo
from cartomancer.db.connection import connect_and_migrate
from cartomancer.models import JobStatus

console = Console()


def _render_table(status: JobStatus | None, tag: str | None) -> int:
    settings = get_settings()
    conn = connect_and_migrate(settings.db_path)
    jobs = jobs_repo.list_jobs(conn, status=status, tag=tag)

    table = Table()
    table.add_column("id")
    table.add_column("status")
    table.add_column("name/prompt")
    table.add_column("tags")
    table.add_column("created_at")
    for job in jobs:
        # Text(...) rather than raw strings: job name/prompt/tags are arbitrary user
        # input and may contain '[' / ']', which Rich table cells would otherwise
        # try to parse as markup tags.
        table.add_row(
            str(job.id),
            job.status.value,
            Text(job.name or job.prompt[:50]),
            Text(", ".join(job.tags)),
            job.created_at,
        )
    console.print(table)
    console.print(f"{len(jobs)} job(s)")
    return len(jobs)


def status_command(
    status: JobStatus | None = typer.Option(None, "--status", help="Filter by status."),
    tag: str | None = typer.Option(None, "--tag", help="Filter by tag."),
    watch: bool = typer.Option(
        False, "--watch", help="Refresh the table every 3 seconds until interrupted."
    ),
) -> None:
    """List queued/running/finished jobs."""
    if not watch:
        _render_table(status, tag)
        return

    try:
        while True:
            console.clear()
            _render_table(status, tag)
            time.sleep(3)
    except KeyboardInterrupt:
        pass


def show_command(id: str = typer.Argument(..., help="Job id or uid.")) -> None:
    """Show full detail of a single job."""
    settings = get_settings()
    conn = connect_and_migrate(settings.db_path)
    job = jobs_repo.get_job(conn, id)
    if job is None:
        console.print(Text(f"no job found for {id!r}", style="red"))
        raise typer.Exit(code=1)
    for field, value in job.model_dump().items():
        line = Text(f"{field}", style="bold")
        line.append(f": {value}")
        console.print(line)


def retry_command(
    id: str | None = typer.Argument(None, help="Job id to retry."),
    all_failed: bool = typer.Option(False, "--all-failed", help="Retry every failed job."),
) -> None:
    """Re-queue a failed job (or every failed job with --all-failed)."""
    settings = get_settings()
    conn = connect_and_migrate(settings.db_path)

    if all_failed:
        jobs = jobs_repo.list_jobs(conn, status=JobStatus.FAILED)
        for job in jobs:
            jobs_repo.requeue(conn, job.id)
        console.print(f"requeued {len(jobs)} failed job(s)")
        return

    if id is None:
        console.print(Text("provide a job id, or use --all-failed", style="red"))
        raise typer.Exit(code=1)
    job = jobs_repo.get_job(conn, id)
    if job is None:
        console.print(Text(f"no job found for {id!r}", style="red"))
        raise typer.Exit(code=1)
    if not jobs_repo.requeue(conn, job.id):
        console.print(
            Text(
                f"job {job.id} is not in a failed state (status={job.status.value})",
                style="red",
            )
        )
        raise typer.Exit(code=1)
    console.print(f"requeued job {job.id}")


def cancel_command(id: str = typer.Argument(..., help="Job id to cancel.")) -> None:
    """Cancel a job that's still pending."""
    settings = get_settings()
    conn = connect_and_migrate(settings.db_path)
    job = jobs_repo.get_job(conn, id)
    if job is None:
        console.print(Text(f"no job found for {id!r}", style="red"))
        raise typer.Exit(code=1)
    if not jobs_repo.cancel_pending(conn, job.id):
        console.print(
            Text(
                f"job {job.id} is not pending (status={job.status.value}); "
                "cancelling a running job isn't supported yet",
                style="red",
            )
        )
        raise typer.Exit(code=1)
    console.print(f"cancelled job {job.id}")


def list_tags_command() -> None:
    """List distinct tags in use across all jobs."""
    settings = get_settings()
    conn = connect_and_migrate(settings.db_path)
    tags = jobs_repo.list_tags(conn)
    if not tags:
        console.print(Text("no tags yet", style="dim"))
        return
    for tag in tags:
        console.print(Text(tag))
