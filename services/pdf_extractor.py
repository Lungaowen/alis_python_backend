import gc
import logging
import pdfplumber
from pdfminer.high_level import extract_text as pdfminer_extract_text
from utils.text_cleaner import clean_text

logger = logging.getLogger(__name__)

def extract_text_generator(file_path: str):
    """Yields cleaned text page by page to keep memory usage low."""
    success = False
    
    try:
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    yield clean_text(text)
                
                # Critical for memory constraints
                page.flush_cache()
                if hasattr(page, "close"):
                    page.close()
                del text
                gc.collect()
        success = True
    except Exception:
        logger.exception("pdfplumber extraction failed; falling back to pdfminer")

    if not success:
        # Fallback to pdfminer.six, processed via page numbers to save memory
        try:
            # We approximate page extraction iteratively if pdfplumber fails
            # Extracting 5 pages at a time to honor memory limits
            chunk_size = 5
            page_num = 0
            while True:
                pages_to_extract = list(range(page_num, page_num + chunk_size))
                text = pdfminer_extract_text(file_path, page_numbers=pages_to_extract)
                if not text.strip():
                    break
                yield clean_text(text)
                
                del text
                gc.collect()
                page_num += chunk_size
        except Exception as e:
            raise RuntimeError(f"Text extraction failed on both engines: {str(e)}")
