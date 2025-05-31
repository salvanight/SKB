import time # Added for sleeps in hotkey, press, write
import os # Added for environment variable
from .ino_rs import ArduinoComm, ArduinoCommError # New import

# Default COM port
DEFAULT_ARDUINO_COM_PORT = "COM33"
# Get COM port from environment variable, or use default
arduino_com_port = os.environ.get("ARDUINO_COM_PORT", DEFAULT_ARDUINO_COM_PORT)

try:
    arduino_comm = ArduinoComm(arduino_com_port)
    if arduino_com_port == DEFAULT_ARDUINO_COM_PORT and "ARDUINO_COM_PORT" not in os.environ:
        print(f"Warning: Using default Arduino COM port '{DEFAULT_ARDUINO_COM_PORT}'. Set ARDUINO_COM_PORT environment variable to override.")
    print(f"Attempting to use Arduino on COM port: {arduino_com_port} for keyboard")
except ArduinoCommError as e:
    print(f"Failed to initialize Arduino communication on port {arduino_com_port} for keyboard: {e}")
    arduino_comm = None

def getAsciiFromKey(key):
    if not key:
        return 0

    sanitized = key.lower()

    if sanitized == '?':
        return 63

    if sanitized.isalpha() and len(sanitized) == 1:
        return ord(sanitized)
    
    if sanitized == 'space':
        return 32
    elif sanitized == 'esc':
        return 177
    elif sanitized == 'ctrl':
        return 128
    elif sanitized == 'alt':
        return 130
    elif sanitized == 'shift':
        return 129
    elif sanitized == 'enter':
        return 176
    elif sanitized == 'up':
        return 218
    elif sanitized == 'down':
        return 217
    elif sanitized == 'left':
        return 216
    elif sanitized == 'right':
        return 215
    elif sanitized == 'backspace':
        return 178
    elif sanitized == 'f1':
        return 194
    elif sanitized == 'f2':
        return 195
    elif sanitized == 'f3':
        return 196
    elif sanitized == 'f4':
        return 197
    elif sanitized == 'f5':
        return 198
    elif sanitized == 'f6':
        return 199
    elif sanitized == 'f7':
        return 200
    elif sanitized == 'f8':
        return 201
    elif sanitized == 'f9':
        return 202
    elif sanitized == 'f10':
        return 203
    elif sanitized == 'f11':
        return 204
    elif sanitized == 'f12':
        return 205
    else:
        return 0

def hotkey(*args, interval: float = 0.01): # Added interval based on original ino.py
    if not arduino_comm:
        print("Arduino communication not initialized for keyboard (hotkey).")
        return
    
    try:
        for key in args:
            asciiKey = getAsciiFromKey(key)
            if asciiKey != 0:
                raw_command_down = f"keyDown,{asciiKey}"
                arduino_comm.send(raw_command_down)
        
        time.sleep(interval) # Sleep between all downs and all ups

        for key in args:
            asciiKey = getAsciiFromKey(key)
            if asciiKey != 0:
                raw_command_up = f"keyUp,{asciiKey}"
                arduino_comm.send(raw_command_up)
    except ArduinoCommError as e:
        print(f"Error sending hotkey command: {e}")


def keyDown(key: str):
    if not arduino_comm:
        print("Arduino communication not initialized for keyboard (keyDown).")
        return
        
    asciiKey = getAsciiFromKey(key)
    if asciiKey != 0:
        raw_command = f"keyDown,{asciiKey}"
        try:
            arduino_comm.send(raw_command)
        except ArduinoCommError as e:
            print(f"Error sending keyDown command: {e}")

def keyUp(key: str):
    if not arduino_comm:
        print("Arduino communication not initialized for keyboard (keyUp).")
        return

    asciiKey = getAsciiFromKey(key)
    if asciiKey != 0:
        raw_command = f"keyUp,{asciiKey}"
        try:
            arduino_comm.send(raw_command)
        except ArduinoCommError as e:
            print(f"Error sending keyUp command: {e}")

def press(*args, duration: float = 0.05): # Added duration based on original ino.py
    if not arduino_comm:
        print("Arduino communication not initialized for keyboard (press).")
        return

    try:
        for key in args:
            asciiKey = getAsciiFromKey(key)
            if asciiKey != 0:
                raw_command = f"press,{asciiKey}"
                arduino_comm.send(raw_command)
                # The sleep for 'press' in original ino.py was after arduinoSerial.write()
                # and specific to each key press in the loop.
                time.sleep(duration) 
    except ArduinoCommError as e:
        print(f"Error sending press command: {e}")

def write(phrase: str, delayBetweenPresses: float = 0.01): # Added delay based on original ino.py
    if not arduino_comm:
        print("Arduino communication not initialized for keyboard (write).")
        return

    raw_command = f"write,{phrase}"
    try:
        arduino_comm.send(raw_command)
        # The sleep for 'write' in original ino.py was after arduinoSerial.write()
        time.sleep(delayBetweenPresses * len(phrase)) 
    except ArduinoCommError as e:
        print(f"Error sending write command: {e}")
