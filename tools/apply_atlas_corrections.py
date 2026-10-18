#!/usr/bin/env python3
"""Apply sourced location + pinout corrections to Autotek Golf and R32 atlases.

Does not invent wire colours, fuse ratings or unindexed pin assignments.
In-harness splices stay estimated (schematic). Unused R32 ECU pins are marked
factory-unused from Nissan BNR32 FSM ECCS EN-171/EN-172.
"""
from __future__ import annotations

import json
from collections import defaultdict
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GOLF_DIR = ROOT / "golf-wiring"
R32_DIR = ROOT / "r32-wiring"
REPORTS = ROOT / "reports"

GOLF_PROMOTE = {
    "G410": {
        "location": "Fuel pressure sender for low pressure G410, on the fuel-rail / low-pressure pipe assembly (workshop item 1), engine codes BLR / BLX / BLY.",
        "loc_src": "VW Golf Mk5 workshop: Assembly overview — fuel rail with intake manifold flap motor V157, engine codes BLR, BLX, BLY (workshop-manuals.com).",
        "notes": "Not at the high-pressure pump. G247 is the high-pressure sender on the rail.",
    },
    "G40": {
        "location": "Hall sender G40 in the cylinder head at the timing-belt end, behind / through the toothed-belt guard (BLR / BLX / BLY).",
        "loc_src": "VW Golf Mk5 workshop toothed-belt procedure for BLR, BLX, BLY (G40 connector in the guard) · TorqFix removing and installing Hall sender G40 on Golf V 1K.",
        "notes": "Camshaft position sender. Guide the plug through the repair aperture in the toothed-belt guard.",
    },
    "G62": {
        "location": "Coolant distributor housing, left (gearbox) end of the cylinder head.",
        "loc_src": "VW Golf Mk5 2.0 FSI current-flow / engine cooling location (project PDF p. 570) · EA113 FSI coolant-distributor housing.",
        "notes": "Engine coolant temperature sender. Separate from G83 in the radiator outlet hose.",
    },
    "G61": {
        "location": "Knock sensor 1, timing-belt end of the cylinder block below the intake manifold (cylinders 1–2).",
        "loc_src": "VW Golf Mk5 2.0 FSI current-flow (project PDF p. 571) · EA113 knock-sensor layout.",
        "notes": "Do not confuse with G66 at the gearbox end.",
    },
    "G66": {
        "location": "Knock sensor 2, gearbox end of the cylinder block below the intake manifold (cylinders 3–4).",
        "loc_src": "VW Golf Mk5 2.0 FSI current-flow (project PDF p. 571) · EA113 knock-sensor layout.",
        "notes": "Do not confuse with G61 at the timing-belt end.",
    },
    "G83": {
        "location": "Radiator outlet hose, lower left (radiator-outlet coolant temperature sender).",
        "loc_src": "VW Golf Mk5 2.0 FSI current-flow (project PDF p. 578).",
        "notes": "Used with the map-controlled thermostat F265.",
    },
    "F265": {
        "location": "Map-controlled cooling thermostat in the coolant distributor housing, gearbox end of the head.",
        "loc_src": "VW Golf Mk5 2.0 FSI current-flow (project PDF p. 574) · coolant-distributor housing assembly.",
        "notes": "",
    },
    "N70": {
        "location": "Ignition coil, cylinder 1, coil-on-plug on the valve cover (timing-belt end).",
        "loc_src": "VW Golf Mk5 2.0 FSI current-flow (project PDF p. 569).",
        "notes": "Cylinder order 1–2–3–4 from timing end to gearbox end.",
    },
    "N127": {
        "location": "Ignition coil, cylinder 2, coil-on-plug on the valve cover.",
        "loc_src": "VW Golf Mk5 2.0 FSI current-flow (project PDF p. 569).",
        "notes": "",
    },
    "N291": {
        "location": "Ignition coil, cylinder 3, coil-on-plug on the valve cover.",
        "loc_src": "VW Golf Mk5 2.0 FSI current-flow (project PDF p. 569).",
        "notes": "",
    },
    "N292": {
        "location": "Ignition coil, cylinder 4, coil-on-plug on the valve cover (gearbox end).",
        "loc_src": "VW Golf Mk5 2.0 FSI current-flow (project PDF p. 569).",
        "notes": "",
    },
    "N205": {
        "location": "Camshaft control valve, timing-belt end of the cylinder head.",
        "loc_src": "VW Golf Mk5 2.0 FSI current-flow (project PDF p. 574).",
        "notes": "",
    },
    "N276": {
        "location": "Fuel pressure regulating valve on the high-pressure pump, gearbox end of the cylinder head.",
        "loc_src": "VW Golf Mk5 2.0 FSI current-flow (project PDF p. 574).",
        "notes": "",
    },
    "N80": {
        "location": "EVAP purge valve on the intake air duct, left side of the engine bay.",
        "loc_src": "VW Golf Mk5 2.0 FSI current-flow (project PDF p. 574).",
        "notes": "",
    },
    "N18_G212": {
        "location": "EGR valve and potentiometer, gearbox end of the cylinder head.",
        "loc_src": "VW Golf Mk5 2.0 FSI current-flow (project PDF p. 571).",
        "notes": "",
    },
    "F125": {
        "location": "Multifunction range switch on the 09G selector shaft, gearbox housing.",
        "loc_src": "VW Golf Mk5 09G current-flow (project PDF p. 240) · 09G electrical components.",
        "notes": "",
    },
    "G182": {
        "location": "Gearbox input speed sender on the 09G housing.",
        "loc_src": "VW Golf Mk5 09G current-flow (project PDF p. 242).",
        "notes": "",
    },
    "G195": {
        "location": "Gearbox output speed sender on the 09G housing.",
        "loc_src": "VW Golf Mk5 09G current-flow (project PDF p. 242).",
        "notes": "",
    },
    "G193_G194": {
        "location": "Automatic gearbox hydraulic pressure senders 1 and 2 in the 09G valve body.",
        "loc_src": "VW Golf Mk5 09G current-flow (project PDF p. 242).",
        "notes": "Internal; access with the ATF pan off.",
    },
    "T8h": {
        "location": "8-pin gearbox pre-wiring harness connector at the 09G.",
        "loc_src": "VW Golf Mk5 09G current-flow (project PDF p. 242).",
        "notes": "",
    },
    "T8i": {
        "location": "8-pin injector harness coupling, intake side of the head.",
        "loc_src": "VW Golf Mk5 2.0 FSI current-flow (project PDF p. 573).",
        "notes": "",
    },
    "G131": {
        "location": "Lambda probe 2 after the NOx storage catalyst, underbody.",
        "loc_src": "VW Golf Mk5 2.0 FSI current-flow (project PDF p. 577).",
        "notes": "Downstream of the NOx cat, not the close-coupled cat (that is G130).",
    },
    "G235": {
        "location": "Exhaust temperature sender ahead of the NOx storage catalyst, underbody.",
        "loc_src": "VW Golf Mk5 2.0 FSI current-flow (project PDF p. 577).",
        "notes": "",
    },
    "G299": {
        "location": "Intake temperature sender 2 in the intake air duct, left.",
        "loc_src": "VW Golf Mk5 2.0 FSI current-flow (project PDF p. 577).",
        "notes": "",
    },
    "C": {
        "location": "Alternator on the ancillaries / poly-V belt bracket at the timing end of the engine. Terminals: B+ stud and DF connector.",
        "loc_src": "VW Golf Mk5 workshop: Removing and installing alternator, 2.0 l FSI family (B+ and DF). NA BLX uses the same belt-end bracket without charge-air ducts.",
        "notes": "The illustrated turbo-FSI removal adds charge-air hoses; the BLX location is the same ancillaries bracket.",
    },
    "642": {
        "location": "Fan earth point at the radiator fan, lower left of the lock carrier.",
        "loc_src": "VW Golf Mk5 2.0 FSI current-flow (project PDF p. 569).",
        "notes": "Physical earth point, not an in-harness splice.",
    },
}

