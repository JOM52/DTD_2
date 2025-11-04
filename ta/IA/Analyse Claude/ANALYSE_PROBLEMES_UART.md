# Analyse des Problèmes de Communication UART/Radio GT38

## Date: 03/11/2025

## Résumé Exécutif

Le système présente des pertes d'informations importantes au niveau de la communication UART avec le module GT38. Les détecteurs sont incorrectement détectés comme présents/absents. L'analyse révèle plusieurs problèmes critiques dans la gestion de l'UART.

---

## 🔴 PROBLÈMES IDENTIFIÉS

### 1. **Timeout UART Trop Court (CRITIQUE)**

**Localisation:** `ta_radio_433.py` ligne 73

```python
self.uart = UART(
    uart_index,
    baudrate=9600,
    tx=Pin(tx_pin),
    rx=Pin(rx_pin),
    timeout=10,  # ⚠️ PROBLÈME: 10ms est BEAUCOUP TROP COURT
    rxbuf=256
)
```

**Impact:**
- À 9600 bauds, la transmission d'une trame "ACK:01:1\n" (9 bytes) prend ~9.4ms
- Avec timeout=10ms, la lecture peut être coupée au milieu d'une trame
- Cela explique les détections erratiques

**Solution:** Augmenter à minimum 100ms

---

### 2. **Vidage de Buffer Insuffisant**

**Localisation:** `ta_radio_433.py` lignes 166-173

```python
# Vider buffer (avant envoi POLL)
for _ in range(10):  # ⚠️ Seulement 10 itérations
    bytes_avail = await self._async_uart_any()
    if bytes_avail > 0:
        await self._async_uart_read(bytes_avail)
        await asyncio.sleep_ms(1)
    else:
        break
```

**Problèmes:**
1. Si le buffer contient des données fragmentées de réponses précédentes, 10 itérations peuvent être insuffisantes
2. Le `sleep_ms(1)` entre lectures peut permettre à de nouvelles données d'arriver
3. Pas de timeout global pour cette opération

**Impact:**
- Données résiduelles contaminent les nouvelles réponses
- Parsing de trames incohérentes

---

### 3. **Gestion de Timeout Incohérente**

**Localisation:** `ta_radio_433.py` lignes 186-229

```python
timeout_ms = 1000  # Timeout global
timeout_start = time.ticks_ms()
response_buffer = bytearray()
loop_count = 0

while time.ticks_diff(time.ticks_ms(), timeout_start) < timeout_ms:
    loop_count += 1
    if loop_count > 100:  # ⚠️ Protection anti-blocage
        self.stats["blocked_calls"] += 1
        break
    # ...
    await asyncio.sleep_ms(10)  # 100 itérations × 10ms = 1000ms théorique
```

**Problèmes:**
1. La boucle peut faire jusqu'à 100 itérations (1000ms théorique)
2. Mais chaque itération avec `sleep_ms(10)` peut prendre plus de 10ms
3. Le compteur `loop_count > 100` peut déclencher avant le timeout de 1000ms
4. Double condition de sortie crée une confusion

**Impact:**
- Timeouts prématurés
- Statistiques `blocked_calls` incorrectes

---

### 4. **Pas de Synchronisation de Trames**

**Localisation:** `ta_radio_433.py` lignes 188-224

```python
response_buffer = bytearray()

while time.ticks_diff(...):
    # ...
    if bytes_available > 0:
        data = await self._async_uart_read(bytes_available)
        
        if data:
            response_buffer.extend(data)  # ⚠️ Ajout aveugle
            
            if b'\n' in response_buffer:
                try:
                    response = response_buffer.decode('utf-8', 'ignore').strip()
```

**Problèmes:**
1. Pas de recherche du début de trame (ex: "ACK:")
2. Si des données corrompues arrivent, elles sont concaténées
3. La détection `b'\n'` ne garantit pas une trame complète valide

**Exemple de cas d'échec:**
```
Buffer: "garb age ACK:01:1\n" 
→ Parsing réussit mais avec "garb age ACK:01:1" = parsing invalide
```

---

### 5. **Configuration UART Incohérente**

**Localisation:** `ta_config.py` lignes 38-46

