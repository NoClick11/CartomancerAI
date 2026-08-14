import json
import sqlite3
import uuid
from collections.abc import Iterable

from cartomancer.models import Job, JobStatus, PromptEntry


class DuplicateJobError(Exception):
    """Raised when a job with the same (source_file, source_key) already exists."""


def _row_to_job(row: sqlite3.Row) -> Job:
    data = dict(row)
    data["tags"] = json.loads(data["tags"])
    return Job(**data)


def create_job(
    conn: sqlite3.Connection,
    entry: PromptEntry,
    source_file: str | None,
    *,
    allow_duplicates: bool = False,
) -> Job:
    """Insert a new pending job from a resolved PromptEntry.

    When `allow_duplicates` is True, the (source_file, source_key) uniqueness
    check is bypassed by storing a NULL source_key (SQLite never treats two
    NULLs as equal under a UNIQUE constraint), so the same map can be queued
    again deliberately (e.g. to try a different seed).
    """
    uid = uuid.uuid4().hex
    source_key = None if allow_duplicates else entry.source_key
    try:
        cur = conn.execute(
            """
            INSERT INTO jobs (
                uid, source_file, source_key, name, prompt, negative_prompt,
                tags, notes, width, height, steps, cfg, guidance, sampler,
                scheduler, seed, quantization, unet_filename
            ) VALUES (
                :uid, :source_file, :source_key, :name, :prompt, :negative_prompt,
                :tags, :notes, :width, :height, :steps, :cfg, :guidance, :sampler,
                :scheduler, :seed, :quantization, :unet_filename
            )
            RETURNING *
            """,
            {
                "uid": uid,
                "source_file": source_file,
                "source_key": source_key,
                "name": entry.name,
                "prompt": entry.prompt,
                "negative_prompt": entry.negative_prompt,
                "tags": json.dumps(entry.tags),
                "notes": entry.notes,
                "width": entry.width,
                "height": entry.height,
                "steps": entry.steps,
                "cfg": entry.cfg,
                "guidance": entry.guidance,
                "sampler": entry.sampler,
                "scheduler": entry.scheduler,
                "seed": entry.seed,
                "quantization": entry.quantization,
                "unet_filename": entry.unet_filename,
            },
        )
        row = cur.fetchone()
        conn.commit()
        return _row_to_job(row)
    except sqlite3.IntegrityError as exc:
        conn.rollback()
        raise DuplicateJobError(
            f"a job for source_file={source_file!r} source_key={entry.source_key!r} "
            "already exists"
        ) from exc


def claim_next_pending(conn: sqlite3.Connection) -> Job | None:
    """Atomically move the oldest pending job to 'running' and return it."""
    cur = conn.execute(
        """
        UPDATE jobs
        SET status = 'running', started_at = strftime('%Y-%m-%dT%H:%M:%fZ','now'),
            updated_at = strftime('%Y-%m-%dT%H:%M:%fZ','now')
        WHERE id = (
            SELECT id FROM jobs WHERE status = 'pending' ORDER BY created_at LIMIT 1
        )
        AND status = 'pending'
        RETURNING *
        """
    )
    row = cur.fetchone()
    conn.commit()
    return _row_to_job(row) if row else None


def set_seed(conn: sqlite3.Connection, job_id: int, seed: int) -> None:
    """Persist the actual seed used for a job (resolved from None at submit time)."""
    conn.execute(
        "UPDATE jobs SET seed = ?, updated_at = strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE id = ?",
        (seed, job_id),
    )
    conn.commit()


def set_comfyui_ids(conn: sqlite3.Connection, job_id: int, prompt_id: str, client_id: str) -> None:
    conn.execute(
        """
        UPDATE jobs
        SET comfyui_prompt_id = ?, comfyui_client_id = ?,
            updated_at = strftime('%Y-%m-%dT%H:%M:%fZ','now')
        WHERE id = ?
        """,
        (prompt_id, client_id, job_id),
    )
    conn.commit()


