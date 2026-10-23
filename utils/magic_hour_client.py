"""Shared Magic Hour helpers used by the provider and every tool.

Kept free of Dify message helpers so the logic can be unit-tested offline.
"""

from __future__ import annotations

import time
from typing import Any, Callable, Optional

import httpx
from magic_hour import Client
from make_api_request import ApiError

from dify_plugin.errors.tool import ToolProviderCredentialValidationError

API_BASE = "https://api.magichour.ai/v1"
DOCS_URL = "https://docs.magichour.ai"
TERMINAL_STATUSES = {"complete", "error", "canceled"}

FREE_VIDEO_MODELS = ("wan-2.2", "ltx-2.3", "minimax-h3")

# model id -> (allowed durations in seconds, credits per second, notes)
VIDEO_MODELS: dict[str, dict[str, Any]] = {
    "wan-2.2": {"durations": list(range(3, 11)) + [15], "credits_per_sec": 24, "note": "free tier, good default"},
    "ltx-2.3": {"durations": list(range(1, 11)) + [15, 20, 25, 30], "credits_per_sec": 24, "note": "free tier, long clips"},
    "minimax-h3": {"durations": list(range(1, 11)) + [15, 20, 25, 30], "credits_per_sec": 24, "note": "free tier, up to 1080p"},
    "seedance-1.5": {"durations": list(range(4, 13)), "credits_per_sec": 30, "note": ""},
    "kling-2.6": {"durations": [5, 10], "credits_per_sec": 36, "note": ""},
    "kling-3.0": {"durations": list(range(3, 16)), "credits_per_sec": 48, "note": "high quality motion"},
    "veo3.1-lite": {"durations": [4, 6, 8, 16, 24, 32, 40, 48, 56], "credits_per_sec": 48, "note": ""},
    "veo3.1": {"durations": [4, 6, 8, 16, 24, 32, 40, 48, 56], "credits_per_sec": 96, "note": "top quality"},
    "veo3.1-audio": {"durations": [4, 6, 8, 16, 24, 32, 40, 48, 56], "credits_per_sec": 96, "note": "native audio"},
    "sora-2": {"durations": [4, 8, 12, 24, 36, 48, 60], "credits_per_sec": 120, "note": "max 720p"},
    "seedance-2.0-mini": {"durations": list(range(4, 16)), "credits_per_sec": None, "note": "720p"},
    "seedance-2.0": {"durations": list(range(4, 16)), "credits_per_sec": None, "note": "720p"},
    "seedance-2.5": {"durations": list(range(4, 31)), "credits_per_sec": None, "note": "720p"},
}

IMAGE_MODELS = (
    "default",
    "gpt-image-2",
    "nano-banana-pro",
    "seedream-5-pro",
    "flux-2-klein",
    "z-image-turbo",
    "qwen-edit",
)


def make_client(api_key: str, timeout: float = 120) -> Client:
    return Client(token=api_key, timeout=timeout)


def validate_api_key(api_key: str) -> None:
    """Cheap authenticated call: fetching a nonexistent project costs no credits.

    A valid key returns 404 ("Not Found"); an invalid key returns 401.
    """
    try:
        resp = httpx.get(
            f"{API_BASE}/video-projects/dify-credential-check",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=20,
        )
    except httpx.HTTPError as e:
        raise ToolProviderCredentialValidationError(f"Could not reach Magic Hour API: {e}") from e
    if resp.status_code in (401, 403):
        raise ToolProviderCredentialValidationError(
            "Invalid Magic Hour API key. Get one at https://magichour.ai/developer"
        )
    if resp.status_code >= 500:
        raise ToolProviderCredentialValidationError(f"Magic Hour API error {resp.status_code}; try again later.")
    if resp.status_code not in (200, 404):
        raise ToolProviderCredentialValidationError(
            f"Magic Hour credential check returned HTTP {resp.status_code}; authentication is unverified. Try again later."
        )
    # 404 (unknown id) or 200 both prove the key is accepted.


def estimate_video_credits(model: str, duration_seconds: float) -> Optional[int]:
    info = VIDEO_MODELS.get(model)
    if not info or info.get("credits_per_sec") is None:
        return None
    return int(round(info["credits_per_sec"] * duration_seconds))


def _downloads(project: Any) -> list[str]:
    downloads = getattr(project, "downloads", None) or []
    urls = []
    for d in downloads:
        url = getattr(d, "url", None) if not isinstance(d, dict) else d.get("url")
        if url:
            urls.append(url)
    return urls


def project_to_dict(project: Any, kind: str) -> dict[str, Any]:
    """Normalise an SDK project response into the JSON shape every integration returns."""
    urls = _downloads(project)
    out: dict[str, Any] = {
        "project_id": getattr(project, "id", None),
        "status": getattr(project, "status", None),
        "credits_charged": getattr(project, "credits_charged", None),
    }
    if kind == "video":
        out["video_url"] = urls[0] if urls else None
        for k in ("width", "height", "fps"):
            v = getattr(project, k, None)
            if v is not None:
                out[k] = v
    else:
        out["image_urls"] = urls
        out["image_url"] = urls[0] if urls else None
    err = getattr(project, "error", None)
    if err:
        out["error"] = err.model_dump() if hasattr(err, "model_dump") else str(err)
    return out


