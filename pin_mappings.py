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