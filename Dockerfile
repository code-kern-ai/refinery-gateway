ARG PARENT_IMAGE=kernai/refinery-parent-images:v2.5.0-common

FROM ${PARENT_IMAGE} AS builder

WORKDIR /app

USER root

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

WORKDIR /app

USER root

COPY --from=builder --chown=65532:65532 /opt/venv /opt/venv
COPY --from=builder --chown=65532:65532 /app /app

USER 65532:65532

CMD ["/usr/local/bin/uvicorn", "--host", "0.0.0.0", "--port", "80", "app:app"]
