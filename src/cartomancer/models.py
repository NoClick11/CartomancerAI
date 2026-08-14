from enum import StrEnum

from pydantic import BaseModel, Field


class JobStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PromptEntry(BaseModel):
    """A fully-resolved map description, ready to become a queued job.

    Produced by the ingest parsers (YAML/TXT) after merging per-entry
    overrides with file-level and config-level defaults.
    """

    source_key: str
    name: str | None = None
    prompt: str
    negative_prompt: str | None = None
    tags: list[str] = Field(default_factory=list)
    notes: str | None = None

    width: int
    height: int
    steps: int
    cfg: float = 1.0
    guidance: float
    sampler: str
    scheduler: str
    seed: int | None = None
    quantization: str | None = None
    unet_filename: str | None = None


class Job(BaseModel):
    """Mirrors a row in the `jobs` table."""

    id: int
    uid: str
    source_file: str | None
    source_key: str | None
    name: str | None
    prompt: str
    negative_prompt: str | None
    tags: list[str]
    notes: str | None

    width: int
    height: int
    steps: int
    cfg: float
    guidance: float
    sampler: str
    scheduler: str
    seed: int | None
    quantization: str | None
    unet_filename: str | None

    status: JobStatus
    comfyui_prompt_id: str | None
    comfyui_client_id: str | None
    output_path: str | None
    output_filename: str | None
    error_message: str | None
    retry_count: int

    created_at: str
    updated_at: str
    started_at: str | None
    finished_at: str | None
