import pdfplumber
import sys

pdf_path = r'D:\shankha\documents\files\EMRI_Complete_Analytical_Pipeline.pdf'
output_file = r'D:\shankha\github\emri-capstone\pdf_model_extracted.txt'

with pdfplumber.open(pdf_path) as pdf:
    total_pages = len(pdf.pages)
    print(f"Total pages: {total_pages}\n")

    with open(output_file, 'w', encoding='utf-8') as out:
        out.write(f"PDF: wdi_eda_professional.pdf\n")
        out.write(f"Total pages: {total_pages}\n\n")

        # Extract all pages
        for i, page in enumerate(pdf.pages):
            out.write(f"\n{'='*60}\n")
            out.write(f"PAGE {i+1}\n")
            out.write('='*60 + '\n')
            text = page.extract_text()
            if text:
                out.write(text + '\n')
            else:
                out.write("[No text extracted from this page]\n")

print(f"Extraction complete. Output saved to: {output_file}")
