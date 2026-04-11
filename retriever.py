# import sys, os
# sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# import chromadb
# from sentence_transformers import SentenceTransformer
# from db import locksems_col, timetables_col, PERIOD_TIMES
# import warnings
# warnings.filterwarnings("ignore")

# chroma_client = chromadb.PersistentClient(path="./chroma_store")
# collection = chroma_client.get_or_create_collection(name="timetable_slots")
# embedder = SentenceTransformer("all-MiniLM-L6-v2")


# def get_active_codes() -> list:
#     return timetables_col.distinct("code", {"currentSession": True})


# def build_mongo_filter(parsed: dict) -> dict:
#     query = {}
#     active_codes = get_active_codes()
#     query["code"] = {"$in": active_codes}

#     if parsed.get("faculty"):
#         query["slotData.faculty"] = {"$regex": parsed["faculty"], "$options": "i"}
#     if parsed.get("day"):
#         query["day"] = {"$regex": parsed["day"], "$options": "i"}
#     if parsed.get("room"):
#         query["slotData.room"] = {"$regex": parsed["room"], "$options": "i"}
#     if parsed.get("subject"):
#         query["slotData.subject"] = {"$regex": parsed["subject"], "$options": "i"}

#     if parsed.get("sem"):
#         query["sem"] = {"$regex": parsed["sem"], "$options": "i"}
#     else:
#         sem_parts = []
#         if parsed.get("course"):
#             sem_parts.append(parsed["course"])
#         if parsed.get("branch"):
#             sem_parts.append(parsed["branch"])
#         if parsed.get("semester_number"):
#             sem_parts.append(str(parsed["semester_number"]))
#         if sem_parts:
#             query["$and"] = [
#                 {"sem": {"$regex": part, "$options": "i"}}
#                 for part in sem_parts
#             ]

#     if parsed.get("slot"):
#         query["slot"] = parsed["slot"]

#     return query


# def get_actual_faculty_name(faculty_query: str, candidates: list) -> str | None:
#     """
#     Resolves the exact faculty name as stored in ChromaDB
#     by looking it up from MongoDB candidates (case-insensitive match).
#     This fixes the issue where parser returns 'vipin kumar' but
#     ChromaDB stores 'Vipin Kumar'.
#     """
#     faculty_lower = faculty_query.lower()
#     for doc in candidates:
#         for entry in doc.get("slotData", []):
#             stored_name = entry.get("faculty", "")
#             if stored_name and faculty_lower in stored_name.lower():
#                 return stored_name
#     return faculty_query  # fallback to original if not found


# def retrieve(parsed: dict, user_query: str, top_k: int = 10) -> list:
#     mongo_filter = build_mongo_filter(parsed)
#     candidates   = list(locksems_col.find(mongo_filter))
#     query_embedding = embedder.encode(user_query).tolist()

#     if not candidates:
#         print("⚠️  No MongoDB candidates, falling back to full semantic search")
#         results = collection.query(
#             query_embeddings=[query_embedding],
#             n_results=top_k,
#         )
#         return _format_results(results)

#     # Build ChromaDB filter parts
#     filter_parts = []

#     # Resolve exact faculty name from candidates (fixes case mismatch)
#     if parsed.get("faculty"):
#         actual_name = get_actual_faculty_name(parsed["faculty"], candidates)
#         if actual_name:
#             filter_parts.append({"faculty": {"$eq": actual_name}})

#     # Add day only if user specified it
#     if parsed.get("day"):
#         days = list(set(d["day"] for d in candidates if d.get("day")))
#         if len(days) == 1:
#             filter_parts.append({"day": {"$eq": days[0]}})
#         elif len(days) > 1:
#             filter_parts.append({"day": {"$in": days}})

#     # Add slot only if user specified it
#     if parsed.get("slot"):
#         filter_parts.append({"slot": {"$eq": parsed["slot"]}})

#     # Add sem filter only if user specified sem-related fields
#     sem_specified = any([
#         parsed.get("sem"), parsed.get("course"),
#         parsed.get("branch"), parsed.get("semester_number")
#     ])
#     if sem_specified:
#         sems = list(set(d["sem"] for d in candidates if d.get("sem")))
#         if len(sems) == 1:
#             filter_parts.append({"sem": {"$eq": sems[0]}})
#         elif len(sems) > 1:
#             filter_parts.append({"sem": {"$in": sems}})

#     # Add room filter if specified
#     if parsed.get("room"):
#         filter_parts.append({"room": {"$eq": parsed["room"]}})

#     # Build final chroma filter
#     if len(filter_parts) == 0:
#         chroma_filter = None
#     elif len(filter_parts) == 1:
#         chroma_filter = filter_parts[0]
#     else:
#         chroma_filter = {"$and": filter_parts}

#     try:
#         total = collection.count()
#         n = min(top_k, total)
#         if chroma_filter:
#             results = collection.query(
#                 query_embeddings=[query_embedding],
#                 n_results=n,
#                 where=chroma_filter,
#             )
#         else:
#             results = collection.query(
#                 query_embeddings=[query_embedding],
#                 n_results=n,
#             )
#     except Exception as e:
#         print(f"⚠️  ChromaDB query failed: {e}, falling back to unfiltered")
#         results = collection.query(
#             query_embeddings=[query_embedding],
#             n_results=top_k,
#         )

