"""Generate the full synthetic corpus for 'Bharat Petrochem Ltd. — Refinery Unit 4'.

Every document is internally consistent with docs/corpus-design.md: the same tags,
people and history recur across document types so the knowledge graph forms real
cross-document links. Planted patterns (monsoon seal failures, confined-space
near-miss precursors, compliance gaps, SOP version chain) drive the demo beats.

Documents are authored as real PDFs (via pdf_author) so ingestion is honest.
The confined-space permit for TK-401 is dated tomorrow (relative to generation
time) so the proactive-warning demo always works.
"""
from __future__ import annotations

import datetime as dt
import json
import random
from pathlib import Path

from pdf_author import write_scanned_pdf, write_text_pdf
from pid_svg import build_cw_pid, build_et_pid

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "corpus"
TODAY = dt.date.today()
TOMORROW = TODAY + dt.timedelta(days=1)

rng = random.Random(42)

# ---------------------------------------------------------------- equipment
EQUIPMENT = [
    {"tag": "P-101", "type": "centrifugal_pump", "service": "Cooling water supply A",
     "manufacturer": "BurgFlow", "model": "MS-40D", "install_date": "1998-11-02",
     "area": "Area 1", "criticality": "high", "seal_model": "BurgFlow MS-40D cartridge seal"},
    {"tag": "P-102", "type": "centrifugal_pump", "service": "Cooling water supply B (standby)",
     "manufacturer": "BurgFlow", "model": "MS-40D", "install_date": "1998-11-02",
     "area": "Area 1", "criticality": "high", "seal_model": "BurgFlow MS-40D cartridge seal"},
    {"tag": "P-103", "type": "centrifugal_pump", "service": "Cooling water booster to Area 2",
     "manufacturer": "BurgFlow", "model": "MS-32C", "install_date": "2004-03-15",
     "area": "Area 1", "criticality": "medium", "seal_model": "BurgFlow MS-40D cartridge seal"},
    {"tag": "P-107", "type": "centrifugal_pump", "service": "Effluent transfer",
     "manufacturer": "BurgFlow", "model": "MS-32C", "install_date": "2009-06-20",
     "area": "Area 4", "criticality": "medium", "seal_model": "BurgFlow MS-40D cartridge seal"},
    {"tag": "E-201", "type": "shell_tube_exchanger", "service": "CW / crude interchanger",
     "manufacturer": "Thermax", "model": "ST-800", "install_date": "1998-11-02",
     "area": "Area 1", "criticality": "high"},
    {"tag": "E-202", "type": "shell_tube_exchanger", "service": "Trim cooler",
     "manufacturer": "Thermax", "model": "ST-400", "install_date": "2011-01-12",
     "area": "Area 1", "criticality": "medium"},
    {"tag": "T-301", "type": "storage_tank", "service": "HSD (diesel) storage",
     "manufacturer": "site-built", "model": "fixed roof 5000 m3", "install_date": "1999-05-30",
     "area": "Area 3", "criticality": "high"},
    {"tag": "T-302", "type": "storage_tank", "service": "Naphtha storage",
     "manufacturer": "site-built", "model": "fixed roof 3000 m3", "install_date": "1999-05-30",
     "area": "Area 3", "criticality": "high"},
    {"tag": "PSV-1101", "type": "pressure_safety_valve", "service": "P-101 discharge header relief",
     "manufacturer": "Sarasin", "model": "RSBD-2", "install_date": "1998-11-02",
     "area": "Area 1", "criticality": "high"},
    {"tag": "PSV-3101", "type": "pressure_safety_valve", "service": "T-301 breather relief",
     "manufacturer": "Sarasin", "model": "RSBD-1", "install_date": "1999-05-30",
     "area": "Area 3", "criticality": "high"},
    {"tag": "CT-101", "type": "cooling_tower", "service": "CW return / evaporative cooling",
     "manufacturer": "Paharpur", "model": "CF-3200", "install_date": "1998-11-02",
     "area": "Area 1", "criticality": "high"},
    {"tag": "STR-101", "type": "strainer", "service": "P-101/P-102 common suction strainer",
     "manufacturer": "Filtrex", "model": "basket DN300", "install_date": "1998-11-02",
     "area": "Area 1", "criticality": "medium"},
    {"tag": "TK-401", "type": "equalization_tank", "service": "Effluent equalization (CONFINED SPACE)",
     "manufacturer": "site-built", "model": "620 m3", "install_date": "2009-06-20",
     "area": "Area 4", "criticality": "medium"},
    {"tag": "V-205", "type": "knock_out_drum", "service": "Area 2 fuel gas KO drum",
     "manufacturer": "L&T", "model": "KOD-1200", "install_date": "2001-08-14",
     "area": "Area 2", "criticality": "medium"},
    {"tag": "MOV-110", "type": "motor_operated_valve", "service": "CW header isolation",
     "manufacturer": "Rotork", "model": "IQ3", "install_date": "2015-02-10",
     "area": "Area 1", "criticality": "medium"},
]

PEOPLE = {
    "rks": {"name": "R. K. Sharma", "role": "Senior Reliability Engineer (retiring Dec 2026)"},
    "ad": {"name": "A. Deshpande", "role": "Maintenance Planner"},
    "sv": {"name": "S. Venkatesan", "role": "Shift Supervisor"},
    "mp": {"name": "M. Pillai", "role": "Safety Officer"},
    "nk": {"name": "N. Kaur", "role": "Inspection Engineer"},
    "jr": {"name": "J. Reddy", "role": "Compliance Officer"},
}

