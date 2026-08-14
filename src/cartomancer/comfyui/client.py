import json
import time
import uuid
from dataclasses import dataclass

import requests
import websocket

from .exceptions import (
    ComfyUIConnectionError,
    ComfyUIExecutionError,
    ComfyUIRequestError,
    ComfyUITimeoutError,
)


@dataclass
class ImageRef:
    filename: str
    subfolder: str
    type: str


def new_client_id() -> str:
    return uuid.uuid4().hex


class ComfyUIClient:
    """Thin wrapper around the ComfyUI HTTP + WebSocket API.

    Deliberately synchronous/blocking: the worker processes one job at a
    time, so there's no benefit to async here and it keeps the code easy to
    compare against ComfyUI's own `script_examples`.
    """

    def __init__(self, base_url: str, *, timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    @property
    def _ws_url(self) -> str:
        return self.base_url.replace("http://", "ws://").replace("https://", "wss://") + "/ws"

    def _get(self, path: str, **kwargs) -> dict | None:
        try:
            resp = requests.get(f"{self.base_url}{path}", timeout=self.timeout, **kwargs)
        except requests.RequestException as exc:
            raise ComfyUIConnectionError(
                f"could not reach ComfyUI at {self.base_url}: {exc}"
            ) from exc
        if resp.status_code == 404:
            return None
        if not resp.ok:
            raise ComfyUIRequestError(f"GET {path} failed: {resp.status_code} {resp.text[:500]}")
        return resp.json()

    def system_stats(self) -> dict | None:
        return self._get("/system_stats")

    def object_info(self, class_name: str | None = None) -> dict | None:
        path = f"/object_info/{class_name}" if class_name else "/object_info"
        return self._get(path)

    def has_node(self, class_name: str) -> bool:
        info = self.object_info(class_name)
        return bool(info) and class_name in info

    def queue_prompt(self, graph: dict, client_id: str) -> str:
        try:
            resp = requests.post(
                f"{self.base_url}/prompt",
                json={"prompt": graph, "client_id": client_id},
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise ComfyUIConnectionError(
                f"could not reach ComfyUI at {self.base_url}: {exc}"
            ) from exc
        if not resp.ok:
            raise ComfyUIRequestError(f"POST /prompt failed: {resp.status_code} {resp.text[:1000]}")
        data = resp.json()
        node_errors = data.get("node_errors") or {}
        if node_errors:
            raise ComfyUIRequestError(
                f"ComfyUI rejected the workflow: {json.dumps(node_errors)[:1000]}"
            )
        prompt_id = data.get("prompt_id")
        if not prompt_id:
            raise ComfyUIRequestError(f"unexpected /prompt response: {data!r}")
        return prompt_id

    def get_history(self, prompt_id: str) -> dict | None:
        history = self._get(f"/history/{prompt_id}")
        if not history:
            return None
        return history.get(prompt_id)

    def get_image_bytes(self, image: ImageRef) -> bytes:
        try:
            resp = requests.get(
                f"{self.base_url}/view",
                params={
                    "filename": image.filename,
                    "subfolder": image.subfolder,
                    "type": image.type,
                },
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise ComfyUIConnectionError(
                f"could not reach ComfyUI at {self.base_url}: {exc}"
            ) from exc
        if not resp.ok:
            raise ComfyUIRequestError(f"GET /view failed: {resp.status_code}")
        return resp.content

    def wait_for_completion(
        self,
        prompt_id: str,
        client_id: str,
        *,
        timeout: float,
        poll_interval: float = 5.0,
    ) -> dict:
        """Block until `prompt_id` finishes and return its /history entry.

        Tries the WebSocket first (near-instant completion detection), and
        falls back to polling /history if the socket can't be opened or
        drops mid-wait. Jobs can take 10-20 minutes, long enough for a flaky
        connection (e.g. between Docker containers) to matter.
        """
        deadline = time.monotonic() + timeout
        if self._wait_via_websocket(prompt_id, client_id, deadline):
            history = self.get_history(prompt_id)
            if history is not None:
                return self._check_history_status(prompt_id, history)
        return self._wait_via_polling(prompt_id, deadline, poll_interval)

    def _wait_via_websocket(self, prompt_id: str, client_id: str, deadline: float) -> bool:
        url = f"{self._ws_url}?clientId={client_id}"
        try:
            ws = websocket.create_connection(url, timeout=10)
        except (OSError, websocket.WebSocketException):
            return False
        try:
            while time.monotonic() < deadline:
                remaining = max(deadline - time.monotonic(), 0.1)
                ws.settimeout(min(remaining, 30))
                try:
                    message = ws.recv()
                except websocket.WebSocketTimeoutException:
                    continue
                except (OSError, websocket.WebSocketException):
                    return False
                if isinstance(message, bytes):
                    continue  # binary preview frames, not a status message
                try:
                    data = json.loads(message)
                except json.JSONDecodeError:
                    continue
                if data.get("type") != "executing":
                    continue
                payload = data.get("data") or {}
                if payload.get("prompt_id") == prompt_id and payload.get("node") is None:
                    return True
            return False
        finally:
            try:
                ws.close()
            except Exception:
                pass

    def _wait_via_polling(self, prompt_id: str, deadline: float, poll_interval: float) -> dict:
        while True:
            history = self.get_history(prompt_id)
            if history is not None:
                return self._check_history_status(prompt_id, history)
            if time.monotonic() >= deadline:
                raise ComfyUITimeoutError(f"prompt {prompt_id} did not finish in time")
            time.sleep(poll_interval)

    @staticmethod
    def _check_history_status(prompt_id: str, history: dict) -> dict:
        status = history.get("status") or {}
        if status.get("status_str") == "error":
            raise ComfyUIExecutionError(f"prompt {prompt_id} failed: {status.get('messages')}")
        return history

    @staticmethod
    def extract_images(history: dict) -> list[ImageRef]:
        images: list[ImageRef] = []
        for node_output in (history.get("outputs") or {}).values():
            for img in node_output.get("images", []):
                images.append(
                    ImageRef(
                        filename=img["filename"],
                        subfolder=img.get("subfolder", ""),
                        type=img.get("type", "output"),
                    )
                )
        return images
