# Lichtstimmung für Home Assistant

Alle Lampen eines Raums leuchten gleichzeitig in **unterschiedlichen, zueinander
passenden Farben** – je nach Modus (Cozy, Cyberpunk, Ruhig, Regen / Gewitter, …).

- **Eine Taste** schaltet alles aus. Nur dann wechselt beim nächsten Einschalten
  der Modus.
- **Einzelne Lampen** an- und ausschalten ändert den Modus nie.
- **Favoriten:** Gefällt dir eine Kombination, speicherst du sie per Knopfdruck.
  Sie taucht als „★ Name“ in der Modusauswahl auf.
- Läuft komplett **in Home Assistant**: kein Add-on, keine HACS-Integration,
  kein externer Server.

## Wie es funktioniert

| Baustein | Aufgabe |
|---|---|
| `custom_templates/lichtstimmung.jinja` | **Deine Konfiguration:** Lampen (in Raumreihenfolge) und Farbpaletten der Modi |
| `packages/lichtstimmung.yaml` | Logik: Helfer, Skripte, Automationen, Speicher-Sensoren |
| `dashboard/lichtstimmung-karte.yaml` | Fertige Dashboard-Karte |

**Farbverteilung:** Jeder Modus hat eine Palette (3–5 Farben). Benachbarte
Lampen bekommen benachbarte Palettenfarben. Bei jedem Einschalten wird die Palette
zufällig gedreht und der Farbton leicht gestreut, deshalb sieht es jedes Mal
etwas anders aus, bleibt aber stimmig. Lampen, die nur Weiß können, bekommen
die passende Farbtemperatur des Modus. Lampen, die nur dimmen können, bekommen
die passende Helligkeit.

**Taste und Moduswechsel:**

```
Taste ──► Lampe(n) an? ──ja──► alles aus + „Wechsel fällig“ merken
                      └─nein─► alles an ── Wechsel fällig? ──ja──► nächster Modus
                                                            └─nein─► gleiche Stimmung
```

Wird nach „alles aus“ über die Taste eine einzelne Lampe anders eingeschaltet
(App, Sprache, Wandschalter), startet auch das den nächsten Modus. Lampen, die
beim Moduswechsel aus waren, bekommen ihre Farbe, sobald sie eingeschaltet
werden.

## Installation

1. In der `configuration.yaml` Packages aktivieren (falls noch nicht geschehen):
   ```yaml
   homeassistant:
     packages: !include_dir_named packages
   ```
2. Dateien kopieren (z. B. mit dem File-Editor- oder Samba-Add-on):
   - `homeassistant/packages/lichtstimmung.yaml` → `/config/packages/`
   - `homeassistant/custom_templates/lichtstimmung.jinja` → `/config/custom_templates/`
3. In `lichtstimmung.jinja` unter **1) LAMPEN** deine Lampen eintragen.
4. Home Assistant **neu starten** (einmalig; später reicht das Skript
   „Lichtstimmung – Konfiguration neu laden“).
5. Prüfen: **Entwicklerwerkzeuge → Template** →
   `{% from 'lichtstimmung.jinja' import pruefen %}{{ pruefen() }}`
   zeigt, ob alle Lampen gefunden wurden und was sie können.
6. Taste anbinden: in `lichtstimmung.yaml` bei der Automation
   „Lichtstimmung – Taste gedrückt“ den passenden Auslöser einkommentieren
   (Beispiele für Hue, Zigbee2MQTT, ZHA sind drin). Bis dahin funktioniert die
   virtuelle Taste `input_button.lichtstimmung_taste` im Dashboard.
7. Dashboard-Karte aus `homeassistant/dashboard/lichtstimmung-karte.yaml` einfügen
   (Dashboard → Bearbeiten → Karte hinzufügen → Manuell).

Ab Home Assistant 2024.10 (neue `triggers:`/`actions:`-Schreibweise).

## Bedienung

| Was | Wie |
|---|---|
| Alles an/aus | Taste oder Skript „Lichtstimmung – Taste“ |
| Modus direkt wählen | Auswahl „Lichtstimmung“ |
| Gleicher Modus, neue Verteilung | Skript „Neu würfeln“ |
| Favorit speichern | optional Namen eintippen → „Als Favorit speichern“ (ohne Namen: z. B. „Cozy 04.10. 21:15“) |
| Favorit abrufen | in der Auswahl „★ Name“ wählen |
| Favorit löschen | Favorit auswählen (oder Namen eintippen) → „Favorit löschen“ |
| Zufällige statt feste Reihenfolge | Schalter „Zufällige Reihenfolge“ |
| Favoriten mit in den Wechsel nehmen | Schalter „Favoriten im Wechsel“ |
| Blitze bei Regen / Gewitter | Schalter „Gewitter-Blitze“ (ist anfangs aus) |

## Neuen Modus anlegen

In `lichtstimmung.jinja` unter **2) MODI** einen Block kopieren, Namen und
Farben ändern, dann „Lichtstimmung – Konfiguration neu laden“ ausführen.
Vorbereitet (mit `'aktiv': false`): Sonnenuntergang, Nordlicht, Ozean, Wald.

```jinja
'Kino': {
  'aktiv': true,
  'farben': [[230, 90], [250, 85], [210, 80]],   {# [Farbton 0–360, Sättigung 0–100] #}
  'hell': {'standard': 15, 'decke': 0, 'streifen': 25},
  'kelvin': 2700,
  'streuung': 4,
  'uebergang': 3,
},
```

Farbton-Orientierung: 0 Rot · 30 Orange · 60 Gelb · 120 Grün · 180 Cyan ·
220 Blau · 270 Violett · 300 Magenta · 330 Pink.

## Tipps

- **Smarte Lampen am Wandschalter:** In der Lampen-App bzw. in Zigbee2MQTT das
  Einschaltverhalten nach Stromausfall („power-on behavior“) auf **vorheriger
  Zustand** stellen. Sonst gehen sie nach dem Einschalten weiß an.
- Favoriten und der aktuelle Modus überstehen Neustarts. Gespeichert werden sie
  in den Attributen von `sensor.lichtstimmung_favoriten` bzw.
  `sensor.lichtstimmung_zustand`.
- Hast du Philips-Hue-Lampen und willst *nur* fertige Szenen, geht das auch mit
  der Hue-App. Der Modus-Wechsel per Taste und das Speichern beliebiger Lampen
  geht so aber nicht.

## Tests

Die Logik wird gegen ein echtes Home Assistant mit simulierten Lampen
(Farbe, nur Weiß, nur Helligkeit) getestet:

```bash
pip install -r requirements-test.txt
pytest
```

## Raum-Layout

Wie du mir dein Zimmer mit den Lampen schickst, steht in
[`docs/raum-layout.md`](docs/raum-layout.md).
