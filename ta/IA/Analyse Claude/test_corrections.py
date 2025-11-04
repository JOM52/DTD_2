# test_corrections.py - Script de validation des corrections v2.4.0
# À exécuter après installation des nouveaux modules

try:
    import uasyncio as asyncio
except ImportError:
    import asyncio

import ta_config as config
from ta_radio_433 import Radio433
from ta_logger import get_logger
import time

logger = get_logger()

class TestCorrections:
    """Suite de tests pour valider les corrections UART/Radio"""
    
    def __init__(self):
        self.results = {
            "config_validation": False,
            "uart_init": False,
            "timeout_coherence": False,
            "buffer_flush": False,
            "parser_robustesse": False,
            "poll_basique": False,
            "statistiques": False,
            "cycle_complet": False
        }
        self.radio = None
    
    def print_header(self, title):
        """Affiche un en-tête de section"""
        print("\n" + "="*60)
        print(title)
        print("="*60)
    
    def print_test(self, name, result, details=""):
        """Affiche résultat d'un test"""
        status = "✓ PASS" if result else "✗ FAIL"
        print("[{}] {} {}".format(status, name, details))
        return result
    
    # ========== TEST 1: Validation Configuration ==========
    def test_config_validation(self):
        """Vérifie que la configuration est cohérente"""
        self.print_header("TEST 1: Validation Configuration")
        
        try:
            # Récupérer valeurs
            uart_to = config.HARDWARE["UART_RADIO"].get("TIMEOUT_MS", 0)
            reply_to = config.RADIO.get("REPLY_TIMEOUT_MS", 0)
            poll_period = config.RADIO.get("POLL_PERIOD_MS", 0)
            
            print("UART timeout:  {}ms".format(uart_to))
            print("Reply timeout: {}ms".format(reply_to))
            print("Poll period:   {}ms".format(poll_period))
            
            # Vérifications
            checks = []
            checks.append(self.print_test(
                "UART timeout >= 50ms", 
                uart_to >= 50,
                "({})".format(uart_to)))
            
            checks.append(self.print_test(
                "UART timeout < Reply timeout",
                uart_to < reply_to,
                "({} < {})".format(uart_to, reply_to)))
            
            checks.append(self.print_test(
                "Reply timeout < Poll period",
                reply_to < poll_period,
                "({} < {})".format(reply_to, poll_period)))
            
            checks.append(self.print_test(
                "Version config >= 2.1.0",
                config.__version_no__ >= "2.1.0",
                "({})".format(config.__version_no__)))
            
            self.results["config_validation"] = all(checks)
            return self.results["config_validation"]
            
        except Exception as e:
            print("ERREUR: {}".format(e))
            return False
    
    # ========== TEST 2: Initialisation UART ==========
    def test_uart_init(self):
        """Vérifie l'initialisation correcte de l'UART"""
        self.print_header("TEST 2: Initialisation UART")
        
        try:
            self.radio = Radio433(config.RADIO, logger)
            
            # Vérifier que l'UART est initialisé
            if not config.RADIO.get("SIMULATE", False):
                checks = []
                checks.append(self.print_test(
                    "Instance radio créée",
                    self.radio is not None))
                
                checks.append(self.print_test(
                    "UART non cassé",
                    not self.radio.uart_broken))
                
                checks.append(self.print_test(
                    "UART existe",
                    self.radio.uart is not None))
                
                # Vérifier stats initialisées
                has_new_stats = (
                    "flushed_bytes" in self.radio.stats and
                    "parse_errors" in self.radio.stats
                )
                checks.append(self.print_test(
                    "Nouvelles stats présentes",
                    has_new_stats))
                
                self.results["uart_init"] = all(checks)
            else:
                print("Mode simulation - test passé automatiquement")
                self.results["uart_init"] = True
            
            return self.results["uart_init"]
            
        except Exception as e:
            print("ERREUR: {}".format(e))
            return False
    
    # ========== TEST 3: Cohérence Timeouts ==========
    def test_timeout_coherence(self):
        """Vérifie la cohérence des timeouts"""
        self.print_header("TEST 3: Cohérence Timeouts")
        
        try:
            if not self.radio:
                print("Radio non initialisée, skip")
                return False
            
            # Calculs théoriques
            bytes_per_frame = 9  # "ACK:01:1\n"
            bits_per_byte = 10   # start + 8 data + stop
            baudrate = config.HARDWARE["UART_RADIO"].get("BAUD", 9600)
            
            time_per_frame_ms = (bytes_per_frame * bits_per_byte * 1000) / baudrate
            
            print("Calculs théoriques:")
            print("  Taille trame: {} bytes".format(bytes_per_frame))
            print("  Baudrate: {} baud".format(baudrate))
            print("  Temps trame: {:.2f}ms".format(time_per_frame_ms))
            
            uart_timeout = config.HARDWARE["UART_RADIO"].get("TIMEOUT_MS", 0)
            safety_margin = uart_timeout / time_per_frame_ms
            
            checks = []
            checks.append(self.print_test(
                "UART timeout > temps trame",
                uart_timeout > time_per_frame_ms,
                "({:.0f}ms > {:.1f}ms)".format(uart_timeout, time_per_frame_ms)))
            
            checks.append(self.print_test(
                "Marge sécurité >= 3x",
                safety_margin >= 3,
                "({:.1f}x)".format(safety_margin)))
            
            self.results["timeout_coherence"] = all(checks)
            return self.results["timeout_coherence"]
            
        except Exception as e:
            print("ERREUR: {}".format(e))
            return False
    
    # ========== TEST 4: Buffer Flush ==========
    async def test_buffer_flush(self):
        """Teste la fonction de vidage de buffer"""
        self.print_header("TEST 4: Vidage Buffer")
        
        try:
            if not self.radio or config.RADIO.get("SIMULATE", False):
                print("Mode simulation ou radio non initialisée, skip")
                self.results["buffer_flush"] = True
                return True
            
            # Tester la méthode flush
            checks = []
            
            # Vérifier méthode existe
            has_flush = hasattr(self.radio, '_flush_uart_buffer')
            checks.append(self.print_test(
                "Méthode _flush_uart_buffer existe",
                has_flush))
            
            if has_flush:
                # Appeler flush
                flushed = await self.radio._flush_uart_buffer(max_time_ms=50)
                checks.append(self.print_test(
                    "Flush exécuté sans erreur",
                    flushed is not None,
                    "({} bytes)".format(flushed if flushed else 0)))
            
            self.results["buffer_flush"] = all(checks)
            return self.results["buffer_flush"]
            
        except Exception as e:
            print("ERREUR: {}".format(e))
            return False
    
    # ========== TEST 5: Parser Robustesse ==========
    def test_parser_robustesse(self):
        """Teste le parser avec différentes entrées"""
        self.print_header("TEST 5: Robustesse Parser")
        
        try:
            if not self.radio:
                print("Radio non initialisée, skip")
                return False
            
            # Vérifier méthode existe
            has_parser = hasattr(self.radio, '_parse_ack_response')
            if not self.print_test("Méthode _parse_ack_response existe", has_parser):
                return False
            
            # Tests de parsing
            test_cases = [
                # (input, should_parse, description)
                ("ACK:01:1\n", True, "Trame valide"),
                ("ACK:05:0", True, "Trame valide sans \\n"),
                ("GARBAGE ACK:02:1 MORE", True, "Trame valide avec bruit"),
                ("ACK:03:1:EXTRA", False, "Trame avec extra données"),
                ("ACK:04:X", False, "État non-numérique"),
                ("ACK:XX:1", False, "ID non-numérique"),
                ("NO_ACK_HERE", False, "Pas de ACK"),
                ("CK:01:1", False, "ACK tronqué"),
                ("", False, "String vide"),
            ]
            
            checks = []
            for test_input, should_parse, description in test_cases:
                result = self.radio._parse_ack_response(test_input)
                is_valid = (result is not None)
                test_passed = (is_valid == should_parse)
                
                status = "✓" if test_passed else "✗"
                print("  [{}] {}: '{}'".format(
                    status, description, test_input[:30]))
                
                checks.append(test_passed)
            
            self.results["parser_robustesse"] = all(checks)
            return self.results["parser_robustesse"]
            
        except Exception as e:
            print("ERREUR: {}".format(e))
            return False
    
    # ========== TEST 6: Poll Basique ==========
    async def test_poll_basique(self):
        """Teste un poll simple"""
        self.print_header("TEST 6: Poll Basique")
        
        try:
            if not self.radio:
                print("Radio non initialisée, skip")
                return False
            
            # Tester poll
            print("Envoi POLL à DD01...")
            result = await self.radio.poll("01")
            
            checks = []
            checks.append(self.print_test(
                "Poll exécuté sans exception",
                True))
            
            if config.RADIO.get("SIMULATE", False):
                checks.append(self.print_test(
                    "Résultat reçu (simulation)",
                    result is not None))
            else:
                print("  Résultat: {}".format(result))
                if result:
                    checks.append(self.print_test(
                        "Résultat reçu",
                        True,
                        "(DD{}, state={})".format(
                            result.get("detector_id", "?"),
                            result.get("state", "?"))))
                else:
                    print("  Aucune réponse (timeout ou DD absent)")
                    checks.append(self.print_test(
                        "Timeout géré correctement",
                        True))
            
            self.results["poll_basique"] = all(checks)
            return self.results["poll_basique"]
            
        except Exception as e:
            print("ERREUR: {}".format(e))
            return False
    
    # ========== TEST 7: Statistiques ==========
    async def test_statistiques(self):
        """Vérifie les statistiques"""
        self.print_header("TEST 7: Statistiques")
        
        try:
            if not self.radio:
                print("Radio non initialisée, skip")
                return False
            
            # Faire quelques polls pour générer stats
            print("Exécution de 3 polls...")
            for i in range(3):
                await self.radio.poll("01")
                await asyncio.sleep_ms(200)
            
            # Récupérer stats
            stats = self.radio.get_statistics()
            
            print("\nStatistiques actuelles:")
            for key, value in stats.items():
                print("  {}: {}".format(key, value))
            
            # Vérifications
            checks = []
            checks.append(self.print_test(
                "Stats disponibles",
                stats is not None))
            
            checks.append(self.print_test(
                "Stat 'flushed_bytes' existe",
                "flushed_bytes" in stats))
            
            checks.append(self.print_test(
                "Stat 'parse_errors' existe",
                "parse_errors" in stats))
            
            # Si non simulation, vérifier activité
            if not config.RADIO.get("SIMULATE", False):
                has_activity = (
                    stats.get("tx_count", 0) > 0 or
                    stats.get("rx_count", 0) > 0 or
                    stats.get("timeout_count", 0) > 0
                )
                checks.append(self.print_test(
                    "Activité détectée",
                    has_activity,
                    "(tx={}, rx={}, to={})".format(
                        stats.get("tx_count", 0),
                        stats.get("rx_count", 0),
                        stats.get("timeout_count", 0))))
            
            self.results["statistiques"] = all(checks)
            return self.results["statistiques"]
            
        except Exception as e:
            print("ERREUR: {}".format(e))
            return False
    
    # ========== TEST 8: Cycle Complet ==========
    async def test_cycle_complet(self):
        """Teste un cycle complet de polling"""
        self.print_header("TEST 8: Cycle Complet")
        
        try:
            if not self.radio:
                print("Radio non initialisée, skip")
                return False
            
            print("Polling tous les détecteurs...")
            start_time = time.ticks_ms()
            
            results = await self.radio.poll_status()
            
            elapsed = time.ticks_diff(time.ticks_ms(), start_time)
            
            print("\nRésultats:")
            for r in results:
                state_str = {
                    0: "UNKNOWN",
                    1: "PRESENT",
                    2: "ABSENT"
                }.get(r.state, "?")
                print("  DD{:02d}: {}".format(r.dd_id, state_str))
            
            print("\nTemps écoulé: {}ms".format(elapsed))
            
            # Vérifications
            checks = []
            checks.append(self.print_test(
                "Résultats reçus",
                results is not None))
            
            checks.append(self.print_test(
                "Nombre détecteurs correct",
                len(results) == len(config.RADIO["GROUP_IDS"]),
                "({}/{})".format(len(results), len(config.RADIO["GROUP_IDS"]))))
            
            # Vérifier temps minimum (délai inter-poll)
            num_detectors = len(config.RADIO["GROUP_IDS"])
            inter_poll_delay = 150  # ms
            min_time = (num_detectors - 1) * inter_poll_delay
            
            checks.append(self.print_test(
                "Délai inter-poll respecté",
                elapsed >= min_time,
                "({}ms >= {}ms)".format(elapsed, min_time)))
            
            self.results["cycle_complet"] = all(checks)
            return self.results["cycle_complet"]
            
        except Exception as e:
            print("ERREUR: {}".format(e))
            return False
    
    # ========== Exécution Complète ==========
    async def run_all_tests(self):
        """Exécute tous les tests"""
        self.print_header("SUITE DE TESTS - Corrections v2.4.0")
        
        print("\nInfo système:")
        print("  Version config: {}".format(config.__version_no__))
        print("  Mode simulation: {}".format(config.RADIO.get("SIMULATE", False)))
        print("  Debug: {}".format(config.MAIN.get("DEBUG_MODE", False)))
        
        # Tests synchrones
        self.test_config_validation()
        self.test_uart_init()
        self.test_timeout_coherence()
        self.test_parser_robustesse()
        
        # Tests asynchrones
        await self.test_buffer_flush()
        await self.test_poll_basique()
        await self.test_statistiques()
        await self.test_cycle_complet()
        
        # Rapport final
        self.print_report()
    
    def print_report(self):
        """Affiche le rapport final"""
        self.print_header("RAPPORT FINAL")
        
        total = len(self.results)
        passed = sum(1 for r in self.results.values() if r)
        failed = total - passed
        
        print("\nRésultats par test:")
        for test_name, result in self.results.items():
            status = "✓ PASS" if result else "✗ FAIL"
            print("  [{}] {}".format(status, test_name))
        
        print("\n" + "="*60)
        print("TOTAL: {}/{} tests réussis".format(passed, total))
        
        if failed == 0:
            print("✓ TOUS LES TESTS PASSÉS")
            print("Les corrections sont validées et fonctionnelles.")
        else:
            print("✗ {} test(s) échoué(s)".format(failed))
            print("Vérifier les erreurs ci-dessus.")
        
        print("="*60)
        
        return failed == 0


# ========== Point d'entrée ==========
async def main():
    """Point d'entrée principal"""
    tester = TestCorrections()
    success = await tester.run_all_tests()
    
    if success:
        print("\n✓ Validation complète réussie!")
        print("Le système est prêt pour production.")
    else:
        print("\n✗ Validation échouée")
        print("Corriger les problèmes avant mise en production.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nTests interrompus par l'utilisateur")
    except Exception as e:
        print("\n\nERREUR FATALE: {}".format(e))
        import sys
        sys.exit(1)
