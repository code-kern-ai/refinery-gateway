ARG PARENT_IMAGE=registry.dev.kern.ai/code-kern-ai/refinery-parent-images:dev-common
FROM ${PARENT_IMAGE}

WORKDIR /app

VOLUME ["/app"]

USER root

RUN apt-get update && \
    apt-get install --no-install-recommends -y curl libc6-dev zlib1g gcc && \
    rm -rf /var/lib/apt/lists/*

RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y

ENV PATH="/root/.cargo/bin:${PATH}"

COPY requirements*.txt .

RUN pip3 install --no-cache-dir -r requirements-dev.txt

COPY / .

ARG DOCKER_GID=999
RUN if id nonroot >/dev/null 2>&1; then \
      groupadd -o -g "${DOCKER_GID}" dockerhost 2>/dev/null || \
        groupmod -o -g "${DOCKER_GID}" dockerhost 2>/dev/null || true; \
      usermod -aG dockerhost nonroot; \
    fi

CMD ["/usr/local/bin/uvicorn", "--host", "0.0.0.0", "--port", "80", "app:app", "--reload"]
