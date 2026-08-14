import json

import typer
from rich.console import Console
from rich.text import Text

from cartomancer.config import get_settings
from cartomancer.doctor.checks import run_checks, run_full_smoke_test

console = Console()


def doctor_command(
    full: bool = typer.Option(
        False, "--full", help="Also run a real end-to-end generation smoke test."
    ),
    as_json: bool = typer.Option(False, "--json", help="Print results as JSON instead of a table."),
) -> None:
    """Diagnose the ComfyUI connection, required nodes/models, and local setup."""
    settings = get_settings()
    results = run_checks(settings)
    if full:
        results.append(run_full_smoke_test(settings))

    if as_json:
        console.print_json(json.dumps([r.__dict__ for r in results]))
    else:
        for r in results:
            # r.message/r.hint can embed raw ComfyUI error text (e.g. JSON node
            # errors, full of '[' / ']'), so build with Text instead of markup
            # f-strings to avoid it being misparsed as Rich markup.
            line = Text("OK  ", style="green") if r.ok else Text("FAIL", style="red")
            line.append(f" {r.name}: {r.message}")
            console.print(line)
            if not r.ok and r.hint:
                console.print(Text(f"       hint: {r.hint}", style="dim"))

    if any(not r.ok for r in results):
        raise typer.Exit(code=1)
