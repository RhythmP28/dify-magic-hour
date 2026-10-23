import importlib
import os
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
import httpx
import yaml

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

from utils import magic_hour_client as mh  # noqa: E402


def _load(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
        return yaml.safe_load(f)


def test_manifest_and_provider_wiring():
    manifest = _load("manifest.yaml")
    assert manifest["author"] == "rhythmp28"
    assert manifest["name"] == "magic_hour"
    assert manifest["privacy"] == "PRIVACY.md"
    assert os.path.exists(os.path.join(ROOT, "_assets", manifest["icon"]))
    assert manifest["plugins"]["tools"] == ["provider/magic_hour.yaml"]

    provider = _load("provider/magic_hour.yaml")
    assert "magic_hour_api_key" in provider["credentials_for_provider"]
    assert provider["credentials_for_provider"]["magic_hour_api_key"]["type"] == "secret-input"
    assert os.path.exists(os.path.join(ROOT, provider["extra"]["python"]["source"]))
    assert set(provider["tools"]) == {
        "tools/text_to_video.yaml",
        "tools/image_to_video.yaml",
        "tools/generate_image.yaml",
        "tools/get_project.yaml",
    }


@pytest.mark.parametrize("tool_yaml", ["text_to_video", "image_to_video", "generate_image", "get_project"])
def test_tool_yaml_matches_python(tool_yaml):
    spec = _load(f"tools/{tool_yaml}.yaml")
    assert spec["identity"]["name"] == tool_yaml
    source = spec["extra"]["python"]["source"]
    assert source == f"tools/{tool_yaml}.py"
    assert os.path.exists(os.path.join(ROOT, source))
    assert spec["description"]["llm"]
    names = [p["name"] for p in spec["parameters"]]
    assert len(names) == len(set(names))
    for p in spec["parameters"]:
        assert p["form"] in {"llm", "form", "schema"}
        assert p["type"] in {"string", "number", "boolean", "select", "file", "files"}
        if p["type"] == "select":
            values = [o["value"] for o in p["options"]]
            assert p.get("default") in values
    mod = importlib.import_module(f"tools.{tool_yaml}")
    tool_classes = [c for c in vars(mod).values() if isinstance(c, type) and c.__name__.endswith("Tool") and c.__module__ == mod.__name__]
    assert len(tool_classes) == 1


def test_video_model_options_match_catalogue():
    spec = _load("tools/text_to_video.yaml")
    models = next(p for p in spec["parameters"] if p["name"] == "model")
    assert {o["value"] for o in models["options"]} == set(mh.VIDEO_MODELS)
    img = _load("tools/generate_image.yaml")
    imodels = next(p for p in img["parameters"] if p["name"] == "model")
    assert {o["value"] for o in imodels["options"]} == set(mh.IMAGE_MODELS)


def _project(status="complete", url="https://cdn.magichour.ai/out.mp4", **extra):
    return SimpleNamespace(
        id="proj_123", status=status, credits_charged=120,
        downloads=[SimpleNamespace(url=url, expires_at="x")] if url else [],
        width=854, height=480, fps=24, error=None, **extra,
    )


def test_text_to_video_polls_until_complete(monkeypatch):
    client = MagicMock()
    client.v1.text_to_video.generate.return_value = SimpleNamespace(id="proj_123", credits_charged=120)
    client.v1.video_projects.get.side_effect = [_project("queued", None), _project("rendering", None), _project()]
    monkeypatch.setattr(mh.time, "sleep", lambda s: None)

    out = mh.text_to_video(client, prompt="a corgi surfing", model="wan-2.2", duration_seconds=5, resolution="480p")

    kwargs = client.v1.text_to_video.generate.call_args.kwargs
    assert kwargs["end_seconds"] == 5.0 and kwargs["model"] == "wan-2.2"
    assert kwargs["style"] == {"prompt": "a corgi surfing"} and kwargs["aspect_ratio"] == "16:9"
    assert kwargs["wait_for_completion"] is False
    assert client.v1.video_projects.get.call_count == 3
    assert out == {
        "project_id": "proj_123", "status": "complete", "credits_charged": 120,
        "video_url": "https://cdn.magichour.ai/out.mp4", "width": 854, "height": 480, "fps": 24,
    }


def test_no_wait_returns_immediately():
    client = MagicMock()
    client.v1.text_to_video.generate.return_value = SimpleNamespace(id="proj_9", credits_charged=120)
    out = mh.text_to_video(client, prompt="x", wait=False)
    assert out["project_id"] == "proj_9" and out["status"] == "queued" and out["video_url"] is None
    client.v1.video_projects.get.assert_not_called()


def test_image_to_video_and_generate_image():
    client = MagicMock()
    client.v1.image_to_video.generate.return_value = SimpleNamespace(id="v1")
    client.v1.video_projects.get.return_value = _project()
    out = mh.image_to_video(client, image_file_path="https://x/y.png", prompt="zoom in")
    assert client.v1.image_to_video.generate.call_args.kwargs["assets"] == {"image_file_path": "https://x/y.png"}
    assert out["video_url"].endswith(".mp4")

    client.v1.ai_image_generator.generate.return_value = SimpleNamespace(id="i1")
    client.v1.image_projects.get.return_value = SimpleNamespace(
        id="i1", status="complete", credits_charged=5, error=None,
        downloads=[SimpleNamespace(url="https://x/a.png"), SimpleNamespace(url="https://x/b.png")],
    )
    out = mh.generate_image(client, prompt="poster", image_count=2, aspect_ratio="1:1")
    assert client.v1.ai_image_generator.generate.call_args.kwargs["image_count"] == 2
    assert out["image_urls"] == ["https://x/a.png", "https://x/b.png"] and out["image_url"] == "https://x/a.png"


def test_upload_image_bytes(monkeypatch):
    client = MagicMock()
    client.v1.files.upload_urls.create.return_value = SimpleNamespace(
        items=[SimpleNamespace(upload_url="https://bucket/put", file_path="api-assets/id/x.png")]
    )
    put = MagicMock(return_value=MagicMock(raise_for_status=lambda: None))
    monkeypatch.setattr(mh.httpx, "put", put)
    assert mh.upload_image_bytes(client, b"\x89PNG", "png") == "api-assets/id/x.png"
    assert put.call_args.args[0] == "https://bucket/put" and put.call_args.kwargs["content"] == b"\x89PNG"


def test_validate_api_key(monkeypatch):
    from dify_plugin.errors.tool import ToolProviderCredentialValidationError

    monkeypatch.setattr(mh.httpx, "get", lambda *a, **k: SimpleNamespace(status_code=404))
    mh.validate_api_key("good")
    monkeypatch.setattr(mh.httpx, "get", lambda *a, **k: SimpleNamespace(status_code=401))
    with pytest.raises(ToolProviderCredentialValidationError):
        mh.validate_api_key("bad")


def test_tool_invoke_emits_json_and_link(monkeypatch):
    from tools.text_to_video import TextToVideoTool

    monkeypatch.setattr("tools.text_to_video.text_to_video", lambda client, **kw: {
        "project_id": "p", "status": "complete", "video_url": "https://x/v.mp4", "credits_charged": 120,
    })
    tool = TextToVideoTool.__new__(TextToVideoTool)
    tool.runtime = SimpleNamespace(credentials={"magic_hour_api_key": "k"})
    tool.create_json_message = lambda j: ("json", j)
    tool.create_link_message = lambda l: ("link", l)
    tool.create_variable_message = lambda n, v: ("var", n, v)
    tool.create_text_message = lambda t: ("text", t)
    msgs = list(tool._invoke({"prompt": "hi"}))
    assert msgs[0][0] == "json" and msgs[0][1]["video_url"] == "https://x/v.mp4"
    assert ("link", "https://x/v.mp4") in msgs
    assert ("var", "video_url", "https://x/v.mp4") in msgs


def test_estimate_credits():
    assert mh.estimate_video_credits("wan-2.2", 5) == 120
    assert mh.estimate_video_credits("seedance-2.5", 5) is None


@pytest.mark.parametrize("kind", ["image", "video"])
@pytest.mark.parametrize("failure", ["timeout", "server"])
def test_polling_failure_preserves_paid_job_for_get_only_recovery(kind, failure):
    client = MagicMock()
    resource = client.v1.image_projects if kind == "image" else client.v1.video_projects
    generate = client.v1.ai_image_generator.generate if kind == "image" else client.v1.text_to_video.generate
    generate.return_value = SimpleNamespace(id="accepted_123", credits_charged=5)
    resource.get.side_effect = (
        httpx.ReadTimeout("private transport detail") if failure == "timeout"
        else mh.ApiError(response=httpx.Response(503, json={"message": "private transport detail"}))
    )
    out = mh.generate_image(client, prompt="poster") if kind == "image" else mh.text_to_video(client, prompt="poster")
    assert out["project_id"] == "accepted_123" and out["status"] == "queued"
    assert out["credits_charged"] == 5 and out["polling_error"]
    assert "private transport detail" not in out["polling_error"]
    if failure == "server":
        assert "503" in out["polling_error"]
    generate.assert_called_once()
    resource.get.side_effect = None
    resource.get.return_value = SimpleNamespace(id="accepted_123", status="complete", credits_charged=5, downloads=[])
    recovered = mh.get_project(client, out["project_id"], kind)
    assert recovered["status"] == "complete"
    resource.get.assert_called_with(id="accepted_123")
    generate.assert_called_once()


def test_later_polling_failure_retains_last_status_and_zero_charge(monkeypatch):
    client = MagicMock()
    created = SimpleNamespace(id="accepted_123", credits_charged=5)
    client.v1.image_projects.get.side_effect = [
        SimpleNamespace(id="accepted_123", status="rendering", credits_charged=0, downloads=[]),
        httpx.ReadTimeout("timeout"),
    ]
    real_wait = mh.wait_for_project
    monkeypatch.setattr(mh, "wait_for_project", lambda fetch: real_wait(fetch, sleep=lambda _: None))
    out = mh._finish(client, created, "image", True)
    assert out["project_id"] == "accepted_123" and out["status"] == "rendering"
    assert out["credits_charged"] == 0 and out["polling_error"]


@pytest.mark.parametrize("status", [400, 402, 429, 500])
def test_credential_validation_does_not_accept_an_inconclusive_response(monkeypatch, status):
    from dify_plugin.errors.tool import ToolProviderCredentialValidationError
    monkeypatch.setattr(mh.httpx, "get", lambda *a, **k: SimpleNamespace(status_code=status))
    with pytest.raises(ToolProviderCredentialValidationError, match=str(status)):
        mh.validate_api_key("key")


@pytest.mark.parametrize("module", ["text_to_video", "image_to_video", "generate_image", "get_project"])
def test_dify_native_class_loader_finds_exactly_one_tool(module):
    from dify_plugin import Tool
    from dify_plugin.core.utils.class_loader import load_single_subclass_from_source

    tool_cls = load_single_subclass_from_source(
        module_name=f"tools.{module}",
        script_path=os.path.join(ROOT, "tools", f"{module}.py"),
        parent_type=Tool,
    )
    assert tool_cls.__module__ == f"tools.{module}"
