from unittest.mock import MagicMock

from cartomancer.comfyui.exceptions import ComfyUIConnectionError
from cartomancer.doctor.checks import (
    check_config,
    check_connectivity,
    check_gpu,
    check_model_file,
    check_node,
)


def test_check_config_ok(settings):
    assert check_config(settings).ok


def test_check_connectivity_failure_has_hint():
    client = MagicMock()
    client.base_url = "http://localhost:8188"
    client.system_stats.side_effect = ComfyUIConnectionError("boom")

    result, stats = check_connectivity(client)

    assert not result.ok
    assert stats is None
    assert "localhost:8188" in result.hint


def test_check_connectivity_ok():
    client = MagicMock()
    client.base_url = "http://localhost:8188"
    client.system_stats.return_value = {"devices": []}

    result, stats = check_connectivity(client)

    assert result.ok
    assert stats == {"devices": []}


def test_check_gpu_no_devices():
    assert not check_gpu({"devices": []}).ok


def test_check_gpu_no_connection():
    assert not check_gpu(None).ok


def test_check_gpu_with_device():
    result = check_gpu({"devices": [{"name": "RTX 3070", "vram_total": 8_000_000_000}]})
    assert result.ok
    assert "RTX 3070" in result.message


def test_check_node_present():
    client = MagicMock()
    client.has_node.return_value = True
    assert check_node(client, "UnetLoaderGGUF").ok


def test_check_node_missing_has_hint():
    client = MagicMock()
    client.has_node.return_value = False
    result = check_node(client, "UnetLoaderGGUF")
    assert not result.ok
    assert "ComfyUI-GGUF" in result.hint


def test_check_model_file_found():
    client = MagicMock()
    client.object_info.return_value = {
        "UnetLoaderGGUF": {"input": {"required": {"unet_name": [["flux1-dev-Q4_K_S.gguf"]]}}}
    }
    result = check_model_file(
        client, "UnetLoaderGGUF", "unet_name", "flux1-dev-Q4_K_S.gguf", "unet"
    )
    assert result.ok


def test_check_model_file_missing_has_hint():
    client = MagicMock()
    client.object_info.return_value = {
        "UnetLoaderGGUF": {"input": {"required": {"unet_name": [["other.gguf"]]}}}
    }
    result = check_model_file(
        client, "UnetLoaderGGUF", "unet_name", "flux1-dev-Q4_K_S.gguf", "unet"
    )
    assert not result.ok
    assert "unet" in result.hint
