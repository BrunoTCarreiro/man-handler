"""Language detection and section selection for multilingual PDFs."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List, Tuple

import fitz  # PyMuPDF
from langdetect import detect, LangDetectException

logger = logging.getLogger("backend.language_detection")


# Language ranking for translation ease (lower = easier to translate to English)
TRANSLATION_EASE_RANKING = {
    "en": 0,    # English - no translation needed
    "nl": 1,    # Dutch - Germanic language, close to English
    "de": 2,    # German - Germanic language
    "da": 3,    # Danish - Germanic language
    "sv": 4,    # Swedish - Germanic language
    "no": 5,    # Norwegian - Germanic language
    "fr": 6,    # French - Romance language, many shared words
    "es": 7,    # Spanish - Romance language
    "pt": 8,    # Portuguese - Romance language
    "it": 9,    # Italian - Romance language
    "ro": 10,   # Romanian - Romance language
    "pl": 11,   # Polish - Slavic language
    "cs": 12,   # Czech - Slavic language
    "ru": 13,   # Russian - Slavic, Cyrillic script
    "tr": 14,   # Turkish - Different grammar structure
    "ar": 15,   # Arabic - Right-to-left, different script
    "zh": 16,   # Chinese - Ideographic, very different
    "ja": 17,   # Japanese - Mixed scripts, very different
    "ko": 18,   # Korean - Different script and grammar
}


def detect_page_language(pdf_path: Path | str, page_num: int) -> str | None:
    """Detect the language of a specific page using text extraction.
    
    Args:
        pdf_path: Path to the PDF file
        page_num: Page number (0-indexed)
        
    Returns:
        ISO language code (e.g., 'en', 'es', 'fr') or None if detection fails
    """
    try:
        doc = fitz.open(str(pdf_path))
        
        if page_num >= len(doc):
            doc.close()
            return None
        
        page = doc[page_num]
        text = page.get_text()
        doc.close()
        
        # Need at least some text to detect language
        if not text or len(text.strip()) < 20:
            return None
        
        # Detect language
        lang = detect(text)
        return lang
        
    except (LangDetectException, Exception) as e:
        logger.warning("Language detection failed for page %d: %s", page_num + 1, e)
        return None


def scan_pdf_languages(pdf_path: Path | str, sample_interval: int = 3) -> Dict[int, str]:
    """Scan a PDF and detect languages for sampled pages.
    
    Args:
        pdf_path: Path to the PDF file
        sample_interval: Check every Nth page (default: 3)
        
    Returns:
        Dictionary mapping page numbers to language codes
    """
    logger.info("Scanning PDF for language sections...")
    
    try:
        doc = fitz.open(str(pdf_path))
        page_count = len(doc)
        doc.close()
    except Exception as e:
        logger.error("Failed to open PDF: %s", e)
        return {}
    
    languages: Dict[int, str] = {}
    
    # Always check first 5 pages individually (page 0 onwards)
    # Language sections often start at the beginning
    first_pages_to_check = min(5, page_count)
    for page_num in range(first_pages_to_check):
        lang = detect_page_language(pdf_path, page_num)
        if lang:
            languages[page_num] = lang
            logger.debug("Page %d: %s", page_num + 1, lang)
    
    # Then sample remaining pages at intervals
    for page_num in range(first_pages_to_check, page_count, sample_interval):
        lang = detect_page_language(pdf_path, page_num)
        if lang:
            languages[page_num] = lang
            logger.debug("Page %d: %s", page_num + 1, lang)
    
    return languages


def group_consecutive_pages(languages: Dict[int, str], total_pages: int) -> List[Dict]:
    """Group pages into language sections.
    
    Args:
        languages: Dictionary mapping page numbers to language codes
        total_pages: Total number of pages in the PDF
        
    Returns:
        List of sections with start_page, end_page, language, page_count
    """
    if not languages:
        return []
    
    # Sort pages
    sorted_pages = sorted(languages.keys())
    
    sections = []
    current_lang = None
    current_start = None
    
    for i, page_num in enumerate(sorted_pages):
        lang = languages[page_num]
        
        if current_lang != lang:
            # Save previous section
            if current_lang is not None and current_start is not None:
                # Estimate end of section
                end_page = sorted_pages[i] - 1 if i < len(sorted_pages) else total_pages - 1
                sections.append({
                    "language": current_lang,
                    "start_page": current_start,
                    "end_page": end_page,
                    "page_count": end_page - current_start + 1,
                })
            
            # Start new section
            current_lang = lang
            current_start = page_num
    
    # Add final section
    if current_lang is not None and current_start is not None:
        sections.append({
            "language": current_lang,
            "start_page": current_start,
            "end_page": total_pages - 1,
            "page_count": total_pages - current_start,
        })
    
    return sections


def select_best_language_section(sections: List[Dict]) -> Dict | None:
    """Select the best language section to extract.
    
    Strategy:
    1. Find longest contiguous English section (preferred)
    2. If no English, find longest section of easiest-to-translate language
    
    Args:
        sections: List of language sections
        
    Returns:
        Best section to extract, or None if no sections
    """
    if not sections:
        return None
    
    # First priority: Find longest English section
    english_sections = [s for s in sections if s["language"] == "en"]
    
    if english_sections:
        # Select longest English section
        best_section = max(english_sections, key=lambda s: s["page_count"])
        logger.info("Found %d English section(s)", len(english_sections))
        logger.info("Selected longest English section: pages %d-%d (%d pages)",
                    best_section['start_page'] + 1, best_section['end_page'] + 1,
                    best_section['page_count'])
        return best_section
    
    # No English found - fall back to easiest language to translate
    logger.warning("No English sections found")
    logger.info("Selecting section with easiest translation...")
    
    def score_section(section: Dict) -> Tuple[int, int]:
        lang = section["language"]
        ease_rank = TRANSLATION_EASE_RANKING.get(lang, 999)  # Unknown languages get high penalty
        page_count = section["page_count"]
        
        # Primary sort: translation ease (lower is better)
        # Secondary sort: page count (more pages is better)
        return (ease_rank, -page_count)
    
    best_section = min(sections, key=score_section)
    lang_name = get_language_name(best_section["language"])
    
    logger.info("Selected %s section: pages %d-%d (%d pages)",
                lang_name, best_section['start_page'] + 1, best_section['end_page'] + 1,
                best_section['page_count'])
    logger.info("This section will be translated to English")
    
    return best_section


def detect_and_select_language_section(
    pdf_path: Path | str,
    sample_interval: int = 3
) -> Tuple[str, int, int] | None:
    """Detect language sections and select the best one to extract.
    
    Args:
        pdf_path: Path to the PDF file
        sample_interval: Check every Nth page for language detection
        
    Returns:
        Tuple of (language_code, start_page, end_page) or None if detection fails
    """
    try:
        doc = fitz.open(str(pdf_path))
        total_pages = len(doc)
        doc.close()
    except Exception as e:
        logger.error("Failed to open PDF: %s", e)
        return None
    
    # Scan for languages
    languages = scan_pdf_languages(pdf_path, sample_interval)
    
    if not languages:
        logger.warning("No languages detected, will process all pages")
        return None
    
    # Group into sections
    sections = group_consecutive_pages(languages, total_pages)
    
    if not sections:
        logger.warning("No language sections found, will process all pages")
        return None
    
    # Debug: Show all detected sections
    logger.info("Detected %d section(s):", len(sections))
    for sec in sections:
        lang_name = get_language_name(sec["language"])
        logger.info("  - %s: pages %d-%d (%d pages)",
                    lang_name, sec['start_page'] + 1, sec['end_page'] + 1, sec['page_count'])
    
    # Select best section
    best_section = select_best_language_section(sections)
    
    if not best_section:
        return None
    
    return (
        best_section["language"],
        best_section["start_page"],
        best_section["end_page"]
    )


def get_language_name(lang_code: str) -> str:
    """Get human-readable language name from ISO code."""
    language_names = {
        "en": "English",
        "es": "Spanish",
        "fr": "French",
        "de": "German",
        "it": "Italian",
        "pt": "Portuguese",
        "nl": "Dutch",
        "ru": "Russian",
        "zh": "Chinese",
        "ja": "Japanese",
        "ko": "Korean",
        "ar": "Arabic",
        "tr": "Turkish",
        "pl": "Polish",
        "cs": "Czech",
        "da": "Danish",
        "sv": "Swedish",
        "no": "Norwegian",
        "ro": "Romanian",
    }
    return language_names.get(lang_code, lang_code.upper())

