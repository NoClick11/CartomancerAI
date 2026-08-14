import logging
import signal
import sqlite3
import time

from cartomancer.comfyui.client import ComfyUIClient, new_client_id
from cartomancer.comfyui.exceptions import ComfyUIError
from cartomancer.comfyui.workflow_builder import build_flux_gguf_txt2img_graph
from cartomancer.config import Settings
from cartomancer.db import jobs_repo
from cartomancer.db.connection import connect_and_migrate
from cartomancer.models import Job
from cartomancer.utils.slugify import slugify

logger = logging.getLogger("cartomancer.worker")


class _StopSignal:
    def __init__(self) -> None:
        self.requested = False

    def request_stop(self, *_args) -> None:
        if self.requested:
            logger.warning(
                "second stop signal received; still finishing the current job (kill -9 to force)"
            )
            return
        logger.info("stop requested; will exit after the current job finishes")
        self.requested = True


def run_worker(
    settings: Settings,
    *,
    poll_interval: float | None = None,
    once: bool = False,
    max_jobs: int | None = None,
) -> None:
    """Sequential worker loop: one job on the GPU at a time, forever (or until --once/--max-jobs).

    A failed job never kills the loop. SIGTERM/SIGINT don't abort a job in
    progress — 10-20 minutes of GPU time is too expensive to throw away —
    they just stop the loop from claiming a new one.
    """
    poll_interval = (
        poll_interval if poll_interval is not None else settings.worker_poll_interval_seconds
    )

    conn = connect_and_migrate(settings.db_path)
    recovered = jobs_repo.recover_stuck(conn)
    if recovered:
        logger.warning("recovered %d job(s) stuck in 'running' from a previous crash", recovered)

    stop = _StopSignal()
    signal.signal(signal.SIGTERM, stop.request_stop)
    signal.signal(signal.SIGINT, stop.request_stop)

    client = ComfyUIClient(settings.comfyui_url)
    processed = 0

    logger.info(
        "worker started, polling every %.1fs (comfyui: %s)", poll_interval, settings.comfyui_url
    )

    while not stop.requested:
        job = jobs_repo.claim_next_pending(conn)
        if job is None:
            if once:
                logger.info("no pending jobs (--once)")
                return
            time.sleep(poll_interval)
            continue

        _process_job(conn, client, job, settings)
        processed += 1

        if once or (max_jobs is not None and processed >= max_jobs):
            return

    logger.info("worker stopped")


def _process_job(
    conn: sqlite3.Connection, client: ComfyUIClient, job: Job, settings: Settings
) -> None:
    logger.info("job %s (%s): starting - %r", job.id, job.uid, job.prompt[:80])
    try:
        graph, seed = build_flux_gguf_txt2img_graph(job, settings)
        jobs_repo.set_seed(conn, job.id, seed)

        client_id = new_client_id()
        prompt_id = client.queue_prompt(graph, client_id)
        jobs_repo.set_comfyui_ids(conn, job.id, prompt_id, client_id)
        logger.info("job %s: queued on ComfyUI as prompt_id=%s", job.id, prompt_id)

        history = client.wait_for_completion(
            prompt_id, client_id, timeout=settings.worker_job_timeout_seconds
        )
        images = client.extract_images(history)
        if not images:
            raise RuntimeError(
                f"ComfyUI reported completion but produced no images for {prompt_id}"
            )

        image_bytes = client.get_image_bytes(images[0])
        settings.output_dir.mkdir(parents=True, exist_ok=True)
        name_part = slugify(job.name) if job.name else "map"
        output_path = settings.output_dir / f"{job.uid}__{name_part}.png"
        output_path.write_bytes(image_bytes)

        jobs_repo.mark_done(conn, job.id, str(output_path), output_path.name)
        logger.info("job %s: done -> %s", job.id, output_path)
    except ComfyUIError as exc:
        logger.error("job %s: failed: %s", job.id, exc)
        jobs_repo.mark_failed(conn, job.id, str(exc))
    except Exception as exc:  # noqa: BLE001 - a bad job must never kill the worker loop
        logger.exception("job %s: unexpected error", job.id)
        jobs_repo.mark_failed(conn, job.id, str(exc))
