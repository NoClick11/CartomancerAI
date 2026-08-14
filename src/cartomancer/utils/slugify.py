import hashlib
import re

_NON_SLUG_CHARS = re.compile(r"[^a-z0-9]+")


def slugify(text: str, max_len: int = 40) -> str:
    slug = _NON_SLUG_CHARS.sub("-", text.lower()).strip("-")
    return slug[:max_len].strip("-")


def default_source_key(prompt: str, name: str | None) -> str:
    """Deterministic id for a map entry that doesn't declare its own `id`."""
    base = slugify(name) if name else slugify(prompt[:40])
    digest = hashlib.sha1(prompt.encode("utf-8")).hexdigest()[:6]
    return f"{base}-{digest}" if base else digest
