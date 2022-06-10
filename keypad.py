import board
import busio
import digitalio
from adafruit_mcp230xx.mcp23017 import MCP23017
import pin_mappings
import time

class Keypad:

    buttons = {}
    leds = {}

    def __init__(self):
        i2c = busio.I2C(board.SCL, board.SDA)
        left = MCP23017(i2c, address=0x25) #Leftmost port expander
        middle = MCP23017(i2c, address=0x22) #Middle port expander
        right = MCP23017(i2c, address=0x20) #Rightmost port expander

        #Set up input pins
        for k, v in pin_mappings.keymap_left.items():
            pin = left.get_pin(k)
            pin.direction = digitalio.Direction.INPUT
            pin.pull = digitalio.Pull.UP
            self.buttons[v] = pin
        for k, v in pin_mappings.keymap_middle.items():
            pin = middle.get_pin(k)
            pin.direction = digitalio.Direction.INPUT
            pin.pull = digitalio.Pull.UP
            self.buttons[v] = pin
        for k, v in pin_mappings.keymap_right.items():
            pin = right.get_pin(k)
            pin.direction = digitalio.Direction.INPUT
            pin.pull = digitalio.Pull.UP
            self.buttons[v] = pin

        # Set up LED's
        for k, v in pin_mappings.ledmap_left.items():
            pin = left.get_pin(k)
            pin.direction = digitalio.Direction.OUTPUT
            pin.pull = digitalio.Pull.UP
            pin.value = True
            self.leds[v] = pin
        for k, v in pin_mappings.ledmap_middle.items():
            pin = middle.get_pin(k)
            pin.direction = digitalio.Direction.OUTPUT
            pin.pull = digitalio.Pull.UP
            pin.value = True
            self.leds[v] = pin
        for k, v in pin_mappings.ledmap_right.items():
            pin = right.get_pin(k)
            pin.direction = digitalio.Direction.OUTPUT
            pin.pull = digitalio.Pull.UP
            pin.value = True
            self.leds[v] = pin

    def setKeysOff(self):
        for k,v in self.leds.items():
            if k != "credit":
                v.value = True
                time.sleep(0.01)#Gives a nice transition
        return True

    def setKeysOn(self):
        for k,v in self.leds.items():
            if k != "credit":
                v.value = False
                time.sleep(0.01)#Gives a nice transition
        return True

    def setKeyOn(self,key):
        self.leds["key"].value = False

    def setKeyOff(self,key):
        self.leds["key"].value = True

    def toggleKey(self,key):
        if self.leds[key].value == True:
            self.leds[key].value = False
        elif self.leds[key].value == False:
            self.leds[key].value = True

    def setCreditOff(self):
        self.leds["credit"].value = True
        return True

    def setCreditOn(self):
        self.leds["credit"].value = False
        return True

    def getKeypress(self):
        for k,v in self.buttons.items():  
            if v.value == False:
                    return k
        return False

keypad = Keypad()

#Sample logic, move to function
while True:
    # Get keypress and check if it is a letter
    l = keypad.getKeypress()
    if l != False:
        if l.isalpha():
            #Toggle backlight on chosen letter
            keypad.toggleKey(l)
            #Wait 5 seconds for user to input number, if nothing entered, disregard and go back round the main loop
            t_end = time.time() + 5
            while time.time() < t_end:
                # Get keypress and chck if it is a digit
                n = keypad.getKeypress()
                if n != False:
                    if n.isdigit():
                        # Digit selected. Toggle backlight on chosen letter
                        keypad.toggleKey(n)
                        print(l + n + " selected")
                        # Sample code, wait 1 second then turn all backlights off
                        time.sleep(1)
                        keypad.setKeysOff()
                time.sleep(0.1)
            keypad.setKeysOff()
    time.sleep(0.1)
