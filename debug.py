
import sys, os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import warnings
warnings.filterwarnings("ignore")

from parser import parse_query
from retriever import retrieve, build_mongo_filter
from db import locksems_col, timetables_col

tests = [
    "what subjects does harimurugan teach?",
    "what does Vipin Kumar teach on Monday?",
    "what subject is taught in room SB-3 during period3 on Thursday?",
    "give me the timetable of vipin kumar",
]

active_codes = timetables_col.distinct("code", {"currentSession": True})

for q in tests:
    print(f"\n{'='*60}")
    print(f"Q: {q}")
    parsed = parse_query(q)
    print(f"Parsed: {parsed}")

    mongo_filter = build_mongo_filter(parsed)
    candidates = list(locksems_col.find(mongo_filter))
    print(f"MongoDB candidates: {len(candidates)}")
    for c in candidates[:2]:
        print(f"  day={c['day']} slot={c['slot']} sem={c['sem']}")
        for e in c.get('slotData', []):
            print(f"    → {e.get('faculty')} | {e.get('subject')} | {e.get('room')}")

    results = retrieve(parsed, q)
    print(f"Retrieval results: {len(results)}")
    for r in results:
        print(f"  → {r['faculty']} | {r['subject']} | {r['day']} {r['slot']} ({r['time']}) | {r['sem']}")