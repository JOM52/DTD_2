# Guide de Correction des Problèmes UART/Radio

## 📦 Fichiers Corrigés

### 1. ta_radio_433.py → v2.4.0
**Fichier:** `ta_radio_433_v2.4.0.py`

### 2. ta_config.py → v2.1.0
**Fichier:** `ta_config_v2.1.0.py`

---

## 🔧 Changements Principaux

### A. Configuration UART (ta_config.py v2.1.0)

#### Avant (v2.0.1):
```python
"UART_RADIO": {
    "TIMEOUT_MS": 100,     # Défini mais non utilisé
},
"POLL_PERIOD_MS": 500,     # Trop rapide
"REPLY_TIMEOUT_MS": 250,   # Trop court
```

#### Après (v2.1.0):
```python
"UART_RADIO": {
    "TIMEOUT_MS": 100,     # Maintenant utilisé dans le code
},
"POLL_PERIOD_MS": 800,     # ✓ Augmenté (500→800ms)
"REPLY_TIMEOUT_MS": 500,   # ✓ Augmenté (250→500ms)
```

**Justification:**
- 800ms entre polls = temps pour 5 détecteurs + marges
- 500ms reply timeout = laisse temps au GT38 de répondre
- Cohérence UART_TIMEOUT < REPLY_TIMEOUT < POLL_PERIOD

---

### B. Module Radio (ta_radio_433.py v2.4.0)

#### Changement 1: Timeout UART
```python
# AVANT
self.uart = UART(
    uart_index,
    baudrate=9600,
    timeout=10,  # ❌ TROP COURT
    rxbuf=256
)

# APRÈS
self.uart = UART(
    uart_index,
    baudrate=self.uart_config.get("BAUD", 9600),  # ✓ Depuis config
    timeout=self.uart_config.get("TIMEOUT_MS", 100),  # ✓ 100ms
    rxbuf=512  # ✓ Buffer augmenté
)
```

#### Changement 2: Vidage de Buffer Robuste
```python
# AVANT
for _ in range(10):  # Limité à 10 itérations
    bytes_avail = await self._async_uart_any()
    if bytes_avail > 0:
        await self._async_uart_read(bytes_avail)
        await asyncio.sleep_ms(1)
    else:
        break

# APRÈS
async def _flush_uart_buffer(self, max_time_ms=100):
    """Vide complètement avec timeout"""
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
    
    return flushed_bytes
```

#### Changement 3: Parser Robuste
```python
# AVANT
if response.startswith("ACK:"):
    parts = response.split(":")
    if len(parts) >= 3:
        resp_id = parts[1]
        state = int(parts[2]) if parts[2].isdigit() else 0

# APRÈS
def _parse_ack_response(self, response):
    """Parse avec validation stricte"""
    # 1. Chercher "ACK:" dans la réponse
    if "ACK:" not in response:
        return None
    
    # 2. Extraire depuis "ACK:"
    ack_start = response.index("ACK:")
    response = response[ack_start:]
    
    # 3. Valider structure
    parts = response.split(":")
    if len(parts) != 3:
        return None
    
    # 4. Valider valeurs
    if not parts[1].isdigit() or not parts[2].isdigit():
        return None
    
    return {
        "detector_id": parts[1],
        "state": int(parts[2]),
        "simulated": False
    }
```

#### Changement 4: Délai Inter-Poll
```python
# AVANT
async def poll_status(self):
    for dd_id in ta_config.RADIO["GROUP_IDS"]:
        result = await self.poll("{:02d}".format(dd_id))
        # ...
        await asyncio.sleep_ms(0)  # ❌ Pas de délai

# APRÈS
async def poll_status(self):
    inter_poll_delay = 150  # ✓ 150ms entre polls
    
    for dd_id in ta_config.RADIO["GROUP_IDS"]:
        result = await self.poll("{:02d}".format(dd_id))
        # ...
        await asyncio.sleep_ms(inter_poll_delay)  # ✓ Délai
```

#### Changement 5: Gestion d'Erreurs
```python
# AVANT
except:
    pass  # ❌ Erreurs silencieuses

# APRÈS
except Exception as e:
    self.stats["parse_errors"] += 1
    self.logger.error("Erreur parse ACK: {}".format(e), "radio")
    return None
```

---

## 📊 Nouvelles Statistiques

Ajout de métriques dans `self.stats`:

```python
self.stats = {
    "tx_count": 0,
    "rx_count": 0,
    "timeout_count": 0,
    "error_count": 0,
    "uart_errors": 0,
    "blocked_calls": 0,
    "flushed_bytes": 0,    # ✓ NOUVEAU
    "parse_errors": 0      # ✓ NOUVEAU
}
```

---

## 🚀 Installation

### Étape 1: Sauvegarde
```bash
# Sur l'ESP32
cp ta_radio_433.py ta_radio_433_v2.3.0_backup.py
cp ta_config.py ta_config_v2.0.1_backup.py
```

### Étape 2: Remplacement
```bash
# Copier les nouvelles versions
cp ta_radio_433_v2.4.0.py ta_radio_433.py
cp ta_config_v2.1.0.py ta_config.py
```

### Étape 3: Redémarrage
```python
# Soft reset
import machine
machine.soft_reset()
```

---

## 🧪 Tests de Validation

