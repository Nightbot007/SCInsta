# Raum-Layout schicken – Vorlage

Damit die Farben sinnvoll durch den Raum laufen, brauche ich drei Dinge.

## 1. Die Lampen aus Home Assistant (am wichtigsten)

In Home Assistant **Entwicklerwerkzeuge → Template** öffnen, den Inhalt links
komplett durch folgendes ersetzen und das Ergebnis rechts kopieren:

```jinja
{% for s in states.light | sort(attribute='entity_id') -%}
{{ s.entity_id }} | {{ s.name }} | {{ (s.attributes.supported_color_modes or []) | join(', ') }}
{% endfor %}
```

Daran sehe ich die exakte Entity-ID jeder Lampe und ob sie Farbe
(`hs`, `xy`, `rgb…`), nur Weiß (`color_temp`) oder nur Helligkeit kann.

## 2. Tabelle: Wo steht welche Lampe?

Einfach ausfüllen – Position grob reicht („Ecke hinten links“, „über dem Bett“).

| Entity-ID | Art | Position im Raum | Bemerkung |
|---|---|---|---|
| light.beispiel_decke | Deckenlampe | Raummitte | |
| light.beispiel_steh | Stehlampe | Ecke links neben Sofa | |
| light.beispiel_strip | LED-Streifen | hinter dem TV, ca. 2 m | |
| light.beispiel_nacht | Nachttischlampe | rechts neben Bett | |

## 3. Skizze (optional, aber hilfreich)

Ein Foto einer Handskizze oder ein Screenshot reicht. Wichtig sind nur: Tür,
Fenster, große Möbel (Bett, Sofa, Schreibtisch, TV) und die Lampen mit ihrem
Namen aus der Tabelle. Alternativ als Text:

```
  ┌──────────── Fenster ────────────┐
  │ [Steh]                    [Nacht]│
  │  Sofa          ( Decke )    Bett │
  │                                  │
  │ ═══ LED-Streifen hinter TV ═══   │
  └──Tür─────────────────────────────┘
```

Wenn das Bild hier nicht angehängt werden kann: die Tabelle aus Punkt 2 genügt.

## Was ich daraus mache

- Die Lampen kommen in `homeassistant/custom_templates/lichtstimmung.jinja`
  unter `LAMPEN` – in der Reihenfolge, in der sie im Raum nebeneinander stehen.
  Benachbarte Lampen bekommen benachbarte Farben der Palette, so entsteht ein
  ruhiger Verlauf statt Farbchaos.
- Jede Lampe bekommt einen Typ (`decke`, `steh`, `streifen`, `nacht`, …).
  Darüber steuert jeder Modus die Helligkeit: z. B. Deckenlampe bei
  „Regen / Gewitter“ aus, LED-Streifen bei „Cyberpunk“ kräftig.
