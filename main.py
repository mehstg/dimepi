#!/usr/bin/env python 
from keypad import Keypad
from credits import Credits
import RPi.GPIO as GPIO 
import asyncio
import json

async def print_queue(queue,credits,keypad):
    while True:
        if credits.get_credits() >= 1:
            # Get a "work item" out of the queue.
            output = await queue.get()

            # Notify the queue that the "work item" has been processed.
            queue.task_done()

            print(output)
            credits.decrement_credits()
        else:
            keypad.set_credit_off()

def main():
    try:
        keypad_queue = asyncio.Queue()
        keypad = Keypad(keypad_queue)
        credits = Credits(4)

        loop = asyncio.get_event_loop()
        loop.create_task(keypad.get_track_choice())
        loop.create_task(print_queue(keypad_queue,credits,keypad))

        keypad.set_credit_on()

        loop.run_forever()

    finally:
        GPIO.cleanup()
        loop.close()

if __name__ == "__main__":
        main()