# ---------------------------------------------------------------- work orders
HERO_WOS = [
    # --- Pattern A: monsoon mechanical seal failures, P-101 / P-103 / P-107
    dict(id="WO-2019-0712", equipment="P-101", date="2019-07-18", wo_type="CM",
         title="P-101 mechanical seal replacement after leak",
         findings="Seal faces (BurgFlow MS-40D cartridge) heavily scored. Gland leak-off "
                  "exceeded 60 drops/min. Suction strainer STR-101 basket found 40% blocked "
                  "with silt after monsoon rains; cooling water visibly turbid. Suspected "
                  "intermittent cavitation damaged the seal faces.",
         parts="MS-40D cartridge seal x1, gasket kit", labor_h=14, downtime_h=9,
         author="ad", closed_by="rks"),
    dict(id="WO-2021-0843", equipment="P-101", date="2021-08-05", wo_type="CM",
         title="P-101 seal failure - replace cartridge seal",
         findings="Second wet-season seal loss. Face pattern identical to 2019 event: "
                  "thermal crazing + abrasive scoring. STR-101 differential pressure logged "
                  "0.9 bar the same week (normal < 0.3). Recommended monsoon strainer "
                  "cleaning frequency be doubled - NOT implemented at the time.",
         parts="MS-40D cartridge seal x1", labor_h=12, downtime_h=8,
         author="ad", closed_by="rks"),
    dict(id="WO-2023-0771", equipment="P-101", date="2023-07-22", wo_type="CM",
         title="P-101 seal replacement (repeat failure)",
         findings="Third monsoon seal failure since 2019 on this pump. R.K. Sharma closeout "
                  "note: 'Suspect strainer bypass during monsoon - third time I've seen this "
                  "since 2019. CW turbidity spikes after heavy rain at CT-101 basin, STR-101 "
                  "blinds, pump cavitates briefly on start, seal faces open and ingest grit. "
                  "Fix the water, not the seal. Recommend monsoon-mode weekly seal flush "
                  "verification and STR-101 cleaning at dP 0.4 bar.'",
         parts="MS-40D cartridge seal x1, seal flush tubing", labor_h=16, downtime_h=11,
         author="ad", closed_by="rks"),
    dict(id="WO-2024-0912", equipment="P-101", date="2024-09-10", wo_type="CM",
         title="P-101 seal leak - replace seal, inspect flush line",
         findings="Seal flush line (Plan 11) orifice found partially plugged with scale; "
                  "flush flow ~50% of design. Combined with monsoon turbidity this "
                  "accelerated face wear. Flush orifice replaced. Note: SOP-CW-012 rev 2 has "
                  "no seal-flush verification step - revision proposed.",
         parts="MS-40D cartridge seal x1, flush orifice", labor_h=13, downtime_h=8,
         author="ad", closed_by="rks"),
    dict(id="WO-2025-0655", equipment="P-101", date="2025-06-28", wo_type="CM",
         title="P-101 seal replacement at monsoon onset",
         findings="Failure caught early by the new weekly monsoon seal-flush verification "
                  "(SOP-CW-012 rev 3). Downtime halved vs prior events. Root cause chain "
                  "unchanged: CT-101 basin turbidity -> STR-101 blinding -> cavitation. "
                  "Fleet check recommended: P-103 and P-107 share the same MS-40D seal model.",
         parts="MS-40D cartridge seal x1", labor_h=10, downtime_h=4,
         author="ad", closed_by="rks"),
    dict(id="WO-2022-0808", equipment="P-103", date="2022-08-19", wo_type="CM",
         title="P-103 booster pump seal failure",
         findings="MS-40D seal failed after wet-season operation. Same abrasive scoring "
                  "signature as P-101 history. P-103 takes suction downstream of E-201 but "
                  "shares the same cooling water quality.",
         parts="MS-40D cartridge seal x1", labor_h=11, downtime_h=6,
         author="ad", closed_by="sv"),
    dict(id="WO-2024-0733", equipment="P-103", date="2024-07-30", wo_type="CM",
         title="P-103 seal replacement (second wet-season failure)",
         findings="Second monsoon failure on P-103. Seal face condition matches P-101 "
                  "pattern. Recommend including P-103 in monsoon-mode flush verification "
                  "round (currently only P-101/P-102 covered by SOP-CW-012).",
         parts="MS-40D cartridge seal x1", labor_h=11, downtime_h=7,
         author="ad", closed_by="rks"),
    dict(id="WO-2023-0921", equipment="P-107", date="2023-09-14", wo_type="CM",
         title="P-107 effluent pump seal leak",
         findings="MS-40D seal leak on effluent service. High solids in TK-401 equalization "
                  "tank during monsoon; same seal model as CW pumps. Abrasive wear pattern.",
         parts="MS-40D cartridge seal x1", labor_h=9, downtime_h=5,
         author="ad", closed_by="sv"),
    # --- E-201 fouling / P-101 high temperature trips (Copilot demo beats)
    dict(id="WO-2025-4471", equipment="P-101", date="2025-07-09", wo_type="breakdown",
         title="P-101 tripped on high discharge temperature TI-1103",
         findings="TI-1103 reached 68 degC (trip 65). Investigation: E-201 CW-side fouled - "
                  "outlet approach temperature 9 degC above clean baseline; STR-101 dP 0.55 "
                  "bar. E-201 backflushed, STR-101 cleaned, trip reset. Root cause: fouled "
                  "cooler restricting CW flow (FI-1102 low). Monsoon turbidity again.",
         parts="none", labor_h=6, downtime_h=3, author="sv", closed_by="rks"),
    dict(id="WO-2025-4620", equipment="P-101", date="2025-09-02", wo_type="breakdown",
         title="P-101 high temperature trip (repeat) - TI-1103",
         findings="Second high-temp trip of the season, same signature as WO-2025-4471. "
                  "E-201 fouling confirmed by dP survey; chemical clean completed. "
                  "Root cause: fouled cooler. Action: E-201 monsoon backflush schedule "
                  "added to PM plan for 2026.",
         parts="cleaning chemicals", labor_h=8, downtime_h=5, author="sv", closed_by="rks"),
    # --- PSV history (compliance evidence)
    dict(id="WO-2022-0410", equipment="PSV-1101", date="2022-04-12", wo_type="PM",
         title="PSV-1101 removal, bench test and recertification",
         findings="Pop test at 1.02x set pressure - PASS. Recertified and reinstalled. "
                  "Next test due per OISD-STD-132 interval.",
         parts="gaskets", labor_h=6, downtime_h=0, author="nk", closed_by="nk"),
    dict(id="WO-2025-0301", equipment="PSV-3101", date="2025-03-06", wo_type="PM",
         title="PSV-3101 bench test and recertification",
         findings="Pop test PASS at set pressure. Recertified. In compliance window.",
         parts="gaskets", labor_h=5, downtime_h=0, author="nk", closed_by="nk"),
]

PM_TEMPLATES = [
    ("P-102", "PM", "Quarterly vibration survey and lube oil top-up", "Vibration within ISO 10816 zone A/B. Oil level corrected."),
    ("CT-101", "PM", "Cooling tower basin inspection and dosing check", "Basin silt level {}mm. Biocide dosing pump OK."),
    ("MOV-110", "PM", "MOV partial stroke test", "Stroke time {}s, within spec. Torque profile normal."),
    ("E-202", "PM", "Trim cooler dP survey", "Shell-side dP {} bar. No action."),
    ("V-205", "PM", "KO drum level instrument calibration", "LT calibrated, drain checked."),
    ("T-302", "PM", "Tank dyke and valve inspection", "Dyke wall sound, drain valve locked closed."),
    ("STR-101", "PM", "Strainer basket cleaning", "Basket removed and washed. dP restored to 0.1 bar."),
    ("P-107", "PM", "Effluent pump coupling alignment check", "Alignment within 0.05 mm TIR."),
]


def gen_filler_wos() -> list[dict]:
    out = []
    n = 0
    for year in range(2019, 2026):
        for tag, wo_type, title, findings in PM_TEMPLATES:
            n += 1
            if rng.random() < 0.35:
                continue
            month = rng.randint(1, 12)
            day = rng.randint(1, 28)
            f = findings.format(rng.choice([8, 12, 20, 35, 0.12, 0.18, 0.22]))
            out.append(dict(
                id=f"WO-{year}-{1000+n:04d}", equipment=tag, date=f"{year}-{month:02d}-{day:02d}",
                wo_type=wo_type, title=title, findings=f, parts="consumables",
                labor_h=rng.randint(2, 6), downtime_h=0, author="ad", closed_by="sv"))
    return out


def wo_lines(wo: dict) -> list[str]:
    a, c = PEOPLE[wo["author"]], PEOPLE[wo["closed_by"]]
    return [
        f"Work Order No: {wo['id']}        Type: {wo['wo_type']}        Priority: {'P1' if wo['wo_type']=='breakdown' else 'P3'}",
        f"Equipment: {wo['equipment']}        Date completed: {wo['date']}",
        f"Title: {wo['title']}",
        "",
        "FINDINGS / WORK PERFORMED:",
        wo["findings"],
        "",
        f"Parts used: {wo['parts']}",
        f"Labor hours: {wo['labor_h']}        Equipment downtime: {wo['downtime_h']} h",
        f"Raised by: {a['name']} ({a['role']})",
        f"Closed by: {c['name']} ({c['role']})",
        "Reference drawing: D-CW-104 rev 3" if wo["equipment"] in
        ("P-101", "P-102", "P-103", "E-201", "E-202", "STR-101", "CT-101", "MOV-110", "PSV-1101")
        else "Reference drawing: D-ET-401 rev 1" if wo["equipment"] in ("P-107", "TK-401")
        else "",
    ]


