#!/usr/bin/python3 

#!/usr/bin/env python3
"""
Merge all PDF files in a directory into a single PDF.
Each page is annotated with its source filename at the top-right corner.
"""

import os
import argparse
from io import BytesIO

from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas


def create_overlay(text, page_width, page_height):
    """
    Create a single-page PDF overlay that draws text
    at the top-right corner of the page.

    Parameters
    ----------
    text : str
        Text to be drawn (e.g., filename).
    page_width : float
        Width of the target PDF page.
    page_height : float
        Height of the target PDF page.

    Returns
    -------
    pypdf.PageObject
        A PDF page containing the overlay text.
    """
    packet = BytesIO()
    c = canvas.Canvas(packet, pagesize=(page_width, page_height))

    font_size = 10
    margin = 20

    x = page_width - margin
    y = page_height - margin

    c.setFont("Helvetica", font_size)
    c.drawRightString(x, y, text)
    c.save()

    packet.seek(0)
    return PdfReader(packet).pages[0]


def merge_pdfs(input_dir, output_pdf):
    """
    Merge all PDF files in a directory into one PDF.
    Each page is stamped with the source filename.

    Parameters
    ----------
    input_dir : str
        Directory containing PDF files.
    output_pdf : str
        Path to the output merged PDF.
    """
    writer = PdfWriter()

    for filename in sorted(os.listdir(input_dir)):
        if not filename.lower().endswith(".pdf"):
            continue

        filepath = os.path.join(input_dir, filename)
        reader = PdfReader(filepath)

        for page in reader.pages:
            width = float(page.mediabox.width)
            height = float(page.mediabox.height)

            overlay = create_overlay(filename, width, height)
            page.merge_page(overlay)

            writer.add_page(page)

    with open(output_pdf, "wb") as f:
        writer.write(f)


def main():
    """
    Parse command-line arguments and run the PDF merge process.
    """
    parser = argparse.ArgumentParser(
        description=(
            "Merge all PDF files in a directory into a single PDF. "
            "Each page will be annotated with its source filename "
            "at the top-right corner."
        )
    )

    parser.add_argument(
        "input_dir",
        help="Directory containing PDF files to be merged"
    )

    parser.add_argument(
        "output_pdf",
        help="Output PDF file path"
    )

    args = parser.parse_args()

    merge_pdfs(args.input_dir, args.output_pdf)


if __name__ == "__main__":
    main()

