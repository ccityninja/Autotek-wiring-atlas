#!/usr/bin/env python3
"""Read-only audit of Golf and R32 atlas JSON."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def missing_2d(node: dict) -> bool:
    top, side = node.get("top"), node.get("side")
    return (not top) or (not side) or top == [0, 0] or side == [0, 0]


def audit(name: str, data: dict, connectors: dict) -> list[str]:
    errors = []
    ids = [n["id"] for n in data["nodes"]]
    if len(ids) != len(set(ids)):
        errors.append(f"{name}: duplicate node ids")
    for n in data["nodes"]:
        if n.get("loc_status") not in ("confirmed", "estimated"):
            errors.append(f"{name}: {n['id']} bad loc_status {n.get('loc_status')}")
        if n.get("loc_status") == "confirmed" and not n.get("location"):
            errors.append(f"{name}: {n['id']} confirmed without location")
        if missing_2d(n) and n.get("kind") not in ("splice",):
            errors.append(f"{name}: {n['id']} missing 2D overlay coords")
    owners = set()
    pointed = set()
    for c in connectors["connectors"]:
        owners.update(c.get("owners") or [])
        for entries in (c.get("pins") or {}).values():
            for e in entries:
                if e.get("toNode"):
                    pointed.add(e["toNode"])
                if e.get("fromNode"):
                    pointed.add(e["fromNode"])
        if not c.get("pins") and not (c.get("faceStatus") or c.get("figure")):
            errors.append(f"{name}: housing {c['id']} has no pins and no factory face")
    for n in data["nodes"]:
        if n["kind"] == "module" and n["id"] not in owners and n["id"] not in pointed:
            errors.append(f"{name}: module {n['id']} has no pinout housing or ECU endpoint")
    return errors


def main() -> int:
    golf = json.loads((ROOT / "golf-wiring" / "data.json").read_text())
    gconn = json.loads((ROOT / "golf-wiring" / "connectors.json").read_text())
    r32 = json.loads((ROOT / "r32-wiring" / "data.json").read_text())
    rconn = json.loads((ROOT / "r32-wiring" / "connectors.json").read_text())
    errors = audit("golf", golf, gconn) + audit("r32", r32, rconn)
    ecu = next(c for c in rconn["connectors"] if c["id"] == "ECU")
    if len(ecu["pins"]) != 76:
        errors.append(f"r32: ECU has {len(ecu['pins'])} pins, expected 76")
    p109 = ecu["pins"]["109"][0]
    if "ECCS" in str(p109.get("toNode")):
        errors.append("r32: pin 109 still points at ECCS relay")
    if "counter-EMF" not in (p109.get("function") or "") and "Injector power" not in (p109.get("function") or ""):
        errors.append("r32: pin 109 function is not injector power")
    g410 = next(n for n in golf["nodes"] if n["id"] == "G410")
    if g410.get("loc_status") != "confirmed":
        errors.append("golf: G410 should be confirmed on the fuel rail")
    if errors:
        print("AUDIT FAIL")
        for e in errors:
            print(" -", e)
        return 1
    print("AUDIT OK")
    print(" golf nodes", len(golf["nodes"]), "estimated", sum(1 for n in golf["nodes"] if n["loc_status"] == "estimated"))
    print(" r32 nodes", len(r32["nodes"]), "estimated", sum(1 for n in r32["nodes"] if n["loc_status"] == "estimated"))
    print(" r32 ECU pins", len(ecu["pins"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
