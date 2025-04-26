import time
import machine
import neopixel
import network
import socket
from machine import Pin, I2C, PWM, UART
import sys

# ---- Setup Stepper Motor (A4988 Driver) ----
dir_pin = Pin(18, Pin.OUT)   # Direction pin
step_pin = Pin(19, Pin.OUT)  # Step pin

# ---- Setup Neopixel ----
NUM_PIXELS = 16
np = neopixel.NeoPixel(Pin(5), NUM_PIXELS)

# ---- Setup DFPlayer Mini ----
uart = UART(2, baudrate=9600, tx=17, rx=16)  # Adjust pins
busy_pin = Pin(34, Pin.IN)

# ---- Setup I2C LCD ----
i2c = I2C(0, scl=Pin(22), sda=Pin(21), freq=400000)

import i2c_lcd
lcd = i2c_lcd.I2cLcd(i2c, 0x27, 2, 16)

# ---- Setup WiFi ----
ssid = 'YOUR_SSID'
password = 'YOUR_PASSWORD'

playlist = 'pop'  # Default playlist
current_song = 1

# ---- Connect WiFi ----
def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(ssid, password)
    while not wlan.isconnected():
        time.sleep(1)
    print('Connected:', wlan.ifconfig())
    return wlan.ifconfig()[0]

# ---- Simple Web Server ----
def start_server(ip):
    s = socket.socket()
    s.bind((ip, 80))
    s.listen(1)
    return s

def web_page():
    html = """<html><head><title>Lotus Jukebox</title></head>
    <body><h1>Choose Playlist:</h1>
    <a href="/pop"><button>Pop</button></a>
    <a href="/rap"><button>Rap</button></a>
    <a href="/edm"><button>EDM</button></a>
    </body></html>"""
    return html

# ---- Control DFPlayer Mini ----
def play_song(song_num):
    uart.write(b'\x7E\xFF\x06\x03\x00\x00' + bytes([song_num]) + b'\xEF')

def set_folder(folder_num):
    uart.write(b'\x7E\xFF\x06\x17\x00\x00' + bytes([folder_num]) + b'\xEF')

def next_song():
    uart.write(b'\x7E\xFF\x06\x01\x00\x00\x00\xEF')

# ---- Stepper Motor Movement ----
def bloom():
    dir_pin.value(1)  # Set direction to open
    for _ in range(200):
        step_pin.value(1)
        time.sleep_us(800)
        step_pin.value(0)
        time.sleep_us(800)

def unbloom():
    dir_pin.value(0)  # Set direction to close
    for _ in range(200):
        step_pin.value(1)
        time.sleep_us(800)
        step_pin.value(0)
        time.sleep_us(800)

# ---- Neopixel Breathing Rainbow ----
def wheel(pos):
    if pos < 85:
        return (pos * 3, 255 - pos*3, 0)
    elif pos < 170:
        pos -= 85
        return (255 - pos*3, 0, pos*3)
    else:
        pos -= 170
        return (0, pos*3, 255 - pos*3)

def breathe(direction):
    # direction = 1 for red->violet, -1 for violet->red
    steps = 256
    for i in range(steps):
        color_pos = (i if direction == 1 else 255 - i)
        color = wheel(color_pos % 256)
        for p in range(NUM_PIXELS):
            np[p] = color
        np.write()
        brightness = (1 + math.sin(i/40)) * 0.5  # breathing
        scaled = tuple(int(c * brightness) for c in color)
        for p in range(NUM_PIXELS):
            np[p] = scaled
        np.write()
        time.sleep(0.02)

# ---- Main Loop ----
def main():
    ip = connect_wifi()
    server = start_server(ip)
    lcd.clear()
    lcd.putstr("Ready to Bloom!")

    global playlist, current_song

    while True:
        # Bloom
        lcd.clear()
        lcd.putstr("Now Playing...")
        bloom()
        breathe(1)

        # Unbloom
        unbloom()
        breathe(-1)

        # Music Control
        if uart.any():
            uart.read()

        if busy_pin.value() == 1:  # If not busy, play next
            next_song()

        # Check Webserver
        conn, addr = server.accept()
        request = conn.recv(1024)
        request = str(request)
        if '/pop' in request:
            playlist = 'pop'
            set_folder(1)
            play_song(1)
            current_song = 1
        elif '/rap' in request:
            playlist = 'rap'
            set_folder(2)
            play_song(1)
            current_song = 1
        elif '/edm' in request:
            playlist = 'edm'
            set_folder(3)
            play_song(1)
            current_song = 1

        response = web_page()
        conn.send('HTTP/1.1 200 OK\n')
        conn.send('Content-Type: text/html\n')
        conn.send('Connection: close\n\n')
        conn.sendall(response)
        conn.close()

# ---- Run ----
try:
    main()
except KeyboardInterrupt:
    sys.exit()
