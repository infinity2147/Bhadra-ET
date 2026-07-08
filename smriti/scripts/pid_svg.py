"""Hero P&ID author.

Draws the Unit 4 drawings as SVG with ISO-10628-style primitive symbols and
emits, alongside the image, the exact DrawingRegion ground truth
({tag, bbox, symbol_class}) and line connectivity (FEEDS_INTO edges) that a
production CV digitizer would output. Coordinates are in the rendered PNG's
pixel space (SVG user units == px at scale 1; we render at 2x and scale bboxes).
"""
from __future__ import annotations

import json

import fitz

SCALE = 2  # render multiplier; bboxes emitted in rendered-pixel space

W, H = 1200, 760


class Sheet:
    def __init__(self, number: str, title: str, rev: str):
        self.number, self.title, self.rev = number, title, rev
        self.parts: list[str] = []
        self.regions: list[dict] = []
        self.edges: list[dict] = []

    def _region(self, tag: str, x, y, w, h, symbol_class: str):
        self.regions.append({
            "tag": tag, "symbol_class": symbol_class,
            "bbox": [round(x * SCALE), round(y * SCALE),
                     round((x + w) * SCALE), round((y + h) * SCALE)],
        })

    def text(self, x, y, s, size=13, anchor="middle", bold=False, color="#1a2733"):
        weight = "bold" if bold else "normal"
        self.parts.append(
            f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}" '
            f'font-family="Helvetica, Arial" font-weight="{weight}" fill="{color}">{s}</text>')

    def pump(self, tag: str, x, y, label2=""):
        r = 26
        self.parts.append(
            f'<circle cx="{x}" cy="{y}" r="{r}" fill="white" stroke="#1a2733" stroke-width="2.2"/>'
            f'<polygon points="{x-12},{y-14} {x-12},{y+14} {x+16},{y}" fill="none" '
            f'stroke="#1a2733" stroke-width="2"/>')
        self.text(x, y - r - 8, tag, bold=True)
        if label2:
            self.text(x, y + r + 16, label2, size=10, color="#5a6b7a")
        self._region(tag, x - r - 4, y - r - 22, 2 * r + 8, 2 * r + 30, "centrifugal_pump")

    def exchanger(self, tag: str, x, y):
        r = 30
        self.parts.append(
            f'<circle cx="{x}" cy="{y}" r="{r}" fill="white" stroke="#1a2733" stroke-width="2.2"/>'
            f'<polyline points="{x-r},{y} {x-r/2},{y-14} {x},{y+14} {x+r/2},{y-14} {x+r},{y}" '
            f'fill="none" stroke="#1a2733" stroke-width="2"/>')
        self.text(x, y - r - 8, tag, bold=True)
        self._region(tag, x - r - 4, y - r - 22, 2 * r + 8, 2 * r + 26, "shell_tube_exchanger")

    def tank(self, tag: str, x, y, w=70, h=90):
        self.parts.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="white" '
            f'stroke="#1a2733" stroke-width="2.2"/>'
            f'<line x1="{x}" y1="{y+18}" x2="{x+w}" y2="{y+18}" stroke="#1a2733" stroke-width="1"/>')
        self.text(x + w / 2, y - 8, tag, bold=True)
        self._region(tag, x - 4, y - 22, w + 8, h + 26, "storage_tank")

    def cooling_tower(self, tag: str, x, y):
        w, h = 84, 74
        self.parts.append(
            f'<polygon points="{x},{y+h} {x+w},{y+h} {x+w-14},{y} {x+14},{y}" fill="white" '
            f'stroke="#1a2733" stroke-width="2.2"/>'
            f'<path d="M {x+18} {y+12} q 8 -10 16 0 q 8 -10 16 0 q 8 -10 16 0" fill="none" '
            f'stroke="#1a2733" stroke-width="1.6"/>')
        self.text(x + w / 2, y - 8, tag, bold=True)
        self._region(tag, x - 4, y - 22, w + 8, h + 26, "cooling_tower")

    def strainer(self, tag: str, x, y):
        s = 30
        self.parts.append(
            f'<polygon points="{x},{y-s/2} {x+s/2},{y} {x},{y+s/2} {x-s/2},{y}" fill="white" '
            f'stroke="#1a2733" stroke-width="2.2"/>'
            f'<line x1="{x-8}" y1="{y+8}" x2="{x+8}" y2="{y-8}" stroke="#1a2733" stroke-width="1.4"/>')
        self.text(x, y - s / 2 - 8, tag, bold=True, size=11)
        self._region(tag, x - s / 2 - 4, y - s / 2 - 20, s + 8, s + 24, "strainer")

    def psv(self, tag: str, x, y):
        self.parts.append(
            f'<polygon points="{x-11},{y+14} {x+11},{y+14} {x},{y-4}" fill="white" '
            f'stroke="#1a2733" stroke-width="2"/>'
            f'<polyline points="{x},{y-4} {x},{y-16} {x+14},{y-16}" fill="none" '
            f'stroke="#1a2733" stroke-width="2"/>'
            f'<path d="M {x-10} {y-22} l 20 0 m -20 4 l 20 0" stroke="#1a2733" stroke-width="1.3"/>')
        self.text(x, y + 30, tag, bold=True, size=11)
        self._region(tag, x - 16, y - 26, 34, 60, "pressure_safety_valve")

    def valve(self, tag: str, x, y):
        s = 12
        self.parts.append(
            f'<polygon points="{x-s},{y-s} {x-s},{y+s} {x+s},{y-s} {x+s},{y+s}" fill="white" '
            f'stroke="#1a2733" stroke-width="2"/>')
        if tag:
            self.text(x, y + s + 14, tag, size=10, bold=True)
            self._region(tag, x - s - 4, y - s - 4, 2 * s + 8, 2 * s + 30, "valve")

    def instrument(self, tag: str, x, y):
        r = 15
        top, bottom = tag.split("-")[0], tag.split("-", 1)[1]
        self.parts.append(
            f'<circle cx="{x}" cy="{y}" r="{r}" fill="white" stroke="#1a2733" stroke-width="1.6"/>'
            f'<line x1="{x-r}" y1="{y}" x2="{x+r}" y2="{y}" stroke="#1a2733" stroke-width="1"/>')
        self.text(x, y - 3, top, size=8.5, bold=True)
        self.text(x, y + 10, bottom, size=8.5)
        self._region(tag, x - r - 2, y - r - 2, 2 * r + 4, 2 * r + 4, "instrument")

    def pipe(self, points: list[tuple], src: str = "", dst: str = "", label: str = "",
             dashed: bool = False):
        pts = " ".join(f"{x},{y}" for x, y in points)
        dash = ' stroke-dasharray="7,5"' if dashed else ""
        self.parts.append(
            f'<polyline points="{pts}" fill="none" stroke="#2b6cb0" stroke-width="2.4"{dash}/>')
        # arrowhead on last segment
        (x1, y1), (x2, y2) = points[-2], points[-1]
        import math
        ang = math.atan2(y2 - y1, x2 - x1)
        a1 = (x2 - 11 * math.cos(ang - 0.42), y2 - 11 * math.sin(ang - 0.42))
        a2 = (x2 - 11 * math.cos(ang + 0.42), y2 - 11 * math.sin(ang + 0.42))
        self.parts.append(
            f'<polygon points="{x2},{y2} {a1[0]:.1f},{a1[1]:.1f} {a2[0]:.1f},{a2[1]:.1f}" '
            f'fill="#2b6cb0"/>')
        if label:
            mx, my = points[len(points) // 2]
            self.text(mx, my - 8, label, size=9.5, color="#2b6cb0")
        if src and dst:
            self.edges.append({"src": src, "dst": dst, "via": label or "pipe"})

    def svg(self) -> str:
        border = (f'<rect x="6" y="6" width="{W-12}" height="{H-12}" fill="none" '
                  f'stroke="#1a2733" stroke-width="2"/>')
        tb_y = H - 74
        titleblock = (
            f'<rect x="{W-430}" y="{tb_y}" width="{W-6-(W-430)}" height="{H-6-tb_y}" '
            f'fill="white" stroke="#1a2733" stroke-width="1.6"/>'
            f'<text x="{W-418}" y="{tb_y+22}" font-size="13" font-family="Helvetica" '
            f'font-weight="bold" fill="#1a2733">{self.title}</text>'
            f'<text x="{W-418}" y="{tb_y+42}" font-size="11" font-family="Helvetica" '
            f'fill="#1a2733">DWG NO: {self.number}   REV {self.rev}   BHARAT PETROCHEM LTD — UNIT 4</text>'
            f'<text x="{W-418}" y="{tb_y+58}" font-size="9" font-family="Helvetica" '
            f'fill="#5a6b7a">SCALE NTS | ISO 10628 SYMBOLOGY | FOR OPERATION &amp; MAINTENANCE</text>')
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
                f'viewBox="0 0 {W} {H}"><rect width="{W}" height="{H}" fill="#fbfaf7"/>'
                + border + "".join(self.parts) + titleblock + "</svg>")

    def render(self, out_dir, stem: str):
        svg = self.svg()
        (out_dir / f"{stem}.svg").write_text(svg)
        doc = fitz.open(stream=svg.encode(), filetype="svg")
        pix = doc[0].get_pixmap(matrix=fitz.Matrix(SCALE, SCALE))
        pix.save(str(out_dir / f"{stem}.png"))
        (out_dir / f"{stem}.regions.json").write_text(json.dumps({
            "drawing_number": self.number, "title": self.title, "rev": self.rev,
            "image": f"{stem}.png", "width": W * SCALE, "height": H * SCALE,
            "regions": self.regions, "connectivity": self.edges,
        }, indent=1))


