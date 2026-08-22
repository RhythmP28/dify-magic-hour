from collections.abc import Generator
from typing import Any

from dify_plugin.entities.tool import ToolInvokeMessage

from tools._base import MagicHourBaseTool
from utils.magic_hour_client import image_to_video, upload_image_bytes


class ImageToVideoTool(MagicHourBaseTool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        prompt = (tool_parameters.get("prompt") or "").strip()
        if not prompt:
            raise ValueError("prompt is required")
        image_url = (tool_parameters.get("image_url") or "").strip()
        image_file = tool_parameters.get("image_file")
        if not image_url and image_file is None:
            raise ValueError("Provide image_url (public https URL) or image_file.")
        try:
            client = self._client()
            if image_url:
                image_file_path = image_url
            else:
                ext = getattr(image_file, "extension", None) or "png"
                image_file_path = upload_image_bytes(client, image_file.blob, ext)
            result = image_to_video(
                client,
                image_file_path=image_file_path,
                prompt=prompt,
                model=tool_parameters.get("model") or "wan-2.2",
                duration_seconds=float(tool_parameters.get("duration_seconds") or 5),
                resolution=tool_parameters.get("resolution") or "480p",
                wait=tool_parameters.get("wait_for_completion", True) is not False,
            )
        except Exception as e:  # noqa: BLE001
            raise self._error(e) from e
        yield from self._emit_result(result)
