import sys, os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import warnings
warnings.filterwarnings("ignore")

from db import locksems_col, timetables_col, PERIOD_TIMES


def get_active_codes():
    return timetables_col.distinct("code", {"currentSession": True})


def build_mongo_filter(parsed: dict) -> dict:
    query = {}
    active_codes = get_active_codes()
    query["code"] = {"$in": active_codes}

    if parsed.get("faculty"):
        query["slotData.faculty"] = {"$regex": parsed["faculty"], "$options": "i"}
    if parsed.get("day"):
        query["day"] = {"$regex": parsed["day"], "$options": "i"}
    if parsed.get("room"):
        query["slotData.room"] = {"$regex": parsed["room"], "$options": "i"}
    if parsed.get("subject"):
        query["slotData.subject"] = {"$regex": parsed["subject"], "$options": "i"}

    if parsed.get("sem"):
        query["sem"] = {"$regex": parsed["sem"], "$options": "i"}
    else:
        sem_parts = []
        if parsed.get("course"):          sem_parts.append(parsed["course"])
        if parsed.get("branch"):          sem_parts.append(parsed["branch"])
        if parsed.get("semester_number"): sem_parts.append(str(parsed["semester_number"]))
        if sem_parts:
            query["$and"] = [{"sem": {"$regex": p, "$options": "i"}} for p in sem_parts]

    if parsed.get("slot"):
        query["slot"] = parsed["slot"]

    return query


def retrieve(parsed: dict, user_query: str, top_k: int = 100) -> list:
    """
    MongoDB-only retrieval.
    top_k is high (100) to ensure ALL slots for a faculty are returned.
    No early break — collects everything then returns.
    """
    mongo_filter = build_mongo_filter(parsed)
    # No limit on MongoDB query — fetch ALL matching docs
    docs = list(locksems_col.find(mongo_filter))

    if not docs:
        return []

    results = []
    faculty_filter = parsed.get("faculty", "").lower() if parsed.get("faculty") else None
    room_filter    = parsed.get("room", "").lower()    if parsed.get("room")    else None

    for doc in docs:
        day  = doc.get("day",  "")
        slot = doc.get("slot", "")
        sem  = doc.get("sem",  "")
        code = doc.get("code", "")

        for entry in doc.get("slotData", []):
            faculty = entry.get("faculty", "").strip()
            subject = entry.get("subject", "").strip()
            room    = entry.get("room",    "").strip()

            if not faculty and not subject:
                continue

            # Faculty filter — case insensitive partial match
            if faculty_filter and faculty_filter not in faculty.lower():
                continue

            # Room filter — case insensitive partial match
            if room_filter and room_filter not in room.lower():
                continue

            results.append({
                "faculty": faculty,
                "subject": subject,
                "room":    room,
                "day":     day,
                "slot":    slot,
                "sem":     sem,
                "code":    code,
                "time":    PERIOD_TIMES.get(slot, slot),
                "text":    f"{faculty} teaches {subject} in {room} on {day} {slot} for {sem}",
            })

    return results  # return ALL results, answerer will deduplicate subjects