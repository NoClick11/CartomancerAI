import typer

from cartomancer.__about__ import __version__
from cartomancer.config import get_settings

from .config import config_app
from .db import db_app
from .doctor import doctor_command
from .enqueue import enqueue_command
from .init import init_command
from .status import (
    cancel_command,
    list_tags_command,
    retry_command,
    show_command,
    status_command,
)
from .worker import worker_app

app = typer.Typer(
    name="cartomancer",
    help="Queue RPG map descriptions and generate them locally via ComfyUI + Flux.1 dev GGUF.",
    no_args_is_help=True,
)

app.add_typer(worker_app, name="worker")
app.add_typer(db_app, name="db")
app.add_typer(config_app, name="config")

app.command("init")(init_command)
app.command("enqueue")(enqueue_command)
app.command("status")(status_command)
app.command("show")(show_command)
app.command("retry")(retry_command)
app.command("cancel")(cancel_command)
app.command("list-tags")(list_tags_command)
app.command("doctor")(doctor_command)


@app.command("version")
def version() -> None:
    """Print the Cartomancer version (and the connected ComfyUI's, if reachable)."""
    typer.echo(f"cartomancer {__version__}")
    settings = get_settings()
    try:
        from cartomancer.comfyui.client import ComfyUIClient

        stats = ComfyUIClient(settings.comfyui_url, timeout=5.0).system_stats()
        comfy_version = (stats or {}).get("system", {}).get("comfyui_version")
        if comfy_version:
            typer.echo(f"comfyui {comfy_version} (at {settings.comfyui_url})")
    except Exception:
        pass


if __name__ == "__main__":
    app()
