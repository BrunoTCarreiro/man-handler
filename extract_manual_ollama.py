import json
import ollama
from pathlib import Path

# The extraction schema
SCHEMA = """{
  "device_metadata": {
    "device_id": "wsed7613s_wsed7613b_wsed7612s_wsed7612b",
    "brand": "LG Electronics",
    "model": "WSED7613S",
    "category": "oven",
    "manual_language": "es"
  },
  "specifications": {
    "dimensions": {"width": "", "height": "", "depth": "", "unit": "cm"},
    "weight": {"value": "", "unit": "kg"},
    "power": {"voltage": "", "frequency": "", "power_consumption": ""},
    "capacity": {"value": "", "unit": "liters"},
    "temperature_range": {"min": "", "max": "", "unit": "°C"},
    "features": []
  },
  "installation": {
    "requirements": [],
    "clearances": {},
    "electrical_connection": {},
    "steps": []
  },
  "operations": [
    {
      "operation_id": "example_operation",
      "name": "Operation name in English",
      "description": "What this operation does",
      "steps": [
        {"step_number": 1, "instruction": "Clear instruction", "notes": []}
      ],
      "tips": [],
      "warnings": []
    }
  ],
  "cooking_modes": [
    {
      "mode_id": "example_mode",
      "name": "Mode name in English",
      "icon_description": "Description of the icon/symbol",
      "best_for": [],
      "temperature_recommendations": {},
      "instructions": ""
    }
  ],
  "maintenance": [
    {
      "task_id": "example_task",
      "name": "Task name in English",
      "frequency": "daily|weekly|monthly|yearly|after_each_use|as_needed",
      "frequency_days": null,
      "difficulty": "easy|medium|hard",
      "estimated_time_minutes": 10,
      "steps": [],
      "required_materials": [],
      "warnings": []
    }
  ],
  "troubleshooting": [
    {
      "issue_id": "example_issue",
      "symptom": "What the user experiences",
      "possible_causes": [
        {
          "cause": "What might be wrong",
          "solution": "How to fix it",
          "diy_possible": true,
          "requires_professional": false
        }
      ],
      "severity": "low|medium|high|critical"
    }
  ],
  "safety_warnings": [
    {
      "warning_id": "example_warning",
      "type": "burn_hazard|electrical|fire_risk|chemical|general",
      "description": "What the danger is",
      "preventive_measures": []
    }
  ],
  "error_codes": [
    {
      "code": "E01",
      "meaning": "What the error means",
      "severity": "info|warning|error|critical",
      "user_action": "What the user should do",
      "requires_technician": false
    }
  ],
  "recipes_or_cooking_guides": [
    {
      "dish": "Food type",
      "mode": "cooking_mode_id",
      "temperature": 220,
      "temperature_unit": "C",
      "time_minutes": 15,
      "rack_position": "middle|top|bottom",
      "tips": []
    }
  ],
  "warranty": {
    "duration_years": null,
    "coverage": "",
    "exclusions": [],
    "contact_info": {}
  },
  "accessories": [
    {
      "name": "Accessory name in English",
      "part_number": "",
      "included": true,
      "optional": false,
      "description": ""
    }
  ]
}"""

EXTRACTION_PROMPT = """You are extracting structured information from an appliance manual (LG oven) to create a comprehensive knowledge base. The manual is in Spanish, but **all output must be in English**.

Your task:
1. Read through the entire manual carefully
2. Extract information according to the schema below
3. Translate all content to English
4. Be thorough but concise - capture key information without being verbose
5. If information is missing or unclear, use null or empty arrays [] rather than guessing

CRITICAL GUIDELINES:

**For operations & cooking_modes:**
- Create separate entries for each distinct function/mode
- Use snake_case for IDs (e.g., "convection_bake", "self_clean", "broil")
- Be specific about when and why to use each mode

**For maintenance:**
- Extract ALL maintenance tasks mentioned
- Standardize frequency values to: daily|weekly|monthly|yearly|after_each_use|as_needed
- Include both routine (cleaning) and occasional (bulb replacement) tasks
- Mark difficulty: easy|medium|hard

**For troubleshooting:**
- Capture the user's perspective (symptom) first
- List all possible causes mentioned
- Mark if DIY or requires professional help
- Assign severity: low (cosmetic), medium (inconvenient), high (non-functional), critical (safety risk)

**For safety_warnings:**
- Extract ALL warnings, especially those with warning icons
- Consolidate similar warnings
- Be explicit about the hazard type

**For error_codes:**
- Create a complete lookup table
- If the manual says "contact service," set requires_technician: true

**For recipes/cooking guides:**
- Extract recommended settings for common foods
- Include temperature, time, and rack position

Return ONLY valid JSON following this exact schema:

{schema}

Quality checks:
✓ All text is in English (translate from Spanish)
✓ JSON is valid (no trailing commas, proper quotes)
✓ IDs are unique and descriptive using snake_case
✓ Arrays are used even for single items
✓ Missing data uses null, "", or []
✓ Step numbers are sequential
✓ No personal interpretation—stick to what the manual states

Return ONLY the JSON object. No markdown code fences, no explanatory text before or after."""


