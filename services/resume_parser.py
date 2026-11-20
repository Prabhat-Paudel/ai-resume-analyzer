
import fitz


def extract_text_from_pdf(file_path):
    """
    Extract text from an uploaded PDF resume.
    """

    try:
        document = fitz.open(file_path)

        extracted_text = ""

        for page in document:
            extracted_text += page.get_text()

        document.close()

        return extracted_text.strip()

    except Exception as error:
        raise ValueError(
            f"Could not read the PDF file: {error}"
        )
