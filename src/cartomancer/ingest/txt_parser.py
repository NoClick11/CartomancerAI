from pathlib import Path

from cartomancer.config import Settings
from cartomancer.models import PromptEntry
from cartomancer.utils.slugify import default_source_key


def parse_txt(path: Path, settings: Settings) -> list[PromptEntry]:
    entries: list[PromptEntry] = []
    for line in path.read_text().splitlines():
        prompt = line.strip()
        if not prompt or prompt.startswith("#"):
            continue
        entries.append(
            PromptEntry(
                source_key=default_source_key(prompt, None),
                name=None,
                prompt=prompt,
                tags=[],
                width=settings.default_width,
                height=settings.default_height,
                steps=settings.default_steps,
                guidance=settings.default_guidance,
                sampler=settings.default_sampler,
                scheduler=settings.default_scheduler,
                quantization=settings.default_quantization,
                unet_filename=settings.default_unet_filename,
            )
        )
    return entries
