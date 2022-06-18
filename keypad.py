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

    # Map out assignment of backlight LED's to port expander IO on Sound Leisure keypad module
    ledmap = {
        "left" : {1: "2", 2: "1", 5: "A", 7: "B", 9: "C", 10: "D", 13: "4", 14: "3"},
        "middle" : {6: "credit", 9: "E", 10: "F", 13: "6", 14: "5"},
        "right" : {1: "8", 2: "7", 5: "G", 6: "H", 8: "J", 10: "K", 13: "10", 15: "9"}
    }

    # Map out assignment of buttons to port expander IO on Sound Leisure keypad module
    keymap = {
        "left" : {0: "2", 3: "1", 4: "A", 6: "B", 8: "C", 11: "D", 12: "4", 15: "3"},
        "middle" : {8: "E", 11: "F", 12: "6", 15: "5"},
        "right" : {0: "8", 3: "7", 4: "G", 7: "H", 9: "J", 11: "K", 12: "10", 14: "9"}
    }

    def __init__(self,queue):
        self.queue = queue
        i2c = busio.I2C(board.SCL, board.SDA)
        left = MCP23017(i2c, address=0x25) #Leftmost port expander
        middle = MCP23017(i2c, address=0x22) #Middle port expander
        right = MCP23017(i2c, address=0x20) #Rightmost port expander

        #Set up input pins
        for k, v in self.keymap.items():
            for k1, v1 in self.keymap[k].items():
                pin = locals()[k].get_pin(k1)
                pin.direction = digitalio.Direction.INPUT
                pin.pull = digitalio.Pull.UP
                self.buttons[v1] = pin

        # Set up LED's
        for k, v in self.ledmap.items():
            for k1, v1 in self.ledmap[k].items():
                pin = locals()[k].get_pin(k1)
                pin.direction = digitalio.Direction.OUTPUT
                pin.pull = digitalio.Pull.UP
                pin.value = True
                self.leds[v1] = pin

    def set_keys_off(self):
        for k,v in self.leds.items():
            if k != "credit":
                v.value = True
                time.sleep(0.01)#Gives a nice transition
        return True

    def set_keys_on(self):
        for k,v in self.leds.items():
            if k != "credit":
                v.value = False
                time.sleep(0.01)#Gives a nice transition
        return True

    def set_key_on(self,key):
        self.leds[key].value = False

    def set_key_off(self,key):
        self.leds[key].value = True

    def toggle_key(self,key):
        if self.leds[key].value == True:
            self.leds[key].value = False
        elif self.leds[key].value == False:
            self.leds[key].value = True

    def set_credit_light_off(self):
        self.leds["credit"].value = True
        return True

    def set_credit_light_on(self):
        self.leds["credit"].value = False
        return True

    def get_credit_light(self):
        return self.leds["credit"].value

    def get_keypress(self):
        for k,v in self.buttons.items():  
            if v.value == False:
                    return k
        return False

    async def get_key_combination(self):
        #Keypad poller
        while True:
            # Get keypress and check if it is a letter
            l = self.get_keypress()
            if l != False:
                if l.isalpha():
                    logging.info("Matched Alpha Character: " + l)
                    #Toggle backlight on chosen letter
                    self.toggle_key(l)
                    #Wait 5 seconds for user to input number, if nothing entered, disregard and go back round the main loop
                    t_end = time.time() + 5
                    while time.time() < t_end:
                        # Get keypress and chck if it is a digit
                        n = self.get_keypress()
                        if n != False:
                            if n.isdigit():
                                logging.info("Matched Digit: " + n)
                                # Digit selected. Toggle backlight on chosen letter
                                self.toggle_key(n)
                                # Sample code, wait 1 second then turn all backlights off
                                await asyncio.sleep(1)
                                self.set_keys_off()
                                # Break out of parent loop
                                t_end = 0
                                logging.debug("Put key combination " + l + n + " on asyncio queue")
                                self.queue.put_nowait(l + n)
                        await asyncio.sleep(0.1)
                    logging.info("Timeout waiting for digit")
                    self.set_keys_off()
            await asyncio.sleep(0.1)
