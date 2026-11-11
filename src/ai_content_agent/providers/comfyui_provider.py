"""Scene visuals from a local ComfyUI — any image or video model you can run yourself.

ComfyUI is the common front end for local models (Wan 2.2, FramePack, Flux,
SDXL, ...). Instead of wrapping each model, this drives a workflow you
already have working:

1. Build the workflow in ComfyUI and export it with "Save (API Format)".
2. In the exported JSON put placeholders where the studio should fill in:
       "{{prompt}}"   inside the positive prompt text (may be part of a longer string)
       "{{seed}}"     as the whole value of a seed input      -> random integer per scene
       "{{width}}" / "{{height}}"  as whole values            -> frame size for the aspect ratio
3. Set VISUAL_PROVIDER=comfyui (workflow outputs an image, animated with a
   slow zoom) or comfyui-video (workflow outputs a clip), COMFYUI_WORKFLOW to
   the file and COMFYUI_URL if ComfyUI is not on http://127.0.0.1:8188.

API used: POST /prompt, GET /history/<id>, GET /view. One scene is generated
at a time — a local GPU does not run two video models at once. No workflow is
bundled: they depend on the models and custom nodes installed on your machine.
"""

from __future__ import annotations

import copy
import json
import random
import time
import uuid
from pathlib import Path

import requests

from .base import ImageGenerator, VideoGenerator

_IMAGE_EXT = (".png", ".jpg", ".jpeg", ".webp")
_VIDEO_EXT = (".mp4", ".webm", ".mov", ".mkv", ".gif")
_SIZES = {
    "image": {"9:16": (1080, 1920), "16:9": (1920, 1080), "1:1": (1080, 1080)},
    "video": {"9:16": (720, 1280), "16:9": (1280, 720), "1:1": (720, 720)},  # typical local video-model sizes
}


def fill_workflow(workflow, values: dict):
    """Copy of `workflow` with placeholders replaced. A string that is exactly one placeholder takes
    the value's own type (so seeds and sizes stay integers); otherwise it is substituted as text."""

    if isinstance(workflow, dict):
        return {key: fill_workflow(value, values) for key, value in workflow.items()}
    if isinstance(workflow, list):
        return [fill_workflow(value, values) for value in workflow]
    if isinstance(workflow, str):
        for name, value in values.items():
            token = "{{" + name + "}}"
            if workflow.strip() == token:
                return value
            workflow = workflow.replace(token, str(value))
    return workflow


class _ComfyUI:
    kind = "image"
    extensions = _IMAGE_EXT
    max_concurrency = 1

    def __init__(
        self,
        workflow: str | None,
        url: str = "http://127.0.0.1:8188",
        model: str | None = None,
        *,
        timeout: float = 1800,
        poll_seconds: float = 2.0,
    ) -> None:
        if not workflow:
            raise ValueError(
                f"VISUAL_PROVIDER={self.name} needs COMFYUI_WORKFLOW: the path of a workflow exported from "
                "ComfyUI with “Save (API Format)”"
            )
        path = Path(workflow)
        if not path.is_file():
            raise FileNotFoundError(f"COMFYUI_WORKFLOW {workflow!r} not found")
        try:
            self._workflow = json.loads(path.read_text(encoding="utf-8"))
        except ValueError as exc:
            raise ValueError(f"COMFYUI_WORKFLOW {workflow!r} is not valid JSON: {exc}") from exc
        if "{{prompt}}" not in json.dumps(self._workflow):
            raise ValueError(f"COMFYUI_WORKFLOW {workflow!r} has no {{{{prompt}}}} placeholder for the scene description")
        if not all(isinstance(node, dict) and "class_type" in node for node in self._workflow.values()):
            raise ValueError(
                f"COMFYUI_WORKFLOW {workflow!r} is not in API format — export it with “Save (API Format)”, "
                "not the normal Save"
            )
        self._url = url.rstrip("/")
        self._model = model or path.stem  # label for provenance; ComfyUI picks the real model in the workflow
        self._timeout = timeout
        self._poll_seconds = poll_seconds

    def _generate(self, prompt: str, out_path: str, aspect_ratio: str) -> None:
        width, height = _SIZES[self.kind].get(aspect_ratio, _SIZES[self.kind]["9:16"])
        workflow = fill_workflow(copy.deepcopy(self._workflow), {
            "prompt": prompt, "seed": random.randint(1, 2**31 - 1), "width": width, "height": height,
        })
        try:
            queued = requests.post(f"{self._url}/prompt", json={"prompt": workflow, "client_id": uuid.uuid4().hex},
                                   timeout=60).json()
        except requests.ConnectionError as exc:
            raise ConnectionError(f"Cannot reach ComfyUI at {self._url} — start ComfyUI first (COMFYUI_URL)") from exc
        prompt_id = queued.get("prompt_id")
        if not prompt_id:
            raise RuntimeError(f"ComfyUI rejected the workflow: {json.dumps(queued.get('node_errors') or queued)[:600]}")

        output = self._wait(prompt_id)
        data = requests.get(
            f"{self._url}/view",
            params={"filename": output["filename"], "subfolder": output.get("subfolder", ""),
                    "type": output.get("type", "output")},
            timeout=300,
        )
        if data.status_code != 200 or not data.content:
            raise RuntimeError(f"ComfyUI could not serve {output['filename']} (HTTP {data.status_code})")
        Path(out_path).write_bytes(data.content)

    def _wait(self, prompt_id: str) -> dict:
        deadline = time.monotonic() + self._timeout
        while True:
            history = requests.get(f"{self._url}/history/{prompt_id}", timeout=60).json()
            entry = history.get(prompt_id)
            if entry:
                status = entry.get("status") or {}
                if status.get("status_str") == "error":
                    raise RuntimeError(f"ComfyUI workflow failed: {json.dumps(status.get('messages'))[:600]}")
                files = [item for node in (entry.get("outputs") or {}).values() for items in node.values()
                         if isinstance(items, list) for item in items
                         if isinstance(item, dict) and str(item.get("filename", "")).lower().endswith(self.extensions)]
                if files:
                    return files[-1]
                if status.get("completed") or status.get("status_str") == "success":
                    raise RuntimeError(
                        f"ComfyUI finished but produced no {self.kind} file — the workflow needs a "
                        f"{'Save Image' if self.kind == 'image' else 'video save/combine'} node"
                    )
            if time.monotonic() >= deadline:
                raise TimeoutError(f"ComfyUI did not finish within {self._timeout:.0f}s")
            time.sleep(self._poll_seconds)


class ComfyUIImageProvider(_ComfyUI, ImageGenerator):
    name = "comfyui"

    def generate_image(self, prompt: str, out_path: str, *, aspect_ratio: str = "9:16") -> None:
        self._generate(prompt, out_path, aspect_ratio)


class ComfyUIVideoProvider(_ComfyUI, VideoGenerator):
    name = "comfyui-video"
    kind = "video"
    extensions = _VIDEO_EXT

    def generate_clip(self, prompt: str, out_path: str, *, aspect_ratio: str = "9:16") -> None:
        self._generate(prompt, out_path, aspect_ratio)