# ---------------------------------------------------------------- inspections
def gen_inspections() -> list[dict]:
    out = []
    # STR-101 dP series: high in monsoon months (the corroborating signal)
    for date, dp in [("2021-08-02", 0.85), ("2022-03-14", 0.15), ("2023-07-18", 0.92),
                     ("2023-12-04", 0.12), ("2024-08-21", 0.71), ("2025-02-10", 0.14),
                     ("2025-07-05", 0.58)]:
        monsoon = dp > 0.4
        out.append(dict(
            id=f"INSP-STR101-{date}", equipment="STR-101", date=date, method="dP gauge reading",
            result="ALERT" if monsoon else "PASS",
            text=f"STR-101 differential pressure recorded {dp} bar (normal < 0.3, clean ~0.1). "
                 + ("Basket blinding consistent with monsoon CW turbidity from CT-101 basin. "
                    "Cleaning recommended within 48 h." if monsoon else
                    "Within normal range.")))
    # E-201 fouling series
    for date, appr in [("2023-08-01", 7.5), ("2024-09-05", 8.2), ("2025-07-15", 9.0),
                       ("2025-10-01", 2.1)]:
        fouled = appr > 5
        out.append(dict(
            id=f"INSP-E201-{date}", equipment="E-201", date=date, method="thermal performance survey",
            result="ALERT" if fouled else "PASS",
            text=f"E-201 CW-side approach temperature {appr} degC above clean baseline. "
                 + ("Fouling significant; correlates with P-101 high-temperature trip risk on "
                    "TI-1103. Backflush/chemical clean recommended." if fouled else
                    "Post-cleaning performance restored.")))
    # T-301 external inspection: last done 2021 -> next due soon (time-aware warning)
    out.append(dict(
        id="INSP-T301-2021-11-20", equipment="T-301", date="2021-11-20",
        method="external visual + UT thickness (OISD-129 schedule)", result="PASS",
        text="T-301 external inspection completed. Shell courses UT within corrosion allowance. "
             "Per OISD-STD-129 external inspection interval (5 years), next external inspection "
             "due by 2026-11-20."))
    # PSV-1101 record trail: tested 2022, due 2024/2025 window, deferred -> OVERDUE (gap)
    out.append(dict(
        id="INSP-PSV1101-2022-04-12", equipment="PSV-1101", date="2022-04-12",
        method="bench pop test", result="PASS",
        text="PSV-1101 bench tested and recertified (see WO-2022-0410). Certificate PSV-CERT-2231. "
             "Next test due within the OISD-STD-132 periodicity for critical relief valves."))
    out.append(dict(
        id="INSP-PSV3101-2025-03-06", equipment="PSV-3101", date="2025-03-06",
        method="bench pop test", result="PASS",
        text="PSV-3101 bench tested and recertified (WO-2025-0301). Certificate PSV-CERT-2519. "
             "In compliance."))
    # fire water / drill records: last drill old -> gap
    out.append(dict(
        id="INSP-FIREDRILL-2025-01-15", equipment="Area 3", date="2025-01-15",
        method="emergency response drill record", result="PASS",
        text="Fire and emergency drill conducted for Area 3 tank farm (T-301/T-302 scenario). "
             "Muster time 6 min. NOTE: Factories Act read with State Rules and OISD guidance "
             "expects drills at least once every calendar quarter for MAH units. No later "
             "drill record exists for Area 3 as of mid-2026."))
    out.append(dict(
        id="INSP-FW-2026-05-11", equipment="Area 3", date="2026-05-11",
        method="fire water pump weekly run test", result="PASS",
        text="Jockey and main fire water pumps auto-start tested per OISD-STD-116; header "
             "pressure held at 8.8 kg/cm2 at the hydraulically remotest point in Area 3 "
             "(design minimum 7.0 kg/cm2). Jockey pump J-FW-2 capacity verified at 1.2% of "
             "design fire water rate with auto cut-in at 8.2 and cut-off at 9.0 kg/cm2. "
             "Weekly test log current."))
    # --- positive compliance evidence (so the register is not all-red; the
    #     planted hero gaps remain: PSV-1101, drills, T-301 external, TK-401 permit)
    out.append(dict(
        id="INSP-EARTH-2026-02-18", equipment="T-301", date="2026-02-18",
        method="tank earthing resistance test (megger, competent person)", result="PASS",
        text="Annual earth-resistance test per Petroleum Rules 2002 Rules 127/128: T-301 "
             "measured 2.1 ohms and T-302 measured 2.4 ohms across both diametrically "
             "opposite connections (limit 7 ohms). Both tanks retain two separate and "
             "distinct earth connections. Record retained in the licensee file."))
    out.append(dict(
        id="DOC-PESO-LICENCE-2024", equipment="T-301", date="2024-01-09",
        method="PESO storage licence verification", result="PASS",
        text="Petroleum storage licence P/HQ/MH/15/2214(P) under Petroleum Rules 2002 "
             "Rule 116 held for the Unit 4 tank farm covering T-301 (HSD, Class B) and "
             "T-302 (naphtha, Class A); renewed 2024-01-09, valid to 2028-12-31. Licensed "
             "capacities within sanctioned limits."))
    out.append(dict(
        id="INSP-TANKMOUNT-2025-10-12", equipment="T-302", date="2025-10-12",
        method="post-monsoon tank mountings check (OISD-129 10.1.3)", result="PASS",
        text="Post-monsoon annual check of tank mountings for T-301 and T-302: breather "
             "valves, P&V valves and flame arrestors removed, cleaned and function-tested "
             "operable. PSV-3101 visually verified in-service. Completed within the 2025 "
             "post-monsoon window."))
    out.append(dict(
        id="INSP-V205-HYDRO-2023-03-22", equipment="V-205", date="2023-03-22",
        method="pressure vessel hydraulic test + internal inspection (SMPV(U) R.19)", result="PASS",
        text="V-205 KO drum hydraulically tested by competent person at the pressure marked "
             "on the vessel per SMPV(U) Rules 2016 Rule 19(1)(a); internal inspection and "
             "residual thickness measurement completed - thickness within corrosion "
             "allowance. Test certificate CP/2023/0187. Next periodic test due 2028-03-22."))
    out.append(dict(
        id="INSP-V205-RV-2026-01-20", equipment="V-205", date="2026-01-20",
        method="relief valve annual test by competent person (SMPV(U) R.18(2)(xiii))", result="PASS",
        text="V-205 relief valve tested for correct operation by competent person per "
             "SMPV(U) Rules 2016 Rule 18(2)(xiii); start-to-discharge within tolerance of "
             "set pressure. Certificate CP/2026/0031 issued in the prescribed proforma."))
    out.append(dict(
        id="INSP-FWSPRAY-2026-03-02", equipment="T-302", date="2026-03-02",
        method="fixed water spray system quarterly function test", result="PASS",
        text="Fixed water spray (deluge) system installed on T-302 (naphtha, Class A, "
             "diameter > 6 m per OISD-STD-116 cl. 4.2.1) function-tested: deluge valve "
             "opened on test signal, ring main pressure adequate, nozzles clear. Quarterly "
             "test record current."))
    out.append(dict(
        id="DOC-PTW-TRAINING-2026", equipment="Area 3", date="2026-01-22",
        method="work permit system training record (OISD-STD-105)", result="PASS",
        text="Annual one-day work permit system training completed 2026-01-22 for all "
             "authorized permit issuers and receivers of Unit 4 (22 personnel) per "
             "OISD-STD-105; attendance register and test scores on file. Permit register "
             "audit shows shift-wise validity and revalidation limits observed."))
    return out


def insp_lines(i: dict) -> list[str]:
    return [
        f"Inspection Report: {i['id']}",
        f"Equipment / Location: {i['equipment']}        Date: {i['date']}",
        f"Method: {i['method']}        Result: {i['result']}",
        "",
        "DETAILS:",
        i["text"],
        "",
        f"Inspector: {PEOPLE['nk']['name']} ({PEOPLE['nk']['role']})",
    ]


