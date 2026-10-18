#!/usr/bin/env python3
"""Atlas location / pinout checks."""
from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class GolfTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads((ROOT / "golf-wiring" / "data.json").read_text())
        cls.conn = json.loads((ROOT / "golf-wiring" / "connectors.json").read_text())
        cls.by_id = {n["id"]: n for n in cls.data["nodes"]}

    def test_g410_on_rail_not_pump(self):
        n = self.by_id["G410"]
        self.assertEqual(n["loc_status"], "confirmed")
        loc = n["location"].lower()
        self.assertIn("fuel", loc)
        self.assertIn("rail", loc)
        self.assertNotIn("at the high-pressure pump", n["location"].lower())

    def test_knock_sensors_split_along_engine(self):
        g61, g66 = self.by_id["G61"], self.by_id["G66"]
        self.assertEqual(g61["loc_status"], "confirmed")
        self.assertEqual(g66["loc_status"], "confirmed")
        self.assertIn("timing", g61["location"].lower())
        self.assertIn("gearbox", g66["location"].lower())
        self.assertNotEqual(g61["p3"][2], g66["p3"][2])

    def test_coils_confirmed_in_order(self):
        for cid in ("N70", "N127", "N291", "N292"):
            self.assertEqual(self.by_id[cid]["loc_status"], "confirmed", cid)
        z = [self.by_id[c]["p3"][2] for c in ("N70", "N127", "N291", "N292")]
        self.assertEqual(z, sorted(z, reverse=True))

    def test_alternator_has_df_and_bplus(self):
        n = self.by_id["C"]
        self.assertEqual(n["loc_status"], "confirmed")
        housing = next(c for c in self.conn["connectors"] if c["id"] == "C")
        self.assertIn("B+", housing["pins"]["1"][0]["function"])
        self.assertIn("DF", housing["pins"]["2"][0]["function"])

    def test_ignition_switch_pinout(self):
        housing = next(c for c in self.conn["connectors"] if c["id"] == "D")
        fns = " ".join(housing["pins"][str(i)][0]["function"] for i in range(1, 4))
        for term in ("30", "15", "50"):
            self.assertIn(term, fns)

    def test_no_zero_overlay_on_parts(self):
        missing = []
        for n in self.data["nodes"]:
            top, side = n.get("top"), n.get("side")
            if (not top) or (not side) or top == [0, 0] or side == [0, 0]:
                missing.append(n["id"])
        self.assertEqual(missing, [])

    def test_splices_remain_estimated(self):
        for sid in ("PT", "COM", "D182", "131"):
            self.assertEqual(self.by_id[sid]["loc_status"], "estimated")

    def test_physical_conflicted_items_stay_labelled(self):
        for sid in ("H8", "R47", "F241"):
            n = self.by_id[sid]
            self.assertEqual(n["loc_status"], "estimated", sid)
            self.assertTrue(n.get("loc_src"), sid)

    def test_modules_have_housings(self):
        owners = {o for c in self.conn["connectors"] for o in (c.get("owners") or [])}
        missing = [n["id"] for n in self.data["nodes"] if n["kind"] == "module" and n["id"] not in owners]
        self.assertEqual(missing, [])


class R32Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads((ROOT / "r32-wiring" / "data.json").read_text())
        cls.conn = json.loads((ROOT / "r32-wiring" / "connectors.json").read_text())
        cls.ecu = next(c for c in cls.conn["connectors"] if c["id"] == "ECU")
        cls.by_id = {n["id"]: n for n in cls.data["nodes"]}

    def test_ecu_has_76_pins(self):
        self.assertEqual(len(self.ecu["pins"]), 76)
        for pin in list(range(1, 61)) + list(range(101, 117)):
            self.assertIn(str(pin), self.ecu["pins"], pin)

    def test_pin_109_is_injector_power_not_eccs_relay(self):
        e = self.ecu["pins"]["109"][0]
        self.assertIn("Injector power", e["function"])
        self.assertNotEqual(e.get("toNode"), "ECCSRLY")
        for edge in self.data["edges"]:
            for w in edge.get("wires") or []:
                if str(w.get("from")) == "ECU/109":
                    self.assertNotIn("ECCS", str(w.get("to")))

    def test_factory_unused_pins_marked(self):
        for pin in (5, 8, 14, 15, 17, 33, 37, 39, 40, 102, 111, 113, 115):
            e = self.ecu["pins"][str(pin)][0]
            self.assertEqual(e["function"], "Not used")
            self.assertTrue(e.get("factory_unused"))

    def test_ignition_order_pins(self):
        # FSM: 1=cyl1, 2=cyl5, 3=cyl3, 11=cyl6, 12=cyl2, 13=cyl4
        self.assertIn("1", self.ecu["pins"]["1"][0]["function"] + str(self.ecu["pins"]["1"][0]))
        self.assertIn("No. 1", self.ecu["pins"]["1"][0]["function"])
        self.assertIn("No. 5", self.ecu["pins"]["2"][0]["function"])

    def test_physical_parts_confirmed(self):
        for nid in ("ECU", "FPUMP", "PTU", "INJ1", "INJ6", "COILS", "TPS", "CLUSTER", "AFM_F", "KS1", "KS2"):
            self.assertEqual(self.by_id[nid]["loc_status"], "confirmed", nid)

    def test_ground_bolts_stay_estimated(self):
        for nid in ("GND_ECU", "GND_IGN", "GND_INJ"):
            self.assertEqual(self.by_id[nid]["loc_status"], "estimated")

    def test_eccs_relay_in_engine_bay_not_at_ecu(self):
        loc = self.by_id["ECCSRLY"]["location"].lower()
        self.assertIn("engine", loc)
        self.assertIn("relay", loc)

    def test_fuel_pump_housing_from_fpcm(self):
        housing = next(c for c in self.conn["connectors"] if c["id"] == "FPUMP")
        self.assertEqual(housing["count"], 2)
        self.assertIn("positive", housing["pins"]["1"][0]["function"].lower())
        self.assertIn("negative", housing["pins"]["2"][0]["function"].lower())
        self.assertEqual(housing["pins"]["1"][0]["toNode"], "FPCM")


class RemainingEstimatedTests(unittest.TestCase):
    def test_golf_estimated_are_only_schematic_or_conflicted(self):
        data = json.loads((ROOT / "golf-wiring" / "data.json").read_text())
        estimated = {n["id"] for n in data["nodes"] if n["loc_status"] == "estimated"}
        schematic = {
            "EARTH", "PT", "COM", "INF", "LIN",
            "131", "132", "220", "327", "A76", "B315",
            "D101", "D107", "D136", "D182", "D206", "D180", "D181", "D78",
            "85", "281", "383", "E30", "E7", "372", "374",
        }
        physical_conflicted = {"H8", "R47", "F241"}
        self.assertEqual(estimated, schematic | physical_conflicted)

    def test_r32_estimated_are_only_ground_bolts(self):
        data = json.loads((ROOT / "r32-wiring" / "data.json").read_text())
        estimated = {n["id"] for n in data["nodes"] if n["loc_status"] == "estimated"}
        self.assertEqual(estimated, {"GND_ECU", "GND_IGN", "GND_INJ"})


if __name__ == "__main__":
    unittest.main()