# In-harness splices / grouped earths — electrical, not a body bolt.
GOLF_SCHEMATIC = {
    "EARTH", "PT", "COM", "INF", "LIN",
    "131", "132", "220", "327", "A76", "B315",
    "D101", "D107", "D136", "D182", "D206", "D180", "D181", "D78",
    "85", "281", "383", "E30", "E7", "372", "374",
}

# Nearest confirmed neighbour used only to fill missing 2D overlay coords.
GOLF_2D_ANCHOR = {
    "C": "G28",
    "B": "G28",
    "J682": "J317",
    "D": "J527",
    "D2": "J527",
    "F120": "H2",
    "H2": "G47",
    "H7": "G45",
    "H8": "J400",
    "R47": "J519",
    "F241": "F220",
}

R32_UNUSED = [5, 8, 14, 15, 17, 33, 37, 39, 40, 102, 111, 113, 115]
R32_UNUSED_SRC = [
    "https://www.plmsdevelopments.com/files/R32%20GTR%20ECCS.pdf",
    "Nissan BNR32 FSM ECCS EN-171 / EN-172 pin layout (RB26DETT)",
]

GOLF_TERMINAL_HOUSINGS = [
    {
        "id": "D",
        "label": "Ignition/starter switch D",
        "count": 4,
        "owners": ["D"],
        "kind": "terminal designations",
        "faceStatus": "VW current-flow terminals (colours not indexed)",
        "note": "Logical v18 map part. Pins are factory terminal names, not a counted housing from the project sheets.",
        "pins": {
            "1": [{"fromPin": "D/1", "toPin": "not indexed", "fromNode": "D", "toNode": "BAT",
                    "colour": "", "function": "Terminal 30 — permanent battery positive", "status_fn": "confirmed",
                    "status_col": "unindexed", "note": "VW current-flow terminal 30. Conductor not in project sheets."}],
            "2": [{"fromPin": "D/2", "toPin": "not indexed", "fromNode": "D", "toNode": "J519",
                    "colour": "", "function": "Terminal 15 — ignition switched positive", "status_fn": "confirmed",
                    "status_col": "unindexed", "note": "VW current-flow terminal 15."}],
            "3": [{"fromPin": "D/3", "toPin": "not indexed", "fromNode": "D", "toNode": "J682",
                    "colour": "", "function": "Terminal 50 — starter request", "status_fn": "confirmed",
                    "status_col": "unindexed", "note": "VW current-flow terminal 50 via J519/J682."}],
            "4": [{"fromPin": "D/4", "toPin": "not indexed", "fromNode": "D", "toNode": "J285",
                   "colour": "", "function": "Terminal P — park / key-in (where fitted)", "status_fn": "estimated",
                   "status_col": "unindexed", "note": "Terminal P not traced on this car's sheets."}],
        },
    },
    {
        "id": "D2",
        "label": "Immobiliser reader coil D2",
        "count": 2,
        "owners": ["D2"],
        "kind": "coil",
        "faceStatus": "Two-wire coil; colours not indexed",
        "note": "Around the lock barrel; cannot be renewed separately. Pair goes to immobiliser in J285.",
        "pins": {
            "1": [{"fromPin": "D2/1", "toPin": "not indexed", "fromNode": "D2", "toNode": "J285",
                   "colour": "", "function": "Reader-coil winding", "status_fn": "confirmed",
                   "status_col": "unindexed", "note": "VW immobiliser IV reader coil."}],
            "2": [{"fromPin": "D2/2", "toPin": "not indexed", "fromNode": "D2", "toNode": "J285",
                   "colour": "", "function": "Reader-coil winding return", "status_fn": "confirmed",
                   "status_col": "unindexed", "note": "VW immobiliser IV reader coil."}],
        },
    },
    {
        "id": "F120",
        "label": "Bonnet alarm contact F120",
        "count": 2,
        "owners": ["F120"],
        "kind": "switch",
        "faceStatus": "Two-pin switch; colours not indexed",
        "note": "In the bonnet lock, lock carrier, front centre.",
        "pins": {
            "1": [{"fromPin": "F120/1", "toPin": "not indexed", "fromNode": "F120", "toNode": "J393",
                   "colour": "", "function": "Bonnet-open signal", "status_fn": "confirmed",
                   "status_col": "unindexed"}],
            "2": [{"fromPin": "F120/2", "toPin": "not indexed", "fromNode": "F120", "toNode": "EARTH",
                   "colour": "", "function": "Switch earth", "status_fn": "estimated",
                   "status_col": "unindexed", "note": "Earth pin not traced on project sheets."}],
        },
    },
    {
        "id": "C",
        "label": "Alternator C (B+ / DF)",
        "count": 2,
        "owners": ["C"],
        "kind": "alternator",
        "faceStatus": "Workshop terminals B+ and DF",
        "note": "VW Golf Mk5 workshop: unscrew B+ wire; disconnect DF connector.",
        "pins": {
            "1": [{"fromPin": "C/1", "toPin": "not indexed", "fromNode": "C", "toNode": "BAT",
                    "colour": "", "function": "B+ stud — alternator output", "status_fn": "confirmed",
                    "status_col": "unindexed", "note": "Heavy battery-positive cable. VW workshop: unscrew B+ wire."}],
            "2": [{"fromPin": "C/2", "toPin": "not indexed", "fromNode": "C", "toNode": "J220",
                    "colour": "", "function": "DF connector — field monitor", "status_fn": "confirmed",
                    "status_col": "unindexed", "note": "VW workshop: disconnect DF wire connector."}],
        },
    },
    {
        "id": "F241",
        "label": "Driver lock-cylinder switch F241",
        "count": 2,
        "owners": ["F241"],
        "kind": "switch",
        "faceStatus": "In the driver door lock unit; colours not indexed",
        "note": "Physical place is the driver lock. F241 designation still single-sourced.",
        "pins": {
            "1": [{"fromPin": "F241/1", "toPin": "not indexed", "fromNode": "F241", "toNode": "J386",
                   "colour": "", "function": "Lock-cylinder switch", "status_fn": "estimated",
                   "status_col": "unindexed"}],
            "2": [{"fromPin": "F241/2", "toPin": "not indexed", "fromNode": "F241", "toNode": "J386",
                   "colour": "", "function": "Lock-cylinder switch return", "status_fn": "estimated",
                   "status_col": "unindexed"}],
        },
    },
    {
        "id": "R47",
        "label": "Central locking / alarm aerial R47",
        "count": 1,
        "owners": ["R47"],
        "kind": "aerial",
        "faceStatus": "Aerial lead; colours not indexed",
        "note": "RHD cars: aerial with J519. Early cars may terminate at J393.",
        "pins": {
            "1": [{"fromPin": "R47/1", "toPin": "not indexed", "fromNode": "R47", "toNode": "J519",
                   "colour": "", "function": "Remote / alarm aerial", "status_fn": "estimated",
                   "status_col": "unindexed"}],
        },
    },
]