def build_cw_pid(out_dir):
    """D-CW-104 rev 3 — Cooling Water System, Area 1 (the hero drawing)."""
    s = Sheet("D-CW-104", "COOLING WATER SYSTEM — AREA 1", "3")
    s.cooling_tower("CT-101", 90, 120)
    s.strainer("STR-101", 300, 194)
    s.pump("P-101", 440, 194, "CW SUPPLY A")
    s.pump("P-102", 440, 330, "CW SUPPLY B (STANDBY)")
    s.psv("PSV-1101", 585, 148)
    s.exchanger("E-201", 760, 194)
    s.exchanger("E-202", 760, 470)
    s.pump("P-103", 1000, 330, "CW BOOSTER")
    s.instrument("PI-1101", 368, 128)
    s.instrument("TI-1103", 640, 258)
    s.instrument("FI-1102", 545, 128)
    s.valve("MOV-110", 640, 194)

    s.pipe([(132, 194), (270, 194)], "CT-101", "STR-101", "CW SUPPLY HDR")
    s.pipe([(315, 194), (414, 194)], "STR-101", "P-101")
    s.pipe([(300, 194), (300, 330), (414, 330)], "STR-101", "P-102", dashed=True)
    s.pipe([(466, 194), (585, 194), (585, 162)], "P-101", "PSV-1101", "RELIEF")
    s.pipe([(466, 194), (628, 194)], "P-101", "MOV-110")
    s.pipe([(652, 194), (730, 194)], "MOV-110", "E-201")
    s.pipe([(466, 330), (700, 330), (700, 214), (730, 214)], "P-102", "E-201", dashed=True)
    s.pipe([(790, 194), (900, 194), (900, 90), (110, 90), (110, 118)], "E-201", "CT-101",
           "CW RETURN")
    s.pipe([(790, 214), (860, 214), (860, 330), (974, 330)], "E-201", "P-103", "TAP TO A2 HDR")
    s.pipe([(1026, 330), (1140, 330)], "P-103", "AREA-2-HDR", "TO AREA 2 CRUDE PREHEAT")
    s.pipe([(1140, 470), (790, 470)], "AREA-2-RET", "E-202", "TRIM CW FROM AREA 2")
    s.pipe([(730, 470), (150, 470), (150, 200)], "E-202", "CT-101", "TRIM RETURN")
    s.text(1140, 316, "AREA 2", size=11, bold=True)
    s.text(210, 640, "NOTES: 1. STR-101 D/P GAUGE LOCAL. 2. SEAL FLUSH PLAN 11 ON P-101/102/103.",
           anchor="start", size=10)
    s.text(210, 658, "3. MONSOON MODE: WEEKLY SEAL FLUSH VERIFICATION PER SOP-CW-012 REV 3.",
           anchor="start", size=10)
    s.render(out_dir, "D-CW-104")
    return s


