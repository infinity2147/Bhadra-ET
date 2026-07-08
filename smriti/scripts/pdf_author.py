"""Author real PDF documents for the synthetic corpus using pymupdf.

Two styles:
- clean text PDFs (work orders, SOPs, inspections, incidents, permits, emails)
- "scanned-look" pages (OEM manual extracts): light gray background, slight
  skew and noise so OCR-hostile visual retrieval has something honest to shine on.
"""
from __future__ import annotations

import random

import fitz  # pymupdf

PAGE_W, PAGE_H = 595, 842  # A4 points
MARGIN = 50
LINE_H = 14
BODY_SIZE = 9.5
TITLE_SIZE = 14


def write_text_pdf(path, title: str, lines: list[str], header: str = "",
                   footer: str = "Bharat Petrochem Ltd. — Refinery Unit 4 — INTERNAL"):
    doc = fitz.open()
    page = doc.new_page(width=PAGE_W, height=PAGE_H)
    y = MARGIN

    def new_page():
        nonlocal page, y
        page = doc.new_page(width=PAGE_W, height=PAGE_H)
        y = MARGIN

    if header:
        page.insert_text((MARGIN, y), header, fontsize=8, color=(0.4, 0.4, 0.4))
        y += LINE_H
    page.insert_text((MARGIN, y + 6), title, fontsize=TITLE_SIZE, fontname="helv",
                     color=(0, 0, 0))
    y += 2 * LINE_H + 6
    for line in lines:
        # naive wrap at ~95 chars
        while len(line) > 95:
            cut = line.rfind(" ", 0, 95)
            cut = cut if cut > 40 else 95
            seg, line = line[:cut], line[cut:].lstrip()
            if y > PAGE_H - MARGIN - LINE_H:
                new_page()
            page.insert_text((MARGIN, y), seg, fontsize=BODY_SIZE, fontname="helv")
            y += LINE_H
        if y > PAGE_H - MARGIN - LINE_H:
            new_page()
        page.insert_text((MARGIN, y), line, fontsize=BODY_SIZE, fontname="helv")
        y += LINE_H
    for p in doc:
        p.insert_text((MARGIN, PAGE_H - 25), footer, fontsize=7,
                      color=(0.5, 0.5, 0.5))
    doc.save(str(path))
    doc.close()


def write_scanned_pdf(path, title: str, lines: list[str], seed: int = 0):
    """Scanned-look page: gray tint, skewed text, speckle noise, stamp box."""
    rng = random.Random(seed)
    doc = fitz.open()
    page = doc.new_page(width=PAGE_W, height=PAGE_H)
    # aged-paper background
    page.draw_rect(fitz.Rect(0, 0, PAGE_W, PAGE_H), color=None,
                   fill=(0.93, 0.92, 0.88))
    # speckle noise
    for _ in range(350):
        x, y = rng.uniform(0, PAGE_W), rng.uniform(0, PAGE_H)
        g = rng.uniform(0.55, 0.8)
        page.draw_circle((x, y), rng.uniform(0.2, 0.7), color=(g, g, g),
                         fill=(g, g, g))
    skew = rng.uniform(-1.2, 1.2)  # degrees
    morph = fitz.Matrix(1, 1).prerotate(skew)
    y = MARGIN + 10
    page.insert_text((MARGIN, y), title, fontsize=12.5, fontname="cobo",
                     color=(0.15, 0.15, 0.18), morph=(fitz.Point(MARGIN, y), morph))
    y += 26
    for line in lines:
        while len(line) > 92:
            cut = line.rfind(" ", 0, 92)
            cut = cut if cut > 40 else 92
            seg, line = line[:cut], line[cut:].lstrip()
            page.insert_text((MARGIN, y), seg, fontsize=9, fontname="cour",
                             color=(0.18, 0.18, 0.2),
                             morph=(fitz.Point(MARGIN, y), morph))
            y += 13
        page.insert_text((MARGIN, y), line, fontsize=9, fontname="cour",
                         color=(0.18, 0.18, 0.2),
                         morph=(fitz.Point(MARGIN, y), morph))
        y += 13
    # "RECEIVED" style stamp
    stamp = fitz.Rect(PAGE_W - 190, 60, PAGE_W - 55, 105)
    page.draw_rect(stamp, color=(0.55, 0.15, 0.15), width=1.4)
    page.insert_text((stamp.x0 + 8, stamp.y0 + 18), "DOC CONTROL", fontsize=9,
                     color=(0.55, 0.15, 0.15), fontname="cobo")
    page.insert_text((stamp.x0 + 8, stamp.y0 + 33), "UNIT-4 LIBRARY", fontsize=8,
                     color=(0.55, 0.15, 0.15), fontname="cobo")
    doc.save(str(path))
    doc.close()
