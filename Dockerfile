FROM balenalib/raspberrypi3-python:sid

# Avoid buffered logs
ENV PYTHONUNBUFFERED=1

# Install dependencies
RUN apt-get update && \
    apt-get -y install python3-smbus build-essential && \
    rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /usr/src/app

# Copy requirements and install
COPY requirements.txt ./
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Add entrypoint script for modprobe and running Python
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# Use entrypoint
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]