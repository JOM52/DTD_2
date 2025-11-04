"""
Script de test DIRECT TA → DD
Lance manuellement des commandes POLL pour diagnostiquer
"""

from machine import Pin, UART
import time

print("\n" + "="*60)
print("TEST DIRECT TA → DD")
print("="*60)

# Configuration TA
UART_PORT = 2
TX_PIN = 17
RX_PIN = 18
SET_PIN = 43

print("\nConfiguration TA:")
print(f"  UART: UART{UART_PORT}")
print(f"  TX: GPIO{TX_PIN}")
print(f"  RX: GPIO{RX_PIN}")
print(f"  SET: GPIO{SET_PIN}")

# Init pin SET
pin_set = Pin(SET_PIN, Pin.OUT)
pin_set.value(1)  # Mode RUN
print(f"\nSET = HIGH (mode RUN)")

# Init UART
uart = UART(UART_PORT, baudrate=9600, tx=Pin(TX_PIN), rx=Pin(RX_PIN), timeout=100)
print(f"UART{UART_PORT} initialisé (9600 bauds)")

time.sleep_ms(500)

print("\n" + "-"*60)
print("TEST 1: Envoi POLL:01")
print("-"*60)

for test_num in range(5):
    print(f"\n[Test {test_num + 1}/5]")
    
    # Vider buffer
    while uart.any():
        uart.read()
    
    # Envoyer POLL:01
    cmd = "POLL:01\n"
    written = uart.write(cmd.encode())
    print(f"→ Envoyé: {cmd.strip()} ({written} octets)")
    
    # Attendre réponse
    timeout_start = time.ticks_ms()
    timeout_ms = 2000  # 2 secondes
    received = False
    
    while time.ticks_diff(time.ticks_ms(), timeout_start) < timeout_ms:
        if uart.any():
            data = uart.read()
            try:
                response = data.decode('utf-8', 'ignore').strip()
                print(f"← Reçu: {response}")
                received = True
                break
            except:
                print(f"← Reçu (raw): {data}")
                received = True
                break
        time.sleep_ms(10)
    
    if not received:
        print("✗ Timeout - Pas de réponse")
    else:
        print("✓ Réponse reçue !")
    
    time.sleep_ms(1000)

print("\n" + "-"*60)
print("TEST 2: Envoi continu pendant 10s")
print("-"*60)

start_time = time.ticks_ms()
tx_count = 0
rx_count = 0

while time.ticks_diff(time.ticks_ms(), start_time) < 10000:
    # Envoyer POLL
    uart.write(b"POLL:01\n")
    tx_count += 1
    
    # Attendre un peu
    time.sleep_ms(100)
    
    # Lire réponses
    if uart.any():
        data = uart.read()
        rx_count += 1
        try:
            response = data.decode('utf-8', 'ignore').strip()
            print(f"← [{rx_count}] {response}")
        except:
            pass
    
    time.sleep_ms(1500)

print(f"\nRésultat:")
print(f"  TX: {tx_count} commandes envoyées")
print(f"  RX: {rx_count} réponses reçues")
print(f"  Taux: {rx_count/tx_count*100:.1f}%")

print("\n" + "="*60)
print("TEST TERMINÉ")
print("="*60)

if rx_count == 0:
    print("\n⚠️  AUCUNE RÉPONSE REÇUE")
    print("\nVérifications à faire:")
    print("  1. Le DD est-il allumé et lancé ?")
    print("  2. Les GT38 sont-ils sur le même canal ?")
    print("  3. La portée est-elle suffisante ?")
    print("  4. Les antennes sont-elles bien positionnées ?")
elif rx_count < tx_count:
    print(f"\n⚠️  {tx_count - rx_count} réponses manquantes")
    print("\nProblèmes possibles:")
    print("  - Portée limite")
    print("  - Interférences")
else:
    print("\n✓ Communication parfaite !")

print()