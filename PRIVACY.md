## Privacy Policy — Magic Hour plugin for Dify

This plugin lets Dify applications call the Magic Hour API (https://magichour.ai) to generate videos and images.

### Data collection

- The plugin itself does not collect, store or log any personal data.
- It requires a **Magic Hour API key**, which you enter in Dify's provider settings. The key is stored by your Dify instance using Dify's credential storage and is only sent to `https://api.magichour.ai` as a Bearer token.

### Data sent to third parties

- **Prompts**, generation settings (model, duration, resolution, aspect ratio) and, for image-to-video, the **source image** (a public URL you provide, or the bytes of a file uploaded in Dify) are sent to Magic Hour to perform the generation.
- Magic Hour processes this content under its own privacy policy: https://magichour.ai/privacy and terms: https://magichour.ai/terms. Generated outputs are hosted by Magic Hour on time-limited download URLs.
- No other third-party service is contacted.

### Data retention

- The plugin keeps nothing between invocations. Generated outputs and project history live in your Magic Hour account and can be deleted there (or via `DELETE /v1/video-projects/{id}` / `DELETE /v1/image-projects/{id}`).

### Contact

Questions: open an issue at https://github.com/RhythmP28/dify-magic-hour or contact the author via GitHub (https://github.com/RhythmP28).
