from machine import UART, Pin
u = UART(2, baudrate=9600, tx=Pin(17), rx=Pin(18), timeout=200)
u.write(b'PING\r\n')
import time; time.sleep_ms(50)
print('any=', u.any(), 'read=', u.read())
