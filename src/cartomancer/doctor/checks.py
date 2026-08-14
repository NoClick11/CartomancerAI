import uuid
from dataclasses import dataclass

from cartomancer.comfyui.client import ComfyUIClient, new_client_id
from cartomancer.comfyui.exceptions import ComfyUIError
from cartomancer.comfyui.workflow_builder import build_flux_gguf_txt2img_graph
from cartomancer.config import Settings
from cartomancer.db.connection import connect, current_version, pending_migrations
from cartomancer.models import Job, JobStatus


@dataclass
class CheckResult:
    name: str
    ok: bool
    message: str
    hint: str | None = None


def check_config(settings: Settings) -> CheckResult:
    if not settings.comfyui_url:
        return CheckResult(
            "config",
            False,
            "CARTOMANCER_COMFYUI_URL is not set",
            "Set CARTOMANCER_COMFYUI_URL (e.g. http://comfyui:8188) in your environment "
            "or .env file.",
        )
    return CheckResult("config", True, f"comfyui_url={settings.comfyui_url}")


def check_connectivity(client: ComfyUIClient) -> tuple[CheckResult, dict | None]:
    try:
        stats = client.system_stats()
    except ComfyUIError as exc:
        return (
            CheckResult(
                "connectivity",
                False,
                str(exc),
                f"Check that ComfyUI is running and reachable at {client.base_url} "
                "(e.g. `docker compose ps`).",
            ),
            None,
        )
    if stats is None:
        return (
            CheckResult("connectivity", False, "unexpected empty response from /system_stats"),
            None,
        )
    return CheckResult("connectivity", True, f"connected to {client.base_url}"), stats


def check_gpu(stats: dict | None) -> CheckResult:
    if stats is None:
        return CheckResult("gpu", False, "skipped (no connection to ComfyUI)")
    devices = stats.get("devices") or []
    gpu_devices = [d for d in devices if d.get("vram_total", 0) > 0]
    if not gpu_devices:
        return CheckResult(
            "gpu",
            False,
            "ComfyUI reports no device with VRAM",
            "Install the NVIDIA Container Toolkit and start the stack with "
            "`docker compose -f docker-compose.yml -f docker-compose.nvidia.yml up`.",
        )
    names = ", ".join(d.get("name", "?") for d in gpu_devices)
    return CheckResult("gpu", True, f"GPU visible: {names}")


def check_node(client: ComfyUIClient, class_name: str) -> CheckResult:
    try:
        ok = client.has_node(class_name)
    except ComfyUIError as exc:
        return CheckResult(f"node:{class_name}", False, str(exc))
    if not ok:
        return CheckResult(
            f"node:{class_name}",
            False,
            f"node '{class_name}' is not registered on the ComfyUI instance",
            "Confirm the comfyui image built https://github.com/city96/ComfyUI-GGUF into "
            "custom_nodes/ and rebuild it (`docker compose build comfyui`).",
        )
    return CheckResult(f"node:{class_name}", True, f"node '{class_name}' registered")


def _combo_options(info: dict | None, node_class: str, input_name: str) -> list[str] | None:
    if not info or node_class not in info:
        return None
    required = info[node_class].get("input", {}).get("required", {})
    spec = required.get(input_name)
    if not spec or not isinstance(spec[0], list):
        return None
    return spec[0]


def check_model_file(
    client: ComfyUIClient,
    node_class: str,
    input_name: str,
    expected_filename: str,
    model_subdir: str,
) -> CheckResult:
    name = f"model:{expected_filename}"
    try:
        info = client.object_info(node_class)
    except ComfyUIError as exc:
        return CheckResult(name, False, str(exc))
    options = _combo_options(info, node_class, input_name)
    if options is None:
        return CheckResult(
            name,
            False,
            f"could not read options for {node_class}.{input_name} (is the node registered?)",
        )
    if expected_filename not in options:
        return CheckResult(
            name,
            False,
            f"'{expected_filename}' not found among {node_class}.{input_name} options",
            f"Download it and place it at {{MODELS_DIR}}/{model_subdir}/{expected_filename} "
            "(mounted into the comfyui container via docker-compose.yml).",
        )
    return CheckResult(name, True, f"'{expected_filename}' found")


