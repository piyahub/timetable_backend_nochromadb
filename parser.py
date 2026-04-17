import sys, os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import json
import warnings
warnings.filterwarnings("ignore")

from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

PARSE_PROMPT = """
You are a college timetable query parser. Extract structured fields from the user query below.
Return ONLY valid JSON. No explanation. No extra text. No markdown. No code blocks.

Fields to extract:
- intent: one of [faculty_schedule, room_availability, subject_info, free_slots, sem_timetable, general]
- faculty: full or partial faculty name as string, or null
- room: room name/number as string, or null
- day: full day name (Monday/Tuesday/Wednesday/Thursday/Friday/Saturday) or null
- subject: subject name as string, or null
- sem: semester string like B.Sc-CHE-4 if mentioned exactly, or null
- course: degree name like B.Sc, B.Tech, BCA etc, or null
- branch: department/branch like CHE, CSE, PHY etc, or null
- semester_number: just the number like 4, 6 etc, or null
- slot: period name like period1, period2 etc, or null

Intent guide:
- faculty_schedule: user asks what/when a faculty teaches
- room_availability: user asks about a room
- subject_info: user asks who teaches a subject or when a subject is taught
- free_slots: user asks when a faculty is free or available
- sem_timetable: user asks for a full timetable of a class/sem/branch
- general: anything else

IMPORTANT: If the query uses pronouns like "he", "she", "they", "his", "her", "their", "it"
or references like "that faculty", "the same person", "them" — resolve them using the
conversation history provided. For example if history shows we were talking about
"Rawel Singh" and user asks "when is he free?", extract faculty as "Rawel Singh".

{history_section}
Current Query: "{query}"
"""

def parse_query(user_query: str, history: list = []) -> dict:
    """
    Sends the user query to Groq and returns extracted fields as a dict.
    Uses conversation history to resolve pronouns and follow-up references.
    """
    # Build history section for the prompt
    history_section = ""
    if history:
        history_section = "Conversation history (use this to resolve pronouns/references):\n"
        for msg in history[-6:]:  # last 3 exchanges
            role = "User" if msg["role"] == "user" else "Assistant"
            history_section += f"{role}: {msg['content']}\n"
        history_section += "\n"

    prompt = PARSE_PROMPT.format(
        query=user_query,
        history_section=history_section
    )

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )
        raw = response.choices[0].message.content.strip()

        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()

        return json.loads(raw)

    except Exception as e:
        print(f"⚠️  Query parsing failed: {e}")
        return {
            "intent": "general", "faculty": None, "room": None,
            "day": None, "subject": None, "sem": None,
            "course": None, "branch": None, "semester_number": None, "slot": None,
        }


if __name__ == "__main__":
    tests = [
        "When is Rawel Singh free on Monday?",
        "Who teaches chemistry to B.Sc CHE semester 4?",
        "What is in room CY-102 on Wednesday period3?",
        "Show me the full timetable for B.Sc-CHE-4",
        "When does Suneel Dutt teach on Friday?",
    ]
    for q in tests:
        print(f"\nQ: {q}")
        print(f"→ {parse_query(q)}")