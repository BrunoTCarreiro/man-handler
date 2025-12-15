"""
Translation module for converting manual text to English.

Uses local LLM via Ollama for privacy-first translation.
"""

from __future__ import annotations

import logging
import re

import ollama

from . import settings

logger = logging.getLogger("backend.translation")


def _strip_llm_preamble_and_fences(text: str) -> str:
    """Remove common LLM preambles and surrounding markdown fences.

    The translator sometimes returns helpers like:
      "Here is the English translation of your text..."
      ```markdown
      ...
      ```

    This function keeps only the inner markdown content.
    """
    cleaned = text

    # Remove common English-translation preambles wherever they appear as full lines.
    # These are clearly LLM artifacts and extremely unlikely to be part of the manual.
    preamble_patterns = [
        r"(?im)^\s*here is the english translation of your text, preserving markdown formatting:.*$",
        r"(?im)^\s*here is the english translation of your text:.*$",
        r"(?im)^\s*here is the translated text in english:.*$",
        r"(?im)^\s*here is the translated text with preserved markdown formatting:.*$",
        r"(?im)^\s*here is the english translation:.*$",
        r"(?im)^\s*english translation:.*$",
        r"(?im)^\s*the translated markdown is as follows:.*$",
        r"(?im)^\s*the translated markdown is:.*$",
        # Table explanations
        r"(?im)^\s*this text is a table with two rows.*$",
        r"(?im)^\s*this table contains information about.*$",
        r"(?im)^\s*each row corresponds to a specific dish.*$",
        r"(?im)^\s*the instructions are provided in both english and spanish.*$",
    ]
    for pattern in preamble_patterns:
        cleaned = re.sub(pattern, "", cleaned)

    # Normalise leading whitespace after removing whole-line preambles
    cleaned = cleaned.lstrip()

    # If the whole response is wrapped in a single pair of ``` fences, keep the inside
    stripped = cleaned.lstrip()
    if stripped.startswith("```"):
        # Drop the first fence line (e.g. ``` or ```markdown)
        first_newline = stripped.find("\n")
        if first_newline != -1:
            inner = stripped[first_newline + 1 :]
        else:
            inner = ""

        # Drop trailing closing fence if present
        inner_stripped = inner.rstrip()
        if inner_stripped.endswith("```"):
            inner = inner_stripped[:-3]

        cleaned = inner.strip("\n")

    # At this point, any remaining ``` fences inside the text are almost
    # certainly artifacts from the translator rather than real manual content.
    # Strip any standalone fence lines like ``` or ```markdown or ```makrdown.
    cleaned = re.sub(r"^```[a-zA-Z]*\s*$", "", cleaned, flags=re.MULTILINE)

    return cleaned


def _looks_non_english(text: str) -> bool:
    """Language-agnostic heuristic to flag likely non-English paragraphs."""
    if not text or not text.strip():
        return False

    # If there are several non-ascii letters, assume non-English.
    non_ascii_letters = sum(1 for ch in text if ord(ch) > 127 and ch.isalpha())
    if non_ascii_letters >= 2:
        return True

    # If very few English stopwords appear, and length is reasonable, flag it.
    stopwords = [" the ", " and ", " to ", " of ", " in ", " for ", " with ", " on "]
    lower = text.lower()
    sw_hits = sum(1 for w in stopwords if w in lower)
    if len(text) > 120 and sw_hits <= 1:
        return True

    return False


def translate_text(
    text: str,
    target_lang: str = "English",
    source_lang: str | None = None,
    model: str | None = None,
) -> str:
    """Translate text to target language using local LLM.

    Args:
        text: Text to translate
        target_lang: Target language (default: "English")
        source_lang: Source language (optional, LLM will detect if not specified)
        model: Ollama model to use (default: from settings.TRANSLATION_MODEL_NAME)

    Returns:
        Translated text with markdown formatting preserved
    """
    if not text or not text.strip():
        return text

    model = model or settings.TRANSLATION_MODEL_NAME

    # Build concise but explicit prompt.
    # Emphasize that ALL content (including tables) must be translated and no explanation returned.
    if source_lang:
        lang_instruction = (
            f"Translate this text from {source_lang} to {target_lang}. "
            "Translate ALL content, including table headers, table cells, and labels. "
            "Do not leave any words or phrases in the original language. "
            "Preserve markdown formatting. Respond with ONLY the translated markdown, "
            "with no explanations or commentary."
        )
    else:
        lang_instruction = (
            f"Translate this text to {target_lang}. "
            "Translate ALL content, including table headers, table cells, and labels. "
            "Do not leave any words or phrases in the original language. "
            "Preserve markdown formatting. Respond with ONLY the translated markdown, "
            "with no explanations or commentary."
        )

    prompt = f"""{lang_instruction}

{text}"""

    try:
        response = ollama.chat(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            options={
                "temperature": 0.1,  # Low temperature for consistent translation
                "num_ctx": 8192,  # Larger context for long texts
            },
        )

        translated = response["message"]["content"].strip()

        # Post-processing: Strip any prompt leakage / preambles
        cleaned = _strip_llm_preamble_and_fences(translated)

        # Remove older-style prompt leaks if they still appear
        cleaned = re.sub(r"TRANSLATED TEXT:\s*", "", cleaned)
        cleaned = re.sub(r"CRITICAL RULES:.*?(?=\n\n|\Z)", "", cleaned, flags=re.DOTALL)
        cleaned = re.sub(r"^TEXT TO TRANSLATE:.*?(?=\n\n|\Z)", "", cleaned, flags=re.DOTALL)

        # Final trim
        cleaned = re.sub(r"^[\s\n]+", "", cleaned)  # Leading whitespace
        cleaned = re.sub(r"[\s\n]+$", "", cleaned)  # Trailing whitespace

        return cleaned

    except Exception as e:
        logger.warning("Translation failed: %s", e)
        logger.warning("Returning original text")
        return text


