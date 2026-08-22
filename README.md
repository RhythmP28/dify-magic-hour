# Magic Hour plugin for Dify

**Author:** rhythmp28 · **Version:** 0.0.1 · **Type:** tool · **Source:** https://github.com/RhythmP28/dify-magic-hour

Generate AI videos and images inside Dify workflows, chatflows and agents using the [Magic Hour](https://magichour.ai) API. One API key gives access to Sora 2, Veo 3.1, Kling 3.0, Seedance, MiniMax H3, WAN 2.2, LTX 2.3 (video) and GPT-image, Nano Banana Pro, Seedream, Flux, Z-Image (image).

## Setup

1. Get a free API key at https://magichour.ai/developer (400 credits on signup + 100/day, no card required).
2. Install this plugin in Dify (Marketplace, or upload the `.difypkg` from the [releases](https://github.com/RhythmP28/dify-magic-hour/releases) / `dify-plugin plugin package .`).
3. In **Plugins → Magic Hour → Authorize**, paste the key as **Magic Hour API key**. The plugin validates it with a free authenticated request.

Connection requirements: outbound HTTPS to `api.magichour.ai` (and to the Magic Hour upload bucket when using `image_file`).

## Tools

| Tool | What it does | Returns |
|---|---|---|
| `text_to_video` | Video from a text prompt | `{project_id, status, video_url, credits_charged, width, height, fps}` + link |
| `image_to_video` | Animate an image (public URL or uploaded file) | same as above |
| `generate_image` | 1-4 images from a prompt | `{project_id, status, image_urls, image_url, credits_charged}` + links |
| `get_project` | Status / URLs of an earlier project (free) | same shapes |

Each generation tool has a `wait_for_completion` switch (default on: polls every 5 s, up to 15 min). Turn it off for fire-and-forget and use `get_project` later. Failed jobs are auto-refunded by Magic Hour.

## Quickstart (agent prompt)

Add the Magic Hour tools to an Agent app and ask:

> Make a 5 second 480p video of a corgi surfing at sunset, then generate a square poster image for it.

The agent calls `text_to_video` (wan-2.2, 5 s, 480p = 120 credits, inside the free tier) and `generate_image`, and replies with the output links. In a Workflow, reference the tool outputs as `{{#node.json.video_url#}}` or the `video_url` / `image_url` variables.

## Video models

| model | durations (s) | credits/s | notes |
|---|---|---|---|
| `wan-2.2` (default) | 3-10, 15 | 24 | free tier |
| `ltx-2.3` | 1-10, 15, 20, 25, 30 | 24 | free tier |
| `minimax-h3` | 1-10, 15, 20, 25, 30 | 24 | free tier, up to 1080p |
| `seedance-1.5` | 4-12 | 30 | |
| `kling-2.6` | 5, 10 | 36 | |
| `kling-3.0` | 3-15 | 48 | |
| `veo3.1-lite` | 4, 6, 8, 16, ..., 56 | 48 | |
| `veo3.1` / `veo3.1-audio` | 4, 6, 8, 16, ..., 56 | 96 | native audio variant |
| `sora-2` | 4, 8, 12, 24, 36, 48, 60 | 120 | max 720p |
| `seedance-2.0-mini` / `seedance-2.0` / `seedance-2.5` | 4-15 / 4-15 / 4-30 | — | 720p |

Image models: `default`, `gpt-image-2`, `nano-banana-pro`, `seedream-5-pro`, `flux-2-klein`, `z-image-turbo`, `qwen-edit`.

## Development

```bash
uv venv --python 3.12 && uv pip install -r requirements.txt pytest pyyaml
uv run pytest                        # offline tests (SDK mocked)
dify-plugin plugin package .         # builds magic_hour.difypkg
MAGIC_HOUR_API_KEY=... python examples/live_smoke.py   # real API call, ~120 credits
```

## Links

- API docs: https://docs.magichour.ai
- Python SDK: https://pypi.org/project/magic_hour/
- Other integrations: [LangChain](https://github.com/RhythmP28/langchain-magic-hour), [Vercel AI SDK provider](https://github.com/RhythmP28/magic-hour-ai-provider), [ComfyUI node](https://github.com/RhythmP28/comfyui-magic-hour), [MCP server](https://github.com/magichourhq)

## Privacy

See [PRIVACY.md](PRIVACY.md). Contact: https://github.com/RhythmP28/dify-magic-hour/issues

## License

MIT
