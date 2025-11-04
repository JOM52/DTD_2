# Guide d'Utilisation - Démarrage Automatique DD

## 📋 Vue d'Ensemble

Le système de démarrage automatique permet :
- ✅ Démarrage automatique du DD à l'alimentation
- ✅ Délai de 3 secondes pour interrompre (Ctrl+C)
- ✅ Feedback LED visuel
- ✅ Mode debug facile avec Thonny

---

## 📁 Fichiers Nécessaires

```
/                    (racine ESP32)
├── boot.py         ← Démarrage auto (ce fichier)
├── dd_main.py      ← Script principal DD v1.7.0
└── config.py       ← Configuration (DETECTOR_ID)
```

---

## 🚀 Installation

### Étape 1: Copier les Fichiers

```python
# Dans Thonny, copier vers l'ESP32:
# 1. boot.py           → /boot.py
# 2. dd_main_v1.7.0.py → /dd_main.py
# 3. config.py         → /config.py
```

### Étape 2: Vérifier config.py

```python
# config.py doit contenir:
DETECTOR_ID = "01"  # ou "02", "03", "04" selon le DD
```

### Étape 3: Tester

```python
# Redémarrer l'ESP32
import machine
machine.reset()
```

---

## 🎬 Comportement au Démarrage

### Démarrage Normal (Auto)

```
============================================================
BOOT DD - Démarrage automatique avec délai d'interruption
============================================================

[BOOT] Informations système:
[BOOT]   MicroPython: 3.4.0
[BOOT]   Fichiers racine: boot.py, dd_main.py, config.py
[BOOT]   ✓ dd_main.py présent
[BOOT]   ✓ config.py présent
[BOOT]   Mémoire libre: 112640 bytes

[BOOT] Démarrage automatique activé
[BOOT] Appuyez sur Ctrl+C dans les 3s pour interrompre
[BOOT] LED clignote pendant le délai...

[BOOT] Démarrage dans 3s... (Ctrl+C pour annuler)
[BOOT] Démarrage dans 2s... (Ctrl+C pour annuler)
[BOOT] Démarrage dans 1s... (Ctrl+C pour annuler)
[BOOT] Délai écoulé - Lancement du script principal...
============================================================

[DD] Démarrage v1.7.0 PRODUCTION
[DD] ID: 01
...
```

**LED :** Clignote rapidement pendant les 3 secondes

---

### Interruption par Utilisateur (Ctrl+C)

```
[BOOT] Démarrage dans 2s... (Ctrl+C pour annuler)
^C

[BOOT] *** INTERROMPU PAR UTILISATEUR ***
[BOOT] Démarrage automatique annulé
[BOOT] Vous êtes maintenant en mode REPL
[BOOT] Pour lancer manuellement: import dd_main
============================================================

>>>  ← Mode REPL actif
```

**LED :** 5 clignotements rapides puis éteinte

---

### Erreur de Démarrage

```
[BOOT] Lancement de dd_main...
============================================================

[BOOT] ERREUR lors du lancement de dd_main:
[BOOT] ImportError: no module named 'config'

Traceback (most recent call last):
  ...

[BOOT] Le script n'a pas pu démarrer
[BOOT] Vous êtes en mode REPL pour debug
============================================================

>>>  ← Mode REPL pour corriger
```

**LED :** 10 clignotements puis éteinte

---

## 🔧 Utilisation avec Thonny

### Scénario 1: Premier Flash / Installation

```
1. Connecter ESP32 à l'USB
2. Ouvrir Thonny
3. Sélectionner port série (Tools > Options > Interpreter)
4. Attendre 3 secondes OU appuyer sur Ctrl+C
5. Mode REPL actif
6. Copier boot.py, dd_main.py, config.py
7. Tester: machine.reset()
```

### Scénario 2: Mise à Jour dd_main.py

```
1. Connecter ESP32
2. Dans les 3 secondes: Ctrl+C
3. Mode REPL actif
4. Copier nouveau dd_main.py
5. Tester: import dd_main
6. Si OK: machine.reset()
```

### Scénario 3: Debug / Modification

```
1. Connecter ESP32
2. Ctrl+C pendant les 3 secondes
3. Mode REPL
4. Modifier code
5. Lancer manuellement:
   >>> import dd_main
6. Observer logs
7. Corriger si nécessaire
```

### Scénario 4: Désactiver Auto-Start Temporairement

Option A: Interruption à chaque boot (Ctrl+C)

Option B: Modifier boot.py:
```python
AUTO_START_ENABLED = False  # Changer True → False
```

---

## 🎛️ Configuration boot.py

### Paramètres Ajustables

```python
# Activer/désactiver auto-start
AUTO_START_ENABLED = True    # True = auto, False = manuel

# Délai avant démarrage (millisecondes)
INTERRUPT_DELAY_MS = 3000    # 3 secondes (recommandé)
                             # 2000 = 2s (plus rapide)
                             # 5000 = 5s (plus de temps)

# Pin LED pour feedback
LED_PIN = 2                  # GPIO2 (LED intégrée ESP32)

# Script à lancer
MAIN_SCRIPT = "dd_main"      # Sans .py
```

### Exemples de Configuration