def translate_in_chunks(
    text: str,
    target_lang: str = "English",
    chunk_size: int = 4000,
    model: str | None = None,
) -> str:
    """Translate long text by breaking into chunks.
    
    Useful for very long documents that exceed model context limits.
    
    Args:
        text: Text to translate
        target_lang: Target language
        chunk_size: Character count per chunk (default: 4000)
        model: Ollama model to use
        
    Returns:
        Translated text
    """
    if len(text) <= chunk_size:
        return translate_text(text, target_lang=target_lang, model=model)
    
    # Split by paragraphs to maintain context
    paragraphs = text.split('\n\n')
    
    chunks = []
    current_chunk = []
    current_size = 0
    
    for para in paragraphs:
        para_size = len(para)
        if current_size + para_size > chunk_size and current_chunk:
            # Translate current chunk
            chunk_text = '\n\n'.join(current_chunk)
            translated_chunk = translate_text(chunk_text, target_lang=target_lang, model=model)
            chunks.append(translated_chunk)
            
            # Start new chunk
            current_chunk = [para]
            current_size = para_size
        else:
            current_chunk.append(para)
            current_size += para_size
    
    # Translate remaining chunk
    if current_chunk:
        chunk_text = '\n\n'.join(current_chunk)
        translated_chunk = translate_text(chunk_text, target_lang=target_lang, model=model)
        chunks.append(translated_chunk)
    
    return '\n\n'.join(chunks)


def detect_language(text: str, model: str | None = None) -> str:
    """Detect the language of the given text.
    
    Args:
        text: Text to analyze
        model: Ollama model to use
        
    Returns:
        Detected language name (e.g., "Spanish", "English", "German")
    """
    model = model or settings.TRANSLATION_MODEL_NAME
    
    # Take a sample if text is very long
    sample = text[:1000] if len(text) > 1000 else text
    
    prompt = f"""What language is this text written in? Answer with ONLY the language name (e.g., "Spanish", "English", "German").

TEXT:
{sample}

LANGUAGE:"""
    
    try:
        response = ollama.chat(
            model=model,
            messages=[{
                'role': 'user',
                'content': prompt
            }],
            options={
                'temperature': 0.0,
            }
        )
        
        language = response['message']['content'].strip()
        return language
        
    except Exception as e:
        logger.warning("Language detection failed: %s", e)
        return "Unknown"


def clean_translated_markdown(text: str, model: str | None = None) -> str:
    """Second-pass cleanup for translated markdown.

    Responsibilities:
    - Remove any remaining LLM preambles / explanations and stray fences
    - Detect obviously Spanish-heavy blocks and re-translate them
    """
    if not text:
        return text

    # Global cleanup for preambles and stray fences
    cleaned = _strip_llm_preamble_and_fences(text)

    # Split by paragraphs (double newline) to localise re-translation
    paragraphs = cleaned.split("\n\n")
    result_paragraphs: list[str] = []

    # Only re-translate when a model is provided; if model is None we just
    # perform structural cleanup without additional LLM calls.
    can_translate = model is not None

    # Known junk/hallucination markers we want to drop entirely
    junk_markers = [
        "physics work",
        "chemistry report",
        "mathematics project",
        "tarefas pendentes",
        "completed tasks",
        "descrição da tarefa",
        "limpeza geral do escritório",
        "negociação de preços",
        "relatório mensal de vendas",
        "sistema de contabilidade",
    ]

    for para in paragraphs:
        lower_para = para.lower()

        # Skip clearly irrelevant hallucinated blocks
        if any(marker in lower_para for marker in junk_markers):
            continue

        if can_translate and _looks_non_english(para):
            translated_para = translate_text(para, target_lang="English", model=model)
            result_paragraphs.append(translated_para)
        else:
            result_paragraphs.append(para)

    return "\n\n".join(result_paragraphs)


