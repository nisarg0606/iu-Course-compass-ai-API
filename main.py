# main.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from utils import get_gemini_response, catalog

app = FastAPI()

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request body model
class QueryRequest(BaseModel):
    query: str
    history: Optional[List[Dict[str, Any]]] = None

# Chat endpoint
@app.post("/chat")
async def chat(request: QueryRequest):
    try:
        reply = get_gemini_response(request.query, request.history)
        return {"response": reply}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/courses")
async def get_courses():
    return catalog

# GET /health - Simple health check
@app.get("/health")
async def health_check():
    return {"status": "ok", "message": "Course Selector API is running"}