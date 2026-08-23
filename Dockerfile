# Frontend build stage
FROM oven/bun:1.4.0-alpine AS frontend-build

WORKDIR /app/frontend

RUN apk add --no-cache bash

COPY frontend/package.json frontend/bun.lock ./
RUN --mount=type=cache,target=/root/.bun \
    bun install --frozen-lockfile

COPY frontend/nuxt.config.ts ./nuxt.config.ts
COPY frontend/tsconfig.json ./tsconfig.json
COPY frontend/app ./app
COPY frontend/public ./public
RUN bun run generate

# Batch build stage
FROM rust:1-slim AS batch-build

ARG TARGETPLATFORM

WORKDIR /app/batch

COPY batch/Cargo.toml batch/Cargo.lock ./
RUN mkdir src && echo "fn main(){}" > src/main.rs

RUN --mount=type=cache,id=cargo-registry-${TARGETPLATFORM},target=/usr/local/cargo/registry,sharing=locked \
    --mount=type=cache,id=cargo-target-${TARGETPLATFORM},target=/app/batch/target,sharing=locked \
    cargo build --release

COPY batch/src ./src

RUN --mount=type=cache,id=cargo-registry-${TARGETPLATFORM},target=/usr/local/cargo/registry,sharing=locked \
    --mount=type=cache,id=cargo-target-${TARGETPLATFORM},target=/app/batch/target,sharing=locked \
    cargo build --release \
    && cp target/release/shiori-feed-batch /bin/

# Python dependency export stage: generates requirements.txt straight from
# api/pyproject.toml + api/uv.lock (the same lockfile `uv sync` uses in
# development), so the pinned set installed at runtime can never drift from
# what development actually uses. A hand-maintained requirements.txt did
# exactly that once already — sqlite-vec was added to pyproject.toml for the
# embedding feature but never copied into the old requirements.txt by hand,
# so a shipped image crashed at runtime with `ModuleNotFoundError:
# No module named 'sqlite_vec'` the first time that code path ran.
FROM python:3.14-slim AS api-deps

WORKDIR /app/api

RUN pip install --no-cache-dir uv

COPY api/pyproject.toml api/uv.lock ./
RUN uv export --no-dev --no-emit-project --no-hashes --format requirements.txt \
    -o requirements.txt

# Runtime stage
FROM python:3.14-slim

ARG TARGETARCH

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update \
  && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends nginx curl tzdata \
  && rm -rf /var/lib/apt/lists/*

RUN case "$TARGETARCH" in \
      amd64|arm64) ;; \
      *) echo "Unsupported architecture: $TARGETARCH" >&2; exit 1 ;; \
    esac \
  && curl -fsSL -o ./dbmate "https://github.com/amacneil/dbmate/releases/latest/download/dbmate-linux-${TARGETARCH}"
RUN chmod +x dbmate

ARG SUPERCRONIC_VERSION=v0.2.44
RUN case "$TARGETARCH" in \
      amd64) supercronic_sha1=6eb0a8e1e6673675dc67668c1a9b6409f79c37bc ;; \
      arm64) supercronic_sha1=6c6cba4cde1dd4a1dd1e7fb23498cde1b57c226c ;; \
      *) echo "Unsupported architecture: $TARGETARCH" >&2; exit 1 ;; \
    esac \
  && supercronic="supercronic-linux-${TARGETARCH}" \
  && curl -fsSLO "https://github.com/aptible/supercronic/releases/download/${SUPERCRONIC_VERSION}/${supercronic}" \
  && echo "${supercronic_sha1}  ${supercronic}" | sha1sum -c - \
  && chmod +x "$supercronic" \
  && mv "$supercronic" /usr/local/bin/supercronic

RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY --from=api-deps /app/api/requirements.txt /app/api/requirements.txt
RUN pip install --no-cache-dir -r /app/api/requirements.txt

COPY api /app/api
COPY db /app/db
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=frontend-build /app/frontend/dist /usr/share/nginx/html
COPY --from=batch-build /bin/shiori-feed-batch /usr/local/bin/shiori-feed-batch

COPY scripts/container/ /app/scripts/container/
RUN chmod +x /app/scripts/container/start.sh /app/scripts/container/render-scheduler.sh

# Runtime defaults; users can override these with `docker run -e` or compose
ENV DATABASE_URL=/data/data.db
ENV API_PORT=8000
ENV RSS_CRON_SCHEDULE="0 * * * *"

EXPOSE 3000 8000

CMD ["/app/scripts/container/start.sh"]
