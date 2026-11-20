[Русский](README.md) · **English** · [Deutsch](README.de.md)

# Hitachi MAC-14 and MAC-12D

Firmware dumps of the Hitachi MAC-14 and MAC-12D engine control units and their commented disassembly listings.

| File | Unit | Engine | EPROM | SHA-256 |
|---|---|---|---|---|
| `src/MAC-14.BIN` | MAC-14, 447905383L | MC (1988–1991) | MBM27128, 16 KB, $C000–$FFFF | `a229f12c5f0fadd0214c420c67368cab571f0e1736263b6ccc484de028713d29` |
| `src/MAC-12D.BIN` | MAC-12D, 857905383 | 1B/2B (1988–1990) | MBM2764, 8 KB, $E000–$FFFF | `407089b4111323564130cfe3333cd1fb94f1ae7f2ad20de5ac04ee586765375e` |

Both units use the HD63B03XP processor.

## Contents

- `docs/asm/en/MAC-14.lst` — MAC-14 listing with English comments.
- `docs/asm/en/MAC-14.notes` — the annotation file the English listing is built from.
- `docs/asm/*.lst`, `docs/asm/*.notes` — listings and annotations in Russian, including MAC-12D. The annotation format is described in `docs/asm/NOTES_FORMAT.md` (Russian).
- `src/*_pinout.md` — pinouts of the units, the processor and the EPROMs (Russian).
- `tools/lst6303.py` — HD6303 disassembler.
- `tools/match6303.py` — finds matching code sequences in two firmware images.

Building the English listing:

```
python3 -I tools/lst6303.py src/MAC-14.BIN docs/asm/en/MAC-14.notes --lang=en > docs/asm/en/MAC-14.lst
```

`--cov` prints how much of the code is annotated, `--todo` lists the parts that are not.

## Caveats

Assumptions in the comments are marked `[assumed]`, unknowns `[?]`. The tick length (≈ 10 ms) and the
rpm scale (≈ 22 rpm per unit) are derived from the code and have not been measured on a car. The same applies
to the ignition map unit (1° per unit) and to the direction "larger value = later spark": not checked with a
timing light. The type of the external chip at $0100/$0101 is not identified.

The English and German comments are translated from the Russian originals; the Russian files are the reference.

## Licences

`tools/` — MIT, listings and annotations — CC BY 4.0. These licences do not cover the firmware files.
