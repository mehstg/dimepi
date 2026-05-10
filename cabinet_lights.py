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
    pixels = neopixel.NeoPixel(board.D18, 1)
    pixels[0] = (r, g, b)
    return pixels

def set_color(pixels, r, g, b):
    pixels[0] = (r, g, b)
    return pixels

def _parse_time(value):
    return datetime.strptime(value, '%H:%M').time()

async def scheduler(pixels, settings_provider):
    lights_on = True
    applied_color = None
    while True:
        settings = settings_provider()
        if not settings:
            await asyncio.sleep(1)
            continue

        r = settings["r"]
        g = settings["g"]
        b = settings["b"]
        color = (r, g, b)
        on_time = _parse_time(settings["on_time"])
        off_time = _parse_time(settings["off_time"])
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
            elif applied_color != color:
                logging.info("Updating cabinet light colour.")
                turn_on(pixels, r, g, b)

        applied_color = color if lights_on else None
        logging.debug(f"Lighting scheduler tick: now={now}, on_time={on_time}, off_time={off_time}, color={color}")
        await asyncio.sleep(1)
