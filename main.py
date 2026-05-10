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
from functools import partial
import asyncio
import logging
import configparser
import cabinet_lights

logger = logging.getLogger()
logger.setLevel(logging.INFO)

formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

if logger.hasHandlers():
    logger.handlers.clear()

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

config = configparser.ConfigParser()
config.sections()
config.read('config.ini')

url = config['sonos']['api_url']
zone = config['sonos']['zone']
queuemode = config['sonos']['queuemode']
queueclear = config['sonos'].getboolean('queueclear')
coinslot_gpio_pin = config['general'].getint('coinslot_gpio_pin')
cabinet_lights_colour = config['general']['cabinet_lights_colour'].split(",")

last_coin_time = 0
DEBOUNCE_TIME = config['general'].getfloat('coin_debounce_time')
_gpio_initialized = False
IDLE_POLL_INTERVAL = 0.1

async def jukebox_handler(queue,keypad,sonos):
    while True:
        if database.get_credits() >= 1:
            if keypad.get_credit_light() is not False:
                keypad.set_credit_light_on()
            # Get a "work item" out of the queue.
            output = await queue.get()

            # Notify the queue that the "work item" has been processed.
            queue.task_done()

            logging.debug(f'Track selection detected on queue: {output}')
            logging.info(f"Matched to song in database. Playing song {database.get_track_name(output)} by {database.get_artist_name(output)}")
            result = await sonos.set_track(database.get_track_id(output))
            if result:
                logging.debug(f"Track successfully queued.")
                database.decrement_credits()
            else:
                logging.error("Track does not exist. No credits decremented")
        else:
            if keypad.get_credit_light() is not True:
                keypad.set_credit_light_off()
            await asyncio.sleep(IDLE_POLL_INTERVAL)

def coinslot_handler():
    global _gpio_initialized
    if not _gpio_initialized:
        GPIO.setup(coinslot_gpio_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        try:
            GPIO.add_event_detect(coinslot_gpio_pin, GPIO.FALLING, callback=coinslot_callback, bouncetime=50)
            _gpio_initialized = True  # Only set this if successful
        except RuntimeError as e:
            logging.error(f"Failed to add edge detection: {e}")

def coinslot_callback(channel):
    global last_coin_time
    current_time = time.time()
    if current_time - last_coin_time > DEBOUNCE_TIME:
        last_coin_time = current_time
        logging.info(f"Coin inserted")
        database.increment_credits()
    else:
        logging.debug("Coin detected too quickly after previous. Ignored (debounced).")


def main():
    loop = None
    sonos = None
    tasks = []
    loop = asyncio.get_event_loop()
    try:
        r, g, b = int(cabinet_lights_colour[0]), int(cabinet_lights_colour[1]), int(cabinet_lights_colour[2])
        database.ensure_cabinet_lights_settings(
            r,
            g,
            b,
            config['general']['cabinet_lights_on_time'],
            config['general']['cabinet_lights_off_time'],
        )
        cabinet_lights_pixels = cabinet_lights.initialize(r, g, b)
        keypad_queue = asyncio.Queue()
        keypad = Keypad(keypad_queue)
        database.set_credits(0)
        sonos = SonosInterface(url, zone, queuemode, queueclear)
        coinslot_handler()

        tasks = [
            loop.create_task(keypad.get_key_combination()),
            loop.create_task(jukebox_handler(keypad_queue, keypad, sonos)),
            loop.create_task(cabinet_lights.scheduler(cabinet_lights_pixels, database.get_cabinet_lights_settings))
        ]

        loop.run_forever()
    finally:
        logging.info("Shutting down...")
        for task in tasks:
            task.cancel()
        loop.run_until_complete(asyncio.gather(*tasks, return_exceptions=True))
        if sonos:
            loop.run_until_complete(sonos.close())
        GPIO.cleanup()
        if loop:
            loop.close()
if __name__ == "__main__":
        main()
