#!/bin/sh

# Try to load i2c-dev module (may fail silently if already loaded or unsupported)
modprobe i2c-dev || echo "Could not modprobe i2c-dev; continuing anyway"

# Run Python with unbuffered output
exec python3 -u main.py