```python
"UART_RADIO": {
    "INDEX": 2,
    "BAUD": 9600,          # ⚠️ Défini mais NON UTILISÉ
    "TX": 17,
    "RX": 18,
    "PIN_GT38_SET": 43,
    "TIMEOUT_MS": 100,     # ⚠️ Défini mais NON UTILISÉ
},
```

Le code utilise des valeurs hardcodées au lieu de la config:
- `baudrate=9600` (hardcodé)
- `timeout=10` (hardcodé, devrait être `TIMEOUT_MS`)

---

### 6. **Gestion d'Erreurs Incomplète**

**Localisation:** `ta_radio_433.py` lignes 206-224

```python
try:
    response = response_buffer.decode('utf-8', 'ignore').strip()
    self.logger.debug("← {}".format(response), "radio")
    
    if response.startswith("ACK:"):
        parts = response.split(":")
        if len(parts) >= 3:
            resp_id = parts[1]
            state = int(parts[2]) if parts[2].isdigit() else 0  # ⚠️ Défaut 0
            # ...
except:
    pass  # ⚠️ Erreurs silencieuses
```

**Problèmes:**
1. `except:` trop large - masque tous les types d'erreurs
2. Pas de logging des erreurs de parsing
3. Valeur par défaut `state = 0` peut être confondue avec un état valide

---

### 7. **Timing Entre Polls Inadapté**

**Localisation:** `ta_radio_433.py` lignes 240-262

```python
async def poll_status(self):
    results = []
    
    for dd_id in ta_config.RADIO["GROUP_IDS"]:
        result = await self.poll("{:02d}".format(dd_id))
        
        if result:
            # ...
        
        await asyncio.sleep_ms(0)  # ⚠️ Pas de délai entre polls
    
    return results
```

**Problème:**
- `asyncio.sleep_ms(0)` ne donne qu'un yield sans délai
- Les polls successifs peuvent se chevaucher si les réponses sont lentes
- Pas de temps de "repos" pour le module GT38

**Impact:**
- Collisions de trames
- Module GT38 peut ne pas avoir le temps de traiter

---

## 📊 ANALYSE DE LA CONFIGURATION

### Paramètres Critiques

| Paramètre | Valeur Actuelle | Valeur Recommandée | Justification |
|-----------|----------------|-------------------|---------------|
| UART timeout | 10ms | 100-200ms | Temps de transmission complet |
| POLL_PERIOD_MS | 500ms | 800-1000ms | Éviter saturation |
| REPLY_TIMEOUT_MS | 250ms | 500ms | GT38 peut être lent |
| Délai entre polls | 0ms | 100-200ms | Repos du module |

### Timing à 9600 bauds

- 1 caractère = ~1.04ms (10 bits: start + 8 data + stop)
- Trame "POLL:01\n" (8 chars) = ~8.3ms
- Trame "ACK:01:1\n" (9 chars) = ~9.4ms
- **Total théorique par poll:** 8.3 + 9.4 = ~17.7ms
- **Total avec marge:** ~30-50ms recommandé

---

## 🔧 CALCULS ET RECOMMANDATIONS

### Calcul du Timeout UART Optimal

```
Trame max attendue = "ACK:99:1\n" = 9 bytes
Temps transmission = 9 bytes × 1.04ms/byte = 9.36ms
Marge de sécurité = 3× (recommandation standard)
Timeout recommandé = 9.36 × 3 = 28ms
→ Arrondi à 50ms (confortable)
→ Ou 100ms si GT38 a latence de traitement
```

### Calcul du Poll Period

```
5 détecteurs
Temps par poll = 50ms (timeout) + 20ms (traitement)
Temps total cycle = 5 × 70ms = 350ms
Marge système = 2×
Poll period optimal = 700-800ms
```

---

## ✅ SOLUTIONS PROPOSÉES

### Solution 1: Configuration UART Robuste

```python
# Utiliser les valeurs de ta_config
self.uart = UART(
    uart_index,
    baudrate=self.uart_config.get("BAUD", 9600),
    tx=Pin(tx_pin),
    rx=Pin(rx_pin),
    timeout=self.uart_config.get("TIMEOUT_MS", 100),  # 100ms minimum
    rxbuf=512  # Augmenter buffer (256 → 512)
)
```

### Solution 2: Vidage de Buffer Amélioré

```python
async def _flush_uart_buffer(self, max_time_ms=100):
    """Vide complètement le buffer UART avec timeout"""
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
        self.logger.debug("Flushed {} bytes".format(flushed_bytes), "radio")
    
    return flushed_bytes
```

