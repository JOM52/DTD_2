# ta_radio_433.py - Module radio 433MHz pour GT38 (v2.4.0 - RX robuste + mutex + retries)
# Version : 2.4.0 - Améliore la fiabilité UART (timeout cohérents config, lecture par ligne,
#                   mutex pour appels concurrents, retries exponentiels, validations strictes)

from machine import Pin, UART
import time

try:
    import uasyncio as asyncio
except ImportError:
    import asyncio

import ta_config as config

class Radio433:
    """Gestion communication radio 433MHz via GT38, protocole texte simple.
    Requête:  b"POLL:{id}\n"
    Réponse:  b"ACK:{id}:{0|1}\n"
    """
    ACK_PREFIX = b"ACK:"
    EOL = b"\n"

    def __init__(self, radio_config, logger):
        self.config = radio_config
        self.logger = logger
        self.simulate = radio_config.get("SIMULATE", False)

        # Statistiques
        self.stats = {
            "tx_count": 0,
            "rx_count": 0,
            "timeout_count": 0,
            "error_count": 0,
            "uart_errors": 0,
            "blocked_calls": 0
        }

        # UART / HW
        self.uart = None
        self.pin_set = None
        self.uart_config = None
        self.uart_broken = False

        # Mutex pour empêcher 2 polls concurrents sur l'UART
        try:
            self._lock = asyncio.Lock()
        except Exception:
            class _Dummy:
                async def __aenter__(self_s): return None
                async def __aexit__(self_s, *a): return False
            self._lock = _Dummy()

        # Buffer de réception (conserve les restes de trame incomplète)
        self._rx_buf = bytearray()

        if not self.simulate:
            self._init_hardware()

    # ---------------------
    # Hardware
    # ---------------------
    def _init_hardware(self):
        try:
            self.uart_config = config.HARDWARE["UART_RADIO"]
            uart_index = self.uart_config.get("INDEX", 2)
            baud = self.uart_config.get("BAUD", 9600)
            tx_pin = self.uart_config.get("TX", 17)
            rx_pin = self.uart_config.get("RX", 18)
            uart_timeout_ms = int(self.uart_config.get("TIMEOUT_MS", 100))

            # Pin SET (si câblée)
            set_pin_num = self.uart_config.get("PIN_GT38_SET")
            if set_pin_num is not None:
                try:
                    self.pin_set = Pin(set_pin_num, Pin.OUT)
                    self.pin_set.value(0); time.sleep_ms(30)
                    self.pin_set.value(1); time.sleep_ms(30)
                    self.logger.debug("Pin SET (GPIO{}) initialisée".format(set_pin_num), "radio")
                except Exception as e:
                    self.logger.warning("SET pin non utilisée: {}".format(e), "radio")

            # RX buffer plus grand pour éviter les pertes
            self.uart = UART(
                uart_index,
                baudrate=baud,
                tx=Pin(tx_pin),
                rx=Pin(rx_pin),
                timeout=uart_timeout_ms,   # timeout lecture (ms)
                rxbuf=1024
            )
            self.logger.info("UART{} {} bauds prêt (TX={} RX={})".format(uart_index, baud, tx_pin, rx_pin), "radio")

            # Purge initiale
            self._drain_input(max_cycles=25)

            self.uart_broken = False
            self.logger.info("✓ Hardware radio OK", "radio")
        except Exception as e:
            self.logger.error("Erreur init hardware: {}".format(e), "radio")
            self.uart_broken = True

    def _drain_input(self, max_cycles=10):
        """Vide l'input UART (synchrone, court)."""
        if not self.uart: return
        try:
            for _ in range(max_cycles):
                n = self.uart.any()
                if not n: break
                _ = self.uart.read(n or 1)
                time.sleep_ms(2)
        except Exception:
            self.stats["uart_errors"] += 1

    # ---------------------
    # Helpers async UART
    # ---------------------
    async def _uart_any(self):
        if not self.uart or self.uart_broken:
            return -1
        try:
            await asyncio.sleep_ms(0)
            n = self.uart.any()
            await asyncio.sleep_ms(0)
            return n or 0
        except Exception:
            self.stats["uart_errors"] += 1
            return -1

    async def _uart_read(self, n):
        if not self.uart or self.uart_broken:
            return b""
        try:
            await asyncio.sleep_ms(0)
            data = self.uart.read(n)
            await asyncio.sleep_ms(0)
            return data or b""
        except Exception:
            self.stats["uart_errors"] += 1
            return b""

    async def _uart_write(self, data: bytes) -> int:
        if not self.uart or self.uart_broken:
            return 0
        try:
            await asyncio.sleep_ms(0)
            w = self.uart.write(data)
            await asyncio.sleep_ms(0)
            return int(w or 0)
        except Exception:
            self.stats["uart_errors"] += 1
            return 0

    async def _readline(self, timeout_ms: int) -> bytes:
        """Lit jusqu'à EOL ou timeout; concatène avec _rx_buf; renvoie une ligne complète si dispo.
        Conserve le reste dans _rx_buf si plusieurs lignes arrivent.
        """
        deadline = time.ticks_add(time.ticks_ms(), timeout_ms)
        while time.ticks_diff(deadline, time.ticks_ms()) > 0:
            idx = self._rx_buf.find(self.EOL)
            if idx >= 0:
                line = bytes(self._rx_buf[:idx])
                self._rx_buf = self._rx_buf[idx+1:]
                return line

            n = await self._uart_any()
            if n > 0:
                chunk = await self._uart_read(n)
                if chunk:
                    chunk = chunk.replace(b"\r", b"")
                    self._rx_buf.extend(chunk)
                    continue

            await asyncio.sleep_ms(5)

        idx = self._rx_buf.find(self.EOL)
        if idx >= 0:
            line = bytes(self._rx_buf[:idx])
            self._rx_buf = self._rx_buf[idx+1:]
            return line
        return b""

    # ---------------------
    # API publique
    # ---------------------
    def check_hardware(self):
        if self.simulate:
            self.logger.info("Mode simulation", "radio")
            return True
        return not self.uart_broken

    def get_statistics(self):
        return dict(self.stats)

    async def poll(self, detector_id: str):
        if self.simulate:
            await asyncio.sleep_ms(30)
            import random
            return {"detector_id": detector_id, "state": random.choice([0,1]), "simulated": True}

        if self.uart_broken:
            return None

        reply_timeout = int(self.config.get("REPLY_TIMEOUT_MS", 400))
        retries = int(self.config.get("RETRY", {}).get("MAX_RETRIES", 3))
        base = float(self.config.get("RETRY", {}).get("TIMEOUT_BASE_MS", 400))
        mult = float(self.config.get("RETRY", {}).get("TIMEOUT_MULTIPLIER", 1.5))

        cmd = "POLL:{}\n".format(detector_id).encode()

        async with self._lock:
            self._drain_input(max_cycles=10)
            self._rx_buf.clear()

            delay_ms = 0.0
            for attempt in range(retries + 1):
                if delay_ms:
                    await asyncio.sleep_ms(int(delay_ms))
                written = await self._uart_write(cmd)
                if not written:
                    self.stats["uart_errors"] += 1
                    continue
                self.stats["tx_count"] += 1
                self.logger.debug("→ {}".format(cmd.decode().strip()), "radio")

                deadline = time.ticks_add(time.ticks_ms(), reply_timeout)
                while time.ticks_diff(deadline, time.ticks_ms()) > 0:
                    line = await self._readline(timeout_ms=reply_timeout)
                    if not line:
                        await asyncio.sleep_ms(5)
                        continue
                    try:
                        if not line.startswith(self.ACK_PREFIX):
                            self.logger.debug("← (bruit) {}".format(line), "radio")
                            continue
                        parts = line.decode("utf-8", "ignore").strip().split(":")
                        if len(parts) < 3:
                            continue
                        resp_id, state_txt = parts[1].strip(), parts[2].strip()
                        if resp_id != str(detector_id):
                            continue
                        state = 1 if (state_txt.isdigit() and int(state_txt) == 1) else 0
                        self.stats["rx_count"] += 1
                        self.logger.debug("← ACK:{}:{}".format(resp_id, state), "radio")
                        return {"detector_id": resp_id, "state": state, "simulated": False}
                    except Exception:
                        self.stats["error_count"] += 1
                        # continuer jusqu'au deadline

                self.stats["timeout_count"] += 1
                delay_ms = max(base, base * (mult ** attempt))

            return None

    async def poll_status(self):
        class _DDStatus:
            def __init__(self, dd_id, state): self.dd_id, self.state = dd_id, state
        results = []
        for dd_id in config.RADIO["GROUP_IDS"]:
            res = await self.poll("{:02d}".format(dd_id))
            if res is None:
                results.append(_DDStatus(dd_id, config.RADIO.get("STATE_UNKNOWN", 2)))
            else:
                state = config.RADIO.get("STATE_PRESENT", 1) if res["state"] == 1 else config.RADIO.get("STATE_ABSENT", 0)
                results.append(_DDStatus(dd_id, state))
            await asyncio.sleep_ms(0)
        return results

    async def request_status(self, dd_id):
        return await self.poll("{:02d}".format(dd_id))
