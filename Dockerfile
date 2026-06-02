ARG PARENT_IMAGE=registry.dev.kern.ai/code-kern-ai/refinery-parent-images:dev-common

FROM ${PARENT_IMAGE} AS builder

ENV VENV_PATH=/opt/venv
ENV PATH="${VENV_PATH}/bin:${PATH}"

WORKDIR /app

USER root

RUN if [ ! -d "${VENV_PATH}" ]; then python -m venv "${VENV_PATH}"; fi

# used for encryption and zipping of files
RUN apt-get update && \
    apt-get install --no-install-recommends -y curl libc6-dev zlib1g gcc && \
    rm -rf /var/lib/apt/lists/*

RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y

ENV PATH="/root/.cargo/bin:${PATH}"

COPY requirements.txt .

RUN pip3 install --no-cache-dir -r requirements.txt

COPY . .

FROM ${PARENT_IMAGE}

ENV VENV_PATH=/opt/venv
ENV PATH="${VENV_PATH}/bin:${PATH}"

WORKDIR /app

USER root

COPY --from=builder --chown=65532:65532 ${VENV_PATH} ${VENV_PATH}
COPY --from=builder --chown=65532:65532 /app /app

ARG DOCKER_GID=999
RUN if id nonroot >/dev/null 2>&1; then \
      groupadd -o -g "${DOCKER_GID}" dockerhost 2>/dev/null || \
        groupmod -o -g "${DOCKER_GID}" dockerhost 2>/dev/null || true; \
      usermod -aG dockerhost nonroot; \
    fi

USER nonroot

CMD ["/opt/venv/bin/uvicorn", "--host", "0.0.0.0", "--port", "80", "app:app"]