def build_et_pid(out_dir):
    """D-ET-401 rev 1 — Effluent Treatment, Area 4."""
    s = Sheet("D-ET-401", "EFFLUENT TREATMENT — AREA 4", "1")
    s.tank("TK-401", 200, 160, w=110, h=130)
    s.pump("P-107", 520, 230, "EFFLUENT TRANSFER")
    s.valve("MOV-410", 660, 230)
    s.instrument("LI-4011", 180, 120)
    s.text(255, 320, "EQUALIZATION TANK — CONFINED SPACE (ENTRY PER SOP-ET-005)",
           size=10, color="#8a2c2c")
    s.pipe([(310, 230), (494, 230)], "TK-401", "P-107")
    s.pipe([(546, 230), (648, 230)], "P-107", "MOV-410")
    s.pipe([(672, 230), (860, 230)], "MOV-410", "ETP-OUTFALL", "TO ETP OUTFALL")
    s.text(880, 234, "ETP", size=11, bold=True, anchor="start")
    s.render(out_dir, "D-ET-401")
    return s


if __name__ == "__main__":
    from pathlib import Path
    out = Path(__file__).resolve().parents[1] / "corpus" / "drawings"
    out.mkdir(parents=True, exist_ok=True)
    build_cw_pid(out)
    build_et_pid(out)
    print("drawings written to", out)
