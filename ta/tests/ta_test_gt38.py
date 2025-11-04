from machine import UART, Pin
u = UART(2, 9600, tx=Pin(17), rx=Pin(18), timeout=200)
# Vide le buffer
while u.any(): u.read()
# Envoie une requête
u.write(b'POLL:01\n')
import time
t0 = time.ticks_ms()
buf = bytearray()
while time.ticks_diff(time.ticks_ms(), t0) < 1500:
    if u.any():
        buf.extend(u.read())
    time.sleep_ms(20)
print('RX=', bytes(buf))
