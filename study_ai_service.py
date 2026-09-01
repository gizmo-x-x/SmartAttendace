"""
study_ai_service.py
Uses Gemini to help a student study a specific topic - structured guidance,
not a huge dumped answer. Reuses the same API key already set up for OCR.
"""

import os
from google import genai

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
MODEL_NAME = "gemini-3.6-flash"

ANALYZE_PROMPT = """You are a helpful, encouraging study assistant for a student learning
the topic below. Do NOT dump one giant wall of text - structure your response
clearly using these exact section headers, each on its own line:

SIMPLE EXPLANATION:
(2-4 sentences, plain language)

KEY CONCEPTS:
(short bullet list)

IMPORTANT TERMS:
(short bullet list, term - one line meaning)

EXAMPLE:
(one short concrete example)

COMMON MISTAKES:
(short bullet list)

SUMMARY:
(1-2 sentences)

PRACTICE QUESTIONS:
(2-3 short questions, no answers)

Course: {course_name}
Topic: {topic_title}
Topic description (if provided): {topic_description}

Keep the whole response reasonably short and focused on learning, not
overwhelming. Do not claim your explanation is guaranteed to be fully correct -
encourage the student to verify against their course materials.
"""

FOLLOWUP_PROMPT = """You are continuing a study conversation about this topic.

Course: {course_name}
Topic: {topic_title}

Earlier explanation you gave:
{previous_explanation}

The student's follow-up question:
{question}

Answer clearly and concisely, staying focused on helping the student learn.
Do not repeat the entire earlier explanation.
"""


def analyze_topic(course_name, topic_title, topic_description):
    prompt = ANALYZE_PROMPT.format(
        course_name=course_name,
        topic_title=topic_title,
        topic_description=topic_description or "None provided",
    )
    try:
        response = client.models.generate_content(model=MODEL_NAME, contents=[prompt])
        return {"success": True, "text": response.text, "error": None}
    except Exception as e:
        return {"success": False, "text": None, "error": f"AI request failed: {e}"}


def ask_followup(course_name, topic_title, previous_explanation, question):
    prompt = FOLLOWUP_PROMPT.format(
        course_name=course_name,
        topic_title=topic_title,
        previous_explanation=previous_explanation,
        question=question,
    )
    try:
        response = client.models.generate_content(model=MODEL_NAME, contents=[prompt])
        return {"success": True, "text": response.text, "error": None}
    except Exception as e:
        return {"success": False, "text": None, "error": f"AI request failed: {e}"}