from pathlib import Path

import yaml

from cartomancer.config import Settings
from cartomancer.models import PromptEntry
from cartomancer.utils.slugify import default_source_key

GENERATION_FIELDS = {
    "width",
    "height",
    "steps",
    "cfg",
    "guidance",
    "sampler",
    "scheduler",
    "seed",
    "quantization",
    "unet_filename",
}


def _settings_defaults(settings: Settings) -> dict:
    return {
        "width": settings.default_width,
        "height": settings.default_height,
        "steps": settings.default_steps,
        "guidance": settings.default_guidance,
        "sampler": settings.default_sampler,
        "scheduler": settings.default_scheduler,
        "quantization": settings.default_quantization,
        "unet_filename": settings.default_unet_filename,
    }


def parse_yaml(path: Path, settings: Settings) -> list[PromptEntry]:
    raw = yaml.safe_load(path.read_text()) or {}
    file_defaults = raw.get("defaults") or {}
    raw_entries = raw.get("maps") or []

    base = _settings_defaults(settings)
    base.update({k: v for k, v in file_defaults.items() if k in GENERATION_FIELDS})
    base_tags = file_defaults.get("tags", [])

    entries: list[PromptEntry] = []
    for item in raw_entries:
        if "prompt" not in item or not str(item["prompt"]).strip():
            raise ValueError(f"map entry is missing a required 'prompt' field: {item!r}")

        merged = dict(base)
        merged.update({k: v for k, v in item.items() if k in GENERATION_FIELDS})

        name = item.get("name")
        prompt = str(item["prompt"]).strip()
        source_key = item.get("id") or default_source_key(prompt, name)

        entries.append(
            PromptEntry(
                source_key=str(source_key),
                name=name,
                prompt=prompt,
                negative_prompt=item.get("negative_prompt"),
                tags=list(item.get("tags", base_tags)),
                notes=item.get("notes"),
                **merged,
            )
        )
    return entries
