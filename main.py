import sys, os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import warnings
warnings.filterwarnings("ignore")

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel
from typing import List, Optional
from dotenv import load_dotenv

from parser import parse_query
from retriever import retrieve
from answerer import generate_answer
from pdf_handler import generate_faculty_timetable_pdf, generate_course_timetable_pdf
from profanity_check import contains_profanity, PROFANITY_RESPONSE

load_dotenv()

app = FastAPI(title="Timetable Chatbot API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Models ────────────────────────────────────────────────────────────────────

class HistoryMessage(BaseModel):
    role:    str
    content: str

class ChatRequest(BaseModel):
    query:   str
    history: List[HistoryMessage] = []

class ChatResponse(BaseModel):
    answer:  str
    intent:  str
    parsed:  dict
    pdf_url: Optional[str] = None

class SlotUpdateRequest(BaseModel):
    faculty: str
    subject: str
    room:    str
    day:     str
    slot:    str
    sem:     str
    code:    str


# ── PDF intent detection ──────────────────────────────────────────────────────

TIMETABLE_TRIGGERS = [
    "timetable of", "timetable for",
    "schedule of",  "schedule for",
    "give me timetable", "show me timetable",
    "generate timetable", "get timetable",
    "download timetable", "print timetable",
]

def is_timetable_pdf_request(query: str) -> bool:
    return any(trigger in query.lower() for trigger in TIMETABLE_TRIGGERS)


# ── Chat endpoint ─────────────────────────────────────────────────────────────

@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    user_query = req.query.strip()
    history    = [{"role": m.role, "content": m.content} for m in req.history]

    if not user_query:
        return ChatResponse(
            answer="Please ask a question about the timetable.",
            intent="general", parsed={},
        )

    # ── Profanity check ───────────────────────────────────────────────────────
    if contains_profanity(user_query):
        return ChatResponse(
            answer=PROFANITY_RESPONSE,
            intent="profanity",
            parsed={},
        )

    parsed  = parse_query(user_query, history)
    faculty = parsed.get("faculty")
    sem     = parsed.get("sem") or parsed.get("branch")

    # PDF request
    if is_timetable_pdf_request(user_query):
        if faculty:
            return ChatResponse(
                answer=f"Here is the timetable for {faculty}. Click the PDF link to download it.",
                intent="timetable_pdf", parsed=parsed,
                pdf_url=f"/timetable/pdf/faculty/{faculty}",
            )
        elif sem:
            return ChatResponse(
                answer=f"Here is the timetable for {sem}. Click the PDF link to download it.",
                intent="timetable_pdf", parsed=parsed,
                pdf_url=f"/timetable/pdf/course/{sem}",
            )
        else:
            return ChatResponse(
                answer="Please mention a faculty name or course to generate a timetable.",
                intent="timetable_pdf", parsed=parsed,
            )

    # Normal flow
    results = retrieve(parsed, user_query)
    answer  = generate_answer(parsed, results, user_query, history)
    return ChatResponse(answer=answer, intent=parsed.get("intent", "general"), parsed=parsed)


# ── PDF download endpoints ────────────────────────────────────────────────────

@app.get("/timetable/pdf/faculty/{faculty_name}")
async def download_faculty_pdf(faculty_name: str):
    pdf_bytes = generate_faculty_timetable_pdf(faculty_name)
    if not pdf_bytes:
        raise HTTPException(status_code=404, detail=f"No timetable found for {faculty_name}")
    return Response(
        content=pdf_bytes, media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="timetable_{faculty_name.replace(" ","_")}.pdf"'}
    )

@app.get("/timetable/pdf/course/{course_name}")
async def download_course_pdf(course_name: str):
    pdf_bytes = generate_course_timetable_pdf(course_name)
    if not pdf_bytes:
        raise HTTPException(status_code=404, detail=f"No timetable found for {course_name}")
    return Response(
        content=pdf_bytes, media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="timetable_{course_name.replace(" ","_")}.pdf"'}
    )


# ── Slot update hook ──────────────────────────────────────────────────────────

@app.put("/slot/update")
async def update_slot(req: SlotUpdateRequest):
    return {
        "status":  "received",
        "message": f"Slot update received for {req.faculty} on {req.day} {req.slot}."
    }


# ── Health check ──────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)