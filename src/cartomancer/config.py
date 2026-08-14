from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CARTOMANCER_", env_file=".env", extra="ignore")

    comfyui_url: str = "http://localhost:8188"

    db_path: Path = Path("./data/db/cartomancer.sqlite3")
    output_dir: Path = Path("./data/output")

    # Defaults used when a prompt entry / CLI flag doesn't override them.
    default_width: int = 1024
    default_height: int = 1024
    default_steps: int = 20
    default_guidance: float = 3.5
    default_sampler: str = "euler"
    default_scheduler: str = "simple"
    default_quantization: str = "Q4_K_S"

    default_unet_filename: str = "flux1-dev-Q4_K_S.gguf"
    default_clip_t5_filename: str = "t5-v1_1-xxl-encoder-Q4_K_S.gguf"
    default_clip_l_filename: str = "clip_l.safetensors"
    default_vae_filename: str = "ae.safetensors"

    worker_poll_interval_seconds: float = 5.0
    worker_job_timeout_seconds: float = 1800.0


def get_settings() -> Settings:
    return Settings()