def check_database(settings: Settings) -> CheckResult:
    try:
        conn = connect(settings.db_path)
        pending = pending_migrations(conn)
        version = current_version(conn)
    except Exception as exc:  # noqa: BLE001 - report any DB access problem as a check failure
        return CheckResult(
            "database", False, str(exc), f"Check that {settings.db_path} is writable."
        )
    if pending:
        return CheckResult(
            "database",
            False,
            f"{len(pending)} pending migration(s)",
            "Run `cartomancer db upgrade`.",
        )
    return CheckResult("database", True, f"schema up to date (version {version})")


def check_output_dir(settings: Settings) -> CheckResult:
    try:
        settings.output_dir.mkdir(parents=True, exist_ok=True)
        probe = settings.output_dir / ".cartomancer_write_test"
        probe.write_text("ok")
        probe.unlink()
    except OSError as exc:
        return CheckResult(
            "output_dir", False, str(exc), f"Check permissions on {settings.output_dir}."
        )
    return CheckResult("output_dir", True, f"{settings.output_dir} is writable")


def run_checks(settings: Settings) -> list[CheckResult]:
    results = [check_config(settings)]

    client = ComfyUIClient(settings.comfyui_url)
    connectivity, stats = check_connectivity(client)
    results.append(connectivity)
    results.append(check_gpu(stats))

    if connectivity.ok:
        results.append(check_node(client, "UnetLoaderGGUF"))
        results.append(check_node(client, "DualCLIPLoaderGGUF"))
        results.append(
            check_model_file(
                client, "UnetLoaderGGUF", "unet_name", settings.default_unet_filename, "unet"
            )
        )
        results.append(
            check_model_file(
                client,
                "DualCLIPLoaderGGUF",
                "clip_name1",
                settings.default_clip_t5_filename,
                "clip",
            )
        )
        results.append(
            check_model_file(
                client,
                "DualCLIPLoaderGGUF",
                "clip_name2",
                settings.default_clip_l_filename,
                "clip",
            )
        )
        results.append(
            check_model_file(
                client, "VAELoader", "vae_name", settings.default_vae_filename, "vae"
            )
        )
    else:
        results.append(
            CheckResult(
                "comfyui_dependent_checks", False, "skipped (no connection to ComfyUI)"
            )
        )

    results.append(check_database(settings))
    results.append(check_output_dir(settings))
    return results


def run_full_smoke_test(settings: Settings, *, steps: int = 1, size: int = 64) -> CheckResult:
    """End-to-end generation of a tiny test image, to confirm generation actually works
    (not just that the nodes/models are present)."""
    client = ComfyUIClient(settings.comfyui_url, timeout=60.0)
    dummy = Job(
        id=0,
        uid=f"doctor-smoke-{uuid.uuid4().hex[:8]}",
        source_file=None,
        source_key=None,
        name=None,
        prompt="a simple test image, doctor smoke test",
        negative_prompt=None,
        tags=[],
        notes=None,
        width=size,
        height=size,
        steps=steps,
        cfg=1.0,
        guidance=3.5,
        sampler=settings.default_sampler,
        scheduler=settings.default_scheduler,
        seed=1,
        quantization=None,
        unet_filename=settings.default_unet_filename,
        status=JobStatus.RUNNING,
        comfyui_prompt_id=None,
        comfyui_client_id=None,
        output_path=None,
        output_filename=None,
        error_message=None,
        retry_count=0,
        created_at="",
        updated_at="",
        started_at=None,
        finished_at=None,
    )
    try:
        graph, _seed = build_flux_gguf_txt2img_graph(dummy, settings)
        client_id = new_client_id()
        prompt_id = client.queue_prompt(graph, client_id)
        history = client.wait_for_completion(prompt_id, client_id, timeout=180, poll_interval=2)
        images = client.extract_images(history)
        if not images:
            return CheckResult(
                "full_smoke_test", False, "generation completed but produced no image"
            )
        return CheckResult(
            "full_smoke_test", True, f"generated a {size}x{size} test image (prompt_id={prompt_id})"
        )
    except ComfyUIError as exc:
        return CheckResult(
            "full_smoke_test",
            False,
            str(exc),
            "Run `cartomancer doctor` without --full first to narrow down the issue.",
        )
