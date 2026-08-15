# Roadmap

Items consciously deferred from v1 (CLI-only, txt2img with Flux.1 dev GGUF via
an external ComfyUI instance, everything running in Docker). Order does not
imply priority.

- **Web UI / frontend**: gallery of generated maps, search by name/tag, a
  visual queue. v1 is CLI-only because the data shape (tags, names) needed to
  be nailed down first — the schema was already designed with this in mind.
- **Upscale** (Ultimate SD Upscale) as an optional second stage of the
  pipeline, to take maps to 2K-4K via tiling.
- **ControlNet** to guide map layout/composition.
- **Robust, validated ROCm/AMD support.** The included
  `docker-compose.rocm.yml` is an unvalidated reference (no AMD hardware
  available to test against) — needs validation and likely adjustments from
  someone with the hardware.
- **Cancelling a running job** via the ComfyUI `POST /interrupt` endpoint
  (today `cartomancer cancel` only cancels jobs still `pending`).
- **Full-text search / normalized tags** (a `tags`/`job_tags` table or an
  FTS5 index), in case simple JSON-based tag filtering isn't enough once the
  map library grows.
- **Batch generation / variations** (N seeds per prompt) and LoRA support to
  keep a consistent visual style across maps.
  **Confirmed during real end-to-end testing (2026-08-15):** base Flux.1 dev,
  even with an "orthographic top-down / bird's eye view / battle map" prompt
  and a raised guidance value, still renders as a cinematic illustration
  (perspective, dramatic lighting/shadows) rather than the flat, geometric
  style expected of a tabletop battle map. Prompt tuning improved
  top-down-ness and detail level, but couldn't fully override the base
  model's bias — a LoRA trained on real battle maps is very likely required
  to actually hit the flat/orthographic VTT-map style, not just a nice-to-have
  for consistency. This is the next real gap to close after v1.
- **Completion notifications** (webhook, desktop notification) — today you
  have to run `cartomancer status` to know a job finished.