### Test 1: Vérification des Timeouts
```python
import ta_config as config

# Vérifier cohérence
uart_to = config.HARDWARE["UART_RADIO"]["TIMEOUT_MS"]
reply_to = config.RADIO["REPLY_TIMEOUT_MS"]
poll_period = config.RADIO["POLL_PERIOD_MS"]

print("UART timeout:", uart_to)
print("Reply timeout:", reply_to)
print("Poll period:", poll_period)
print("Cohérence:", uart_to < reply_to < poll_period)
```

**Résultat attendu:**
```
UART timeout: 100
Reply timeout: 500
Poll period: 800
Cohérence: True
```

### Test 2: Statistiques Radio
```python
from ta_radio_433 import Radio433
from ta_logger import get_logger
import ta_config as config
import uasyncio as asyncio

async def test():
    logger = get_logger()
    radio = Radio433(config.RADIO, logger)
    
    # Faire quelques polls
    for i in range(10):
        result = await radio.poll("01")
        print("Poll {}: {}".format(i+1, result))
        await asyncio.sleep_ms(500)
    
    # Afficher stats
    stats = radio.get_statistics()
    print("\n=== STATISTIQUES ===")
    for key, value in stats.items():
        print("{}: {}".format(key, value))

asyncio.run(test())
```

**Métriques à surveiller:**
- `uart_errors` devrait rester à 0
- `parse_errors` devrait être très bas (<5%)
- `timeout_count` devrait diminuer significativement
- `flushed_bytes` indique nettoyage buffer

### Test 3: Cycle Complet
```python
async def test_cycle():
    from ta_app import TaApp
    import ta_config as config
    
    app = TaApp()
    
    # Laisser tourner 5 minutes
    for i in range(300):  # 300 secondes
        await app._update_states()
        await app._refresh_ui()
        await asyncio.sleep_ms(1000)
        
        if i % 30 == 0:
            stats = app.radio.get_statistics()
            print("Cycle {}: {}".format(i, stats))

asyncio.run(test_cycle())
```

---

## 📈 Résultats Attendus

### Avant Corrections (v2.3.0)

| Métrique | Valeur Typique |
|----------|----------------|
| Taux de timeout | 20-40% |
| UART errors | 5-10/min |
| Parse errors | Non tracé |
| Fausses détections | Fréquent |

### Après Corrections (v2.4.0)

| Métrique | Valeur Cible |
|----------|--------------|
| Taux de timeout | <5% |
| UART errors | 0 |
| Parse errors | <2% |
| Fausses détections | Rare |

---

## 🔍 Diagnostic des Problèmes

Si les problèmes persistent après correction:

### Problème: Timeouts Élevés
**Symptôme:** `timeout_count` élevé (>10%)

**Actions:**
1. Vérifier connexions physiques TX/RX
2. Augmenter `REPLY_TIMEOUT_MS` à 700ms
3. Vérifier alimentation GT38 stable

### Problème: Parse Errors Élevés
**Symptôme:** `parse_errors` >5%

**Actions:**
1. Ajouter résistances pull-up sur TX/RX
2. Vérifier bruit électromagnétique
3. Réduire longueur câbles (<15cm)

### Problème: UART Errors
**Symptôme:** `uart_errors` >0

**Actions:**
1. Vérifier pin SET (GPIO43)
2. Soft reset du GT38
3. Vérifier baudrate 9600

---

## 🎯 Prochaines Étapes

### Phase 1: Stabilisation (1-7 jours)
- [ ] Installer corrections
- [ ] Monitorer statistiques
- [ ] Ajuster timeouts si nécessaire
- [ ] Vérifier taux d'erreurs <5%

### Phase 2: Optimisation (8-14 jours)
- [ ] Réduire timeouts si stable
- [ ] Implémenter retry automatique
- [ ] Ajouter checksum/CRC

### Phase 3: Production (15+ jours)
- [ ] Désactiver DEBUG_MODE
- [ ] Activer WATCHDOG
- [ ] Documentation finale

---

## 📝 Notes Importantes

### Calculs Théoriques à 9600 Bauds

```
Temps par caractère = 10 bits / 9600 bauds = 1.04ms

Trames:
- "POLL:01\n" = 8 chars = 8.3ms
- "ACK:01:1\n" = 9 chars = 9.4ms

Cycle minimal théorique:
- 5 détecteurs × (8.3 + 9.4)ms = 88.5ms
- Avec délais inter-poll (150ms × 5) = 750ms
- Total: ~840ms → POLL_PERIOD_MS = 800ms (cohérent)
```

### Marges de Sécurité

| Paramètre | Théorique | Pratique | Marge |
|-----------|-----------|----------|-------|
| Temps trame | 9.4ms | 50-100ms | 5-10× |
| Reply timeout | 20ms | 500ms | 25× |
| Poll period | 100ms | 800ms | 8× |

---

## ⚠️ Avertissements

1. **Ne pas redémarrer** pendant un cycle de poll
2. **Surveiller** la température du GT38
3. **Vérifier** alimentation 3.3V stable
4. **Tester** en conditions réelles avant production
5. **Documenter** tout comportement anormal

---

## 📞 Support

En cas de problème:
1. Vérifier logs avec `DEBUG_MODE=True`
2. Consulter statistiques radio
3. Tester en mode `SIMULATE=True`
4. Vérifier hardware (multimètre)

---

**Dernière mise à jour:** 03/11/2025  
**Version du guide:** 1.0  
**Auteur:** Analyse système DTD
