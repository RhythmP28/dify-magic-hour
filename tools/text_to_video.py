from collections.abc import Generator
from typing import Any

from dify_plugin.entities.tool import ToolInvokeMessage

from tools._base import MagicHourBaseTool
from utils.magic_hour_client import text_to_video


class TextToVideoTool(MagicHourBaseTool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        prompt = (tool_parameters.get("prompt") or "").strip()
        if not prompt:
            raise ValueError("prompt is required")
        try:
            result = text_to_video(
                self._client(),
                prompt=prompt,
                model=tool_parameters.get("model") or "wan-2.2",
                duration_seconds=float(tool_parameters.get("duration_seconds") or 5),
                resolution=tool_parameters.get("resolution") or "480p",
                aspect_ratio=tool_parameters.get("aspect_ratio") or "16:9",
                audio=True if tool_parameters.get("audio") else None,
                wait=tool_parameters.get("wait_for_completion", True) is not False,
            )
        except Exception as e:  # noqa: BLE001
            raise self._error(e) from e
        yield from self._emit_result(result)
