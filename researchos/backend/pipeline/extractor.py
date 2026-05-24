import fitz  # PyMuPDF


MAX_CHARS = 12000


def extract_pdf_text(pdf_bytes: bytes) -> str:
    """
    Extract plain text from a PDF file using PyMuPDF.

    Opens the PDF from bytes, concatenates text from all pages, and caps the
    result at MAX_CHARS to stay within Claude context window limits. Returns a
    warning string if the PDF appears to be scanned/image-based (no extractable text).
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    full_text = ""
    for page in doc:
        full_text += page.get_text()

    if len(full_text.strip()) < 100:
        return (
            "[SCANNED PDF WARNING] This PDF appears to be scanned or image-based. "
            "Text extraction was not possible. Please upload a text-based PDF exported "
            "directly from your IRB submission system (e.g. Kuali Research)."
        )

    return full_text[:MAX_CHARS]
