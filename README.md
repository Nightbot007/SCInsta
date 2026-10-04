# Lichtstimmung für Home Assistant

Alle Lampen eines Raums leuchten gleichzeitig in **unterschiedlichen, zueinander
passenden Farben** – je nach Modus (Cozy, Cyberpunk, Ruhig, Regen / Gewitter,
Farbwörterbuch, …).

- **Farben aus dem Buch:** Die Kombinationen stammen aus Sanzo Wadas
  *A Dictionary of Color Combinations* (配色事典, Seigensha), dazu eigene
  Paletten. Angezeigt wird, welche Buch-Nummer gerade leuchtet, damit du sie im
  Buch nachschlagen kannst.

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
| `custom_templates/lichtstimmung.jinja` | **Deine Konfiguration:** Lampen (in Raumreihenfolge) und Modi (Buch-Nummern + eigene Paletten) |
| `custom_templates/lichtstimmung_buch.jinja` | Die 333 als Licht geeigneten Kombinationen des Buchs (erzeugt, nicht bearbeiten) |
| `packages/lichtstimmung.yaml` | Logik: Helfer, Skripte, Automationen, Speicher-Sensoren |
| `dashboard/lichtstimmung-karte.yaml` | Fertige Dashboard-Karte |

**Farbverteilung:** Bei jedem Einschalten wählt der Modus eine Kombination: aus
seiner Liste von Buch-Nummern oder aus deinen eigenen Paletten, nie zweimal
hintereinander dieselbe. Benachbarte Lampen bekommen benachbarte Farben der
Kombination, die Reihenfolge wird zufällig gedreht und der Farbton leicht
gestreut. So sieht es jedes Mal etwas anders aus, bleibt aber stimmig. Lampen,
die nur Weiß können, bekommen die Farbtemperatur des Modus. Lampen, die nur
dimmen können, bekommen die passende Helligkeit.

**Vom Buch zum Licht:** Die Druckfarben werden in Lampenfarben umgerechnet.
Der Farbton bleibt, blasse Farben werden etwas kräftiger, dunkle Farben leuchten
gedämpfter. Helle Neutraltöne (Weiß, Elfenbein) werden zu warmweißem Licht.
Schwarz und Grau lassen sich nicht leuchten und entfallen. 15 der 348
Kombinationen bestehen fast nur daraus und sind deshalb nicht dabei.

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

**Genaue Schritt-für-Schritt-Anleitung: [`docs/installation.md`](docs/installation.md)**
(Lampen einbinden, Entity-IDs, Dateien kopieren, Taste, Dashboard).

Kurzfassung:

1. Hue (Integration „Philips Hue“), Govee („Govee lights local“) und FancyLEDs
   (über Smart Life → Integration „Tuya“) in Home Assistant einbinden.
2. Lampen auf die Entity-IDs aus `lichtstimmung.jinja` umbenennen.
3. In `configuration.yaml`: `homeassistant: packages: !include_dir_named packages`
4. `lichtstimmung.yaml` → `/config/packages/`,
   `lichtstimmung.jinja` + `lichtstimmung_buch.jinja` → `/config/custom_templates/`
5. Neu starten, mit `pruefen()` kontrollieren, Dashboard-Karte einfügen.

Ab Home Assistant 2024.10.

## Dein Zimmer

Neun Lampen, im Uhrzeigersinn ab der Tür. In dieser Reihenfolge laufen die
Farben einer Kombination durch den Raum:

| # | Lampe | Marke | Entity-ID | Typ |
|---|---|---|---|---|
| 1 | Hue Play auf der Kommode | Philips Hue | `light.hue_play_kommode` | play |
| 2 | TV-Backlight | FancyLEDs | `light.tv_backlight` | tv |
| 3 | Kommode, Unterbeleuchtung | FancyLEDs | `light.kommode_unterbeleuchtung` | unterbau |
| 4 | IKEA-Regal rechts vom TV, unten | Govee | `light.regal_rechts_unten` | unterbau |
| 5 | IKEA-Regal rechts vom TV, oben | Govee | `light.regal_rechts_oben` | regal |
| 6 | Floor Lamp Pro am Fenster | Govee | `light.govee_floor_lamp` | steh |
| 7 | Hue Play im Treppenregal | Philips Hue | `light.hue_play_treppenregal` | play |
| 8 | Hue unten am Regal überm Bett, rechts | Philips Hue | `light.hue_regal_rechts` | regal |
| 9 | Hue unten am Regal überm Bett, links | Philips Hue | `light.hue_regal_links` | regal |

