#!/usr/bin/env python3
"""
Generates the FUXA project for CONV-001: plant/scada/project/vigilimen-conv001.fuxa.json

    python3 plant/scada/project/build_project.py

Import: FUXA editor -> gear (top right) -> Project -> Import. This REPLACES the
whole project, so export your current one first if you have edits worth keeping.

Tag addresses are OPC UA numeric NodeIds (ns=2;i=N) in gateway CREATION ORDER.
Never insert a node before the end of gateway/opcua_server.py build(): every
binding below would silently point at a different variable.

Credentials are NOT in this file (FUXA does not export them). After import,
open Connections -> CONV-001 and set user `engineer` and its password
(see gateway/opcua_server.py) if the device shows as disconnected.
"""
import json
from pathlib import Path
from xml.sax.saxutils import escape

DEV = "d_bac44f27-4b1744ff"
TAGS = [  # name, type, ns=2 id, tag id
    ("Running", "Boolean", 6, "t_69fbc576-28174428"),
    ("SafetyTripped", "Boolean", 7, "t_576fe42f-a2774bdd"),
    ("BeltSpeed_mps", "Double", 8, "t_b063281d-cd8046e1"),
    ("Load_tph", "Double", 9, "t_fa535891-3ceb4294"),
    ("BearingTemp_C", "Double", 10, "t_1575227f-b66d418d"),
    ("Vibration_mms", "Double", 11, "t_5cf9b42e-777f4b9b"),
    ("MotorCurrent_A", "Double", 12, "t_44b20c04-dd7b4b1f"),
    ("StartCommand", "Boolean", 13, "t_6f1159cc-274f479d"),
    ("StopCommand", "Boolean", 14, "t_bc573c71-89154239"),
    ("FaultBearingWear", "Double", 15, "t_5a20fb4c-86b36bfd"),
    ("FaultBeltSlip", "Double", 16, "t_826ed50b-00e2ff9d"),
    ("FaultMisalignment", "Double", 17, "t_fcc05857-4a991645"),
    ("FaultIdlerSeizure", "Double", 18, "t_3a16fdc9-10a1a10c"),
    ("FaultVibrationSpike", "Double", 19, "t_11811392-977ed8e8"),
]
T = {n: tid for n, _, _, tid in TAGS}
FAULTS = ["FaultBearingWear", "FaultBeltSlip", "FaultMisalignment", "FaultIdlerSeizure", "FaultVibrationSpike"]
STATUS_TAG = "t_7c641304-d0704ac5"

daq = {"enabled": False, "interval": 60, "changed": False, "restored": False}
devices = {
    "0": {"id": "0", "name": "FUXA Server", "type": "FuxaServer", "property": {}, "polling": 1000, "enabled": True,
          "tags": {STATUS_TAG: {"id": STATUS_TAG, "name": "CONV-001 Connection Status", "label": "CONV-001 Connection Status",
                                "value": 0, "type": "number", "memaddress": DEV, "daq": dict(daq), "init": "", "sysType": 1,
                                "timestamp": 0}}},
    DEV: {"id": DEV, "name": "CONV-001", "type": "OPCUA", "enabled": True, "polling": 3000,
          "property": {"address": "opc.tcp://gateway:4840/vigilimen/conv001/", "port": None, "slot": None, "rack": None,
                       "baudrate": 9600, "databits": 8, "stopbits": 1, "parity": "None", "delay": 10,
                       "forceFC16": False, "timeout": 2000},
          "tags": {tid: {"id": tid, "name": n, "label": n, "type": ty, "address": f"ns=2;i={i}", "daq": dict(daq),
                         "value": False if ty == "Boolean" else 0, "timestamp": 0} for n, ty, i, tid in TAGS}},
}

svg, items, k = [], {}, [0]
def uid(p="svg"):
    k[0] += 1
    return f"{p}_{k[0]:04x}-{k[0] * 7919 % 0xFFFFFF:06x}"

def text(x, y, s, size=20, fill="#222222", weight="normal", anchor="start", extra=""):
    svg.append(f'  <text id="{uid()}" xml:space="preserve" stroke-width="0" fill="{fill}" text-anchor="{anchor}" '
               f'font-weight="{weight}" font-size="{size}" font-family="sans-serif" y="{y}" x="{x}" {extra}>{escape(s)}</text>')

def value(tag, x, y, label, size=26, ph="##.##"):
    text(40, y, label)
    gid = uid("VAL")
    svg.append(f'  <g data-name="{tag}" id="{gid}" type="svg-ext-value">\n   <text xml:space="preserve" stroke-width="0" '
               f'fill="#0d47a1" text-anchor="start" font-weight="bold" font-size="{size}" font-family="sans-serif" '
               f'y="{y}" x="{x}" id="{uid("VAL")}">{ph}</text>\n  </g>')
    items[gid] = {"id": gid, "type": "svg-ext-value", "name": tag, "label": "Value", "hide": False, "lock": False,
                  "property": {"variableId": T[tag], "ranges": [{"min": 20, "max": 80, "color": "", "type": 1, "stroke": ""}],
                                "events": [], "actions": []}}