def extract_with_ollama(pdf_path: str, model: str = "qwen2.5:32b"):
    """Extract structured data from PDF using Ollama."""
    
    print(f"\n{'='*60}")
    print(f"Manual Extraction with Ollama")
    print(f"{'='*60}")
    print(f"Model: {model}")
    print(f"PDF: {pdf_path}")
    
    # Check if PyMuPDF is available
    try:
        import fitz  # PyMuPDF
    except ImportError:
        print("\n❌ Error: PyMuPDF (fitz) not installed")
        print("Run: pip install pymupdf")
        return None
    
    # Read PDF
    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        print(f"\n❌ Error reading PDF: {e}")
        return None
    
    # Extract text from all pages
    print(f"\n📄 Extracting text from PDF...")
    full_text = ""
    for page_num in range(len(doc)):
        page = doc[page_num]
        full_text += f"\n--- Page {page_num + 1} ---\n"
        full_text += page.get_text()
    
    print(f"✓ Extracted {len(full_text):,} characters from {len(doc)} pages")
    
    # Save extracted text for reference
    with open("extraction_text.txt", "w", encoding="utf-8") as f:
        f.write(full_text)
    print(f"✓ Saved raw text to: extraction_text.txt")
    
    # Send to Ollama
    print(f"\n🤖 Sending to Ollama model: {model}")
    print(f"⏳ This may take 5-15 minutes depending on your hardware...")
    print(f"   (Processing ~{len(full_text):,} characters)")
    
    try:
        response = ollama.chat(
            model=model,
            messages=[{
                'role': 'user',
                'content': EXTRACTION_PROMPT.format(schema=SCHEMA) + "\n\nMANUAL TEXT:\n" + full_text
            }],
            options={
                'temperature': 0.1,  # Low temperature for consistent extraction
                'num_ctx': 32768,    # Large context window
            }
        )
        
        result = response['message']['content']
        
    except Exception as e:
        print(f"\n❌ Error calling Ollama: {e}")
        print(f"   Make sure Ollama is running and the model '{model}' is available")
        print(f"   Try: ollama pull {model}")
        return None
    
    print(f"\n✓ Received response ({len(result):,} characters)")
    
    # Save raw response
    with open("extraction_raw.txt", "w", encoding="utf-8") as f:
        f.write(result)
    print(f"✓ Saved raw response to: extraction_raw.txt")
    
    # Try to parse as JSON
    try:
        # Remove markdown code fences if present
        cleaned = result.strip()
        if cleaned.startswith('```'):
            lines = cleaned.split('\n')
            # Remove first line with ```json or ```
            lines = lines[1:]
            # Remove last line with ```
            if lines[-1].strip() == '```':
                lines = lines[:-1]
            cleaned = '\n'.join(lines)
        
        data = json.loads(cleaned)
        print(f"\n✅ Successfully parsed JSON!")
        return data
        
    except json.JSONDecodeError as e:
        print(f"\n⚠️  Error parsing JSON: {e}")
        print(f"   Raw output saved to extraction_raw.txt")
        print(f"   You may need to manually clean it up")
        return None


if __name__ == "__main__":
    pdf_path = "data/manuals/wsed7613s_wsed7613b_wsed7612s_wsed7612b/d814e17fdd75346eb28064f68ada7b17828e151ec076124ea4272726a131d0c4.pdf"
    
    # Check if PDF exists
    if not Path(pdf_path).exists():
        print(f"❌ Error: PDF not found at {pdf_path}")
        exit(1)
    
    # Extract
    print("\nStarting extraction...")
    data = extract_with_ollama(pdf_path, model="qwen2.5:32b")
    
    if data:
        # Save to file
        output_path = "data/catalog/lg_oven_structured.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"\n{'='*60}")
        print(f"✅ EXTRACTION COMPLETE!")
        print(f"{'='*60}")
        print(f"Output saved to: {output_path}")
        print(f"\nYou can now:")
        print(f"  1. Review the structured data")
        print(f"  2. Refine the schema if needed")
        print(f"  3. Use this as a template for other manuals")
        print(f"{'='*60}\n")
    else:
        print(f"\n{'='*60}")
        print(f"❌ EXTRACTION FAILED")
        print(f"{'='*60}")
        print(f"Check the error messages above for details.")
        print(f"{'='*60}\n")