# ---------------------------------------------------------------- SOPs
SOPS = [
    dict(id="SOP-CW-012", rev=1, date="2015-03-10", title="Operation & Changeover of CW Pumps P-101 / P-102",
         steps=[
             "1. Confirm CT-101 basin level > 60% on local gauge.",
             "2. Open suction valve fully; crack open discharge valve.",
             "3. Start selected pump (P-101 duty / P-102 standby) from MCC.",
             "4. Slowly open discharge valve; confirm PI-1101 within 3.2-3.8 kg/cm2.",
             "5. Confirm flow on FI-1102 > 420 m3/h.",
             "6. For changeover, start standby pump first, then stop duty pump.",
             "7. Log changeover in shift register."],
         hazards="Rotating equipment; water hammer on fast valve operation."),
    dict(id="SOP-CW-012", rev=2, date="2021-09-01", title="Operation & Changeover of CW Pumps P-101 / P-102",
         steps=[
             "1. Confirm CT-101 basin level > 60% on local gauge.",
             "2. CHECK STR-101 DIFFERENTIAL PRESSURE: if dP > 0.4 bar, arrange strainer cleaning "
             "BEFORE pump start (added rev 2 after 2021 seal failure, ref WO-2021-0843).",
             "3. Open suction valve fully; crack open discharge valve.",
             "4. Start selected pump from MCC.",
             "5. Slowly open discharge valve; confirm PI-1101 within 3.2-3.8 kg/cm2.",
             "6. Confirm flow on FI-1102 > 420 m3/h.",
             "7. For changeover, start standby pump first, then stop duty pump.",
             "8. Log changeover and STR-101 dP reading in shift register."],
         hazards="Rotating equipment; water hammer; cavitation at blinded strainer."),
    dict(id="SOP-CW-012", rev=3, date="2025-04-15", title="Operation & Changeover of CW Pumps P-101 / P-102",
         steps=[
             "1. Confirm CT-101 basin level > 60% on local gauge.",
             "2. Check STR-101 differential pressure: if dP > 0.4 bar, arrange strainer cleaning "
             "before pump start.",
             "3. MONSOON MODE (June-September): perform WEEKLY seal flush (Plan 11) verification "
             "on P-101 and P-102 - confirm flush flow at the rotameter and no blockage at the "
             "flush orifice. Added rev 3 from lessons learned in WO-2024-0912 / reliability "
             "review 2025 (R.K. Sharma).",
             "4. Open suction valve fully; crack open discharge valve.",
             "5. Start selected pump from MCC.",
             "6. Slowly open discharge valve; confirm PI-1101 within 3.2-3.8 kg/cm2.",
             "7. Confirm flow on FI-1102 > 420 m3/h.",
             "8. For changeover, start standby pump first, then stop duty pump.",
             "9. Log changeover, STR-101 dP and (monsoon) flush verification in shift register."],
         hazards="Rotating equipment; water hammer; cavitation at blinded strainer; seal failure "
                 "spray hazard."),
    dict(id="SOP-ET-005", rev=2, date="2023-05-20", title="Confined Space Entry - TK-401 Equalization Tank",
         steps=[
             "1. Obtain confined space entry permit (PTW) authorized by Safety Officer.",
             "2. Isolate TK-401: blind inlet and outlet lines, LOTO P-107.",
             "3. Drain and flush tank; remove sludge as far as practicable from outside.",
             "4. FORCED VENTILATION / AIR PURGE: run eductor for MINIMUM 4 HOURS before entry. "
             "Do not shorten purge for schedule reasons (ref near-miss NM-2019-07, NM-2022-31).",
             "5. Gas test by competent person: O2 19.5-23.5%, H2S < 10 ppm, LEL < 5% - "
             "IMMEDIATELY BEFORE entry and REPEAT EVERY 30 MINUTES during work.",
             "6. CAUTION: disturbing settled sludge can re-release H2S even after a passing "
             "initial gas test. Continuous monitor mandatory inside.",
             "7. Standby attendant at manway at all times; rescue tripod rigged.",
             "8. Entry log maintained; permit closed on exit."],
         hazards="H2S from sludge; oxygen deficiency; engulfment."),
    dict(id="SOP-FW-002", rev=1, date="2019-02-01", title="Weekly Fire Water Pump Test - Unit 4",
         steps=["1. Notify control room.", "2. Auto-start test on pressure drop simulation.",
                "3. Record jockey/main/diesel pump start pressures.",
                "4. Run main pump 30 min; log header pressure (target >= 8.5 kg/cm2 per "
                "OISD-STD-116).", "5. Restore auto lineup."],
         hazards="High pressure water; rotating equipment."),
    dict(id="SOP-TK-014", rev=1, date="2020-06-10", title="Manual Gauging & Sampling of T-301 / T-302",
         steps=["1. Verify tank not receiving/dispatching.", "2. Bond sampling equipment; "
                "use only conductive tape.", "3. Wait 30 min after any transfer before gauging "
                "(static electricity).", "4. Record level, temperature, water cut.",
                "5. Close gauge hatch fully."],
         hazards="Flammable atmosphere at gauge hatch; static discharge."),
    dict(id="SOP-EX-003", rev=1, date="2018-04-22", title="E-201 Exchanger Backflush / Chemical Cleaning",
         steps=["1. Swap CW duty to P-102 leg / E-202 trim as applicable.",
                "2. Isolate E-201 CW side; connect backflush hoses.",
                "3. Backflush against normal flow for 2 h; monitor effluent clarity.",
                "4. If approach temperature not restored, circulate approved descalant 4 h.",
                "5. Neutralize, drain to ETP via TK-401, restore lineup."],
         hazards="Chemical handling; pressurized hoses."),
    dict(id="SOP-HW-001", rev=3, date="2022-01-05", title="Hot Work Permit Procedure - Unit 4",
         steps=["1. Gas test at worksite; LEL must be 0% for welding in Area 3.",
                "2. Fire watch posted with extinguisher.", "3. Screens and drain covers in place.",
                "4. Permit valid one shift only; revalidate after breaks.",
                "5. Post-work fire watch 30 min."],
         hazards="Ignition of hydrocarbon vapors."),
    dict(id="SOP-LOTO-001", rev=2, date="2021-11-11", title="Lockout-Tagout of Rotating Equipment",
         steps=["1. Identify all energy sources at MCC and field.",
                "2. Apply personal locks and tags; try-start test.",
                "3. Record in LOTO register; remove only by lock owner."],
         hazards="Stored energy; inadvertent start."),
    dict(id="SOP-CT-006", rev=1, date="2019-08-30", title="CT-101 Cooling Tower Basin Cleaning & Dosing",
         steps=["1. Reduce CW demand; swing to single-pump operation.",
                "2. Vacuum basin silt quadrant by quadrant (monsoon: monthly; dry season: quarterly).",
                "3. Verify biocide and dispersant dosing rates.",
                "4. Record basin turbidity sample result."],
         hazards="Legionella aerosol; slippery surfaces."),
    dict(id="SOP-PSV-002", rev=1, date="2017-05-16", title="PSV Removal, Bench Testing and Reinstallation",
         steps=["1. Confirm equipment depressurized and isolated.",
                "2. Remove PSV; tag with location and set pressure.",
                "3. Bench pop test at certified shop; witness by Inspection.",
                "4. Recertify, fit new gaskets, reinstall, seal wire.",
                "5. Update test register and certificate file (OISD-STD-132 periodicity)."],
         hazards="Trapped pressure; lifting."),
    dict(id="SOP-MOV-004", rev=1, date="2016-09-12", title="MOV-110 Operation and Partial Stroke Test",
         steps=["1. Confirm CW system lineup allows brief flow disturbance.",
                "2. Initiate partial stroke from panel; observe torque curve.",
                "3. Full stroke annually during shutdown only.",
                "4. Record stroke time and torque signature."],
         hazards="Flow transient; pinch points."),
]


def sop_lines(s: dict) -> list[str]:
    lines = [
        f"Standard Operating Procedure {s['id']}        Revision: {s['rev']}        "
        f"Effective date: {s['date']}",
        f"Title: {s['title']}",
        "",
        "PROCEDURE STEPS:",
        *s["steps"],
        "",
        f"HAZARDS: {s['hazards']}",
        "Approved by: Plant Manager, Unit 4",
    ]
    if s["rev"] > 1:
        lines.insert(2, f"Supersedes: {s['id']} rev {s['rev']-1}")
    return lines


