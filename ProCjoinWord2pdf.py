#!/usr/bin/python3
import os
import argparse
import subprocess
from pypdf import PdfReader, PdfWriter

def convert_docx_to_pdf(input_dir):
    docx_files = sorted(
        f for f in os.listdir(input_dir) if f.lower().endswith(".docx")
    )

    generated_pdfs = []
    for docx_file in docx_files:
        input_file_path = os.path.join(input_dir, docx_file)
        output_pdf_path = os.path.splitext(input_file_path)[0] + ".pdf"
        generated_pdfs.append(output_pdf_path)

        subprocess.run(
            [
                "libreoffice",
                "--headless",
                "--convert-to",
                "pdf",
                "--outdir",
                input_dir,
                input_file_path,
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        if not os.path.exists(output_pdf_path):
            raise FileNotFoundError(
                f"PDF was not generated: {output_pdf_path}"
            )

    return generated_pdfs

def merge_pdfs(pdf_paths, output_file_path):
    writer = PdfWriter()

    for pdf_path in pdf_paths:
        reader = PdfReader(pdf_path)
        writer.append_pages_from_reader(reader)

    outdir = os.path.dirname(os.path.abspath(output_file_path))
    if outdir:
        os.makedirs(outdir, exist_ok=True)

    with open(output_file_path, "wb") as f:
        writer.write(f)

def main():
    parser = argparse.ArgumentParser(
        description="Convert .docx files to PDF and merge them"
    )
    parser.add_argument("input_directory")
    parser.add_argument("output_pdf_path")
    args = parser.parse_args()

    input_dir = os.path.abspath(args.input_directory)
    output_pdf = os.path.abspath(args.output_pdf_path)

    if not os.path.isdir(input_dir):
        raise NotADirectoryError(input_dir)

    pdfs = convert_docx_to_pdf(input_dir)
    merge_pdfs(pdfs, output_pdf)

if __name__ == "__main__":
    main()

