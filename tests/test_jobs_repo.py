import pytest

from cartomancer.db import jobs_repo
from cartomancer.db.connection import connect_and_migrate
from cartomancer.models import JobStatus, PromptEntry


def _entry(**overrides) -> PromptEntry:
    base = dict(
        source_key="map-1",
        name="Test Map",
        prompt="a test prompt",
        tags=["a", "b"],
        width=1024,
        height=1024,
        steps=20,
        guidance=3.5,
        sampler="euler",
        scheduler="simple",
    )
    base.update(overrides)
    return PromptEntry(**base)


def test_create_and_claim_job(settings):
    conn = connect_and_migrate(settings.db_path)
    job = jobs_repo.create_job(conn, _entry(), "maps.yaml")

    assert job.status == JobStatus.PENDING
    assert job.tags == ["a", "b"]

    claimed = jobs_repo.claim_next_pending(conn)
    assert claimed is not None
    assert claimed.id == job.id
    assert claimed.status == JobStatus.RUNNING

    assert jobs_repo.claim_next_pending(conn) is None


def test_duplicate_job_raises(settings):
    conn = connect_and_migrate(settings.db_path)
    jobs_repo.create_job(conn, _entry(), "maps.yaml")
    with pytest.raises(jobs_repo.DuplicateJobError):
        jobs_repo.create_job(conn, _entry(), "maps.yaml")


def test_allow_duplicates_bypasses_uniqueness(settings):
    conn = connect_and_migrate(settings.db_path)
    jobs_repo.create_job(conn, _entry(), "maps.yaml")
    job2 = jobs_repo.create_job(conn, _entry(), "maps.yaml", allow_duplicates=True)
    assert job2 is not None
    assert job2.source_key is None


def test_mark_done(settings):
    conn = connect_and_migrate(settings.db_path)
    job = jobs_repo.create_job(conn, _entry(), "maps.yaml")
    jobs_repo.claim_next_pending(conn)

    jobs_repo.mark_done(conn, job.id, "/out/x.png", "x.png")
    fetched = jobs_repo.get_job(conn, str(job.id))
    assert fetched.status == JobStatus.DONE
    assert fetched.output_filename == "x.png"


def test_requeue_failed_job(settings):
    conn = connect_and_migrate(settings.db_path)
    job = jobs_repo.create_job(conn, _entry(), "maps.yaml")
    jobs_repo.claim_next_pending(conn)
    jobs_repo.mark_failed(conn, job.id, "boom")

    assert jobs_repo.requeue(conn, job.id) is True
    fetched = jobs_repo.get_job(conn, str(job.id))
    assert fetched.status == JobStatus.PENDING
    assert fetched.retry_count == 1


def test_requeue_non_failed_job_is_noop(settings):
    conn = connect_and_migrate(settings.db_path)
    job = jobs_repo.create_job(conn, _entry(), "maps.yaml")
    assert jobs_repo.requeue(conn, job.id) is False


def test_recover_stuck_jobs(settings):
    conn = connect_and_migrate(settings.db_path)
    job = jobs_repo.create_job(conn, _entry(), "maps.yaml")
    jobs_repo.claim_next_pending(conn)  # now running

    recovered = jobs_repo.recover_stuck(conn)
    assert recovered == 1
    fetched = jobs_repo.get_job(conn, str(job.id))
    assert fetched.status == JobStatus.PENDING


def test_cancel_pending_job(settings):
    conn = connect_and_migrate(settings.db_path)
    job = jobs_repo.create_job(conn, _entry(), "maps.yaml")
    assert jobs_repo.cancel_pending(conn, job.id) is True
    assert jobs_repo.get_job(conn, str(job.id)).status == JobStatus.CANCELLED


def test_list_tags(settings):
    conn = connect_and_migrate(settings.db_path)
    jobs_repo.create_job(conn, _entry(source_key="a", tags=["x", "y"]), "maps.yaml")
    jobs_repo.create_job(conn, _entry(source_key="b", tags=["y", "z"]), "maps.yaml")
    assert jobs_repo.list_tags(conn) == ["x", "y", "z"]