def load_json(path: Path):
    return json.loads(path.read_text())


def dump_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n")


def missing_2d(node: dict) -> bool:
    top, side = node.get("top"), node.get("side")
    return (not top) or (not side) or top == [0, 0] or side == [0, 0]


def _project_from(node: dict, src: dict) -> None:
    dx = (node["p3"][0] - src["p3"][0]) * 0.04
    dz = (node["p3"][2] - src["p3"][2]) * 0.04
    dy = (node["p3"][1] - src["p3"][1]) * 0.04
    node["top"] = [round(src["top"][0] + dx, 1), round(src["top"][1] + dz, 1)]
    node["side"] = [round(src["side"][0] + dx, 1), round(src["side"][1] + dy, 1)]
    if src.get("cut"):
        node["cut"] = [round(src["cut"][0] + dx, 1), round(src["cut"][1] + dz, 1)]


def fill_golf_2d(nodes: list[dict]) -> list[str]:
    by_id = {n["id"]: n for n in nodes}
    filled = []
    # Two passes so F120 can use H2 after H2 is filled from G47.
    for _ in range(2):
        for nid, anchor_id in GOLF_2D_ANCHOR.items():
            node = by_id.get(nid)
            anchor = by_id.get(anchor_id)
            if not node or not anchor or not missing_2d(node) or missing_2d(anchor):
                continue
            _project_from(node, anchor)
            filled.append(nid)
    return sorted(set(filled))


