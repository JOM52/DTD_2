# ==================== TEST RADIO TA (Corrigé) ====================
# test_radio_ta_fixed.py
from machine import UART, Pin
import time

# Config TA
UART_PORT = 2
TX = 17
RX = 18
SET = 43  # Pin corrigée

print("=== TEST RADIO TA (v2) ===")

# Init pin SET
pin_set = Pin(SET, Pin.OUT)
pin_set.value(1)
print("SET (GPIO{}) = HIGH (mode RUN)".format(SET))
time.sleep_ms(200)

# Init UART
uart = UART(UART_PORT, baudrate=9600, tx=Pin(TX), rx=Pin(RX), timeout=100)
print("UART2 initialisé")

# IMPORTANT : Vider buffer initial (contient garbage)
time.sleep_ms(500)
while uart.any():
    trash = uart.read(uart.any())
    print("Buffer initial vidé: {}".format(trash))

print("\n" + "="*60)

# Test 1 : Émission
print("1. Test émission (10 messages)")
for i in range(10):
    msg = "TEST:{}\n".format(i)
    uart.write(msg.encode())
    print("→ Envoyé: {}".format(msg.strip()))
    time.sleep_ms(500)

print("\n" + "="*60)

# Test 2 : Réception
print("2. Test réception (écoute 10s)")
t0 = time.ticks_ms()
recv_count = 0

while time.ticks_diff(time.ticks_ms(), t0) < 10000:
    if uart.any():
        data = uart.read(uart.any())
        print("← Reçu: {}".format(data))
        recv_count += 1
    time.sleep_ms(100)

print("\nMessages reçus: {}".format(recv_count))

print("\n" + "="*60)

# Test 3 : POLL avec timeout
print("3. Test POLL:01")

# Vider buffer avant test
while uart.any():
    uart.read(uart.any())

uart.write(b"POLL:01\n")
print("→ POLL:01 envoyé")

t0 = time.ticks_ms()
while time.ticks_diff(time.ticks_ms(), t0) < 2000:
    if uart.any():
        resp = uart.read(uart.any())
        print("← Réponse: {}".format(resp))
        
        # Parser
        try:
            text = resp.decode('utf-8', 'ignore').strip()
            if text.startswith("ACK:"):
                parts = text.split(":")
                print("✓ ACK parsé: ID={}, State={}".format(parts[1], parts[2]))
                break
        except:
            pass
    time.sleep_ms(10)
else:
    print("✗ Timeout POLL:01")

print("\n=== FIN TEST ===")