# ---------------------------------------------------------------- incidents / near-misses
INCIDENTS = [
    dict(id="NM-2019-07", date="2019-08-24", area="Area 4", equipment="TK-401",
         category="near_miss_toxic_gas",
         title="H2S alarm during TK-401 confined space entry",
         narrative="During desludging inside TK-401, personal H2S monitor alarmed at 12 ppm "
                   "approximately 40 minutes after entry. Entry gas test HAD PASSED. "
                   "Investigation: forced air purge was shortened to ~2 h (procedure requires "
                   "4 h) due to schedule pressure on the monsoon outage; disturbing settled "
                   "sludge re-released H2S. Workers exited safely.",
         root_cause="Shortened pre-entry purge + sludge disturbance re-releasing H2S; "
                    "schedule pressure.",
         precursors="confined space entry; TK-401/Area 4; monsoon window high sludge load; "
                    "purge duration below 4 h; initial gas test passed",
         actions="SOP-ET-005 to mandate minimum 4 h purge and 30-min repeat gas tests.",
         permit="PTW-2019-0288"),
    dict(id="NM-2022-31", date="2022-09-13", area="Area 4", equipment="TK-401",
         category="near_miss_toxic_gas",
         title="Repeat H2S excursion during TK-401 entry",
         narrative="Near-identical repeat of NM-2019-07. Entry crew withdrew when continuous "
                   "monitor read 9 ppm H2S rising, ~35 minutes into sludge raking. Purge had "
                   "again been curtailed (~3 h) because the eductor was borrowed by another "
                   "job. Monsoon-season sludge load was high. Same failure pattern as 2019 "
                   "despite SOP revision - procedural control alone is proving weak.",
         root_cause="Purge below 4 h; equipment availability planning; monsoon sludge load.",
         precursors="confined space entry; TK-401/Area 4; monsoon window high sludge load; "
                    "purge duration below 4 h; eductor availability conflict",
         actions="Eductor dedicated to confined space jobs; permit checklist adds recorded "
                 "purge start/finish times.",
         permit="PTW-2022-0871"),
    dict(id="INC-2018-02", date="2018-06-30", area="Area 1", equipment="P-101",
         category="loss_of_containment",
         title="P-101 seal spray - minor CW release",
         narrative="Mechanical seal on P-101 opened during monsoon start-up, spraying cooling "
                   "water over the pump bay. No injury. First recorded instance of the "
                   "monsoon seal distress pattern later seen in 2019/2021/2023/2024/2025 "
                   "work orders.",
         root_cause="Cavitation after strainer blinding (post-event analysis 2023).",
         precursors="monsoon onset; STR-101 high dP; pump start after standby",
         actions="Initially treated as one-off; pattern recognized only in 2023.", permit=""),
    dict(id="INC-2020-03", date="2020-03-11", area="Area 3", equipment="T-302",
         category="fire_small",
         title="Small flange fire at T-302 mixer during hot work",
         narrative="Grinding spark ignited residue at a leaking mixer flange near T-302. "
                   "Extinguished with DCP in under a minute. Gas test had been done 3 h "
                   "before work started, not immediately prior.",
         root_cause="Stale gas test; leaking flange not identified in JSA.",
         precursors="hot work near live naphtha equipment; gas test older than 1 h",
         actions="SOP-HW-001 rev 3: gas test immediately before hot work; revalidation rule.",
         permit="PTW-2020-0104"),
    dict(id="INC-2023-08", date="2023-07-23", area="Area 1", equipment="P-101",
         category="equipment_damage",
         title="P-101 bearing distress following seal failure operation",
         narrative="Pump run briefly with failed seal (WO-2023-0771 event) allowed CW into "
                   "bearing housing; DE bearing replaced. Consequential damage of the monsoon "
                   "seal pattern.",
         root_cause="Operation with failed seal; delayed changeover to P-102.",
         precursors="seal leak alarm ignored for one shift; standby pump not started",
         actions="Changeover drill added; leak-off inspection on operator round.", permit=""),
    dict(id="NM-2020-14", date="2020-10-02", area="Area 4", equipment="P-107",
         category="near_miss_toxic_gas",
         title="H2S odor at P-107 during seal replacement",
         narrative="Fitters reported strong odor while breaking P-107 seal housing; area "
                   "monitor peaked 4 ppm. Work paused, line flushed again, completed safely. "
                   "Effluent service equipment retains H2S in dead legs.",
         root_cause="Insufficient line flushing before maintenance on effluent service.",
         precursors="effluent service equipment opening; incomplete flush",
         actions="Flush verification step added to effluent maintenance JSA.", permit=""),
    dict(id="NM-2021-11", date="2021-04-19", area="Area 2", equipment="V-205",
         category="near_miss_dropped_object",
         title="Scaffold clamp dropped near V-205",
         narrative="Clamp fell 6 m during scaffold erection, landing 2 m from a fitter.",
         root_cause="Tool lanyard not used.", precursors="work at height; loose tooling",
         actions="Tool tethering enforced.", permit="PTW-2021-0233"),
    dict(id="NM-2023-27", date="2023-11-08", area="Area 3", equipment="T-301",
         category="near_miss_procedural",
         title="Gauging performed during receipt into T-301",
         narrative="Operator opened gauge hatch while tank was receiving HSD, contrary to "
                   "SOP-TK-014 static precautions. Stopped by supervisor.",
         root_cause="Task pressure; SOP awareness gap.", precursors="tank receiving; manual gauging",
         actions="Toolbox talk; interlock signage at gauge platform.", permit=""),
    dict(id="NM-2024-19", date="2024-06-14", area="Area 1", equipment="CT-101",
         category="near_miss_slip",
         title="Slip at CT-101 basin walkway during monsoon cleaning",
         narrative="Contractor slipped on algae-slick walkway during basin cleaning; caught "
                   "handrail, no injury.",
         root_cause="Walkway anti-skid worn; monsoon algae growth.",
         precursors="monsoon; basin cleaning task", actions="Anti-skid strips replaced.",
         permit=""),
    dict(id="NM-2025-06", date="2025-02-27", area="Area 1", equipment="E-201",
         category="near_miss_lifting",
         title="Exchanger bundle swing during extraction",
         narrative="E-201 bundle swung against structure during pull; rigging plan had not "
                   "accounted for wind.",
         root_cause="Rigging plan gap.", precursors="heavy lift; wind above 20 km/h",
         actions="Wind limit added to lift plans.", permit="PTW-2025-0119"),
]


def incident_lines(inc: dict) -> list[str]:
    return [
        f"Incident / Near-Miss Report: {inc['id']}        Category: {inc['category']}",
        f"Date: {inc['date']}        Area: {inc['area']}        Equipment: {inc['equipment']}",
        f"Title: {inc['title']}",
        "",
        "NARRATIVE:",
        inc["narrative"],
        "",
        f"ROOT CAUSE: {inc['root_cause']}",
        f"PRECURSOR CONDITIONS: {inc['precursors']}",
        f"CORRECTIVE ACTIONS: {inc['actions']}",
        (f"Associated permit: {inc['permit']}" if inc["permit"] else ""),
        f"Reported to: {PEOPLE['mp']['name']} ({PEOPLE['mp']['role']})",
    ]