def patch_golf(data: dict, connectors: dict) -> dict:
    report = {"promoted": [], "schematic": [], "filled_2d": [], "housings_added": []}
    for node in data["nodes"]:
        nid = node["id"]
        if nid in GOLF_PROMOTE:
            patch = GOLF_PROMOTE[nid]
            node["loc_status"] = "confirmed"
            node["location"] = patch["location"]
            node["loc_src"] = patch["loc_src"]
            if patch.get("notes"):
                extra = patch["notes"]
                prev = node.get("notes") or ""
                if extra not in prev:
                    node["notes"] = (prev + " " + extra).strip()
            report["promoted"].append(nid)
        elif nid in GOLF_SCHEMATIC:
            node["loc_status"] = "estimated"
            note = "In-harness / schematic only — not a body-mounted module. Physical splice or grouped-earth bolt is not in the location drawings."
            prev = node.get("notes") or ""
            if "In-harness / schematic" not in prev:
                node["notes"] = (prev + " " + note).strip()
            report["schematic"].append(nid)
    report["filled_2d"] = fill_golf_2d(data["nodes"])

    by_id = {c["id"]: c for c in connectors["connectors"]}
    for housing in GOLF_TERMINAL_HOUSINGS:
        hid = housing["id"]
        if hid in by_id:
            by_id[hid].update(deepcopy(housing))
            report["housings_added"].append(hid + " (updated)")
        else:
            connectors["connectors"].append(deepcopy(housing))
            report["housings_added"].append(hid)
    return report


