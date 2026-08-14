import json
from pathlib import Path

from cartomancer.comfyui.workflow_builder import build_flux_gguf_txt2img_graph
from cartomancer.models import Job, JobStatus

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "flux_gguf_api_workflow.json"


def _job(**overrides) -> Job:
    base = dict(
        id=1,
        uid="test-uid-1234",
        source_file="maps.yaml",
        source_key="map-1",
        name="Test Map",
        prompt="a test prompt",
        negative_prompt=None,
        tags=["a"],
        notes=None,
        width=1024,
        height=768,
        steps=25,
        cfg=1.0,
        guidance=4.0,
        sampler="euler",
        scheduler="simple",
        seed=42,
        quantization="Q4_K_S",
        unet_filename="flux1-dev-Q4_K_S.gguf",
        status=JobStatus.RUNNING,
        comfyui_prompt_id=None,
        comfyui_client_id=None,
        output_path=None,
        output_filename=None,
        error_message=None,
        retry_count=0,
        created_at="2026-01-01T00:00:00.000Z",
        updated_at="2026-01-01T00:00:00.000Z",
        started_at=None,
        finished_at=None,
    )
    base.update(overrides)
    return Job(**base)


def test_graph_matches_fixture(settings):
    graph, seed = build_flux_gguf_txt2img_graph(_job(), settings)

    expected = json.loads(FIXTURE_PATH.read_text())
    assert graph == expected
    assert seed == 42


def test_cfg_is_always_1_regardless_of_job_cfg(settings):
    graph, _ = build_flux_gguf_txt2img_graph(_job(cfg=7.5), settings)
    assert graph["sampler"]["inputs"]["cfg"] == 1.0


def test_random_seed_generated_when_job_seed_is_none(settings):
    graph, seed = build_flux_gguf_txt2img_graph(_job(seed=None), settings)
    assert isinstance(seed, int)
    assert graph["sampler"]["inputs"]["seed"] == seed


def test_unet_filename_falls_back_to_settings_default(settings):
    graph, _ = build_flux_gguf_txt2img_graph(_job(unet_filename=None), settings)
    assert graph["unet_loader"]["inputs"]["unet_name"] == settings.default_unet_filename
