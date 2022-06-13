#!/usr/bin/env python 
from keypad import Keypad
from credits import Credits
from sonos_interface import SonosInterface
import tracks
import RPi.GPIO as GPIO 
import asyncio
import json
import logging

url = 'http://192.168.1.50'
zone = 'Kitchen'
queuemode = 'now'

logging.basicConfig(level=logging.DEBUG)


async def print_queue(queue,credits,keypad,sonos):
    while True:
        if credits.get_credits() >= 1:
            keypad.set_credit_light_on()
            # Get a "work item" out of the queue.
            output = await queue.get()

            # Notify the queue that the "work item" has been processed.
            queue.task_done()

            logging.debug("Track matched. ID= " + output)
            result = sonos.set_track(tracks.get_track_id(output))
            if result:
                logging.info("Track successfully queued. Decrementing credits")
                credits.decrement_credits()
            else:
                logging.error("Track does not exist. No credits decremented")
        else:
            keypad.set_credit_light_off()



def main():
    try:
        keypad_queue = asyncio.Queue()
        keypad = Keypad(keypad_queue)
        credits = Credits(4)
        sonos = SonosInterface(url,zone,queuemode)

        loop = asyncio.get_event_loop()
        loop.create_task(keypad.get_key_combination())
        loop.create_task(print_queue(keypad_queue,credits,keypad,sonos))

        loop.run_forever()

    finally:
        GPIO.cleanup()
        loop.close()

if __name__ == "__main__":
        main()
