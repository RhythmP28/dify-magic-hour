from collections.abc import Generator
from typing import Any

from dify_plugin.entities.tool import ToolInvokeMessage

from tools._base import MagicHourBaseTool
from utils.magic_hour_client import get_project


class GetProjectTool(MagicHourBaseTool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        project_id = (tool_parameters.get("project_id") or "").strip()
        if not project_id:
            raise ValueError("project_id is required")
        kind = tool_parameters.get("kind") or "video"
        try:
            result = get_project(self._client(), project_id, kind)
        except Exception as e:  # noqa: BLE001
            raise self._error(e) from e
        yield from self._emit_result(result)
