[Русский](README.md) · [English](README.en.md) · **Deutsch**

# Hitachi MAC-14 und MAC-12D

Firmware-Dumps der Steuergeräte Hitachi MAC-14 und MAC-12D und ihre kommentierten Disassembler-Listings.

| Datei | Steuergerät | Motor | EPROM | SHA-256 |
|---|---|---|---|---|
| `src/MAC-14.BIN` | MAC-14, 447905383L | MC (1988–1991) | MBM27128, 16 KB, $C000–$FFFF | `a229f12c5f0fadd0214c420c67368cab571f0e1736263b6ccc484de028713d29` |
| `src/MAC-12D.BIN` | MAC-12D, 857905383 | 1B/2B (1988–1990) | MBM2764, 8 KB, $E000–$FFFF | `407089b4111323564130cfe3333cd1fb94f1ae7f2ad20de5ac04ee586765375e` |

Beide Steuergeräte verwenden den Prozessor HD63B03XP.

## Inhalt

- `docs/asm/de/MAC-14.lst` — Listing des MAC-14 mit deutschen Kommentaren.
- `docs/asm/de/MAC-14.notes` — Annotationsdatei, aus der das deutsche Listing erzeugt wird.
- `docs/asm/*.lst`, `docs/asm/*.notes` — Listings und Annotationen auf Russisch, auch für das MAC-12D. Das Format der Annotationen ist in `docs/asm/NOTES_FORMAT.md` beschrieben (Russisch).
- `src/*_pinout.md` — Pinbelegungen der Steuergeräte, des Prozessors und der EPROMs (Russisch).
- `tools/lst6303.py` — Disassembler für den HD6303.
- `tools/match6303.py` — sucht gleiche Codeabschnitte in zwei Firmware-Abbildern.

Erzeugen des deutschen Listings:

```
python3 -I tools/lst6303.py src/MAC-14.BIN docs/asm/de/MAC-14.notes --lang=de > docs/asm/de/MAC-14.lst
```

`--cov` zeigt, wie viel des Codes kommentiert ist, `--todo` listet die nicht kommentierten Abschnitte.

## Hinweise

Vermutungen sind in den Kommentaren mit `[Vermutung]` gekennzeichnet, Unbekanntes mit `[?]`. Die Tick-Länge (≈ 10 ms)
und der Drehzahlmaßstab (≈ 22 U/min pro Einheit) sind aus dem Code abgeleitet und nicht am Fahrzeug gemessen.

Die englischen und deutschen Kommentare sind aus dem russischen Original übersetzt; maßgeblich sind die russischen Dateien.

## Lizenzen

`tools/` — MIT, Listings und Annotationen — CC BY 4.0. Für die Firmware-Dateien gelten diese Lizenzen nicht.
