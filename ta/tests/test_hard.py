from ta_radio_433 import Radio433
from ta_logger import get_logger
import ta_config as config

cfg = {
  "UART_INDEX": config.HARDWARE["UART_RADIO"]["INDEX"],
  "TX": config.HARDWARE["UART_RADIO"]["TX"],
  "RX": config.HARDWARE["UART_RADIO"]["RX"],
  "PIN_GT38_SET": config.HARDWARE["UART_RADIO"]["PIN_GT38_SET"],
  "TIMEOUT_MS": 800, "SIMULATE": False
}
r = Radio433(cfg, get_logger())
print('HW OK?', r.check_hardware())
print('PING OK?', r.ping())  # envoie POLL:01 et regarde si "quelque chose" revient
