#!/usr/bin/env python 
from keypad import Keypad
from sonos_interface import SonosInterface
import database
import RPi.GPIO as GPIO 
from functools import partial
import asyncio
import logging
import board
import neopixel
import configparser

config = configparser.ConfigParser()
config.sections()
config.read('config.ini')

url = config['sonos']['api_url']
zone = config['sonos']['zone']
queuemode = config['sonos']['queuemode']
queueclear = config['sonos'].getboolean('queueclear')
coinslot_gpio_pin = config['general'].getint('coinslot_gpio_pin')
cabinet_lights_colour = config['general']['cabinet_lights_colour'].split(",")


logging.basicConfig(format='%(asctime)s %(levelname)-8s %(message)s',
    level=logging.DEBUG,
    datefmt='%Y-%m-%d %H:%M:%S')


async def jukebox_handler(queue,keypad,sonos):
    while True:
        if database.get_credits() >= 1:
            keypad.set_credit_light_on()
            # Get a "work item" out of the queue.
            output = await queue.get()

            # Notify the queue that the "work item" has been processed.
            queue.task_done()

            logging.info(f'Track selection detected on queue: {output}')
            logging.info(f"Matched to song in database. Playing song {database.get_track_name(output)} by {database.get_artist_name(output)}")
            result = sonos.set_track(database.get_track_id(output))
            if result:
                logging.info(f"Track successfully queued. Decrementing credits to {database.get_credits()}")
                database.decrement_credits()
            else:
                logging.error("Track does not exist. No credits decremented")
        else:
            keypad.set_credit_light_off()

def coinslot_handler(c):
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(coinslot_gpio_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.add_event_detect(coinslot_gpio_pin, GPIO.FALLING, 
            callback=coinslot_callback, bouncetime=200)

def coinslot_callback(channel):
    logging.info(f"Coin inserted - Incrementing credits to {database.get_credits()+1}")
    database.increment_credits()

def init_cabinet_lights(r,g,b):
    pixels = neopixel.NeoPixel(board.D18, 1)
    pixels[0] = (r,g,b)
    return pixels

def set_cabinet_lights(pixels,r,g,b):
    pixels[0] = (r,g,b)
    return pixels

def main():
    try:
        cabinet_lights = init_cabinet_lights(int(cabinet_lights_colour[0]),int(cabinet_lights_colour[1]),int(cabinet_lights_colour[2]))
        keypad_queue = asyncio.Queue()
        keypad = Keypad(keypad_queue)
        database.set_credits(0)
        sonos = SonosInterface(url,zone,queuemode,queueclear)
        coinslot_handler(credits)

        loop = asyncio.get_event_loop()
        loop.create_task(keypad.get_key_combination())
        loop.create_task(jukebox_handler(keypad_queue,keypad,sonos))
        loop.run_forever()

        loop.run_forever()

    finally:
        GPIO.cleanup()
        loop.close()

if __name__ == "__main__":
        main()
