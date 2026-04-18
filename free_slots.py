import sys, os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from db import locksems_col, timetables_col, TEACHING_PERIODS, PERIOD_TIMES


def get_active_codes():
    return timetables_col.distinct("code", {"currentSession": True})


def get_free_slots(faculty_name: str, day: str) -> dict:
    """Computes free slots for a faculty on a given day."""
    active_codes = get_active_codes()

    docs = list(locksems_col.find({
        "code":               {"$in": active_codes},
        "day":                {"$regex": day, "$options": "i"},
        "slotData.faculty":   {"$regex": faculty_name, "$options": "i"},
    }))

    busy_slots   = []
    busy_details = []

    for doc in docs:
        slot = doc.get("slot", "")
        sem  = doc.get("sem", "")
        for entry in doc.get("slotData", []):
            if faculty_name.lower() in entry.get("faculty", "").lower():
                busy_slots.append(slot)
                busy_details.append({
                    "slot":    slot,
                    "time":    PERIOD_TIMES.get(slot, slot),
                    "subject": entry.get("subject", ""),
                    "room":    entry.get("room", ""),
                    "sem":     sem,
                })

    free_slots = [
        {"slot": p, "time": PERIOD_TIMES[p]}
        for p in TEACHING_PERIODS
        if p not in busy_slots
    ]

    return {
        "faculty":      faculty_name,
        "day":          day,
        "busy_slots":   busy_slots,
        "busy_details": busy_details,
        "free_slots":   free_slots,
    }


def get_room_free_slots(room_name: str, day: str) -> dict:
    """
    Computes which periods a room is free on a given day.
    Done entirely in Python — never delegated to LLM.
    """
    active_codes = get_active_codes()

    docs = list(locksems_col.find({
        "code":             {"$in": active_codes},
        "day":              {"$regex": day, "$options": "i"},
        "slotData.room":    {"$regex": room_name, "$options": "i"},
    }))

    busy_slots   = []
    busy_details = []

    for doc in docs:
        slot = doc.get("slot", "")
        sem  = doc.get("sem", "")
        for entry in doc.get("slotData", []):
            if room_name.lower() in entry.get("room", "").lower():
                busy_slots.append(slot)
                busy_details.append({
                    "slot":    slot,
                    "time":    PERIOD_TIMES.get(slot, slot),
                    "subject": entry.get("subject", ""),
                    "faculty": entry.get("faculty", ""),
                    "sem":     sem,
                })

    free_slots = [
        {"slot": p, "time": PERIOD_TIMES[p]}
        for p in TEACHING_PERIODS
        if p not in busy_slots
    ]

    return {
        "room":         room_name,
        "day":          day,
        "busy_slots":   busy_slots,
        "busy_details": busy_details,
        "free_slots":   free_slots,
    }


def format_free_slots_context(result: dict) -> str:
    """Formats faculty free slot result as plain text for LLM."""
    lines = [f"Free slot analysis for {result['faculty']} on {result['day']}:"]

    if result["free_slots"]:
        free_str = ", ".join(f"{f['slot']} ({f['time']})" for f in result["free_slots"])
        lines.append(f"FREE periods: {free_str}")
    else:
        lines.append("FREE periods: none — fully booked all day")

    if result["busy_details"]:
        lines.append("BUSY periods:")
        for b in result["busy_details"]:
            lines.append(
                f"  - {b['slot']} ({b['time']}): teaching {b['subject']} "
                f"in {b['room']} for {b['sem']}"
            )

    return "\n".join(lines)


def format_room_free_slots_context(result: dict) -> str:
    """Formats room free slot result as plain text for LLM."""
    lines = [f"Room {result['room']} availability on {result['day']}:"]

    if result["free_slots"]:
        free_str = ", ".join(f"{f['slot']} ({f['time']})" for f in result["free_slots"])
        lines.append(f"FREE periods: {free_str}")
    else:
        lines.append("FREE periods: none — room is occupied all day")

    if result["busy_details"]:
        lines.append("OCCUPIED periods:")
        for b in result["busy_details"]:
            lines.append(
                f"  - {b['slot']} ({b['time']}): {b['subject']} "
                f"by {b['faculty']} for {b['sem']}"
            )

    return "\n".join(lines)