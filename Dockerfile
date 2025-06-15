FROM balenalib/raspberrypi3-python:3.9

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    python3-smbus \
    build-essential && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip3 install --no-cache-dir -r requirements.txt

COPY . .

CMD ["sh", "-c", "modprobe i2c-dev && python3 main.py"]