# ---------------------------------------------------------------- permits
def gen_permits() -> list[dict]:
    return [
        dict(id="PTW-2019-0288", ptype="Confined Space Entry", date="2019-08-24",
             equipment="TK-401", area="Area 4",
             text="Entry for desludging. Purge started 06:10, entry 08:25. Gas test 07:55: "
                  "O2 20.8%, H2S 2 ppm, LEL 0%. See NM-2019-07."),
        dict(id="PTW-2022-0871", ptype="Confined Space Entry", date="2022-09-13",
             equipment="TK-401", area="Area 4",
             text="Entry for sludge raking ahead of coating survey. Purge 05:40-08:30. "
                  "Gas test 08:35 passed. See NM-2022-31."),
        dict(id="PTW-2020-0104", ptype="Hot Work", date="2020-03-11",
             equipment="T-302", area="Area 3",
             text="Grinding at mixer flange platform. Gas test 06:50 (work started 10:05). "
                  "See INC-2020-03."),
        dict(id=f"PTW-{TOMORROW.year}-0902", ptype="Confined Space Entry",
             date=TOMORROW.isoformat(), equipment="TK-401", area="Area 4",
             text=f"SCHEDULED: Confined space entry into TK-401 equalization tank planned for "
                  f"{TOMORROW.isoformat()} 08:00 for internal coating inspection and sludge "
                  f"removal. Isolation per SOP-ET-005; P-107 LOTO. Eductor purge planned "
                  f"06:00-08:00 (2 h) to meet the inspection contractor window. Gas test "
                  f"scheduled 07:45. Authorized by: {PEOPLE['mp']['name']}."),
    ]


def permit_lines(p: dict) -> list[str]:
    return [
        f"Permit to Work: {p['id']}        Type: {p['ptype']}",
        f"Date: {p['date']}        Equipment: {p['equipment']}        Area: {p['area']}",
        "",
        p["text"],
        "",
        "Precautions per SOP-ET-005 / SOP-HW-001 as applicable.",
    ]


# ---------------------------------------------------------------- emails
EMAILS = [
    dict(id="EMAIL-2023-07-25-sharma", date="2023-07-25",
         frm="R. K. Sharma <rk.sharma@bharatpetrochem.example>",
         to="A. Deshpande; S. Venkatesan",
         subject="P-101 seal failures - it is the water, not the seals",
         body=["Team,", "",
               "Closing WO-2023-0771 I want this on record. We have now lost P-101 seals in "
               "Jul 2019, Aug 2021 and Jul 2023 - every one inside the monsoon window. The "
               "seal vendor is not the problem. The chain is: heavy rain washes silt into the "
               "CT-101 basin -> CW turbidity spikes -> STR-101 blinds within days -> on the "
               "next start the pump cavitates for a few seconds -> faces flash open, grit "
               "enters, seal dies weeks later.", "",
               "Ask me how I know: I saw the identical pattern at my previous refinery in the "
               "90s. The fix there was dP-triggered strainer cleaning and a hard rule on "
               "monsoon seal flush verification. I have proposed the same for SOP-CW-012.",
               "", "P-103 and P-107 run the same MS-40D cartridge. Watch them.",
               "", "R.K.S."]),
    dict(id="EMAIL-2023-07-26-deshpande", date="2023-07-26",
         frm="A. Deshpande <a.deshpande@bharatpetrochem.example>",
         to="R. K. Sharma", subject="RE: P-101 seal failures",
         body=["Noted. Raising the SOP revision request and adding STR-101 dP to the operator "
               "round sheet. Will include P-103/P-107 in the fleet review for the next "
               "reliability meeting."]),
    dict(id="EMAIL-2025-04-16-sharma", date="2025-04-16",
         frm="R. K. Sharma <rk.sharma@bharatpetrochem.example>",
         to="Unit 4 Operations", subject="SOP-CW-012 rev 3 issued - monsoon mode",
         body=["Rev 3 is effective today. The new step 3 (weekly monsoon seal-flush "
               "verification on P-101/P-102) exists because we paid for it four times over. "
               "Please make it stick after I retire in December.", "R.K.S."]),
    dict(id="EMAIL-2024-11-03-kaur", date="2024-11-03",
         frm="N. Kaur <n.kaur@bharatpetrochem.example>", to="J. Reddy",
         subject="PSV-1101 test deferral - flag for compliance register",
         body=["Jyoti,", "",
               "PSV-1101 (P-101 discharge relief) was bench tested 2022-04-12 and fell due "
               "within the OISD-STD-132 periodicity window this year. The removal was "
               "planned with the October shutdown, which slipped to 2026. As of today the "
               "valve is PAST its test due date and I do not see a revalidation or deferral "
               "approval on file. Please carry this on the compliance register until the "
               "test is done.", "", "PSV-3101 was done 2025-03-06 and is fine.", "N."]),
    dict(id="EMAIL-2026-05-20-reddy", date="2026-05-20",
         frm="J. Reddy <j.reddy@bharatpetrochem.example>", to="Plant Manager",
         subject="Area 3 audit-readiness gaps",
         body=["Ahead of the expected OISD external audit: two open items on Area 3.",
               "1. Fire/emergency drill for the tank farm - last record 2025-01-15; quarterly "
               "expectation for MAH units means we are several quarters behind.",
               "2. T-301 external inspection falls due 2026-11-20 (five-year OISD-129 "
               "interval from 2021-11-20) - need to plan access/scaffolding now.",
               "PSV-1101 test overdue remains open from N. Kaur's note of Nov 2024."]),
    dict(id="EMAIL-2021-02-09-rfi-mov", date="2021-02-09",
         frm="S. Venkatesan <s.venkatesan@bharatpetrochem.example>", to="Rotork service",
         subject="RFI: MOV-110 torque alarm on opening stroke",
         body=["MOV-110 (IQ3) intermittently alarms high torque at 20% open. Partial stroke "
               "tests otherwise normal. Please advise inspection points."]),
    dict(id="EMAIL-2021-02-12-rfi-reply", date="2021-02-12",
         frm="Rotork service <service@rotork.example>", to="S. Venkatesan",
         subject="RE: RFI: MOV-110 torque alarm",
         body=["Likely seat debris or stem lubrication. Recommend stem clean/re-grease and a "
               "full stroke at next opportunity; check disc for CW scale build-up - common on "
               "cooling water isolation duty."]),
    dict(id="EMAIL-2025-06-30-spares", date="2025-06-30",
         frm="A. Deshpande <a.deshpande@bharatpetrochem.example>", to="Stores",
         subject="Min-max review: MS-40D cartridge seals",
         body=["Given the recurring monsoon seal consumption on P-101/P-103/P-107, raise "
               "min stock of BurgFlow MS-40D cartridges from 1 to 3 between May and October."]),
]


def email_lines(e: dict) -> list[str]:
    return [f"From: {e['frm']}", f"To: {e['to']}", f"Date: {e['date']}",
            f"Subject: {e['subject']}", "", *e["body"]]


