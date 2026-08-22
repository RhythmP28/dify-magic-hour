from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

from utils.magic_hour_client import describe_api_error, make_client


class MagicHourBaseTool(Tool):
    """Common helpers: build an SDK client from provider credentials and emit results."""

    def _client(self):
        api_key = (self.runtime.credentials or {}).get("magic_hour_api_key")
        if not api_key:
            raise ValueError("Magic Hour API key is not configured for this provider.")
        return make_client(str(api_key).strip())

    def _emit_result(self, result: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        yield self.create_json_message(result)
        urls = []
        if result.get("video_url"):
            urls.append(result["video_url"])
        urls.extend(result.get("image_urls") or [])
        for url in urls:
            yield self.create_link_message(url)
        for key in ("video_url", "image_url", "project_id", "status"):
            if result.get(key) is not None:
                yield self.create_variable_message(key, result[key])
        if result.get("status") == "error":
            yield self.create_text_message(f"Magic Hour job failed: {result.get('error')}. Credits are auto-refunded.")
        elif not urls:
            yield self.create_text_message(
                f"Magic Hour project {result.get('project_id')} is {result.get('status')}. "
                "Use the Get Project Status tool to fetch the output later."
            )

    @staticmethod
    def _error(e: Exception) -> ValueError:
        return ValueError(describe_api_error(e))
