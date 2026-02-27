import spacy
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Load spacy model once at module level (Streamlit-safe singleton pattern)
# The model is loaded only once and reused across all function calls
_nlp = None


def _load_spacy_model():
    """Lazy load spaCy model with error handling.
    
    Returns:
        spacy language model or None if loading fails
    """
    global _nlp
    
    if _nlp is not None:
        return _nlp
    
    try:
        _nlp = spacy.load("en_core_web_sm")
        logger.info("spaCy model 'en_core_web_sm' loaded successfully")
        return _nlp
    except OSError:
        logger.warning(
            "spaCy model 'en_core_web_sm' not found. "
            "Install with: python -m spacy download en_core_web_sm"
        )
        return None


def extract_vendor_spacy(ocr_text: str) -> Optional[str]:
    """Extract vendor name using spaCy ORG entity detection.
    
    This is a named entity recognition (NER) based approach that identifies
    organization names from OCR text. Used as a fallback when Gemini extraction
    or regex-based extraction fails.
    
    Args:
        ocr_text: Raw text extracted from receipt/invoice via OCR
    
    Returns:
        Best matching vendor name or None if no ORG entities found
    
    Process:
        1. Validate input text (minimum length check)
        2. Load spaCy model if not already loaded
        3. Process text with NER pipeline
        4. Extract all ORG entities
        5. Filter by minimum length and prefer shorter names
    """
    # Input validation
    if not ocr_text or len(ocr_text.strip()) < 10:
        return None
    
    # Load model with lazy initialization
    nlp = _load_spacy_model()
    if nlp is None:
        logger.debug("spaCy fallback skipped: model not available")
        return None
    
    try:
        # Process text through spaCy NER pipeline
        doc = nlp(ocr_text)
        
        # Extract all ORG entities and filter by quality
        orgs = [
            ent.text.strip()
            for ent in doc.ents
            if ent.label_ == "ORG" and len(ent.text.strip()) > 2
        ]
        
        if not orgs:
            logger.debug("No ORG entities found in OCR text")
            return None
        
        # Sort by length: prefer shorter, cleaner organization names
        # (longer names often contain addresses or extra details)
        orgs.sort(key=len)
        vendor_name = orgs[0]
        logger.debug(f"spaCy extracted vendor: {vendor_name}")
        return vendor_name
        
    except Exception as e:
        logger.error(f"Error during spaCy vendor extraction: {e}")
        return None
