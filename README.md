# Autotek wiring atlas

Location and pinout records for the live Golf Mk5 BLX / 09G atlas and the Nissan Skyline GT-R R32 (BNR32) atlas.

This repository does **not** replace the live `autotek.nz` app. Copy `golf-wiring/data.json` and `golf-wiring/connectors.json` over `/golf-wiring/` on the site, and `r32-wiring/` over `/r32-wiring/`, after review.

## What was wrong

The live Golf dataset had **55 estimated** map points. Many were in-harness splices (those stay estimated — a wiring diagram does not give a body bolt). Physical senders, coils, the 09G range switch and the alternator were workshop-known but still flagged estimated, and several v18 parts sat at `[0, 0]` so they never drew on the 2D overlays.

The R32 dataset had most modules estimated, an incomplete 76-pin ECCS layout, and **pin 109 wired to the ECCS relay**. The Nissan FSM lists pin 109 as injector power / counter-EMF.

## Corrected

- Golf physical sensors, coils, 09G senders and the alternator: `loc_status: confirmed` with workshop sources.
- Golf in-harness splices: still `estimated`, labelled schematic.
- Missing 2D overlay coordinates filled from a neighbouring confirmed part.
- Pinout housings added for ignition switch D (terminals 30 / 15 / 50), reader coil D2, bonnet switch F120, alternator B+/DF, lock-cylinder switch and aerial. Colours that are not on the project sheets stay blank.
- R32: factory ECCS pin layout including unused pins; pin 109 corrected; module and sensor locations confirmed from the FSM / Haltech / GTR USA notes. Chassis-bolt grounds stay estimated.

## Preview the audit

```bash
python3 -m http.server 8765
```

Open `http://127.0.0.1:8765/atlas-audit.html`.

## Checks

```bash
python3 tools/apply_atlas_corrections.py
python3 tools/audit_atlas.py
python3 -m unittest tests/test_atlas.py
```

Do not invent remaining Golf T94 / T75 pins. Empty grid cells mean “not in the indexed current-flow sheets”.
