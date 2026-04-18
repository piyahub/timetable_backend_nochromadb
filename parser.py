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
- intent: one of [faculty_schedule, room_availability, room_free_slots, subject_info, free_slots, sem_timetable, general]
- faculty: full or partial faculty name as string, or null
- room: room name/number as string, or null
- day: full day name (Monday/Tuesday/Wednesday/Thursday/Friday/Saturday) or null
- subject: subject name as string, or null
- sem: semester string like B.Sc-CHE-4 if mentioned exactly, or null
- course: degree name like B.Sc, B.Tech, BCA etc, or null
- branch: department/branch abbreviation like CHE, CSE, PHY, ME etc, or null
- semester_number: just the number like 4, 6 etc, or null
- slot: period name like period1, period2 etc, or null

═══════════════════════════════════════════════════
ROOM DETECTION (CRITICAL):
═══════════════════════════════════════════════════
Room identifiers are alphanumeric codes like: EE-304, CY-102, SB-3, ALT-0-2, L8-B
Pattern: letters optionally followed by dash and numbers.

If query contains such a pattern WITHOUT asking about free/empty/available:
→ intent: room_availability, room: <the code>

If query asks when a room is FREE, EMPTY, AVAILABLE, VACANT:
→ intent: room_free_slots, room: <the code>

Examples:
- "ee-304 on monday" → intent: room_availability, room: "EE-304"
- "what is in cy-102 wednesday" → intent: room_availability, room: "CY-102"
- "when is ee-304 free on monday" → intent: room_free_slots, room: "EE-304"
- "is ee-304 empty on monday" → intent: room_free_slots, room: "EE-304"
- "which periods is sb-3 available on friday" → intent: room_free_slots, room: "SB-3"
- "when is cy-102 vacant" → intent: room_free_slots, room: "CY-102"

═══════════════════════════════════════════════════
COURSE/SEM MATCHING:
═══════════════════════════════════════════════════
- "bsc chemical" / "b.sc chemistry" → course: "B.Sc", branch: "CHE"
- "btech computer science" / "btech cse" → course: "B.Tech", branch: "CSE"
- "msc chemistry" → course: "M.Sc", branch: "CHE"
- "4th semester" / "sem 4" → semester_number: 4

Branch mappings:
chemical/chemistry/che→CHE, computer/cse/cs→CSE, mechanical/me/mech→ME,
electrical/ee→EE, electronics/ece→ECE, civil/ce→CE, physics/phy→PHY,
maths/math/mathematics→MA

═══════════════════════════════════════════════════
OTHER INTENTS:
═══════════════════════════════════════════════════
- faculty_schedule: what/when a faculty teaches
- free_slots: when a FACULTY is free
- subject_info: who teaches a subject or when it is taught
- sem_timetable: full timetable of a class/branch/semester
- general: anything else

PRONOUN RESOLUTION: Resolve "he/she/they/his/her/it" using conversation history.

{history_section}
Current Query: "{query}"
"""

def parse_query(user_query: str, history: list = []) -> dict:
    history_section = ""
    if history:
        history_section = "Conversation history (use to resolve pronouns/references):\n"
        for msg in history[-6:]:
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
        "when is ee-304 free on monday",
        "when is ee 304 empty on monday",
        "which periods is cy-102 available on wednesday",
        "ee-304 on monday",
        "what is in cy-102 wednesday period3",
    ]
    for q in tests:
        print(f"\nQ: {q}")
        r = parse_query(q)
        print(f"→ intent={r['intent']}, room={r['room']}, day={r['day']}")