#     return _format_results(results)


# def _format_results(results: dict) -> list:
#     output = []
#     if not results or not results.get("metadatas"):
#         return output
#     for meta, doc in zip(results["metadatas"][0], results["documents"][0]):
#         entry = dict(meta)
#         entry["text"] = doc
#         entry["time"] = PERIOD_TIMES.get(entry.get("slot", ""), entry.get("slot", ""))
#         output.append(entry)
#     return output


# if __name__ == "__main__":
#     from parser import parse_query

#     tests = [
#         "what subjects does Vipin Kumar teach?",
#         "what does Vipin Kumar teach on Monday?",
#         "what subject is taught in room SB-3 during period3 on Thursday?",
#         "give me the timetable of vipin kumar",
#     ]
#     for q in tests:
#         print(f"\nQ: {q}")
#         parsed  = parse_query(q)
#         results = retrieve(parsed, q)
#         print(f"Results ({len(results)}):")
#         for r in results:
#             print(f"  → {r['faculty']} | {r['subject']} | {r['day']} {r['slot']} ({r['time']}) | {r['sem']}")





import sys, os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import chromadb
import warnings
warnings.filterwarnings("ignore")

from db import locksems_col, timetables_col, PERIOD_TIMES
from embedder import embed

chroma_client = chromadb.PersistentClient(path="./chroma_store")
collection = chroma_client.get_or_create_collection(name="timetable_slots")


def get_active_codes():
    return timetables_col.distinct("code", {"currentSession": True})


def build_mongo_filter(parsed):
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
        if parsed.get("course"):       sem_parts.append(parsed["course"])
        if parsed.get("branch"):       sem_parts.append(parsed["branch"])
        if parsed.get("semester_number"): sem_parts.append(str(parsed["semester_number"]))
        if sem_parts:
            query["$and"] = [{"sem": {"$regex": p, "$options": "i"}} for p in sem_parts]

    if parsed.get("slot"):
        query["slot"] = parsed["slot"]

    return query


def get_actual_faculty_name(faculty_query, candidates):
    faculty_lower = faculty_query.lower()
    for doc in candidates:
        for entry in doc.get("slotData", []):
            stored = entry.get("faculty", "")
            if stored and faculty_lower in stored.lower():
                return stored
    return faculty_query


def retrieve(parsed, user_query, top_k=10):
    mongo_filter = build_mongo_filter(parsed)
    candidates   = list(locksems_col.find(mongo_filter))
    query_embedding = embed(user_query)

    if not candidates:
        print("⚠️  No MongoDB candidates, falling back to full semantic search")
        results = collection.query(query_embeddings=[query_embedding], n_results=top_k)
        return _format_results(results)

    filter_parts = []

    if parsed.get("faculty"):
        actual_name = get_actual_faculty_name(parsed["faculty"], candidates)
        if actual_name:
            filter_parts.append({"faculty": {"$eq": actual_name}})

    if parsed.get("day"):
        days = list(set(d["day"] for d in candidates if d.get("day")))
        if len(days) == 1:
            filter_parts.append({"day": {"$eq": days[0]}})
        elif len(days) > 1:
            filter_parts.append({"day": {"$in": days}})

    if parsed.get("slot"):
        filter_parts.append({"slot": {"$eq": parsed["slot"]}})

    sem_specified = any([parsed.get("sem"), parsed.get("course"),
                         parsed.get("branch"), parsed.get("semester_number")])
    if sem_specified:
        sems = list(set(d["sem"] for d in candidates if d.get("sem")))
        if len(sems) == 1:
            filter_parts.append({"sem": {"$eq": sems[0]}})
        elif len(sems) > 1:
            filter_parts.append({"sem": {"$in": sems}})

    if parsed.get("room"):
        filter_parts.append({"room": {"$eq": parsed["room"]}})

    if len(filter_parts) == 0:
        chroma_filter = None
    elif len(filter_parts) == 1:
        chroma_filter = filter_parts[0]
    else:
        chroma_filter = {"$and": filter_parts}

    try:
        n = min(top_k, collection.count())
        if chroma_filter:
            results = collection.query(query_embeddings=[query_embedding], n_results=n, where=chroma_filter)
        else:
            results = collection.query(query_embeddings=[query_embedding], n_results=n)
    except Exception as e:
        print(f"⚠️  ChromaDB query failed: {e}")
        results = collection.query(query_embeddings=[query_embedding], n_results=top_k)

    return _format_results(results)


def _format_results(results):
    output = []
    if not results or not results.get("metadatas"):
        return output
    for meta, doc in zip(results["metadatas"][0], results["documents"][0]):
        entry = dict(meta)
        entry["text"] = doc
        entry["time"] = PERIOD_TIMES.get(entry.get("slot", ""), entry.get("slot", ""))
        output.append(entry)
    return output