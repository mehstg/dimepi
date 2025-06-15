import board
import busio
import digitalio
from adafruit_mcp230xx.mcp23017 import MCP23017
import time
import asyncio
import logging

class Keypad:

    buttons = {}
    leds = {}

    ledmap = {
        "left" : {1: "2", 2: "1", 5: "A", 7: "B", 9: "C", 10: "D", 13: "4", 14: "3"},
        "middle" : {6: "credit", 9: "E", 10: "F", 13: "6", 14: "5"},
        "right" : {1: "8", 2: "7", 5: "G", 6: "H", 8: "J", 10: "K", 13: "10", 15: "9"}
    }

    keymap = {
        "left" : {0: "2", 3: "1", 4: "A", 6: "B", 8: "C", 11: "D", 12: "4", 15: "3"},
        "middle" : {8: "E", 11: "F", 12: "6", 15: "5"},
        "right" : {0: "8", 3: "7", 4: "G", 7: "H", 9: "J", 11: "K", 12: "10", 14: "9"}
    }

    def __init__(self, queue):
        self.queue = queue
        self.reinitialize_keypad()

    def reinitialize_keypad(self):
        try:
            i2c = busio.I2C(board.SCL, board.SDA)
            self.left = MCP23017(i2c, address=0x25)
            self.middle = MCP23017(i2c, address=0x22)
            self.right = MCP23017(i2c, address=0x20)

            self.buttons.clear()
            self.leds.clear()

            for k, v in self.keymap.items():
                for k1, v1 in v.items():
                    pin = getattr(self, k).get_pin(k1)
                    pin.direction = digitalio.Direction.INPUT
                    pin.pull = digitalio.Pull.UP
                    self.buttons[v1] = pin

            for k, v in self.ledmap.items():
                for k1, v1 in v.items():
                    pin = getattr(self, k).get_pin(k1)
                    pin.direction = digitalio.Direction.OUTPUT
                    pin.pull = digitalio.Pull.UP
                    pin.value = True
                    self.leds[v1] = pin

            logging.info("Keypad reinitialized successfully.")
        except Exception as e:
            logging.error(f"Failed to initialize keypad: {e}")

    def set_keys_off(self):
        for k,v in self.leds.items():
            if k != "credit":
                try:
                    v.value = True
                    time.sleep(0.01)
                except Exception as e:
                    logging.warning(f"Error turning off key {k}: {e}")
        return True

    def set_keys_on(self):
        for k,v in self.leds.items():
            if k != "credit":
                try:
                    v.value = False
                    time.sleep(0.01)
                except Exception as e:
                    logging.warning(f"Error turning on key {k}: {e}")
        return True

    def set_key_on(self, key):
        try:
            self.leds[key].value = False
        except Exception as e:
            logging.warning(f"Error setting key {key} on: {e}")

    def set_key_off(self, key):
        try:
            self.leds[key].value = True
        except Exception as e:
            logging.warning(f"Error setting key {key} off: {e}")

    def toggle_key(self, key):
        try:
            self.leds[key].value = not self.leds[key].value
        except Exception as e:
            logging.warning(f"Error toggling key {key}: {e}")

    def set_credit_light_off(self):
        try:
            self.leds["credit"].value = True
            return True
        except Exception as e:
            logging.warning("Error turning credit light off")
            return False

    def set_credit_light_on(self):
        try:
            self.leds["credit"].value = False
            return True
        except Exception as e:
            logging.warning("Error turning credit light on")
            return False

    def get_credit_light(self):
        try:
            return self.leds["credit"].value
        except Exception as e:
            logging.warning("Error reading credit light")
            return None

    def get_keypress(self):
        try:
            for k, v in self.buttons.items():
                if v.value == False:
                    return k
            return False
        except Exception as e:
            logging.warning(f"I2C error during keypress check: {e}")
            self.reinitialize_keypad()
            return False

    async def get_key_combination(self):
        while True:
            try:
                l = self.get_keypress()
                if l and l.isalpha():
                    logging.debug("Matched Alpha Character: " + l)
                    self.toggle_key(l)
                    t_end = time.time() + 5
                    while time.time() < t_end:
                        n = self.get_keypress()
                        if n and n.isdigit():
                            logging.debug("Matched Digit: " + n)
                            self.toggle_key(n)
                            await asyncio.sleep(1)
                            self.set_keys_off()
                            self.queue.put_nowait(l + n)
                            break
                        await asyncio.sleep(0.1)
                    else:
                        logging.debug("Timeout waiting for digit")
                        self.set_keys_off()
                await asyncio.sleep(0.1)
            except Exception as e:
                logging.warning(f"Error in key combination poller: {e}")
                self.reinitialize_keypad()
                await asyncio.sleep(1)