Über den Typ legt jeder Modus die Helligkeit fest. Ein Beispiel: Bei
Cyberpunk leuchten TV-Backlight und Unterbau kräftig, bei Ruhig ist alles
gedämpft. Gewitter-Blitze laufen nur über die vier Hue-Lampen.

## Bedienung

| Was | Wie |
|---|---|
| Alles an/aus | Taste oder Skript „Lichtstimmung – Taste“ |
| Modus direkt wählen | Auswahl „Lichtstimmung“ |
| Gleicher Modus, andere Kombination | Skript „Neu würfeln“ |
| Welche Buch-Kombination leuchtet? | Zeile „Kombination“ in der Karte, z. B. „Buch Nr. 236“ |
| Das ganze Buch durchstöbern | Modus „Farbwörterbuch“ + „Neu würfeln“, Treffer als Favorit speichern |
| Favorit speichern | optional Namen eintippen → „Als Favorit speichern“ (ohne Namen: z. B. „Cozy 04.10. 21:15“) |
| Favorit abrufen | in der Auswahl „★ Name“ wählen |
| Favorit löschen | Favorit auswählen (oder Namen eintippen) → „Favorit löschen“ |
| Zufällige statt feste Reihenfolge | Schalter „Zufällige Reihenfolge“ |
| Favoriten mit in den Wechsel nehmen | Schalter „Favoriten im Wechsel“ |
| Blitze bei Regen / Gewitter | Schalter „Gewitter-Blitze“ (ist anfangs aus) |

## Modi anpassen und neu anlegen

In `lichtstimmung.jinja` unter **2) MODI** einen Block kopieren, Namen ändern,
Buch-Nummern und/oder eigene Paletten eintragen, dann „Lichtstimmung –
Konfiguration neu laden“ ausführen. Vorbereitet (mit `'aktiv': false`):
Sonnenuntergang, Nordlicht, Ozean, Wald.

```jinja
'Kino': {
  'aktiv': true,
  'buch': [106, 139, 218],
  'eigene': [
    [[230, 90], [250, 85], [210, 80]],
  ],
  'eigene_anteil': 30,
  'hell': {'standard': 15, 'tv': 20, 'unterbau': 10},
  'kelvin': 2700,
  'streuung': 3,
  'uebergang': 3,
},
```

Innerhalb von `MODI` keine `{# … #}`-Kommentare schreiben, das ist dort ein
Syntaxfehler. Was die Felder bedeuten, steht im Kommentarblock darüber.

- **Buch-Nummern:** Die Nummer steht im Buch bei jeder Kombination
  (1–120: 2 Farben, 121–240: 3, 241–348: 4). `'buch': 'alle'` nimmt das ganze
  Buch. Die Listen der Modi sind nach Farbton, Sättigung und Helligkeit
  vorsortiert. Gefällt dir eine Kombination im Buch, trag ihre Nummer einfach
  dazu.
- **Eigene Paletten:** beliebig viele, je 2–5 Farben. Farbton-Orientierung:
  0 Rot · 30 Orange · 60 Gelb · 120 Grün · 180 Cyan · 220 Blau · 270 Violett ·
  300 Magenta · 330 Pink.
- Der Konfig-Check (`pruefen()`) meldet unbekannte oder als Licht ungeeignete
  Buch-Nummern.

Vorschläge passender Buch-Nummern für eine Stimmung:

```bash
python3 tools/buch_importieren.py --vorschlaege
```

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

## Quellen

- Sanzo Wada (1883–1967): *A Dictionary of Color Combinations* / 配色事典,
  Seigensha Art.
- Farbdaten: [mattdesl/dictionary-of-colour-combinations](https://github.com/mattdesl/dictionary-of-colour-combinations)
  (MIT, © 2020 Matt DesLauriers; ursprünglich von Dain M. Blodorn Kim),
  Kopie unter `tools/wada/`. `tools/buch_importieren.py` erzeugt daraus
  `lichtstimmung_buch.jinja`.

## Weitere Lampen

Neue Lampe: in `lichtstimmung.jinja` unter `LAMPEN` an der passenden Stelle im
Raum eintragen. Wie man die Entity-IDs ausliest, steht in
[`docs/raum-layout.md`](docs/raum-layout.md).
