#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import csv
import os
import sys
import tempfile
import shutil
from pypdf import PdfReader, PdfWriter

def read_csv_cp932(path):
    rows = []
    with open(path, "r", encoding="cp932", newline="") as f:
        r = csv.reader(f)
        for row in r:
            if len(row) < 4:
                continue
            pdfname = row[2].strip()
            pages_s = row[3].strip()
            if not pdfname.lower().endswith(".pdf"):
                continue
            try:
                pages = int(pages_s)
            except ValueError:
                print(f"[WARN] Column 4 is not an integer. Skipped: {row}", file=sys.stderr)
                continue
            rows.append((pdfname, pages))
    return rows

def main():
    ap = argparse.ArgumentParser(
        description="Prepend N pages from a header PDF to each target PDF (overwrite in place)."
    )
    ap.add_argument("csv_file", help="CSV (col3: target PDF, col4: number of header pages to prepend)")
    ap.add_argument("header_pdf", help="Header PDF")
    ap.add_argument("--dry-run", action="store_true", help="Show plan without modifying files")
    args = ap.parse_args()

    if not os.path.isfile(args.header_pdf):
        print(f"[ERROR] Header PDF not found: {args.header_pdf}", file=sys.stderr)
        sys.exit(1)

    rows = read_csv_cp932(args.csv_file)
    if not rows:
        print("[INFO] No valid rows found. Nothing to do.")
        return

    # Load header once
    try:
        header_reader = PdfReader(args.header_pdf, strict=False)
    except Exception as e:
        print(f"[ERROR] Failed to read header PDF: {e}", file=sys.stderr)
        sys.exit(1)

    header_total = len(header_reader.pages)

    # Build plan: consume header pages sequentially
    plan = []
    cursor = 0  # zero-based index
    needed = 0
    for fn, n in rows:
        n = max(0, n)
        needed += n
        if n == 0:
            plan.append((fn, None))
        else:
            start = cursor
            end = cursor + n  # exclusive
            plan.append((fn, (start, end)))
            cursor = end

    if needed > header_total:
        print(f"[ERROR] Not enough header pages. Needed {needed}, available {header_total}", file=sys.stderr)
        sys.exit(1)

    if args.dry_run:
        hname = os.path.basename(args.header_pdf)
        print(f"[DRY-RUN] Using {hname}. Plan is as follows (no files modified):")
        for fn, seg in plan:
            if seg is None:
                print(f"  {fn}: no header pages added")
            else:
                a, b = seg
                print(f"  {fn}: prepend {hname} pages {a+1}-{b} → overwrite")
        return

    # Process each file
    with tempfile.TemporaryDirectory() as td:
        for fn, seg in plan:
            if not os.path.isfile(fn):
                print(f"[WARN] Target PDF not found. Skipped: {fn}", file=sys.stderr)
                continue

            try:
                target_reader = PdfReader(fn, strict=False)
            except Exception as e:
                print(f"[ERROR] Failed to read target PDF {fn}: {e}", file=sys.stderr)
                sys.exit(1)

            writer = PdfWriter()
            # prepend header pages (if any)
            if seg is not None:
                a, b = seg
                for i in range(a, b):
                    writer.add_page(header_reader.pages[i])
            else:
                print(f"[INFO] No pages added: {fn}")

            # append target pages
            for p in target_reader.pages:
                writer.add_page(p)

            # write to temp then overwrite atomically
            out_path = os.path.join(td, "merged.pdf")
            with open(out_path, "wb") as outf:
                writer.write(outf)

            try:
                shutil.copy2(out_path, fn)
            except Exception as e:
                print(f"[ERROR] Failed to overwrite {fn}: {e}", file=sys.stderr)
                sys.exit(1)

            if seg is None:
                print(f"[OK] {fn}: kept original (no header pages).")
            else:
                print(f"[OK] {fn}: prepended pages {seg[0]+1}-{seg[1]} from {os.path.basename(args.header_pdf)}.")

if __name__ == "__main__":
    main()

