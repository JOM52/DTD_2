"""
Project: DTD - ta_app.py v2.3.0
Version avec: debouncing 2 coups pour états DD + logs étendus
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

logger = get_logger()

STATE_ABSENT  = config.RADIO.get("STATE_ABSENT", 0)
STATE_PRESENT = config.RADIO.get("STATE_PRESENT", 1)
STATE_UNKNOWN = config.RADIO.get("STATE_UNKNOWN", 2)

class App:
    def __init__(self, ui, radio):
        self.ui = ui
        self.radio = radio

        self.wdt = WDT(timeout=config.MAIN.get("WATCHDOG_TIMEOUT_MS", 10000)) if (config.MAIN.get("WATCHDOG_ENABLED", False) and WDT) else None

        # États stables affichés
        self.states = {dd: STATE_UNKNOWN for dd in config.RADIO["GROUP_IDS"]}
        # Debounce: {dd: {"cand": state, "count": n}}
        self._deb = {dd: {"cand": STATE_UNKNOWN, "count": 0} for dd in config.RADIO["GROUP_IDS"]}
        self._deb_needed = 2  # 2 lectures identiques pour valider

        self.loop_count = 0
        self.testing_id = None
        self.req_period = config.RADIO.get("POLL_PERIOD_MS", 500)
        self.last_status_update = 0
        self.error_count = 0

        mode = "SIMULATION" if self.radio.simulate else "REEL"
        self.ui.status("Init OK - Mode {}".format(mode))
        logger.info("Application initialisée", "app")

    def feed_watchdog(self):
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
        try:
            present = sum(1 for s in self.states.values() if s == STATE_PRESENT)
            absent  = sum(1 for s in self.states.values() if s == STATE_ABSENT)
            unknown = sum(1 for s in self.states.values() if s == STATE_UNKNOWN)

            msg = "DD: P:{} A:{} U:{}".format(present, absent, unknown)

            if hasattr(self.radio, 'stats'):
                st = self.radio.stats
                if st.get("blocked_calls", 0) > 0: msg += " BLK:{}".format(st["blocked_calls"])
                if st.get("uart_errors", 0) > 0:   msg += " UErr:{}".format(st["uart_errors"])
                if st.get("timeout_count", 0) > 0: msg += " TO:{}".format(st["timeout_count"])

            self.ui.status(msg)
        except Exception as e:
            logger.error("_update_status_message erreur: {}".format(e), "app")

    async def _refresh_ui(self):
        try:
            for idx, dd_id in enumerate(config.RADIO["GROUP_IDS"]):
                st = self.states.get(dd_id, STATE_UNKNOWN)
                state = True if st == STATE_PRESENT else (False if st == STATE_ABSENT else None)
                self.ui.update_group(idx, state=state)

            if config.UI.get("DIRTY_TRACKING", True):
                self.ui.render_dirty()

            await asyncio.sleep_ms(0)
        except Exception as e:
            logger.error("_refresh_ui erreur: {}".format(e), "app")
            self.error_count += 1

    async def _update_states(self):
        """Lit les états via radio et applique un debounce 2 coups."""
        try:
            statuses = await self.radio.poll_status()

            for st in statuses:
                dd = st.dd_id
                new_state = st.state
                d = self._deb[dd]
                if d["cand"] == new_state:
                    d["count"] += 1
                else:
                    d["cand"] = new_state
                    d["count"] = 1

                if d["count"] >= self._deb_needed and new_state != STATE_UNKNOWN:
                    old = self.states.get(dd, STATE_UNKNOWN)
                    self.states[dd] = new_state
                    if old != new_state:
                        state_name = "PRESENT" if new_state == STATE_PRESENT else "ABSENT"
                        logger.info("DD{}: {}".format(dd, state_name), "app")

            if (self.loop_count % 20) == 0:
                try:
                    if hasattr(self.radio, 'stats'):
                        logger.info("Radio: {}".format(self.radio.get_statistics()), "app")
                    logger.info("Logs: {}".format(logger.get_stats()), "app")
                except Exception as e:
                    logger.error("Erreur affichage stats: {}".format(e), "app")

        except Exception as e:
            logger.error("_update_states erreur: {}".format(e), "app")
            self.error_count += 1
            self.ui.status("ERREUR lecture radio")


    async def run(self):
        """Boucle principale (full async)."""
        logger.info("BOUCLE: Entrée dans while True", "app")
        self.ui.status("Demarrage scan detecteurs...")
        while True:
            try:
                if (self.loop_count % 10) == 0 and self.loop_count > 0:
                    logger.info("BOUCLE: iteration {}".format(self.loop_count), "app")

                self.feed_watchdog()

                await self._update_states()
                await self._refresh_ui()

                if self.testing_id:
                    await self.radio.request_status(self.testing_id)
                    self._update_status_message()
                    await asyncio.sleep_ms(self.req_period)

                self.loop_count += 1
                await asyncio.sleep_ms(10)
            except Exception as e:
                logger.critical("Erreur critique dans boucle principale: {}".format(e), "app")
                self.error_count += 1
                self.ui.status("ERREUR: {}".format(str(e)[:30]))
                await asyncio.sleep_ms(1000)

logger.info("ta_app.py v2.3.0 chargé (debounce + logs)", "app")