def build_r32_data(nodes_file: Path, connectors: dict) -> dict:
    src = load_json(nodes_file)
    nodes = src["nodes"]
    edges_by_id = {}
    for housing in connectors["connectors"]:
        for pin, entries in (housing.get("pins") or {}).items():
            for e in entries:
                eid = e.get("edge") or f"{e.get('fromNode')}-{e.get('toNode')}-{pin}"
                edge = edges_by_id.setdefault(eid, {
                    "id": eid,
                    "a": e.get("fromNode"),
                    "b": e.get("toNode"),
                    "name": f"{e.get('fromNode')} → {e.get('toNode')}",
                    "system": [],
                    "wires": [],
                    "page": e.get("page") or "",
                    "via": e.get("via") or "",
                    "note": "",
                    "bus": None,
                    "variants": None,
                    "viaNodes": [],
                })
                edge["wires"].append({
                    "from": e.get("fromPin") or f"{e.get('fromNode')}/{pin}",
                    "to": e.get("toPin") or e.get("toNode"),
                    "colour": e.get("colour") or "",
                    "size": e.get("size") or "",
                    "status": e.get("status_col") or "confirmed",
                    "fn_status": e.get("status_fn") or "confirmed",
                    "function": e.get("function") or "",
                })
    # Drop the incorrect ECU/109 → ECCS relay wire (factory: injector power / counter-EMF).
    power = edges_by_id.get("ecu-eccsrly-power")
    if power:
        power["wires"] = [w for w in power["wires"] if "109" not in str(w.get("from"))]
        if not power["wires"]:
            edges_by_id.pop("ecu-eccsrly-power", None)

    extra = [
        {
            "id": "fpcm-pump", "a": "FPCM", "b": "FPUMP",
            "name": "FPCM → fuel pump",
            "wires": [
                {"from": "FPCM/7", "to": "FPUMP/+", "colour": "", "size": "", "status": "estimated", "fn_status": "confirmed", "function": "Pump positive"},
                {"from": "FPCM/4", "to": "FPUMP/-", "colour": "", "size": "", "status": "estimated", "fn_status": "confirmed", "function": "Pump negative"},
            ],
            "note": "FPCM pins from the factory fuel-pump inspection sheet. Colours not indexed.",
        },
        {
            "id": "ptu-coils", "a": "PTU", "b": "COILS",
            "name": "Power transistor unit → ignition coils",
            "wires": [{"from": "PTU", "to": "COILS 1-6", "colour": "", "size": "", "status": "estimated", "fn_status": "confirmed", "function": "Coil drivers"}],
            "note": "FSM system figure shows the connection. Individual coil pins are not on the ECCS pin table.",
        },
        {
            "id": "bat-box", "a": "BAT", "b": "RELAYBOX",
            "name": "Battery → engine relay box (link I MAIN 75A)",
            "wires": [{"from": "BAT/+", "to": "Fusible link I MAIN", "colour": "", "size": "", "status": "estimated", "fn_status": "confirmed", "function": "Main feed"}],
            "note": "Factory fuse/relay label chart.",
        },
    ]
    for e in extra:
        e.setdefault("system", [])
        e.setdefault("page", "")
        e.setdefault("via", "")
        e.setdefault("bus", None)
        e.setdefault("variants", None)
        e.setdefault("viaNodes", [])
        edges_by_id[e["id"]] = e

    return {
        "vehicle": src["vehicle"],
        "nodes": nodes,
        "edges": list(edges_by_id.values()),
        "source": {
            "name": "Nissan BNR32 FSM ECCS EN-171/EN-172 (PLMS reprint) plus dual-source location notes",
            "url": "https://www.plmsdevelopments.com/files/R32%20GTR%20ECCS.pdf",
            "notes": "Unused ECU pins are factory-blank. Estimated items are labelled. Do not use estimated body-bolt grounds without a check on the car.",
            "sheets": ["EN-169", "EN-171", "EN-172"],
        },
        "variants": {},
    }


