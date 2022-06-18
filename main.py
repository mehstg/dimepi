#!/usr/bin/env python 
from keypad import Keypad
from credits import Credits
from sonos_interface import SonosInterface
import database
import RPi.GPIO as GPIO 
import signal
import asyncio
import logging

url = 'http://localhost:5005'
zone = 'Master Bedroom'
queuemode = 'now'
coinslot_gpio_pin = 4

logging.basicConfig(level=logging.DEBUG)


async def jukebox_handler(queue,credits,keypad,sonos):
    while True:
        if credits.get_credits() >= 1:
            keypad.set_credit_light_on()
            # Get a "work item" out of the queue.
            output = await queue.get()

            # Notify the queue that the "work item" has been processed.
            queue.task_done()

            logging.debug(f'Track selection detected on keypad: {output}')
            result = sonos.set_track(database.get_track_id(output))
            if result:
                logging.info("Track successfully queued. Decrementing credits")
                credits.decrement()
            else:
                logging.error("Track does not exist. No credits decremented")
        else:
            keypad.set_credit_light_off()

async def coinslot_handler(credits):
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(coinslot_gpio_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.add_event_detect(coinslot_gpio_pin, GPIO.FALLING, 
            callback=coinslot_callback, bouncetime=100)

    signal.signal(signal.SIGINT, signal_handler)
    signal.pause()

def coinslot_callback(channel):
    logging.info("Coin inserted - Incrementing credits")
    #credits.increment()

def signal_handler(sig, frame):
    GPIO.cleanup()

def main():
    try:

        keypad_queue = asyncio.Queue()
        keypad = Keypad(keypad_queue)
        credits = Credits(6)
        sonos = SonosInterface(url,zone,queuemode)

        loop = asyncio.get_event_loop()
        loop.create_task(keypad.get_key_combination())
        loop.create_task(jukebox_handler(keypad_queue,credits,keypad,sonos))
        loop.create_task(coinslot_handler(credits))

        loop.run_forever()

    finally:
        GPIO.cleanup()
        loop.close()

if __name__ == "__main__":
        main()