**Production (rapide) :**
```python
AUTO_START_ENABLED = True
INTERRUPT_DELAY_MS = 2000    # 2s seulement
```

**Développement (plus de temps) :**
```python
AUTO_START_ENABLED = True
INTERRUPT_DELAY_MS = 5000    # 5s pour Ctrl+C
```

**Debug permanent :**
```python
AUTO_START_ENABLED = False   # Jamais d'auto-start
```

---

## 🔍 Troubleshooting

### Problème: DD ne démarre pas automatiquement

**Vérifications :**
1. ✓ boot.py présent à la racine ?
   ```python
   >>> import os
   >>> 'boot.py' in os.listdir()
   True
   ```

2. ✓ AUTO_START_ENABLED = True ?
   ```python
   >>> import boot
   >>> boot.AUTO_START_ENABLED
   True
   ```

3. ✓ dd_main.py présent ?
   ```python
   >>> 'dd_main.py' in os.listdir()
   True
   ```

4. ✓ Pas d'erreurs dans dd_main.py ?
   ```python
   >>> import dd_main
   # Observer s'il y a des erreurs
   ```

### Problème: Impossible d'interrompre avec Ctrl+C

**Causes possibles :**
- Thonny pas connecté au bon port
- Délai trop court (augmenter INTERRUPT_DELAY_MS)
- Appuyer trop tard (après les 3 secondes)

**Solutions :**
1. Hard reset physique (bouton RESET sur ESP32)
2. Débrancher/rebrancher USB rapidement
3. Dans Thonny: Stop/Restart backend (bouton rouge)

### Problème: LED ne clignote pas

**Normal si :**
- ESP32 n'a pas de LED sur GPIO2
- Pin LED incorrecte dans config

**Solution :**
- Changer LED_PIN dans boot.py
- Ou ignorer (fonctionnement normal sans LED)

---

## 📊 Séquence de Boot Complète

```
[T=0ms]     Alimentation ESP32
            ↓
[T=50ms]    MicroPython boot
            ↓
[T=200ms]   Exécution boot.py
            ↓
            - Affiche info système
            - Vérifie fichiers
            - Affiche mémoire
            ↓
[T=300ms]   Début délai interruption
            LED commence à clignoter
            Affiche: "Démarrage dans 3s..."
            ↓
[T=800ms]   "Démarrage dans 2s..."
            ↓
[T=1300ms]  "Démarrage dans 1s..."
            ↓
[T=1800ms]  Ctrl+C possible ici ────┐
            ↓                         │
[T=3300ms]  Délai écoulé            │
            LED pattern démarrage    │
            ↓                         │
            import dd_main           │
            ↓                         │
[T=3500ms]  dd_main.py actif        │
            ↓                         │
            Boucle principale        │
                                      │
                                      ↓
                                [Mode REPL]
                                Si Ctrl+C pressé
```

---

## 🎯 Recommandations

### Pour Production
```python
AUTO_START_ENABLED = True
INTERRUPT_DELAY_MS = 2000     # 2s suffisant
```
- Démarrage rapide
- Délai court pour redémarrage après panne

### Pour Développement
```python
AUTO_START_ENABLED = True
INTERRUPT_DELAY_MS = 5000     # 5s confortable
```
- Plus de temps pour Ctrl+C
- Facilite modifications fréquentes

### Pour Debug Intensif
```python
AUTO_START_ENABLED = False
```
- Pas d'auto-start
- Contrôle total
- Lancer manuellement quand prêt

---

## 💡 Astuces

### Astuce 1: Test Rapide Sans Reset Complet

```python
# En mode REPL, tester directement:
>>> import dd_main

# Si ça plante, Ctrl+C puis corriger
# Pas besoin de reset complet
```

### Astuce 2: Voir les Logs de Boot

```python
# Dans Thonny, garder fenêtre Shell visible
# Au reset, tous les logs de boot.py s'affichent
# Utile pour debug
```

### Astuce 3: Auto-Start Conditionnel

```python
# Dans boot.py, ajouter condition:
try:
    import debug_flag
    AUTO_START_ENABLED = not debug_flag.DEBUG_MODE
except:
    AUTO_START_ENABLED = True
```

### Astuce 4: Script de Maintenance

```python
# maintenance.py - À créer dans Thonny
import machine
import os

def safe_reset():
    """Reset avec info"""
    print("Reset dans 1 seconde...")
    import time
    time.sleep(1)
    machine.reset()

def disable_autostart():
    """Désactiver auto-start temporairement"""
    # Renommer boot.py
    os.rename("boot.py", "boot.py.disabled")
    print("Auto-start désactivé (boot.py renommé)")
    
def enable_autostart():
    """Réactiver auto-start"""
    os.rename("boot.py.disabled", "boot.py")
    print("Auto-start activé")
    safe_reset()
```

---

## 📞 Support

Si problèmes persistent :
1. Vérifier tous les fichiers présents
2. Tester dd_main.py en mode manuel
3. Vérifier logs d'erreur complets
4. Hard reset ESP32

---

**Version du guide :** 1.0  
**Compatible avec :** boot.py v1.0, dd_main.py v1.7.0  
**Date :** 04/11/2025