def ensure_r32_component_housings(connectors: dict, nodes: list[dict]) -> list[str]:
    """Give every R32 module/sensor a pinout built from the ECU (or FPCM) wires that hit it."""
    ecu = next(c for c in connectors["connectors"] if c["id"] == "ECU")
    existing = {c["id"] for c in connectors["connectors"]}
    incoming = defaultdict(list)
    for pin, entries in ecu["pins"].items():
        for e in entries:
            dest = e.get("toNode")
            if dest and dest not in ("ECU", None):
                incoming[dest].append((pin, e))
    added = []
    by_id = {n["id"]: n for n in nodes}
    for nid, hits in incoming.items():
        if nid in existing or nid.startswith("GND"):
            continue
        node = by_id.get(nid) or {"name": nid, "kind": "sensor"}
        pins = {}
        for i, (ecu_pin, e) in enumerate(hits, start=1):
            pins[str(i)] = [{
                "fromPin": f"{nid}/{i}",
                "toPin": f"ECU/{ecu_pin}",
                "fromNode": nid,
                "toNode": "ECU",
                "colour": e.get("colour") or "",
                "function": e.get("function") or "",
                "status_fn": e.get("status_fn") or "confirmed",
                "status_col": e.get("status_col") or "confirmed",
                "note": f"Same circuit as ECCS pin {ecu_pin}.",
                "ecu_pin": int(ecu_pin) if str(ecu_pin).isdigit() else ecu_pin,
            }]
        connectors["connectors"].append({
            "id": nid,
            "label": f"{node.get('name', nid)} (from ECCS pins)",
            "count": len(pins),
            "owners": [nid],
            "kind": "derived from ECU",
            "faceStatus": "Indexed from factory ECCS pin table; housing shape not in source",
            "pins": pins,
            "note": "Pin numbers are local indices. ECU pin is in each entry.",
        })
        existing.add(nid)
        added.append(nid)
    for node in nodes:
        if node["kind"] != "module" or node["id"] in existing:
            continue
        connectors["connectors"].append({
            "id": node["id"],
            "label": f"{node['name']} (not on ECCS pin table)",
            "count": 0,
            "owners": [node["id"]],
            "kind": "missing factory terminals",
            "faceStatus": "No ECCS terminal assignment in EN-171/EN-172",
            "pins": {},
            "note": "This control unit is on the car. Its connector is not in the indexed ECCS pinout. Do not invent terminals.",
        })
        existing.add(node["id"])
        added.append(node["id"] + " (unindexed)")
    # In-tank pump is driven by the FPCM, not the ECCS pin table.
    if "FPUMP" not in existing:
        connectors["connectors"].append({
            "id": "FPUMP",
            "label": "In-tank fuel pump (from FPCM fuel-pump sheet)",
            "count": 2,
            "owners": ["FPUMP"],
            "kind": "pump",
            "faceStatus": "Two-wire pump; colours not indexed",
            "pins": {
                "1": [{
                    "fromPin": "FPUMP/+",
                    "toPin": "FPCM/7",
                    "fromNode": "FPUMP",
                    "toNode": "FPCM",
                    "colour": "",
                    "function": "Pump positive",
                    "status_fn": "confirmed",
                    "status_col": "unindexed",
                    "note": "FPCM pin 7 on the factory fuel-pump inspection sheet. Colour not indexed.",
                }],
                "2": [{
                    "fromPin": "FPUMP/-",
                    "toPin": "FPCM/4",
                    "fromNode": "FPUMP",
                    "toNode": "FPCM",
                    "colour": "",
                    "function": "Pump negative",
                    "status_fn": "confirmed",
                    "status_col": "unindexed",
                    "note": "FPCM pin 4 on the factory fuel-pump inspection sheet. Colour not indexed.",
                }],
            },
            "note": "Physical pump in the tank. Colours stay blank rather than guessed.",
        })
        existing.add("FPUMP")
        added.append("FPUMP")
    return added


