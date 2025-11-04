# ta_radio_433.py - Module radio 433MHz pour GT38 (v2.4.0 - Corrections UART)
# Version : 2.4.0 - Corrections majeures communication UART
# Changelog v2.4.0:
#   - Timeout UART augmenté à 100ms (était 10ms)
#   - Buffer UART augmenté à 512 bytes (était 256)
#   - Vidage de buffer amélioré avec timeout
#   - Parser de trames robuste avec validation stricte
#   - Délai inter-poll de 150ms ajouté
#   - Gestion d'erreurs améliorée
#   - Utilisation cohérente de la configuration

from machine import Pin, UART
import time

# Import asyncio
try:
    import uasyncio as asyncio
except ImportError:
    import asyncio

class Radio433:
    """Gestion communication radio 433MHz via GT38 - VERSION ASYNC CORRIGÉE"""
    
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
            "blocked_calls": 0,
            "flushed_bytes": 0,
            "parse_errors": 0
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
            
            # UART avec configuration depuis ta_config
            uart_index = self.uart_config.get("INDEX", 2)
            tx_pin = self.uart_config.get("TX", 17)
            rx_pin = self.uart_config.get("RX", 18)
            baud = self.uart_config.get("BAUD", 9600)
            timeout_ms = self.uart_config.get("TIMEOUT_MS", 100)
            
            self.uart = UART(
                uart_index,
                baudrate=baud,
                tx=Pin(tx_pin),
                rx=Pin(rx_pin),
                timeout=timeout_ms,  # 100ms par défaut (était 10ms)
                rxbuf=512  # Augmenté (était 256)
            )
            
            self.logger.debug("UART{} initialisé ({}baud, {}ms timeout)".format(
                uart_index, baud, timeout_ms), "radio")
            
            time.sleep_ms(200)
            
            # Vider buffer initial
            flushed = 0
            try:
                while self.uart.any():
                    self.uart.read(1)
                    flushed += 1
                    time.sleep_ms(1)
                    if flushed > 100:  # Limite de sécurité
                        break
            except:
                pass
            
            if flushed > 0:
                self.logger.debug("Buffer initial vidé: {} bytes".format(flushed), "radio")
            
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
            self.logger.error("UART any() erreur: {}".format(e), "radio")
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
            self.logger.error("UART read() erreur: {}".format(e), "radio")
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
            self.logger.error("UART write() erreur: {}".format(e), "radio")
            return 0
    
    async def _flush_uart_buffer(self, max_time_ms=100):
        """
        Vide complètement le buffer UART avec timeout
        
        Args:
            max_time_ms: Temps maximum pour vider (ms)
            
        Returns:
            int: Nombre de bytes vidés
        """
        start = time.ticks_ms()
        flushed_bytes = 0
        
        while time.ticks_diff(time.ticks_ms(), start) < max_time_ms:
            bytes_avail = await self._async_uart_any()
            if bytes_avail <= 0:
                break
            
            data = await self._async_uart_read(bytes_avail)
            if data:
                flushed_bytes += len(data)
            
            await asyncio.sleep_ms(2)
        
        if flushed_bytes > 0:
            self.stats["flushed_bytes"] += flushed_bytes
            self.logger.debug("Flushed {} bytes".format(flushed_bytes), "radio")
        
        return flushed_bytes
    
    def _parse_ack_response(self, response):
        """
        Parse une réponse ACK avec validation stricte
        
        Args:
            response: String de la forme "ACK:ID:STATE"
            
        Returns:
            dict ou None: {"detector_id": str, "state": int, "simulated": bool}
        """
        try:
            # Chercher début de trame valide
            if "ACK:" not in response:
                self.stats["parse_errors"] += 1
                self.logger.warning("Pas de 'ACK:' dans: {}".format(response), "radio")
                return None
            
            # Extraire depuis "ACK:"
            ack_start = response.index("ACK:")
            response = response[ack_start:]
            
            # Split et validation
            parts = response.split(":")
            if len(parts) != 3:
                self.stats["parse_errors"] += 1
                self.logger.warning("ACK malformé: {}".format(response), "radio")
                return None
            
            detector_id = parts[1].strip()
            state_str = parts[2].strip()
            
            # Validation des valeurs
            if not detector_id.isdigit():
                self.stats["parse_errors"] += 1
                self.logger.warning("ID non-numérique: {}".format(detector_id), "radio")
                return None
            
            if not state_str.isdigit():
                self.stats["parse_errors"] += 1
                self.logger.warning("State non-numérique: {}".format(state_str), "radio")
                return None
            
            return {
                "detector_id": detector_id,
                "state": int(state_str),
                "simulated": False
            }
            
        except Exception as e:
            self.stats["parse_errors"] += 1
            self.logger.error("Erreur parse ACK: {}".format(e), "radio")
            return None
    
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
        """
        Interroge un détecteur (ASYNC) avec gestion robuste
        
        Args:
            detector_id: ID du détecteur (string)
            
        Returns:
            dict ou None: Résultat du poll
        """
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
            # Vider buffer avec timeout
            await self._flush_uart_buffer(max_time_ms=50)
            
            # Envoyer POLL
            cmd = "POLL:{}\n".format(detector_id)
            written = await self._async_uart_write(cmd.encode())
            
            if written > 0:
                self.stats["tx_count"] += 1
                self.logger.debug("→ {}".format(cmd.strip()), "radio")
            else:
                self.logger.warning("Échec écriture POLL", "radio")
                return None
            
            # Attendre réponse avec timeout
            timeout_ms = self.config.get("REPLY_TIMEOUT_MS", 500)
            timeout_start = time.ticks_ms()
            response_buffer = bytearray()
            
            while time.ticks_diff(time.ticks_ms(), timeout_start) < timeout_ms:
                bytes_available = await self._async_uart_any()
                
                if bytes_available > 0:
                    data = await self._async_uart_read(bytes_available)
                    
                    if data:
                        response_buffer.extend(data)
                        
                        # Chercher fin de trame
                        if b'\n' in response_buffer:
                            response = response_buffer.decode('utf-8', 'ignore').strip()
                            self.logger.debug("← {}".format(response), "radio")
                            
                            # Parser avec validation stricte
                            result = self._parse_ack_response(response)
                            if result:
                                self.stats["rx_count"] += 1
                                return result
                            else:
                                # Trame invalide, continuer à attendre
                                response_buffer = bytearray()
                
                # Check toutes les 5ms (équilibre réactivité/CPU)
                await asyncio.sleep_ms(5)
            
            # Timeout
            self.stats["timeout_count"] += 1
            self.logger.debug("Timeout poll DD{}".format(detector_id), "radio")
            return None
            
        except Exception as e:
            self.stats["error_count"] += 1
            self.logger.error("Erreur poll DD{}: {}".format(detector_id, e), "radio")
            return None
    
    def get_statistics(self):
        """Retourne statistiques"""
        return dict(self.stats)
    
    async def poll_status(self):
        """
        Interroge tous les détecteurs (ASYNC - retourne une liste)
        Avec délai inter-poll pour éviter collisions
        """
        import ta_config
        
        class DDStatus:
            def __init__(self, dd_id, state):
                self.dd_id = dd_id
                self.state = state
        
        results = []
        inter_poll_delay = 150  # 150ms entre chaque poll
        
        for dd_id in ta_config.RADIO["GROUP_IDS"]:
            result = await self.poll("{:02d}".format(dd_id))
            
            if result:
                state = (ta_config.RADIO["STATE_PRESENT"] 
                        if result["state"] == 1 
                        else ta_config.RADIO["STATE_ABSENT"])
                results.append(DDStatus(dd_id, state))
            else:
                results.append(DDStatus(dd_id, ta_config.RADIO["STATE_UNKNOWN"]))
            
            # Délai important entre polls pour laisser le GT38 respirer
            await asyncio.sleep_ms(inter_poll_delay)
        
        return results
    
    async def request_status(self, dd_id):
        """Demande l'état d'un détecteur (ASYNC)"""
        return await self.poll("{:02d}".format(dd_id))