def mark_done(
    conn: sqlite3.Connection, job_id: int, output_path: str, output_filename: str
) -> None:
    conn.execute(
        """
        UPDATE jobs
        SET status = 'done', output_path = ?, output_filename = ?,
            finished_at = strftime('%Y-%m-%dT%H:%M:%fZ','now'),
            updated_at = strftime('%Y-%m-%dT%H:%M:%fZ','now')
        WHERE id = ?
        """,
        (output_path, output_filename, job_id),
    )
    conn.commit()


def mark_failed(conn: sqlite3.Connection, job_id: int, error_message: str) -> None:
    conn.execute(
        """
        UPDATE jobs
        SET status = 'failed', error_message = ?,
            finished_at = strftime('%Y-%m-%dT%H:%M:%fZ','now'),
            updated_at = strftime('%Y-%m-%dT%H:%M:%fZ','now')
        WHERE id = ?
        """,
        (error_message, job_id),
    )
    conn.commit()


def cancel_pending(conn: sqlite3.Connection, job_id: int) -> bool:
    """Cancel a job if it's still pending. Returns False if it wasn't (e.g. already running)."""
    cur = conn.execute(
        """
        UPDATE jobs
        SET status = 'cancelled', updated_at = strftime('%Y-%m-%dT%H:%M:%fZ','now')
        WHERE id = ? AND status = 'pending'
        """,
        (job_id,),
    )
    conn.commit()
    return cur.rowcount > 0


def requeue(conn: sqlite3.Connection, job_id: int) -> bool:
    """Move a failed job back to pending, incrementing retry_count. Returns False if not failed."""
    cur = conn.execute(
        """
        UPDATE jobs
        SET status = 'pending', retry_count = retry_count + 1,
            error_message = NULL, comfyui_prompt_id = NULL, comfyui_client_id = NULL,
            started_at = NULL, finished_at = NULL,
            updated_at = strftime('%Y-%m-%dT%H:%M:%fZ','now')
        WHERE id = ? AND status = 'failed'
        """,
        (job_id,),
    )
    conn.commit()
    return cur.rowcount > 0


def recover_stuck(conn: sqlite3.Connection) -> int:
    """Reset jobs left in 'running' by a previous crash back to 'pending'."""
    cur = conn.execute(
        """
        UPDATE jobs
        SET status = 'pending', started_at = NULL,
            updated_at = strftime('%Y-%m-%dT%H:%M:%fZ','now')
        WHERE status = 'running'
        """
    )
    conn.commit()
    return cur.rowcount


def get_job(conn: sqlite3.Connection, id_or_uid: str) -> Job | None:
    if id_or_uid.isdigit():
        row = conn.execute("SELECT * FROM jobs WHERE id = ?", (int(id_or_uid),)).fetchone()
    else:
        row = conn.execute("SELECT * FROM jobs WHERE uid = ?", (id_or_uid,)).fetchone()
    return _row_to_job(row) if row else None


def list_jobs(
    conn: sqlite3.Connection,
    *,
    status: JobStatus | None = None,
    tag: str | None = None,
) -> list[Job]:
    query = "SELECT * FROM jobs"
    clauses: list[str] = []
    params: list[str] = []
    if status is not None:
        clauses.append("status = ?")
        params.append(status.value)
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY created_at DESC"
    rows = conn.execute(query, params).fetchall()
    jobs = [_row_to_job(r) for r in rows]
    if tag is not None:
        jobs = [j for j in jobs if tag in j.tags]
    return jobs


def list_tags(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute("SELECT tags FROM jobs").fetchall()
    tags: set[str] = set()
    for row in rows:
        tags.update(json.loads(row["tags"]))
    return sorted(tags)


def all_source_keys(conn: sqlite3.Connection, source_file: str) -> Iterable[str]:
    rows = conn.execute(
        "SELECT source_key FROM jobs WHERE source_file = ? AND source_key IS NOT NULL",
        (source_file,),
    ).fetchall()
    return {r["source_key"] for r in rows}
