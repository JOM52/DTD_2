"""
Project: DTD - ta_app.py v2.1.0
Version corrigée avec asyncio non-bloquant et log dynamique
"""

import ta_config as config
from ta_logger import get_logger

try:
    import uasyncio as asyncio
except ImportError:
    import asyncio

try:
    from machine import WDT
except ImportError:
    WDT = None

from ta_ui import UI
from ta_radio_433 import Radio433 as Radio

# États depuis la config
STATE_UNKNOWN = config.RADIO["STATE_UNKNOWN"]
STATE_PRESENT = config.RADIO["STATE_PRESENT"]
STATE_ABSENT = config.RADIO["STATE_ABSENT"]

logger = get_logger()

class TaApp:
    def __init__(self, tft=None, ui=None, radio=None):
        logger.info("Initialisation de l'application DTD v{}".format(
            config.MAIN["VERSION_NO"]), "app")
        
        self.ui = ui if ui else UI()
        self.radio = radio if radio else Radio(config.RADIO, logger)
        
        # Après l'initialisation de self.radio
        if not self.radio.simulate:
            hw_ok = self.radio.check_hardware()
            logger.info("Hardware GT38: {}".format("OK" if hw_ok else "ERREUR"), "app")
        
        self.states = {dd_id: STATE_UNKNOWN for dd_id in config.RADIO["GROUP_IDS"]}
        self.testing_id = None
        self.req_period = max(150, config.RADIO.get("POLL_PERIOD_MS", 1500))
        
        # Watchdog
        self.wdt = None
        if config.MAIN.get("WATCHDOG_ENABLED", True) and WDT:
            try:
                self.wdt = WDT(timeout=config.MAIN.get("WATCHDOG_TIMEOUT_MS", 30000))
                logger.info("Watchdog activé", "app")
            except Exception as e:
                logger.error("Erreur watchdog: {}".format(e), "app")
        
        # Compteurs et stats
        self.loop_count = 0
        self.error_count = 0
        self.last_status_update = 0
        
        # Message initial
        mode = "SIMULATION" if self.radio.simulate else "REEL"
        self.ui.status("Init OK - Mode {}".format(mode))
        logger.info("Application initialisée", "app")

    def feed_watchdog(self):
        """Alimente le watchdog"""
        if self.wdt:
            try:
                self.wdt.feed()
            except Exception as e:
                logger.error("Erreur feed watchdog: {}".format(e), "app")

    def set_testing(self, dd_id):
        self.testing_id = dd_id
        try:
            if dd_id is None:
                self.ui.progress(None)
            else:
                self.ui.progress(int(dd_id), color=config.COLORS["C_PGR"])
        except Exception as e:
            logger.warning("set_testing erreur UI: {}".format(e), "app")

    def _update_status_message(self):
        """Met à jour le message de statut affiché"""
        try:
            # Compter les états
            present_count = sum(1 for s in self.states.values() if s == STATE_PRESENT)
            absent_count = sum(1 for s in self.states.values() if s == STATE_ABSENT)
            unknown_count = sum(1 for s in self.states.values() if s == STATE_UNKNOWN)
            
            # Message selon le contexte
            if self.testing_id:
                msg = "Test DD{} en cours...".format(self.testing_id)
            elif unknown_count == len(self.states):
                msg = "Scan des {} detecteurs...".format(len(self.states))
            else:
                msg = "OK:{} ERR:{} ?:{}  Loop:{}".format(
                    present_count, absent_count, unknown_count, self.loop_count)
            
            # Ajouter erreurs si présentes
            if self.error_count > 0:
                msg += " Err:{}".format(self.error_count)
            
            self.ui.status(msg)
            
        except Exception as e:
            logger.error("_update_status_message erreur: {}".format(e), "app")

    async def _refresh_ui(self):
        """Met à jour l'affichage avec dirty tracking (ASYNC)"""
        try:
            # Mettre à jour les barres de statut
            for idx, dd_id in enumerate(config.RADIO["GROUP_IDS"]):
                st = self.states.get(dd_id, STATE_UNKNOWN)
                
                if st == STATE_PRESENT:
                    state = True
                elif st == STATE_ABSENT:
                    state = False
                else:
                    state = None
                
                self.ui.update_group(idx, state=state)
            
            # Mettre à jour le message de statut périodiquement
            # (toutes les 5 itérations pour éviter trop de rafraîchissements)
            if (self.loop_count - self.last_status_update) >= 5:
                self._update_status_message()
                self.last_status_update = self.loop_count
            
            # Rafraîchir uniquement les éléments modifiés
            if config.UI.get("DIRTY_TRACKING", True):
                self.ui.render_dirty()
            
            # Laisser respirer asyncio
            await asyncio.sleep_ms(0)
        except Exception as e:
            logger.error("_refresh_ui erreur: {}".format(e), "app")
            self.error_count += 1

    async def _update_states(self):
        """Lit les états depuis la radio (ASYNC)"""
        try:
            for st in self.radio.poll_status():
                old_state = self.states.get(st.dd_id, STATE_UNKNOWN)
                self.states[st.dd_id] = st.state
                
                # Logger les changements d'état
                if old_state != st.state and st.state != STATE_UNKNOWN:
                    state_name = "PRESENT" if st.state == STATE_PRESENT else "ABSENT"
                    logger.info("DD{}: {}".format(st.dd_id, state_name), "app")
                
                # Laisser respirer asyncio entre chaque DD
                await asyncio.sleep_ms(0)
        except Exception as e:
            logger.error("_update_states erreur: {}".format(e), "app")
            self.error_count += 1
            self.ui.status("ERREUR lecture radio")

    async def _handle_testing(self):
        """Gère la requête rapide si test actif"""
        try:
            if self.testing_id:
                self.radio.request_status(self.testing_id)
                # Mettre à jour le statut immédiatement pendant un test
                self._update_status_message()
                await asyncio.sleep_ms(self.req_period)
            else:
                await asyncio.sleep_ms(200)
        except Exception as e:
            logger.error("_handle_testing erreur: {}".format(e), "app")

    async def _print_stats(self):
        """Tâche périodique pour afficher les statistiques"""
        if not config.MAIN.get("DEBUG_MODE", False):
            return
        
        while True:
            await asyncio.sleep_ms(30000)  # Toutes les 30s
            
            try:
                logger.info("=== STATISTIQUES ===", "app")
                logger.info("Boucles: {} | Erreurs: {}".format(
                    self.loop_count, self.error_count), "app")
                
                # État des détecteurs
                present = sum(1 for s in self.states.values() if s == STATE_PRESENT)
                absent = sum(1 for s in self.states.values() if s == STATE_ABSENT)
                unknown = sum(1 for s in self.states.values() if s == STATE_UNKNOWN)
                logger.info("DD: Present={} Absent={} Unknown={}".format(
                    present, absent, unknown), "app")
                
                if hasattr(self.radio, 'stats') and self.radio.stats:
                    logger.info("Radio: {}".format(self.radio.stats), "app")
                
                # Stats logger
                log_stats = logger.get_stats()
                logger.info("Logs: {}".format(log_stats), "app")
                
            except Exception as e:
                logger.error("Erreur affichage stats: {}".format(e), "app")

    async def run(self):
        """Boucle principale de l'application"""
        logger.info("Démarrage de la boucle principale", "app")
        
        # Lancer tâche stats si debug
        if config.MAIN.get("DEBUG_MODE", False):
            asyncio.create_task(self._print_stats())
        
        # Log critique pour debug
        logger.info("BOUCLE: Entrée dans while True", "app")
        
        # Message initial
        self.ui.status("Demarrage scan detecteurs...")
        
        while True:
            try:
                # Log périodique
                if (self.loop_count % 10) == 0 and self.loop_count > 0:
                    logger.info("BOUCLE: iteration {}".format(self.loop_count), "app")
                
                # Alimenter watchdog
                self.feed_watchdog()
                
                # Traitement principal (ASYNC - NON BLOQUANT)
                await self._update_states()
                await self._refresh_ui()
                await self._handle_testing()
                
                self.loop_count += 1
                
            except Exception as e:
                logger.critical("Erreur critique dans boucle principale: {}".format(e), "app")
                self.error_count += 1
                self.ui.status("ERREUR: {}".format(str(e)[:30]))
                await asyncio.sleep_ms(1000)

logger.info("ta_app.py v2.1.0 chargé (async + log dynamique)", "app")
