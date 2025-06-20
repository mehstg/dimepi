import neopixel
import board
import asyncio
import logging
from datetime import datetime

def turn_off(pixels):
    pixels[0] = (0, 0, 0)

def turn_on(pixels, r, g, b):
    pixels[0] = (r, g, b)

def initialize(r, g, b):
    logging.debug("[CabinetLights] Initializing NeoPixel...")
    pixels = neopixel.NeoPixel(board.D18, 1)
    logging.debug("[CabinetLights] NeoPixel created, setting initial color.")
    pixels[0] = (r, g, b)
    return pixels

def set_color(pixels, r, g, b):
    pixels[0] = (r, g, b)
    return pixels

async def scheduler(pixels, r, g, b, on_time, off_time):
    lights_on = True
    logging.debug("[Scheduler] Task started and running.")
    while True:
        now = datetime.now().time()
        if now >= off_time or now < on_time:
            if lights_on:
                logging.info("Turning OFF cabinet lights (night mode).")
                turn_off(pixels)
                lights_on = False
        else:
            if not lights_on:
                logging.info("Turning ON cabinet lights (day mode).")
                turn_on(pixels, r, g, b)
                lights_on = True
        logging.debug(f"Lighting scheduler tick: now={now}, on_time={on_time}, off_time={off_time}")
        await asyncio.sleep(60)