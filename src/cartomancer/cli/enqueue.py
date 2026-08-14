from pathlib import Path

import typer
from rich.console import Console
from rich.text import Text

from cartomancer.config import get_settings
from cartomancer.db import jobs_repo
from cartomancer.db.connection import connect_and_migrate
from cartomancer.ingest import parse_file

console = Console()


def enqueue_command(
    file: Path = typer.Argument(
        ..., exists=True, readable=True, help="A .yaml/.yml or .txt file of map prompts."
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Parse and show what would be queued, without writing to the database.",
    ),
    allow_duplicates: bool = typer.Option(
        False,
        "--allow-duplicates",
        help="Queue entries even if the same source file/id was already queued before.",
    ),
) -> None:
    """Parse a prompts file and add its entries to the queue."""
    settings = get_settings()
    entries = parse_file(file, settings)

    if not entries:
        console.print("[yellow]No prompt entries found in file.[/yellow]")
        raise typer.Exit(code=0)

    if dry_run:
        header = Text(f"{len(entries)} entry(ies) would be queued from ", style="bold")
        header.append(str(file), style="bold")
        header.append(":", style="bold")
        console.print(header)
        for entry in entries:
            label = entry.name or entry.prompt[:60]
            # markup=False: source_key/prompt text is arbitrary user input and may
            # itself contain '[' / ']', which Rich would otherwise try to parse as tags.
            console.print(f"  - [{entry.source_key}] {label!r} tags={entry.tags}", markup=False)
        raise typer.Exit(code=0)

    conn = connect_and_migrate(settings.db_path)
    queued, skipped = 0, 0
    for entry in entries:
        label = entry.name or entry.prompt[:60]
        try:
            job = jobs_repo.create_job(conn, entry, str(file), allow_duplicates=allow_duplicates)
            line = Text("  ")
            line.append("queued", style="green")
            line.append(f" #{job.id} [{entry.source_key}] {label!r}")
            console.print(line)
            queued += 1
        except jobs_repo.DuplicateJobError:
            line = Text("  ")
            line.append("skipped (already queued)", style="dim")
            line.append(f" [{entry.source_key}]")
            console.print(line)
            skipped += 1

    summary = Text(f"{queued} queued, {skipped} skipped", style="bold")
    summary.append(f" from {file}")
    console.print(summary)
