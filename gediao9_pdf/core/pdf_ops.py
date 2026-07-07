import os
from pathlib import Path

import fitz
import pdfplumber
from playwright.sync_api import sync_playwright

from .text_utils import detect_split_x, rebuild_text


def merge_first_pages(pdf_paths, out_path):
    merged = fitz.open()
    for p in pdf_paths:
        if not os.path.exists(p):
            continue
        doc = fitz.open(p)
        merged.insert_pdf(doc, from_page=0, to_page=0)
        doc.close()
    merged.save(out_path)
    merged.close()


def extract_column(pdf_path, page_no=0, side="right"):
    with pdfplumber.open(pdf_path) as pdf:
        if page_no >= len(pdf.pages):
            return ""
        words = pdf.pages[page_no].extract_words()
        if not words:
            return ""
        split_x = detect_split_x(words)
        if split_x is None:
            return "" if side == "left" else rebuild_text(words)
        if side == "right":
            filtered = [w for w in words if w["x0"] >= split_x]
        else:
            filtered = [w for w in words if w["x0"] < split_x]
        return rebuild_text(filtered) if filtered else ""


def extract_all_text(pdf_path, page_no=0):
    with pdfplumber.open(pdf_path) as pdf:
        if page_no >= len(pdf.pages):
            return ""
        words = pdf.pages[page_no].extract_words()
        return rebuild_text(words) if words else ""


def render_pdf(html_path, pdf_path):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(f"file://{Path(html_path).resolve()}", wait_until="networkidle")
        page.pdf(path=pdf_path, format="A4", print_background=True)
        browser.close()


def get_page_count(pdf_path):
    doc = fitz.open(pdf_path)
    count = doc.page_count
    doc.close()
    return count


def has_bio_overflow(pdf_path):
    doc = fitz.open(pdf_path)
    if doc.page_count < 2:
        doc.close()
        return False, ""

    words1 = doc[0].get_text("words")
    if not words1:
        doc.close()
        return False, ""

    split_x = detect_split_x(words1)
    if split_x is None:
        doc.close()
        return False, ""

    words2 = doc[1].get_text("words")
    doc.close()
    if not words2:
        return False, ""

    left_words = [w for w in words2 if w[0] < split_x]
    if not left_words:
        return False, ""

    lines = {}
    for w in left_words:
        row = round(w[1] / 10) * 10
        lines.setdefault(row, []).append(w)
    text = ""
    for row in sorted(lines):
        text += "".join(w[4] for w in sorted(lines[row], key=lambda w: w[0]))
    return True, text