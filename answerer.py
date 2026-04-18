import sys, os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import time
import warnings
warnings.filterwarnings("ignore")

from groq import Groq
from dotenv import load_dotenv
from free_slots import (
    get_free_slots, format_free_slots_context,
    get_room_free_slots, format_room_free_slots_context
)

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

ANSWER_PROMPT = """
You are a helpful college timetable assistant.
Answer the user's question using ONLY the context provided below.
Be concise and to the point. Use plain English. No vague answers.
List all items clearly — do not summarize or skip any.
If the answer is not in the context, say "I don't have that information in the timetable."
Do not guess, invent, or assume any details not present in the context.

Context:
{context}

Question: {question}
"""


def build_context(parsed: dict, retrieval_results: list) -> str:
    intent  = parsed.get("intent", "general")
    faculty = parsed.get("faculty")
    room    = parsed.get("room")
    day     = parsed.get("day")
    slot    = parsed.get("slot")

    # ── Faculty free slots — Python computed ──────────────────────────────────
    if intent == "free_slots":
        if not faculty:
            return "Could not determine which faculty member you're asking about."
        if not day:
            return f"Could not determine which day you're asking about for {faculty}."
        result = get_free_slots(faculty, day)
        return format_free_slots_context(result)

    # ── Room free slots — Python computed ─────────────────────────────────────
    if intent == "room_free_slots":
        if not room:
            return "Could not determine which room you're asking about."
        if not day:
            return f"Could not determine which day you're asking about for room {room}."
        result = get_room_free_slots(room, day)
        return format_room_free_slots_context(result)

    if not retrieval_results:
        return "No matching timetable entries found."

    # ── Faculty schedule ──────────────────────────────────────────────────────
    if intent == "faculty_schedule":
        by_day = {}
        for r in retrieval_results:
            d = r.get("day", "Unknown")
            if d not in by_day:
                by_day[d] = []
            by_day[d].append(r)

        unique_subjects = []
        seen = set()
        for r in retrieval_results:
            subj = r.get("subject", "")
            base = subj.split("(")[0].strip() if "(" in subj else subj
            if base and base not in seen:
                seen.add(base)
                unique_subjects.append(base)

        lines = []
        if day:
            lines.append(f"Schedule for {faculty} on {day}:")
            for r in sorted(retrieval_results, key=lambda x: x.get("slot", "")):
                lines.append(
                    f"- {r.get('slot')} ({r.get('time')}): "
                    f"teaches {r.get('subject')} in room {r.get('room')} for {r.get('sem')}"
                )
        elif slot:
            lines.append(f"Schedule for {faculty} during {slot}:")
            for r in retrieval_results:
                lines.append(
                    f"- {r.get('day')}: teaches {r.get('subject')} "
                    f"in room {r.get('room')} for {r.get('sem')}"
                )
        else:
            lines.append(f"Unique subjects taught by {faculty}: {', '.join(unique_subjects)}")
            lines.append(f"\nFull teaching schedule for {faculty}:")
            for d, entries in sorted(by_day.items()):
                lines.append(f"\n{d}:")
                for r in sorted(entries, key=lambda x: x.get("slot", "")):
                    lines.append(
                        f"  - {r.get('slot')} ({r.get('time')}): "
                        f"{r.get('subject')} in {r.get('room')} for {r.get('sem')}"
                    )
        return "\n".join(lines)

    # ── Room availability ─────────────────────────────────────────────────────
    if intent == "room_availability":
        lines = [f"Schedule for room {room}:"]
        for r in sorted(retrieval_results, key=lambda x: (x.get("day",""), x.get("slot",""))):
            lines.append(
                f"- {r.get('day')} {r.get('slot')} ({r.get('time')}): "
                f"{r.get('subject')} by {r.get('faculty')} for {r.get('sem')}"
            )
        return "\n".join(lines)

    # ── Subject info ──────────────────────────────────────────────────────────
    if intent == "subject_info":
        lines = ["Subject information:"]
        for r in sorted(retrieval_results, key=lambda x: (x.get("day",""), x.get("slot",""))):
            lines.append(
                f"- {r.get('subject')} is taught by {r.get('faculty')} "
                f"on {r.get('day')} {r.get('slot')} ({r.get('time')}) "
                f"in room {r.get('room')} for {r.get('sem')}"
            )
        return "\n".join(lines)

    # ── Sem timetable ─────────────────────────────────────────────────────────
    if intent == "sem_timetable":
        by_day = {}
        for r in retrieval_results:
            d = r.get("day", "Unknown")
            if d not in by_day:
                by_day[d] = []
            by_day[d].append(r)
        lines = [f"Timetable for {parsed.get('sem') or parsed.get('branch') or 'requested class'}:"]
        for d, entries in sorted(by_day.items()):
            lines.append(f"\n{d}:")
            for r in sorted(entries, key=lambda x: x.get("slot", "")):
                lines.append(
                    f"  - {r.get('slot')} ({r.get('time')}): "
                    f"{r.get('subject')} by {r.get('faculty')} in {r.get('room')}"
                )
        return "\n".join(lines)

    # ── General fallback ──────────────────────────────────────────────────────
    lines = []
    for r in retrieval_results:
        lines.append(
            f"- {r.get('faculty')} teaches {r.get('subject')} "
            f"in room {r.get('room')} on {r.get('day')} "
            f"during {r.get('slot')} ({r.get('time')}) for {r.get('sem')}"
        )
    return "\n".join(lines)


def call_groq_with_retry(messages: list, max_retries: int = 3) -> str:
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=messages,
                temperature=0.1,   # lower temp = more consistent answers
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "rate_limit" in error_str.lower():
                wait = 30
                if attempt < max_retries - 1:
                    print(f"⚠️  Rate limited. Waiting {wait}s...")
                    time.sleep(wait)
                    continue
                return "The assistant is temporarily rate limited. Please try again in a moment."
            return "Sorry, I couldn't generate an answer right now. Please try again."
    return "Sorry, the assistant is temporarily unavailable."


def generate_answer(parsed: dict, retrieval_results: list, user_query: str, history: list = []) -> str:
    context = build_context(parsed, retrieval_results)

    messages = [
        {
            "role": "system",
            "content": (
                "You are a helpful college timetable assistant. "
                "Answer using ONLY the context provided. Be concise and to the point. "
                "List all items — never skip or summarize. "
                "Never guess or invent details. "
                "If answer not in context say: I don't have that information in the timetable."
            )
        }
    ]

    for msg in history[-6:]:
        messages.append({"role": msg["role"], "content": msg["content"]})

    messages.append({
        "role": "user",
        "content": f"Context:\n{context}\n\nQuestion: {user_query}"
    })

    return call_groq_with_retry(messages)