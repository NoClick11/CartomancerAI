FROM python:3.12-slim

RUN pip install --no-cache-dir uv

WORKDIR /app

# Install dependencies first so this layer is cached across source changes.
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project

COPY src/ src/
RUN uv sync --frozen --no-dev

ENV PATH="/app/.venv/bin:${PATH}"

# docker-compose runs this container as a non-root uid (see `user:` in
# docker-compose.yml); HOME needs to point somewhere world-writable since
# that uid has no /etc/passwd entry and /app is owned by root.
ENV HOME=/tmp

ENTRYPOINT ["cartomancer"]
CMD ["worker", "start"]
