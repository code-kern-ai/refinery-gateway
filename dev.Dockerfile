FROM kernai/refinery-parent-images:v1.12.0-common

WORKDIR /app

VOLUME ["/app"]

# used for encryption and zipping of files
RUN apt-get update && apt-get install -y libc6-dev zlib1g gcc --no-install-recommends

COPY requirements.txt .

RUN pip3 install --no-cache-dir -r requirements.txt

COPY / .

CMD [ "/usr/local/bin/uvicorn", "--host", "0.0.0.0", "--port", "80", "app:app", "--reload" ]
