import io


def extract_text_from_pdf(uploaded_file) -> str:
    """Extract text from an uploaded PDF file."""
    import pdfplumber

    text_parts = []
    with pdfplumber.open(io.BytesIO(uploaded_file.read())) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
    return "\n\n".join(text_parts)


def extract_text_from_docx(uploaded_file) -> str:
    """Extract text from an uploaded DOCX file."""
    from docx import Document

    doc = Document(io.BytesIO(uploaded_file.read()))
    text_parts = [para.text for para in doc.paragraphs if para.text.strip()]
    return "\n\n".join(text_parts)
