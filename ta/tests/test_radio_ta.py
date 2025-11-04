# test_radio_ta.py - Test communication TA
from machine import UART, Pin
import time

# Config TA
UART_PORT = 2
TX = 17
RX = 18
SET = 4

print("=== TEST RADIO TA ===")

# Init pin SET
pin_set = Pin(SET, Pin.OUT)
pin_set.value(1)
print("SET = HIGH (mode RUN)")

# Init UART
uart = UART(UART_PORT, baudrate=9600, tx=Pin(TX), rx=Pin(RX), timeout=100)
print("UART2 initialisé")

# Vider buffer
while uart.any():
    uart.read(uart.any())

# Test 1 : Émission continue
print("\n1. Test émission (10 messages)")
for i in range(10):
    msg = "TEST:{}\n".format(i)
    uart.write(msg.encode())
    print("→ Envoyé: {}".format(msg.strip()))
    time.sleep_ms(500)

# Test 2 : Écoute
print("\n2. Test réception (écoute 10s)")
t0 = time.ticks_ms()
recv_count = 0

while time.ticks_diff(time.ticks_ms(), t0) < 10000:
    if uart.any():
        data = uart.read(uart.any())
        print("← Reçu: {}".format(data))
        recv_count += 1
    time.sleep_ms(100)

print("\nMessages reçus: {}".format(recv_count))

# Test 3 : POLL avec timeout
print("\n3. Test POLL:01")
uart.write(b"POLL:01\n")
print("→ POLL:01 envoyé")

t0 = time.ticks_ms()
while time.ticks_diff(time.ticks_ms(), t0) < 2000:
    if uart.any():
        resp = uart.read(uart.any())
        print("← Réponse: {}".format(resp))
        break
    time.sleep_ms(10)
else:
    print("✗ Timeout POLL:01")

print("\n=== FIN TEST ===")