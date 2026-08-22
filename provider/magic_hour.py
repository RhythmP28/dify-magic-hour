from typing import Any

from dify_plugin import ToolProvider
from dify_plugin.errors.tool import ToolProviderCredentialValidationError

from utils.magic_hour_client import validate_api_key


class MagicHourProvider(ToolProvider):
    def _validate_credentials(self, credentials: dict[str, Any]) -> None:
        api_key = (credentials or {}).get("magic_hour_api_key")
        if not api_key or not str(api_key).strip():
            raise ToolProviderCredentialValidationError("Magic Hour API key is required.")
        try:
            validate_api_key(str(api_key).strip())
        except ToolProviderCredentialValidationError:
            raise
        except Exception as e:  # noqa: BLE001
            raise ToolProviderCredentialValidationError(str(e)) from e
