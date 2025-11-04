# dd_main.py - Détecteur Distant (DD) pour ESP32 + GT38 (MicroPython)
# Version : 1.6.1 - Debug parse errors
# Changelog v1.6.1:
#   - Logging détaillé des parse errors
#   - Affichage des 10 derniers messages non parsés
#   - Détection trames fragmentées
#   - Stats améliorées

from machine import Pin, UART, Timer, reset
import time

# ============================ CONFIG ============================
UART_PORT = 1
UART_BAUD = 9600
UART_TX_PIN = 17
UART_RX_PIN = 16
GT38_SET_PIN = 5
LED_PIN = 2

WATCHDOG_ENABLED = False
WATCHDOG_MS = 30000
DEV_MODE = True

LOOP_DELAY_MS = 50
LED_BLINK_MS = 20

# ====================== ID UNIQUE DU DETECTEUR ==================
def _get_id_from_config():
    try:
        import config
        did = getattr(config, "DETECTOR_ID", None)
        if isinstance(did, str) and 1 <= len(did) <= 8:
            return did
    except Exception:
        pass
    return None

def _get_id_from_nvs():
    try:
        import esp32
        n = esp32.NVS("dd")
        b = bytearray(8)
        ln = n.get_blob("id", b)
        if ln and ln > 0:
            return b[:ln].decode()
    except Exception:
        pass
    return None

def _get_id_from_straps():
    try:
        pA = Pin(18, Pin.IN, Pin.PULL_UP)
        pB = Pin(19, Pin.IN, Pin.PULL_UP)
        pC = Pin(21, Pin.IN, Pin.PULL_UP)
        bit0 = 0 if pA.value() == 0 else 1
        bit1 = 0 if pB.value() == 0 else 1
        bit2 = 0 if pC.value() == 0 else 1
        val = (bit2 << 2) | (bit1 << 1) | (bit0 << 0)
        mapping = {1: "01", 2: "02", 3: "03", 4: "04", 5: "05"}
        return mapping.get(val, None)
    except Exception:
        return None

def _persist_id_to_nvs(new_id):
    try:
        import esp32
        n = esp32.NVS("dd")
        b = new_id.encode()
        n.set_blob("id", b)
        n.commit()
        return True
    except Exception:
        return False

DETECTOR_ID = (
    _get_id_from_config()
    or _get_id_from_nvs()
    or _get_id_from_straps()
    or "01"
)

# ======================== INITIALISATION ========================
print("[DD] Démarrage v1.6.1 (debug parse errors)")
print("[DD] ID: {}".format(DETECTOR_ID))

# LED
led = Pin(LED_PIN, Pin.OUT)
led_state = False
led_timer = 0

def led_pulse():
    global led_state, led_timer
    led_state = True
    led.value(1)
    led_timer = time.ticks_ms()

def led_update():
    global led_state, led_timer
    if led_state:
        if time.ticks_diff(time.ticks_ms(), led_timer) > LED_BLINK_MS:
            led.value(0)
            led_state = False

led.value(1)
time.sleep_ms(100)
led.value(0)

# Pin SET
print("[DD] Init pin SET (GPIO{})".format(GT38_SET_PIN))
try:
    gt38_set = Pin(GT38_SET_PIN, Pin.OUT)
    gt38_set.value(1)
    print("[DD] GT38 en mode RUN (SET=HIGH)")
except Exception as e:
    print("[DD] Erreur pin SET: {}".format(e))
    gt38_set = None

# UART
print("[DD] Init UART{} à {} bauds".format(UART_PORT, UART_BAUD))
try:
    uart = UART(
        UART_PORT, 
        baudrate=UART_BAUD, 
        tx=Pin(UART_TX_PIN), 
        rx=Pin(UART_RX_PIN),
        timeout=100,
        rxbuf=256
    )
    print("[DD] UART initialisé (timeout=100ms)")
except Exception as e:
    print("[DD] Erreur UART: {}".format(e))
    uart = UART(UART_PORT, baudrate=UART_BAUD, tx=Pin(UART_TX_PIN), rx=Pin(UART_RX_PIN))

# ========================== WATCHDOG ============================
last_loop_ts = time.ticks_ms()
_wdt_triggered = False
wdt_timer = None

def _blink_led(times, on_ms=80, off_ms=80):
    for _ in range(times):
        led.value(1)
        time.sleep_ms(on_ms)
        led.value(0)
        time.sleep_ms(off_ms)

