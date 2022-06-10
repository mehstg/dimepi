#!/usr/bin/env python 
from keypad import Keypad
import asyncio

async def print_queue(queue):
    while True:
        # Get a "work item" out of the queue.
        output = await queue.get()

        # Notify the queue that the "work item" has been processed.
        queue.task_done()

        print(output)

async def flash_credits(keypad):
    while True:
        keypad.toggle_key("credit")
        await asyncio.sleep(1)


def main():
    keypad_queue = asyncio.Queue()
    keypad = Keypad(keypad_queue)

    loop = asyncio.get_event_loop()
    get_track_choice = loop.create_task(keypad.get_track_choice())
    print = loop.create_task(print_queue(keypad_queue))
    flash = loop.create_task(flash_credits(keypad))

    loop.run_forever()


if __name__ == "__main__":
    main()