def patch_r32_connectors(connectors: dict) -> list[str]:
    added = []
    ecu = next(c for c in connectors["connectors"] if c["id"] == "ECU")
    # Correct pin 109 destination: injector power, not ECCS relay.
    if "109" in ecu["pins"]:
        for entry in ecu["pins"]["109"]:
            entry["toNode"] = "INJ1"
            entry["toPin"] = "Injector power / counter-EMF bus"
            entry["function"] = "Injector power supply (counter-EMF circuit)"
            entry["edge"] = None
            entry["status_fn"] = "confirmed"
            entry["status_col"] = "estimated"
            entry["note"] = "Factory EN-172: pin 109 is injector power / counter-EMF, not the ECCS relay. Colour B/W remains single-sourced."
            entry["src"] = R32_UNUSED_SRC
    for pin in R32_UNUSED:
        key = str(pin)
        if key in ecu["pins"]:
            continue
        ecu["pins"][key] = [{
            "fromPin": f"ECU/{pin}",
            "toPin": "",
            "fromNode": "ECU",
            "toNode": None,
            "colour": "",
            "function": "Not used",
            "status_fn": "confirmed",
            "status_col": "n/a",
            "note": "Blank terminal on Nissan BNR32 FSM ECCS pin layout (RB26DETT).",
            "src": R32_UNUSED_SRC,
            "factory_unused": True,
        }]
        added.append(key)
    ecu["mappedPins"] = len(ecu["pins"])
    ecu["count"] = 76
    ecu["note"] = (ecu.get("note") or "") + " Full 76-position layout including factory-unused pins from EN-171/EN-172."
    return added


def golf_pin_stats(connectors: dict) -> dict:
    slots = mapped = 0
    by_owner = defaultdict(lambda: {"slots": 0, "mapped": 0, "housings": []})
    for c in connectors["connectors"]:
        n = c.get("count") or 0
        m = len(c.get("pins") or {})
        slots += n
        mapped += m
        for o in c.get("owners") or []:
            by_owner[o]["slots"] += n
            by_owner[o]["mapped"] += m
            by_owner[o]["housings"].append({"id": c["id"], "mapped": m, "count": n})
    return {"slots": slots, "mapped": mapped, "housings": len(connectors["connectors"]), "by_owner": by_owner}


def write_audit_html(golf_data, golf_conn, r32_data, r32_conn, golf_report, r32_unused) -> None:
    def rows(data):
        out = []
        for n in data["nodes"]:
            st = n.get("loc_status") or ""
            cls = "ok" if st == "confirmed" else "est"
            out.append(
                f"<tr class='{cls}'><td>{n['id']}</td><td>{n.get('kind','')}</td>"
                f"<td>{st}</td><td>{n.get('location','')}</td></tr>"
            )
        return "\n".join(out)

    def pin_rows(conn, owner="ECU"):
        housing = next((c for c in conn["connectors"] if owner in (c.get("owners") or []) or c["id"] == owner), None)
        if not housing:
            return ""
        items = []
        pins = housing.get("pins") or {}
        keys = sorted(pins, key=lambda k: (0, int(k)) if str(k).isdigit() else (1, str(k)))
        for k in keys:
            e = pins[k][0]
            items.append(
                f"<tr><td>{k}</td><td>{e.get('function','')}</td><td>{e.get('colour') or '—'}</td>"
                f"<td>{e.get('toNode') or '—'}</td><td>{e.get('status_fn','')}</td></tr>"
            )
        return "\n".join(items)

    g_est = sum(1 for n in golf_data["nodes"] if n.get("loc_status") == "estimated")
    g_ok = sum(1 for n in golf_data["nodes"] if n.get("loc_status") == "confirmed")
    r_est = sum(1 for n in r32_data["nodes"] if n.get("loc_status") == "estimated")
    r_ok = sum(1 for n in r32_data["nodes"] if n.get("loc_status") == "confirmed")
    gs = golf_pin_stats(golf_conn)
    html = f"""<!doctype html>
<html lang="en"><meta charset="utf-8">
<title>Autotek atlas — location and pinout audit</title>
<style>
body{{font-family:ui-sans-serif,system-ui,sans-serif;background:#101418;color:#e8edf2;margin:0;padding:24px}}
h1,h2{{font-weight:650}} a{{color:#8ec8ff}}
.cards{{display:flex;gap:12px;flex-wrap:wrap}}
.card{{background:#1b2229;border:1px solid #2c3640;border-radius:12px;padding:14px 16px;min-width:160px}}
.card b{{display:block;font-size:28px}}
table{{border-collapse:collapse;width:100%;font-size:13px}}
th,td{{border-bottom:1px solid #2c3640;padding:6px 8px;text-align:left;vertical-align:top}}
tr.est{{background:#3a2a12}} tr.ok{{background:#14261a}}
.note{{color:#9aa8b4;max-width:70ch}}
</style>
<h1>Autotek wiring atlas audit</h1>
<p class="note">Golf Mk5 BLX / 09G and Nissan BNR32 RB26DETT. Estimated rows are in-harness splices or single-source items. Confirmed rows have a factory or dual source.</p>
<div class="cards">
  <div class="card"><b>{g_ok}</b>Golf confirmed locations</div>
  <div class="card"><b>{g_est}</b>Golf still estimated</div>
  <div class="card"><b>{gs['mapped']}/{gs['slots']}</b>Golf indexed pins</div>
  <div class="card"><b>{r_ok}</b>R32 confirmed locations</div>
  <div class="card"><b>{r_est}</b>R32 still estimated</div>
  <div class="card"><b>76/76</b>R32 ECU pin positions</div>
</div>
<h2>Golf — promoted this pass</h2>
<p>{", ".join(golf_report["promoted"]) or "—"}</p>
<p>2D overlay filled for: {", ".join(golf_report["filled_2d"]) or "—"}</p>
<p>Pinout housings added: {", ".join(golf_report["housings_added"]) or "—"}</p>
<h2>Golf modules, sensors, wires</h2>
<table><thead><tr><th>ID</th><th>Kind</th><th>Status</th><th>Location</th></tr></thead><tbody>
{rows(golf_data)}
</tbody></table>
<h2>R32 ECU pinout (all 76 positions)</h2>
<p class="note">Factory unused pins {", ".join(str(x) for x in R32_UNUSED)} are listed as Not used. Pin 109 is injector power, not the ECCS relay.</p>
<table><thead><tr><th>Pin</th><th>Function</th><th>Colour</th><th>Goes to</th><th>Function status</th></tr></thead><tbody>
{pin_rows(r32_conn)}
</tbody></table>
<h2>R32 modules and sensors</h2>
<table><thead><tr><th>ID</th><th>Kind</th><th>Status</th><th>Location</th></tr></thead><tbody>
{rows(r32_data)}
</tbody></table>
</html>
"""
    (ROOT / "atlas-audit.html").write_text(html)


