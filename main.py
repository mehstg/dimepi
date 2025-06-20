#!/usr/bin/env python

import time
from time import monotonic as now
import sys
import RPi.GPIO as GPIO
GPIO.cleanup()
time.sleep(0.5)
GPIO.setmode(GPIO.BCM)

from keypad import Keypad
from sonos_interface import SonosInterface
import database
import cabinet_lights
import asyncio
import logging
import configparser
from datetime import datetime

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

if logger.hasHandlers():
    logger.handlers.clear()

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

config = configparser.ConfigParser()
config.read('config.ini')

url = config['sonos']['api_url']
zone = config['sonos']['zone']
queuemode = config['sonos']['queuemode']
queueclear = config['sonos'].getboolean('queueclear')
coinslot_gpio_pin = config['general'].getint('coinslot_gpio_pin')
cabinet_lights_colour = config['general']['cabinet_lights_colour'].split(",")

# Strip to avoid hidden spaces
lights_on_time = datetime.strptime(config['general']['cabinet_lights_on_time'].strip(), '%H:%M').time()
lights_off_time = datetime.strptime(config['general']['cabinet_lights_off_time'].strip(), '%H:%M').time()

last_coin_time = 0
DEBOUNCE_TIME = config['general'].getfloat('coin_debounce_time')
_gpio_initialized = False

# Async jukebox handler
async def jukebox_handler(queue, keypad, sonos):
    while True:
        if database.get_credits() >= 1:
            keypad.set_credit_light_on()
            output = await queue.get()
            queue.task_done()

            logging.debug(f'Track selection detected on queue: {output}')
            logging.info(f"Playing song {database.get_track_name(output)} by {database.get_artist_name(output)}")
            result = sonos.set_track(database.get_track_id(output))

            if result:
                logging.debug("Track successfully queued.")
                database.decrement_credits()
            else:
                logging.error("Track does not exist. No credits decremented")
        else:
            keypad.set_credit_light_off()

# GPIO setup for coinslot
def coinslot_handler():
    global _gpio_initialized
    if not _gpio_initialized:
        GPIO.setup(coinslot_gpio_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        try:
            GPIO.add_event_detect(coinslot_gpio_pin, GPIO.FALLING, callback=coinslot_callback, bouncetime=50)
            _gpio_initialized = True
        except RuntimeError as e:
            logging.error(f"Failed to add edge detection: {e}")

def coinslot_callback(channel):
    global last_coin_time
    current_time = time.time()
    if current_time - last_coin_time > DEBOUNCE_TIME:
        last_coin_time = current_time
        logging.info("Coin inserted")
        database.increment_credits()
    else:
        logging.debug("Coin detected too quickly after previous. Ignored (debounced).")

# ✅ Main async application entrypoint
async def main():
    r, g, b = int(cabinet_lights_colour[0]), int(cabinet_lights_colour[1]), int(cabinet_lights_colour[2])
    cabinet_lights_pixels = cabinet_lights.initialize(r, g, b)

    keypad_queue = asyncio.Queue()
    keypad = Keypad(keypad_queue)
    database.set_credits(0)
    sonos = SonosInterface(url, zone, queuemode, queueclear)

    # Schedule async tasks before enabling GPIO
    asyncio.create_task(keypad.get_key_combination())
    asyncio.create_task(jukebox_handler(keypad_queue, keypad, sonos))
    asyncio.create_task(cabinet_lights.scheduler(
        cabinet_lights_pixels, r, g, b, lights_on_time, lights_off_time
    ))

    logging.info("Async tasks scheduled. Initializing GPIO...")
    coinslot_handler()

    logging.info("Entering main event loop.")
    await asyncio.Event().wait()  # Keeps the program running

# Entry point
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Interrupted by user.")
    finally:
        GPIO.cleanup()