### Solution 3: Parser de Trames Robuste

```python
def _parse_ack_response(self, response):
    """Parse une réponse ACK avec validation stricte"""
    try:
        # Chercher début de trame valide
        if "ACK:" not in response:
            return None
        
        # Extraire depuis "ACK:"
        ack_start = response.index("ACK:")
        response = response[ack_start:]
        
        parts = response.split(":")
        if len(parts) != 3:
            self.logger.warning("ACK malformé: {}".format(response), "radio")
            return None
        
        detector_id = parts[1].strip()
        state_str = parts[2].strip()
        
        if not detector_id.isdigit() or not state_str.isdigit():
            self.logger.warning("ACK non-numérique: {}".format(response), "radio")
            return None
        
        return {
            "detector_id": detector_id,
            "state": int(state_str),
            "simulated": False
        }
        
    except Exception as e:
        self.logger.error("Erreur parse ACK: {}".format(e), "radio")
        return None
```

### Solution 4: Gestion du Timeout Simplifiée

```python
async def poll(self, detector_id):
    """Interroge un détecteur avec timeout unifié"""
    # ...
    
    # Attendre réponse avec timeout simple
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
                    
                    # Parser avec validation
                    result = self._parse_ack_response(response)
                    if result:
                        self.stats["rx_count"] += 1
                        return result
                    else:
                        # Trame invalide, continuer à attendre
                        response_buffer = bytearray()
        
        await asyncio.sleep_ms(5)  # Check toutes les 5ms
    
    # Timeout
    self.stats["timeout_count"] += 1
    return None
```

### Solution 5: Délais Entre Polls

```python
async def poll_status(self):
    """Interroge tous les détecteurs avec délai inter-poll"""
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
        
        # Délai important entre polls
        await asyncio.sleep_ms(inter_poll_delay)
    
    return results
```

---

## 🎯 PRIORITÉS DE CORRECTION

### Priorité 1 (CRITIQUE - Immédiat)
1. ✅ Augmenter timeout UART (10ms → 100ms)
2. ✅ Ajouter délai entre polls (0ms → 150ms)
3. ✅ Améliorer vidage de buffer

### Priorité 2 (IMPORTANT - Court terme)
4. ✅ Implémenter parser robuste avec validation
5. ✅ Simplifier logique de timeout
6. ✅ Augmenter POLL_PERIOD_MS (500 → 800ms)

### Priorité 3 (AMÉLIORATION - Moyen terme)
7. Ajouter checksum/CRC aux trames
8. Implémenter retry automatique
9. Moniteur de santé UART (diagnostics)

---

## 📈 MÉTRIQUES DE SUCCÈS

Après corrections, surveiller:

| Métrique | Avant | Cible |
|----------|-------|-------|
| Taux de timeout | >30% | <5% |
| UART errors | >10/min | 0 |
| Blocked calls | >5/min | 0 |
| Fausses détections | Fréquent | Rare |

---

## 🔬 TESTS RECOMMANDÉS

1. **Test unitaire de timing:**
   - Mesurer temps réel de transmission à 9600 bauds
   - Vérifier cohérence avec calculs théoriques

2. **Test de stress:**
   - Polls continus pendant 10 minutes
   - Vérifier stabilité des statistiques

3. **Test de corruption:**
   - Injecter bruit sur ligne UART
   - Vérifier robustesse du parser

4. **Test de latence GT38:**
   - Mesurer temps de réponse réel du module
   - Ajuster timeouts si nécessaire

---

## 📝 NOTES ADDITIONNELLES

### Considérations Hardware

1. **Qualité des connexions:**
   - Vérifier soudures TX/RX/GND
   - Câbles courts (<20cm recommandé)
   - Pas de parasites électromagnétiques

2. **Alimentation GT38:**
   - Vérifier stabilité du 3.3V
   - Condensateur de découplage recommandé

3. **Pull-up/Pull-down:**
   - Pin SET (GPIO43) correctement configuré
   - Résistances de pull si nécessaire

### Prochaines Étapes

1. Implémenter corrections priorité 1
2. Tester pendant 24h en conditions réelles
3. Analyser statistiques
4. Ajuster si nécessaire
5. Implémenter corrections priorité 2

---

**Fin du rapport d'analyse**
