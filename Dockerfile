ARG PARENT_IMAGE=kernai/refinery-parent-images:v3.1.0-common
ARG DHI_PYTHON_BUILD=dhi.io/python:3.11-debian12-dev

FROM ${PARENT_IMAGE} AS venv-source

FROM ${DHI_PYTHON_BUILD} AS builder

ENV VENV_PATH=/opt/venv
ENV PATH="${VENV_PATH}/bin:${PATH}"

WORKDIR /app

COPY --from=venv-source ${VENV_PATH} ${VENV_PATH}

RUN apt-get update && \
    apt-get install --no-install-recommends -y curl libc6-dev zlib1g gcc && \
    rm -rf /var/lib/apt/lists/*

RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y

ENV PATH="/root/.cargo/bin:${PATH}"

COPY requirements.txt .

RUN pip3 install --no-cache-dir -r requirements.txt

RUN mkdir -p /inference && chown -R 65532:65532 /inference

COPY . .

ARG DOCKER_GID=999
RUN groupadd -o -g "${DOCKER_GID}" dockerhost 2>/dev/null || \
      groupmod -o -g "${DOCKER_GID}" dockerhost 2>/dev/null || true && \
    (getent passwd nonroot >/dev/null || useradd -u 65532 -g 65532 -M -s /bin/sh nonroot) && \
    usermod -aG dockerhost nonroot

FROM ${PARENT_IMAGE}

ENV VENV_PATH=/opt/venv
ENV PATH="${VENV_PATH}/bin:${PATH}"

WORKDIR /app

COPY --from=builder /etc/group /etc/group
COPY --from=builder --chown=65532:65532 ${VENV_PATH} ${VENV_PATH}
COPY --from=builder --chown=65532:65532 /app /app

USER nonroot

CMD ["/opt/venv/bin/uvicorn", "--host", "0.0.0.0", "--port", "80", "app:app"]
