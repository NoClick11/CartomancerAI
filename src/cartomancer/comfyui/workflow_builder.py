import random

from cartomancer.config import Settings
from cartomancer.models import Job

MAX_SEED = 2**32 - 1


def build_flux_gguf_txt2img_graph(job: Job, settings: Settings) -> tuple[dict, int]:
    """Build a ComfyUI API-format prompt graph for a Flux.1 dev GGUF txt2img job.

    Returns (graph, seed_used) — when `job.seed` is None a random seed is
    generated here so the caller can persist the actual value used (jobs
    should be reproducible from their DB row alone).

    CFG is fixed at 1.0: Flux dev's prompt adherence is controlled by the
    FluxGuidance node's `guidance` value instead, which *is* configurable
    per job. KSampler still requires a "negative" conditioning input even
    though it's unused at cfg=1.0, so it's wired to a zeroed-out copy of the
    positive conditioning via ConditioningZeroOut.
    """
    seed = job.seed if job.seed is not None else random.randint(0, MAX_SEED)

    graph = {
        "unet_loader": {
            "class_type": "UnetLoaderGGUF",
            "inputs": {"unet_name": job.unet_filename or settings.default_unet_filename},
        },
        "clip_loader": {
            "class_type": "DualCLIPLoaderGGUF",
            "inputs": {
                "clip_name1": settings.default_clip_t5_filename,
                "clip_name2": settings.default_clip_l_filename,
                "type": "flux",
            },
        },
        "vae_loader": {
            "class_type": "VAELoader",
            "inputs": {"vae_name": settings.default_vae_filename},
        },
        "positive_encode": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": job.prompt, "clip": ["clip_loader", 0]},
        },
        "positive_guided": {
            "class_type": "FluxGuidance",
            "inputs": {"conditioning": ["positive_encode", 0], "guidance": job.guidance},
        },
        "negative": {
            "class_type": "ConditioningZeroOut",
            "inputs": {"conditioning": ["positive_encode", 0]},
        },
        "empty_latent": {
            "class_type": "EmptyLatentImage",
            "inputs": {"width": job.width, "height": job.height, "batch_size": 1},
        },
        "sampler": {
            "class_type": "KSampler",
            "inputs": {
                "model": ["unet_loader", 0],
                "positive": ["positive_guided", 0],
                "negative": ["negative", 0],
                "latent_image": ["empty_latent", 0],
                "seed": seed,
                "steps": job.steps,
                "cfg": 1.0,
                "sampler_name": job.sampler,
                "scheduler": job.scheduler,
                "denoise": 1.0,
            },
        },
        "vae_decode": {
            "class_type": "VAEDecode",
            "inputs": {"samples": ["sampler", 0], "vae": ["vae_loader", 0]},
        },
        "save_image": {
            "class_type": "SaveImage",
            "inputs": {
                "images": ["vae_decode", 0],
                "filename_prefix": f"cartomancer/{job.uid}",
            },
        },
    }
    return graph, seed
