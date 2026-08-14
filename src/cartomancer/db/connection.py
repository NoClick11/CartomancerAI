import sqlite3
from pathlib import Path

MIGRATIONS_DIR = Path(__file__).parent / "migrations"


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn


def _migration_files() -> list[Path]:
    return sorted(MIGRATIONS_DIR.glob("*.sql"), key=lambda p: int(p.name.split("_", 1)[0]))


def current_version(conn: sqlite3.Connection) -> int:
    return conn.execute("PRAGMA user_version").fetchone()[0]


def pending_migrations(conn: sqlite3.Connection) -> list[Path]:
    version = current_version(conn)
    return [p for p in _migration_files() if int(p.name.split("_", 1)[0]) > version]


def migrate(conn: sqlite3.Connection) -> int:
    """Apply any pending migrations in order. Returns the number applied."""
    applied = 0
    for path in pending_migrations(conn):
        version = int(path.name.split("_", 1)[0])
        conn.executescript(path.read_text())
        conn.execute("INSERT INTO schema_migrations (version) VALUES (?)", (version,))
        conn.execute(f"PRAGMA user_version = {version}")
        conn.commit()
        applied += 1
    return applied


def connect_and_migrate(db_path: Path) -> sqlite3.Connection:
    conn = connect(db_path)
    migrate(conn)
    return conn
