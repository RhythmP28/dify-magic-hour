from collections.abc import Generator
from typing import Any

from dify_plugin.entities.tool import ToolInvokeMessage

from tools._base import MagicHourBaseTool
from utils.magic_hour_client import generate_image


class GenerateImageTool(MagicHourBaseTool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        prompt = (tool_parameters.get("prompt") or "").strip()
        if not prompt:
            raise ValueError("prompt is required")
        count = int(tool_parameters.get("image_count") or 1)
        count = max(1, min(count, 4))
        try:
            result = generate_image(
                self._client(),
                prompt=prompt,
                model=tool_parameters.get("model") or "default",
                image_count=count,
                aspect_ratio=tool_parameters.get("aspect_ratio") or None,
                wait=tool_parameters.get("wait_for_completion", True) is not False,
            )
        except Exception as e:  # noqa: BLE001
            raise self._error(e) from e
        yield from self._emit_result(result)