def wait_for_project(
    fetch: Callable[[], Any],
    poll_interval: float = 5.0,
    max_wait: float = 900.0,
    sleep: Callable[[float], None] = time.sleep,
) -> Any:
    """Poll `fetch()` until the project reaches a terminal status or max_wait elapses."""
    deadline = time.monotonic() + max_wait
    project = fetch()
    while getattr(project, "status", None) not in TERMINAL_STATUSES:
        if time.monotonic() >= deadline:
            return project
        sleep(poll_interval)
        project = fetch()
    return project


def text_to_video(
    client: Client,
    *,
    prompt: str,
    model: str = "wan-2.2",
    duration_seconds: float = 5,
    resolution: str = "480p",
    aspect_ratio: Optional[str] = "16:9",
    audio: Optional[bool] = None,
    name: Optional[str] = None,
    wait: bool = True,
) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "end_seconds": float(duration_seconds),
        "style": {"prompt": prompt},
        "model": model,
        "resolution": resolution,
        "name": name or f"Dify: {prompt[:60]}",
        "wait_for_completion": False,
        "download_outputs": False,
    }
    if aspect_ratio:
        kwargs["aspect_ratio"] = aspect_ratio
    if audio is not None:
        kwargs["audio"] = audio
    created = client.v1.text_to_video.generate(**kwargs)
    return _finish(client, created, "video", wait)


def image_to_video(
    client: Client,
    *,
    image_file_path: str,
    prompt: str,
    model: str = "wan-2.2",
    duration_seconds: float = 5,
    resolution: str = "480p",
    name: Optional[str] = None,
    wait: bool = True,
) -> dict[str, Any]:
    created = client.v1.image_to_video.generate(
        assets={"image_file_path": image_file_path},
        end_seconds=float(duration_seconds),
        style={"prompt": prompt},
        model=model,
        resolution=resolution,
        name=name or f"Dify: {prompt[:60]}",
        wait_for_completion=False,
        download_outputs=False,
    )
    return _finish(client, created, "video", wait)


def generate_image(
    client: Client,
    *,
    prompt: str,
    model: str = "default",
    image_count: int = 1,
    aspect_ratio: Optional[str] = None,
    name: Optional[str] = None,
    wait: bool = True,
) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "image_count": int(image_count),
        "style": {"prompt": prompt},
        "model": model,
        "name": name or f"Dify: {prompt[:60]}",
        "wait_for_completion": False,
        "download_outputs": False,
    }
    if aspect_ratio:
        kwargs["aspect_ratio"] = aspect_ratio
    created = client.v1.ai_image_generator.generate(**kwargs)
    return _finish(client, created, "image", wait)


def get_project(client: Client, project_id: str, kind: str = "video") -> dict[str, Any]:
    if kind == "image":
        project = client.v1.image_projects.get(id=project_id)
    else:
        project = client.v1.video_projects.get(id=project_id)
    return project_to_dict(project, kind)


def upload_image_bytes(client: Client, data: bytes, extension: str = "png") -> str:
    """Upload raw image bytes via the files API and return the file_path usable in assets."""
    ext = (extension or "png").lstrip(".").lower() or "png"
    resp = client.v1.files.upload_urls.create(items=[{"extension": ext, "type_": "image"}])
    item = resp.items[0]
    r = httpx.put(item.upload_url, content=data, timeout=120)
    r.raise_for_status()
    return item.file_path


def _finish(client: Client, created: Any, kind: str, wait: bool) -> dict[str, Any]:
    project_id = getattr(created, "id", None)
    if not wait or not project_id:
        result = project_to_dict(created, kind)
        result["project_id"] = project_id
        if not result.get("status"):
            result["status"] = "queued"
        return result
    resource = client.v1.image_projects if kind == "image" else client.v1.video_projects
    last_project = created

    def fetch() -> Any:
        nonlocal last_project
        last_project = resource.get(id=project_id)
        return last_project

    polling_error = None
    try:
        project = wait_for_project(fetch)
    except (ApiError, httpx.HTTPError) as e:
        # The paid creation succeeded. Preserve it even when status retrieval fails.
        project = last_project
        status_code = getattr(e, "status_code", None)
        polling_error = f"Status retrieval failed (HTTP {status_code})." if status_code else "Status retrieval failed."
    result = project_to_dict(project, kind)
    result["project_id"] = project_id
    if not result.get("status"):
        result["status"] = "queued"
    if result.get("credits_charged") is None:
        result["credits_charged"] = getattr(created, "credits_charged", None)
    if polling_error:
        result["polling_error"] = polling_error
    return result


def describe_api_error(e: Exception) -> str:
    if isinstance(e, ApiError):
        body = e.body
        msg = body.get("message") if isinstance(body, dict) else body
        if e.status_code in (401, 403):
            return "Magic Hour rejected the API key (401). Check the provider credentials."
        if e.status_code == 402:
            return f"Not enough Magic Hour credits: {msg}. Top up at https://magichour.ai/pricing"
        return f"Magic Hour API error {e.status_code}: {msg}"
    return f"Magic Hour request failed: {e}"
