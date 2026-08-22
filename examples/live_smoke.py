"""Live smoke test against the real Magic Hour API (costs ~120 credits + a few for the image).

    MAGIC_HOUR_API_KEY=mhk_live_... python examples/live_smoke.py
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.magic_hour_client import generate_image, make_client, text_to_video, validate_api_key  # noqa: E402

key = os.environ.get("MAGIC_HOUR_API_KEY")
if not key:
    sys.exit("Set MAGIC_HOUR_API_KEY (free at https://magichour.ai/developer)")

validate_api_key(key)
client = make_client(key)

print(json.dumps(generate_image(client, prompt="a corgi surfing at sunset, poster art", image_count=1), indent=2))
print(json.dumps(text_to_video(client, prompt="a corgi surfing at sunset", model="wan-2.2", duration_seconds=5, resolution="480p"), indent=2))
