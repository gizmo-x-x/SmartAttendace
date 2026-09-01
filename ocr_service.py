"""
ocr_service.py

Handles all communication with the AI/OCR provider (currently Google Gemini).
The extraction prompt is now built dynamically based on the teacher's chosen
table configuration (number of weeks, column names) instead of being fixed.
"""

import os
import json
from google import genai
from google.genai import types

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

MODEL_NAME = "gemini-3.6-flash"

DEFAULT_CONFIG = {
    "numWeeks": 14,
    "columns": [
        {"id": "student_name", "label": "Name"},
        {"id": "matric_no", "label": "Matric No"},
        {"id": "programme", "label": "Programme"},
    ],
}


def build_extraction_prompt(config):
    """Builds the AI instructions dynamically based on the teacher's chosen
    columns and number of weeks."""
    columns = config.get("columns") or DEFAULT_CONFIG["columns"]
    num_weeks = config.get("numWeeks") or DEFAULT_CONFIG["numWeeks"]

    column_lines = "\n".join(f'- "{c["id"]}": {c["label"]}' for c in columns)
    example_fields = ",\n      ".join(
        f'"{c["id"]}": "value for {c["label"]}"' for c in columns
    )

    return f"""You are looking at a photo or PDF of a paper attendance register.

The sheet has these columns for each student:
{column_lines}

...followed by {num_weeks} week columns (Week 1 through Week {num_weeks}),
where each week is marked either 1 (present) or 0 (absent).

Extract the attendance information and respond with ONLY a valid JSON object,
no explanation, no markdown formatting, no code fences. Use this exact shape:

{{
  "students": [
    {{
      {example_fields},
      "weekly_attendance": [
        {{"week": 1, "status": "1"}},
        {{"week": 2, "status": "0"}},
        ...continue for all {num_weeks} weeks...
      ]
    }}
  ]
}}

Important rules:
- Use EXACTLY the JSON keys given above for each column - do not rename or
  translate them.
- Always include all {num_weeks} week entries for every student, even if a
  column looks empty - use "Unclear" as the status in that case.
- Each week's "status" must be exactly "1", "0", or "Unclear" - nothing else.
- Handwriting may be messy or partially illegible. Do your best, but if you
  genuinely cannot read a value clearly, use "Unclear" rather than guessing.
- Do not invent students who aren't on the sheet.
- Respond with ONLY the JSON object, nothing else.
"""


def _get_media_type(file_path):
    extension = file_path.rsplit(".", 1)[-1].lower()
    if extension in ("jpg", "jpeg"):
        return "image/jpeg"
    if extension == "png":
        return "image/png"
    if extension == "pdf":
        return "application/pdf"
    raise ValueError(f"Unsupported file type: {extension}")


def extract_attendance_data(file_path, config=None):
    """Sends the image/PDF to Gemini and asks it to extract structured
    attendance data, using the teacher's chosen table configuration."""
    if not config:
        config = DEFAULT_CONFIG

    try:
        media_type = _get_media_type(file_path)
    except ValueError as e:
        return {"success": False, "data": None, "raw_text": None, "error": str(e)}

    try:
        with open(file_path, "rb") as f:
            file_bytes = f.read()
    except OSError as e:
        return {"success": False, "data": None, "raw_text": None,
                "error": f"Could not read the file: {e}"}

    file_part = types.Part.from_bytes(data=file_bytes, mime_type=media_type)
    prompt = build_extraction_prompt(config)

    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=[file_part, prompt],
        )
    except Exception as e:
        return {"success": False, "data": None, "raw_text": None,
                "error": f"AI request failed: {e}"}

    raw_text = response.text or ""
    cleaned_text = raw_text.strip()
    if cleaned_text.startswith("```"):
        cleaned_text = cleaned_text.strip("`")
        if cleaned_text.startswith("json"):
            cleaned_text = cleaned_text[4:]
        cleaned_text = cleaned_text.strip()

    try:
        parsed = json.loads(cleaned_text)
    except json.JSONDecodeError:
        return {
            "success": False,
            "data": None,
            "raw_text": raw_text,
            "error": "The AI's response wasn't valid JSON. Check raw_text to see what it actually returned.",
        }

    return {"success": True, "data": parsed, "raw_text": raw_text, "error": None}