import typer

from cartomancer.config import get_settings

config_app = typer.Typer(help="Inspect the effective configuration.")


@config_app.command("show")
def show() -> None:
    """Print the effective configuration (env vars + defaults)."""
    settings = get_settings()
    for field, value in settings.model_dump().items():
        typer.echo(f"{field}={value}")
