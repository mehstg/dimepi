FROM balenalib/raspberrypi3-python:sid

RUN apt-get update && \
    apt-get -y install python3-smbus build-essential && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["sh", "-c", "modprobe i2c-dev && python3 main.py"]
