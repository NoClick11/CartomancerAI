import typer

from cartomancer.config import get_settings
from cartomancer.db.connection import connect, migrate

db_app = typer.Typer(help="Manage the SQLite schema.")


@db_app.command("upgrade")
def upgrade() -> None:
    """Apply any pending schema migrations."""
    settings = get_settings()
    conn = connect(settings.db_path)
    applied = migrate(conn)
    typer.echo(f"applied {applied} migration(s)")
