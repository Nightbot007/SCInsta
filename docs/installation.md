# Installation in Home Assistant

Schritt für Schritt für dein Zimmer: 4× Philips Hue, 3× Govee, 2× FancyLEDs.
Dauer etwa 30–45 Minuten. Voraussetzung: Home Assistant ab Version 2024.10.

## 1. Lampen in Home Assistant einbinden

### Philips Hue (Hue Play Kommode, Hue Play Treppenregal, 2× Hue am Regal)

1. **Einstellungen → Geräte & Dienste.** Meist wird die Hue Bridge schon unter
   „Entdeckt“ angezeigt → **Konfigurieren**. Sonst unten rechts
   **+ Integration hinzufügen** → „Philips Hue“.
2. Wenn Home Assistant danach fragt: den runden Knopf auf der Hue Bridge drücken.
3. Alle Hue-Lampen erscheinen als `light.…`. Hue-Räume und -Zonen tauchen
   ebenfalls als Lampen auf – die werden nicht gebraucht.

### Govee (Regal rechts oben, Regal rechts unten, Floor Lamp Pro)

1. In der **Govee Home App** jedes der drei Geräte öffnen → Zahnrad
   (Einstellungen) → **LAN Control** einschalten. Home Assistant und die Lampen
   müssen im selben Netzwerk sein.
2. In Home Assistant: **+ Integration hinzufügen** → **„Govee lights local“**.
   Sie findet alle Geräte mit LAN Control automatisch.
3. Fehlt „LAN Control“ bei einem Gerät (möglich bei der Floor Lamp Pro), kann
   es die lokale Schnittstelle nicht. Dann:
   - Bietet die Govee-App für das Gerät **Matter** an: in Home Assistant unter
     **Einstellungen → Geräte & Dienste → Geräte → Gerät hinzufügen → Matter**
     einbinden.
   - Sonst bleibt nur die Govee-Cloud. Sag mir Bescheid, dann suchen wir die
     passende Integration. Über die Cloud ist die Lampe etwas träger, für die
     Lichtstimmung reicht das.

### FancyLEDs (TV-Backlight, Kommode-Unterbeleuchtung)

Die FancyLEDs-Geräte sind Tuya-Geräte und kommen über die Smart-Life-App in
Home Assistant.

1. **Smart Life** App installieren. Sind die Geräte bisher in der
   FancyLEDs-App: dort entfernen und in Smart Life neu hinzufügen (Gerät in den
   Kopplungsmodus bringen, siehe Anleitung des Geräts).
2. In Smart Life: **Ich → Zahnrad → Konto und Sicherheit → User-Code** – den
   Code anzeigen lassen.
3. In Home Assistant: **+ Integration hinzufügen** → **„Tuya“** → User-Code
   eingeben → den angezeigten QR-Code mit der Smart-Life-App scannen
   (Plus oben rechts → Scannen) → bestätigen.

## 2. Lampen umbenennen

Die Lichtstimmung erwartet diese Entity-IDs. Am einfachsten benennst du die
Lampen in Home Assistant so um – dann musst du keine Datei anpassen und kannst
spätere Updates einfach überschreiben.

| Lampe | Entity-ID |
|---|---|
| Hue Play auf der Kommode | `light.hue_play_kommode` |
| TV-Backlight (FancyLEDs) | `light.tv_backlight` |
| Kommode, Unterbeleuchtung (FancyLEDs) | `light.kommode_unterbeleuchtung` |
| IKEA-Regal rechts vom TV, unten (Govee) | `light.regal_rechts_unten` |
| IKEA-Regal rechts vom TV, oben (Govee) | `light.regal_rechts_oben` |
| Floor Lamp Pro am Fenster (Govee) | `light.govee_floor_lamp` |
| Hue Play im Treppenregal | `light.hue_play_treppenregal` |
| Hue unten am Regal überm Bett, rechts | `light.hue_regal_rechts` |
| Hue unten am Regal überm Bett, links | `light.hue_regal_links` |

So geht's: **Einstellungen → Geräte & Dienste → Reiter „Entitäten“** → Lampe
suchen → anklicken → **Zahnrad** → Feld **„Entitäts-ID“** ändern →
**Aktualisieren**. Welche Lampe welche ist, siehst du, wenn du sie im selben
Dialog ein- und ausschaltest.

## 3. Packages einschalten

1. **Einstellungen → Add-ons → Add-on Store** → **„File editor“** installieren,
   starten, „In Seitenleiste anzeigen“ aktivieren.
2. Im File editor die Datei `configuration.yaml` öffnen und Folgendes ergänzen:
   ```yaml
   homeassistant:
     packages: !include_dir_named packages
   ```
   Steht `homeassistant:` schon in der Datei, nur die Zeile
   `packages: !include_dir_named packages` eingerückt darunter setzen – der
   Schlüssel `homeassistant:` darf nur einmal vorkommen.
3. Speichern.

## 4. Dateien holen

### Variante A: mit dem Terminal (schnell)

1. **Einstellungen → Add-ons → Add-on Store** → **„Terminal & SSH“**
   installieren, starten, „In Seitenleiste anzeigen“.