def wdt_cb(t):
    global last_loop_ts, _wdt_triggered
    if _wdt_triggered:
        return
    if time.ticks_diff(time.ticks_ms(), last_loop_ts) > WATCHDOG_MS:
        _wdt_triggered = True
        print("[DD] WATCHDOG TIMEOUT - RESET")
        try:
            _blink_led(4, 80, 80)
        except Exception:
            pass
        reset()

if WATCHDOG_ENABLED and not DEV_MODE:
    try:
        wdt_timer = Timer(0)
        wdt_timer.init(period=max(100, WATCHDOG_MS // 2), mode=Timer.PERIODIC, callback=wdt_cb)
        print("[DD] Watchdog activé ({}s)".format(WATCHDOG_MS // 1000))
    except Exception as e:
        print("[DD] Erreur watchdog: {}".format(e))
        wdt_timer = None
else:
    if DEV_MODE:
        print("[DD] Mode DEV : Watchdog désactivé")

# ======================= OUTILS / PROTOCOLE =====================
def parse_line(line):
    """Parse une ligne de commande reçue"""
    try:
        s = line.decode().strip()
    except Exception:
        return None

    # ✓ NOUVEAU: Ignorer les ACK (echo de nos propres réponses ou des autres DD)
    if s.startswith("ACK:") or s.startswith("BOOT:") or s.startswith("ACKSETID:"):
        return ("IGNORE", None, None)  # Message à ignorer, pas une erreur

    if s.startswith("POLL:"):
        parts = s.split(":", 1)
        if len(parts) >= 2:
            return ("POLL", parts[1].strip(), None)
    
    if s.startswith("SETID:"):
        parts = s.split(":", 1)
        if len(parts) == 2:
            candidate = parts[1].strip()
            if 1 <= len(candidate) <= 8:
                return ("SETID", candidate, None)
    
    return None

def measure_state():
    return 1

def _uart_write_str(s):
    try:
        uart.write(s.encode())
        return True
    except Exception as e:
        if DEV_MODE:
            print("[DD] Erreur write: {}".format(e))
        return False

def flush_uart_rx():
    flushed = 0
    try:
        while uart.any():
            uart.read(1)
            flushed += 1
            if flushed > 100:
                break
    except Exception:
        pass
    return flushed

def send_ack(det_id, state):
    flush_uart_rx()
    msg = "ACK:{}:{}\n".format(det_id, 1 if state else 0)
    success = _uart_write_str(msg)
    if DEV_MODE and not success:
        print("[DD] Échec envoi ACK")
    return success

def send_ack_id_change(ok, new_id):
    flush_uart_rx()
    _uart_write_str("ACKSETID:{}:{}\n".format(new_id, "OK" if ok else "ERR"))

# ======================== STATISTIQUES ==========================
stats = {
    "loop_count": 0,
    "ok_count": 0,
    "nok_count": 0,
    "setid_ok": 0,
    "setid_err": 0,
    "uart_read_err": 0,
    "parse_err": 0,
    "last_poll_time": 0,
    "min_response_time": 9999,
    "max_response_time": 0,
    "avg_response_time": 0,
    # ✓ NOUVEAU: Tracking parse errors
    "parse_err_samples": [],  # 10 derniers messages non parsés
    "empty_lines": 0,
    "decode_errors": 0,
    "partial_messages": 0
}

def log_parse_error(line, reason="unknown"):
    """Log une erreur de parsing avec le message"""
    stats["parse_err"] += 1
    
    # Garder les 10 derniers
    if len(stats["parse_err_samples"]) >= 10:
        stats["parse_err_samples"].pop(0)
    
    try:
        # Essayer de décoder pour affichage
        try:
            msg = line.decode('utf-8', 'ignore')
        except:
            msg = str(line)
        
        stats["parse_err_samples"].append({
            "msg": msg[:50],  # Max 50 chars
            "len": len(line),
            "reason": reason
        })
    except:
        pass

def print_stats():
    """Affiche les statistiques"""
    print("[STATS] loop={} ok={} nok={} setid_ok={} setid_err={}".format(
        stats["loop_count"], stats["ok_count"], stats["nok_count"],
        stats["setid_ok"], stats["setid_err"]
    ))
    
    if stats["ok_count"] > 0:
        print("[STATS] response_time: min={}ms avg={}ms max={}ms".format(
            stats["min_response_time"],
            stats["avg_response_time"],
            stats["max_response_time"]
        ))
    
    if stats["parse_err"] > 0:
        print("[STATS] parse_errors: total={} empty={} decode={} partial={}".format(
            stats["parse_err"],
            stats["empty_lines"],
            stats["decode_errors"],
            stats["partial_messages"]
        ))
        
        # Afficher échantillons
        print("[STATS] Derniers parse errors:")
        for sample in stats["parse_err_samples"]:
            print("  [{}] len={} msg='{}'".format(
                sample["reason"],
                sample["len"],
                sample["msg"]
            ))

# ======================== BOUCLE PRINCIPALE =====================
buf = bytearray()

# Vider buffer au démarrage
time.sleep_ms(200)
flushed = flush_uart_rx()
if flushed > 0 and DEV_MODE:
    print("[DD] Buffer initial vidé: {} bytes".format(flushed))

# Message de boot
_uart_write_str("BOOT:{}\n".format(DETECTOR_ID))
print("[DD] Message BOOT envoyé")
led.value(0)

print("[DD] Boucle principale démarrée (délai {}ms)\n".format(LOOP_DELAY_MS))

while True:
    last_loop_ts = time.ticks_ms()
    stats["loop_count"] += 1
    led_update()

    # Lecture UART
    try:
        if uart.any():
            data = uart.read()
            if data:
                buf.extend(data)
                
                # Traiter toutes les lignes complètes
                while True:
                    nl = buf.find(b'\n')
                    if nl == -1:
                        break
                    
                    # Extraire ligne
                    line = bytes(buf[:nl + 1])
                    buf = bytearray(buf[nl + 1:])

                    # ✓ NOUVEAU: Vérifications détaillées
                    
                    # Ligne vide?
                    if len(line) <= 1:  # Juste '\n'
                        stats["empty_lines"] += 1
                        log_parse_error(line, "empty")
                        continue
                    
                    # Timestamp début traitement
                    process_start = time.ticks_ms()

                    # Essayer de parser
                    parsed = parse_line(line)
                    
                    if not parsed:
                        # Analyser pourquoi parsing a échoué
                        try:
                            s = line.decode('utf-8', 'ignore').strip()
                            
                            if len(s) == 0:
                                stats["empty_lines"] += 1
                                log_parse_error(line, "empty_after_decode")
                            elif len(s) < 5:
                                stats["partial_messages"] += 1
                                log_parse_error(line, "too_short")
                            elif not s.startswith(("POLL:", "SETID:", "ACK:", "BOOT:")):
                                log_parse_error(line, "unknown_prefix")
                            else:
                                log_parse_error(line, "malformed")
                        except Exception as e:
                            stats["decode_errors"] += 1
                            log_parse_error(line, "decode_error")
                        
                        continue

                    cmd, det_id, _ = parsed
                    
                    # ✓ NOUVEAU: Ignorer messages echo/broadcast
                    if cmd == "IGNORE":
                        continue  # Pas une erreur, juste à ignorer

                    if cmd == "POLL":
                        if det_id == DETECTOR_ID or det_id.upper() == "ALL":
                            state = measure_state()
                            success = send_ack(DETECTOR_ID, state)
                            
                            if success:
                                stats["ok_count"] += 1
                                
                                response_time = time.ticks_diff(time.ticks_ms(), process_start)
                                if response_time < stats["min_response_time"]:
                                    stats["min_response_time"] = response_time
                                if response_time > stats["max_response_time"]:
                                    stats["max_response_time"] = response_time
                                
                                stats["avg_response_time"] = (
                                    (stats["avg_response_time"] * (stats["ok_count"] - 1) + response_time)
                                    // stats["ok_count"]
                                )
                                
                                led_pulse()
                                
                                if DEV_MODE:
                                    print("[DD] POLL→ACK en {}ms".format(response_time))
                        else:
                            stats["nok_count"] += 1

                    elif cmd == "SETID":
                        new_id = det_id
                        ok = _persist_id_to_nvs(new_id)
                        
                        if ok:
                            DETECTOR_ID = new_id
                            stats["setid_ok"] += 1
                            print("[DD] ID changé: {}".format(new_id))
                            led_pulse()
                        else:
                            stats["setid_err"] += 1
                            print("[DD] Erreur changement ID")
                        
                        send_ack_id_change(ok, new_id)
                        
    except Exception as e:
        stats["uart_read_err"] += 1
        if DEV_MODE:
            print("[DD] Erreur boucle: {}".format(e))
                        
    # Stats toutes les 200 boucles
    if (stats["loop_count"] % 200) == 0:
        print_stats()

    time.sleep_ms(LOOP_DELAY_MS)