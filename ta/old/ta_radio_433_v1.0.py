# ta_radio_433.py - Module radio 433MHz pour GT38 (corrigé)
# Version : 2.0 - Communication bidirectionnelle stable

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
            "error_count": 0
        }
        
        # Hardware
        self.uart = None
        self.pin_set = None
        
        if not self.simulate:
            self._init_hardware()
    
    def _init_hardware(self):
        """Initialise le hardware (UART + pin SET)"""
        # Importer ta_config pour accéder à HARDWARE
        import ta_config
        uart_config = ta_config.HARDWARE["UART_RADIO"]
        
        try:
            # Pin SET (mode CONFIG/RUN du GT38)
            set_pin_num = uart_config.get("PIN_GT38_SET")
            if set_pin_num:
                self.pin_set = Pin(set_pin_num, Pin.OUT)
                # Reset: LOW puis HIGH pour forcer état connu
                self.pin_set.value(0)
                time.sleep_ms(50)
                self.pin_set.value(1)  # Mode RUN (transparent)
                time.sleep_ms(50)
                self.logger.debug("Pin SET (GPIO{}) initialisée et resetée".format(set_pin_num), "radio")
            
            # UART
            uart_index = uart_config.get("INDEX", 2)
            tx_pin = uart_config.get("TX", 17)
            rx_pin = uart_config.get("RX", 18)
            
            self.uart = UART(
                uart_index,
                baudrate=9600,
                tx=Pin(tx_pin),
                rx=Pin(rx_pin),
                timeout=100
            )
            
            self.logger.debug("UART{} initialisé (TX={}, RX={})".format(
                uart_index, tx_pin, rx_pin
            ), "radio")
            
            # Petit délai pour stabilisation
            time.sleep_ms(200)
            
            # CRITIQUE: Vider le buffer UART (données parasites)
            while self.uart.any():
                self.uart.read()
            self.logger.debug("Buffer UART vidé", "radio")
            
        except Exception as e:
            self.logger.error("Erreur init hardware: {}".format(e), "radio")
            raise
    
    def check_hardware(self):
        """
        Vérifie que le module GT38 est accessible
        
        Returns:
            True si hardware OK, False sinon
        """
        if self.simulate:
            self.logger.info("Mode simulation", "radio")
            return True
        
        self.logger.info("=== VÉRIFICATION GT38 ===", "radio")
        
        # Vérifier pin SET
        if self.pin_set:
            # S'assurer mode RUN
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
                self.logger.info("  Canal: 001 | Baud: 9600", "radio")
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
        Envoie un POLL et vérifie qu'il y a une réponse
        
        Returns:
            True si communication OK, False sinon
        """
        if self.simulate:
            return True
        
        try:
            # Vider buffer
            while self.uart.any():
                self.uart.read(self.uart.any())
            
            # Envoyer test POLL
            self.uart.write(b"POLL:01\n")
            self.logger.debug("→ Ping: POLL:01", "radio")
            
            # Attendre réponse courte
            timeout_start = time.ticks_ms()
            
            while time.ticks_diff(time.ticks_ms(), timeout_start) < 1000:  # 1s timeout
                if self.uart.any():
                    # Données reçues = communication OK
                    resp = self.uart.read(self.uart.any())
                    self.logger.debug("← Ping réponse: {}".format(resp), "radio")
                    self.logger.info("✓ Ping réussi", "radio")
                    return True
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
        
        try:
            # Vider buffer
            while self.uart.any():
                self.uart.read(self.uart.any())
            # Envoyer commande POLL
            cmd = "POLL:{}\n".format(detector_id)
            self.uart.write(cmd.encode())
            self.stats["tx_count"] += 1
            
            self.logger.debug("→ Envoi: {}".format(cmd.strip()), "radio")
            
            # Attendre réponse avec timeout
            timeout_start = time.ticks_ms()
            timeout_ms = self.config.get("TIMEOUT_MS", 2000)
            response_buffer = bytearray()
            
            while time.ticks_diff(time.ticks_ms(), timeout_start) < timeout_ms:
                #=================================================================================
                # c'est ici que ça bloque
                #=================================================================================
                if self.uart.any():
                    data = self.uart.read(self.uart.any())
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
            # Mode simulation : retourner plusieurs détecteurs
            import random
            return [
                {"detector_id": "01", "state": random.choice([0, 1]), "simulated": True},
                {"detector_id": "02", "state": random.choice([0, 1]), "simulated": True},
            ]
        
        try:
            # Vider buffer
            while self.uart.any():
                self.uart.read(self.uart.any())
            
            # Envoyer POLL:ALL
            self.uart.write(b"POLL:ALL\n")
            self.logger.debug("→ Broadcast: POLL:ALL", "radio")
            
            # Collecter réponses pendant 2 secondes
            timeout_start = time.ticks_ms()
            timeout_ms = self.config.get("TIMEOUT_MS", 2000)
            
            responses = []
            response_buffer = bytearray()
            
            while time.ticks_diff(time.ticks_ms(), timeout_start) < timeout_ms:
                if self.uart.any():
                    data = self.uart.read(self.uart.any())
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
        """
        Change l'ID d'un détecteur
        
        Args:
            old_id: ID actuel du détecteur
            new_id: Nouvel ID (01 à 05)
            
        Returns:
            True si changement réussi, False sinon
        """
        if self.simulate:
            return True
        
        try:
            # Vider buffer
            while self.uart.any():
                self.uart.read(self.uart.any())
            
            # Envoyer SETID
            cmd = "SETID:{}\n".format(new_id)
            self.uart.write(cmd.encode())
            
            self.logger.info("→ Changement ID: {}".format(cmd.strip()), "radio")
            
            # Attendre confirmation
            timeout_start = time.ticks_ms()
            response_buffer = bytearray()
            
            while time.ticks_diff(time.ticks_ms(), timeout_start) < 3000:
                if self.uart.any():
                    data = self.uart.read(self.uart.any())
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
                
                time.sleep_ms(10)
            
            self.logger.warning("Timeout changement ID", "radio")
            return False
            
        except Exception as e:
            self.logger.error("Erreur set_id: {}".format(e), "radio")
            return False
    
    def get_statistics(self):
        """
        Retourne statistiques de communication
        
        Returns:
            Dict avec stats (pour future implémentation)
        """
        return {
            "mode": "simulation" if self.simulate else "real",
            "uart_port": self.config.get("UART_INDEX"),
            "timeout_ms": self.config.get("TIMEOUT_MS"),
        }
    
    def poll_status(self):
        """
        Interroge tous les détecteurs configurés
        
        Yields:
            Objets avec dd_id et state pour chaque détecteur
        """
        # Importer les IDs depuis ta_config
        import ta_config
        
        class DDStatus:
            def __init__(self, dd_id, state):
                self.dd_id = dd_id
                self.state = state
        for dd_id in ta_config.RADIO["GROUP_IDS"]:
            result = self.poll("{:02d}".format(dd_id))
            if result:
                # Convertir en état normalisé
                state = ta_config.RADIO["STATE_PRESENT"] if result["state"] == 1 else ta_config.RADIO["STATE_ABSENT"]
                yield DDStatus(dd_id, state)
            else:
                # Pas de réponse = état inconnu
                yield DDStatus(dd_id, ta_config.RADIO["STATE_UNKNOWN"])
    
    def request_status(self, dd_id):
        """
        Demande l'état d'un détecteur spécifique (pour tests)
        
        Args:
            dd_id: ID du détecteur (1-5)
            
        Returns:
            Résultat de poll() pour ce détecteur
        """
        return self.poll("{:02d}".format(dd_id))