2. Im Terminal einfügen:
   ```bash
   cd /homeassistant 2>/dev/null || cd /config
   ls configuration.yaml
   mkdir -p packages custom_templates
   BASIS=https://raw.githubusercontent.com/Nightbot007/SCInsta/main/homeassistant
   curl -fsSL -o packages/lichtstimmung.yaml            $BASIS/packages/lichtstimmung.yaml
   curl -fsSL -o custom_templates/lichtstimmung.jinja      $BASIS/custom_templates/lichtstimmung.jinja
   curl -fsSL -o custom_templates/lichtstimmung_buch.jinja $BASIS/custom_templates/lichtstimmung_buch.jinja
   ls -l packages custom_templates
   ```
   `ls configuration.yaml` muss die Datei anzeigen. Sonst bist du im falschen
   Ordner, dann bitte nicht weitermachen und mir schreiben.

### Variante B: ohne SSH, mit dem File editor

1. Am PC die drei Dateien von GitHub herunterladen: Datei öffnen, dann rechts
   oben auf **„Download raw file“** (Pfeil nach unten) klicken.
   - [`lichtstimmung.yaml`](https://github.com/Nightbot007/SCInsta/blob/main/homeassistant/packages/lichtstimmung.yaml)
   - [`lichtstimmung.jinja`](https://github.com/Nightbot007/SCInsta/blob/main/homeassistant/custom_templates/lichtstimmung.jinja)
   - [`lichtstimmung_buch.jinja`](https://github.com/Nightbot007/SCInsta/blob/main/homeassistant/custom_templates/lichtstimmung_buch.jinja)
2. Im File editor oben links auf das **Ordner-Symbol** klicken. Du bist jetzt
   im Ordner `/homeassistant` (bzw. `/config`), in dem `configuration.yaml` liegt.
3. Ordner anlegen: **„Neuer Ordner“** → `packages`. Noch einmal → `custom_templates`.
4. In den Ordner `packages` wechseln → **Hochladen** (Wolke mit Pfeil) →
   `lichtstimmung.yaml` auswählen.
5. In den Ordner `custom_templates` wechseln → **Hochladen** →
   `lichtstimmung.jinja` und `lichtstimmung_buch.jinja` auswählen.
6. Prüfen: Die Dateinamen müssen exakt so heißen. Hat der Browser `(1)` oder
   `.txt` angehängt, die Datei im File editor umbenennen.

## 5. Prüfen und neu starten

1. **Entwicklerwerkzeuge → YAML → „Konfiguration prüfen“** – muss grün sein.
2. **Einstellungen → System → ⋮ oben rechts → Home Assistant neu starten**.
3. Danach **Entwicklerwerkzeuge → Template**, links alles löschen und einfügen:
   ```jinja
   {% from 'lichtstimmung.jinja' import pruefen %}{{ pruefen() }}
   ```
   Rechts müssen alle 9 Lampen mit „Farbe“ stehen, ohne ❌.
   Ein ❌ heißt: Entity-ID stimmt nicht – zurück zu Schritt 2.

## 6. Dashboard-Karte

Dashboard öffnen → **Stift (Bearbeiten)** → **+ Karte hinzufügen** → ganz unten
**„Manuell“** → Inhalt von
[`homeassistant/dashboard/lichtstimmung-karte.yaml`](../homeassistant/dashboard/lichtstimmung-karte.yaml)
einfügen → **Speichern**.

Jetzt **„An / Aus“** in der Karte drücken: Alle 9 Lampen gehen in der ersten
Stimmung an. Nochmal drücken = alles aus. Beim nächsten „An“ kommt der nächste
Modus.

## 7. Deine Taste

Ohne YAML, direkt in der Oberfläche:

**Einstellungen → Automationen & Szenen → + Automation erstellen → Neue
Automation**

- **Auslöser:** „Gerät“ → deine Taste → „Taste gedrückt“ (bzw. „kurz
  gedrückt“)
- **Aktion:** „Skript ausführen“ bzw. Skript auswählen →
  **„Lichtstimmung – Taste (alles an/aus)“**
- Speichern.

Die virtuelle Taste in der Dashboard-Karte funktioniert weiterhin.

## 8. Feinschliff

- **Gewitter-Blitze:** Schalter in der Karte einschalten. Es blitzen nur die
  Hue-Lampen, weil die lokal sofort reagieren.
- **HDMI-Sync der FancyLEDs-Box:** Läuft der TV im Sync-Modus, setzt ein
  Moduswechsel das Backlight auf die Stimmungsfarbe. Soll der Sync Vorrang
  haben, sag Bescheid. Dann lasse ich das Backlight aus, solange der TV läuft.
- **Neue Farben aus dem Buch:** Nummer im Buch suchen und in
  `custom_templates/lichtstimmung.jinja` beim Modus unter `'buch'` eintragen,
  dann das Skript **„Lichtstimmung – Konfiguration neu laden“** ausführen.

## Spätere Updates

Die drei `curl`-Befehle aus Schritt 4 nochmal ausführen. Danach:

- nur `.jinja` geändert → Skript **„Lichtstimmung – Konfiguration neu laden“**
- `lichtstimmung.yaml` geändert → **Entwicklerwerkzeuge → YAML → „Alle
  YAML-Konfigurationen“ neu laden** oder neu starten

Achtung: Das überschreibt auch eigene Änderungen an `lichtstimmung.jinja`
(z. B. zusätzliche Buch-Nummern). Solche Änderungen am besten hier im Repo
machen lassen.
