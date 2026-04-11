# """
# ingest.py

# Run this ONCE to do the initial load of all active timetable slots into ChromaDB.
# After this, individual slot updates are handled automatically via the upsert hook
# in the API routes — you never need to run a full re-ingestion again.

# Usage:
#     python ingest.py
# """

# import sys, os
# sys.path.append(os.path.dirname(os.path.abspath(__file__)))
# import hashlib
# from sentence_transformers import SentenceTransformer
# import chromadb
# from db import timetables_col, locksems_col, PERIOD_TIMES, parse_sem

# # ── ChromaDB client (local persistent storage) ──────────────────────────────
# chroma_client = chromadb.PersistentClient(path="./chroma_store")
# collection = chroma_client.get_or_create_collection(name="timetable_slots")

# # ── Embedding model ──────────────────────────────────────────────────────────
# embedder = SentenceTransformer("all-MiniLM-L6-v2")


# def make_doc_id(faculty: str, day: str, slot: str, sem: str, subject: str) -> str:
#     """
#     Creates a stable, unique ID for a single slotData entry.
#     Same inputs always produce the same ID — so upserting never creates duplicates.
#     """
#     key = f"{faculty}|{day}|{slot}|{sem}|{subject}".lower()
#     return hashlib.md5(key.encode()).hexdigest()


# def build_sentence(faculty: str, subject: str, room: str,
#                    day: str, slot: str, sem: str) -> str:
#     """
#     Converts raw fields into a natural language sentence for embedding.
#     The period label is expanded to its actual time range.
#     """
#     time_range = PERIOD_TIMES.get(slot, slot)  # fallback to raw value if unknown
#     parsed = parse_sem(sem)
#     return (
#         f"{faculty} teaches {subject} in room {room} "
#         f"on {day} during {slot} ({time_range}) "
#         f"for {sem} "
#         f"(course: {parsed['course']}, branch: {parsed['branch']}, semester: {parsed['semester']})."
#     )


# def get_active_locksems():
#     """
#     Step 1: Find all timetable codes where currentSession is True.
#     Step 2: Return all locksems documents whose code is in that active set.
#     """
#     active_codes = timetables_col.distinct("code", {"currentSession": True})
#     if not active_codes:
#         print("⚠️  No active sessions found in timetables collection.")
#         return []

#     print(f"✅  Found {len(active_codes)} active session code(s).")
#     docs = list(locksems_col.find({"code": {"$in": active_codes}}))
#     print(f"✅  Found {len(docs)} locksems documents for active sessions.")
#     return docs


# def upsert_slot_entry(faculty: str, subject: str, room: str,
#                       day: str, slot: str, sem: str, code: str):
#     """
#     Builds a sentence, embeds it, and upserts into ChromaDB.
#     Called both during full ingestion and on individual slot updates.
#     """
#     doc_id   = make_doc_id(faculty, day, slot, sem, subject)
#     sentence = build_sentence(faculty, subject, room, day, slot, sem)
#     embedding = embedder.encode(sentence).tolist()

#     collection.upsert(
#         ids=[doc_id],
#         embeddings=[embedding],
#         documents=[sentence],
#         metadatas=[{
#             "faculty":  faculty,
#             "subject":  subject,
#             "room":     room,
#             "day":      day,
#             "slot":     slot,
#             "sem":      sem,
#             "code":     code,
#         }]
#     )
#     return doc_id


# def run_full_ingestion():
#     """
#     Full ingestion — only needed once (or after a major data reset).
#     Iterates every active locksem, expands slotData, and upserts each entry.
#     """
#     docs = get_active_locksems()
#     if not docs:
#         return

#     total = 0
#     skipped = 0

#     for doc in docs:
#         day  = doc.get("day", "")
#         slot = doc.get("slot", "")
#         sem  = doc.get("sem", "")
#         code = doc.get("code", "")
#         slot_data = doc.get("slotData", [])

#         for entry in slot_data:
#             faculty = entry.get("faculty", "").strip()
#             subject = entry.get("subject", "").strip()
#             room    = entry.get("room", "").strip()

#             # Skip entries with missing critical fields
#             if not faculty or not subject:
#                 skipped += 1
#                 continue

#             upsert_slot_entry(faculty, subject, room, day, slot, sem, code)
#             total += 1

#     print(f"✅  Ingestion complete. {total} slot entries upserted, {skipped} skipped.")


# if __name__ == "__main__":
#     run_full_ingestion()
import sys, os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import hashlib
import warnings
warnings.filterwarnings("ignore")

import chromadb
from dotenv import load_dotenv
from db import timetables_col, locksems_col, PERIOD_TIMES, parse_sem
from embedder import embed

load_dotenv()

chroma_client = chromadb.PersistentClient(path="./chroma_store")
collection = chroma_client.get_or_create_collection(name="timetable_slots")


def make_doc_id(faculty: str, day: str, slot: str, sem: str, subject: str) -> str:
    key = f"{faculty}|{day}|{slot}|{sem}|{subject}".lower()
    return hashlib.md5(key.encode()).hexdigest()


def build_sentence(faculty, subject, room, day, slot, sem) -> str:
    time_range = PERIOD_TIMES.get(slot, slot)
    parsed = parse_sem(sem)
    return (
        f"{faculty} teaches {subject} in room {room} "
        f"on {day} during {slot} ({time_range}) "
        f"for {sem} "
        f"(course: {parsed['course']}, branch: {parsed['branch']}, semester: {parsed['semester']})."
    )


def get_active_locksems():
    active_codes = timetables_col.distinct("code", {"currentSession": True})
    if not active_codes:
        print("⚠️  No active sessions found.")
        return []
    print(f"✅  Found {len(active_codes)} active session code(s).")
    docs = list(locksems_col.find({"code": {"$in": active_codes}}))
    print(f"✅  Found {len(docs)} locksems documents.")
    return docs


def upsert_slot_entry(faculty, subject, room, day, slot, sem, code):
    doc_id   = make_doc_id(faculty, day, slot, sem, subject)
    sentence = build_sentence(faculty, subject, room, day, slot, sem)
    embedding = embed(sentence)

    collection.upsert(
        ids=[doc_id],
        embeddings=[embedding],
        documents=[sentence],
        metadatas=[{
            "faculty": faculty, "subject": subject,
            "room": room,      "day": day,
            "slot": slot,      "sem": sem,
            "code": code,
        }]
    )
    return doc_id


def run_full_ingestion():
    docs = get_active_locksems()
    if not docs:
        return

    total = 0
    skipped = 0

    for doc in docs:
        day  = doc.get("day", "")
        slot = doc.get("slot", "")
        sem  = doc.get("sem", "")
        code = doc.get("code", "")

        for entry in doc.get("slotData", []):
            faculty = entry.get("faculty", "").strip()
            subject = entry.get("subject", "").strip()
            room    = entry.get("room", "").strip()

            if not faculty or not subject:
                skipped += 1
                continue

            upsert_slot_entry(faculty, subject, room, day, slot, sem, code)
            total += 1

    print(f"✅  Ingestion complete. {total} upserted, {skipped} skipped.")


if __name__ == "__main__":
    run_full_ingestion()