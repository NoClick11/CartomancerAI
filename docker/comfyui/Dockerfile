# Pinned, known-good ComfyUI + ComfyUI-GGUF image for Cartomancer (NVIDIA/CUDA path).
# Bump COMFYUI_REF / GGUF_NODE_REF deliberately when you want a newer ComfyUI or
# GGUF node; never track a moving branch in production.
FROM nvidia/cuda:12.6.3-cudnn-runtime-ubuntu22.04

ARG COMFYUI_REF=v0.3.34
ARG GGUF_NODE_REF=main

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
        git \
        python3.11 \
        python3.11-venv \
        python3-pip \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && ln -sf /usr/bin/python3.11 /usr/bin/python3 \
    && ln -sf /usr/bin/python3.11 /usr/bin/python

WORKDIR /opt/ComfyUI

RUN git clone --depth 1 --branch ${COMFYUI_REF} https://github.com/comfyanonymous/ComfyUI.git . \
    && pip install --no-cache-dir -r requirements.txt \
    # Force the CUDA 12.6 build of torch last, in case requirements.txt pulled
    # in a different (e.g. CPU-only) wheel as a transitive dependency.
    && pip install --no-cache-dir --force-reinstall \
        --index-url https://download.pytorch.org/whl/cu126 \
        torch torchvision

RUN git clone https://github.com/city96/ComfyUI-GGUF.git custom_nodes/ComfyUI-GGUF \
    && cd custom_nodes/ComfyUI-GGUF \
    && git checkout ${GGUF_NODE_REF} \
    && pip install --no-cache-dir -r requirements.txt

EXPOSE 8188

CMD ["python3", "main.py", "--listen", "0.0.0.0", "--port", "8188"]