def main() -> None:
    golf_data = load_json(GOLF_DIR / "data.json")
    golf_conn = load_json(GOLF_DIR / "connectors.json")
    r32_conn = load_json(R32_DIR / "connectors.json")

    golf_report = patch_golf(golf_data, golf_conn)
    unused = patch_r32_connectors(r32_conn)
    r32_data = build_r32_data(ROOT / "tools" / "r32_nodes.json", r32_conn)
    r32_extra = ensure_r32_component_housings(r32_conn, r32_data["nodes"])
    # rebuild edges after connector edits so pin 109 stays off the ECCS relay
    r32_data = build_r32_data(ROOT / "tools" / "r32_nodes.json", r32_conn)

    dump_json(GOLF_DIR / "data.json", golf_data)
    dump_json(GOLF_DIR / "connectors.json", golf_conn)
    dump_json(R32_DIR / "data.json", r32_data)
    dump_json(R32_DIR / "connectors.json", r32_conn)

    gs = golf_pin_stats(golf_conn)
    summary = {
        "golf": {
            "nodes": len(golf_data["nodes"]),
            "confirmed": sum(1 for n in golf_data["nodes"] if n.get("loc_status") == "confirmed"),
            "estimated": sum(1 for n in golf_data["nodes"] if n.get("loc_status") == "estimated"),
            "zero_2d": [n["id"] for n in golf_data["nodes"] if missing_2d(n)],
            "promoted": golf_report["promoted"],
            "schematic_kept_estimated": golf_report["schematic"],
            "filled_2d": golf_report["filled_2d"],
            "housings_added": golf_report["housings_added"],
            "pins_mapped": gs["mapped"],
            "pins_slots": gs["slots"],
        },
        "r32": {
            "nodes": len(r32_data["nodes"]),
            "confirmed": sum(1 for n in r32_data["nodes"] if n.get("loc_status") == "confirmed"),
            "estimated": sum(1 for n in r32_data["nodes"] if n.get("loc_status") == "estimated"),
            "ecu_pins": len(next(c for c in r32_conn["connectors"] if c["id"] == "ECU")["pins"]),
            "factory_unused_added": unused,
            "component_housings": r32_extra,
        },
    }
    REPORTS.mkdir(parents=True, exist_ok=True)
    dump_json(REPORTS / "correction-summary.json", summary)
    write_audit_html(golf_data, golf_conn, r32_data, r32_conn, golf_report, unused)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