# ---------------------------------------------------------------- OEM manual pages (scanned look)
MANUALS = [
    dict(id="OEM-BURGFLOW-IOM-S7", title="BurgFlow MS-40D Installation, Operation & Maintenance - Section 7: Troubleshooting",
         seed=7, lines=[
             "SECTION 7 - TROUBLESHOOTING GUIDE (MS-40D / MS-32C SERIES)",
             "",
             "SYMPTOM 7.3: HIGH DISCHARGE TEMPERATURE / THERMAL TRIP",
             "Probable causes and checks, in order:",
             "  (a) Downstream cooler or exchanger fouled - verify exchanger approach",
             "      temperature against clean baseline; backflush if >5 degC above.",
             "  (b) Suction strainer differential pressure high - clean basket if dP",
             "      exceeds 0.4 bar; low suction pressure causes recirculation heating.",
             "  (c) Seal flush line (API Plan 11) blocked - confirm flow at rotameter;",
             "      inspect flush orifice for scale. A blocked flush line overheats the",
             "      seal chamber and will present as rising stuffing-box temperature.",
             "  (d) Minimum-flow operation - confirm flow instrument reading exceeds",
             "      the minimum continuous stable flow on the pump datasheet.",
             "",
             "SYMPTOM 7.5: PREMATURE MECHANICAL SEAL FAILURE",
             "  Abrasive solids in pumped liquid are the leading cause on cooling water",
             "  duty. Verify strainer condition and water turbidity FIRST. Face scoring",
             "  with thermal crazing indicates dry running after cavitation - inspect",
             "  suction line and strainer before blaming the seal.",
             "",
             "WARNING: Do not restart after a thermal trip until the cause of restricted",
             "cooling flow has been identified and corrected.",
         ]),
    dict(id="OEM-BURGFLOW-IOM-S4", title="BurgFlow MS-40D IOM - Section 4: Cartridge Seal Installation",
         seed=4, lines=[
             "SECTION 4 - MECHANICAL SEAL (CARTRIDGE) INSTALLATION",
             "4.1 Handle cartridge by the gland plate only. Do not compress the",
             "    setting clips before the sleeve collar is torqued.",
             "4.2 Torque gland bolts to 25 Nm in a star pattern.",
             "4.3 Connect API Plan 11 flush from discharge tapping through the",
             "    0.125 in orifice to the seal chamber port marked F.",
             "4.4 Remove setting clips AFTER final alignment. Rotate shaft by hand;",
             "    torque shall not exceed 12 Nm.",
             "4.5 On commissioning, vent the seal chamber until liquid emerges.",
             "    Dry running for more than 30 seconds voids warranty.",
         ]),
    dict(id="OEM-ROTORK-IQ3-S6", title="Rotork IQ3 Actuator Manual - Section 6: Torque Alarms",
         seed=6, lines=[
             "SECTION 6 - TORQUE MONITORING AND ALARMS",
             "6.2 Intermittent high-torque alarm during travel commonly indicates",
             "    seat/disc debris, stem lubrication breakdown, or scale build-up",
             "    on isolation valves in cooling water duty.",
             "6.3 Retrieve the torque-position log via the setting tool to identify",
             "    the position band of the excursion before intrusive work.",
         ]),
]

# ---------------------------------------------------------------- golden Q&A
GOLDEN_QA = [
    # verbatim demo beats
    dict(q="P-101 keeps tripping on high temperature - what feeds it, has this happened before, and what does the manual say to check?",
         category="multi_modal_fusion", modality=["graph", "text", "visual"],
         expect=["CT-101 feeds STR-101 which feeds P-101 (cooling water supply)",
                 "two high-temperature trips in monsoon 2025: WO-2025-4471 and WO-2025-4620",
                 "root cause was fouled E-201 cooler (plus STR-101 blinding)",
                 "OEM manual section 7.3: check cooler fouling, strainer dP, seal flush line"],
         citations=["D-CW-104", "WO-2025-4471", "WO-2025-4620", "OEM-BURGFLOW-IOM-S7"]),
    dict(q="Why does P-101 keep failing?",
         category="rca", modality=["graph", "text"],
         expect=["recurring mechanical seal failures concentrated in monsoon months (2019, 2021, 2023, 2024, 2025)",
                 "causal chain: monsoon rain -> CT-101 basin turbidity -> STR-101 blinding -> cavitation -> seal face damage",
                 "same pattern on sister pumps P-103 and P-107 (same MS-40D seal)",
                 "mitigation: SOP-CW-012 rev 3 monsoon seal-flush verification"],
         citations=["WO-2023-0771", "WO-2019-0712", "WO-2021-0843", "EMAIL-2023-07-25-sharma"]),
    dict(q="Prepare us for an OISD audit on the fuel storage area.",
         category="compliance", modality=["graph", "text"],
         expect=["fire/emergency drill record for Area 3 is stale (last 2025-01-15)",
                 "PSV-1101 test overdue per OISD-STD-132 periodicity (last tested 2022-04-12)",
                 "T-301 external inspection due 2026-11-20 (OISD-129 five-year interval)",
                 "PSV-3101 and fire water weekly tests are compliant evidence"],
         citations=["INSP-FIREDRILL-2025-01-15", "EMAIL-2024-11-03-kaur", "INSP-T301-2021-11-20"]),
    dict(q="What is the current procedure for P-101 / P-102 changeover and what changed in the latest revision?",
         category="temporal", modality=["text", "graph"],
         expect=["current is SOP-CW-012 rev 3 (effective 2025-04-15)",
                 "rev 3 added monsoon-mode weekly seal flush (Plan 11) verification",
                 "rev 2 (2021) had added the STR-101 dP check before start"],
         citations=["SOP-CW-012_rev3", "SOP-CW-012_rev2"]),
    dict(q="What feeds into pump P-101?",
         category="graph_lookup", modality=["graph"],
         expect=["STR-101 suction strainer immediately upstream", "CT-101 cooling tower upstream of the strainer"],
         citations=["D-CW-104"]),
    dict(q="Is there any risk with the confined space entry planned for TK-401 tomorrow?",
         category="proactive", modality=["graph", "text"],
         expect=["planned purge is only 2 hours; SOP-ET-005 requires minimum 4 hours",
                 "two prior near-misses NM-2019-07 and NM-2022-31 had the same precursor signature",
                 "sludge disturbance can re-release H2S even after a passing gas test"],
         citations=["NM-2019-07", "NM-2022-31", "SOP-ET-005"]),
    # factual lookups
    dict(q="What is the seal model used on P-101?", category="factual", modality=["text"],
         expect=["BurgFlow MS-40D cartridge seal"], citations=["WO-2019-0712"]),
    dict(q="When was PSV-1101 last bench tested and what was the result?",
         category="factual", modality=["text"],
         expect=["2022-04-12", "pass / recertified"], citations=["WO-2022-0410"]),
    dict(q="What is the trip setpoint context for TI-1103 on P-101?",
         category="factual", modality=["text"],
         expect=["trip at 65 degC; reached 68 degC in the July 2025 event"],
         citations=["WO-2025-4471"]),
    dict(q="Which drawing shows the cooling water system and what revision is current?",
         category="factual", modality=["visual", "text"],
         expect=["D-CW-104 rev 3"], citations=["D-CW-104"]),
    dict(q="Who authored the analysis connecting monsoon turbidity to seal failures?",
         category="factual", modality=["text"],
         expect=["R. K. Sharma, senior reliability engineer"],
         citations=["EMAIL-2023-07-25-sharma", "WO-2023-0771"]),
    dict(q="What are the gas test acceptance limits for TK-401 entry?",
         category="factual", modality=["text"],
         expect=["O2 19.5-23.5%", "H2S < 10 ppm", "LEL < 5%", "repeat every 30 minutes"],
         citations=["SOP-ET-005"]),
    dict(q="What does the Rotork manual suggest for MOV-110's intermittent torque alarm?",
         category="factual", modality=["visual", "text"],
         expect=["seat/disc debris, stem lubrication, CW scale build-up; retrieve torque-position log"],
         citations=["OEM-ROTORK-IQ3-S6", "EMAIL-2021-02-12-rfi-reply"]),
    dict(q="What is the minimum fire water header pressure target in the weekly test?",
         category="factual", modality=["text"],
         expect=[">= 8.5 kg/cm2 per OISD-STD-116 practice"], citations=["SOP-FW-002"]),
    # multi-hop / graph
    dict(q="What else shares the cooling water loop that feeds P-101?",
         category="multi_hop", modality=["graph"],
         expect=["P-102 standby on the same strainer", "E-201 and E-202 exchangers", "P-103 booster downstream"],
         citations=["D-CW-104"]),
    dict(q="Which equipment items use the BurgFlow MS-40D seal and which of them have failed?",
         category="multi_hop", modality=["graph", "text"],
         expect=["P-101, P-102, P-103, P-107 use it", "failures recorded on P-101, P-103, P-107"],
         citations=["WO-2025-0655", "WO-2024-0733", "WO-2023-0921"]),
    dict(q="If STR-101 blinds, which downstream equipment is at risk and why?",
         category="multi_hop", modality=["graph", "text"],
         expect=["P-101/P-102 cavitation and seal damage", "reduced CW flow raises P-101 discharge temperature via E-201"],
         citations=["D-CW-104", "WO-2025-4471"]),
    dict(q="Trace the path of cooling water from the tower to Area 2.",
         category="multi_hop", modality=["graph"],
         expect=["CT-101 -> STR-101 -> P-101 (or P-102) -> MOV-110 -> E-201 -> P-103 -> Area 2 header"],
         citations=["D-CW-104"]),
    dict(q="What consequential damage followed the 2023 P-101 seal failure?",
         category="multi_hop", modality=["text", "graph"],
         expect=["bearing distress / DE bearing replacement (INC-2023-08) after running with failed seal"],
         citations=["INC-2023-08", "WO-2023-0771"]),
    # RCA / patterns
    dict(q="Is the P-101 seal problem seasonal? Show the evidence.",
         category="rca", modality=["text", "graph"],
         expect=["all failures fall June-September", "STR-101 dP inspections high only in monsoon months"],
         citations=["INSP-STR101-2023-07-18", "WO-2021-0843"]),
    dict(q="Do P-103 or P-107 show the same failure pattern as P-101?",
         category="rca", modality=["graph", "text"],
         expect=["yes - P-103 failed Aug 2022 and Jul 2024; P-107 failed Sep 2023; same seal model and wet-season timing"],
         citations=["WO-2022-0808", "WO-2024-0733", "WO-2023-0921"]),
    dict(q="What has actually reduced the impact of P-101 seal failures?",
         category="rca", modality=["text"],
         expect=["SOP-CW-012 rev 3 weekly monsoon flush verification caught the 2025 failure early, halving downtime"],
         citations=["WO-2025-0655", "SOP-CW-012_rev3"]),
    dict(q="What recurring causes appear across TK-401 confined space near-misses?",
         category="rca", modality=["text"],
         expect=["purge shortened below 4 h in both events", "monsoon-season sludge load", "gas re-release on sludge disturbance"],
         citations=["NM-2019-07", "NM-2022-31"]),
    # compliance
    dict(q="Which relief valves are overdue for testing?",
         category="compliance", modality=["graph", "text"],
         expect=["PSV-1101 overdue (last test 2022-04-12, shutdown slip, flagged Nov 2024)", "PSV-3101 in date (2025-03-06)"],
         citations=["EMAIL-2024-11-03-kaur", "WO-2022-0410", "WO-2025-0301"]),
    dict(q="When is T-301 due for its next external inspection?",
         category="compliance", modality=["text", "graph"],
         expect=["plant records assume a five-year interval (next 2026-11-20 from the 2021-11-20 inspection)",
                 "but OISD-STD-129 clause 11.1 requires visual external inspection once a YEAR, so T-301 is already overdue and the plant's assumed interval conflicts with the standard"],
         citations=["INSP-T301-2021-11-20", "OISD-129-11.1"]),
    dict(q="Are fire drills for the tank farm up to date?",
         category="compliance", modality=["text"],
         expect=["no - last recorded drill 2025-01-15, several quarters stale for an MAH unit"],
         citations=["INSP-FIREDRILL-2025-01-15", "EMAIL-2026-05-20-reddy"]),
    # temporal / versioning
    dict(q="What did rev 2 of SOP-CW-012 add and why?",
         category="temporal", modality=["text"],
         expect=["STR-101 dP check before pump start, added after the 2021 seal failure WO-2021-0843"],
         citations=["SOP-CW-012_rev2"]),
    dict(q="Which procedure governs hot work and what changed after the 2020 T-302 fire?",
         category="temporal", modality=["text"],
         expect=["SOP-HW-001; rev 3 requires gas test immediately before work and revalidation"],
         citations=["SOP-HW-001", "INC-2020-03"]),
    # visual
    dict(q="Show me where PSV-1101 is on the cooling water drawing.",
         category="visual", modality=["visual", "graph"],
         expect=["relief branch off the P-101 discharge line on D-CW-104"],
         citations=["D-CW-104"]),
    dict(q="Which instrument measures P-101 discharge temperature and where is it?",
         category="visual", modality=["graph", "visual"],
         expect=["TI-1103, on the P-101 discharge run near MOV-110/E-201 on D-CW-104"],
         citations=["D-CW-104"]),
    dict(q="Find the OEM page about cartridge seal installation torque values.",
         category="visual", modality=["visual"],
         expect=["BurgFlow IOM section 4: gland bolts 25 Nm star pattern"],
         citations=["OEM-BURGFLOW-IOM-S4"]),
    # out-of-corpus honesty
    dict(q="What is the vibration alarm setpoint for compressor K-501?",
         category="insufficient_evidence", modality=["text"],
         expect=["no K-501 exists in the corpus - system should say it lacks evidence"],
         citations=[]),
    dict(q="What chemical is dosed at CT-101 and at what rate?",
         category="partial_evidence", modality=["text"],
         expect=["biocide and dispersant dosing mentioned; exact rate not in corpus - should say so"],
         citations=["SOP-CT-006"]),
]