def lamp(name, tag, cx, cy, ranges, caption, capx):
    text(capx, cy + 7, caption)
    i = uid()
    svg.append(f'  <ellipse data-name="{name}" stroke-width="2" stroke="#000000" fill="#9e9e9e" ry="16" rx="16" cy="{cy}" cx="{cx}" id="{i}"/>')
    items[i] = {"id": i, "type": "svg-ext-shapes", "name": name, "label": "Shapes", "hide": False, "lock": False,
                "property": {"variableId": T[tag], "events": [], "actions": [],
                             "ranges": [{"min": a, "max": b, "color": c, "stroke": "#000000", "type": 2} for a, b, c in ranges]}}

def button(name, label, x, y, w, fill, sets):
    i = uid()
    # Colour is the rect's own static fill. FUXA 'html_button' colours are
    # value RANGES on a tag, which a 0/1 command tag never reaches - that is
    # why a hand-built button stays white.
    svg.append(f'  <rect data-name="{name}" stroke-width="2" stroke="#000000" fill="{fill}" ry="8" rx="8" height="56" width="{w}" y="{y}" x="{x}" id="{i}"/>')
    text(x + w / 2, y + 35, label, 20, "#ffffff", "bold", "middle", 'pointer-events="none"')
    items[i] = {"id": i, "type": "svg-ext-shapes", "name": name, "label": "Shapes", "hide": False, "lock": False,
                "property": {"variableId": None, "ranges": [], "actions": [],
                             "events": [{"type": "click", "action": "onSetValue", "actparam": str(v),
                                          "actoptions": {"variableId": T[t]}} for t, v in sets]}}

text(40, 50, "VIGILIMEN - CONV-001", 28, weight="bold")
text(40, 78, "Simulated plant. OPC UA via gateway, account engineer.", 14, "#666666")
value("BearingTemp_C", 420, 150, "Bearing temperature (degC)")
value("Vibration_mms", 420, 206, "Vibration (mm/s)")
value("MotorCurrent_A", 420, 262, "Motor current (A)")
value("BeltSpeed_mps", 420, 318, "Belt speed (m/s)")
value("Load_tph", 420, 374, "Load (t/h)")
lamp("Running", "Running", 60, 470, [(0, 0, "#9e9e9e"), (1, 1, "#2e7d32")], "Running", 94)
lamp("SafetyTripped", "SafetyTripped", 300, 470, [(0, 0, "#9e9e9e"), (1, 1, "#c62828")], "Safety tripped (red = tripped)", 334)
lamp("VibAlarm", "Vibration_mms", 300, 505,
     [(0, 4.4999, "#9e9e9e"), (4.5, 7.0999, "#f9a825"), (7.1, 1000, "#c62828")],
     "Vibration (amber >= 4.5, red >= 7.1 mm/s)", 334)
button("btn_START", "START", 40, 540, 170, "#2e7d32", [("StartCommand", 1), ("StopCommand", 0)])
button("btn_STOP", "STOP", 240, 540, 170, "#c62828", [("StopCommand", 1), ("StartCommand", 0)])
button("btn_SPIKE", "Spike vibration +8", 440, 540, 200, "#ef6c00", [("FaultVibrationSpike", 8)])
button("btn_MISALIGN", "Misalignment 100%", 660, 540, 200, "#6a1b9a", [("FaultMisalignment", 1)])
button("btn_CLEAR", "Clear all faults", 440, 610, 200, "#455a64", [(f, 0) for f in FAULTS])
text(40, 640, "HMI holds a credential that can start the conveyor (risk R-14). Recorded, not fixed: S8 attacks it.", 14, "#888888")
text(40, 705, "StartCommand", 16)
text(300, 705, "StopCommand", 16)
for tag, x in (("StartCommand", 190), ("StopCommand", 450)):
    gid = uid("VAL")
    svg.append(f'  <g data-name="{tag}" id="{gid}" type="svg-ext-value">\n   <text xml:space="preserve" stroke-width="0" fill="#0d47a1" '
               f'text-anchor="start" font-weight="bold" font-size="18" font-family="sans-serif" y="705" x="{x}" id="{uid("VAL")}">##</text>\n  </g>')
    items[gid] = {"id": gid, "type": "svg-ext-value", "name": tag, "label": "Value", "hide": False, "lock": False,
                  "property": {"variableId": T[tag], "ranges": [{"min": 20, "max": 80, "color": "", "type": 1, "stroke": ""}],
                                "events": [], "actions": []}}

view = {"id": "v_claude_conv001_hmi", "name": "CONV-001 HMI", "type": "svg", "variables": {},
        "profile": {"width": 1024, "height": 768, "bkcolor": "#ffffffff", "margin": 10, "align": "topCenter",
                    "gridType": "fixed", "viewRenderDelay": 0},
        "items": items,
        "svgcontent": '<svg width="1024" height="768" xmlns="http://www.w3.org/2000/svg" xmlns:svg="http://www.w3.org/2000/svg">\n <g>\n  <title>Layer 1</title>\n'
                      + "\n".join(svg) + "\n </g>\n</svg>"}

project = {"devices": devices, "hmi": {"views": [view]}, "recipes": [], "ar": {"enabled": False, "markers": []},
           "version": "1.00", "server": {"id": "0", "name": "FUXA Server", "type": "FuxaServer", "property": {}, "polling": 1000}}

out = Path(__file__).with_name("vigilimen-conv001.fuxa.json")
out.write_text(json.dumps(project, indent=1), encoding="utf-8")
print(f"{out.name}: {len(items)} items, {len(TAGS)} tags")
