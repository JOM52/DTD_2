# ta_radio_433.py - Module radio 433MHz pour GT38 (v2.3.0 - Full Async)
# Version : 2.3.0 - Toutes les méthodes UART sont async pour éviter blocages

from machine import Pin, UART
import time

# Import asyncio
try:
    import uasyncio as asyncio
except ImportError:
    import asyncio

class Radio433:
    """Gestion communication radio 433MHz via GT38 - VERSION ASYNC"""
    
    def __init__(self, radio_config, logger):
        """
        Initialise le module radio
        
        Args:
            radio_config: Configuration radio complète (config.RADIO)
            logger: Instance du logger
        """
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
        
        # Hardware
        self.uart = None
        self.pin_set = None
        self.uart_config = None
        self.uart_broken = False
        
        if not self.simulate:
            self._init_hardware()
    
    def _init_hardware(self):
        """Initialise le hardware (UART + pin SET)"""
        import ta_config
        self.uart_config = ta_config.HARDWARE["UART_RADIO"]
        
        try:
            # Pin SET
            set_pin_num = self.uart_config.get("PIN_GT38_SET")
            if set_pin_num:
                self.pin_set = Pin(set_pin_num, Pin.OUT)
                self.pin_set.value(0)
                time.sleep_ms(50)
                self.pin_set.value(1)
                time.sleep_ms(50)
                self.logger.debug("Pin SET (GPIO{}) initialisée".format(set_pin_num), "radio")
            
            # UART avec timeout minimal
            uart_index = self.uart_config.get("INDEX", 2)
            tx_pin = self.uart_config.get("TX", 17)
            rx_pin = self.uart_config.get("RX", 18)
            
            self.uart = UART(
                uart_index,
                baudrate=9600,
                tx=Pin(tx_pin),
                rx=Pin(rx_pin),
                timeout=10,  # Timeout minimal
                rxbuf=256
            )
            
            self.logger.debug("UART{} initialisé".format(uart_index), "radio")
            
            time.sleep_ms(200)
            
            # Vider buffer
            try:
                while self.uart.any():
                    self.uart.read(1)
                    time.sleep_ms(1)
            except:
                pass
            
            self.uart_broken = False
            self.logger.info("✓ Hardware radio OK", "radio")
            
        except Exception as e:
            self.logger.error("Erreur init hardware: {}".format(e), "radio")
            self.uart_broken = True
            raise
    
    async def _async_uart_any(self):
        """Vérifie ASYNC s'il y a des données"""
        if not self.uart or self.uart_broken:
            return -1
        
        try:
            await asyncio.sleep_ms(0)
            result = self.uart.any()
            await asyncio.sleep_ms(0)
            return result if result is not None else 0
        except Exception as e:
            self.stats["uart_errors"] += 1
            return -1
    
    async def _async_uart_read(self, num_bytes):
        """Lecture ASYNC depuis l'UART"""
        if not self.uart or self.uart_broken:
            return None
        
        try:
            await asyncio.sleep_ms(0)
            data = self.uart.read(num_bytes)
            await asyncio.sleep_ms(0)
            return data
        except Exception as e:
            self.stats["uart_errors"] += 1
            return None
    
    async def _async_uart_write(self, data):
        """Écriture ASYNC vers l'UART"""
        if not self.uart or self.uart_broken:
            return 0
        
        try:
            await asyncio.sleep_ms(0)
            written = self.uart.write(data)
            await asyncio.sleep_ms(0)
            return written
        except Exception as e:
            self.stats["uart_errors"] += 1
            return 0
    
    def check_hardware(self):
        """Vérifie le module GT38"""
        if self.simulate:
            self.logger.info("Mode simulation", "radio")
            return True
        
        if self.uart_broken:
            return False
        
        self.logger.info("✓ GT38 opérationnel", "radio")
        return True
    
    async def poll(self, detector_id):
        """Interroge un détecteur (ASYNC)"""
        if self.simulate:
            await asyncio.sleep_ms(50)
            import random
            return {
                "detector_id": detector_id,
                "state": random.choice([0, 1]),
                "simulated": True
            }
        
        if self.uart_broken:
            return None
        
        try:
            # Vider buffer
            for _ in range(10):
                bytes_avail = await self._async_uart_any()
                if bytes_avail > 0:
                    await self._async_uart_read(bytes_avail)
                    await asyncio.sleep_ms(1)
                else:
                    break
            
            # Envoyer POLL
            cmd = "POLL:{}\n".format(detector_id)
            written = await self._async_uart_write(cmd.encode())
            
            if written > 0:
                self.stats["tx_count"] += 1
                self.logger.debug("→ {}".format(cmd.strip()), "radio")
            else:
                return None
            
            # Attendre réponse
            timeout_ms = 1000
            timeout_start = time.ticks_ms()
            response_buffer = bytearray()
            loop_count = 0
            
            while time.ticks_diff(time.ticks_ms(), timeout_start) < timeout_ms:
                loop_count += 1
                if loop_count > 100:
                    self.stats["blocked_calls"] += 1
                    break
                
                bytes_available = await self._async_uart_any()
                
                if bytes_available > 0:
                    data = await self._async_uart_read(bytes_available)
                    
                    if data:
                        response_buffer.extend(data)
                        
                        if b'\n' in response_buffer:
                            try:
                                response = response_buffer.decode('utf-8', 'ignore').strip()
                                self.logger.debug("← {}".format(response), "radio")
                                
                                if response.startswith("ACK:"):
                                    parts = response.split(":")
                                    if len(parts) >= 3:
                                        resp_id = parts[1]
                                        state = int(parts[2]) if parts[2].isdigit() else 0
                                        
                                        self.stats["rx_count"] += 1
                                        
                                        return {
                                            "detector_id": resp_id,
                                            "state": state,
                                            "simulated": False
                                        }
                            except:
                                pass
                
                await asyncio.sleep_ms(10)
            
            self.stats["timeout_count"] += 1
            return None
            
        except Exception as e:
            self.stats["error_count"] += 1
            self.logger.error("Erreur poll: {}".format(e), "radio")
            return None
    
    def get_statistics(self):
        """Retourne statistiques"""
        return dict(self.stats)
    
    async def poll_status(self):
        """Interroge tous les détecteurs (ASYNC - retourne une liste)"""
        import ta_config
        
        class DDStatus:
            def __init__(self, dd_id, state):
                self.dd_id = dd_id
                self.state = state
        
        results = []
        
        for dd_id in ta_config.RADIO["GROUP_IDS"]:
            result = await self.poll("{:02d}".format(dd_id))
            
            if result:
                state = ta_config.RADIO["STATE_PRESENT"] if result["state"] == 1 else ta_config.RADIO["STATE_ABSENT"]
                results.append(DDStatus(dd_id, state))
            else:
                results.append(DDStatus(dd_id, ta_config.RADIO["STATE_UNKNOWN"]))
            
            await asyncio.sleep_ms(0)
        
        return results
    
    async def request_status(self, dd_id):
        """Demande l'état d'un détecteur (ASYNC)"""
        return await self.poll("{:02d}".format(dd_id))