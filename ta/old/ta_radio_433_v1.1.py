# ta_radio_433.py - Module radio 433MHz pour GT38 (v2.2.0 - Anti-blocage)
# Version : 2.2.0 - Protection contre blocages UART

from machine import Pin, UART
import time

class Radio433:
    """Gestion communication radio 433MHz via GT38"""
    
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
            "uart_resets": 0
        }
        
        # Hardware
        self.uart = None
        self.pin_set = None
        self.uart_config = None  # Sauvegarder config pour réinit
        
        # Protection anti-blocage
        self.last_uart_call = 0
        self.uart_timeout_ms = 500  # Timeout pour détecter un blocage
        self.uart_broken = False     # Flag si UART est HS
        
        if not self.simulate:
            self._init_hardware()
    
    def _init_hardware(self):
        """Initialise le hardware (UART + pin SET)"""
        # Importer ta_config pour accéder à HARDWARE
        import ta_config
        self.uart_config = ta_config.HARDWARE["UART_RADIO"]
        
        try:
            # Pin SET (mode CONFIG/RUN du GT38)
            set_pin_num = self.uart_config.get("PIN_GT38_SET")
            if set_pin_num:
                self.pin_set = Pin(set_pin_num, Pin.OUT)
                # Reset: LOW puis HIGH pour forcer état connu
                self.pin_set.value(0)
                time.sleep_ms(50)
                self.pin_set.value(1)  # Mode RUN (transparent)
                time.sleep_ms(50)
                self.logger.debug("Pin SET (GPIO{}) initialisée et resetée".format(set_pin_num), "radio")
            
            # UART avec timeout court
            uart_index = self.uart_config.get("INDEX", 2)
            tx_pin = self.uart_config.get("TX", 17)
            rx_pin = self.uart_config.get("RX", 18)
            
            self.uart = UART(
                uart_index,
                baudrate=9600,
                tx=Pin(tx_pin),
                rx=Pin(rx_pin),
                timeout=50,  # CRITIQUE: Timeout très court (50ms)
                rxbuf=256    # Buffer de réception réduit
            )
            
            self.logger.debug("UART{} initialisé (TX={}, RX={})".format(
                uart_index, tx_pin, rx_pin
            ), "radio")
            
            # Petit délai pour stabilisation
            time.sleep_ms(200)
            
            # CRITIQUE: Vider le buffer UART (données parasites)
            self._safe_flush_uart()
            
            self.uart_broken = False
            
        except Exception as e:
            self.logger.error("Erreur init hardware: {}".format(e), "radio")
            self.uart_broken = True
            raise
    
    def _safe_flush_uart(self):
        """Vide le buffer UART de manière sécurisée"""
        try:
            flush_start = time.ticks_ms()
            max_flush_time = 500  # Max 500ms pour vider
            
            while time.ticks_diff(time.ticks_ms(), flush_start) < max_flush_time:
                # Essayer de lire avec protection timeout
                try:
                    if self.uart.any():
                        self.uart.read()
                        time.sleep_ms(5)  # Petit délai entre lectures
                    else:
                        break  # Buffer vide
                except:
                    break  # En cas d'erreur, sortir
            
            self.logger.debug("Buffer UART vidé", "radio")
            
        except Exception as e:
            self.logger.warning("Erreur flush UART: {}".format(e), "radio")
    
    def _reset_uart(self):
        """Réinitialise complètement l'UART en cas de blocage"""
        try:
            self.logger.warning("Tentative reset UART...", "radio")
            
            # Désactiver UART
            if self.uart:
                try:
                    self.uart.deinit()
                except:
                    pass
            
            time.sleep_ms(100)
            
            # Réinitialiser
            uart_index = self.uart_config.get("INDEX", 2)
            tx_pin = self.uart_config.get("TX", 17)
            rx_pin = self.uart_config.get("RX", 18)
            
            self.uart = UART(
                uart_index,
                baudrate=9600,
                tx=Pin(tx_pin),
                rx=Pin(rx_pin),
                timeout=50,
                rxbuf=256
            )
            
            time.sleep_ms(100)
            self._safe_flush_uart()
            
            self.stats["uart_resets"] += 1
            self.uart_broken = False
            self.logger.info("✓ UART réinitialisé", "radio")
            
            return True
            
        except Exception as e:
            self.logger.error("Échec reset UART: {}".format(e), "radio")
            self.uart_broken = True
            return False
    
    def _safe_uart_any(self):
        """
        Appel sécurisé à uart.any() avec protection timeout
        
        Returns:
            Nombre d'octets disponibles, ou -1 en cas d'erreur/timeout
        """
        if not self.uart or self.uart_broken:
            return -1
        
        try:
            # Enregistrer l'heure de l'appel
            call_start = time.ticks_ms()
            self.last_uart_call = call_start
            
            # TENTATIVE 1: Lecture simple
            result = self.uart.any()
            
            # Vérifier que l'appel n'a pas pris trop de temps
            call_duration = time.ticks_diff(time.ticks_ms(), call_start)
            
            if call_duration > 100:  # Plus de 100ms = suspect
                self.logger.warning("uart.any() lent: {}ms".format(call_duration), "radio")
                self.stats["uart_errors"] += 1
            
            return result if result is not None else 0
            
        except Exception as e:
            self.logger.error("Erreur uart.any(): {}".format(e), "radio")
            self.stats["uart_errors"] += 1
            
            # Si trop d'erreurs, marquer UART comme cassé
            if self.stats["uart_errors"] > 10:
                self.uart_broken = True
                self.logger.error("UART marqué comme défectueux", "radio")
            
            return -1
    
    def _safe_uart_read(self, num_bytes):
        """
        Lecture sécurisée depuis l'UART
        
        Args:
            num_bytes: Nombre d'octets à lire
            
        Returns:
            Données lues, ou None en cas d'erreur
        """
        if not self.uart or self.uart_broken:
            return None
        
        try:
            data = self.uart.read(num_bytes)
            return data
        except Exception as e:
            self.logger.error("Erreur uart.read(): {}".format(e), "radio")
            self.stats["uart_errors"] += 1
            return None
    
    def check_hardware(self):
        """
        Vérifie que le module GT38 est accessible
        
        Returns:
            True si hardware OK, False sinon
        """
        if self.simulate:
            self.logger.info("Mode simulation", "radio")
            return True
        
        if self.uart_broken:
            self.logger.error("UART défectueux - tentative reset", "radio")
            if not self._reset_uart():
                return False
        
        self.logger.info("=== VÉRIFICATION GT38 ===", "radio")
        
        # Vérifier pin SET
        if self.pin_set:
            self.pin_set.value(1)
            self.logger.info("Pin SET en mode RUN", "radio")
        else:
            self.logger.warning("Pin SET non configurée", "radio")
        
        # Vérifier UART
        if not self.uart:
            self.logger.error("UART non initialisé", "radio")
            return False
        
        self.logger.info("UART configuré (9600 bauds)", "radio")
        
        # Test simple d'écriture
        try:
            test_data = b"CHECK"
            written = self.uart.write(test_data)
            
            if written == len(test_data):
                self.logger.info("✓ GT38 opérationnel (mode FU3)", "radio")
                return True
            else:
                self.logger.error("Erreur écriture UART", "radio")
                return False
                
        except Exception as e:
            self.logger.error("Erreur check GT38: {}".format(e), "radio")
            return False
    
    def ping(self):
        """
        Test simple de communication
        
        Returns:
            True si communication OK, False sinon
        """
        if self.simulate:
            return True
        
        if self.uart_broken:
            return False
        
        try:
            self._safe_flush_uart()
            
            # Envoyer test POLL
            self.uart.write(b"POLL:01\n")
            self.logger.debug("→ Ping: POLL:01", "radio")
            
            # Attendre réponse courte
            timeout_start = time.ticks_ms()
            
            while time.ticks_diff(time.ticks_ms(), timeout_start) < 1000:
                bytes_avail = self._safe_uart_any()
                
                if bytes_avail > 0:
                    resp = self._safe_uart_read(bytes_avail)
                    if resp:
                        self.logger.debug("← Ping réponse: {}".format(resp), "radio")
                        self.logger.info("✓ Ping réussi", "radio")
                        return True
                elif bytes_avail < 0:
                    # Erreur UART
                    return False
                
                time.sleep_ms(10)
            
            self.logger.warning("Ping timeout", "radio")
            return False
            
        except Exception as e:
            self.logger.error("Erreur ping: {}".format(e), "radio")
            return False
    
    def poll(self, detector_id):
        """
        Interroge un détecteur spécifique
        
        Args:
            detector_id: ID du détecteur ("01" à "05" ou "ALL")
            
        Returns:
            Dict avec 'detector_id' et 'state', ou None si pas de réponse
        """
        if self.simulate:
            import random
            return {
                "detector_id": detector_id,
                "state": random.choice([0, 1]),
                "simulated": True
            }
        
        # Si UART est cassé, tenter un reset
        if self.uart_broken:
            self.logger.warning("UART défectueux - reset automatique", "radio")
            if not self._reset_uart():
                return None
        
        try:
            # Vider buffer de manière sécurisée
            self._safe_flush_uart()
            
            # Envoyer commande POLL
            cmd = "POLL:{}\n".format(detector_id)
            self.uart.write(cmd.encode())
            self.stats["tx_count"] += 1
            
            self.logger.debug("→ Envoi: {}".format(cmd.strip()), "radio")
            
            # Attendre réponse avec timeout
            timeout_start = time.ticks_ms()
            timeout_ms = self.config.get("TIMEOUT_MS", 2000)
            response_buffer = bytearray()
            
            loop_count = 0
            max_loops = timeout_ms // 10  # Nombre max d'itérations
            
            while time.ticks_diff(time.ticks_ms(), timeout_start) < timeout_ms:
                loop_count += 1
                
                # Protection anti-boucle infinie
                if loop_count > max_loops:
                    self.logger.warning("Boucle poll dépassée", "radio")
                    break
                
                # Lecture sécurisée
                bytes_available = self._safe_uart_any()
                if bytes_available : print("xxxxxx", bytes_available)
                if bytes_available > 0:
                    # Lire les données disponibles
                    data = self._safe_uart_read(bytes_available)
                    
                    if data:
                        response_buffer.extend(data)
                        
                        # Chercher ligne complète
                        if b'\n' in response_buffer:
                            try:
                                # Décoder réponse
                                response = response_buffer.decode('utf-8', 'ignore').strip()
                                self.logger.debug("← Reçu: {}".format(response), "radio")
                                
                                # Parser ACK:XX:S
                                if response.startswith("ACK:"):
                                    parts = response.split(":")
                                    if len(parts) >= 3:
                                        resp_id = parts[1]
                                        state_str = parts[2]
                                        state = int(state_str) if state_str.isdigit() else 0
                                        
                                        self.logger.info("✓ ACK de {}: état={}".format(
                                            resp_id, state
                                        ), "radio")
                                        
                                        self.stats["rx_count"] += 1
                                        
                                        return {
                                            "detector_id": resp_id,
                                            "state": state,
                                            "simulated": False
                                        }
                                    else:
                                        self.logger.warning("Format ACK invalide: {}".format(
                                            response
                                        ), "radio")
                            except Exception as e:
                                self.logger.error("Erreur parsing: {}".format(e), "radio")
                
                elif bytes_available < 0:
                    # Erreur UART détectée
                    self.logger.error("Erreur UART durant poll", "radio")
                    break
                
                # Pause pour éviter surcharge CPU
                time.sleep_ms(10)
            
            # Timeout
            self.stats["timeout_count"] += 1
            self.logger.warning("Timeout POLL:{}".format(detector_id), "radio")
            return None
            
        except Exception as e:
            self.stats["error_count"] += 1
            self.logger.error("Erreur poll: {}".format(e), "radio")
            return None
    
    def poll_all(self):
        """
        Interroge tous les détecteurs (broadcast)
        
        Returns:
            Liste de dict avec réponses de tous les détecteurs
        """
        if self.simulate:
            import random
            return [
                {"detector_id": "01", "state": random.choice([0, 1]), "simulated": True},
                {"detector_id": "02", "state": random.choice([0, 1]), "simulated": True},
            ]
        
        if self.uart_broken:
            if not self._reset_uart():
                return []
        
        try:
            self._safe_flush_uart()
            
            # Envoyer POLL:ALL
            self.uart.write(b"POLL:ALL\n")
            self.logger.debug("→ Broadcast: POLL:ALL", "radio")
            
            # Collecter réponses
            timeout_start = time.ticks_ms()
            timeout_ms = self.config.get("TIMEOUT_MS", 2000)
            
            responses = []
            response_buffer = bytearray()
            
            while time.ticks_diff(time.ticks_ms(), timeout_start) < timeout_ms:
                bytes_available = self._safe_uart_any()
                
                if bytes_available > 0:
                    data = self._safe_uart_read(bytes_available)
                    
                    if data:
                        response_buffer.extend(data)
                        
                        # Traiter lignes complètes
                        while b'\n' in response_buffer:
                            nl_pos = response_buffer.find(b'\n')
                            line_bytes = bytes(response_buffer[:nl_pos + 1])
                            response_buffer = bytearray(response_buffer[nl_pos + 1:])
                            
                            try:
                                line = line_bytes.decode('utf-8', 'ignore').strip()
                                
                                if line.startswith("ACK:"):
                                    parts = line.split(":")
                                    if len(parts) >= 3:
                                        resp_id = parts[1]
                                        state = int(parts[2]) if parts[2].isdigit() else 0
                                        
                                        responses.append({
                                            "detector_id": resp_id,
                                            "state": state,
                                            "simulated": False
                                        })
                                        
                                        self.logger.debug("← ACK de {}: {}".format(
                                            resp_id, state
                                        ), "radio")
                            except:
                                pass
                
                elif bytes_available < 0:
                    break
                
                time.sleep_ms(10)
            
            if responses:
                self.logger.info("✓ {} détecteur(s) ont répondu".format(
                    len(responses)
                ), "radio")
            else:
                self.logger.warning("Aucune réponse au broadcast", "radio")
            
            return responses
            
        except Exception as e:
            self.logger.error("Erreur poll_all: {}".format(e), "radio")
            return []
    
    def set_detector_id(self, old_id, new_id):
        """Change l'ID d'un détecteur"""
        if self.simulate:
            return True
        
        if self.uart_broken:
            if not self._reset_uart():
                return False
        
        try:
            self._safe_flush_uart()
            
            cmd = "SETID:{}\n".format(new_id)
            self.uart.write(cmd.encode())
            self.logger.info("→ Changement ID: {}".format(cmd.strip()), "radio")
            
            timeout_start = time.ticks_ms()
            response_buffer = bytearray()
            
            while time.ticks_diff(time.ticks_ms(), timeout_start) < 3000:
                bytes_available = self._safe_uart_any()
                
                if bytes_available > 0:
                    data = self._safe_uart_read(bytes_available)
                    
                    if data:
                        response_buffer.extend(data)
                        
                        if b'\n' in response_buffer:
                            try:
                                response = response_buffer.decode('utf-8', 'ignore').strip()
                                self.logger.debug("← Reçu: {}".format(response), "radio")
                                
                                if response.startswith("ACKSETID:"):
                                    if "OK" in response:
                                        self.logger.info("✓ ID changé avec succès", "radio")
                                        return True
                                    else:
                                        self.logger.error("✗ Changement ID refusé", "radio")
                                        return False
                            except:
                                pass
                
                elif bytes_available < 0:
                    break
                
                time.sleep_ms(10)
            
            self.logger.warning("Timeout changement ID", "radio")
            return False
            
        except Exception as e:
            self.logger.error("Erreur set_id: {}".format(e), "radio")
            return False
    
    def get_statistics(self):
        """Retourne statistiques de communication"""
        return dict(self.stats)
    
    def poll_status(self):
        """
        Interroge tous les détecteurs configurés
        
        Yields:
            Objets avec dd_id et state pour chaque détecteur
        """
        import ta_config
        
        class DDStatus:
            def __init__(self, dd_id, state):
                self.dd_id = dd_id
                self.state = state
        
        for dd_id in ta_config.RADIO["GROUP_IDS"]:
            result = self.poll("{:02d}".format(dd_id))
            if result:
                state = ta_config.RADIO["STATE_PRESENT"] if result["state"] == 1 else ta_config.RADIO["STATE_ABSENT"]
                yield DDStatus(dd_id, state)
            else:
                yield DDStatus(dd_id, ta_config.RADIO["STATE_UNKNOWN"])
    
    def request_status(self, dd_id):
        """Demande l'état d'un détecteur spécifique"""
        return self.poll("{:02d}".format(dd_id))