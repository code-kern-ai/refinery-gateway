FROM kernai/refinery-parent-images:v1.19.0-common

WORKDIR /app

VOLUME ["/app"]

# used for encryption and zipping of files
RUN apt-get update && apt-get install -y curl libc6-dev zlib1g gcc --no-install-recommends

RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y

ENV PATH="/root/.cargo/bin:${PATH}"

COPY requirements*.txt .

RUN pip3 install --no-cache-dir -r requirements-dev.txt

COPY / .

CMD [ "/usr/local/bin/uvicorn", "--host", "0.0.0.0", "--port", "80", "app:app", "--reload" ]