# ---------------------------------------------------------------- main
def main():
    for sub in ("drawings", "work_orders", "inspections", "sops", "incidents",
                "email", "manuals", "permits", "regulatory"):
        (CORPUS / sub).mkdir(parents=True, exist_ok=True)

    build_cw_pid(CORPUS / "drawings")
    build_et_pid(CORPUS / "drawings")

    wos = HERO_WOS + gen_filler_wos()
    (CORPUS / "work_orders" / "work_orders.json").write_text(json.dumps(wos, indent=1))
    for wo in wos:
        write_text_pdf(CORPUS / "work_orders" / f"{wo['id']}.pdf",
                       f"WORK ORDER {wo['id']}", wo_lines(wo),
                       header="CMMS EXPORT - MAXIMO / UNIT 4")

    insps = gen_inspections()
    (CORPUS / "inspections" / "inspections.json").write_text(json.dumps(insps, indent=1))
    for i in insps:
        write_text_pdf(CORPUS / "inspections" / f"{i['id']}.pdf",
                       f"INSPECTION REPORT {i['id']}", insp_lines(i))

    for s in SOPS:
        stem = f"{s['id']}_rev{s['rev']}"
        write_text_pdf(CORPUS / "sops" / f"{stem}.pdf",
                       f"{s['id']} REV {s['rev']}: {s['title']}", sop_lines(s))
    (CORPUS / "sops" / "sops.json").write_text(json.dumps(SOPS, indent=1))

    for inc in INCIDENTS:
        write_text_pdf(CORPUS / "incidents" / f"{inc['id']}.pdf",
                       f"{inc['id']}: {inc['title']}", incident_lines(inc))
    (CORPUS / "incidents" / "incidents.json").write_text(json.dumps(INCIDENTS, indent=1))

    permits = gen_permits()
    for p in permits:
        write_text_pdf(CORPUS / "permits" / f"{p['id']}.pdf",
                       f"PERMIT TO WORK {p['id']}", permit_lines(p))
    (CORPUS / "permits" / "permits.json").write_text(json.dumps(permits, indent=1))

    for e in EMAILS:
        (CORPUS / "email" / f"{e['id']}.txt").write_text("\n".join(email_lines(e)))
    (CORPUS / "email" / "emails.json").write_text(json.dumps(EMAILS, indent=1))

    for m in MANUALS:
        write_scanned_pdf(CORPUS / "manuals" / f"{m['id']}.pdf", m["title"],
                          m["lines"], seed=m["seed"])
    (CORPUS / "manuals" / "manuals.json").write_text(
        json.dumps([{k: m[k] for k in ("id", "title")} for m in MANUALS], indent=1))

    (CORPUS / "equipment.json").write_text(json.dumps(EQUIPMENT, indent=1))
    (CORPUS / "people.json").write_text(json.dumps(PEOPLE, indent=1))
    (ROOT / "eval" / "golden_qa.json").write_text(json.dumps(GOLDEN_QA, indent=1))

    counts = {d.name: len(list((CORPUS / d.name).glob('*'))) for d in CORPUS.iterdir() if d.is_dir()}
    print("corpus generated:", counts)
    print("golden QA:", len(GOLDEN_QA))


if __name__ == "__main__":
    main()
