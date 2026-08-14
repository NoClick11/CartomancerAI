# Cartomancer

Cartomancer is a small, local-first queueing system for generating RPG battle
maps with AI. Write a batch of map descriptions, queue them, and let a worker
feed them one at a time into a local [ComfyUI](https://github.com/comfyanonymous/ComfyUI)
instance running **Flux.1 dev (GGUF quantized)**. It's built for the "I have
patience, not VRAM" case: a single 8GB NVIDIA GPU, offloading to RAM, 10-20
minutes per image — queue a handful of maps before bed, wake up to a folder
of finished images.

Cartomancer does **not** install, run, or manage ComfyUI itself, and it does
not download models for you. See [Prerequisites](#prerequisites) below for
why, and [`cartomancer doctor`](#diagnosing-problems) for a command that
tells you exactly what's missing.

See [ROADMAP.md](./ROADMAP.md) for what's intentionally out of scope for now
(web UI, upscaling, ControlNet, validated ROCm support, ...).

## How it works

1. You write map descriptions in a YAML (or plain text) file.
2. `cartomancer enqueue prompts.yaml` parses it and inserts jobs into a local
   SQLite queue.
3. `cartomancer worker start` runs a loop that takes one pending job at a
   time, builds the ComfyUI workflow graph for Flux.1 dev GGUF txt2img,
   submits it to the ComfyUI API, waits for the result, and saves the image.
4. `cartomancer status` / `cartomancer show <id>` let you check progress.

Everything (the worker and ComfyUI itself) runs in Docker via
`docker-compose`, with the generated queue database and images persisted to
your host filesystem under `./data`.

## Prerequisites

- Docker and Docker Compose.
- An NVIDIA GPU with the [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html)
  installed (this is the tested path; see `docker-compose.rocm.yml` for an
  unvalidated AMD/ROCm reference — contributions welcome).
- Flux.1 dev GGUF model files, downloaded manually and placed in
  `./data/models/...` (see below). Cartomancer doesn't fetch these for you:
  they're multi-gigabyte downloads with their own license (Black Forest
  Labs' non-commercial Flux.1-dev license), and auto-downloading them would
  make setup fragile and take licensing decisions out of your hands.

### Why is ComfyUI external?

ComfyUI is a fast-moving project with its own release cadence, and running
Flux GGUF requires a third-party custom node
([`city96/ComfyUI-GGUF`](https://github.com/city96/ComfyUI-GGUF)) plus
specific model files chosen deliberately (which quantization, which
source). Baking all of that into Cartomancer and trying to keep it working
across ComfyUI updates and every GPU/driver combination would make the
project fragile and hard to maintain. Instead, Cartomancer treats ComfyUI as
an external service it talks to over HTTP/WebSocket — similar to how a CLI
client for Ollama treats the Ollama server. The `docker/comfyui/Dockerfile`
in this repo builds a pinned, known-good ComfyUI + ComfyUI-GGUF image for
you, but you're free to point Cartomancer at any ComfyUI instance
(`CARTOMANCER_COMFYUI_URL`).

## Setup

```bash
git clone <this repo>
cd Cartomancer
cp .env.example .env

# Download Flux.1 dev GGUF model files and place them under ./data/models
# following ComfyUI's folder layout, e.g.:
#   ./data/models/unet/flux1-dev-Q4_K_S.gguf
#   ./data/models/clip/t5-v1_1-xxl-encoder-Q4_K_S.gguf
#   ./data/models/clip/clip_l.safetensors
#   ./data/models/vae/ae.safetensors
# `cartomancer doctor` (see below) tells you exactly what's missing.

docker compose -f docker-compose.yml -f docker-compose.nvidia.yml up -d --build
docker compose exec cartomancer cartomancer doctor
```

Once `doctor` passes:

```bash
docker compose exec cartomancer cartomancer enqueue /data/prompts/example.maps.yaml
docker compose logs -f cartomancer   # worker runs as the container's main process
```

Finished images land in `./data/output`.

## Writing prompts

**YAML (recommended)** — lets you attach a name and tags to each map, which
already lays the groundwork for a future search/gallery UI:

```yaml
defaults:
  width: 1024
  height: 1024
  steps: 20
  guidance: 3.5

maps:
  - id: forest-ruins-01
    name: "Ruins in the Ancient Forest"
    prompt: >
      top-down fantasy RPG battle map, ancient ruins overgrown with vines,
      moss-covered stone, dappled sunlight, hand-painted style, high detail
    tags: [forest, ruins, outdoor, battle]
```

**Plain text** — one prompt per line, using the configured defaults:

```
cozy fantasy tavern interior, top-down RPG map, wooden tables, warm lighting
```

## CLI reference

| Command | What it does |
|---|---|
| `cartomancer init` | Scaffold `prompts/`, `data/`, `.env` in the current directory |
| `cartomancer enqueue <file> [--dry-run] [--allow-duplicates]` | Parse a `.yaml`/`.txt` file and queue jobs |
| `cartomancer worker start [--poll-interval N] [--once]` | Run the worker loop (default command of the `cartomancer` container) |
| `cartomancer worker recover` | Reset jobs stuck in `running` after a crash back to `pending` |
| `cartomancer status [--status X] [--tag X] [--watch]` | List queued/running/finished jobs |
| `cartomancer show <id>` | Full detail of a single job |
| `cartomancer retry <id> [--all-failed]` | Re-queue failed job(s) |
| `cartomancer cancel <id>` | Cancel a still-`pending` job |
| `cartomancer list-tags` | List distinct tags in use |
| `cartomancer doctor [--full] [--json]` | Diagnose ComfyUI connectivity/model/node issues |
| `cartomancer db upgrade` | Apply pending SQLite schema migrations |
| `cartomancer config show` | Print effective configuration |
| `cartomancer version` | Print Cartomancer (and connected ComfyUI) version |

## Diagnosing problems

`cartomancer doctor` checks, in order: config validity, connectivity to the
ComfyUI API, whether ComfyUI can see a GPU, whether the `ComfyUI-GGUF`
custom node is registered, whether the expected model files are present, and
whether the local database/output directory are usable — each failure comes
with a concrete hint. Run it any time something isn't working before filing
an issue.

## Licensing

Cartomancer itself is [MIT-licensed](./LICENSE). That covers only the code
in this repository. ComfyUI (GPL-3.0) and the Flux.1-dev model weights
(Black Forest Labs' own non-commercial license) are external dependencies
you install and use separately — Cartomancer never bundles or redistributes
either.
