from machine import UART, Pin
u = UART(2, 9600, tx=Pin(17), rx=Pin(18), timeout=300)  # si pas de réponse, essaie 2400/4800/19200
u.write(b'AT\n')
print(u.read())         # attendu: b'OK'
u.write(b'AT+RX\n')     # certains firmwares répondent OK (test basique)
u.write(b'AT+B9600\n')  # baud = 9600
u.write(b'AT+FU3\n')    # mode transparent standard
u.write(b'AT+C001\n')   # canal 001 (adapter si tu en utilises un autre)
u.write(b'AT+SLEEP\n')  # selon firmware, sinon ignorer
