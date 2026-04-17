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
- branch: department/branch abbreviation like CHE, CSE, PHY, ME etc, or null
- semester_number: just the number like 4, 6 etc, or null
- slot: period name like period1, period2 etc, or null

═══════════════════════════════════════════════════
CRITICAL RULE — ROOM DETECTION (read carefully):
═══════════════════════════════════════════════════
A room identifier is any alphanumeric code that looks like a physical location.
Room patterns include: EE-304, CY-102, SB-3, ALT-0-2, L8-B, ALT-3-3, LH-1 etc.
The pattern is typically: 2-4 letters, optionally followed by dash and numbers.

If the query contains ANY such pattern — even without the word "room" —
set intent to "room_availability" and extract it as the room field.

Examples:
- "what is in ee-304 on monday" → room: "EE-304", intent: room_availability
- "ee-304 monday period3" → room: "EE-304", intent: room_availability  
- "cy-102 wednesday" → room: "CY-102", intent: room_availability
- "who is in sb-3 during period2" → room: "SB-3", intent: room_availability
- "what happens in alt-3-3 on friday" → room: "ALT-3-3", intent: room_availability
- "is l8-b free on tuesday" → room: "L8-B", intent: room_availability
- "what subject is taught in cy-102" → room: "CY-102", intent: room_availability

═══════════════════════════════════════════════════
COURSE/SEM MATCHING:
═══════════════════════════════════════════════════
Map natural language to structured fields:
- "bsc chemical" / "b.sc chemistry" / "bsc che" → course: "B.Sc", branch: "CHE"
- "btech computer science" / "btech cse" → course: "B.Tech", branch: "CSE"
- "mtech" → course: "M.Tech"
- "msc chemistry" → course: "M.Sc", branch: "CHE"
- "4th semester" / "semester 4" / "4th sem" / "sem 4" → semester_number: 4

Branch mappings:
- chemical/chemistry/che → CHE
- computer/cse/cs → CSE
- mechanical/me/mech → ME
- electrical/ee → EE
- electronics/ece → ECE
- civil/ce → CE
- physics/phy → PHY
- maths/math/mathematics/ma → MA

═══════════════════════════════════════════════════
PRONOUN RESOLUTION:
═══════════════════════════════════════════════════
If the query uses "he", "she", "they", "his", "her", "it", "that faculty" —
resolve them using conversation history below.

═══════════════════════════════════════════════════
OTHER INTENT RULES:
═══════════════════════════════════════════════════
- faculty_schedule: user asks what/when a faculty teaches
- subject_info: user asks who teaches a subject or when it is taught
- free_slots: user asks when a faculty is free or available
- sem_timetable: user asks for full timetable of a class/branch/semester
- general: anything not covered above

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
        "ee-304 on monday",
        "what is in cy-102 wednesday period3",
        "sb-3 thursday period2",
        "alt-3-3 friday",
        "who is teaching in l8-b on tuesday",
        "bsc chemical 4th semester timetable",
        "when is emf theory taught",
        "is rawel singh free on monday",
    ]
    for q in tests:
        print(f"\nQ: {q}")
        result = parse_query(q)
        print(f"→ intent={result['intent']}, room={result['room']}, faculty={result['faculty']}, subject={result['subject']}")